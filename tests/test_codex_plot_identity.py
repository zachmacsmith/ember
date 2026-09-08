"""Plot data must retain the source/target/batch identity used by statistics."""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from ember_qc_analysis import plots
from ember_qc_analysis.statistics import _per_problem_means


def _row(algorithm, acl, graph_id=1, **overrides):
    result = {
        'algorithm': algorithm,
        'algorithm_version': '1.0',
        'graph_id': graph_id,
        'graph_name': 'shared_name',
        'topology_name': 'zephyr_12',
        'batch_id': 'batch_one',
        'category': 'random_er',
        'trial': 0,
        'success': True,
        'is_valid': True,
        'is_timeout': False,
        'avg_chain_length': acl,
        'max_chain_length': acl + 1,
        'wall_time': acl / 10,
        'total_qubits_used': acl * 10,
        'qubit_overhead_ratio': acl,
        'problem_nodes': 10,
        'problem_edges': 20,
        'problem_density': 0.4,
    }
    result.update(overrides)
    return result


def _collision_frame():
    return pd.DataFrame([
        _row('A', 1, 1), _row('A', 3, 1, trial=1), _row('B', 3, 1),
        _row('A', 7, 2), _row('A', 9, 2, trial=1), _row('B', 7, 2),
    ])


def _heatmap_values(fig, shape):
    return np.asarray(fig.axes[0].collections[0].get_array()).reshape(shape)


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close('all')


def test_plot_identity_matches_statistics_and_does_not_mutate_input():
    frame = _collision_frame()
    original = frame.copy(deep=True)
    rows = plots._identified_plot_rows(frame)
    assert rows['_problem_id'].nunique() == len(_per_problem_means(frame, 'avg_chain_length')) == 2
    assert rows['_problem_label'].nunique() == 2
    assert rows['_problem_category'].unique().tolist() == ['random_er']
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize('field', ['graph_id', 'topology_name', 'batch_id'])
def test_plot_identity_separates_source_target_and_configuration(field):
    values = [1, 2] if field == 'graph_id' else ['one', 'two']
    frame = pd.DataFrame([_row('A', 1, **{field: values[0]}), _row('A', 9, **{field: values[1]})])
    rows = plots._identified_plot_rows(frame)
    assert rows['_problem_id'].nunique() == 2
    assert rows['_problem_label'].nunique() == 2
    assert rows['_problem_jitter_key'].nunique() == 2


def test_display_alias_does_not_split_manifest_identity():
    frame = pd.DataFrame([_row('A', 1), _row('A', 3, graph_name='renamed')])
    assert plots._identified_plot_rows(frame)['_problem_id'].nunique() == 1


def test_legacy_fallback_warns_and_missing_provenance_is_not_dropped():
    frame = pd.DataFrame([_row('A', 1, 0), _row('A', 3, 0, graph_name='other')])
    frame = frame.drop(columns=['topology_name', 'batch_id']).rename(columns={'graph_name': 'problem_name'})
    with pytest.warns(UserWarning, match='Incomplete problem identity'):
        assert plots._identified_plot_rows(frame)['_problem_id'].nunique() == 2


def test_source_batch_fallback_matches_statistics():
    frame = pd.DataFrame([_row('A', 1), _row('A', 3)]).drop(columns='batch_id')
    frame['source_batch'] = ['one', 'two']
    with warnings.catch_warnings():
        warnings.simplefilter('error', UserWarning)
        assert plots._identified_plot_rows(frame)['_problem_id'].nunique() == 2


@pytest.mark.parametrize('field', ['topology_name', 'batch_id'])
def test_unknown_identity_component_stays_separate(field):
    frame = pd.DataFrame([_row('A', 1), _row('A', 3, **{field: None})])
    with pytest.warns(UserWarning, match='Incomplete problem identity'):
        assert plots._identified_plot_rows(frame)['_problem_id'].nunique() == 2


def test_pareto_has_one_point_per_identified_problem_mean():
    fig = plots.plot_pareto(_collision_frame())
    points = {collection.get_label(): np.asarray(collection.get_offsets()) for collection in fig.axes[0].collections}
    np.testing.assert_allclose(points['A'], [[0.2, 2], [0.8, 8]])
    np.testing.assert_allclose(points['B'], [[0.3, 3], [0.7, 7]])


