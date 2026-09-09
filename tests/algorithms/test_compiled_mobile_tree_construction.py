"""B028's specific semantic/packing/deadline risks; no full constructors run."""
import ast
import importlib.abc
import importlib.util
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'packages/ember-qc/src/ember_qc/algorithms/factored'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pilot = load('b028_check_pilot', ROOT / 'scripts/codex/pilot.py')
blocker = pilot.NoExternalEmbedder()
sys.meta_path.insert(0, blocker)
reference = load('b028_reference', BASE / 'recurrence_mobile_tree_construction.py')
candidate = load('b028_candidate', BASE / 'compiled_mobile_tree_construction.py')
helper = load('b028_check_helpers', ROOT / 'tests/algorithms/test_mobile_tree_construction.py')
oracle = load('b028_original_oracle', ROOT / 'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py')


def engines(G, H, mapping=None, seed=0):
    result = []
    for module in (reference, candidate):
        e = module._Engine(G, H, module._Meter(time.perf_counter() + 60), seed)
        if mapping is not None:
            e.state = helper.state(e, mapping)
        result.append(e)
    return result


def route_projection(result):
    if result is None:
        return None
    root, distances, parents, stats = result
    return (root, [(u, list(row.items())) for u, row in distances.items()],
            [(u, list(row.items())) for u, row in parents.items()], stats)


def paired_route(test, pair, neighbors, mapping, occupancy, quality):
    routes = [e.joint_root(neighbors, mapping, occupancy, quality) for e in pair]
    test.assertEqual(route_projection(routes[0]), route_projection(routes[1]))
    if routes[0] is not None:
        chains = [e.attach(route[0], neighbors, mapping, route[1], route[2])
                  for e, route in zip(pair, routes)]
        test.assertEqual(chains[0], chains[1])
    return routes


def full_valid(e):
    edges = lambda adj: {(u, v) for u in adj for v in adj[u] if u < v}
    return oracle.embedding_quality({str(u): list(s) for u, s in e.state.chains.items()},
                                   e.G, edges(e.G), e.H, edges(e.H))[0]


