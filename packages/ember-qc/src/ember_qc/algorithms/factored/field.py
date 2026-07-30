"""
ember_qc/algorithms/factored/field.py
======================================
The coarse layer of the attraction embedder, post-consolidation (2026-07-29,
archive commit 612ced3e holds every superseded variant): the **typed tile
grid** over the target, the **stair (single-coverage) readout** of positions,
the **alternating 1-D arrangement** that packs capacity-forced variables into
integer rows/columns, and **wire-coherent seed derivation**.

The model (notes s3.31/s3.34): position is the ONLY state — one (x, y) per
variable in continuous tile space. Everything extended about a variable is a
deterministic READOUT of positions: any embedding of v must reach its
neighbours, so v owes arms spanning its assigned contacts' coordinates. Under
the DIAGONAL RULE (busclique's staircase generalized), edge (u, v) is covered
at u's h-arm x v's v-arm iff (y_u, u) < (y_v, v) — one designated crossing
per edge, so total arm length is the single-coverage chain length itself
(VLSI HPWL with directional nets), not a simulated proxy. Dynamics =
subgradient descent on that energy; capacity = exact per-line interval
overlap depth inside the arrangement; order search (insertion sweeps) covers
the permutation directions gradients and order-preserving packing cannot
reach.

Load-bearing invariants (correctness, not tuning):
  * bars are never recentered — the contact-at-(x_u, y_v) guarantee, wire
    seeding's line = round(y_v), and the energy identity assume each bar
    sits on its owner's row/column;
  * every packing is order-preserving — the stair rule is keyed on the
    coordinate ORDER, so a half-step must only permute values;
  * every discrete projection is gated on the true stair energy (except the
    iteration-0 feasibility projection, unconditional by design);
  * seed derivation is ALWAYS best-effort — oversubscribed bars and
    unsatisfied crossings are left for the router, no error paths;
  * participation is by derived ARM LENGTH, per axis (interval >= 1 tile:
    the variable owes a wire run), so the dense machinery is structurally
    inert wherever chains are sub-tile; kappa survives only in the floor.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

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
            # Zephyr qubits span unit cells; a faithful typed tiling is the
            # queued adapter (its junctions are COMPLETE — the Pegasus 56%
            # coupler pathology is absent there, notes s3.37). Untyped
            # fallback until then.
            return None
    except Exception:
        return None
    return None


class TileGrid:
    """Coarse capacitated grid over the target: per-tile typed wire pools.

    ``cap`` has shape (H, W, 2): pool 0 = vertical wires, pool 1 = horizontal,
    counted from working qubits only (dead qubits reduce the right pool by
    construction). Unrecognised targets fall back to drawing-coordinate bins
    with a single untyped pool duplicated across both slots (each halved, so
    the total is preserved and typed code paths degrade gracefully).

    Positions map between drawing space and continuous tile space through an
    affine fit (tiles are regular in hardware space and drawing layouts are
    near-affine images of it).
    """

    def __init__(self, target: nx.Graph, pos: Dict[int, Point],
                 fallback_bins: int = 16):
        self.graph = target  # reference only (coupler lookups)
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


# ==============================================================================
# STAIR READOUT (notes s3.34): per-edge single coverage
# ==============================================================================
#
# Busclique's construction (verified in source, clique_cache.hpp
# inflate_first_ell) is the staircase: arms (i+1, width-2-i), row+column ~
# constant, each pair meeting exactly once above the diagonal. The
# generalization is the DIAGONAL RULE, a pure readout of positions: edge
# (u, v) is covered at u's h-arm x v's v-arm iff (y_u, u) < (y_v, v) — the
# y-lower variable reaches across columns, the y-upper reaches up rows. Arms
# span only their ASSIGNED contacts. The rule is keyed on y-ORDER, so it is
# invariant under the order-preserving packing in alternate_arrange.
# Cost accepted (measured, s3.34): single coverage forfeits the redundancy
# that made double-covered seeds auto-legal; on Pegasus (~56% in-tile
# coupler density) the router repairs the designated crossings that the
# blind coloring misses — the repair is short-range and cheap next to the
# 2x seed-mass saving.

BarIntervals = Dict[int, Tuple[np.ndarray, np.ndarray]]


def _stair_contacts(pos: Dict[int, Point],
                    src_adj: Dict[int, List[int]]):
    """Assigned contacts per variable under the diagonal rule. Returns
    {v: (h_us, v_us)}: neighbour ids whose COLUMNS v's h-arm must reach,
    and neighbour ids whose ROWS its v-arm must reach."""
    out = {}
    for v in pos:
        h_us: List[int] = []
        v_us: List[int] = []
        yv = float(pos[v][1])
        for u in src_adj.get(v, []):
            if u not in pos or u == v:
                continue
            if (yv, v) < (float(pos[u][1]), u):
                h_us.append(u)
            else:
                v_us.append(u)
        out[v] = (h_us, v_us)
    return out


def derive_bars_stair(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
                      *, kappa: float = 13.0, floor: bool = True,
                      bounds: Optional[Tuple[int, int]] = None
                      ) -> BarIntervals:
    """Single-coverage bars: v's h-arm spans the columns of its h-assigned
    contacts (+ its own column); v-arm spans the rows of its v-assigned
    contacts (+ its own row). Pure function of positions; never recentered.

    ``floor``: contact capacity (s3.30) — a chain of L qubits hosts at most
    ~kappa*L contacts, so total arm length owes w + h >= deg(v)/kappa - 1;
    any deficit is split evenly per axis and widened symmetrically.
    ``bounds=(W, H)`` clips intervals into the grid.
    """
    contacts = _stair_contacts(pos, src_adj)
    out: BarIntervals = {}
    for v in sorted(pos):
        h_us, v_us = contacts[v]
        xs = [float(pos[u][0]) for u in h_us] + [float(pos[v][0])]
        ys = [float(pos[u][1]) for u in v_us] + [float(pos[v][1])]
        h_iv = np.array([min(xs), max(xs)])
        v_iv = np.array([min(ys), max(ys)])
        if floor:
            deg = len([u for u in src_adj.get(v, []) if u in pos])
            need = deg / kappa - 1.0
            deficit = need - float((h_iv[1] - h_iv[0]) + (v_iv[1] - v_iv[0]))
            if deficit > 0:
                h_iv = h_iv + np.array([-deficit / 4.0, deficit / 4.0])
                v_iv = v_iv + np.array([-deficit / 4.0, deficit / 4.0])
        if bounds is not None:
            h_iv = np.clip(h_iv, 0.0, bounds[0] - 1.0)
            v_iv = np.clip(v_iv, 0.0, bounds[1] - 1.0)
        out[v] = (h_iv, v_iv)
    return out


def stair_energy(pos: Dict[int, Point],
                 src_adj: Dict[int, List[int]]) -> float:
    """Total arm length under the diagonal rule (un-floored) — the
    single-coverage chain-length objective."""
    contacts = _stair_contacts(pos, src_adj)
    e = 0.0
    for v in pos:
        h_us, v_us = contacts[v]
        xs = [float(pos[u][0]) for u in h_us] + [float(pos[v][0])]
        ys = [float(pos[u][1]) for u in v_us] + [float(pos[v][1])]
        e += (max(xs) - min(xs)) + (max(ys) - min(ys))
    return e


def stair_step(pos: Dict[int, Point], src_adj: Dict[int, List[int]], *,
               eta: float, max_step: float = 1.0) -> Dict[int, Point]:
    """One subgradient step on :func:`stair_energy`. Each variable owns two
    directional nets — {v + h-assigned contacts} along x, {v + v-assigned
    contacts} along y — and the extremes of each net are pulled inward
    (HPWL subgradient, ties by (coord, id)). Net membership changes when
    the y-order changes; nets are recomputed every call, which is standard
    subgradient semantics. Normalized by incident-net count (deg + 2);
    displacements trust-region clipped at ``max_step`` tiles."""
    contacts = _stair_contacts(pos, src_adj)
    f = {v: np.zeros(2) for v in pos}
    nets = {v: 2 + len([u for u in src_adj.get(v, []) if u in pos])
            for v in pos}
    for v in sorted(pos):
        h_us, v_us = contacts[v]
        for axis, members in ((0, h_us + [v]), (1, v_us + [v])):
            if len(members) < 2:
                continue
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
    """(w, h) view of interval bars — diagnostics helper."""
    return {v: np.array([float(h_iv[1] - h_iv[0]),
                         float(v_iv[1] - v_iv[0])])
            for v, (h_iv, v_iv) in bars.items()}


# ==============================================================================
# SEED DERIVATION: bars -> wire-coherent qubit chains
# ==============================================================================


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


def _couples(grid: TileGrid, r: int, s_h: int, c: int, s_v: int) -> bool:
    """True iff the h-wire (row r, sub s_h) and the v-wire (col c, sub s_v)
    share a physical coupler at their crossing tile (c, r). Missing qubits
    (dead, or wire absent at that tile) -> False. On Chimera every in-tile
    pair couples; on Pegasus only ~56% do (s3.33) — which wires you pick
    decides whether a crossing is real."""
    qh = grid.wire_map.get((1, r, s_h), {}).get(c)
    qv = grid.wire_map.get((0, c, s_v), {}).get(r)
    return qh is not None and qv is not None and grid.graph.has_edge(qh, qv)


def _color_claim_bars(grid: TileGrid, claimed: set,
                      chains: Dict[int, List[int]], orientation: int,
                      bars: List[Tuple[int, float, float, int]]) -> None:
    """Color explicit interval bars onto physical wires and claim runs.
    ``bars``: (line, start, end, v) tuples of one orientation. Bars sharing
    a line with disjoint intervals may share a wire; overlapping ones may
    not — interval graph coloring, solved exactly by the greedy
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
            free = [c for c in subs if c not in used_colors]
            if not free:
                continue  # line oversubscribed; leave this bar point-seeded
            color = free[0]
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


