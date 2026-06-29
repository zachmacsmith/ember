"""
ember_qc/algorithms/pf_dirtyset.py
==================================
PathFinder variant **pathfinder-dirtyset** — dirty-set incremental LNS reroute
(experiment S4).

Motivation
----------
The baseline LNS improver :meth:`PathFinderRouter._lns_improve` is *round-based*:
every round it re-sweeps **every** chain, longest-first, calling ``_try_shorten``
on each, and only stops once a full round produces no improvement (or the round /
deadline cap is hit). Once the embedding has mostly stabilised that is wasted
work — re-examining a far-away chain whose neighbourhood has not changed since it
last failed cannot find a new shortcut. On a converging cell the baseline still
pays for at least one full all-chains sweep just to *prove* it is done, plus all
the redundant re-examinations of stable chains in the intervening rounds.

This variant keeps the move operator and the accept rule **byte-for-byte** (it
reuses ``_try_shorten`` unchanged) and changes only the *schedule*: a worklist /
"dirty set". A vertex is *dirty* when a shortcut for it might newly exist. Only
dirty vertices are examined; a vertex that fails ``_try_shorten`` is dropped from
the worklist and is not looked at again until something in its neighbourhood
changes.

Why the propagation rule is exactly the closed source-neighbourhood
------------------------------------------------------------------
``_try_shorten(u)`` re-routes ``u``'s chain as a Steiner tree to the boundaries
of ``u``'s *placed source-neighbours*, accepting only if the chain shrinks. Its
outcome therefore depends on (i) ``u``'s own current chain (the length it must
beat) and (ii) the chains of ``u``'s source-neighbours (the routing targets).
An accepted move at ``v`` changes the chains of exactly ``{v} ∪ displaced`` (the
shortened ``v`` plus the chains its shortcut displaced and rerouted). The only
vertices ``u`` whose ``_try_shorten`` outcome can have changed are thus those
whose own chain changed, or one of whose source-neighbours' chains changed — i.e.
the **closed source-neighbourhood of the changed chains**:

    redirty = (changed) ∪ ⋃_{w ∈ changed} source_neighbours(w),
    where  changed = {v} ∪ displaced.

Those are re-marked dirty; everything else stays clean. (This is the same dirty
rule the ``lns-cpsat`` candidate uses to drive its region repairs.) The loop runs
to a local fixpoint — an empty worklist — or the deadline.

Recovering the displaced set without touching the baseline
----------------------------------------------------------
``_try_shorten`` computes its ``displaced`` list internally and does not return
it. We recover it without editing the frozen baseline: on an **accepted** move,
``_try_shorten`` re-assigns a fresh list object to ``self.chains[v]`` and to each
displaced ``self.chains[w]`` and leaves every other chain's list object untouched
(a *rejected* move restores the whole dict, but we never inspect that case). So a
shallow snapshot of the chain dict before the call, diffed by list-object
identity afterwards, yields exactly ``{v} ∪ displaced`` — see
:meth:`DirtySetRouter._try_shorten_tracked`.

Determinism & safety
--------------------
The next vertex is ``max(dirty, key=(chain length, -id))`` — longest dirty chain
first, smallest id on ties; the key is unique per vertex, so the choice is
deterministic regardless of set iteration order (matching the baseline's
longest-first / lowest-id preference and ``lns-cpsat``'s worklist). Only
``_try_shorten`` mutates the embedding, and it commits a move only when it both
shortens a chain and leaves the embedding valid, so — exactly as in the baseline
— the routine can only return a valid embedding no worse than its input. The new
schedule may reach a *different* fixpoint than the round-based sweep (the cost
function depends on global occupancy, which the source-local rule does not chase),
so ACL is verified to be not-worse empirically (see
docs/candidate-algorithms/pf-improvements/dirtyset.md).
"""

from __future__ import annotations

import time
from typing import Optional, Set, Tuple

from ember_qc.registry import register_algorithm
from ember_qc.embedding_backend import Embedding
from ember_qc.algorithms.pathfinder import PathFinderRouter, _PathFinderBase


class DirtySetRouter(PathFinderRouter):
    """PathFinderRouter whose LNS phase is driven by an incremental worklist."""

    def _try_shorten_tracked(
        self, v: int, best_total: int
    ) -> Tuple[bool, Tuple[int, ...]]:
        """Call the unchanged ``_try_shorten`` and recover its displaced set.

        On an accepted move only ``v`` and the displaced chains are re-assigned
        fresh list objects; every other chain keeps its identity (and a rejected
        move restores the whole dict, which we never inspect because we only read
        ``displaced`` on acceptance). Diffing list-object identity against a
        pre-call shallow snapshot of ``self.chains`` therefore yields exactly the
        displaced vertices. ``_try_shorten`` itself is reused verbatim.
        """
        before = dict(self.chains)  # shallow: vertex -> current chain list object
        accepted = self._try_shorten(v, best_total)
        if not accepted:
            return False, ()
        displaced = tuple(
            w
            for w, chain in self.chains.items()
            if w != v and before.get(w) is not chain
        )
        return True, displaced

    def _lns_improve(self, deadline: Optional[float]) -> Embedding:
        """Dirty-set incremental version of the baseline LNS improver.

        Same move operator (``_try_shorten``) and accept rule as the baseline;
        only the schedule differs. Instead of re-sweeping all chains each round,
        it maintains a worklist of vertices whose shortcut opportunities may have
        changed and runs to a local fixpoint (empty worklist) or the deadline.
        """
        best = self._materialise()
        best_total = sum(len(c) for c in self.chains.values())

        # Every vertex starts dirty. The unique (length, -id) key makes the
        # longest-first / lowest-id choice deterministic despite set ordering.
        dirty: Set[int] = set(self.chains)

        while dirty:
            if deadline is not None and time.perf_counter() > deadline:
                return best
            v = max(dirty, key=lambda u: (len(self.chains[u]), -u))
            dirty.discard(v)
            if len(self.chains[v]) <= 1:
                continue  # a singleton can never be shortened (baseline skips it too)

            accepted, displaced = self._try_shorten_tracked(v, best_total)
            if not accepted:
                continue  # v is clean until a neighbourhood change re-dirties it

            best = self._materialise()
            best_total = sum(len(c) for c in self.chains.values())

            # Re-dirty the closed source-neighbourhood of every changed chain:
            # those are exactly the vertices whose _try_shorten outcome can have
            # changed (their own chain, or a source-neighbour's chain, moved).
            for w in (v, *displaced):
                dirty.add(w)
                dirty.update(self.src_adj[w])

        return best


# DirtySetRouter is a production optimization component composed into the
# optimized PathFinder router in pathfinder_opt.py (no standalone algorithm here).
