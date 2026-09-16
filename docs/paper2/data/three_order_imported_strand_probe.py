"""Check imported-order strands and retain one clique diagnostic witness.

Run: .venv/bin/python docs/paper2/data/three_order_imported_strand_probe.py

The production wrapper extracts a unit in the destination order. Its private
two-prefix kernel can instead merge ANY prescribed strand with the destination
complement. Exhaustive tiny cases below check that observation independently.
The retained K100 case imports entire other orders (including reversal), so its
complement is empty. It demonstrates a missing macro move, not a board-wide win
or a convergence guarantee. No production search or acceptance rule is changed.
"""

import hashlib
import itertools
import json
from pathlib import Path
import time

import dwave_networkx as dnx
import networkx as nx
import numpy as np

from ember_qc.algorithms.factored import plane
from ember_qc.algorithms.factored.native_model import (
    Source, complete_coordinates, make_book,
)
from ember_qc.algorithms.factored.order_dp import _solve, score_layout
from ember_qc.algorithms.factored.placement import ZephyrFabric, materialize
from ember_qc.embedding_backend import is_valid_embedding


def direct_score(graph, orders, coords, chip_m, rank_axis):
    """Independent vertex/neighbor oracle, with no production cost helper."""
    ranks = [{int(v): i for i, v in enumerate(order)} for order in orders]
    outside = reserved = 0
    for v in graph:
        earlier = [u for u in graph[v] if ranks[2][u] < ranks[2][v]]
        later = [u for u in graph[v] if ranks[2][u] > ranks[2][v]]
        mixed = bool(earlier and later)
        for axis, neighbors in ((0, earlier), (1, later)):
            if not neighbors:
                continue
            endpoints = [int(coords[1 - axis, u]) for u in neighbors]
            if mixed:
                endpoints.append(int(coords[1 - axis, v]))
            first = (min(endpoints) - 1) // 2
            last = max(endpoints) // 2
            reserved += last - first + 1
            for brick in range(first, last + 1):
                outside += int(coords[axis, v] > 2 * chip_m - 1 or brick >= chip_m)
    span = sum(abs(ranks[rank_axis][u] - ranks[rank_axis][v])
               for u, v in graph.edges())
    return outside, reserved, span


def merges(part, rest):
    for selected_positions in itertools.combinations(range(len(part) + len(rest)), len(part)):
        selected_positions = set(selected_positions)
        left, right = iter(part), iter(rest)
        yield np.asarray([next(left) if k in selected_positions else next(right)
                          for k in range(len(part) + len(rest))], dtype=np.int64)


