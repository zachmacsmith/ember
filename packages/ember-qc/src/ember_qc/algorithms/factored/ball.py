"""Ball polish — composite chain re-embedding on a finished embedding.

The move minorminer's one-chain-at-a-time shortener cannot make: evict the
WHOLE chains of a small set of source variables (a "ball"), re-embed them
jointly against the frozen remaining chains, and accept the composite iff
the total real chain length strictly decreases. Tearing one chain leaves a
chain-shaped hole that refills in its own image; tearing a ball leaves a
region whose interior can re-crystallize.

Design rules (2026-08-08 discussion):
- Whole-chain eviction only — no partial chains, no split-chain machinery.
  Chains outside the ball are frozen background: their qubits are simply
  forbidden fabric, and edges into them are attachment targets.
- The judge is reality: qubit counts of the actual rebuilt chains, with the
  validity verifier as backstop. No proxy energy exists anywhere in the
  loop, so the "judging on fictions" defect class is structurally absent.
- Strict descent, deterministic sweep, no acceptance schedules. Reject is
  the only failure path. Termination without a deadline is guaranteed: the
  integer total length strictly decreases on every accept.
- Fabric-agnostic by construction: nothing here needs junction completeness
  or courses — the first mechanism that runs on Pegasus ungated.

Ball selector (v3): one question per chain, from its obligation hull,
regenerated at the start of every pass. The anchor chain's hull is the
bounding rectangle (in tile space) of its own footprint tiles extended,
per source neighbour, to the nearest line the neighbour's runs occupy on
each axis; the ball is the anchor plus every chain with a footprint tile
inside that rectangle. No inflation, no floor, no cap, no windows — the
question set shrinks and moves as the embedding improves.
"""

from __future__ import annotations

import math
import random
import time
from typing import Dict, Iterable, List, Optional, Set, Tuple

import networkx as nx

from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    chain_connected,
    is_valid_embedding,
)
from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.algorithms.factored.trees import sph_tree


def _hull_balls(work: Embedding, src_adj: Dict[int, List[int]],
                grid, rev) -> List[Tuple[int, ...]]:
    """One question per chain: its obligation hull, as a ball.

    ``rev`` is the qubit -> (orientation, line, sub, pos) map derived from
    ``grid.wire_map``. Per anchor chain C the hull is the bounding
    rectangle of C's footprint tiles, extended per source neighbour u to
    the nearest line u's runs occupy on each axis: the x-interval grows to
    include the nearest col of u's v-runs (if any), the y-interval to the
    nearest row of u's h-runs (if any); "nearest" is measured from C's
    footprint interval on that axis (distance 0 if inside; ties toward
    the lower line). The ball is the anchor plus every other chain with a
    footprint tile inside the hull (inclusive). Balls of size < 2 are
    skipped; identical tuples are deduped keeping the first occurrence in
    ascending anchor order. Untyped grids (empty rev) yield no balls.
    """
    tiles: Dict[int, Set[Tuple[int, int]]] = {}
    cols: Dict[int, List[int]] = {}
    rows: Dict[int, List[int]] = {}
    for v, c in work.items():
        ts: Set[Tuple[int, int]] = set()
        cs: Set[int] = set()
        rs: Set[int] = set()
        for q in c:
            k = rev.get(q)
            if k is None:
                continue
            o, ln, _s, p = k
            if o == 1:
                ts.add((p, ln))
                rs.add(ln)
            else:
                ts.add((ln, p))
                cs.add(ln)
        if ts:
            tiles[v] = ts
        cols[v] = sorted(cs)
        rows[v] = sorted(rs)

    def nearest(lines: List[int], lo: int, hi: int) -> int:
        return min(lines, key=lambda ln: (0 if lo <= ln <= hi
                                          else min(abs(ln - lo),
                                                   abs(ln - hi)), ln))

    seen: Set[Tuple[int, ...]] = set()
    balls: List[Tuple[int, ...]] = []
    for v in sorted(work):
        if not src_adj.get(v) or v not in tiles:
            continue
        fx = [t[0] for t in tiles[v]]
        fy = [t[1] for t in tiles[v]]
        fx0, fx1 = min(fx), max(fx)
        fy0, fy1 = min(fy), max(fy)
        xmin, xmax, ymin, ymax = fx0, fx1, fy0, fy1
        for u in src_adj[v]:
            if u == v or not work.get(u):
                continue
            cu = cols.get(u)
            if cu:
                t = nearest(cu, fx0, fx1)
                xmin, xmax = min(xmin, t), max(xmax, t)
            ru = rows.get(u)
            if ru:
                t = nearest(ru, fy0, fy1)
                ymin, ymax = min(ymin, t), max(ymax, t)
        members = {v}
        for w, ts in tiles.items():
            if w != v and any(xmin <= x <= xmax and ymin <= y <= ymax
                              for (x, y) in ts):
                members.add(w)
        ball = tuple(sorted(members))
        if len(ball) < 2 or ball in seen:
            continue
        seen.add(ball)
        balls.append(ball)
    return balls


