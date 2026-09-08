"""Frozen pre-edit proposal regressions for conditional neighbor preparation.

Expected results were generated before the change from field.py SHA256
1778a3af4670c34a8acdc51ec7be000195bb208f0213399203e4982c498bb18c.
The complete reference source and live full-trajectory differential harness are
saved under results/codex/028-reinsert-preparation. These small expected values
keep the unit tests independent of ignored research artifacts and git history.
"""
from copy import deepcopy

import networkx as nx
import numpy as np
import pytest

from ember_qc.algorithms.factored.field import _stair_contacts, align_reinsert


_EDGES = [(0, 1), (0, 2), (0, 3), (1, 2), (2, 4), (2, 5),
          (2, 7), (3, 6), (4, 5), (5, 6)]
_PROPOSALS = {
    0: (([2, 4, 6, 5, 3, 0, 1, 7], False), ([3, 2, 4, 6, 5, 0, 1, 7], False)),
    1: (([5, 6, 3, 0, 1, 4, 2, 7], False), ([5, 6, 0, 3, 1, 4, 2, 7], False)),
    2: (([6, 5, 3, 4, 7, 2, 0, 1], False), ([6, 5, 3, 4, 7, 2, 0, 1], False)),
    3: (([3, 6, 5, 1, 2, 4, 7, 0], True), ([7, 1, 5, 3, 6, 2, 4, 0], False)),
    4: ((None, False), (None, False)),
    5: (([1, 4, 2, 7, 5, 6, 3, 0], False), ([1, 4, 2, 7, 5, 3, 6, 0], False)),
    6: (([6, 4, 5, 2, 3, 7, 0, 1], True), ([6, 4, 5, 2, 3, 7, 0, 1], True)),
    7: (([0, 3, 1, 2, 7, 6, 4, 5], True), ([6, 7, 0, 2, 1, 3, 4, 5], False)),
    8: (([3, 7, 0, 2, 5, 6, 1, 4], False), ([3, 2, 7, 0, 5, 6, 1, 4], False)),
    9: (([0, 3, 7, 5, 4, 2, 6, 1], True), (None, False)),
    10: (([7, 1, 2, 4, 5, 6, 0, 3], True), ([3, 6, 1, 2, 7, 4, 5, 0], False)),
    11: (([7, 4, 2, 0, 3, 1, 5, 6], False), ([7, 4, 2, 0, 6, 5, 1, 3], True)),
}
_SLOTS = {
    (0, 0): [1188, 1448, 1317, 1316, 1185, 1185, 1250.5, 1251.5],
    (0, 1): [1893.5, 2283.5, 2152.5, 2217, 2217, 2217, 2217, 2217],
    (1, 0): [987.5, 986.5, 986.5, 986.5, 986.5, 855.5, 855.5, 921],
    (1, 1): [14529.5, 14401.5, 14532.5, 14532.5, 14532.5, 14598, 14598, 14598],
    (2, 0): [919, 853.5, 853.5, 983.5, 1114.5, 1115.5, 1115.5, 1116.5],
    (2, 1): [1627.5, 1627.5, 1563, 1693, 1759.5, 1759.5, 1759.5, 1759.5],
    (3, 0): [599.5, 599.5, 665, 796, 796, 927, 925, 990.5],
    (3, 1): [13755.5, 13755.5, 13821, 13952, 13952, 13952, 13952, 13952],
}


def case(seed, axis):
    source = nx.Graph()
    source.add_nodes_from(range(8))
    source.add_edges_from(_EDGES)
    adjacency = {v: sorted(source[v]) for v in source}
    rng = np.random.default_rng(seed)
    order = rng.permutation(8).tolist()
    values = sorted((rng.integers(0, 7, 8) / 2).tolist())
    other = {v: float(rng.integers(0, 7)) / 2 for v in source}
    group = rng.choice(8, size=1 + seed % 4, replace=False).tolist()
    positions = {v: np.array([values[i], other[v]] if axis == 0
                             else [other[v], values[i]])
                 for i, v in enumerate(order)}
    contacts = _stair_contacts(positions, adjacency)
    kwargs = dict(axis=axis, other=other, contacts=contacts,
                  bar=8.0 if seed % 2 else 0.0)
    return order, group, adjacency, values, kwargs


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('seed', range(12))
def test_exact_pre_edit_proposals_and_orientation_choices(seed, axis):
    order, group, adjacency, values, kwargs = case(seed, axis)
    original = deepcopy((order, group, adjacency, values, kwargs))
    assert align_reinsert(order, group, adjacency, values, None,
                          **kwargs) == _PROPOSALS[seed][axis]
    assert (order, group, adjacency, values, kwargs) == original


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('seed', range(4))
def test_exact_pre_edit_singleton_slot_cost_vectors(seed, axis):
    order, group, adjacency, values, kwargs = case(seed, axis)
    result = align_reinsert(order, [group[0]], adjacency, values, None,
                            slot_costs=True, **kwargs)
    assert np.array_equal(result, np.asarray(_SLOTS[seed, axis]))


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('slot_costs', [False, True])
def test_horizontal_frozen_contacts_do_not_rebuild_source_neighbor_views(axis, slot_costs):
    class CountingAdjacency(dict):
        calls = 0

        def get(self, key, default=None):
            self.calls += 1
            return super().get(key, default)

    order, group, adjacency, values, kwargs = case(0, axis)
    counted = CountingAdjacency(adjacency)
    result = align_reinsert(order, group, counted, values, None,
                            slot_costs=slot_costs, **kwargs)
    assert counted.calls == (0 if axis == 0 else len(order))
    if slot_costs:
        assert np.array_equal(result, _SLOTS[0, axis])
    else:
        assert result == _PROPOSALS[0][axis]


@pytest.mark.parametrize('axis', [0, 1])
@pytest.mark.parametrize('decline', ['empty', 'whole', 'anchored', 'non_singleton_slots'])
def test_early_declines_preserve_return_contract(axis, decline):
    order, group, adjacency, values, kwargs = case(3, axis)
    anchors = None
    if decline == 'empty':
        group = []
    elif decline == 'whole':
        group = list(order)
    elif decline == 'anchored':
        anchors = ([0.0] * len(order), [float('-inf')] * len(order))
    else:
        kwargs['slot_costs'] = True
    result = align_reinsert(order, group, adjacency, values, anchors, **kwargs)
    assert result == (None if kwargs.get('slot_costs') else (None, False))
