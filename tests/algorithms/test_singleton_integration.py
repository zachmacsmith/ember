"""Native boundaries for the direct proposal rule in one refinement call."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import dwave_networkx as dnx
import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair, native, plane, spectral_order


def assert_valid(embedding, source, target):
    assert set(embedding) == set(source)
    occupied = set()
    for chain in embedding.values():
        assert chain and len(set(chain)) == len(chain)
        assert set(chain) <= set(target) and not occupied.intersection(chain)
        occupied.update(chain)
        assert nx.is_connected(target.subgraph(chain))
    for v, w in source.edges():
        assert any(target.has_edge(p, q) for p in embedding[v] for q in embedding[w])


def test_unknown_policy_rejected_before_construction(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('construction must not consume an invalid policy')

    monkeypatch.setattr(plane, 'arrange', forbidden)
    result = native.native_embed(nx.path_graph(4), dnx.zephyr_graph(2),
                                 polish_singleton_policy='unknown')
    assert result['status'] == 'ERROR' and not result['embedding']
    assert result['error'] == 'unknown singleton policy'


@pytest.mark.parametrize('kind', ['directed', 'parallel', 'loop'])
def test_direct_mode_rejects_unsupported_target_before_empty_source_success(kind):
    target = dnx.zephyr_graph(2)
    if kind == 'directed':
        target = nx.DiGraph(target)
    elif kind == 'parallel':
        target = nx.MultiGraph(target)
    else:
        target.add_edge(0, 0)
    result = native.native_embed(nx.Graph(), target, polish_singleton_policy='direct')
    assert result['status'] == 'ERROR' and not result['embedding']
    assert 'simple and undirected' in result['error']


def test_direct_policy_uses_one_refinement_call_and_original_deadline(monkeypatch):
    calls = []
    deadlines = []

    def wrap(fn):
        def record(*args, **kwargs):
            deadlines.append(kwargs['deadline'])
            return fn(*args, **kwargs)
        return record

    def refine(embedding, source, target, **kwargs):
        calls.append(kwargs)
        deadlines.append(kwargs['deadline'])
        assert_valid(embedding, source, target)
        return embedding, {'integration_probe': True}

    monkeypatch.setattr(spectral_order, 'spectral_orders', wrap(spectral_order.spectral_orders))
    monkeypatch.setattr(plane, 'arrange', wrap(plane.arrange))
    monkeypatch.setattr(contact_repair, 'contact_polish', refine)
    source = nx.path_graph(7)
    source.add_node(7)
    labels = {v: ('v', v) if v % 2 else f'x{v}' for v in source}
    source = nx.relabel_nodes(source, labels)
    source.graph.update(family='ignored', embedding={'not_an_input': [-1]})
    original = deepcopy(source)
    target = dnx.zephyr_graph(3)
    result = native.native_embed(source, target, initialization='spectral',
                                 max_asks=20, polish_passes=2, max_groups=31,
                                 polish_expansions=4000, polish_group_sizes=(1, 2),
                                 polish_singleton_policy='direct', timeout=30)
    assert result['success'], result
    assert_valid(result['embedding'], source, target)
    assert nx.utils.graphs_equal(source, original)
    assert len(calls) == 1
    assert calls[0]['singleton_policy'] == 'direct'
    assert calls[0]['max_expansions'] == 4000 and calls[0]['max_groups'] == 31
    assert len(deadlines) == 3 and len(set(deadlines)) == 1
    assert deadlines[0] is not None
    assert result['diag']['polish_singleton_policy'] == 'direct'


def test_native_final_validator_still_rejects_bad_refinement_output(monkeypatch):
    def bad_refinement(embedding, *args, **kwargs):
        broken = dict(embedding)
        broken[next(iter(broken))] = [-1]
        return broken, {}

    monkeypatch.setattr(contact_repair, 'contact_polish', bad_refinement)
    result = native.native_embed(nx.path_graph(7), dnx.zephyr_graph(3),
                                 max_asks=20, polish_passes=1,
                                 polish_singleton_policy='direct', timeout=30)
    assert result['status'] == 'INVALID_OUTPUT' and not result['embedding']


def test_zero_passes_does_not_call_direct_refinement(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('refinement called with zero passes')

    monkeypatch.setattr(contact_repair, 'contact_polish', forbidden)
    source, target = nx.path_graph(7), dnx.zephyr_graph(3)
    result = native.native_embed(source, target, max_asks=20, polish_passes=0,
                                 polish_singleton_policy='direct', timeout=30)
    assert result['success'], result
    assert_valid(result['embedding'], source, target)


def test_real_direct_pipeline_preserves_labels_isolates_and_ignores_family_metadata():
    source = nx.gnp_random_graph(24, 0.2, seed=42)
    source.add_node(24)
    labels = {v: ('variable', v) if v % 2 else f'x{v}' for v in source}
    renamed = nx.relabel_nodes(source, labels)
    renamed.graph.update(family='unseen', id=-123, embedding={'unused': [-1]})
    nx.set_node_attributes(renamed, 'irrelevant', 'family')
    original = deepcopy(renamed)
    target = dnx.zephyr_graph(3)
    config = dict(initialization='spectral', seed=4, max_asks=40,
                  polish_passes=2, max_groups=32, polish_expansions=8000,
                  polish_group_sizes=(1, 2, 3, 4), beam_width=1,
                  polish_group_policy='round_robin', polish_objective='qubits_contacts',
                  polish_singleton_policy='direct', timeout=30)
    base = native.native_embed(source, target, **config)
    changed = native.native_embed(renamed, target, **config)
    assert base['success'] and changed['success'], (base, changed)
    assert_valid(base['embedding'], source, target)
    assert_valid(changed['embedding'], renamed, target)
    assert {v: changed['embedding'][labels[v]] for v in source} == base['embedding']
    assert nx.utils.graphs_equal(renamed, original)
    repair = changed['diag']['contact_repair']
    assert repair['singleton_search']['direct_visits'] > 0
    assert repair['singleton_search']['work'] <= 400
    assert repair['groups_tried'] <= 32 and repair['expansions'] <= 8000


def test_frozen_singleton_arm_changes_only_the_proposal_rule():
    path = Path(__file__).resolve().parents[2] / 'scripts/codex/pilot.py'
    spec = importlib.util.spec_from_file_location('_singleton_pilot_test', path)
    pilot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pilot)
    control = pilot.CONFIGS['native-search-joint1-contacts-spectral']
    variant = pilot.CONFIGS['native-search-joint1-contacts-spectral-singletons']
    assert variant == dict(control, polish_singleton_policy='direct')
    assert 'polish_singleton_policy' not in control
