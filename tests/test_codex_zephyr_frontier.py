"""C012 five new-risk groups; tiny inputs only, no corpus/solver comparator."""
import copy
import hashlib
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
OUT=Path(os.environ.get('C012_CHECK_OUTPUT','results/codex/track-c-012-checks/unset'))
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
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
c=load('isolated_c012','packages/ember-qc/src/ember_qc/algorithms/zephyr_frontier.py')
o=load('original_oracle','results/codex/042-results-review/pre-execution/ember_embedding_oracle.py')

def save(name,value):
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/(name+'.json')
    with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')

def valid(source,target,mapping):
    sa={u:set(source[u]) for u in source};se={tuple(sorted(e)) for e in source.edges}
    ta={q:set(target[q]) for q in target};te={tuple(sorted(e)) for e in target.edges}
    return o.embedding_quality({str(u):v for u,v in mapping.items()},sa,se,ta,te)

def label(q,m):
    u,w,k,j,z=q
    return (((u*(2*m+1)+w)*4+k)*2+j)*m+z

def supplied(m,coordinates,edges=None):
    ids=[label(q,m) for q in coordinates]
    graph=dnx.zephyr_graph(m).subgraph(ids).copy()
    if edges is not None:
        keep={frozenset((ids[a],ids[b])) for a,b in edges}
        graph.remove_edges_from([e for e in graph.edges if frozenset(e) not in keep])
        assert {frozenset(e) for e in graph.edges}==keep
    return graph,ids

def state(source,target,seed=2):
    b=c._Budget(time.perf_counter()+100.)
    sl,sa=c._graph(source,b);tl,ta=c._graph(target,b)
    m,coords=c._geometry(target,tl,ta,b)
    s=c._State(sa,ta,coords,m,seed,b)
    return s,{q:i for i,q in enumerate(tl)},sl,tl

def payload(s):
    return copy.deepcopy((s.I,s.chains,s.trees,s.roots,s.owner,s.contacts,s.cut,s.generation))

def suffix_fixture(extra_edge=False):
    source=nx.Graph();source.add_nodes_from(range(5));source.add_edges_from([(0,2),(1,3),(0,4),(1,4)])
    if extra_edge:source.add_edge(0,1)
    coords=[(0,0,0,0,z) for z in range(6)]+[(0,0,0,1,0),(0,0,0,1,4)]
    target,ids=supplied(6,coords)
    s,inv,sl,tl=state(source,target)
    assert s.sweep==0
    s.I={0,1,2,3}
    for u,indices in [(0,[1,2]),(1,[4,3]),(2,[0]),(3,[5])]:
        s.claim(u,[inv[ids[q]] for q in indices])
    assert s.certify(s.I) is None
    return source,target,s,inv,sl,tl,ids