def verify_imported_strands():
    rng = np.random.default_rng(917)
    problems = candidates = reordered_strands = 0
    for n in range(3, 7):
        for kind in ("path", "cycle", "random"):
            graph = (nx.path_graph(n) if kind == "path" else nx.cycle_graph(n)
                     if kind == "cycle" else nx.gnp_random_graph(n, 0.53, seed=100 + n))
            # Preserve every ID even in the random case: the DP supports zero
            # degree vertices although the public pipeline normally removes them.
            indptr = np.zeros(n + 1, dtype=np.int64)
            indices = []
            for v in range(n):
                indices.extend(sorted(graph[v]))
                indptr[v + 1] = len(indices)
            indices = np.asarray(indices, dtype=np.int64)
            orders = np.asarray([rng.permutation(n) for _ in range(3)], dtype=np.int64)
            coords = np.empty((2, n), dtype=np.int64)
            for axis in range(2):
                # Include tied slots, both parities, and out-of-chip positions.
                slots = np.sort(rng.integers(1, 8, size=n))
                coords[axis, orders[axis]] = slots
            selected = set(int(v) for v in rng.permutation(n)[:n // 2])
            for axis in range(3):
                rest = np.asarray([v for v in orders[axis] if int(v) not in selected], dtype=np.int64)
                original = [int(v) for v in orders[axis] if int(v) in selected]
                for donor in range(3):
                    if donor == axis:
                        continue
                    strand = np.asarray([v for v in orders[donor] if int(v) in selected], dtype=np.int64)
                    for reverse in (False, True):
                        part = np.ascontiguousarray(strand[::-1] if reverse else strand)
                        reordered_strands += int(part.tolist() != original)
                        result, cost = _solve(orders, coords, indptr, indices,
                                              axis, part, rest, 2)
                        scores = {}
                        for merged in merges(part, rest):
                            trial_orders, trial_coords = orders.copy(), coords.copy()
                            trial_orders[axis] = merged
                            if axis < 2:
                                trial_coords[axis, merged] = coords[axis, orders[axis]]
                            scores[tuple(merged)] = direct_score(
                                graph, trial_orders, trial_coords, 2, axis)
                            candidates += 1
                        assert tuple(int(x) for x in cost) == min(scores.values())
                        assert scores[tuple(result)] == min(scores.values())
                        problems += 1
    assert reordered_strands
    return dict(problems=problems, exhaustive_candidates=candidates,
                strands_differing_from_destination=reordered_strands,
                vertex_counts=[3, 4, 5, 6], graph_types=["path", "cycle", "random"],
                axes=[0, 1, 2], chip_m=2, passed=True)


def whole_order_witness():
    source_path = Path(__file__).with_name("three_order_clique_search_probe.json")
    case = next(c for c in json.loads(source_path.read_text())["cases"] if c["n"] == 100)
    graph = nx.complete_graph(case["n"])
    source = Source.from_graph(graph)
    m = case["chip_m"]
    target = dnx.zephyr_graph(m, 4)
    fabric = ZephyrFabric.from_graph(target)
    orders = np.asarray(case["current_orders"], dtype=np.int64)
    raw_coords = np.asarray(case["current_coords"], dtype=np.int64)
    book = make_book(orders, raw_coords, source.indptr, source.indices, m)
    before = plane.Layout(orders.copy(), raw_coords, book, m)

    def describe(layout):
        embedding = materialize(layout, source, fabric)
        assert is_valid_embedding(embedding, graph, target)
        return dict(score=layout.book.score,
                    physical_qubits=sum(map(len, embedding.values())), valid=True)

    coords = complete_coordinates(orders, raw_coords, book.active, 8)
    initial_score = score_layout(orders, coords, source.indptr, source.indices, m)
    stages = []
    for axis in (0, 1):
        slots = coords[axis, orders[axis]].copy()
        current_score = score_layout(orders, coords, source.indptr, source.indices, m)
        best_score, best_order, chosen = current_score, orders[axis].copy(), "incumbent"
        candidates = []
        for donor in range(3):
            if donor == axis:
                continue
            for reverse in (False, True):
                part = np.ascontiguousarray(orders[donor, ::-1] if reverse else orders[donor])
                order, cost = _solve(orders, coords, source.indptr, source.indices,
                                     axis, part, np.empty(0, dtype=np.int64), m)
                trial_orders, trial_coords = orders.copy(), coords.copy()
                trial_orders[axis] = order
                trial_coords[axis, order] = slots
                score = score_layout(trial_orders, trial_coords, source.indptr, source.indices, m)
                assert tuple(int(x) for x in cost[:2]) == score[:2]
                label = "xyt"[donor] + (" reversed" if reverse else " forward")
                candidates.append(dict(strand=label, frozen_score=score))
                if score < best_score:
                    best_score, best_order, chosen = score, order.copy(), label
        orders[axis] = best_order
        coords[axis, best_order] = slots
        stages.append(dict(axis="xy"[axis], chosen=chosen, before=current_score,
                           after=best_score, candidates=candidates))
    after = plane.decode(orders, source, m, 4, seed=0)
    return dict(n=100, chip_m=m, source_file=source_path.name,
                source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                before=describe(before), frozen_before=initial_score, stages=stages,
                decoded_after=describe(after), final_orders=orders.tolist(),
                final_coords=after.coords.tolist(),
                limitation="One retained clique state; no board-wide or convergence claim.")


if __name__ == "__main__":
    started = time.perf_counter()
    result = dict(exhaustive_checks=verify_imported_strands(),
                  whole_order_witness=whole_order_witness())
    result["wall_seconds"] = time.perf_counter() - started
    Path(__file__).with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(checks=result["exhaustive_checks"],
                          before=result["whole_order_witness"]["before"],
                          after=result["whole_order_witness"]["decoded_after"],
                          wall_seconds=result["wall_seconds"])))
