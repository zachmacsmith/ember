"""
ember_qc/algorithms/factored/placement.py
==========================================
The **attraction** embedder (paper 2): placement-first embedding, one
algorithm since the 2026-07-29 consolidation (archive commit 612ced3e holds
the superseded point/cross/span-field variants; verdicts in
docs/paper2/attraction.md).

The placement layer decides *where* variables live — globally and jointly,
the decision one-chain-at-a-time local search cannot revise — and the
strongest available routing and polish then work from that placement,
unconstrained. The placement earns its keep by improving the endpoint of an
*unconstrained* polish (free-polish doctrine, notes §3.22); hobbling the
polisher to protect the layout was tried and measured worse.

Pipeline per call:

1. **init** — spectral layout of the source scaled into the target's drawing
   box (a warm-start heuristic, not load-bearing: the s3.36
   init-independence result); circle fallback for degenerate spectra.
2. **geometry** (per round) — one ``stair_step`` (HPWL subgradient on the
   single-coverage stair energy) then ``alternate_arrange`` (alternating 1-D
   interval packing of the capacity-forced variables into integer
   rows/columns, diagonal alignment, insertion order-search). Sparse sources
   have no participants and pass through untouched — the capacity gate is
   what keeps the dense machinery from taxing easy instances.
3. **seeds** — ``derive_bars_stair`` (arms are a pure readout of positions)
   then ``wire_seeds_iv``: greedy interval coloring onto physical wires,
   contiguous runs, always best-effort. ``wire_exact=True`` swaps in the
   per-line matching (``wire_seeds_matched``, s3.37).
4. **routing** — stock minorminer seeded cheap legalization
   (``initial_chains``, ``chainlength_patience=0``), each call capped by the
   rounds budget (``round_frac`` of timeout; the polish reserve is by
   construction).
5. **feedback** — spur-prune, realized chain centroids re-enter the geometry;
   repeat while the rounds budget and ``max_rounds`` allow. The trajectory
   endpoint (last legal round) feeds the finish.
6. **feasibility fallback** — if no round legalized: one *uncapped*
   snap-seeded attempt with all remaining time (degradation mode =
   spectral-seeded stock MM, the net feasibility winner of §3.23).
7. **finish** — stock minorminer's full grind warm-started from the selected
   round (``skip_initialization``), unconstrained.

Deterministic per ``seed``.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, fields, replace
from typing import Dict, List, Optional, Sequence

import networkx as nx
import numpy as np

from ember_qc.embedding_backend import (
    Embedding,
    build_adjacency,
    is_valid_embedding,
)
from ember_qc.algorithms.factored.polish import spur_prune

logger = logging.getLogger(__name__)

Point = np.ndarray  # shape (2,)
Centroids = Dict[int, Point]


# ==============================================================================
# GEOMETRY HELPERS
# ==============================================================================

def target_layout(target: nx.Graph) -> Dict[int, Point]:
    """Drawing coordinates for the target's qubits.

    D-Wave families get their native layouts (the coordinates the fabric was
    designed in); anything else falls back to a spectral layout of the target
    itself, which is deterministic and respects its coarse geometry.
    """
    family = target.graph.get("family")
    if family in ("pegasus", "chimera", "zephyr"):
        import dwave_networkx as dnx
        layout = {"pegasus": dnx.pegasus_layout,
                  "chimera": dnx.chimera_layout,
                  "zephyr": dnx.zephyr_layout}[family]
        pos = layout(target)
    else:
        pos = nx.spectral_layout(target)
    return {q: np.asarray(p, dtype=float) for q, p in pos.items()}


def source_positions(source: nx.Graph, lo: Point, hi: Point) -> Centroids:
    """Initial centroids: spectral layout of the source scaled into the middle
    80% of the target's bounding box. Degenerate spectra (complete graphs,
    tiny graphs, disconnected sources with collapsing components) fall back to
    a deterministic circle — the arrangement does the shaping from there.
    """
    nodes = sorted(source.nodes())
    n = len(nodes)
    arr: Optional[np.ndarray] = None
    if n >= 3:
        try:
            pos = nx.spectral_layout(source)
            cand = np.array([pos[v] for v in nodes], dtype=float)
            span = cand.max(axis=0) - cand.min(axis=0)
            if np.all(np.isfinite(cand)) and np.all(span > 1e-9):
                arr = cand
        except Exception:
            arr = None
    if arr is None:
        angles = 2.0 * math.pi * np.arange(n) / max(n, 1)
        arr = np.stack([np.cos(angles), np.sin(angles)], axis=1)
    arr = (arr - arr.min(axis=0)) / np.maximum(arr.max(axis=0) - arr.min(axis=0), 1e-9)
    # middle-80% span. The harness-style compact init (middle-30%) was probed
    # at consolidation (consolidation_probe_init30.log): K100/K140 -0.15 but
    # turan +2.0 / spin_glass +0.5 -- compact init interleaves blocks harder
    # than insertion recovers (the s3.35 circle-init lesson again). Reverted.
    margin = 0.1 * (hi - lo)
    arr = lo + margin + arr * (hi - lo - 2.0 * margin)
    return {v: arr[i] for i, v in enumerate(nodes)}


def snap(cent: Centroids, coords: np.ndarray, qubits: Sequence[int],
         degree_order: Sequence[int]) -> Dict[int, int]:
    """Each variable (high degree first) claims the nearest unclaimed qubit.
    Used by the feasibility fallback."""
    taken = np.zeros(len(qubits), dtype=bool)
    seeds: Dict[int, int] = {}
    for v in degree_order:
        d = np.einsum("ij,ij->i", coords - cent[v], coords - cent[v])
        d[taken] = np.inf
        i = int(np.argmin(d))
        taken[i] = True
        seeds[v] = qubits[i]
    return seeds


def centroids_of(chains: Embedding, pos: Dict[int, Point]) -> Centroids:
    return {v: np.mean([pos[q] for q in c], axis=0) for v, c in chains.items()}


# ==============================================================================
# DRIVER
# ==============================================================================

@dataclass(frozen=True)
class AttractConfig:
    """The attraction embedder's knobs (post-consolidation: one pipeline).

    Unknown keyword arguments to :func:`attract_embed` are ignored, so
    pre-consolidation knobs silently fall back to the single pipeline.
    """
    max_rounds: int = 1        # geometry -> seeds -> route cycles. Default 1
                               # (the 1-shot protocol) per the consolidation
                               # probe's pre-registered rule: 1shot beat the
                               # rounds protocol on all four dense cells
                               # (rounds re-derive geometry from realized
                               # centroids and destroy insertion-found order
                               # -- turan 12.73 vs 8.40). Rounds (>1) were
                               # better on ws_n486 (3.41 vs 3.76): seeded
                               # re-rolls help sparse quality; the
                               # participant-gated adaptive-rounds idea is on
                               # record in attraction.md, undesigned.
    round_frac: float = 0.5    # fraction of timeout the rounds phase may use;
                               # the rest is reserved for the polish (where
                               # minorminer earns ~35% ACL, mm-internals §6).
    geo_iters: int = 1         # stair_step + arrange cycles per round
    eta: float = 0.5           # attraction (subgradient) step size, tiles
    vary_rng: bool = True      # False: identical router RNG every round, so
                               # ONLY geometry varies between rounds — the
                               # attribution arm (failed rounds still re-roll)
    arrange_iters: int = 8     # alternation iterations per arrange call
    insert_sweeps: int = 8     # best-insertion order-search sweeps inside the
                               # alternation (s3.36; the move that makes block
                               # structure emerge from any init). 0 = off.
    kappa: Optional[float] = None  # contact capacity (usable couplers per
                               # chain qubit). None (default) = derived from
                               # the target: mean working-qubit degree - 2
                               # (Pegasus ~13.3, matching the long-hardwired
                               # 13; Zephyr ~18; Chimera ~4) — the constant
                               # stopped being Pegasus-specific in the
                               # contraction round. Floor physics ONLY since
                               # s3.40 — participation is by arm length.
    span_floor: bool = True    # apply the contact-capacity floor to derived
                               # bars (readout-side clamp, s3.30)
    cap_derate: float = 1.0    # capacity scale during rounds (<1 keeps the
                               # packing off 100% utilization; packing at
                               # exactly full starves routing slack, s3.29/31)
    wire_exact: bool = False   # coupler-exact seeds via per-line matchings
                               # (s3.37; always best-effort). Off by default:
                               # blind greedy holds the K100 champion; the
                               # matching holds K140/spin_glass/turan records
                               # and is the co-design frontier.
    courses: bool = False      # Zephyr course-resolved wires (s3.49, fabrics
                               # s4.5): sub-lane = 2k+j, stride-2 same-course
                               # runs, kappa = fresh contacts per tile (~7.7
                               # on Z12 vs 18 folded). Off = the folded
                               # representation (recorded stock arm). No-op
                               # on Pegasus/Chimera/untyped targets.
    shake_cycles: int = 0      # settle-and-reshake geometry cycles (the
                               # s3.41 shell on stair-E; s3.51/s3.52): cycle
                               # 0 = shake_steps of contraction before the
                               # first pack (the frozen-fixed-point remedy),
                               # later cycles inflate about the centroid by
                               # decaying amplitude and re-settle; keep the
                               # best (E, unplaced). 0 = stock geo_iters
                               # path, byte-identical.
    shake_steps: int = 16      # stair steps per shake cycle (measured
                               # trajectory: 16 steps take the turan bundle
                               # 19.8 -> ~12 tiles)
    masked_pool: bool = False  # line capacity from masked-nonzero cap mean
                               # (Zephyr course lines 7.68 -> 8.0; s3.51
                               # item 4). Own switch: pre-validation measured
                               # pack-level E moving the WRONG way under it.
                               # Gated on stride > 1 inside _half.
    order_shake: int = 0       # coarse-to-fine discrete shake of the 1-D
                               # order (s3.53): segment reversals + block
                               # relocations at decaying scale, chained
                               # before insertion inside the same
                               # true-E-gated composite. Value = passes;
                               # 0 = off. Same cyc-0 gating as
                               # insert_sweeps in the shake shell.
    shake_invert: bool = False  # reshake cycles use radial RANK REVERSAL
                               # about the centroid instead of dilation
                               # (s3.53: dilation preserves radial order —
                               # the core can never change hands; inversion
                               # makes it earn its place). Only active with
                               # shake_cycles >= 2.
    exact_seeds: bool = False  # exactness completion (s3.54): extend claims
                               # along their wires until every source edge
                               # has a physical coupler (corner + edge +
                               # bridge passes); on junction-complete
                               # fabrics validity is constructed and MM
                               # legalization is SKIPPED when the deficit
                               # hits 0 (the router-slack tax abolished).
                               # Includes boundary-line avoidance on
                               # stride-2 grids. Residual deficit routes as
                               # today with a better warm start.
    cover_select: bool = False  # shake-shell keep-best key becomes
                               # (post-claim coupler deficit, E, unplaced)
                               # — de-exploits the E-proxy (s3.53's
                               # E-vs-routed inversion). Only meaningful
                               # with shake_cycles >= 2.
    snap_claims: bool = False  # claim-time crossing alignment (s3.56):
                               # aim each arm's claim at its contacts'
                               # lines, parity-exact at color time — the
                               # co-design snap. Extensions drop to ~0;
                               # completion becomes a verifier. Stride-2
                               # grids only; no-op elsewhere.
    overload_lam: float = 0.0  # feasibility priced into the gate energy
                               # (s3.57, Max's design): gates and cycle
                               # selection score stair-E + lam * hinge^2
                               # of claim-layer line-capacity violations.
                               # Evaluation only; lam trades, never ranks
                               # (lam=1 repairs turan's d729 for +0.2% E;
                               # lam>=4 measured to over-trade). 0 = off,
                               # byte-identical. round_E stays raw stair-E.
    bins: Optional[int] = None  # untyped-target fallback grid resolution;
                               # None = auto


def _auto_bins(n_qubits: int) -> int:
    return max(4, min(16, int(math.sqrt(n_qubits) / 5)))


def _mm_route(source_graph: nx.Graph, target_graph: nx.Graph, *,
              chains: Optional[Dict[int, List[int]]] = None,
              warm: Optional[Embedding] = None,
              seed: int = 0, timeout: float = 60.0) -> Embedding:
    """Stock minorminer, in one of two roles: seeded cheap legalization
    (``chains``: derived seed chains, ``chainlength_patience=0``) or the full
    warm-started polish (``warm``: a legal embedding, ``skip_initialization``).
    Returns ``{}`` on failure.

    The source is passed as a graph object, NOT an edge list: the edge-list
    form silently drops isolated vertices, and minorminer then rejects
    ``initial_chains`` entries for them ("labels that weren't referred to by
    any edges" — 1,546 failures in the first full-Ember sweep before this
    fix). The graph form preserves them with singleton chains.
    """
    import minorminer

    kwargs: dict = {"random_seed": seed, "timeout": timeout}
    if warm is not None:
        kwargs.update(initial_chains=warm, skip_initialization=True)
    else:
        kwargs.update(initial_chains=chains or {}, chainlength_patience=0)
    return minorminer.find_embedding(
        source_graph, list(target_graph.edges()), **kwargs) or {}


def attract_embed(
    source_graph: nx.Graph,
    target_graph: nx.Graph,
    *,
    timeout: float = 300.0,
    seed: int = 0,
    config: Optional[AttractConfig] = None,
    **overrides,
) -> dict:
    """Functional entry point; returns an ember-qc result dict (never raises).

    ``overrides`` matching :class:`AttractConfig` fields replace those fields;
    unknown keyword arguments are ignored.
    """
    start = time.perf_counter()
    deadline = start + timeout if timeout else None

    def _failure(**extra) -> dict:
        return {"embedding": {}, "time": time.perf_counter() - start,
                "success": False, "status": "FAILURE", **extra}

    try:
        cfg = config if config is not None else AttractConfig()
        known = {f.name for f in fields(AttractConfig)}
        picked = {k: v for k, v in overrides.items() if k in known}
        if picked:
            cfg = replace(cfg, **picked)

        from ember_qc.algorithms.factored.field import (
            TileGrid, _target_kappa, alternate_arrange, bar_widths,
            claim_overload, complete_seeds, derive_bars_stair,
            stair_energy, stair_step, wire_seeds_iv, wire_seeds_matched)

        adj = build_adjacency(target_graph)
        qubits = sorted(adj)
        nodes = sorted(source_graph.nodes())
        if not nodes or not qubits or len(nodes) > len(qubits):
            return _failure()
        src_adj = {v: sorted(source_graph.neighbors(v)) for v in nodes}
        degree_order = sorted(nodes, key=lambda v: (-len(src_adj[v]), v))

        pos = target_layout(target_graph)
        coords = np.array([pos[q] for q in qubits], dtype=float)
        lo, hi = coords.min(axis=0), coords.max(axis=0)
        grid = TileGrid(target_graph, pos,
                        fallback_bins=cfg.bins or _auto_bins(len(qubits)),
                        courses=cfg.courses)
        if cfg.cap_derate != 1.0:
            grid.cap = grid.cap * cfg.cap_derate
        if cfg.exact_seeds and grid.stride > 1:
            # Boundary-line avoidance (s3.54): lines 0 and 2m have HALF the
            # crossing capacity (a bar at p covers lines {p, p+1}, so line 0
            # is even-course-only) and parity-blind packing there creates
            # structurally uncoverable crossings. Zero the boundary pools —
            # measured E-neutral-to-positive on the dense cells.
            grid.cap = grid.cap.copy()
            grid.cap[0, :, 1] = 0.0
            grid.cap[grid.H - 1, :, 1] = 0.0
            grid.cap[:, 0, 0] = 0.0
            grid.cap[:, grid.W - 1, 0] = 0.0
        bounds = (grid.W, grid.H)
        kappa = cfg.kappa if cfg.kappa is not None else _target_kappa(grid)

        def _bars(tpts):
            # arms are a pure readout of positions (s3.31/s3.34)
            return derive_bars_stair(tpts, src_adj, kappa=kappa,
                                     floor=cfg.span_floor, bounds=bounds)

        cent = source_positions(source_graph, lo, hi)
        last_emb: Optional[Embedding] = None
        last_acl = math.inf
        rounds_run = 0
        last_info: dict = {"assigned": 0}
        rng_rerolls = 0  # advances RNG after failed rounds when vary_rng=False
        mm_skips = 0     # rounds where valid seeds skipped MM legalization
        ex_last: Optional[dict] = None  # last round's completion info
        round_acls: List[Optional[float]] = []
        round_E: List[float] = []
        seed_sat: Optional[str] = None  # wire_exact: designated-crossing metric

        # Rounds phase: capped at round_frac of the budget so the polish (the
        # phase where minorminer earns ~35% ACL, notes §3.15) cannot be starved.
        rounds_deadline = (start + cfg.round_frac * timeout) if timeout else None
        for outer in range(cfg.max_rounds):
            now = time.perf_counter()
            if rounds_deadline is not None and now >= rounds_deadline:
                break
            tpts = {v: grid.to_tile(p) for v, p in cent.items()}
            if cfg.shake_cycles > 0:
                # Settle-and-reshake shell (s3.41's cycles on stair-E,
                # s3.52): cycle 0 contracts before the first pack; later
                # cycles inflate about the centroid by decaying amplitude
                # (2.0, 1.0, 0.5, ... — the s3.41 schedule verbatim) and
                # re-settle. Keep-best is load-bearing: arrange's forced
                # iter-0 projection makes repeated calls non-monotone in E.
                pts = tpts
                best_pts = None
                best_key = (math.inf, math.inf)
                amp = 2.0
                for cyc in range(cfg.shake_cycles):
                    if cyc and rounds_deadline is not None \
                            and time.perf_counter() >= rounds_deadline:
                        break  # keep best from completed cycles
                    if cyc and cfg.shake_invert:
                        # radial rank reversal (s3.53): v at radius-rank i
                        # takes the radius of rank n-1-i — core and shell
                        # swap, and whatever re-settles into the middle has
                        # earned it. (Dilation preserves radial order, the
                        # measured reason s3.52's reshakes explored
                        # nothing.) Exact-centroid points keep their spot —
                        # a one-point radius-multiset leak, documented.
                        vs = sorted(pts)
                        arr = np.array([pts[v] for v in vs])
                        c0 = arr.mean(axis=0)
                        d = arr - c0
                        r = np.linalg.norm(d, axis=1)
                        rank = sorted(range(len(vs)),
                                      key=lambda i: (r[i], vs[i]))
                        r_new = np.empty_like(r)
                        for i, ri in enumerate(rank):
                            r_new[ri] = r[rank[len(vs) - 1 - i]]
                        with np.errstate(invalid="ignore"):
                            u = np.where(r[:, None] > 1e-9,
                                         d / np.maximum(r, 1e-12)[:, None],
                                         0.0)
                        arr2 = np.clip(c0 + u * r_new[:, None],
                                       [0.0, 0.0],
                                       [grid.W - 1.0, grid.H - 1.0])
                        pts = {v: arr2[i].copy()
                               for i, v in enumerate(vs)}
                    elif cyc:
                        arr = np.array([pts[v] for v in sorted(pts)])
                        c0 = arr.mean(axis=0)
                        pts = {v: np.clip(c0 + amp * (pts[v] - c0),
                                          [0.0, 0.0],
                                          [grid.W - 1.0, grid.H - 1.0])
                               for v in pts}
                        amp *= 0.5
                    for _s in range(cfg.shake_steps):
                        pts = stair_step(pts, src_adj, eta=cfg.eta)
                    pts, info_c = alternate_arrange(
                        pts, src_adj, grid, iters=cfg.arrange_iters,
                        kappa=kappa, floor=cfg.span_floor,
                        insert_sweeps=(cfg.insert_sweeps if cyc == 0
                                       else 0),
                        masked_pool=cfg.masked_pool,
                        order_shake=(cfg.order_shake if cyc == 0
                                     else 0),
                        overload_lam=cfg.overload_lam)

                    def _sel_E(p):
                        # one lam everywhere: cycle selection must be
                        # coherent with the arrange-internal gates
                        e = stair_energy(p, src_adj)
                        if cfg.overload_lam > 0.0:
                            e += cfg.overload_lam * claim_overload(
                                p, src_adj, grid, kappa=kappa,
                                floor=cfg.span_floor)
                        return e

                    if cfg.cover_select and cfg.shake_cycles >= 2:
                        # s3.54: select on what actually gates routing —
                        # the post-claim coupler deficit — before E. The
                        # cheap interval estimate is vacuously zero
                        # (intervals contain their crossings by
                        # construction), so this derives real seeds
                        # (~10-30 ms/cycle).
                        sc = wire_seeds_iv(
                            grid, pts, _bars(pts),
                            src_adj=src_adj if cfg.snap_claims else None)
                        _, dinf = complete_seeds(grid, sc, src_adj, adj)
                        key = (dinf["deficit_edges"]
                               + dinf["corner_deficit"],
                               _sel_E(pts),
                               info_c.get("unplaced", 0))
                    else:
                        key = (_sel_E(pts),
                               info_c.get("unplaced", 0))
                    if key < best_key:
                        best_key = key
                        best_pts = {v: p.copy() for v, p in pts.items()}
                        last_info = info_c
                tpts = best_pts
            else:
                for _g in range(cfg.geo_iters):
                    tpts = stair_step(tpts, src_adj, eta=cfg.eta)
                    tpts, last_info = alternate_arrange(
                        tpts, src_adj, grid, iters=cfg.arrange_iters,
                        kappa=kappa, floor=cfg.span_floor,
                        insert_sweeps=cfg.insert_sweeps,
                        masked_pool=cfg.masked_pool,
                        order_shake=cfg.order_shake,
                        overload_lam=cfg.overload_lam)
            cent = {v: grid.Minv @ (tpts[v] - grid.c) for v in cent}
            # round_E stays RAW stair-E (recorded trajectory metric,
            # comparable to history) regardless of overload_lam
            round_E.append(round(stair_energy(tpts, src_adj), 1))

            if cfg.wire_exact:
                seed_chains, sat, tot = wire_seeds_matched(
                    grid, tpts, _bars(tpts), src_adj)
                seed_sat = f"{sat}/{tot}"
            else:
                seed_chains = wire_seeds_iv(
                    grid, tpts, _bars(tpts),
                    src_adj=src_adj if cfg.snap_claims else None)
            if cfg.exact_seeds:
                # s3.54 exactness completion: close the coverage deficit by
                # interval arithmetic; if it hits zero the seeds ARE the
                # legal embedding — skip MM legalization (the router-slack
                # tax abolished). Residual deficit routes with the
                # completed chains as a strictly better warm start.
                seed_chains, ex_info = complete_seeds(
                    grid, seed_chains, src_adj, adj)
                ex_last = ex_info
            else:
                ex_info = None
            if (ex_info is not None
                    and ex_info["deficit_edges"] == 0
                    and ex_info["corner_deficit"] == 0
                    and is_valid_embedding(seed_chains, source_graph,
                                           target_graph, adj=adj)):
                emb = {v: list(c) for v, c in seed_chains.items()}
                rounds_run += 1
                mm_skips += 1
            else:
                cap = (rounds_deadline - time.perf_counter()) \
                    if rounds_deadline else 60.0
                if cap <= 0:
                    break
                rng = seed * 100 + (outer if cfg.vary_rng else rng_rerolls)
                emb = _mm_route(source_graph, target_graph,
                                chains=seed_chains, seed=rng, timeout=cap)
                rounds_run += 1
                if not emb:
                    round_acls.append(None)
                    rng_rerolls += 1  # geometry unchanged: must re-roll
                    continue
            emb = spur_prune(emb, src_adj, adj, deadline=deadline)
            a = sum(len(c) for c in emb.values()) / len(emb)
            round_acls.append(round(a, 3))
            cent = centroids_of(emb, pos)
            last_emb, last_acl = emb, a

        # Feasibility fallback: no round legalized within the rounds budget —
        # one uncapped snap-seeded attempt with everything that remains.
        # Degradation mode = "spectral-seeded stock MM" (§3.23's net
        # feasibility winner).
        if last_emb is None:
            remaining = (deadline - time.perf_counter()) if deadline else 60.0
            if remaining > 0:
                fb = {v: [q] for v, q in
                      snap(cent, coords, qubits, degree_order).items()}
                emb = _mm_route(source_graph, target_graph, chains=fb,
                                seed=seed * 100 + 99, timeout=remaining)
                rounds_run += 1
                if emb:
                    emb = spur_prune(emb, src_adj, adj, deadline=deadline)
                    a = sum(len(c) for c in emb.values()) / len(emb)
                    round_acls.append(round(a, 3))
                    last_emb, last_acl = emb, a
                else:
                    round_acls.append(None)

        if last_emb is None:
            return _failure(rounds=rounds_run, round_acls=round_acls)

        remaining = (deadline - time.perf_counter()) if deadline else 60.0
        if remaining > 0:
            finished = _mm_route(source_graph, target_graph, warm=last_emb,
                                 seed=seed, timeout=remaining) or last_emb
        else:
            finished = last_emb
        # Paranoia guard: a broken finishing pass must never corrupt a legal
        # result.
        if not is_valid_embedding(finished, source_graph, target_graph, adj=adj):
            finished = last_emb

        tpts = {v: grid.to_tile(p) for v, p in cent.items()}
        widths = bar_widths(_bars(tpts))
        sizes = (np.array([widths[v].sum() for v in widths])
                 if widths else np.zeros(1))
        diag = {"assigned": int(last_info.get("assigned", 0)),
                "assigned_rows": int(last_info.get("assigned_rows", 0)),
                "assigned_cols": int(last_info.get("assigned_cols", 0)),
                "insert_reverts": int(last_info.get("insert_reverts", 0)),
                "mono_time": float(last_info.get("mono_time", 0.0)),
                "extent_mean": round(float(sizes.mean()), 3),
                "extent_max": round(float(sizes.max()), 3),
                "stride": int(grid.stride)}
        if seed_sat is not None:
            diag["designated"] = seed_sat
        if cfg.exact_seeds:
            diag["mm_skips"] = mm_skips
            if ex_last is not None:
                for k in ("deficit_edges", "corner_deficit", "extensions",
                          "ext_qubits", "bridges"):
                    diag[k] = ex_last[k]
        return {"embedding": finished,
                "time": time.perf_counter() - start,
                "rounds": rounds_run,
                "round_acls": round_acls,
                "round_E": round_E,
                "legal_acl": round(last_acl, 3),
                "diag": diag}
    except Exception as exc:
        logger.error("attraction embed error: %s", exc)
        return _failure(error=str(exc))