def wire_seeds_iv(grid: TileGrid, pos: Dict[int, Point],
                  bars: BarIntervals) -> Dict[int, List[int]]:
    """Wire-coherent seed chains (the sub-tile last mile, notes s3.30): each
    bar claims the CONTIGUOUS run of its greedily-colored wire's qubits
    across its interval, so seed chains are real coupled paths instead of
    stitched-together nearest qubits (which inflated routed ACL by ~30%).
    Derived bars are one-sided in general, so claims run over the ACTUAL
    interval, anchored at the owner's row/column — never a centered
    approximation. Untyped grids fall back to nearest-qubit sampling along
    the intervals (~1 per tile). Every variable gets at least one qubit."""
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

    def _tuples(orientation: int):
        out = []
        for v in sorted(pos):
            h_iv, v_iv = bars[v]
            iv = h_iv if orientation == 1 else v_iv
            length = float(iv[1] - iv[0])
            if length < 1.0:
                continue
            line = int(round(float(pos[v][1] if orientation == 1
                                   else pos[v][0])))
            out.append((line, float(iv[0]), float(iv[1]), v))
        return out

    _color_claim_bars(grid, claimed, chains, 1, _tuples(1))
    _color_claim_bars(grid, claimed, chains, 0, _tuples(0))
    _ensure_seeds(grid, claimed, chains, pos)
    return {v: c for v, c in chains.items() if c}


