"""Independent contraction-loss witnesses and original-target gate checks."""
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
path=ROOT/'packages/ember-qc/src/ember_qc/algorithms/quotient_distinct.py'
spec=importlib.util.spec_from_file_location('isolated_distinct_constructor',path)
qr=importlib.util.module_from_spec(spec);spec.loader.exec_module(qr)


def structures(graph):
    return ({q:{q} for q in graph},{q:Counter({v:1 for v in graph[q]}) for q in graph},list(graph))


def meter():
    return qr._Meter(time.perf_counter()+5,{'stage_wall':{}})


class DistinctChecks(unittest.TestCase):
    def test_all_four_vertex_graph_contraction_losses(self):
        edges=list(itertools.combinations(range(4),2));checked=0
        for mask in range(64):
            graph=nx.empty_graph(4);graph.add_edges_from(e for i,e in enumerate(edges) if mask>>i&1)
            for u,v in graph.edges():
                regions,links,owner=structures(graph)
                before=graph.number_of_edges()
                expected=nx.contracted_nodes(graph,u,v,self_loops=False)
                loss,raw=qr._contract(regions,links,owner,u,v,4,meter())
                self.assertEqual(loss,before-expected.number_of_edges());self.assertEqual(raw,1)
                actual=Counter(tuple(sorted((owner[a],owner[b]))) for a,b in graph.edges() if owner[a]!=owner[b])
                self.assertEqual(sum(map(len,links.values()))//2,len(actual))
                for a,row in links.items():
                    for b,count in row.items():self.assertEqual(count,actual[tuple(sorted((a,b)))])
                self.assertTrue(all(nx.is_connected(graph.subgraph(r)) for r in regions.values()))
                checked+=1
        self.assertEqual(checked,192)

    def test_equal_raw_couplers_different_distinct_loss(self):
        graph=nx.Graph([(0,1),(0,2),(0,3),(0,4),(2,3),(2,4)])
        graph=nx.Graph((u,v) for u,v in graph.edges());graph.add_nodes_from(range(5))
        adj=[tuple(sorted(graph[q])) for q in range(5)]
        class Fixed:
            def shuffle(self,values):values.sort(key={0:0,2:1,1:2,3:3,4:4}.get)
        regions,links,owner=structures(nx.empty_graph(5))
        links={q:Counter({v:1 for v in adj[q]}) for q in range(5)}
        self.assertEqual(links[0][1],links[0][2])
        self.assertEqual((qr._loss(links,0,1,meter()),qr._loss(links,0,2,meter())),(1,3))
        d={'coarsening_levels':0,'target_contractions':0}
        new=qr._coarsen(adj,4,Fixed(),meter(),d)
        old=qr._helpers._coarsen(adj,4,Fixed(),meter(),{'coarsening_levels':0,'target_contractions':0})
        self.assertIn({0,1},new);self.assertIn({0,2},old)
        self.assertEqual(d['coarsened_quotient_edges'],5)

    def test_live_batch_losses_and_weighted_couplers(self):
        graph=nx.complete_graph(4);regions,links,owner=structures(graph);m=meter()
        stale=qr._loss(links,0,1,m)+qr._loss(links,2,3,m)
        first,_=qr._contract(regions,links,owner,0,1,4,m)
        second,_=qr._contract(regions,links,owner,2,3,5,m)
        self.assertEqual(stale,6);self.assertEqual(first+second,5)
        self.assertEqual(links,{4:Counter({5:4}),5:Counter({4:4})})

    def test_all_coarsening_levels_telescope_and_remain_connected(self):
        graph=nx.convert_node_labels_to_integers(nx.grid_2d_graph(5,5))
        adj=[tuple(graph[q]) for q in graph]
        for n in (1,4,10,25):
            d={'coarsening_levels':0,'target_contractions':0}
            regions=qr._coarsen(adj,n,random.Random(0),meter(),d)
            self.assertEqual(len(regions),n);self.assertEqual(sum(map(len,regions)),25)
            self.assertTrue(all(nx.is_connected(graph.subgraph(r)) for r in regions))
            owner={q:u for u,r in enumerate(regions) for q in r}
            contacts={tuple(sorted((owner[u],owner[v]))) for u,v in graph.edges() if owner[u]!=owner[v]}
            self.assertEqual(len(contacts),d['coarsened_quotient_edges'])
            self.assertEqual(graph.number_of_edges()-len(contacts),sum(r['distinct_loss'] for r in d['coarsening_trace']))
            for row in d['coarsening_trace']:
                self.assertEqual(row['quotient_edges_before']-row['quotient_edges_after'],row['distinct_loss'])

    def test_interrupted_commit_and_tiny_original_target_gate(self):
        graph=nx.complete_graph(4);regions,links,owner=structures(graph);m=meter()
        with patch.object(m,'check',side_effect=qr._Expired):
            with self.assertRaises(qr._Expired):qr._contract(regions,links,owner,0,1,4,m)
        self.assertEqual(regions,{q:{q} for q in graph});self.assertEqual(owner,list(graph))
        source,target=nx.path_graph(3),nx.complete_graph(50)
        result=qr.distinct_embed(source,target,timeout=1)
        self.assertEqual(result['status'],'SUCCESS',result)
        self.assertEqual(sum(map(len,result['embedding'].values())),3)
        initial=result['diag']['initial_regions_target_ranks']
        self.assertEqual(sum(map(len,initial.values())),12)
        clock=[100.];original=qr._valid;calls=[0]
        def late(*args):
            self.assertEqual(len(args[2]),50)
            value=original(*args);calls[0]+=1
            if calls[0]==2:clock[0]=111.
            return value
        with patch.object(qr.time,'perf_counter',lambda:clock[0]),patch.object(qr,'_valid',late):
            result=qr.distinct_embed(source,target,timeout=10)
        self.assertEqual(result['status'],'TIMEOUT')
        self.assertFalse(any('minorminer' in name or 'busclique' in name or name.startswith('ember_qc') for name in sys.modules))


if __name__=='__main__':
    unittest.main()
