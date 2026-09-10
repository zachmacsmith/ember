"""Focused A066 checks: domains versus independent complete-map enumeration."""
import importlib.util
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('a066_check_subject', ROOT/'scripts/codex/a066_pair_diagnostic.py')
d = importlib.util.module_from_spec(spec); sys.modules[spec.name] = d; spec.loader.exec_module(d)


def fixture(kind):
    source = {'nodes': [10, 20, 30, 40], 'edges': [[30,10],[10,20],[20,40]]}
    edges = [[0,1],[0,3],[1,2],[2,4],[5,4],[6,3],[6,5]]
    if kind in ('neutral', 'direct'): edges.append([5,1])
    if kind == 'direct': edges.append([6,2])
    target = {'nodes': list(range(7)), 'edges': edges}
    chains = {10: (0,1), 20: (2,), 30: (3,), 40: (4,)}
    return source, target, chains


class Domains(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle, cls.preparation, cls.guard = d.runtime()

    def run_case(self, kind):
        source, target, chains = fixture(kind)
        G,E = self.oracle.adjacency(source); H,F = self.oracle.adjacency(target)
        meter = d.Meter(time.perf_counter()+5)
        contact = d.boundaries(chains,H,meter)
        free = set(H)-{q for c in chains.values() for q in c}
        row = d.pair_domain(10,20,G,H,chains,free,contact,meter)
        actual = {'assignments':0,'neutral_assignments':0,'simultaneous_assignments':0,'fixed_v_assignments':0}
        for p in H:
            for q in H:
                raw = d.modified(chains,{10:[p],20:[q]})
                valid,_,_ = self.oracle.embedding_quality(raw,G,E,H,F)
                if not valid: continue
                actual['assignments'] += 1
                if q == 2: actual['fixed_v_assignments'] += 1
                else:
                    valid,_,_ = self.oracle.embedding_quality(d.modified(chains,{20:[q]}),G,E,H,F)
                    actual['neutral_assignments' if valid else 'simultaneous_assignments'] += 1
        for key,value in actual.items(): self.assertEqual(row[key],value,(kind,key))
        d.certify_witnesses(row,chains,G,E,H,F,self.oracle,meter)
        self.assertEqual(row['direct_domain'],actual['fixed_v_assignments'])
        return row

    def test_exact_domains_direct_neutral_joint_and_occupied_exclusion(self):
        direct,neutral,joint = [self.run_case(k) for k in ('direct','neutral','joint')]
        self.assertGreater(direct['direct_domain'],0)
        self.assertTrue(neutral['neutral_bridge_requires_relocation'])
        self.assertFalse(neutral['joint_release_only'])
        self.assertEqual(neutral['direct_domain'],0)
        self.assertTrue(joint['joint_release_only'])
        self.assertEqual(joint['neutral_assignments'],0)
        # Exhaustive oracle includes occupied sites 3/4 and absent physical edges.
        self.assertTrue(all(w['u'] not in (3,4) and w['v'] not in (3,4)
            for row in (direct,neutral,joint) for w in row['witnesses'].values()))

    def test_unchanged_preparation_zero_donor_attribution(self):
        source,target,chains = fixture('neutral')
        G,_ = self.oracle.adjacency(source); H,_ = self.oracle.adjacency(target)
        m = self.preparation._Meter(time.perf_counter()+5)
        c = self.preparation._Context(G,H,0,None,m)
        bundle = c.bundle(c.read_entry(chains))
        record = {}; reduced,removed,_,_ = c.prepare(bundle,c.vindex[10],record)
        self.assertEqual(record['stem_sites'],0)
        self.assertTrue(all(not sites for sites in removed.values()))
        self.assertEqual(sum(map(len,reduced.values())),2)

    def test_interruption_never_becomes_negative_or_certified_intermediate(self):
        source,target,chains = fixture('neutral')
        G,E = self.oracle.adjacency(source); H,F = self.oracle.adjacency(target)
        expired = d.Meter(time.perf_counter()-1)
        with self.assertRaises(d.Deadline): d.boundaries(chains,H,expired)
        meter = d.Meter(time.perf_counter()+5)
        row = {'owner_u':10,'owner_v':20,'witnesses':{'neutral':{'u':6,'v':5}}}
        oracle = self.oracle
        class InterruptSecondCertificate:
            def __init__(self): self.calls=0
            def embedding_quality(self,*args):
                self.calls += 1
                if self.calls == 2: raise d.Deadline('validation')
                return oracle.embedding_quality(*args)
        with self.assertRaises(d.Deadline):
            d.certify_witnesses(row,chains,G,E,H,F,InterruptSecondCertificate(),meter)
        self.assertTrue(row['witnesses']['neutral']['final_valid'])
        self.assertNotIn('intermediate_valid',row['witnesses']['neutral'])
        self.assertEqual(self.guard.attempts,[])


if __name__ == '__main__': unittest.main(verbosity=2)
