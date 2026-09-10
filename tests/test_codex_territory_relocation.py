"""One focused C018 check: whole-owner proposals, cache/publication and clocks."""
import argparse
import copy
import hashlib
import importlib.abc
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
ATTEMPTS=[];RECORDS=[];PUBLIC_CALLS=0


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if 'minorminer' in fullname or 'busclique' in fullname:
            ATTEMPTS.append(fullname);raise ImportError('forbidden embedding dependency')


sys.meta_path.insert(0,Guard())


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


c=load('_c018_under_test',ROOT/'packages/ember-qc/src/ember_qc/algorithms/territory_relocation.py')
ORACLE=ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
assert hashlib.sha256(ORACLE.read_bytes()).hexdigest()=='e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
oracle=load('_c018_original_oracle',ORACLE)
helper=kernels=None


def adjacency(n,edges):
    rows=[set() for _ in range(n)]
    for u,v in edges:rows[u].add(v);rows[v].add(u)
    return [tuple(sorted(r)) for r in rows]


class FixedRandom:
    def __init__(self,value):self.value=value
    def random(self):return self.value


class InjectedBudget(c._Budget):
    def __init__(self,deadline):
        super().__init__(deadline);self.trigger=None;self.calls=None
    def check(self):
        super().check()
        if self.trigger is not None and self.trigger():
            self.trigger=None;raise c._Deadline('injected '+self.phase)
        if self.calls is not None:
            self.calls-=1
            if self.calls==0:
                self.calls=None;raise c._Deadline('injected publication boundary')


def engine(src,adj,chains,old=False):
    return c._Engine(src,adj,chains,0,InjectedBudget(time.perf_counter()+30),helper,kernels,old_roots=old)


def choose(e,u,root):
    np=e.np;sites=np.flatnonzero((e.state.owner<0)|(e.state.owner==u))
    if e.old_roots:sites=e.state.chains[u].copy()
    sites=sites[np.argsort(e.trank[sites],kind='stable')]
    scores=e.k.root_scores(e.cache,e.neighbors[u],e.weights[e.incident[u]],sites)
    scale=(float(np.median(e.weights)) if len(e.weights) else 2.)*max(1,len(e.neighbors[u]))
    masses=np.exp(-(scores-float(scores.min()))/scale)
    index=list(map(int,sites)).index(root)
    draw=(float(masses[:index].sum())+float(masses[index])/2)/float(masses.sum())
    e.rng=FixedRandom(draw)


def validate(test,label,e,state=None,complete=False):
    """Original oracle on nontrivial labels, retaining all owners and actual contacts."""
    s=e.state if state is None else state
    sl=[101-17*u for u in range(e.n)];tl=[2003-23*q for q in range(e.h)]
    source_edges=[(sl[u],sl[v]) for i,(u,v) in enumerate(e.edges) if complete or s.counts[i]>0]
    sa,se=oracle.adjacency(dict(nodes=sl,edges=source_edges))
    ta,te=oracle.adjacency(dict(nodes=tl,edges=[(tl[q],tl[p]) for q,r in enumerate(e.adj) for p in r if q<p]))
    mapping={str(sl[u]):[tl[int(q)] for q in chain] for u,chain in enumerate(s.chains)}
    good,reason,quality=oracle.embedding_quality(mapping,sa,se,ta,te)
    test.assertTrue(good,reason)
    test.assertEqual(quality['qubits'],s.Q)
    actual=[]
    for u,v in e.edges:
        actual.append(sum(p in set(map(int,s.chains[v])) for q in s.chains[u] for p in e.adj[q]))
    test.assertEqual(actual,list(map(int,s.counts)))
    RECORDS.append(dict(check=label,source_vertices=e.n,complete_original=complete,
                        independently_valid=good,Q=s.Q,missing=s.missing))


def blocked(old=False):
    return engine(adjacency(3,[(0,1),(1,2),(0,2)]),
                  adjacency(7,[(q,q+1) for q in range(6)]),[{0},{1},{2}],old)


def branched():
    return engine(adjacency(4,[(0,1),(0,2),(0,3)]),
                  adjacency(8,[(0,1),(1,2),(1,3),(1,4),(2,5),(3,6),(4,7)]),
                  [{0},{5},{6},{7}])


