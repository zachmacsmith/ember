"""
ember_qc/algorithms/factored/placement.py
==========================================
The **attraction** embedder (paper 2, notes §3.18–§3.21): placement-first
embedding. The placement layer decides *where* variables live; the strongest
available routing and polish then work from that placement, unconstrained.

Philosophy (notes, 2026-07-17 discussions): make the placement carry the
information, so that whatever builds chains from it naturally builds good
ones — and then let the polish move wherever is genuinely better. The
placement earns its keep by improving the endpoint of an *unconstrained*
polish (the v1 result: −0.34 ACL vs the same-budget unguided control); a
placement that only looks good under a polish forbidden to leave it was not
real. Hobbling the polisher to protect the layout is therefore explicitly
rejected here (first tried, then measured worse: the region-biased finish cut
17% where minorminer's free grind cuts ~37%).

Pipeline:

1. **init** — spectral layout of the source graph scaled into the target's
   drawing coordinates (no router call, no minorminer basin as an anchor;
   degenerate spectra — e.g. complete graphs — fall back to a circle and let
   the density field do the shaping).
2. **geometry rounds** — Laplacian attraction (each centroid moves toward the
   mean of its problem-graph neighbours) plus binned density-overflow
   repulsion (the §3.19 v1 force law: capacity = working qubits per bin,
   demand = per-variable expected chain length, overfull bins push centroids
   toward the least-pressured neighbouring bin). Router-free.
3. **snap** — variables claim distinct nearest qubits, high degree first.
4. **seeded routing** — legalization from the snapped singletons.
   ``backend="mm"`` (default): stock minorminer with ``initial_chains`` and
   ``chainlength_patience=0`` — the cheap ~10% phase, C++ speed.
   ``backend="native"``: the factored router (SPH trees, negotiated cost with
   history) — the minorminer-free arm, kept for the purity ablation.
5. **feedback** — realized chain centroids re-enter the geometry loop; a few
   outer rounds of geometry → routing, best kept by legal ACL.
6. **finish** — ``polish="mm"`` (default): stock minorminer's full
   chainlength grind warm-started from the best round
   (``skip_initialization``), free to move anything anywhere.
   ``polish="native"``: spur-prune + free-space shortening (uniform prices by
   default; ``gamma > 0`` restores the region-biased ablation arm).

Deterministic per ``seed`` (minorminer arms are deterministic per
``random_seed`` as well).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field as dc_field, fields, replace
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np

from ember_qc.embedding_backend import (
    Adjacency,
    CostMap,
    Embedding,
    build_adjacency,
    is_valid_embedding,
)
from ember_qc.algorithms.factored.loop import RouterConfig, embed_factored
from ember_qc.algorithms.factored.polish import shorten_chains, spur_prune

logger = logging.getLogger(__name__)

Point = np.ndarray  # shape (2,)
Centroids = Dict[int, Point]


# ==============================================================================
# GEOMETRY
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
    a deterministic circle — the density field does the shaping from there.
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
    margin = 0.1 * (hi - lo)
    arr = lo + margin + arr * (hi - lo - 2.0 * margin)
    return {v: arr[i] for i, v in enumerate(nodes)}


def relax(cent: Centroids, src_adj: Dict[int, List[int]], eta: float) -> Centroids:
    """One Laplacian-attraction step: move each centroid ``eta`` of the way
    toward the mean of its problem-graph neighbours' centroids."""
    new: Centroids = {}
    for v, p in cent.items():
        nbrs = src_adj.get(v, [])
        if nbrs:
            target = np.mean([cent[u] for u in nbrs], axis=0)
            new[v] = p + eta * (target - p)
        else:
            new[v] = p
    return new