def _trim_ball(S: Iterable[int],
               src_adj: Dict[int, List[int]]) -> Tuple[int, ...]:
    """Reduce S to the members a rebuild can actually construct: drop
    degree-0 vertices, then keep only the components of S's induced source
    subgraph that touch a neighbour OUTSIDE S (a component with no frozen
    contact has no attachment point and would reject forever)."""
    inside = {v for v in S if src_adj.get(v)}
    keep: Set[int] = set()
    seen: Set[int] = set()
    for start in sorted(inside):
        if start in seen:
            continue
        comp = {start}
        stack = [start]
        while stack:
            v = stack.pop()
            for u in src_adj.get(v, []):
                if u in inside and u not in comp:
                    comp.add(u)
                    stack.append(u)
        seen |= comp
        if any(u not in inside for v in comp for u in src_adj.get(v, [])):
            keep |= comp
    return tuple(sorted(keep)) if len(keep) >= 2 else ()


def _rebuild_ball(S: Tuple[int, ...], work: Embedding,
                  src_adj: Dict[int, List[int]], adj: Adjacency,
                  visits: List[int],
                  deadline: Optional[float],
                  rng=None) -> Optional[Embedding]:
    """Jointly rebuild the chains of S against the frozen rest. Returns the
    new {v: chain} for S, or None (reject) on any failure or deadline."""
    frozen_used: Set[int] = set()
    for u, c in work.items():
        if u not in S:
            frozen_used.update(c)
    local = {u: c for u, c in work.items() if u not in S}
    rebuilt_used: Set[int] = set()
    out: Embedding = {}
    todo = set(S)
    while todo:
        if deadline is not None and time.perf_counter() > deadline:
            return None
        # dynamic greedy order: most already-placed neighbours first —
        # after _trim_ball every pick has at least one placed neighbour
        v = max(sorted(todo),
                key=lambda x: (sum(1 for u in src_adj.get(x, [])
                                   if u in local),
                               len(src_adj.get(x, [])), -x))
        placed = [u for u in src_adj.get(v, []) if u in local]
        chain = sph_tree(v, placed, local, adj, {}, visits,
                         forbidden_extra=frozen_used | rebuilt_used,
                         require_all_neighbors=True, rng=rng)
        if not chain:
            return None
        local[v] = chain
        rebuilt_used.update(chain)
        out[v] = chain
        todo.discard(v)
    return out


