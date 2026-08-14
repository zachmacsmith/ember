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
    if contacts is None:
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
    bars = derive_bars_stair(pos, src_adj, kappa=kappa, floor=floor,
                             bounds=(grid.W, grid.H), contacts=contacts)
    tuples = {}
    for o in (1, 0):
        ax = 0 if o == 1 else 1
        out = []
        for v in sorted(pos):
            iv = bars[v][0] if o == 1 else bars[v][1]
            if float(iv[1] - iv[0]) < min_span:  # participation gate
                continue
            a, b = float(iv[0]), float(iv[1])
            if snap:
                us = contacts[v][0] if o == 1 else contacts[v][1]
                lines = {int(round(float(pos[u][ax]))) for u in us}
                lines.add(int(round(float(pos[v][ax]))))
                a = min(a, float(min(lines) - 1))
                b = max(b, float(max(lines)))
            if min_span < 1.0 and b - a < 1.0:
                # occupancy footprint (order mode): a zero-width arm
                # still occupies its tile. Without this the census is
                # blind to point arms (line_depth treats touching
                # endpoints as disjoint) and the true-objective DP packs
                # every variable onto one line for free — the P16
                # collapse of order_probe (E=0.0, turan 7.9->13.1).
                # No-op wherever snap widening already applies.
                b = a + 1.0
            line = int(round(float(pos[v][1] if o == 1
                                   else pos[v][0])))
            out.append((line, a, b, v))
        tuples[o] = out
    return contacts, bars, tuples


