"""Targeted source-journal and lifting falsifiers; no Ember corpus inputs."""
from collections import defaultdict
import copy
import time
import unittest
from unittest.mock import patch

import networkx as nx
import dwave_networkx as dnx
from ember_qc.algorithms.factored import reduced_core_construction as rc

OBSERVATIONS = {}
FIXTURES = {}


def fixtures():
    if not FIXTURES:
        target = dnx.zephyr_graph(12)
        complete = nx.complete_graph(5)
        subdivided = nx.Graph()
        subdivided.add_nodes_from(complete)
        for i, (a,b) in enumerate(complete.edges()):
            v = 5+i
            subdivided.add_edges_from([(a,v),(v,b)])
        FIXTURES.update(star127=(nx.star_graph(127),target),
                        wheel127=(nx.wheel_graph(128),target),
                        subdivided_k5=(subdivided,target))
    return FIXTURES


def valid(embedding, source, target):
    """Independent direct original-edge oracle, also used for active partial R."""
    if set(embedding) != set(source): return False
    occupied=set()
    for v,chain in embedding.items():
        if not chain or len(chain)!=len(set(chain)):return False
        if not set(chain)<=set(target) or occupied.intersection(chain):return False
        occupied.update(chain)
        if not nx.is_connected(target.subgraph(chain)):return False
    return all(any(q in target[p] for p in embedding[a] for q in embedding[b])
               for a,b in source.edges())


def engine(source,target):
    info=defaultdict(int,stage='test',scans_by_stage={},stopped_by=None)
    return rc._Expansion(source,target,time.perf_counter()+10,0,info)


