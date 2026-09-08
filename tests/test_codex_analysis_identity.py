"""Problem identity and pairing regressions using the current run schema."""

import warnings

import numpy as np
import pandas as pd
import pytest

from ember_qc_analysis.statistics import (
    _per_problem_means,
    friedman_test,
    significance_tests,
    win_rate_matrix,
)
from ember_qc_analysis.summary import rank_table


def _row(algorithm, value, graph_id=1, **overrides):
    row = {
        'algorithm': algorithm,
        'algorithm_version': '1.0',
        'graph_id': graph_id,
        'graph_name': 'same_display_name',
        'topology_name': 'zephyr_12',
        'batch_id': 'batch_one',
        'trial': 0,
        'success': True,
        'avg_chain_length': value,
    }
    row.update(overrides)
    return row


def _collision_frame():
    return pd.DataFrame([
        _row('A', 1, 1), _row('A', 3, 1, trial=1), _row('B', 3, 1),
        _row('A', 7, 2), _row('A', 9, 2, trial=1), _row('B', 7, 2),
    ])


def test_same_names_do_not_merge_graph_ids_or_reweight_trial_means():
    frame = _collision_frame()
    original = frame.copy(deep=True)
    means = _per_problem_means(frame, 'avg_chain_length')
    assert len(means) == 2
    assert means['A'].tolist() == [2, 8]
    assert means['B'].tolist() == [3, 7]
    ranks = rank_table(frame)
    assert ranks.loc['A', 'n_problems_ranked'] == 2
    assert ranks.loc['B', 'n_problems_ranked'] == 2
    assert ranks.loc['A', 'mean_rank'] == 1.5
    assert ranks.loc['B', 'mean_rank'] == 1.5
    wins = win_rate_matrix(frame)
    assert wins.loc['A', 'B'] == 0.5
    assert wins.loc['B', 'A'] == 0.5
    pd.testing.assert_frame_equal(frame, original)


def test_display_name_changes_do_not_split_a_manifest_graph():
    frame = pd.DataFrame([
        _row('A', 1, graph_name='first_name'),
        _row('A', 3, graph_name='renamed', trial=1),
        _row('B', 4, graph_name='third_name'),
    ])
    means = _per_problem_means(frame, 'avg_chain_length')
    assert len(means) == 1
    assert means.iloc[0].to_dict() == {'A': 2, 'B': 4}


@pytest.mark.parametrize(
    ('field', 'values'),
    [
        ('topology_name', ['zephyr_12', 'zephyr_3']),
        ('topology_name', ['zephyr_12', 'pegasus_16']),
        ('topology_name', ['zephyr_12_fr0.01_seed1', 'zephyr_12_fr0.01_seed2']),
        ('batch_id', ['quality_budget', 'short_budget']),
    ],
)
def test_same_graph_on_different_hardware_or_batches_is_separate(field, values):
    rows = []
    for i, value in enumerate(values):
        rows.extend([_row('A', 1 + i, **{field: value}), _row('B', 4 + i, **{field: value})])
    frame = pd.DataFrame(rows)
    assert len(_per_problem_means(frame, 'avg_chain_length')) == 2
    assert significance_tests(frame)['n_pairs'].tolist() == [2]
    assert rank_table(frame)['n_problems_ranked'].tolist() == [2, 2]


@pytest.mark.parametrize('field', ['graph_id', 'topology_name', 'batch_id'])
def test_unmatched_identities_are_not_pairs_or_failures(field):
    values = [1, 2] if field == 'graph_id' else ['one', 'two']
    frame = pd.DataFrame([
        _row('A', 1, **{field: values[0]}),
        _row('B', 2, **{field: values[1]}),
    ])
    assert significance_tests(frame)['n_pairs'].tolist() == [0]
    assert rank_table(frame).empty
    assert np.isnan(win_rate_matrix(frame).loc['A', 'B'])
    assert np.isnan(win_rate_matrix(frame).loc['B', 'A'])


def test_view_source_batch_supplies_batch_provenance():
    frame = pd.DataFrame([_row('A', 1), _row('B', 2)])
    frame = frame.drop(columns='batch_id').assign(source_batch='source_one')
    with warnings.catch_warnings():
        warnings.simplefilter('error', UserWarning)
        means = _per_problem_means(frame, 'avg_chain_length')
    assert means.index.get_level_values('batch_id').tolist() == ['source_one']


def test_different_algorithm_versions_can_be_compared():
    frame = pd.DataFrame([_row('A', 1, algorithm_version='2.0'), _row('B', 2, algorithm_version='9.0')])
    assert significance_tests(frame)['n_pairs'].tolist() == [1]


@pytest.mark.parametrize('version', ['2.0', None])
def test_one_cell_cannot_pool_multiple_or_unknown_algorithm_versions(version):
    frame = pd.DataFrame([_row('A', 1), _row('A', 9, algorithm_version=version), _row('B', 2)])
    with pytest.raises(ValueError, match='Multiple algorithm_version'):
        rank_table(frame)


