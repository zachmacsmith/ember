"""
tests/test_validation_layers.py
================================
Validation layer smoke test — outputs a real benchmark batch so results can
be inspected manually in the batch directory.

Runs 8 mock algorithms against a small K3 source graph and a hand-crafted
6-node target graph.  Each algorithm is designed to trigger a specific
validation failure (or succeed cleanly).  The batch is written to results/
with batch_note="testingValidationLayers1_2" so it is clearly labelled.

Expected outcomes
-----------------
Algorithm               Layer   Check               Status
----------------------  ------  ------------------  ---------------
mock_valid              —       —                   SUCCESS
mock_numpy_keys         L2      type_correctness    INVALID_OUTPUT
mock_tuple_chains       L2      chain_format        INVALID_OUTPUT
mock_nan_time           L2      wall_time_validity  INVALID_OUTPUT
mock_extra_key          L2      key_validity        INVALID_OUTPUT
mock_disconnected       L1      connectivity        INVALID_OUTPUT
mock_shared_qubit       L1      disjointness        INVALID_OUTPUT
mock_missing_edge       L1      edge_preservation   INVALID_OUTPUT

Run:
    conda run -n minor python tests/test_validation_layers.py

After the run, inspect:
  - results/batch_*/logs/runner/*.log  — WARNING lines for each failure
  - results/batch_*/logs/runs/*.log    — per-run footer with 'error:' field
  - results/batch_*/workers/*.jsonl    — raw records
"""

import sys
import time
import numpy as np
import networkx as nx
from pathlib import Path

# Make sure project root is on sys.path when run directly
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from qebench.registry import ALGORITHM_REGISTRY, EmbeddingAlgorithm
from qebench.benchmark import EmbeddingBenchmark


# ── Target and source graphs ────────────────────────────────────────────────
#
# Target: 6 nodes, two types of edges:
#   Chain-internal: 0-1, 2-3, 4-5   (each pair is a connected "qubit pair")
#   Cross-chain:    0-2, 1-4, 3-5   (connects the pairs so K3 can be embedded)
#
# Valid embedding of K3:
#   src 0 → [0, 1]   src 1 → [2, 3]   src 2 → [4, 5]
#
# Source edges and their chain-adjacency checks:
#   (0,1): {0,1} ↔ {2,3} via 0-2  ✓
#   (0,2): {0,1} ↔ {4,5} via 1-4  ✓
#   (1,2): {2,3} ↔ {4,5} via 3-5  ✓

def _make_target() -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(6))
    G.add_edges_from([
        (0, 1), (2, 3), (4, 5),   # chain-internal
        (0, 2), (1, 4), (3, 5),   # cross-chain
    ])
    return G

def _make_source() -> nx.Graph:
    return nx.complete_graph(3)   # K3: nodes 0,1,2; edges (0,1),(0,2),(1,2)

TARGET = _make_target()
SOURCE = _make_source()

VALID_EMBEDDING = {0: [0, 1], 1: [2, 3], 2: [4, 5]}


# ── Mock algorithm base ─────────────────────────────────────────────────────

class _MockBase(EmbeddingAlgorithm):
    """Returns a preset result dict; ignores source/target graphs."""
    version = "mock-1.0"

    def _result_dict(self) -> dict:
        raise NotImplementedError

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        time.sleep(0.01)   # tiny sleep so wall_time > 0
        return self._result_dict()


# ── Mock algorithms ─────────────────────────────────────────────────────────

class MockValid(_MockBase):
    """Returns the correct embedding — should produce SUCCESS."""
    def _result_dict(self):
        return {
            'success': True,
            'embedding': dict(VALID_EMBEDDING),
            'time': 0.01,
        }


class MockNumpyKeys(_MockBase):
    """Uses numpy.int64 keys — Layer 2 type_correctness failure."""
    def _result_dict(self):
        emb = {np.int64(k): list(v) for k, v in VALID_EMBEDDING.items()}
        return {'success': True, 'embedding': emb, 'time': 0.01}


class MockTupleChains(_MockBase):
    """Wraps chains in tuples — Layer 2 chain_format failure."""
    def _result_dict(self):
        emb = {k: tuple(v) for k, v in VALID_EMBEDDING.items()}
        return {'success': True, 'embedding': emb, 'time': 0.01}


class MockNanTime(_MockBase):
    """Reports NaN wall time — Layer 2 wall_time_validity failure."""
    def _result_dict(self):
        return {
            'success': True,
            'embedding': dict(VALID_EMBEDDING),
            'time': float('nan'),
        }


class MockExtraKey(_MockBase):
    """Embedding has key 99 (not in K3) — Layer 2 key_validity failure."""
    def _result_dict(self):
        emb = dict(VALID_EMBEDDING)
        emb[99] = [0]
        return {'success': True, 'embedding': emb, 'time': 0.01}