@pytest.mark.parametrize(
    ('points', 'expected'),
    [
        ([[1, 1], [2, 2]], [True, False]),
        ([[2, 2], [1, 1]], [False, True]),
        ([[1, 3], [2, 2], [3, 1], [3, 3]], [True, True, True, False]),
        ([[1, 1], [1, 1], [1, 2], [2, 1]], [True, True, False, False]),
    ],
)
def test_pareto_front_minimizes_both_dimensions(points, expected):
    np.testing.assert_array_equal(plots._pareto_front(np.asarray(points)), expected)


def test_pareto_front_matches_definition_for_all_subsets_of_small_grid():
    grid = np.array([(x, y) for x in range(3) for y in range(3)])
    for subset in range(1, 1 << len(grid)):
        points = grid[[bool(subset & (1 << i)) for i in range(len(grid))]]
        expected = [not any(all(q <= p) and any(q < p) for q in points) for p in points]
        np.testing.assert_array_equal(plots._pareto_front(points), expected)


def test_head_to_head_preserves_two_pairs():
    fig = plots.plot_head_to_head(_collision_frame(), 'A', 'B')
    np.testing.assert_allclose(fig.axes[0].collections[0].get_offsets(), [[2, 3], [8, 7]])
    assert 'A better: 1, B better: 1' in fig.axes[0].get_title()


@pytest.mark.parametrize('field', ['graph_id', 'topology_name', 'batch_id'])
def test_head_to_head_does_not_pair_unmatched_problems(field):
    values = [1, 2] if field == 'graph_id' else ['one', 'two']
    frame = pd.DataFrame([_row('A', 1, **{field: values[0]}), _row('B', 2, **{field: values[1]})])
    fig = plots.plot_head_to_head(frame, 'A', 'B')
    assert any('No paired problems' in text.get_text() for text in fig.axes[0].texts)


def test_consistency_uses_within_problem_trial_variation():
    frame = pd.DataFrame([_row('A', value, gid, trial=trial) for gid, value in [(1, 2), (2, 8)] for trial in range(2)])
    fig = plots.plot_consistency(frame)
    assert [ax.patches[0].get_height() for ax in fig.axes] == [0, 0]


@pytest.mark.parametrize('function', [plots.plot_success_heatmap, plots.plot_graph_indexed_success])
def test_success_heatmap_distinguishes_colliding_names(function):
    frame = pd.DataFrame([
        _row('A', 1, 1), _row('B', 0, 1, success=False),
        _row('A', 0, 2, success=False), _row('B', 1, 2),
    ])
    fig = function(frame)
    np.testing.assert_array_equal(_heatmap_values(fig, (2, 2)), [[1, 0], [0, 1]])
    labels = [text.get_text() for text in fig.axes[0].get_xticklabels()]
    assert len(set(labels)) == 2
    assert 'id=1' in labels[0] and 'id=2' in labels[1]


@pytest.mark.parametrize('function', [plots.plot_success_heatmap, plots.plot_graph_indexed_success])
def test_heatmap_size_guard_counts_identities_not_names(function):
    frame = pd.DataFrame([_row('A', 1, gid) for gid in range(1, 302)])
    fig = function(frame)
    assert any('301' in text.get_text() for text in fig.axes[0].texts)


@pytest.mark.parametrize('mode', ['by_graph_id', 'by_n_nodes', 'by_density'])
def test_graph_indexed_chain_means_do_not_merge(mode):
    fig = plots.plot_graph_indexed_chain(_collision_frame(), mode)
    collections = fig.axes[0].collections
    np.testing.assert_allclose(collections[1].get_offsets()[:, 1], [2, 8])
    np.testing.assert_allclose(collections[3].get_offsets()[:, 1], [3, 7])


def test_graph_indexed_time_has_distinct_categorical_positions():
    frame = pd.DataFrame([_row('A', 1, 1), _row('A', 8, 2)])
    fig = plots.plot_graph_indexed_time(frame)
    points = np.concatenate([collection.get_offsets() for collection in fig.axes[0].collections])
    assert sorted(points[:, 0]) == [0, 1]


