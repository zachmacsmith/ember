"""
ember_qc/algorithms/factored/placement.py
==========================================
The **attraction** embedder: the plane engine (``plane.py``) decides
where every variable lives — two orders, positions derived by the
packer under hard capacity, chains derived by the stair rule — and the
hardware adapter turns that layout into qubits:

1. **arrange** — ``plane.arrange``: random orders in, the bookmark's
   positions and books out (see ``plane.py`` for the whole algorithm).
2. **seeds** — the bookmark's books feed the converter
   (``wire_seeds_exact`` on course-resolved fabrics, ``wire_seeds_iv``
   elsewhere) and, on stride-2 fabrics, the exactness completion; a
   completion with zero deficits and a passing validity check IS the
   embedding and minorminer legalization is skipped (``mm_skipped``).
3. **legalize** — otherwise stock minorminer, seeded with the chains.
4. **fallback** — one nearest-qubit-seeded attempt if that failed.
5. **tail** — ``tail="mm"``: minorminer's warm-started grind then the
   ball pass; ``tail="none"``: the legal embedding as is.

Fabric policy is decided once, here: exactness and snap are gated to
stride > 1 (junction completeness is what makes coverage = validity).
``field.py`` and ``plane.py`` never inspect the fabric.

Parameters: ``timeout`` (a safety net; the engine's real stop is the
work budget), ``seed``, ``max_asks`` (DP evaluations), ``sched_seed``
(the bag's own seed; defaults to ``seed``), ``tail``. Deterministic
per ``(seed, sched_seed)``.
"""
from __future__ import annotations

import logging
import math
import time
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

FALLBACK_TIMEOUT = 60.0  # budget when the caller passes timeout=0/None
SEED_STRIDE = 100        # router-seed derivation: seed*STRIDE (+99 fallback)
TAIL_SPLIT = 0.5         # wall reserved for the tail when a timeout exists


def target_layout(target: nx.Graph) -> Dict[int, Point]:
    """Drawing coordinates for the target's qubits: the native D-Wave
    layouts, else a spectral layout of the target."""
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


def snap(cent: Dict[int, Point], coords: np.ndarray, qubits: Sequence[int],
         degree_order: Sequence[int]) -> Dict[int, int]:
    """Each variable (high degree first) claims the nearest unclaimed
    qubit. The feasibility fallback's seeds."""
    taken = np.zeros(len(qubits), dtype=bool)
    seeds: Dict[int, int] = {}
    for v in degree_order:
        d = np.einsum("ij,ij->i", coords - cent[v], coords - cent[v])
        d[taken] = np.inf
        i = int(np.argmin(d))
        taken[i] = True
        seeds[v] = qubits[i]
    return seeds


def _auto_bins(n_qubits: int) -> int:
    return max(4, min(16, int(math.sqrt(n_qubits) / 5)))