class MockDisconnected(_MockBase):
    """Chain for src 0 is [0, 3] — not connected in target (no 0-3 edge).
    Layer 1 connectivity failure.

    0 connects to {1, 2} in target; 3 connects to {2, 5} in target.
    chain_set={0,3}: BFS from 0 finds {1,2} ∩ {0,3} = {} → not connected.
    """
    def _result_dict(self):
        emb = {0: [0, 3], 1: [2], 2: [4, 5]}
        return {'success': True, 'embedding': emb, 'time': 0.01}


class MockSharedQubit(_MockBase):
    """Qubit 1 appears in chains for both src 0 and src 1.
    Layer 1 disjointness failure.

    Chains: {0:[0,1], 1:[1,4], 2:[4,5]}
    All chains are connected (0-1, 1-4, 4-5 are target edges).
    Disjointness check builds reverse map and finds qubit 1 already
    assigned to src 0 when processing src 1's chain.
    """
    def _result_dict(self):
        emb = {0: [0, 1], 1: [1, 4], 2: [4, 5]}
        return {'success': True, 'embedding': emb, 'time': 0.01}


class MockMissingEdge(_MockBase):
    """Chain for src 1 is [3] (isolated in terms of adjacency to chain 0).
    Source edge (0,1): chains {0,1} and {3}.
    0's target neighbors: {1,2}; 1's target neighbors: {0,4}.
    Neither 2 nor 4 is in chain_1_set={3}; neither neighbor of 3 ({2,5})
    is in chain_0_set={0,1}.  → edge_preservation failure.
    """
    def _result_dict(self):
        emb = {0: [0, 1], 1: [3], 2: [4, 5]}
        return {'success': True, 'embedding': emb, 'time': 0.01}


# ── Register mocks (temporarily, for this script's process only) ────────────

MOCKS = {
    'mock_valid':        MockValid(),
    'mock_numpy_keys':   MockNumpyKeys(),
    'mock_tuple_chains': MockTupleChains(),
    'mock_nan_time':     MockNanTime(),
    'mock_extra_key':    MockExtraKey(),
    'mock_disconnected': MockDisconnected(),
    'mock_shared_qubit': MockSharedQubit(),
    'mock_missing_edge': MockMissingEdge(),
}

ALGORITHM_REGISTRY.update(MOCKS)


# ── Expected outcomes ────────────────────────────────────────────────────────

EXPECTED = {
    'mock_valid':        ('SUCCESS',        None),
    'mock_numpy_keys':   ('INVALID_OUTPUT', 'type_correctness'),
    'mock_tuple_chains': ('INVALID_OUTPUT', 'chain_format'),
    'mock_nan_time':     ('INVALID_OUTPUT', 'wall_time_validity'),
    'mock_extra_key':    ('INVALID_OUTPUT', 'key_validity'),
    'mock_disconnected': ('INVALID_OUTPUT', 'connectivity'),
    'mock_shared_qubit': ('INVALID_OUTPUT', 'disjointness'),
    'mock_missing_edge': ('INVALID_OUTPUT', 'edge_preservation'),
}


# ── Run benchmark ────────────────────────────────────────────────────────────

def main():
    bench = EmbeddingBenchmark(target_graph=TARGET, results_dir="./results")

    problems = [("K3_test", SOURCE)]
    methods = list(MOCKS.keys())

    batch_dir = bench.run_full_benchmark(
        problems=problems,
        methods=methods,
        n_trials=1,
        timeout=10.0,
        batch_note="testingValidationLayers1_2",
        seed=42,
        verbose=True,
    )

    print(f"\nBatch written to: {batch_dir}")
    print(f"  logs/runner/  → {batch_dir / 'logs' / 'runner'}")
    print(f"  logs/runs/    → {batch_dir / 'logs' / 'runs'}")

    # ── Assertions ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("ASSERTION CHECKS")
    print("=" * 60)

    from qebench.benchmark import EmbeddingResult
    import json

    results_by_algo = {}
    for jf in sorted((batch_dir / "workers").glob("worker_*.jsonl")):
        with open(jf) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    results_by_algo[rec['algorithm']] = rec

    failures = []
    for algo, (exp_status, exp_check) in EXPECTED.items():
        rec = results_by_algo.get(algo)
        if rec is None:
            failures.append(f"  MISSING result for {algo}")
            continue

        actual_status = rec.get('status')
        actual_error  = rec.get('error') or ''

        status_ok = actual_status == exp_status
        check_ok  = (exp_check is None) or (exp_check in actual_error)

        symbol = '✓' if (status_ok and check_ok) else '✗'
        print(f"  {symbol} {algo:<22}  status={actual_status:<16}  "
              f"check={'ok' if check_ok else 'MISSING in error'}")
        if not status_ok:
            failures.append(f"  {algo}: expected status={exp_status}, got {actual_status}")
        if not check_ok:
            failures.append(f"  {algo}: expected '{exp_check}' in error, got: {actual_error!r}")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("All assertions passed.")


if __name__ == '__main__':
    main()
