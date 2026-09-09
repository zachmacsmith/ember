"""C013 focused risks and six tiny complete calls; no development panel."""
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

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ['C013_CHECK_OUTPUT'])
ATTEMPTS = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if 'minorminer' in fullname or 'busclique' in fullname:
            ATTEMPTS.append(fullname); raise ImportError('prohibited embedding dependency')
sys.meta_path.insert(0,Guard())
import networkx as nx
import dwave_networkx as dnx

def load(name,path):
    spec = importlib.util.spec_from_file_location(name,ROOT/path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
c = load('isolated_c013','packages/ember-qc/src/ember_qc/algorithms/zephyr_contact_domain.py')
o = load('original_oracle','results/codex/042-results-review/pre-execution/ember_embedding_oracle.py')

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/(name+'.json')).open('x') as f: json.dump(value,f,indent=2,sort_keys=True); f.write('\n')

def valid(source,target,mapping):
    sa={u:set(source[u]) for u in source}; se={tuple(sorted(e)) for e in source.edges}
    ta={q:set(target[q]) for q in target}; te={tuple(sorted(e)) for e in target.edges}
    return o.embedding_quality({str(u):list(v) for u,v in mapping.items()},sa,se,ta,te)

def state(source,target,mapping=None,rank=None):
    G=[set(source[u]) for u in range(len(source))]; H=[set(target[q]) for q in range(len(target))]
    e=c._Engine(G,H,[(0,0,0,0,0)]*len(H),0,0,c._Budget(time.perf_counter()+30))
    if rank is not None:
        e.trank={q:i for i,q in enumerate(rank)}; e.torder=list(rank)
        e.adj=[sorted(ns,key=e.trank.__getitem__) for ns in H]
    s=c._State(e,mapping); s.certify();e.published=s
    return s

def payload(s):
    return copy.deepcopy((s.I,s.chains,s.owner,s.masks,s.boundaries,s.contacts,s.domains,s.Q))

