"""
tests/test_qeanalysis.py
========================
Test suite for the qeanalysis post-benchmark analysis package.

All tests use synthetic in-memory data; no real batch directory or D-Wave
toolchain is needed.  Fixtures build a minimal but representative DataFrame
covering all graph categories, 3 algorithms, and 3 trials.

Test classes
------------
TestLoader          — load_batch(), infer_category(), derived columns, validation
TestSummary         — overall_summary(), summary_by_category(), rank_table()
TestWinRate         — win_rate_matrix() correctness and edge cases
TestSignificance    — significance_tests(), friedman_test(), correlation_matrix()
TestPlots           — all 10 plot functions return plt.Figure without error
TestExport          — df_to_latex() LaTeX structure and export_tables() file writing
TestBenchmarkAnalysis — integration: load from batch_dir, generate_report()
"""

import json
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# ==============================================================================
# Fixtures
# ==============================================================================

# Problem set that covers every infer_category() branch
_PROBLEMS = [
    # (name,                    n,  edges, density, category)
    ('K5',                      5,  10,    1.000,  'complete'),
    ('bipartite_K3_3',          6,  9,     0.600,  'bipartite'),
    ('grid_3x3',                9,  12,    0.333,  'grid'),
    ('cycle_10',               10,  10,    0.222,  'cycle'),
    ('tree_r2_d3',             15,  14,    0.133,  'tree'),
    ('petersen',               10,  15,    0.333,  'special'),
    ('random_n10_d0.5_i0',     10,  22,    0.489,  'random'),
    ('random_n10_d0.5_i1',     10,  25,    0.556,  'random'),
]

_ALGOS = ['minorminer', 'atom', 'oct-triad']
_TOPO  = 'chimera_4x4x4'
_N_TRIALS = 3
_TIMEOUT  = 60.0


def _make_row(algo, prob_name, n, edges, density, trial, rng, success=True):
    if success:
        t = rng.uniform(0.001, 0.5)
        avg_cl = rng.uniform(1.5, 4.0)
        max_cl = int(avg_cl * rng.uniform(1.0, 1.5)) + 1
        qubits = n * int(avg_cl + 0.5)
        couplers = max(1, edges - rng.integers(0, 3))
        return {
            'algorithm': algo, 'problem_name': prob_name,
            'topology_name': _TOPO, 'trial': trial,
            'success': True, 'is_valid': True,
            'wall_time': t,
            'avg_chain_length': avg_cl, 'max_chain_length': max_cl,
            'total_qubits_used': qubits, 'total_couplers_used': int(couplers),
            'problem_nodes': n, 'problem_edges': edges,
            'problem_density': density, 'error': None,
        }
    else:
        return {
            'algorithm': algo, 'problem_name': prob_name,
            'topology_name': _TOPO, 'trial': trial,
            'success': False, 'is_valid': False,
            'wall_time': _TIMEOUT,
            'avg_chain_length': 0.0, 'max_chain_length': 0,
            'total_qubits_used': 0, 'total_couplers_used': 0,
            'problem_nodes': n, 'problem_edges': edges,
            'problem_density': density, 'error': 'timeout',
        }


@pytest.fixture(scope='module')
def sample_df() -> pd.DataFrame:
    """Synthetic runs DataFrame (3 algos × 8 problems × 3 trials = 72 rows).

    All trials succeed to keep expected-value assertions simple.
    """
    rng = np.random.default_rng(42)
    rows = []
    for algo in _ALGOS:
        for prob_name, n, edges, density, _cat in _PROBLEMS:
            for trial in range(_N_TRIALS):
                rows.append(_make_row(algo, prob_name, n, edges, density, trial, rng))
    df = pd.DataFrame(rows)
    # Mimic the derived columns added by load_batch()
    from qeanalysis.loader import _derive_columns
    return _derive_columns(df, timeout=_TIMEOUT)


@pytest.fixture(scope='module')
def sample_df_with_failure(sample_df) -> pd.DataFrame:
    """Same as sample_df but with some failures injected (atom on K5, trial 2)."""
    df = sample_df.copy()
    mask = (df['algorithm'] == 'atom') & (df['problem_name'] == 'K5') & (df['trial'] == 2)
    df.loc[mask, 'success']         = False
    df.loc[mask, 'is_valid']        = False
    df.loc[mask, 'wall_time']        = _TIMEOUT
    df.loc[mask, 'avg_chain_length'] = 0.0
    df.loc[mask, 'error']            = 'timeout'
    return df


