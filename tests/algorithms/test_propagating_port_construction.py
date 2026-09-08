"""Targeted necessary connector filtering and ownership-cut witnesses."""
import copy,importlib.util,time,unittest
from pathlib import Path
from unittest.mock import patch
import networkx as nx
ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
front=load('ports','packages/ember-qc/src/ember_qc/algorithms/factored/propagating_port_construction.py')
old=load('old','packages/ember-qc/src/ember_qc/algorithms/factored/propagating_matching_construction.py')
pilot=load('validator','scripts/codex/pilot.py')
def engine(module,S,T):return module._Builder(S,T,time.perf_counter()+5,0,{'stopped_by':None})
def fixture():
 S=nx.Graph([(0,1),(2,3)]);T=nx.Graph([(0,1),(1,5),(2,1),(0,3),(3,4),(4,5)])
 return S,T,{0:{0},1:{5},2:{2}}

class Checks(unittest.TestCase):
 def test_unrelated_sole_port_shortest_path_trap_and_alternative(self):
  S,T,E=fixture();before=copy.deepcopy(E);a=engine(old,S,T);b=engine(front,S,T)
  w,path=a.path(0,E,{1});self.assertEqual(path,[1]);self.assertIsNone(a.cut(0,w,path,E,{1}))
  w,path=b.path(0,E,{1});self.assertEqual(path,[3,4]);trial=b.cut(0,w,path,E,{1})
  self.assertIsNotNone(trial);self.assertEqual(E,before)
  self.assertIsNone(pilot.verify_embedding({u:sorted(c) for u,c in trial.items()},S.subgraph(trial),T))
  self.assertEqual(b.info['port_filter_records'][0]['blocked_sites'],[1])

 def test_unique_terminal_exemption_allows_chain_extension(self):
  S=nx.path_graph(3);T=nx.Graph([(0,1),(1,2),(1,3)]);E={0:{0},1:{2}};b=engine(front,S,T)
  w,path=b.path(0,E,{1});self.assertEqual((w,path),(1,[1]))
  self.assertEqual(b.info['port_filter_records'][0]['blocked_sites'],[])
  trial=b.cut(0,w,path,E,{1});self.assertEqual(trial[1],{1,2})
  self.assertEqual(trial[0],{0})
  self.assertIsNone(pilot.verify_embedding({u:sorted(c) for u,c in trial.items()},S.subgraph(trial),T))

 def test_multiple_terminal_owners_cannot_share_a_connector_site(self):
  S=nx.Graph([(0,2),(0,4),(2,3),(4,5)]);T=nx.Graph([(0,1),(2,1),(6,1),(0,3)])
  E={0:{0},2:{2},4:{6}};b=engine(front,S,T);_,_,bounds,free=b.state(E)
  blocked=b.unusable_ports(0,E,bounds,free,{2,4})
  self.assertEqual(blocked,{1})
  self.assertEqual(b.info['port_filter_records'][0]['protected_owners'],{1:[2,4]})

 def test_recomputes_after_a_frontier_changes(self):
  S,T,E=fixture();S.add_node(4);T.add_edge(2,7);T.add_node(8);E[4]={7};b=engine(front,S,T)
  _,_,bounds,free=b.state(E);self.assertEqual(b.unusable_ports(0,E,bounds,free,{1}),{1})
  changed=copy.deepcopy(E);changed[4]={8}
  _,_,bounds,free=b.state(changed);self.assertEqual(b.unusable_ports(0,changed,bounds,free,{1}),set())
  self.assertEqual(E[4],{7})

 def test_deadline_work_and_recorded_partial_cost(self):
  S,T,E=fixture();b=engine(front,S,T);_,_,bounds,free=b.state(E);before=copy.deepcopy(E)
  with patch.object(front,'SCANS',b.scans+1):
   with self.assertRaises(front._Stop):b.unusable_ports(0,E,bounds,free,{1})
  r=b.info['port_filter_records'][-1];self.assertEqual((r['status'],r['units']),('work_limit',1))
  self.assertEqual(E,before)
  b=engine(front,S,T);_,_,bounds,free=b.state(E);b.deadline=100.5
  with patch.object(front.time,'perf_counter',side_effect=[100.,100.,101.,101.]):
   with self.assertRaises(front._Stop):b.unusable_ports(0,E,bounds,free,{1})
  self.assertEqual(b.info['port_filter_records'][-1]['status'],'deadline')

 def test_small_complete_calls_and_full_validity(self):
  for S,T in ((nx.path_graph(6),nx.path_graph(10)),(nx.complete_graph(3),nx.cycle_graph(4)),
              (nx.star_graph(6),nx.convert_node_labels_to_integers(nx.grid_2d_graph(6,6)))):
   before=(pilot.graph_record(S),pilot.graph_record(T));r=front.frontier_embed(S,T,timeout=5)
   self.assertEqual(r['status'],'SUCCESS',r['diag']);self.assertIsNone(pilot.verify_embedding(r['embedding'],S,T))
   self.assertEqual(before,(pilot.graph_record(S),pilot.graph_record(T)))
   self.assertEqual(r['diag']['port_filter_units'],sum(x['units'] for x in r['diag']['port_filter_records']))

if __name__=='__main__':unittest.main()
