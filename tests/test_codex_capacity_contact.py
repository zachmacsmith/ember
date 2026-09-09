"""C014 new-risk checks, two real tiny constructors, one injected wrapper."""
import copy
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ['C014_CHECK_OUTPUT'])
ATTEMPTS=[]
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if 'minorminer' in fullname or 'busclique' in fullname:
            ATTEMPTS.append(fullname);raise ImportError('prohibited embedding dependency')
sys.meta_path.insert(0,Guard())
import networkx as nx
import dwave_networkx as dnx

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
c=load('isolated_c014','packages/ember-qc/src/ember_qc/algorithms/zephyr_capacity_contact.py')
o=load('original_oracle','results/codex/042-results-review/pre-execution/ember_embedding_oracle.py')

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/(name+'.json')).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')

def valid(source,target,mapping):
    sa={u:set(source[u]) for u in source};se={tuple(sorted(e)) for e in source.edges}
    ta={q:set(target[q]) for q in target};te={tuple(sorted(e)) for e in target.edges}
    return o.embedding_quality({str(u):list(v) for u,v in mapping.items()},sa,se,ta,te)

def state(source,target,chains=None):
    G=[set(source[u]) for u in range(len(source))];H=[set(target[q]) for q in range(len(target))]
    e=c._Engine(G,H,[(0,0,0,0,0)]*len(H),0,0,c._Budget(time.perf_counter()+30))
    e.sorder=list(range(len(G)));e.srank={u:u for u in range(len(G))}
    e.torder=list(range(len(H)));e.trank={q:q for q in range(len(H))};e.adj=[sorted(ns) for ns in H]
    s=c._State(e,chains);s.certify();e.published=s
    return s

def payload(s):return copy.deepcopy((s.I,s.chains,s.owner,s.contacts,s.domains,s.Q,c._capacities(s)))

def corridor():
    H=nx.Graph();H.add_nodes_from(range(9));H.add_edges_from([(0,1),(1,2),(2,3),(2,4),(2,5),(3,6),(3,7),(3,8)])
    return nx.star_graph(5),H