def _line_tracks(items: List[Tuple[float, float, int]]
                 ) -> List[List[Tuple[float, float, int]]]:
    """Group one line's arm intervals (sorted (a, b, v) tuples) into TRACKS:
    the color classes of the exact greedy interval coloring. Disjoint arms
    share a track; #tracks = overlap depth (chi = omega), so tracks -> subs
    is a feasible one-to-one matching whenever the packer's depth test
    held. The matching step then chooses WHICH sub each track gets; it can
    never break feasibility."""
    tracks: List[List[Tuple[float, float, int]]] = []
    ends: List[float] = []
    for a, b, v in sorted(items):
        placed = False
        for i, e in enumerate(ends):
            if e <= a:
                tracks[i].append((a, b, v))
                ends[i] = b
                placed = True
                break
        if not placed:
            tracks.append([(a, b, v)])
            ends.append(b)
    return tracks


def wire_seeds_matched(grid: TileGrid, pos: Dict[int, Point],
                       bars: BarIntervals,
                       src_adj: Dict[int, List[int]], *,
                       sweeps: int = 4,
                       junction_w: float = 2.0):
    """Coupler-exact wire seeds (notes s3.37): per-line maximum-weight
    matching of tracks to physical subs, alternating columns<->rows —
    coordinate ascent on the number of DESIGNATED crossings that land on
    real couplers (the diagonal rule's contacts). Each half-step is exact
    (scipy linear_sum_assignment, <=12x12 per line); the total satisfied
    count is monotone across line re-solves and the loop stops when it
    plateaus.

    SELF-JUNCTIONS (a variable's own h-arm x v-arm corner) are in the
    objective at ``junction_w`` > 1: the corner is what makes its chain
    CONNECTED — omitting it let the matcher trade corners for contacts
    (K100 connectivity 100->44, s3.37).

    ALWAYS best-effort: whatever crossings remain unsatisfied are simply
    left for the router to repair, exactly as with the greedy coloring —
    no error paths, no legality requirement. ``sweeps=0`` evaluates the
    greedy initial assignment (the measurement baseline). Returns
    (chains, satisfied, total) where satisfied/total is the honest
    per-designated-crossing metric (crossings between two colored arms).
    Untyped grids fall back to :func:`wire_seeds_iv`."""
    if not grid.typed:
        chains = wire_seeds_iv(grid, pos, bars)
        return chains, 0, 0
    from scipy.optimize import linear_sum_assignment

    # per-orientation line structure: line -> tracks of (a, b, v)
    tracks: Dict[int, Dict[int, list]] = {1: {}, 0: {}}
    arm_of: Dict[int, dict] = {1: {}, 0: {}}   # v -> (line, track_idx)
    subs_of: Dict[Tuple[int, int], List[int]] = {}
    for o in (1, 0):
        by_line: Dict[int, list] = {}
        for v in sorted(pos):
            h_iv, v_iv = bars[v]
            iv = h_iv if o == 1 else v_iv
            if float(iv[1] - iv[0]) < 1.0:
                continue
            line = int(round(float(pos[v][1] if o == 1 else pos[v][0])))
            by_line.setdefault(line, []).append(
                (float(iv[0]), float(iv[1]), v))
        for line, items in sorted(by_line.items()):
            tr = _line_tracks(items)
            tracks[o][line] = tr
            subs_of[(o, line)] = sorted(
                {int(s) for (u, ln, s) in grid.wire_map
                 if u == o and ln == line})
            for ti, t in enumerate(tr):
                for (_a, _b, v) in t:
                    arm_of[o][v] = (line, ti)

    # designated crossings between two colored arms:
    # edge covered at v's h-arm x u's v-arm -> tile (col_u, row_v)
    contacts = _stair_contacts(pos, src_adj)
    crossings = []  # (v_h, u_v, row, col, weight, is_junction)
    for v in sorted(pos):
        if v not in arm_of[1]:
            continue
        row = arm_of[1][v][0]
        for u in contacts[v][0]:          # u assigned to v's h-arm
            if u in arm_of[0]:
                crossings.append((v, u, row, arm_of[0][u][0], 1.0, False))
    for v in sorted(pos):
        if v in arm_of[1] and v in arm_of[0]:
            crossings.append((v, v, arm_of[1][v][0], arm_of[0][v][0],
                              float(junction_w), True))
    total = sum(1 for c in crossings if not c[5])

    # assignment state: (o, line, track_idx) -> sub; greedy init
    assign: Dict[Tuple[int, int, int], Optional[int]] = {}
    for o in (1, 0):
        for line, tr in tracks[o].items():
            S = subs_of[(o, line)]
            for ti in range(len(tr)):
                assign[(o, line, ti)] = S[ti] if ti < len(S) else None

    # crossings indexed by each side's (line, track)
    by_h: Dict[Tuple[int, int], list] = {}
    by_v: Dict[Tuple[int, int], list] = {}
    for cr in crossings:
        vh, uv, row, col = cr[0], cr[1], cr[2], cr[3]
        by_h.setdefault((row, arm_of[1][vh][1]), []).append(cr)
        by_v.setdefault((col, arm_of[0][uv][1]), []).append(cr)

    def _sat(weighted: bool):
        n_ok = 0.0
        for (vh, uv, row, col, w, junc) in crossings:
            sh = assign[(1, row, arm_of[1][vh][1])]
            sv = assign[(0, col, arm_of[0][uv][1])]
            if sh is not None and sv is not None \
                    and _couples(grid, row, sh, col, sv):
                n_ok += w if weighted else (0.0 if junc else 1.0)
        return n_ok

    def satisfied_count() -> int:
        return int(_sat(weighted=False))

    best = _sat(weighted=True)
    for _ in range(max(sweeps, 0)):
        for o in (0, 1):  # columns given rows, then rows given columns
            oo = 1 - o
            index = by_v if o == 0 else by_h
            for line, tr in sorted(tracks[o].items()):
                S = subs_of[(o, line)]
                if not S or not tr:
                    continue
                W = np.zeros((len(tr), len(S)))
                for ti in range(len(tr)):
                    for (vh, uv, row, col, w, _j) in index.get((line, ti), []):
                        other = assign[(oo, row if oo == 1 else col,
                                        arm_of[oo][vh if oo == 1 else uv][1])]
                        if other is None:
                            continue
                        for sj, s in enumerate(S):
                            ok = (_couples(grid, row, other, col, s)
                                  if o == 0 else
                                  _couples(grid, row, s, col, other))
                            if ok:
                                W[ti, sj] += w
                ri, ci = linear_sum_assignment(-W[:min(len(tr), len(S))])
                for ti, sj in zip(ri, ci):
                    assign[(o, line, ti)] = S[sj]
        cur = _sat(weighted=True)
        if cur <= best + 1e-9:
            break
        best = cur

    # claim qubit runs from the final assignment
    claimed: set = set()
    chains: Dict[int, List[int]] = {v: [] for v in pos}
    for o in (1, 0):
        for line, tr in sorted(tracks[o].items()):
            for ti, t in enumerate(tr):
                sub = assign[(o, line, ti)]
                if sub is None:
                    continue
                run = grid.wire_map.get((o, line, sub), {})
                for a, b, v in t:
                    for tt in range(int(math.floor(a)),
                                    int(math.ceil(b)) + 1):
                        q = run.get(tt)
                        if q is not None and q not in claimed:
                            claimed.add(q)
                            chains[v].append(q)
    _ensure_seeds(grid, claimed, chains, pos)
    return ({v: c for v, c in chains.items() if c},
            satisfied_count(), total)