class CompiledRoutingChecks(unittest.TestCase):
    def test_01_exact_ranked_routes_parents_order_and_successive_queries(self):
        G = helper.graph(3, [(0, 1), (0, 2)])
        shapes = [helper.path(7), helper.graph(6, [(u, (u + 1) % 6) for u in range(6)]),
                  helper.graph(7, [(u, u + 1) for u in range(6)] + [(1, 4), (2, 5)])]
        for H in shapes:
            for seed in (0, 17):
                pair = engines(G, H, {1: [0], 2: [len(H) - 1]}, seed)
                neighbors = sorted((1, 2), key=pair[0].srank.__getitem__)
                for quality in (False, True, False):
                    for e in pair:
                        e.prices = {0: 7 if quality else 3, 1: 2, len(H) - 1: 11}
                    occupancy = {0: frozenset()} if quality else {}
                    paired_route(self, pair, neighbors, pair[0].state.chains, occupancy, quality)
        # Labels larger than int64, and negative labels, never enter compiled indices.
        source_labels = {0: -40, 1: 2 ** 80, 2: 6}
        target_labels = {i: (2 ** 82 + 7 * i if i % 2 else -50 * (i + 1)) for i in range(7)}
        convert = lambda adj, labels: {labels[u]: {labels[v] for v in row} for u, row in adj.items()}
        pair = engines(convert(G, source_labels), convert(helper.path(7), target_labels),
                       {source_labels[1]: [target_labels[0]], source_labels[2]: [target_labels[6]]}, 17)
        neighbors = sorted((source_labels[1], source_labels[2]), key=pair[0].srank.__getitem__)
        paired_route(self, pair, neighbors, pair[0].state.chains, {}, False)

    def test_02_disconnection_empty_boundary_and_no_neighbor(self):
        G = helper.graph(3, [(0, 1), (0, 2)])
        pair = engines(G, helper.graph(5, [(0, 1), (2, 3)]), {1: [0], 2: [2]})
        paired_route(self, pair, [1, 2], pair[0].state.chains, {}, True)
        pair = engines(G, helper.graph(5, [(0, 1), (1, 2)]), {1: [4], 2: [2]})
        paired_route(self, pair, [1, 2], pair[0].state.chains, {}, True)
        pair = engines(G, helper.path(5), {1: [0], 2: [4]})
        paired_route(self, pair, [], pair[0].state.chains, {}, False)
        self.assertFalse(hasattr(pair[1], '_b028_kernel'))

    def test_03_integer_admission_and_unchanged_arithmetic_fallback(self):
        pair = engines(helper.graph(3, [(0, 1), (0, 2)]), helper.path(7), {1: [0], 2: [6]})
        paired_route(self, pair, [1, 2], pair[0].state.chains, {}, False)
        kernel = pair[1]._b028_kernel
        self.assertTrue(kernel.range_safe(7, 2, kernel.INF // 21 - 1, 12))
        self.assertFalse(kernel.range_safe(7, 2, kernel.INF // 21 + 1, 12))
        self.assertFalse(kernel.range_safe(7, 2, -1, 12))
        for max_cost, fallback in [(kernel.INF // 21 - 1, False), (kernel.INF // 21 + 1, True)]:
            for e in pair:
                e.prices = {0: max_cost - 1, 6: max_cost - 1}
            paired_route(self, pair, [1, 2], pair[0].state.chains, {}, False)
            self.assertEqual(pair[1].acceleration['last_query']['fallback'], fallback)

    def test_04_stale_before_stop_and_equal_score_root_tie(self):
        pair = engines(helper.path(2), helper.path(3), {1: [0]})
        pair[1].joint_root([1], pair[1].state.chains, {}, False)
        k = pair[1]._b028_kernel
        np = k.np
        d = np.asarray([[2, 2]], dtype=np.int64)
        settled = np.asarray([[k.INF, 2]], dtype=np.int64)
        parent = np.full((1, 2), -1, dtype=np.int64)
        discovered = np.asarray([[1, 0]], dtype=np.int64)
        discovery_counts = np.asarray([2], dtype=np.int64)
        order = np.asarray([[1, -1]], dtype=np.int64)
        counts = np.asarray([1], dtype=np.int64)
        sums = np.asarray([0, 2], dtype=np.int64)
        reached = np.asarray([0, 1], dtype=np.int64)
        heap = k.List.empty_list(k.HEAP_TYPE)
        for entry in [(2, 0, 0, 0, 0), (5, 0, 1, 0, 1)]:
            heap.append(tuple(map(np.int64, entry)))  # already a valid two-item min heap
        control = np.asarray([2, 1, 0, -1], dtype=np.int64)
        work = np.zeros(5, dtype=np.int64)
        done = k._advance(np.asarray([0, 0, 0], dtype=np.int64), np.asarray([], dtype=np.int64),
            np.asarray([1, 1], dtype=np.int64), np.asarray([0], dtype=np.int64),
            d, settled, parent, discovered, discovery_counts, order, counts,
            sums, reached, heap, control, work, np.int64(256))
        self.assertTrue(done)
        self.assertEqual(tuple(map(int, control[:3])), (2, 0, 0))
        self.assertEqual(int(work[1]), 2)
        self.assertEqual(int(work[2]), 1)

    def test_05_completed_proposals_preserve_chains_witnesses_and_original_validity(self):
        fixtures = [(helper.path(3), helper.path(5), {0: [0], 1: [1, 2, 3], 2: [4]}),
            (helper.graph(3, [(0, 1), (1, 2), (0, 2)]),
             helper.graph(5, [(u, (u + 1) % 5) for u in range(5)]),
             {0: [0], 1: [1, 2], 2: [3, 4]})]
        for G, H, mapping in fixtures:
            pair = engines(G, H, mapping)
            for e in pair:
                e.quality = True; e.began = time.perf_counter()
                self.assertTrue(full_valid(e))
            for owner in (0, 1, 2):
                outcomes = [e.visit(owner) for e in pair]
                self.assertEqual(*outcomes)
                self.assertEqual(pair[0].state.chains, pair[1].state.chains)
                self.assertEqual(pair[0].state.witnesses, pair[1].state.witnesses)
                self.assertEqual(pair[0].state.trees, pair[1].state.trees)
                self.assertEqual(pair[0].state.owners, pair[1].state.owners)
                self.assertEqual(pair[0].state.score(), pair[1].state.score())
                self.assertTrue(full_valid(pair[1]))

    def test_06_interrupted_chunk_keeps_private_query_unpublished(self):
        pair = engines(helper.graph(3, [(0, 1), (0, 2)]), helper.path(800), {1: [0], 2: [799]})
        e = pair[1]
        # Load/compile through a separate tiny query first: this is a deadline
        # injection check, never used as a headline timing or constructor warmup.
        tiny = engines(helper.path(2), helper.path(3), {1: [0]})[1]
        tiny.joint_root([1], tiny.state.chains, {}, False)
        kernel = tiny._b028_kernel
        original = kernel._advance
        invocations = []
        def interrupted(*args):
            answer = original(*args)
            invocations.append(bool(answer))
            e.m.deadline = -1
            return answer
        interrupted.signatures = original.signatures
        before = e.state
        with patch.object(kernel, '_advance', interrupted):
            with self.assertRaises(candidate._Stop):
                e.joint_root([1, 2], e.state.chains, {}, True)
        self.assertEqual(invocations, [False])
        self.assertIs(e.state, before)
        self.assertFalse(e.acceleration['last_query']['complete'])
        self.assertEqual(e.acceleration['last_query']['semantic_work']['heap_pop'], 256)
        self.assertEqual(e.acceleration['incomplete_queries'], 1)

    def test_07_exact_inherited_methods_and_dependency_isolation(self):
        old = ast.parse((BASE / 'recurrence_mobile_tree_construction.py').read_text())
        new = ast.parse((BASE / 'compiled_mobile_tree_construction.py').read_text())
        nodes = lambda tree: {node.name: node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
        a, b = nodes(old), nodes(new)
        self.assertEqual(set(a), set(b))
        for name in set(a) - {'_Engine', 'contact_embed'}:
            self.assertEqual(ast.dump(a[name]), ast.dump(b[name]))
        old_methods, new_methods = nodes(a['_Engine']), nodes(b['_Engine'])
        self.assertEqual(set(new_methods) - set(old_methods), {'_python_joint_root'})
        for name in set(old_methods) - {'joint_root'}:
            self.assertEqual(ast.dump(old_methods[name]), ast.dump(new_methods[name]))
        old_methods['joint_root'].name = '_python_joint_root'
        self.assertEqual(ast.dump(old_methods['joint_root']), ast.dump(new_methods['_python_joint_root']))
        # Public wrapper differs only in identity and the passive acceleration receipt.
        old_text = ast.unparse(a['contact_embed'])
        new_text = ast.unparse(b['contact_embed'])
        new_text = new_text.replace("algorithm='compiled-mobile-tree-construction', version='B028'",
                                    "algorithm='recurrence-mobile-tree-construction', version='B027'")
        new_text = new_text.replace(", acceleration=getattr(engine, 'acceleration', None)", '')
        self.assertEqual(old_text, new_text)
        self.assertEqual(blocker.attempts, [])
        self.assertFalse(any('minorminer' in name.lower() or name.split('.')[0] == 'busclique'
                             for name in sys.modules))


if __name__ == '__main__':
    unittest.main(verbosity=2)
