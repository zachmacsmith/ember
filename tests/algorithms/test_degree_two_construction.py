"""Fixed contraction/provenance checks; no exhaustive domain or corpus calls."""
from collections import defaultdict
import ast
import copy
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import networkx as nx
from ember_qc.algorithms.factored import degree_two_construction as rc
from ember_qc.algorithms.factored import site_transfer_construction as ancestor


def valid(chains, source, target):
    if set(chains) != set(source): return False
    used=set()
    for chain in chains.values():
        if not chain or len(chain)!=len(set(chain)) or used.intersection(chain):return False
        if not set(chain)<=set(target) or not nx.is_connected(target.subgraph(chain)):return False
        used.update(chain)
    return all(any(q in target[p] for p in chains[a] for q in chains[b]) for a,b in source.edges())


def engine(source):
    info=defaultdict(int,stage='reduction',scans_by_stage={},stopped_by=None)
    return rc._Expansion(source,nx.path_graph(max(1,len(source))),time.perf_counter()+5,0,info)


def compare_direct_contractions(source):
    e=engine(source);original=copy.deepcopy(e.source)
    core,journal,R,anchors=rc._reduce(e)
    work=source.copy()
    for row in journal:
        v=row['vertex'];neighbors=sorted(work[v]);assert neighbors==list(row['neighbors'])
        assert len(neighbors)<=2
        if len(neighbors)==2:
            work=nx.contracted_nodes(work,min(neighbors),v,self_loops=False)
        else:work.remove_node(v)
    assert {v:set(work[v]) for v in work}==core
    for row in reversed(journal):R=rc._trial_requirements(R,row,e)
    assert R=={v:set(source[v]) for v in source}
    assert e.source==original
    return e,core,journal,R,anchors


class DegreeTwoChecks(unittest.TestCase):
    def test_only_two_eligibility_conditions_and_identity_change(self):
        old=Path(ancestor.__file__).read_text();new=Path(rc.__file__).read_text()
        self.assertEqual(old.count('<= 3'),2)
        expected=old.replace('<= 3','<= 2').replace(
            '"""Filled-core expansion with bounded one-site transfers before ordinary insertion.',
            '"""Degree-two filled-core expansion with unchanged bounded one-site transfers.').replace(
            "algorithm='degree_three_core_expansion_site_transfer', version=3, seed=seed,",
            "algorithm='degree_two_core_expansion_site_transfer', version=4, seed=seed,\n                elimination_degree_limit=2,")
        self.assertEqual(new,expected);self.assertEqual(rc.CORE_CONFIG,ancestor.CORE_CONFIG)
        self.assertIs(rc.transfer_site,ancestor.transfer_site)
        self.assertIs(rc.blocked_reinsert,ancestor.blocked_reinsert)

    def test_cycle_suppression_and_triangle_existing_contact(self):
        _,_,cycle,_,_=compare_direct_contractions(nx.cycle_graph(4))
        self.assertEqual(len(cycle[0]['created_fill']),1)
        _,_,triangle,_,_=compare_direct_contractions(nx.complete_graph(3))
        self.assertEqual(triangle[0]['created_fill'],())

    def test_older_shared_fill_released_by_its_own_row(self):
        source=nx.Graph([(0,2),(0,3),(1,2),(1,3)])
        e,core,journal,R,anchors=compare_direct_contractions(source)
        self.assertEqual(anchors,{2});self.assertEqual([r['vertex'] for r in journal[:2]],[0,1])
        self.assertEqual(journal[0]['created_fill'],((2,3),));self.assertEqual(journal[1]['created_fill'],())
        # Reconstruct initial requirements, then reverse only through vertex1.
        required={v:set(core.get(v,())) for v in source}
        for r in journal:
            for w in r['neighbors']:required[r['vertex']].add(w);required[w].add(r['vertex'])
        for r in reversed(journal):
            required=rc._trial_requirements(required,r,e)
            if r['vertex']==1:self.assertIn(3,required[2])
        self.assertNotIn(3,required[2])

    def test_components_isolates_anchors_and_K4_core(self):
        source=nx.disjoint_union(nx.path_graph(4),nx.complete_graph(3));source.add_node(20)
        _,core,_,_,anchors=compare_direct_contractions(source)
        self.assertEqual(set(core),anchors);self.assertEqual(len(anchors),3);self.assertIn(20,anchors)
        _,core,journal,_,_=compare_direct_contractions(nx.complete_graph(4))
        self.assertEqual(len(core),4);self.assertEqual(journal,[])

    def test_deadline_during_reduction_retains_original_input(self):
        source=nx.cycle_graph(8);e=engine(source);saved=copy.deepcopy(e.source)
        scan=e.scan;count=[0];clock=[0.];e.deadline=1.
        def expire():
            scan();count[0]+=1
            if count[0]==3:clock[0]=2.
        with patch.object(rc.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(e,'scan',side_effect=expire):
            with self.assertRaises(rc._Stop):rc._reduce(e)
        self.assertEqual(e.source,saved);self.assertEqual(e.info['stopped_by'],'deadline')

    def test_unchanged_small_constructor_output_and_original_requirements(self):
        source=nx.path_graph(5);target=nx.complete_graph(12)
        a=ancestor.reduced_core_embed(source,target,timeout=5);b=rc.reduced_core_embed(source,target,timeout=5)
        self.assertEqual(a['status'],b['status']);self.assertEqual(b['status'],'SUCCESS')
        self.assertTrue(valid(b['embedding'],source,target));self.assertEqual(a['embedding'],b['embedding'])
        for key in ('journal','committed_updates','partial_requirements','scan_count','core_config'):
            self.assertEqual(a['diag'][key],b['diag'][key])
        self.assertEqual(b['diag']['elimination_degree_limit'],2)


if __name__=='__main__':unittest.main()