@pytest.mark.parametrize('mode', ['by_n_nodes', 'by_density'])
def test_numeric_jitter_is_stable_when_input_order_changes(mode):
    frame = pd.DataFrame([_row('A', 1, 1), _row('A', 8, 2)])
    figs = [plots.plot_graph_indexed_time(rows, mode) for rows in (frame, frame.iloc[::-1])]
    points = [np.concatenate([collection.get_offsets() for collection in fig.axes[0].collections]) for fig in figs]
    np.testing.assert_allclose(points[0], points[1][::-1])


@pytest.mark.parametrize('field', ['graph_id', 'topology_name', 'batch_id'])
def test_intersection_does_not_treat_name_collision_as_shared_success(field):
    values = [1, 2] if field == 'graph_id' else ['one', 'two']
    frame = pd.DataFrame([_row('A', 1, **{field: values[0]}), _row('B', 2, **{field: values[1]})])
    fig = plots.plot_intersection_comparison(frame, 'A', 'B')
    assert any('No shared data' in text.get_text() for text in fig.axes[0].texts)


def test_intersection_counts_distinct_shared_identities():
    fig = plots.plot_intersection_comparison(_collision_frame(), 'A', 'B')
    assert any('N = 2 graphs' in text.get_text() for text in fig.texts)


@pytest.mark.parametrize('field', ['graph_id', 'topology_name', 'batch_id'])
def test_deep_dive_rejects_ambiguous_name_and_accepts_prefilter(field):
    values = [1, 2] if field == 'graph_id' else ['one', 'two']
    frame = pd.DataFrame([_row('A', 1, **{field: values[0]}), _row('A', 9, **{field: values[1]})])
    with pytest.raises(ValueError, match='Ambiguous graph_name'):
        plots.plot_problem_deep_dive(frame, 'shared_name')
    fig = plots.plot_problem_deep_dive(frame.iloc[:1], 'shared_name')
    assert fig.axes[1].patches[0].get_height() == 1


def test_category_wins_use_mean_acl_and_split_ties():
    frame = pd.DataFrame([
        _row('A', 1, 1), _row('A', 9, 1, trial=1), _row('B', 4, 1),
        _row('A', 1, 2), _row('B', 2, 2),
        _row('A', 3, 3), _row('B', 3, 3),
    ])
    rates = plots._category_win_rates(frame)
    assert rates['random_er'].to_dict() == {'A': 0.5, 'B': 0.5}
    pd.testing.assert_frame_equal(rates.sort_index(), plots._category_win_rates(frame.iloc[::-1]).sort_index())
    fig = plots.plot_heatmap(frame, 'win_rate')
    np.testing.assert_allclose(_heatmap_values(fig, (2, 1)), [[0.5], [0.5]])


def test_category_wins_distinguish_failed_and_unattempted_algorithms():
    frame = pd.DataFrame([
        _row('A', 1, 1), _row('B', 0, 1, success=False),
        _row('B', 1, 2),
        _row('A', 0, 3, success=False), _row('B', 0, 3, success=False),
    ])
    assert plots._category_win_rates(frame)['random_er'].to_dict() == {'A': 1, 'B': 0}


@pytest.mark.parametrize('field', ['topology_name', 'batch_id'])
def test_category_wins_require_matching_target_and_configuration(field):
    frame = pd.DataFrame([_row('A', 1, **{field: 'one'}), _row('B', 2, **{field: 'two'})])
    assert plots._category_win_rates(frame).empty
    fig = plots.plot_heatmap(frame, 'win_rate')
    assert any('No data' in text.get_text() for text in fig.axes[0].texts)


def test_family_win_rate_preserves_documented_category_macro_average():
    rows = []
    for gid in range(1, 4):
        rows += [_row('A', 1, gid), _row('B', 2, gid)]
    rows += [_row('A', 2, 4, category='random_planar'), _row('B', 1, 4, category='random_planar')]
    fig = plots.plot_heatmap_family_summary(pd.DataFrame(rows), 'win_rate')
    np.testing.assert_allclose(_heatmap_values(fig, (2, 1)), [[0.5], [0.5]])


@pytest.mark.parametrize('function', [plots.plot_pareto, plots.plot_consistency, plots.plot_success_heatmap])
def test_plot_grouping_rejects_version_mixture(function):
    frame = pd.DataFrame([_row('A', 1), _row('A', 9, algorithm_version='2.0')])
    with pytest.raises(ValueError, match='Multiple algorithm_version'):
        function(frame)
