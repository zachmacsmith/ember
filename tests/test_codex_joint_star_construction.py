"""One C019 guarded packet: weighted assignment, real blocks and admission clocks."""
import argparse
import copy
import hashlib
import importlib.abc
import importlib.metadata
import importlib.util
import itertools
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


c=load('_c019_under_test',ROOT/'packages/ember-qc/src/ember_qc/algorithms/joint_star_construction.py')
ORACLE=ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
assert hashlib.sha256(ORACLE.read_bytes()).hexdigest()=='e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
oracle=load('_c019_original_oracle',ORACLE)
helper=kernels=None


def adjacency(n,edges):
    rows=[set() for _ in range(n)]
    for u,v in edges:rows[u].add(v);rows[v].add(u)
    return [tuple(sorted(row)) for row in rows]


class InjectedBudget(c._Budget):
    def __init__(self,deadline):
        super().__init__(deadline);self.trigger=None
    def check(self):
        super().check()
        if self.trigger is not None and self.trigger():
            self.trigger=None;raise c._Deadline('injected '+self.phase)


def engine(src,adj,chains,cardinality_only=False):
    return c._Engine(src,adj,chains,0,InjectedBudget(time.perf_counter()+120),helper,kernels,
                     cardinality_only=cardinality_only)


def validate(test,label,e,state=None,complete=False):
    """Reuse original oracle with different labels and independently recount contacts."""
    s=e.state if state is None else state
    sl=[101-17*u for u in range(e.n)];tl=[2003-23*q for q in range(e.h)]
    source_edges=[(sl[u],sl[v]) for ix,(u,v) in enumerate(e.edges) if complete or s.counts[ix]>0]
    sa,se=oracle.adjacency(dict(nodes=sl,edges=source_edges))
    ta,te=oracle.adjacency(dict(nodes=tl,edges=[(tl[q],tl[p]) for q,r in enumerate(e.adj) for p in r if q<p]))
    mapping={str(sl[u]):[tl[int(q)] for q in chain] for u,chain in enumerate(s.chains)}
    good,reason,quality=oracle.embedding_quality(mapping,sa,se,ta,te)
    test.assertTrue(good,reason);test.assertEqual(quality['qubits'],s.Q)
    counts=[sum(p in set(map(int,s.chains[v])) for q in s.chains[u] for p in e.adj[q]) for u,v in e.edges]
    test.assertEqual(counts,list(map(int,s.counts)));test.assertEqual(sum(counts)-len(counts),s.R)
    RECORDS.append(dict(check=label,independently_valid=good,complete_original=complete,Q=s.Q,R=s.R,missing=s.missing))


def enumeration(cost,allowed):
    k,b=cost.shape;best=None;examined=0
    for assignment in itertools.product(range(-1,b),repeat=k):
        sites=[j for j in assignment if j>=0]
        if len(set(sites))!=len(sites):continue
        if any(j>=0 and not allowed[i,j] for i,j in enumerate(assignment)):continue
        examined+=1;score=(-len(sites),sum(int(cost[i,j]) for i,j in enumerate(assignment) if j>=0))
        if best is None or score<best:best=score
    return best,examined


BRANCH_EDGES=[(0,1),(0,2),(0,3),(1,4),(1,5),(2,6),(2,7),(3,8),(3,9)]


def branching():
    return engine(adjacency(7,[(0,v) for v in range(1,7)]),adjacency(10,BRANCH_EDGES),
                  [{4},{0},{1},{2},{3},{5},{6}])


def protected():
    return engine(adjacency(4,[(0,1),(0,2),(0,3)]),adjacency(10,BRANCH_EDGES),
                  [{4},{5},{6},{3,8}])


