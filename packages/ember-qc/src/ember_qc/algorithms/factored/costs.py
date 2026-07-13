"""
ember_qc/algorithms/factored/costs.py
=======================================
The **cost axis**: what a qubit costs to route through.

Design rationale, citations, and the audit of the previous implementation live
in ``docs/paper2/notes.md`` §3. Summary of the chosen default
(:class:`NegotiatedCost`):

    price(q) = (1 + h_q) * beta^occ(q)          beta = estimated diam(G)
    h_q     <- max(0, h_q + alpha*(occ_q - 1))  once per pass, every qubit

* ``beta^occ`` is minorminer's exponential present cost: occupancy depth is
  lexicographically dominant over path length, one occupancy level trades
  against ~beta hops of detour. With ``alpha = 0`` the price *is* minorminer's
  cost — the memoryless corner of the family.
* ``h`` is a Lagrange-multiplier-style history: it rises in proportion to
  overuse while a qubit is contested, holds at exactly-full, decays while
  slack, and floors at zero (the subgradient update of the Lagrangian-routing
  literature — not PathFinder's add-only accumulation, and not a blanket
  forgetting factor).

A cost object owns occupancy, history, and the live price map. ``claim`` /
``release`` are the *only* occupancy mutators and update prices in place, so a
stale price is impossible by construction (the previous implementation cached
prices per pass and forgot to refresh them on release; see notes.md §3.7).

:class:`LinearPathFinderCost` (VPR's linear present term) is kept solely as the
ablation arm for the present-term shape; it shares the same history update so
the ablation isolates exactly one choice.
"""

from __future__ import annotations

import collections
from typing import Dict, List, Sequence, Tuple

from ember_qc.embedding_backend import Adjacency

# Exponent cap so beta**occ stays a finite float with headroom for the
# (1 + h) factor and path summation (beta >= 2 ==> beta**830 > 1e250).
_MAX_EXPONENT_MAGNITUDE = 1.0e250


def estimate_diameter(adj: Adjacency) -> int:
    """Double-BFS-sweep diameter estimate (exact diameter is O(n*m); too slow
    at Advantage scale, and the sweep is near-exact on hardware graphs).

    BFS from the lowest-id node, then BFS from the farthest node found; the
    second eccentricity is the estimate (a lower bound on the true diameter).
    Disconnected targets: the sweep covers the component of the start node,
    which for a hardware graph with dead qubits is the working fabric.
    """
    if not adj:
        return 1

    def _bfs_far(start: int) -> Tuple[int, int]:
        dist = {start: 0}
        dq = collections.deque([start])
        far, far_d = start, 0
        while dq:
            x = dq.popleft()
            dx = dist[x]
            for w in adj[x]:
                if w not in dist:
                    dist[w] = dx + 1
                    if dx + 1 > far_d or (dx + 1 == far_d and w < far):
                        far, far_d = w, dx + 1
                    dq.append(w)
        return far, far_d

    u, _ = _bfs_far(min(adj))
    _, d = _bfs_far(u)
    return max(d, 1)