class CapacityContactChecks(unittest.TestCase):
    def test_01_distinct_capacity_zero_gain_and_pruning(self):
        G=nx.star_graph(2);H=nx.complete_graph(3);s=state(G,H,{0:{0,1}})
        self.assertEqual(c._capacities(s)[0],(1,2)) # Two couplers reach one distinct free site.
        self.assertEqual(c._violations(s),{0:1})
        G,H=corridor();entry=state(G,H);before=payload(entry);receipt={}
        grown=c._capacity_tree(entry,0,frozenset((0,)),receipt)
        save('growth_observation',dict(receipt=receipt,state=grown.snapshot() if grown else None))
        self.assertIsNotNone(grown);self.assertEqual(payload(entry),before)
        self.assertEqual(receipt['growth'][0]['delta'],0)
        self.assertEqual(grown.chains[0],frozenset((2,3)))
        self.assertEqual(c._capacities(grown)[0],(6,5));self.assertFalse(c._violations(grown))
        self.assertEqual(len(receipt['pruning']),2)
        # Both capacity-supporting endpoints survive despite absent old contacts.
        for q in grown.chains[0]:self.assertTrue(c._violations(c._replace(grown,0,{q})))
        boundary=sorted(set(c._bits(grown.boundaries[0]&grown.free)))
        mapping={0:grown.chains[0],**{u:{q} for u,q in enumerate(boundary[:5],1)}}
        self.assertTrue(valid(G,H,mapping)[0])
        save('capacity_growth',dict(status='PASS',distinct_boundary_not_couplers=True,
                                   zero_gain_preserved=True,capacity_survives_pruning=True))

    def test_02_unrelated_capacity_blocker_and_retraction_accounting(self):
        G=nx.Graph();G.add_nodes_from(range(3));G.add_edge(0,1);H=nx.path_graph(4)
        s=state(G,H,{0:{0}});before=payload(s);receipt={}
        self.assertIsNone(c._capacity_tree(s,2,{1},receipt))
        self.assertEqual(receipt['old_violations'],{0:1});self.assertIn(0,receipt['blockers'])
        safe=c._place(s,2);self.assertIsNotNone(safe);self.assertFalse(c._violations(safe))
        self.assertEqual(payload(s),before)
        GG=nx.path_graph(3);HH=nx.path_graph(5);entry=state(GG,HH,{0:{0},1:{1,2}})
        c._certify(entry);before=payload(entry);account={};retracted=c._retract(entry,{1},account)
        self.assertEqual(account['retained_capacity_changes'][0],dict(capacity_before=0,capacity_after=1,
            remaining_before=0,remaining_after=1,removed_original_neighbors=1))
        self.assertFalse(c._violations(retracted));self.assertEqual(payload(entry),before)
        save('old_owner_capacity',dict(status='PASS',unrelated_rejection=receipt,retraction=account))

    def test_03_failure_classification_and_strict_private_refusal(self):
        # Contact extension exists, but no connected region in a cycle has four
        # distinct free external sites. This must not invoke a contact guide.
        G=nx.star_graph(4);H=nx.cycle_graph(5);s=state(G,H);before=payload(s)
        self.assertIsNone(c._place(s,0));failure=s.e.placements[-1]
        self.assertEqual(failure['failure_reason'],'capacity_exhausted');self.assertTrue(failure['exhaustive'])
        row={}
        with patch.object(c._c,'_place',side_effect=AssertionError('capacity failure invoked contact guide')):
            self.assertIsNone(c._transaction(s,0,None,row,failure))
        self.assertEqual(row['status'],'rebuild_failed_capacity_no_outside');self.assertEqual(payload(s),before)
        GG=nx.path_graph(3);HH=nx.Graph();HH.add_nodes_from(range(4));HH.add_edges_from([(0,1),(2,3)])
        separated=state(GG,HH,{0:{0},2:{2}});c._certify(separated)
        self.assertIsNone(c._place(separated,1));contact=separated.e.placements[-1]
        self.assertEqual(contact['failure_reason'],'contact_unreachable')
        save('failure_reasons',dict(status='PASS',capacity_failure=failure,refusal=row,contact_failure=contact))

    def test_04_growth_interruption_and_certified_full_censoring(self):
        G,H=corridor();s=state(G,H);before=payload(s);clock=[0.]
        s.e.b.clock=lambda:clock[0];s.e.b.deadline=1.
        replace=c._replace
        def interrupted(*args):
            value=replace(*args);clock[0]=2.;return value
        with patch.object(c,'_replace',interrupted):
            with self.assertRaises(c._Deadline):c._place(s,0)
        # Restore the measurement clock before inspecting the unchanged state.
        s.e.b.clock=time.perf_counter;s.e.b.deadline=time.perf_counter()+30
        self.assertEqual(payload(s),before);self.assertFalse(s.e.placements[-1]['exhaustive'])
        self.assertEqual(s.e.placements[-1]['status'],'interrupted');self.assertIsNone(s.e.complete)
        source=nx.empty_graph(1);target=dnx.zephyr_graph(1);clock[0]=0.;root_calls=[0];tick=c._Budget.tick
        def stop_second_root(obj,name,count=1):
            if name=='root_attempts':
                root_calls[0]+=1
                if root_calls[0]==2:clock[0]=9.6
            return tick(obj,name,count)
        with patch.object(c.time,'perf_counter',lambda:clock[0]),patch.object(c._Budget,'tick',stop_second_root):
            censored=c.capacity_contact_embed(source,target,timeout=10.)
        self.assertEqual(censored['status'],'SUCCESS');self.assertTrue(valid(source,target,censored['embedding'])[0])
        self.assertTrue(censored['diag']['complete_private_scan_censored'])
        save('interruption',dict(status='PASS',unpublished_growth_preserved=True,injected_wrapper=censored))

    def test_05_two_complete_tiny_controls(self):
        target=dnx.zephyr_graph(2)
        fixtures=[('star22',nx.star_graph(21),23),('shared_k2_10',nx.complete_bipartite_graph(2,10),12)]
        summary=[]
        for name,source,expected_q in fixtures:
            for u in source:source.nodes[u].clear()
            wall,cpu=time.perf_counter(),time.process_time()
            result=c.capacity_contact_embed(source,target,seed=0,timeout=5.)
            elapsed,cputime=time.perf_counter()-wall,time.process_time()-cpu
            ok,why,quality=valid(source,target,result['embedding'])
            save(name,dict(result=result,wall=elapsed,cpu=cputime,original_valid=ok,reason=why,quality=quality,expected_q=expected_q))
            summary.append(dict(name=name,status=result['status'],wall=elapsed,cpu=cputime,original_valid=ok,quality=quality,expected_q=expected_q))
            with self.subTest(name=name):
                self.assertEqual(result['status'],'SUCCESS');self.assertFalse(result.get('error'))
                self.assertTrue(ok,why);self.assertEqual(quality['qubits'],expected_q);self.assertLessEqual(result['time'],5.)
        self.assertFalse(ATTEMPTS)
        save('full_tiny_summary',dict(calls=summary,prohibited_import_attempts=ATTEMPTS))

if __name__=='__main__':unittest.main(verbosity=2)