class ReductionChecks(unittest.TestCase):
    def test_nested_fill_exact_forward_and_reverse_states(self):
        source=nx.wheel_graph(9); target=nx.complete_graph(16)
        e=engine(source,target)
        core,journal,required,anchors=rc._reduce(e)
        self.assertEqual(anchors,{0});self.assertGreater(sum(len(r['created_fill']) for r in journal),2)
        graph=source.copy();before=[]
        for row in journal:
            before.append(graph.copy());v=row['vertex'];neighbors=sorted(graph[v])
            self.assertEqual(list(row['neighbors']),neighbors)
            added=[]
            for i,a in enumerate(neighbors):
                for b in neighbors[i+1:]:
                    if not graph.has_edge(a,b):added.append((a,b));graph.add_edge(a,b)
            self.assertEqual(added,list(row['created_fill']))
            self.assertTrue(all(not source.has_edge(a,b) for a,b in added))
            graph.remove_node(v)
            self.assertLessEqual(graph.number_of_edges(),before[-1].number_of_edges())
        self.assertEqual({v:set(graph[v]) for v in graph},core)
        placed=set(core)
        for row,expected in zip(reversed(journal),reversed(before)):
            required=rc._trial_requirements(required,row,e);placed.add(row['vertex'])
            self.assertEqual({v:set(required[v])&placed for v in placed},
                             {v:set(expected[v]) for v in expected})
        self.assertEqual(required,{v:set(source[v]) for v in source})

    def test_components_isolates_and_input_nonmutation(self):
        source=nx.disjoint_union_all([nx.path_graph(5),nx.empty_graph(2),nx.cycle_graph(4)])
        target=nx.complete_graph(24);before=(copy.deepcopy(source),copy.deepcopy(target))
        with patch.object(rc,'_native_embed',side_effect=AssertionError('edgeless core called native')):
            result=rc.reduced_core_embed(source,target,timeout=5)
        self.assertEqual(result['status'],'SUCCESS',result['diag'])
        self.assertTrue(valid(result['embedding'],source,target))
        self.assertEqual(result['diag']['core_calls'],0)
        self.assertEqual(len(result['diag']['anchors']),4)
        self.assertEqual(nx.to_dict_of_lists(source),nx.to_dict_of_lists(before[0]))
        self.assertEqual(nx.to_dict_of_lists(target),nx.to_dict_of_lists(before[1]))
        empty=rc.reduced_core_embed(nx.Graph(),nx.empty_graph(2))
        self.assertEqual((empty['status'],empty['embedding']),('SUCCESS',{}))

    def test_core_once_fixed_config_and_exact_output_validation(self):
        source,target=nx.complete_graph(5),nx.complete_graph(8);calls=[]
        def core(s,t,**kw):
            calls.append((s.copy(),kw));return dict(status='SUCCESS',embedding={v:[v] for v in s},diag={'fixture':True})
        with patch.object(rc,'_native_embed',side_effect=core):
            result=rc.reduced_core_embed(source,target,timeout=5)
        self.assertEqual(result['status'],'SUCCESS',result['diag']);self.assertEqual(len(calls),1)
        self.assertTrue(valid(result['embedding'],source,target))
        kw=calls[0][1];self.assertEqual(kw['seed'],0);self.assertGreater(kw['timeout'],0)
        self.assertEqual({k:v for k,v in kw.items() if k not in ('seed','timeout')},rc.CORE_CONFIG)
        for bad in ({v:[0] for v in source},{v:[v,v] for v in source},{0:[0]}):
            with patch.object(rc,'_native_embed',return_value=dict(status='SUCCESS',embedding=bad)):
                result=rc.reduced_core_embed(source,target)
            self.assertEqual(result['status'],'FAILURE');self.assertEqual(result['embedding'],{})
            self.assertEqual(result['diag']['stopped_by'],'internal_error')

    def test_late_core_success_is_rejected_by_original_deadline(self):
        clock=[0.]
        def core(s,t,**kw):
            self.assertGreater(kw['timeout'],0);clock[0]=11.
            return dict(status='SUCCESS',embedding={v:[v] for v in s},diag={})
        with patch.object(rc.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(rc,'_native_embed',side_effect=core):
            result=rc.reduced_core_embed(nx.complete_graph(5),nx.complete_graph(8),timeout=10)
        self.assertEqual((result['status'],result['embedding']),('TIMEOUT',{}))
        self.assertEqual(result['diag']['core_calls'],1);self.assertEqual(result['diag']['core_status'],'SUCCESS')
        self.assertEqual(result['diag']['core_wall'],11.);self.assertEqual(result['diag']['deadline_overrun'],1.)
        self.assertEqual(result['diag']['placed_vertices'],0)

    def test_failed_core_keeps_top_level_evidence_without_adoption(self):
        response=dict(status='FAILURE',embedding={},partial_embedding={0:[0]},
                      error='fixture failure',diag={'partial_count':1},time=0.25)
        with patch.object(rc,'_native_embed',return_value=response):
            result=rc.reduced_core_embed(nx.complete_graph(5),nx.complete_graph(8))
        self.assertEqual((result['status'],result['embedding']),('FAILURE',{}))
        self.assertEqual(result['diag']['core_failure'],{k:v for k,v in response.items() if k!='diag'})
        self.assertEqual(result['diag']['core_diag'],response['diag'])
        self.assertEqual(result['diag']['placed_vertices'],0)

    def test_released_fill_prunes_an_unchanged_endpoint_only(self):
        source=nx.Graph([(0,2),(2,1)])
        target=nx.Graph([(0,1),(1,2),(2,3),(3,0)])
        e=engine(source,target);trial={0:{0,1},1:{2},2:{3}};before=copy.deepcopy(trial)
        self.assertTrue(valid(trial,source,target))
        result,saved=rc._prune_released(e,trial,{'created_fill':[(0,1)]})
        self.assertEqual(result,{0:{0},1:{2},2:{3}});self.assertEqual(saved,1)
        self.assertEqual(trial,before);self.assertTrue(valid(result,source,target))

    def test_failed_fill_reversal_does_not_publish_requirements(self):
        source,target=nx.wheel_graph(7),nx.complete_graph(16)
        with patch.object(rc._Expansion,'insert',return_value=None):
            result=rc.reduced_core_embed(source,target)
        self.assertEqual(result['status'],'FAILURE')
        self.assertEqual(result['diag']['stopped_by'],'insertion_blocked')
        partial=result['diag']['partial_embedding'];active=nx.Graph(result['diag']['partial_requirements'])
        self.assertTrue(valid(partial,active,target))
        self.assertEqual(result['diag']['committed_updates'],[])

    def test_deadline_before_commit_retains_prior_partial(self):
        clock=[0.];calls=[];real=rc._Expansion.insert
        def delayed(e,v,current):
            answer=real(e,v,current);calls.append(v)
            if len(calls)==2:clock[0]=11.
            return answer
        with patch.object(rc.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(rc._Expansion,'insert',delayed):
            result=rc.reduced_core_embed(nx.path_graph(5),nx.complete_graph(12),timeout=10)
        self.assertEqual(result['status'],'TIMEOUT');self.assertEqual(len(calls),2)
        self.assertEqual(len(result['diag']['committed_updates']),1)
        partial=result['diag']['partial_embedding'];active=nx.Graph(result['diag']['partial_requirements'])
        self.assertTrue(valid(partial,active,nx.complete_graph(12)))
        self.assertEqual(len(partial),2)
        with patch.object(rc._helpers,'SCANS',10):
            result=rc.reduced_core_embed(nx.path_graph(5),nx.complete_graph(12))
        self.assertEqual(result['diag']['scan_count'],10)
        self.assertEqual(result['diag']['stopped_by'],'work_limit')
        self.assertEqual(sum(result['diag']['scans_by_stage'].values()),10)

    def test_explicit_p4_missing_free_detour_is_reported(self):
        source=nx.Graph([(0,2),(2,1)]);target=nx.path_graph(4)
        e=engine(source,target);entry={0:{1},1:{2}};before=copy.deepcopy(entry)
        self.assertIsNone(e.insert(2,entry));self.assertEqual(entry,before)
        self.assertTrue(valid({0:[0],2:[1],1:[2]},source,target))
        OBSERVATIONS['p4_fixed_core']={'returned':None,'alternative_manually_valid':True,
                                      'reason':'free-only connector cannot relocate occupied endpoints'}

    def test_seed_order_metadata_and_parameter_guards(self):
        source=nx.wheel_graph(7);target=nx.complete_graph(16)
        reverse=nx.Graph();reverse.add_nodes_from(reversed(list(source)));reverse.add_edges_from(reversed(list(source.edges())))
        reverse.graph['family']='unused';a=rc.reduced_core_embed(source,target);b=rc.reduced_core_embed(reverse,target)
        self.assertEqual(a['embedding'],b['embedding']);self.assertEqual(a['diag']['journal'],b['diag']['journal'])
        self.assertEqual(a['diag']['scan_count'],b['diag']['scan_count'])
        for timeout in (0,float('nan')):
            with self.assertRaises(ValueError):rc.reduced_core_embed(source,target,timeout=timeout)
        result=rc.reduced_core_embed(source,target,deadline=time.perf_counter()-1)
        self.assertEqual((result['status'],result['embedding']),('TIMEOUT',{}))

    def test_z12_reach_falsifiers(self):
        for name,(source,target) in fixtures().items():
            with self.subTest(name=name):
                result=rc.reduced_core_embed(source,target,timeout=20,seed=0)
                OBSERVATIONS[name]=result
                self.assertIn(result['status'],('SUCCESS','FAILURE','TIMEOUT'))
                if result['status']=='SUCCESS':
                    self.assertTrue(valid(result['embedding'],source,target))
                    self.assertTrue(result['diag']['requirements_recovered'])
                    if name in ('star127','wheel127'):
                        self.assertGreaterEqual(len(result['embedding'][0]),7)
                else:
                    self.assertEqual(result['embedding'],{})
                    active=nx.Graph(result['diag']['partial_requirements'])
                    self.assertTrue(valid(result['diag']['partial_embedding'],active,target))
                self.assertEqual(sum(result['diag']['scans_by_stage'].values()),result['diag']['scan_count'])


if __name__=='__main__':unittest.main()