def bar_domains(grid: TileGrid, pos: Dict[int, Point], bars: BarIntervals,
                src_adj: Dict[int, List[int]], *, kappa: float = 13.0,
                margin: int = 1) -> Dict[int, List[int]]:
    """Per-variable qubit domains for minorminer's ``restrict_chains``: shape
    transmitted as a CONSTRAINT REGION instead of a constructed chain — MM
    keeps every sub-tile identity choice (no wire coloring on this path).

    PARKED (Max, 2026-07-29): kept as the exact-handoff interface for the
    strip-minorminer-down agenda; blocked on stock minorminer 0.2.22's
    restrict_chains hang/segfault with non-trivial domains (repro:
    docs/paper2/data/restrict_bug_repro.py). The unblock is a fork-level
    patch when its hour comes.

    Capacity-gated: only variables with deg/kappa - 1 > 0 get a domain
    (missing entries are unrestricted in minorminer). Domain = h-wire qubits
    in the row band round(y_v) +- margin over the h-interval (+- margin),
    union v-wire qubits in the symmetric column band. Untyped grids: {}.
    """
    if not grid.typed:
        return {}
    tp = grid.coords @ grid.M.T + grid.c  # tile coords of all qubits
    tx, ty = tp[:, 0], tp[:, 1]
    rtx, rty = np.round(tx), np.round(ty)
    out: Dict[int, List[int]] = {}
    for v in sorted(pos):
        nbrs = [u for u in src_adj.get(v, []) if u in pos]
        if len(nbrs) / kappa - 1.0 <= 0:
            continue
        h_iv, v_iv = bars[v]
        r = round(float(pos[v][1]))
        c = round(float(pos[v][0]))
        m = float(margin)
        sel_h = ((grid.orient == 1)
                 & (rty >= r - m) & (rty <= r + m)
                 & (tx >= float(h_iv[0]) - m) & (tx <= float(h_iv[1]) + m))
        sel_v = ((grid.orient == 0)
                 & (rtx >= c - m) & (rtx <= c + m)
                 & (ty >= float(v_iv[0]) - m) & (ty <= float(v_iv[1]) + m))
        out[v] = [grid.qubits[int(i)] for i in np.flatnonzero(sel_h | sel_v)]
    return out


