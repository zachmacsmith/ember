"""
ember_qc/algorithms/rw_ripup.py
===============================
Reweave **rip-up selection** variants — the search lever (#2) that decides which
chain to tear out and reroute next during large-neighbourhood improvement.

Reweave's optimized LNS (the dirty-set schedule in ``rw_dirtyset.py``) repeatedly
picks the *longest* dirty chain and tries to shorten it (``_try_shorten``). The
move operator and accept rule are strong; the open question is whether the
*selection* — which chain to attack first — changes the local optimum the
improver settles into (quality) or just how fast it gets there (speed). This is
the embedding analogue of FPGA "which net to rip up and reroute" (PathFinder /
RL-Ripper).

Design.  ``_RipupRouter`` re-implements the dirty-set ``_lns_improve`` loop with
the selection key factored into a single hook, ``_ripup_key(v)`` — everything else
(the ``_try_shorten`` move, the accept rule, the closed-neighbourhood dirty
propagation, the deadline) is **byte-for-byte the dirty-set baseline**, so each
variant differs *only* in selection order and can only return a valid embedding no
worse than its input. Each policy overrides just ``_ripup_key``.

Registered ``reweave-ripup-<policy>``:
  longest      (baseline parity)  longest chain first — same as ``reweave``.
  boundary     chain bordering the most *distinct* other chains (most reroute room).
  contention   chain on the highest-traffic qubits (sum of distinct neighbour chains).
  inflation    chain longest relative to its source degree (most wasteful).
  shortest     contrarian control (shortest first) — bounds whether direction matters.
"""
from __future__ import annotations

import time
from typing import Optional, Set

from ember_qc.registry import register_algorithm
from ember_qc.embedding_backend import Embedding
from ember_qc.algorithms.reweave import _ReweaveBase
from ember_qc.algorithms.reweave_opt import _OptimizedRouter


class _RipupRouter(_OptimizedRouter):
    """Optimized Reweave whose LNS rip-up *selection* is pluggable via ``_ripup_key``.

    The loop body is the dirty-set baseline (``DirtySetRouter._lns_improve``); only
    ``max(dirty, key=...)`` is redirected through ``self._ripup_key``. A per-iteration
    qubit→owning-chain map (``self._owner``) is provided for policies that need to
    reason about neighbouring chains. The default key reproduces the baseline
    (longest-first, lowest-id tie-break) exactly."""

    def _build_owner(self):
        owner = {}
        for v, chain in self.chains.items():
            for q in chain:
                owner[q] = v
        self._owner = owner

    def _ripup_key(self, v: int):
        return (len(self.chains[v]), -v)

    def _lns_improve(self, deadline: Optional[float]) -> Embedding:
        best = self._materialise()
        best_total = sum(len(c) for c in self.chains.values())
        dirty: Set[int] = set(self.chains)
        self._build_owner()

        while dirty:
            if deadline is not None and time.perf_counter() > deadline:
                return best
            v = max(dirty, key=self._ripup_key)
            dirty.discard(v)
            if len(self.chains[v]) <= 1:
                continue

            accepted, displaced = self._try_shorten_tracked(v, best_total)
            if not accepted:
                continue

            best = self._materialise()
            best_total = sum(len(c) for c in self.chains.values())
            self._build_owner()  # ownership changed on the accepted move
            for w in (v, *displaced):
                dirty.add(w)
                dirty.update(self.src_adj[w])
        return best

    # -- helpers for neighbour-aware policies ------------------------------
    def _neighbour_chains(self, v: int) -> Set[int]:
        """Distinct other chains adjacent (in the target) to v's chain."""
        owner = self._owner
        out: Set[int] = set()
        for q in self.chains[v]:
            for w in self.adj[q]:
                o = owner.get(w)
                if o is not None and o != v:
                    out.add(o)
        return out


class _LongestRipup(_RipupRouter):
    pass  # default key == baseline


class _BoundaryRipup(_RipupRouter):
    def _ripup_key(self, v: int):
        return (len(self._neighbour_chains(v)), len(self.chains[v]), -v)


class _ContentionRipup(_RipupRouter):
    def _ripup_key(self, v: int):
        owner = self._owner
        total = 0
        for q in self.chains[v]:
            seen = set()
            for w in self.adj[q]:
                o = owner.get(w)
                if o is not None and o != v:
                    seen.add(o)
            total += len(seen)
        return (total, len(self.chains[v]), -v)


class _InflationRipup(_RipupRouter):
    def _ripup_key(self, v: int):
        return (len(self.chains[v]) - self.src_deg[v], len(self.chains[v]), -v)


class _ShortestRipup(_RipupRouter):
    def _ripup_key(self, v: int):
        return (-len(self.chains[v]), -v)


_POLICIES = {
    "longest": _LongestRipup,
    "boundary": _BoundaryRipup,
    "contention": _ContentionRipup,
    "inflation": _InflationRipup,
    "shortest": _ShortestRipup,
}


def _make_variant(policy: str, router_cls: type) -> type:
    cls = type(
        f"ReweaveRipup_{policy}",
        (_ReweaveBase,),
        {
            "_params": {"router_cls": router_cls, "base_method": "minorminer"},
            "__doc__": f"Reweave (MM-seeded) with '{policy}' rip-up selection.",
        },
    )
    return register_algorithm(f"reweave-ripup-{policy}")(cls)


_VARIANTS = {p: _make_variant(p, cls) for p, cls in _POLICIES.items()}
