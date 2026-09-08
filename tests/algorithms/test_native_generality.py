"""Metamorphic source controls for the independent native constructor.

Run with pytest, or directly with the isolated interpreter (pytest is not a
dependency of this module):

  PYTHONPATH=packages/ember-qc/src .venv/codex-native/bin/python \
      tests/algorithms/test_native_generality.py

The executable audit reports label/order controls and tiny construction
diagnostics. It does not compare algorithms or estimate benchmark performance.
"""
from copy import deepcopy
import importlib.util
import json
import random
import sys
import time

import networkx as nx
import dwave_networkx as dnx

from ember_qc.algorithms.factored.contact_repair import contact_polish
from ember_qc.algorithms.factored.native import native_embed


def _assert_valid(embedding, source, target):
    assert set(embedding) == set(source)
    occupied = []
    for chain in embedding.values():
        assert chain and set(chain) <= set(target)
        assert len(chain) == len(set(chain))
        assert nx.is_connected(target.subgraph(chain))
        occupied.extend(chain)
    assert len(occupied) == len(set(occupied))
    for v, w in source.edges():
        assert any(target.has_edge(q, r) for q in embedding[v] for r in embedding[w])


def _source():
    graph = nx.cycle_graph(12)
    graph.add_edges_from([(0, 6), (1, 5), (3, 9)])
    graph.add_node(20)  # Isolated nodes must survive every source transformation.
    return graph


def _solve(source, target, construction="packed"):
    return native_embed(source, target, construction=construction,
                        order_strategy="random", seed=4, packing_passes=2,
                        max_asks=20, polish_passes=1, max_groups=3, timeout=10)


def test_source_relabeling_preserves_normalized_algorithm_path():
    source, target = _source(), dnx.zephyr_graph(3)
    mapping = {v: ("label", i) if i % 3 == 0 else f"variable-{100-i}"
               if i % 3 == 1 else 1000 + i
               for i, v in enumerate(source)}
    renamed = nx.relabel_nodes(source, mapping, copy=True)
    for construction in ("packed", "search"):
        baseline = _solve(source, target, construction)
        transformed = _solve(renamed, target, construction)
        assert baseline["success"] and transformed["success"]
        restored = {v: transformed["embedding"][mapping[v]] for v in source}
        assert restored == baseline["embedding"]
        _assert_valid(transformed["embedding"], renamed, target)


def test_source_edge_insertion_order_is_irrelevant_with_fixed_node_order():
    source, target = _source(), dnx.zephyr_graph(3)
    reordered = nx.Graph()
    reordered.add_nodes_from(source)
    reordered.add_edges_from((v, u) for u, v in reversed(list(source.edges())))
    for construction in ("packed", "search"):
        baseline = _solve(source, target, construction)
        transformed = _solve(reordered, target, construction)
        assert baseline["success"] and transformed["success"]
        assert transformed["embedding"] == baseline["embedding"]


def test_source_family_names_and_ids_do_not_select_behavior():
    source, target = _source(), dnx.zephyr_graph(3)
    for construction in ("packed", "search"):
        baseline = _solve(source, target, construction)
        assert baseline["success"]
        for metadata in (
            {"family": "complete", "graph_type": "king_graph", "id": 1590,
             "name": "K100", "embedding": {"ignored": [999999]}},
            {"family": "unseen_category", "graph_type": "arbitrary",
             "graph_id": -123, "name": "unrelated_metadata"},
        ):
            tagged = source.copy()
            tagged.graph.update(metadata)
            nx.set_node_attributes(tagged, "unrelated", "family")
            snapshot = deepcopy(tagged.graph)
            transformed = _solve(tagged, target, construction)
            assert transformed["success"]
            assert transformed["embedding"] == baseline["embedding"]
            assert tagged.graph == snapshot


def test_contact_search_ignores_source_insertion_order_and_metadata():
    source, target = nx.path_graph(3), nx.path_graph(9)
    incumbent = {0: [0, 1, 2], 1: [3, 4, 5], 2: [6, 7, 8]}
    reordered = nx.Graph(family="unseen", name="anything", graph_id=-1)
    reordered.add_nodes_from(reversed(list(source)))
    reordered.add_edges_from(reversed(list(source.edges())))
    a, da = contact_polish(incumbent, source, target, max_groups=8)
    b, db = contact_polish(incumbent, reordered, target, max_groups=8)
    assert a == b
    assert da["expansions"] == db["expansions"]
    _assert_valid(a, source, target)


