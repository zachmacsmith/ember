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
from dataclasses import dataclass, field, fields, replace
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
    outer_rounds: int = 3      # geometry -> snap -> route cycles
    geo_iters: int = 10        # relax+push steps per cycle
    eta: float = 0.5           # attraction step size
    bins: Optional[int] = None  # density grid resolution; None = auto
    lam0: float = 3.0          # initial expected-chain-length charge
    backend: str = "mm"        # per-round seeded routing: "mm" | "native"
    polish: str = "mm"         # finishing pass: "mm" | "native"
    gamma: float = 0.0         # native polish only: region-bias strength
                               # (0 = unconstrained; >0 is the ablation arm —
                               # measured worse, kept for the record)
    shorten_sweeps: int = 8    # native polish only
    router: RouterConfig = field(default_factory=lambda: RouterConfig(
        order="cuthill", tree="sph", cost="negotiated", alpha=1.0,
        max_passes=32, polish=False))


def _auto_bins(n_qubits: int) -> int:
    return max(4, min(16, int(math.sqrt(n_qubits) / 5)))


def _mm_route(source_graph: nx.Graph, target_graph: nx.Graph, *,
              seeds: Optional[Dict[int, int]] = None,
              warm: Optional[Embedding] = None,
              seed: int = 0, timeout: float = 60.0) -> Embedding:
    """Stock minorminer, in one of two roles: seeded cheap legalization
    (``seeds``: snapped singletons, ``chainlength_patience=0``) or the full
    warm-started polish (``warm``: a legal embedding, ``skip_initialization``).
    Returns ``{}`` on failure. Lazy import so the native arm has no
    minorminer dependency.
    """
    import minorminer

    kwargs: dict = {"random_seed": seed, "timeout": timeout}
    if warm is not None:
        kwargs.update(initial_chains=warm, skip_initialization=True)
    else:
        kwargs.update(initial_chains={v: [q] for v, q in (seeds or {}).items()},
                      chainlength_patience=0)
    return minorminer.find_embedding(
        list(source_graph.edges()), list(target_graph.edges()), **kwargs) or {}


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

        cent = source_positions(source_graph, lo, hi)
        lam = cfg.lam0
        chain_len: Dict[int, float] = {}
        best_emb: Optional[Embedding] = None
        best_acl = math.inf
        best_cent: Optional[Centroids] = None
        rounds_run = 0

        for outer in range(cfg.outer_rounds):
            if deadline is not None and time.perf_counter() > deadline:
                break
            for _ in range(cfg.geo_iters):
                cent = relax(cent, src_adj, cfg.eta)
                cent = density.push(
                    cent, {v: chain_len.get(v, lam) for v in cent})
            seeds = snap(cent, coords, qubits, degree_order)
            remaining = (deadline - time.perf_counter()) if deadline else 60.0
            if remaining <= 0:
                break
            if cfg.backend == "mm":
                emb = _mm_route(source_graph, target_graph, seeds=seeds,
                                seed=seed * 100 + outer, timeout=remaining)
            else:
                res = embed_factored(
                    source_graph, target_graph,
                    timeout=remaining, seed=seed * 100 + outer,
                    config=cfg.router,
                    initial_chains={v: [q] for v, q in seeds.items()},
                )
                emb = res.get("embedding")
            rounds_run += 1
            if not emb:
                continue  # keep the geometry; next round varies the router seed
            emb = spur_prune(emb, src_adj, adj)
            a = sum(len(c) for c in emb.values()) / len(emb)
            cent = centroids_of(emb, pos)
            lam = a
            chain_len = {v: float(len(c)) for v, c in emb.items()}
            if a < best_acl:
                best_emb, best_acl, best_cent = emb, a, dict(cent)

        if best_emb is None:
            return _failure(rounds=rounds_run)

        remaining = (deadline - time.perf_counter()) if deadline else 60.0
        if cfg.polish == "mm" and remaining > 0:
            finished = _mm_route(source_graph, target_graph, warm=best_emb,
                                 seed=seed, timeout=remaining) or best_emb
        else:
            prices_for = (region_prices(best_cent, coords, qubits,
                                        cfg.gamma, scale=span / 2.0)
                          if cfg.gamma > 0 else None)
            finished = shorten_chains(
                best_emb, src_adj, adj,
                deadline=deadline, max_sweeps=cfg.shorten_sweeps,
                vertex_prices=prices_for,
            )
            finished = spur_prune(finished, src_adj, adj)
        # Paranoia guard, same as the router's: a broken finishing pass must
        # never corrupt a legal result.
        if not is_valid_embedding(finished, source_graph, target_graph, adj=adj):
            finished = best_emb

        return {"embedding": finished,
                "time": time.perf_counter() - start,
                "rounds": rounds_run,
                "legal_acl": round(best_acl, 3)}
    except Exception as exc:
        logger.error("attraction embed error: %s", exc)
        return _failure(error=str(exc))
