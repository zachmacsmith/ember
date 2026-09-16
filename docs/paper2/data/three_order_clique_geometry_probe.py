#!/usr/bin/env python3
"""Bounded clique diagnosis, not a production initializer or embedding algorithm.

Enumerate all K10 coordinate choices for one axis and pack the other exactly.
Also test whether retained old physical embeddings fit the new contact-order
model and separate reservation cost from course-coloring cost. Run from the
repository environment; no downloads or MinorMiner calls are made here.

Global reservation lower bound for K10 with eight tracks per lane: every
contact order has nine H arms sharing x_last and nine V arms sharing y_first.
Capacity therefore forces at least two H rows and two V columns. A mixed
vertex u on a column different from x_last makes both H_u and H_first span
distinct integer coordinates. Each such span reserves at least two bricks,
so H costs at least 9+2. The symmetric row argument gives V at least 9+2.
Thus R >= 22 over ALL orders and coordinates; native R=22 attains the bound.
This is a bound on reservations, not on physical qubits after course choice.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import time

import dwave_networkx as dnx
import networkx as nx
import numpy as np

from ember_qc.algorithms.factored.native_model import (
    Source, capacity_ok, make_book, packing_problem,
)
from ember_qc.algorithms.factored.packing import pack_axis
from ember_qc.algorithms.factored import plane as plane_module
from ember_qc.algorithms.factored.plane import Layout, arrange, decode
from ember_qc.algorithms.factored.placement import ZephyrFabric, materialize
from ember_qc.embedding_backend import is_valid_embedding


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def layout_summary(layout, source, fabric):
    embedding = materialize(layout, source, fabric)
    return dict(orders=layout.orders.tolist(), coords=layout.coords.tolist(),
                reserved=layout.book.reserved,
                greedy_physical_qubits=sum(map(len, embedding.values())))


def optimal_clique_colors(layout, source, fabric, graph, target):
    """Exact colors for THIS diagnostic: clique bars share a common junction.

    Every lane's interval graph is a clique, so selecting at most tile bars
    per physical course reduces to sorting the two course costs. This is not
    a general interval-coloring optimizer and is not used by production code.
    """
    book = layout.book
    embedding = {v: [] for v in source.labels}
    for axis in (0, 1):
        for lane in np.unique(layout.coords[axis, book.active[axis]]):
            vertices = np.flatnonzero(book.active[axis] & (layout.coords[axis] == lane))
            assert book.guard_lo[axis, vertices].max() <= book.guard_hi[axis, vertices].min()
            a, b = book.lo[axis, vertices], book.hi[axis, vertices]
            cost0 = b // 2 - a // 2 + 1
            cost1 = (b - 1) // 2 - (a - 1) // 2 + 1
            delta = cost1 - cost0
            ranked = np.argsort(delta, kind="stable")
            allowed = range(max(0, len(vertices) - fabric.tile), min(len(vertices), fabric.tile) + 1)
            count = min(allowed, key=lambda k: int(delta[ranked[:k]].sum()))
            course1 = set(map(int, vertices[ranked[:count]]))
            tracks = [0, 0]
            for v in vertices:
                course = int(int(v) in course1)
                track = tracks[course]
                tracks[course] += 1
                for z in range((int(book.lo[axis, v]) - course) // 2,
                               (int(book.hi[axis, v]) - course) // 2 + 1):
                    embedding[int(v)].append(fabric.lookup[axis, int(lane), track, course, z])
    assert is_valid_embedding(embedding, graph, target)
    return sum(map(len, embedding.values()))


def exhaustive_k10(layout, source, fabric):
    """Global coordinate optimum: all 715 x choices times exact y recourse."""
    started = time.perf_counter()
    orders, coords = layout.orders, layout.coords.copy()
    active = orders[0, layout.book.active[0, orders[0]]]
    best, witness, feasible, tested = None, None, 0, 0
    for xs in itertools.combinations_with_replacement(range(1, 2 * fabric.m), len(active)):
        tested += 1
        coords[0, active] = xs
        book = make_book(orders, coords, source.indptr, source.indices, fabric.m)
        problem = packing_problem(1, orders, coords, book)
        ys, info = pack_axis(*problem, capacity=2 * fabric.tile,
                             chip_m=fabric.m, extent_m=fabric.m)
        if ys is None:
            continue
        feasible += 1
        if best is None or info["objective"] < best:
            best = info["objective"]
            witness = coords.copy()
            witness[1, problem[0]] = ys
    book = make_book(orders, witness, source.indptr, source.indices, fabric.m)
    assert book.score == best and capacity_ok(book, witness, 2 * fabric.tile, fabric.m)
    # Reservation cost separates into a term for each coordinate axis. Use it
    # to enumerate every equal-best coordinate pair without a large loop.
    configs, costs = [], []
    for axis in (0, 1):
        active = orders[axis, layout.book.active[axis, orders[axis]]]
        matrix, values = [], []
        for chosen in itertools.combinations_with_replacement(range(1, 2 * fabric.m), len(active)):
            trial = layout.coords.copy()
            trial[axis, active] = chosen
            b = make_book(orders, trial, source.indptr, source.indices, fabric.m)
            vertices = b.active[1 - axis]
            values.append(int((b.guard_hi[1 - axis, vertices] - b.guard_lo[1 - axis, vertices] + 1).sum()))
            matrix.append(trial[axis].copy())
        configs.append(np.asarray(matrix))
        costs.append(np.asarray(values))
    candidates = np.argwhere(costs[0][:, None] + costs[1][None, :] == best[1])
    equal_feasible, physical_best, physical_witness = 0, None, None
    for ix, iy in candidates:
        trial = np.vstack((configs[0][ix], configs[1][iy]))
        b = make_book(orders, trial, source.indptr, source.indices, fabric.m)
        if not capacity_ok(b, trial, 2 * fabric.tile, fabric.m):
            continue
        equal_feasible += 1
        physical = sum(map(len, materialize(Layout(orders, trial, b, fabric.m), source, fabric).values()))
        if physical_best is None or physical < physical_best:
            physical_best, physical_witness = physical, trial.copy()
    return dict(x_assignments=tested, feasible_x_assignments=feasible,
                joint_reserved_optimum=best, witness=witness.tolist(),
                equal_optimum_pairs=equal_feasible,
                minimum_greedy_physical_at_equal_reservations=physical_best,
                equal_score_physical_witness=physical_witness.tolist(),
                seconds=time.perf_counter() - started)


def old_physical_witness(path, chip_m):
    capture = json.loads(path.read_text())
    embedding = {int(v): qubits for v, qubits in capture["embedding"].items()}
    n = len(embedding)
    graph, target = nx.complete_graph(n), dnx.zephyr_graph(chip_m, 4)
    source, fabric = Source.from_graph(graph), ZephyrFabric.from_graph(target)
    assert is_valid_embedding(embedding, graph, target)
    converter = dnx.zephyr_coordinates(chip_m, 4)
    physical = {q: converter.linear_to_zephyr(q) for qs in embedding.values() for q in qs}
    forced = nx.DiGraph()
    forced.add_nodes_from(embedding)
    missing = []
    for u, v in itertools.combinations(embedding, 2):
        uv = any(physical[a][0] == 1 and physical[b][0] == 0 and target.has_edge(a, b)
                 for a in embedding[u] for b in embedding[v])
        vu = any(physical[a][0] == 0 and physical[b][0] == 1 and target.has_edge(a, b)
                 for a in embedding[u] for b in embedding[v])
        if uv and not vu:
            forced.add_edge(u, v)
        elif vu and not uv:
            forced.add_edge(v, u)
        elif not uv and not vu:
            missing.append((u, v))
    result = dict(input_path=str(path.relative_to(ROOT)), input_sha256=sha(path),
                  n=n, chip_m=chip_m, old_physical_qubits=sum(map(len, embedding.values())),
                  pairs_without_cross_contact=missing, forced_precedences=forced.number_of_edges(),
                  forced_precedence_is_acyclic=nx.is_directed_acyclic_graph(forced))
    if missing or not result["forced_precedence_is_acyclic"]:
        if not result["forced_precedence_is_acyclic"]:
            result["forced_cycle"] = nx.find_cycle(forced)
        return result
    coords = np.ones((2, n), dtype=np.int64)
    bars = {}
    for v, qubits in embedding.items():
        for axis in (0, 1):
            bar = [physical[q] for q in qubits if physical[q][0] == axis]
            if not bar:
                continue
            assert len({q[1:4] for q in bar}) == 1
            coords[axis, v] = bar[0][1]
            bars[axis, v] = bar[0][2], bar[0][3], {q[4] for q in bar}
    orders = np.asarray([np.argsort(coords[0], kind="stable"),
                         np.argsort(coords[1], kind="stable"), list(nx.topological_sort(forced))])
    book = make_book(orders, coords, source.indptr, source.indices, chip_m)
    result["conservative_capacity_fits"] = capacity_ok(book, coords, 8, chip_m)
    required = {v: [] for v in source.labels}
    for axis in (0, 1):
        for v in np.flatnonzero(book.active[axis]):
            track, course, available = bars[axis, v]
            indices = range((int(book.lo[axis, v]) - course) // 2,
                            (int(book.hi[axis, v]) - course) // 2 + 1)
            assert set(indices) <= available
            required[int(v)].extend(fabric.lookup[axis, int(coords[axis, v]), track, course, z] for z in indices)
    assert is_valid_embedding(required, graph, target)
    result["designated_contacts_fit_existing_qubits"] = True
    result["required_existing_physical_qubits"] = sum(map(len, required.values()))
    original = Layout(orders, coords, book, chip_m)
    canonical = decode(orders, source, chip_m, 4, seed=0)
    for name, layout in (("old_coordinates", original), ("canonical_same_orders", canonical)):
        record = layout_summary(layout, source, fabric)
        record["optimal_course_physical_qubits"] = optimal_clique_colors(layout, source, fabric, graph, target)
        result[name] = record
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    source_graph, target = nx.complete_graph(10), dnx.zephyr_graph(3, 4)
    source, fabric = Source.from_graph(source_graph), ZephyrFabric.from_graph(target)
    # arrange returns its best reservation bookmark, which can differ from
    # the final accepted state even at the same reservation score. Capture
    # decoder output within this diagnostic without changing production code.
    native_final = None
    original_decode = plane_module.decode

    def capture_final(*decode_args, **decode_kwargs):
        nonlocal native_final
        native_final = original_decode(*decode_args, **decode_kwargs)
        return native_final

    plane_module.decode = capture_final
    try:
        native, info = arrange(source, 3, 4, seed=0, max_asks=50000)
    finally:
        plane_module.decode = original_decode
    assert native_final is not None
    aligned = decode(np.tile(np.arange(10), (3, 1)), source, 3, 4)
    result = dict(kind="clique_geometry_diagnosis", created_utc=datetime.now(timezone.utc).isoformat(),
                  scope="Fixed-order coordinate exactness and physical representation/cost diagnosis; no production changes.",
                  native_seed=0, native_asks=info["asks"], native_stopped_by=info["stopped_by"],
                  code_sha256={name: sha(ROOT / "packages/ember-qc/src/ember_qc/algorithms/factored" / name)
                               for name in ("plane.py", "packing.py", "native_model.py", "order_dp.py", "placement.py")},
                  k10={}, old_physical=[])
    for name, layout in (("native", native), ("aligned", aligned)):
        record = layout_summary(layout, source, fabric)
        record["selection"] = "best reservation bookmark" if name == "native" else "aligned control"
        record["optimal_course_physical_qubits"] = optimal_clique_colors(layout, source, fabric, source_graph, target)
        record["exhaustive"] = exhaustive_k10(layout, source, fabric)
        result["k10"][name] = record
    record = layout_summary(native_final, source, fabric)
    record["selection"] = "final accepted state"
    record["optimal_course_physical_qubits"] = optimal_clique_colors(
        native_final, source, fabric, source_graph, target)
    result["k10"]["native_final"] = record
    for n, chip_m in ((10, 3), (100, 12)):
        result["old_physical"].append(old_physical_witness(HERE / f"three_order_clique_old_{n}.json", chip_m))
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
        print(args.out)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