class NewRisks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global helper,kernels
        for package in ('minorminer','busclique'):
            try:version=importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:continue
            raise AssertionError('forbidden installed dependency '+package+' '+version)
        helper,kernels=c._support()

    def test_weighted_assignment_and_actual_boundary_proxy(self):
        np=kernels.np;e=engine(adjacency(1,[]),adjacency(2,[(0,1)]),[{0}])
        fixtures=[
            ([[0,1],[0,8]],[[1,1],[1,1]]),
            ([[0,4],[3,0],[0,2]],[[1,0],[1,1],[0,0]]),
            ([[4,1,0],[2,0,3],[0,2,0]],[[1,1,0],[1,0,1],[0,1,0]]),
            ([[7,0,3,1],[1,2,0,4],[3,1,4,0]],[[1,1,1,1],[0,1,1,1],[1,0,1,1]]),
            ([[],[],[]],[[],[],[]]),
        ]
        for index,(values,domain) in enumerate(fixtures):
            cost=np.asarray(values,dtype=np.int64);allowed=np.asarray(domain,dtype=np.bool_)
            expected,examined=enumeration(cost,allowed)
            assignment,m,value=c._matching(e,cost,allowed,True)
            self.assertEqual((-m,value),expected)
            self.assertEqual(len(set(map(int,assignment[assignment>=0]))),m)
            _,cm,cv=c._matching(e,cost,allowed,False)
            self.assertEqual(cm,m);self.assertGreaterEqual(cv,value)
            RECORDS.append(dict(check='tiny_assignment',fixture=index,enumerated_feasible=examined,
                                cardinality=m,minimum_cost=value,cardinality_only_cost=cv))
        # Removing an occupied site changes the maximum cardinality and optimum.
        cost=np.asarray([[0,1],[0,8]],dtype=np.int64);allowed=np.ones((2,2),dtype=np.bool_)
        expected,_=enumeration(cost[:,1:],allowed[:,1:])
        _,m,value=c._matching(e,cost[:,1:],allowed[:,1:],True)
        self.assertEqual((-m,value),expected)

        src=adjacency(5,[(0,1),(0,2),(1,3),(2,4)])
        adj=adjacency(6,[(0,1),(0,2),(1,3),(1,4),(2,5),(5,3),(5,4)])
        e=engine(src,adj,[{0},{1},{2},{3},{4}]);old=e.state;row={};query=c._Query(e,0,row)
        expected_costs={1:[2,0,2,0,2,0],2:[2,0,2,2,0,0]}
        for i,v in enumerate(query.leaves):self.assertEqual(list(query.costs[i]),expected_costs[v])
        root=query.root()
        self.assertEqual(root['proxy'],(0,3));self.assertEqual(root['score'],(0,5))
        grown=query.extension(root)
        self.assertEqual(grown['size'],2);self.assertEqual(grown['proxy'],(0,4));self.assertEqual(grown['score'],(0,4))
        self.assertIs(e.state,old)
        row={};proposal,delta=c._propose(e,0,row)
        self.assertEqual((proposal.Q,proposal.missing,delta),(6,0,-1))
        validate(self,'competition_resolved_on_actual_edges',e,proposal,True)

    def test_branched_block_old_internal_gaps_and_protected_long_neighbor(self):
        e=branching();before=e.state;row={};proposal,delta=c._propose(e,0,row)
        self.assertEqual(set(row['selected']),set(range(7)))
        self.assertEqual((proposal.Q,len(proposal.chains[0]),proposal.missing),(10,4,0))
        center=set(map(int,proposal.chains[0]))
        self.assertGreaterEqual(max(sum(q in center for q in e.adj[p]) for p in center),3)
        independent=proposal.Q-before.Q+sum(int(w)*(int(a)-int(b)) for w,a,b in zip(e.weights,proposal.gaps,before.gaps))
        self.assertEqual(delta,independent);self.assertLess(delta,0)
        self.assertGreater(sum(map(int,before.gaps)),0);self.assertEqual(row['new_block_cost'],10)
        self.assertEqual(row['old_block_cost'],before.Q+sum(int(w)*int(g) for w,g in zip(e.weights,before.gaps)))
        self.assertIs(e.state,before);validate(self,'branched_complete_joint_block',e,proposal,True)

        e=protected();before=e.state;cached=e.cache.copy();versions=e.cache_versions.copy();row={}
        proposal,delta=c._propose(e,0,row)
        self.assertEqual(set(row['selected']),{0,1,2});self.assertEqual(row['long_neighbor_exclusions'],1)
        self.assertTrue(e.np.array_equal(proposal.chains[3],before.chains[3]))
        self.assertEqual(int(proposal.versions[3]),int(before.versions[3]))
        self.assertTrue(c._accept(e,proposal,delta,row));c._admit(e,proposal,row)
        validate(self,'long_neighbor_kept_and_joint_owners_published',e,complete=True)
        self.assertTrue(e.np.array_equal(e.cache,cached));self.assertTrue(e.np.array_equal(e.cache_versions,versions))
        for v in row['changed_owners']:self.assertNotEqual(int(e.cache_versions[v]),int(e.state.versions[v]))
        e.distance(0)
        self.assertFalse(e.np.array_equal(e.cache[0],cached[0]))
        self.assertTrue(e.np.array_equal(e.cache[3],cached[3]))
        self.assertEqual(int(e.cache_versions[3]),int(e.state.versions[3]))

    def test_interruption_and_latest_equal_Q_certification(self):
        e=protected();before=e.state;snapshot=copy.deepcopy(e.snapshot())
        e.b.trigger=lambda:e.b.phase=='growth_scoring';row=dict(proposal_complete=False,committed=False)
        with self.assertRaises(c._Deadline):c._propose(e,0,row)
        self.assertIs(e.state,before);self.assertEqual(e.snapshot(),snapshot)
        self.assertFalse(row['proposal_complete']);self.assertFalse(row['committed']);self.assertIsNone(e.incumbent)
        self.assertGreater(row['covering_footprints'],0)
        np=e.np;cost=np.asarray([[0,1],[0,8]],dtype=np.int64);allowed=np.ones((2,2),dtype=np.bool_)
        prior_paths=e.b.work['assignment_path_records']
        e.b.trigger=lambda:e.b.work['assignment_path_records']>prior_paths
        with self.assertRaises(c._Deadline):c._matching(e,cost,allowed,True)
        self.assertIs(e.state,before);self.assertEqual(e.snapshot(),snapshot)

        e=engine(adjacency(2,[(0,1)]),adjacency(5,[(0,1),(1,2),(2,3),(3,4),(2,4)]),[{0,1},{2}])
        c._admit(e,e.state,{},initial=True);old=e.incumbent;events=copy.deepcopy(e.events)
        row=dict(committed=False);proposal,delta=c._recount(e,[0],{0:[3,4]},row)
        self.assertEqual((row['delta_Q'],row['delta_R'],delta),(0,1,0))
        self.assertTrue(c._accept(e,proposal,delta,row))
        e.b.trigger=lambda:e.b.phase=='incumbent_validation'
        with self.assertRaises(c._Deadline):c._admit(e,proposal,row)
        self.assertIs(e.state,old);self.assertIs(e.incumbent,old);self.assertEqual(e.events,events)
        self.assertFalse(row['committed'])
        e.b.trigger=lambda:e.incumbent is proposal
        with self.assertRaises(c._Deadline):c._admit(e,proposal,row)
        self.assertIs(e.state,proposal);self.assertIs(e.incumbent,proposal);self.assertEqual(e.events,events)
        self.assertTrue(row['committed']);self.assertTrue(row['certified'])
        self.assertEqual(e.latest_certified['R'],1);self.assertEqual(e.latest_certified['publication'],1)
        validate(self,'latest_equal_Q_R_state_survives_postpublication_interrupt',e,complete=True)

    def test_public_modes_final_deadline_and_postvalid_error(self):
        global PUBLIC_CALLS
        import networkx as nx
        G=nx.Graph();G.add_nodes_from([91-7*u for u in range(7)])
        G.add_edges_from((91,91-7*v) for v in range(1,7))
        H=nx.Graph();H.add_nodes_from([203-11*q for q in range(10)])
        H.add_edges_from((203-11*q,203-11*p) for q,p in BRANCH_EDGES)
        sa,se=oracle.adjacency(dict(nodes=list(G),edges=list(G.edges())))
        ta,te=oracle.adjacency(dict(nodes=list(H),edges=list(H.edges())))
        for fn in (c.joint_star_construction_embed,c.cardinality_star_construction_embed):
            PUBLIC_CALLS+=1;result=fn(G,H,seed=0,timeout=60.)
            self.assertEqual(result['status'],'SUCCESS',result.get('error'))
            good,reason,quality=oracle.embedding_quality({str(u):v for u,v in result['embedding'].items()},sa,se,ta,te)
            self.assertTrue(good,reason);self.assertEqual(quality['qubits'],10)
            self.assertLess(result['diag']['first_valid']['wall'],result['time'])
            self.assertEqual(result['diag']['latest_certified']['Q'],10)
            self.assertGreater(len(result['diag']['visits']),0)
            RECORDS.append(dict(check='public_tiny_branched_constructor',entrypoint=fn.__name__,
                                independently_valid=good,Q=quality['qubits'],wall=result['time']))
        smallG=nx.Graph([(9,-4)]);smallH=nx.Graph([(101,87),(87,-3)])
        class FinalExpired(c._Budget):
            def check(self):
                if self.phase=='final_validation_output':raise c._Deadline('injected final boundary')
                super().check()
        with patch.object(c,'_Budget',FinalExpired):
            PUBLIC_CALLS+=1;late=c.joint_star_construction_embed(smallG,smallH,seed=0,timeout=30.)
        self.assertEqual(late['status'],'TIMEOUT');self.assertFalse(late['embedding']);self.assertIsNotNone(late['diag']['first_valid'])
        original=c._run
        def postvalid_error(e):
            original(e);self.assertIsNotNone(e.incumbent)
            raise ValueError('injected post-first-valid runtime failure')
        with patch.object(c,'_run',postvalid_error):
            PUBLIC_CALLS+=1;failed=c.joint_star_construction_embed(smallG,smallH,seed=0,timeout=30.)
        self.assertEqual(failed['status'],'ERROR');self.assertTrue(failed['diag']['fatal_error'])
        self.assertFalse(failed['embedding']);self.assertNotIn('diagnostic_embedding',failed)
        self.assertEqual(failed['error'],'ValueError: injected post-first-valid runtime failure')
        RECORDS.append(dict(check='final_deadline_and_postvalid_error',deadline_status=late['status'],error_status=failed['status']))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    started,cpu=time.perf_counter(),time.process_time()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NewRisks))
    record=dict(status='PASS' if result.wasSuccessful() and not ATTEMPTS else 'FAIL',
        focused_check_groups=1,test_cases=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        prohibited_attempts=ATTEMPTS,public_tiny_constructor_calls=PUBLIC_CALLS,development_constructor_calls=0,
        records=RECORDS,versions={x:importlib.metadata.version(x) for x in ('numpy','numba','llvmlite','networkx')},
        wall=time.perf_counter()-started,cpu=time.process_time()-cpu)
    (args.output/'summary.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('records','versions')}))
    return 0 if record['status']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
