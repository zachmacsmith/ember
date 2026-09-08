"""Focused revision checks plus the small V1 structural/deadline contract."""
import importlib.util
from pathlib import Path
import random
import sys
import time
import types
import unittest

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('isolated_multilevel_check_v2', ROOT/'packages/ember-qc/src/ember_qc/algorithms/multilevel_regions_v2.py')
mr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mr)
base_spec = importlib.util.spec_from_file_location('multilevel_test_contract', ROOT/'tests/test_codex_multilevel_regions.py')
base = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(base)
base.mr = mr


class CommonContract(base.MultilevelChecks):
    pass


class RevisionChecks(unittest.TestCase):
    def meter(self):
        return mr._Meter(time.perf_counter()+2, {'stage_wall':{}})

    def test_connected_source_aggregates(self):
        for source in (nx.path_graph(21), nx.balanced_tree(2, 3), nx.cycle_graph(19)):
            adj = [tuple(source[v]) for v in source]
            root, members, weight, merges = mr._hierarchy(adj, [1]*len(source), random.Random(0), self.meter(), {'coarsening_levels':0})
            self.assertEqual(len(merges), len(source)-1)
            self.assertEqual(members[root], frozenset(source))
            for group in members.values():
                self.assertTrue(nx.is_connected(source.subgraph(group)), group)

    def test_impossible_seed_filter(self):
        target = nx.path_graph(6)
        target.add_edge(2, 6)
        adj = [tuple(target[q]) for q in target]
        record={}
        result = mr._split(set(range(6)), [{77}, set()], [1,1], [1,1], adj,
                           [9]*6+[77], random.Random(0), self.meter(), record)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(record['seed_pool']['rejected'], 1)
        self.assertTrue(all(a['seed'] != 2 for a in record['attempts']))
        self.assertTrue(all(a['status'] != 'seed_disconnects_donor' for a in record['attempts']))
        self.assertIn(2, result[0])

    def test_soft_balance_preserves_hard_constraints(self):
        class Ordered:
            def shuffle(self, values):
                pass
        target = nx.path_graph(6)
        target.add_edge(3, 6)
        adj = [tuple(target[q]) for q in target]
        record={}
        a,b = mr._split(set(range(6)), [set(), {99}], [1,1], [1,1], adj,
                        [8]*6+[99], Ordered(), self.meter(), record)
        self.assertEqual(a,{4,5})
        self.assertEqual(b,{0,1,2,3})
        self.assertEqual(record['desired_child_a'],3)
        self.assertEqual(record['attempts'][-1]['status'],'accepted')
        self.assertFalse(record['attempts'][-1]['balanced_target_reached'])
        self.assertEqual(record['attempts'][-1]['balancing_stop'],'no_safe_boundary_transfer')
        self.assertTrue(nx.is_connected(target.subgraph(a)))
        self.assertTrue(nx.is_connected(target.subgraph(b)))
        self.assertTrue(any(target.has_edge(q,6) for q in b))


if __name__=='__main__':
    unittest.main()
