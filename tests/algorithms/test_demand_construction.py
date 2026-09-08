"""Small mechanism and contract checks for the first demand-tree prototype."""
import copy
import importlib.util
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import networkx as nx

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('demand_under_test', ROOT /
    'packages/ember-qc/src/ember_qc/algorithms/factored/demand_construction.py')
demand = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demand)
PSPEC = importlib.util.spec_from_file_location('audited_pilot', ROOT/'scripts/codex/pilot.py')
pilot = importlib.util.module_from_spec(PSPEC)
PSPEC.loader.exec_module(pilot)


class DemandChecks(unittest.TestCase):
    def test_connected_original_graph_outputs(self):
        cases = [(nx.path_graph(6), nx.path_graph(12)),
                 (nx.complete_graph(4), nx.complete_graph(8)),
                 (nx.cycle_graph(6), nx.grid_2d_graph(5, 5)),
                 (nx.star_graph(6), nx.grid_2d_graph(6, 6)),
                 (nx.empty_graph(4), nx.empty_graph(8))]
        for source, target in cases:
            target = nx.convert_node_labels_to_integers(target)
            before = (pilot.graph_record(source), pilot.graph_record(target))
            result = demand.demand_embed(source, target, timeout=5)
            self.assertEqual(result['status'], 'SUCCESS', result['diag'])
            self.assertIsNone(pilot.verify_embedding(result['embedding'], source, target))
            self.assertEqual(before, (pilot.graph_record(source), pilot.graph_record(target)))
            self.assertLessEqual(result['diag']['scan_count'], demand.SCANS)

    def test_high_degree_center_needs_and_receives_multiple_sites(self):
        source = nx.star_graph(6)
        target = nx.convert_node_labels_to_integers(nx.grid_2d_graph(6, 6))
        result = demand.demand_embed(source, target, timeout=5)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertGreaterEqual(len(result['embedding'][0]), 2)
        self.assertEqual(result['diag']['construction_order'][0], 0)
        self.assertIsNone(pilot.verify_embedding(result['embedding'], source, target))

    def test_failure_is_not_an_embedding_and_partial_state_stays_valid(self):
        source, target = nx.complete_graph(3), nx.path_graph(4)
        result = demand.demand_embed(source, target, timeout=5)
        self.assertEqual(result['status'], 'FAILURE')
        self.assertEqual(result['embedding'], {})
        partial = result['diag']['partial_embedding']
        self.assertIsNone(pilot.verify_embedding(partial, source.subgraph(partial), target))

    def test_failed_displacement_preserves_incumbent(self):
        info = dict(stopped_by=None, displacement_attempts=0, displacement_commits=0)
        engine = demand._Engine(nx.complete_graph(3), nx.complete_graph(5),
                                time.perf_counter()+5, 0, info)
        chains = {0: {0}, 1: {1}}
        before = copy.deepcopy(chains)
        with patch.object(engine, 'propose', side_effect=[{2}, None]):
            self.assertIsNone(engine.displacement(2, chains))
        self.assertEqual(chains, before)
        self.assertEqual(info['displacement_commits'], 0)

    def test_expired_deadline_and_work_limit(self):
        source, target = nx.path_graph(4), nx.path_graph(8)
        result = demand.demand_embed(source, target, deadline=time.perf_counter()-1)
        self.assertEqual((result['status'], result['embedding']), ('TIMEOUT', {}))
        with patch.object(demand, 'SCANS', 3):
            result = demand.demand_embed(source, target)
        self.assertEqual((result['status'], result['embedding']), ('FAILURE', {}))
        self.assertEqual(result['diag']['stopped_by'], 'work_limit')
        self.assertEqual(result['diag']['scan_count'], 3)

    def test_deterministic_metadata_and_insertion_order_control(self):
        source, target = nx.cycle_graph(6), nx.complete_graph(10)
        first = demand.demand_embed(source, target, seed=0)
        reverse = nx.Graph()
        reverse.add_nodes_from(reversed(list(source)))
        reverse.add_edges_from(reversed(list(source.edges)))
        reverse.graph['family'] = 'irrelevant'
        second = demand.demand_embed(reverse, target, seed=0)
        self.assertEqual(first['embedding'], second['embedding'])
        for key in ('scan_count', 'construction_order', 'trajectory'):
            self.assertEqual(first['diag'][key], second['diag'][key])


if __name__ == '__main__':
    unittest.main()
