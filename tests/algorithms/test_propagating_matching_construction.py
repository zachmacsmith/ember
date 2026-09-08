"""Targeted matching feasibility, growth and interruption witnesses."""
import copy
import importlib.util
import itertools
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import networkx as nx

ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
front=load('candidate','packages/ember-qc/src/ember_qc/algorithms/factored/propagating_matching_construction.py')
pilot=load('validator','scripts/codex/pilot.py')

def fixture(anchor=False):
    source=nx.star_graph(3);target=nx.Graph([(0,1),(0,2),(1,3),(1,4)])
    base={0:{0}}
    if anchor:source.add_edge(0,4);target.add_edge(0,5);base[4]={5}
    info=dict(stopped_by=None,propagation_units=0,propagation_records=[],neighborhood_unions=0,
              domain_source_entries=0,value_support_tests=0,singleton_trials=0,rejected_empty_domains=0,
              growth_units=0,growth_queries=0,growth_records=[],growth_skipped_budget=0)
    return source,target,base,front._Builder(source,target,time.perf_counter()+5,0,info),info

class Checks(unittest.TestCase):
    def test_actual_arc_consistent_collision_and_distinct_growth(self):
        for anchor in (False,True):
            S,T,base,e,info=fixture(anchor);before=copy.deepcopy(base)
            D=e.singleton_domains(base,{0})
            self.assertTrue(e.last_domain_result[1]);self.assertTrue(all(D.values()))
            self.assertEqual({x.bit_count() for x in D.values()},{2})
            m=e.matching(D);self.assertEqual((m['status'],m['matched'],m['deficit']),('deficit',2,1))
            grown,r=e.future_growth(0,base,{0})
            self.assertEqual(r['status'],'resolved',r)
            self.assertEqual((r['extra_sites'],r['matching_deficit'],r['propagation_complete']),(1,0,True))
            self.assertEqual(base,before)
            if anchor:self.assertEqual(grown[4],{5})
            for v in (1,2,3):
                D=e.singleton_domains(grown,{0});grown=e.singleton(v,grown,{0},D)
                self.assertIsNotNone(grown)
            self.assertIsNone(pilot.verify_embedding({v:sorted(c) for v,c in grown.items()},S,T))
            self.assertEqual(sum(map(len,grown.values())),len(S)+1)
            self.assertEqual(info['matching_units'],sum(x['units'] for x in info['matching_records']))

    def test_singleton_trial_rejects_hall_collision(self):
        S,T,base,e,info=fixture()
        D=e.singleton_domains({},set());D[0]=e.bit[0]
        self.assertIsNone(e.singleton(0,{},set(),D))
        self.assertEqual(info['singleton_feasibility_rejections'],['deficit'])
        self.assertIsNone(e.completed_singleton_domains)

    def test_matching_against_independent_tiny_assignment_oracle(self):
        for D in ({0:3,1:3,2:3},{0:3,1:6,2:5},{0:3,1:1},{0:0,1:3}):
            _,_,_,e,_=fixture();before=dict(D);best=0
            for values in itertools.product(*[[-1]+[q for q in range(3) if mask>>q&1] for mask in D.values()]):
                assigned=[q for q in values if q>=0]
                if len(assigned)==len(set(assigned)):best=max(best,len(assigned))
            m=e.matching(D)
            self.assertEqual((m['matched'],m['deficit']),(best,len(D)-best))
            self.assertEqual(D,before)

    def test_matching_exact_cap_unknown_and_total_interruption(self):
        _,_,_,e,_=fixture();D={0:3,1:3,2:3};r=e.matching(D);used=r['units']
        _,_,_,e,info=fixture()
        with patch.object(front,'MATCHING_QUERY',used):self.assertEqual(e.matching(D)['status'],'deficit')
        _,_,_,e,info=fixture()
        with patch.object(front,'MATCHING_QUERY',used-1):
            r=e.matching(D);self.assertEqual(r['status'],'query_limit');self.assertIsNone(r['deficit'])
        self.assertEqual(info['matching_units'],used-1)
        _,_,base,e,info=fixture();before=copy.deepcopy(base)
        with patch.object(front,'MATCHING_TOTAL',1):
            with self.assertRaises(front._Stop):e.future_growth(0,base,{0})
        self.assertEqual(info['stopped_by'],'matching_work_limit')
        self.assertEqual(info['matching_units'],1);self.assertEqual(base,before)
        self.assertIsNone(e.growth_end)

    def test_final_matching_deadline_and_unknown_growth_rollback(self):
        _,_,base,e,info=fixture();e.deadline=100.5
        with patch.object(front.time,'perf_counter',side_effect=[100.,100.,101.,101.]):
            with self.assertRaises(front._Stop):e.matching({0:e.bit[0]})
        self.assertEqual(info['matching_records'][-1]['status'],'deadline')
        self.assertIsNone(info['matching_records'][-1]['deficit'])
        _,_,base,e,info=fixture()
        with patch.object(front,'MATCHING_QUERY',1):
            grown,r=e.future_growth(0,base,{0})
        self.assertIs(grown,base);self.assertEqual(r['status'],'unresolved_matching_limit')
        self.assertEqual(r['extra_sites'],0)

    def test_small_complete_calls_and_original_input_nonmutation(self):
        for S,T in ((nx.path_graph(6),nx.path_graph(10)),(nx.complete_graph(3),nx.cycle_graph(4)),
                    (nx.star_graph(6),nx.convert_node_labels_to_integers(nx.grid_2d_graph(6,6))),
                    (nx.empty_graph(3),nx.empty_graph(5))):
            before=(pilot.graph_record(S),pilot.graph_record(T))
            r=front.frontier_embed(S,T,timeout=5)
            self.assertEqual(r['status'],'SUCCESS',r['diag'])
            self.assertIsNone(pilot.verify_embedding(r['embedding'],S,T))
            self.assertEqual(before,(pilot.graph_record(S),pilot.graph_record(T)))
            self.assertEqual(r['diag']['matching_units'],sum(x['units'] for x in r['diag']['matching_records']))
        with patch.object(front,'MATCHING_TOTAL',1):
            r=front.frontier_embed(nx.path_graph(6),nx.path_graph(10),timeout=5)
        self.assertEqual(r['status'],'FAILURE');self.assertEqual(r['embedding'],{})
        E=r['diag']['partial_embedding']
        self.assertIsNone(pilot.verify_embedding(E,nx.path_graph(6).subgraph(E),nx.path_graph(10)))

if __name__=='__main__':unittest.main()
