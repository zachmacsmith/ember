"""Four focused compound-integration risk groups; no full constructor/corpus call."""
import importlib.util
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'packages/ember-qc/src/ember_qc/algorithms'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


c = load('compound_check_candidate', BASE/'compound_regions.py')
a = load('compound_check_control', BASE/'atomic_regions.py')


def adjacency(n, edges):
    answer = [set() for _ in range(n)]
    for u,v in edges: answer[u].add(v);answer[v].add(u)
    return [tuple(sorted(row)) for row in answer]


def fixture(kind='normal'):
    source_edges=[(0,1),(1,2),(0,2)]
    target_edges=[(0,2),(1,2),(2,3),(2,4),(3,4),(1,5),(3,5)]
    regions=[{0},{1,2,3},{4}]
    n=6
    if kind=='inflated':
        source_edges.extend([(0,3),(1,4),(1,5)])
        target_edges.extend([(0,6),(1,7),(3,8)])
        regions.extend([{6},{7},{8}]);n=9
    elif kind=='lost':
        source_edges.append((1,3));target_edges.append((2,6));regions.append({6});n=7
    elif kind=='ordinary_fallback':
        target_edges.extend([(6,7),(0,7),(4,7)]);regions.append({6,7});n=8
    return regions,adjacency(len(regions),source_edges),adjacency(n,target_edges)


def make(parts, module=c):
    regions,source,target=parts
    base=module._atomic._elementary if module is c else module._elementary
    meter=base._Meter(time.perf_counter()+30.,{'stage_wall':{}})
    return module._State([set(r) for r in regions],source,target,meter)


def snapshot(s):
    return ([set(r) for r in s.regions],list(s.owner),[list(r) for r in s.count],list(s.missing),
            dict(s.position),list(s.version),s.q)


def recount(s):
    owners={};counts=[[0]*s.n for _ in range(s.n)]
    for u,region in enumerate(s.regions):
        assert region
        reached=set();todo=[min(region)]
        while todo:
            q=todo.pop()
            if q in reached:continue
            reached.add(q);todo.extend(p for p in s.adj[q] if p in region and p not in reached)
        assert reached==region
        for q in region:assert q not in owners;owners[q]=u
    for q,u in owners.items():
        for p in s.adj[q]:
            v=owners.get(p,-1)
            if q<p and v>=0 and u!=v:counts[u][v]+=1;counts[v][u]+=1
    assert counts==s.count
    assert {e for e in s.edges if not counts[e[0]][e[1]]}==set(s.missing)
    assert len(owners)==s.q
    return len(s.missing),s.q


def stage(s):
    row={'eligible':False,'certified':False,'committed':False}
    budget=c._Budget(s.meter,row)
    found=c._screen(s,0,2,2,budget,row)
    if found is None:return None,row,budget
    local,parts=found
    if not local.bridge(parts,row):return None,row,budget
    required=local.compensate(row)
    if required is None:return None,row,budget
    proposal=local.certify((0,2),required,row);budget.finish()
    return proposal,row,budget


class IdentityRng:
    def randrange(self,n):return 0
    def shuffle(self,values):pass


