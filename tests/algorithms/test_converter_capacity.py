"""Exhaustive class-interval oracles and original-target seating checks."""
from copy import deepcopy
from functools import lru_cache
from itertools import product
import random
from types import SimpleNamespace
import unittest
from unittest import mock

import networkx as nx

from ember_qc.algorithms.factored import field


def class_oracle(arms, capacities):
    """Enumerate all class vectors; count occupied integer sites directly."""
    order = sorted(range(len(arms)), key=lambda i: (
        min(arms[i][3][0][0], arms[i][3][1][0]), arms[i][2]))
    best = None
    feasible = 0
    for classes in product((0, 1), repeat=len(arms)):
        occupancy = ({}, {})
        valid = True
        cost = 0
        for i, parity in enumerate(classes):
            lo, hi = arms[i][3][parity]
            cost += hi - lo
            for position in range(lo, hi + 1):
                count = occupancy[parity].get(position, 0) + 1
                occupancy[parity][position] = count
                if count > capacities[parity]:
                    valid = False
                    break
            if not valid:
                break
        if valid:
            feasible += 1
            value = (cost, tuple((i, classes[i]) for i in order))
            if best is None or value < best:
                best = value
    return {'feasible_vectors': feasible,
            'cost': None if best is None else best[0],
            'history': None if best is None else best[1],
            'assignment': None if best is None else dict(best[1])}


def random_interval_cases():
    rng = random.Random(3501)
    for case in range(256):
        n = 1 + case % 9
        capacities = {0: rng.randrange(5), 1: rng.randrange(5)}
        labels = rng.sample(range(100, 100 + n), n)
        arms = []
        for i in range(n):
            intervals = {}
            for parity in (0, 1):
                lo = rng.randrange(9)
                intervals[parity] = (lo, lo + rng.randrange(7))
            arms.append((0.0, 15.0, labels[i], intervals))
        yield 'random_%03d' % case, arms, capacities


def toy_grid():
    wires = {(1, 1, s): {p: ('lane', s, p) for p in range(s, 12, 2)}
             for s in (0, 1)}
    target = nx.Graph()
    crossings = {c: ('crossing', c) for c in range(12)}
    for run in wires.values():
        target.add_nodes_from(run.values())
        target.add_edges_from((run[p], run[p + 2]) for p in run if p + 2 in run)
        for c, crossing in crossings.items():
            target.add_node(crossing)
            target.add_edges_from((q, crossing) for p, q in run.items() if p <= c <= p + 1)
    return SimpleNamespace(stride=2, wire_map=wires, graph=target), crossings


@lru_cache(maxsize=1)
def actual_grid():
    import dwave_networkx as dnx
    target = dnx.zephyr_graph(12, 4, coordinates=True)
    wires = {}
    for q in target:
        u, w, k, j, z = q
        if u == 1 and w == 1:
            wires.setdefault((1, 1, 2 * k + j), {})[2 * z + j] = q
    crossings = {c: (0, c, 0, 0, 0) for c in range(25)}
    return SimpleNamespace(stride=2, wire_map=wires, graph=target), crossings


def physical_fixtures():
    yield '034_toy_infeasible', 'toy', [[1], [1], [1]]
    yield '034_toy_feasible', 'toy', [[2], [3], [3]]
    yield '034_z12_infeasible', 'z12', [[1]] * 9
    yield '034_z12_feasible', 'z12', [[2]] * 4 + [[3]] * 5
    rng = random.Random(3502)
    for n in (4, 8, 12):
        for rep in range(4):
            targets = []
            for _ in range(n):
                lo = rng.randrange(1, 24)
                hi = min(23, lo + rng.randrange(7))
                targets.append([lo] if lo == hi else [lo, hi])
            yield 'z12_%02d_%d' % (n, rep), 'z12', targets


def line_inputs(target_lists):
    items = [(float(min(ts) - 1), float(max(ts)), i) for i, ts in enumerate(target_lists)]
    targets = {v: (a, b, list(target_lists[v])) for a, b, v in items}
    return items, targets


def physical_certificate(grid, crossings, target_lists, chains):
    all_qubits = [q for chain in chains.values() for q in chain]
    membership = all(q in grid.graph for q in all_qubits)
    disjoint = len(all_qubits) == len(set(all_qubits))
    connected, covered = {}, {}
    for v, ts in enumerate(target_lists):
        chain = chains[v]
        connected[v] = bool(chain) and nx.is_connected(grid.graph.subgraph(chain))
        covered[v] = all(any(grid.graph.has_edge(q, crossings[c]) for q in chain)
                         for c in ts)
    return dict(membership=membership, disjoint=disjoint,
                connected=connected, covered=covered, qubits=len(all_qubits),
                full=sum(connected[v] and covered[v] for v in connected))