# ==============================================================================
# ALTERNATING ARRANGEMENT (notes s3.32): the fabric as two coupled 1-D layers
# ==============================================================================
#
# The hardware is ~ (grid x complete bipartite per tile) — a horizontal wire
# layer organized into rows and a vertical layer into columns, glued only by
# tile-local coupling. A variable is one interval in each layer; the plane
# "cross" is their superposition. Coordinate descent on the stair energy:
# alternately assign rows (columns frozen — each participant's h-interval is
# then a fixed-length 1-D interval, and rows are an exact interval-packing
# problem) and columns (rows frozen). Capacity is enforced per line by
# overlap DEPTH (interval-graph clique number) — no wire coloring inside the
# optimizer, only the depth test. Iteration 0 projects onto the feasible set
# (spreading from a compact init necessarily RAISES energy — that step is
# unconditional); later iterations accept a half-step only if E does not
# increase, so the alternation is monotone on the feasible set. Diagonal
# alignment (s3.35) couples the two 1-D orders; insertion sweeps (s3.36) are
# the general order move where adjacent structure is plateau-bound.


def line_depth(intervals: List[Tuple[float, float]]) -> int:
    """Max overlap depth of (a, b) intervals (endpoint sweep; the interval
    graph's clique number). Touching endpoints do not overlap."""
    if not intervals:
        return 0
    events = []
    for a, b in intervals:
        events.append((float(a), 1))
        events.append((float(b), -1))
    events.sort(key=lambda e: (e[0], e[1]))
    depth = best = 0
    for _, delta in events:
        depth += delta
        if depth > best:
            best = depth
    return best


