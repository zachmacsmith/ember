"""Retained conditional-packing pilot; no embedding-quality claim.

Run from the repository with its virtualenv, for example:
  .venv/bin/python docs/paper2/data/three_order_packing_probe.py --out /tmp/packing.json

The input is a local Ember graph JSON. The default is the WS17188 dataset next
to this repository; use --graph when the dataset is elsewhere. No download or
minorminer call is made. Report startup separately from repeated warm cuts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import networkx as nx
import numba
import numpy as np

from ember_qc.algorithms.factored.native_model import (
    Source, capacity_ok, make_book, packing_problem,
)
from ember_qc.algorithms.factored.packing import pack_axis


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH = (ROOT.parent / "ember-qc-data" / "ember-qc" / "graphs"
                 / "17188_ws_n486_k4_b0.30_s0.json")


def run(graph_path, seed, chip_m, tile, requested_extent, repeats):
    raw = graph_path.read_bytes()
    payload = json.loads(raw)
    data = payload["graph"]
    graph = nx.Graph()
    graph.add_nodes_from(node["id"] for node in data["nodes"])
    graph.add_edges_from((edge["source"], edge["target"])
                         for edge in data.get("edges", data.get("links", [])))
    source = Source.from_graph(graph)
    n = len(source.labels)
    rng = np.random.default_rng(seed)
    orders = np.asarray([rng.permutation(n) for _ in range(3)], dtype=np.int64)
    capacity = 2 * tile
    coords = np.ones((2, n), dtype=np.int64)
    started = time.perf_counter()
    book = make_book(orders, coords, source.indptr, source.indices, chip_m)
    groups = 1
    for axis in (0, 1):
        active = orders[axis][book.active[axis, orders[axis]]]
        coords[axis, active] = 1 + np.arange(len(active)) // capacity
        groups = max(groups, (len(active) + capacity - 1) // capacity)
    minimum_extent = max(chip_m, (groups + 2) // 2)
    extent = minimum_extent if requested_extent is None else requested_extent
    if extent < minimum_extent:
        raise ValueError(f"extent_m must be at least {minimum_extent} for this canonical seed")
    book = make_book(orders, coords, source.indptr, source.indices, chip_m)
    initialization = time.perf_counter() - started
    assert capacity_ok(book, coords, capacity, extent)
    records = []
    for axis in (1, 0):
        problem = packing_problem(axis, orders, coords, book)
        rows = []
        reference = None
        for repeat in range(repeats + 1):
            lines, info = pack_axis(*problem, capacity=capacity,
                                   chip_m=chip_m, extent_m=extent)
            assert lines is not None
            if reference is not None:
                assert np.array_equal(lines, reference)
            reference = lines.copy()
            candidate_coords = coords.copy()
            candidate_coords[axis, problem[0]] = lines
            candidate_book = make_book(orders, candidate_coords,
                                       source.indptr, source.indices, chip_m)
            assert capacity_ok(candidate_book, candidate_coords, capacity, extent)
            assert candidate_book.score == info["objective"]
            rows.append(dict(info, startup=repeat == 0,
                             capacity_verified=True, shared_score_verified=True))
        coords, book = candidate_coords, candidate_book
        records.append(dict(axis=axis, active_items=len(problem[0]),
                            opposite_bars=len(problem[3]),
                            max_coordinate=int(reference.max()), runs=rows))
    code_hashes = {}
    for name in ("packing.py", "native_model.py"):
        path = ROOT / "packages/ember-qc/src/ember_qc/algorithms/factored" / name
        code_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(kind="conditional_packing_pilot", created_utc=datetime.now(timezone.utc).isoformat(),
                graph_path=str(graph_path), graph_sha256=hashlib.sha256(raw).hexdigest(),
                graph_id=payload.get("id"), nodes=len(graph), edges=graph.number_of_edges(),
                seed=seed, chip_m=chip_m, tile=tile, extent_m=extent,
                active_horizontal=int(book.active[1].sum()),
                active_vertical=int(book.active[0].sum()),
                initialization_seconds=initialization, python=platform.python_version(),
                numpy=np.__version__, numba=numba.__version__,
                load_average=os.getloadavg(), code_sha256=code_hashes, axes=records,
                scope="Two conditional axis packs from a canonical seed; not a search or embedding benchmark.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--chip-m", type=int, default=12)
    parser.add_argument("--tile", type=int, default=4)
    parser.add_argument("--extent-m", type=int)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    result = run(args.graph, args.seed, args.chip_m, args.tile, args.extent_m, args.repeats)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.write_text(rendered)
        print(args.out)
    else:
        print(rendered, end="")