class DensityField:
    """Binned density-overflow repulsion (notes §3.19, the v1 force law).

    Capacity per bin is measured from the layout — the number of working
    qubits whose drawing position falls in the bin, so broken qubits are
    handled by construction. Demand per centroid is its charge (expected
    chain length). Centroids in overfull bins move up to one bin toward the
    least-pressured of the 8 neighbouring bins, scaled by the overflow.
    """

    def __init__(self, coords: np.ndarray, bins: int):
        self.B = bins
        self.mins = coords.min(axis=0)
        span = coords.max(axis=0) - self.mins
        self.width = np.maximum(span / bins, 1e-9)
        self.cap = np.zeros((bins, bins))
        for xy in coords:
            i, j = self._bin(xy)
            self.cap[i, j] += 1

    def _bin(self, p: Point) -> Tuple[int, int]:
        ij = np.clip(((p - self.mins) / self.width).astype(int), 0, self.B - 1)
        return int(ij[0]), int(ij[1])

    def _center(self, i: int, j: int) -> Point:
        return self.mins + (np.array([i, j]) + 0.5) * self.width

    def push(self, cent: Centroids, charges: Dict[int, float]) -> Centroids:
        where = {v: self._bin(p) for v, p in cent.items()}
        demand = np.zeros_like(self.cap)
        for v, ij in where.items():
            demand[ij] += charges[v]
        pressure = np.where(self.cap > 0, demand / np.maximum(self.cap, 1), np.inf)
        new: Centroids = {}
        for v, p in cent.items():
            i, j = where[v]
            pr = pressure[i, j]
            if pr <= 1.0:
                new[v] = p
                continue
            best, best_pr = (i, j), pr
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    a, b = i + di, j + dj
                    if 0 <= a < self.B and 0 <= b < self.B and pressure[a, b] < best_pr:
                        best, best_pr = (a, b), pressure[a, b]
            if best == (i, j):
                new[v] = p
            else:
                step = min(1.0, pr - 1.0)
                new[v] = p + step * (self._center(*best) - self._center(i, j))
        return new


def snap(cent: Centroids, coords: np.ndarray, qubits: Sequence[int],
         degree_order: Sequence[int]) -> Dict[int, int]:
    """Each variable (high degree first) claims the nearest unclaimed qubit."""
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


def region_prices(cent: Centroids, coords: np.ndarray, qubits: Sequence[int],
                  gamma: float, scale: float):
    """Per-vertex qubit prices for the finishing shorten:
    ``1 + gamma * (dist(q, centroid_v) / scale)^2``. Local rebuilds cost ~1;
    wandering across the fabric costs a few multiples — a bias on which short
    tree the search finds, never a wall (acceptance is on true qubit count).
    Maps are built lazily and cached per vertex.
    """
    cache: Dict[int, CostMap] = {}
    s2 = max(scale * scale, 1e-12)

    def prices_for(v: int) -> CostMap:
        p = cache.get(v)
        if p is None:
            diff = coords - cent[v]
            d2 = np.einsum("ij,ij->i", diff, diff) / s2
            p = dict(zip(qubits, (1.0 + gamma * d2).tolist()))
            cache[v] = p
        return p

    return prices_for


# ==============================================================================
# DRIVER
# ==============================================================================

