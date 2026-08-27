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

try:  # s3.114 perf round: JIT for the hot loops (Max's call)
    from numba import njit as _njit
except ImportError:  # pragma: no cover — degrade to pure Python
    def _njit(*_a, **_k):
        def _wrap(f):
            return f
        return _wrap

Point = np.ndarray


def _tile_orient(target: nx.Graph, *, courses: bool = False
                 ) -> Optional[Dict[int, Tuple[int, int, int]]]:
    """Map each node to (tile_x, tile_y, orientation) using the hardware's own
    coordinate system, or None if the family isn't recognised.

    Orientation follows dnx conventions: u=0 couples along the vertical axis
    (consumes the vertical wire pool), u=1 along the horizontal axis.
    Pegasus nice-coordinates (t, y, x, u, k) interleave three Chimera-like
    subgrids; the t shifts are merged into one (x, y) tile since they share the
    same unit-cell footprint.

    ``courses`` (Zephyr only, no-op elsewhere): resolve the two j-courses of
    each track into separate sub-lanes (sub = 2k + j), so wire runs become
    same-course stride-2 sequences — the representation the constructive
    templates use (notes s3.49, fabrics s4.5). Off = the folded representation
    (sub = k, both courses on one run), the recorded stock arm.
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
            # Typed Zephyr adapter (2026-07-29, contraction round; conventions
            # pinned against dnx.zephyr_layout): coordinates (u, w, k, j, z);
            # u=0 vertical at column w, u=1 horizontal at row w; position
            # along the wire p = 2z + j. Half-cell tile resolution: (2m+1)
            # lines x (2m) positions. Two representations (s3.49, fabrics
            # s4.5):
            #   courses=False (stock): sub = k; a run holds both j-courses at
            #     consecutive p (COUPLED, verified — the odd-coupler zigzag).
            #   courses=True: sub = 2k + j; a run is one course at stride-2 p
            #     (COUPLED via external couplers, verified) — the lane the
            #     constructive templates are built from (16 fresh contacts
            #     per bar vs the zigzag's ~8).
            # Zephyr junctions are complete K_{8,8} — the Pegasus 56% coupler
            # pathology is absent (s3.37, fabrics s4.2).
            m = g.get("rows")
            t = g.get("tile")
            conv = dnx.zephyr_coordinates(m, t)
            out = {}
            for q in target.nodes():
                if labels == "coordinate":
                    u, w, k, j, z = q
                else:
                    u, w, k, j, z = conv.linear_to_zephyr(q)
                p = 2 * int(z) + int(j)
                sub = 2 * int(k) + int(j) if courses else int(k)
                if int(u) == 0:   # vertical: column w, spans y
                    out[q] = (int(w), p, 0, sub)
                else:             # horizontal: row w, spans x
                    out[q] = (p, int(w), 1, sub)
            return out
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
                 fallback_bins: int = 16, courses: bool = False):
        self.graph = target  # reference only (coupler lookups)
        qubits = sorted(pos)
        coords = np.array([pos[q] for q in qubits], dtype=float)
        tio = _tile_orient(target, courses=courses)
        # stride: tile-along step between consecutive qubits of one wire run
        # (2 for course-resolved Zephyr sub-lanes, 1 everywhere else)
        self.stride = 2 if (courses and tio is not None
                            and target.graph.get("family") == "zephyr") else 1

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
# invariant under the order-preserving packing in pack_project.
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
                      bounds: Optional[Tuple[int, int]] = None,
                      contacts=None) -> BarIntervals:
    """Single-coverage bars: v's h-arm spans the columns of its h-assigned
    contacts (+ its own column); v-arm spans the rows of its v-assigned
    contacts (+ its own row). Pure function of positions; never recentered.

    ``floor``: contact capacity (s3.30) — a chain of L qubits hosts at most
    ~kappa*L contacts, so total arm length owes w + h >= deg(v)/kappa - 1;
    any deficit is split evenly per axis and widened symmetrically.
    ``bounds=(W, H)`` clips intervals into the grid. ``contacts`` (an
    ``_stair_contacts`` result for the same y-order) skips recomputation
    — contacts depend only on the y-ORDER, so any caller whose mutation
    preserved it may pass the previous bundle through.
    """
    ids, arrs, _edges = _bars_arrays(pos, src_adj, kappa=kappa,
                                     floor=floor, bounds=bounds,
                                     contacts=contacts)
    hmin, hmax, vmin, vmax = arrs
    out: BarIntervals = {}
    for k, v in enumerate(ids):
        out[v] = (np.array([hmin[k], hmax[k]]),
                  np.array([vmin[k], vmax[k]]))
    return out


def _bars_arrays(pos, src_adj, *, kappa, floor, bounds, contacts):
    """Vectorized interior of ``derive_bars_stair`` (s3.114 perf round;
    the per-vertex original survives as the oracle in
    TestBooksEquivalence). Returns (ids, (hmin, hmax, vmin, vmax),
    (h_vi, h_ui, v_vi, v_ui)) — the edge index arrays are reused by
    ``arm_books``'s snap widening. Scatter min/max involves no
    arithmetic, and the floor/clip arithmetic replicates the original's
    op order exactly."""
    if contacts is None:
        contacts = _stair_contacts(pos, src_adj)
    ids = sorted(pos)
    idx = {v: k for k, v in enumerate(ids)}
    X = np.array([float(pos[v][0]) for v in ids])
    Y = np.array([float(pos[v][1]) for v in ids])
    hmin, hmax = X.copy(), X.copy()
    vmin, vmax = Y.copy(), Y.copy()
    h_vi: List[int] = []
    h_ui: List[int] = []
    v_vi: List[int] = []
    v_ui: List[int] = []
    for v in ids:
        h_us, v_us = contacts[v]
        k = idx[v]
        for u in h_us:
            h_vi.append(k)
            h_ui.append(idx[u])
        for u in v_us:
            v_vi.append(k)
            v_ui.append(idx[u])
    hv = np.array(h_vi, dtype=np.intp)
    hu = np.array(h_ui, dtype=np.intp)
    vv = np.array(v_vi, dtype=np.intp)
    vu = np.array(v_ui, dtype=np.intp)
    if hv.size:
        np.minimum.at(hmin, hv, X[hu])
        np.maximum.at(hmax, hv, X[hu])
    if vv.size:
        np.minimum.at(vmin, vv, Y[vu])
        np.maximum.at(vmax, vv, Y[vu])
    if floor:
        deg = np.array([float(len([u for u in src_adj.get(v, [])
                                   if u in pos])) for v in ids])
        need = deg / kappa - 1.0
        deficit = need - ((hmax - hmin) + (vmax - vmin))
        d4 = deficit / 4.0
        grow = deficit > 0
        hmin = np.where(grow, hmin + (-d4), hmin)
        hmax = np.where(grow, hmax + d4, hmax)
        vmin = np.where(grow, vmin + (-d4), vmin)
        vmax = np.where(grow, vmax + d4, vmax)
    if bounds is not None:
        hmin = np.clip(hmin, 0.0, bounds[0] - 1.0)
        hmax = np.clip(hmax, 0.0, bounds[0] - 1.0)
        vmin = np.clip(vmin, 0.0, bounds[1] - 1.0)
        vmax = np.clip(vmax, 0.0, bounds[1] - 1.0)
    return ids, (hmin, hmax, vmin, vmax), (hv, hu, vv, vu)


def stair_energy(pos: Dict[int, Point],
                 src_adj: Dict[int, List[int]],
                 contacts=None) -> float:
    """Total arm length under the diagonal rule (un-floored) — the
    single-coverage chain-length objective."""
    if contacts is None:
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


def _color_claim_bars(grid: TileGrid, claimed: set,
                      chains: Dict[int, List[int]], orientation: int,
                      bars: List[Tuple[int, float, float, int]],
                      targets: Optional[Dict[int, tuple]] = None,
                      require_free: bool = False, rng=None) -> None:
    """Color explicit interval bars onto physical wires and claim runs.
    ``bars``: (line, start, end, v) tuples of one orientation. Bars sharing
    a line with disjoint intervals may share a wire; overlapping ones may
    not — interval graph coloring, solved exactly by the greedy
    left-endpoint sweep. Oversubscribed bars are skipped (left point-seeded
    by the caller's guarantee pass).

    ``targets`` (snap claims, s3.56): {v: (a0, b0, [crossing lines])} —
    once the color s is known, the claim range becomes the integer hull of
    the ORIGINAL interval and the parity-exact crossing bars
    p* = c if c and s share parity else c-1 (aim, don't repair; s3.54's
    extension passes become verifiers). Targets at line 0 with an odd
    course give p* = -1 -> absent key, silently skipped (completion is
    the net)."""
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
            if require_free:
                # frozen-world awareness (ball rebuild): the color CHOICE
                # must consult occupancy, not just claim-time stealing —
                # otherwise a rebuild against a full fabric picks dead
                # wires or claims disconnected fragments. Admissible =
                # the lane's existing positions across the claim range
                # are all unclaimed (and there is at least one).
                lo0, hi0 = int(math.floor(a)), int(math.ceil(b))

                def _free_run(s_):
                    run_ = grid.wire_map.get((orientation, line, s_), {})
                    qs = [run_.get(t) for t in range(lo0, hi0 + 1)]
                    qs = [q for q in qs if q is not None]
                    return bool(qs) and all(q not in claimed for q in qs)

                free = [c for c in free if _free_run(c)]
            if not free:
                continue  # line oversubscribed; leave this bar point-seeded
            if targets is not None and v in targets:
                # s3.61 parity-preferring lane choice: pick the free lane
                # that can physically couple the most of this arm's
                # designated crossings (p* = c or c-1 by course parity
                # must exist on the lane's run — false exactly at
                # boundary junctions for the wrong parity). Replaces
                # blind free[0]; makes half-pool boundary lines usable.
                cls = targets[v][2]

                def _covered(s_):
                    run_ = grid.wire_map.get((orientation, line, s_), {})
                    return sum(1 for c in cls
                               if (c if c % 2 == s_ % 2 else c - 1) in run_)

                if rng is None:
                    color = max(free, key=lambda s_: (_covered(s_), -s_))
                else:
                    best_cov = max(_covered(s_) for s_ in free)
                    ties = sorted(s_ for s_ in free
                                  if _covered(s_) == best_cov)
                    color = ties[rng.randrange(len(ties))]
            else:
                # all free lanes are cost-equal: a frozen die today,
                # a fair one under re-asked descent (s3.82)
                color = free[0] if rng is None \
                    else free[rng.randrange(len(free))]
            used_colors[color] = b
            run = grid.wire_map.get((orientation, line, color), {})
            if targets is not None and v in targets:
                a0, b0, cls = targets[v]
                ps = [c if c % 2 == color % 2 else c - 1 for c in cls]
                lo = min([int(math.floor(a0))] + ps)
                hi = max([int(math.ceil(b0))] + ps)
            else:
                lo, hi = int(math.floor(a)), int(math.ceil(b))
            for t in range(lo, hi + 1):
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
                  bars: BarIntervals,
                  src_adj: Optional[Dict[int, List[int]]] = None,
                  snap: bool = False,
                  books=None) -> Dict[int, List[int]]:
    """Wire-coherent seed chains (notes s3.30): each bar claims the
    CONTIGUOUS run of its greedily-colored wire's qubits across its
    interval. Untyped grids fall back to nearest-qubit sampling.
    Every variable gets at least one qubit.

    ``snap`` (s3.56; the CALLER decides — the driver's effective config,
    s3.66): aim each arm's claim at the lines of its stair-assigned
    contacts plus its own corner, parity-exact at color time. Requires
    ``src_adj``. Claim intervals and participation come from the SHARED
    books (`arm_books`; pass ``books`` to reuse a bundle), so the
    coloring, the packer, and the overload census read one accounting.
    """
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

    snap = snap and src_adj is not None
    if books is not None:
        contacts, _, tuples = books
    else:
        contacts = (_stair_contacts(pos, src_adj)
                    if src_adj is not None else None)
        tuples = {}
        for o in (1, 0):
            ax = 0 if o == 1 else 1
            out = []
            for v in sorted(pos):
                iv = bars[v][0] if o == 1 else bars[v][1]
                if float(iv[1] - iv[0]) < 1.0:
                    continue
                a, b = float(iv[0]), float(iv[1])
                if snap:
                    us = contacts[v][0] if o == 1 else contacts[v][1]
                    lines = {int(round(float(pos[u][ax]))) for u in us}
                    lines.add(int(round(float(pos[v][ax]))))
                    a = min(a, float(min(lines) - 1))
                    b = max(b, float(max(lines)))
                line = int(round(float(pos[v][1] if o == 1
                                       else pos[v][0])))
                out.append((line, a, b, v))
            tuples[o] = out

    def _targets(orientation: int):
        if not snap:
            return None
        out = {}
        ax = 0 if orientation == 1 else 1
        present = {t[3] for t in tuples[orientation]}
        for v in sorted(pos):
            if v not in present:
                continue
            us = contacts[v][0] if orientation == 1 else contacts[v][1]
            lines = {int(round(float(pos[u][ax]))) for u in us}
            lines.add(int(round(float(pos[v][ax]))))
            iv = bars[v][0] if orientation == 1 else bars[v][1]
            out[v] = (float(iv[0]), float(iv[1]), sorted(lines))
        return out

    t1, t0 = _targets(1), _targets(0)
    _color_claim_bars(grid, claimed, chains, 1, tuples[1], t1)
    _color_claim_bars(grid, claimed, chains, 0, tuples[0], t0)
    _ensure_seeds(grid, claimed, chains, pos)
    return {v: c for v, c in chains.items() if c}


def _arm_targets(pos: Dict[int, Point], contacts, bars: BarIntervals,
                 orientation: int, present) -> Dict[int, tuple]:
    """Per-arm snap targets for one orientation: (a0, b0, sorted crossing
    lines incl. the arm's own corner). Shared by the exact converter and
    the required-hull census so the two can never drift (one
    accounting)."""
    ax = 0 if orientation == 1 else 1
    out: Dict[int, tuple] = {}
    for v in sorted(pos):
        if v not in present:
            continue
        us = contacts[v][0] if orientation == 1 else contacts[v][1]
        lines = {int(round(float(pos[u][ax]))) for u in us}
        lines.add(int(round(float(pos[v][ax]))))
        iv = bars[v][0] if orientation == 1 else bars[v][1]
        out[v] = (float(iv[0]), float(iv[1]), sorted(lines))
    return out


def _convert_line(grid: TileGrid, claimed: set,
                  chains: Dict[int, List[int]], orientation: int,
                  line: int, items: List[Tuple[float, float, int]],
                  targets: Optional[Dict[int, tuple]]) -> Tuple[int, int]:
    """The exact per-line converter, v2 (s3.96): jointly choose a
    parity class and a lane for every arm on one line so that every
    designated crossing (and the arm's own corner — it is in the
    target list) is parity-covered.

    v2 fixes the two measured v1 defects (notes s3.96): (1) claims
    contest POSITIONS, not books-hulls — an arm claims only its
    REQUIRED hull (the span of its parity targets), so benign overlap
    of the wider books intervals no longer blocks seating and chains
    get shorter than the kappa-floor width; (2) the class assignment
    is an exact DP whose state is the CLASSED ACTIVE SET — any
    feasible line keeps <= cap0+cap1 (= 8) arms alive at once, so the
    state space is tiny and the v1 greedy+repair thrash (1747 flips
    on ws) is gone. Dead qubits are absorbed as lane-infeasibility;
    they never reach the packer. Returns (misses, 0)."""
    subs_all = sorted({s for (o_, ln_, s) in grid.wire_map
                       if o_ == orientation and ln_ == line})
    if not subs_all or not items:
        return (len(items), 0)
    lanes = {0: [s for s in subs_all if s % 2 == 0],
             1: [s for s in subs_all if s % 2 == 1]}
    caps = {0: len(lanes[0]), 1: len(lanes[1])}

    # per arm, per parity: the REQUIRED hull — the span of the
    # parity-snapped targets only (p*(c,pi) is always == pi mod 2, so
    # covering the hull covers every target). The books interval
    # matters only as the fallback seed when an arm has no targets.
    arms = []
    for a, b, v in sorted(items):
        cls = (list(targets[v][2])
               if targets is not None and v in targets else [])
        R = {}
        for pi in (0, 1):
            ps = [c if c % 2 == pi else c - 1 for c in cls]
            ps = [p for p in ps if p >= 0]
            if ps:
                R[pi] = (min(ps), max(ps))
            else:
                p0 = int(round((a + b) / 2.0))
                p0 = p0 if p0 % 2 == pi else max(0, p0 - 1)
                R[pi] = (p0, p0)
        arms.append((a, b, v, R))
    n = len(arms)

    # ---- exact class assignment: DP over arms (sorted by earliest
    # required-lo), state = frozenset of (arm index, class) for arms
    # still active; any feasible state has <= 8 members. Cost =
    # total required-hull length (shorter claims win ties).
    order_i = sorted(range(n), key=lambda i: (min(arms[i][3][0][0],
                                                  arms[i][3][1][0]),
                                              arms[i][2]))
    states: Dict[frozenset, Tuple[float, tuple]] = {frozenset(): (0.0, ())}
    for i in order_i:
        lo0, hi0 = arms[i][3][0]
        lo1, hi1 = arms[i][3][1]
        nxt: Dict[frozenset, Tuple[float, tuple]] = {}
        for st, (cost, hist) in states.items():
            # expire actives whose interval ends before this arm starts
            # (interval-graph fact: depth maxima occur at starts, so
            # checking capacity at starts is exact)
            for pi, lo in ((0, lo0), (1, lo1)):
                live = frozenset(
                    (j, cj) for (j, cj) in st
                    if arms[j][3][cj][1] >= lo)
                cnt = sum(1 for (_j, cj) in live if cj == pi)
                if cnt + 1 > caps[pi]:
                    continue
                st2 = live | {(i, pi)}
                c2 = cost + (arms[i][3][pi][1] - arms[i][3][pi][0])
                h2 = hist + ((i, pi),)
                cur = nxt.get(st2)
                if cur is None or (c2, h2) < cur:
                    nxt[st2] = (c2, h2)
        if not nxt:
            # no feasible class assignment at all: seat greedily below
            states = {}
            break
        # prune: keep best cost per state
        states = nxt
    assign: Dict[int, int] = {}
    if states:
        best = min(states.values(), key=lambda t: (t[0], t[1]))
        for (i, pi) in best[1]:
            assign[i] = pi

    def _lane_ok(s: int, lo: int, hi: int) -> Optional[List[int]]:
        run = grid.wire_map.get((orientation, line, s), {})
        present = [p for p in range(lo, hi + 1) if p in run]
        if not present:
            return None
        if any(run[p] in claimed for p in present):
            return None
        if any(b_ - a_ != grid.stride
               for a_, b_ in zip(present, present[1:])):
            return None
        return [run[p] for p in present]

    # ---- seating: left-endpoint per class over REQUIRED hulls;
    # per-lane runs are position-disjoint by construction
    misses = 0
    lane_busy: Dict[int, int] = {}
    seat_order = sorted(range(n),
                        key=lambda i: arms[i][3][assign.get(i, 0)][0])
    for i in seat_order:
        a, b, v, R = arms[i]
        pi = assign.get(i)
        tried = ([pi, 1 - pi] if pi is not None else [0, 1])
        seated = False
        for cls_pi in tried:
            lo, hi = R[cls_pi]
            for s in lanes[cls_pi]:
                if lane_busy.get(s, -10**9) >= lo:
                    continue
                qs = _lane_ok(s, lo, hi)
                if qs is None:
                    continue
                for q in qs:
                    claimed.add(q)
                    chains[v].append(q)
                lane_busy[s] = hi
                seated = True
                break
            if seated:
                break
        if not seated:
            # fallback: books interval on any lane (old greedy claim)
            for s in subs_all:
                if lane_busy.get(s, -10**9) >= int(math.floor(a)):
                    continue
                qs = _lane_ok(s, int(math.floor(a)), int(math.ceil(b)))
                if qs is None:
                    continue
                for q in qs:
                    claimed.add(q)
                    chains[v].append(q)
                lane_busy[s] = int(math.ceil(b))
                break
            misses += 1
    return (misses, 0)


def wire_seeds_exact(grid: TileGrid, pos: Dict[int, Point],
                     bars: BarIntervals,
                     src_adj: Dict[int, List[int]],
                     books) -> Tuple[Dict[int, List[int]], dict]:
    """The exact converter (s3.96): plane layout -> claimed wires, one
    exact per-line solve at a time (``_convert_line``), replacing the
    three global greedy passes (snap coloring + completion's
    corner/edge repairs) with joint parity+lane choices. Completion
    still runs afterwards as the VERIFIER and bridge net. Reads the
    same shared books as everything else; returns (chains, info)."""
    claimed: set = set()
    chains: Dict[int, List[int]] = {v: [] for v in pos}
    info = {"convert_miss": 0, "convert_flips": 0}
    contacts, _, tuples = books
    for o in (1, 0):
        present = {t[3] for t in tuples[o]}
        targets = _arm_targets(pos, contacts, bars, o, present)
        by_line: Dict[int, list] = {}
        for line, a, b, v in tuples[o]:
            by_line.setdefault(line, []).append((a, b, v))
        for line, items in sorted(by_line.items()):
            m, f = _convert_line(grid, claimed, chains, o, line,
                                 items, targets)
            info["convert_miss"] += m
            info["convert_flips"] += f
    _ensure_seeds(grid, claimed, chains, pos)
    return {v: c for v, c in chains.items() if c}, info


def arm_books(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
              grid: TileGrid, *, kappa: float, floor: bool = True,
              snap: bool = False, min_span: float = 1.0,
              contacts=None):
    """THE one accounting (s3.66): the claim layer's books, computed once
    — contacts, bars, and per-orientation (line, interval, participant)
    tuples with snap's parity-agnostic hull widening applied when
    ``snap`` is on. Every consumer (the coloring's `_tuples`, the
    overload census, the packer's feasibility intervals) reads THESE
    books; the s3.65 fresh-eyes review caught the census skipping the
    widening the claims actually use (measured: inert on turan/K140,
    +1 violation-unit on spin_glass — the books had diverged).

    Returns (contacts, bars, tuples) where tuples[o] is a list of
    (line, a, b, v) for orientation o in (1, 0)."""
    if contacts is None:
        contacts = _stair_contacts(pos, src_adj)
    elif _VERIFY_CONTACTS:
        # staleness fence (s3.86, Max's question): any reused contacts
        # must equal a fresh recomputation — a mismatch here is the
        # silent-proxy-drift bug class, caught mechanically
        assert contacts == _stair_contacts(pos, src_adj), \
            "stale contacts consumed by a gate evaluation"
    ids, arrs, edges = _bars_arrays(pos, src_adj, kappa=kappa,
                                    floor=floor, bounds=(grid.W, grid.H),
                                    contacts=contacts)
    hmin, hmax, vmin, vmax = arrs
    hv, hu, vv, vu = edges
    bars: BarIntervals = {}
    for k, v in enumerate(ids):
        bars[v] = (np.array([hmin[k], hmax[k]]),
                   np.array([vmin[k], vmax[k]]))
    # rounded coordinates: Python round is half-to-even, np.rint matches
    RX = np.rint(np.array([float(pos[v][0]) for v in ids])).astype(np.int64)
    RY = np.rint(np.array([float(pos[v][1]) for v in ids])).astype(np.int64)
    tuples = {}
    for o in (1, 0):
        if o == 1:
            lo_a, hi_a, R = hmin, hmax, RX
            evi, eui = hv, hu
            lines_arr = RY
        else:
            lo_a, hi_a, R = vmin, vmax, RY
            evi, eui = vv, vu
            lines_arr = RX
        part = (hi_a - lo_a) >= min_span  # participation gate
        A, B = lo_a, hi_a
        if snap:
            ln_min, ln_max = R.copy(), R.copy()
            if evi.size:
                np.minimum.at(ln_min, evi, R[eui])
                np.maximum.at(ln_max, evi, R[eui])
            A = np.minimum(A, (ln_min - 1).astype(float))
            B = np.maximum(B, ln_max.astype(float))
        if min_span < 1.0:
            # occupancy footprint (order mode): a zero-width arm still
            # occupies its tile. Without this the census is blind to
            # point arms (line_depth treats touching endpoints as
            # disjoint) and the true-objective DP packs every variable
            # onto one line for free — the P16 collapse of order_probe
            # (E=0.0, turan 7.9->13.1). No-op wherever snap widening
            # already applies.
            B = np.where(B - A < 1.0, A + 1.0, B)
        out = []
        for k, v in enumerate(ids):
            if not part[k]:
                continue
            out.append((int(lines_arr[k]), float(A[k]), float(B[k]), v))
        tuples[o] = out
    return contacts, bars, tuples


def _brick_pool_arrays(grid: TileGrid, s: int):
    """Per-(line, brick) pools from wire_map: one slot per (wire, bar
    position) with the bar keyed to brick ``t // s``. Interior Zephyr
    bricks count 8 (4 aligned + 4 straddling); dead qubits and the
    over-allocated boundary column self-absorb to smaller pools (the
    packer's own boundary treatment, one accounting). Memoized on the
    grid (the line_pools pattern): the reference evaluator is called
    per gather candidate."""
    cache = getattr(grid, "_brick_pools", None)
    if cache is not None and s in cache:
        return cache[s]
    Wb = (grid.W + s - 1) // s
    Hb = (grid.H + s - 1) // s
    ph = np.zeros((grid.H, Wb), dtype=float)
    pv = np.zeros((grid.W, Hb), dtype=float)
    for (o, ln, _sub), d in grid.wire_map.items():
        A = ph if o == 1 else pv
        if not (0 <= ln < A.shape[0]):
            continue
        for t in d:
            tq = t // s
            if 0 <= tq < A.shape[1]:
                A[ln, tq] += 1.0
    if cache is None:
        cache = {}
        try:
            grid._brick_pools = cache
        except AttributeError:
            return ph, pv
    cache[s] = (ph, pv)
    return ph, pv


def line_pools(grid: TileGrid) -> Dict[Tuple[int, int], int]:
    """Per-(orientation, line) integer sub-lane pools from ``wire_map`` —
    the claim layer's own capacity census (absorbs the former
    ``_subs_count`` cache; s3.59): the number of physically claimable
    wires on each line. The packer's ONE census book — the s3.56 d729
    defect class was the packer budgeting from a float cap-mean (7.68 on
    course Zephyr lines) while the claim layer colored onto 8 integer
    sub-lanes. Whole-dead runs are absent from wire_map by construction;
    partially dead runs still count (their live segments are claimable).
    Untyped grids have no wire_map -> empty dict (callers fall back to
    the cap-mean pool). Cached on the grid; append-only usage."""
    cache = getattr(grid, "_line_pools", None)
    if cache is None:
        cache = {}
        for (u, ln, s) in grid.wire_map:
            cache[(u, ln)] = cache.get((u, ln), 0) + 1
        grid._line_pools = cache
    return cache


def complete_seeds(grid: TileGrid, chains: Dict[int, List[int]],
                   src_adj: Dict[int, List[int]], adj,
                   only: Optional[set] = None) -> tuple:
    """Exactness completion (notes s3.54): drive the seed chains to validity
    by construction. On junction-complete fabrics (Zephyr) validity ==
    coverage, so uncovered edges are closed by pure interval arithmetic:
    extend a chain's claimed run along its own wire, through FREE bars only,
    until a physical coupler to the other chain exists. Three passes, all
    deterministic:

    1. CORNER: connect each variable's own runs (chain connectivity).
    2. EDGE (sorted; live re-check — extensions cover later edges
       incidentally): for each uncovered source edge, the cheapest feasible
       perpendicular extension among both crossings and both sides. Target
       bar for run (1, r, s) to reach column line c: p* = c if c and s share
       parity else c-1 (verified an exact iff over all Z12 cross-orientation
       couplers); symmetric for v-runs.
    3. BRIDGE: 1- then 2-free-qubit bridges for the parallel-only residue.

    Residual deficit > 0 is not failure — the completed chains are a
    strictly better warm start for the router. Returns (chains, info).

    ``only`` (ball rebuild, the spur_prune precedent): restrict which
    chains may be EXTENDED — the corner pass skips non-members, the edge
    pass considers only edges incident to members and never extends a
    frozen side, bridges attach to the member endpoint. Pass the FULL
    chain dict regardless; frozen chains stay byte-identical.
    """
    out = {v: list(c) for v, c in chains.items()}
    claimed = set().union(*out.values()) if out else set()
    rev = {}
    for (u, ln, s), run in grid.wire_map.items():
        for p, q in run.items():
            rev[q] = (u, ln, s, p)

    def runs_of(v):
        by = {}
        for q in out.get(v, []):
            k = rev.get(q)
            if k is not None:
                by.setdefault(k[:3], []).append(k[3])
        return by

    def coupled(v, u):
        cu = out.get(u, [])
        su = set(cu)
        for q in out.get(v, []):
            for nb in adj[q]:
                if nb in su:
                    return True
        return False

    def ext_to(key, ps, p_star):
        """Bars to claim so run ``key`` (holding sorted positions ps)
        contains p_star; None if infeasible (missing/claimed bar)."""
        run = grid.wire_map.get(key, {})
        if p_star in ps:
            return []
        if run.get(p_star) is None:
            return None
        lo, hi = min(ps), max(ps)
        step = grid.stride
        if p_star < lo:
            span = range(lo - step, p_star - 1, -step)
        elif p_star > hi:
            span = range(hi + step, p_star + 1, step)
        else:
            return None  # hole inside the claimed interval: not extendable
        need = []
        for p in span:
            q = run.get(p)
            if q is None or q in claimed:
                return None
            need.append((p, q))
        return need

    def cross_cost(kh, ph_s, kv, pv_s):
        """Extensions for h-run kh and v-run kv to couple at their crossing;
        None if infeasible."""
        _, r, sh = kh
        _, c, sv = kv
        p_h = c if c % 2 == sh % 2 else c - 1
        p_v = r if r % 2 == sv % 2 else r - 1
        eh = ext_to(kh, ph_s, p_h)
        ev = ext_to(kv, pv_s, p_v)
        if eh is None or ev is None:
            return None
        return eh, ev

    def commit(v_h, eh, v_v, ev):
        for p, q in eh:
            claimed.add(q)
            out[v_h].append(q)
        for p, q in ev:
            claimed.add(q)
            out[v_v].append(q)
        info["extensions"] += 1
        info["ext_qubits"] += len(eh) + len(ev)

    info = {"deficit_edges": 0, "corner_deficit": 0, "extensions": 0,
            "ext_qubits": 0, "bridges": 0}

    # ---- corner pass: each variable's own runs must couple ----------------
    for v in sorted(out):
        if only is not None and v not in only:
            continue
        by = runs_of(v)
        hr = sorted(k for k in by if k[0] == 1)
        vr = sorted(k for k in by if k[0] == 0)
        if not hr or not vr:
            continue
        # already connected? any h-bar adjacent to any v-bar of the chain
        hs = [q for q in out[v] if rev.get(q, (None,))[0] == 1]
        vs_ = set(q for q in out[v] if rev.get(q, (None,))[0] == 0)
        if any(nb in vs_ for q in hs for nb in adj[q]):
            continue
        best = None
        for kh in hr:
            for kv in vr:
                got = cross_cost(kh, sorted(by[kh]), kv, sorted(by[kv]))
                if got is not None:
                    cost = len(got[0]) + len(got[1])
                    if best is None or cost < best[0]:
                        best = (cost, got)
        if best is not None:
            commit(v, best[1][0], v, best[1][1])
        else:
            info["corner_deficit"] += 1

    # ---- edge pass --------------------------------------------------------
    edges = sorted((min(a, b), max(a, b)) for a in src_adj
                   for b in src_adj[a] if a < b or b < a)
    edges = sorted(set(edges))
    if only is not None:
        edges = [e for e in edges if e[0] in only or e[1] in only]
    residual = []
    for a, b in edges:
        if a not in out or b not in out:
            info["deficit_edges"] += 1
            continue
        if coupled(a, b):
            continue
        ra, rb = runs_of(a), runs_of(b)
        best = None
        for va, vb in ((a, b), (b, a)):
            rha = [k for k in (ra if va == a else rb) if k[0] == 1]
            rvb = [k for k in (rb if vb == b else ra) if k[0] == 0]
            src_runs = ra if va == a else rb
            dst_runs = rb if vb == b else ra
            for kh in rha:
                for kv in rvb:
                    got = cross_cost(kh, sorted(src_runs[kh]),
                                     kv, sorted(dst_runs[kv]))
                    if got is not None:
                        if only is not None and (
                                (got[0] and va not in only)
                                or (got[1] and vb not in only)):
                            continue  # would extend a frozen chain
                        cost = len(got[0]) + len(got[1])
                        if best is None or cost < best[0]:
                            best = (cost, va, got[0], vb, got[1])
        if best is not None:
            commit(best[1], best[2], best[3], best[4])
        else:
            residual.append((a, b))

    # ---- bridge pass on the residual -------------------------------------
    for a, b in residual:
        # under ``only`` the bridge qubits must live on a member chain
        if only is not None and a not in only:
            a, b = b, a
        sa, sb = set(out[a]), set(out[b])
        na = sorted({nb for q in sorted(sa) for nb in adj[q]
                     if nb not in claimed})
        nb_set = {nb for q in sb for nb in adj[q] if nb not in claimed}
        done = False
        for w in na:
            if w in nb_set:  # 1-qubit bridge
                claimed.add(w)
                out[a].append(w)
                info["bridges"] += 1
                done = True
                break
        if not done:
            for w1 in na:
                w2s = sorted(x for x in adj[w1]
                             if x in nb_set and x not in claimed and x != w1)
                if w2s:
                    w2 = w2s[0]
                    claimed.add(w1)
                    claimed.add(w2)
                    out[a].extend([w1, w2])
                    info["bridges"] += 1
                    done = True
                    break
        if not done:
            info["deficit_edges"] += 1

    return out, info


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


def _target_kappa(grid: TileGrid) -> float:
    """Derived contact capacity: mean working-qubit degree of the target
    minus 2 (intra-chain links), floored at 2. Pegasus ~13.3 (matching the
    long-hardwired 13), Zephyr ~18, Chimera ~4 — the constant stops being
    Pegasus-specific (2026-07-29 contraction round).

    Course-resolved grids (stride > 1, s3.49): kappa must be the fresh-contact
    rate PER TILE of the claimable run, not the per-qubit degree — a stride-2
    lane's bar spans `stride` tiles, so kappa = mean cross-orientation degree
    / stride (Z12 ~7.7). The degree formula stays for stride-1 fabrics so
    Pegasus/Chimera are unchanged (fabrics s5 item 4)."""
    g = grid.graph
    n = g.number_of_nodes()
    if not n:
        return 2.0
    if grid.stride > 1:
        ori = {q: int(grid.orient[i]) for i, q in enumerate(grid.qubits)}
        cross = sum(1 for q, u in ori.items() for nb in g[q]
                    if ori.get(nb, u) != u)
        return max(2.0, cross / max(1, len(ori)) / grid.stride)
    return max(2.0, 2.0 * g.number_of_edges() / n - 2.0)


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


_VERIFY_CONTACTS = False  # staleness fence, tests only

_MISS_COST = 1e6  # a skip must dominate any real displacement (|y-l| <= L)


def _axis_coeffs(contacts, pos: Dict[int, Point],
                 axis: int) -> Dict[int, int]:
    """Linear coefficients of the stair energy's ``axis`` term (v4 order
    state): given the orders, E_axis = sum over nets of (value of the
    net's order-max member - value of its order-min member), which is
    SUM_v c_v * pos[v][axis] with c_v = (#nets v tops) - (#nets v
    bottoms). Valid for any order-preserving assignment, so the packer
    can minimize the true objective instead of displacement. Nets on
    axis 1 (row assignment / y values) are the v-nets {v} + v_us(v);
    on axis 0 (column assignment / x values) the h-nets {v} + h_us(v).
    Order-extremes are taken under (value, id) — the stair tie-break."""
    side = 1 if axis == 1 else 0
    c: Dict[int, int] = {v: 0 for v in pos}
    for v, (h_us, v_us) in contacts.items():
        members = [v] + (v_us if side == 1 else h_us)
        if len(members) < 2:
            continue
        hi = max(members, key=lambda u: (float(pos[u][axis]), u))
        lo = min(members, key=lambda u: (float(pos[u][axis]), u))
        c[hi] += 1
        c[lo] -= 1
    return c


@_njit(cache=True)
def _seg_radd(mx, dz, N, lo, hi, v):
    # iterative lazy range-add on [lo, hi), root max at mx[1]; exact
    # integer arithmetic, so any correct max structure reproduces the
    # old recursive _DepthTree's depths verbatim
    a = lo + N
    b = hi + N
    ll, rr = a, b
    while a < b:
        if a & 1:
            dz[a] += v
            mx[a] += v
            a += 1
        if b & 1:
            b -= 1
            dz[b] += v
            mx[b] += v
        a >>= 1
        b >>= 1
    x = ll >> 1
    while x >= 1:
        l2, r2 = mx[2 * x], mx[2 * x + 1]
        mx[x] = (l2 if l2 > r2 else r2) + dz[x]
        x >>= 1
    x = (rr - 1) >> 1
    while x >= 1:
        l2, r2 = mx[2 * x], mx[2 * x + 1]
        mx[x] = (l2 if l2 > r2 else r2) + dz[x]
        x >>= 1


@_njit(cache=True)
def _jstar_pass(lo, hi, nseg, c):
    # two-pointer feasible-run-start pass for one capacity: js[i] =
    # minimal j with depth(items j..i-1) <= c ("touching endpoints do
    # not overlap" via the lo < hi zero-width guard)
    n = lo.shape[0]
    N = 1
    while N < nseg:
        N <<= 1
    mx = np.zeros(2 * N, np.int64)
    dz = np.zeros(2 * N, np.int64)
    js = np.zeros(n + 1, np.int64)
    j = 0
    for i in range(1, n + 1):
        if lo[i - 1] < hi[i - 1]:
            _seg_radd(mx, dz, N, lo[i - 1], hi[i - 1], 1)
        while mx[1] > c:
            if lo[j] < hi[j]:
                _seg_radd(mx, dz, N, lo[j], hi[j], -1)
            j += 1
        js[i] = j
    return js


@_njit(cache=True)
def _jstar_profile(lo, hi, caps):
    # per-line feasibility with per-brick caps (s3.116): leaves start
    # at -cap[b] so the root tracks max(cover - cap) — feasible iff
    # root <= 0. Termination is structural: every leaf <= 0, so once
    # the window empties the root is <= 0 (js[i] = i at worst; the
    # DP's empty-window guard handles it). Padding leaves sit at a
    # sentinel no deposit can reach (endpoints are clamped to nb).
    n = lo.shape[0]
    nb = caps.shape[0]
    N = 1
    while N < nb:
        N <<= 1
    mx = np.empty(2 * N, np.int64)
    dz = np.zeros(2 * N, np.int64)
    for b in range(N):
        mx[N + b] = -caps[b] if b < nb else -(2 ** 60)
    for x in range(N - 1, 0, -1):
        l2, r2 = mx[2 * x], mx[2 * x + 1]
        mx[x] = l2 if l2 > r2 else r2
    js = np.zeros(n + 1, np.int64)
    j = 0
    for i in range(1, n + 1):
        if lo[i - 1] < hi[i - 1]:
            _seg_radd(mx, dz, N, lo[i - 1], hi[i - 1], 1)
        while mx[1] > 0:
            if lo[j] < hi[j]:
                _seg_radd(mx, dz, N, lo[j], hi[j], -1)
            j += 1
        js[i] = j
    return js


@_njit(cache=True)
def _pack_dp(n, L, values, coeffs, use_coeffs, js2d, capidx, miss):
    # the s3.59 DP, ported verbatim (s3.114): same op order, same
    # epsilons, deque as ring arrays — bit-identical to the Python
    # original by construction. parent codes: -2 carry, -1 skip,
    # j >= 0 run start.
    f_prev = np.empty(n + 1, np.float64)
    for i in range(n + 1):
        f_prev[i] = i * miss
    f_cur = np.empty(n + 1, np.float64)
    parent = np.full((L, n + 1), -2, np.int64)
    Cp = np.empty(n + 1, np.float64)
    dq_g = np.empty(n + 1, np.float64)
    dq_j = np.empty(n + 1, np.int64)
    for l in range(L):
        Cp[0] = 0.0
        if use_coeffs:
            for k in range(n):
                Cp[k + 1] = Cp[k] + coeffs[k] * l
        else:
            for k in range(n):
                Cp[k + 1] = Cp[k] + abs(values[k] - l)
        ci = capidx[l]
        head = 0
        tail = 0
        f_cur[0] = 0.0
        for i in range(1, n + 1):
            best = f_prev[i]
            par = -2
            if ci >= 0:
                jnew = i - 1
                g = f_prev[jnew] - Cp[jnew]
                while tail > head and dq_g[tail - 1] >= g:
                    tail -= 1
                dq_g[tail] = g
                dq_j[tail] = jnew
                tail += 1
                while tail > head and dq_j[head] < js2d[ci, i]:
                    head += 1
                if tail > head:
                    cand = dq_g[head] + Cp[i]
                    if cand < best - 1e-12:
                        best = cand
                        par = dq_j[head]
            scand = f_cur[i - 1] + miss
            if scand < best - 1e-12:
                best = scand
                par = -1
            f_cur[i] = best
            parent[l, i] = par
        for i in range(n + 1):
            f_prev[i] = f_cur[i]
    return parent, f_prev[n]


def pack_lines(intervals: List[Tuple[float, float]], values: List[float],
               pools: List[float], coeffs: Optional[List[float]] = None,
               brick: Optional[Tuple[int, list]] = None):
    """Exact order-preserving line packing (the s3.59 DP; replaces the
    greedy nearest-line-with-room loop). Items must be pre-sorted by
    (value, id); the assignment is NON-DECREASING in that order — the
    order-preservation invariant holds by construction (and the greedy's
    spill-boundary order scrambling is structurally impossible). Each
    line receives a contiguous run of the sorted sequence; a run is
    feasible on line l iff its interval overlap depth (``line_depth``)
    is <= pools[l] — capacity is a hard constraint, not a price. Cost =
    total displacement sum |value - line| (order-preserving packing =
    minimal-total-displacement 1-D transport, the standing doctrine);
    structurally unplaceable items are skipped at ``_MISS_COST`` each
    (they stay put — today's ``miss`` semantics; a skip inside a line's
    run ends that line's run, a documented mild restriction).

    Returns ``(assign, cost)``: ``assign[k]`` is the line index for the
    k-th item or ``None`` (skipped). Deterministic. Complexity: one
    two-pointer feasibility pass per distinct pool value (windows are
    depth-bounded) plus an O(n * L) sliding-window-minimum DP.

    ``coeffs`` (v4 order state) switches the cost to the TRUE stair
    objective: item k assigned to line l costs coeffs[k] * l (linear in
    the assignment, see ``_axis_coeffs``; negative coefficients are
    fine). ``values`` then serves only as the pre-sort carrier. The gate
    still re-checks the real energy on the caller's side, so the cost
    mode changes which assignment is proposed, never what is accepted.
    """
    n = len(intervals)
    L = len(pools)
    if n == 0:
        return [], 0.0

    # s3.114: the same algorithm, JIT-compiled — every decision lives
    # in the kernels above (ported op-for-op from the Python original,
    # which survives as the oracle in
    # TestPackLinesFeasibilityEquivalence). This body is marshaling.
    a_ends = np.array([float(a) for a, _b in intervals])
    b_ends = np.array([float(b) for _a, b in intervals])
    if brick is not None:
        # s3.116: per-(line, brick) capacity profiles — the pen books
        # as feasibility data. Inclusive hull [a, b] covers bricks
        # [floor(a/s), floor(b/s)] = half-open [lo, hi); endpoints
        # clamped into the fabric (out-of-fabric bricks are free,
        # matching the uniform pack's ignorance of out-of-window
        # extent; snap widening can produce a = -1 on line-0 contacts
        # and ideal-plane states can overhang on the right).
        s_b, profiles = brick
        lo_b = np.maximum(0.0, np.floor(a_ends / s_b)).astype(np.int64)
        hi_raw = (np.floor(b_ends / s_b) + 1.0).astype(np.int64)
        rows: List[np.ndarray] = []
        seen: dict = {}
        cap_list: List[int] = []
        for l in range(L):
            prof = profiles[l] if l < len(profiles) else None
            if prof is None or not np.any(prof > 0):
                cap_list.append(-1)
                continue
            key = prof.tobytes()
            if key not in seen:
                caps64 = prof.astype(np.int64)
                hi_c = np.minimum(hi_raw, caps64.shape[0])
                seen[key] = len(rows)
                rows.append(_jstar_profile(lo_b, hi_c, caps64))
            cap_list.append(seen[key])
        js2d = (np.vstack(rows) if rows
                else np.zeros((1, n + 1), np.int64))
        capidx = np.array(cap_list, np.int64)
        lo = lo_b  # unused below, kept for symmetry
    else:
        caps = sorted({int(p) for p in pools if p >= 1.0})
        coords = np.unique(np.concatenate((a_ends, b_ends)))
        m = max(1, coords.shape[0] - 1)  # elementary segments
        lo = np.searchsorted(coords, a_ends).astype(np.int64)
        hi = np.searchsorted(coords, b_ends).astype(np.int64)

        cap_of = {c: k for k, c in enumerate(caps)}
        js2d = (np.vstack([_jstar_pass(lo, hi, m, c) for c in caps])
                if caps else np.zeros((1, n + 1), np.int64))
        # cl == 0 lines (pool < 1) get capidx -1: no run transitions,
        # the old ``jstar.get(0) is None`` branch
        capidx = np.array([cap_of.get(int(p), -1) if p >= 1.0 else -1
                           for p in pools], np.int64)
    vals_arr = np.array([float(v) for v in values])
    if coeffs is None:
        cf = np.zeros(1)
        use_cf = False
    else:
        cf = np.array([float(c) for c in coeffs])
        use_cf = True
    parent, cost = _pack_dp(n, L, vals_arr, cf, use_cf, js2d, capidx,
                            _MISS_COST)

    assign: List[Optional[int]] = [None] * n
    i, l = n, L - 1
    while i > 0:
        if l < 0:
            i -= 1                                  # pre-line skips
            continue
        par = int(parent[l, i])
        if par == -2:                               # carry
            l -= 1
        elif par == -1:                             # skip
            i -= 1
        else:                                       # run par..i-1 on l
            for k in range(par, i):
                assign[k] = l
            i = par
            l -= 1
    return assign, float(cost)


def edge_monotonize(pos: Dict[int, Point], src_adj: Dict[int, List[int]], *,
                    max_sweeps: int = 16, contacts=None):
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

    x-swaps never change the orientation ASSIGNMENT (with the bits held
    fixed, v-hulls depend only on ys), so only h-spans change through the
    sweep — the gate is evaluated on the h-span total, with the (constant)
    v-span total omitted. ``contacts``: pass the caller's live contacts
    to skip the recompute (byte-identical: at every pipeline call site
    the carried contacts equal a fresh y-rule recomputation); None
    recomputes the y-rule.
    Deterministic (sorted edge order, strict gate). Returns
    (new_pos, info): info carries sweep/swap counts and wall time (the
    pre-registered wall-time bar reads it).
    """
    import time as _time
    t0 = _time.perf_counter()
    nodes = sorted(pos)
    idx = {v: i for i, v in enumerate(nodes)}
    x = np.array([float(pos[v][0]) for v in nodes])
    y = np.array([float(pos[v][1]) for v in nodes])

    if contacts is None:
        contacts = _stair_contacts(pos, src_adj)
    # h-net of w = {w} ∪ h-contacts(w); padded index matrix (self-padding is
    # span-neutral, so no mask is needed)
    hnets = [[idx[w]] + [idx[u] for u in contacts[w][0]] for w in nodes]
    width = max(len(h) for h in hnets)
    H = np.array([h + [h[0]] * (width - len(h)) for h in hnets])

    # s3.100b: incremental span accounting. A swap of x[iu], x[iv]
    # changes only the nets CONTAINING iu or iv, so its delta is priced
    # over those rows against a cached per-row span vector instead of
    # re-reducing the whole matrix (the measured hotspot: ~700k full
    # h_total calls per dense arrange). Positions are integer line
    # indices in the pipeline, so the delta arithmetic is exact and the
    # accept decisions are identical to the full re-evaluation.
    rows_of: List[List[int]] = [[] for _ in nodes]
    for r, net in enumerate(hnets):
        for i_mem in set(net):
            rows_of[i_mem].append(r)
    rows_pair = {}
    vals0 = x[H]
    row_span = vals0.max(axis=1) - vals0.min(axis=1)
    cur = float(row_span.sum())

    edges = [(idx[v], idx[u]) for v in nodes
             for u in src_adj.get(v, []) if u in idx and u > v]
    sweeps = swaps = 0
    for _ in range(max(max_sweeps, 1)):
        sweeps += 1
        improved = False
        for iu, iv in edges:
            dx = x[iu] - x[iv]
            dy = y[iu] - y[iv]
            if abs(dx) < 1e-9 or abs(dy) < 1e-9 or dx * dy > 0:
                continue  # degenerate or already monotone
            sel = rows_pair.get((iu, iv))
            if sel is None:
                sel = np.array(sorted(set(rows_of[iu] + rows_of[iv])),
                               dtype=np.int64)
                rows_pair[(iu, iv)] = sel
            x[iu], x[iv] = x[iv], x[iu]
            sub = x[H[sel]]
            new_span = sub.max(axis=1) - sub.min(axis=1)
            delta = float(new_span.sum() - row_span[sel].sum())
            if delta < -1e-9:
                cur += delta
                row_span[sel] = new_span
                swaps += 1
                improved = True
            else:
                x[iu], x[iv] = x[iv], x[iu]
        if not improved:
            break
    out = {v: np.array([x[idx[v]], float(pos[v][1])]) for v in nodes}
    return out, {"sweeps": sweeps, "swaps": swaps,
                 "time": round(_time.perf_counter() - t0, 4)}


def align_reinsert(order: List[int], cluster,
                   src_adj: Dict[int, List[int]],
                   values, anchors, *, axis: int,
                   other: Dict[int, float], contacts
                   ) -> Tuple[Optional[List[int]], bool]:
    """The alignment reinsertion move (s3.100): remove ``cluster``'s
    members from the order and reinsert them at the exact optimum over
    ALL interleavings with the rest — both sequences keep their internal
    relative order, and the reversed block competes (the gather's
    orientation bit, subsumed). Same contract as ``cluster_gather_order``:
    (new_order, flipped), (None, False) when nothing strictly improves.

    Pricing is the DP's own (not the O(n^2) proxy), exact within the
    view, per axis:

    - axis=1 (y): INDUCED-RULE pricing. The stair rule is an order
      statistic of the y-order, and the DP builds the y-order bottom-up,
      so contacts are re-derived per candidate instead of read stale:
      placing v, its h-net is {v} + its not-yet-placed neighbours
      (placed-after = above), whose OTHER-axis values are static this
      move — pay that span at the transition; the v-hull total is
      SUM over slot gaps of gap x #(arms crossing), where an arm crosses
      a gap iff its owner is unplaced while >=1 neighbour is placed.
      Both terms are functions of the placed set, which at DP cell
      (i, j) is path-independent (rest's first i, S's first j).
    - axis=0 (x): y untouched => contacts exactly frozen; the h-net
      spans decompose the same way (a net crosses a gap iff some member
      is placed and some is not); the v-term is constant and omitted.

    Values are epsilon-ramped (value + 1e-4*slot, the s3.40 tie-plateau
    convention shared with ``_order_proxy``); since the view's order0 is
    sorted by (value, id), the ramp's tie-break on the CURRENT order
    matches the stair rule's (y, id) exactly, so the current order's
    path cost equals its true view energy. Candidate merges may break
    same-value ties differently from the id rule — a documented h-side
    mispricing on same-line edges only, corrected by the composite's
    real-books gate. Anchored views (never produced by the pipeline,
    where every variable participates) are declined: (None, False)."""
    n = len(order)
    if n < 3:
        return None, False
    if anchors is not None:
        lo_fix = np.asarray(anchors[0], dtype=float)
        hi_fix = np.asarray(anchors[1], dtype=float)
        if (lo_fix < np.inf).any() or (hi_fix > -np.inf).any():
            return None, False
    cset = set(cluster)
    S = [v for v in order if v in cset]
    if len(S) < 1 or len(S) >= n:
        return None, False
    R = [v for v in order if v not in cset]
    p, m = len(R), len(S)
    val = np.asarray(values, dtype=float) + 1e-4 * np.arange(n)
    gapv = np.zeros(n)
    gapv[1:] = val[1:] - val[:-1]
    BIG = n + 1  # +inf proxy for index minima

    # ---- shared setup (s3.100b): one O(E) pass, numpy throughout;
    # both orientation arms derive from these structures (the reversed
    # arm's Q-side indices are m-1-q, so its sorted views are pure
    # slices of the forward arm's — nothing is rebuilt from src_adj) ----
    slot_of = {v: t for t, v in enumerate(order)}
    inS = np.zeros(n, dtype=bool)
    for t, v in enumerate(order):
        inS[t] = v in cset
    rpos = np.cumsum(~inS) - 1          # side-index, valid at R slots
    qpos = np.cumsum(inS) - 1           # side-index, valid at S slots
    r_slots = np.flatnonzero(~inS)      # slot of R[i]
    q_slots = np.flatnonzero(inS)       # slot of S[j] (forward)
    xs_slot = (np.array([float(other[v]) for v in order])
               if axis == 1 else None)

    heads: List[int] = []
    tails: List[int] = []
    for t, v in enumerate(order):
        for u in src_adj.get(v, []):
            if u != v and u in slot_of:
                heads.append(t)
                tails.append(slot_of[u])
    ha = np.asarray(heads, dtype=np.int64)
    ta = np.asarray(tails, dtype=np.int64)
    if ha.size:
        srt = np.argsort(ha, kind="stable")
        ta_s = ta[srt]
        bnd = np.searchsorted(ha[srt], np.arange(n + 1))
    else:
        ta_s = ta
        bnd = np.zeros(n + 1, dtype=np.int64)

    nRi: List[np.ndarray] = [None] * n  # R-side nbr indices, sorted
    nQi: List[np.ndarray] = [None] * n  # Q-side nbr indices (fwd), sorted
    xRn: List[Optional[np.ndarray]] = [None] * n  # x aligned with nRi
    xQn: List[Optional[np.ndarray]] = [None] * n  # x aligned with nQi
    for t in range(n):
        nb = ta_s[bnd[t]:bnd[t + 1]]
        mq = inS[nb]
        rn_t = rpos[nb[~mq]]
        qn_t = qpos[nb[mq]]
        ro = np.argsort(rn_t, kind="stable")
        qo = np.argsort(qn_t, kind="stable")
        nRi[t] = rn_t[ro]
        nQi[t] = qn_t[qo]
        if axis == 1:
            xRn[t] = xs_slot[nb[~mq]][ro]
            xQn[t] = xs_slot[nb[mq]][qo]
    minRv = np.array([int(a[0]) if a.size else BIG for a in nRi])
    minQf = np.array([int(a[0]) if a.size else BIG for a in nQi])
    maxQf = np.array([int(a[-1]) if a.size else -1 for a in nQi])

    net_stats = None
    if axis == 0:
        # frozen h-nets ({w} + h_us(w)) as forward index bounds
        net_stats = []
        for t, w in enumerate(order):
            mem = [t]
            for u in contacts[w][0]:
                tu = slot_of.get(u)
                if tu is not None and tu != t:
                    mem.append(tu)
            if len(mem) < 2:
                continue
            sl = np.asarray(mem, dtype=np.int64)
            mq = inS[sl]
            rs = rpos[sl[~mq]]
            qs = qpos[sl[mq]]
            net_stats.append((int(rs.min()) if rs.size else BIG,
                              int(rs.max()) if rs.size else -1,
                              int(qs.min()) if qs.size else BIG,
                              int(qs.max()) if qs.size else -1))

    # stepQ's R-side extrema rows are arm-independent: per S slot, the
    # extrema of static x over R-neighbours with index >= i, all i
    rrow_max: List[Optional[np.ndarray]] = [None] * n
    rrow_min: List[Optional[np.ndarray]] = [None] * n
    if axis == 1:
        ii_all = np.arange(p + 1)
        for t in q_slots:
            ra, xr = nRi[t], xRn[t]
            if ra.size:
                smaxs = np.concatenate(
                    [np.maximum.accumulate(xr[::-1])[::-1], [-np.inf]])
                smins = np.concatenate(
                    [np.minimum.accumulate(xr[::-1])[::-1], [np.inf]])
                pos = np.searchsorted(ra, ii_all)
                rrow_max[t] = smaxs[pos]
                rrow_min[t] = smins[pos]

    def _arm(arm_flip, path_of=None):
        """One orientation arm (``arm_flip`` reverses S). Returns
        (best_cost, best_order[, e_path]) where e_path is the DP path
        cost of ``path_of`` (a merge of R and forward S) if given."""
        Q = S[::-1] if arm_flip else S
        qsl = q_slots[::-1] if arm_flip else q_slots  # slot of Q[j]
        minQv = (m - 1 - maxQf) if arm_flip else minQf

        def _qview(t):
            # Q-side indices sorted ascending in THIS arm, x aligned
            if arm_flip:
                return ((m - 1 - nQi[t])[::-1],
                        xQn[t][::-1] if axis == 1 else None)
            return nQi[t], xQn[t]

        # point-cost arrays: stepR[i, j] = cost of placing R[i-1] into
        # cell (i, j) (from (i-1, j)); stepQ[i, j] likewise for Q[j-1]
        # (from (i, j-1)). Zero on axis=0 (all cost lives in the gaps).
        stepR = np.zeros((p + 1, m + 1))
        stepQ = np.zeros((p + 1, m + 1))
        if axis == 1:
            jj_all = np.arange(m + 1)
            for i in range(1, p + 1):
                t = r_slots[i - 1]
                ra, xr = nRi[t], xRn[t]
                pos = int(np.searchsorted(ra, i))
                smax = float(xr[pos:].max()) if pos < ra.size else -np.inf
                smin = float(xr[pos:].min()) if pos < ra.size else np.inf
                qa, xq = _qview(t)
                if qa.size:
                    sufmax = np.concatenate(
                        [np.maximum.accumulate(xq[::-1])[::-1],
                         [-np.inf]])
                    sufmin = np.concatenate(
                        [np.minimum.accumulate(xq[::-1])[::-1],
                         [np.inf]])
                    posj = np.searchsorted(qa, jj_all)
                    hi = np.maximum(np.maximum(sufmax[posj], smax),
                                    xs_slot[t])
                    lo = np.minimum(np.minimum(sufmin[posj], smin),
                                    xs_slot[t])
                    stepR[i, :] = hi - lo
                else:
                    stepR[i, :] = (max(smax, xs_slot[t])
                                   - min(smin, xs_slot[t]))
            for j in range(1, m + 1):
                t = qsl[j - 1]
                qa, xq = _qview(t)
                pos = int(np.searchsorted(qa, j))
                smax = float(xq[pos:].max()) if pos < qa.size else -np.inf
                smin = float(xq[pos:].min()) if pos < qa.size else np.inf
                if rrow_max[t] is not None:
                    hi = np.maximum(np.maximum(rrow_max[t], smax),
                                    xs_slot[t])
                    lo = np.minimum(np.minimum(rrow_min[t], smin),
                                    xs_slot[t])
                    stepQ[:, j] = hi - lo
                else:
                    stepQ[:, j] = (max(smax, xs_slot[t])
                                   - min(smin, xs_slot[t]))

        # count grid CG[i, j]: #arms (axis=1) / #open nets (axis=0)
        # crossing the next slot gap at cell (i, j) — a pure function of
        # the placed set, built by rectangle scatter + 2-D prefix sum.
        diff = np.zeros((p + 2, m + 2))

        def _rect(i0, i1, j0, j1, w):
            i0 = max(i0, 0)
            j0 = max(j0, 0)
            i1 = min(i1, p)
            j1 = min(j1, m)
            if i1 < i0 or j1 < j0:
                return
            diff[i0, j0] += w
            diff[i1 + 1, j0] -= w
            diff[i0, j1 + 1] -= w
            diff[i1 + 1, j1 + 1] += w

        if axis == 1:
            # arm of v crosses the gap at (i, j) iff v is unplaced and
            # >=1 neighbour is placed: [v unplaced] - [v unplaced and
            # no neighbour placed]
            for t in range(n):
                mr = int(minRv[t])
                mq_ = int(minQv[t])
                if not inS[t]:
                    r = int(rpos[t])
                    _rect(0, r, 0, m, +1.0)
                    _rect(0, min(r, mr), 0, mq_, -1.0)
                else:
                    q = int(m - 1 - qpos[t]) if arm_flip else int(qpos[t])
                    _rect(0, p, 0, q, +1.0)
                    _rect(0, mr, 0, min(q, mq_), -1.0)
        else:
            # h-net of w crosses the gap iff some member is placed and
            # some is not: 1 - [none placed] - [all placed]
            for (mnR, mxR, mnQ, mxQ) in net_stats:
                if arm_flip:
                    mnQ, mxQ = m - 1 - mxQ, m - 1 - mnQ
                _rect(0, p, 0, m, +1.0)
                _rect(0, mnR, 0, mnQ, -1.0)
                _rect(mxR + 1, p, mxQ + 1, m, -1.0)
        CG = np.cumsum(np.cumsum(diff, axis=0), axis=1)[:p + 1, :m + 1]

        # the DP. Full transition-cost matrices first: a[i, j] = cost of
        # the R-step into (i, j), b[i, j] = the Q-step's. Then the
        # right/down grid recurrence collapses per line: any path to
        # (i, j) enters row i by one R-step at some column k and
        # Q-steps from k to j, so T[i] = B[i] + running-min of
        # (T[i-1] + a[i] - B[i]) with B the row prefix-sum of b — one
        # minimum.accumulate per line, sweeping the SHORTER dimension.
        K = np.arange(p + 1)[:, None] + np.arange(m + 1)[None, :]
        gapM = gapv[np.maximum(K - 1, 0)]
        a = np.full((p + 1, m + 1), np.inf)
        a[1:, :] = stepR[1:, :] + gapM[1:, :] * CG[:-1, :]
        b = np.full((p + 1, m + 1), np.inf)
        b[:, 1:] = stepQ[:, 1:] + gapM[:, 1:] * CG[:, :-1]
        T = np.empty((p + 1, m + 1))
        if p <= m:
            B = np.zeros((p + 1, m + 1))
            B[:, 1:] = np.cumsum(b[:, 1:], axis=1)
            T[0, :] = B[0, :]
            for i in range(1, p + 1):
                T[i, :] = B[i, :] + np.minimum.accumulate(
                    T[i - 1, :] + a[i, :] - B[i, :])
        else:
            Bc = np.zeros((p + 1, m + 1))
            Bc[1:, :] = np.cumsum(a[1:, :], axis=0)
            T[:, 0] = Bc[:, 0]
            for j in range(1, m + 1):
                T[:, j] = Bc[:, j] + np.minimum.accumulate(
                    T[:, j - 1] + b[:, j] - Bc[:, j])
        # backtrack choices recovered vectorized from T + the cost
        # matrices; ties prefer the rest-step (deterministic merge)
        candR = np.full((p + 1, m + 1), np.inf)
        candR[1:, :] = T[:-1, :] + a[1:, :]
        candQ = np.full((p + 1, m + 1), np.inf)
        candQ[:, 1:] = T[:, :-1] + b[:, 1:]
        CH = (candR <= candQ + 1e-9).astype(np.int8)  # 1 = R-step

        i, j = p, m
        merged: List[int] = []
        while i + j > 0:
            if CH[i, j] == 1:
                merged.append(R[i - 1])
                i -= 1
            else:
                merged.append(Q[j - 1])
                j -= 1
        merged.reverse()

        e_path = None
        if path_of is not None:
            ci = cj = 0
            e_path = 0.0
            for v in path_of:
                g = gapv[ci + cj]
                if v not in cset:
                    e_path += stepR[ci + 1, cj] + g * CG[ci, cj]
                    ci += 1
                else:
                    e_path += stepQ[ci, cj + 1] + g * CG[ci, cj]
                    cj += 1
        return float(T[p, m]), merged, e_path

    bf, of, e0 = _arm(False, path_of=order)
    bb, ob, _ = _arm(True)
    if bb < bf - 1e-12:
        best, border, flip = bb, ob, True
    else:
        best, border, flip = bf, of, False
    if best < e0 - 1e-9 and border != order:
        return border, flip
    return None, False


def pack_project(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
                 grid: TileGrid, *, kappa: float, floor: bool = True,
                 snap: bool = False, monotonize: bool = True,
                 project: bool = True, brick_pools: bool = False):
    """The packer, alone (consolidation 7, s3.112): the exact
    order-preserving DP projection extracted verbatim from the old
    arrange loop's iter-0 path — one forced unbounded pack per axis
    with ``edge_monotonize`` between them (load-bearing: it permutes
    x-values between the packs, feeding the axis-0 sort and
    coefficients), then the s3.93 final bounded projection to the real
    window. Every accept is unconditional (a projection, not a
    search), so no gate energy is evaluated — positions are
    byte-identical to the old ``alternate_arrange(iters=1,
    insert_sweeps=0, cluster_groups=None)`` call this replaces, with
    the dead stair/census evaluations dropped. Used twice by the
    pipeline: the init projection and the family normalizer before
    conversion (the s3.110 discovery: the packer's remaining job is
    normalizing states into the family the converter/completion stack
    was co-designed with — its deletion is the converter co-design
    round's, not this one's). ``monotonize=False`` skips the
    x-permutation step: the orders engine uses the packer as a pure
    orders -> positions readout, which must not edit orders.
    Returns (new_pos, info)."""
    min_span = 0.0

    def _books(p, contacts=None):
        # contacts reuse: pass the previous bundle's contacts only when
        # the mutation provably preserved the y-ORDER (x-value
        # permutations and order-preserving x-packs)
        return arm_books(p, src_adj, grid, kappa=kappa, floor=floor,
                         snap=snap, min_span=min_span,
                         contacts=contacts)

    new_pos = {v: np.asarray(p, dtype=float).copy()
               for v, p in pos.items()}
    info = {"unplaced": 0, "mono_swaps": 0, "mono_time": 0.0}
    cur_books = _books(new_pos)

    def _mono():
        nonlocal new_pos, cur_books
        new_pos, mi = edge_monotonize(new_pos, src_adj,
                                      contacts=cur_books[0])
        info["mono_swaps"] += mi["swaps"]
        info["mono_time"] = round(info["mono_time"] + mi["time"], 4)
        if mi["swaps"]:
            # x-transpositions never touch the y-order
            cur_books = _books(new_pos, contacts=cur_books[0])

    def _half(axis: int, bounded: bool = False) -> None:
        """One forced pack of the axis's variables into lines.
        ``bounded=True`` uses the real-window pools (the final
        projection); otherwise the s3.93 infinite packer (uniform
        lanes, line-count bound dropped — L_max feasibility-safe by
        construction) with the canonical line-1 anchor."""
        nonlocal cur_books
        nlines = grid.H if axis == 1 else grid.W
        o = axis  # orientation == axis by construction
        items = [(a, b, v) for (line, a, b, v) in cur_books[2][o]]
        if not items:
            return
        parts = [v for (_a, _b, v) in items]
        ivs = {v: (a, b) for (a, b, v) in items}
        order = sorted(parts, key=lambda v: (float(new_pos[v][axis]), v))
        trial = {v: new_pos[v].copy() for v in new_pos}
        miss = 0
        lp = line_pools(grid)
        unb = (not bounded) and bool(lp)
        if unb:
            pool_u = float(max(lp.values()))
            L_max = nlines + ((len(items) + int(pool_u) - 1)
                              // max(1, int(pool_u)))
            pool = [pool_u] * L_max
            nlines = L_max
        elif bounded and brick_pools:
            # s3.116: the honest per-(line, brick) profile — the SAME
            # truth pen reads — replaces both the uniform-along-line
            # capacity and the boundary-line zeroing (boundary lines
            # get their true half pools instead of 0; watch item:
            # count-feasible but parity-starved boundary arms)
            s_b = max(int(getattr(grid, "stride", 1) or 1), 1)
            ph, pv = _brick_pool_arrays(grid, s_b)
            arr = ph if o == 1 else pv
            profiles = [arr[ln] for ln in range(nlines)]
            pool = [float(lp.get((o, ln), 0)) for ln in range(nlines)]
            brick_arg = (s_b, profiles)
        else:
            pool = [float(lp.get((o, ln), 0)) for ln in range(nlines)]
            if nlines >= 2:
                # boundary lines carry one course parity only
                # (fabrics s4.3b); the avoid rule as pool data
                pool[0] = 0.0
                pool[nlines - 1] = 0.0
        cmap = _axis_coeffs(cur_books[0], new_pos, axis)
        cs = [float(cmap.get(v, 0)) for v in order]
        assign, _cost = pack_lines(
            [ivs[v] for v in order],
            [float(new_pos[v][axis]) for v in order], pool,
            coeffs=cs,
            brick=(brick_arg if (bounded and brick_pools) else None))
        if unb:
            # canonical translation: anchor the layout at line 1 —
            # line 0 is a BOUNDARY line (halved real capacity;
            # measured: anchoring at 0 broke turan's exactness)
            placed_lines = [ln for ln in assign if ln is not None]
            if placed_lines:
                base = min(placed_lines) - 1
                if base:
                    assign = [None if ln is None else ln - base
                              for ln in assign]
        for v, ln in zip(order, assign):
            if ln is None:
                miss += 1
                if unb:
                    # structurally impossible (the L_max lemma); count
                    # instead of crash, tests assert zero
                    info["unb_miss"] = info.get("unb_miss", 0) + 1
                if grid.wire_map:
                    # s3.92 straggler clamp: a skipped variable must
                    # still live on a REAL line
                    trial[v][axis] = float(
                        min(nlines - 1,
                            max(0, round(float(new_pos[v][axis])))))
            else:
                trial[v][axis] = float(ln)
        # contacts reuse is safe ONLY for axis=0 (x untouched by
        # y-order); axis=1 must recompute (line collapse can flip
        # (y, id) tie-breaks)
        books_new = _books(trial,
                           contacts=cur_books[0] if axis == 0 else None)
        for v in parts:
            new_pos[v] = trial[v]
        cur_books = books_new
        info["unplaced"] = miss

    _half(axis=1)
    if monotonize:
        _mono()
    _half(axis=0)

    if project and line_pools(grid):
        # s3.93 final projection to the real window: record the ideal
        # layout's occupied width, then one forced bounded pack per
        # axis (real pools, boundary zeroing — or the honest brick
        # profiles under ``brick_pools`` — clamp for residues).
        # ``project=False`` (the plane engine's readout) stops here:
        # states stay on the ideal plane, the ONE projection runs
        # at the end of the search instead of inside every readout
        for ax, key in ((1, "final_width_y"), (0, "final_width_x")):
            vals = [float(p[ax]) for p in new_pos.values()]
            info[key] = int(max(vals) - min(vals)) + 1 if vals else 0
        _half(axis=1, bounded=True)
        m1 = info.get("unplaced", 0)
        _half(axis=0, bounded=True)
        info["projection_misses"] = m1 + info.get("unplaced", 0)

    # the final books' contacts describe the returned positions (the
    # axis-0 reuse invariant: x-packs preserve the y-order); callers
    # that would recompute _stair_contacts may read them here instead
    info["_contacts"] = cur_books[0]
    return new_pos, info

