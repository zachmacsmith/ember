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



def _color_claim_bars(grid: TileGrid, claimed: set,
                      chains: Dict[int, List[int]], orientation: int,
                      bars: List[Tuple[int, float, float, int]],
                      targets: Optional[Dict[int, tuple]] = None) -> None:
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
            if not free:
                continue  # line oversubscribed; leave this bar point-seeded
            color = free[0]
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
                  src_adj: Optional[Dict[int, List[int]]] = None
                  ) -> Dict[int, List[int]]:
    """Wire-coherent seed chains (the sub-tile last mile, notes s3.30): each
    bar claims the CONTIGUOUS run of its greedily-colored wire's qubits
    across its interval, so seed chains are real coupled paths instead of
    stitched-together nearest qubits (which inflated routed ACL by ~30%).
    Derived bars are one-sided in general, so claims run over the ACTUAL
    interval, anchored at the owner's row/column — never a centered
    approximation. Untyped grids fall back to nearest-qubit sampling along
    the intervals (~1 per tile). Every variable gets at least one qubit.

    ``src_adj`` (snap claims, s3.56; stride-2 grids only, else ignored):
    aim each arm's claim at the lines of its stair-assigned contacts plus
    its own corner — parity-exact at color time. Measured: extension
    passes drop to zero, corners couple 100% directly. None = legacy,
    byte-identical."""
    claimed: set = set()
    chains: Dict[int, List[int]] = {v: [] for v in pos}
    snap = src_adj is not None and grid.stride > 1

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

    contacts = _stair_contacts(pos, src_adj) if snap else None

    def _targets(orientation: int):
        if not snap:
            return None
        out = {}
        ax = 0 if orientation == 1 else 1
        for v in sorted(pos):
            us = contacts[v][0] if orientation == 1 else contacts[v][1]
            lines = {int(round(float(pos[u][ax]))) for u in us}
            lines.add(int(round(float(pos[v][ax]))))  # own corner line
            out[v] = sorted(lines)
        return out

    def _tuples(orientation: int, targets):
        out = []
        for v in sorted(pos):
            h_iv, v_iv = bars[v]
            iv = h_iv if orientation == 1 else v_iv
            length = float(iv[1] - iv[0])
            if length < 1.0:  # participation on the ORIGINAL interval
                continue
            line = int(round(float(pos[v][1] if orientation == 1
                                   else pos[v][0])))
            a, b = float(iv[0]), float(iv[1])
            if targets is not None:
                # parity-agnostic hull widening: covering line c may need
                # p in {c-1, c}; guards the coloring against same-line
                # crossing-qubit theft (measured inert on capacity)
                cls = targets[v]
                a = min(a, float(min(cls) - 1))
                b = max(b, float(max(cls)))
                targets[v] = (float(iv[0]), float(iv[1]), cls)
            out.append((line, a, b, v))
        return out

    t1, t0 = _targets(1), _targets(0)
    _color_claim_bars(grid, claimed, chains, 1, _tuples(1, t1), t1)
    _color_claim_bars(grid, claimed, chains, 0, _tuples(0, t0), t0)
    _ensure_seeds(grid, claimed, chains, pos)
    return {v: c for v, c in chains.items() if c}


def claim_overload(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
                   grid: TileGrid, *, kappa: float = 13.0,
                   floor: bool = True) -> float:
    """Line-capacity violation of the CLAIM LAYER'S OWN census (s3.57):
    per orientation and line, hinge^2 of (interval depth - available
    sub-lanes), with intervals, participation, and line assignment
    computed by exactly wire_seeds_iv._tuples' rules — so the hinge is
    the uncolorability count squared, not a proxy. Used as a gate-energy
    term (evaluation only, never descended on): E-gated moves stop being
    blind to the violations that stranded 9 turan arms (d729, s3.56)."""
    cache = getattr(grid, "_subs_count", None)
    if cache is None:
        cache = {}
        for (u, ln, s) in grid.wire_map:
            cache[(u, ln)] = cache.get((u, ln), 0) + 1
        grid._subs_count = cache
    bars = derive_bars_stair(pos, src_adj, kappa=kappa, floor=floor,
                             bounds=(grid.W, grid.H))
    total = 0.0
    for orientation in (1, 0):
        by_line: Dict[int, list] = {}
        for v in sorted(pos):
            h_iv, v_iv = bars[v]
            iv = h_iv if orientation == 1 else v_iv
            if float(iv[1] - iv[0]) < 1.0:
                continue
            line = int(round(float(pos[v][1] if orientation == 1
                                   else pos[v][0])))
            by_line.setdefault(line, []).append(
                (float(iv[0]), float(iv[1])))
        for line, ivs in by_line.items():
            subs = cache.get((orientation, line), 0)
            over = line_depth(ivs) - subs
            if over > 0:
                total += float(over) ** 2
    return total


