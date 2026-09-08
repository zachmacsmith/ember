"""Independent tiny whole-target checks for constant-Q free-site exchange."""
from collections import Counter
import importlib.util
from pathlib import Path
import random
import sys
import time
import unittest
from unittest.mock import patch

import networkx as nx

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'packages/ember-qc/src/ember_qc/algorithms/quotient_vacancy.py'
spec=importlib.util.spec_from_file_location('isolated_vacancy_constructor',path)
qr=importlib.util.module_from_spec(spec);spec.loader.exec_module(qr)


def recount(state,source,target):
    owner={}
    for u,chain in enumerate(state.regions):
        assert chain and nx.is_connected(target.subgraph(chain))
        for q in chain:
            assert q in target and q not in owner
            owner[q]=u
    contacts=Counter(tuple(sorted((owner[q],owner[p]))) for q,p in target.edges()
                     if q in owner and p in owner and owner[q]!=owner[p])
    for u in source:
        for v in source:
            assert state.count[u][v]==(contacts[tuple(sorted((u,v)))] if u!=v else 0)
    missing={tuple(sorted((u,v))) for u,v in source.edges() if contacts[tuple(sorted((u,v)))]==0}
    assert set(state.missing)==missing
    assert len(state.missing)==len(state.position)
    assert all(state.missing[i]==edge for edge,i in state.position.items())
    assert state.owner==[owner.get(q,-1) for q in target]
    return len(missing),len(owner)


def state_for(source,target,regions):
    meter=qr._Meter(time.perf_counter()+5,{'stage_wall':{}})
    return qr._State([set(r) for r in regions],[tuple(source[u]) for u in source],
                     [tuple(target[q]) for q in target],meter)


