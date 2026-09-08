"""Focused supplied-graph checks for compact allocation and original IDs."""
import importlib.util
from pathlib import Path
import random
import sys
import time
import unittest
from unittest.mock import patch

import networkx as nx

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'packages/ember-qc/src/ember_qc/algorithms/quotient_compact.py'
spec=importlib.util.spec_from_file_location('isolated_compact_constructor',path)
qr=importlib.util.module_from_spec(spec)
spec.loader.exec_module(qr)


def minor(result,source,target):
    chains=result['embedding'];owner={}
    assert set(chains)==set(source)
    for u,chain in chains.items():
        assert chain and len(chain)==len(set(chain))
        assert nx.is_connected(target.subgraph(chain))
        for q in chain:
            assert q in target and q not in owner
            owner[q]=u
    represented={frozenset((owner[q],owner[p])) for q,p in target.edges() if q in owner and p in owner}
    assert all(frozenset((u,v)) in represented for u,v in source.edges())


class CompactChecks(unittest.TestCase):
    def test_subset_exact_connected_induced_original_edges(self):
        target=nx.convert_node_labels_to_integers(nx.grid_2d_graph(10,10))
        adj=[tuple(sorted(target[q])) for q in target]
        for lower in ([1],[1,1],[2]*6,[1]*30):
            diag={};meter=qr._Meter(time.perf_counter()+2,{'stage_wall':{}})
            selected,restricted=qr._subset(adj,len(lower),lower,random.Random(0),meter,diag)
            self.assertEqual(len(selected),min(100,4*sum(lower)))
            self.assertEqual(len(set(selected)),len(selected))
            self.assertTrue(nx.is_connected(target.subgraph(selected)))
            self.assertIn(diag['target_center_rank'],selected)
            self.assertEqual({(selected[u],selected[v]) for u,row in enumerate(restricted) for v in row},
                             {(q,p) for q in selected for p in target[q] if p in selected})

    def test_one_subset_determinism_and_component_limit(self):
        target=nx.disjoint_union(nx.path_graph(3),nx.path_graph(20))
        adj=[tuple(target[q]) for q in target]
        outputs=[]
        for _ in range(2):
            d={};m=qr._Meter(time.perf_counter()+1,{'stage_wall':{}})
            outputs.append(qr._subset(adj,2,[1,1],random.Random(9),m,d))
            self.assertTrue(set(outputs[-1][0])<=set(range(3,23)))
        self.assertEqual(outputs[0],outputs[1])
        with self.assertRaises(qr._Failed):
            qr._subset(adj,21,[1]*21,random.Random(0),m,{})

    def test_real_tiny_original_labels_and_gate_uses_full_target(self):
        source=nx.relabel_nodes(nx.path_graph(3),lambda u:'s'+str(u))
        target=nx.relabel_nodes(nx.complete_graph(50),lambda q:1000+3*q)
        original=qr._valid;gate_target_sizes=[]
        def observed(chains,src,adj,meter):
            gate_target_sizes.append(len(adj))
            return original(chains,src,adj,meter)
        with patch.object(qr,'_valid',observed):
            result=qr.compact_embed(source,target,timeout=1)
        self.assertEqual(result['status'],'SUCCESS',result)
        minor(result,source,target)
        self.assertEqual(result['diag']['active_target_nodes'],12)
        self.assertEqual(result['diag']['entry_qubits'],12)
        self.assertEqual(sum(map(len,result['embedding'].values())),3)
        self.assertEqual(gate_target_sizes,[50,50])

    def test_failed_search_preserves_original_id_partial(self):
        source=nx.relabel_nodes(nx.path_graph(3),lambda u:'s'+str(u))
        target=nx.relabel_nodes(nx.complete_graph(50),lambda q:1000+3*q)
        with patch.object(qr,'_search',side_effect=qr._Expired):
            result=qr.compact_embed(source,target,timeout=1)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertEqual(result['embedding'],{})
        partial=result['partial_embedding']
        self.assertEqual(set(partial),set(source))
        self.assertEqual(sum(map(len,partial.values())),12)
        self.assertTrue(all(q in target for chain in partial.values() for q in chain))
        self.assertTrue(all(nx.is_connected(target.subgraph(chain)) for chain in partial.values()))

    def test_late_original_target_gate_is_not_success(self):
        clock=[100.];calls=[0];original=qr._valid
        def late(*args):
            result=original(*args);calls[0]+=1
            if calls[0]==2:clock[0]=111.
            return result
        with patch.object(qr.time,'perf_counter',lambda:clock[0]),patch.object(qr,'_valid',late):
            result=qr.compact_embed(nx.path_graph(3),nx.complete_graph(50),timeout=10)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertGreater(result['diag']['deadline_overrun'],0)

    def test_empty_expired_capacity_and_no_package_import(self):
        self.assertEqual(qr.compact_embed(nx.Graph(),nx.Graph())['status'],'SUCCESS')
        self.assertEqual(qr.compact_embed(nx.path_graph(4),nx.path_graph(3))['status'],'FAILURE')
        result=qr.compact_embed(nx.path_graph(3),nx.path_graph(8),deadline=time.perf_counter()-1)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertEqual(result['embedding'],{})
        self.assertFalse(any('minorminer' in name or 'busclique' in name or name.startswith('ember_qc') for name in sys.modules))


if __name__=='__main__':
    unittest.main()
