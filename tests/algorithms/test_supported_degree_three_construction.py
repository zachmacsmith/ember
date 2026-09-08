"""Focused source-reduction checks; no corpus, native call or reach suite."""
import ast
import copy
from pathlib import Path
import random
import time
import unittest
from unittest.mock import patch

import networkx as nx
from ember_qc.algorithms.factored import supported_degree_three_construction as rc
from ember_qc.algorithms.factored import site_transfer_construction as ancestor


def activation_graph():
    # 0=v,1=a,2=b,3=x,4=c; three high-degree cliques keep endpoints alive.
    graph=nx.Graph([(0,1),(0,2),(3,1),(3,2),(3,4)])
    for center,tail in ((1,range(5,9)),(2,range(9,13)),(4,range(13,17))):
        clique=[center,*tail]
        graph.add_edges_from((a,b) for i,a in enumerate(clique) for b in clique[i+1:])
    return graph


class Engine:
    def __init__(self, graph, cap=None):
        self.source={v:tuple(sorted(graph[v])) for v in graph}
        shuffled=sorted(graph);random.Random(0).shuffle(shuffled)
        self.vrank={v:i for i,v in enumerate(shuffled)}
        self.info={'journal':[],'stopped_by':None};self.scans=0;self.cap=cap
    def check(self):
        if self.cap is not None and self.scans>=self.cap:
            self.info['stopped_by']='work_limit';raise rc._Stop
    def scan(self):self.check();self.scans+=1


def full_rescan(graph, rank):
    work=graph.copy();anchors={min(c,key=lambda v:(-graph.degree(v),rank[v])) for c in nx.connected_components(graph)}
    journal=[]
    while True:
        allowed=[]
        for v in work:
            if v in anchors:continue
            ns=list(work[v]);d=len(ns)
            if d<=2 or d==3 and work.subgraph(ns).number_of_edges():allowed.append(v)
        if not allowed:break
        v=min(allowed,key=lambda u:(work.degree(u),rank[u],u));ns=sorted(work[v]);fill=[]
        for i,a in enumerate(ns):
            for b in ns[i+1:]:
                if not work.has_edge(a,b):fill.append((a,b));work.add_edge(a,b)
        work.remove_node(v);journal.append(dict(vertex=v,neighbors=tuple(ns),created_fill=tuple(fill)))
    return {v:set(work[v]) for v in work},journal,anchors


def direct_contractions(graph,journal):
    work=graph.copy()
    for row in journal:
        v=row['vertex'];ns=sorted(work[v]);assert ns==list(row['neighbors'])
        if len(ns)<=1:work.remove_node(v)
        elif len(ns)==2:work=nx.contracted_nodes(work,ns[0],v,self_loops=False)
        else:
            edge=next(((a,b) for i,a in enumerate(ns) for b in ns[i+1:] if work.has_edge(a,b)),None)
            assert edge is not None
            c=next(w for w in ns if w not in edge)
            work=nx.contracted_nodes(work,c,v,self_loops=False)
    return {v:set(work[v]) for v in work}