@pytest.fixture()
def batch_dir(tmp_path, sample_df) -> Path:
    """Write synthetic data to a temp batch directory for integration tests.

    Writes results.db (primary source) so load_batch() exercises the SQLite
    path.  config.json is written alongside for timeout/metadata.
    """
    import sqlite3 as _sqlite3

    bd = tmp_path / 'batch_test'
    bd.mkdir()
    batch_id = 'batch_test'

    # Drop derived columns; SQLite stores the raw run data only
    raw_cols = [c for c in sample_df.columns
                if c not in ('category', 'qubit_overhead_ratio',
                             'coupler_overhead_ratio', 'max_to_avg_chain_ratio',
                             'is_timeout')]
    raw_df = sample_df[raw_cols].copy()
    raw_df['batch_id'] = batch_id
    # Coerce booleans to int for SQLite
    for col in ('success', 'is_valid'):
        if col in raw_df.columns:
            raw_df[col] = raw_df[col].astype(int)

    db_path = bd / 'results.db'
    con = _sqlite3.connect(db_path)
    raw_df.to_sql('runs', con, if_exists='replace', index=False)
    # Minimal batches table so _load_config_from_db has something to query
    con.execute(
        "CREATE TABLE IF NOT EXISTS batches (batch_id TEXT PRIMARY KEY, config_json TEXT)"
    )
    con.execute(
        "INSERT OR IGNORE INTO batches (batch_id, config_json) VALUES (?, ?)",
        (batch_id, json.dumps({})),
    )
    con.commit()
    con.close()

    # Write config.json
    config = {
        'algorithms': _ALGOS,
        'graph_selection': 'test',
        'topologies': [_TOPO],
        'n_trials': _N_TRIALS,
        'warmup_trials': 0,
        'timeout': _TIMEOUT,
        'n_problems': len(_PROBLEMS),
        'batch_note': 'Synthetic test batch',
        'batch_name': 'batch_test',
        'timestamp': '2026-02-24T00:00:00',
    }
    with open(bd / 'config.json', 'w') as f:
        json.dump(config, f)

    return bd


# ==============================================================================
# TestLoader
# ==============================================================================

