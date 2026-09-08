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

front = load('frontier', 'packages/ember-qc/src/ember_qc/algorithms/factored/frontier_reinsertion_construction.py')
pilot = load('audited_pilot', 'scripts/codex/pilot.py')


class FrontierChecks(unittest.TestCase):
    def witness(self):
        source = nx.Graph([(0, 2), (1, 2), (3, 4), (3, 5)])
        target = nx.Graph([(0, 2), (2, 4), (0, 1), (4, 5), (2, 6),
                           (2, 8), (6, 7), (3, 7), (3, 8)])
        entry = {0: {0}, 1: {4}, 3: {2, 6}, 4: {7}, 5: {8}}
        info = dict(stopped_by=None, repair_scans=0, repair_skipped_budget=0,
                    repair_queries=0, repair_records=[], insertion_queries=0,
                    root_branches=0, path_queries=0, preparation_failures=0,
                    frontier_rejections=0, staged_extension_sites=0, staged_pruned_sites=0)
        engine = front._Builder(source, target, time.perf_counter()+5, 0, info)
        return source, target, entry, engine, info

    def test_relocation_reaches_blocked_insertion_with_frozen_contacts(self):
        source, target, entry, engine, info = self.witness()
        before = copy.deepcopy(entry)
        self.assertIsNone(pilot.verify_embedding({v: sorted(c) for v, c in entry.items()}, source.subgraph(entry), target))
        # Every occupied site of the blocking two-site chain is contact-essential.
        for q in entry[3]:
            changed = copy.deepcopy(entry); changed[3].remove(q)
            self.assertIsNotNone(pilot.verify_embedding({v: sorted(c) for v, c in changed.items()}, source.subgraph(changed), target))
        self.assertIsNone(engine.insert(2, entry))
        proposed = engine.repair(2, entry)
        self.assertIsNotNone(proposed, info)
        self.assertIsNone(pilot.verify_embedding({v: sorted(c) for v, c in proposed.items()}, source, target))
        self.assertEqual(sum(map(len, proposed.values())), 6)
        self.assertEqual(proposed[3], {3})
        self.assertEqual(entry, before)
        for v in set(entry)-set(info['repair_records'][-1]['selected']):
            self.assertEqual(proposed[v], entry[v])
        self.assertEqual(info['repair_records'][-1]['scans'], info['repair_scans'])

    def test_repair_cap_rolls_back_and_exact_last_unit_can_complete(self):
        source, target, entry, engine, info = self.witness()
        before = copy.deepcopy(entry)
        with patch.object(front, 'REPAIR_SCANS', 1):
            self.assertIsNone(engine.repair(2, entry))
        self.assertEqual(info['repair_scans'], 1)
        self.assertEqual(info['repair_records'][-1]['status'], 'local_work_limit')
        self.assertEqual(entry, before)
        self.assertIsNone(engine.repair_end)
        # A completed query's last scan may exactly exhaust its own allowance.
        source, target, entry, engine, info = self.witness()
        self.assertIsNotNone(engine.repair(2, entry))
        needed = info['repair_scans']
        source, target, entry, engine, info = self.witness()
        with patch.object(front, 'REPAIR_SCANS', needed):
            proposed = engine.repair(2, entry)
        self.assertIsNotNone(proposed)
        self.assertEqual(info['repair_scans'], needed)
        self.assertIsNone(pilot.verify_embedding({v: sorted(c) for v, c in proposed.items()}, source, target))

    def test_repair_deadline_and_frozen_preparation_are_atomic(self):
        source, target, entry, engine, info = self.witness()
        before = copy.deepcopy(entry)
        engine.deadline = time.perf_counter()-1
        with self.assertRaises(front._Stop):
            engine.repair(2, entry)
        self.assertEqual(entry, before)
        self.assertEqual(info['repair_records'][-1]['status'], 'deadline')
        self.assertIsNone(engine.repair_end)
        source = nx.Graph([(0, 1), (0, 2)])
        target = nx.path_graph(5)
        info = dict(stopped_by=None, staged_extension_sites=0)
        engine = front._Builder(source, target, time.perf_counter()+5, 0, info)
        entry = {0: {0}}
        self.assertIsNone(engine.prepare(1, entry, {0}))
        self.assertEqual(entry, {0: {0}})

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
