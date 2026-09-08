"""Targeted joint insertion, frontier and deadline checks; no corpus cases."""
import copy
import importlib.util
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import networkx as nx

ROOT = Path(__file__).resolve().parents[2]
def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

front = load('frontier', 'packages/ember-qc/src/ember_qc/algorithms/factored/propagating_construction.py')
pilot = load('audited_pilot', 'scripts/codex/pilot.py')


class FrontierChecks(unittest.TestCase):
    def propagation_fixture(self):
        source = nx.Graph([(0, 1)])
        target = nx.Graph([(0, 2), (1, 3), (3, 4)])
        info = dict(stopped_by=None, propagation_units=0, propagation_records=[], neighborhood_unions=0)
        engine = front._Builder(source, target, time.perf_counter()+5, 0, info)
        return source, target, engine, info

    def test_future_pair_removes_unsupported_value_and_keeps_completion(self):
        source, target, engine, info = self.propagation_fixture()
        domains = {0: engine.bit[0] | engine.bit[1], 1: engine.bit[2]}
        result, record = engine.arc_queue(domains, engine.all_bits)
        self.assertTrue(record['complete'])
        self.assertEqual(result, {0: engine.bit[0], 1: engine.bit[2]})
        self.assertEqual(domains[0], engine.bit[0] | engine.bit[1])
        self.assertIsNone(pilot.verify_embedding({0: [0], 1: [2]}, source, target))
        self.assertEqual(record['removed_values'], 1)

    def test_domains_derive_from_valid_partial_minor_then_complete(self):
        source = nx.Graph([(0, 1), (0, 2), (1, 3)])
        target = nx.Graph([(0, 2), (1, 3), (3, 4), (5, 0), (5, 1), (6, 2)])
        entry = {2: {5}, 3: {6}}
        info = dict(stopped_by=None, propagation_units=0, propagation_records=[],
                    neighborhood_unions=0, domain_source_entries=0, value_support_tests=0,
                    singleton_trials=0, rejected_empty_domains=0)
        engine = front._Builder(source, target, time.perf_counter()+5, 0, info)
        self.assertIsNone(pilot.verify_embedding({2: [5], 3: [6]}, source.subgraph(entry), target))
        domains = engine.singleton_domains(entry, set())
        self.assertEqual(domains, {0: engine.bit[0], 1: engine.bit[2]})
        trial = engine.singleton(0, entry, set(), domains)
        next_domains = engine.singleton_domains(trial, set())
        result = engine.singleton(1, trial, set(), next_domains)
        self.assertEqual(entry, {2: {5}, 3: {6}})
        self.assertIsNone(pilot.verify_embedding({v: sorted(c) for v, c in result.items()}, source, target))
        self.assertEqual(sum(map(len, result.values())), 4)

    def test_interrupted_union_cannot_remove_supported_values(self):
        source, target, engine, info = self.propagation_fixture()
        domains = {0: engine.bit[0] | engine.bit[1], 1: engine.bit[2] | engine.bit[3]}
        # Two queue insertions, one arc pop, one of two neighborhood unions.
        with patch.object(front, 'PROPAGATION_CALL', 4):
            result, record = engine.arc_queue(domains, engine.all_bits)
        self.assertEqual(result, domains)
        self.assertEqual(record['status'], 'propagation_limit')
        self.assertFalse(record['complete'])
        self.assertEqual(record['units'], 4)
        result, record = engine.arc_queue(domains, engine.all_bits)
        self.assertTrue(record['complete'])
        self.assertEqual(result, domains)

    def test_degree_promotion_grows_a_connected_chain(self):
        source = nx.star_graph(6)
        target = nx.convert_node_labels_to_integers(nx.grid_2d_graph(6, 6))
        result = front.frontier_embed(source, target, timeout=5)
        self.assertEqual(result['status'], 'SUCCESS', result['diag'])
        self.assertIsNone(pilot.verify_embedding(result['embedding'], source, target))
        self.assertGreater(len(result['embedding'][0]), 1)
        self.assertIn({'vertex': 0, 'reason': 'degree_bound'}, result['diag']['promotions'])
        self.assertEqual(result['diag']['propagation_units'],
                         sum(r['units'] for r in result['diag']['propagation_records']))

    def test_bounded_congestion_cost_on_required_ports(self):
        source = nx.star_graph(6)
        target = nx.convert_node_labels_to_integers(nx.grid_2d_graph(6, 6))
        engine = front._Builder(source, target, time.perf_counter()+5, 0, {'stopped_by': None})
        chains = {0: {0}}
        owners, _, bounds, free = engine.state(chains)
        cost = engine.prices(chains, owners, bounds, free)
        self.assertEqual(cost(1), 1.75)  # six demands / two free ports => pressure3
        self.assertEqual(cost(35), 1.)
        self.assertTrue(all(1 <= cost(q) < 2 for q in target if q not in owners))

    def test_valid_small_original_graphs_and_nonmutation(self):
        for source, target in [(nx.path_graph(6), nx.path_graph(12)),
                               (nx.complete_graph(4), nx.complete_graph(8)),
                               (nx.cycle_graph(6), nx.grid_2d_graph(5, 5)),
                               (nx.star_graph(6), nx.grid_2d_graph(6, 6)),
                               (nx.empty_graph(4), nx.empty_graph(8))]:
            target = nx.convert_node_labels_to_integers(target)
            before = (pilot.graph_record(source), pilot.graph_record(target))
            result = front.frontier_embed(source, target, timeout=5)
            self.assertEqual(result['status'], 'SUCCESS', result['diag'])
            self.assertIsNone(pilot.verify_embedding(result['embedding'], source, target))
            self.assertEqual(before, (pilot.graph_record(source), pilot.graph_record(target)))

    def test_existing_high_degree_center_extends_during_insertion(self):
        source = nx.star_graph(6)
        target = nx.convert_node_labels_to_integers(nx.grid_2d_graph(6, 6))
        result = front.frontier_embed(source, target, timeout=5)
        self.assertEqual(result['status'], 'SUCCESS', result['diag'])
        self.assertGreaterEqual(len(result['embedding'][0]), 2)
        self.assertGreater(sum(m['changed_existing'] for m in result['diag']['committed_updates']), 0)

    def test_two_ended_path_cut_preserves_future_singleton_domain(self):
        source = nx.path_graph(4)
        target = nx.Graph([(0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (5, 6), (4, 7)])
        info = {'stopped_by': None}
        engine = front._Builder(source, target, time.perf_counter()+5, 0, info)
        entry = {0: {0}, 1: {4}, 3: {6}}
        before = copy.deepcopy(entry)
        proposed = engine.cut(0, 1, [1, 2, 3], entry, {1})
        self.assertEqual(proposed, {0: {0, 1}, 1: {2, 3, 4}, 3: {6}})
        self.assertEqual(entry, before)
        self.assertIsNone(pilot.verify_embedding({v: list(c) for v, c in proposed.items()},
                                                source.subgraph(proposed), target))
        _, _, bounds, free = engine.state(proposed)
        self.assertEqual(engine.domains(proposed, bounds, free), (1,))

    def test_impossible_extension_is_atomic(self):
        source = nx.Graph([(0, 1), (0, 2)])
        info = dict(stopped_by=None, staged_extension_sites=0)
        engine = front._Builder(source, nx.path_graph(3), time.perf_counter()+5, 0, info)
        entry = {0: {0}}
        self.assertIsNone(engine.prepare(1, entry))
        self.assertEqual(entry, {0: {0}})

    def test_deadline_work_and_partial_failure(self):
        source, target = nx.complete_graph(3), nx.path_graph(4)
        result = front.frontier_embed(source, target)
        self.assertEqual((result['status'], result['embedding']), ('FAILURE', {}))
        partial = result['diag']['partial_embedding']
        self.assertIsNone(pilot.verify_embedding(partial, source.subgraph(partial), target))
        result = front.frontier_embed(source, target, deadline=time.perf_counter()-1)
        self.assertEqual((result['status'], result['embedding']), ('TIMEOUT', {}))
        with patch.object(front, 'SCANS', 3):
            result = front.frontier_embed(source, target)
        self.assertEqual(result['diag']['scan_count'], 3)
        self.assertEqual(result['diag']['stopped_by'], 'work_limit')

    def test_seed_metadata_and_order_control(self):
        source, target = nx.cycle_graph(6), nx.complete_graph(10)
        first = front.frontier_embed(source, target)
        reverse = nx.Graph()
        reverse.add_nodes_from(reversed(list(source)))
        reverse.add_edges_from(reversed(list(source.edges)))
        reverse.graph['family'] = 'irrelevant'
        second = front.frontier_embed(reverse, target)
        self.assertEqual(first['embedding'], second['embedding'])
        for key in ('construction_order', 'committed_updates', 'scan_count'):
            self.assertEqual(first['diag'][key], second['diag'][key])


if __name__ == '__main__':
    unittest.main()
