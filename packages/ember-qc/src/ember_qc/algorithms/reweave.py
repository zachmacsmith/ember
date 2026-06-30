"""
ember_qc/algorithms/reweave.py
=================================
Reweave — negotiated rip-up-and-reroute for minor embedding (approach 3.5).

Minor embedding *is* multi-net global routing: each chain is a Steiner tree (a
"net") joining terminals (qubits adjacent to its neighbours' chains) while
competing for a congested fabric — the FPGA/VLSI routing problem, where
rip-up-and-reroute has been refined for thirty years. This module ports the two
routing ideas that ``minorminer`` (MM) leaves on the table, as the smallest
useful delta from MM:

1. **A real Steiner inner step.** MM rebuilds a vertex's chain as a *union of
   independent shortest paths* to its placed neighbours (a weak Steiner
   heuristic). Reweave grows one tree with the shortest-path heuristic (SPH):
   each neighbour is wired to the *nearest node of the growing tree*, not to a
   common root, so paths share structure and the chain comes out shorter.

2. **Negotiated congestion (McMurchie–Ebeling 1995).** MM prices an over-used
   qubit by ``diam(G)^(#chains on it)`` — a per-pass snapshot with no memory.
   Reweave prices qubit ``q`` by ``(1 + history[q]) · (1 + pres_fac · occ[q])``,
   where the **present** term rises within a pass as nets pile on and the
   **history** term *accumulates across passes* whenever ``q`` is over-subscribed.
   A consistent, growing price forces chains to negotiate scarce qubits over
   rounds rather than thrash — a Lagrangian congestion dual, not a snapshot.

How it is used matters. A pure cold start (route every chain from scattered
single-qubit seeds) is held back by the very thing the MM paper named as the key
open problem — *initial placement*: without co-locating adjacent vertices,
dense-graph chains balloon. So Reweave's headline mode is an **improver**: it
takes a fast base embedding (MM by default — any registered algorithm works),
then runs negotiated, **large-neighbourhood** rip-up-and-reroute — let the
longest chain take a shortcut through occupied territory, then re-route the
displaced chains in free space — keeping a move only if it shortens the chain and
leaves the embedding valid. Because it tracks the best valid embedding seen, it
**never returns anything worse than its base**, and it spends its whole time
budget shrinking average chain length (anytime behaviour). A BFS-ordered cold
start is the fallback when no base embedding is available.

Registered algorithms:
    reweave            MM-seeded negotiated improver (balanced)
    reweave-thorough   more rounds, deeper search — slower, shorter chains
    reweave-cold       standalone BFS cold start (no MM seed), then improve

Pure Python; no compiled or optional dependencies beyond ``networkx``.
"""

from __future__ import annotations

import collections
import logging
import random
import time
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import (
    Adjacency,
    CostMap,
    Embedding,
    build_adjacency,
    is_valid_embedding,
    reconstruct_path,
    resolve_overlaps,
    weighted_multisource_dijkstra,
)

logger = logging.getLogger(__name__)

_BIG = 1.0e18


