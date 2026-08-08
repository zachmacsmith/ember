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

Two ball selectors, both producing plain variable sets:
- unit balls: the affinity coarsening hierarchy's member groups (the same
  units the cluster moves use), fine to coarse;
- rect balls: variables whose entire chain falls inside a raster window of
  the tile grid (geometric locality the source-side hierarchy cannot see).
"""

from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional, Set, Tuple

import networkx as nx

from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    is_valid_embedding,
)
from ember_qc.algorithms.factored.coarsen import coarsen
from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.algorithms.factored.trees import sph_tree

RECT_SIZE = 4    # tile window side; raster stride is RECT_SIZE // 2
MAX_BALL = 16    # cost cap: bigger balls near-always reject but cost seconds


def _unit_balls(src_adj: Dict[int, List[int]]) -> List[Tuple[int, ...]]:
    """Member groups of the affinity hierarchy, fine to coarse, as sorted
    tuples of fine ids (size 2..MAX_BALL, never more than half the source)."""
    levels = coarsen(src_adj, units=True)
    cap = min(MAX_BALL, len(src_adj) // 2)
    balls: List[Tuple[int, ...]] = []
    if len(levels) < 2:
        return balls
    mem = {v: [v] for v in levels[0].adj}
    for li in range(1, len(levels)):
        up: Dict[int, List[int]] = {}
        for c, ms in mem.items():
            p = levels[li].parent_of[c]
            up.setdefault(p, []).extend(ms)
        mem = up
        for ms in sorted(map(sorted, mem.values())):
            if 2 <= len(ms) <= cap:
                balls.append(tuple(ms))
    return balls


def _rect_balls(chains: Embedding, grid) -> List[Tuple[int, ...]]:
    """Variables whose entire chain maps into a RECT_SIZE tile window, for
    raster windows at half-window stride. Uses the grid's affine drawing->
    tile map (approximate on typed fabrics, exact enough for a selector;
    works identically on untyped fallback grids)."""
    cap = min(MAX_BALL, len(chains) // 2)
    tile_of = {}
    for k, q in enumerate(grid.qubits):
        t = grid.to_tile(grid.coords[k])
        tile_of[q] = (int(min(max(round(t[0]), 0), grid.W - 1)),
                      int(min(max(round(t[1]), 0), grid.H - 1)))
    span = {}
    for v, c in chains.items():
        ts = [tile_of[q] for q in c if q in tile_of]
        if ts:
            xs = [t[0] for t in ts]
            ys = [t[1] for t in ts]
            span[v] = (min(xs), max(xs), min(ys), max(ys))
    step = max(RECT_SIZE // 2, 1)
    balls: List[Tuple[int, ...]] = []
    for y0 in range(0, max(grid.H - RECT_SIZE, 0) + 1, step):
        for x0 in range(0, max(grid.W - RECT_SIZE, 0) + 1, step):
            x1, y1 = x0 + RECT_SIZE - 1, y0 + RECT_SIZE - 1
            ms = sorted(v for v, (a, b, c0, d) in span.items()
                        if a >= x0 and b <= x1 and c0 >= y0 and d <= y1)
            if 2 <= len(ms) <= cap:
                balls.append(tuple(ms))
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
                  deadline: Optional[float]) -> Optional[Embedding]:
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
                         require_all_neighbors=True)
        if not chain:
            return None
        local[v] = chain
        rebuilt_used.update(chain)
        out[v] = chain
        todo.discard(v)
    return out


def ball_polish(chains: Embedding, source_graph: nx.Graph,
                target_graph: nx.Graph, *,
                deadline: Optional[float] = None,
                adj: Optional[Adjacency] = None,
                grid=None) -> Tuple[Embedding, dict]:
    """Improve a finished legal embedding by ball eviction/re-embedding.

    Sweeps a fixed, deterministic ball list (unit balls fine->coarse, then
    rect balls in raster order) until a full sweep accepts nothing or the
    deadline passes. Returns ``(embedding, info)``; on invalid input the
    input is returned unchanged with ``info["invalid_input"] = True``.
    """
    t0 = time.perf_counter()
    work: Embedding = {int(v): [int(q) for q in c] for v, c in chains.items()}
    info = {"tried": 0, "accepted": 0, "sweeps": 0,
            "unit_balls": 0, "rect_balls": 0, "wall": 0.0}
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
        grid = TileGrid(target_graph, pos, fallback_bins=_auto_bins(len(pos)))

    units = [_trim_ball(S, src_adj) for S in _unit_balls(src_adj)]
    rects = [_trim_ball(S, src_adj) for S in _rect_balls(work, grid)]
    seen: Set[Tuple[int, ...]] = set()
    balls: List[Tuple[int, ...]] = []
    for S in units + rects:
        if S and S not in seen:
            seen.add(S)
            balls.append(S)
    info["unit_balls"] = sum(1 for S in units if S)
    info["rect_balls"] = sum(1 for S in rects if S)

    visits = [0]
    out_of_time = False
    while not out_of_time:
        info["sweeps"] += 1
        any_accept = False
        for S in balls:
            if deadline is not None and time.perf_counter() > deadline:
                out_of_time = True
                break
            info["tried"] += 1
            incumbent = sum(len(work[v]) for v in S)
            candidate = _rebuild_ball(S, work, src_adj, adj, visits, deadline)
            if candidate is None:
                continue
            trial = dict(work)
            trial.update(candidate)
            trial = spur_prune(trial, src_adj, adj, deadline=deadline, only=S)
            if sum(len(trial[v]) for v in S) < incumbent:
                work = trial
                any_accept = True
                info["accepted"] += 1
        if not any_accept:
            break

    if not is_valid_embedding(work, source_graph, target_graph, adj=adj):
        # paranoia guard: a broken move can never corrupt a legal result
        work = {int(v): [int(q) for q in c] for v, c in chains.items()}
        info["guard_reverted"] = True
    info["wall"] = time.perf_counter() - t0
    return work, info