class ContactDomainChecks(unittest.TestCase):
    def test_01_domains_scores_and_rank_keys(self):
        G=nx.path_graph(3);H=nx.path_graph(4)
        s=state(G,H,{0:{0},2:{3}})
        for v in s.domains:
            direct=set(range(len(H)))-set(q for cc in s.chains.values() for q in cc)
            for u in G[v]:
                if u in s.I: direct &= set().union(*(set(H[q]) for q in s.chains[u]))
            self.assertEqual(set(c._bits(s.domains[v])),direct)
        self.assertEqual(s.domains[1],0)
        proposed=c._place(s,1)
        self.assertEqual(proposed.chains[1],frozenset((1,2)))
        self.assertTrue(valid(G,H,proposed.chains)[0])
        self.assertEqual(s.score()[0],4) # Fixed endpoint chains require Q4.
        moved=state(G,H,{0:{0},2:{2}})
        self.assertEqual(c._place(moved,1).Q,3) # Moving a frozen chain invalidates that bound.
        for sr,sites in proposed.score()[-1]:
            self.assertIs(type(sr),int);self.assertTrue(all(type(q) is int for q in sites))
        self.assertNotIn(1,c._lost(s,proposed))
        save('domains',dict(status='PASS',conditional_bound=4,moved_bound=3,
                            root_record=s.e.placements,prohibited_import_attempts=ATTEMPTS))

    def test_02_tree_pruning_and_actual_geometry(self):
        G=nx.path_graph(2);H=nx.path_graph(3)
        s=state(G,H,{0:{2}},rank=[0,1,2])
        tree=c._tree(s,1,0,s.free)
        self.assertEqual(tree,frozenset((1,))) # The initial root at 0 is removable.
        self.assertTrue(valid(G,H,s.add(1,tree).chains)[0])
        target=dnx.zephyr_graph(2); b=c._Budget(time.perf_counter()+10)
        labels,adj=c._graph(target,b); m,coords=c._geometry(target,labels,adj,b)
        target.remove_edge(0,1); ll,aa=c._graph(target,b);c._geometry(target,ll,aa,b)
        self.assertNotIn(ll.index(1),aa[ll.index(0)])
        bad=target.copy();bad.add_edge(0,4); ll,aa=c._graph(bad,b)
        with self.assertRaises(c._InputError):c._geometry(bad,ll,aa,b)
        save('tree_geometry',dict(status='PASS',root_removed=True,missing_coupler_preserved=True,illegal_coupler_rejected=True))

    def test_03_retraction_closed_owner_expansion_and_rollback(self):
        G=nx.Graph();G.add_nodes_from(range(4));G.add_edges_from([(1,2),(2,3)])
        H=nx.path_graph(4);s=state(G,H,{0:{1},1:{3}},rank=[0,1,2,3]); before=payload(s)
        ordinary=c._place(s,2);self.assertEqual(c._lost(s,ordinary),[3])
        row={};new=c._transaction(s,2,ordinary,row)
        self.assertEqual(payload(s),before); self.assertEqual(new.I,{0,1,2})
        self.assertIn(0,row['initial_K']);self.assertNotEqual(new.chains[0],s.chains[0])
        full=c._place(new,3);self.assertEqual(full.Q,4);self.assertTrue(valid(G,H,full.chains)[0])
        # Exact outside-owner expansion: a closed isolate at 3 obstructs a
        # private b-c-v path after the first two owners have been retracted.
        GG=nx.Graph();GG.add_nodes_from(range(4));GG.add_edges_from([(0,1),(0,2)])
        HH=nx.path_graph(6);ss=state(GG,HH,{0:{5},1:{4},3:{3}},rank=[2,1,0,3,4,5]);entry=payload(ss)
        self.assertIsNone(c._place(ss,2)); expanded={};finish=c._transaction(ss,2,None,expanded)
        save('expansion_observation',dict(transaction=expanded,placements=ss.e.placements,
             final=finish.snapshot() if finish else None))
        self.assertIsNotNone(finish);self.assertTrue(valid(GG,HH,finish.chains)[0])
        self.assertEqual(expanded['initial_K'],[0,1]);self.assertEqual(expanded['attempts'][0]['expanded_by'],[3])
        self.assertEqual(payload(ss),entry)
        impossible=nx.complete_graph(3);line=nx.path_graph(4);neg=state(impossible,line,{0:{0},1:{1}})
        original=payload(neg);self.assertIsNone(c._place(neg,2));failure={}
        self.assertIsNone(c._transaction(neg,2,None,failure));self.assertEqual(payload(neg),original)
        save('retraction',dict(status='PASS',closed_owner=row,expanded=expanded,failed_rebuild=failure))

    def test_04_deadline_censored_full_proposal_fatal_and_late(self):
        source=nx.empty_graph(1);target=dnx.zephyr_graph(1);clock=[0.]
        tick=c._Budget.tick; roots=[0]
        def stop_second_root(obj,name,count=1):
            if name=='root_attempts':
                roots[0]+=1
                if roots[0]==2: clock[0]=9.6
            return tick(obj,name,count)
        with patch.object(c.time,'perf_counter',lambda:clock[0]),patch.object(c._Budget,'tick',stop_second_root):
            censored=c.contact_domain_embed(source,target,timeout=10.)
        self.assertEqual(censored['status'],'SUCCESS');self.assertTrue(valid(source,target,censored['embedding'])[0])
        self.assertTrue(censored['diag']['complete_private_scan_censored'])
        self.assertFalse(censored['diag']['placements'][0]['exhaustive'])
        # An interrupted, uncertified proposal cannot invoke the obstruction guide.
        clock[0]=0.
        def stop_score(obj):clock[0]=9.6;obj.e.b.check()
        with patch.object(c.time,'perf_counter',lambda:clock[0]),patch.object(c._State,'score',stop_score):
            unfinished=c.contact_domain_embed(source,target,timeout=10.)
        self.assertEqual(unfinished['status'],'FAILURE');self.assertEqual(unfinished['embedding'],{})
        self.assertFalse(unfinished['diag']['rebuilds'])
        def complete_then_error(s,diag):
            new=s.add(0,{0});new.certify();s.e.published=new
            raise RuntimeError('injected fatal after complete published state')
        with patch.object(c,'_run',complete_then_error):
            fatal=c.contact_domain_embed(source,target,timeout=2.)
        self.assertEqual(fatal['status'],'ERROR');self.assertEqual(fatal['embedding'],{})
        self.assertTrue(fatal['diag']['final']['valid'])
        final=c._final;clock[0]=0.
        def complete(s,diag):
            new=s.add(0,{0});new.certify();s.e.published=new;return new,'complete_introduced_source'
        def late_final(*args):final(*args);clock[0]=11.
        with patch.object(c.time,'perf_counter',lambda:clock[0]),patch.object(c,'_run',complete),patch.object(c,'_final',late_final):
            late=c.contact_domain_embed(source,target,timeout=10.)
        self.assertEqual(late['status'],'TIMEOUT');self.assertEqual(late['embedding'],{})
        self.assertTrue(late['diag']['final']['valid'])
        save('deadlines',dict(status='PASS',censored=censored,unfinished=unfinished,fatal=fatal,late=late))

    def test_05_six_complete_tiny_calls(self):
        hardware=dnx.zephyr_graph(2)
        fixtures=[('path8',nx.path_graph(8),hardware),('binary_tree7',nx.balanced_tree(2,2),hardware),
                  ('star22',nx.star_graph(21),hardware),
                  ('grid3x3',nx.convert_node_labels_to_integers(nx.grid_2d_graph(3,3)),hardware),
                  ('path3_two_isolates',nx.disjoint_union(nx.path_graph(3),nx.empty_graph(2)),hardware)]
        p4=dnx.zephyr_graph(4).subgraph(range(4)).copy()
        self.assertEqual(set(p4.edges),{(0,1),(1,2),(2,3)})
        fixtures.append(('triangle_in_path4',nx.complete_graph(3),p4));summary=[]
        for name,source,target in fixtures:
            wall,cpu=time.perf_counter(),time.process_time()
            result=c.contact_domain_embed(source,target,seed=0,timeout=5.)
            elapsed,cputime=time.perf_counter()-wall,time.process_time()-cpu
            ok,why,quality=valid(source,target,result['embedding'])
            save(name,dict(result=result,wall=elapsed,cpu=cputime,original_valid=ok,reason=why,quality=quality))
            summary.append(dict(name=name,status=result['status'],wall=elapsed,cpu=cputime,original_valid=ok,quality=quality))
            with self.subTest(name=name):
                self.assertFalse(result.get('error'));self.assertLessEqual(result['time'],5.)
                if name=='triangle_in_path4':
                    self.assertFalse(ok);self.assertEqual(result['status'],'FAILURE')
                else:
                    self.assertEqual(result['status'],'SUCCESS');self.assertTrue(ok,why)
        self.assertFalse(ATTEMPTS)
        save('full_tiny_summary',dict(calls=summary,prohibited_import_attempts=ATTEMPTS))

if __name__=='__main__':unittest.main(verbosity=2)