class CompoundChecks(unittest.TestCase):
    def test_1_compensated_delta_private_state_and_both_geometry_caches(self):
        s=make(fixture());before=snapshot(s)
        caches=[s.distance(u) for u in (0,1)]
        proposal,row,budget=stage(s)
        self.assertIsNotNone(proposal);self.assertEqual(snapshot(s),before)
        self.assertEqual((proposal.dm,proposal.dq),(-1,0))
        self.assertEqual(row['path'],[5]);self.assertEqual(row['removed_sites'],1)
        s.transfer(2,0,proposal)
        self.assertEqual(recount(s),(0,5));self.assertEqual(s.version,[1,1,0])
        for u in (0,1):self.assertIsNot(s.distance(u),caches[u])
        self.assertEqual(s.distance(0)[2],0);self.assertGreater(s.distance(1)[2],0)
        self.assertTrue(row['committed']);self.assertLessEqual(budget.work,25000)

    def test_2_contact_loss_and_failed_compensation_leave_entry_unchanged(self):
        for kind,status in [('lost','lost_contact'),('inflated','inflated')]:
            with self.subTest(kind=kind):
                s=make(fixture(kind));before=snapshot(s)
                proposal,row,_=stage(s)
                self.assertIsNone(proposal);self.assertEqual(snapshot(s),before);recount(s)
                self.assertEqual(row['screened'][0]['status'] if kind=='lost' else row['status'],status)
        s=make(fixture());before=snapshot(s)
        # An explicit exhausted allowance cannot examine a 25,001st record.
        budget=c._Budget(s.meter,{})
        budget.tick('synthetic',25000)
        with self.assertRaises(c._Limit):budget.tick('synthetic',1)
        self.assertEqual(budget.work,25000);self.assertEqual(snapshot(s),before)

    def test_3_ordinary_rng_replay_and_documented_score_displacement(self):
        parts=([{1},{0},{2}],adjacency(3,[(0,1),(1,2),(0,2)]),adjacency(6,[(0,1),(1,2),(2,3),(3,4),(4,5),(0,5)]))
        for kind in ('swap','transfer','addition','deletion'):
            for seed in range(3):
                with self.subTest(kind=kind,seed=seed):
                    left,right=make(parts),make(parts,a)
                    lr,rr=random.Random(seed),random.Random(seed);ld,rd={},{}
                    l=c._propose(left,kind,lr,left.meter,ld,.25)
                    r=a._propose(right,kind,rr,right.meter,rd,.25)
                    self.assertEqual(ld,rd);self.assertEqual(l,r);self.assertEqual(lr.getstate(),rr.getstate())
                    self.assertEqual(snapshot(left),snapshot(right))
        regions=[{0},{1},{2,3,4}]+[{6+2*i,7+2*i} for i in range(16)]
        te=[(2,3),(3,4),(0,3),(1,3),(2,5),(4,5)]
        for i in range(16):te.extend([(6+2*i,7+2*i),(0,6+2*i),(1,6+2*i)])
        parts=regions,adjacency(19,[(0,1)]),adjacency(38,te)
        left,right=make(parts),make(parts,a);ld,rd={},{}
        chosen=c._propose(left,'transfer',IdentityRng(),left.meter,ld,1/26)
        a._propose(right,'transfer',IdentityRng(),right.meter,rd,1/26)
        self.assertEqual(len(ld['scored']),16);self.assertEqual(len(rd['scored']),16)
        self.assertTrue(ld['scored'][0]['compound']);self.assertIsInstance(chosen[2],c._Proposal)
        self.assertEqual([r['site_or_owner'] for r in ld['scored'][1:]],[r['site_or_owner'] for r in rd['scored'][:15]])
        self.assertNotIn(rd['scored'][-1]['site_or_owner'],[r['site_or_owner'] for r in ld['scored']])

    def test_4_limits_preserve_ordinary_option_and_no_late_publication(self):
        s=make(fixture('ordinary_fallback'));before=snapshot(s);row={}
        with patch.object(c,'_screen',side_effect=c._Limit('forced_local_limit')):
            chosen=c._propose(s,'transfer',IdentityRng(),s.meter,row,1/26)
        self.assertIsNotNone(chosen);self.assertEqual(chosen[1],7)
        self.assertNotIsInstance(chosen[2],c._Proposal);self.assertEqual(snapshot(s),before)
        s=make(fixture());before=snapshot(s);proposal,row,budget=stage(s)
        endpoint=budget.finished;wall=row['wall']
        with patch.object(c.time,'perf_counter',return_value=endpoint+10):budget.finish()
        self.assertEqual(budget.finished,endpoint);self.assertEqual(row['wall'],wall)
        s.meter.deadline=-1
        with self.assertRaises(c._Expired):s.transfer(2,0,proposal)
        self.assertEqual(snapshot(s),before);self.assertFalse(row['committed'])
        s=make(fixture());before=snapshot(s)
        with patch.object(c.time,'perf_counter',return_value=0.):budget=c._Budget(s.meter,{})
        with patch.object(c.time,'perf_counter',return_value=.05):
            with self.assertRaises(c._Limit):budget.check()
        self.assertEqual(snapshot(s),before)
        s=make(fixture());before=snapshot(s);row={};tick=c._Budget.tick
        def interrupt(budget,key,count=1):
            tick(budget,key,count)
            if key=='bridge_vertices':s.meter.deadline=-1;s.meter.check()
        with patch.object(c._Budget,'tick',interrupt):
            with self.assertRaises(c._Expired):c._propose(s,'transfer',IdentityRng(),s.meter,row,1/26)
        self.assertEqual(snapshot(s),before)


if __name__=='__main__':unittest.main(verbosity=2)
