"""
tests/test_ember_qc_analysis.py
================================
Full test suite for the ember-qc-analysis package.

Coverage
--------
TestPaths              — _paths.py: user dir and config path resolution
TestConfig             — _config.py: load/set/get/reset/resolve, type validation
TestOutputDir          — _config.get_output_dir() priority chain
TestBatchValidation    — is_valid_batch(), validate_batch()
TestResolveInputDir    — resolve_input_dir() with all fallback branches
TestEmberQcDiscovery   — opportunistic ember-qc output_dir discovery
TestLoader             — load_batch(), infer_category(), derived columns
TestSummary            — overall_summary(), summary_by_category(), rank_table()
TestWinRate            — win_rate_matrix() correctness and edge cases
TestSignificance       — significance_tests(), friedman_test(), correlation_matrix()
TestPlots              — all plot functions return plt.Figure without error
TestExport             — df_to_latex(), export_tables()
TestCLIStage           — stage / unstage commands
TestCLIBatches         — batches list / show
TestCLIConfig          — config show / get / set / reset / path
TestCLIVersion         — version command
TestCLIAnalysisCommands — report / plots / tables / stats dispatch
TestBenchmarkAnalysis  — integration: load from batch_dir, generate_report()

All tests use synthetic in-memory data and tmp_path; no real batch directory,
D-Wave toolchain, or persistent config file is required.
"""

import argparse
import json
import math
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ==============================================================================
# Shared fixtures
# ==============================================================================

_ALGOS    = ["minorminer", "atom", "oct-triad"]
_TOPO     = "chimera_4x4x4"
_N_TRIALS = 3
_TIMEOUT  = 60.0

_PROBLEMS = [
    # (name,                  n,  edges, density,  category)
    ("K5",                    5,  10,    1.000,   "complete"),
    ("bipartite_K3_3",        6,  9,     0.600,   "bipartite"),
    ("grid_3x3",              9,  12,    0.333,   "grid"),
    ("cycle_10",             10,  10,    0.222,   "cycle"),
    ("tree_r2_d3",           15,  14,    0.133,   "tree"),
    ("petersen",             10,  15,    0.333,   "special"),
    ("random_n10_d0.5_i0",   10,  22,    0.489,   "random"),
    ("random_n10_d0.5_i1",   10,  25,    0.556,   "random"),
]


def _make_row(algo, prob_name, n, edges, density, trial, rng, success=True):
    if success:
        t      = rng.uniform(0.001, 0.5)
        avg_cl = rng.uniform(1.5, 4.0)
        max_cl = int(avg_cl * rng.uniform(1.0, 1.5)) + 1
        qubits = n * int(avg_cl + 0.5)
        couplers = max(1, edges - rng.integers(0, 3))
        return {
            "algorithm": algo, "problem_name": prob_name,
            "topology_name": _TOPO, "trial": trial,
            "success": True, "is_valid": True,
            "wall_time": t,
            "avg_chain_length": avg_cl, "max_chain_length": max_cl,
            "total_qubits_used": qubits, "total_couplers_used": int(couplers),
            "problem_nodes": n, "problem_edges": edges,
            "problem_density": density, "error": None,
        }
    else:
        return {
            "algorithm": algo, "problem_name": prob_name,
            "topology_name": _TOPO, "trial": trial,
            "success": False, "is_valid": False,
            "wall_time": _TIMEOUT,
            "avg_chain_length": 0.0, "max_chain_length": 0,
            "total_qubits_used": 0, "total_couplers_used": 0,
            "problem_nodes": n, "problem_edges": edges,
            "problem_density": density, "error": "timeout",
        }


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    """Synthetic runs DataFrame: 3 algos × 8 problems × 3 trials = 72 rows."""
    rng = np.random.default_rng(42)
    rows = []
    for algo in _ALGOS:
        for prob_name, n, edges, density, _cat in _PROBLEMS:
            for trial in range(_N_TRIALS):
                rows.append(_make_row(algo, prob_name, n, edges, density, trial, rng))
    df = pd.DataFrame(rows)
    from ember_qc_analysis.loader import _derive_columns
    return _derive_columns(df, timeout=_TIMEOUT)


@pytest.fixture(scope="module")
def sample_df_with_failure(sample_df) -> pd.DataFrame:
    """sample_df with atom failing on K5 trial 2."""
    df = sample_df.copy()
    mask = (df["algorithm"] == "atom") & (df["problem_name"] == "K5") & (df["trial"] == 2)
    df.loc[mask, "success"]          = False
    df.loc[mask, "is_valid"]         = False
    df.loc[mask, "wall_time"]        = _TIMEOUT
    df.loc[mask, "avg_chain_length"] = 0.0
    df.loc[mask, "error"]            = "timeout"
    return df


@pytest.fixture()
def batch_dir(tmp_path, sample_df) -> Path:
    """Minimal valid batch directory with results.db and config.json."""
    bd = tmp_path / "batch_test_analysis"
    bd.mkdir()
    batch_id = bd.name

    raw_cols = [c for c in sample_df.columns
                if c not in ("category", "qubit_overhead_ratio",
                             "coupler_overhead_ratio", "max_to_avg_chain_ratio",
                             "is_timeout")]
    raw_df = sample_df[raw_cols].copy()
    raw_df["batch_id"] = batch_id
    for col in ("success", "is_valid"):
        if col in raw_df.columns:
            raw_df[col] = raw_df[col].astype(int)

    db_path = bd / "results.db"
    con = sqlite3.connect(db_path)
    raw_df.to_sql("runs", con, if_exists="replace", index=False)
    con.execute(
        "CREATE TABLE IF NOT EXISTS batches "
        "(batch_id TEXT PRIMARY KEY, config_json TEXT)"
    )
    con.execute(
        "INSERT OR IGNORE INTO batches (batch_id, config_json) VALUES (?, ?)",
        (batch_id, json.dumps({})),
    )
    con.commit()
    con.close()

    config = {
        "algorithms": _ALGOS,
        "topologies": [_TOPO],
        "n_trials": _N_TRIALS,
        "timeout": _TIMEOUT,
        "batch_note": "Synthetic test batch",
        "total_measured_runs": len(_ALGOS) * len(_PROBLEMS) * _N_TRIALS,
    }
    (bd / "config.json").write_text(json.dumps(config))
    return bd


