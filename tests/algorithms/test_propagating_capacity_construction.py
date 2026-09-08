"""Bounded reconstruction semantics; synthetic supplied minors only."""
import ast
import copy
import importlib.util
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import networkx as nx

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/propagating_capacity_construction.py'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
m = load('reconstruction', PATH)
old = load('reconstruction_control', PATH.with_name('propagating_component_construction.py'))
pilot = load('validator', ROOT/'scripts/codex/pilot.py')

def info():
    fn = next(x for x in ast.parse(PATH.read_text()).body
              if isinstance(x, ast.FunctionDef) and x.name == 'frontier_embed')
    node = next(x.value for x in fn.body if isinstance(x, ast.Assign)
                and isinstance(x.targets[0], ast.Name) and x.targets[0].id == 'info')
    return eval(compile(ast.Expression(node), str(PATH), 'eval'), m.__dict__, {'seed': 0})

def engine(source, target):
    return m._Builder(source, target, time.perf_counter()+5, 0, info())

def fixture():
    source = nx.path_graph(4)
    target = nx.Graph([(0,1),(1,2),(2,3),(0,4),(1,5)])
    return source, target, {0:{0},2:{1},3:{2}}

class Checks(unittest.TestCase):
    def test_capacity_selected_future_and_shared_guard_cases(self):
        cases=[
          ([(0,1),(1,2),(2,3)],[],[(0,1),(1,2),(2,3),(0,4),(1,5)],[],
           {0:{0},2:{1},3:{2}},1,[0],True),
          ([(0,1),(0,2),(1,2),(3,4)],[],[(0,1),(0,2),(3,2),(1,4)],[],
           {1:{1},2:{0},3:{3}},0,[1],False),
          ([(0,1),(0,2),(1,2),(3,4)],[],[(0,1),(0,2),(3,2),(1,4),(0,4)],[],
           {1:{1},2:{0},3:{3}},0,[1],True),
          ([(0,1),(1,2)],[],[(0,1),(1,2)],[],{1:{1},2:{0}},0,[1],True),
          ([(0,2),(2,3),(0,1)],[],[(0,1),(2,3)],[],{2:{0},1:{2}},0,[1],False),
          ([(1,4),(2,5)],[0,3],[(0,1),(1,2)],[4,5],{1:{0},2:{2},3:{4}},0,[3],True),
        ]
        records=[]
        for se,sn,te,tn,entry,v,K,expected in cases:
            source=nx.Graph(se);source.add_nodes_from(sn);target=nx.Graph(te);target.add_nodes_from(tn)
            e=engine(source,target);before=copy.deepcopy(entry)
            result=e.block_capacity(v,entry,K)
            self.assertEqual(result['admissible'],expected,result)
            self.assertEqual(entry,before)
            self.assertEqual(result['units'],e.info['capacity_assessment_units'])
            records.append(result)
        triangle=next(r for r in records[1]['rows'] if r['owner']==2)
        self.assertEqual((triangle['d'],triangle['usable']),(2,[1]))
        restored=next(r for r in records[3]['rows'] if r['owner']==2)
        self.assertEqual((restored['d'],restored['p']),(1,0))
        self.assertEqual(records[5]['protected_sites'],{1:[1,2]})

    def test_complete_capacity_pass_precedes_search_and_interruption_has_no_vector(self):
        source,target,entry=fixture();e=engine(source,target)
        insertions=[]
        def fail(u,trial,frozen):
            insertions.append(u)
            self.assertEqual(len(e.info['capacity_assessment_records']),4)
            self.assertTrue(all(r['status']=='complete' for r in e.info['capacity_assessment_records']))
            return None
        with patch.object(e,'insert',side_effect=fail):result,record=e.repair(1,entry,{1})
        self.assertIsNone(result);self.assertEqual(len(insertions),3)
        self.assertEqual([r['selected'] for r in record['reordered_blocks']],record['ordered_blocks'])
        self.assertEqual(e.info['capacity_assessment_units'],sum(r['units'] for r in e.info['capacity_assessment_records']))
        e=engine(source,target)
        with patch.object(m,'REPAIR_QUERY',20),patch.object(e,'insert',side_effect=AssertionError('early search')):
            result,record=e.repair(1,entry,{1})
        self.assertIsNone(result);self.assertIsNone(record['reordered_blocks'])
        self.assertEqual(record['status'],'local_work_limit')
        self.assertIsNone(e.info['capacity_assessment_records'][-1]['admissible'])

    def test_six_fixed_predicate_cases_match_component_oracle(self):
        cases=[
            ([(0,1),(0,2),(0,4)],[],[(0,1),(2,3),(2,7),(6,7)],[],
             {1:{0},2:{3}},True),
            ([(0,1),(0,2),(0,4)],[],[(0,1),(2,3),(2,7),(6,7),(1,2)],[],
             {1:{0},2:{3}},False),
            ([],[0,4],[],[6],{},False),
            ([],[0,4],[],[6],{4:{6}},True),
            ([(0,1)],[4],[(0,1)],[6],{1:{0}},False),
            ([(0,1),(1,2)],[4],[(0,1)],[6],{1:{0}},True),
        ]
        for se,sn,te,tn,frozen,expected in cases:
            source=nx.Graph(se);source.add_nodes_from(sn)
            target=nx.Graph(te);target.add_nodes_from(tn)
            e=engine(source,target);before=copy.deepcopy(frozen)
            self.assertEqual(e.component_obstruction(0,frozen),expected)
            self.assertEqual(frozen,before)
            record=e.info['component_filter_records'][-1]
            self.assertEqual(record['status'],'complete')
            self.assertEqual(record['obstructed'],expected)
            self.assertEqual(record['units'],e.info['component_filter_units'])

    def test_filter_unknown_rollback_and_overlapping_accounting(self):
        source,target,entry=fixture();e=engine(source,target)
        e.repair_end=e.scans+1
        with self.assertRaises(m._RepairLimit):e.component_obstruction(1,entry)
        record=e.info['component_filter_records'][-1]
        self.assertEqual((record['status'],record['obstructed'],record['units']),('repair_limit',None,1))
        self.assertEqual(e.info['component_filter_units'],1)
        e=engine(source,target);e.deadline=time.perf_counter()-1
        with self.assertRaises(m._Stop):e.component_obstruction(1,entry)
        self.assertIsNone(e.info['component_filter_records'][-1]['obstructed'])
        e=engine(source,target);start=e.scans;result,record=e.repair(1,entry,{1})
        self.assertIsNotNone(result)
        self.assertEqual(e.scans-start,record['units'])
        self.assertEqual(e.info['component_filter_units'],sum(r['units'] for r in e.info['component_filter_records']))
        self.assertLess(e.info['component_filter_units'],record['units'])

    def test_fixed_occupied_endpoint_relocation_and_frozen_original_contacts(self):
        source, target, entry = fixture(); before = copy.deepcopy(entry)
        e = engine(source, target); promoted = {1}; previous = set(promoted)
        self.assertIsNone(e.insert(1, entry))
        e.completed_singleton_domains = ('stale', 'cache')
        result, record = e.repair(1, entry, promoted)
        self.assertIsNotNone(result, record)
        self.assertEqual(sum(map(len, result.values())), 4)
        self.assertIsNone(pilot.verify_embedding({u:sorted(c) for u,c in result.items()}, source, target))
        for u in entry.keys()-set(record['selected']):
            self.assertEqual(result[u], entry[u])
        self.assertEqual(entry, before); self.assertEqual(promoted, previous)
        self.assertIsNone(e.completed_singleton_domains)
        self.assertFalse(record['accepted'])
        self.assertEqual(record['units'], e.info['repair_units'])

    def test_local_cap_last_unit_global_continuity_and_entry_rollback(self):
        source, target, entry = fixture(); before = copy.deepcopy(entry)
        e = engine(source, target)
        with patch.object(m, 'REPAIR_QUERY', 1):
            result, record = e.repair(1, entry, {1})
        self.assertIsNone(result); self.assertEqual(record['units'], 1)
        self.assertEqual(record['status'], 'local_work_limit')
        self.assertEqual(entry, before); self.assertIsNone(e.repair_end)
        e = engine(source, target); result, record = e.repair(1, entry, {1})
        self.assertIsNotNone(result); needed = record['units']
        e = engine(source, target)
        with patch.object(m, 'REPAIR_QUERY', needed):
            result, record = e.repair(1, entry, {1})
        self.assertIsNotNone(result); self.assertEqual(record['units'], needed)
        e = engine(source, target); e.info['repair_units'] = m.REPAIR_TOTAL-2
        result, record = e.repair(1, entry, {1})
        self.assertIsNone(result); self.assertEqual(record['units'], 2)
        self.assertEqual(e.info['repair_units'], m.REPAIR_TOTAL)
        e = engine(source, target)
        with patch.object(m, 'SCANS', e.scans+2):
            with self.assertRaises(m._Stop): e.repair(1, entry, {1})
        self.assertEqual(e.info['repair_records'][-1]['status'], 'work_limit')
        self.assertEqual(entry, before)

    def test_frozen_preparation_and_all_to_new_cut(self):
        e = engine(nx.Graph([(0,1),(0,2)]), nx.path_graph(5)); entry={0:{0}}
        self.assertIsNone(e.prepare(1, entry, {0})); self.assertEqual(entry, {0:{0}})
        source=nx.path_graph(2); target=nx.path_graph(4); e=engine(source,target)
        entry={0:{0},1:{3}}
        trial=e.cut(0,1,[1,2],entry,{1},{1})
        self.assertEqual(trial, {0:{0,1,2},1:{3}})

    def test_pool_arbitrary_degree_truncation_and_complete_block_vector(self):
        source=nx.star_graph(8); target=nx.complete_graph(14)
        entry={u:{u} for u in range(1,9)}; e=engine(source,target); record={}
        blocks=e.repair_pool(0,entry,record)
        self.assertEqual(len(record['required']),8)
        self.assertEqual(len(record['pool']),4)
        self.assertEqual(len(record['omitted_required']),4)
        self.assertEqual(len(blocks),10)
        self.assertEqual([len(b) for b in blocks], [1]*4+[2]*6)

    def test_nested_matching_and_growth_repair_interruptions_are_charged_unknown(self):
        source,target,entry=fixture(); e=engine(source,target)
        e.repair_end=e.scans+2
        with self.assertRaises(m._RepairLimit):
            e.matching({0:e.bit[3]|e.bit[4],1:e.bit[3]|e.bit[4]})
        self.assertEqual(e.info['matching_records'][-1]['status'],'repair_limit')
        self.assertEqual(e.info['matching_units'],2)
        self.assertIsNone(e.info['matching_records'][-1]['deficit'])
        e=engine(source,target); e.repair_end=e.scans+1
        base={0:{0}}
        with self.assertRaises(m._RepairLimit):e.future_growth(0,base,set())
        self.assertEqual(e.info['growth_records'][-1]['status'],'repair_limit')
        self.assertEqual(e.info['growth_units'],1)
        self.assertIsNone(e.growth_end)

    def test_deadline_at_return_and_no_schedule_changes_on_success(self):
        source,target,entry=fixture(); e=engine(source,target); before=copy.deepcopy(entry)
        real_frontier=e.frontier_ok
        def late(chains,bounds,free):
            ok=real_frontier(chains,bounds,free)
            if len(chains)==len(source):e.deadline=time.perf_counter()-1
            return ok
        with patch.object(e,'frontier_ok',side_effect=late):
            with self.assertRaises(m._Stop):e.repair(1,entry,{1})
        self.assertEqual(entry,before); self.assertFalse(e.info['repair_records'][-1]['accepted'])
        self.assertEqual(e.info['repair_records'][-1]['status'],'deadline')
        for source,target in [(nx.path_graph(6),nx.path_graph(12)),
                              (nx.complete_graph(3),nx.cycle_graph(4))]:
            first=old.frontier_embed(source,target,timeout=5)
            with patch.object(m._Builder,'repair',side_effect=AssertionError('unneeded repair')):
                second=m.frontier_embed(source,target,timeout=5)
            self.assertEqual(second['status'],'SUCCESS',second['diag'])
            self.assertEqual(second['embedding'],first['embedding'])
            for key in ('construction_order','committed_updates','scan_count','promotions'):
                self.assertEqual(second['diag'][key],first['diag'][key])

if __name__ == '__main__': unittest.main()