class FrontierChecks(unittest.TestCase):
    def test_01_geometry_actual_couplers(self):
        g=dnx.zephyr_graph(2);b=c._Budget(time.perf_counter()+10)
        labels,adj=c._graph(g,b);m,coords=c._geometry(g,labels,adj,b)
        kinds={c._edge_kind(coords[q],coords[p]) for q,ns in enumerate(adj) for p in ns}
        self.assertEqual(kinds,{'external','odd','cross_orientation'})
        for seed in (2,1,5,0):
            s=c._State([set()],adj,coords,m,seed,b)
            self.assertTrue(all(abs(s.strip[q]-s.strip[p])<=2 for q,ns in enumerate(adj) for p in ns))
        broken=g.copy();broken.remove_edge(0,1)
        labs,aa=c._graph(broken,b);c._geometry(broken,labs,aa,b)
        self.assertNotIn(labs.index(1),aa[labs.index(0)])
        illegal=g.copy();illegal.add_edge(0,4)
        labs,aa=c._graph(illegal,b)
        with self.assertRaises(c._InputError):c._geometry(illegal,labs,aa,b)
        wrong=g.copy();wrong.nodes[0]['zephyr_index']=(0,1,0,0,0)
        with self.assertRaises(c._InputError):c._geometry(wrong,labels,adj,b)
        save('geometry',dict(status='PASS',kinds=sorted(kinds),missing_edge_preserved=True,illegal_edge_rejected=True,prohibited_import_attempts=ATTEMPTS))

    def test_02_full_tiny_constructions(self):
        target=dnx.zephyr_graph(2)
        fixtures=[('path8',nx.path_graph(8)),('binary_tree7',nx.balanced_tree(2,2)),
                  ('star22',nx.star_graph(21)),('grid3x3',nx.convert_node_labels_to_integers(nx.grid_2d_graph(3,3))),
                  ('path3_two_isolates',nx.disjoint_union(nx.path_graph(3),nx.empty_graph(2)))]
        summaries=[]
        for name,source in fixtures:
            wall,cpu=time.perf_counter(),time.process_time()
            result=c.frontier_embed(source,target,seed=0,timeout=5.)
            elapsed,cputime=time.perf_counter()-wall,time.process_time()-cpu
            ok,why,q=valid(source,target,result['embedding'])
            save(name,dict(result=result,wall=elapsed,cpu=cputime,original_valid=ok,reason=why,quality=q))
            summaries.append(dict(name=name,status=result['status'],stop=result['diag'].get('stop_reason'),
                                  wall=elapsed,cpu=cputime,original_valid=ok,quality=q))
            with self.subTest(name=name):
                self.assertEqual(result['status'],'SUCCESS')
                self.assertTrue(ok,why)
                self.assertFalse(result.get('error'))
                self.assertLessEqual(result['time'],5.)
                if name=='path3_two_isolates':
                    self.assertEqual(len(result['embedding'][3]),1);self.assertEqual(len(result['embedding'][4]),1)
        save('full_tiny_summary',summaries)

    def test_03_suffix_joint_original_contacts(self):
        source,target,s,inv,sl,tl,ids=suffix_fixture()
        before=payload(s);ordinary={};self.assertIsNone(c._birth(s,4,False,ordinary));self.assertEqual(payload(s),before)
        row={};new=c._birth(s,4,True,row)
        self.assertIsNotNone(new);self.assertEqual(payload(s),before)
        self.assertEqual(set(row['released']),{0,1});self.assertEqual(row['released_Q'],2)
        self.assertEqual(row['Q_after']-row['Q_before'],0)
        result={u:[tl[q] for q in cc] for u,cc in new.chains.items()}
        self.assertTrue(valid(source,target,result)[0])
        self.assertFalse(any(new.live(u) for u in new.I))
        self.assertEqual(new.roots[0],s.roots[0]);self.assertEqual(new.roots[1],s.roots[1])
        with self.assertRaises(RuntimeError):s.release(0,[s.roots[0]])
        self.assertEqual(payload(s),before)
        bad=s.fork();bad.trees[0]=set();self.assertEqual(bad.certify({0}),'construction_tree')
        source2,target2,s2,*_=suffix_fixture(extra_edge=True);before2=payload(s2);negative={}
        self.assertIsNone(c._birth(s2,4,True,negative));self.assertEqual(payload(s2),before2)
        # Singleton/root immobility: no proper suffix is available for singleton owners.
        singleton=s.fork();singleton.release(0,[inv[ids[2]]]);self.assertNotIn(0,c._suffixes(singleton,4,singleton.window()))
        save('joint_suffix',dict(status='PASS',ordinary=ordinary,positive=row,negative=negative,
                                 original_full_valid=True,last_neighbor_port_guard_released=True))

    def test_04_carry_expiring_port_and_atomic_rollback(self):
        coords=[(1,0,0,0,1),(1,0,0,1,0),(1,0,0,1,1),(1,0,0,0,2)]
        target,ids=supplied(3,coords,[(0,1),(1,2),(2,3)])
        source=nx.path_graph(2);s,inv,sl,tl=state(source,target);s.cut=1;s.I={0};s.claim(0,[inv[ids[0]]])
        self.assertIsNone(s.certify(s.I));self.assertTrue(s.chains[0]&s.window(2));self.assertFalse(s.port(0,2))
        before=payload(s);row={};new=c._carry(s,row)
        self.assertIsNotNone(new);self.assertEqual(payload(s),before);self.assertEqual(new.cut,2)
        self.assertEqual(row['added'],2);self.assertTrue(new.port(0,2));self.assertIsNone(new.certify(new.I))
        coords2=[(1,0,0,0,0),(1,0,1,0,0),(0,1,0,0,0),(1,1,0,1,0)]
        target2,ids2=supplied(2,coords2,[(0,2),(1,2),(2,3)])
        source2=nx.Graph();source2.add_nodes_from(range(4));source2.add_edges_from([(0,2),(1,3)])
        s2,iv,*_=state(source2,target2);s2.I={0,1};s2.claim(0,[iv[ids2[0]]]);s2.claim(1,[iv[ids2[1]]])
        self.assertIsNone(s2.certify(s2.I));before2=payload(s2);negative={}
        self.assertIsNone(c._carry(s2,negative));self.assertEqual(payload(s2),before2)
        self.assertEqual(len(negative['paths']),1)
        save('carry',dict(status='PASS',expiring_port_positive=row,shared_bottleneck_negative=negative))

    def test_05_deadline_and_fatal_noncredit(self):
        source,target,s,inv,sl,tl,ids=suffix_fixture();before=payload(s)
        now=[0.];s.b.clock=lambda:now[0];s.b.deadline=1.
        grow=c._State.grow
        def delayed(obj,*args,**kwargs):
            result=grow(obj,*args,**kwargs);now[0]=2.;return result
        with patch.object(c._State,'grow',delayed):
            with self.assertRaises(c._Deadline):c._birth(s,4,True,{})
        self.assertEqual(payload(s),before)
        tiny=nx.empty_graph(1);hardware=dnx.zephyr_graph(1)
        def completed_then_error(obj,diag):
            obj.I={0};obj.claim(0,[0]);raise ValueError('injected internal failure after complete state')
        fatal=c.frontier_embed
        with patch.object(c,'_run',completed_then_error):
            result=fatal(tiny,hardware,timeout=2.)
        self.assertEqual(result['status'],'ERROR');self.assertEqual(result['embedding'],{})
        self.assertTrue(result['diag']['final']['valid']);self.assertIn('injected internal',result['error'])
        final=c._final;clock=[0.]
        def complete(obj,diag):obj.I={0};obj.claim(0,[0]);return 'complete_introduced_source'
        def late_final(*args):final(*args);clock[0]=2.
        with patch.object(c.time,'perf_counter',lambda:clock[0]),patch.object(c,'_run',complete),patch.object(c,'_final',late_final):
            late=c.frontier_embed(tiny,hardware,timeout=1.)
        self.assertEqual(late['status'],'TIMEOUT');self.assertEqual(late['embedding'],{})
        self.assertTrue(late['diag']['final']['valid']);self.assertTrue(late['diagnostic_embedding'])
        self.assertFalse(ATTEMPTS)
        save('interruption',dict(status='PASS',published_state_preserved=True,fatal=fatal_summary(result),late=fatal_summary(late)))

def fatal_summary(result):
    return {k:result.get(k) for k in ('status','embedding','diagnostic_embedding','error','time','diag')}

if __name__=='__main__':unittest.main(verbosity=2)
