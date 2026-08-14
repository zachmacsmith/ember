"""Crossfinder — iterated rip-and-replace at cross granularity (s3.90).

The paradigm hypothesis (discussed with Max, 2026-08-13): every move that
ever won a measurement — insertion, gather, the orientation bit, the
fold, ball, minorminer's grind — is one move in disguise: evict a
subset, re-place it against the frozen complement. This module builds
that move as THE algorithm, standalone, judged on routed reality
(no proxy energy anywhere, the s3.75 design), leaving the attraction
pipeline untouched as the control.

The operator is minorminer's own dominant-phase loop (mm-internals §3:
rip one chain, candidate roots from the intersection of BFS balls
around neighbour chains, exhaustive audition) with three changes:

- chains are CROSSES — one h-run and one v-run meeting at an anchor
  tile — the fabric's native shape (busclique-optimal dense);
- the audition is exact interval arithmetic over ~W×H anchor tiles
  (cheap), then realization of only the ranked few via the frozen-aware
  lane audit — attacking mm's measured 90% slice (the audition is their
  expensive part, §3.17);
- eviction sets of any size (``rip_windows``) — the coordinated move mm
  structurally lacks, and the switch that measures whether template-ish
  big moves add anything over the pure local operator.

Inherited shipped-mm lessons (mm-internals): coverage deficit and
overload dominate length lexicographically; seeded randomization does
feasibility work (a deterministic replica deadlocks); no history term
(inert next to randomness).
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, fields, replace
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    chain_connected,
    is_valid_embedding,
)
from ember_qc.algorithms.factored.ball import (
    _audit_claim,
    _hull_balls,
    _trim_ball,
)
from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.algorithms.factored.trees import sph_tree


@dataclass(frozen=True)
class CrossConfig:
    init: str = "shuffle"      # "shuffle" (seeded BFS) | "spectral"
                               # (same order, spectral anchor hints; mm
                               # lesson: legal-stage quality carries no
                               # information — measure, don't assume)
    rip_windows: bool = False  # THE experiment: coordinated evictions
                               # (obligation-hull windows re-placed
                               # member-by-member with the operator) on
                               # top of single-variable rips
    tail: str = "none"         # "none" | "ball" — default none: the
                               # probe measures the operator, not a tail
    realize_cap: int = 24      # ranked anchors realized per placement
                               # before the sph_tree fallback


def _audit_claim_evict(grid, claimed, owner, orientation: int, line: int,
                       lo: float, hi: float, cross_lines, rng=None,
                       max_evict: int = 2
                       ) -> Optional[Tuple[List[int], Set[int], int]]:
    """The lane audit with eviction pricing — mm's lexicographic
    occupancy rule translated to exclusive claims: a candidate lane's
    cost is (#owners whose qubits block it, qubits + parity_miss), so a
    free lane is always preferred (identical to ``_audit_claim`` then),
    and otherwise the lane evicting the fewest chains wins. Returns
    (qubits, owners_to_evict, cost) or None (no lane with <= max_evict
    blocking owners, or a blocked qubit has no known owner — dead
    fabric is never evictable)."""
    lo_i, hi_i = int(math.floor(lo)), int(math.ceil(hi))
    cands = []
    for s in sorted({s_ for (o_, ln_, s_) in grid.wire_map
                     if o_ == orientation and ln_ == line}):
        run = grid.wire_map[(orientation, line, s)]
        present = [p for p in range(lo_i, hi_i + 1) if p in run]
        if not present:
            continue
        if any(b - a != grid.stride
               for a, b in zip(present, present[1:])):
            continue
        owners: Set[int] = set()
        dead = False
        for p in present:
            q = run[p]
            if q in claimed:
                u = owner.get(q)
                if u is None:
                    dead = True
                    break
                owners.add(u)
        if dead or len(owners) > max_evict:
            continue
        if grid.stride > 1:
            parity_miss = sum(
                1 for cl in cross_lines
                if (cl if cl % 2 == s % 2 else cl - 1) not in run)
        else:
            parity_miss = 0
        cands.append((len(owners), len(present) + parity_miss, s,
                      [run[p] for p in present], owners))
    if not cands:
        return None
    if rng is None:
        n_ev, cost, _s, qs, owners = min(cands, key=lambda t: t[:3])
    else:
        best = min(t[:2] for t in cands)
        ties = sorted((t for t in cands if t[:2] == best),
                      key=lambda t: t[:3])
        n_ev, cost, _s, qs, owners = ties[rng.randrange(len(ties))]
    return qs, owners, n_ev * 10000 + cost


def _runs_of(chain: List[int], rev) -> Tuple[List[Tuple[int, int, int]],
                                             List[Tuple[int, int, int]]]:
    """A chain's physical runs: (h_runs, v_runs) where an h_run is
    (row_line, p_lo, p_hi) over column positions and a v_run is
    (col_line, p_lo, p_hi) over row positions."""
    by_lane: Dict[Tuple[int, int, int], List[int]] = {}
    for q in chain:
        k = rev.get(q)
        if k is None:
            continue
        o, ln, s, p = k
        by_lane.setdefault((o, ln, s), []).append(p)
    h_runs: List[Tuple[int, int, int]] = []
    v_runs: List[Tuple[int, int, int]] = []
    for (o, ln, _s), ps in by_lane.items():
        ps.sort()
        (h_runs if o == 1 else v_runs).append((ln, ps[0], ps[-1]))
    return h_runs, v_runs


def _place_cross(v: int, work: Embedding, src_adj, adj, grid, rev,
                 rng, *, allow_deficit: bool, incumbent: Optional[int],
                 realize_cap: int, deadline: Optional[float],
                 hints=None, visits=None,
                 diag: Optional[dict] = None,
                 evict_plan_out: Optional[List[Set[int]]] = None,
                 window: int = 0) -> Optional[List[int]]:
    """THE move: place v's cross exactly-best against the frozen rest.

    v must already be evicted from ``work``. Scores every anchor tile
    (r, c) by exact interval arithmetic — per placed neighbour u, the
    h-arm covers u iff some v-run of u spans row r (reach = extend the
    h-hull to that run's column; nearest run wins), symmetrically for
    the v-arm; neither side available = a coverage deficit. Anchor cost
    is lexicographic (deficits, hull length) — mm's shipped pricing
    shape. Ranked anchors (seeded tie-shuffle) are then REALIZED via
    the frozen-aware lane audit + scoped completion + scoped verify;
    the first realization that beats ``incumbent`` (or any realization
    when ``incumbent`` is None) wins. Falls back to the sph_tree
    Steiner build through free fabric when no anchor realizes (ball
    measured bars+fallback beating either pure arm, s3.77). Returns
    the new chain or None.
    """
    from ember_qc.algorithms.factored.field import complete_seeds

    W, H = grid.W, grid.H
    placed_nbrs = [u for u in src_adj.get(v, []) if work.get(u)]
    claimed: Set[int] = set()
    for u, c in work.items():
        claimed.update(c)

    # neighbour run books
    nb_v_runs: Dict[int, List[Tuple[int, int, int]]] = {}
    nb_h_runs: Dict[int, List[Tuple[int, int, int]]] = {}
    for u in placed_nbrs:
        h_runs, v_runs = _runs_of(work[u], rev)
        nb_h_runs[u] = h_runs
        nb_v_runs[u] = v_runs

    hint = hints.get(v) if hints else None
    owner_map: Optional[Dict[int, int]] = None
    if evict_plan_out is not None:
        owner_map = {}
        for u, cc in work.items():
            for q in cc:
                owner_map[q] = u

    # ---- stage 1: score every anchor by interval arithmetic ----
    # ``window`` > 0 (the polish use-case): restrict anchors to the
    # hull of the neighbours' reachable lines +/- window — mm's
    # ball-intersection trick as a pure speedup (a full 576-anchor
    # Python scan cost ~80 ms/question and starved the singles pass)
    if window > 0 and placed_nbrs:
        rset: Set[int] = set()
        cset: Set[int] = set()
        for u in placed_nbrs:
            for (row, p0, p1) in nb_h_runs.get(u, ()):
                rset.add(row)
                cset.update((p0, p1))
            for (col, p0, p1) in nb_v_runs.get(u, ()):
                cset.add(col)
                rset.update((p0, p1))
        r_range = range(max(0, min(rset) - window),
                        min(H - 1, max(rset) + window) + 1)
        c_range = range(max(0, min(cset) - window),
                        min(W - 1, max(cset) + window) + 1)
    else:
        r_range = range(H)
        c_range = range(W)
    scored: List[Tuple[int, float, float, int, int]] = []
    for r in r_range:
        for c in c_range:
            deficit = 0
            x_lo = x_hi = float(c)
            y_lo = y_hi = float(r)
            for u in placed_nbrs:
                best: Optional[Tuple[float, int, int]] = None
                for (col, p0, p1) in nb_v_runs.get(u, ()):
                    if p0 <= r <= p1:
                        d = abs(col - c)
                        if best is None or d < best[0]:
                            best = (d, 1, col)
                for (row, p0, p1) in nb_h_runs.get(u, ()):
                    if p0 <= c <= p1:
                        d = abs(row - r)
                        if best is None or d < best[0]:
                            best = (d, 0, row)
                if best is None:
                    deficit += 1
                elif best[1] == 1:
                    x_lo = min(x_lo, float(best[2]))
                    x_hi = max(x_hi, float(best[2]))
                else:
                    y_lo = min(y_lo, float(best[2]))
                    y_hi = max(y_hi, float(best[2]))
            length = (x_hi - x_lo) + (y_hi - y_lo)
            tie = (abs(hint[0] - c) + abs(hint[1] - r)) if hint is not None \
                else 0.0
            scored.append((deficit, length, tie, r, c))
    if not scored:
        return None
    if not allow_deficit:
        feasible = [t for t in scored if t[0] == 0]
        if feasible:
            scored = feasible
    scored.sort(key=lambda t: (t[0], t[1], t[2]))
    # seeded shuffle within exact (deficit, length) ties — feasibility
    # randomness, the mm lesson
    i = 0
    shuffled: List[Tuple[int, float, float, int, int]] = []
    while i < len(scored):
        j = i
        while (j < len(scored)
               and scored[j][:2] == scored[i][:2]):
            j += 1
        group = scored[i:j]
        if rng is not None and len(group) > 1:
            rng.shuffle(group)
        shuffled.extend(group)
        i = j
    scored = shuffled

    # ---- stage 2: realize down the ranking ----
    attempts = 0
    bad_h_lines: Set[int] = set()
    bad_v_lines: Set[int] = set()
    for deficit, _length, _tie, r, c in scored:
        if attempts >= realize_cap:
            break
        if deadline is not None and time.perf_counter() > deadline:
            return None
        # a line that already failed its audit this placement fails
        # again for near-identical intervals — skip without spending
        # the cap, so the ranked scan escapes a crowded region
        if r in bad_h_lines or c in bad_v_lines:
            continue
        attempts += 1
        # rebuild the coverage assignment at this anchor:
        # (neighbour, target-line) pairs per arm, so degradation can
        # drop a target and its coverage claim together
        h_cov: List[Tuple[int, int]] = []
        v_cov: List[Tuple[int, int]] = []
        n_cov = 0
        for u in placed_nbrs:
            best = None
            for (col, p0, p1) in nb_v_runs.get(u, ()):
                if p0 <= r <= p1:
                    d = abs(col - c)
                    if best is None or d < best[0]:
                        best = (d, 1, col)
            for (row, p0, p1) in nb_h_runs.get(u, ()):
                if p0 <= c <= p1:
                    d = abs(row - r)
                    if best is None or d < best[0]:
                        best = (d, 0, row)
            if best is None:
                continue
            n_cov += 1
            if best[1] == 1:
                h_cov.append((u, best[2]))
            else:
                v_cov.append((u, best[2]))
        if not allow_deficit and n_cov < len(placed_nbrs):
            continue
        # graceful degradation under allow_deficit: when an arm's full
        # hull has no free lane, drop that arm's FARTHEST
        # (neighbour, target) pair and retry — coverage decays into
        # recorded deficits instead of collapsing to the router
        # fallback
        while True:
            h_targets = [t for _u, t in h_cov]
            v_targets = [t for _u, t in v_cov]
            hx = [float(c)] + [float(x) for x in h_targets]
            vy = [float(r)] + [float(y) for y in v_targets]
            need_h = bool(h_targets) or bool(v_targets)
            need_v = bool(v_targets) or bool(h_targets)
            # deg-0-placed case: claim a single qubit at the anchor
            if not h_targets and not v_targets:
                need_h, need_v = True, False
            local_claim = set(claimed)
            chain = []
            ok = True
            fail_arm = None
            if need_h:
                got = _audit_claim(grid, local_claim, 1, [r],
                                   min(hx), max(hx),
                                   [int(round(x)) for x in h_targets],
                                   rng=rng)
                if got is None:
                    ok, fail_arm = False, "h"
                else:
                    local_claim.update(got[2])
                    chain.extend(got[2])
            if ok and need_v:
                got = _audit_claim(grid, local_claim, 0, [c],
                                   min(vy), max(vy),
                                   [int(round(y)) for y in v_targets],
                                   rng=rng)
                if got is None:
                    ok, fail_arm = False, "v"
                else:
                    local_claim.update(got[2])
                    chain.extend(got[2])
            if ok:
                break
            if not allow_deficit:
                break
            if fail_arm == "h" and h_cov:
                h_cov.remove(max(h_cov, key=lambda t: abs(t[1] - c)))
            elif fail_arm == "v" and v_cov:
                v_cov.remove(max(v_cov, key=lambda t: abs(t[1] - r)))
            else:
                break
        if ok and chain and incumbent is not None \
                and len(chain) >= incumbent:
            # completion only ADDS qubits — reject before paying for it
            if diag is not None:
                diag["rz_worse"] = diag.get("rz_worse", 0) + 1
            continue
        if not ok or not chain:
            if diag is not None:
                diag["rz_audit_fail"] = diag.get("rz_audit_fail", 0) + 1
            if fail_arm == "h":
                bad_h_lines.add(r)
            elif fail_arm == "v":
                bad_v_lines.add(c)
            # eviction plan: the cheapest lane whose blockers, once
            # ripped, would let this zero-deficit anchor realize
            if (evict_plan_out is not None and deficit == 0
                    and not evict_plan_out and fail_arm is not None):
                if fail_arm == "h":
                    got = _audit_claim_evict(
                        grid, claimed, owner_map, 1, r, min(hx), max(hx),
                        [int(round(x)) for x in hx[1:]], rng=rng)
                else:
                    got = _audit_claim_evict(
                        grid, claimed, owner_map, 0, c, min(vy), max(vy),
                        [int(round(y)) for y in vy[1:]], rng=rng)
                if got is not None and got[1]:
                    evict_plan_out.append(set(got[1]))
            continue
        covered = [u for u, _t in h_cov] + [u for u, _t in v_cov]
        full = {u: list(cc) for u, cc in work.items()}
        full[v] = list(chain)
        if grid.stride > 1:
            full, _ci = complete_seeds(grid, full, src_adj, adj,
                                       only={v})
        cand = full.get(v)
        if not cand or not chain_connected(cand, adj):
            if diag is not None:
                diag["rz_conn_fail"] = diag.get("rz_conn_fail", 0) + 1
            continue
        good = True
        for u in covered:
            uset = set(work[u])
            if not any(nb in uset for q in cand for nb in adj.get(q, ())):
                good = False
                break
        if not good:
            if diag is not None:
                diag["rz_cover_fail"] = diag.get("rz_cover_fail", 0) + 1
            continue
        if incumbent is not None and len(cand) >= incumbent:
            if diag is not None:
                diag["rz_worse"] = diag.get("rz_worse", 0) + 1
            continue
        return sorted(int(q) for q in cand)

    # ---- fallback: Steiner build through free fabric ----
    if placed_nbrs and (allow_deficit or incumbent is None):
        if diag is not None:
            diag["sph_fallbacks"] = diag.get("sph_fallbacks", 0) + 1
        chain = sph_tree(v, placed_nbrs, work, adj, {},
                         visits if visits is not None else [0],
                         forbidden_extra=claimed,
                         require_all_neighbors=not allow_deficit,
                         rng=rng)
        if chain:
            if incumbent is not None and len(chain) >= incumbent:
                return None
            return sorted(int(q) for q in chain)
    return None


def _deficit_edges(work: Embedding, src_adj, adj) -> List[Tuple[int, int]]:
    """Source edges between two PLACED variables with no coupler between
    their chains."""
    out = []
    for v in sorted(work):
        cv = work.get(v)
        if not cv:
            continue
        for u in src_adj.get(v, []):
            if u <= v:
                continue
            cu = work.get(u)
            if not cu:
                continue
            uset = set(cu)
            if not any(nb in uset for q in cv for nb in adj.get(q, ())):
                out.append((v, u))
    return out


def crossfinder_embed(source_graph: nx.Graph, target_graph: nx.Graph, *,
                      timeout: float = 300.0, seed: int = 0,
                      config: Optional[CrossConfig] = None,
                      **overrides) -> dict:
    """Standalone crossfinder embedding. Same return shape as
    attract_embed: {"embedding", "time", "stair_E", "legal_acl",
    "diag"}. Never raises."""
    start = time.perf_counter()
    deadline = start + timeout if timeout else None
    cfg = config or CrossConfig()
    known = {f.name for f in fields(CrossConfig)}
    picked = {k: v for k, v in overrides.items() if k in known}
    if picked:
        cfg = replace(cfg, **picked)

    def _fail(diag):
        return {"embedding": {}, "time": time.perf_counter() - start,
                "stair_E": None, "legal_acl": None, "diag": diag}

    diag: dict = {"phase": "init"}
    try:
        nodes = sorted(source_graph.nodes())
        src_adj = {int(v): sorted(int(u) for u in source_graph.neighbors(v))
                   for v in nodes}
        adj = build_adjacency(target_graph)
        from ember_qc.algorithms.factored.field import TileGrid
        from ember_qc.algorithms.factored.placement import (
            _auto_bins, target_layout)
        tpos = target_layout(target_graph)
        grid = TileGrid(target_graph, tpos,
                        fallback_bins=_auto_bins(len(tpos)), courses=True)
        if not grid.wire_map:
            return _fail({"error": "untyped grid: no wire picture"})
        rev: Dict[int, Tuple[int, int, int, int]] = {}
        for (o_, ln, s), run in grid.wire_map.items():
            for p, q in run.items():
                rev[q] = (o_, ln, s, p)
        rng = random.Random(seed)
        visits = [0]

        hints = None
        if cfg.init == "spectral":
            from ember_qc.algorithms.factored.placement import (
                source_positions)
            spts = source_positions(source_graph, (0.0, 0.0),
                                    (float(grid.W - 1),
                                     float(grid.H - 1)))
            hints = {int(v): (float(p[0]), float(p[1]))
                     for v, p in spts.items()}

        # ---- init pass: seeded BFS order (every non-seed variable has
        # a placed neighbour when placed), STRICT coverage from the
        # start — coverage deferred to a later legalize phase was
        # measured unfixable (the fabric fills with badly-placed
        # chains and, unlike mm, exclusive claims cannot negotiate
        # through occupied qubits; deficits stuck at 247/972 on ws).
        # Blocker ripping is the inline pressure valve. ----
        t_phase = time.perf_counter()
        work: Embedding = {}

        def _settle(v, rip_budget: List[int],
                    queue: List[int]) -> None:
            """Strict placement with eviction; deficit placement only
            as the last resort. Evicted blockers join ``queue``."""
            work.pop(v, None)
            plan: List[Set[int]] = []
            chain = _place_cross(v, work, src_adj, adj, grid, rev, rng,
                                 allow_deficit=False, incumbent=None,
                                 realize_cap=cfg.realize_cap,
                                 deadline=deadline, hints=hints,
                                 visits=visits, diag=diag,
                                 evict_plan_out=plan)
            if chain is None and plan and rip_budget[0] > 0:
                for b in sorted(plan[0]):
                    if rip_budget[0] <= 0:
                        break
                    if work.pop(b, None) is not None:
                        queue.append(b)
                        rip_budget[0] -= 1
                        diag["blocker_rips"] = \
                            diag.get("blocker_rips", 0) + 1
                chain = _place_cross(v, work, src_adj, adj, grid, rev,
                                     rng, allow_deficit=False,
                                     incumbent=None,
                                     realize_cap=cfg.realize_cap,
                                     deadline=deadline, hints=hints,
                                     visits=visits, diag=diag)
            if chain is None:
                chain = _place_cross(v, work, src_adj, adj, grid, rev,
                                     rng, allow_deficit=True,
                                     incumbent=None,
                                     realize_cap=cfg.realize_cap,
                                     deadline=deadline, hints=hints,
                                     visits=visits, diag=diag)
            if chain:
                work[v] = chain

        order: List[int] = []
        seen: Set[int] = set()
        rest = sorted(src_adj, key=lambda v: (-len(src_adj[v]), v))
        for root in rest:
            if root in seen:
                continue
            queue = [root]
            seen.add(root)
            while queue:
                v = queue.pop(0)
                order.append(v)
                nbrs = [u for u in src_adj[v] if u not in seen]
                rng.shuffle(nbrs)
                for u in nbrs:
                    seen.add(u)
                    queue.append(u)
        init_budget = [len(order)]
        init_queue: List[int] = list(order)
        qi = 0
        while qi < len(init_queue):
            if deadline is not None and time.perf_counter() > deadline:
                break
            v = init_queue[qi]
            qi += 1
            if work.get(v):
                continue
            _settle(v, init_budget, init_queue)
        diag["init_wall"] = round(time.perf_counter() - t_phase, 2)
        diag["init_unplaced"] = len(src_adj) - len(work)

        # ---- legalize passes: rip deficit endpoints and unplaced ----
        t_phase = time.perf_counter()
        diag["legalize_passes"] = 0
        diag["legalize_rips"] = 0
        while deadline is None or time.perf_counter() < deadline:
            defs = _deficit_edges(work, src_adj, adj)
            unplaced = [v for v in src_adj if not work.get(v)]
            if not defs and not unplaced:
                break
            diag["legalize_passes"] += 1
            targets = sorted({rng.choice(e) for e in defs} | set(unplaced))
            rng.shuffle(targets)
            before = (len(defs), len(unplaced))
            budget = [3 * max(1, len(targets))]
            qi = 0
            while qi < len(targets):
                v = targets[qi]
                qi += 1
                if deadline is not None and time.perf_counter() > deadline:
                    break
                _settle(v, budget, targets)
                diag["legalize_rips"] += 1
            after = (len(_deficit_edges(work, src_adj, adj)),
                     sum(1 for v in src_adj if not work.get(v)))
            if after >= before and diag["legalize_passes"] > 3:
                # no progress under reshuffles either — the honest exit
                break
        diag["legalize_wall"] = round(time.perf_counter() - t_phase, 2)
        diag["deficits"] = len(_deficit_edges(work, src_adj, adj))
        diag["unplaced"] = sum(1 for v in src_adj if not work.get(v))
        if diag["deficits"] or diag["unplaced"]:
            diag["phase"] = "legalize-failed"
            return _fail(diag)

        # ---- shorten passes: worst-billed first, strict improvement;
        # rip_windows interleaves coordinated evictions when enabled ----
        t_phase = time.perf_counter()
        diag["shorten_rips"] = 0
        diag["shorten_accepts"] = 0
        diag["window_tried"] = 0
        diag["window_accepts"] = 0
        dry = 0
        while dry < 2 and (deadline is None
                           or time.perf_counter() < deadline):
            any_accept = False
            sweep = sorted(work, key=lambda v: (-len(work[v]), v))
            for v in sweep:
                if deadline is not None and time.perf_counter() > deadline:
                    break
                incumbent = len(work[v])
                if incumbent <= 1:
                    continue
                old = work.pop(v)
                chain = _place_cross(v, work, src_adj, adj, grid, rev,
                                     rng, allow_deficit=False,
                                     incumbent=incumbent,
                                     realize_cap=cfg.realize_cap,
                                     deadline=deadline, hints=hints,
                                     visits=visits, diag=diag)
                diag["shorten_rips"] += 1
                if chain is not None:
                    trial = dict(work)
                    trial[v] = chain
                    trial = spur_prune(trial, src_adj, adj,
                                       deadline=deadline, only={v})
                    if len(trial[v]) < incumbent:
                        work = trial
                        diag["shorten_accepts"] += 1
                        any_accept = True
                        continue
                work[v] = old
            if cfg.rip_windows:
                balls = [_trim_ball(S, src_adj)
                         for S in _hull_balls(work, src_adj, grid, rev)]
                balls = [S for S in balls if S]
                rng.shuffle(balls)
                for S in balls:
                    if (deadline is not None
                            and time.perf_counter() > deadline):
                        break
                    diag["window_tried"] += 1
                    incumbent = sum(len(work[v]) for v in S)
                    saved = {v: work.pop(v) for v in S}
                    ok = True
                    todo = sorted(
                        S, key=lambda x: (-sum(1 for u in src_adj.get(x, [])
                                               if work.get(u)), x))
                    for v in todo:
                        chain = _place_cross(
                            v, work, src_adj, adj, grid, rev, rng,
                            allow_deficit=False, incumbent=None,
                            realize_cap=cfg.realize_cap,
                            deadline=deadline, hints=hints,
                            visits=visits, diag=diag)
                        if chain is None:
                            ok = False
                            break
                        work[v] = chain
                    if ok:
                        trial = spur_prune(work, src_adj, adj,
                                           deadline=deadline, only=S)
                        if (sum(len(trial[v]) for v in S) < incumbent
                                and not _deficit_edges(trial, src_adj,
                                                       adj)):
                            work = trial
                            diag["window_accepts"] += 1
                            any_accept = True
                            continue
                    for v in S:
                        work.pop(v, None)
                    work.update(saved)
            if any_accept:
                dry = 0
            else:
                dry += 1
        diag["shorten_wall"] = round(time.perf_counter() - t_phase, 2)

        # ---- finish ----
        if cfg.tail == "ball":
            from ember_qc.algorithms.factored.ball import ball_polish
            work, binfo = ball_polish(work, source_graph, target_graph,
                                      deadline=deadline, adj=adj,
                                      grid=grid, rng_seed=seed)
            diag["ball_accepts"] = binfo.get("accepted")
        work = spur_prune(work, src_adj, adj, deadline=deadline)
        if not is_valid_embedding(work, source_graph, target_graph,
                                  adj=adj):
            diag["phase"] = "invalid-final"
            return _fail(diag)
        diag["phase"] = "done"
        diag["max_chain"] = max(len(c) for c in work.values())
        mes = 0
        foot: Dict[int, Tuple[Tuple[int, int], Tuple[int, int]]] = {}
        for v, c in work.items():
            xs, ys = [], []
            for q in c:
                k = rev.get(q)
                if k is None:
                    continue
                o_, ln, _s, p = k
                xs.append(p if o_ == 1 else ln)
                ys.append(ln if o_ == 1 else p)
            if xs:
                foot[v] = ((min(xs), max(xs)), (min(ys), max(ys)))
        for v in src_adj:
            for u in src_adj[v]:
                if u <= v or v not in foot or u not in foot:
                    continue
                vx, vy = foot[v]
                ux, uy = foot[u]
                dx = max(0, max(vx[0], ux[0]) - min(vx[1], ux[1]))
                dy = max(0, max(vy[0], uy[0]) - min(vy[1], uy[1]))
                mes = max(mes, dx + dy)
        diag["max_edge_span"] = mes
        acl = sum(len(c) for c in work.values()) / len(work)
        return {"embedding": {v: sorted(c) for v, c in work.items()},
                "time": time.perf_counter() - start,
                "stair_E": None,
                "legal_acl": round(acl, 3),
                "diag": diag}
    except Exception as exc:  # never raises — probe compatibility
        diag["error"] = f"{type(exc).__name__}: {exc}"
        return _fail(diag)
