"""Diagnose clique order plateaus without changing the native algorithm.

Run: .venv/bin/python docs/paper2/data/three_order_clique_search_probe.py
The tied-slot shuffles below are diagnostic interventions, not production moves.
"""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import dwave_networkx as dnx
import networkx as nx
import numpy as np

from ember_qc.algorithms.factored import plane
from ember_qc.algorithms.factored.native_model import Source, complete_coordinates
from ember_qc.algorithms.factored.order_dp import interleave, score_layout
from ember_qc.algorithms.factored.placement import ZephyrFabric, materialize
from ember_qc.embedding_backend import is_valid_embedding


def run(n):
    graph = nx.complete_graph(n)
    source = Source.from_graph(graph)
    m = 3 if n == 10 else 12
    target = dnx.zephyr_graph(m, 4)
    fabric = ZephyrFabric.from_graph(target)
    original_decode = plane.decode
    history = []

    def capture(*args, **kwargs):
        layout = original_decode(*args, **kwargs)
        history.append(layout)
        return layout

    def describe(layout):
        embedding = materialize(layout, source, fabric)
        assert is_valid_embedding(embedding, graph, target)
        return dict(score=layout.book.score, physical_qubits=sum(map(len, embedding.values())))

    with patch.object(plane, "decode", capture):
        best, info = plane.arrange(source, m, 4, seed=0, max_asks=50000)
    current = history[-1]
    orders = current.orders
    coords = complete_coordinates(orders, current.coords, current.book.active, 8)
    base_score = score_layout(orders, coords, source.indptr, source.indices, m)
    assert base_score[2] == n * (n * n - 1) // 2
    slots = np.array([coords[a, orders[a]] for a in range(2)])
    controls = {}
    for label, proposal in (
        ("x_equals_contact", np.array([orders[2], orders[1], orders[2]])),
        ("y_equals_contact", np.array([orders[0], orders[2], orders[2]])),
        ("all_aligned", np.tile(orders[2], (3, 1))),
    ):
        trial_coords = coords.copy()
        for axis in range(2):
            trial_coords[axis, proposal[axis]] = slots[axis]
        controls[label] = dict(
            frozen_score=score_layout(proposal, trial_coords, source.indptr, source.indices, m),
            decoded=describe(plane.decode(proposal, source, m, 4)))

    runs = []
    for seed in range(5):
        rng = np.random.default_rng(seed)
        proposal = orders.copy()
        for axis in range(2):
            for slot in np.unique(coords[axis]):
                ids = np.flatnonzero(coords[axis, proposal[axis]] == slot)
                proposal[axis, ids] = rng.permutation(proposal[axis, ids])
        before = score_layout(proposal, coords, source.indptr, source.indices, m)
        assert before == base_score
        assert np.array_equal(proposal[2], orders[2])
        neutral = describe(plane.decode(proposal, source, m, 4))
        trial_coords = coords.copy()
        frozen_slots = np.array([coords[a, proposal[a]] for a in range(2)])
        accepts = 0
        for axis, unit in plane.units(proposal, source, rng):
            result, _ = interleave(proposal, trial_coords, source.indptr,
                                   source.indices, axis, unit, m)
            if result is None:
                continue
            accepts += 1
            proposal[axis] = result
            if axis < 2:
                trial_coords[axis, result] = frozen_slots[axis]
        runs.append(dict(seed=seed, frozen_before=before, neutral_decode=neutral,
                         strict_accepts=accepts,
                         frozen_after=score_layout(proposal, trial_coords, source.indptr, source.indices, m),
                         decoded_after=describe(plane.decode(proposal, source, m, 4))))
    return dict(n=n, chip_m=m, seed=0, asks=info["asks"], stopped_by=info["stopped_by"],
                accept_traj=info["accept_traj"], history=[describe(d) for d in history],
                bookmark=describe(best), current=describe(current),
                current_orders=orders.tolist(), current_coords=current.coords.tolist(),
                controls=controls, neutral_shuffle_runs=runs)


if __name__ == "__main__":
    digest = hashlib.sha256()
    for file in sorted(Path(plane.__file__).parent.glob("*.py")):
        digest.update(file.name.encode())
        digest.update(file.read_bytes())
    result = dict(code_hash=digest.hexdigest(), cases=[run(10), run(100)])
    output = Path(__file__).with_suffix(".json")
    output.write_text(json.dumps(result, indent=2) + "\n")
    for case in result["cases"]:
        print(case["n"], "current", case["current"], "neutral-then-sweep",
              [r["decoded_after"] for r in case["neutral_shuffle_runs"]])
