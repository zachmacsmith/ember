"""
ember_qc/algorithms/factored/polish.py
========================================
Post-legality cleanup — the "matched cleanup" counterpart of minorminer's
chainlength phase, so polished-vs-polished comparisons isolate the *allocation*
(who got which region) from the missing-cleanup effect.

Two deterministic, validity-preserving operations on a **legal** embedding:

* :func:`spur_prune` — delete every *removable spur*: a qubit whose removal
  keeps its chain connected AND keeps every incident source edge covered. Pure
  overhead by definition; iterated to a fixpoint. (Same (a)/(b) spec as
  paper 1's ``rw_spur.prune_spurs``, reimplemented here — this package imports
  nothing from the frozen paper-1 code.)
* :func:`shorten_chains` — free-space rip-up-and-shorten: longest chain first,
  rebuild the chain minimum-length through *free qubits only* (all other
  chains hard-forbidden, every placed neighbour required to re-attach), keep
  the rebuild iff strictly fewer qubits. Sweep to a fixpoint. Because overlap
  is unrepresentable and coverage is enforced by ``require_all_neighbors``,
  no fight can restart and validity is preserved by construction — congestion
  prices (and their history) play no role in this phase. This is the same move
  class as minorminer's ``chainlength_patience`` phase.

:func:`polish` = prune -> shorten -> prune (shortening can expose new spurs).
"""

from __future__ import annotations

import time
from typing import Callable, Dict, Iterable, List, Optional, Set

from ember_qc.embedding_backend import (
    Adjacency,
    CostMap,
    Embedding,
    chain_connected,
)
from ember_qc.algorithms.factored.trees import sph_tree

SrcAdj = Dict[int, List[int]]


def spur_prune(chains: Embedding, src_adj: SrcAdj, adj: Adjacency,
               *, deadline: Optional[float] = None,
               only: Optional[Iterable[int]] = None) -> Embedding:
    """Delete removable spur qubits from every chain, to a fixpoint.

    A qubit ``q`` in chain ``phi(v)`` is removable iff (a) ``phi(v) - {q}``
    stays connected in the target, and (b) for every source edge ``(v, u)``
    some qubit of ``phi(v) - {q}`` is still target-adjacent to ``phi(u)``.
    Chains and qubits are visited in sorted order (deterministic); coverage is
    checked against the current, possibly already-pruned neighbour chains.
    Input is not mutated; chains never shrink below one qubit.

    ``deadline`` (perf_counter timestamp) bounds the fixpoint loop: pruning is
    validity-preserving move by move, so stopping early is always safe. Without
    it, hub-and-spoke sources (star/wheel) with chains of hundreds of qubits
    made the quadratic inner loop blow through the caller's whole time budget
    (measured up to ~1000 s in the first full-Ember sweep).

    ``only`` restricts WHICH chains get pruned; coverage is still checked
    against every neighbour in ``chains``, so the caller must pass the
    complete embedding, never a slice. Chains outside ``only`` are returned
    byte-identical.
    """
    work: Embedding = {int(v): [int(q) for q in c] for v, c in chains.items()}
    todo = sorted(work) if only is None else sorted(set(only) & set(work))

    changed = True
    while changed:
        if deadline is not None and time.perf_counter() > deadline:
            return work
        changed = False
        for v in todo:
            if deadline is not None and time.perf_counter() > deadline:
                return work
            chain = work[v]
            if len(chain) <= 1:
                continue
            nbr_sets = {
                u: set(work[u]) for u in src_adj.get(v, []) if work.get(u)
            }
            for q in sorted(chain):  # sorted() snapshots the list
                if len(chain) <= 1:
                    break
                remainder = [x for x in chain if x != q]
                if not chain_connected(remainder, adj):
                    continue
                rem_set = set(remainder)
                covered = True
                for u in src_adj.get(v, []):
                    u_set = nbr_sets.get(u)
                    if not u_set:
                        covered = False  # neighbour unplaced: keep q (safety)
                        break
                    if not any(w in u_set for x in rem_set for w in adj.get(x, ())):
                        covered = False
                        break
                if covered:
                    chain.remove(q)
                    changed = True
    return work


def shorten_chains(
    chains: Embedding,
    src_adj: SrcAdj,
    adj: Adjacency,
    *,
    deadline: Optional[float] = None,
    max_sweeps: int = 8,
    visit_counter: Optional[List[int]] = None,
    vertex_prices: Optional[Callable[[int], CostMap]] = None,
) -> Embedding:
    """Free-space rip-up-and-shorten sweeps over a legal embedding.

    Longest chain first: release ``v``'s chain, rebuild it with the SPH
    assembly with every other chain's qubits forbidden and all placed
    neighbours required; keep iff strictly fewer qubits. A kept rebuild is
    disjoint (forbidden), connected and covering (assembly guarantees) —
    validity is preserved move by move.

    ``vertex_prices`` (optional) supplies a per-vertex qubit price map for the
    rebuild search — the region-respecting variant (notes §3.20 handoff
    discussion): prices rising with distance from ``v``'s placement bias
    *which* short tree the search finds, while acceptance stays on true qubit
    count, so the shorten descends chain length subject to the placement
    instead of scribbling over it. ``None`` (default) is uniform pricing —
    the same move class as minorminer's chainlength phase.
    """
    work: Embedding = {int(v): [int(q) for q in c] for v, c in chains.items()}
    visits = visit_counter if visit_counter is not None else [0]
    ones = {q: 1.0 for q in adj}
    used: Set[int] = {q for c in work.values() for q in c}

    for _ in range(max_sweeps):
        improved = False
        for v in sorted(work, key=lambda x: (-len(work[x]), x)):
            if deadline is not None and time.perf_counter() > deadline:
                return work
            old = work[v]
            if len(old) <= 1:
                continue
            placed = [u for u in src_adj.get(v, []) if work.get(u)]
            if not placed:
                continue
            forbidden = used - set(old)
            prices = vertex_prices(v) if vertex_prices is not None else ones
            new = sph_tree(
                v, placed, work, adj, prices, visits,
                forbidden_extra=forbidden, require_all_neighbors=True,
            )
            if new and len(new) < len(old):
                used -= set(old)
                used |= set(new)
                work[v] = new
                improved = True
        if not improved:
            break
    return work


def polish(
    chains: Embedding,
    src_adj: SrcAdj,
    adj: Adjacency,
    *,
    deadline: Optional[float] = None,
    visit_counter: Optional[List[int]] = None,
) -> Embedding:
    """Full cleanup: spur-prune, shorten in free space, spur-prune again."""
    work = spur_prune(chains, src_adj, adj, deadline=deadline)
    work = shorten_chains(work, src_adj, adj,
                          deadline=deadline, visit_counter=visit_counter)
    return spur_prune(work, src_adj, adj, deadline=deadline)