def edge_monotonize(pos: Dict[int, Point], src_adj: Dict[int, List[int]], *,
                    max_sweeps: int = 16):
    """Per-edge diagonalization (2026-07-29 refinement; replaces the global
    x-rank := y-rank alignment). For each edge whose x-order disagrees with
    its y-order, propose swapping the two x-values — a multiset-preserving
    transposition, the local analog of the old global permutation — accepted
    only on a STRICT stair-energy decrease. Leverage scales with
    |x_u − x_v|: short (geometric) edges move almost nothing, long
    (dense-structure) edges do real reordering — the sparse/dense
    interpolation is a property of the move, not of any gate.

    On K_n every pair is an edge, so the sweep is a full sorting network and
    converges to a monotone (diagonal or anti-diagonal — mirror-equivalent)
    arrangement; across disjoint dense patches no cross-patch pressure
    exists, so patches diagonalize IN PLACE and side-by-side tilings stay
    reachable (the configuration the global alignment provably destroyed).

    x-swaps never change ``_stair_contacts`` (contacts key on y-order), so
    the per-edge orientation assignment is invariant through the sweep and
    only h-spans change — the gate is evaluated on the h-span total, with
    the (constant) v-span total omitted. Deterministic (sorted edge order,
    strict gate). Returns (new_pos, info): info carries sweep/swap counts
    and wall time (the pre-registered wall-time bar reads it).
    """
    import time as _time
    t0 = _time.perf_counter()
    nodes = sorted(pos)
    idx = {v: i for i, v in enumerate(nodes)}
    x = np.array([float(pos[v][0]) for v in nodes])
    y = np.array([float(pos[v][1]) for v in nodes])

    contacts = _stair_contacts(pos, src_adj)
    # h-net of w = {w} ∪ h-contacts(w); padded index matrix (self-padding is
    # span-neutral, so no mask is needed)
    hnets = [[idx[w]] + [idx[u] for u in contacts[w][0]] for w in nodes]
    width = max(len(h) for h in hnets)
    H = np.array([h + [h[0]] * (width - len(h)) for h in hnets])

    def h_total(xv: np.ndarray) -> float:
        vals = xv[H]
        return float((vals.max(axis=1) - vals.min(axis=1)).sum())

    edges = [(idx[v], idx[u]) for v in nodes
             for u in src_adj.get(v, []) if u in idx and u > v]
    cur = h_total(x)
    sweeps = swaps = 0
    for _ in range(max(max_sweeps, 1)):
        sweeps += 1
        improved = False
        for iu, iv in edges:
            dx = x[iu] - x[iv]
            dy = y[iu] - y[iv]
            if abs(dx) < 1e-9 or abs(dy) < 1e-9 or dx * dy > 0:
                continue  # degenerate or already monotone
            x[iu], x[iv] = x[iv], x[iu]
            new = h_total(x)
            if new < cur - 1e-9:
                cur = new
                swaps += 1
                improved = True
            else:
                x[iu], x[iv] = x[iv], x[iu]
        if not improved:
            break
    out = {v: np.array([x[idx[v]], float(pos[v][1])]) for v in nodes}
    return out, {"sweeps": sweeps, "swaps": swaps,
                 "time": round(_time.perf_counter() - t0, 4)}


def insertion_sweeps(order: List[int], src_adj: Dict[int, List[int]], *,
                     max_sweeps: int = 8,
                     values: Optional[np.ndarray] = None,
                     anchors: Optional[Tuple[np.ndarray, np.ndarray]] = None):
    """Best-insertion order search in rank space (notes s3.36) — the general
    global move for the queue abstraction. Relocating one variable flips
    ALL its edge orientations across the jumped interval at once, giving
    first-order energy signal exactly where adjacent swaps are
    plateau-bound (s3.35).

    Evaluated with EXACT integer-slot semantics (remove + reinsert, the
    jumped block shifts by one) — a fractional-rank shortcut was tried and
    collapses (rank stacking, the s3.30 pathology reborn in the proxy).
    Candidate targets sit adjacent to the moved variable's neighbours'
    slots (descent, not per-variable optimality, is the contract).
    Full-vector energy per candidate is O(n^2) numpy — participants are
    fabric-bounded (~<= 200), so a sweep is ~10^8 flops of BLAS, well under
    a second. Deterministic; returns (new_order, energy_trajectory).

    ``values`` (2026-07-29 refinement): the sorted y-value multiset the
    final permutation will be applied to. When given, the proxy prices a
    slot at the VALUE it would hold (``values[slot]``) instead of the slot
    index — rank space treats all gaps as 1, which is a lie exactly on
    clustered layouts (adjacent ranks can be 0.01 or 7 tiles apart). None
    = legacy slot pricing (uniform values).

    ``anchors`` = (lo_fix, hi_fix), arrays aligned with ``order``: per
    member, the min/max y of its NON-member neighbours (+inf/-inf when
    none). Folded into the proxy's span bounds, so edges into the sparse
    world GUIDE relocations instead of only vetoing them at the caller's
    composite gate; an anchor also contributes one candidate slot (the
    value's insertion point)."""
    members = list(order)
    n = len(members)
    if n <= 2:
        return list(members), [0.0]
    idx = {v: i for i, v in enumerate(members)}
    A = np.zeros((n, n), dtype=bool)
    for v in members:
        for u in src_adj.get(v, []):
            j = idx.get(u)
            if j is not None and j != idx[v]:
                A[idx[v], j] = True
    if values is not None:
        # Lexicographic pricing (the refine-probe turan bisection,
        # 2026-07-29): insertion runs after packing has quantized y onto
        # integer lines, so the raw value multiset is full of TIES and the
        # value-priced landscape becomes flat plateaus — no strict descent
        # within a tie class (E 3335 vs rank's 2098 on random-init turan;
        # rank pricing was accidentally a plateau-smoothing tie-break).
        # Price at value first, rank second: the epsilon (1e-4/slot, max
        # ~0.05 tiles at fabric scale) is far below the 1-tile line
        # quantum, so real gaps still dominate — truthful on cluster gaps,
        # strict on plateaus.
        val = np.asarray(values, dtype=float) + 1e-4 * np.arange(n)
    else:
        val = np.arange(n, dtype=float)
    if anchors is not None:
        lo_fix = np.asarray(anchors[0], dtype=float)
        hi_fix = np.asarray(anchors[1], dtype=float)
    else:
        lo_fix = np.full(n, np.inf)
        hi_fix = np.full(n, -np.inf)
    has = A.any(axis=1) | (hi_fix > -np.inf) | (lo_fix < np.inf)

    def energy(p):
        pv = val[p.astype(int)]
        P = np.where(A, pv[None, :], -np.inf)
        M = np.maximum(P.max(axis=1), hi_fix)
        Pm = np.where(A, pv[None, :], np.inf)
        m = np.minimum(Pm.min(axis=1), lo_fix)
        e = np.where(has,
                     np.maximum(M - pv, 0.0) + np.maximum(pv - m, 0.0), 0.0)
        return float(e.sum())

    p = np.arange(n, dtype=float)  # p[variable-index] = slot
    e_cur = energy(p)
    traj = [e_cur]
    sweep_vis = sorted(range(n), key=lambda i: members[i])
    for _ in range(max(max_sweeps, 1)):
        improved = False
        for vi in sweep_vis:
            if not has[vi]:
                continue
            i = int(p[vi])
            cand = set()
            for s in p[A[vi]]:
                cand.add(int(s))
                cand.add(int(s) + 1)
            if hi_fix[vi] > -np.inf:
                cand.add(int(np.searchsorted(val, hi_fix[vi])))
            if lo_fix[vi] < np.inf:
                cand.add(int(np.searchsorted(val, lo_fix[vi])))
            cand = {min(max(j, 0), n - 1) for j in cand} - {i}
            best_e, best_p = e_cur - 1e-9, None
            for j in sorted(cand):
                p2 = p.copy()
                if j > i:
                    mask = (p > i) & (p <= j)
                    p2[mask] -= 1.0
                else:
                    mask = (p >= j) & (p < i)
                    p2[mask] += 1.0
                p2[vi] = float(j)
                e2 = energy(p2)
                if e2 < best_e:
                    best_e, best_p = e2, p2
            if best_p is not None:
                p, e_cur = best_p, best_e
                improved = True
        traj.append(e_cur)
        if not improved:
            break
    new_order = [members[i] for i in
                 sorted(range(n), key=lambda i: (p[i], members[i]))]
    return new_order, traj