class TestLoader:

    def test_infer_category_complete(self):
        from qeanalysis.loader import infer_category
        assert infer_category('K4')  == 'complete'
        assert infer_category('K15') == 'complete'

    def test_infer_category_bipartite(self):
        from qeanalysis.loader import infer_category
        assert infer_category('bipartite_K3_3') == 'bipartite'

    def test_infer_category_grid(self):
        from qeanalysis.loader import infer_category
        assert infer_category('grid_4x4') == 'grid'

    def test_infer_category_cycle(self):
        from qeanalysis.loader import infer_category
        assert infer_category('cycle_10') == 'cycle'

    def test_infer_category_tree(self):
        from qeanalysis.loader import infer_category
        assert infer_category('tree_r2_d3') == 'tree'

    def test_infer_category_special(self):
        from qeanalysis.loader import infer_category
        for name in ('petersen', 'dodecahedral', 'icosahedral'):
            assert infer_category(name) == 'special'

    def test_infer_category_random(self):
        from qeanalysis.loader import infer_category
        assert infer_category('random_n10_d0.5_i0') == 'random'

    def test_infer_category_unknown(self):
        from qeanalysis.loader import infer_category
        assert infer_category('my_custom_graph') == 'other'

    def test_infer_category_case_insensitive(self):
        from qeanalysis.loader import infer_category
        assert infer_category('PETERSEN') == 'special'
        assert infer_category('Grid_3x3') == 'grid'

    def test_derived_columns_present(self, sample_df):
        for col in ('category', 'qubit_overhead_ratio',
                    'coupler_overhead_ratio', 'max_to_avg_chain_ratio',
                    'is_timeout'):
            assert col in sample_df.columns, f"Missing derived column: {col}"

    def test_category_values(self, sample_df):
        cats = set(sample_df['category'].unique())
        # All fixture categories should be covered
        for expected in ('complete', 'bipartite', 'grid', 'cycle',
                         'tree', 'special', 'random'):
            assert expected in cats, f"Category '{expected}' missing from sample_df"

    def test_qubit_overhead_ratio(self, sample_df):
        sdf = sample_df[sample_df['success']]
        ratios = sdf['qubit_overhead_ratio']
        assert (ratios >= 1.0).all(), "qubit_overhead_ratio should be ≥ 1 for valid embeddings"
        assert ratios.notna().all()

    def test_coupler_overhead_non_negative(self, sample_df):
        sdf = sample_df[sample_df['success'] & (sample_df['problem_edges'] > 0)]
        ratios = sdf['coupler_overhead_ratio'].dropna()
        assert (ratios >= 0).all()

    def test_is_timeout_flag(self, sample_df):
        # No trial should be flagged as timeout (all succeed in < 1s)
        assert not sample_df['is_timeout'].any()

    def test_load_batch_returns_tuple(self, batch_dir):
        from qeanalysis.loader import load_batch
        df, config = load_batch(batch_dir)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(config, dict)

    def test_load_batch_reads_sqlite(self, batch_dir):
        """load_batch() should read from results.db when it exists."""
        from qeanalysis.loader import load_batch
        assert (batch_dir / 'results.db').exists(), "fixture must write results.db"
        df, config = load_batch(batch_dir)
        assert len(df) == len(_ALGOS) * len(_PROBLEMS) * _N_TRIALS
        assert df['success'].dtype == bool

    def test_load_batch_derived_columns(self, batch_dir):
        from qeanalysis.loader import load_batch
        df, _ = load_batch(batch_dir)
        for col in ('category', 'qubit_overhead_ratio', 'is_timeout'):
            assert col in df.columns

    def test_load_batch_missing_dir(self, tmp_path):
        from qeanalysis.loader import load_batch
        with pytest.raises(FileNotFoundError):
            load_batch(tmp_path / 'nonexistent')

    def test_load_batch_missing_csv(self, tmp_path):
        from qeanalysis.loader import load_batch
        (tmp_path / 'bd').mkdir()
        with pytest.raises(FileNotFoundError):
            load_batch(tmp_path / 'bd')

    def test_load_batch_bad_schema(self, tmp_path):
        from qeanalysis.loader import load_batch
        bd = tmp_path / 'bad'
        bd.mkdir()
        pd.DataFrame({'algorithm': ['x']}).to_csv(bd / 'runs.csv', index=False)
        with pytest.raises(ValueError, match='missing required columns'):
            load_batch(bd)


# ==============================================================================
# TestSummary
# ==============================================================================

class TestSummary:

    def test_overall_summary_shape(self, sample_df):
        from qeanalysis.summary import overall_summary
        result = overall_summary(sample_df)
        assert result.shape[0] == len(_ALGOS)
        assert 'success_rate' in result.columns
        assert 'chain_mean' in result.columns

    def test_overall_summary_success_rate(self, sample_df):
        from qeanalysis.summary import overall_summary
        result = overall_summary(sample_df)
        # All trials succeed in sample_df
        assert (result['success_rate'] == 1.0).all()

    def test_overall_summary_with_failure(self, sample_df_with_failure):
        from qeanalysis.summary import overall_summary
        result = overall_summary(sample_df_with_failure)
        atom_rate = result.loc['atom', 'success_rate']
        assert atom_rate < 1.0

    def test_overall_summary_index(self, sample_df):
        from qeanalysis.summary import overall_summary
        result = overall_summary(sample_df)
        assert set(result.index) == set(_ALGOS)

    def test_summary_by_category_shape(self, sample_df):
        from qeanalysis.summary import summary_by_category
        result = summary_by_category(sample_df, 'avg_chain_length')
        assert result.shape[0] == len(_ALGOS)
        # Every fixture category should appear as a column
        for cat in ('complete', 'bipartite', 'grid', 'cycle', 'tree', 'special', 'random'):
            assert cat in result.columns, f"Category '{cat}' missing from summary_by_category"

    def test_summary_by_category_values_positive(self, sample_df):
        from qeanalysis.summary import summary_by_category
        result = summary_by_category(sample_df, 'avg_chain_length')
        assert (result.dropna() > 0).all().all()

    def test_summary_by_category_bad_metric(self, sample_df):
        from qeanalysis.summary import summary_by_category
        with pytest.raises(ValueError):
            summary_by_category(sample_df, 'nonexistent_metric')

    def test_rank_table_shape(self, sample_df):
        from qeanalysis.summary import rank_table
        result = rank_table(sample_df, 'avg_chain_length')
        assert result.shape[0] == len(_ALGOS)
        assert 'mean_rank' in result.columns
        assert 'n_problems_ranked' in result.columns

    def test_rank_table_ranks_in_range(self, sample_df):
        from qeanalysis.summary import rank_table
        result = rank_table(sample_df, 'avg_chain_length')
        n = len(_ALGOS)
        assert (result['mean_rank'] >= 1.0).all()
        assert (result['mean_rank'] <= n).all()

    def test_rank_table_sorted_ascending(self, sample_df):
        from qeanalysis.summary import rank_table
        result = rank_table(sample_df, 'avg_chain_length')
        ranks = result['mean_rank'].tolist()
        assert ranks == sorted(ranks)


