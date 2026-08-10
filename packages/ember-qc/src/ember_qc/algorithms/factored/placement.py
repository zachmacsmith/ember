"""
ember_qc/algorithms/factored/placement.py
==========================================
The **attraction** embedder (paper 2): placement-first embedding, one
algorithm and one code path since the 2026-08-03 consolidation 2 (archive
commit 9d99ebdd holds the deleted switch stack; 612ced3e holds the older
point/cross/span-field variants; verdicts in docs/paper2/attraction.md).

The placement layer decides *where* variables live — globally and jointly,
the decision one-chain-at-a-time local search cannot revise — and the
strongest available routing and polish then work from that placement,
unconstrained. The placement earns its keep by improving the endpoint of an
*unconstrained* polish (free-polish doctrine, notes §3.22); hobbling the
polisher to protect the layout was tried and measured worse.

Pipeline per call (1-shot):

1. **init** — the V-cycle two-stage coarsening init (``coarsen.py``,
   default since s3.66; ``vcycle=False`` = the legacy spectral init).
2. **geometry** — contraction (``CONTRACT_STEPS`` stair steps on
   stride-2 fabrics, the measured single step elsewhere — see the
   effective-config block), then ``alternate_arrange`` under the policy
   the effective config selected (DP packer + overload-priced gates on
   course-resolved Zephyr; the measured greedy elsewhere).
3. **seeds** — one `arm_books` bundle feeds the snap-aimed coloring and,
   on stride-2 fabrics, the exactness completion; deficit 0 = the seeds
   ARE legal and minorminer legalization is skipped (diagnostic:
   ``mm_skipped``).
4. **routing** — otherwise stock minorminer seeded legalization, capped
   at ``round_frac`` of the timeout.
5. **feasibility fallback** — one uncapped snap-seeded attempt.
6. **finish** — stock minorminer's full grind warm-started,
   unconstrained; validity-guarded.

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
            if n > 300:
                # sparse path (s3.67): networkx's spectral_layout fell
                # through to DENSE O(n^3) BLAS on large suite graphs —
                # 100 sweep workers stuck in dtrmm for minutes-to-hours
                # each (gdb-confirmed). Sparse eigsh is seconds at
                # n=17k. Small n keeps the exact legacy numerics.
                import scipy.sparse as sp
                import scipy.sparse.linalg as spl
                idx = {v: i for i, v in enumerate(nodes)}
                rows, cols = [], []
                for u, w in source.edges():
                    rows += [idx[u], idx[w]]
                    cols += [idx[w], idx[u]]
                data = np.ones(len(rows))
                A = sp.coo_matrix((data, (rows, cols)), shape=(n, n))
                L = (sp.diags(np.asarray(A.sum(axis=1)).ravel()) - A).tocsc()
                vals, vecs = spl.eigsh(L, k=3, sigma=-1e-3, which="LM")
                order = np.argsort(vals)
                cand = vecs[:, order[1:3]].astype(float)
            else:
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


# ==============================================================================
# DRIVER
# ==============================================================================

FALLBACK_TIMEOUT = 60.0  # budget when the caller passes timeout=0/None
SEED_STRIDE = 100        # router-seed derivation: seed*STRIDE (+99 fallback)

CONTRACT_STEPS = 16  # stair steps of contraction before the first pack — the
                     # s3.52 cycle-0 mechanism (stock 1-step geometry was a
                     # frozen fixed point, s3.51: a single step on a 20-tile
                     # cloud, then nearest-line packing snaps back all drift;
                     # 16 steps take the turan bundle 19.8 -> ~12 tiles).
                     # The decaying-amplitude reshakes of the s3.41 shell
                     # added nothing (keep-best discarded them everywhere,
                     # s3.52 attribution) and were deleted at consolidation 2.


@dataclass(frozen=True)
class AttractConfig:
    """The attraction embedder's knobs (consolidation 2: one code path).

    Unknown keyword arguments to :func:`attract_embed` are ignored, so
    pre-consolidation knobs silently fall back to the single pipeline.
    """
    round_frac: float = 0.5    # fraction of timeout the placement+legalize
                               # phase may use; the rest is reserved for the
                               # polish (where minorminer earns ~35% ACL,
                               # mm-internals §6).
    eta: float = 0.5           # attraction (subgradient) step size, tiles
    arrange_iters: int = 8     # alternation iterations per arrange call
    insert_sweeps: int = 8     # best-insertion order-search sweeps inside the
                               # alternation (s3.36; the move that makes block
                               # structure emerge from any init). 0 = off.
    kappa: Optional[float] = None  # contact capacity (usable couplers per
                               # chain qubit). None (default) = derived from
                               # the target: mean working-qubit degree - 2 on
                               # stride-1 fabrics; fresh contacts per tile on
                               # course-resolved Zephyr (~7.7 on Z12). Floor
                               # physics ONLY since s3.40 — participation is
                               # by arm length.
    span_floor: bool = True    # apply the contact-capacity floor to derived
                               # bars (readout-side clamp, s3.30)
    courses: bool = True       # Zephyr course-resolved wires (s3.49, fabrics
                               # s4.5): sub-lane = 2k+j, stride-2 same-course
                               # runs, kappa = fresh contacts per tile.
                               # Default ON since consolidation 2 (the folded
                               # representation was the measured 2x-template
                               # ceiling, s3.48). False = the folded control
                               # arm. No-op on Pegasus/Chimera/untyped.
    exact_seeds: bool = True   # exactness completion (s3.54): extend claims
                               # along their wires until every source edge
                               # has a physical coupler (corner + edge +
                               # bridge passes); when the deficit hits 0 the
                               # seeds ARE the legal embedding and MM
                               # legalization is SKIPPED (the router-slack
                               # tax abolished). Includes boundary-line
                               # avoidance. Engages on stride>1 fabrics only
                               # (junction completeness makes coverage =
                               # validity there; Pegasus's 56% junctions do
                               # not qualify — the open co-design problem).
    snap_claims: bool = True   # claim-time crossing alignment (s3.56):
                               # aim each arm's claim at its contacts'
                               # lines, parity-exact at color time — aim,
                               # don't repair. Extensions drop to ~0;
                               # completion becomes a verifier. Stride-2
                               # grids only; no-op elsewhere.
    overload_lam: float = 1.0  # feasibility priced into the gate energy
                               # (s3.57, Max's design): arrange gates score
                               # stair-E + lam * hinge^2 of claim-layer
                               # line-capacity violations. Evaluation only;
                               # lam trades, never ranks (lam=1 repairs
                               # turan's d729 for +0.2% E; lam>=4 measured
                               # to over-trade). Applied on stride>1 fabrics
                               # only (measured on Z12; unmeasured
                               # elsewhere). round_E stays raw stair-E.
    vcycle: bool = True        # source-side two-stage coarsening init
                               # (s3.62-3.64): twin-first + Jaccard
                               # matching, spectral-of-the-coarse-graph
                               # placement (circle fallback), inherited
                               # positions. DEFAULT ON since
                               # consolidation 3 (s3.66): under
                               # outcome-first scoring the vc arm
                               # beats-or-ties the spectral init on all
                               # measured cells and beats minorminer
                               # everywhere, including the cells the
                               # old default lost; confirmed by the
                               # s3.66 guard probe. False = the legacy
                               # spectral init.
    vcycle_agg: bool = True    # s3.68/s3.69: leader-aggregation fixpoint
                               # replaces {one pairwise matching round +
                               # the no-fixpoint decree}; twin hash kept
                               # at round 0; quotient protection emerges
                               # from the weighted score. Probe-validated
                               # at board parity twice (s3.68, s3.70);
                               # DEFAULT ON (Max, 2026-08-06: winners
                               # ship). Inert unless vcycle is active.
    vcycle_transport: bool = False
                               # s3.69 measure-transport junction: the
                               # fine layout = the coarse layout's ORDERS
                               # expanded by wire MASS (adjoint of the
                               # merge; contiguous blocks, attachment
                               # rank within, mass-CDF coordinates in the
                               # standard box). Replaces the disc/anchor
                               # spread and its geometry constants on
                               # this path. Inert unless vcycle is
                               # active.
    cluster_moves: bool = True
                               # s3.70: coarsen the MOVES, not the state.
                               # Clusters (aggregation-fixpoint groups)
                               # are member sets gathered/relocated as
                               # one E-gated composite inside arrange —
                               # real bars through real gates, nothing
                               # summarized, no sizes guessed. NOT
                               # stride-gated: rides the ordinary gates
                               # on every fabric. DEFAULT ON (Max,
                               # 2026-08-06: obvious winners ship as
                               # defaults — turan 8.12→6.52 at 3 seeds
                               # with the tail killed (cmove_probe.csv;
                               # s3.74 corrected the unartifacted 10-seed
                               # figures), expanders at exact parity,
                               # first Pegasus movement).
    cluster_units: bool = True
                               # s3.71: move units from THRESHOLD-FREE
                               # mutual-preference coarsening (τ never
                               # consulted; every graph gets its natural
                               # log-depth hierarchy — lattices become
                               # patch tilings, the gate filters).
                               # False = s3.70's τ-aggregation units
                               # (the measurement control arm).
    order_state: bool = False
                               # v4 stage O1: the state is two orders.
                               # Init points are reduced to per-axis
                               # ranks (sort keys only); the continuous
                               # contraction phase does not exist on
                               # this arm; the DP packs with the TRUE
                               # stair objective (field._axis_coeffs)
                               # on every fabric, overload priced into
                               # the gates fabric-agnostically, and all
                               # variables live in the books. Positions
                               # are thereafter always derived line
                               # indices — a readout, never state.
                               # Stride gates for exact_seeds/snap/
                               # courses are untouched (junction
                               # completeness is physics, not carrier).
    contract_stable: bool = False
                               # s3.74: derived contraction stopping rule
                               # in place of the CONTRACT_STEPS=16 count.
                               # The count was a disguised density knob —
                               # pure attraction's continuous minimum is
                               # collapse; stopping early was the only
                               # counter-force. Under this switch the
                               # loop stops when best stair-E goes
                               # unimproved 2 consecutive steps, hard cap
                               # W+H (the fabric travel bound), and runs
                               # UN-gated on stride-1 fabrics (the probe
                               # asks whether contraction can be un-gated
                               # on Pegasus under an honest rule).


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
            TileGrid, _target_kappa, alternate_arrange, arm_books,
            bar_widths, complete_seeds, stair_energy, stair_step,
            wire_seeds_iv)

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
                        fallback_bins=_auto_bins(len(qubits)),
                        courses=cfg.courses)
        # The stride gate (consolidation 2): the exactness path and the
        # overload penalty are measured on stride>1 (course-resolved Zephyr)
        # only, where junction completeness makes coverage = validity. On
        # stride-1 fabrics both are inert, so Pegasus/Chimera seeding
        # behavior is byte-identical to the first consolidation's default.
        # ---- EFFECTIVE CONFIG (s3.66): every fabric-policy decision,
        # decided ONCE. field.py never inspects the fabric. On stride-1
        # (Pegasus/Chimera/untyped) the pipeline runs the measured
        # legacy policy end to end; courses=False on Zephyr therefore
        # selects the WHOLE legacy pipeline, not just the folded wires.
        stride2 = grid.stride > 1
        eff_contract = CONTRACT_STEPS if stride2 else 1
        eff_lam = cfg.overload_lam if stride2 else 0.0
        eff_exact = cfg.exact_seeds and stride2
        eff_snap = cfg.snap_claims and stride2
        eff_dp = stride2
        if cfg.order_state:
            # v4: the packer and the overload gate are properties of the
            # state representation, not of the fabric — fabric-agnostic
            # under the switch. Exactness/snap stay stride-gated above.
            eff_lam = cfg.overload_lam
            eff_dp = True
        # vcycle activation is stride-gated (s3.66 guard probe): the
        # compact coarse init needs the contraction+DP machinery to
        # exploit it — on the P16 legacy path it regressed the dense
        # cells (turan 8.45->9.47, K100 13.19->14.08, clean controls)
        # while helping sparse (ws 3.79->3.60; recorded as
        # restricted-polish-round evidence, s3.65 C).
        eff_vcycle = cfg.vcycle and stride2
        kappa = cfg.kappa if cfg.kappa is not None else _target_kappa(grid)

        if eff_vcycle:
            from ember_qc.algorithms.factored.coarsen import multilevel_init
            cent = multilevel_init(src_adj, lo, hi, seed=seed,
                                   agg=cfg.vcycle_agg,
                                   transport=cfg.vcycle_transport,
                                   grid=grid, kappa=kappa)
        else:
            cent = source_positions(source_graph, lo, hi)
        legal_emb: Optional[Embedding] = None
        legal_acl = math.inf
        mm_skipped = False
        ex_info: Optional[dict] = None

        placement_deadline = (start + cfg.round_frac * timeout) \
            if timeout else None

        if cfg.order_state:
            # v4: the init's continuous points are reduced to their
            # per-axis RANKS — sort keys for the first readout, nothing
            # more. The first arrange projection replaces them with true
            # line assignments; no continuous phase exists on this arm.
            tpts = {v: np.zeros(2) for v in cent}
            for axis in (0, 1):
                ranked = sorted(cent, key=lambda v: (float(cent[v][axis]),
                                                     v))
                for r, v in enumerate(ranked):
                    tpts[v][axis] = float(r)
        else:
            tpts = {v: grid.to_tile(p) for v, p in cent.items()}
        # Galerkin-defect instrumentation (s3.69): stair-E of the raw
        # interpolated init and after contraction — with the final
        # stair_E below, attributes what the junction hands over vs
        # what contraction and arrange must repair.
        E_interp = round(stair_energy(tpts, src_adj), 1)
        contract_steps = None
        if cfg.order_state:
            pass  # no contraction: the continuous phase is deleted here
        elif cfg.contract_stable:
            best_E = stair_energy(tpts, src_adj)
            stall = 0
            contract_steps = 0
            step_cap = grid.W + grid.H
            while stall < 2 and contract_steps < step_cap:
                if (placement_deadline is not None
                        and time.perf_counter() > placement_deadline):
                    break
                tpts = stair_step(tpts, src_adj, eta=cfg.eta)
                contract_steps += 1
                E_now = stair_energy(tpts, src_adj)
                if E_now < best_E:
                    best_E = E_now
                    stall = 0
                else:
                    stall += 1
        else:
            for _s in range(eff_contract):
                tpts = stair_step(tpts, src_adj, eta=cfg.eta)
        E_contract = round(stair_energy(tpts, src_adj), 1)
        # s3.70 cluster moves: the aggregation hierarchy's groups, in
        # FINE ids, one list per level (coarsest last). Position-free —
        # computed once from the source graph.
        cluster_groups = None
        if cfg.cluster_moves:
            from ember_qc.algorithms.factored.coarsen import (
                coarsen as _coarsen)
            _levels = (_coarsen(src_adj, units=True) if cfg.cluster_units
                       else _coarsen(src_adj, agg=True))
            if len(_levels) > 1:
                cluster_groups = []
                _mem = {v: [v] for v in _levels[0].adj}
                for _li in range(1, len(_levels)):
                    _up: dict = {}
                    for _c, _ms in _mem.items():
                        _p = _levels[_li].parent_of[_c]
                        _up.setdefault(_p, []).extend(_ms)
                    _mem = _up
                    _g = [sorted(ms) for ms in _mem.values() if len(ms) > 1]
                    if _g:
                        cluster_groups.append(_g)
                cluster_groups = cluster_groups or None
        tpts, last_info = alternate_arrange(
            tpts, src_adj, grid, iters=cfg.arrange_iters,
            kappa=kappa, floor=cfg.span_floor,
            insert_sweeps=cfg.insert_sweeps,
            overload_lam=eff_lam, use_dp=eff_dp, snap=eff_snap,
            deadline=placement_deadline,
            cluster_groups=cluster_groups,
            order_mode=cfg.order_state)
        cent = {v: grid.Minv @ (tpts[v] - grid.c) for v in cent}
        # raw stair-E (recorded trajectory metric)
        stair_E = round(stair_energy(tpts, src_adj), 1)

        # one accounting: the seeds read the SAME books the gates used
        books = arm_books(tpts, src_adj, grid, kappa=kappa,
                          floor=cfg.span_floor, snap=eff_snap,
                          min_span=0.0 if cfg.order_state else 1.0)
        seed_chains = wire_seeds_iv(grid, tpts, books[1],
                                    src_adj=src_adj, snap=eff_snap,
                                    books=books)
        if eff_exact:
            seed_chains, ex_info = complete_seeds(
                grid, seed_chains, src_adj, adj)
        emb: Embedding = {}
        if (ex_info is not None
                and ex_info["deficit_edges"] == 0
                and ex_info["corner_deficit"] == 0
                and is_valid_embedding(seed_chains, source_graph,
                                       target_graph, adj=adj)):
            emb = {v: list(c) for v, c in seed_chains.items()}
            mm_skipped = True
        else:
            cap = (placement_deadline - time.perf_counter()) \
                if placement_deadline else FALLBACK_TIMEOUT
            if cap > 0:
                emb = _mm_route(source_graph, target_graph,
                                chains=seed_chains,
                                seed=seed * SEED_STRIDE, timeout=cap)

        if not emb:
            # feasibility fallback: one uncapped snap-seeded attempt
            # (degradation mode = spectral-seeded stock MM, s3.23)
            remaining = (deadline - time.perf_counter()) if deadline \
                else FALLBACK_TIMEOUT
            if remaining > 0:
                fb = {v: [q] for v, q in
                      snap(cent, coords, qubits, degree_order).items()}
                emb = _mm_route(source_graph, target_graph, chains=fb,
                                seed=seed * SEED_STRIDE + 99,
                                timeout=remaining)
        if emb:
            emb = spur_prune(emb, src_adj, adj, deadline=deadline)
            legal_acl = sum(len(c) for c in emb.values()) / len(emb)
            legal_emb = emb

        if legal_emb is None:
            return _failure(stair_E=stair_E)

        remaining = (deadline - time.perf_counter()) if deadline \
            else FALLBACK_TIMEOUT
        if remaining > 0:
            finished = _mm_route(source_graph, target_graph,
                                 warm=legal_emb, seed=seed,
                                 timeout=remaining) or legal_emb
        else:
            finished = legal_emb
        # a broken finishing pass must never corrupt a legal result
        if not is_valid_embedding(finished, source_graph, target_graph,
                                  adj=adj):
            finished = legal_emb

        widths = bar_widths(books[1])
        sizes = (np.array([widths[v].sum() for v in widths])
                 if widths else np.zeros(1))
        diag = {"assigned": int(last_info.get("assigned", 0)),
                "assigned_rows": int(last_info.get("assigned_rows", 0)),
                "assigned_cols": int(last_info.get("assigned_cols", 0)),
                "insert_reverts": int(last_info.get("insert_reverts", 0)),
                "cluster_accepts": int(last_info.get("cluster_accepts", 0)),
                "cluster_reverts": int(last_info.get("cluster_reverts", 0)),
                "mono_time": float(last_info.get("mono_time", 0.0)),
                "extent_mean": round(float(sizes.mean()), 3),
                "extent_max": round(float(sizes.max()), 3),
                "stride": int(grid.stride),
                # Galerkin-defect triple (s3.69): init handoff vs
                # contraction vs arrange — junction-loss attribution
                "E_interp": E_interp,
                "E_contract": E_contract,
                # the hardware-relevant tail metric (s3.65): recorded
                # from consolidation 3 onward, everywhere
                "max_chain": max(len(c) for c in finished.values())}
        if contract_steps is not None:
            diag["contract_steps"] = contract_steps
        if cfg.order_state:
            diag["order_state"] = True
        if eff_exact:
            diag["mm_skipped"] = mm_skipped
            if ex_info is not None:
                for k in ("deficit_edges", "corner_deficit", "extensions",
                          "ext_qubits", "bridges"):
                    diag[k] = ex_info[k]
        return {"embedding": finished,
                "time": time.perf_counter() - start,
                "stair_E": stair_E,
                "legal_acl": round(legal_acl, 3),
                "diag": diag}
    except Exception as exc:
        logger.error("attraction embed error: %s", exc)
        return _failure(error=str(exc))