def _audit_claim(grid, claimed, orientation: int, lines, lo: float,
                 hi: float, cross_lines,
                 rng=None) -> Optional[Tuple[int, int, List[int], int]]:
    """Lane audit (s3.85): selection by MEASURED cost over the bar
    family — minorminer's audition, O(candidate lanes) arithmetic.

    A candidate is one physical lane: ``(orientation, line, s)`` in
    ``grid.wire_map`` for ``line`` in ``lines``. Its run must cover the
    interval ``[lo, hi]`` in tile-along positions: the PRESENT keys of
    the run in that range (stride-aligned lanes hold one parity of p —
    absent keys are not gaps). Infeasible if there are no present
    positions, any present qubit is already ``claimed``, or the present
    positions do not form a contiguous stride chain (a mid-run
    claimed/dead qubit breaks the run). Cost = qubits to claim +
    parity_miss, where parity_miss counts crossing targets in
    ``cross_lines`` the lane cannot physically couple (p* = c if c and
    s share parity else c-1 must be a key of the run; stride-1 fabrics
    have no course parity — parity_miss = 0, the verifier judges).

    Returns the best ``(line, s, qubits, cost)`` minimizing
    ``(cost, line, s)``; with ``rng``, uniform among the exact
    minimum-cost candidates. ``None`` if no lane is feasible."""
    lo_i, hi_i = int(math.floor(lo)), int(math.ceil(hi))
    cands: List[Tuple[int, int, int, List[int]]] = []
    for line in sorted(set(lines)):
        subs = sorted({s for (o_, ln, s) in grid.wire_map
                       if o_ == orientation and ln == line})
        for s in subs:
            run = grid.wire_map[(orientation, line, s)]
            present = [p for p in range(lo_i, hi_i + 1) if p in run]
            if not present:
                continue
            if any(run[p] in claimed for p in present):
                continue
            if any(b - a != grid.stride
                   for a, b in zip(present, present[1:])):
                continue
            if grid.stride > 1:
                parity_miss = sum(
                    1 for c in cross_lines
                    if (c if c % 2 == s % 2 else c - 1) not in run)
            else:
                parity_miss = 0
            cost = len(present) + parity_miss
            cands.append((cost, line, s, [run[p] for p in present]))
    if not cands:
        return None
    if rng is None:
        cost, line, s, qs = min(cands, key=lambda t: t[:3])
    else:
        best_cost = min(t[0] for t in cands)
        ties = sorted((t for t in cands if t[0] == best_cost),
                      key=lambda t: t[:3])
        cost, line, s, qs = ties[rng.randrange(len(ties))]
    return line, s, qs, cost


