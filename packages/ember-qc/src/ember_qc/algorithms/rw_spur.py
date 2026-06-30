"""
ember_qc/algorithms/rw_spur.py
==============================
Reweave variant **reweave-spur** — a cheap spur-pruning post-pass.

Motivation
----------
The matheuristic ``lns-cpsat`` candidate spent seconds of CP-SAT time to shave a
little average-chain-length (ACL) off ``minorminer`` output, and an ablation
showed essentially all of that gain came from one cheap effect: **removing the
redundant chain spurs** that a union-of-shortest-paths embedder leaves behind. A
"spur" is a qubit that dangles off a chain — it keeps the chain connected only to
itself and is not load-bearing for any logical edge. Such a qubit is pure waste:
deleting it lowers ACL and total qubit count with no risk to validity.

This variant reproduces that gain for free. After Reweave produces a *valid*
embedding it runs :func:`prune_spurs`, which deletes **removable spur** qubits to
a fixpoint:

    A qubit ``q`` in chain ``φ(v)`` is a REMOVABLE SPUR iff BOTH
      (a) ``φ(v) \ {q}`` is still a connected subgraph of the target, AND
      (b) ``q`` is not needed for any incident edge — for every source edge
          ``(v, u)`` some qubit of ``φ(v) \ {q}`` is still adjacent (in the
          target graph) to some qubit of ``φ(u)``.

Removing one spur can expose another (the qubit it was propping up is now a leaf),
so the pass iterates to a fixpoint. Qubits are processed in sorted order so the
result is deterministic. The cost is O(chain · degree) per qubit per pass, i.e.
negligible next to routing.

Because pruning only ever *removes* qubits, it cannot create overlaps or
disconnect a chain (guarded by (a)) and cannot drop an edge (guarded by (b)); the
run() override nonetheless re-validates with ``is_valid_embedding`` and falls back
to the unpruned embedding if validity were ever broken.

``prune_spurs`` is written as a free function on ``(embedding, source, target)``
so it can later be promoted verbatim into ``embedding_backend`` as a universal
``prune_spurs`` op (see docs/candidate-algorithms/pf-improvements/spur.md).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx

from ember_qc.registry import register_algorithm
from ember_qc.algorithms.reweave import ReweaveRouter, _ReweaveBase
from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    chain_connected,
    is_valid_embedding,
)


def prune_spurs(
    embedding: Embedding,
    source: nx.Graph,
    target: nx.Graph,
    *,
    adj: Optional[Adjacency] = None,
    src_adj: Optional[Dict[int, List[int]]] = None,
) -> Embedding:
    """Delete removable spur qubits from every chain, to a fixpoint.

    A *removable spur* is a qubit ``q`` in chain ``φ(v)`` such that

        (a) ``φ(v) \\ {q}`` is still connected in ``target``, and
        (b) for every source edge ``(v, u)``, some qubit of ``φ(v) \\ {q}`` is
            still adjacent in ``target`` to some qubit of ``φ(u)``.

    Such a qubit is pure overhead — it lengthens the chain without holding it
    together or carrying any logical edge — so it is dropped. Removing one spur
    can turn a previously-needed qubit into a new spur, so the scan repeats until
    a full pass changes nothing. Qubits and chains are visited in sorted order, so
    the result is deterministic. Coverage / connectivity are always re-checked
    against the *current* (possibly already-pruned) chains, so every invariant of
    a valid embedding is preserved by construction.

    The input ``embedding`` is not mutated; a fresh chain dict is returned. Only
    chains of length ≥ 2 are touched, so a chain is never emptied. ``adj`` and
    ``src_adj`` may be supplied to reuse a caller's frozen adjacencies; otherwise
    they are built from ``target`` / ``source``.

    Args:
        embedding: A (typically valid) ``{source_node: [qubit, ...]}`` map.
        source:    Problem graph (supplies incident edges).
        target:    Hardware graph (supplies qubit adjacency).
        adj:       Optional frozen target adjacency from :func:`build_adjacency`.
        src_adj:   Optional ``{source_node: [neighbour, ...]}`` map.

    Returns:
        A new embedding with all removable spurs deleted.
    """
    if adj is None:
        adj = build_adjacency(target)
    if src_adj is None:
        src_adj = {v: list(source.neighbors(v)) for v in source.nodes()}

    chains: Embedding = {int(v): [int(q) for q in qs] for v, qs in embedding.items()}

    changed = True
    while changed:
        changed = False
        for v in sorted(chains):
            chain = chains[v]
            if len(chain) <= 1:
                continue
            # Current qubit sets of v's placed neighbours (reflects earlier
            # prunings in this same pass — that is what makes coverage exact).
            nbr_sets = {
                u: set(chains[u]) for u in src_adj.get(v, []) if chains.get(u)
            }
            for q in sorted(chain):            # snapshot: sorted() copies the list
                if len(chain) <= 1:
                    break
                remainder = [x for x in chain if x != q]
                # (a) chain must stay connected without q.
                if not chain_connected(remainder, adj):
                    continue
                # (b) every incident edge must still be covered without q.
                rem_set = set(remainder)
                covered = True
                for u in src_adj.get(v, []):
                    u_set = nbr_sets.get(u)
                    if not u_set:
                        covered = False       # neighbour unplaced ⇒ keep q (safety)
                        break
                    if not any(w in u_set for x in rem_set for w in adj.get(x, ())):
                        covered = False
                        break
                if covered:
                    chain.remove(q)
                    changed = True
    return chains


class SpurRouter(ReweaveRouter):
    """Reweave router that spur-prunes its final valid embedding."""

    def run(self, deadline, base_timeout) -> Optional[Embedding]:
        emb = super().run(deadline, base_timeout)
        if not emb:
            return emb
        return self._prune_spurs(emb)

    def _prune_spurs(self, embedding: Embedding) -> Embedding:
        """Prune removable spurs; fall back to the input if validity were broken."""
        pruned = prune_spurs(
            embedding, self.source, self.target,
            adj=self.adj, src_adj=self.src_adj,
        )
        if is_valid_embedding(pruned, self.source, self.target, adj=self.adj):
            return pruned
        return embedding


# SpurRouter is a production optimization component composed into the optimized
# Reweave router in reweave_opt.py (no standalone algorithm here). The
# module-level prune_spurs() free function remains available as a universal
# post-pass for any embedder's output.
