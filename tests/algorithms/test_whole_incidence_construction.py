"""B022 focused private-state checks; no public constructor or corpus calls."""
from collections import Counter
import copy
import importlib.util
from itertools import combinations
from pathlib import Path
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/whole_incidence_construction.py'
spec = importlib.util.spec_from_file_location('b022',SOURCE)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def adj(n, edges):
    result = {u:[] for u in range(n)}
    for u,v in edges:
        result[u].append(v); result[v].append(u)
    return {u:tuple(v) for u,v in result.items()}


def fixture(G,H,chains,links):
    meter = m._Meter(time.perf_counter()+5)
    ctx = m._Context(G,H,meter,0)
    trees = {u:m._tree(set(chain),ctx.adj,ctx.rank,meter) for u,chain in chains.items()}
    return ctx,ctx.state(trees,links)


def witness():
    return fixture(adj(4,[(0,1),(1,2),(2,3)]),
        adj(6,[(1,2),(0,2),(3,2),(0,4),(4,5),(5,3)]),
        {0:[0],1:[1,2],2:[2],3:[3]},
        {(0,1):(0,2),(1,2):(1,2),(2,3):(2,3)})


def independent(G,H,chains,prices=None):
    if set(chains)!=set(G) or any(not chain for chain in chains.values()):
        return None
    for chain in chains.values():
        if not set(chain)<=H.keys(): return None
        reached = {next(iter(chain))}; queue = list(reached)
        for q in queue:
            for r in H[q]:
                if r in chain and r not in reached:
                    reached.add(r); queue.append(r)
        if reached!=set(chain): return None
    for u in G:
        for v in G[u]:
            if not any(r in H[q] for q in chains[u] for r in chains[v]): return None
    counts = Counter(q for chain in chains.values() for q in chain)
    Q = sum(counts.values()); O = sum(k-1 for k in counts.values())
    E = Q+sum((prices or {}).get(q,1)*(k-1) for q,k in counts.items())
    return Q,O,E


def actual(state):
    owners = {}
    for u,chain in state.trees.items():
        for q in chain: owners.setdefault(q,set()).add(u)
    h = {u:sum(len(owners[q])-1 for q in chain) for u,chain in state.trees.items()}
    terms = {u:Counter() for u in state.trees}
    for edge,pair in state.links.items():
        for u,q in zip(edge,pair): terms[u][q]+=1
    return owners,h,terms