def test_versions_in_separate_batches_do_not_merge():
    frame = pd.DataFrame([
        _row('A', 1), _row('B', 2),
        _row('A', 3, algorithm_version='2.0', batch_id='batch_two'),
        _row('B', 4, batch_id='batch_two'),
    ])
    means = _per_problem_means(frame, 'avg_chain_length')
    assert len(means) == 2
    assert means['A'].tolist() == [1, 3]


@pytest.mark.parametrize('id_value', [0, None, np.nan])
def test_custom_and_legacy_ids_use_warned_name_fallback(id_value):
    frame = pd.DataFrame([
        _row('A', 1, id_value, graph_name='first'), _row('B', 2, id_value, graph_name='first'),
        _row('A', 3, id_value, graph_name='second'), _row('B', 4, id_value, graph_name='second'),
    ])
    with pytest.warns(UserWarning, match='positive graph_id'):
        means = _per_problem_means(frame, 'avg_chain_length')
    assert len(means) == 2


def test_custom_graph_sizes_separate_obvious_same_name_collisions():
    frame = pd.DataFrame([
        _row('A', 1, 0, problem_nodes=10, problem_edges=20),
        _row('A', 3, 0, problem_nodes=20, problem_edges=40),
    ])
    with pytest.warns(UserWarning, match='Legacy fallback'):
        assert len(_per_problem_means(frame, 'avg_chain_length')) == 2


def test_missing_legacy_columns_warn_and_preserve_name_based_means():
    frame = pd.DataFrame([_row('A', 1), _row('A', 3), _row('B', 4)])
    frame = frame.drop(columns=['graph_id', 'topology_name', 'batch_id'])
    frame = frame.rename(columns={'graph_name': 'problem_name'})
    with pytest.warns(UserWarning, match='configuration equivalence unverified'):
        means = _per_problem_means(frame, 'avg_chain_length')
    assert means.iloc[0].to_dict() == {'A': 2, 'B': 4}


@pytest.mark.parametrize('field', ['graph_id', 'topology_name', 'batch_id'])
def test_partial_identity_nulls_are_preserved_separately(field):
    frame = pd.DataFrame([
        _row('A', 1), _row('B', 2),
        _row('A', 3, **{field: None}), _row('B', 4, **{field: None}),
    ])
    with pytest.warns(UserWarning, match='Incomplete problem identity'):
        means = _per_problem_means(frame, 'avg_chain_length')
    assert len(means) == 2
    assert means['A'].sum() == 4


def test_unknown_graph_without_name_cannot_be_grouped():
    frame = pd.DataFrame([_row('A', 1, 0)]).drop(columns='graph_name')
    with pytest.raises(ValueError, match='Cannot identify a problem'):
        _per_problem_means(frame, 'avg_chain_length')


def test_all_failed_algorithm_remains_comparable_on_attempted_problems():
    frame = pd.DataFrame([_row('A', 2), _row('B', 0, success=False)])
    means = _per_problem_means(frame, 'avg_chain_length')
    assert list(means.columns) == ['A', 'B']
    assert np.isnan(means.iloc[0]['B'])
    wins = win_rate_matrix(frame)
    assert wins.loc['A', 'B'] == 1
    assert wins.loc['B', 'A'] == 0
    assert significance_tests(frame)['n_pairs'].tolist() == [0]


def test_failed_trials_do_not_change_successful_trial_mean():
    frame = pd.DataFrame([_row('A', 2), _row('A', 0, success=False), _row('B', 3)])
    assert _per_problem_means(frame, 'avg_chain_length').iloc[0]['A'] == 2


def test_both_failed_problem_does_not_enter_win_denominator():
    frame = pd.DataFrame([
        _row('A', 1, 1), _row('B', 2, 1),
        _row('A', 0, 2, success=False), _row('B', 0, 2, success=False),
    ])
    assert win_rate_matrix(frame).loc['A', 'B'] == 1


def test_significance_uses_distinct_graphs_even_when_names_collide():
    frame = pd.DataFrame([_row(algo, gid + offset, gid) for gid in range(1, 7) for algo, offset in [('A', 0), ('B', 1)]])
    result = significance_tests(frame)
    assert result['n_pairs'].tolist() == [6]
    assert result['p_value'].notna().all()


def test_friedman_uses_graph_identity_for_complete_blocks():
    frame = pd.DataFrame([_row(algo, value, gid) for gid in range(1, 4) for algo, value in [('A', 1), ('B', 2), ('C', 3)]])
    result = friedman_test(frame)
    assert 'error' not in result
    assert result['n_problems'] == 3
    assert result['mean_ranks'] == {'A': 1, 'B': 2, 'C': 3}


def test_empty_frame_produces_empty_tables():
    frame = pd.DataFrame([_row('A', 1)]).iloc[:0]
    assert _per_problem_means(frame, 'avg_chain_length').empty
    assert rank_table(frame).empty
    assert win_rate_matrix(frame).empty
    assert significance_tests(frame).empty