def _rebuild_ball_bars(S: Tuple[int, ...], work: Embedding,
                       src_adj: Dict[int, List[int]], adj: Adjacency,
                       grid,
                       deadline: Optional[float],
                       rng=None, rev=None) -> Optional[Embedding]:
    """Bar-based joint rebuild (v5: the lane audit). The same
    constructor family as the pipeline — member positions from frozen
    obligations, the stair contact rule, stride-gated completion,
    scoped verify — but member placement is SELECTION BY MEASURED COST:
    every candidate lane over the member's obligation hull is
    auditioned via ``_audit_claim`` and the cheapest feasible run is
    claimed, in the dynamic greedy order. Reject is the only failure
    path."""
    import numpy as np
    from ember_qc.algorithms.factored.field import (
        _stair_contacts, complete_seeds)
    if deadline is not None and time.perf_counter() > deadline:
        return None
    if not grid.wire_map:
        return None  # untyped grid: no bar picture
    Sset = set(S)
    claimed0: Set[int] = set()
    for u, c in work.items():
        if u not in Sset:
            claimed0.update(c)
    if rev is None:
        rev = {}
        for (o_, ln, s), run in grid.wire_map.items():
            for p, q in run.items():
                rev[q] = (o_, ln, s, p)

    # frozen neighbours: which lines their runs occupy + pseudo-position
    frozen_nbrs = sorted({u for v in S for u in src_adj.get(v, [])
                          if u not in Sset and u in work})
    cols: Dict[int, List[int]] = {}
    rows: Dict[int, List[int]] = {}
    fpos: Dict[int, "np.ndarray"] = {}
    for u in frozen_nbrs:
        cs, rs, pts = [], [], []
        for q in work[u]:
            k = rev.get(q)
            if k is None:
                continue
            o_, ln, _s, p = k
            if o_ == 1:
                rs.append(ln)
                pts.append((p, ln))
            else:
                cs.append(ln)
                pts.append((ln, p))
        cols[u] = sorted(set(cs))
        rows[u] = sorted(set(rs))
        if pts:
            xs = sorted(x for x, _ in pts)
            ys = sorted(y for _, y in pts)
            fpos[u] = np.array([float(xs[(len(xs) - 1) // 2]),
                                float(ys[(len(ys) - 1) // 2])])

    # member positions: deterministic fixed-point median sweep (trim
    # guarantees every component touches a positioned frozen neighbour)
    pos: Dict[int, "np.ndarray"] = dict(fpos)
    todo = set(S)
    while todo:
        progress = False
        for v in sorted(todo):
            nb = [pos[u] for u in src_adj.get(v, []) if u in pos]
            if not nb:
                continue
            xs = sorted(float(p[0]) for p in nb)
            ys = sorted(float(p[1]) for p in nb)
            pos[v] = np.array([float(round(xs[(len(xs) - 1) // 2])),
                               float(round(ys[(len(ys) - 1) // 2]))])
            todo.discard(v)
            progress = True
        if not progress:
            return None

    contacts = _stair_contacts(pos, src_adj)

    # audit books per member: obligation hulls of own position, member
    # contacts, and each frozen contact's nearest occupied line;
    # orientation flips when the frozen side owns no run of the
    # required orientation. The h-run's interval is the x-hull, its
    # candidate LINES are every integer row of the y-hull, and its
    # crossing targets are the hull's integer x-targets (own position
    # term excluded); the v-run is symmetric.
    books: Dict[int, tuple] = {}
    for v in sorted(S):
        h_us, v_us = contacts[v]
        h_list, v_list = [], []
        for u in h_us:
            (h_list if (u in Sset or cols.get(u)) else v_list).append(u)
        for u in v_us:
            (v_list if (u in Sset or rows.get(u)) else h_list).append(u)
        x_v, y_v = float(pos[v][0]), float(pos[v][1])
        hx, vy = [x_v], [y_v]
        for u in h_list:
            if u in Sset:
                hx.append(float(pos[u][0]))
            else:
                cs = cols.get(u)
                if not cs:
                    return None
                hx.append(float(min(cs, key=lambda c: (abs(c - x_v), c))))
        for u in v_list:
            if u in Sset:
                vy.append(float(pos[u][1]))
            else:
                rs = rows.get(u)
                if not rs:
                    return None
                vy.append(float(min(rs, key=lambda r: (abs(r - y_v), r))))
        need_h = bool(h_list) or max(hx) - min(hx) > 0
        need_v = bool(v_list) or max(vy) - min(vy) > 0
        h_rows = range(int(math.floor(min(vy))),
                       int(math.ceil(max(vy))) + 1)
        v_cols = range(int(math.floor(min(hx))),
                       int(math.ceil(max(hx))) + 1)
        h_cross = [int(round(x)) for x in hx[1:]]
        v_cross = [int(round(y)) for y in vy[1:]]
        books[v] = (need_h, need_v, (min(hx), max(hx)), (min(vy), max(vy)),
                    h_rows, v_cols, h_cross, v_cross)

    # member placement by measured cost: audition every candidate lane
    # over the hull, claim the cheapest feasible run, in the dynamic
    # greedy order (most already-placed neighbours first)
    claimed = set(claimed0)
    new_chains: Embedding = {v: [] for v in S}
    placed = set(work) - Sset
    todo = set(S)
    while todo:
        v = max(sorted(todo),
                key=lambda x: (sum(1 for u in src_adj.get(x, [])
                                   if u in placed),
                               len(src_adj.get(x, [])), -x))
        need_h, need_v, h_iv, v_iv, h_rows, v_cols, h_cross, v_cross \
            = books[v]
        if need_h:
            got = _audit_claim(grid, claimed, 1, h_rows, h_iv[0], h_iv[1],
                               h_cross, rng=rng)
            if got is None:
                return None
            claimed.update(got[2])
            new_chains[v].extend(got[2])
        if need_v:
            got = _audit_claim(grid, claimed, 0, v_cols, v_iv[0], v_iv[1],
                               v_cross, rng=rng)
            if got is None:
                return None
            claimed.update(got[2])
            new_chains[v].extend(got[2])
        if not new_chains[v]:
            return None
        placed.add(v)
        todo.discard(v)

    full = {u: list(c) for u, c in work.items() if u not in Sset}
    full.update({v: list(c) for v, c in new_chains.items()})
    if grid.stride > 1:
        # completion's parity arithmetic is a course-resolved-Zephyr
        # fact; on stride-1 the verifier below is the whole judge
        full, _cinfo = complete_seeds(grid, full, src_adj, adj, only=Sset)

    for v in sorted(S):
        c = full.get(v)
        if not c or not chain_connected(c, adj):
            return None
        for u in src_adj.get(v, []):
            uset = (set(full[u]) if u in Sset
                    else set(work[u]) if u in work else None)
            if uset is None:
                continue
            if not any(nb in uset for q in c for nb in adj.get(q, ())):
                return None
    return {v: sorted(int(q) for q in full[v]) for v in S}


def ball_polish(chains: Embedding, source_graph: nx.Graph,
                target_graph: nx.Graph, *,
                deadline: Optional[float] = None,
                adj: Optional[Adjacency] = None,
                grid=None,
                max_sweeps: Optional[int] = None,
                rng_seed: Optional[int] = None) -> Tuple[Embedding, dict]:
    """Improve a finished legal embedding by ball eviction/re-embedding.

    Sweeps one question per chain — its obligation hull ball, regenerated
    at the start of every pass from the current embedding — until a full
    sweep accepts nothing or the deadline passes. Returns ``(embedding,
    info)``; on invalid input the input is returned unchanged with
    ``info["invalid_input"] = True``.

    Rebuild: bars first (the pipeline's constructor family — straight
    arm runs selected by measured cost over candidate lanes,
    stride-gated completion), the router (the
    sph_tree Steiner build) when bars reject. Untyped grids (no
    wire_map) have no hull picture and yield no questions: ball_polish
    is a no-op there.
    """
    t0 = time.perf_counter()
    work: Embedding = {int(v): [int(q) for q in c] for v, c in chains.items()}
    info = {"tried": 0, "accepted": 0, "sweeps": 0,
            "questions": 0, "wall": 0.0}
    if adj is None:
        adj = build_adjacency(target_graph)
    if not work or not is_valid_embedding(work, source_graph, target_graph,
                                          adj=adj):
        info["invalid_input"] = True
        info["wall"] = time.perf_counter() - t0
        return work, info
    src_adj = {int(v): sorted(int(u) for u in source_graph.neighbors(v))
               for v in source_graph}

    if grid is None:
        from ember_qc.algorithms.factored.field import TileGrid
        from ember_qc.algorithms.factored.placement import (
            _auto_bins, target_layout)
        pos = target_layout(target_graph)
        # courses=True: the pipeline's wire representation (the folded
        # grid was a live bug — wrong sub-lanes on Zephyr)
        grid = TileGrid(target_graph, pos,
                        fallback_bins=_auto_bins(len(pos)), courses=True)
    # shared qubit -> (orientation, line, sub, pos) map: hull questions
    # and the bar rebuild read the same frozen book
    rev: Dict[int, Tuple[int, int, int, int]] = {}
    for (o_, ln, s), run in grid.wire_map.items():
        for p, q in run.items():
            rev[q] = (o_, ln, s, p)

    visits = [0]
    rng = random.Random(rng_seed) if rng_seed is not None else None
    dry = 0
    out_of_time = False
    while not out_of_time:
        if max_sweeps is not None and info["sweeps"] >= max_sweeps:
            break
        info["sweeps"] += 1
        any_accept = False
        # regenerate the questions from the CURRENT embedding: the hulls
        # shrink and move as chains improve
        trimmed = [_trim_ball(S, src_adj)
                   for S in _hull_balls(work, src_adj, grid, rev)]
        seen: Set[Tuple[int, ...]] = set()
        balls: List[Tuple[int, ...]] = []
        for S in trimmed:
            if S and S not in seen:
                seen.add(S)
                balls.append(S)
        info["questions"] = len(balls)
        sweep = list(balls)
        if rng is not None:
            rng.shuffle(sweep)
        for S in sweep:
            if deadline is not None and time.perf_counter() > deadline:
                out_of_time = True
                break
            info["tried"] += 1
            incumbent = sum(len(work[v]) for v in S)
            candidate = None
            if grid.wire_map:
                candidate = _rebuild_ball_bars(S, work, src_adj, adj,
                                               grid, deadline,
                                               rng=rng, rev=rev)
                if candidate is not None:
                    info["bar_rebuilds"] = info.get("bar_rebuilds", 0) + 1
            if candidate is None:
                candidate = _rebuild_ball(S, work, src_adj, adj, visits,
                                          deadline, rng=rng)
            if candidate is None:
                continue
            trial = dict(work)
            trial.update(candidate)
            trial = spur_prune(trial, src_adj, adj, deadline=deadline, only=S)
            if sum(len(trial[v]) for v in S) < incumbent:
                work = trial
                any_accept = True
                info["accepted"] += 1
        if any_accept:
            dry = 0
        else:
            dry += 1
            # under re-rolled ties one dry pass does not prove dryness
            if dry >= (2 if rng is not None else 1):
                break

    if not is_valid_embedding(work, source_graph, target_graph, adj=adj):
        # paranoia guard: a broken move can never corrupt a legal result
        work = {int(v): [int(q) for q in c] for v, c in chains.items()}
        info["guard_reverted"] = True
    info["wall"] = time.perf_counter() - t0
    return work, info