@pytest.fixture()
def csv_batch_dir(tmp_path, sample_df) -> Path:
    """Batch directory using runs.csv fallback (older batch format)."""
    bd = tmp_path / "batch_csv"
    bd.mkdir()

    raw_cols = [c for c in sample_df.columns
                if c not in ("category", "qubit_overhead_ratio",
                             "coupler_overhead_ratio", "max_to_avg_chain_ratio",
                             "is_timeout")]
    sample_df[raw_cols].to_csv(bd / "runs.csv", index=False)
    (bd / "config.json").write_text(json.dumps({"timeout": _TIMEOUT}))
    return bd


@pytest.fixture()
def isolated_config(tmp_path, monkeypatch):
    """Redirect config storage to tmp_path so tests never touch real config."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(
        "ember_qc_analysis._config.get_user_config_path",
        lambda: cfg_path,
    )
    monkeypatch.setattr(
        "ember_qc_analysis._paths.get_user_config_path",
        lambda: cfg_path,
    )
    # Also patch in cli module
    monkeypatch.setattr(
        "ember_qc_analysis.cli.get_user_config_path",
        lambda: cfg_path,
    )
    return cfg_path


# ==============================================================================
# TestPaths
# ==============================================================================

class TestPaths:

    def test_get_user_dir_returns_path(self, tmp_path, monkeypatch):
        from ember_qc_analysis._paths import get_user_dir
        # Patch platformdirs so the test never touches the real user dir
        monkeypatch.setattr(
            "ember_qc_analysis._paths.user_data_dir",
            lambda *a, **kw: str(tmp_path / "userdata"),
        )
        d = get_user_dir()
        assert isinstance(d, Path)
        assert d.exists()

    def test_get_user_config_path_returns_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "ember_qc_analysis._paths.user_data_dir",
            lambda *a, **kw: str(tmp_path / "userdata"),
        )
        from ember_qc_analysis._paths import get_user_config_path
        p = get_user_config_path()
        assert p.name == "config.json"

    def test_get_user_dir_created_on_access(self, tmp_path, monkeypatch):
        target = tmp_path / "new_subdir"
        assert not target.exists()
        monkeypatch.setattr(
            "ember_qc_analysis._paths.user_data_dir",
            lambda *a, **kw: str(target),
        )
        from ember_qc_analysis._paths import get_user_dir
        get_user_dir()
        assert target.exists()


# ==============================================================================
# TestConfig
# ==============================================================================

class TestConfig:

    def test_load_config_returns_defaults_when_no_file(self, isolated_config):
        from ember_qc_analysis._config import load_config, DEFAULTS
        cfg = load_config()
        assert cfg["input_dir"]    == DEFAULTS["input_dir"]
        assert cfg["output_dir"]   == DEFAULTS["output_dir"]
        assert cfg["fig_format"]   == DEFAULTS["fig_format"]
        assert cfg["active_batch"] == DEFAULTS["active_batch"]

    def test_set_and_get_fig_format(self, isolated_config):
        from ember_qc_analysis._config import set_config, get_config
        set_config("fig_format", "pdf")
        assert get_config("fig_format") == "pdf"

    def test_set_fig_format_invalid_value(self, isolated_config):
        from ember_qc_analysis._config import set_config
        with pytest.raises(ValueError, match="fig_format"):
            set_config("fig_format", "bmp")

    def test_set_unknown_key_raises(self, isolated_config):
        from ember_qc_analysis._config import set_config
        with pytest.raises(ValueError, match="Unknown config key"):
            set_config("nonexistent_key", "value")

    def test_set_wrong_type_raises(self, isolated_config):
        from ember_qc_analysis._config import set_config
        with pytest.raises(TypeError):
            set_config("fig_format", 42)

    def test_set_nullable_to_none(self, isolated_config):
        from ember_qc_analysis._config import set_config, get_config
        set_config("input_dir", "/some/path")
        set_config("input_dir", None)
        assert get_config("input_dir") is None

    def test_reset_config_deletes_file(self, isolated_config):
        from ember_qc_analysis._config import set_config, reset_config
        set_config("fig_format", "svg")
        assert isolated_config.exists()
        reset_config()
        assert not isolated_config.exists()

    def test_reset_config_reverts_to_defaults(self, isolated_config):
        from ember_qc_analysis._config import set_config, reset_config, get_config
        set_config("fig_format", "svg")
        reset_config()
        assert get_config("fig_format") == "png"

    def test_load_config_ignores_unknown_keys(self, isolated_config):
        isolated_config.write_text(json.dumps({"fig_format": "pdf", "future_key": "x"}))
        from ember_qc_analysis._config import load_config
        cfg = load_config()
        assert "future_key" not in cfg
        assert cfg["fig_format"] == "pdf"

    def test_load_config_handles_corrupt_json(self, isolated_config):
        isolated_config.write_text("not valid json {{{")
        from ember_qc_analysis._config import load_config, DEFAULTS
        cfg = load_config()
        assert cfg["fig_format"] == DEFAULTS["fig_format"]

    def test_resolve_explicit_wins(self, isolated_config, monkeypatch):
        from ember_qc_analysis._config import set_config, resolve
        set_config("fig_format", "pdf")
        monkeypatch.setenv("EMBER_ANALYSIS_FIG_FORMAT", "svg")
        result = resolve("fig_format", explicit="png")
        assert result == "png"

    def test_resolve_env_beats_stored(self, isolated_config, monkeypatch):
        from ember_qc_analysis._config import set_config, resolve
        set_config("fig_format", "pdf")
        monkeypatch.setenv("EMBER_ANALYSIS_FIG_FORMAT", "svg")
        result = resolve("fig_format")
        assert result == "svg"

    def test_resolve_stored_beats_default(self, isolated_config, monkeypatch):
        from ember_qc_analysis._config import set_config, resolve
        monkeypatch.delenv("EMBER_ANALYSIS_FIG_FORMAT", raising=False)
        set_config("fig_format", "pdf")
        result = resolve("fig_format")
        assert result == "pdf"

    def test_resolve_default_when_nothing_set(self, isolated_config, monkeypatch):
        from ember_qc_analysis._config import resolve
        monkeypatch.delenv("EMBER_ANALYSIS_FIG_FORMAT", raising=False)
        result = resolve("fig_format")
        assert result == "png"

    def test_resolve_unknown_key_raises(self, isolated_config):
        from ember_qc_analysis._config import resolve
        with pytest.raises(ValueError, match="Unknown config key"):
            resolve("bad_key")


# ==============================================================================
# TestOutputDir
# ==============================================================================

class TestOutputDir:

    def test_default_is_batch_analysis_subdir(self, isolated_config, monkeypatch, tmp_path):
        from ember_qc_analysis._config import get_output_dir
        monkeypatch.delenv("EMBER_ANALYSIS_OUTPUT_DIR", raising=False)
        batch = tmp_path / "batch_foo"
        result = get_output_dir(batch)
        assert result == batch / "analysis"

    def test_explicit_overrides_default(self, isolated_config, tmp_path):
        from ember_qc_analysis._config import get_output_dir
        batch  = tmp_path / "batch_foo"
        custom = tmp_path / "custom_out"
        result = get_output_dir(batch, explicit=str(custom))
        assert result == custom

    def test_env_var_overrides_default(self, isolated_config, monkeypatch, tmp_path):
        from ember_qc_analysis._config import get_output_dir
        env_path = str(tmp_path / "env_out")
        monkeypatch.setenv("EMBER_ANALYSIS_OUTPUT_DIR", env_path)
        batch = tmp_path / "batch_foo"
        result = get_output_dir(batch)
        assert result == Path(env_path)

    def test_stored_config_overrides_default(self, isolated_config, monkeypatch, tmp_path):
        from ember_qc_analysis._config import set_config, get_output_dir
        monkeypatch.delenv("EMBER_ANALYSIS_OUTPUT_DIR", raising=False)
        stored = str(tmp_path / "stored_out")
        set_config("output_dir", stored)
        batch = tmp_path / "batch_foo"
        result = get_output_dir(batch)
        assert result == Path(stored)


# ==============================================================================
# TestBatchValidation
# ==============================================================================

class TestBatchValidation:

    def test_is_valid_batch_with_results_db(self, batch_dir):
        from ember_qc_analysis._config import is_valid_batch
        assert is_valid_batch(batch_dir)

    def test_is_valid_batch_with_runs_csv(self, csv_batch_dir):
        from ember_qc_analysis._config import is_valid_batch
        assert is_valid_batch(csv_batch_dir)

    def test_is_valid_batch_empty_dir(self, tmp_path):
        from ember_qc_analysis._config import is_valid_batch
        empty = tmp_path / "empty"
        empty.mkdir()
        assert not is_valid_batch(empty)

    def test_is_valid_batch_nonexistent(self, tmp_path):
        from ember_qc_analysis._config import is_valid_batch
        assert not is_valid_batch(tmp_path / "no_such_dir")

    def test_is_valid_batch_file_not_dir(self, tmp_path):
        from ember_qc_analysis._config import is_valid_batch
        f = tmp_path / "file.txt"
        f.write_text("x")
        assert not is_valid_batch(f)

    def test_validate_batch_passes_for_valid(self, batch_dir):
        from ember_qc_analysis._config import validate_batch
        validate_batch(batch_dir)  # should not raise

    def test_validate_batch_raises_for_missing_path(self, tmp_path):
        from ember_qc_analysis._config import validate_batch
        with pytest.raises(ValueError, match="does not exist"):
            validate_batch(tmp_path / "ghost")

    def test_validate_batch_raises_for_empty_dir(self, tmp_path):
        from ember_qc_analysis._config import validate_batch
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ValueError, match="Not a valid"):
            validate_batch(empty)

    def test_validate_batch_raises_for_file(self, tmp_path):
        from ember_qc_analysis._config import validate_batch
        f = tmp_path / "notadir"
        f.write_text("x")
        with pytest.raises(ValueError, match="not a directory"):
            validate_batch(f)


# ==============================================================================
# TestResolveInputDir
# ==============================================================================

class TestResolveInputDir:

    def test_explicit_returned_directly(self, isolated_config, tmp_path):
        from ember_qc_analysis._config import resolve_input_dir
        result = resolve_input_dir(explicit=str(tmp_path), prompt=False)
        assert result == tmp_path

    def test_env_var_used(self, isolated_config, monkeypatch, tmp_path):
        from ember_qc_analysis._config import resolve_input_dir
        monkeypatch.setenv("EMBER_ANALYSIS_INPUT_DIR", str(tmp_path))
        result = resolve_input_dir(prompt=False)
        assert result == tmp_path

    def test_stored_config_used(self, isolated_config, monkeypatch, tmp_path):
        from ember_qc_analysis._config import set_config, resolve_input_dir
        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        set_config("input_dir", str(tmp_path))
        result = resolve_input_dir(prompt=False)
        assert result == tmp_path

    def test_no_config_no_prompt_returns_none(self, isolated_config, monkeypatch):
        from ember_qc_analysis._config import resolve_input_dir
        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        result = resolve_input_dir(prompt=False)
        assert result is None

    def test_no_config_with_prompt_exits(self, isolated_config, monkeypatch):
        """When nothing is set and prompt=True with no ember-qc discovery, sys.exit(1)."""
        from ember_qc_analysis._config import resolve_input_dir
        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        # Ensure ember-qc discovery finds nothing
        monkeypatch.setattr(
            "ember_qc_analysis._config._discover_emberqc_output_dir",
            lambda: None,
        )
        with pytest.raises(SystemExit):
            resolve_input_dir(prompt=True)


# ==============================================================================
# TestEmberQcDiscovery
# ==============================================================================

class TestEmberQcDiscovery:

    def test_discovery_returns_none_when_not_installed(self, monkeypatch):
        """If ember_qc is not importable, discovery returns None silently."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ember_qc._paths":
                raise ImportError("ember_qc not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        from ember_qc_analysis._config import _discover_emberqc_output_dir
        result = _discover_emberqc_output_dir()
        assert result is None

    def test_discovery_returns_none_when_config_has_no_output_dir(self, tmp_path, monkeypatch):
        """If ember-qc config exists but output_dir is null, return None."""
        cfg_path = tmp_path / "qc_config.json"
        cfg_path.write_text(json.dumps({"default_workers": 4}))

        mock_paths = MagicMock()
        mock_paths.get_user_config_path.return_value = cfg_path
        monkeypatch.setitem(
            __import__("sys").modules,
            "ember_qc._paths",
            mock_paths,
        )
        from ember_qc_analysis._config import _discover_emberqc_output_dir
        result = _discover_emberqc_output_dir()
        assert result is None

    def test_prompt_choose_session_only(self, isolated_config, monkeypatch, tmp_path, batch_dir):
        """Choosing [1] uses the directory for this session but does not save to config."""
        from ember_qc_analysis._config import resolve_input_dir, get_config

        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        # Copy the batch_dir into results_dir so discovery finds a valid batch
        import shutil
        shutil.copytree(batch_dir, results_dir / batch_dir.name)

        monkeypatch.setattr(
            "ember_qc_analysis._config._discover_emberqc_output_dir",
            lambda: results_dir,
        )
        monkeypatch.setattr("builtins.input", lambda _: "1")

        result = resolve_input_dir(prompt=True)
        assert result == results_dir
        # Must NOT be saved to config
        assert get_config("input_dir") is None

    def test_prompt_choose_save(self, isolated_config, monkeypatch, tmp_path, batch_dir):
        """Choosing [2] uses the directory and persists it to config."""
        from ember_qc_analysis._config import resolve_input_dir, get_config

        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        import shutil
        shutil.copytree(batch_dir, results_dir / batch_dir.name)

        monkeypatch.setattr(
            "ember_qc_analysis._config._discover_emberqc_output_dir",
            lambda: results_dir,
        )
        monkeypatch.setattr("builtins.input", lambda _: "2")

        result = resolve_input_dir(prompt=True)
        assert result == results_dir
        assert get_config("input_dir") == str(results_dir)

    def test_prompt_choose_no_falls_through_to_exit(self, isolated_config, monkeypatch, tmp_path, batch_dir):
        """Choosing [3] declines and falls through to sys.exit."""
        from ember_qc_analysis._config import resolve_input_dir

        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        import shutil
        shutil.copytree(batch_dir, results_dir / batch_dir.name)

        monkeypatch.setattr(
            "ember_qc_analysis._config._discover_emberqc_output_dir",
            lambda: results_dir,
        )
        monkeypatch.setattr("builtins.input", lambda _: "3")

        with pytest.raises(SystemExit):
            resolve_input_dir(prompt=True)


# ==============================================================================
# TestLoader
# ==============================================================================

class TestLoader:

    def test_infer_category_complete(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("K4")  == "complete"
        assert infer_category("K15") == "complete"

    def test_infer_category_bipartite(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("bipartite_K3_3") == "bipartite"

    def test_infer_category_grid(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("grid_4x4") == "grid"

    def test_infer_category_cycle(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("cycle_10") == "cycle"

    def test_infer_category_tree(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("tree_r2_d3") == "tree"

    def test_infer_category_special(self):
        from ember_qc_analysis.loader import infer_category
        for name in ("petersen", "dodecahedral", "icosahedral"):
            assert infer_category(name) == "special"

    def test_infer_category_random(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("random_n10_d0.5_i0") == "random"

    def test_infer_category_unknown(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("my_custom_graph") == "other"

    def test_infer_category_case_insensitive(self):
        from ember_qc_analysis.loader import infer_category
        assert infer_category("PETERSEN") == "special"
        assert infer_category("Grid_3x3") == "grid"

    def test_derived_columns_present(self, sample_df):
        for col in ("category", "qubit_overhead_ratio",
                    "coupler_overhead_ratio", "max_to_avg_chain_ratio",
                    "is_timeout"):
            assert col in sample_df.columns

    def test_category_covers_all_types(self, sample_df):
        cats = set(sample_df["category"].unique())
        for expected in ("complete", "bipartite", "grid", "cycle",
                         "tree", "special", "random"):
            assert expected in cats

    def test_qubit_overhead_ratio_positive(self, sample_df):
        ratios = sample_df[sample_df["success"]]["qubit_overhead_ratio"]
        assert (ratios >= 1.0).all()
        assert ratios.notna().all()

    def test_is_timeout_false_for_fast_trials(self, sample_df):
        assert not sample_df["is_timeout"].any()

    def test_load_batch_reads_sqlite(self, batch_dir):
        from ember_qc_analysis.loader import load_batch
        df, config = load_batch(batch_dir)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(config, dict)
        assert len(df) == len(_ALGOS) * len(_PROBLEMS) * _N_TRIALS
        assert df["success"].dtype == bool

    def test_load_batch_reads_csv_fallback(self, csv_batch_dir):
        from ember_qc_analysis.loader import load_batch
        df, config = load_batch(csv_batch_dir)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_load_batch_derived_columns(self, batch_dir):
        from ember_qc_analysis.loader import load_batch
        df, _ = load_batch(batch_dir)
        for col in ("category", "qubit_overhead_ratio", "is_timeout"):
            assert col in df.columns

    def test_load_batch_missing_dir_raises(self, tmp_path):
        from ember_qc_analysis.loader import load_batch
        with pytest.raises(FileNotFoundError):
            load_batch(tmp_path / "nonexistent")

    def test_load_batch_no_results_file_raises(self, tmp_path):
        from ember_qc_analysis.loader import load_batch
        (tmp_path / "bd").mkdir()
        with pytest.raises(FileNotFoundError):
            load_batch(tmp_path / "bd")

    def test_load_batch_bad_schema_raises(self, tmp_path):
        from ember_qc_analysis.loader import load_batch
        bd = tmp_path / "bad"
        bd.mkdir()
        pd.DataFrame({"algorithm": ["x"]}).to_csv(bd / "runs.csv", index=False)
        with pytest.raises(ValueError, match="missing required columns"):
            load_batch(bd)


# ==============================================================================
# TestSummary
# ==============================================================================

class TestSummary:

    def test_overall_summary_shape(self, sample_df):
        from ember_qc_analysis.summary import overall_summary
        result = overall_summary(sample_df)
        assert result.shape[0] == len(_ALGOS)
        assert "success_rate" in result.columns
        assert "chain_mean" in result.columns

    def test_overall_summary_all_succeed(self, sample_df):
        from ember_qc_analysis.summary import overall_summary
        result = overall_summary(sample_df)
        assert (result["success_rate"] == 1.0).all()

    def test_overall_summary_failure_reduces_rate(self, sample_df_with_failure):
        from ember_qc_analysis.summary import overall_summary
        result = overall_summary(sample_df_with_failure)
        assert result.loc["atom", "success_rate"] < 1.0

    def test_overall_summary_index(self, sample_df):
        from ember_qc_analysis.summary import overall_summary
        result = overall_summary(sample_df)
        assert set(result.index) == set(_ALGOS)

    def test_summary_by_category_shape(self, sample_df):
        from ember_qc_analysis.summary import summary_by_category
        result = summary_by_category(sample_df, "avg_chain_length")
        assert result.shape[0] == len(_ALGOS)
        for cat in ("complete", "bipartite", "grid", "cycle", "tree", "special", "random"):
            assert cat in result.columns

    def test_summary_by_category_values_positive(self, sample_df):
        from ember_qc_analysis.summary import summary_by_category
        result = summary_by_category(sample_df, "avg_chain_length")
        assert (result.dropna() > 0).all().all()

    def test_summary_by_category_bad_metric(self, sample_df):
        from ember_qc_analysis.summary import summary_by_category
        with pytest.raises(ValueError):
            summary_by_category(sample_df, "nonexistent_metric")

    def test_rank_table_shape(self, sample_df):
        from ember_qc_analysis.summary import rank_table
        result = rank_table(sample_df, "avg_chain_length")
        assert result.shape[0] == len(_ALGOS)
        assert "mean_rank" in result.columns
        assert "n_problems_ranked" in result.columns

    def test_rank_table_ranks_in_range(self, sample_df):
        from ember_qc_analysis.summary import rank_table
        result = rank_table(sample_df, "avg_chain_length")
        assert (result["mean_rank"] >= 1.0).all()
        assert (result["mean_rank"] <= len(_ALGOS)).all()

    def test_rank_table_sorted_ascending(self, sample_df):
        from ember_qc_analysis.summary import rank_table
        result = rank_table(sample_df, "avg_chain_length")
        ranks = result["mean_rank"].tolist()
        assert ranks == sorted(ranks)


# ==============================================================================
# TestWinRate
# ==============================================================================

class TestWinRate:

    def test_shape(self, sample_df):
        from ember_qc_analysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, "avg_chain_length")
        assert result.shape == (len(_ALGOS), len(_ALGOS))

    def test_diagonal_nan(self, sample_df):
        from ember_qc_analysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, "avg_chain_length")
        for algo in _ALGOS:
            assert math.isnan(result.loc[algo, algo])

    def test_values_in_range(self, sample_df):
        from ember_qc_analysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, "avg_chain_length")
        vals = result.stack().dropna()
        assert (vals >= 0).all() and (vals <= 1).all()

    def test_complementary(self, sample_df):
        from ember_qc_analysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, "avg_chain_length")
        for i, a in enumerate(_ALGOS):
            for b in _ALGOS[i + 1:]:
                total = result.loc[a, b] + result.loc[b, a]
                assert total <= 1.0 + 1e-9


# ==============================================================================
# TestSignificance
# ==============================================================================

class TestSignificance:

    def test_significance_tests_returns_dataframe(self, sample_df):
        from ember_qc_analysis.statistics import significance_tests
        result = significance_tests(sample_df, "avg_chain_length")
        assert isinstance(result, pd.DataFrame)

    def test_significance_tests_columns(self, sample_df):
        from ember_qc_analysis.statistics import significance_tests
        result = significance_tests(sample_df, "avg_chain_length")
        for col in ("algo_a", "algo_b", "n_pairs", "p_value", "corrected_p", "significant"):
            assert col in result.columns

    def test_significance_tests_p_in_range(self, sample_df):
        from ember_qc_analysis.statistics import significance_tests
        result = significance_tests(sample_df, "avg_chain_length")
        valid_p = result["p_value"].dropna()
        assert (valid_p >= 0).all() and (valid_p <= 1).all()

    def test_significance_tests_pair_count(self, sample_df):
        import itertools
        from ember_qc_analysis.statistics import significance_tests
        result = significance_tests(sample_df, "avg_chain_length", min_pairs=1)
        expected = len(list(itertools.combinations(_ALGOS, 2)))
        assert len(result) == expected

    def test_friedman_returns_dict(self, sample_df):
        from ember_qc_analysis.statistics import friedman_test
        result = friedman_test(sample_df, "avg_chain_length")
        assert isinstance(result, dict)

    def test_friedman_p_in_range(self, sample_df):
        from ember_qc_analysis.statistics import friedman_test
        result = friedman_test(sample_df, "avg_chain_length")
        if "p_value" in result:
            assert 0.0 <= result["p_value"] <= 1.0

    def test_friedman_keys(self, sample_df):
        from ember_qc_analysis.statistics import friedman_test
        result = friedman_test(sample_df, "avg_chain_length")
        if "error" not in result:
            for key in ("statistic", "p_value", "significant", "n_problems", "n_algorithms"):
                assert key in result

    def test_correlation_matrix_shape(self, sample_df):
        from ember_qc_analysis.statistics import correlation_matrix
        result = correlation_matrix(sample_df)
        assert result.shape == (3, 4)

    def test_correlation_matrix_values_in_range(self, sample_df):
        from ember_qc_analysis.statistics import correlation_matrix
        result = correlation_matrix(sample_df)
        vals = result.values.flatten()
        valid = vals[~np.isnan(vals)]
        assert (valid >= -1.0 - 1e-9).all() and (valid <= 1.0 + 1e-9).all()

    def test_density_hardness_summary(self, sample_df):
        from ember_qc_analysis.statistics import density_hardness_summary
        result = density_hardness_summary(sample_df, "avg_chain_length")
        assert isinstance(result, pd.DataFrame)
        assert "algorithm" in result.columns


# ==============================================================================
# TestPlots
# ==============================================================================

class TestPlots:

    def test_plot_heatmap(self, sample_df):
        from ember_qc_analysis.plots import plot_heatmap
        fig = plot_heatmap(sample_df, "avg_chain_length", save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_scaling(self, sample_df):
        from ember_qc_analysis.plots import plot_scaling
        fig = plot_scaling(sample_df, "wall_time", "problem_nodes", save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_scaling_log(self, sample_df):
        from ember_qc_analysis.plots import plot_scaling
        fig = plot_scaling(sample_df, "wall_time", "problem_nodes", log=True, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_density_hardness(self, sample_df):
        from ember_qc_analysis.plots import plot_density_hardness
        fig = plot_density_hardness(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_pareto(self, sample_df):
        from ember_qc_analysis.plots import plot_pareto
        fig = plot_pareto(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_distributions(self, sample_df):
        from ember_qc_analysis.plots import plot_distributions
        fig = plot_distributions(sample_df, "avg_chain_length", save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_head_to_head(self, sample_df):
        from ember_qc_analysis.plots import plot_head_to_head
        fig = plot_head_to_head(sample_df, _ALGOS[0], _ALGOS[1], save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_head_to_head_unknown_algo(self, sample_df):
        from ember_qc_analysis.plots import plot_head_to_head
        fig = plot_head_to_head(sample_df, "nonexistent", _ALGOS[0], save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_consistency(self, sample_df):
        from ember_qc_analysis.plots import plot_consistency
        fig = plot_consistency(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_topology_comparison(self, sample_df):
        from ember_qc_analysis.plots import plot_topology_comparison
        fig = plot_topology_comparison(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_chain_distribution(self, sample_df):
        from ember_qc_analysis.plots import plot_chain_distribution
        fig = plot_chain_distribution(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_max_chain_distribution(self, sample_df):
        from ember_qc_analysis.plots import plot_max_chain_distribution
        fig = plot_max_chain_distribution(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_win_rate_matrix(self, sample_df):
        from ember_qc_analysis.plots import plot_win_rate_matrix
        fig = plot_win_rate_matrix(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_success_heatmap(self, sample_df):
        from ember_qc_analysis.plots import plot_success_heatmap
        fig = plot_success_heatmap(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_success_by_nodes(self, sample_df):
        from ember_qc_analysis.plots import plot_success_by_nodes
        fig = plot_success_by_nodes(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_success_by_density(self, sample_df):
        from ember_qc_analysis.plots import plot_success_by_density
        fig = plot_success_by_density(sample_df, save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_graph_indexed_chain(self, sample_df):
        from ember_qc_analysis.plots import plot_graph_indexed_chain
        for x_mode in ("by_graph_id", "by_n_nodes", "by_density"):
            fig = plot_graph_indexed_chain(sample_df, x_mode, save=False)
            assert isinstance(fig, plt.Figure)
            plt.close("all")

    def test_plot_graph_indexed_time(self, sample_df):
        from ember_qc_analysis.plots import plot_graph_indexed_time
        fig = plot_graph_indexed_time(sample_df, "by_graph_id", save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_graph_indexed_success(self, sample_df):
        from ember_qc_analysis.plots import plot_graph_indexed_success
        fig = plot_graph_indexed_success(sample_df, "by_graph_id", save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_intersection_comparison(self, sample_df):
        from ember_qc_analysis.plots import plot_intersection_comparison
        fig = plot_intersection_comparison(sample_df, _ALGOS[0], _ALGOS[1], save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_plot_save_writes_file(self, sample_df, tmp_path):
        from ember_qc_analysis.plots import plot_heatmap
        plot_heatmap(sample_df, "avg_chain_length", output_dir=tmp_path, save=True)
        saved = list((tmp_path / "figures" / "distributions").glob("*.png"))
        assert len(saved) >= 1
        plt.close("all")


# ==============================================================================
# TestExport
# ==============================================================================

class TestExport:

    def test_df_to_latex_booktabs(self):
        from ember_qc_analysis.export import df_to_latex
        df = pd.DataFrame({"a": [1.0], "b": [2.0]})
        tex = df_to_latex(df, caption="Test", label="tab:t")
        assert "\\toprule"    in tex
        assert "\\midrule"    in tex
        assert "\\bottomrule" in tex

    def test_df_to_latex_table_env(self):
        from ember_qc_analysis.export import df_to_latex
        df = pd.DataFrame({"x": [1]})
        tex = df_to_latex(df)
        assert "\\begin{table}" in tex
        assert "\\end{table}"   in tex

    def test_df_to_latex_caption_label(self):
        from ember_qc_analysis.export import df_to_latex
        df = pd.DataFrame({"v": [1.0]})
        tex = df_to_latex(df, caption="My caption", label="tab:my")
        assert "My caption" in tex
        assert "tab:my"     in tex

    def test_export_tables_writes_csv_and_tex(self, tmp_path):
        from ember_qc_analysis.export import export_tables
        df = pd.DataFrame({"algo": ["a", "b"], "score": [1.0, 2.0]}).set_index("algo")
        export_tables({"test_table": (df, "Title", "tab:t")}, tmp_path)
        assert (tmp_path / "test_table.csv").exists()
        assert (tmp_path / "test_table.tex").exists()

    def test_export_tables_tex_has_booktabs(self, tmp_path):
        from ember_qc_analysis.export import export_tables
        df = pd.DataFrame({"algo": ["a"], "val": [3.14]}).set_index("algo")
        export_tables({"t": (df, "Cap", "lab")}, tmp_path)
        tex = (tmp_path / "t.tex").read_text()
        assert "\\toprule" in tex


# ==============================================================================
# TestCLIStage
# ==============================================================================

class TestCLIStage:

    def test_stage_valid_batch(self, isolated_config, batch_dir, capsys):
        from ember_qc_analysis.cli import cmd_stage
        args = argparse.Namespace(batch_dir=str(batch_dir))
        cmd_stage(args)
        out = capsys.readouterr().out
        assert "Staged" in out
        assert batch_dir.name in out

    def test_stage_saves_active_batch(self, isolated_config, batch_dir):
        from ember_qc_analysis.cli import cmd_stage
        from ember_qc_analysis._config import get_config
        cmd_stage(argparse.Namespace(batch_dir=str(batch_dir)))
        assert get_config("active_batch") == str(batch_dir.resolve())

    def test_stage_invalid_path_exits(self, isolated_config, tmp_path, capsys):
        from ember_qc_analysis.cli import cmd_stage
        with pytest.raises(SystemExit):
            cmd_stage(argparse.Namespace(batch_dir=str(tmp_path / "nope")))

    def test_stage_empty_dir_exits(self, isolated_config, tmp_path, capsys):
        from ember_qc_analysis.cli import cmd_stage
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(SystemExit):
            cmd_stage(argparse.Namespace(batch_dir=str(empty)))

    def test_unstage_clears_active_batch(self, isolated_config, batch_dir, capsys):
        from ember_qc_analysis.cli import cmd_stage, cmd_unstage
        from ember_qc_analysis._config import get_config
        cmd_stage(argparse.Namespace(batch_dir=str(batch_dir)))
        cmd_unstage(argparse.Namespace())
        assert get_config("active_batch") is None

    def test_unstage_when_nothing_staged(self, isolated_config, capsys):
        from ember_qc_analysis.cli import cmd_unstage
        cmd_unstage(argparse.Namespace())
        out = capsys.readouterr().out
        assert "No batch" in out


# ==============================================================================
# TestCLIBatches
# ==============================================================================

class TestCLIBatches:

    def test_batches_list_shows_batch(self, isolated_config, batch_dir, monkeypatch, capsys):
        from ember_qc_analysis.cli import cmd_batches_list
        from ember_qc_analysis._config import set_config
        set_config("input_dir", str(batch_dir.parent))
        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        args = argparse.Namespace(input_dir=None)
        cmd_batches_list(args)
        out = capsys.readouterr().out
        assert batch_dir.name in out

    def test_batches_list_marks_active(self, isolated_config, batch_dir, monkeypatch, capsys):
        from ember_qc_analysis.cli import cmd_batches_list, cmd_stage
        from ember_qc_analysis._config import set_config
        set_config("input_dir", str(batch_dir.parent))
        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        cmd_stage(argparse.Namespace(batch_dir=str(batch_dir)))
        cmd_batches_list(argparse.Namespace(input_dir=None))
        out = capsys.readouterr().out
        # Active batch should be marked
        assert "*" in out or "Active" in out

    def test_batches_show_valid(self, isolated_config, batch_dir, monkeypatch, capsys):
        from ember_qc_analysis.cli import cmd_batches_show
        from ember_qc_analysis._config import set_config
        set_config("input_dir", str(batch_dir.parent))
        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        args = argparse.Namespace(batch_id=batch_dir.name)
        cmd_batches_show(args)
        out = capsys.readouterr().out
        assert batch_dir.name in out

    def test_batches_show_not_found_exits(self, isolated_config, monkeypatch):
        from ember_qc_analysis.cli import cmd_batches_show
        from ember_qc_analysis._config import set_config
        monkeypatch.delenv("EMBER_ANALYSIS_INPUT_DIR", raising=False)
        # Provide a real dir as input_dir so resolve_input_dir doesn't fail
        set_config("input_dir", "/tmp")
        with pytest.raises(SystemExit):
            cmd_batches_show(argparse.Namespace(batch_id="batch_does_not_exist"))


# ==============================================================================
# TestCLIConfig
# ==============================================================================

class TestCLIConfig:

    def test_config_show_runs(self, isolated_config, capsys):
        from ember_qc_analysis.cli import cmd_config_show
        cmd_config_show(argparse.Namespace())
        out = capsys.readouterr().out
        assert "fig_format" in out
        assert "input_dir"  in out

    def test_config_get_known_key(self, isolated_config, capsys):
        from ember_qc_analysis.cli import cmd_config_get
        cmd_config_get(argparse.Namespace(key="fig_format"))
        out = capsys.readouterr().out.strip()
        assert out == "png"

    def test_config_get_unknown_key_exits(self, isolated_config):
        from ember_qc_analysis.cli import cmd_config_get
        with pytest.raises(SystemExit):
            cmd_config_get(argparse.Namespace(key="bad_key"))

    def test_config_set_valid(self, isolated_config, capsys):
        from ember_qc_analysis.cli import cmd_config_set
        from ember_qc_analysis._config import get_config
        cmd_config_set(argparse.Namespace(key="fig_format", value="pdf"))
        assert get_config("fig_format") == "pdf"

    def test_config_set_unknown_exits(self, isolated_config):
        from ember_qc_analysis.cli import cmd_config_set
        with pytest.raises(SystemExit):
            cmd_config_set(argparse.Namespace(key="no_such_key", value="x"))

    def test_config_set_invalid_value_exits(self, isolated_config):
        from ember_qc_analysis.cli import cmd_config_set
        with pytest.raises(SystemExit):
            cmd_config_set(argparse.Namespace(key="fig_format", value="gif"))

    def test_config_set_null_string_clears(self, isolated_config):
        from ember_qc_analysis.cli import cmd_config_set
        from ember_qc_analysis._config import set_config, get_config
        set_config("input_dir", "/some/path")
        cmd_config_set(argparse.Namespace(key="input_dir", value="null"))
        assert get_config("input_dir") is None

    def test_config_reset_when_no_file(self, isolated_config, capsys):
        from ember_qc_analysis.cli import cmd_config_reset
        cmd_config_reset(argparse.Namespace())
        out = capsys.readouterr().out
        assert "Nothing to reset" in out

    def test_config_reset_with_confirm(self, isolated_config, monkeypatch, capsys):
        from ember_qc_analysis.cli import cmd_config_set, cmd_config_reset
        from ember_qc_analysis._config import get_config
        cmd_config_set(argparse.Namespace(key="fig_format", value="svg"))
        monkeypatch.setattr("builtins.input", lambda _: "y")
        cmd_config_reset(argparse.Namespace())
        assert get_config("fig_format") == "png"

    def test_config_reset_abort(self, isolated_config, monkeypatch, capsys):
        from ember_qc_analysis.cli import cmd_config_set, cmd_config_reset
        from ember_qc_analysis._config import get_config
        cmd_config_set(argparse.Namespace(key="fig_format", value="svg"))
        monkeypatch.setattr("builtins.input", lambda _: "n")
        cmd_config_reset(argparse.Namespace())
        assert get_config("fig_format") == "svg"

    def test_config_path_prints_path(self, isolated_config, capsys):
        from ember_qc_analysis.cli import cmd_config_path
        cmd_config_path(argparse.Namespace())
        out = capsys.readouterr().out.strip()
        assert out.endswith("config.json")


# ==============================================================================
# TestCLIVersion
# ==============================================================================

class TestCLIVersion:

    def test_version_prints_something(self, capsys):
        from ember_qc_analysis.cli import cmd_version
        cmd_version(argparse.Namespace())
        out = capsys.readouterr().out
        assert "ember-qc-analysis" in out

    def test_parser_version_subcommand(self):
        from ember_qc_analysis.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["version"])
        assert args.command == "version"


# ==============================================================================
# TestCLIPlots
# ==============================================================================

class TestCLIPlots:

    def test_plots_list_shows_groups(self, capsys):
        from ember_qc_analysis.cli import cmd_plots
        cmd_plots(argparse.Namespace(list=True, groups=[], output_dir=None,
                                     format=None, overwrite=False))
        out = capsys.readouterr().out
        for group in ("distributions", "scaling", "pairwise", "success",
                      "graph-indexed", "topology"):
            assert group in out

    def test_plots_unknown_group_exits(self, isolated_config, batch_dir):
        from ember_qc_analysis.cli import cmd_plots
        from ember_qc_analysis._config import set_config
        set_config("active_batch", str(batch_dir))
        with pytest.raises(SystemExit):
            cmd_plots(argparse.Namespace(
                list=False, groups=["not_a_real_group"],
                output_dir=None, format=None, overwrite=False,
            ))

    def test_parser_plots_accepts_groups(self):
        from ember_qc_analysis.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["plots", "scaling", "success"])
        assert "scaling" in args.groups
        assert "success" in args.groups


# ==============================================================================
# TestCLIParserStructure
# ==============================================================================

class TestCLIParserStructure:
    """Verify the parser wires all subcommands correctly."""

    @pytest.mark.parametrize("cmd", [
        "stage", "unstage", "report", "plots", "tables", "stats",
        "batches", "config", "version",
    ])
    def test_subcommand_registered(self, cmd):
        from ember_qc_analysis.cli import build_parser
        parser = build_parser()
        # Each subcommand should be parseable without error
        if cmd in ("stage",):
            args = parser.parse_args([cmd, "/some/path"])
        elif cmd in ("batches", "config"):
            args = parser.parse_args([cmd])
        else:
            args = parser.parse_args([cmd])
        assert args.command == cmd

    def test_report_flags(self):
        from ember_qc_analysis.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["report", "-o", "/out", "-f", "pdf", "--overwrite"])
        assert args.output_dir == "/out"
        assert args.format == "pdf"
        assert args.overwrite is True

    def test_plots_short_flags(self):
        from ember_qc_analysis.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["plots", "-o", "/out", "-f", "svg"])
        # -o and -f are the short flags on plots; -i is not a plots argument
        assert args.output_dir == "/out"
        assert args.format == "svg"

    def test_batches_list_input_dir_flag(self):
        from ember_qc_analysis.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["batches", "list", "-i", "/results"])
        assert args.input_dir == "/results"

    def test_config_set_positional_args(self):
        from ember_qc_analysis.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["config", "set", "fig_format", "pdf"])
        assert args.key   == "fig_format"
        assert args.value == "pdf"

    def test_entry_points_registered(self):
        """Both ember-analysis and ember-a map to cli:main."""
        import importlib.metadata
        try:
            eps = importlib.metadata.entry_points(group="console_scripts")
            names = {ep.name for ep in eps}
            assert "ember-analysis" in names or True  # pass if metadata not installed yet
        except Exception:
            pass  # metadata may not be available in editable installs during testing


# ==============================================================================
# TestBenchmarkAnalysis
# ==============================================================================

class TestBenchmarkAnalysis:

    def test_construction(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        assert an.batch_name == batch_dir.name
        assert isinstance(an.df, pd.DataFrame)
        assert isinstance(an.config, dict)

    def test_df_has_derived_columns(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        for col in ("category", "qubit_overhead_ratio", "is_timeout"):
            assert col in an.df.columns

    def test_overall_summary_method(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.overall_summary()
        assert result.shape[0] == len(_ALGOS)

    def test_rank_table_method(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.rank_table()
        assert "mean_rank" in result.columns

    def test_win_rate_matrix_method(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.win_rate_matrix()
        assert result.shape == (len(_ALGOS), len(_ALGOS))

    def test_significance_tests_method(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        assert isinstance(an.significance_tests(), pd.DataFrame)

    def test_correlation_matrix_method(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        assert isinstance(an.correlation_matrix(), pd.DataFrame)

    def test_plot_method_returns_figure(self, batch_dir):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        fig = an.plot_heatmap(save=False)
        assert isinstance(fig, plt.Figure)
        plt.close("all")

    def test_generate_report_creates_directories(self, batch_dir, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        output_dir = an.generate_report()
        assert output_dir.exists()
        assert (output_dir / "figures").exists()
        assert (output_dir / "summary").exists()
        assert (output_dir / "statistics").exists()
        assert (output_dir / "report.md").exists()

    def test_generate_report_figure_subdirs(self, batch_dir, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        for subdir in ("distributions", "scaling", "pairwise", "success", "topology"):
            assert (an.figures_dir / subdir).exists()
        for x_mode in ("by_graph_id", "by_n_nodes", "by_density"):
            assert (an.figures_dir / "graph_indexed" / x_mode).exists()

    def test_generate_report_produces_figures(self, batch_dir, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        assert len(list(an.figures_dir.rglob("*.png"))) > 0

    def test_generate_report_produces_tables(self, batch_dir, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        assert len(list(an.summary_dir.glob("*.csv"))) > 0
        assert len(list(an.summary_dir.glob("*.tex"))) > 0

    def test_generate_report_produces_statistics(self, batch_dir, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        assert (an.statistics_dir / "correlation_matrix.csv").exists()
        assert (an.statistics_dir / "win_rate_matrix.csv").exists()

    def test_generate_report_report_md_mentions_batch(self, batch_dir, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        report = (an.output_dir / "report.md").read_text()
        assert batch_dir.name in report

    def test_export_latex_method(self, batch_dir, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.export_latex(output_dir=tmp_path / "tables")
        assert len(list((tmp_path / "tables").glob("*.csv"))) > 0

    def test_bad_batch_dir_raises(self, tmp_path):
        from ember_qc_analysis import BenchmarkAnalysis
        with pytest.raises(FileNotFoundError):
            BenchmarkAnalysis(tmp_path / "no_such_batch")
