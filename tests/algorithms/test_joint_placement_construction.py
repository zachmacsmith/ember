"""Four targeted B024 placement groups; no public constructor/corpus calls."""
from collections import deque
from copy import deepcopy
import importlib.util
from itertools import permutations
from pathlib import Path
from time import perf_counter
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/joint_placement_construction.py'
spec = importlib.util.spec_from_file_location('b024_candidate', SOURCE)
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)


def graph(vertices, edges):
    g = {u:set() for u in vertices}
    for u,v in edges: g[u].add(v); g[v].add(u)
    return g


def path(n):
    return graph(range(n), [(i,i+1) for i in range(n-1)])


def distances(H, root):
    result={root:0}; queue=deque([root])
    while queue:
        for v in H[queue.popleft()]:
            if v not in result:
                result[v]=1+min(result[w] for w in H[v] if w in result)
                queue.append(v)
    return result


def metric(G, H, assignment):
    D={q:distances(H,q) for q in assignment.values()}
    return sum(D[assignment[u]][assignment[v]] for u in G for v in G[u] if u<v)


def context(G, H, pi):
    ctx=b._Context(G,H,b._Meter(perf_counter()+5),0)
    ctx.install({u:{q} for u,q in pi.items()})
    return ctx


class JointPlacementChecks(unittest.TestCase):
    def test_scrambled_path_exact_cost_and_contact_recount(self):
        G=H=path(4); pi=dict(enumerate([0,2,1,3])); saved=deepcopy((G,H,pi))
        ctx=context(G,H,pi); row={}; ctx.prepare_placement(row)
        actual={u:next(iter(c)) for u,c in ctx.state.chains.items()}
        self.assertEqual((row['entry_distance_cost'],row['final_distance_cost']),(5,3))
        self.assertEqual(metric(G,H,actual),3)
        self.assertEqual(set(actual.values()),set(pi.values()))
        self.assertEqual((ctx.state.Q,ctx.state.O,ctx.state.M),(4,0,0))
        self.assertIsNone(ctx.validate())
        self.assertEqual(row['pairs_visited'],12)
        self.assertEqual(row['passes_completed'],2)
        self.assertTrue(row['complete'] and row['published'])
        self.assertEqual(sum(s['delta'] for s in row['swaps']),-2)
        self.assertEqual(ctx.m.work,sum(ctx.m.units.values()))
        self.assertEqual((G,H,pi),saved)

    def test_complete_source_cost_is_permutation_invariant(self):
        G=graph(range(4),[(u,v) for u in range(4) for v in range(u+1,4)])
        H=path(4); costs={metric(G,H,dict(enumerate(p))) for p in permutations(range(4))}
        self.assertEqual(costs,{10})
        pi=dict(enumerate([0,2,1,3])); ctx=context(G,H,pi); row={}; ctx.prepare_placement(row)
        self.assertEqual(row['entry_assignment'],row['proposed_assignment'])
        self.assertEqual(row['accepted_swaps'],0)
        self.assertEqual(row['entry_distance_cost'],row['final_distance_cost'])
        self.assertEqual(row['pairs_visited'],12)
        self.assertEqual(ctx.state.M,3)

    def test_full_target_distances_and_arbitrary_owner_bookkeeping(self):
        vertices=[-4,2,7,9]; G=graph(vertices,list(zip(vertices,vertices[1:]))); H=path(9)
        pi=dict(zip(vertices,[0,5,3,8])); ctx=context(G,H,pi); row={}; ctx.prepare_placement(row)
        actual=dict(row['proposed_assignment'])
        self.assertEqual((row['entry_distance_cost'],row['final_distance_cost']),(12,8))
        self.assertEqual(metric(G,H,actual),8)
        self.assertEqual(set(actual.values()),{0,3,5,8})
        self.assertEqual((row['entry_missing'],row['proposed_missing']),(3,3))
        self.assertEqual(ctx.state.M,3)
        self.assertTrue(all(len(c)==1 for c in ctx.state.chains.values()))
        self.assertEqual(set(ctx.state.owners),set(pi.values()))
        self.assertGreater(ctx.m.units['placement_distance'],0)
        self.assertGreater(ctx.m.units['placement_recount'],0)

    def test_private_exchange_and_final_clock_interrupt_without_fallback_credit(self):
        G=H=path(4); pi=dict(enumerate([0,2,1,3])); ctx=context(G,H,pi)
        entry=ctx.state; saved=deepcopy(entry.chains); row={}; step=ctx.m.step
        def stop_after_exchange():
            if row.get('swaps'):
                ctx.m.limit=ctx.m.work
            step()
        ctx.m.step=stop_after_exchange
        with self.assertRaisesRegex(b._Stop,'work_limit'): ctx.prepare_placement(row)
        self.assertIs(ctx.state,entry)
        self.assertEqual(ctx.state.chains,saved)
        self.assertTrue(row['swaps'])
        self.assertFalse(row['complete'] or row['published'])
        self.assertLess(row['private_distance_cost'],row['entry_distance_cost'])
        self.assertEqual(ctx.m.work,ctx.m.limit)
        self.assertEqual(row['interrupted_stage'],'placement_optimize')
        # This entry is a valid minor: the inherited final gate must still reject
        # incomplete treatment preparation rather than credit this old BFS map.
        ctx=context(G,H,dict(enumerate(range(4)))); entry=ctx.state; row={}; clock=ctx.m.clock
        def late_after_recount():
            if 'proposed_assignment' in row:
                ctx.m.deadline=perf_counter()-1
            return clock()
        ctx.m.clock=late_after_recount
        with self.assertRaisesRegex(b._Stop,'deadline'): ctx.prepare_placement(row)
        self.assertIs(ctx.state,entry)
        self.assertFalse(row['complete'] or row['published'])
        self.assertEqual(row['interrupted_stage'],'placement_recount')
        ctx.m.clock=clock
        ctx.m.deadline=perf_counter()+2
        self.assertIsNone(ctx.validate())
        info={'error':'placement_not_complete'}
        embedding,status=b._finish(ctx,ctx.m,info,perf_counter()+2)
        self.assertEqual((embedding,status),({},'FAILURE'))


if __name__=='__main__': unittest.main()