class ReweaveRouter:
    """One Reweave run over a fixed (source, target) pair.

    Owns the mutable routing state — chains, per-qubit occupancy and history,
    telemetry counters — so the algorithm reads as a short sequence of named
    phases: seed → (cold-negotiate) → LNS-improve.
    """

    def __init__(
        self,
        source: nx.Graph,
        target: nx.Graph,
        *,
        seed: int = 0,
        base_method: Optional[str] = "minorminer",
        lns_penalty: float = 6.0,
        lns_rounds: int = 40,
        cold_pres_fac0: float = 0.5,
        cold_pres_fac_mult: float = 1.4,
        cold_hist_inc: float = 0.5,
        cold_max_iter: int = 60,
    ):
        self.source = source
        self.target = target
        self.adj: Adjacency = build_adjacency(target)
        self.qubits: Tuple[int, ...] = tuple(self.adj.keys())

        self.src_nodes: List[int] = sorted(source.nodes())
        self.src_adj: Dict[int, List[int]] = {
            v: sorted(source.neighbors(v)) for v in self.src_nodes
        }
        self.src_deg: Dict[int, int] = {v: source.degree(v) for v in self.src_nodes}

        self.base_method = base_method
        self.lns_penalty = lns_penalty
        self.lns_rounds = lns_rounds
        self.cold_pres_fac0 = cold_pres_fac0
        self.cold_pres_fac_mult = cold_pres_fac_mult
        self.cold_hist_inc = cold_hist_inc
        self.cold_max_iter = cold_max_iter

        self.rng = random.Random(seed)
        self.seed = seed

        # Per-qubit routing state.
        self.occ: Dict[int, int] = {q: 0 for q in self.qubits}      # chains currently on q
        self.hist: CostMap = {q: 0.0 for q in self.qubits}          # accumulated congestion price
        self.chains: Embedding = {}

        # Telemetry — plain ints, deterministic ⇒ seed-stable.
        self._visits = [0]                 # Dijkstra nodes settled
        self.routes_built = 0              # chain (re)builds
        self.state_mutations = 0           # qubit add/remove events
        self.overlap_iterations = 0        # Σ over passes of contested-qubit count

    # ----------------------------------------------------------- occupancy ----

    def _claim(self, chain: List[int]) -> None:
        for q in chain:
            self.occ[q] += 1
        self.state_mutations += len(chain)

    def _release(self, chain: List[int]) -> None:
        for q in chain:
            if self.occ[q] > 0:
                self.occ[q] -= 1
        self.state_mutations += len(chain)

    def _set_chain(self, v: int, chain: List[int]) -> None:
        old = self.chains.get(v)
        if old:
            self._release(old)
        self.chains[v] = chain
        self._claim(chain)

    def _occupied_by_others(self) -> Set[int]:
        """Qubits currently claimed by some chain (occ > 0)."""
        return {q for q in self.qubits if self.occ[q] > 0}

    # -------------------------------------------------------------- routing ----

    def _seed_qubit(self) -> int:
        """A single qubit for a vertex with no placed neighbour.

        First placement: lowest-id free qubit (a deterministic anchor). Later
        isolated placements: the free qubit *farthest* (in hops) from all
        occupied qubits, so independent seeds spread out instead of colliding.
        """
        free = [q for q in self.qubits if self.occ[q] == 0]
        occupied = [q for q in self.qubits if self.occ[q] > 0]
        if not occupied:
            return min(free or list(self.qubits))
        dist: Dict[int, int] = {q: 0 for q in occupied}
        dq = collections.deque(occupied)
        while dq:
            x = dq.popleft()
            dx = dist[x]
            for w in self.adj[x]:
                if w not in dist:
                    dist[w] = dx + 1
                    dq.append(w)
        cand = free or list(self.qubits)
        far = 1 << 30
        return max(cand, key=lambda q: (dist.get(q, far), -q))

    def _steiner_route(
        self,
        v: int,
        cost: CostMap,
        forbidden_extra: Optional[Set[int]] = None,
    ) -> Optional[List[int]]:
        """Build the chain for ``v`` as an SPH Steiner tree to its placed neighbours.

        For each placed neighbour ``u`` a node-weighted SSSP is run from ``u``'s
        boundary (qubits adjacent to its chain, not in it). Each search forbids
        ``u``'s *own* chain (``v`` must not route into the neighbour it connects
        to) plus any caller-supplied ``forbidden_extra`` (e.g. all occupied
        qubits, to keep the route in free space). Neighbours are then attached to
        the growing tree nearest-first, so paths share structure.

        Returns a connected, de-duplicated qubit list, ``[seed]`` if ``v`` has no
        placed neighbour, or ``None`` if no neighbour is reachable under the
        constraints.
        """
        self.routes_built += 1
        forbidden_extra = forbidden_extra or set()
        placed = [u for u in self.src_adj[v] if self.chains.get(u)]
        if not placed:
            return [self._seed_qubit()]

        dist_by_u: Dict[int, CostMap] = {}
        pred_by_u: Dict[int, Dict[int, Optional[int]]] = {}
        for u in placed:
            chain_u = set(self.chains[u])
            boundary: Set[int] = set()
            for q in self.chains[u]:
                for w in self.adj[q]:
                    if w not in chain_u:
                        boundary.add(w)
            boundary -= forbidden_extra
            if not boundary:
                continue
            forbidden = forbidden_extra | chain_u
            dist, pred = weighted_multisource_dijkstra(
                self.adj, boundary, cost,
                forbidden=forbidden, visit_counter=self._visits,
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
            for t in tree:
                d = dist.get(t, _BIG)
                if d < best_d or (d == best_d and (best_t is None or t < best_t)):
                    best_d, best_t = d, t
            if best_t is None or best_d >= _BIG:
                continue
            tree.update(reconstruct_path(pred_by_u[u], best_t))
        return sorted(tree)

    def _negotiated_cost(self, pres_fac: float) -> CostMap:
        """``(1 + history) · (1 + pres_fac · occupancy)`` for every qubit."""
        hist = self.hist
        occ = self.occ
        return {q: (1.0 + hist[q]) * (1.0 + pres_fac * occ[q]) for q in self.qubits}

    # ----------------------------------------------------------- seeding -------

    def _seed_embedding(self, timeout: float) -> bool:
        """Warm-start ``self.chains`` from a fast base embedder. True on success."""
        if not self.base_method:
            return False
        try:
            from ember_qc.registry import ALGORITHM_REGISTRY
            algo = ALGORITHM_REGISTRY.get(self.base_method)
            if algo is None:
                import minorminer
                raw = minorminer.find_embedding(
                    self.source, list(self.target.edges()),
                    random_seed=self.seed, timeout=timeout, verbose=0,
                )
            else:
                raw = (algo.embed(self.source, self.target,
                                  timeout=timeout, seed=self.seed) or {}).get("embedding")
        except Exception as exc:
            logger.debug("reweave base seed failed: %s", exc)
            return False
        if not raw:
            return False
        target_nodes = set(self.qubits)
        for v in self.src_nodes:
            chain = raw.get(v)
            if not chain or any(q not in target_nodes for q in chain):
                return False
            self._set_chain(int(v), sorted(int(q) for q in chain))
        return True

    def _bfs_order(self) -> List[int]:
        """Source vertices in BFS order from the highest-degree vertex.

        Placing each vertex right after its neighbours keeps cold-start chains
        compact (the placement issue that sinks a naive randomised order)."""
        if not self.src_nodes:
            return []
        start = max(self.src_nodes, key=lambda v: (self.src_deg[v], -v))
        order: List[int] = []
        seen = {start}
        dq = collections.deque([start])
        while dq:
            x = dq.popleft()
            order.append(x)
            for w in self.src_adj[x]:
                if w not in seen:
                    seen.add(w)
                    dq.append(w)
        for v in self.src_nodes:  # disconnected remainder
            if v not in seen:
                order.append(v)
                seen.add(v)
        return order

    def _cold_start(self, deadline: Optional[float]) -> Optional[Embedding]:
        """Negotiated cold start: BFS-order rip-up-reroute until legal."""
        order = self._bfs_order()
        for it in range(self.cold_max_iter):
            if deadline is not None and time.perf_counter() > deadline:
                break
            pres = min(self.cold_pres_fac0 * (self.cold_pres_fac_mult ** it), 1.0e4)
            cost = self._negotiated_cost(pres)
            for v in order:
                if deadline is not None and time.perf_counter() > deadline:
                    break
                if v in self.chains:
                    self._release(self.chains[v])
                route = self._steiner_route(v, cost) or [self._seed_qubit()]
                self.chains[v] = route
                self._claim(route)
                # keep cost current for qubits whose occupancy just changed
                for q in route:
                    cost[q] = (1.0 + self.hist[q]) * (1.0 + pres * self.occ[q])
            contested = [q for q in self.qubits if self.occ[q] > 1]
            self.overlap_iterations += len(contested)
            if not contested:
                emb = self._materialise()
                if is_valid_embedding(emb, self.source, self.target, adj=self.adj):
                    return emb
            for q in contested:
                self.hist[q] += self.cold_hist_inc
        emb = self._materialise()
        if is_valid_embedding(emb, self.source, self.target, adj=self.adj):
            return emb
        return resolve_overlaps(
            self.chains, self.source, self.target,
            seed=self.rng.randrange(1 << 30), adj=self.adj,
        )

    # ----------------------------------------------------------- improvement ---

    def _lns_improve(self, deadline: Optional[float]) -> Embedding:
        """Large-neighbourhood rip-up-and-reroute to shorten chains.

        Starting from a valid embedding, repeatedly take the longest chain, let
        it re-route along the cheapest tree even if that crosses occupied qubits
        (a *shortcut*), then re-route every chain it displaced through free space.
        A move is committed only if it strictly shortens the target chain and the
        whole embedding stays valid; otherwise the snapshot is restored. This is
        an LNS destroy-repair step — the joint chain motion that one-at-a-time
        free-space refinement cannot find.
        """
        best = self._materialise()
        best_total = sum(len(c) for c in self.chains.values())

        improved = True
        rounds = 0
        while improved and rounds < self.lns_rounds:
            improved = False
            rounds += 1
            for v in sorted(self.chains, key=lambda x: (-len(self.chains[x]), x)):
                if deadline is not None and time.perf_counter() > deadline:
                    return best
                if len(self.chains[v]) <= 1:
                    continue
                if self._try_shorten(v, best_total):
                    best = self._materialise()
                    best_total = sum(len(c) for c in self.chains.values())
                    improved = True
        return best

    def _try_shorten(self, v: int, best_total: int) -> bool:
        """Attempt one LNS move on chain ``v``; commit iff it improves & stays valid."""
        snap_chains = {k: list(c) for k, c in self.chains.items()}
        snap_occ = dict(self.occ)
        old = self.chains[v]

        # 1. Re-route v along the cheapest tree (may cross occupied qubits).
        self._release(old)
        cost = {q: 1.0 + self.lns_penalty * self.occ[q] for q in self.qubits}
        new = self._steiner_route(v, cost)
        if not new or len(new) >= len(old):
            self._restore(snap_chains, snap_occ)
            return False
        self.chains[v] = new
        self._claim(new)

        # 2. Re-route every chain v now overlaps, through free space only.
        new_set = set(new)
        displaced = [
            w for w, chain in self.chains.items()
            if w != v and any(self.occ[q] > 1 for q in chain) and not new_set.isdisjoint(chain)
        ]
        for w in displaced:
            self._release(self.chains[w])
            forbidden = self._occupied_by_others()
            cost_free = {q: 1.0 for q in self.qubits}
            rerouted = self._steiner_route(w, cost_free, forbidden_extra=forbidden)
            if not rerouted:
                self._restore(snap_chains, snap_occ)
                return False
            self.chains[w] = rerouted
            self._claim(rerouted)

        # 3. Accept only if strictly better and still valid. The move touched
        #    only v and the displaced chains, so validity can be checked locally
        #    (a global re-validation here is the LNS hot-loop bottleneck).
        total = sum(len(c) for c in self.chains.values())
        if total < best_total and self._move_valid({v, *displaced}):
            return True
        self._restore(snap_chains, snap_occ)
        return False

    def _move_valid(self, touched: Set[int]) -> bool:
        """Validity check restricted to the chains an LNS move rerouted.

        Every ``_steiner_route`` result is connected and non-empty by
        construction, and chains not in ``touched`` are byte-for-byte unchanged.
        So only two invariants can have broken: a touched chain now shares a
        qubit with another chain (some qubit's occupancy ≠ 1), or an edge
        incident to a touched vertex is no longer covered. Edges between two
        untouched vertices are unaffected.
        """
        for t in touched:
            for q in self.chains[t]:
                if self.occ[q] != 1:
                    return False
        for t in touched:
            chain_t = set(self.chains[t])
            for u in self.src_adj[t]:
                chain_u = self.chains.get(u)
                if not chain_u:
                    return False
                if not any(w in chain_t for q in chain_u for w in self.adj[q]):
                    return False
        return True

    def _restore(self, chains: Embedding, occ: Dict[int, int]) -> None:
        self.chains = {k: list(c) for k, c in chains.items()}
        self.occ = dict(occ)

    # ----------------------------------------------------------- driver --------

    def run(self, deadline: Optional[float], base_timeout: float) -> Optional[Embedding]:
        """Seed (warm or cold), then spend the remaining budget improving chains."""
        seeded = self._seed_embedding(base_timeout)
        if not seeded:
            cold = self._cold_start(deadline)
            if cold is None:
                return None
            # adopt the cold-start state for improvement
            self.chains = {int(v): [int(q) for q in c] for v, c in cold.items()}
            self.occ = {q: 0 for q in self.qubits}
            self._claim([q for c in self.chains.values() for q in c])

        if not is_valid_embedding(self._materialise(), self.source, self.target, adj=self.adj):
            return None
        return self._lns_improve(deadline)

    def _materialise(self) -> Embedding:
        return {int(v): [int(q) for q in chain] for v, chain in self.chains.items()}

    @property
    def counters(self) -> Dict[str, int]:
        return {
            "target_node_visits": int(self._visits[0]),
            "cost_function_evaluations": int(self.routes_built),
            "embedding_state_mutations": int(self.state_mutations),
            "overlap_qubit_iterations": int(self.overlap_iterations),
        }


def embed_reweave(
    source_graph: nx.Graph,
    target_graph: nx.Graph,
    *,
    timeout: float = 60.0,
    seed: int = 0,
    base_fraction: float = 0.5,
    n_restarts: int = 1,
    router_cls: type = ReweaveRouter,
    **params,
) -> dict:
    """Functional entry point returning an ember-qc result dict.

    Runs ``n_restarts`` independent seed→improve attempts (each on a slice of the
    time budget) and keeps the fewest-qubit valid embedding — a deterministic
    best-of-k that trades wall-clock for lower ACL and variance. Within an
    attempt the time budget is split: the base embedder gets up to
    ``base_fraction`` of the slice, the negotiated improver gets the rest. Always
    returns a dict (never ``None``, never raises) so it satisfies the contract.
    """
    start = time.perf_counter()
    deadline = start + timeout if timeout else None
    n_restarts = max(1, n_restarts)
    slice_timeout = (timeout / n_restarts) if timeout else 0.0
    base_timeout = max(1.0, slice_timeout * base_fraction) if timeout else 60.0

    best: Optional[Embedding] = None
    best_total = float("inf")
    visits = routes = muts = overlaps = 0
    try:
        for i in range(n_restarts):
            if deadline is not None and time.perf_counter() >= deadline:
                break
            # each attempt gets its own slice of the overall deadline
            attempt_deadline = (
                min(deadline, start + slice_timeout * (i + 1)) if deadline else None
            )
            router = router_cls(
                source_graph, target_graph, seed=seed + i * 1_000_003, **params
            )
            embedding = router.run(attempt_deadline, base_timeout)
            visits += router.counters["target_node_visits"]
            routes += router.counters["cost_function_evaluations"]
            muts += router.counters["embedding_state_mutations"]
            overlaps += router.counters["overlap_qubit_iterations"]
            if embedding:
                total = sum(len(c) for c in embedding.values())
                if total < best_total:
                    best, best_total = embedding, total

        elapsed = time.perf_counter() - start
        counters = {
            "target_node_visits": visits,
            "cost_function_evaluations": routes,
            "embedding_state_mutations": muts,
            "overlap_qubit_iterations": overlaps,
        }
        if not best:
            return {"embedding": {}, "time": elapsed,
                    "success": False, "status": "FAILURE", **counters}
        return {"embedding": best, "time": elapsed, **counters}
    except Exception as exc:
        logger.error("reweave error: %s", exc)
        return {"embedding": {}, "time": time.perf_counter() - start,
                "success": False, "status": "FAILURE", "error": str(exc)}


# ==============================================================================
# Registration
# ==============================================================================

class _ReweaveBase(EmbeddingAlgorithm):
    """Shared embed() wrapper; variants override the parameters."""

    _params: Dict = {}

    @property
    def version(self) -> str:
        return "2.0.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        seed = kwargs.get("seed", 0)
        if seed is None:
            seed = 0
        return embed_reweave(
            source_graph, target_graph,
            timeout=timeout, seed=int(seed), **self._params,
        )


@register_algorithm("reweave-base")
class ReweaveOriginal(_ReweaveBase):
    """The original (un-optimized) Reweave engine, kept for reference and for
    reproducing the paper's numbers. The production ``reweave`` family
    (registered in ``reweave_opt.py``) wraps this engine with the verified
    optimizations — bounded-region routing, dirty-set LNS, and spur-pruning —
    which make it ~3x faster at equal-or-better ACL."""
    _params = {"base_method": "minorminer"}