@dataclass(frozen=True)
class AttractConfig:
    """One point in the attraction family.

    ``backend``/``polish`` choose the routing and finishing machinery:
    ``"mm"`` (default) is stock minorminer — seeded cheap legalization per
    round, full warm-started grind at the end; ``"native"`` is the factored
    router / free-space shortener (the minorminer-free arm). Native-router
    defaults are the paper-2 deterministic corner (Cuthill–McKee, SPH,
    negotiated cost with history).
    """
    max_rounds: int = 10       # cap on geometry -> snap -> route cycles
    round_frac: float = 0.4    # fraction of timeout the rounds phase may use;
                               # the rest is reserved for the polish. Rounds
                               # stop when this budget or max_rounds runs out
                               # (adaptive R: hard instances collapse to 1).
    geo_iters: int = 1         # relax+push steps per cycle. 1 = the validated
                               # v1 trust-region cadence (one proxy step per
                               # router projection); larger values over-optimize
                               # the coarse model beyond its calibration (the
                               # v3 regression, notes §3.23).
    selection: str = "last"    # which legal round feeds the polish:
                               # "last" (trajectory endpoint, default) or
                               # "best_legal" (v3 behavior; doubtful per §3.16)
    vary_rng: bool = True      # False: identical router RNG every round, so
                               # ONLY geometry varies between rounds — the
                               # attribution arm (failed rounds still re-roll)
    eta: float = 0.5           # attraction step size
    bins: Optional[int] = None  # density grid resolution; None = auto
    lam0: float = 3.0          # initial expected-chain-length charge
    lam_tau: float = 0.5       # damping of the charge update
                               # lam <- (1-tau)*lam + tau*realized — the
                               # charge-feedback-instability mitigation
                               # (attraction.md ledger); tau=1 = raw (v3.1)
    # ---- coarse field (VLSI round; field.py) --------------------------------
    field: str = "poisson"     # "poisson" = typed tile grid + smeared demand +
                               # hinge^2+mu Poisson repulsion (default since the
                               # 2026-07-18 field probe: improved the dense cell
                               # -1.3 ACL and widened the ws win -0.34, no
                               # regressions) | "push" = v3.1 one-bin density
                               # push (control arm)
    smear: bool = True         # poisson only: segment-smeared deposits
                               # (False = point deposits, monopole ablation)
    hinge_w: float = 1.0       # present-term weight (0 disables)
    mu_alpha: float = 0.0      # multiplier-field memory step. Default 0 by
                               # parsimony since the 2026-07-19 ablation: mu
                               # measured inert next to the hinge^2 present
                               # term (dACL within noise on all four cells,
                               # despite 30-60% stale mu-mass) -- the s3.13
                               # pattern again: a memory mechanism is inert
                               # when another mechanism already covers its job.
                               # >0 re-enables (the +mu arm).
    field_step: float = 0.5    # force scale, tiles per round (trust-region
                               # clipped at 1 tile by the field)
    ramp_rounds: int = 3       # mu-ramp: field weight scales in over rounds
    # ---- extent state (Option A; field.py CrossState, notes s3.26+) --------
    state: str = "point"       # "point" (current default) | "cross": each
                               # variable is (position, h-extent, v-extent);
                               # contact-deficit descent replaces relax and
                               # deposits follow the variable's OWN bars
                               # (s3.28-29 arms, kept for comparison) |
                               # "span" (notes s3.31): position is the ONLY
                               # state; extents are a READOUT (v's bars span
                               # its closed neighbourhood's coordinates),
                               # attraction is the HPWL subgradient on
                               # span energy = implied qubit mass, deposits
                               # are the implied bars (exact). Sparse limit
                               # == point model; dense limit -> crossbar.
                               # Default flips only if the pre-registered
                               # probe bar clears.
    seed_mode: str = "point"   # cross/span: "point" = snap singleton (as
                               # now); cross: "bars" = nearest-qubit bar
                               # tracing | "wire" = wire-coherent contiguous
                               # runs (interval coloring, s3.30); span:
                               # "wire" = interval-native wire_seeds_iv
                               # (any non-"point" value maps to it)
    extent_eta: float = 0.5    # extent growth step (contact demand)
    extent_cost: float = 0.1   # extent rent (qubits aren't free)
    field_ext_w: float = 0.5   # v2 tip-potential coupling: extent force =
                               # -field_ext_w * psi(bar tips). 0 = v1 (field
                               # cannot actuate extents)
    assign: bool = True        # v2 symmetry break (cross only): per-round
                               # rank-order assignment of bars to distinct
                               # integer rows/columns. False = v1 ablation arm
    assign_threshold: float = 2.0  # min total extent to enter assignment
                               # (points stay free; sparse regime untouched)
    assign_every: int = 1      # span only: assignment cadence within the
                               # geometry iterations (testbed s3.31: ak=5
                               # routed better than ak=1 at K100)
    kappa: float = 13.0        # span only: contact capacity (usable couplers
                               # per chain qubit; Pegasus ~13, the s3.26
                               # degree-counting bound). Derived-bar floor is
                               # w + h >= deg(v)/kappa - 1.
    span_floor: bool = True    # span only: apply the contact-capacity floor
                               # to derived bars (readout-side clamp, s3.30)
    cap_derate: float = 1.0    # span only: capacity scale during rounds.
                               # 1.0 = stock; s7's 0.65 was cross-tuned and
                               # is swept independently in the span testbed.
    backend: str = "mm"        # per-round seeded routing: "mm" | "native"
    polish: str = "mm"         # finishing pass: "mm" | "native"
    gamma: float = 0.0         # native polish only: region-bias strength
                               # (0 = unconstrained; >0 is the ablation arm —
                               # measured worse, kept for the record)
    shorten_sweeps: int = 8    # native polish only
    router: RouterConfig = dc_field(default_factory=lambda: RouterConfig(
        order="cuthill", tree="sph", cost="negotiated", alpha=1.0,
        max_passes=32, polish=False))