class VacancyChecks(unittest.TestCase):
    def test_all_tiny_free_exchanges_and_multiplicity(self):
        target=nx.convert_node_labels_to_integers(nx.grid_2d_graph(5,5))
        source=nx.cycle_graph(4);regions=[{5*u,5*u+1,5*u+2} for u in range(4)]
        count=0
        for u,region in enumerate(regions):
            free={p for q in region for p in target[q]}-set().union(*regions)
            for p in sorted(free):
                for q in sorted(region):
                    state=state_for(source,target,regions)
                    allowed=state.free_safe(u,p,q)
                    if not allowed:continue
                    self.assertTrue(nx.is_connected(target.subgraph((region-{q})|{p})))
                    before,Q=recount(state,source,target)
                    delta,change=state.free_delta(u,p,q)
                    state.free_commit(u,p,q,change)
                    self.assertEqual(recount(state,source,target),(before+delta,Q));count+=1
        self.assertEqual(count,8)

    def test_repeated_moves_cross_initial_domain_and_invalidate_cuts(self):
        target=nx.convert_node_labels_to_integers(nx.grid_2d_graph(6,6))
        source=nx.cycle_graph(4);regions=[{6*u,6*u+1,6*u+2} for u in range(4)]
        state=state_for(source,target,regions);initial=set().union(*regions);rng=random.Random(8)
        outside=0
        for _ in range(80):
            options=[]
            for u,region in enumerate(state.regions):
                free={p for q in region for p in target[q] if state.owner[p]==-1}
                for p in sorted(free):
                    for q in sorted(region):
                        expected=(q not in set(nx.articulation_points(target.subgraph(region))) and
                                  any(v!=q and state.owner[v]==u for v in target[p]))
                        self.assertEqual(state.free_safe(u,p,q),expected)
                        if expected:options.append((u,p,q))
            u,p,q=rng.choice(options);before,Q=recount(state,source,target)
            delta,change=state.free_delta(u,p,q);state.free_commit(u,p,q,change)
            self.assertEqual(recount(state,source,target),(before+delta,Q))
            outside+=p not in initial
        self.assertGreater(outside,0)

    def test_singleton_and_disconnected_release(self):
        target=nx.path_graph(5);source=nx.path_graph(2)
        state=state_for(source,target,[{0},{4}])
        self.assertTrue(state.free_safe(0,1,0))
        delta,change=state.free_delta(0,1,0);state.free_commit(0,1,0,change)
        self.assertEqual(recount(state,source,target),(1,2))
        state=state_for(nx.empty_graph(1),target,[{0,1,2}])
        self.assertFalse(state.free_safe(0,3,1))
        self.assertFalse(state.free_safe(0,3,2))
        self.assertTrue(state.free_safe(0,3,0))

    def test_bounded_bfs_uses_unoccupied_original_target(self):
        target=nx.path_graph(9);source=nx.path_graph(2)
        state=state_for(source,target,[{0},{8}])
        got=qr._nearest(state,1,{3,4,6},2,random.Random(0),state.meter)
        self.assertEqual(got,[6,4])
        distances=nx.single_source_shortest_path_length(target,8)
        self.assertEqual([distances[q] for q in got],[2,4])
        # A candidate set smaller than the cap must not exhaust the graph.
        target=nx.path_graph(1000);state=state_for(source,target,[{0},{999}])
        self.assertEqual(qr._nearest(state,1,{998},8,random.Random(0),state.meter),[998])
        self.assertEqual(state.meter.work['proposal_bfs_vertices'],2)
        self.assertEqual(state.meter.work['proposal_bfs_adjacency'],1)

    def test_atomic_commit_interruption_and_partial_original_ids(self):
        target=nx.path_graph(5);source=nx.path_graph(2)
        state=state_for(source,target,[{0},{4}]);delta,change=state.free_delta(0,1,0)
        with patch.object(state.meter,'check',side_effect=qr._Expired):
            with self.assertRaises(qr._Expired):state.free_commit(0,1,0,change)
        self.assertEqual(state.regions,[{0},{4}])
        state.free_commit(0,1,0,change)
        self.assertGreater(state.meter.work['free_commit_records'],0)
        self.assertEqual(recount(state,source,target),(1,2))
        source=nx.path_graph(3);target=nx.relabel_nodes(nx.complete_graph(50),lambda q:1000+3*q)
        def interrupted(state,lower,rng,meter,diag):
            p=next(q for q in range(50) if state.owner[q]==-1)
            q=next(q for q in sorted(state.regions[0]) if state.free_safe(0,p,q))
            _,change=state.free_delta(0,p,q);state.free_commit(0,p,q,change)
            raise qr._Expired
        with patch.object(qr,'_search',interrupted):result=qr.vacancy_embed(source,target,timeout=1)
        self.assertEqual(result['status'],'TIMEOUT');self.assertEqual(result['embedding'],{})
        partial=result['partial_embedding'];self.assertEqual(sum(map(len,partial.values())),12)
        initial={list(target)[q] for q in result['diag']['active_target_ranks']}
        self.assertEqual(len(set().union(*map(set,partial.values()))-initial),1)
        self.assertTrue(all(q in target for chain in partial.values() for q in chain))

    def test_tiny_constructor_final_target_gate_and_deadline(self):
        source,target=nx.path_graph(3),nx.complete_graph(50)
        result=qr.vacancy_embed(source,target,timeout=1)
        self.assertEqual(result['status'],'SUCCESS',result)
        self.assertEqual(sum(map(len,result['embedding'].values())),3)
        clock=[100.];original=qr._valid;calls=[0]
        def late(*args):
            self.assertEqual(len(args[2]),50)
            valid=original(*args);calls[0]+=1
            if calls[0]==2:clock[0]=111.
            return valid
        with patch.object(qr.time,'perf_counter',lambda:clock[0]),patch.object(qr,'_valid',late):
            result=qr.vacancy_embed(source,target,timeout=10)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertFalse(any('minorminer' in name or 'busclique' in name or name.startswith('ember_qc') for name in sys.modules))


if __name__=='__main__':
    unittest.main()