class NegotiatedCost:
    """``(1 + h) * beta^occ`` with a subgradient history update.

    Args:
        qubits: target nodes (iteration order fixes determinism).
        beta:   base of the exponential present term. The exchange rate:
                one occupancy level ~ ``beta`` hops of detour. Clamped to >= 2
                (at beta = 1 occupancy would be invisible). ``alpha = 0``
                makes the price exactly minorminer's ``beta^occ``.
        alpha:  history step size. 0 disables history entirely (MM corner).
        beta_ramp_passes: if > 0, the *effective* base rises from 1 to ``beta``
                over this many passes (``beta_eff = beta^min(1, t/ramp)``), so
                pass 0 is congestion-oblivious — McMurchie–Ebeling's discovery
                pass. Default 0 = fixed base (minorminer's regime).
    """

    def __init__(
        self,
        qubits: Sequence[int],
        *,
        beta: float,
        alpha: float = 1.0,
        beta_ramp_passes: int = 0,
    ):
        self.qubits: Tuple[int, ...] = tuple(qubits)
        self.beta = max(2.0, float(beta))
        self.alpha = float(alpha)
        self.beta_ramp_passes = int(beta_ramp_passes)

        self.occ: Dict[int, int] = {q: 0 for q in self.qubits}
        self.hist: Dict[int, float] = {q: 0.0 for q in self.qubits}
        self.prices: Dict[int, float] = {q: 1.0 for q in self.qubits}

        self._beta_eff = self.beta
        self._pows: List[float] = [1.0, self._beta_eff]
        self._k_cap = self._exponent_cap(self._beta_eff)
        if self.beta_ramp_passes > 0:
            self._set_beta_eff(1.0)  # pass 0 of a ramp is congestion-oblivious

    # ------------------------------------------------------------- internals --

    @staticmethod
    def _exponent_cap(beta_eff: float) -> int:
        import math
        if beta_eff <= 1.0:
            return 1
        return max(1, int(math.log(_MAX_EXPONENT_MAGNITUDE) / math.log(beta_eff)))

    def _set_beta_eff(self, beta_eff: float) -> None:
        self._beta_eff = beta_eff
        self._pows = [1.0, beta_eff]
        self._k_cap = self._exponent_cap(beta_eff)

    def _bpow(self, k: int) -> float:
        k = min(k, self._k_cap)
        pows = self._pows
        while len(pows) <= k:
            pows.append(pows[-1] * self._beta_eff)
        return pows[k]

    def _price(self, q: int) -> float:
        return (1.0 + self.hist[q]) * self._bpow(self.occ[q])

    def _refresh_all(self) -> None:
        price = self.prices
        for q in self.qubits:
            price[q] = self._price(q)

    # ------------------------------------------------------------- interface --

    def claim(self, chain: Sequence[int]) -> None:
        occ, prices = self.occ, self.prices
        for q in chain:
            occ[q] += 1
            prices[q] = self._price(q)

    def release(self, chain: Sequence[int]) -> None:
        occ, prices = self.occ, self.prices
        for q in chain:
            if occ[q] > 0:
                occ[q] -= 1
            prices[q] = self._price(q)

    def contested(self) -> List[int]:
        """Qubits currently claimed by more than one chain."""
        occ = self.occ
        return [q for q in self.qubits if occ[q] > 1]

    def start_pass(self, pass_idx: int) -> None:
        """Set the effective base for this pass (no-op unless ramping)."""
        if self.beta_ramp_passes <= 0:
            return
        frac = min(1.0, pass_idx / self.beta_ramp_passes)
        beta_eff = self.beta ** frac
        if beta_eff != self._beta_eff:
            self._set_beta_eff(beta_eff)
            self._refresh_all()

    def apply_history_update(self) -> None:
        """Subgradient step on every qubit: up with overuse, down when slack.

        ``h <- max(0, h + alpha*(occ - 1))``: occ >= 2 raises the price memory
        in proportion to overuse, occ == 1 holds it, occ == 0 decays it. With
        ``alpha = 0`` history stays identically zero (the minorminer corner).
        """
        if self.alpha == 0.0:
            return
        occ, hist, prices = self.occ, self.hist, self.prices
        alpha = self.alpha
        for q in self.qubits:
            h = hist[q] + alpha * (occ[q] - 1)
            hist[q] = h if h > 0.0 else 0.0
            prices[q] = self._price(q)


class LinearPathFinderCost(NegotiatedCost):
    """VPR's linear present term — the ablation arm for present-term *shape*.

    ``price(q) = (1 + h_q) * (1 + pres_t * occ(q))`` with the geometric
    ``pres_fac`` ramp (VPR defaults: start 0.5, x1.3 per pass, capped). The
    history update is inherited unchanged, so comparing this against
    :class:`NegotiatedCost` isolates exactly the linear-vs-exponential choice
    (docs/paper2/notes.md §3.3: the linear form prices overlap *mass* and, on
    paths longer than 2, prefers deepening a pile-up over spreading it).
    """

    def __init__(
        self,
        qubits: Sequence[int],
        *,
        beta: float = 0.0,  # unused; accepted for interface parity
        alpha: float = 1.0,
        beta_ramp_passes: int = 0,  # unused; the pres ramp plays this role
        pres0: float = 0.5,
        pres_mult: float = 1.3,
        pres_max: float = 1000.0,
    ):
        self.pres0 = float(pres0)
        self.pres_mult = float(pres_mult)
        self.pres_max = float(pres_max)
        self._pres = self.pres0
        super().__init__(qubits, beta=2.0, alpha=alpha, beta_ramp_passes=0)

    def _price(self, q: int) -> float:
        return (1.0 + self.hist[q]) * (1.0 + self._pres * self.occ[q])

    def start_pass(self, pass_idx: int) -> None:
        pres = min(self.pres0 * (self.pres_mult ** pass_idx), self.pres_max)
        if pres != self._pres:
            self._pres = pres
            self._refresh_all()


COSTS = {
    "negotiated": NegotiatedCost,
    "linear": LinearPathFinderCost,
}
