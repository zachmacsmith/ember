"""
ember_qc/algorithms/factored/field.py
======================================
The VLSI-style coarse model for the attraction embedder (attraction.md roadmap
items 4-6, design settled 2026-07-18): a **typed tile grid** (per-tile
horizontal/vertical wire pools — VLSI gcell track capacities), **segment-smeared
demand** (RUDY-style: each variable's mass is spread along straight segments
toward its neighbours, charging every traversed tile — the mechanism the old
point-deposit field lacked, and the reason it was blind to §3.21's cut
constraint), and a **Poisson-solved repulsion field** sourced one-sidedly from
violation only:

    source = hinge_w * relu(rho - cap)^2  +  mu
    mu    <- max(0, mu + alpha_mu * (rho - cap))     once per router round

Zero force everywhere when nothing violates (slack fabric is silent — the
squared hinge is exactly zero on slack, no softplus tails); when violation
exists the solved potential gives every centroid a long-range gradient (Gauss:
an interior centroid of an overfull blob feels force proportional to the total
enclosed excess — the fix for the one-bin push's plateau problem). The mu term
is the Lagrange-multiplier memory (complementary slackness; same update family
as the §3.5 history term). Neumann boundary with mean-subtracted source
(ePlace's convention); the grid Laplacian is pseudo-inverted once per instance
(grids are <= ~32x32 — dense linear algebra is microseconds here).

Approximations, recorded: no self-force exclusion (a variable feels the total
field including its own deposit — small at these grid resolutions, VLSI makes
the same continuum approximation); anisotropy weights uniform per neighbour
(measured anisotropy is a deferred knob); Zephyr falls back to untyped
drawing-space bins for now (its qubits span unit cells; a faithful typed
tiling adds complexity without measured benefit yet — revisit if Zephyr
becomes a benchmark target).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np

Point = np.ndarray


def _tile_orient(target: nx.Graph) -> Optional[Dict[int, Tuple[int, int, int]]]:
    """Map each node to (tile_x, tile_y, orientation) using the hardware's own
    coordinate system, or None if the family isn't recognised.

    Orientation follows dnx conventions: u=0 couples along the vertical axis
    (consumes the vertical wire pool), u=1 along the horizontal axis.
    Pegasus nice-coordinates (t, y, x, u, k) interleave three Chimera-like
    subgrids; the t shifts are merged into one (x, y) tile since they share the
    same unit-cell footprint.
    """
    import dwave_networkx as dnx

    family = target.graph.get("family")
    labels = target.graph.get("labels", "int")
    g = target.graph
    try:
        if family == "chimera":
            conv = dnx.chimera_coordinates(g["rows"], g["columns"], g["tile"])
            out = {}
            for q in target.nodes():
                i, j, u, k = (q if labels == "coordinate"
                              else conv.linear_to_chimera(q))
                out[q] = (int(j), int(i), int(u), int(k))
            return out
        if family == "pegasus":
            conv = dnx.pegasus_coordinates(g["rows"])
            out = {}
            for q in target.nodes():
                if labels == "int":
                    t, y, x, u, k = conv.linear_to_nice(q)
                elif labels == "nice":
                    t, y, x, u, k = q
                else:  # 'coordinate'
                    t, y, x, u, k = conv.pegasus_to_nice(q)
                out[q] = (int(x), int(y), int(u), int(t) * 4 + int(k))
            return out
        if family == "zephyr":
            # Zephyr qubits span unit cells; use orientation from coordinates
            # and let the caller bin positions for tiles (return None tiles).
            return None
    except Exception:
        return None
    return None


def _interp(g: np.ndarray, W: int, H: int, x: float, y: float) -> float:
    """Bilinear sample of grid ``g`` (H, W) at a continuous tile point."""
    x = float(np.clip(x, 0.0, W - 1.0))
    y = float(np.clip(y, 0.0, H - 1.0))
    x0, y0 = int(x), int(y)
    x1, y1 = min(x0 + 1, W - 1), min(y0 + 1, H - 1)
    fx, fy = x - x0, y - y0
    return ((1 - fx) * (1 - fy) * g[y0, x0] + fx * (1 - fy) * g[y0, x1]
            + (1 - fx) * fy * g[y1, x0] + fx * fy * g[y1, x1])


class TileGrid:
    """Coarse capacitated grid over the target: per-tile typed wire pools.

    ``cap`` has shape (H, W, 2): pool 0 = vertical wires, pool 1 = horizontal,
    counted from working qubits only (dead qubits reduce the right pool by
    construction). Unrecognised targets fall back to drawing-coordinate bins
    with a single untyped pool duplicated across both slots (each halved, so
    the total is preserved and typed code paths degrade gracefully).

    Positions map between drawing space and continuous tile space through an
    affine fit (tiles are regular in hardware space and drawing layouts are
    near-affine images of it); forces computed in tile space return to drawing
    space through the inverse linear part.
    """

    def __init__(self, target: nx.Graph, pos: Dict[int, Point],
                 fallback_bins: int = 16):
        qubits = sorted(pos)
        coords = np.array([pos[q] for q in qubits], dtype=float)
        tio = _tile_orient(target)

        if tio is not None:
            txs = np.array([tio[q][0] for q in qubits])
            tys = np.array([tio[q][1] for q in qubits])
            self.W = int(txs.max()) + 1
            self.H = int(tys.max()) + 1
            tile_pts = np.stack([txs, tys], axis=1).astype(float)
            self.typed = True
            orient = np.array([tio[q][2] for q in qubits])
            self.sub = np.array([tio[q][3] for q in qubits])
            # wire lookup: (orientation, line, sub) -> {tile-along: qubit}
            self.wire_map = {}
            for q in qubits:
                tx, ty, u, sub = tio[q]
                key = (u, ty if u == 1 else tx, sub)
                self.wire_map.setdefault(key, {})[tx if u == 1 else ty] = q
        else:
            B = fallback_bins
            mins = coords.min(axis=0)
            span = np.maximum(coords.max(axis=0) - mins, 1e-9)
            tile_pts = (coords - mins) / span * (B - 1e-9)
            self.W = self.H = B
            self.typed = False
            orient = np.zeros(len(qubits), dtype=int)
            self.sub = np.zeros(len(qubits), dtype=int)
            self.wire_map = {}

        # Affine fit drawing -> tile space: [x_t, y_t] ~ M @ p + c
        A = np.hstack([coords, np.ones((len(qubits), 1))])
        sol, *_ = np.linalg.lstsq(A, tile_pts, rcond=None)
        self.M = sol[:2].T          # (2,2)
        self.c = sol[2]             # (2,)
        self.Minv = np.linalg.inv(self.M)

        self.qubits = qubits
        self.coords = coords
        self.orient = orient
        self.cap = np.zeros((self.H, self.W, 2))
        for k, q in enumerate(qubits):
            tx = int(np.clip(round(tile_pts[k][0]), 0, self.W - 1))
            ty = int(np.clip(round(tile_pts[k][1]), 0, self.H - 1))
            if self.typed:
                self.cap[ty, tx, orient[k]] += 1.0
            else:
                self.cap[ty, tx, 0] += 0.5
                self.cap[ty, tx, 1] += 0.5

    # ------------------------------------------------------------- mapping --

    def to_tile(self, p: Point) -> Point:
        return self.M @ np.asarray(p, dtype=float) + self.c

    def to_drawing_delta(self, d_tile: Point) -> Point:
        return self.Minv @ np.asarray(d_tile, dtype=float)

    # ------------------------------------------------------------ deposits --

    def splat(self, demand: np.ndarray, pt: Point, m_v: float,
              m_h: float) -> None:
        """Bilinear deposit of (vertical-pool, horizontal-pool) mass at a
        tile-space point."""
        x = float(np.clip(pt[0], 0.0, self.W - 1.0))
        y = float(np.clip(pt[1], 0.0, self.H - 1.0))
        x0, y0 = int(x), int(y)
        x1, y1 = min(x0 + 1, self.W - 1), min(y0 + 1, self.H - 1)
        fx, fy = x - x0, y - y0
        for (yy, xx, w) in ((y0, x0, (1 - fx) * (1 - fy)),
                            (y0, x1, fx * (1 - fy)),
                            (y1, x0, (1 - fx) * fy),
                            (y1, x1, fx * fy)):
            demand[yy, xx, 0] += m_v * w
            demand[yy, xx, 1] += m_h * w

    def deposit(self, cent: Dict[int, Point], lam: Dict[int, float],
                src_adj: Dict[int, List[int]], *, smear: bool = True,
                samples_per_tile: float = 2.0) -> np.ndarray:
        """Proposal demand map, shape (H, W, 2).

        With ``smear``: each variable v spreads lam[v] along the straight
        segments from its position toward each neighbour's position (uniform
        per-neighbour weights), sampled densely enough to charge every
        traversed tile; each sample splits between the horizontal pool
        (fraction |dx|/(|dx|+|dy|) of the segment direction) and the vertical
        pool. Isolated variables (and smear=False) deposit at their own tile,
        split evenly across pools.
        """
        demand = np.zeros((self.H, self.W, 2))

        def _splat(pt: Point, m_v: float, m_h: float) -> None:
            self.splat(demand, pt, m_v, m_h)

        tpos = {v: self.to_tile(p) for v, p in cent.items()}
        for v, p in tpos.items():
            mass = float(lam.get(v, 1.0))
            nbrs = src_adj.get(v, []) if smear else []
            nbrs = [u for u in nbrs if u in tpos]
            if not nbrs:
                _splat(p, mass * 0.5, mass * 0.5)
                continue
            share = mass / len(nbrs)
            for u in nbrs:
                d = tpos[u] - p
                length = float(np.hypot(d[0], d[1]))
                frac_h = abs(d[0]) / (abs(d[0]) + abs(d[1]) + 1e-12)
                k = max(2, int(math.ceil(length * samples_per_tile)) + 1)
                per = share / k
                for s in range(k):
                    pt = p + d * (s / (k - 1)) * 0.5  # v's half of the edge
                    _splat(pt, per * (1 - frac_h), per * frac_h)
        return demand


class PoissonField:
    """One-sided violation-sourced Poisson repulsion on a TileGrid.

    ``source = hinge_w * (relu(rho-cap)/cap_scale)^2 + mu`` summed over the two
    pools; ``solve`` returns the potential with Neumann boundaries (grid
    Laplacian pseudo-inverse, factorized once; mean-subtracted source — the
    compatibility condition, ePlace's DC-drop). ``force_at`` interpolates
    -grad(psi) at tile-space points, clipped to ``max_step`` tiles: the
    explicit trust-region bound on placement steps.
    """

    def __init__(self, grid: TileGrid, *, hinge_w: float = 1.0,
                 mu_alpha: float = 0.5, max_step: float = 1.0):
        self.grid = grid
        self.hinge_w = float(hinge_w)
        self.mu_alpha = float(mu_alpha)
        self.max_step = float(max_step)
        self.mu = np.zeros_like(grid.cap)
        self.cap_scale = max(float(grid.cap.sum(axis=2).mean()), 1e-9)
        self.last_demand: Optional[np.ndarray] = None

        H, W = grid.H, grid.W
        n = H * W
        L = np.zeros((n, n))
        for y in range(H):
            for x in range(W):
                i = y * W + x
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < H and 0 <= xx < W:
                        j = yy * W + xx
                        L[i, i] += 1.0
                        L[i, j] -= 1.0
        self._Lpinv = np.linalg.pinv(L)

    # -------------------------------------------------------------- source --

    def _violation(self, demand: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, demand - self.grid.cap) / self.cap_scale

    def potential(self, demand: np.ndarray) -> np.ndarray:
        v = self._violation(demand)
        source = (self.hinge_w * np.square(v) + self.mu).sum(axis=2)
        if not source.any():
            return np.zeros((self.grid.H, self.grid.W))
        rhs = (source - source.mean()).ravel()
        return (self._Lpinv @ rhs).reshape(self.grid.H, self.grid.W)

    def force_at(self, psi: np.ndarray, pts: Dict[int, Point],
                 scale: float) -> Dict[int, Point]:
        """-grad(psi) at each tile-space point, scaled and trust-region
        clipped. Returns tile-space displacements."""
        gy, gx = np.gradient(psi)
        W, H = self.grid.W, self.grid.H
        out: Dict[int, Point] = {}
        for v, p in pts.items():
            d = -scale * np.array([_interp(gx, W, H, p[0], p[1]),
                                   _interp(gy, W, H, p[0], p[1])])
            norm = float(np.hypot(d[0], d[1]))
            if norm > self.max_step:
                d *= self.max_step / norm
            out[v] = d
        return out

    # ------------------------------------------------------------ mu update --

    def update_mu(self, demand: np.ndarray) -> None:
        """Projected subgradient step, once per router round (fresh
        calibration): rises with violation, decays while slack, floors at 0."""
        if self.mu_alpha == 0.0:
            return
        step = (demand - self.grid.cap) / self.cap_scale
        self.mu = np.maximum(0.0, self.mu + self.mu_alpha * step)

    def diagnostics(self, demand: Optional[np.ndarray]) -> Dict[str, float]:
        out = {"mu_total": round(float(self.mu.sum()), 4)}
        if self.mu.sum() > 0 and demand is not None:
            slack = demand <= self.grid.cap
            out["mu_stale_frac"] = round(
                float(self.mu[slack].sum() / self.mu.sum()), 4)
        else:
            out["mu_stale_frac"] = 0.0
        if demand is not None:
            out["max_violation"] = round(
                float(np.maximum(0.0, demand - self.grid.cap).max()), 4)
        return out


# ==============================================================================
# EXTENT STATE (Option A, notes s3.26-3.28): variables as axis-aligned crosses
# ==============================================================================
#
# Each variable is (position, w, h): a horizontal bar of length w and a
# vertical bar of length h through its position, in tile units. An edge (u,v)
# is satisfied when one's h-bar crosses the other's v-bar; the *contact
# deficit* of the cheaper orientation is
#
#     d_hv = relu(|x_v-x_u| - w_u/2) + relu(|y_u-y_v| - h_v/2)
#
# (u's h-bar reaches v's column AND v's v-bar reaches u's row), and gradient
# descent on sum(d^2) generalizes Laplacian attraction: at zero extents d is
# the L1 distance, so sparse sources collapse to today's point model, while
# cliques grow bars and the busclique crossbar becomes an equilibrium of the
# same dynamics. Extents pay rent (extent_cost) so nothing grows without
# contact demand. lambda_v = 1 + w_v + h_v by construction.


def contact_step(pos: Dict[int, Point], ext: Dict[int, Point],
                 src_adj: Dict[int, List[int]], *, eta: float,
                 extent_eta: float, extent_cost: float,
                 max_step: float = 1.0):
    """One gradient step on the total squared contact deficit.

    Returns (new_pos, new_ext); per-variable forces are degree-averaged and
    trust-region clipped at ``max_step`` tiles. Deterministic (sorted
    iteration; hard-min orientation choice with d_hv on ties).
    """
    fpos = {v: np.zeros(2) for v in pos}
    fext = {v: np.zeros(2) for v in pos}
    deg = {v: max(1, len([u for u in src_adj.get(v, []) if u in pos]))
           for v in pos}

    def _accumulate(a, b):
        """Deficit + gradients for a's h-bar crossing b's v-bar."""
        dx = pos[b][0] - pos[a][0]
        dy = pos[a][1] - pos[b][1]
        a1 = abs(dx) - ext[a][0] / 2.0   # a's h-bar must reach b's column
        a2 = abs(dy) - ext[b][1] / 2.0   # b's v-bar must reach a's row
        d = max(0.0, a1) + max(0.0, a2)
        return d, a1, a2, dx, dy

    for v in sorted(pos):
        for u in src_adj.get(v, []):
            if u <= v or u not in pos:
                continue
            d_hv = _accumulate(u, v)   # u's h-bar x v's v-bar
            d_vh = _accumulate(v, u)   # v's h-bar x u's v-bar
            if d_hv[0] <= d_vh[0]:
                d, a1, a2, dx, dy = d_hv
                hbar, vbar = u, v
            else:
                d, a1, a2, dx, dy = d_vh
                hbar, vbar = v, u
            if d <= 0.0:
                continue
            if a1 > 0:  # pull columns together, grow the h-bar
                gx = 2.0 * d * (1.0 if dx > 0 else -1.0)
                fpos[vbar][0] -= gx
                fpos[hbar][0] += gx
                fext[hbar][0] += d
            if a2 > 0:  # pull rows together, grow the v-bar
                gy = 2.0 * d * (1.0 if dy > 0 else -1.0)
                fpos[hbar][1] -= gy
                fpos[vbar][1] += gy
                fext[vbar][1] += d

    new_pos, new_ext = {}, {}
    for v in pos:
        dp = eta * fpos[v] / deg[v]
        n = float(np.hypot(dp[0], dp[1]))
        if n > max_step:
            dp *= max_step / n
        new_pos[v] = pos[v] + dp
        de = extent_eta * fext[v] / deg[v] - extent_cost * ext[v]
        de = np.clip(de, -max_step, max_step)
        new_ext[v] = np.maximum(0.0, ext[v] + de)
    return new_pos, new_ext


def deposit_cross(grid: TileGrid, pos: Dict[int, Point],
                  ext: Dict[int, Point],
                  samples_per_tile: float = 2.0) -> np.ndarray:
    """Typed demand from cross shapes: the h-bar deposits w units into the
    horizontal pool along its row, the v-bar h units into the vertical pool
    along its column, plus one unit at the variable's own tile (split evenly).
    Total mass per variable = 1 + w + h."""
    demand = np.zeros((grid.H, grid.W, 2))
    for v in sorted(pos):
        p = pos[v]
        w, h = float(ext[v][0]), float(ext[v][1])
        grid.splat(demand, p, 0.5, 0.5)
        if w > 1e-9:
            k = max(2, int(math.ceil(w * samples_per_tile)) + 1)
            for s in range(k):
                x = p[0] - w / 2.0 + w * s / (k - 1)
                grid.splat(demand, np.array([x, p[1]]), 0.0, w / k)
        if h > 1e-9:
            k = max(2, int(math.ceil(h * samples_per_tile)) + 1)
            for s in range(k):
                y = p[1] - h / 2.0 + h * s / (k - 1)
                grid.splat(demand, np.array([p[0], y]), h / k, 0.0)
    return demand


def fit_extents(grid: TileGrid, emb: Dict[int, List[int]],
                pos_map: Dict[int, Point]) -> Dict[int, Point]:
    """Measured extents: per-axis bounding width of each realized chain's
    qubits in tile space (the upward map for the extent state)."""
    out: Dict[int, Point] = {}
    for v, chain in emb.items():
        pts = np.array([grid.to_tile(pos_map[q]) for q in chain])
        if len(pts) == 1:
            out[v] = np.zeros(2)
        else:
            out[v] = pts.max(axis=0) - pts.min(axis=0)
    return out


def _nearest_free(grid: TileGrid, claimed: set, pt_tile: Point,
                  want_orient: Optional[int]) -> Optional[int]:
    """Nearest unclaimed qubit to a tile-space point (orientation-matched on
    typed grids when ``want_orient`` is given), or None within the
    64-candidate search horizon."""
    p_draw = grid.Minv @ (np.asarray(pt_tile, dtype=float) - grid.c)
    d = np.einsum("ij,ij->i", grid.coords - p_draw, grid.coords - p_draw)
    if grid.typed and want_orient is not None:
        d = np.where(grid.orient == want_orient, d, np.inf)
    for i in np.argsort(d)[:64]:
        if d[i] == np.inf:
            break
        q = grid.qubits[int(i)]
        if q not in claimed:
            return q
    return None


def bar_seeds(grid: TileGrid, pos: Dict[int, Point],
              ext: Dict[int, Point]) -> Dict[int, List[int]]:
    """Multi-qubit seed chains tracing each variable's bars (~1 qubit/tile,
    orientation-matched where the grid is typed). Every variable gets at least
    its center qubit; qubits are claimed at most once (sorted-variable order).
    Chains may be disconnected -- the router repairs; this is the s3.10-risk
    switch (seed_mode="bars"), measured separately from the cross state.
    """
    claimed: set = set()
    out: Dict[int, List[int]] = {}

    for v in sorted(pos):
        p = pos[v]
        chain: List[int] = []
        q0 = _nearest_free(grid, claimed, p, None)
        if q0 is not None:
            claimed.add(q0)
            chain.append(q0)
        w, h = float(ext[v][0]), float(ext[v][1])
        for s in range(1, int(w) + 1):
            for x in (p[0] - w / 2.0 + (s - 0.5) * w / max(1, int(w)),):
                q = _nearest_free(grid, claimed, np.array([x, p[1]]),
                                  1 if grid.typed else None)
                if q is not None:
                    claimed.add(q)
                    chain.append(q)
        for s in range(1, int(h) + 1):
            y = p[1] - h / 2.0 + (s - 0.5) * h / max(1, int(h))
            q = _nearest_free(grid, claimed, np.array([p[0], y]),
                              0 if grid.typed else None)
            if q is not None:
                claimed.add(q)
                chain.append(q)
        if chain:
            out[v] = chain
    return out


def bar_force(grid: TileGrid, psi: np.ndarray, pos: Dict[int, Point],
              ext: Dict[int, Point], *, scale: float, ext_w: float,
              max_step: float = 1.0):
    """v2 field-bar coupling, from E = density * integral of psi over the bar
    (v1 sampled the field only at the center -- source distributed, response
    point-sampled; Max's far-tip scenario produced no corrective signal).

    Translation force = -grad(psi) averaged over ~1-per-tile samples along
    both bars (+ center). Extent force per bar = -ext_w * mean(psi at the two
    tips): growing a bar adds charge at its tips, so bars refuse to grow into
    -- and retract out of -- high-potential regions. Both trust-region
    clipped at ``max_step``. Returns (dpos, dext_field) in tile units.
    """
    gy, gx = np.gradient(psi)
    W, H = grid.W, grid.H
    dpos: Dict[int, Point] = {}
    dext: Dict[int, Point] = {}
    for v in sorted(pos):
        p = pos[v]
        w, h = float(ext[v][0]), float(ext[v][1])
        samples = [p]
        for k in range(1, int(w) + 1):
            for sx in (p[0] - w / 2.0 + (k - 0.5) * w / max(1, int(w)),):
                samples.append(np.array([sx, p[1]]))
        for k in range(1, int(h) + 1):
            sy = p[1] - h / 2.0 + (k - 0.5) * h / max(1, int(h))
            samples.append(np.array([p[0], sy]))
        g = np.mean([[_interp(gx, W, H, q[0], q[1]),
                      _interp(gy, W, H, q[0], q[1])] for q in samples], axis=0)
        d = -scale * g
        n = float(np.hypot(d[0], d[1]))
        if n > max_step:
            d *= max_step / n
        dpos[v] = d

        tip_w = 0.5 * (_interp(psi, W, H, p[0] - w / 2.0, p[1])
                       + _interp(psi, W, H, p[0] + w / 2.0, p[1]))
        tip_h = 0.5 * (_interp(psi, W, H, p[0], p[1] - h / 2.0)
                       + _interp(psi, W, H, p[0], p[1] + h / 2.0))
        de = np.clip(-ext_w * np.array([tip_w, tip_h]), -max_step, max_step)
        dext[v] = de
    return dpos, dext


def assign_rows_cols(pos: Dict[int, Point], ext: Dict[int, Point],
                     grid: TileGrid, *, threshold: float = 2.0):
    """The discrete symmetry break (notes s3.28: gradient flow cannot decide
    who owns which row/column -- stacked bars are a zero-gradient
    configuration). Variables with total extent above ``threshold`` are
    rank-ordered and hard-snapped to distinct integer rows (h-bars, by y) and
    columns (v-bars, by x), capacity-many per row/column; sorting is
    order-preserving = the minimal-total-displacement 1D transport plan. Bar
    LENGTHS are untouched; sub-threshold variables (the sparse regime) are
    untouched; reassignment is per-round, not a one-shot cage. Returns new
    positions dict (participants moved, others identical objects).
    """
    parts = [v for v in sorted(pos) if ext[v][0] + ext[v][1] > threshold]
    if not parts:
        return dict(pos), 0
    new_pos = dict(pos)

    def _assign(axis: int, pool: int, size: int):
        # per-row (or column) bar budget from that line's mean pool capacity
        # (axis==1: rows (y); line capacity = mean over x of h-pool per row)
        line_cap = grid.cap[:, :, pool].mean(axis=1 if axis == 1 else 0)
        order = sorted(parts, key=lambda v: (float(pos[v][axis]), v))
        med = float(np.median([pos[v][axis] for v in parts]))
        n_lines = size
        per_line = [max(1, int(line_cap[i])) for i in range(n_lines)]
        # slots: lines ordered by distance from the median line, then filled
        lines = sorted(range(n_lines), key=lambda i: (abs(i - med), i))
        slots: List[int] = []
        for ln in lines:
            slots.extend([ln] * per_line[ln])
            if len(slots) >= len(order):
                break
        slots = sorted(slots[:len(order)] if len(slots) >= len(order)
                       else slots + [lines[-1]] * (len(order) - len(slots)))
        for v, ln in zip(order, slots):
            p = np.array(new_pos[v], dtype=float)
            p[axis] = float(ln)
            new_pos[v] = p

    _assign(axis=1, pool=1, size=grid.H)   # h-bars -> rows (y), h-pool
    _assign(axis=0, pool=0, size=grid.W)   # v-bars -> columns (x), v-pool
    return new_pos, len(parts)


def _color_claim_bars(grid: TileGrid, claimed: set,
                      chains: Dict[int, List[int]], orientation: int,
                      bars: List[Tuple[int, float, float, int]]) -> None:
    """Color explicit interval bars onto physical wires and claim contiguous
    runs. ``bars``: (line, start, end, v) tuples of one orientation. Bars
    sharing a line with disjoint intervals may share a wire; overlapping
    ones may not -- interval graph coloring, solved exactly by the greedy
    left-endpoint sweep. Oversubscribed bars are skipped (left point-seeded
    by the caller's guarantee pass)."""
    by_line: Dict[int, list] = {}
    for line, a, b, v in bars:
        by_line.setdefault(line, []).append((a, b, v))
    for line, items in sorted(by_line.items()):
        items.sort()
        used_colors: Dict[int, float] = {}
        subs = sorted({int(s) for (u, ln, s) in grid.wire_map
                       if u == orientation and ln == line})
        for a, b, v in items:
            # free colors whose interval ended
            for c in [c for c, e in used_colors.items() if e <= a]:
                del used_colors[c]
            color = next((c for c in subs if c not in used_colors), None)
            if color is None:
                continue  # line oversubscribed; leave this bar point-seeded
            used_colors[color] = b
            run = grid.wire_map.get((orientation, line, color), {})
            for t in range(int(math.floor(a)), int(math.ceil(b)) + 1):
                q = run.get(t)
                if q is not None and q not in claimed:
                    claimed.add(q)
                    chains[v].append(q)


def _ensure_seeds(grid: TileGrid, claimed: set,
                  chains: Dict[int, List[int]],
                  pos: Dict[int, Point]) -> None:
    """Guarantee every variable at least one (nearest unclaimed) qubit."""
    for v in sorted(pos):
        if not chains[v]:
            q = _nearest_free(grid, claimed, pos[v], None)
            if q is not None:
                claimed.add(q)
                chains[v].append(q)


def wire_seeds(grid: TileGrid, pos: Dict[int, Point],
               ext: Dict[int, Point]) -> Dict[int, List[int]]:
    """Wire-coherent seed chains (the sub-tile last mile, notes s3.30): bars
    sharing an integer row with disjoint x-intervals may share a physical
    wire; overlapping ones may not -- interval graph coloring, solved exactly
    by the greedy left-endpoint sweep. Each bar then claims the CONTIGUOUS
    run of its colored wire's qubits across its span, so seed chains are
    real coupled paths instead of stitched-together nearest qubits (which
    inflated routed ACL by ~30%). Falls back to nearest-qubit sampling on
    untyped grids. Center qubit is always included. Bars here are CENTERED
    (cross state: pos ± ext/2); the span state's one-sided intervals go
    through :func:`wire_seeds_iv`.
    """
    if not grid.typed:
        return bar_seeds(grid, pos, ext)

    claimed: set = set()
    chains: Dict[int, List[int]] = {v: [] for v in pos}

    for orientation in (1, 0):  # h-bars along rows, then v-bars along columns
        bars = []
        for v in sorted(pos):
            length = float(ext[v][0] if orientation == 1 else ext[v][1])
            if length < 1.0:
                continue
            line = int(round(float(pos[v][1] if orientation == 1
                                   else pos[v][0])))
            a = float(pos[v][0] if orientation == 1 else pos[v][1]) - length / 2
            bars.append((line, a, a + length, v))
        _color_claim_bars(grid, claimed, chains, orientation, bars)

    _ensure_seeds(grid, claimed, chains, pos)
    return {v: c for v, c in chains.items() if c}


# ==============================================================================
# SPAN STATE (notes s3.31): derived extents -- position is the only state
# ==============================================================================
#
# The s3.28-3.30 lesson: extents were never legitimate state. Any embedding
# of v must reach its neighbours, so v's bars owe exactly the span of its
# neighbours' coordinates -- a deterministic READOUT of positions, not a
# quantity to evolve under growth/rent/retraction forces. State shrinks to
# one (x, y) per variable; the implied cross is
#
#     h-bar: row y_v, x-interval spanning {x_u : u in N[v] + v}
#     v-bar: col x_v, y-interval spanning {y_u : u in N[v] + v}
#
# Contact for edge (u, v) is at (x_u, y_v), inside both bars BY CONSTRUCTION.
# Never recenter a bar: that guarantee, wire_seeds' line = round(y_v), and
# the energy identity below all depend on the bar sitting on its owner's
# row/column. The energy
#
#     E = sum_v [xspan(N[v]) + yspan(N[v])]
#
# is exactly the total bar length of the implied embedding (qubit mass minus
# n) -- VLSI half-perimeter wirelength with one net per closed neighbourhood.
# Chain length is the objective itself, not a simulated quantity. Collapse is
# infeasible in-model (stacked variables still deposit 1 + w + h each; the
# pool overfills), so the s3.30 collapse pathology cannot arise; the
# deg(v)/kappa contact-capacity floor survives only as a readout-side clamp.

BarIntervals = Dict[int, Tuple[np.ndarray, np.ndarray]]


def derive_bars(pos: Dict[int, Point], src_adj: Dict[int, List[int]], *,
                kappa: float = 13.0, floor: bool = True,
                bounds: Optional[Tuple[int, int]] = None) -> BarIntervals:
    """Implied bars: v's h-bar is the x-interval of N[v] + v at row y_v, its
    v-bar the y-interval at column x_v. Pure function of positions.

    ``floor``: contact capacity (s3.30) -- a chain of L qubits hosts at most
    ~kappa*L contacts, so total bar length owes w + h >= deg(v)/kappa - 1;
    any deficit is split evenly per axis and widened symmetrically about the
    interval. ``bounds=(W, H)`` clips intervals into the grid.
    """
    out: BarIntervals = {}
    for v in sorted(pos):
        nbrs = [u for u in src_adj.get(v, []) if u in pos]
        xs = [float(pos[u][0]) for u in nbrs] + [float(pos[v][0])]
        ys = [float(pos[u][1]) for u in nbrs] + [float(pos[v][1])]
        h_iv = np.array([min(xs), max(xs)])
        v_iv = np.array([min(ys), max(ys)])
        if floor:
            need = len(nbrs) / kappa - 1.0
            deficit = need - float((h_iv[1] - h_iv[0]) + (v_iv[1] - v_iv[0]))
            if deficit > 0:
                h_iv = h_iv + np.array([-deficit / 4.0, deficit / 4.0])
                v_iv = v_iv + np.array([-deficit / 4.0, deficit / 4.0])
        if bounds is not None:
            h_iv = np.clip(h_iv, 0.0, bounds[0] - 1.0)
            v_iv = np.clip(v_iv, 0.0, bounds[1] - 1.0)
        out[v] = (h_iv, v_iv)
    return out


def span_energy(pos: Dict[int, Point],
                src_adj: Dict[int, List[int]]) -> float:
    """E = sum_v [xspan(N[v] + v) + yspan(N[v] + v)]: the total bar length of
    the implied cross embedding (un-floored; implied qubit mass = n + E)."""
    e = 0.0
    for v in pos:
        nbrs = [u for u in src_adj.get(v, []) if u in pos]
        xs = [float(pos[u][0]) for u in nbrs] + [float(pos[v][0])]
        ys = [float(pos[u][1]) for u in nbrs] + [float(pos[v][1])]
        e += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return e


def span_step(pos: Dict[int, Point], src_adj: Dict[int, List[int]], *,
              eta: float, max_step: float = 1.0) -> Dict[int, Point]:
    """One subgradient step on :func:`span_energy`: per net (closed
    neighbourhood), per axis, a unit force pulls the two extreme members
    inward -- the HPWL subgradient; interior members feel nothing. Ties are
    broken by (coordinate, vertex id), so the step is deterministic.
    Per-vertex force is normalized by incident-net count (deg + 1), matching
    relax()'s eta scale; displacements trust-region clipped at ``max_step``
    tiles."""
    f = {v: np.zeros(2) for v in pos}
    nets = {v: 1 + len([u for u in src_adj.get(v, []) if u in pos])
            for v in pos}
    for v in sorted(pos):
        members = [u for u in src_adj.get(v, []) if u in pos] + [v]
        if len(members) < 2:
            continue
        for axis in (0, 1):
            hi = max(members, key=lambda u: (float(pos[u][axis]), u))
            lo = min(members, key=lambda u: (float(pos[u][axis]), u))
            if float(pos[hi][axis]) - float(pos[lo][axis]) <= 1e-12:
                continue
            f[hi][axis] -= 1.0
            f[lo][axis] += 1.0
    out: Dict[int, Point] = {}
    for v in pos:
        dp = eta * f[v] / nets[v]
        n = float(np.hypot(dp[0], dp[1]))
        if n > max_step:
            dp *= max_step / n
        out[v] = pos[v] + dp
    return out


def bar_widths(bars: BarIntervals) -> Dict[int, Point]:
    """(w, h) view of interval bars -- the ext-shaped shim that lets
    :func:`assign_rows_cols` consume derived bars unchanged."""
    return {v: np.array([float(h_iv[1] - h_iv[0]),
                         float(v_iv[1] - v_iv[0])])
            for v, (h_iv, v_iv) in bars.items()}


def deposit_bars(grid: TileGrid, pos: Dict[int, Point], bars: BarIntervals,
                 samples_per_tile: float = 2.0) -> np.ndarray:
    """Typed demand from implied bars (interval sibling of
    :func:`deposit_cross`): the h-interval deposits its length into the
    horizontal pool along row y_v, the v-interval into the vertical pool
    along column x_v, plus one unit at the variable's own tile (split
    evenly). Total mass per variable = 1 + w + h -- exact traversal charging
    of the shape that will actually be seeded; no RUDY approximation."""
    demand = np.zeros((grid.H, grid.W, 2))
    for v in sorted(pos):
        p = pos[v]
        h_iv, v_iv = bars[v]
        w = float(h_iv[1] - h_iv[0])
        h = float(v_iv[1] - v_iv[0])
        grid.splat(demand, p, 0.5, 0.5)
        if w > 1e-9:
            k = max(2, int(math.ceil(w * samples_per_tile)) + 1)
            for s in range(k):
                x = float(h_iv[0]) + w * s / (k - 1)
                grid.splat(demand, np.array([x, p[1]]), 0.0, w / k)
        if h > 1e-9:
            k = max(2, int(math.ceil(h * samples_per_tile)) + 1)
            for s in range(k):
                y = float(v_iv[0]) + h * s / (k - 1)
                grid.splat(demand, np.array([p[0], y]), h / k, 0.0)
    return demand


def bar_force_iv(grid: TileGrid, psi: np.ndarray, pos: Dict[int, Point],
                 bars: BarIntervals, *, scale: float,
                 max_step: float = 1.0) -> Dict[int, Point]:
    """Translation-only field force on implied bars: -grad(psi) averaged over
    ~1-per-tile samples along both intervals plus the center point. No tip
    or extent terms -- extents are not state here; the field steers
    positions and the bars re-derive. Trust-region clipped at ``max_step``
    tiles. Returns tile-space displacements."""
    gy, gx = np.gradient(psi)
    W, H = grid.W, grid.H
    out: Dict[int, Point] = {}
    for v in sorted(pos):
        p = pos[v]
        h_iv, v_iv = bars[v]
        w = float(h_iv[1] - h_iv[0])
        h = float(v_iv[1] - v_iv[0])
        samples = [p]
        for k in range(1, int(w) + 1):
            sx = float(h_iv[0]) + (k - 0.5) * w / max(1, int(w))
            samples.append(np.array([sx, p[1]]))
        for k in range(1, int(h) + 1):
            sy = float(v_iv[0]) + (k - 0.5) * h / max(1, int(h))
            samples.append(np.array([p[0], sy]))
        g = np.mean([[_interp(gx, W, H, q[0], q[1]),
                      _interp(gy, W, H, q[0], q[1])] for q in samples],
                    axis=0)
        d = -scale * g
        n = float(np.hypot(d[0], d[1]))
        if n > max_step:
            d *= max_step / n
        out[v] = d
    return out


def wire_seeds_iv(grid: TileGrid, pos: Dict[int, Point],
                  bars: BarIntervals) -> Dict[int, List[int]]:
    """Interval-native wire-coherent seeds (span-state sibling of
    :func:`wire_seeds`). Derived bars are one-sided in general, so claims
    run over the ACTUAL interval, anchored at the owner's row/column --
    never a centered approximation. Untyped grids fall back to
    nearest-qubit sampling along the intervals (~1 per tile)."""
    claimed: set = set()
    chains: Dict[int, List[int]] = {v: [] for v in pos}

    if not grid.typed:
        for v in sorted(pos):
            p = pos[v]
            q0 = _nearest_free(grid, claimed, p, None)
            if q0 is not None:
                claimed.add(q0)
                chains[v].append(q0)
            h_iv, v_iv = bars[v]
            w = float(h_iv[1] - h_iv[0])
            h = float(v_iv[1] - v_iv[0])
            for k in range(1, int(w) + 1):
                sx = float(h_iv[0]) + (k - 0.5) * w / max(1, int(w))
                q = _nearest_free(grid, claimed, np.array([sx, p[1]]), None)
                if q is not None:
                    claimed.add(q)
                    chains[v].append(q)
            for k in range(1, int(h) + 1):
                sy = float(v_iv[0]) + (k - 0.5) * h / max(1, int(h))
                q = _nearest_free(grid, claimed, np.array([p[0], sy]), None)
                if q is not None:
                    claimed.add(q)
                    chains[v].append(q)
        return {v: c for v, c in chains.items() if c}

    for orientation in (1, 0):  # h-bars along rows, then v-bars along columns
        tuples = []
        for v in sorted(pos):
            h_iv, v_iv = bars[v]
            iv = h_iv if orientation == 1 else v_iv
            length = float(iv[1] - iv[0])
            if length < 1.0:
                continue
            line = int(round(float(pos[v][1] if orientation == 1
                                   else pos[v][0])))
            tuples.append((line, float(iv[0]), float(iv[1]), v))
        _color_claim_bars(grid, claimed, chains, orientation, tuples)

    _ensure_seeds(grid, claimed, chains, pos)
    return {v: c for v, c in chains.items() if c}
