"""Targeted B019 state/budget checks; no full-constructor calls in this file."""
import copy
import importlib.util
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/movable_contact_construction.py'
spec = importlib.util.spec_from_file_location('b019', SOURCE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def adj(nodes, edges):
    result = {u: [] for u in nodes}
    for u,v in edges:result[u].append(v);result[v].append(u)
    return {u:tuple(vs) for u,vs in result.items()}

def fixture(S,H,E,links):
    meter = m._Meter(time.perf_counter()+5)
    ctx = m._Context(S,H,meter,0)
    trees = {u:m._tree(set(c),ctx.adj,ctx.rank,meter) for u,c in E.items()}
    state = ctx.state(trees,links)
    return ctx,state

def small():
    return fixture({0:(1,),1:(0,)},{0:(1,),1:(0,2),2:(1,)},{0:[0],1:[1,2]},{(0,1):(0,1)})

def actual(state):
    owners = {}
    for u,tree in state.trees.items():
        for q in tree:owners.setdefault(q,set()).add(u)
    Q = sum(len(c) for c in state.trees.values())
    O = sum(len(us)-1 for us in owners.values())
    E = Q+sum(state.prices.get(q,1)*(len(us)-1) for q,us in owners.items())
    h = {u:sum(len(owners[q])-1 for q in tree) for u,tree in state.trees.items()}
    return owners,Q,O,E,h

def plain(value):return json.loads(json.dumps(value))

class ConstructionChecks(unittest.TestCase):
    def test_frozen_b018_nonbinding_proposal_equivalence(self):
        base=ROOT/'results/codex/track-b018-contacts'
        for case in json.loads((base/'inputs.json').read_text())['cases']:
            saved=json.loads((base/'attempt002-cases'/(case['name']+'.json')).read_text())
            ctx,state=fixture(adj(case['source_nodes'],case['source_edges']),adj(case['target_nodes'],case['target_edges']),
                              dict(case['embedding']),{tuple(e):tuple(p) for e,p in case['witnesses']})
            before=copy.deepcopy(state.__dict__)
            proposal,record=ctx.query(state,[tuple(e) for e in case['changed_edges']])
            self.assertEqual(plain(record['pools']),saved['info']['pools'])
            self.assertEqual([r.get('score') for r in record['combinations']],
                             [r.get('score') for r in saved['info']['combinations']])
            self.assertEqual(record.get('best_combination'),saved['info'].get('best_combination'))
            if saved['proposal'] is None:self.assertIsNone(proposal)
            else:
                self.assertEqual({u:sorted(c,key=ctx.rank.__getitem__) for u,c in proposal.trees.items()},
                                 dict(saved['proposal']['embedding']))
            self.assertEqual(state.__dict__,before)

    def test_weighted_deltas_and_outside_owner_conflict_updates(self):
        ctx,state=fixture({0:(1,),1:(0,),2:()},adj(range(4),[(0,1),(1,2),(2,3)]),
                          {0:[0,1],1:[2],2:[1]},{(0,1):(1,2)})
        state=state.replace(prices={1:4,3:7},E=8)
        before=copy.deepcopy(state.__dict__)
        replacement={0:{3:set()}}; links={(0,1):(3,2)}
        ctx.certify_patch(state,replacement,links)
        score=ctx.delta(state,replacement)
        self.assertEqual(score,dict(qubits=3,overlap=0,energy=3))
        new=ctx.prepare_commit(state,replacement,links,score)
        owners,Q,O,E,h=actual(new)
        self.assertEqual((new.owners,new.Q,new.O,new.E,new.h),(owners,Q,O,E,h))
        self.assertEqual(state.h[2],1);self.assertEqual(new.h[2],0)
        self.assertEqual(state.__dict__,before)

    def test_exact_distance_early_stop_keeps_outside_paths(self):
        H=adj(range(5),[(0,1),(1,2),(0,3),(3,4),(4,2)])
        rank={q:q for q in H}
        class Overlay:
            def has_other(self,q,u):return q==1
        meter=m._Meter(time.perf_counter()+5)
        short,parent=m._distances({0:set()},0,Overlay(),H,rank,meter,{1:10},{2})
        full,_=m._distances({0:set()},0,Overlay(),H,rank,meter,{1:10},set(H))
        self.assertEqual(short[2],3);self.assertEqual(short[2],full[2])
        self.assertEqual((parent[2],parent[4],parent[3]),(4,3,0))

    def test_query_offsets_exact_last_unit_and_rollback(self):
        ctx,state=small();start=ctx.m.work
        proposed,record=ctx.query(state,[(0,1)])
        self.assertIsNotNone(proposed)
        used=record['work'];self.assertEqual(ctx.m.work,start+used)
        for limit,expected in [(used,True),(used-1,False)]:
            ctx,state=small();before=copy.deepcopy(state.__dict__);start=ctx.m.work
            ctx.m.query_limit=limit
            proposed,row=ctx.query(state,[(0,1)])
            self.assertEqual(proposed is not None,expected)
            self.assertEqual(ctx.m.work,start+row['work'])
            self.assertEqual(row['work'],limit)
            self.assertEqual(state.__dict__,before)
            if not expected:self.assertEqual(row['status'],'query_work_limit')

    def test_failed_commit_keeps_entry_and_records_all_query_work(self):
        ctx,state=small();before=copy.deepcopy(state.__dict__);start=ctx.m.work
        def failed(*args):
            ctx.m.step();ctx.m.step();raise RuntimeError('forced commit preparation failure')
        with patch.object(ctx,'prepare_commit',side_effect=failed):
            proposed,row=ctx.query(state,[(0,1)])
        self.assertIsNone(proposed);self.assertEqual(row['status'],'query_error')
        self.assertIn('best_combination',row)
        self.assertEqual(row['work'],ctx.m.work-start)
        self.assertEqual(state.__dict__,before)

    def test_isolate_prefix_survives_later_interruption(self):
        ctx,state=fixture({0:(),1:(),2:()},adj(range(4),[(0,1),(1,2),(2,3)]),
                          {0:[0],1:[0],2:[0]}, {})
        before=copy.deepcopy(state.__dict__);records=[]
        iterator=ctx.relocate_isolates(state,records)
        first=next(iterator);saved=copy.deepcopy(first.__dict__)
        self.assertEqual(first.O,1);self.assertEqual(len(records),1)
        ctx.m.limit=ctx.m.work
        with self.assertRaises(m._Stop):next(iterator)
        self.assertEqual(first.__dict__,saved)
        self.assertEqual(state.__dict__,before)
        self.assertEqual((first.owners,first.Q,first.O,first.E,first.h),actual(first))

    def test_shared_final_reserve_and_original_edge_validation(self):
        meter=m._Meter(time.perf_counter()+5,limit=2)
        meter.step();meter.step()
        with self.assertRaisesRegex(m._Stop,'search_work_limit'):meter.step()
        meter.stage='finalize';meter.limit=4
        meter.step();meter.step();self.assertEqual(meter.work,4)
        self.assertEqual(sum(meter.counts.values()),4)
        with patch.object(m,'perf_counter',return_value=meter.deadline):
            with self.assertRaisesRegex(m._Stop,'final_deadline'):meter.clock()
        ctx,state=small()
        self.assertIsNone(ctx.full_minor(state.replace(links={(0,1):(999,998)})))
        bad=state.replace(trees={0:{0:set()},1:{0:set()}},O=0)
        self.assertEqual(ctx.full_minor(bad),'membership_or_overlap')

    def test_query_return_deadline_discards_completed_best(self):
        ctx,state=small();before=copy.deepcopy(state.__dict__)
        clock=[0.0];ctx.m.deadline=5.0
        original=ctx.prepare_commit
        def delayed(*args):
            new=original(*args);clock[0]=5.1;return new
        with patch.object(m,'perf_counter',side_effect=lambda:clock[0]),patch.object(ctx,'prepare_commit',side_effect=delayed):
            proposed,row=ctx.query(state,[(0,1)])
        self.assertIsNone(proposed);self.assertEqual(row['status'],'search_deadline')
        self.assertIn('best_combination',row)
        self.assertAlmostEqual(row['deadline_overrun'],.1)
        self.assertEqual(state.__dict__,before)

    def test_snapshot_prices_and_materialization_are_metered(self):
        ctx,state=small();state=state.replace(prices={1:7})
        before=ctx.m.work;out={};ctx.snapshot(state,out)
        self.assertEqual(out['prices'],{1:7});self.assertTrue(out['complete'])
        self.assertEqual(ctx.m.work-before,5)  # Three sites, one witness, one price.


if __name__=='__main__':unittest.main()
