"""Targeted exploratory mechanism checks; reused independent minor validator."""
import copy
import importlib.util
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

vacancy = load('vacancy_under_test', 'packages/ember-qc/src/ember_qc/algorithms/factored/vacancy_repair.py')
pilot = load('audited_pilot', 'scripts/codex/pilot.py')

class Budget:
    def __init__(self, limit=50000, deadline=None):
        self.limit, self.deadline, self.expansions = limit, deadline, 0

    def pop(self):
        if self.expansions >= self.limit:
            return False
        self.expansions += 1
        return True

def fixture():
    source = nx.Graph([(1,0),(0,2)])
    target = nx.Graph([(10,11),(10,12),(11,13),(12,14),(13,14)])
    return source, target, {0:[11,10],1:[12],2:[13]}

def call(source, target, entry, budget=None, deadline=None):
    budget = budget or Budget()
    before = copy.deepcopy(entry)
    result, info = vacancy.vacancy_repair(entry, dict(source.adj), dict(target.adj), [],
        budget=budget, deadline=deadline or time.perf_counter()+2)
    assert entry == before
    assert info['work_total'] == budget.expansions == sum(info['work'].values())
    if result is not None:
        assert pilot.verify_embedding(result, source, target) is None
        assert sum(map(len,result.values())) == sum(map(len,entry.values()))-1
    return result, info

class VacancyChecks(unittest.TestCase):
    def test_free_site_contraction_from_deletion_minimal_entry(self):
        s,t,e = fixture()
        for q in e[0]:
            shorter = copy.deepcopy(e); shorter[0].remove(q)
            self.assertIsNotNone(pilot.verify_embedding(shorter,s,t))
        result, info = call(s,t,e)
        self.assertEqual(result[0], [14])
        self.assertEqual(info['proposal']['depth'], 1)
        self.assertEqual(info['proposal']['selected'], [0])
        self.assertTrue(info['candidate_returned'])

    def test_zero_work_and_expired_deadline_preserve_entry(self):
        s,t,e = fixture()
        result, info = call(s,t,e,Budget(0))
        self.assertIsNone(result)
        self.assertEqual(info['stopped_reason'], 'work')
        result, info = call(s,t,e,deadline=time.perf_counter()-1)
        self.assertIsNone(result)
        self.assertEqual(info['stopped_reason'], 'deadline')

    def test_fixed_outside_chain_order_is_preserved(self):
        s,t,e = fixture()
        s.add_node(3); t.add_edges_from([(30,31),(31,32)])
        e[3] = [32,30,31]
        result, info = call(s,t,e)
        self.assertIsNotNone(result)
        for v in set(e)-set(info['proposal']['selected']):
            self.assertEqual(result[v],e[v])
            self.assertIsNot(result[v],e[v])

    def test_no_false_minor_on_tree_target(self):
        s = nx.cycle_graph(3); t = nx.path_graph(6)
        result, info = call(s,t,{0:[0,1],1:[2,3],2:[4,5]})
        self.assertIsNone(result)
        self.assertEqual(info['stopped_reason'], 'invalid_input')

    def test_singletons_no_deletion_seeds(self):
        s,t = nx.path_graph(3),nx.path_graph(5)
        result,info = call(s,t,{0:[0],1:[1],2:[2]})
        self.assertIsNone(result)
        self.assertEqual(info['seed_attempts'],0)
        self.assertEqual(info['stopped_reason'],'seeds_exhausted')

    def test_deadline_interrupts_search(self):
        s,t,e = fixture()
        calls = 0
        def clock():
            nonlocal calls
            calls += 1
            return 0. if calls < 20 else 10.
        with patch.object(vacancy.time,'perf_counter',clock):
            result,info = call(s,t,e,deadline=1.)
        self.assertIsNone(result)
        self.assertEqual(info['stopped_reason'],'deadline')

if __name__ == '__main__':
    unittest.main()
