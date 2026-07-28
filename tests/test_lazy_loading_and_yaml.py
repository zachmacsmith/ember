"""Regression tests for two harness fixes.

1. YAML key aliases: the documented experiment-YAML keys (workers/trials/
   warmup) were silently ignored — ``workers: 56`` ran single-worker.
2. Lazy library loading: selection batches no longer load every graph
   serially in the parent (hours + tens of GB at full-library scale); workers
   materialize graphs on demand. Results must be identical to the eager path.

Both tests are offline-safe: they use only bundled library graphs.
"""
import argparse
import glob
import json

import pytest

from ember_qc.cli import _build_resolved_params


def _args(**over):
    base = dict(algorithms=None, graphs=None, topologies=None, trials=None,
                warmup=None, timeout=None, seed=None, workers=None,
                fault_rate=None, fault_seed=None, note=None, output_dir=None,
                analyze=None, verbose=None)
    base.update(over)
    return argparse.Namespace(**base)


class TestYamlAliases:
    def test_documented_keys_reach_internal_params(self):
        p = _build_resolved_params(_args(), {"workers": 7, "trials": 2,
                                            "warmup": 1})
        assert p["n_workers"] == 7
        assert p["n_trials"] == 2
        assert p["warmup_trials"] == 1

    def test_cli_flags_still_override_yaml(self):
        p = _build_resolved_params(_args(workers=3), {"workers": 7})
        assert p["n_workers"] == 3

    def test_internal_names_in_yaml_still_work(self):
        p = _build_resolved_params(_args(), {"n_workers": 5})
        assert p["n_workers"] == 5

    def test_defaults_when_absent(self):
        p = _build_resolved_params(_args(), {})
        assert isinstance(p["n_workers"], int) and p["n_workers"] >= 1


class TestLazyLoading:
    SELECTION = "1000, 1004, 1200"   # bundled: K2, K6, bipartite K2,2

    def _rows(self, batch_dir):
        rows = {}
        for f in glob.glob(str(batch_dir / "workers" / "*.jsonl")):
            for line in open(f):
                r = json.loads(line)
                rows[(r["algorithm"], r["graph_id"], r["trial"])] = (
                    r["seed"], r.get("avg_chain_length"), r["status"])
        return rows

    def test_lazy_matches_eager_row_for_row(self, tmp_path):
        from ember_qc.benchmark import EmbeddingBenchmark
        from ember_qc.load_graphs import load_test_graphs
        from ember_qc.topologies import get_topology

        bench = EmbeddingBenchmark(get_topology("chimera_4x4x4"))
        common = dict(methods=["minorminer"], topologies=["chimera_4x4x4"],
                      n_trials=1, timeout=5, seed=7, n_workers=1,
                      verbose=False)
        d_lazy = bench.run_full_benchmark(
            graph_selection=self.SELECTION,
            output_dir=str(tmp_path / "lazy"), **common)
        d_eager = bench.run_full_benchmark(
            problems=load_test_graphs(self.SELECTION),
            output_dir=str(tmp_path / "eager"), **common)

        lazy, eager = self._rows(d_lazy), self._rows(d_eager)
        assert lazy and len(lazy) == len(eager)
        assert lazy == eager  # identical (seed, ACL, status) per run

    def test_materialize_failure_yields_crash_result(self, monkeypatch):
        import ember_qc.benchmark as B

        def boom(graph_id):
            raise RuntimeError("no such graph")

        import ember_qc.load_graphs as LG
        monkeypatch.setattr(LG, "load_graph", boom)
        B._LAZY_SOURCES.clear()
        with pytest.raises(RuntimeError):
            B._materialize_task(None, None, 999999999, "chimera_4x4x4")
        r = B._lazy_failure_result("minorminer", "g", 999999999,
                                   "chimera_4x4x4", 0, RuntimeError("x"))
        assert r.status == "CRASH" and not r.success
        assert "lazy graph load failed" in r.error