class SupportedDegreeThreeChecks(unittest.TestCase):
    def test_only_reduction_and_identity_change(self):
        before=Path(ancestor.__file__).read_text();after=Path(rc.__file__).read_text()
        expected=before.replace('"""Filled-core expansion with bounded one-site transfers before ordinary insertion.',
            '"""Supported-degree-three reduction with unchanged A053 transfer expansion.').replace(
            "algorithm='degree_three_core_expansion_site_transfer', version=3, seed=seed,",
            "algorithm='supported_degree_three_core_expansion_site_transfer', version=5, seed=seed,\n                reduction_policy='degree_le_two_or_supported_degree_three',")
        old,new=ast.parse(expected),ast.parse(after)
        ignored={'_reduce','_eligible','_reduction_charge'}
        old.body=[n for n in old.body if not isinstance(n,ast.FunctionDef) or n.name not in ignored]
        new.body=[n for n in new.body if not isinstance(n,ast.FunctionDef) or n.name not in ignored]
        self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))
        self.assertEqual(rc.CORE_CONFIG,ancestor.CORE_CONFIG)
        self.assertIs(rc.transfer_site,ancestor.transfer_site);self.assertIs(rc.blocked_reinsert,ancestor.blocked_reinsert)

    def test_supported_contraction_and_independent_star_rejection(self):
        for graph in (nx.complete_graph(4),nx.wheel_graph(6)):
            e=Engine(graph);core,journal,_,_=rc._reduce(e)
            self.assertTrue(any(len(r['neighbors'])==3 for r in journal))
            self.assertEqual(direct_contractions(graph,journal),core)
        graph=nx.complete_bipartite_graph(3,3);e=Engine(graph)
        core,journal,_,_=rc._reduce(e)
        self.assertEqual(journal,[]);self.assertEqual(core,{v:set(graph[v]) for v in graph})
        e=Engine(nx.star_graph(3));e.info['reduction_detail']={'work':{},'degree3_rejections':0}
        self.assertFalse(rc._eligible(e,{v:set(ns) for v,ns in e.source.items()},set(),0))

    def test_nonlocal_activation_and_older_fill_provenance(self):
        graph=activation_graph();self.assertEqual((len(graph),graph.number_of_edges()),(17,35))
        e=Engine(graph);original=copy.deepcopy(e.source)
        core,journal,required,anchors=rc._reduce(e)
        expected,journal_oracle,anchors_oracle=full_rescan(graph,e.vrank)
        self.assertEqual((core,journal,anchors),(expected,journal_oracle,anchors_oracle))
        self.assertEqual([r['vertex'] for r in journal],[0,3])
        self.assertEqual(journal[0]['created_fill'],((1,2),))
        self.assertEqual(journal[1]['created_fill'],((1,4),(2,4)))
        self.assertEqual(e.info['reduction_detail']['nonlocal_activations'],1)
        self.assertEqual(direct_contractions(graph,journal),core)
        required=rc._trial_requirements(required,journal[1],e)
        self.assertIn(2,required[1])
        required=rc._trial_requirements(required,journal[0],e)
        self.assertEqual(required,{v:set(ns) for v,ns in original.items()});self.assertEqual(e.source,original)

    def test_full_rescan_order_on_fixed_small_graphs(self):
        graphs=[nx.cycle_graph(4),nx.complete_graph(5),nx.wheel_graph(8),
                nx.disjoint_union(nx.path_graph(4),nx.complete_graph(4))]
        graphs[-1].add_node(99)
        for graph in graphs:
            e=Engine(graph);core,journal,required,anchors=rc._reduce(e)
            expected,ordered,protected=full_rescan(graph,e.vrank)
            self.assertEqual((core,journal,anchors),(expected,ordered,protected))
            self.assertEqual(direct_contractions(graph,journal),core)
            for row in reversed(journal):required=rc._trial_requirements(required,row,e)
            self.assertEqual(required,{v:set(graph[v]) for v in graph})

    def test_work_interruption_preserves_completed_prefix_and_charges_once(self):
        graph=activation_graph();probe=Engine(graph);first_common=[];charge=rc._reduction_charge
        def capture(e,key):
            if key=='common_neighbor_scans' and not first_common:first_common.append(e.scans)
            charge(e,key)
        with patch.object(rc,'_reduction_charge',side_effect=capture):rc._reduce(probe)
        self.assertTrue(first_common)
        for cap in (1,first_common[0]+1):
            e=Engine(graph,cap);original=copy.deepcopy(e.source)
            with self.assertRaises(rc._Stop):rc._reduce(e)
            self.assertEqual(e.scans,cap);self.assertEqual(e.source,original)
            d=e.info['reduction_detail'];self.assertFalse(d['complete'])
            self.assertLessEqual(sum(d['work'].values()),e.scans)
            if cap>1:
                self.assertEqual([r['vertex'] for r in e.info['journal']],[0])
                self.assertEqual(d['stage'],'affected_update')
                direct_contractions(graph,e.info['journal'])

    def test_mid_update_deadline_never_admits_partial_core(self):
        source=activation_graph();target=nx.path_graph(24)
        saved=copy.deepcopy(source);clock=[0.];charge=rc._reduction_charge;expired=[]
        def expire(engine,key):
            charge(engine,key)
            if key=='common_neighbor_scans' and not expired:
                expired.append(engine.scans);clock[0]=2.
        with patch.object(rc.time,'perf_counter',side_effect=lambda:clock[0]),\
             patch.object(rc,'_reduction_charge',side_effect=expire),\
             patch.object(rc,'_native_embed',side_effect=AssertionError('partial core admitted')) as native:
            result=rc.reduced_core_embed(source,target,timeout=1)
        self.assertTrue(expired);self.assertEqual(native.call_count,0)
        self.assertEqual(result['status'],'TIMEOUT');self.assertEqual(result['embedding'],{})
        d=result['diag'];self.assertFalse(d['reduction_detail']['complete'])
        self.assertEqual([r['vertex'] for r in d['journal']],[0])
        self.assertNotIn('core_nodes',d);self.assertEqual(d['core_calls'],0)
        self.assertEqual(d['partial_embedding'],{});self.assertEqual(d['stopped_by'],'deadline')
        self.assertEqual(d['scan_count'],sum(d['scans_by_stage'].values()))
        self.assertEqual(dict(source.adj),dict(saved.adj))


if __name__=='__main__':unittest.main()