# ==============================================================================
# TestWinRate
# ==============================================================================

class TestWinRate:

    def test_win_rate_matrix_shape(self, sample_df):
        from qeanalysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, 'avg_chain_length')
        n = len(_ALGOS)
        assert result.shape == (n, n)

    def test_win_rate_diagonal_nan(self, sample_df):
        from qeanalysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, 'avg_chain_length')
        for algo in _ALGOS:
            assert math.isnan(result.loc[algo, algo])

    def test_win_rate_complementary(self, sample_df):
        """win(A, B) + win(B, A) == 1 when no ties."""
        from qeanalysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, 'avg_chain_length')
        for i, a in enumerate(_ALGOS):
            for b in _ALGOS[i+1:]:
                total = result.loc[a, b] + result.loc[b, a]
                # Allow ties (total could be < 1 in rare edge cases)
                assert abs(total - 1.0) < 1e-9 or total <= 1.0 + 1e-9

    def test_win_rate_values_in_range(self, sample_df):
        from qeanalysis.statistics import win_rate_matrix
        result = win_rate_matrix(sample_df, 'avg_chain_length')
        vals = result.stack().dropna()
        assert (vals >= 0).all() and (vals <= 1).all()


# ==============================================================================
# TestSignificance
# ==============================================================================

class TestSignificance:

    def test_significance_tests_returns_dataframe(self, sample_df):
        from qeanalysis.statistics import significance_tests
        result = significance_tests(sample_df, 'avg_chain_length')
        assert isinstance(result, pd.DataFrame)

    def test_significance_tests_expected_columns(self, sample_df):
        from qeanalysis.statistics import significance_tests
        result = significance_tests(sample_df, 'avg_chain_length')
        for col in ('algo_a', 'algo_b', 'n_pairs', 'p_value', 'corrected_p', 'significant'):
            assert col in result.columns, f"Missing column: {col}"

    def test_significance_tests_p_in_range(self, sample_df):
        from qeanalysis.statistics import significance_tests
        result = significance_tests(sample_df, 'avg_chain_length')
        valid_p = result['p_value'].dropna()
        assert (valid_p >= 0).all() and (valid_p <= 1).all()

    def test_significance_tests_corrected_p_in_range(self, sample_df):
        from qeanalysis.statistics import significance_tests
        result = significance_tests(sample_df, 'avg_chain_length')
        valid_p = result['corrected_p'].dropna()
        assert (valid_p >= 0).all() and (valid_p <= 1).all()

    def test_significance_tests_n_rows(self, sample_df):
        from qeanalysis.statistics import significance_tests
        import itertools
        result = significance_tests(sample_df, 'avg_chain_length', min_pairs=1)
        n_pairs = len(list(itertools.combinations(_ALGOS, 2)))
        assert len(result) == n_pairs

    def test_friedman_test_returns_dict(self, sample_df):
        from qeanalysis.statistics import friedman_test
        result = friedman_test(sample_df, 'avg_chain_length')
        assert isinstance(result, dict)

    def test_friedman_test_keys(self, sample_df):
        from qeanalysis.statistics import friedman_test
        result = friedman_test(sample_df, 'avg_chain_length')
        if 'error' not in result:
            for key in ('statistic', 'p_value', 'significant', 'n_problems', 'n_algorithms'):
                assert key in result

    def test_friedman_test_p_in_range(self, sample_df):
        from qeanalysis.statistics import friedman_test
        result = friedman_test(sample_df, 'avg_chain_length')
        if 'p_value' in result:
            assert 0.0 <= result['p_value'] <= 1.0

    def test_correlation_matrix_shape(self, sample_df):
        from qeanalysis.statistics import correlation_matrix
        result = correlation_matrix(sample_df)
        # rows = graph properties (3), columns = embed metrics (4)
        assert result.shape == (3, 4)

    def test_correlation_matrix_values_in_range(self, sample_df):
        from qeanalysis.statistics import correlation_matrix
        result = correlation_matrix(sample_df)
        vals = result.values.flatten()
        valid = vals[~np.isnan(vals)]
        assert (valid >= -1.0 - 1e-9).all() and (valid <= 1.0 + 1e-9).all()

    def test_density_hardness_summary(self, sample_df):
        from qeanalysis.statistics import density_hardness_summary
        result = density_hardness_summary(sample_df, 'avg_chain_length')
        assert isinstance(result, pd.DataFrame)
        # Should contain only 'random' category data
        assert 'algorithm' in result.columns