def line_pools(grid: TileGrid) -> Dict[Tuple[int, int], int]:
    """Per-(orientation, line) integer sub-lane pools from ``wire_map`` —
    the claim layer's own capacity census (absorbs the former
    ``_subs_count`` cache; s3.59): the number of physically claimable
    wires on each line. Shared by the packer (``alternate_arrange._half``)
    and ``claim_overload`` so the two keep ONE book — the s3.56 d729
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


def claim_overload(pos: Dict[int, Point], src_adj: Dict[int, List[int]],
                   grid: TileGrid, *, kappa: float,
                   floor: bool = True, snap: bool = False,
                   books=None) -> float:
    """Line-capacity violation of the claim layer's own census (s3.57):
    per orientation and line, hinge^2 of (interval depth - available
    sub-lanes), computed on the SHARED books (`arm_books`) — including
    snap's hull widening when the claims use it (s3.66 unification).
    Pass ``books`` to reuse an already-computed bundle."""
    if books is None:
        books = arm_books(pos, src_adj, grid, kappa=kappa, floor=floor,
                          snap=snap)
    _, _, tuples = books
    lp = line_pools(grid)
    total = 0.0
    for o in (1, 0):
        by_line: Dict[int, list] = {}
        for line, a, b, v in tuples[o]:
            by_line.setdefault(line, []).append((a, b))
        for line, ivs in by_line.items():
            subs = lp.get((o, line), 0)
            over = line_depth(ivs) - subs
            if over > 0:
                total += float(over) ** 2
    return total


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


def pack_lines(intervals: List[Tuple[float, float]], values: List[float],
               pools: List[float], coeffs: Optional[List[float]] = None):
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
    from collections import deque

    # Feasible run starts: js[i] = minimal j such that the run of items
    # j..i-1 has depth <= c. Depth is monotone in window extension, so a
    # two-pointer sweep is exact; one pass per distinct capacity value.
    # s3.92: the window depth is maintained INCREMENTALLY with a lazy
    # max segment tree over the compressed interval endpoints (range
    # +1/-1 per insert/remove, root max = current depth) — the previous
    # code re-sorted and re-swept the whole window at every pointer
    # step (measured: 412k line_depth calls / 14M comparator lambdas
    # per ws run; ~20 ms per pack call, one arrange iteration of eight
    # ran). Same jstar arrays, byte-identical assignments.
    caps = sorted({int(p) for p in pools if p >= 1.0})
    coords = sorted({float(x) for a, b in intervals for x in (a, b)})
    cidx = {x: k for k, x in enumerate(coords)}
    m = max(1, len(coords) - 1)  # elementary segments between coords

    class _DepthTree:
        # max over elementary segments, lazy range-add. "Touching
        # endpoints do not overlap": interval (a, b) covers segments
        # [cidx[a], cidx[b]) — an empty range when a == b, exactly the
        # sweep's (x, -1)-before-(x, +1) tie rule.
        __slots__ = ("mx", "add")

        def __init__(self):
            self.mx = [0] * (4 * m)
            self.add = [0] * (4 * m)

        def _upd(self, node, nl, nr, lo, hi, d):
            if hi <= nl or nr <= lo:
                return
            if lo <= nl and nr <= hi:
                self.mx[node] += d
                self.add[node] += d
                return
            mid = (nl + nr) // 2
            self._upd(2 * node, nl, mid, lo, hi, d)
            self._upd(2 * node + 1, mid, nr, lo, hi, d)
            self.mx[node] = self.add[node] + max(self.mx[2 * node],
                                                 self.mx[2 * node + 1])

        def update(self, iv, d):
            lo, hi = cidx[float(iv[0])], cidx[float(iv[1])]
            if lo < hi:
                self._upd(1, 0, m, lo, hi, d)

        def depth(self):
            return self.mx[1]

    jstar = {}
    for c in caps:
        arr = [0] * (n + 1)
        tree = _DepthTree()
        j = 0
        for i in range(1, n + 1):
            tree.update(intervals[i - 1], 1)
            while tree.depth() > c:
                tree.update(intervals[j], -1)
                j += 1
            arr[i] = j
        jstar[c] = arr

    INF = float("inf")
    # f_prev[i] = min cost of the first i items using lines < l (before
    # any line: skips only).
    f_prev = [i * _MISS_COST for i in range(n + 1)]
    parent = [[None] * (n + 1) for _ in range(L)]
    for l in range(L):
        Cp = [0.0] * (n + 1)  # prefix sums of the per-item cost on line l
        if coeffs is None:
            for k in range(n):
                Cp[k + 1] = Cp[k] + abs(float(values[k]) - float(l))
        else:
            for k in range(n):
                Cp[k + 1] = Cp[k] + float(coeffs[k]) * float(l)
        cl = int(pools[l]) if pools[l] >= 1.0 else 0
        js = jstar.get(cl)
        f_cur = [INF] * (n + 1)
        f_cur[0] = 0.0
        dq = deque()  # (g, j) with g = f_prev[j] - Cp[j], increasing
        for i in range(1, n + 1):
            best, par = f_prev[i], ("c",)          # carry: lines < l only
            if js is not None:
                jnew = i - 1
                g = f_prev[jnew] - Cp[jnew]
                while dq and dq[-1][0] >= g:
                    dq.pop()
                dq.append((g, jnew))
                while dq and dq[0][1] < js[i]:
                    dq.popleft()
                if dq:
                    cand = dq[0][0] + Cp[i]        # run dq[0][1]..i-1 on l
                    if cand < best - 1e-12:
                        best, par = cand, ("r", dq[0][1])
            scand = f_cur[i - 1] + _MISS_COST      # skip item i-1
            if scand < best - 1e-12:
                best, par = scand, ("s",)
            f_cur[i] = best
            parent[l][i] = par
        f_prev = f_cur

    cost = f_prev[n]
    assign: List[Optional[int]] = [None] * n
    i, l = n, L - 1
    while i > 0:
        if l < 0:
            i -= 1                                  # pre-line skips
            continue
        par = parent[l][i]
        if par[0] == "c":
            l -= 1
        elif par[0] == "s":
            i -= 1
        else:
            j = par[1]
            for k in range(j, i):
                assign[k] = l
            i = j
            l -= 1
    return assign, cost


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


def cluster_gather_order(order: List[int], cluster,
                         src_adj: Dict[int, List[int]],
                         values: Optional[np.ndarray],
                         anchors: Optional[Tuple[np.ndarray, np.ndarray]],
                         orient: bool = False
                         ) -> Tuple[Optional[List[int]], float, bool]:
    """One coarse move in rank space (s3.70): gather ``cluster``'s members
    into a contiguous block of the order. The cluster is a member SET
    moved as one — nothing is summarized into a size; the caller's gated
    composite judges the real packed result. Within-block order is
    external-attachment rank (anchor midpoint — the certificate says ties
    are free); with ``orient`` (s3.89) the REVERSED block competes too —
    the derived order is a candidate, never a commitment (ideas s2.11),
    and reversal is the fold's atom. Candidate block positions are the
    members' mean slot and the insertion points of the cluster's
    aggregate anchor bounds (the single-member candidate rule
    generalized). Screened by the shared O(n^2) proxy; returns
    ``(order, gain, flipped)`` — the improving order, its proxy gain
    ``e0 - best_e`` (the strain estimate, s3.89), and whether the
    reversed block won; ``(None, 0.0, False)`` when nothing improves."""
    (members, n, A, val, lo_fix, hi_fix, has,
     energy) = _order_proxy(order, src_adj, values, anchors)
    if energy is None:
        return None, 0.0, False
    idx = {v: i for i, v in enumerate(members)}
    ins = [v for v in cluster if v in idx]
    if len(ins) < 2 or len(ins) >= n:
        return None, 0.0, False
    p0 = np.empty(n, dtype=float)
    for slot, v in enumerate(order):
        p0[idx[v]] = slot
    e0 = energy(p0)

    # Within-block order: anchor midpoint where finite, else the member's
    # current priced value; ties broken by id (merge-certified free).
    def _mid(v):
        i = idx[v]
        lo, hi = lo_fix[i], hi_fix[i]
        if lo < np.inf and hi > -np.inf:
            return 0.5 * (lo + hi)
        return float(val[int(p0[i])])
    block = sorted(ins, key=lambda v: (_mid(v), v))

    rest = [v for v in order if v not in set(ins)]
    k = len(ins)
    cands = set()
    cands.add(int(round(float(np.mean([p0[idx[v]] for v in ins])))))
    agg_lo = min((lo_fix[idx[v]] for v in ins), default=np.inf)
    agg_hi = max((hi_fix[idx[v]] for v in ins), default=-np.inf)
    if agg_lo < np.inf:
        cands.add(int(np.searchsorted(val, agg_lo)))
    if agg_hi > -np.inf:
        cands.add(int(np.searchsorted(val, agg_hi)))
    blocks = ((block, False), (block[::-1], True)) if orient \
        else ((block, False),)
    best_e, best_order, best_flip = e0 - 1e-9, None, False
    for s in sorted(cands):
        s = max(0, min(s, n - k))
        for blk, flip in blocks:
            new_order = rest[:s] + blk + rest[s:]
            p2 = np.empty(n, dtype=float)
            for slot, v in enumerate(new_order):
                p2[idx[v]] = slot
            e2 = energy(p2)
            if e2 < best_e:
                best_e, best_order, best_flip = e2, new_order, flip
    if best_order is None:
        return None, 0.0, False
    return best_order, float(e0 - best_e), best_flip


def insertion_sweeps(order: List[int], src_adj: Dict[int, List[int]], *,
                     max_sweeps: int = 8,
                     values: Optional[np.ndarray] = None,
                     anchors: Optional[Tuple[np.ndarray, np.ndarray]] = None,
                     deadline: Optional[float] = None):
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
        import time as _t
        if deadline is not None and _t.perf_counter() > deadline:
            break  # placement budget exhausted (s3.67): anytime bail

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
                      grid: TileGrid, *, iters: int = 8, kappa: float,
                      floor: bool = True, insert_sweeps: int = 0,
                      overload_lam: float = 0.0,
                      snap: bool = False,
                      deadline: Optional[float] = None,
                      cluster_groups=None,
                      gather_orient: bool = False,
                      strain_rank: bool = False,
                      edge_rounds=None,
                      clamp_miss: bool = True,
                      unbounded_pack: bool = False):
    """Alternating 1-D arrangement on the stair energy (v4 order state).

    Every variable participates (``min_span=0``, so the books census
    sees sub-tile arms) and the exact order-preserving DP packer (integer
    line pools, boundary zeroing) packs with the TRUE stair objective
    (``_axis_coeffs``) instead of displacement from the previous
    positions — the anchor that made first projections nearly
    irrevocable. Positions are always derived line indices.

    Policy is EXPLICIT (s3.66; this function never inspects the fabric):
    ``snap`` makes the shared books include the claim layer's hull
    widening; ``overload_lam`` prices claim-layer uncolorability into
    every gate (evaluation only). All bookkeeping (participation,
    intervals, lines) comes from ONE `arm_books` bundle per evaluated
    state, and the accepted state's energy is carried, not recomputed.
    Returns (new_pos, info).
    """
    min_span = 0.0

    def _eval(p, contacts=None):
        # ``contacts``: pass the previous bundle's contacts when the
        # mutation provably preserved the y-ORDER (x-swaps, x-value
        # permutations, and order-preserving packs on either axis) —
        # contacts depend on nothing else, and recomputing them was the
        # measured hotspot (2x _stair_contacts per arm_books, ~40% of
        # arrange wall on turan).
        books = arm_books(p, src_adj, grid, kappa=kappa, floor=floor,
                          snap=snap, min_span=min_span, contacts=contacts)
        e = stair_energy(p, src_adj, contacts=books[0])
        if overload_lam > 0.0:
            e += overload_lam * claim_overload(p, src_adj, grid,
                                               kappa=kappa, floor=floor,
                                               snap=snap, books=books)
        return books, e

    new_pos = {v: np.asarray(p, dtype=float).copy() for v, p in pos.items()}
    cur_books, cur_E = _eval(new_pos)
    info = {"E": [cur_E], "iters": 0, "unplaced": 0,
            "assigned": 0, "assigned_rows": 0, "assigned_cols": 0,
            "insert_reverts": 0, "mono_swaps": 0, "mono_time": 0.0}
    packed_last: Dict[int, set] = {1: set(), 0: set()}

    def _mono():
        nonlocal new_pos, cur_books, cur_E
        new_pos, mi = edge_monotonize(new_pos, src_adj)
        info["mono_swaps"] += mi["swaps"]
        info["mono_time"] = round(info["mono_time"] + mi["time"], 4)
        if mi["swaps"]:
            # x-transpositions never touch the y-order
            cur_books, cur_E = _eval(new_pos, contacts=cur_books[0])

    def _half(axis: int, force: bool, bounded: bool = False) -> bool:
        """Pack the axis's long-arm variables into lines; accept if the
        gate energy does not increase (or unconditionally when
        ``force``: the feasibility projection). ``bounded=True`` forces
        the real-window pools even under ``unbounded_pack`` (the s3.93
        final projection)."""
        nonlocal cur_books, cur_E
        nlines = grid.H if axis == 1 else grid.W
        o = axis  # orientation == axis by construction
        items = [(a, b, v) for (line, a, b, v) in cur_books[2][o]]
        if not items:
            info["E"].append(cur_E)
            return False
        parts = [v for (_a, _b, v) in items]
        ivs = {v: (a, b) for (a, b, v) in items}
        order = sorted(parts, key=lambda v: (float(new_pos[v][axis]), v))
        trial = {v: new_pos[v].copy() for v in new_pos}
        miss = 0
        lp = line_pools(grid)
        unb = unbounded_pack and not bounded and bool(lp)
        if unb:
            # s3.93 infinite packer: the ideal crossbar has uniform
            # lanes and as many lines as demand needs — hard capacity
            # UNCHANGED (the only honest anti-collapse force), the
            # LINE-COUNT bound dropped (the only reason skips ever
            # fired). L_max is feasibility-safe by construction: any
            # run can be cut to <= pool_u items (depth <= run size),
            # and ceil(n/pool_u) such runs always fit. The finite
            # fabric is priced by the census alone (out-of-window
            # lines have pool 0 there); boundary halving stays a
            # claim-layer fact.
            pool_u = float(max(lp.values()))
            L_max = nlines + ((len(items) + int(pool_u) - 1)
                              // max(1, int(pool_u)))
            pool = [pool_u] * L_max
            nlines = L_max
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
            coeffs=cs)
        if unb:
            # canonical translation: the unbounded cost is translation-
            # invariant, so anchor the layout at line 1 — line 0 is a
            # BOUNDARY line (halved real capacity; measured: anchoring
            # at 0 broke turán's exactness, 6.00 -> 6.70 with the skip
            # gate dark). The census then compares like against like
            # across packs.
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
                # (typed grids only: untyped targets have no real lines
                # and their contract is positions-pass-through — the
                # router owns them)
                if clamp_miss and grid.wire_map:
                    # s3.92 straggler clamp: a skipped variable must
                    # still live on a REAL line. Leaving it at its old
                    # value strands init-rank coordinates (up to n on a
                    # ~25-line fabric) in the books forever — measured
                    # death spiral on ws: 69 permanent ghosts, hulls at
                    # rank scale, E inflated 14x, cluster-pass churn on
                    # phantom gains. Clamped, the census sees localized
                    # real pressure the gates can act on, and the
                    # shrunken hulls make the variable packable next
                    # pass.
                    trial[v][axis] = float(
                        min(nlines - 1,
                            max(0, round(float(new_pos[v][axis])))))
            else:
                trial[v][axis] = float(ln)
        # contacts reuse is safe ONLY for axis=0 (x untouched by y-order).
        # axis=1 must recompute: even the order-preserving DP can collapse
        # two distinct y values onto one line, and the (y, id) tie-break
        # then flips any pair whose id order disagrees with the old value
        # order — stale contacts there would be a silent proxy drift.
        books_new, e_new = _eval(
            trial, contacts=cur_books[0] if axis == 0 else None)
        if force or e_new <= cur_E + 1e-9:
            changed = any(not np.allclose(trial[v], new_pos[v])
                          for v in parts)
            for v in parts:
                new_pos[v] = trial[v]
            cur_books, cur_E = books_new, e_new
            packed_last[axis] = set(parts)
            info["unplaced"] = miss
            info["E"].append(e_new)
            return changed
        info["E"].append(cur_E)
        return False

    import time as _time_mod

    def _axis_view(axis: int, members=None):
        """Rank-space view of one axis from the current state: the shared
        preamble of every order composite (s3.89 extraction — the strain
        screen needs it without paying for a gated composite). Returns
        (order0, vals, lo, hi) or None when fewer than 3 members."""
        if members is None:
            members = sorted({v for o in (1, 0)
                              for (_l, _a, _b, v) in cur_books[2][o]})
        if len(members) < 3:
            return None
        vals = np.array(sorted(float(new_pos[v][axis]) for v in members))
        member_set = set(members)
        anchor_of = {}
        for v in members:
            ext = [float(new_pos[u][axis]) for u in src_adj.get(v, [])
                   if u in new_pos and u not in member_set]
            anchor_of[v] = ((min(ext), max(ext)) if ext
                            else (np.inf, -np.inf))
        order0 = sorted(members,
                        key=lambda v: (float(new_pos[v][axis]), v))
        lo = np.array([anchor_of[v][0] for v in order0])
        hi = np.array([anchor_of[v][1] for v in order0])
        return order0, vals, lo, hi

    def _order_composite(_propose, members=None, axis=1, strict=False,
                         probe=None, settle=1):
        """One gated order composite (the s3.36/s3.61 flow, shared by the
        insertion and cluster move families): rebuild the rank-space view
        of the given AXIS from the current state, get a proposal, apply
        as a permutation of that axis's coordinate multiset, re-monotonize
        + repack, dispose by the gate energy with full revert. Returns
        None (no proposal / no-op), True (accepted), False (reverted).
        ``members=None`` recomputes participants from the current books
        (cluster path); the insertion path passes its pre-loop member
        list to preserve the exact s3.66 semantics. ``strict=True``
        (cluster moves, s3.73) requires strict energy DESCENT — lateral
        equal-energy accepts are what powered the expander churn loop
        (gather, pack disperses at equal E, re-gather, forever); with
        strict acceptance the energy itself bounds re-proposals and no
        scheduling rule is needed."""
        nonlocal new_pos, cur_books, cur_E
        view = _axis_view(axis, members)
        if view is None:
            return None
        order0, vals, lo, hi = view
        new_order = _propose(order0, vals, lo, hi)
        if new_order is None or new_order == order0:
            return None
        e_pre = cur_E
        ov_pre = claim_overload(new_pos, src_adj, grid, kappa=kappa,
                                floor=floor, snap=snap,
                                books=cur_books)
        snap_state = {v: new_pos[v].copy() for v in new_pos}
        books_snap = cur_books
        for r, v in enumerate(new_order):
            new_pos[v][axis] = float(vals[r])
        # x-axis proposals never touch the y-order; y-axis ones do
        cur_books, cur_E = _eval(
            new_pos, contacts=cur_books[0] if axis == 0 else None)
        _mono()
        for _s in range(max(1, settle)):
            # ``settle`` > 1 (fold composites, s3.89): a reversal folds
            # two strands onto SHARED lines (the multiset is preserved
            # by construction), so the seam needs extra alternating
            # pack rounds to spread apart before the verdict — the
            # E-gate prices the spreading (overload² relief vs stair
            # cost), the packs just get the chance to do it.
            e_before = cur_E
            _half(axis=1, force=False)
            _half(axis=0, force=False)
            if _s > 0 and cur_E >= e_before - 1e-9:
                break
        e_post = cur_E
        ov_post = claim_overload(new_pos, src_adj, grid, kappa=kappa,
                                 floor=floor, snap=snap,
                                 books=cur_books)
        # s3.61 hard veto: a permutation may not
        # create uncolorable lines — structural feasibility is a
        # gate condition, not a priced preference
        e_bad = (e_post >= e_pre - 1e-9) if strict \
            else (e_post > e_pre + 1e-9)
        if probe is not None:
            probe.append((e_post - e_pre, ov_post - ov_pre))
        if e_bad or ov_post > ov_pre + 1e-9:
            new_pos = snap_state
            cur_books, cur_E = books_snap, e_pre
            return False
        info["E"].append(e_post)
        return True

    def _cluster_pass():
        # s3.70/s3.73 cluster pass — coarse moves as gated composites. A
        # cluster is a member SET gathered as one: proposed in rank space
        # on the real members, judged by the same gate as every fine
        # move. Both axes (a y-only gather is half an address on a 2-D
        # fabric); STRICT descent (the energy is the schedule — see
        # _order_composite); no per-cluster caps — unchanged contexts
        # no-op for free at the proxy, and strict descent bounds total
        # accepts. Coarsest level first — or, with ``strain_rank``
        # (s3.89), in descending order of the screen's estimated gain:
        # the same proxy screens run either way; ranking changes only
        # the execution order and which items a tight deadline starves.
        # Estimates schedule, gates decide — a wrong estimate can only
        # defer a proposal (the composite re-proposes on the live
        # state), never corrupt an acceptance.
        info.setdefault("cluster_accepts", 0)
        info.setdefault("cluster_reverts", 0)
        info.setdefault("orient_accepts", 0)

        def _units():
            for level_groups in reversed(list(cluster_groups)):
                for cl in sorted(level_groups, key=lambda g: (-len(g), g)):
                    # Size-2 units are expressible as one insertion,
                    # which the insertion sweeps already search
                    # exhaustively — the cluster pass exists only for
                    # moves the fine set CANNOT make.
                    if len(cl) < 3:
                        continue
                    yield tuple(cl)

        def _run(key, ax):
            seen_flip = [False]

            def _prop(o0, vals, lo, hi, _cl=key):
                no, _gain, flip = cluster_gather_order(
                    o0, _cl, src_adj, vals, (lo, hi),
                    orient=gather_orient)
                seen_flip[0] = flip
                return no

            res = _order_composite(_prop, axis=ax, strict=True)
            if res is True:
                info["cluster_accepts"] += 1
                if seen_flip[0]:
                    info["orient_accepts"] += 1
            elif res is False:
                info["cluster_reverts"] += 1

        if not strain_rank:
            for key in _units():
                for ax in (1, 0):
                    if (deadline is not None
                            and _time_mod.perf_counter() > deadline):
                        return  # s3.67 anytime bail
                    _run(key, ax)
            return
        # s3.89 strain agenda: screen every (unit, axis) once on the
        # current state, then execute in descending estimated gain.
        agenda = []
        views = {ax: _axis_view(ax) for ax in (1, 0)}
        for key in _units():
            if (deadline is not None
                    and _time_mod.perf_counter() > deadline):
                break  # execute what is scored so far (defer, not drop)
            for ax in (1, 0):
                view = views[ax]
                if view is None:
                    continue
                o0, vals, lo, hi = view
                no, gain, _flip = cluster_gather_order(
                    o0, key, src_adj, vals, (lo, hi),
                    orient=gather_orient)
                if no is not None and gain > 0.0:
                    agenda.append((gain, key, ax))
        agenda.sort(key=lambda t: (-t[0], t[1], t[2]))
        for _gain, key, ax in agenda:
            if (deadline is not None
                    and _time_mod.perf_counter() > deadline):
                return  # s3.67 anytime bail
            _run(key, ax)

    fold_seen: Dict[Tuple[int, int, int], Tuple[int, int]] = {}

    def _fold_riffle(order_s, u, v):
        """The hairpin permutation of the [u..v] rank interval on the
        strand axis: far half reversed and RIFFLED into the near half,
        so strand partners land on adjacent slots (the DP then packs
        partner pairs onto shared lines). Returns (i, j, new_order) or
        None. A plain block reversal was measured dead here (194/194
        overload-vetoed): one axis preserves the value multiset, so
        both strands sat on the same lines — the fold is irreducibly
        a two-axis object."""
        iu = {x: r for r, x in enumerate(order_s)}
        if u not in iu or v not in iu:
            return None
        i, j = iu[u], iu[v]
        if i > j:
            i, j = j, i
        if j - i < 3:
            return None
        seg = order_s[i:j + 1]
        m = (len(seg) + 1) // 2
        near, far = seg[:m], seg[m:][::-1]  # far leads with v
        riff = []
        for k in range(m):
            riff.append(near[k])
            if k < len(far):
                riff.append(far[k])
        return i, j, order_s[:i] + riff + order_s[j + 1:]

    def _fold_composite(u, v, s_ax):
        # s3.89 two-axis hairpin composite: riffle the [u..v] interval
        # on the strand axis s AND split the interval's OWN value
        # multiset on the other axis t — near strand takes the lower
        # half, far strand the upper half (each keeping its internal
        # t-order) — so the two strands separate onto different lines
        # instead of doubling back over the same wires. Both
        # permutations preserve their axis's value multiset; judged by
        # the ordinary gate (strict descent + the s3.61 overload veto)
        # with settle rounds, full snapshot revert. Returns
        # None/True/False like _order_composite.
        nonlocal new_pos, cur_books, cur_E
        t_ax = 1 - s_ax
        view = _axis_view(s_ax)
        if view is None:
            return None
        order_s, vals_s, _lo, _hi = view
        rf = _fold_riffle(order_s, u, v)
        if rf is None:
            return None
        _i, _j, new_s = rf
        seg = order_s[_i:_j + 1]
        m = (len(seg) + 1) // 2
        near, far = seg[:m], seg[m:]
        tvals = sorted(float(new_pos[x][t_ax]) for x in seg)
        near_t = sorted(near, key=lambda x: (float(new_pos[x][t_ax]), x))
        far_t = sorted(far, key=lambda x: (float(new_pos[x][t_ax]), x))
        assign_t = {x: tvals[r] for r, x in enumerate(near_t + far_t)}
        e_pre = cur_E
        ov_pre = claim_overload(new_pos, src_adj, grid, kappa=kappa,
                                floor=floor, snap=snap, books=cur_books)
        snap_state = {x: new_pos[x].copy() for x in new_pos}
        books_snap = cur_books
        for r, x in enumerate(new_s):
            new_pos[x][s_ax] = float(vals_s[r])
        for x, tv in assign_t.items():
            new_pos[x][t_ax] = tv
        cur_books, cur_E = _eval(new_pos)  # y-order changed: no reuse
        _mono()
        for _s in range(3):
            e_before = cur_E
            _half(axis=1, force=False)
            _half(axis=0, force=False)
            if cur_E >= e_before - 1e-9:
                break
        e_post = cur_E
        ov_post = claim_overload(new_pos, src_adj, grid, kappa=kappa,
                                 floor=floor, snap=snap, books=cur_books)
        info["fold_dE_best"] = min(
            info.get("fold_dE_best", float("inf")), e_post - e_pre)
        if len(info.setdefault("fold_trace", [])) < 12:
            info["fold_trace"].append(
                (round(e_pre, 1), round(e_post, 1),
                 round(ov_pre, 1), round(ov_post, 1)))
        # The s3.61 ratchet guards feasibility ONCE ATTAINED. On a
        # still-infeasible state (ov_pre > 0: uncolorable lines exist
        # NOW) the ratchet was measured blocking 4-6x energy drops over
        # an overload epsilon (fold_trace, ws seed 0: E 57k -> 12k at
        # ov 391 -> 600, 84/84 vetoed) — there the priced energy, which
        # already contains lam x overload, is the guide.
        ov_bad = (ov_pre <= 1e-9 and ov_post > 1e-9)
        if e_post >= e_pre - 1e-9 or ov_bad:
            if ov_bad:
                info["fold_ov_rej"] = info.get("fold_ov_rej", 0) + 1
            new_pos = snap_state
            cur_books, cur_E = books_snap, e_pre
            return False
        info["E"].append(e_post)
        return True

    def _fold_pass():
        # s3.89 fold pass — the flagged-edge nominator. An edge that
        # merges LATE in the affinity filtration AND is long in the
        # CURRENT layout (graph x layout; the layout-free census was
        # refuted 2026-08-12) nominates a two-axis hairpin of the rank
        # interval between its endpoints, per strand axis. Nominations
        # are ranked by span x merge_round (threshold-free AND) and
        # screened by the strand-axis proxy so unchanged/hopeless
        # contexts no-op for free (an unscreened pass would eat the
        # placement budget on dense cells); the TOP-scored edge
        # bypasses the screen unconditionally — the detector's #1
        # target always reaches the real gate, so a proxy blind spot
        # can defer folds, never delete them. A rejected proposal is
        # remembered by its (i, j) rank context and not re-asked until
        # the context changes.
        info.setdefault("fold_tried", 0)
        info.setdefault("fold_accepts", 0)
        info.setdefault("fold_reverts", 0)
        if not edge_rounds:
            return
        scored = []
        for (u, v), rnd in edge_rounds.items():
            pu, pv = new_pos.get(u), new_pos.get(v)
            if pu is None or pv is None:
                continue
            span = (abs(float(pu[0] - pv[0]))
                    + abs(float(pu[1] - pv[1])))
            if span < 2.0:
                continue  # nothing to fold at rank-adjacent distance
            scored.append((span * float(rnd), u, v))
        if not scored:
            return
        scored.sort(key=lambda t: (-t[0], t[1], t[2]))
        top_uv = (scored[0][1], scored[0][2])

        # ONE executed composite per pass, found by lazy screening down
        # the span x round ranking. Folds are surgical, not bulk: a
        # measured eager pass (screen everything, execute everything
        # improving) spent the entire placement budget on fold
        # composites and screens (~150 x ~0.3 s) and starved the
        # ordinary moves that finish the layout — acl WORSE despite 9
        # accepted folds. One per pass x arrange_iters passes gives the
        # chords their surgical chances at ~5% of the budget.
        proxies = {}

        def _proxy_for(ax):
            if ax not in proxies:
                view = _axis_view(ax)
                if view is None:
                    proxies[ax] = None
                else:
                    o0, vals, lo, hi = view
                    pr = _order_proxy(o0, src_adj, vals, (lo, hi))
                    energy = pr[7]
                    if energy is None:
                        proxies[ax] = None
                    else:
                        n = pr[1]
                        e0 = energy(np.arange(n, dtype=float))
                        idx = {x: r for r, x in enumerate(o0)}
                        proxies[ax] = (o0, n, idx, e0, energy)
            return proxies[ax]

        for _score, u, v in scored:
            if (deadline is not None
                    and _time_mod.perf_counter() > deadline):
                return  # s3.67 anytime bail
            pu, pv = new_pos[u], new_pos[v]
            # fold along the longer axis first
            axes = sorted((1, 0), key=lambda a:
                          -abs(float(pu[a] - pv[a])))
            for ax in axes:
                pr = _proxy_for(ax)
                if pr is None:
                    continue
                o0, n, idx, e0, energy = pr
                rf = _fold_riffle(o0, u, v)
                if rf is None:
                    continue
                i, j, no = rf
                key = (u, v, ax)
                # context = the edge's GEOMETRY (interval size + line
                # spans), not raw ranks: rank drift from unrelated
                # packs must not re-buy an identical rejection.
                ctx = (j - i,
                       int(abs(float(pu[ax] - pv[ax]))),
                       int(abs(float(pu[1 - ax] - pv[1 - ax]))))
                if fold_seen.get(key) == ctx:
                    continue  # unchanged geometry: free no-op
                p2 = np.empty(n, dtype=float)
                for slot, x in enumerate(no):
                    p2[idx[x]] = slot
                gain = float(e0 - energy(p2))
                if gain <= 1e-9 and (u, v) != top_uv:
                    fold_seen[key] = ctx  # screened out at this context
                    continue
                res = _fold_composite(u, v, ax)
                if res is None:
                    continue
                info["fold_tried"] += 1
                if res is True:
                    info["fold_accepts"] += 1
                else:
                    info["fold_reverts"] += 1
                    fold_seen[key] = ctx
                return  # one executed composite per pass

    for it in range(max(iters, 1)):
        if (deadline is not None and it > 0
                and _time_mod.perf_counter() > deadline):
            break  # placement budget exhausted (s3.67); iter-0 projection
                   # always completes (feasibility is not optional)
        force = (it == 0)
        moved = _half(axis=1, force=force)
        _mono()
        moved = _half(axis=0, force=force) or moved
        info["iters"] = it + 1
        if cluster_groups:
            # s3.70: one coarse pass per iteration, always after the
            # projection (a pre-pack pass measured worse: gates compare
            # fictions on the soft state). Pack and gather alternate, so
            # each gather sees the multiset the previous round earned —
            # E-gated, so converged iterations cost only proxy screens.
            _cluster_pass()
        if edge_rounds:
            # s3.89: folds judge packed geometry (same cadence rule as
            # the cluster pass — never before the projection).
            _fold_pass()
        if not moved and not force:
            break

    if cluster_groups:
        _cluster_pass()  # late: coarse polish on the packed state
    if edge_rounds:
        _fold_pass()  # late: fold polish on the packed state

    if unbounded_pack and line_pools(grid):
        # s3.93 final projection to the real window: record the ideal
        # layout's occupied width (the honest fit-vs-fabric
        # observable), then one forced bounded pack per axis (real
        # pools, boundary zeroing, clamp for residues).
        for ax, key in ((1, "final_width_y"), (0, "final_width_x")):
            vals = [float(p[ax]) for p in new_pos.values()]
            info[key] = int(max(vals) - min(vals)) + 1 if vals else 0
        _half(axis=1, force=True, bounded=True)
        m1 = info.get("unplaced", 0)
        _half(axis=0, force=True, bounded=True)
        info["projection_misses"] = m1 + info.get("unplaced", 0)



    if insert_sweeps > 0:
        # s3.36 best-insertion order search, value-priced; members are
        # the union of both orientations' participants per the shared
        # books (s3.66 — replaces the former summed-width predicate;
        # gate-protected change). Members fixed before the composite loop
        # (pre-refactor semantics preserved exactly).
        def _ins_propose(order0, ys, lo, hi):
            no, _tr = insertion_sweeps(
                order0, src_adj, max_sweeps=insert_sweeps,
                values=ys, anchors=(lo, hi), deadline=deadline)
            return no

        ins_members = sorted({v for o in (1, 0)
                              for (_l, _a, _b, v) in cur_books[2][o]})
        for _composite in range(2):
            if len(ins_members) < 3:
                break
            if (deadline is not None
                    and _time_mod.perf_counter() > deadline):
                break  # s3.67 anytime bail
            res = _order_composite(_ins_propose, members=ins_members)
            if res is False:
                info["insert_reverts"] += 1
            if res is not True:
                break

    info["assigned_rows"] = len(packed_last[1])
    info["assigned_cols"] = len(packed_last[0])
    info["assigned"] = len(packed_last[1] | packed_last[0])
    return new_pos, info
