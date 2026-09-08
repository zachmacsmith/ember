"""Tiny independent quotient bookkeeping and construction/deadline checks."""
from collections import Counter
import importlib.util
import itertools
from pathlib import Path
import random
import sys
import time
import unittest
from unittest.mock import patch

import networkx as nx

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'packages/ember-qc/src/ember_qc/algorithms/quotient_reconfiguration.py'
spec=importlib.util.spec_from_file_location('isolated_quotient_constructor',path)
qr=importlib.util.module_from_spec(spec)
spec.loader.exec_module(qr)


def independent(state,target,source):
    owner={}
    for u,chain in enumerate(state.regions):
        assert chain and nx.is_connected(target.subgraph(chain))
        for q in chain:
            assert q in target and q not in owner
            owner[q]=u
    count=Counter(tuple(sorted((owner[q],owner[p]))) for q,p in target.edges()
                  if q in owner and p in owner and owner[q]!=owner[p])
    for u in source:
        for v in source:
            assert state.count[u][v] == (count[tuple(sorted((u,v)))] if u!=v else 0)
    missing={tuple(sorted((u,v))) for u,v in source.edges() if count[tuple(sorted((u,v)))]==0}
    assert set(state.missing)==missing
    assert len(state.missing)==len(state.position)
    assert all(state.missing[i]==edge for edge,i in state.position.items())
    assert all(state.owner[q]==v for q,v in owner.items())
    return len(missing)


class QuotientChecks(unittest.TestCase):
    def test_all_label_exchanges_exact(self):
        target=nx.convert_node_labels_to_integers(nx.grid_2d_graph(4,4))
        source=nx.cycle_graph(4)
        regions=[set(range(i*4,(i+1)*4)) for i in range(4)]
        for u,v in itertools.combinations(range(4),2):
            meter=qr._Meter(time.perf_counter()+2,{'stage_wall':{}})
            state=qr._State([r.copy() for r in regions],[tuple(source[u]) for u in source],[tuple(target[q]) for q in target],meter)
            before=independent(state,target,source)
            delta,affected=state.swap_delta(u,v)
            state.swap(u,v,affected)
            self.assertEqual(independent(state,target,source),before+delta)

    def test_safe_transfers_and_cache_invalidation(self):
        target=nx.convert_node_labels_to_integers(nx.grid_2d_graph(4,4))
        source=nx.cycle_graph(4)
        meter=qr._Meter(time.perf_counter()+5,{'stage_wall':{}})
        state=qr._State([set(range(i*4,(i+1)*4)) for i in range(4)],
                        [tuple(source[u]) for u in source],[tuple(target[q]) for q in target],meter)
        rng=random.Random(3)
        transfers=0
        for step in range(80):
            candidates=[]
            for q in target:
                u=state.owner[q]
                for v in sorted({state.owner[p] for p in target[q]}-{u}):
                    mathematically_safe=len(state.regions[u])>1 and nx.is_connected(target.subgraph(state.regions[u]-{q}))
                    self.assertEqual(state.movable(q,v,[1]*4),mathematically_safe)
                    if mathematically_safe:
                        candidates.append((q,v))
            if not candidates:
                break
            q,v=rng.choice(candidates)
            old_distance=state.distance(v)
            before=independent(state,target,source)
            delta,change=state.transfer_delta(q,v)
            state.transfer(q,v,change)
            self.assertEqual(independent(state,target,source),before+delta)
            measured=state.distance(v)
            expected=nx.multi_source_dijkstra_path_length(target,state.regions[v],weight=None)
            self.assertEqual(measured,expected)
            transfers+=1
            if step%7==0:
                u,w=rng.sample(range(4),2)
                before=independent(state,target,source)
                delta,affected=state.swap_delta(u,w)
                state.swap(u,w,affected)
                self.assertEqual(independent(state,target,source),before+delta)
        self.assertEqual(transfers,80)

    def test_target_coarsening_exact_count_and_connectedness(self):
        target=nx.convert_node_labels_to_integers(nx.grid_2d_graph(5,5))
        adj=[tuple(target[q]) for q in target]
        for n in (1,4,7,24,25):
            diag={'coarsening_levels':0,'target_contractions':0}
            regions=qr._coarsen(adj,n,random.Random(0),qr._Meter(time.perf_counter()+2,{'stage_wall':{}}),diag)
            self.assertEqual(len(regions),n)
            self.assertEqual(set().union(*regions),set(target))
            self.assertEqual(sum(map(len,regions)),len(target))
            self.assertTrue(all(nx.is_connected(target.subgraph(r)) for r in regions))
            self.assertEqual(diag['target_contractions'],25-n)

    def test_complete_target_all_four_vertex_sources(self):
        target=nx.complete_graph(4)
        edges=list(itertools.combinations(range(4),2))
        for mask in range(64):
            source=nx.empty_graph(4)
            source.add_edges_from(e for i,e in enumerate(edges) if mask>>i&1)
            result=qr.quotient_embed(source,target,timeout=1)
            self.assertEqual(result['status'],'SUCCESS',result)
            self.assertEqual(sum(map(len,result['embedding'].values())),4)
            self.assertEqual(set(result['embedding']),set(source))
            for u,v in source.edges():
                self.assertTrue(target.has_edge(result['embedding'][u][0],result['embedding'][v][0]))

    def test_trimming_and_late_final_validation(self):
        source,target=nx.path_graph(3),nx.complete_graph(12)
        result=qr.quotient_embed(source,target,timeout=1)
        self.assertEqual(result['status'],'SUCCESS')
        self.assertEqual(result['diag']['trim_deletions'],9)
        self.assertEqual(sum(map(len,result['embedding'].values())),3)
        clock=[100.]
        original=qr._valid
        calls=[0]
        def late(*args):
            valid=original(*args)
            calls[0]+=1
            if calls[0]==2:
                clock[0]=111.
            return valid
        with patch.object(qr.time,'perf_counter',lambda:clock[0]),patch.object(qr,'_valid',late):
            result=qr.quotient_embed(source,target,timeout=10)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertGreater(result['diag']['deadline_overrun'],0)

    def test_invalid_and_expired_inputs(self):
        source,target=nx.path_graph(3),nx.path_graph(8)
        result=qr.quotient_embed(source,target,deadline=time.perf_counter()-1)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertEqual(result['embedding'],{})
        self.assertEqual(qr.quotient_embed(nx.Graph(),nx.Graph())['status'],'SUCCESS')
        self.assertEqual(qr.quotient_embed(nx.path_graph(4),nx.path_graph(3))['status'],'FAILURE')
        for kw in ({'timeout':0},{'seed':True},{'deadline':float('nan')}):
            self.assertEqual(qr.quotient_embed(source,target,**kw)['status'],'ERROR')
        self.assertFalse(any('minorminer' in name or 'busclique' in name or name.startswith('ember_qc') for name in sys.modules))


if __name__=='__main__':
    unittest.main()
