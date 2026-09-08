"""Narrow A050 admission/rollback and unchanged-path checks; no corpus calls."""
from collections import defaultdict
import copy
import time
import unittest
from unittest.mock import patch

import networkx as nx
from ember_qc.algorithms.factored import blocked_reinsertion as br
from ember_qc.algorithms.factored import reduced_reinsertion_construction as new
from ember_qc.algorithms.factored import reduced_core_construction as old

OBSERVATIONS = {}


def valid(chains, source, target):
    if set(chains) != set(source): return False
    occupied = set()
    for chain in chains.values():
        if not chain or len(chain) != len(set(chain)): return False
        if not set(chain) <= set(target) or occupied.intersection(chain): return False
        occupied.update(chain)
        if not nx.is_connected(target.subgraph(chain)): return False
    return all(any(q in target[p] for p in chains[a] for q in chains[b])
               for a,b in source.edges())


def engine(source=None, target=None):
    source = source if source is not None else nx.Graph([(0,2),(2,1)])
    target = target if target is not None else nx.path_graph(4)
    info = defaultdict(int, stage='test', scans_by_stage={}, stopped_by=None)
    return new._Expansion(source,target,time.perf_counter()+5,0,info)


class RepairChecks(unittest.TestCase):
    def test_p4_entry_requirements_and_frozen_ownership_immutable(self):
        e=engine(); entry={0:{1},1:{2}}
        before=copy.deepcopy(entry); requirements=copy.deepcopy(e.source)
        answer,record=br.blocked_reinsert(e,2,entry)
        self.assertTrue(valid(answer,nx.Graph(requirements),nx.path_graph(4)))
        self.assertEqual(entry,before); self.assertEqual(e.source,requirements)
        self.assertTrue(record['certified']); self.assertTrue(record['returned'])
        self.assertFalse(record['committed']); self.assertIsNone(e.repair_end)
        for w in set(entry)-set(record['selected']): self.assertEqual(answer[w],entry[w])
        answer[2].clear(); self.assertEqual(entry,before)
        self.assertEqual(record['scans'],record['selection_scans']+sum(b['scans'] for b in record['blocks']))
        OBSERVATIONS['p4']=record

    def test_query_cumulative_and_global_caps_no_renewal(self):
        e=engine(); entry={0:{1},1:{2}}; original=copy.deepcopy(entry)
        with patch.object(br,'QUERY_SCANS',1):
            _,a=br.blocked_reinsert(e,2,entry)
            _,b=br.blocked_reinsert(e,2,entry)
        self.assertEqual((a['scans'],b['scans'],b['total_start'],b['total_end']),(1,1,1,2))
        e.info['blocked_repair_scans']=br.TOTAL_SCANS-1
        _,c=br.blocked_reinsert(e,2,entry)
        _,d=br.blocked_reinsert(e,2,entry)
        self.assertEqual((c['limit'],c['scans'],d['limit'],d['scans']),(1,1,0,0))
        self.assertEqual(d['status'],'repair_budget_exhausted')
        e=engine(); e.scans=br._helpers.SCANS-1
        _,record=br.blocked_reinsert(e,2,entry)
        self.assertEqual(record['limit_sources'],['global'])
        self.assertEqual(e.scans,br._helpers.SCANS); self.assertEqual(record['scans'],1)
        self.assertEqual(entry,original); self.assertIsNone(e.repair_end)

    def test_interrupt_inside_rebuild_restores_entry_and_source(self):
        e=engine(); entry={0:{1},1:{2}}; before=copy.deepcopy(entry); requirements=copy.deepcopy(e.source)
        clock=[0.]; e.deadline=10.; real=e.insert
        def delayed(*args,**kwargs):
            answer=real(*args,**kwargs); clock[0]=11.; return answer
        with patch.object(br.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(e,'insert',side_effect=delayed):
            with self.assertRaises(br.Stop): br.blocked_reinsert(e,2,entry)
        self.assertEqual(entry,before); self.assertEqual(e.source,requirements)
        self.assertIsNone(e.repair_end); self.assertEqual(e.info['stopped_by'],'deadline')
        record=e.info['blocked_repair_records'][0]
        self.assertFalse(record['committed']); self.assertFalse(record['returned'])
        self.assertGreater(record['scans'],0)

    def test_removed_fill_cleanup_count_and_frozen_endpoint(self):
        source=nx.Graph([(0,2),(2,1)]); target=nx.cycle_graph(4)
        e=engine(source,target); entry={0:{0,1},1:{2}}; before=copy.deepcopy(entry)
        requirements=copy.deepcopy(e.source)
        def insert(v,trial,frozen=frozenset()):
            if frozen=={0}: return None  # First cheaper block cannot rebuild.
            self.assertEqual(frozen,{1})
            answer={w:set(c) for w,c in trial.items()}
            answer[v]={3} if v==2 else {0,1}
            return answer
        with patch.object(e,'insert',side_effect=insert): answer,record=br.blocked_reinsert(e,2,entry,[(0,1)])
        self.assertEqual(record['selected'],[0]); self.assertEqual(record['released_fill_qubits_pruned'],1)
        self.assertEqual(record['blocks'][-1]['released_fill_qubits_pruned'],1)
        self.assertEqual(answer[1],entry[1]); self.assertEqual(answer[0],{0})
        self.assertTrue(valid(answer,source,target)); self.assertEqual(entry,before); self.assertEqual(e.source,requirements)
        OBSERVATIONS['fill_cleanup']=record

    def test_no_block_matches_049_choices_and_never_calls_repair(self):
        fixtures=[nx.path_graph(7),nx.wheel_graph(7),nx.disjoint_union(nx.cycle_graph(4),nx.empty_graph(2))]
        for source in fixtures:
            target=nx.complete_graph(16); originals=(nx.to_dict_of_lists(source),nx.to_dict_of_lists(target))
            with patch.object(new,'blocked_reinsert',side_effect=AssertionError('ordinary success called repair')):
                a=old.reduced_core_embed(source,target,timeout=5)
                b=new.reduced_core_embed(source,target,timeout=5)
            self.assertEqual(a['status'],'SUCCESS');self.assertEqual(b['status'],'SUCCESS')
            self.assertEqual(a['embedding'],b['embedding']);self.assertTrue(valid(b['embedding'],source,target))
            for key in ('journal','anchors','core_config','core_calls','scan_count','scans_by_stage',
                        'insertion_queries','root_branches','staged_pruned_sites','requirements_recovered'):
                self.assertEqual(a['diag'][key],b['diag'][key],key)
            updates=[{k:v for k,v in row.items() if k!='insertion_operator'} for row in b['diag']['committed_updates']]
            self.assertEqual(a['diag']['committed_updates'],updates)
            self.assertEqual(b['diag']['blocked_repair_queries'],0)
            self.assertEqual(originals,(nx.to_dict_of_lists(source),nx.to_dict_of_lists(target)))

    def test_blocked_wrapper_commits_one_certified_repair(self):
        real_insert=new._Expansion.insert; real_repair=br.blocked_reinsert; inside=[False]; ordinary=[]
        def insert(e,v,entry,frozen=frozenset()):
            if not inside[0]:
                ordinary.append(v)
                if len(ordinary)==2: return None
            return real_insert(e,v,entry,frozen)
        def repair(*args,**kwargs):
            inside[0]=True
            try:return real_repair(*args,**kwargs)
            finally:inside[0]=False
        source=nx.wheel_graph(7);target=nx.complete_graph(16)
        with patch.object(new._Expansion,'insert',insert),patch.object(new,'blocked_reinsert',side_effect=repair):
            result=new.reduced_core_embed(source,target,timeout=5)
        self.assertEqual(result['status'],'SUCCESS',result['diag'])
        self.assertTrue(valid(result['embedding'],source,target))
        info=result['diag'];self.assertEqual(info['blocked_repair_accepted'],1)
        self.assertEqual(info['blocked_repair_queries'],1)
        self.assertEqual(sum(r['committed'] for r in info['blocked_repair_records']),1)
        self.assertEqual(sum(r['insertion_operator']=='repair' for r in info['committed_updates']),1)
        self.assertEqual(sum(info['scans_by_stage'].values()),info['scan_count'])
        self.assertLessEqual(info['blocked_repair_scans'],info['scan_count'])
        OBSERVATIONS['pipeline_repair']=result

    def test_certified_late_repair_not_committed_and_prior_R_retained(self):
        real_insert=new._Expansion.insert; real_repair=br.blocked_reinsert
        clock=[0.]; inside=[False]; ordinary=[]
        def insert(e,v,entry,frozen=frozenset()):
            if not inside[0]:
                ordinary.append(v)
                if len(ordinary)==2:return None
            return real_insert(e,v,entry,frozen)
        def repair(*args,**kwargs):
            inside[0]=True
            try:answer=real_repair(*args,**kwargs)
            finally:inside[0]=False
            self.assertIsNotNone(answer[0]);clock[0]=11.;return answer
        source=nx.wheel_graph(7);target=nx.complete_graph(16)
        with patch.object(new.time,'perf_counter',side_effect=lambda:clock[0]),patch.object(new._Expansion,'insert',insert),patch.object(new,'blocked_reinsert',side_effect=repair):
            result=new.reduced_core_embed(source,target,timeout=10)
        info=result['diag'];self.assertEqual(result['status'],'TIMEOUT')
        self.assertEqual(len(info['committed_updates']),1);self.assertEqual(info['blocked_repair_accepted'],0)
        record=info['blocked_repair_records'][0]
        self.assertTrue(record['certified']);self.assertTrue(record['returned']);self.assertFalse(record['committed'])
        partial=info['partial_embedding']; self.assertEqual(len(partial),2)
        self.assertTrue(valid(partial,nx.Graph(info['partial_requirements']),target))
        # Reconstruct the exact preceding filled R independently, before rejected step.
        expected=source.copy(); journal=info['journal']; forward=[]
        for row in journal:
            forward.append(expected.copy())
            n=list(expected[row['vertex']])
            for i,a in enumerate(n):
                for b in n[i+1:]:expected.add_edge(a,b)
            expected.remove_node(row['vertex'])
        previous=forward[-1]
        self.assertEqual({v:set(w) for v,w in info['partial_requirements'].items()},
                         {v:set(previous[v]) for v in previous})
        OBSERVATIONS['late_certified']=result

    def test_failed_repair_retains_exact_previous_partial_requirements(self):
        source=nx.wheel_graph(7);target=nx.complete_graph(16)
        with patch.object(new._Expansion,'insert',return_value=None),patch.object(br,'QUERY_SCANS',1):
            result=new.reduced_core_embed(source,target,timeout=5)
        self.assertEqual(result['status'],'FAILURE');info=result['diag']
        self.assertEqual(info['committed_updates'],[]);self.assertEqual(info['blocked_repair_accepted'],0)
        self.assertEqual(info['blocked_repair_records'][0]['scans'],1)
        self.assertTrue(valid(info['partial_embedding'],nx.Graph(info['partial_requirements']),target))
        self.assertEqual(info['placed_vertices'],1)


if __name__=='__main__':unittest.main()
