"""Bounded one-guide correctness checks; no corpus or parameter sweep."""
from collections import defaultdict
import copy
import time
import unittest
from unittest.mock import patch

import networkx as nx
from ember_qc.algorithms.factored import soft_guidance_construction as rc
from ember_qc.algorithms.factored import original_requirements_construction as ancestor


def valid(chains,source,target):
    if set(chains)!=set(source):return False
    used=set()
    for c in chains.values():
        if not c or len(c)!=len(set(c)) or used.intersection(c) or not set(c)<=set(target):return False
        used.update(c)
        if not nx.is_connected(target.subgraph(c)):return False
    return all(any(q in target[p] for p in chains[a] for q in chains[b]) for a,b in source.edges())


def engine(source,target,kind=rc):
    info=defaultdict(int,stage='test',scans_by_stage={},stopped_by=None,guidance_records=[])
    e=kind._Expansion(source,target,time.perf_counter()+5,0,info)
    e.virtual_neighbors={}
    return e


class GuidanceChecks(unittest.TestCase):
    def test_zero_original_neighbor_soft_guide_changes_root_without_contact(self):
        source=nx.path_graph(3);target=nx.path_graph(80);entry={0:{0}};before=copy.deepcopy(entry)
        guided=engine(source,target);plain=engine(source,target,ancestor)
        guided.virtual_neighbors={2:(0,)}
        guided.qrank=plain.qrank={q:80-q for q in target}
        a=plain.insert(2,entry);b=guided.insert(2,entry)
        self.assertIsNotNone(a);self.assertIsNotNone(b)
        self.assertEqual(b[2],{2});self.assertGreater(min(a[2]),2)
        # The guide is at0; the new singleton2 does not touch it and is still valid.
        self.assertFalse(any(q in target[p] for p in b[2] for q in b[0]))
        self.assertTrue(valid(b,source.subgraph(b),target));self.assertEqual(entry,before)
        self.assertEqual(guided.source,{v:tuple(source[v]) for v in source})
        self.assertEqual(guided.info['guidance_scans'],1+2*target.number_of_edges())

    def test_no_guide_matches_ancestor_insertion_choices(self):
        for source,target,entry,v in ((nx.path_graph(3),nx.path_graph(6),{0:{1}},1),
                                     (nx.star_graph(3),nx.complete_graph(8),{0:{2}},1)):
            a=engine(source,target,ancestor);b=engine(source,target)
            self.assertEqual(a.insert(v,entry),b.insert(v,entry))
            self.assertEqual(a.scans,b.scans);self.assertEqual(b.info['guidance_calls'],0)
            for key in ('root_branches','path_queries','staged_extension_sites','staged_pruned_sites'):
                self.assertEqual(a.info[key],b.info[key])

    def test_exact_distances_ignore_occupancy_and_are_recomputed(self):
        source=nx.path_graph(4);target=nx.path_graph(9);e=engine(source,target)
        e.virtual_neighbors={3:(0,1)};e.vrank={0:0,1:1,2:2,3:3}
        first={0:{0,1},1:{4},2:{7}};saved=copy.deepcopy(first)
        d=e.guide_distances(3,first)
        expected={q:min(nx.shortest_path_length(target,a,q) for a in first[0]) for q in target}
        self.assertEqual(d,expected);self.assertEqual(first,saved)
        moved={0:{5,6},1:{1},2:{8}};second=e.guide_distances(3,moved)
        self.assertEqual(second,{q:min(nx.shortest_path_length(target,a,q) for a in moved[0]) for q in target})
        self.assertNotEqual(d,second);self.assertEqual(e.info['guidance_calls'],2)
        self.assertEqual(e.info['guidance_scans'],2*(2+2*target.number_of_edges()))
        self.assertEqual([r['guide'] for r in e.info['guidance_records']],[0,0])

    def test_guide_budget_and_deadline_discard_partial_distance(self):
        source=nx.path_graph(3);target=nx.path_graph(12);entry={0:{0}};original=copy.deepcopy(entry)
        e=engine(source,target);e.virtual_neighbors={2:(0,)};e.repair_end=e.scans+3
        before=e.scans
        with self.assertRaises(rc._helpers._RepairLimit):e.guide_distances(2,entry)
        self.assertEqual(e.scans-before,3);self.assertEqual(e.info['guidance_scans'],3)
        self.assertFalse(e.info['guidance_records'][0]['complete']);self.assertTrue(e.info['guidance_records'][0]['inside_repair'])
        self.assertEqual(entry,original)
        e=engine(source,target);e.virtual_neighbors={2:(0,)};e.deadline=10.;clock=[0.];scan=e.scan;calls=[0]
        def delayed():
            scan();calls[0]+=1
            if calls[0]==3:clock[0]=11.
        with patch.object(rc.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(e,'scan',delayed):
            with self.assertRaises(rc._Stop):e.guide_distances(2,entry)
        self.assertFalse(e.info['guidance_records'][0]['complete']);self.assertEqual(e.info['stopped_by'],'deadline')
        self.assertEqual(entry,original)

    def test_edgeless_original_core_forest_and_physical_requirements(self):
        base=nx.complete_graph(5);source=nx.Graph();source.add_nodes_from(base)
        for i,(a,b) in enumerate(base.edges()):source.add_edges_from([(a,5+i),(5+i,b)])
        target=nx.complete_graph(24)
        with patch.object(rc,'_native_embed',side_effect=AssertionError('edgeless core invoked native')):
            result=rc.reduced_core_embed(source,target,timeout=5)
        self.assertEqual(result['status'],'SUCCESS',result['diag']);self.assertTrue(valid(result['embedding'],source,target))
        d=result['diag'];order=d['core_guide_order'];self.assertEqual(set(order),set(range(5)))
        seen=set()
        for v in order:
            guide=d['virtual_neighbors'][v]
            if seen:self.assertEqual(len(guide),1);self.assertIn(guide[0],seen)
            else:self.assertEqual(guide,())
            seen.add(v)
        self.assertEqual(d['anchors_placed'],5);self.assertEqual(d['core_edges'],0);self.assertEqual(d['ordering_core_edges'],10)
        self.assertEqual(sum(x['purpose']=='edgeless_core' for x in d['guidance_records']),4)
        self.assertEqual(d['partial_requirements'],{v:sorted(source[v]) for v in source})
        self.assertEqual(d['guidance_scans'],sum(x['scans'] for x in d['guidance_records']))
        self.assertEqual(d['guidance_total_scans'],d['guidance_scans']+d['guidance_setup_scans'])
        self.assertEqual(sum(d['scans_by_stage'].values()),d['scan_count'])
        self.assertTrue(all(x['removed_fill']==[] for x in d['committed_updates']))

    def test_nonempty_original_core_preserves_single_native_call(self):
        source=nx.complete_graph(5);source.remove_edge(0,1);source.add_edges_from([(0,5),(5,1)]);calls=[]
        def native(s,t,**kw):calls.append(s.copy());return dict(status='SUCCESS',embedding={v:[v] for v in s},diag={})
        with patch.object(rc,'_native_embed',side_effect=native):result=rc.reduced_core_embed(source,source.copy(),timeout=5)
        self.assertEqual(result['status'],'SUCCESS',result['diag']);self.assertEqual(len(calls),1)
        self.assertEqual(set(calls[0]),set(range(5)));self.assertFalse(calls[0].has_edge(0,1))
        self.assertEqual(result['diag']['core_guide_order'],[])
        self.assertTrue(valid(result['embedding'],source,source))

if __name__=='__main__':unittest.main()