def _mm_route(source_graph: nx.Graph, target_graph: nx.Graph, *,
              chains: Optional[Dict[int, List[int]]] = None,
              warm: Optional[Embedding] = None,
              seed: int = 0, timeout: float = 60.0) -> Embedding:
    """Stock minorminer in one of two roles: seeded cheap legalization
    (``chains``, ``chainlength_patience=0``) or the warm-started polish
    (``warm``, ``skip_initialization``). Returns ``{}`` on failure. The
    source is passed as a graph object, not an edge list: the edge-list
    form drops isolated vertices and minorminer then rejects their
    ``initial_chains`` entries."""
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
    max_asks: Optional[int] = None,
    sched_seed: Optional[int] = None,
    tail: str = "mm",
    **ignored,
) -> dict:
    """Functional entry point; returns an ember-qc result dict (never
    raises). Unknown keyword arguments are ignored."""
    start = time.perf_counter()
    deadline = start + timeout if timeout else None

    def _failure(**extra) -> dict:
        return {"embedding": {}, "time": time.perf_counter() - start,
                "success": False, "status": "FAILURE", **extra}

    try:
        if tail not in ("none", "mm"):
            raise ValueError(f"unknown tail {tail!r}")
        if max_asks is not None and max_asks < 1:
            raise ValueError("max_asks must be >= 1")
        from ember_qc.algorithms.factored import plane
        from ember_qc.algorithms.factored.field import (
            TileGrid, bar_widths, complete_seeds, stair_energy,
            wire_seeds_exact, wire_seeds_iv)

        adj = build_adjacency(target_graph)
        qubits = sorted(adj)
        nodes = sorted(source_graph.nodes())
        if not nodes or not qubits or len(nodes) > len(qubits):
            return _failure()
        src_adj = {v: sorted(source_graph.neighbors(v)) for v in nodes}
        degree_order = sorted(nodes, key=lambda v: (-len(src_adj[v]), v))

        pos = target_layout(target_graph)
        coords = np.array([pos[q] for q in qubits], dtype=float)
        grid = TileGrid(target_graph, pos,
                        fallback_bins=_auto_bins(len(qubits)),
                        courses=True)
        # fabric policy, decided once: the exactness path (completion,
        # certificate, snap-aimed claims) needs junction completeness,
        # which is a stride-2 fact
        stride2 = grid.stride > 1
        eff_exact = stride2
        eff_snap = stride2
        engine_deadline = ((start + TAIL_SPLIT * timeout)
                           if (timeout and tail != "none") else deadline)

        # ---- arrange
        _t0 = time.perf_counter()
        tpts, books, info = plane.arrange(
            src_adj, grid, seed=seed, max_asks=max_asks,
            deadline=engine_deadline, snap=eff_snap,
            sched_seed=seed if sched_seed is None else sched_seed)
        arrange_wall = time.perf_counter() - _t0
        stair_E = round(stair_energy(tpts, src_adj, contacts=books[0]), 1)

        # ---- seeds: the bookmark's books ARE the converter's books
        conv_info = None
        ex_info = None
        if stride2 and grid.wire_map:
            seed_chains, conv_info = wire_seeds_exact(
                grid, tpts, books[1], src_adj, books)
        else:
            seed_chains = wire_seeds_iv(grid, tpts, books[1],
                                        src_adj=src_adj, snap=eff_snap,
                                        books=books)
        if eff_exact:
            seed_chains, ex_info = complete_seeds(
                grid, seed_chains, src_adj, adj)

        # ---- legalize
        mm_skipped = False
        emb: Embedding = {}
        if (ex_info is not None
                and ex_info["deficit_edges"] == 0
                and ex_info["corner_deficit"] == 0
                and is_valid_embedding(seed_chains, source_graph,
                                       target_graph, adj=adj)):
            emb = {v: list(c) for v, c in seed_chains.items()}
            mm_skipped = True
        else:
            cap = ((engine_deadline - time.perf_counter())
                   if engine_deadline else FALLBACK_TIMEOUT)
            if cap > 0:
                emb = _mm_route(source_graph, target_graph,
                                chains=seed_chains,
                                seed=seed * SEED_STRIDE, timeout=cap)
        if not emb:
            remaining = ((deadline - time.perf_counter()) if deadline
                         else FALLBACK_TIMEOUT)
            if remaining > 0:
                cent = {v: grid.Minv @ (tpts[v] - grid.c) for v in tpts}
                fb = {v: [q] for v, q in
                      snap(cent, coords, qubits, degree_order).items()}
                emb = _mm_route(source_graph, target_graph, chains=fb,
                                seed=seed * SEED_STRIDE + 99,
                                timeout=remaining)
        if not emb:
            return _failure(stair_E=stair_E)
        emb = spur_prune(emb, src_adj, adj, deadline=deadline)
        legal_acl = sum(len(c) for c in emb.values()) / len(emb)
        legal_max_chain = max(len(c) for c in emb.values())

        # ---- tail
        finished = emb
        ball_info = None
        if tail == "mm":
            remaining = ((deadline - time.perf_counter()) if deadline
                         else FALLBACK_TIMEOUT)
            if remaining > 0:
                ground = _mm_route(source_graph, target_graph, warm=emb,
                                   seed=seed, timeout=remaining) or emb
                if is_valid_embedding(ground, source_graph, target_graph,
                                      adj=adj):
                    finished = ground
            from ember_qc.algorithms.factored.ball import ball_polish
            balled, ball_info = ball_polish(
                finished, source_graph, target_graph,
                deadline=deadline, adj=adj, grid=grid)
            if is_valid_embedding(balled, source_graph, target_graph,
                                  adj=adj):
                finished = balled

        # ---- diagnostics
        widths = bar_widths(books[1])
        sizes = (np.array([widths[v].sum() for v in widths])
                 if widths else np.zeros(1))
        diag = {
            "extent_mean": round(float(sizes.mean()), 3),
            "extent_max": round(float(sizes.max()), 3),
            "stride": int(grid.stride),
            "max_chain": max(len(c) for c in finished.values()),
            "arrange_wall": round(arrange_wall, 2),
            "legal_acl": round(float(legal_acl), 3),
            "legal_max_chain": int(legal_max_chain),
        }
        for k in ("asks", "accepts", "passes", "readouts", "bookmark_asks",
                  "bookmark_wall", "stopped_by", "pen", "stair", "bars",
                  "misses", "adopt_worse", "infeasible"):
            diag[k] = info.get(k)
        diag["accept_traj"] = list(info.get("accept_traj", []))[:12]
        _mes = 0.0
        for _u in src_adj:
            for _v in src_adj[_u]:
                if _u < _v and _u in tpts and _v in tpts:
                    _mes = max(_mes,
                               abs(float(tpts[_u][0] - tpts[_v][0]))
                               + abs(float(tpts[_u][1] - tpts[_v][1])))
        diag["max_edge_span"] = round(_mes, 1)
        if conv_info is not None:
            diag["convert_miss"] = int(conv_info["convert_miss"])
            # the certificate: every arm seated its required hull AND
            # completion closed — the prediction the validity check
            # (the paranoia net) is checked against
            diag["certified"] = bool(
                conv_info["convert_miss"] == 0
                and ex_info is not None
                and ex_info.get("deficit_edges", 1) == 0
                and ex_info.get("corner_deficit", 1) == 0)
        if eff_exact:
            diag["mm_skipped"] = mm_skipped
            if ex_info is not None:
                for k in ("deficit_edges", "corner_deficit", "extensions",
                          "ext_qubits", "bridges"):
                    diag[k] = ex_info[k]
        if ball_info is not None:
            diag["ball_accepts"] = ball_info["accepted"]
            diag["ball_tried"] = ball_info["tried"]
            diag["ball_wall"] = round(ball_info["wall"], 1)
        return {"embedding": finished,
                "time": time.perf_counter() - start,
                "stair_E": stair_E,
                "legal_acl": round(legal_acl, 3),
                "diag": diag}
    except Exception as exc:  # noqa: BLE001 — the contract: never raise
        logger.exception("attraction embed error: %s", exc)
        return _failure(error=str(exc))
