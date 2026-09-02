"""The orders-state arrange engine (rounds 1-5, 2026-08-26/28).

State is the two axis orders; positions are always DERIVED by the pack
readout — ``pack_project(monotonize=False)``, a pure orders->positions
projection (books -> forced y-pack -> forced x-pack -> bounded window
packs). Every state the engine occupies is therefore packer output by
construction, so no family normalizer runs before conversion.

One structural move: ``align_reinsert`` on variable sets — contiguous
intervals of the current order at all dyadic scales (singles gather,
wider intervals weave), optional graph-derived hierarchy groups, and
(carry mode) per-edge pairs. The DP already gates on its own view of
the current order, so in the default mode every non-None proposal is
adopted and the readout projects it back onto the feasible manifold —
projected block-coordinate descent: the order is the graph's variable,
the positions are the fabric's. The best-state bookmark is what the
engine returns. ``audit=True`` is the acceptance-rule control arm.

``carry=True`` (s3.118) makes the two orders the state LITERALLY: the
tie-break everywhere on this path is rank in the carried order (ids
speak once, at entry, when the orders are born), every interleaver
candidate is a real state by construction, the pack cannot invalidate
its own coefficients, and edge-pair units subsume edge_monotonize
(whose per-pass call is dropped here).
"""
from __future__ import annotations

import time as _time
from typing import Dict, List, Optional, Tuple

import numpy as np

from ember_qc.algorithms.factored.field import (
    TileGrid, _stair_contacts, align_reinsert, edge_monotonize,
    line_pools, pack_project, stair_energy, xy_reinsert)
from ember_qc.algorithms.factored.seat import (_LEX_M, _span_vectors,
                                               seat_energy)

# belt-and-braces pass cap: accept-all descends on the DP's view, not on
# E, so no internal energy signal is guaranteed to terminate it — the
# deadline is the real bound, this is the backstop for deadline=None
_MAX_PASSES = 64


def _copy(pos: Dict[int, np.ndarray]) -> Dict[int, np.ndarray]:
    return {v: p.copy() for v, p in pos.items()}


def _same(a: Dict[int, np.ndarray], b: Dict[int, np.ndarray]) -> bool:
    return all(np.array_equal(a[v], b[v]) for v in a)