def _auto_bins(n_qubits: int) -> int:
    return max(4, min(16, int(math.sqrt(n_qubits) / 5)))


def _mm_route(source_graph: nx.Graph, target_graph: nx.Graph, *,
              seeds: Optional[Dict[int, int]] = None,
              chains: Optional[Dict[int, List[int]]] = None,
              warm: Optional[Embedding] = None,
              seed: int = 0, timeout: float = 60.0) -> Embedding:
    """Stock minorminer, in one of two roles: seeded cheap legalization
    (``seeds``: snapped singletons, ``chainlength_patience=0``) or the full
    warm-started polish (``warm``: a legal embedding, ``skip_initialization``).
    Returns ``{}`` on failure. Lazy import so the native arm has no
    minorminer dependency.

    The source is passed as a graph object, NOT an edge list: the edge-list
    form silently drops isolated vertices, and minorminer then rejects
    ``initial_chains`` entries for them ("labels that weren't referred to by
    any edges" — 1,546 failures in the first full-Ember sweep before this
    fix). The graph form preserves them with singleton chains, matching the
    ``minorminer`` wrapper's behavior.
    """
    import minorminer

    kwargs: dict = {"random_seed": seed, "timeout": timeout}
    if warm is not None:
        kwargs.update(initial_chains=warm, skip_initialization=True)
    else:
        init = chains if chains is not None else \
            {v: [q] for v, q in (seeds or {}).items()}
        kwargs.update(initial_chains=init, chainlength_patience=0)
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
    ``RouterConfig`` fields (``alpha``, ``order``, ...) are forwarded to the
    inner router; unknown keyword arguments are ignored.
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
        router_known = {f.name for f in fields(RouterConfig)}
        router_picked = {k: v for k, v in overrides.items()
                         if k in router_known and k not in known}
        if picked:
            cfg = replace(cfg, **picked)
        if router_picked:
            cfg = replace(cfg, router=replace(cfg.router, **router_picked))

        if cfg.state == "cross":
            from ember_qc.algorithms.factored.field import (
                assign_rows_cols, bar_force, bar_seeds, contact_step,
                deposit_cross, fit_extents, wire_seeds)
        elif cfg.state == "span":
            from ember_qc.algorithms.factored.field import (
                assign_rows_cols, bar_force_iv, bar_widths, deposit_bars,
                derive_bars, span_energy, span_step, wire_seeds_iv)
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
        span = float(np.linalg.norm(hi - lo))
        density = DensityField(coords, bins=cfg.bins or _auto_bins(len(qubits)))
        tile_grid = pfield = None
        if cfg.field == "poisson" or cfg.state in ("cross", "span"):
            from ember_qc.algorithms.factored.field import (
                PoissonField, TileGrid)
            tile_grid = TileGrid(target_graph, pos,
                                 fallback_bins=cfg.bins or _auto_bins(len(qubits)))
            if cfg.state == "span" and cfg.cap_derate != 1.0:
                tile_grid.cap = tile_grid.cap * cfg.cap_derate
            pfield = PoissonField(tile_grid, hinge_w=cfg.hinge_w,
                                  mu_alpha=cfg.mu_alpha)

        def _span_bars(tpts):
            # derived bars are a pure readout of positions (notes s3.31)
            return derive_bars(tpts, src_adj, kappa=cfg.kappa,
                               floor=cfg.span_floor,
                               bounds=(tile_grid.W, tile_grid.H))

        cent = source_positions(source_graph, lo, hi)
        ext = {v: np.zeros(2) for v in cent}  # cross state: (w, h) in tiles
        lam = cfg.lam0
        chain_len: Dict[int, float] = {}
        best_emb: Optional[Embedding] = None
        best_acl = math.inf
        best_cent: Optional[Centroids] = None
        last_emb: Optional[Embedding] = None
        last_acl = math.inf
        last_cent: Optional[Centroids] = None
        rounds_run = 0
        last_assigned = 0
        rng_rerolls = 0  # advances RNG after failed rounds when vary_rng=False
        round_acls: List[Optional[float]] = []
        round_E: List[float] = []  # span state: coarse energy per round

        def _route(seed_chains: Dict[int, List[int]], rng: int,
                   cap: float) -> Optional[Embedding]:
            if cfg.backend == "mm":
                return _mm_route(source_graph, target_graph,
                                 chains=seed_chains, seed=rng, timeout=cap)
            res = embed_factored(
                source_graph, target_graph, timeout=cap, seed=rng,
                config=cfg.router, initial_chains=seed_chains,
            )
            return res.get("embedding") or None

        # Rounds phase: capped at round_frac of the budget so the polish (the
        # phase where minorminer earns ~35% ACL, notes §3.15) cannot be starved.
        rounds_deadline = (start + cfg.round_frac * timeout) if timeout else None
        for outer in range(cfg.max_rounds):
            now = time.perf_counter()
            if rounds_deadline is not None and now >= rounds_deadline:
                break
            charges = {v: chain_len.get(v, lam) for v in cent}
            for g_it in range(cfg.geo_iters):
                if cfg.state == "cross":
                    tpts = {v: tile_grid.to_tile(p) for v, p in cent.items()}
                    tpts, ext = contact_step(
                        tpts, ext, src_adj, eta=cfg.eta,
                        extent_eta=cfg.extent_eta,
                        extent_cost=cfg.extent_cost)
                    demand = deposit_cross(tile_grid, tpts, ext)
                    psi = pfield.potential(demand)
                    ramp = min(1.0, (outer + 1) / max(cfg.ramp_rounds, 1))
                    dts, dexts = bar_force(
                        tile_grid, psi, tpts, ext,
                        scale=cfg.field_step * ramp,
                        ext_w=cfg.field_ext_w * ramp)
                    ext = {v: np.maximum(0.0, ext[v] + dexts[v])
                           for v in ext}
                    tpts = {v: tpts[v] + dts[v] for v in tpts}
                    if cfg.assign:
                        tpts, last_assigned = assign_rows_cols(
                            tpts, ext, tile_grid,
                            threshold=cfg.assign_threshold)
                    cent = {v: tile_grid.Minv @ (tpts[v] - tile_grid.c)
                            for v in cent}
                    pfield.last_demand = demand
                    continue
                if cfg.state == "span":
                    tpts = {v: tile_grid.to_tile(p) for v, p in cent.items()}
                    tpts = span_step(tpts, src_adj, eta=cfg.eta)
                    bars = _span_bars(tpts)
                    demand = deposit_bars(tile_grid, tpts, bars)
                    psi = pfield.potential(demand)
                    ramp = min(1.0, (outer + 1) / max(cfg.ramp_rounds, 1))
                    dts = bar_force_iv(tile_grid, psi, tpts, bars,
                                       scale=cfg.field_step * ramp)
                    tpts = {v: tpts[v] + dts[v] for v in tpts}
                    if cfg.assign and g_it % max(cfg.assign_every, 1) == 0:
                        # widths re-derived post-move; the assignment acts on
                        # positions only and extents re-derive afterwards --
                        # no reconciliation step exists or is needed.
                        # Participation is capacity-gated (s3.31 rule): only
                        # variables whose contact floor forces extension
                        # (deg/kappa - 1 > 0) enter the row/column sort;
                        # incidental spread stays free, so the assignment is
                        # inert on sparse sources (win-guard protection).
                        widths = bar_widths(_span_bars(tpts))
                        for v in widths:
                            if len(src_adj.get(v, [])) / cfg.kappa - 1.0 <= 0:
                                widths[v] = np.zeros(2)
                        tpts, last_assigned = assign_rows_cols(
                            tpts, widths, tile_grid,
                            threshold=cfg.assign_threshold)
                    cent = {v: tile_grid.Minv @ (tpts[v] - tile_grid.c)
                            for v in cent}
                    pfield.last_demand = demand
                    continue
                cent = relax(cent, src_adj, cfg.eta)
                if pfield is not None:
                    demand = tile_grid.deposit(cent, charges, src_adj,
                                               smear=cfg.smear)
                    psi = pfield.potential(demand)
                    ramp = min(1.0, (outer + 1) / max(cfg.ramp_rounds, 1))
                    tpts = {v: tile_grid.to_tile(p) for v, p in cent.items()}
                    dts = pfield.force_at(psi, tpts,
                                          scale=cfg.field_step * ramp)
                    cent = {v: cent[v] + tile_grid.to_drawing_delta(dts[v])
                            for v in cent}
                    pfield.last_demand = demand
                else:
                    cent = density.push(cent, charges)
            if cfg.state == "span":
                tpts = {v: tile_grid.to_tile(p) for v, p in cent.items()}
                round_E.append(round(span_energy(tpts, src_adj), 1))
            if cfg.state == "cross" and cfg.seed_mode != "point":
                tpts = {v: tile_grid.to_tile(p) for v, p in cent.items()}
                seed_chains = (wire_seeds(tile_grid, tpts, ext)
                               if cfg.seed_mode == "wire"
                               else bar_seeds(tile_grid, tpts, ext))
            elif cfg.state == "span" and cfg.seed_mode != "point":
                tpts = {v: tile_grid.to_tile(p) for v, p in cent.items()}
                seed_chains = wire_seeds_iv(tile_grid, tpts, _span_bars(tpts))
            else:
                seed_chains = {v: [q] for v, q in
                               snap(cent, coords, qubits,
                                    degree_order).items()}
            cap = (rounds_deadline - time.perf_counter()) if rounds_deadline \
                else 60.0
            if cap <= 0:
                break
            rng = seed * 100 + (outer if cfg.vary_rng else rng_rerolls)
            emb = _route(seed_chains, rng, cap)
            rounds_run += 1
            # mu update: once per router round (fresh-calibration cadence)
            if pfield is not None and pfield.last_demand is not None:
                pfield.update_mu(pfield.last_demand)
            if not emb:
                round_acls.append(None)
                rng_rerolls += 1  # geometry unchanged on failure: must re-roll
                continue
            emb = spur_prune(emb, src_adj, adj, deadline=deadline)
            a = sum(len(c) for c in emb.values()) / len(emb)
            round_acls.append(round(a, 3))
            cent = centroids_of(emb, pos)
            # damped charge updates (charge-feedback-instability mitigation).
            # Span state skips them: deposit mass is 1 + derived spans, a
            # forward function of positions -- the measured-chain-length
            # feedback channel (and its instability) does not exist there.
            tau = cfg.lam_tau
            if cfg.state != "span":
                lam = (1.0 - tau) * lam + tau * a
                realized = {v: float(len(c)) for v, c in emb.items()}
                chain_len = {v: (1.0 - tau) * chain_len.get(v, r) + tau * r
                             for v, r in realized.items()}
            if cfg.state == "cross":
                meas = fit_extents(tile_grid, emb, pos)
                ext = {v: (1.0 - tau) * ext.get(v, np.zeros(2))
                       + tau * meas.get(v, np.zeros(2)) for v in ext}
            last_emb, last_acl, last_cent = emb, a, dict(cent)
            if a < best_acl:
                best_emb, best_acl, best_cent = emb, a, dict(cent)

        # Feasibility fallback: no round legalized within the rounds budget —
        # one uncapped seeded attempt with everything that remains. Degradation
        # mode = "spectral-seeded stock MM" (net feasibility winner in §3.23).
        if best_emb is None:
            remaining = (deadline - time.perf_counter()) if deadline else 60.0
            if remaining > 0:
                fb = {v: [q] for v, q in
                      snap(cent, coords, qubits, degree_order).items()}
                emb = _route(fb, seed * 100 + 99, remaining)
                rounds_run += 1
                if emb:
                    emb = spur_prune(emb, src_adj, adj, deadline=deadline)
                    a = sum(len(c) for c in emb.values()) / len(emb)
                    round_acls.append(round(a, 3))
                    c = centroids_of(emb, pos)
                    best_emb, best_acl, best_cent = emb, a, dict(c)
                    last_emb, last_acl, last_cent = emb, a, dict(c)
                else:
                    round_acls.append(None)

        if best_emb is None:
            return _failure(rounds=rounds_run, round_acls=round_acls)

        if cfg.selection == "best_legal":
            chosen, chosen_acl, chosen_cent = best_emb, best_acl, best_cent
        else:  # "last": the trajectory endpoint
            chosen, chosen_acl, chosen_cent = last_emb, last_acl, last_cent

        remaining = (deadline - time.perf_counter()) if deadline else 60.0
        if cfg.polish == "mm" and remaining > 0:
            finished = _mm_route(source_graph, target_graph, warm=chosen,
                                 seed=seed, timeout=remaining) or chosen
        else:
            prices_for = (region_prices(chosen_cent, coords, qubits,
                                        cfg.gamma, scale=span / 2.0)
                          if cfg.gamma > 0 else None)
            finished = shorten_chains(
                chosen, src_adj, adj,
                deadline=deadline, max_sweeps=cfg.shorten_sweeps,
                vertex_prices=prices_for,
            )
            finished = spur_prune(finished, src_adj, adj, deadline=deadline)
        # Paranoia guard, same as the router's: a broken finishing pass must
        # never corrupt a legal result.
        if not is_valid_embedding(finished, source_graph, target_graph, adj=adj):
            finished = chosen

        result = {"embedding": finished,
                  "time": time.perf_counter() - start,
                  "rounds": rounds_run,
                  "round_acls": round_acls,
                  "legal_acl": round(chosen_acl, 3)}
        if pfield is not None:
            result["field_diag"] = pfield.diagnostics(pfield.last_demand)
            if cfg.state == "cross":
                sizes = np.array([ext[v].sum() for v in ext]) if ext else                     np.zeros(1)
                result["field_diag"]["extent_mean"] = round(float(sizes.mean()), 3)
                result["field_diag"]["extent_max"] = round(float(sizes.max()), 3)
                result["field_diag"]["assigned"] = int(last_assigned)
            elif cfg.state == "span":
                tpts = {v: tile_grid.to_tile(p) for v, p in cent.items()}
                widths = bar_widths(_span_bars(tpts))
                sizes = (np.array([widths[v].sum() for v in widths])
                         if widths else np.zeros(1))
                result["field_diag"]["extent_mean"] = round(float(sizes.mean()), 3)
                result["field_diag"]["extent_max"] = round(float(sizes.max()), 3)
                result["field_diag"]["assigned"] = int(last_assigned)
                result["round_E"] = round_E
        return result
    except Exception as exc:
        logger.error("attraction embed error: %s", exc)
        return _failure(error=str(exc))