def complete_seeds(grid: TileGrid, chains: Dict[int, List[int]],
                   src_adj: Dict[int, List[int]], adj) -> tuple:
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
                        cost = len(got[0]) + len(got[1])
                        if best is None or cost < best[0]:
                            best = (cost, va, got[0], vb, got[1])
        if best is not None:
            commit(best[1], best[2], best[3], best[4])
        else:
            residual.append((a, b))

    # ---- bridge pass on the residual -------------------------------------
    for a, b in residual:
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


def _order_proxy(order: List[int], src_adj: Dict[int, List[int]],
                 values: Optional[np.ndarray],
                 anchors: Optional[Tuple[np.ndarray, np.ndarray]]):
    """Shared rank-space proxy for the order-move family (insertion_sweeps;
    the s3.53 order_shake was deleted at consolidation 2 — superseded by
    overload_lam, s3.57): members-only adjacency matrix, lexicographic value + slot
    pricing (the s3.40 tie-plateau fix), anchor bounds, and the O(n^2)
    vectorized span energy valid for ANY slot permutation p."""
    members = list(order)
    n = len(members)
    if n <= 2:
        return members, n, None, None, None, None, None, None
    idx = {v: i for i, v in enumerate(members)}
    A = np.zeros((n, n), dtype=bool)
    for v in members:
        for u in src_adj.get(v, []):
            j = idx.get(u)
            if j is not None and j != idx[v]:
                A[idx[v], j] = True
    if values is not None:
        # Lexicographic pricing (the refine-probe turan bisection,
        # 2026-07-29): these moves run after packing has quantized y onto
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

    return members, n, A, val, lo_fix, hi_fix, has, energy


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
    members, n, A, val, lo_fix, hi_fix, has, energy = _order_proxy(
        order, src_adj, values, anchors)
    if n <= 2:
        return list(members), [0.0]

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
                      floor: bool = True, insert_sweeps: int = 0,
                      overload_lam: float = 0.0):
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
    if overload_lam > 0.0:
        # s3.57: feasibility priced into the gate energy (Max's design —
        # "feasibility is part of the energy"). Evaluation only, never
        # descended on; rides every existing gate below (_half accepts,
        # the order composite). lam trades, never ranks (lam>=4 measured
        # to over-trade; lam=1 repairs turan's d729 for +0.2% E).
        # NOTE: info["E"] entries are in composed units when lam > 0.
        def efn(p, a):
            return (stair_energy(p, a)
                    + overload_lam * claim_overload(p, a, grid,
                                                    kappa=kappa,
                                                    floor=floor))
    else:
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
        # Line capacity = simultaneous overlapping arms per line = sub-lanes,
        # which is qubits-per-tile x stride (course-resolved Zephyr packs 8
        # interleaved arms per line, 4 bars per tile at any point; s3.49).
        # Multiplying cap keeps dead-qubit derating intact.
        caps = grid.cap[:, :, 1] if axis == 1 else grid.cap[:, :, 0].T
        pool = caps.mean(axis=1) * grid.stride
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
        # revert. Coarse moves + fine repair share ONE gate: a coarse
        # reversal typically raises raw E before insertion repairs it, so
        # gating the stages separately would reject every coarse move.
        widths = bar_widths(derive_bars_stair(
            new_pos, src_adj, kappa=kappa, floor=floor))
        members = [v for v in sorted(new_pos)
                   if float(widths[v][0] + widths[v][1]) >= 1.0]
        for _composite in range(2):
            if len(members) < 3:
                break
            ys = np.array(sorted(float(new_pos[v][1]) for v in members))
            member_set = set(members)
            # anchors per VARIABLE (order-independent); materialized as
            # aligned arrays per order below — passing arrays built for one
            # order to a call receiving another mis-attaches every anchor
            anchor_of = {}
            for v in members:
                ext = [float(new_pos[u][1]) for u in src_adj.get(v, [])
                       if u in new_pos and u not in member_set]
                anchor_of[v] = ((min(ext), max(ext)) if ext
                                else (np.inf, -np.inf))

            def _aligned(olist):
                lo = np.array([anchor_of[v][0] for v in olist])
                hi = np.array([anchor_of[v][1] for v in olist])
                return lo, hi

            order0 = sorted(members,
                            key=lambda v: (float(new_pos[v][1]), v))
            new_order, _tr = insertion_sweeps(
                order0, src_adj, max_sweeps=insert_sweeps,
                values=ys, anchors=_aligned(order0))
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