def order_arrange(pos0: Dict[int, np.ndarray],
                  src_adj: Dict[int, List[int]],
                  grid: TileGrid,
                  *,
                  kappa: float,
                  floor: bool = True,
                  snap: bool = False,
                  audit: bool = False,
                  deadline: Optional[float] = None,
                  extra_units: Optional[List[List[List[int]]]] = None,
                  plane: bool = False,
                  carry: bool = False,
                  tiles: bool = False,
                  xy: bool = False,
                  wave: bool = False,
                  axis_inner: bool = False,
                  widen: bool = False,
                  ) -> Tuple[Dict[int, np.ndarray], dict]:
    info: dict = {
        "passes": 0, "accept_traj": [],
        "interleave_accepts": 0, "interleave_declines": 0,
        "interleave_noops": 0,
        "seat_accepts": 0, "trans_accepts": 0, "swap_accepts": 0,
        "fast_miss": 0,
        "seat_E": None, "seat_pen": None, "seat_stair": None,
        "readouts": 0, "mono_swaps": 0, "readout_info": {},
        "bookmark_wall": 0.0, "bookmark_readouts": 0,
        "hier_accepts": 0, "pair_accepts": 0, "tile_accepts": 0,
        "xy_accepts": 0,
        "wave_count": 0, "wave_questions": 0, "wave_early_stop": False,
        "widen_asked": 0, "widen_accepts": 0,
    }
    if not getattr(grid, "typed", False) or not line_pools(grid):
        return _copy(pos0), info
    t0 = _time.perf_counter()

    # s3.118 carried orders: born ONCE from the entry positions by
    # (value, id) — the id's single surviving act. Thereafter the
    # orders are the state and only moves edit them.
    ords: Optional[Dict[int, List[int]]] = None
    rank: Optional[Dict[int, Dict[int, int]]] = None
    if carry:
        ords = {ax: sorted(pos0, key=lambda v: (float(pos0[v][ax]), v))
                for ax in (0, 1)}
        rank = {ax: {v: r for r, v in enumerate(ords[ax])}
                for ax in (0, 1)}

    def _expired() -> bool:
        return deadline is not None and _time.perf_counter() > deadline

    def _readout(p, o=None):
        info["readouts"] += 1
        return pack_project(p, src_adj, grid, kappa=kappa, floor=floor,
                            snap=snap, monotonize=False,
                            project=not plane,
                            orders=((o[0], o[1]) if o is not None
                                    else None))

    def _judge(p, cts, yr=None):
        # plane mode: states live on the ideal plane — pure stair (the
        # brick arrays would index out of bounds there, and capacity
        # is the unbounded pack's invariant, not a price). Windowed
        # mode: the full lexicographic evaluator, reading the SAME
        # orientation book as the state's contacts.
        if plane:
            return stair_energy(p, src_adj, contacts=cts)
        return seat_energy(p, src_adj, grid, yrank=yr)

    pos, rinfo = _readout(pos0, ords)
    if carry:
        contacts = rinfo["_contacts"]
    else:
        contacts = (rinfo.get("_contacts")
                    or _stair_contacts(pos, src_adj))
    e_cur = _judge(pos, contacts, rank[1] if carry else None)
    best_e, best_pos, best_rinfo = e_cur, _copy(pos), rinfo
    best_ords = ({ax: list(ords[ax]) for ax in (0, 1)}
                 if carry else None)
    n = len(pos)

    # s3.122 wave-scheduler state + s3.123 widen register. Dirtiness
    # is per-VARIABLE (ids is the fixed index space for the whole
    # run); cur_spans caches the current state's per-variable stair
    # spans — the ground truth the disturbance diff in _try_adopt runs
    # against. ``last_diff`` (s3.123) is the most recent adoption's
    # realized diff-set — the displaced variables the cross-axis
    # widening carries to the unit's second-axis probe.
    wave = wave and carry
    axis_inner = axis_inner and carry
    widen = widen and axis_inner
    ids_w: List[int] = []
    ixw: Dict[int, int] = {}
    dirty = None
    dirty_next = None
    cur_spans = None
    last_diff: Optional[List[int]] = None
    if wave or widen:
        ids_w = sorted(pos)
        ixw = {v: i for i, v in enumerate(ids_w)}
        _, _sh, _sv = _span_vectors(pos, src_adj, rank[1])
        cur_spans = (_sh, _sv)
    if wave:
        dirty = np.ones(n, dtype=bool)
        dirty_next = np.zeros(n, dtype=bool)

    def _resort_orders(p2):
        # the monotone-values invariant repair (validator, s3.118):
        # a straggler clamp on a bounded readout can break "values
        # non-decreasing along the carried order"; a STABLE re-sort
        # by value alone restores it while preserving the carried
        # within-line order. No-op when nothing was clamped.
        for ax in (0, 1):
            ords[ax] = sorted(ords[ax], key=lambda v: float(p2[v][ax]))
            rank[ax] = {v: r for r, v in enumerate(ords[ax])}

    def _try_adopt(cand, new_ords=None) -> bool:
        """Readout the materialized candidate; adopt per the acceptance
        rule; bookmark. Returns True iff the state changed."""
        nonlocal pos, e_cur, rinfo, contacts, best_e, best_pos, \
            best_rinfo, best_ords, cur_spans, dirty_next, last_diff
        cand2, rinfo2 = _readout(cand, new_ords if carry else None)
        if carry:
            changed = (new_ords != ords) or not _same(cand2, pos)
        else:
            changed = not _same(cand2, pos)
        if not changed:
            # non-carry: the DP's within-line order intent is
            # unrepresentable in positions ((value, id) re-sort) — a
            # no-op, not an accept, or accept-all livelocks on it.
            # Under carry an order-only change IS a state change
            # (contacts move at identical positions), so this fires
            # only for the true identity.
            info["interleave_noops"] += 1
            return False
        if carry:
            cts2 = rinfo2["_contacts"]
            yr2 = {v: r for r, v in enumerate(new_ords[1])}
        else:
            cts2 = (rinfo2.get("_contacts")
                    or _stair_contacts(cand2, src_adj))
            yr2 = None
        e2 = _judge(cand2, cts2, yr2)
        if audit and not (e2 < e_cur - 1e-9):
            info["interleave_declines"] += 1
            return False
        old_contacts = contacts if (wave or widen) else None
        pos, e_cur, rinfo = cand2, e2, rinfo2
        contacts = cts2
        if carry:
            ords[0], ords[1] = list(new_ords[0]), list(new_ords[1])
            rank[0] = {v: r for r, v in enumerate(ords[0])}
            rank[1] = yr2
            if (rinfo2.get("projection_misses", 0)
                    or rinfo2.get("unplaced", 0)):
                _resort_orders(pos)
                contacts = _stair_contacts(pos, src_adj,
                                           yrank=rank[1])
                e_cur = _judge(pos, contacts, rank[1])
        if wave or widen:
            # s3.122 disturbance diff (ground truth): a variable whose
            # span or contacts entry changed in this adoption joins
            # the NEXT wave (s3.122) and/or the widen register
            # (s3.123). Runs after the carry/repair block so the diff
            # reads the post-repair final state.
            _, nh, nv = _span_vectors(pos, src_adj, rank[1])
            moved = (nh != cur_spans[0]) | (nv != cur_spans[1])
            for i, v in enumerate(ids_w):
                if not moved[i] and old_contacts[v] != contacts[v]:
                    moved[i] = True
            if wave:
                dirty_next = dirty_next | moved
            if widen:
                last_diff = [ids_w[i] for i in np.flatnonzero(moved)]
            cur_spans = (nh, nv)
        if e2 < best_e:
            best_e, best_pos, best_rinfo = e2, _copy(pos), rinfo2
            if carry:
                best_ords = {ax: list(ords[ax]) for ax in (0, 1)}
            # when the returned answer was actually found — the
            # work-to-answer metric; later churn is harvestable budget
            info["bookmark_wall"] = round(_time.perf_counter() - t0, 2)
            info["bookmark_readouts"] = info["readouts"]
        return True

    scales: List[int] = []
    s = n // 2
    while s >= 2:
        scales.append(s)
        s //= 2
    scales.append(1)

    # per-edge units (carry mode): the pair {u, v} through the same
    # DP — size-2 re-insertion strictly contains the pairwise
    # exchange (the reversed arm at the two slots), so this subsumes
    # edge_monotonize with an exactly-judged, tie-sound move
    edges: List[Tuple[int, int]] = []
    if carry:
        seen = set()
        for v in sorted(src_adj):
            for u in src_adj[v]:
                if u != v and u in pos and v in pos:
                    e = (min(u, v), max(u, v))
                    if e not in seen:
                        seen.add(e)
                        edges.append(e)

    # a unit re-probed on an UNCHANGED state repeats its outcome
    # exactly (the DP and the readout are deterministic functions of
    # the state), so stamp every state change and skip units whose
    # last fruitless probe saw the current stamp — late passes then
    # cost nothing on quiet regions, which is what lets the schedule
    # actually cycle (s3.114)
    state_ver = 0
    tried: dict = {}

    def _probe(unit, axis, key) -> int:
        """One DP proposal on ``unit`` (any variable set — an order
        interval, a graph-derived group, or an edge pair), adopted per
        the acceptance rule. Returns 1 iff the state changed."""
        nonlocal state_ver
        if tried.get(key) == state_ver:
            info["interleave_noops"] += 1
            return 0
        if not (1 <= len(unit) < n):
            return 0
        if carry:
            order = ords[axis]
        else:
            order = sorted(pos, key=lambda v: (float(pos[v][axis]), v))
        vals = sorted(float(pos[v][axis]) for v in order)
        other = {v: float(pos[v][1 - axis]) for v in pos}
        new_order, _flip = align_reinsert(
            order, set(unit), src_adj, vals, None,
            axis=axis, other=other, contacts=contacts)
        if new_order is None:
            info["interleave_noops"] += 1
            tried[key] = state_ver
            return 0
        cand = _copy(pos)
        for r, v in enumerate(new_order):
            cand[v][axis] = float(vals[r])
        new_ords = None
        if carry:
            new_ords = {ax: (new_order if ax == axis else ords[ax])
                        for ax in (0, 1)}
        if _try_adopt(cand, new_ords):
            info["interleave_accepts"] += 1
            state_ver += 1
            return 1
        tried[key] = state_ver
        return 0

    def _xy_probe(v, key) -> int:
        """One joint two-axis singleton proposal (s3.121): evict ``v``
        from BOTH carried orders, re-insert at the exact optimum over
        all (x-slot, y-slot) pairs — the fold's atom, a 2-D relocation
        whose 1-D halves are individually net-negative. Same memo,
        same adopt path, same judge as every other move."""
        nonlocal state_ver
        if tried.get(key) == state_ver:
            info["interleave_noops"] += 1
            return 0
        vals_x = sorted(float(pos[u][0]) for u in ords[0])
        vals_y = sorted(float(pos[u][1]) for u in ords[1])
        res = xy_reinsert(v, ords[0], ords[1], src_adj,
                          vals_x, vals_y, contacts)
        if res is None:
            info["interleave_noops"] += 1
            tried[key] = state_ver
            return 0
        new_ox, new_oy = res
        cand = _copy(pos)
        for r, u in enumerate(new_ox):
            cand[u][0] = float(vals_x[r])
        for r, u in enumerate(new_oy):
            cand[u][1] = float(vals_y[r])
        if _try_adopt(cand, {0: new_ox, 1: new_oy}):
            info["interleave_accepts"] += 1
            info["xy_accepts"] += 1
            state_ver += 1
            return 1
        tried[key] = state_ver
        return 0

    # s3.123 slot-paired widening state: when the FIRST sweep's probe
    # at slot K is adopted (under ``widen``), the adoption's realized
    # diff is recorded at K; when the SECOND sweep reaches the same
    # slot, its unit widens by that diff — the cross-axis response
    # (an x-squeeze is relieved by y-reordering via contact flips, a
    # y-reorder is completed by x-re-placement) with the sweep
    # structure itself untouched (the per-block adjacency reorder was
    # convicted by its own smoke: crystal +0.99 at the quiet seed).
    # Cleared each pass; the widened ask uses a ("w",)-prefixed memo
    # key so its decline never suppresses a later plain ask.
    ext: dict = {}

    def _tile_delta(members, moved):
        """Frozen-view delta-stair of moving ``members`` to the
        positions in ``moved`` (the judge's own hull arithmetic,
        restricted to affected variables — a screen, not a second
        evaluator)."""
        affected = set(members)
        for v in members:
            for u in src_adj.get(v, []):
                if u in pos:
                    affected.add(u)

        def _spans(v, override):
            h_us, v_us = contacts[v]
            px = override.get(v)
            x0 = px[0] if px is not None else float(pos[v][0])
            y0 = px[1] if px is not None else float(pos[v][1])
            xs_ = [x0]
            for u in h_us:
                pu = override.get(u)
                xs_.append(pu[0] if pu is not None else float(pos[u][0]))
            ys_ = [y0]
            for u in v_us:
                pu = override.get(u)
                ys_.append(pu[1] if pu is not None else float(pos[u][1]))
            return (max(xs_) - min(xs_)) + (max(ys_) - min(ys_))

        d = 0.0
        for v in affected:
            d += _spans(v, moved) - _spans(v, {})
        return d

    def _tile_pass():
        """The 2-D-joint family (s3.119): tiles = grid windows (order
        -interval intersections under the monotone invariant), each
        offered rigid displacements x internal reversals — the fold
        atoms. Screened by _tile_delta; best candidate proposed iff it
        strictly beats the current state in view; adopted per the
        ordinary rule."""
        nonlocal state_ver
        got_any = 0
        ids_arr = sorted(pos)
        X = np.array([float(pos[v][0]) for v in ids_arr])
        Y = np.array([float(pos[v][1]) for v in ids_arr])
        x0, x1 = int(X.min()), int(X.max())
        y0, y1 = int(Y.min()), int(Y.max())
        for h in (8, 4, 2):
            step = max(h // 2, 1)
            for a in range(y0, y1 + 1, step):
                for b in range(x0, x1 + 1, step):
                    if _expired():
                        return got_any
                    key = ("t", h, a, b)
                    if tried.get(key) == state_ver:
                        continue
                    mask = ((Y >= a) & (Y < a + h)
                            & (X >= b) & (X < b + h))
                    members = [ids_arr[i]
                               for i in np.flatnonzero(mask)]
                    if not (2 <= len(members) < n):
                        tried[key] = state_ver
                        continue
                    best_d, best_mv = -1e-9, None
                    for dx, dy in ((h, 0), (-h, 0), (0, h), (0, -h),
                                   (h, h), (h, -h), (-h, h), (-h, -h)):
                        for rx in (False, True):
                            for ry in (False, True):
                                mv = {}
                                ok = True
                                for v in members:
                                    vx = float(pos[v][0])
                                    vy = float(pos[v][1])
                                    if rx:
                                        vx = (2 * b + h - 1) - vx
                                    if ry:
                                        vy = (2 * a + h - 1) - vy
                                    vx += dx
                                    vy += dy
                                    if vx < 0 or vy < 0:
                                        ok = False
                                        break
                                    mv[v] = (vx, vy)
                                if not ok:
                                    continue
                                d = _tile_delta(members, mv)
                                if d < best_d:
                                    best_d, best_mv = d, mv
                    if best_mv is None:
                        tried[key] = state_ver
                        continue
                    cand = _copy(pos)
                    for v, (vx, vy) in best_mv.items():
                        cand[v][0] = vx
                        cand[v][1] = vy
                    new_ords = {
                        ax: sorted(ords[ax],
                                   key=lambda v, _ax=ax:
                                   float(cand[v][_ax]))
                        for ax in (0, 1)}
                    if _try_adopt(cand, new_ords):
                        info["interleave_accepts"] += 1
                        info["tile_accepts"] += 1
                        state_ver += 1
                        got_any += 1
                    else:
                        tried[key] = state_ver
        return got_any

    # s3.122: the wave schedule — the disturbance-driven alternative to
    # the blind pass loop below. Wave 0 asks EXACTLY the blind loop's
    # first pass (full ladder + pairs, coarse-first), so trajectories
    # coincide until the first schedule decision; two measured detours
    # died here: ascending maintenance scales (crystal +0.395 —
    # fine-first on broadly-dirty state, the s3.81 hazard) and a
    # wave-0 leaf floor (crystal +0.368/10, bookmark 3.7s->25.3s —
    # deferring the fine scales shifts the crystal basin;
    # wave_probe.csv round 1). Maintenance waves re-ask any scale,
    # coarse-first, but only blocks containing a variable the previous
    # wave's adoptions actually disturbed (the span/contacts diff in
    # _try_adopt) — fine floods are prevented by dirtiness, not by
    # amputation. Probes read ``dirty`` (frozen for the wave);
    # adoptions write ``dirty_next``; the swap happens at wave end. A
    # COMPLETED wave that disturbs nothing is a fixpoint certificate
    # over the whole move family -> return early, budget to the tail.
    if wave:
        while info["passes"] < _MAX_PASSES and not _expired():
            info["passes"] += 1
            changes = 0
            first = info["passes"] == 1
            # s3.123 axis_inner: per-pass sweep-direction alternation,
            # so neither axis is systematically the recording sweep
            axpair = ((0, 1) if axis_inner and info["passes"] % 2 == 0
                      else (1, 0))
            ext.clear()
            if first and extra_units:
                for li, level in enumerate(reversed(extra_units)):
                    for gi, grp in enumerate(level):
                        for axis in axpair:
                            if _expired():
                                break
                            unit = [v for v in grp if v in pos]
                            wext = (ext.pop(("h", li, gi), None)
                                    if widen and axis != axpair[0]
                                    else None)
                            if wext:
                                info["widen_asked"] += 1
                                got = _probe(
                                    sorted(set(unit) | wext), axis,
                                    ("w", "h", li, gi, axis))
                                if got:
                                    info["widen_accepts"] += 1
                            else:
                                got = _probe(unit, axis,
                                             ("h", li, gi, axis))
                                if (got and widen
                                        and axis == axpair[0]):
                                    ext[("h", li, gi)] = set(
                                        last_diff or ())
                            if got:
                                info["hier_accepts"] += 1
                            changes += got
                        if _expired():
                            break
                    if _expired():
                        break
            if first and tiles:
                changes += _tile_pass()
            for scale in scales:
                if xy and scale == 1:
                    for off in range(n):
                        if _expired():
                            break
                        vv = ords[1][off]
                        if not first and not dirty[ixw[vv]]:
                            continue
                        info["wave_questions"] += 1
                        changes += _xy_probe(vv, ("s", vv))
                    if _expired():
                        break
                    continue
                for axis in axpair:
                    for off in range(0, n, max(scale // 2, 1)):
                        if _expired():
                            break
                        block = ords[axis][off:off + scale]
                        if not first and not any(
                                dirty[ixw[v]] for v in block):
                            continue
                        info["wave_questions"] += 1
                        wext = (ext.pop((scale, off), None)
                                if widen and axis != axpair[0]
                                else None)
                        if wext:
                            info["widen_asked"] += 1
                            got = _probe(
                                sorted(set(block) | wext), axis,
                                ("w", scale, off, axis))
                            if got:
                                info["widen_accepts"] += 1
                        else:
                            got = _probe(block, axis,
                                         (axis, scale, off))
                            if (got and widen
                                    and axis == axpair[0]):
                                ext[(scale, off)] = set(
                                    last_diff or ())
                        changes += got
                    if _expired():
                        break
                if _expired():
                    break
            for ei, (u, w) in enumerate(edges):
                if _expired():
                    break
                if not first and not (dirty[ixw[u]]
                                      or dirty[ixw[w]]):
                    continue
                for axis in axpair:
                    if _expired():
                        break
                    info["wave_questions"] += 1
                    wext = (ext.pop(("e", ei), None)
                            if widen and axis != axpair[0]
                            else None)
                    if wext:
                        info["widen_asked"] += 1
                        got = _probe(sorted({u, w} | wext), axis,
                                     ("w", "e", ei, axis))
                        if got:
                            info["widen_accepts"] += 1
                    else:
                        got = _probe([u, w], axis, ("e", ei, axis))
                        if got and widen and axis == axpair[0]:
                            ext[("e", ei)] = set(last_diff or ())
                    if got:
                        info["pair_accepts"] += 1
                    changes += got
            info["accept_traj"].append(changes)
            info["wave_count"] = info["passes"]
            dirty, dirty_next = dirty_next, np.zeros(n, dtype=bool)
            if not dirty.any():
                if not _expired():
                    info["wave_early_stop"] = True
                break

    while not wave and info["passes"] < _MAX_PASSES and not _expired():
        info["passes"] += 1
        changes = 0
        # s3.123 axis_inner: per-pass sweep-direction alternation
        axpair = ((0, 1) if axis_inner and info["passes"] % 2 == 0
                  else (1, 0))
        ext.clear()
        if extra_units:
            # graph-derived groups (the affinity hierarchy) as EXTRA
            # units, coarsest level first: a scattered similar set is
            # gathered as ONE jointly-judged weave — the move interval
            # accretion cannot express (Max's ER variance hypothesis)
            for li, level in enumerate(reversed(extra_units)):
                for gi, grp in enumerate(level):
                    for axis in axpair:
                        if _expired():
                            break
                        unit = [v for v in grp if v in pos]
                        wext = (ext.pop(("h", li, gi), None)
                                if widen and axis != axpair[0]
                                else None)
                        if wext:
                            info["widen_asked"] += 1
                            got = _probe(sorted(set(unit) | wext),
                                         axis, ("w", "h", li, gi,
                                                axis))
                            if got:
                                info["widen_accepts"] += 1
                        else:
                            got = _probe(unit, axis,
                                         ("h", li, gi, axis))
                            if (got and widen
                                    and axis == axpair[0]):
                                ext[("h", li, gi)] = set(
                                    last_diff or ())
                        if got:
                            info["hier_accepts"] += 1
                        changes += got
                    if _expired():
                        break
                if _expired():
                    break
        if tiles and carry:
            changes += _tile_pass()
        for scale in scales:
            if xy and carry and scale == 1:
                # s3.121: the joint 2-D singleton sweep REPLACES the
                # per-axis scale-1 sweep (subsumption: pinning either
                # coordinate reproduces the per-axis singleton) — the
                # fold's atom at the ladder's fine end, before pairs
                for off in range(n):
                    if _expired():
                        break
                    vv = ords[1][off]
                    changes += _xy_probe(vv, ("s", vv))
                if _expired():
                    break
                continue
            for axis in axpair:
                for off in range(0, n, max(scale // 2, 1)):
                    if _expired():
                        break
                    if carry:
                        order = ords[axis]
                    else:
                        order = sorted(pos, key=lambda v:
                                       (float(pos[v][axis]), v))
                    block = order[off:off + scale]
                    wext = (ext.pop((scale, off), None)
                            if widen and axis != axpair[0]
                            else None)
                    if wext:
                        info["widen_asked"] += 1
                        got = _probe(sorted(set(block) | wext), axis,
                                     ("w", scale, off, axis))
                        if got:
                            info["widen_accepts"] += 1
                    else:
                        got = _probe(block, axis,
                                     (axis, scale, off))
                        if got and widen and axis == axpair[0]:
                            ext[(scale, off)] = set(last_diff or ())
                    changes += got
                if _expired():
                    break
            if _expired():
                break
        if carry:
            # pairs are FINE moves: they run AFTER the interval ladder
            # (coarsest-first, the s3.81 ladder lesson — measured the
            # hard way at s3.118: pairs-first ate turán's whole budget
            # before a single coarse weave ran)
            for ei, (u, w) in enumerate(edges):
                for axis in axpair:
                    if _expired():
                        break
                    wext = (ext.pop(("e", ei), None)
                            if widen and axis != axpair[0]
                            else None)
                    if wext:
                        info["widen_asked"] += 1
                        got = _probe(sorted({u, w} | wext), axis,
                                     ("w", "e", ei, axis))
                        if got:
                            info["widen_accepts"] += 1
                    else:
                        got = _probe([u, w], axis, ("e", ei, axis))
                        if got and widen and axis == axpair[0]:
                            ext[("e", ei)] = set(last_diff or ())
                    if got:
                        info["pair_accepts"] += 1
                    changes += got
                if _expired():
                    break
        if not carry and not _expired():
            mpos, mi = edge_monotonize(pos, src_adj, contacts=contacts)
            if mi["swaps"]:
                info["mono_swaps"] += mi["swaps"]
                if _try_adopt(mpos):
                    changes += 1
                    state_ver += 1
        info["accept_traj"].append(changes)
        if changes == 0:
            break

    info["seat_E"] = best_e
    if plane:
        # pure-stair judge: pen does not exist during plane search —
        # reporting 0 here would fake a feasibility certificate, so
        # the keys stay None (the projection's proj_pen is the real
        # capacity report)
        info["seat_stair"] = best_e
    else:
        pen = int(best_e // _LEX_M)
        info["seat_pen"] = pen
        info["seat_stair"] = best_e - pen * _LEX_M
    info["readout_info"] = best_rinfo
    if carry and best_ords is not None:
        # the bookmark's ORDERS travel with it: the final projection
        # and the converter books must read the returned state's own
        # orientation book, not the last-visited state's (validator,
        # s3.118 — the fresh two-books seam this closes)
        info["_orders"] = (list(best_ords[0]), list(best_ords[1]))
        info["_yrank"] = {v: r for r, v in enumerate(best_ords[1])}
    return best_pos, info