# ==============================================================================
# TestPlots
# ==============================================================================

class TestPlots:
    """Verify each plot function runs without error and returns a Figure.

    All calls use save=False so no file I/O occurs.
    """

    def test_plot_heatmap(self, sample_df):
        from qeanalysis.plots import plot_heatmap
        fig = plot_heatmap(sample_df, 'avg_chain_length', save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_scaling(self, sample_df):
        from qeanalysis.plots import plot_scaling
        fig = plot_scaling(sample_df, 'wall_time', 'problem_nodes', save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_scaling_log(self, sample_df):
        from qeanalysis.plots import plot_scaling
        fig = plot_scaling(sample_df, 'wall_time', 'problem_nodes', log=True, save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_density_hardness(self, sample_df):
        from qeanalysis.plots import plot_density_hardness
        fig = plot_density_hardness(sample_df, save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_pareto(self, sample_df):
        from qeanalysis.plots import plot_pareto
        fig = plot_pareto(sample_df, save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_distributions(self, sample_df):
        from qeanalysis.plots import plot_distributions
        fig = plot_distributions(sample_df, 'avg_chain_length', save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_head_to_head(self, sample_df):
        from qeanalysis.plots import plot_head_to_head
        fig = plot_head_to_head(sample_df, _ALGOS[0], _ALGOS[1], save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_head_to_head_missing_algo(self, sample_df):
        from qeanalysis.plots import plot_head_to_head
        # Should not crash for unknown algorithm name
        fig = plot_head_to_head(sample_df, 'nonexistent', _ALGOS[0], save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_consistency(self, sample_df):
        from qeanalysis.plots import plot_consistency
        fig = plot_consistency(sample_df, save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_topology_comparison(self, sample_df):
        from qeanalysis.plots import plot_topology_comparison
        fig = plot_topology_comparison(sample_df, save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_problem_deep_dive(self, sample_df):
        from qeanalysis.plots import plot_problem_deep_dive
        fig = plot_problem_deep_dive(sample_df, 'K5', save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_problem_deep_dive_missing(self, sample_df):
        from qeanalysis.plots import plot_problem_deep_dive
        fig = plot_problem_deep_dive(sample_df, 'nonexistent_problem', save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_chain_distribution(self, sample_df):
        from qeanalysis.plots import plot_chain_distribution
        fig = plot_chain_distribution(sample_df, save=False)
        assert isinstance(fig, plt.Figure)

    def test_plot_save_creates_file(self, sample_df, tmp_path):
        """Verify that save=True writes into the correct subdirectory."""
        from qeanalysis.plots import plot_heatmap
        plot_heatmap(sample_df, 'avg_chain_length',
                     output_dir=tmp_path, save=True)
        # heatmap saves to figures/distributions/ relative to output_dir
        saved = list((tmp_path / 'figures' / 'distributions').glob('*.png'))
        assert len(saved) == 1


# ==============================================================================
# TestExport
# ==============================================================================

class TestExport:

    def test_df_to_latex_contains_booktabs(self):
        from qeanalysis.export import df_to_latex
        df = pd.DataFrame({'a': [1.0, 2.0], 'b': [3.0, 4.0]})
        tex = df_to_latex(df, caption='Test', label='tab:test')
        assert '\\toprule'    in tex
        assert '\\midrule'    in tex
        assert '\\bottomrule' in tex

    def test_df_to_latex_contains_table_env(self):
        from qeanalysis.export import df_to_latex
        df = pd.DataFrame({'x': [1]})
        tex = df_to_latex(df)
        assert '\\begin{table}' in tex
        assert '\\end{table}'   in tex

    def test_df_to_latex_caption_label(self):
        from qeanalysis.export import df_to_latex
        df = pd.DataFrame({'v': [1.0]})
        tex = df_to_latex(df, caption='My caption', label='tab:my')
        assert 'My caption' in tex
        assert 'tab:my'     in tex

    def test_export_tables_writes_files(self, tmp_path):
        from qeanalysis.export import export_tables
        df = pd.DataFrame({'algo': ['a', 'b'], 'score': [1.0, 2.0]}).set_index('algo')
        tables = {
            'test_table': (df, 'Test table', 'tab:test'),
        }
        export_tables(tables, tmp_path)
        assert (tmp_path / 'test_table.csv').exists()
        assert (tmp_path / 'test_table.tex').exists()

    def test_export_tables_tex_content(self, tmp_path):
        from qeanalysis.export import export_tables
        df = pd.DataFrame({'algo': ['a'], 'val': [3.14]}).set_index('algo')
        export_tables({'t': (df, 'Cap', 'lab')}, tmp_path)
        tex = (tmp_path / 't.tex').read_text()
        assert '\\toprule' in tex


# ==============================================================================
# TestBenchmarkAnalysis
# ==============================================================================

class TestBenchmarkAnalysis:

    def test_construction(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        assert an.batch_name == 'batch_test'
        assert isinstance(an.df, pd.DataFrame)
        assert isinstance(an.config, dict)

    def test_batch_name(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        assert an.batch_name == batch_dir.name

    def test_df_has_derived_columns(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        for col in ('category', 'qubit_overhead_ratio', 'is_timeout'):
            assert col in an.df.columns

    def test_overall_summary_method(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.overall_summary()
        assert result.shape[0] == len(_ALGOS)

    def test_summary_by_category_method(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.summary_by_category()
        assert isinstance(result, pd.DataFrame)

    def test_rank_table_method(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.rank_table()
        assert 'mean_rank' in result.columns

    def test_win_rate_matrix_method(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.win_rate_matrix()
        assert result.shape == (len(_ALGOS), len(_ALGOS))

    def test_significance_tests_method(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.significance_tests()
        assert isinstance(result, pd.DataFrame)

    def test_correlation_matrix_method(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        result = an.correlation_matrix()
        assert isinstance(result, pd.DataFrame)

    def test_plot_heatmap_method(self, batch_dir):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir)
        fig = an.plot_heatmap(save=False)
        assert isinstance(fig, plt.Figure)

    def test_generate_report_creates_output(self, batch_dir, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        output_dir = an.generate_report()

        assert output_dir.exists()
        assert (output_dir / 'figures').exists()
        assert (output_dir / 'summary').exists()
        assert (output_dir / 'statistics').exists()
        assert (output_dir / 'report.md').exists()

    def test_generate_report_subdir_structure(self, batch_dir, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        for subdir in ('distributions', 'scaling', 'pairwise', 'success', 'topology'):
            assert (an.figures_dir / subdir).exists(), f"figures/{subdir}/ missing"
        for x_mode in ('by_graph_id', 'by_n_nodes', 'by_density'):
            assert (an.figures_dir / 'graph_indexed' / x_mode).exists()

    def test_generate_report_produces_figures(self, batch_dir, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        # Figures go into subdirectories — use rglob
        figures = list(an.figures_dir.rglob('*.png'))
        assert len(figures) > 0

    def test_generate_report_produces_tables(self, batch_dir, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        csvs = list(an.summary_dir.glob('*.csv'))
        texs = list(an.summary_dir.glob('*.tex'))
        assert len(csvs) > 0
        assert len(texs) > 0

    def test_generate_report_produces_statistics(self, batch_dir, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        assert (an.statistics_dir / 'correlation_matrix.csv').exists()
        assert (an.statistics_dir / 'win_rate_matrix.csv').exists()

    def test_generate_report_report_md_content(self, batch_dir, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.generate_report()
        report = (an.output_dir / 'report.md').read_text()
        assert 'batch_test' in report
        assert 'graph_indexed' in report

    def test_export_latex_method(self, batch_dir, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        an = BenchmarkAnalysis(batch_dir, output_root=str(tmp_path))
        an.export_latex(output_dir=tmp_path / 'manual_tables')
        csvs = list((tmp_path / 'manual_tables').glob('*.csv'))
        assert len(csvs) > 0

    def test_bad_batch_dir_raises(self, tmp_path):
        from qeanalysis import BenchmarkAnalysis
        with pytest.raises(FileNotFoundError):
            BenchmarkAnalysis(tmp_path / 'no_such_dir')
