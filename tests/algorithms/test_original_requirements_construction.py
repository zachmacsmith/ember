"""A051 original-only requirements and literal-loss-of-guidance checks."""
import copy
import time
import unittest
from unittest.mock import patch

import networkx as nx
from ember_qc.algorithms.factored import original_requirements_construction as rc
from ember_qc.algorithms.factored import reduced_reinsertion_construction as ancestor


def valid(chains,source,target):
    if set(chains)!=set(source):return False
    used=set()
    for c in chains.values():
        if not c or len(c)!=len(set(c)) or used.intersection(c) or not set(c)<=set(target):return False
        used.update(c)
        if not nx.is_connected(target.subgraph(c)):return False
    return all(any(q in target[p] for p in chains[a] for q in chains[b]) for a,b in source.edges())


class OriginalRequirementsChecks(unittest.TestCase):
    def test_subdivided_edge_core_arguments_have_no_synthetic_contact(self):
        source=nx.complete_graph(5);source.remove_edge(0,1);source.add_edges_from([(0,5),(5,1)])
        calls=[];observed=[];real=rc._Expansion.insert
        def core(s,t,**kw):
            calls.append((s.copy(),kw));return dict(status='SUCCESS',embedding={v:[v] for v in s},diag={})
        def insert(e,v,chains,frozen=frozenset()):
            self.assertEqual({u:set(ws) for u,ws in e.source.items()},{u:set(source[u]) for u in source})
            observed.append((v,sorted(w for w in source[v] if w in chains)))
            return real(e,v,chains,frozen)
        with patch.object(rc,'_native_embed',side_effect=core),patch.object(rc._Expansion,'insert',insert):
            result=rc.reduced_core_embed(source,source.copy(),timeout=5)
        self.assertEqual(result['status'],'SUCCESS',result['diag']);self.assertTrue(valid(result['embedding'],source,source))
        self.assertEqual(len(calls),1);self.assertEqual(set(calls[0][0]),set(range(5)))
        self.assertFalse(calls[0][0].has_edge(0,1));self.assertEqual(calls[0][0].number_of_edges(),9)
        self.assertEqual(result['diag']['ordering_core_edges'],10)
        self.assertEqual(observed,[(5,[0,1])]);self.assertEqual(result['diag']['committed_updates'][0]['removed_fill'],[])
        self.assertEqual(result['diag']['physical_fill_edges'],0)
        self.assertEqual(result['diag']['committed_updates'][0]['released_fill_qubits_pruned'],0)
        self.assertEqual(calls[0][1]['vacancy_refinement'],'cyclic')

    def test_original_edgeless_core_places_all_survivors_without_reduction(self):
        original=nx.complete_graph(5);source=nx.Graph();source.add_nodes_from(original)
        for i,(a,b) in enumerate(original.edges()):source.add_edges_from([(a,5+i),(5+i,b)])
        with patch.object(rc,'_native_embed',side_effect=AssertionError('edgeless original core invoked native')):
            result=rc.reduced_core_embed(source,nx.complete_graph(24),timeout=5)
        d=result['diag'];self.assertEqual(result['status'],'SUCCESS',d)
        self.assertEqual((d['core_nodes'],d['core_edges'],d['ordering_core_edges'],d['core_calls']),(5,0,10,0))
        self.assertEqual(len(d['anchors']),1);self.assertEqual(d['anchors_placed'],5)
        self.assertTrue(valid(result['embedding'],source,nx.complete_graph(24)))

    def test_nested_fill_bound_immutable_graph_and_original_partial_requirements(self):
        source=nx.wheel_graph(9);target=nx.complete_graph(20);before=(nx.to_dict_of_lists(source),nx.to_dict_of_lists(target))
        observed=[];real=rc._Expansion.insert
        def insert(e,v,chains,frozen=frozenset()):
            self.assertEqual({u:set(ws) for u,ws in e.source.items()},{u:set(source[u]) for u in source})
            if not frozen:observed.append((v,len(set(source[v])&set(chains))))
            return real(e,v,chains,frozen)
        with patch.object(rc._Expansion,'insert',insert):result=rc.reduced_core_embed(source,target,timeout=5)
        self.assertEqual(result['status'],'SUCCESS',result['diag']);self.assertTrue(valid(result['embedding'],source,target))
        self.assertTrue(all(n<=3 for v,n in observed));self.assertGreater(result['diag']['fill_edges'],0)
        self.assertEqual(sum(n==0 for v,n in observed),result['diag']['zero_placed_neighbor_insertions'])
        self.assertEqual(before,(nx.to_dict_of_lists(source),nx.to_dict_of_lists(target)))
        self.assertEqual(result['diag']['partial_requirements'],{u:sorted(source[u]) for u in source})
        self.assertTrue(all(r['removed_fill']==[] for r in result['diag']['committed_updates']))

    def test_no_fill_star_preserves_ancestor_choices(self):
        source=nx.star_graph(7);target=nx.complete_graph(20)
        a=ancestor.reduced_core_embed(source,target,timeout=5);b=rc.reduced_core_embed(source,target,timeout=5)
        self.assertEqual((a['status'],b['status']),('SUCCESS','SUCCESS'))
        self.assertEqual(a['embedding'],b['embedding']);self.assertEqual(a['diag']['journal'],b['diag']['journal'])
        self.assertEqual(a['diag']['fill_edges'],0);self.assertEqual(b['diag']['fill_edges'],0)
        self.assertEqual(a['diag']['core_config'],b['diag']['core_config'])

    def test_deadline_retains_original_prefix_and_rejects_late_core(self):
        clock=[0.];real=rc._Expansion.insert;count=[0];source=nx.wheel_graph(9);target=nx.complete_graph(20)
        def delayed(e,*args,**kwargs):
            answer=real(e,*args,**kwargs);count[0]+=1
            if count[0]==2:clock[0]=11.
            return answer
        with patch.object(rc.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(rc._Expansion,'insert',delayed):
            result=rc.reduced_core_embed(source,target,timeout=10)
        d=result['diag'];self.assertEqual(result['status'],'TIMEOUT');self.assertEqual(len(d['committed_updates']),1)
        partial=d['partial_embedding'];expected=source.subgraph(partial)
        self.assertTrue(valid(partial,expected,target));self.assertEqual(d['partial_requirements'],{v:sorted(expected[v]) for v in expected})
        clock[0]=0.
        def core(s,t,**kwargs):clock[0]=11.;return dict(status='SUCCESS',embedding={v:[v] for v in s},diag={})
        with patch.object(rc.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(rc,'_native_embed',side_effect=core):
            result=rc.reduced_core_embed(nx.complete_graph(5),nx.complete_graph(8),timeout=10)
        self.assertEqual(result['status'],'TIMEOUT');self.assertEqual(result['embedding'],{})
        self.assertEqual(result['diag']['core_calls'],1);self.assertEqual(result['diag']['placed_vertices'],0)

if __name__=='__main__':unittest.main()
