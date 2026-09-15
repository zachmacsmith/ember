"""Standalone native output, supported hardware, and explicit polish contracts."""
import dwave_networkx as dnx
import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored import attract_embed
from ember_qc.algorithms.factored import placement
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.registry import ALGORITHM_REGISTRY


@pytest.fixture(scope="module")
def zephyr():
    return dnx.zephyr_graph(3, 4)


@pytest.fixture(autouse=True)
def no_implicit_router(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("native embedding must not invoke MinorMiner")
    monkeypatch.setattr(placement, "_mm_route", forbidden)
    import minorminer
    monkeypatch.setattr(minorminer, "find_embedding", forbidden)


@pytest.mark.parametrize("source", [nx.path_graph(12), nx.complete_graph(10),
    nx.complete_bipartite_graph(7, 9), nx.disjoint_union(nx.cycle_graph(5), nx.path_graph(4))])
def test_native_valid_and_deterministic(source, zephyr):
    a = attract_embed(source, zephyr, timeout=0, seed=0, max_asks=200)
    b = attract_embed(source, zephyr, timeout=0, seed=0, max_asks=200)
    assert a["success"], a
    assert is_valid_embedding(a["embedding"], source, zephyr)
    assert a["embedding"] == b["embedding"]
    assert a["diag"]["certified"] and a["diag"]["mm_calls"] == 0
    assert a["diag"]["outside_reserved_qubits"] == 0
    assert a["diag"]["physical_qubits"] <= a["diag"]["reserved_qubits"]


def test_isolates_and_coordinate_labels():
    target = dnx.zephyr_graph(2, 3, coordinates=True)
    source = nx.Graph()
    source.add_edge("a", ("b", 1))
    source.add_nodes_from(["isolate", 100])
    result = attract_embed(source, target, timeout=0, max_asks=10)
    assert result["success"], result
    assert is_valid_embedding(result["embedding"], source, target)
    assert len(result["embedding"]["isolate"]) == 1
    assert len(result["embedding"][100]) == 1


def test_all_isolates_need_no_search(zephyr):
    source = nx.empty_graph(20)
    result = attract_embed(source, zephyr, timeout=0, max_asks=10)
    assert result["success"], result
    assert result["diag"]["asks"] == 0
    assert result["diag"]["physical_qubits"] == 20
    assert is_valid_embedding(result["embedding"], source, zephyr)


@pytest.mark.parametrize("target", [dnx.chimera_graph(3), dnx.pegasus_graph(3), nx.path_graph(40)])
def test_unsupported_targets_fail_without_fallback(target):
    result = attract_embed(nx.path_graph(5), target, max_asks=1)
    assert not result["success"] and result["status"] == "FAILURE"
    assert "unsupported" in result["error"]
    assert result["diag"]["mm_calls"] == 0


def test_defective_zephyr_is_explicitly_unsupported(zephyr):
    target = zephyr.copy()
    target.remove_edge(*next(iter(target.edges())))
    result = attract_embed(nx.path_graph(5), target, max_asks=1)
    assert not result["success"] and "intact" in result["error"]
    assert result["diag"]["mm_calls"] == 0


def test_missing_native_bookmark_is_failure():
    result = attract_embed(nx.complete_graph(20), dnx.zephyr_graph(1, 2),
                           timeout=0, max_asks=2)
    assert not result["success"]
    assert result["embedding"] == {}
    assert "no native embedding" in result["error"]
    assert result["diag"]["mm_calls"] == 0


def test_explicit_tail_is_postprocessing(monkeypatch, zephyr):
    calls = []
    def polish(source, target, *, warm, **kwargs):
        assert is_valid_embedding(warm, source, target)
        calls.append(warm)
        return warm
    monkeypatch.setattr(placement, "_mm_route", polish)
    result = attract_embed(nx.path_graph(8), zephyr, timeout=0,
                           max_asks=10, tail="mm")
    assert result["success"] and len(calls) == result["diag"]["mm_calls"] == 1


def test_registry_and_diagnostics(zephyr):
    source = nx.complete_graph(8)
    result = ALGORITHM_REGISTRY["attraction"].embed(
        source, zephyr, timeout=0, seed=0, max_asks=50)
    assert result["success"], result
    for key in ("reserved_qubits", "physical_qubits", "outside_reserved_qubits",
                "active_horizontal", "active_vertical", "packing_wall", "interleave_wall",
                "asks", "accepts", "passes", "readouts", "decode_calls", "mm_calls"):
        assert key in result["diag"]


def test_optional_polish_failure_preserves_native_result(monkeypatch, zephyr):
    def failed_polish(*args, **kwargs):
        raise RuntimeError("polish unavailable")
    monkeypatch.setattr(placement, "_mm_route", failed_polish)
    source = nx.path_graph(8)
    result = attract_embed(source, zephyr, timeout=0, max_asks=10, tail="mm")
    assert result["success"] and is_valid_embedding(result["embedding"], source, zephyr)
    assert result["diag"]["polish_error"] == "polish unavailable"


def test_bad_values_fail_and_historical_kwargs_are_ignored(zephyr):
    source = nx.path_graph(5)
    for kw, text in (({"tail": "grind"}, "tail"), ({"max_asks": 0}, "max_asks")):
        result = attract_embed(source, zephyr, **kw)
        assert result["status"] == "FAILURE" and text in result["error"]
    assert attract_embed(source, zephyr, timeout=0, max_asks=1,
                         max_rounds=1, gamma=0, state="cross")["success"]


def test_geometry_helpers_remain_available(zephyr):
    coords = np.array([[float(i), 0.] for i in range(10)])
    seeds = placement.snap({v: np.zeros(2) for v in range(5)}, coords,
                           list(range(10)), list(range(5)))
    assert len(set(seeds.values())) == 5
    assert set(placement.target_layout(zephyr)) == set(zephyr)
