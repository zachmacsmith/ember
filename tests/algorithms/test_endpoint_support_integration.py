"""New policy boundaries and one small native smoke; no corpus benchmark."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import dwave_networkx as dnx
import networkx as nx
import pytest

from ember_qc.algorithms.factored import contact_repair as cr
from ember_qc.algorithms.factored import native, plane, spectral_order


OBJECTIVE = 'qubits_endpoint_support'


@pytest.mark.parametrize('options', [dict(tree_policy='distance'),
                                   dict(singleton_policy='direct'),
                                   dict(star_policy='matching'), dict(star_policy='connected')])
def test_invalid_combinations_rejected_even_when_refinement_is_disabled(options):
    source, target = nx.Graph(), dnx.zephyr_graph(2)
    with pytest.raises(ValueError, match='endpoint support requires'):
        cr.contact_polish({}, source, target, objective=OBJECTIVE, max_groups=0, **options)
    renamed = {'polish_' + key: value for key, value in options.items()}
    result = native.native_embed(source, target, polish_objective=OBJECTIVE,
                                 polish_passes=0, **renamed)
    assert result['status'] == 'ERROR' and not result['embedding']
    assert 'endpoint support requires' in result['error']


@pytest.mark.parametrize('which', ['source', 'target'])
@pytest.mark.parametrize('kind', ['directed', 'parallel', 'loop'])
def test_simple_graph_contract_precedes_empty_source_or_zero_budget(which, kind):
    source, target = nx.Graph(), dnx.zephyr_graph(2)
    graphs = dict(source=source, target=target)
    if kind == 'directed':
        graphs[which] = nx.DiGraph(graphs[which])
    elif kind == 'parallel':
        graphs[which] = nx.MultiGraph(graphs[which])
    else:
        graphs[which].add_edge(0, 0)
    with pytest.raises(ValueError, match='simple undirected loopless'):
        cr.contact_polish({}, graphs['source'], graphs['target'],
                           objective=OBJECTIVE, max_groups=0)
    result = native.native_embed(graphs['source'], graphs['target'],
                                 polish_objective=OBJECTIVE, polish_passes=0)
    assert result['status'] == 'ERROR' and 'simple undirected loopless' in result['error']


def test_direct_group_boundary_also_rejects_an_unsupported_tree():
    with pytest.raises(ValueError, match='endpoint support requires'):
        cr.repair_group({0: [0]}, nx.empty_graph(1), nx.empty_graph(1), (0,),
                          objective=OBJECTIVE, tree_policy='distance', max_expansions=0)


def verify(embedding, source, target):
    assert set(embedding) == set(source)
    occupied = [q for chain in embedding.values() for q in chain]
    assert len(occupied) == len(set(occupied)) and set(occupied) <= set(target)
    for chain in embedding.values():
        assert chain and nx.is_connected(target.subgraph(chain))
    for u, v in source.edges:
        assert any(target.has_edge(q, p) for q in embedding[u] for p in embedding[v])


def test_one_real_native_call_preserves_common_deadline_labels_and_inputs(monkeypatch):
    calls = []
    def observe(name, fn):
        def wrapper(*args, **kwargs):
            calls.append((name, kwargs))
            return fn(*args, **kwargs)
        return wrapper
    monkeypatch.setattr(spectral_order, 'spectral_orders', observe('initial', spectral_order.spectral_orders))
    monkeypatch.setattr(plane, 'arrange', observe('layout', plane.arrange))
    monkeypatch.setattr(cr, 'contact_polish', observe('polish', cr.contact_polish))
    source = nx.path_graph(7)
    source.add_node(7)
    labels = {v: ('v', v) if v % 2 else f'x{v}' for v in source}
    source = nx.relabel_nodes(source, labels)
    source.graph.update(family='unused', embedding={'unused': [-1]})
    target, before = dnx.zephyr_graph(3), deepcopy(source)
    target_before = deepcopy(target)
    result = native.native_embed(source, target, initialization='spectral', seed=0,
                                 max_asks=16, polish_passes=1, max_groups=4,
                                 polish_group_sizes=(1, 2), polish_expansions=2000,
                                 polish_objective=OBJECTIVE, beam_width=1, timeout=30)
    assert result['success'], result
    verify(result['embedding'], source, target)
    assert [name for name, _ in calls] == ['initial', 'layout', 'polish']
    assert len({options['deadline'] for _, options in calls}) == 1
    assert calls[-1][1]['objective'] == OBJECTIVE
    assert result['diag']['contact_repair']['endpoint_support']['objective'] == OBJECTIVE
    assert result['diag']['contact_repair']['expansions'] <= 2000
    assert nx.utils.graphs_equal(source, before) and nx.utils.graphs_equal(target, target_before)


def test_named_pilot_arm_only_changes_objective_and_leaves_historical_arm_unchanged():
    root = Path(__file__).resolve().parents[2]
    def load(path, name):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    pilot = load(root / 'scripts/codex/pilot.py', '_endpoint_pilot')
    old = load(root / 'results/codex/endpoint-support-checks/reference/pilot.py', '_endpoint_old_pilot')
    control = 'native-search-joint1-contacts-spectral'
    variant = 'native-search-joint1-endpoint-support-spectral'
    assert pilot.CONFIGS[variant] == dict(pilot.CONFIGS[control], polish_objective=OBJECTIVE)
    assert {k: v for k, v in pilot.CONFIGS.items() if k != variant} == old.CONFIGS
