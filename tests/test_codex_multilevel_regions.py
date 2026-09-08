"""Small structural checks; no constructors, embedding library or corpus inputs."""
import importlib.util
import itertools
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

import networkx as nx


PATH = Path(__file__).resolve().parents[1] / 'packages/ember-qc/src/ember_qc/algorithms/multilevel_regions.py'
SPEC = importlib.util.spec_from_file_location('multilevel_regions_checked', PATH)
mr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mr)


def valid(embedding, source, target):
    if set(embedding) != set(source):
        return False
    owner = {}
    for v, chain in embedding.items():
        if not chain or len(chain) != len(set(chain)) or any(q not in target for q in chain):
            return False
        if not nx.is_connected(target.subgraph(chain)):
            return False
        for q in chain:
            if q in owner:
                return False
            owner[q] = v
    contacts = {frozenset((owner[q], owner[p])) for q, p in target.edges() if q in owner and p in owner}
    return all(frozenset((u, v)) in contacts for u, v in source.edges())


class MultilevelChecks(unittest.TestCase):
    def test_complete_target_all_four_vertex_source_graphs(self):
        target = nx.complete_graph(4)
        edges = list(itertools.combinations(range(4), 2))
        for mask in range(64):
            source = nx.empty_graph(4)
            source.add_edges_from(edge for i, edge in enumerate(edges) if mask >> i & 1)
            before = (list(source.nodes()), list(source.edges()), list(target.edges()))
            response = mr.multilevel_embed(source, target, timeout=2, seed=0)
            self.assertEqual(response['status'], 'SUCCESS', (mask, response))
            self.assertTrue(valid(response['embedding'], source, target))
            self.assertEqual(sum(map(len, response['embedding'].values())), 4)
            self.assertEqual(before, (list(source.nodes()), list(source.edges()), list(target.edges())))

    def test_articulations_against_networkx(self):
        edges = list(itertools.combinations(range(4), 2))
        for mask in range(64):
            graph = nx.empty_graph(4)
            graph.add_edges_from(edge for i, edge in enumerate(edges) if mask >> i & 1)
            if not nx.is_connected(graph):
                continue
            meter = mr._Meter(time.perf_counter()+2, {'stage_wall': {}})
            adj = [tuple(graph[q]) for q in graph]
            self.assertEqual(mr._articulations(set(graph), adj, meter), set(nx.articulation_points(graph)))

    def test_supplied_paths_and_contact_traps_never_false_success(self):
        for target in (nx.path_graph(12), nx.cycle_graph(12), nx.complete_bipartite_graph(4, 5)):
            for source in (nx.path_graph(5), nx.star_graph(4), nx.complete_graph(4), nx.empty_graph(5)):
                response = mr.multilevel_embed(source, target, seed=1, timeout=2)
                self.assertIn(response['status'], ('SUCCESS', 'FAILURE', 'TIMEOUT'))
                if response['status'] == 'SUCCESS':
                    self.assertTrue(valid(response['embedding'], source, target), response)
                else:
                    self.assertEqual(response['embedding'], {})
                    self.assertIn('error', response)
                    self.assertGreaterEqual(response['diag']['wall'], 0)

    def test_empty_isolates_labels_and_invalid_parameters(self):
        self.assertEqual(mr.multilevel_embed(nx.Graph(), nx.Graph())['status'], 'SUCCESS')
        response = mr.multilevel_embed(nx.path_graph(['a', 'b', 'c']), nx.complete_graph(['w', 'x', 'y', 'z']), seed=2)
        self.assertEqual(response['status'], 'SUCCESS')
        self.assertTrue(valid(response['embedding'], nx.path_graph(['a', 'b', 'c']), nx.complete_graph(['w', 'x', 'y', 'z'])))
        self.assertEqual(mr.multilevel_embed(nx.path_graph(3), nx.path_graph(2))['status'], 'FAILURE')
        for kwargs in ({'timeout': 0}, {'timeout': float('inf')}, {'deadline': float('nan')}, {'seed': True}):
            self.assertEqual(mr.multilevel_embed(nx.path_graph(2), nx.path_graph(3), **kwargs)['status'], 'ERROR')

    def test_deadline_and_late_final_validation(self):
        expired = mr.multilevel_embed(nx.path_graph(4), nx.complete_graph(8), deadline=time.perf_counter()-1)
        self.assertEqual(expired['status'], 'TIMEOUT')
        self.assertEqual(expired['embedding'], {})
        self.assertGreater(expired['diag']['deadline_overrun'], 0)
        clock = [100.0]
        original_valid = mr._valid
        calls = [0]
        def validation(*args):
            result = original_valid(*args)
            calls[0] += 1
            if calls[0] == 2:
                clock[0] = 111.0
            return result
        with patch.object(mr.time, 'perf_counter', lambda: clock[0]), patch.object(mr, '_valid', validation):
            response = mr.multilevel_embed(nx.path_graph(3), nx.complete_graph(6), timeout=10)
        self.assertEqual(response['status'], 'TIMEOUT')
        self.assertGreater(response['diag']['deadline_overrun'], 0)
        if response['embedding']:
            self.assertTrue(valid(response['embedding'], nx.path_graph(3), nx.complete_graph(6)))

    def test_trimming_keeps_original_contacts(self):
        source = nx.star_graph(4)
        target = nx.complete_graph(20)
        response = mr.multilevel_embed(source, target, timeout=2)
        self.assertEqual(response['status'], 'SUCCESS')
        self.assertTrue(valid(response['embedding'], source, target))
        self.assertEqual(response['diag']['entry_qubits'], 20)
        self.assertEqual(response['diag']['trim_deletions'], 15)
        self.assertEqual(sum(map(len, response['embedding'].values())), 5)
        self.assertFalse(any('minorminer' in name or 'busclique' in name or name.startswith('ember_qc') for name in sys.modules))


if __name__ == '__main__':
    unittest.main()
