"""
ember_qc/algorithms/factored/contact.py
========================================
The contact model (notes s3.45(a), committed before this file existed):
minor embedding with EDGES as the placed objects. One point per source
edge; variables are nets (hpwl over their contact sets); capacity is
per-tile junction density applied natively to the placed points — no
readout chain rule. The s3.43 Armijo integrator and s3.41 cycles carry
over; the s3.44 two-term pressure (hinge + Poisson) applies to the single
2D junction-load grid.

Stage 1 readout is deliberately crude (snap to nearest free coupler,
side assignment by horizontal spread, possibly-disconnected seeds — the
best-effort doctrine; minorminer legalizes).
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from ember_qc.algorithms.factored.field import TileGrid, _lpinv

Point = np.ndarray


def junction_caps(grid: TileGrid):
    """(J, couplers): J[ty, tx] = count of physical cross-orientation
    couplers assigned to tile (v-qubit's column line, h-qubit's row line);
    couplers = {(ty, tx): [(qh, qv), ...]} for the seed snap."""
    J = np.zeros((grid.H, grid.W))
    couplers: Dict[Tuple[int, int], list] = {}
    orient = {q: grid.orient[i] for i, q in enumerate(grid.qubits)}
    # tile coords per qubit from the affine map (rounded)
    tp = grid.coords @ grid.M.T + grid.c
    tx = {q: float(tp[i][0]) for i, q in enumerate(grid.qubits)}
    ty = {q: float(tp[i][1]) for i, q in enumerate(grid.qubits)}
    for q1, q2 in grid.graph.edges():
        if q1 not in orient or q2 not in orient:
            continue
        if orient[q1] == orient[q2]:
            continue
        qh, qv = (q1, q2) if orient[q1] == 1 else (q2, q1)
        r = int(np.clip(round(ty[qh]), 0, grid.H - 1))
        c = int(np.clip(round(tx[qv]), 0, grid.W - 1))
        J[r, c] += 1.0
        couplers.setdefault((r, c), []).append((qh, qv))
    for k in couplers:
        couplers[k].sort()
    return J, couplers


class ContactState:
    """Frozen-within-step structure: per-net contact-index matrices and
    the splat cell assignment. Positions are live."""

    def __init__(self, src: nx.Graph, grid: TileGrid,
                 J: Optional[np.ndarray] = None):
        self.edges = sorted(tuple(sorted(e)) for e in src.edges())
        self.m = len(self.edges)
        self.nodes = sorted(src.nodes())
        eidx = {e: i for i, e in enumerate(self.edges)}
        nets = {v: [] for v in self.nodes}
        for (u, v), i in eidx.items():
            nets[u].append(i)
            nets[v].append(i)
        self.net_list = [nets[v] for v in self.nodes]
        rows = [r if r else [0] for r in self.net_list]
        width = max(len(r) for r in rows)
        self.Nm = np.array([r + [r[0]] * (width - len(r)) for r in rows])
        self.net_mask = np.array(
            [[1.0] * len(r) + [0.0] * (width - len(r)) for r in rows])
        self.has_net = np.array([len(r) > 0 for r in self.net_list])
        self.W, self.H = grid.W, grid.H
        self.J = J if J is not None else junction_caps(grid)[0]
        self.G = _lpinv(grid.H, grid.W)
        self.cs = max(float(self.J.mean()), 1e-9)


def _splat_load(state: ContactState, X: np.ndarray,
                Y: np.ndarray) -> np.ndarray:
    L = np.zeros((state.H, state.W))
    x0 = np.clip(np.floor(X).astype(int), 0, state.W - 1)
    y0 = np.clip(np.floor(Y).astype(int), 0, state.H - 1)
    x1 = np.minimum(x0 + 1, state.W - 1)
    y1 = np.minimum(y0 + 1, state.H - 1)
    fx = np.clip(X - x0, 0.0, 1.0)
    fy = np.clip(Y - y0, 0.0, 1.0)
    np.add.at(L, (y0, x0), (1 - fx) * (1 - fy))
    np.add.at(L, (y0, x1), fx * (1 - fy))
    np.add.at(L, (y1, x0), (1 - fx) * fy)
    np.add.at(L, (y1, x1), fx * fy)
    return L


def _wt(state: ContactState, L: np.ndarray):
    """Two-term cell weights on the junction grid (s3.44 form):
    W = dP/dL = 2*o + psi*1[over]/cs; also returns (P, max overload)."""
    o = np.maximum(0.0, L - state.J)
    sN = o / state.cs
    psi = (state.G @ sN.ravel()).reshape(L.shape)
    P = float((o ** 2).sum() + 0.5 * (sN * psi).sum())
    Wt = 2.0 * o + np.where(o > 0.0, psi, 0.0) / state.cs
    return Wt, P, float(o.max())


def contact_energy(state: ContactState, X: np.ndarray, Y: np.ndarray,
                   lam: float) -> float:
    """E = sum_nets hpwl + lam * P(junction load)."""
    hp = 0.0
    xa = X[state.Nm]
    ya = Y[state.Nm]
    # padded entries repeat a real member: span-neutral
    hp = float((xa.max(1) - xa.min(1) + ya.max(1) - ya.min(1))
               [state.has_net].sum())
    _, P, _ = _wt(state, _splat_load(state, X, Y))
    return hp + lam * P


def contact_forces(state: ContactState, X: np.ndarray, Y: np.ndarray,
                   lam: float):
    """-grad of contact_energy (frozen attributions), per s3.45(a)."""
    m = state.m
    fx = np.zeros(m)
    fy = np.zeros(m)
    xa = X[state.Nm]
    ya = Y[state.Nm]
    nn = np.arange(len(state.net_list))
    sel = state.has_net
    imax = state.Nm[nn, xa.argmax(1)]
    imin = state.Nm[nn, xa.argmin(1)]
    np.add.at(fx, imax[sel], -1.0)
    np.add.at(fx, imin[sel], 1.0)
    jmax = state.Nm[nn, ya.argmax(1)]
    jmin = state.Nm[nn, ya.argmin(1)]
    np.add.at(fy, jmax[sel], -1.0)
    np.add.at(fy, jmin[sel], 1.0)
    # density force through the bilinear splat (classical ePlace form)
    Wt, _, _ = _wt(state, _splat_load(state, X, Y))
    x0 = np.clip(np.floor(X).astype(int), 0, state.W - 1)
    y0 = np.clip(np.floor(Y).astype(int), 0, state.H - 1)
    x1 = np.minimum(x0 + 1, state.W - 1)
    y1 = np.minimum(y0 + 1, state.H - 1)
    fxf = np.clip(X - x0, 0.0, 1.0)
    fyf = np.clip(Y - y0, 0.0, 1.0)
    dLdx = (-(1 - fyf) * Wt[y0, x0] - fyf * Wt[y1, x0]
            + (1 - fyf) * Wt[y0, x1] + fyf * Wt[y1, x1])
    dLdy = (-(1 - fxf) * Wt[y0, x0] - fxf * Wt[y0, x1]
            + (1 - fxf) * Wt[y1, x0] + fxf * Wt[y1, x1])
    fx -= lam * dLdx
    fy -= lam * dLdy
    return fx, fy


def contact_place(src: nx.Graph, grid: TileGrid, *, steps: int = 300,
                  cycles: int = 4, expand: float = 2.0, lam0: float = 0.25,
                  lam_factor: float = 4.0, seed: int = 0):
    """Spread init -> Armijo descent (s3.43 shell) with reshake cycles and
    a hardening tail; returns (contacts array (m, 2), info)."""
    t0 = time.perf_counter()
    from ember_qc.algorithms.factored.placement import source_positions
    state = ContactState(src, grid)
    m = state.m
    if m == 0:
        return np.zeros((0, 2)), {"final_hpwl": 0.0,
                                  "residual_overload": 0.0, "time": 0.0}
    cent = source_positions(src, np.zeros(2), np.ones(2))
    lo = np.array([0.5, 0.5])
    hi = np.array([grid.W - 1.5, grid.H - 1.5])
    npos = {v: lo + (np.asarray(cent[v]) - 0.1) / 0.8 * (hi - lo)
            for v in state.nodes}
    X = np.array([(npos[u][0] + npos[v][0]) / 2.0 for u, v in state.edges])
    Y = np.array([(npos[u][1] + npos[v][1]) / 2.0 for u, v in state.edges])
    info = {"cycle_E": [], "stalled_steps": 0, "steps": 0}
    lam_final = lam0 * (lam_factor ** (max(cycles, 1) - 1))
    best = None
    amp = float(expand)
    for cyc in range(max(cycles, 1)):
        lam = lam0 * (lam_factor ** cyc)
        if cyc > 0:
            cx, cy = X.mean(), Y.mean()
            X = np.clip(cx + amp * (X - cx), 0.0, grid.W - 1.0)
            Y = np.clip(cy + amp * (Y - cy), 0.0, grid.H - 1.0)
            amp *= 0.5
        e_prev = None
        hits = 0
        for _it in range(max(steps, 1)):
            fx, fy = contact_forces(state, X, Y, lam)
            dmax = max(float(np.abs(fx).max()), float(np.abs(fy).max()),
                       1e-12)
            e_cur = contact_energy(state, X, Y, lam)
            alpha = 1.0 / dmax
            accepted = False
            for _k in range(7):
                tX = np.clip(X + alpha * fx, 0.0, grid.W - 1.0)
                tY = np.clip(Y + alpha * fy, 0.0, grid.H - 1.0)
                e_try = contact_energy(state, tX, tY, lam)
                if e_try <= e_cur - 1e-9:
                    X, Y = tX, tY
                    accepted = True
                    break
                alpha *= 0.5
            if not accepted:
                info["stalled_steps"] += 1
                e_try = e_cur
            info["steps"] += 1
            if e_prev is not None and \
                    (e_prev - e_try) < 1e-4 * max(abs(e_prev), 1.0):
                hits += 1
                if hits >= 5:
                    break
            else:
                hits = 0
            e_prev = e_try
        e_cyc = contact_energy(state, X, Y, lam_final)
        info["cycle_E"].append(round(e_cyc, 1))
        if best is None or e_cyc < best[0]:
            best = (e_cyc, X.copy(), Y.copy(), cyc)
    _, X, Y, info["best_cycle"] = best
    # hardening tail: escalate lambda until junction overload clears
    _, _, over = _wt(state, _splat_load(state, X, Y))
    lam_h = lam_final
    for _round in range(10):
        if over <= 0.5:
            break
        lam_h *= 2.0
        e_prev = None
        hits = 0
        for _it in range(50):
            fx, fy = contact_forces(state, X, Y, lam_h)
            dmax = max(float(np.abs(fx).max()), float(np.abs(fy).max()),
                       1e-12)
            e_cur = contact_energy(state, X, Y, lam_h)
            alpha = 1.0 / dmax
            e_try = e_cur
            for _k in range(7):
                tX = np.clip(X + alpha * fx, 0.0, grid.W - 1.0)
                tY = np.clip(Y + alpha * fy, 0.0, grid.H - 1.0)
                e_new = contact_energy(state, tX, tY, lam_h)
                if e_new <= e_cur - 1e-9:
                    X, Y = tX, tY
                    e_try = e_new
                    break
                alpha *= 0.5
            if e_prev is not None and \
                    (e_prev - e_try) < 1e-4 * max(abs(e_prev), 1.0):
                hits += 1
                if hits >= 5:
                    break
            else:
                hits = 0
            e_prev = e_try
        _, _, over = _wt(state, _splat_load(state, X, Y))
    info["lam_hard"] = round(lam_h, 1)
    info["residual_overload"] = round(over, 2)
    xa = X[state.Nm]
    ya = Y[state.Nm]
    info["final_hpwl"] = round(float(
        (xa.max(1) - xa.min(1) + ya.max(1) - ya.min(1))
        [state.has_net].sum()), 1)
    info["time"] = round(time.perf_counter() - t0, 3)
    return np.stack([X, Y], axis=1), info


def contact_seeds(src: nx.Graph, grid: TileGrid, contacts: np.ndarray,
                  couplers: Dict[Tuple[int, int], list]):
    """Stage-1 readout: snap each contact (sorted edge order) to the
    nearest free coupler by ring search over tiles; h-side qubit to the
    endpoint whose contact set is horizontally wider (tie: lower id);
    seeds = per-variable qubit unions (possibly disconnected)."""
    state_edges = sorted(tuple(sorted(e)) for e in src.edges())
    free: Dict[Tuple[int, int], list] = {k: list(v)
                                         for k, v in couplers.items()}
    # horizontal width per variable from placed contacts
    nets: Dict[int, list] = {v: [] for v in src.nodes()}
    for i, (u, v) in enumerate(state_edges):
        nets[u].append(i)
        nets[v].append(i)
    width = {v: (float(np.ptp(contacts[ids, 0])) if ids else 0.0)
             for v, ids in nets.items()}
    seeds: Dict[int, set] = {v: set() for v in src.nodes()}
    taken: set = set()  # qubit-level exclusivity: a qubit sits in MANY
    H, W = grid.H, grid.W  # couplers, so coupler pools alone don't suffice

    def _clean(pool):
        for k, (qh, qv) in enumerate(pool):
            if qh not in taken and qv not in taken:
                return k
        return None

    for i, (u, v) in enumerate(state_edges):
        cx, cy = float(contacts[i][0]), float(contacts[i][1])
        r0, c0 = int(round(cy)), int(round(cx))
        got = None
        for radius in range(0, max(H, W)):
            best = None
            for r in range(max(0, r0 - radius), min(H, r0 + radius + 1)):
                for c in range(max(0, c0 - radius), min(W, c0 + radius + 1)):
                    if max(abs(r - r0), abs(c - c0)) != radius:
                        continue
                    pool = free.get((r, c))
                    if pool and _clean(pool) is not None:
                        d = (r - cy) ** 2 + (c - cx) ** 2
                        if best is None or d < best[0]:
                            best = (d, (r, c))
            if best is not None:
                got = best[1]
                break
        if got is None:
            continue
        k = _clean(free[got])
        qh, qv = free[got].pop(k)
        taken.add(qh)
        taken.add(qv)
        hw = (u if (width[u], -u) > (width[v], -v) else v)
        vw = v if hw == u else u
        seeds[hw].add(qh)
        seeds[vw].add(qv)
    out = {}
    used = set(taken)
    for v in sorted(src.nodes()):
        if seeds[v]:
            out[v] = sorted(seeds[v])
        else:  # isolated or unseated: nearest unclaimed qubit
            for q in grid.qubits:
                if q not in used:
                    used.add(q)
                    out[v] = [q]
                    break
    return out