def alternate_arrange(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
                      grid: TileGrid, *, iters: int = 8, kappa: float = 13.0,
                      floor: bool = True, insert_sweeps: int = 0):
    """Alternating 1-D arrangement on the stair energy.

    Participation is **per-axis by derived arm length** (2026-07-29
    refinement): a variable enters row-packing iff its floored h-interval
    is >= 1 tile (it needs a wire run to lie on), column-packing iff its
    v-interval is — "a chain has an extent" is detected by the chain having
    an extent, not by degree. kappa survives only inside the floor. Short-
    arm variables are structurally untouched at every stage. Returns
    (new_pos, info); info = {"E": trajectory, "iters", "unplaced",
    "assigned" (union of last-packed sets; also per-axis counts),
    "insert_reverts", "mono_swaps", "mono_time"}.

    Intervals and the accepted energy come from the single-coverage
    diagonal rule (s3.34); the rule is keyed on the coordinate ORDER of the
    frozen axis's counterpart, and the packing is order-preserving, so the
    per-edge orientation assignment is invariant across a half-step.
    Order coupling is per-edge (``edge_monotonize``), not global — patches
    diagonalize in place and side-by-side tilings are reachable.
    """
    efn = stair_energy
    new_pos = {v: np.asarray(p, dtype=float).copy() for v, p in pos.items()}
    info = {"E": [efn(new_pos, src_adj)], "iters": 0, "unplaced": 0,
            "assigned": 0, "assigned_rows": 0, "assigned_cols": 0,
            "insert_reverts": 0, "mono_swaps": 0, "mono_time": 0.0}
    packed_last: Dict[int, set] = {1: set(), 0: set()}

    def _intervals(axis: int) -> Dict[int, Tuple[float, float]]:
        # floored stair interval per variable on the frozen axis (all
        # variables — participation is decided from the result)
        other = 0 if axis == 1 else 1
        contacts = _stair_contacts(new_pos, src_adj)
        out = {}
        for v in sorted(new_pos):
            nbrs = [u for u in src_adj.get(v, []) if u in new_pos]
            ids = contacts[v][0] if axis == 1 else contacts[v][1]
            xs = [float(new_pos[u][other]) for u in ids] \
                + [float(new_pos[v][other])]
            a, b = min(xs), max(xs)
            if floor:
                # half of the contact-capacity floor lives on each layer
                need = (len(nbrs) / kappa - 1.0) / 2.0
                deficit = need - (b - a)
                if deficit > 0:
                    a -= deficit / 2.0
                    b += deficit / 2.0
            out[v] = (a, b)
        return out

    def _mono():
        nonlocal new_pos
        new_pos, mi = edge_monotonize(new_pos, src_adj)
        info["mono_swaps"] += mi["swaps"]
        info["mono_time"] = round(info["mono_time"] + mi["time"], 4)

    def _half(axis: int, force: bool) -> bool:
        """Pack the axis's long-arm variables into lines; accept if E does
        not increase (or unconditionally when ``force``: the feasibility
        projection). Returns True if the state changed."""
        pool = (grid.cap[:, :, 1].mean(axis=1) if axis == 1
                else grid.cap[:, :, 0].mean(axis=0))
        nlines = grid.H if axis == 1 else grid.W
        ivs = _intervals(axis)
        parts = [v for v in sorted(new_pos)
                 if ivs[v][1] - ivs[v][0] >= 1.0]
        if not parts:
            info["E"].append(efn(new_pos, src_adj))
            return False
        order = sorted(parts, key=lambda v: (float(new_pos[v][axis]), v))
        lines: Dict[int, list] = {i: [] for i in range(nlines)}
        trial = {v: new_pos[v].copy() for v in new_pos}
        miss = 0
        for v in order:
            y0 = float(new_pos[v][axis])
            placed = False
            for ln in sorted(range(nlines), key=lambda i: (abs(i - y0), i)):
                if line_depth(lines[ln] + [ivs[v]]) <= pool[ln]:
                    lines[ln].append(ivs[v])
                    trial[v][axis] = float(ln)
                    placed = True
                    break
            if not placed:
                miss += 1  # no feasible line; stays put
        e_old = efn(new_pos, src_adj)
        e_new = efn(trial, src_adj)
        if force or e_new <= e_old + 1e-9:
            changed = any(not np.allclose(trial[v], new_pos[v])
                          for v in parts)
            for v in parts:
                new_pos[v] = trial[v]
            packed_last[axis] = set(parts)
            info["unplaced"] = miss
            info["E"].append(e_new)
            return changed
        info["E"].append(e_old)
        return False

    for it in range(max(iters, 1)):
        force = (it == 0)
        moved = _half(axis=1, force=force)
        _mono()
        moved = _half(axis=0, force=force) or moved
        info["iters"] = it + 1
        if not moved and not force:
            break

    if insert_sweeps > 0:
        # s3.36 best-insertion order search, value-priced (2026-07-29):
        # members = long-arm variables (floored w + h >= 1 tile); the proxy
        # prices slots at the y-VALUES the permutation will assign (rank
        # space lies on clustered layouts), with non-member neighbours
        # folded in as fixed anchors (they guide, not just veto). Propose
        # in rank space, apply as a permutation of the existing y-values,
        # re-monotonize and repack, dispose by TRUE stair energy with full
        # revert.
        widths = bar_widths(derive_bars_stair(
            new_pos, src_adj, kappa=kappa, floor=floor))
        members = [v for v in sorted(new_pos)
                   if float(widths[v][0] + widths[v][1]) >= 1.0]
        for _composite in range(2):
            if len(members) < 3:
                break
            order0 = sorted(members,
                            key=lambda v: (float(new_pos[v][1]), v))
            ys = np.array(sorted(float(new_pos[v][1]) for v in members))
            member_set = set(members)
            lo_fix = np.full(len(order0), np.inf)
            hi_fix = np.full(len(order0), -np.inf)
            for i, v in enumerate(order0):
                ext = [float(new_pos[u][1]) for u in src_adj.get(v, [])
                       if u in new_pos and u not in member_set]
                if ext:
                    lo_fix[i] = min(ext)
                    hi_fix[i] = max(ext)
            new_order, _tr = insertion_sweeps(
                order0, src_adj, max_sweeps=insert_sweeps,
                values=ys, anchors=(lo_fix, hi_fix))
            if new_order == order0:
                break
            e_pre = efn(new_pos, src_adj)
            # full-state snapshot: the composite's inner moves (monotonize
            # is universal, packing re-derives participation) may touch
            # non-members, and the revert must be total
            snap = {v: new_pos[v].copy() for v in new_pos}
            for r, v in enumerate(new_order):
                new_pos[v][1] = float(ys[r])
            _mono()
            _half(axis=1, force=False)
            _half(axis=0, force=False)
            e_post = efn(new_pos, src_adj)
            if e_post > e_pre + 1e-9:
                new_pos = snap
                info["insert_reverts"] += 1
                break
            info["E"].append(e_post)

    info["assigned_rows"] = len(packed_last[1])
    info["assigned_cols"] = len(packed_last[0])
    info["assigned"] = len(packed_last[1] | packed_last[0])
    return new_pos, info
