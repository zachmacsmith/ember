"""Native three-order embedding on intact Zephyr; optional explicit MM polish."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
import logging
import math
import time
from typing import Dict, List, Optional, Sequence

import networkx as nx
import numpy as np

from ember_qc.embedding_backend import Embedding, build_adjacency, is_valid_embedding
from .native_model import Source, capacity_ok

logger = logging.getLogger(__name__)
Point = np.ndarray


def _auto_bins(n_qubits: int) -> int:
    """Drawing resolution used by the separately callable legacy ball utility."""
    return max(4, min(16, int(math.sqrt(n_qubits) / 5)))


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


@dataclass
class ZephyrFabric:
    m: int
    tile: int
    lookup: dict
    qubits: tuple

    @classmethod
    def from_graph(cls, target):
        import dwave_networkx as dnx
        if target.is_directed() or target.is_multigraph() or target.graph.get("family") != "zephyr":
            raise ValueError("unsupported target: native attraction requires intact Zephyr")
        m = int(target.graph.get("rows", 0))
        tile = int(target.graph.get("tile", 0))
        labels = target.graph.get("labels")
        if m < 1 or tile < 1 or labels not in ("int", "coordinate"):
            raise ValueError("unsupported Zephyr metadata or node labels")
        expected = dnx.zephyr_graph(m, tile, coordinates=labels == "coordinate", data=False)
        if (set(target) != set(expected) or target.number_of_edges() != expected.number_of_edges()
                or any(not target.has_edge(u, v) for u, v in expected.edges())):
            raise ValueError("unsupported target: native attraction currently requires intact Zephyr")
        converter = dnx.zephyr_coordinates(m, tile)
        lookup = {}
        for q in target:
            coordinate = q if labels == "coordinate" else converter.linear_to_zephyr(q)
            lookup[tuple(int(k) for k in coordinate)] = q
        return cls(m, tile, lookup, tuple(sorted(target)))


def materialize(layout, source, fabric):
    """Color the certified reservations, then take actual same-course runs."""
    book, coords = layout.book, layout.coords
    if book.outside or not capacity_ok(book, coords, 2 * fabric.tile, fabric.m):
        raise AssertionError("only a fitting conservative book can be materialized")
    if book.reserved + len(source.isolates) > len(fabric.qubits):
        raise AssertionError("book does not reserve room for isolated vertices")
    embedding = {v: [] for v in source.labels}
    occupied = set()
    guard_lo, guard_hi = book.guard_lo, book.guard_hi
    for axis in range(2):
        lanes = {}
        for v in np.flatnonzero(book.active[axis]):
            lanes.setdefault(int(coords[axis, v]), []).append(
                (int(guard_lo[axis, v]), int(guard_hi[axis, v]), int(v)))
        for lane, arms in sorted(lanes.items()):
            busy = []
            free = list(range(2 * fabric.tile))
            heapq.heapify(free)
            for lo, hi, v in sorted(arms):
                while busy and busy[0][0] < lo:
                    _, color = heapq.heappop(busy)
                    heapq.heappush(free, color)
                if not free:
                    raise AssertionError("reservation coloring exhausted its proven capacity")
                color = heapq.heappop(free)
                heapq.heappush(busy, (hi, color))
                track, course = divmod(color, 2)
                a = (int(book.lo[axis, v]) - course) // 2
                b = (int(book.hi[axis, v]) - course) // 2
                chain = embedding[source.labels[v]]
                for z in range(a, b + 1):
                    q = fabric.lookup[axis, lane, track, course, z]
                    if q in occupied:
                        raise AssertionError("conservative coloring reused a physical qubit")
                    chain.append(q)
                    occupied.add(q)
    free_qubits = (q for q in fabric.qubits if q not in occupied)
    for v in source.isolates:
        embedding[v] = [next(free_qubits)]
    return embedding


def attract_embed(source_graph: nx.Graph, target_graph: nx.Graph, *,
                  timeout: float = 300.0, seed: int = 0,
                  max_asks: Optional[int] = None,
                  sched_seed: Optional[int] = None, tail: str = "none", **ignored) -> dict:
    """Standalone native result; unknown historical keyword arguments are ignored.

    tail='mm' requests only postprocessing of a successful native embedding.
    Unsupported hardware or a missing finite bookmark returns an explicit
    failure, never a routed fallback or a partial success.
    """
    start = time.perf_counter()
    deadline = start + timeout if timeout else None
    diag = dict(mm_calls=0, mm_skipped=True, certified=False)

    def failure(error):
        return dict(embedding={}, time=time.perf_counter() - start,
                    success=False, status="FAILURE", error=error, diag=diag)

    try:
        if tail not in ("none", "mm"):
            raise ValueError("unknown tail %r" % tail)
        if max_asks is not None and max_asks < 1:
            raise ValueError("max_asks must be >= 1")
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be nonnegative")
        if not source_graph or len(source_graph) > len(target_graph):
            return failure("empty source or insufficient target qubits")
        fabric = ZephyrFabric.from_graph(target_graph)
        source = Source.from_graph(source_graph)
        from . import plane
        layout, metrics = plane.arrange(
            source, fabric.m, fabric.tile, seed=int(seed), max_asks=max_asks,
            deadline=deadline, sched_seed=sched_seed,
            trace=bool(ignored.get("trace", False)), target_qubits=len(target_graph))
        diag.update(metrics)
        diag["stride"] = 2
        if layout is None:
            return failure("no native embedding fitting the chip was found within the budget")
        embedding = materialize(layout, source, fabric)
        adj = build_adjacency(target_graph)
        if not is_valid_embedding(embedding, source_graph, target_graph, adj=adj):
            raise AssertionError("native materialization failed independent embedding validation")
        native_q = sum(map(len, embedding.values()))
        native_max = max(map(len, embedding.values()))
        diag.update(certified=True, native_physical_qubits=native_q,
                    legal_acl=native_q / len(source_graph), legal_max_chain=native_max,
                    deficit_edges=0, corner_deficit=0, extensions=0,
                    ext_qubits=0, bridges=0, convert_miss=0)
        # Historical tail opt-in remains explicit; it is never legalization.
        if tail == "mm":
            remaining = max(0.0, deadline - time.perf_counter()) if deadline else 60.0
            if remaining:
                diag["mm_calls"] += 1
                diag["mm_skipped"] = False
                try:
                    polished = _mm_route(source_graph, target_graph, warm=embedding,
                                         seed=seed, timeout=remaining)
                except Exception as exc:
                    diag["polish_error"] = str(exc)
                    polished = None
                if (polished and is_valid_embedding(polished, source_graph, target_graph, adj=adj)
                        and sum(map(len, polished.values())) < native_q):
                    embedding = polished
        lengths = [len(c) for c in embedding.values()]
        widths = (layout.book.hi - layout.book.lo + 1)[layout.book.active]
        diag.update(physical_qubits=sum(lengths), max_chain=max(lengths),
                    extent_mean=float(widths.mean()) if len(widths) else 0.0,
                    extent_max=int(widths.max()) if len(widths) else 0)
        return dict(embedding=embedding, time=time.perf_counter() - start,
                    success=True, status="SUCCESS", stair_E=layout.book.reserved,
                    legal_acl=diag["legal_acl"], diag=diag)
    except Exception as exc:
        logger.debug("native attraction failed", exc_info=True)
        return failure(str(exc))
