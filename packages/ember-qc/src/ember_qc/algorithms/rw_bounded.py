"""
ember_qc/algorithms/rw_bounded.py
=================================
Reweave variant **S3 — early-termination + bounded routing region**.

ISOLATED experiment (see docs/candidate-algorithms/pf-improvements/bounded.md).
The frozen baseline ``reweave`` rebuilds every chain in ``_steiner_route`` by
running, for each placed neighbour, a node-weighted Dijkstra *from that
neighbour's boundary over the whole target graph* — a full single-source
shortest-path (SSSP). On the small/dense D-Wave patches in the harness that
settles ~all 680 (Pegasus-6) / 576 (Zephyr-4) qubits **per neighbour, per
rebuild** (measured: ~675 settled nodes × ~28 neighbours × 120 rebuilds for one
n40 d0.7 run). Almost all of that work is wasted: instrumentation shows the chain
the baseline actually returns never strays more than **one hop** outside the
union of the chains it is wiring together.

This variant keeps the baseline's *tree-assembly* (same root choice, same
nearest-tree attachment ⇒ same chains ⇒ same ACL) but shrinks the **search
space** each Dijkstra is allowed to explore, with two cheap, validity-preserving
speed-ups:

(1) **Bounded region.** Each rebuild restricts routing to a BFS-ball of radius
    ``R`` around the union of (the vertex's own current chain ∪ its placed
    neighbours' chains). Implemented by running the Dijkstra on a *region-
    restricted adjacency* (qubits outside the ball are simply absent), which is
    cheaper than materialising the ~hundreds of "outside" qubits as a
    ``forbidden=`` set every call. The ball is built once per rebuild and shared
    by all the neighbour searches.

(2) **Early termination.** Each per-neighbour Dijkstra only has to reach the
    cluster *centre* — the vertex's own released footprint (``v_old``), which in
    a valid embedding sat adjacent to every neighbour, so it is exactly where the
    Steiner meeting-point/root and the growing tree end up. Passing ``v_old`` as
    ``targets=`` lets each search stop the instant it touches the centre instead
    of draining the whole ball. Because the root/tree sit *at* the centre, they
    are settled by the time the search stops, so root selection and attachment
    are unchanged (verified: ACL identical to the bit). Targeting the centre
    (rather than the far *other-neighbour boundaries*, which a search must cross
    the whole cluster to reach) is what makes early-stop actually pay: it cuts
    settled nodes ~4x on n40 d0.7. When ``v_old`` is empty (a vertex's first
    placement, e.g. early in a cold start) there is no centre to aim at and the
    search is bounded by the ball alone.

**Validity is never sacrificed.** If the ball is too small to wire some
neighbour, the radius is doubled and the rebuild retried; the final fallback runs
the *unbounded* assembly, which is byte-for-byte the baseline. So the variant can
only ever match the baseline's coverage — it just usually gets there faster.

Registered algorithms:
    reweave-bounded        region + early-termination (recommended)
    reweave-bounded-region region only (ablation: no targets early-stop)

Pure Python; no dependencies beyond the baseline's.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from ember_qc.registry import register_algorithm
from ember_qc.embedding_backend import (
    Adjacency,
    CostMap,
    reconstruct_path,
    weighted_multisource_dijkstra,
)
from ember_qc.algorithms.reweave import (
    ReweaveRouter,
    _ReweaveBase,
    embed_reweave,
    _BIG,
)


class ReweaveBoundedRouter(ReweaveRouter):
    """Reweave router with a bounded, early-terminating Steiner inner step.

    Adds four knobs on top of :class:`ReweaveRouter`; everything else (seeding,
    LNS, negotiated cost, telemetry) is inherited unchanged.

    Args:
        region_radius:  BFS-ball radius around the seed footprint (the first,
                        tightest attempt). Measurements show the baseline tree
                        stays within ~1 hop of the seed, so 1 is plenty (and the
                        ball still spans ~56%% of a Pegasus-6 patch); the
                        expansion fallback covers the rare wider tree.
        region_max_expand: how many times to double the radius (per rebuild) when
                        a neighbour can't be wired inside the ball, before the
                        unbounded baseline fallback.
        early_stop:     stop each per-neighbour Dijkstra once it reaches the
                        cluster centre (the vertex's released ``v_old``
                        footprint), via Dijkstra ``targets=``.
        region_enabled: master switch for the ball restriction (ablation: off ⇒
                        full-graph search, only ``early_stop`` may apply).
    """

    def __init__(
        self,
        source: nx.Graph,
        target: nx.Graph,
        *,
        region_radius: int = 1,
        region_max_expand: int = 2,
        early_stop: bool = True,
        region_enabled: bool = True,
        **kwargs,
    ):
        super().__init__(source, target, **kwargs)
        self.region_radius = int(region_radius)
        self.region_max_expand = int(region_max_expand)
        self.early_stop = bool(early_stop)
        self.region_enabled = bool(region_enabled)

    # ------------------------------------------------------------- region ------

    def _bfs_ball(self, seed: Set[int], radius: int) -> Set[int]:
        """All qubits within ``radius`` hops of ``seed`` (multi-source BFS)."""
        adj = self.adj
        ball = set(seed)
        frontier = list(seed)
        for _ in range(radius):
            nxt: List[int] = []
            for x in frontier:
                for w in adj[x]:
                    if w not in ball:
                        ball.add(w)
                        nxt.append(w)
            if not nxt:
                break
            frontier = nxt
        return ball

    def _restrict_adj(self, region: Set[int]) -> Adjacency:
        """Adjacency induced on ``region`` (out-of-region neighbours dropped).

        Filtering keeps each node's original neighbour order, so Dijkstra
        tie-breaking matches the baseline for every edge that stays in-region.
        """
        adj = self.adj
        return {q: tuple(w for w in adj[q] if w in region) for q in region}

    # ------------------------------------------------------------- routing -----

    def _steiner_route(
        self,
        v: int,
        cost: CostMap,
        forbidden_extra: Optional[Set[int]] = None,
    ) -> Optional[List[int]]:
        """Bounded, early-terminating version of the baseline SPH Steiner step.

        Same contract as :meth:`ReweaveRouter._steiner_route`: returns a
        connected, de-duplicated qubit list, ``[seed]`` if ``v`` has no placed
        neighbour, or ``None`` if no neighbour is reachable.
        """
        self.routes_built += 1
        forbidden_extra = forbidden_extra or set()
        placed = [u for u in self.src_adj[v] if self.chains.get(u)]
        if not placed:
            return [self._seed_qubit()]

        # Per-neighbour boundaries (qubits adjacent to a neighbour's chain, not in
        # it, and not caller-forbidden). Computed once; reused across attempts.
        chain_set: Dict[int, Set[int]] = {u: set(self.chains[u]) for u in placed}
        boundary: Dict[int, Set[int]] = {}
        for u in placed:
            cu = chain_set[u]
            b: Set[int] = set()
            for q in self.chains[u]:
                for w in self.adj[q]:
                    if w not in cu:
                        b.add(w)
            b -= forbidden_extra
            boundary[u] = b

        # Cluster centre = this vertex's own footprint. During an LNS reroute the
        # entry still holds the just-released chain (release() decrements
        # occupancy but does not delete it); empty only on a first placement.
        center: Set[int] = set(self.chains.get(v, ()))

        if not self.region_enabled:
            return self._assemble(placed, cost, forbidden_extra,
                                  chain_set, boundary, center, self.adj, region=None)

        # Seed footprint for the ball: the centre ∪ the placed-neighbour chains.
        seed: Set[int] = set(center)
        for u in placed:
            seed |= chain_set[u]

        radius = self.region_radius
        for _ in range(self.region_max_expand + 1):
            region = self._bfs_ball(seed, radius)
            region_adj = self._restrict_adj(region)
            tree = self._assemble(placed, cost, forbidden_extra,
                                  chain_set, boundary, center, region_adj, region)
            if tree is not None:
                # Coverage guard: every neighbour with a (non-empty, reachable)
                # boundary must end up adjacent to the tree. If one fell outside
                # the ball, grow the ball and retry.
                ts = set(tree)
                if all(not boundary[u] or not ts.isdisjoint(boundary[u])
                       for u in placed):
                    return tree
            radius *= 2

        # Unbounded fallback == baseline assembly: guarantees we never connect
        # fewer neighbours than the baseline would.
        return self._assemble(placed, cost, forbidden_extra,
                              chain_set, boundary, center, self.adj, region=None)

    def _assemble(
        self,
        placed: List[int],
        cost: CostMap,
        forbidden_extra: Set[int],
        chain_set: Dict[int, Set[int]],
        boundary: Dict[int, Set[int]],
        center: Set[int],
        adj: Adjacency,
        region: Optional[Set[int]],
    ) -> Optional[List[int]]:
        """Baseline root-and-attach tree assembly over a (possibly restricted) adj.

        With ``adj is self.adj``, ``region is None`` and ``early_stop`` off this is
        identical to the baseline — that is exactly the unbounded fallback path.
        """
        # Early-stop targets: the in-region centre footprint. Each neighbour's
        # search halts once it has settled the centre (minus its own boundary /
        # forbidden qubits); the root/tree live there, so they are settled first.
        early = self.early_stop and region is not None and bool(center)
        center_in: Set[int] = (center & region) if early else set()

        dist_by_u: Dict[int, CostMap] = {}
        pred_by_u: Dict[int, Dict[int, Optional[int]]] = {}
        for u in placed:
            b = boundary[u]
            if not b:
                continue
            forbidden = forbidden_extra | chain_set[u]
            targets: Optional[Set[int]] = None
            if early:
                tg = center_in - b - forbidden
                if tg:
                    targets = tg
            dist, pred = weighted_multisource_dijkstra(
                adj, b, cost, forbidden=forbidden, targets=targets,
                visit_counter=self._visits,
            )
            if dist:
                dist_by_u[u] = dist
                pred_by_u[u] = pred

        if not dist_by_u:
            return None

        # Root: qubit reachable from the most neighbours, then least total cost.
        reach: Dict[int, int] = {}
        total: Dict[int, float] = {}
        for dist in dist_by_u.values():
            for q, d in dist.items():
                reach[q] = reach.get(q, 0) + 1
                total[q] = total.get(q, 0.0) + d
        root = max(reach, key=lambda q: (reach[q], -total[q], -q))

        tree: Set[int] = {root}
        for u in sorted(dist_by_u, key=lambda u: (dist_by_u[u].get(root, _BIG), u)):
            dist = dist_by_u[u]
            best_t, best_d = None, _BIG
            attach = (root,) if self.union_paths else tree
            for t in attach:
                d = dist.get(t, _BIG)
                if d < best_d or (d == best_d and (best_t is None or t < best_t)):
                    best_d, best_t = d, t
            if best_t is None or best_d >= _BIG:
                continue
            tree.update(reconstruct_path(pred_by_u[u], best_t))
        return sorted(tree)


# ReweaveBoundedRouter is a production optimization component: it is composed
# into the optimized Reweave router in reweave_opt.py (no standalone
# algorithm is registered here). Its __init__ defaults (region_radius=1,
# region_max_expand=2, early_stop=True, region_enabled=True) are the verified
# configuration.