class NewRisks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global helper,kernels
        helper,kernels=c._support()

    def test_nonadjacent_relocation_and_real_uphill_acceptance(self):
        e=blocked();old=e.state;before=copy.deepcopy(e.snapshot())
        choose(e,0,4);row={};proposal,delta=c._propose(e,0,False,row)
        self.assertEqual(row['root'],4);self.assertTrue(row['root_outside_old'])
        self.assertGreater(delta,0);self.assertEqual(delta,1.)
        self.assertEqual(set(map(int,proposal.chains[0])),{3,4})
        self.assertEqual(e.snapshot(),before);self.assertIs(e.state,old)
        self.assertEqual(row['contacts_broken'],1);self.assertEqual(row['contacts_gained'],1)
        self.assertTrue(c._accept(delta,2.,False,old,proposal,FixedRandom(0.),row))
        self.assertEqual(row['acceptance_uniform'],0.)
        c._publish(e,proposal,row);validate(self,'accepted_uphill_partial',e)
        self.assertFalse(c._certify(e));self.assertIsNone(e.incumbent)
        anchor=blocked(True);choose(anchor,0,0);r={};p,d=c._propose(anchor,0,False,r)
        self.assertEqual(r['root_domain'],1);self.assertFalse(r['root_outside_old'])
        self.assertEqual(set(map(int,p.chains[0])),{0});self.assertEqual(r['no_free_endpoint'],1)
        self.assertFalse(r['geometry_changed']);self.assertEqual(int(p.versions[0]),0)
        validate(self,'old_territory_access_obstruction',anchor,p)

    def test_actual_shared_branch_energy_and_cache_versions(self):
        e=branched();before=e.state;cached=e.cache.copy();versions=e.cache_versions.copy()
        choose(e,0,0);row={};proposal,delta=c._propose(e,0,False,row)
        self.assertEqual(delta,-8.)
        self.assertEqual(sum(x['length'] for x in row['extensions']),4)
        self.assertEqual(row['delta_Q'],4);self.assertEqual(proposal.missing,0)
        self.assertGreaterEqual(sum(q in set(map(int,proposal.chains[0])) for q in e.adj[1]),3)
        independent_delta=proposal.Q-before.Q+sum(float(w)*(int(a)-int(b)) for w,a,b in zip(e.weights,proposal.gaps,before.gaps))
        self.assertEqual(delta,independent_delta)
        c._publish(e,proposal,row);validate(self,'shared_branch_complete',e,complete=True)
        self.assertTrue(e.np.array_equal(e.cache,cached));self.assertTrue(e.np.array_equal(e.cache_versions,versions))
        self.assertNotEqual(int(e.cache_versions[0]),int(e.state.versions[0]))
        e.distance(0)
        self.assertTrue(e.np.array_equal(e.cache[1:],cached[1:]))
        self.assertFalse(e.np.array_equal(e.cache[0],cached[0]))
        self.assertEqual(int(e.cache_versions[0]),int(e.state.versions[0]))
        self.assertTrue(c._certify(e));self.assertEqual(e.events[0]['kind'],'first_valid')
        self.assertEqual(e.events[0]['Q'],8)
        old_incumbent=e.incumbent;old_events=list(e.events)
        r={};shorter,delta=c._propose(e,0,True,r)
        self.assertTrue(c._accept(delta,0.,True,e.state,shorter,e.rng,r))
        c._publish(e,shorter,r)
        e.b.trigger=lambda:e.incumbent is e.state
        with self.assertRaises(c._Deadline):c._certify(e)
        self.assertIs(e.incumbent,old_incumbent);self.assertEqual(e.events,old_events)
        validate(self,'retained_incumbent_after_interrupted_certification',e,old_incumbent,True)

    def test_interruption_preserves_atomic_publication(self):
        e=branched();old=e.state;before=copy.deepcopy(e.snapshot());choose(e,0,0)
        e.b.trigger=lambda:e.b.phase=='regrowth'
        row={}
        with self.assertRaises(c._Deadline):c._propose(e,0,False,row)
        self.assertIs(e.state,old);self.assertEqual(e.snapshot(),before)
        row={};proposal,_=c._propose(e,0,False,row)
        e.b.calls=1
        with self.assertRaises(c._Deadline):c._publish(e,proposal,row)
        self.assertIs(e.state,old);self.assertEqual(e.snapshot(),before)
        e.b.calls=2
        with self.assertRaises(c._Deadline):c._publish(e,proposal,row)
        self.assertIs(e.state,proposal);self.assertTrue(row['committed']);self.assertEqual(row['status'],'committed')
        self.assertFalse(e.events);self.assertIsNone(e.incumbent)
        validate(self,'coherent_postpublication_interruption',e,complete=True)

    def test_public_first_valid_and_final_deadline_gate(self):
        global PUBLIC_CALLS
        import networkx as nx
        G=nx.Graph();G.add_nodes_from([9,-4]);G.add_edge(9,-4)
        H=nx.Graph();H.add_nodes_from([101,87,-3]);H.add_edges_from([(101,87),(87,-3)])
        PUBLIC_CALLS+=1
        result=c.territory_relocation_embed(G,H,seed=0,timeout=30.)
        self.assertEqual(result['status'],'SUCCESS',result.get('error'))
        self.assertEqual(result['diag']['first_valid']['Q'],2)
        self.assertLess(result['diag']['first_valid']['wall'],result['time'])
        sa,se=oracle.adjacency(dict(nodes=list(G),edges=list(G.edges())))
        ta,te=oracle.adjacency(dict(nodes=list(H),edges=list(H.edges())))
        mapping={str(u):v for u,v in result['embedding'].items()}
        self.assertTrue(oracle.embedding_quality(mapping,sa,se,ta,te)[0])
        RECORDS.append(dict(check='public_tiny_complete',independently_valid=True,Q=2,complete_original=True))
        class FinalExpired(c._Budget):
            def check(self):
                if self.phase=='final_validation_output':raise c._Deadline('injected final boundary')
                super().check()
        with patch.object(c,'_Budget',FinalExpired):
            PUBLIC_CALLS+=1
            late=c.territory_relocation_embed(G,H,seed=0,timeout=30.)
        self.assertEqual(late['status'],'TIMEOUT');self.assertFalse(late['embedding'])
        self.assertIsNotNone(late['diag']['first_valid'])
        RECORDS.append(dict(check='final_deadline_no_credit',status=late['status'],embedding_empty=True))

    def test_post_first_valid_runtime_valueerror_is_fatal(self):
        global PUBLIC_CALLS
        import networkx as nx
        G=nx.Graph([(9,-4)]);H=nx.Graph([(101,87),(87,-3)])
        original_run=c._run
        def fail_after_valid(e):
            original_run(e)
            self.assertIsNotNone(e.incumbent)
            self.assertEqual(e.events[0]['kind'],'first_valid')
            validate(self,'valid_before_injected_runtime_error',e,e.incumbent,True)
            raise ValueError('injected post-first-valid runtime failure')
        with patch.object(c,'_run',fail_after_valid):
            PUBLIC_CALLS+=1
            result=c.territory_relocation_embed(G,H,seed=0,timeout=30.)
        self.assertEqual(result['status'],'ERROR')
        self.assertTrue(result['diag']['fatal_error'])
        self.assertEqual(result['diag']['stop_reason'],'exception')
        self.assertEqual(result['error'],'ValueError: injected post-first-valid runtime failure')
        self.assertFalse(result['embedding']);self.assertNotIn('diagnostic_embedding',result)
        self.assertEqual(result['diag']['first_valid']['Q'],2)
        self.assertEqual(result['diag']['terminal']['missing_edges'],0)
        RECORDS.append(dict(check='post_first_valid_runtime_error_no_credit',status=result['status'],
                            fatal_error=True,embedding_empty=True,prior_first_valid_Q=2))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    parser.add_argument('--case',choices=unittest.defaultTestLoader.getTestCaseNames(NewRisks))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    started,cpu=time.perf_counter(),time.process_time()
    suite=(unittest.TestSuite([NewRisks(args.case)]) if args.case else
           unittest.defaultTestLoader.loadTestsFromTestCase(NewRisks))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record=dict(status='PASS' if result.wasSuccessful() and not ATTEMPTS else 'FAIL',
        focused_check_groups=1,test_cases=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        prohibited_attempts=ATTEMPTS,public_tiny_constructor_calls=PUBLIC_CALLS,development_constructor_calls=0,
        records=RECORDS,versions={x:importlib.metadata.version(x) for x in ('numpy','numba','llvmlite','networkx')},
        wall=time.perf_counter()-started,cpu=time.process_time()-cpu)
    (args.output/'summary.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('records','versions')}))
    return 0 if record['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