class WholeIncidenceChecks(unittest.TestCase):
    def test_joint_releases_all_bindings_and_crosses_single_owner_barrier(self):
        ctx,state = witness(); before = copy.deepcopy(state.__dict__)
        for owner in (1,2):
            feasible = []
            for size in range(1,7):
                for subset in combinations(range(6),size):
                    chains = {u:set(tree) for u,tree in state.trees.items()}; chains[owner]=set(subset)
                    score = independent(ctx.G,ctx.H,chains)
                    if score is not None: feasible.append(score[2])
            self.assertEqual(min(feasible),6)
        proposed,row = ctx.query(state,[1,2])
        self.assertIsNotNone(proposed)
        self.assertEqual(row['edges'],[(0,1),(1,2),(2,3)])
        self.assertEqual(independent(ctx.G,ctx.H,proposed.trees),(4,0,4))
        self.assertEqual(set(proposed.trees[1]),{4}); self.assertEqual(set(proposed.trees[2]),{5})
        self.assertEqual(proposed.trees[0],state.trees[0]); self.assertEqual(proposed.trees[3],state.trees[3])
        self.assertEqual((proposed.owners,proposed.h,proposed.terms),actual(proposed))
        self.assertEqual(state.__dict__,before)

    def test_negative_triangle_path_has_no_valid_minor_credit(self):
        ctx,state = fixture(adj(3,[(0,1),(1,2),(0,2)]),adj(3,[(0,1),(1,2)]),
            {0:[0],1:[1],2:[1,2]},{(0,1):(0,1),(0,2):(0,1),(1,2):(1,2)})
        before = copy.deepcopy(state.__dict__)
        proposed,row = ctx.query(state,[0,1])
        self.assertIsNone(proposed)
        self.assertEqual(row['eligible_proposals'],0)
        self.assertNotEqual(independent(ctx.G,ctx.H,state.trees)[1],0)
        self.assertIsNotNone(ctx.full_minor(state.replace(O=0)))
        self.assertEqual(state.__dict__,before)

    def test_outside_terminal_counters_conflicts_and_weighted_energy(self):
        ctx,state = fixture(adj(3,[(0,1),(1,2)]),adj(6,[(0,1),(1,2),(2,3),(0,4),(4,5)]),
            {0:[0,1],1:[1,2],2:[3]},{(0,1):(1,2),(1,2):(2,3)})
        state = state.replace(prices={1:7},E=12); before=copy.deepcopy(state.__dict__)
        rebuilt={1:{4:set()},2:{5:set()}}; links={(0,1):(0,4),(1,2):(4,5)}
        ctx.certify_patch(state,rebuilt,links)
        score=ctx.delta(state,rebuilt); new=ctx.prepare_commit(state,rebuilt,links,score)
        self.assertEqual(score,dict(qubits=4,overlap=0,energy=4))
        self.assertEqual(independent(ctx.G,ctx.H,new.trees,new.prices),(4,0,4))
        self.assertEqual((new.owners,new.h,new.terms),actual(new))
        self.assertEqual(new.terms[0],Counter({0:1}));self.assertEqual(new.h[0],0)
        self.assertEqual(state.__dict__,before)

    def test_internal_path_cuts_preserve_trees_and_contact(self):
        ctx,state = fixture(adj(2,[(0,1)]),adj(4,[(0,1),(1,2),(2,3)]),
            {0:[0,1],1:[2,3]},{(0,1):(1,2)})
        trees={0:{0:set()},1:{3:set()}}; old=Counter(q for tree in state.trees.values() for q in tree)
        record={'routes':[]}; paths=ctx.routes(state,trees,old,0,{3},1,record,internal=True)
        self.assertEqual(paths,[[0,1,2,3]])
        for cut in (0,1,2):
            rebuilt={0:ctx.extend(trees[0],paths[0][:cut+1]),1:ctx.extend(trees[1],paths[0][cut+1:])}
            self.assertEqual(independent(ctx.G,ctx.H,rebuilt),(4,0,4))
        self.assertEqual(trees,{0:{0:set()},1:{3:set()}})

    def test_last_unit_and_interrupted_eligible_best_rollback(self):
        ctx,state=witness(); proposed,row=ctx.query(state,[1,2]); self.assertIsNotNone(proposed); used=row['work']
        for allowance,success in [(used,True),(used-1,False),(1,False)]:
            ctx,state=witness(); before=copy.deepcopy(state.__dict__);start=ctx.m.work;ctx.m.query_limit=allowance
            proposed,row=ctx.query(state,[1,2])
            self.assertEqual(proposed is not None,success)
            self.assertEqual(row['work'],allowance);self.assertEqual(ctx.m.work,start+allowance)
            self.assertEqual(sum(ctx.m.counts.values()),ctx.m.work)
            if allowance==used-1:
                self.assertGreater(row['eligible_proposals'],0)
                self.assertEqual(row['discarded_eligible'],row['eligible_proposals'])
            self.assertEqual(state.__dict__,before)

    def test_common_deadline_after_staging_discards_and_keeps_entry(self):
        ctx,state=witness(); before=copy.deepcopy(state.__dict__);clock=[0.0];ctx.m.deadline=5
        original=ctx.prepare_commit
        def delayed(*args):
            proposal=original(*args);clock[0]=5.1;return proposal
        with patch.object(m,'perf_counter',side_effect=lambda:clock[0]),patch.object(ctx,'prepare_commit',side_effect=delayed):
            proposed,row=ctx.query(state,[1,2])
        self.assertIsNone(proposed);self.assertEqual(row['status'],'search_deadline')
        self.assertGreater(row['discarded_eligible'],0);self.assertAlmostEqual(row['deadline_overrun'],.1)
        self.assertEqual(state.__dict__,before)

    def test_staging_error_and_later_query_do_not_mutate(self):
        ctx,state=witness();before=copy.deepcopy(state.__dict__);start=ctx.m.work
        def failed(*args):
            ctx.m.step();raise RuntimeError('forced cache staging failure')
        with patch.object(ctx,'prepare_commit',side_effect=failed):proposed,row=ctx.query(state,[1,2])
        self.assertIsNone(proposed);self.assertEqual(row['status'],'query_error')
        self.assertGreater(row['discarded_eligible'],0);self.assertEqual(row['work'],ctx.m.work-start)
        self.assertIsNone(ctx.m.query_start);self.assertIsNone(ctx.m.query_deadline)
        self.assertEqual(state.__dict__,before)
        proposed,row=ctx.query(state,[1,2]);self.assertIsNotNone(proposed)
        self.assertEqual(state.__dict__,before)

    def test_feasible_primary_q_requires_strict_reduction(self):
        ctx,state = fixture(adj(2,[(0,1)]),adj(3,[(0,1),(1,2)]),{0:[0],1:[1,2]},{(0,1):(0,1)})
        proposed,row=ctx.query(state,[0,1]);self.assertIsNotNone(proposed)
        self.assertEqual(independent(ctx.G,ctx.H,proposed.trees),(2,0,2))
        again,next_row=ctx.query(proposed,[0,1]);self.assertIsNone(again)
        self.assertEqual(next_row['eligible_proposals'],0)


if __name__=='__main__': unittest.main()
