"""C011 budget/clock risks only; no public constructor or repeated C010 suite."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

old = load('_fixed_c010_budget', 'packages/ember-qc/src/ember_qc/algorithms/adaptive_clones.py')
new = load('_wall_c011_budget', 'packages/ember-qc/src/ember_qc/algorithms/wall_adaptive_clones.py')


def public(s):
    return copy.deepcopy((s.owners,s.aux,s.placement,s.timestamps,s.used,s.serial,s.generation,s.internal_count))


def state(src, target, clock):
    return new._State(src,target,new._Budget(1.,limit=19_000_000,clock=clock))


class WallBudgetChecks(unittest.TestCase):
    def test_budget_and_first_crossings(self):
        a = old._Budget(100.,limit=19_000_000,clock=lambda:0.)
        b = new._Budget(100.,limit=19_000_000,clock=lambda:0.)
        for amount in (1,255,19_000_000-256):
            a.tick('same',amount); b.tick('same',amount)
            self.assertEqual((a.units,a.work,a.next_check),(b.units,b.work,b.next_check))
        self.assertEqual(b.first_crossings,{})
        with self.assertRaises(old._Stop): a.tick('beyond',1)
        b.tick('beyond',1)
        self.assertEqual(a.units,19_000_000)
        self.assertEqual(b.units,19_000_001)
        event = b.first_crossings['search_reference_19M']
        self.assertEqual((event['units_before'],event['requested'],event['units_after'],event['phase']),
                         (19_000_000,1,19_000_001,'search'))
        b.limit = 20_000_000
        b.tick('final',1_000_000)
        total = b.first_crossings['cumulative_20M']
        self.assertEqual((total['units_before'],total['requested'],total['units_after'],total['phase']),
                         (19_000_001,1_000_000,20_000_001,'final'))
        prior = copy.deepcopy(b.first_crossings)
        b.tick('later',20_000_000)
        self.assertEqual(b.first_crossings,prior)
        self.assertEqual(sum(b.work.values()),b.units)
        self.assertIsNone(b.denied)
        jump = new._Budget(1.,limit=19_000_000,clock=lambda:0.)
        jump.tick('jump',20_000_001)
        self.assertEqual(len(jump.first_crossings),2)
        self.assertTrue(all(v['units_before']==0 and v['units_after']==20_000_001 for v in jump.first_crossings.values()))

    def test_clock_and_private_rollback_after_crossing(self):
        now = [0.]
        b = new._Budget(1.,limit=19_000_000,clock=lambda:now[0])
        b.tick('beyond',20_000_001)
        before = (b.units,dict(b.work),copy.deepcopy(b.first_crossings))
        now[0] = 2.
        with self.assertRaisesRegex(new._Stop,'deadline'): b.tick('late',256)
        self.assertEqual((b.units,dict(b.work),b.first_crossings),before)
        # Clock denial before a threshold crossing creates no false crossing event.
        early = new._Budget(1.,clock=lambda:now[0])
        with self.assertRaises(new._Stop): early.tick('late',20_000_001)
        self.assertEqual((early.units,early.first_crossings),(0,{}))
        now[0] = 0.
        s = state(((1,),(0,2),(1,)),((1,),(0,2),(1,3),(2,4),(3,)),lambda:now[0])
        s.publish_single(0,0); s.publish_single(2,4)
        s.b.tick('beyond',20_000_001)
        before = public(s)
        choose, calls = s.choose, [0]
        def crosses(*args,**kwargs):
            result = choose(*args,**kwargs)
            calls[0] += 1
            if calls[0] == 2: now[0] = 2.
            return result
        receipt = {}
        with patch.object(s,'choose',crosses), self.assertRaises(new._Stop):
            s.revise(1,s.domains(1)[1],receipt)
        self.assertEqual(public(s),before)
        self.assertFalse(any(r['committed'] for r in receipt['attempts']))

    def test_final_work_is_allowed_but_late_and_fatal_are_not(self):
        now = [0.]
        s = state(((1,),(0,)),((1,),(0,2),(1,)),lambda:now[0])
        s.publish_single(0,0); s.publish_single(1,1)
        s.b.tick('search_past_old_total',20_000_001)
        s.b.limit = 20_000_000
        good = dict(status='FAILURE',embedding={},diag={})
        new._finish(good,s,['u','v'],['a','b','c'],1.)
        self.assertEqual(good['status'],'SUCCESS')
        self.assertEqual(good['embedding'],{'u':['a'],'v':['b']})
        self.assertGreater(s.b.units,20_000_000)
        self.assertTrue(good['diag']['final']['valid'])
        raw = new._materialize
        def late(*args):
            result = raw(*args); now[0] = 2.; return result
        response = dict(status='FAILURE',embedding={},diag={})
        with patch.object(new,'_materialize',late):
            new._finish(response,s,['u','v'],['a','b','c'],1.)
        self.assertEqual(response['status'],'TIMEOUT')
        self.assertEqual(response['embedding'],{})
        self.assertEqual(response['diagnostic_embedding'],{'u':['a'],'v':['b']})
        now[0] = 0.
        fatal = dict(status='FAILURE',embedding={},diag={})
        new._exception(fatal,ValueError('fatal after old work threshold'))
        new._finish(fatal,s,['u','v'],['a','b','c'],1.)
        self.assertEqual(fatal['status'],'ERROR')
        self.assertEqual(fatal['embedding'],{})
        self.assertTrue(fatal['diag']['final']['valid'])
        self.assertEqual(fatal['error'],'ValueError: fatal after old work threshold')


if __name__ == '__main__': unittest.main()