def _cases():
    cycle = nx.cycle_graph(24)
    cycle.add_edges_from([(0, 12), (1, 13), (7, 18)])
    return [
        ("cycle_with_chords_24", cycle),
        ("regular_32_degree3", nx.random_regular_graph(3, 32, seed=7)),
        ("er_30_p016", nx.gnp_random_graph(30, 0.16, seed=9)),
        ("star_40", nx.star_graph(39)),
    ]


def _insertion_rows():
    target = dnx.zephyr_graph(3)
    rows = []
    for name, graph in _cases():
        for variant in ("base", "reverse", "shuffle"):
            nodes = list(graph)
            if variant == "reverse":
                nodes.reverse()
            elif variant == "shuffle":
                random.Random(811).shuffle(nodes)
            source = nx.Graph()
            source.add_nodes_from(nodes)
            source.add_edges_from(graph.edges())
            result = _solve(source, target)
            assert result["success"], result
            _assert_valid(result["embedding"], source, target)
            repair = result["diag"].get("contact_repair", {})
            rows.append({
                "case": name, "node_order": variant, "status": result["status"],
                "qubits": sum(map(len, result["embedding"].values())),
                "wall": result["time"], "repair_wall": repair.get("wall"),
                "repair_expansions": repair.get("expansions"),
                "tree_attempts": repair.get("tree_attempts"),
            })
    return rows


def test_node_insertion_variants_remain_valid_without_assuming_equal_quality():
    # Arbitrary fixed-seed output equality under reordered nodes is not an API
    # guarantee. This tests validity; the executable audit reports quality drift.
    assert len(_insertion_rows()) == 12


def _construction_rows():
    rows = []
    for m, n in ((2, 40), (3, 80)):
        target = dnx.zephyr_graph(m)
        source = nx.path_graph(n)
        # A direct independent existence witness: a simple physical DFS-tree
        # path gives a one-qubit chain for each source vertex, with ACL exactly 1.
        witness_path = nx.dag_longest_path(nx.dfs_tree(target, source=0))[:n]
        assert len(witness_path) == n
        witness = {v: [witness_path[v]] for v in source}
        _assert_valid(witness, source, target)
        result = native_embed(source, target, construction="packed",
                              order_strategy="random", seed=4, packing_passes=2,
                              polish_passes=0, timeout=10)
        if result["success"]:
            _assert_valid(result["embedding"], source, target)
        else:
            assert result["status"] == "CONSTRUCTION_FAILED"
            assert not result["embedding"] and result.get("partial_embedding")
        rows.append({"zephyr_size": m, "source_vertices": n,
                     "witness_acl": 1, "status": result["status"],
                     "wall": result["time"], "diag": result["diag"]})
    return rows


def test_a_feasible_path_is_either_validly_constructed_or_reported_incomplete():
    # Do not freeze today's failure as desired behavior. A future general
    # constructor may succeed; it must not silently certify incomplete chains.
    assert len(_construction_rows()) == 2


if __name__ == "__main__":
    started = time.perf_counter()
    checks = [value for name, value in list(globals().items())
              if name.startswith("test_") and callable(value)]
    for check in checks:
        check()
    print(json.dumps({
        "checks_passed": len(checks), "check_wall": time.perf_counter() - started,
        "python": sys.executable, "prefix": sys.prefix,
        "networkx": nx.__version__, "dwave_networkx": dnx.__version__,
        "mm_available": importlib.util.find_spec("minorminer") is not None,
        "loaded_embedding_libraries": [name for name in sys.modules
            if name.split(".")[0] in {"minorminer", "_minorminer", "busclique"}],
        "imported_comparator_wrappers": [name for name in sys.modules
            if name.startswith("ember_qc.algorithms.minorminer")],
        "insertion_controls": _insertion_rows(),
        "construction_controls": _construction_rows(),
    }, indent=2))
