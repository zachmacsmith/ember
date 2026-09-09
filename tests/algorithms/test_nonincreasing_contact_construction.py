"""Four B025 acceptance-only checks; no public constructor or corpus calls."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path
from time import perf_counter
import unittest

ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'packages/ember-qc/src/ember_qc/algorithms/factored/nonincreasing_contact_construction.py'
spec=importlib.util.spec_from_file_location('b025_candidate',path)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def context(length,updates):
    G={0:{1},1:{0}};H={q:set() for q in range(length)}
    for q in range(length-1):H[q].add(q+1);H[q+1].add(q)
    chains={0:{0},1:{length-1}}
    ctx=b._Context(G,H,b._Meter(perf_counter()+5),0);ctx.install(chains)
    for _ in range(updates):ctx.price_edge((0,1))
    return ctx,G,H,chains

def physical_score(ctx,chains):
    counts=Counter(q for chain in chains.values() for q in chain)
    missing=sum(not any(p in ctx.H[q] for q in chains[u] for p in chains[v]) for u,v in ctx.edges)
    Q=sum(map(len,chains.values()));O=sum(n-1 for n in counts.values())
    F=Q+sum(ctx.lam.get(q,1)*(n-1) for q,n in counts.items())
    F+=sum(ctx.mu[(u,v)] for u,v in ctx.edges if not any(p in ctx.H[q] for q in chains[u] for p in chains[v]))
    return dict(qubits=Q,missing=missing,overlap=O,energy=F)

class AcceptanceChecks(unittest.TestCase):
    def assert_receipt(self,ctx,row):
        proposed=dict(ctx.state.chains);p=row['selected_proposal'];proposed[p['owner']]=p['sites']
        self.assertEqual(p['score'],physical_score(ctx,proposed))
        self.assertEqual(ctx.m.work,sum(ctx.m.units.values()))
        self.assertEqual(row['scored'],2)
        self.assertTrue(row['complete'])
        self.assertGreater(ctx.m.units['acceptance'],0)

    def test_strict_improving_winner_publishes(self):
        ctx,G,H,chains=context(4,2);saved=deepcopy((G,H,chains));before=ctx.state.F
        row=ctx.route((0,1));self.assert_receipt(ctx,row)
        self.assertEqual((before,ctx.state.F),(5,4))
        self.assertTrue(row['committed'] and row['acceptance_eligible'])
        self.assertFalse(row['acceptance_rejected'])
        self.assertEqual(ctx.stats['acceptance_rejections'],0)
        self.assertEqual(ctx.state.score(),physical_score(ctx,ctx.state.chains))
        self.assertIsNone(ctx.validate());self.assertEqual((G,H,chains),saved)

    def test_equal_energy_winner_still_changes_contacts(self):
        ctx,*_=context(4,1);row=ctx.route((0,1));self.assert_receipt(ctx,row)
        self.assertTrue(row['committed'])
        self.assertEqual(row['before']['energy'],row['after']['energy'])
        self.assertEqual((row['before']['missing'],row['after']['missing']),(1,0))
        self.assertIsNone(ctx.validate())

    def test_uphill_rejection_retains_applied_price_and_valid_raw_proposal(self):
        ctx,*_=context(5,1);entry=ctx.state;saved=deepcopy(entry.chains)
        row=ctx.route((0,1));self.assert_receipt(ctx,row)
        self.assertEqual((row['acceptance_threshold'],row['selected_proposal']['score']['energy']),(4,5))
        self.assertFalse(row['committed'] or row['acceptance_eligible'])
        self.assertTrue(row['acceptance_rejected'])
        self.assertIs(ctx.state,entry);self.assertEqual(ctx.state.chains,saved)
        self.assertEqual((ctx.mu[(0,1)],ctx.stats['edge_price_updates']),(2,1))
        self.assertEqual((ctx.stats['acceptance_rejections'],ctx.stats['route_acceptance_rejections']),(1,1))
        self.assertEqual(row['discarded_scored'],2)
        self.assertEqual(row['selected_proposal']['score']['missing'],0)
        embedding,status=b._finish(ctx,ctx.m,{'error':None},perf_counter()+2)
        self.assertEqual((embedding,status),({},'FAILURE'))

    def test_interrupted_rejection_is_not_a_completed_rejection(self):
        for stop in ('work','deadline'):
            with self.subTest(stop=stop):
                ctx,*_=context(5,1);entry=ctx.state;saved=deepcopy(entry.chains)
                if stop=='work':
                    original=ctx.m.step
                    def fail_during_recording():
                        if ctx.m.stage=='acceptance':ctx.m.limit=ctx.m.work
                        return original()
                    ctx.m.step=fail_during_recording
                else:
                    original=ctx.m.clock
                    def fail_last_rejection_clock():
                        if ctx.m.stage=='acceptance' and ctx.moves[-1]['selected_proposal'] is not None:
                            raise b._Stop('search_deadline')
                        return original()
                    ctx.m.clock=fail_last_rejection_clock
                with self.assertRaises(b._Stop):ctx.route((0,1))
                row=ctx.moves[-1]
                self.assertFalse(row['complete'] or row['committed'] or row['acceptance_rejected'])
                self.assertIs(ctx.state,entry);self.assertEqual(entry.chains,saved)
                self.assertEqual((ctx.mu[(0,1)],ctx.stats['edge_price_updates']),(2,1))
                self.assertEqual(ctx.stats['acceptance_rejections'],0)
                self.assertEqual(row['discarded_scored'],2)
                self.assertEqual(ctx.m.work,sum(ctx.m.units.values()))
                if stop=='deadline':self.assertFalse(row['acceptance_eligible'])

if __name__=='__main__':unittest.main(verbosity=2)
