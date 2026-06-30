"""
ember_qc/algorithms/lns_cpsat.py
================================
LNS-CP-SAT — large-neighbourhood search with *exact* CP-SAT region repair
(approach 3.4 of the minor-embedding research brief).

Where Reweave (approach 3.5) untangles a congested embedding *heuristically*
— rip-up the longest chain, re-route the displaced ones with weighted Dijkstra —
this module untangles it *optimally*, one bounded block at a time:

1. **Seed.** Start from a valid ``minorminer`` (MM) embedding. Record it as the
   incumbent best; the search never returns anything worse, so LNS-CP-SAT is a
   strict improver over MM (anytime).

2. **Destroy.** Pick a structured block ``F`` of the source graph — a
   longest-chain vertex plus a few of its source-neighbours (``|F| <= F_MAX``).
   Rip out their chains, freeing the qubits they occupied.

3. **Repair (the crux).** Re-embed *just* ``F`` into a bounded hardware region
   ``R`` (the freed qubits plus a halo of nearby currently-free qubits), with the
   surrounding **fixed** chains pinned as boundary conditions, by solving a
   constraint-programming model with OR-Tools **CP-SAT**. The model is the
   minor-embedding integer program of Bernal et al. (2020, arXiv:1912.08314)
   restricted to ``R``: binary qubit-assignment variables, **single-commodity
   flow** to force each chain to induce a connected subgraph, disjointness, and
   source-edge coverage (F-F couplers and F-to-fixed boundary contacts). The
   objective minimises the qubits used by ``F``. Because the *old* chains of
   ``F`` are always a feasible point of this model (they live inside ``R`` and
   already honour the boundary), the optimum can only match or beat them — the
   block never gets worse.

4. **Accept (SA) + tabu.** Accept the repaired block under a simulated-annealing
   rule (improving and lateral moves always; the design makes strictly-worse
   moves impossible at the block level, so the incumbent is monotone), and keep a
   short **tabu** list of recently-destroyed blocks to diversify which tangle is
   attacked next.

Why it can beat MM: the contested tangle MM commits to greedily (random vertex
order, myopic ``diam(G)^k`` overlap weight) is here dissolved by an *exact*
solver on a small piece, with global structure pinned around it — so chains that
MM leaves long get re-packed optimally. The trade is wall-clock: each repair is
an NP-hard solve, kept tractable only by keeping ``F`` and ``R`` small.

Registered algorithms:
    lns-cpsat   MM-seeded LNS with exact CP-SAT block repair (never worse than MM)

Reuses the shared backend (``ember_qc.embedding_backend``) for adjacency and the
authoritative validity check. Requires ``ortools``; degrades to returning the MM
seed unchanged if CP-SAT is unavailable.
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Dict, List, Optional, Sequence, Set, Tuple

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    chain_connected,
    is_valid_embedding,
)

logger = logging.getLogger(__name__)

# --- Tuning constants ---------------------------------------------------------
F_MAX = 4               # max source vertices freed per destroy step
REGION_CAP = 70         # max qubits in a repair region R (smaller ⇒ faster solves)
CPSAT_CALL_CAP = 2.0    # max wall-seconds for one CP-SAT solve
GROW_SLACK = 3          # how far a freed chain may exceed its old length (lets the
                        # block redistribute qubits — shrink one chain, lengthen
                        # another — for a net win the objective then minimises)
MIN_SOLVE_BUDGET = 0.25 # stop the LNS loop when less budget than this remains
SA_T0 = 2.0             # initial SA temperature (qubit units)
SA_T_END = 0.05         # final SA temperature


class _LnsCpsatRun:
    """One LNS-CP-SAT run over a fixed (source, target) pair.

    Owns the immutable graph data, the mutable *working* embedding, the
    incumbent *best* embedding, the seeded RNG and the telemetry counters, so the
    driver reads as: seed -> (destroy -> repair -> accept)* -> best.
    """

    def __init__(self, source: nx.Graph, target: nx.Graph, *, seed: int = 0):
        self.source = source
        self.target = target
        self.adj: Adjacency = build_adjacency(target)
        self.all_qubits: Set[int] = set(self.adj.keys())

        self.src_nodes: List[int] = sorted(int(v) for v in source.nodes())
        self.src_adj: Dict[int, List[int]] = {
            int(v): sorted(int(u) for u in source.neighbors(v)) for v in source.nodes()
        }

        self.seed = int(seed)
        self.rng = random.Random(self.seed)

        # Mutable search state (populated in run()).
        self.working: Embedding = {}
        self.best: Embedding = {}
        self.working_total = 0
        self.best_total = 0

        # Larger (cluster) destroy moves. Measured to add no improvement over the
        # single-vertex worklist on the benchmark instances while consuming the
        # whole budget (see docs/candidate-algorithms/lns-cpsat.md §4), so the
        # production default is single-vertex only; flip to True to enable them.
        self.use_clusters = False

        # Telemetry — plain ints, deterministic for a fixed seed.
        self.region_qubit_visits = 0     # Σ |R| over repairs (search effort)
        self.repair_solves = 0           # number of CP-SAT solves attempted
        self.state_mutations = 0         # qubits rewritten by committed moves
        self.noimprove_repairs = 0       # repairs that did not lower the cost

    # ---------------------------------------------------------------- seeding --

    def _mm_seed(self, mm_timeout: float) -> Optional[Embedding]:
        """Warm-start from a valid minorminer embedding (or None on failure)."""
        try:
            import minorminer
            raw = minorminer.find_embedding(
                self.source, list(self.target.edges()),
                random_seed=self.seed, timeout=max(0.05, mm_timeout), verbose=0,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("lns-cpsat: minorminer seed failed: %s", exc)
            return None
        if not raw:
            return None
        emb: Embedding = {}
        for v in self.src_nodes:
            chain = raw.get(v)
            if not chain:
                return None
            ch = [int(q) for q in chain]
            if any(q not in self.all_qubits for q in ch):
                return None
            emb[int(v)] = ch
        if not is_valid_embedding(emb, self.source, self.target, adj=self.adj):
            return None
        return emb

    # --------------------------------------------------------------- destroy ---

    def _cluster_block(self, working: Embedding, anchor: int) -> List[int]:
        """A small connected block: ``anchor`` + its longest-chain neighbours."""
        nbrs = sorted(self.src_adj[anchor], key=lambda u: (-len(working[u]), u))
        return [anchor] + nbrs[: F_MAX - 1]

    def _build_region(self, working: Embedding, F: Sequence[int]) -> Tuple[List[int], Set[int]]:
        """Freed qubits (always) plus a bounded BFS halo of currently-free qubits.

        ``R`` always contains every freed qubit, so the old chains of ``F`` remain
        a feasible point of the repair model (guaranteeing the block can never get
        worse). The halo only adds qubits that no fixed chain occupies.
        """
        Fset = set(F)
        used_by_fixed: Set[int] = set()
        for v, chain in working.items():
            if v not in Fset:
                used_by_fixed.update(chain)
        freed: Set[int] = set()
        for v in F:
            freed.update(working[v])
        available = self.all_qubits - used_by_fixed  # freed ⊆ available

        region: Set[int] = set(freed)
        # BFS outward from freed qubits over available qubits until the cap.
        frontier = sorted(freed)
        while frontier and len(region) < REGION_CAP:
            nxt: List[int] = []
            for q in frontier:
                for w in self.adj[q]:
                    if w in available and w not in region:
                        region.add(w)
                        nxt.append(w)
                        if len(region) >= REGION_CAP:
                            break
                if len(region) >= REGION_CAP:
                    break
            frontier = sorted(nxt)
        return sorted(region), used_by_fixed

    # ---------------------------------------------------------------- repair ---

    def _cpsat_repair(
        self,
        working: Embedding,
        F: Sequence[int],
        region: Sequence[int],
        cpsat_time: float,
    ) -> Optional[Dict[int, List[int]]]:
        """Solve the restricted minor-embedding IP for block ``F`` over ``R``.

        Variables (per freed vertex f, per region qubit q):
            x[f,q]   in {0,1}   q belongs to chain φ(f)
            rt[f,q]  in {0,1}   q is the (single) root of φ(f)
            sup[f,q] in [0,U]   flow supply, non-zero only at the root
            fl[f,a,b] in [0,U]  single-commodity flow on directed arc a->b of G[R]

        Constraints:
            Σ_q x[f,q] >= 1                       chain non-empty
            Σ_q x[f,q] <= L_cap[f]                size cap (>= old length)
            Σ_q rt[f,q] == 1 ; rt[f,q] <= x[f,q]  one root, root is selected
            fl[f,a,b] <= U·x[f,a], <= U·x[f,b]    flow only through selected qubits
            sup[f,q] <= U·rt[f,q] ; Σ_q sup == Σ_q x      supply lives at the root
            inflow(q) - outflow(q) == x[f,q] - sup[f,q]   conservation ⇒ connected
            Σ_f x[f,q] <= 1                       chains disjoint (and ⊆ R ⇒ disjoint
                                                  from the pinned fixed chains)
            for source edge (f,g), f,g∈F:  Σ couplers z >= 1  (F-F adjacency)
            for source edge (f,h), h fixed: Σ_{q∈∂φ(h)∩R} x[f,q] >= 1  (boundary)
        Objective:  minimise Σ_{f,q} x[f,q].

        Returns ``{f: [qubits]}`` on OPTIMAL/FEASIBLE, else ``None``.
        """
        try:
            from ortools.sat.python import cp_model
        except Exception as exc:  # pragma: no cover - ortools missing
            logger.debug("lns-cpsat: ortools unavailable: %s", exc)
            return None

        Fset = set(F)
        Rset = set(region)
        adjR: Dict[int, Tuple[int, ...]] = {
            q: tuple(w for w in self.adj[q] if w in Rset) for q in region
        }

        # Boundary contact qubits for each fixed neighbour h of some f∈F:
        # the region qubits adjacent to the (pinned) chain φ(h).
        fixed_boundary: Dict[int, Set[int]] = {}
        for f in F:
            for h in self.src_adj[f]:
                if h in Fset or h in fixed_boundary:
                    continue
                bh: Set[int] = set()
                for q in working[h]:
                    for w in self.adj[q]:
                        if w in Rset:
                            bh.add(w)
                fixed_boundary[h] = bh
                if not bh:
                    # No way for f to ever touch h within R — old solution would
                    # have placed a contact here, so this should not happen; bail.
                    return None

        model = cp_model.CpModel()
        x: Dict[Tuple[int, int], object] = {}
        rt: Dict[Tuple[int, int], object] = {}
        sup: Dict[Tuple[int, int], object] = {}
        fl: Dict[Tuple[int, int, int], object] = {}

        Lcap: Dict[int, int] = {}
        for f in F:
            old_len = len(working[f])
            # Allow a chain to exceed its old length by GROW_SLACK so the block can
            # *redistribute* qubits between its chains for a net reduction. The old
            # chains stay feasible, and the hint + post-solve guard keep the block
            # from ever finishing worse than it started.
            Lcap[f] = max(1, min(old_len + GROW_SLACK, len(region)))

        for f in F:
            U = Lcap[f]
            for q in region:
                x[f, q] = model.NewBoolVar(f"x_{f}_{q}")
                rt[f, q] = model.NewBoolVar(f"r_{f}_{q}")
                sup[f, q] = model.NewIntVar(0, U, f"s_{f}_{q}")
                model.Add(rt[f, q] <= x[f, q])
                model.Add(sup[f, q] <= U * rt[f, q])
            model.Add(sum(rt[f, q] for q in region) == 1)
            model.Add(sum(x[f, q] for q in region) >= 1)
            model.Add(sum(x[f, q] for q in region) <= U)
            model.Add(sum(sup[f, q] for q in region) == sum(x[f, q] for q in region))
            # directed flow arcs
            for q in region:
                for w in adjR[q]:
                    fl[f, q, w] = model.NewIntVar(0, U, f"f_{f}_{q}_{w}")
                    model.Add(fl[f, q, w] <= U * x[f, q])
                    model.Add(fl[f, q, w] <= U * x[f, w])
            # flow conservation ⇒ every selected qubit reachable from the root
            for q in region:
                inflow = [fl[f, w, q] for w in adjR[q]]
                outflow = [fl[f, q, w] for w in adjR[q]]
                model.Add(sum(inflow) - sum(outflow) == x[f, q] - sup[f, q])

        # disjointness across the freed chains
        for q in region:
            model.Add(sum(x[f, q] for f in F) <= 1)

        # source-edge coverage
        Flist = list(F)
        for i, f in enumerate(Flist):
            # F-to-fixed boundary contacts
            for h in self.src_adj[f]:
                if h not in Fset:
                    bh = fixed_boundary[h]
                    model.Add(sum(x[f, q] for q in bh) >= 1)
            # F-F adjacency (one shared coupler suffices)
            for g in Flist[i + 1:]:
                if g not in self.src_adj[f]:
                    continue
                lits = []
                for q in region:
                    for w in adjR[q]:
                        z = model.NewBoolVar(f"z_{f}_{g}_{q}_{w}")
                        model.Add(z <= x[f, q])
                        model.Add(z <= x[g, w])
                        lits.append(z)
                if not lits:
                    return None
                model.Add(sum(lits) >= 1)

        # objective + warm-start hint from the old chains. Hinting x and the root
        # (rt/sup) gives CP-SAT the previous embedding as an initial incumbent, so
        # a time-truncated solve still returns something no worse than the start.
        model.Minimize(sum(x[f, q] for f in F for q in region))
        for f in F:
            oldset = set(working[f])
            root_q = min(oldset) if oldset else None
            for q in region:
                in_chain = q in oldset
                model.AddHint(x[f, q], 1 if in_chain else 0)
                model.AddHint(rt[f, q], 1 if q == root_q else 0)
                model.AddHint(sup[f, q], len(oldset) if q == root_q else 0)

        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1                  # single worker ⇒ deterministic
        solver.parameters.random_seed = self.seed & 0x7FFFFFFF
        solver.parameters.log_search_progress = False
        solver.parameters.max_time_in_seconds = max(0.05, float(cpsat_time))

        self.repair_solves += 1
        self.region_qubit_visits += len(region)
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        repair: Dict[int, List[int]] = {}
        for f in F:
            chain = [int(q) for q in region if solver.Value(x[f, q]) == 1]
            if not chain or not chain_connected(chain, self.adj):
                return None
            repair[int(f)] = sorted(chain)
        return repair

    # ----------------------------------------------------------------- driver --

    def run(self, deadline: float, mm_timeout: float) -> Optional[Embedding]:
        """Seed from MM, then spend the remaining budget on exact block repairs.

        The engine is a **worklist**: a *dirty* set of source vertices whose chain
        might still be shrinkable. The move is a **single-vertex** repair —
        re-embed one freed vertex optimally against its pinned neighbours, which
        prunes the redundant qubits (spurs) MM's union-of-shortest-paths leaves
        behind. When a vertex improves, its neighbours are re-dirtied (their own
        optimum may now be shorter). The loop ends when the worklist drains (a
        fixpoint — anytime and well inside budget here) or the deadline. Optional
        larger **cluster** repairs (``use_clusters``, off by default — they added
        no gain in benchmarking) can run once the worklist drains. Everything is
        deterministic for a fixed seed.
        """
        seed_emb = self._mm_seed(min(mm_timeout, max(0.05, deadline - time.perf_counter())))
        if seed_emb is None:
            return None

        self.working = {v: list(c) for v, c in seed_emb.items()}
        self.best = {v: list(c) for v, c in seed_emb.items()}
        self.working_total = sum(len(c) for c in self.working.values())
        self.best_total = self.working_total

        n = len(self.src_nodes)
        max_iters = min(4000, max(40, 120 * n))
        dirty: Set[int] = set(self.src_nodes)
        cluster_tabu: Set[frozenset] = set()

        it = 0
        while it < max_iters:
            now = time.perf_counter()
            if now + MIN_SOLVE_BUDGET >= deadline:
                break
            cpsat_time = min(CPSAT_CALL_CAP, deadline - now)
            if cpsat_time < MIN_SOLVE_BUDGET:
                break

            if dirty:
                # Longest dirty chain first (deterministic tie-break on id).
                v = max(dirty, key=lambda u: (len(self.working[u]), -u))
                dirty.discard(v)
                if len(self.working[v]) <= 1:
                    continue                       # already minimal — nothing to prune
                it += 1
                gain = self._try_repair([v], cpsat_time, it, max_iters)
                if gain > 0:
                    # v is now optimal for the current neighbours; their optima may
                    # have shifted, so re-dirty them and reopen cluster moves.
                    for h in self.src_adj[v]:
                        dirty.add(h)
                    cluster_tabu.clear()
                continue

            # Worklist drained. Single-vertex pruning has reached its fixpoint —
            # stop here (anytime, deterministic) unless larger cluster moves are
            # explicitly enabled.
            if not self.use_clusters:
                break

            # Optional: cluster repair to try to escape the local optimum.
            anchor = self._next_cluster_anchor(cluster_tabu)
            if anchor is None:
                break                              # fixpoint — converged
            F = self._cluster_block(self.working, anchor)
            cluster_tabu.add(frozenset(F))
            it += 1
            gain = self._try_repair(F, cpsat_time, it, max_iters)
            if gain > 0:
                for f in F:
                    dirty.add(f)
                    for h in self.src_adj[f]:
                        dirty.add(h)
                cluster_tabu.clear()

        return self.best

    def _next_cluster_anchor(self, cluster_tabu: Set[frozenset]) -> Optional[int]:
        """Longest-chain vertex whose cluster block has not been tried (else None)."""
        for v in sorted(self.src_nodes, key=lambda u: (-len(self.working[u]), u)):
            if len(self.working[v]) <= 1:
                break                              # all remaining chains are singletons
            if frozenset(self._cluster_block(self.working, v)) not in cluster_tabu:
                return v
        return None

    def _try_repair(self, F: Sequence[int], cpsat_time: float,
                    it: int, max_iters: int) -> int:
        """Free block ``F``, solve its CP-SAT repair, accept (SA) if not worse.

        Returns the number of qubits saved versus the current working embedding
        (0 if the solve failed, was infeasible, or found no improvement).
        """
        region, _ = self._build_region(self.working, F)
        if not region:
            self.noimprove_repairs += 1
            return 0
        repair = self._cpsat_repair(self.working, F, region, cpsat_time)
        if repair is None:
            self.noimprove_repairs += 1
            return 0

        old_F_total = sum(len(self.working[f]) for f in F)
        new_F_total = sum(len(c) for c in repair.values())
        # Hard guard: a (possibly time-truncated) solve must never worsen a block,
        # keeping the working embedding monotone non-increasing.
        if new_F_total > old_F_total:
            self.noimprove_repairs += 1
            return 0

        candidate = {v: list(c) for v, c in self.working.items()}
        for f in F:
            candidate[int(f)] = repair[int(f)]
        if not is_valid_embedding(candidate, self.source, self.target, adj=self.adj):
            self.noimprove_repairs += 1
            return 0

        cand_total = self.working_total - old_F_total + new_F_total
        delta = cand_total - self.working_total          # <= 0 by construction
        if self._accept(delta, it, max_iters):
            if cand_total != self.working_total:
                self.state_mutations += new_F_total
            self.working = candidate
            self.working_total = cand_total
        if cand_total < self.best_total:
            self.best = {v: list(c) for v, c in candidate.items()}
            self.best_total = cand_total
        else:
            self.noimprove_repairs += 1
        return max(0, old_F_total - new_F_total)

    def _accept(self, delta: int, it: int, max_iters: int) -> bool:
        """Simulated-annealing acceptance on the qubit-count delta.

        Improving and lateral moves (delta <= 0) are always accepted; the design
        makes delta > 0 unreachable, but the Metropolis branch is kept for
        completeness. Temperature is annealed on the *iteration* fraction (not
        wall-clock) so the decision sequence stays deterministic for a fixed seed.
        """
        if delta <= 0:
            return True
        frac = it / max(1, max_iters)
        temp = SA_T0 * ((SA_T_END / SA_T0) ** frac)
        return self.rng.random() < math.exp(-delta / max(1e-9, temp))

    @property
    def counters(self) -> Dict[str, int]:
        return {
            "target_node_visits": int(self.region_qubit_visits),
            "cost_function_evaluations": int(self.repair_solves),
            "embedding_state_mutations": int(self.state_mutations),
            "overlap_qubit_iterations": int(self.noimprove_repairs),
        }


def embed_lns_cpsat(
    source_graph: nx.Graph,
    target_graph: nx.Graph,
    *,
    timeout: float = 60.0,
    seed: int = 0,
) -> dict:
    """Functional entry point returning an ember-qc result dict.

    Splits the budget: minorminer gets up to ~30% (capped) to produce a valid
    seed, the CP-SAT LNS gets the rest to shrink it. Always returns a dict (never
    None, never raises) so it satisfies the algorithm contract.
    """
    start = time.perf_counter()
    deadline = start + timeout if timeout else start + 60.0
    mm_timeout = max(0.5, min(timeout * 0.3, 30.0)) if timeout else 30.0

    try:
        run = _LnsCpsatRun(source_graph, target_graph, seed=int(seed))
        best = run.run(deadline, mm_timeout)
        elapsed = time.perf_counter() - start
        counters = run.counters
        if not best:
            return {"embedding": {}, "time": elapsed,
                    "success": False, "status": "FAILURE", **counters}
        embedding = {int(v): [int(q) for q in chain] for v, chain in best.items()}
        return {"embedding": embedding, "time": elapsed, **counters}
    except Exception as exc:  # pragma: no cover - contract safety net
        logger.error("lns-cpsat error: %s", exc)
        return {"embedding": {}, "time": time.perf_counter() - start,
                "success": False, "status": "FAILURE", "error": str(exc)}


@register_algorithm("lns-cpsat")
class LnsCpsat(EmbeddingAlgorithm):
    """LNS with exact CP-SAT block repair — MM-seeded, never worse than MM."""

    _requires = ["ortools"]

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        seed = kwargs.get("seed", 0)
        if seed is None:
            seed = 0
        return embed_lns_cpsat(
            source_graph, target_graph, timeout=timeout, seed=int(seed),
        )