class TestClassCapacity(unittest.TestCase):
    def compare(self, arms, capacities):
        snapshot = deepcopy((arms, capacities))
        oracle = class_oracle(arms, capacities)
        assignment = field._class_interval_assignment(arms, capacities)
        self.assertEqual(assignment, oracle['assignment'] or {})
        self.assertEqual((arms, capacities), snapshot)
        if len(assignment) == len(arms):
            cost = sum(arms[i][3][p][1] - arms[i][3][p][0] for i, p in assignment.items())
            self.assertEqual(cost, oracle['cost'])
        return assignment, oracle

    def test_empty_zero_capacity_touching_and_ties(self):
        examples = [
            ([], {0: 0, 1: 0}),
            ([(0, 1, 0, {0: (0, 0), 1: (1, 1)})], {0: 0, 1: 0}),
            ([(0, 1, 0, {0: (0, 1), 1: (0, 1)}),
              (1, 2, 1, {0: (1, 2), 1: (1, 2)})], {0: 1, 1: 1}),
            ([(0, 1, 0, {0: (0, 0), 1: (1, 1)}),
              (0, 1, 1, {0: (0, 0), 1: (1, 1)}),
              (0, 1, 2, {0: (0, 0), 1: (1, 1)})], {0: 1, 1: 1}),
        ]
        for arms, caps in examples:
            with self.subTest(arms=arms, caps=caps):
                self.compare(arms, caps)

    def test_boundary_shaped_late_interval_does_not_block_disjoint_earlier_interval(self):
        arms = [(0, 8, 0, {0: (0, 8), 1: (7, 7)}),
                (0, 1, 1, {0: (0, 0), 1: (1, 1)})]
        assignment, oracle = self.compare(arms, {0: 0, 1: 1})
        self.assertEqual(assignment, {0: 1, 1: 1})
        self.assertEqual(oracle['cost'], 0)

    def test_all_predeclared_random_interval_cases_against_exhaustive_oracle(self):
        for name, arms, caps in random_interval_cases():
            with self.subTest(case=name):
                self.compare(arms, caps)

    def test_all_predeclared_actual_seatings_and_class_optima(self):
        for name, kind, target_lists in physical_fixtures():
            with self.subTest(case=name):
                grid, crossings = actual_grid() if kind == 'z12' else toy_grid()
                items, targets = line_inputs(target_lists)
                snapshot = deepcopy((items, targets))
                chains = {v: [] for v in range(len(items))}
                claimed = set()
                captured = {}
                original = field._class_interval_assignment

                def checked(arms, caps):
                    captured['oracle'] = class_oracle(arms, caps)
                    captured['assignment'] = original(arms, caps)
                    self.assertEqual(captured['assignment'], captured['oracle']['assignment'] or {})
                    return captured['assignment']

                with mock.patch.object(field, '_class_interval_assignment', checked):
                    misses, flips = field._convert_line(grid, claimed, chains, 1, 1, items, targets)
                certificate = physical_certificate(grid, crossings, target_lists, chains)
                self.assertTrue(certificate['membership'] and certificate['disjoint'])
                self.assertEqual(claimed, {q for chain in chains.values() for q in chain})
                self.assertEqual((items, targets), snapshot)
                self.assertEqual(flips, 0)  # Existing return contract, not parity-change telemetry.
                if captured['oracle']['assignment'] is not None:
                    self.assertEqual(misses, 0)
                    self.assertEqual(certificate['full'], len(items))
                    self.assertEqual(certificate['qubits'], len(items) + captured['oracle']['cost'] // 2)
                else:
                    self.assertGreater(misses, 0)
                    self.assertLess(certificate['full'], len(items))
                if name == '034_z12_feasible':
                    self.assertEqual(certificate['qubits'], 9)

    def test_class_feasibility_does_not_assert_missing_endpoint_coverage(self):
        grid, crossings = toy_grid()
        # Restrict to odd lane and crossing zero. The class interval fallback
        # is [0,0], which has no physical odd-lane endpoint here; seating emits
        # no chain. Class feasibility does not certify physical coverage.
        grid.wire_map = {k: v for k, v in grid.wire_map.items() if k[2] == 1}
        items, targets = line_inputs([[0]])
        chains = {0: []}
        field._convert_line(grid, set(), chains, 1, 1, items, targets)
        certificate = physical_certificate(grid, crossings, [[0]], chains)
        self.assertTrue(certificate['membership'] and certificate['disjoint'])
        self.assertFalse(certificate['covered'][0])


if __name__ == '__main__':
    unittest.main()
