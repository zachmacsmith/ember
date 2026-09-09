"""Bounded scheduler/R risk checks; no public constructor or native import/call."""
import ast
from collections import defaultdict
import copy
import hashlib
import importlib.util
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'packages/ember-qc/src/ember_qc/algorithms/factored'
spec = importlib.util.spec_from_file_location('ready_schedule_under_test', SRC / 'ready_lifting_schedule.py')
schedule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule)


class Stop(Exception):
    pass


def adjacency(nodes, edges):
    out = {v: set() for v in nodes}
    for a, b in edges:
        out[a].add(b); out[b].add(a)
    return out


def valid(chains, source, target, complete=False):
    if complete and set(chains) != set(source):
        return False
    owners = {}
    for v, chain in chains.items():
        if v not in source or not chain or set(chain) - set(target):
            return False
        if any(q in owners for q in chain):
            return False
        owners.update((q, v) for q in chain)
        found, todo = set(), [next(iter(chain))]
        while todo:
            q = todo.pop()
            if q in found:
                continue
            found.add(q); todo.extend((target[q] & set(chain))-found)
        if found != set(chain):
            return False
    return all(any(target[q] & set(chains[w]) for q in chains[v])
               for v in chains for w in source[v] if w in chains)


class Engine:
    def __init__(self, source, target, limit=10**9):
        self.source, self.target = copy.deepcopy(source), copy.deepcopy(target)
        self.bit = {q: 1 << i for i, q in enumerate(target)}
        self.adj_bits = {q: sum(self.bit[p] for p in ns) for q, ns in target.items()}
        self.all_bits = sum(self.bit.values())
        self.vrank = {v: v for v in source}
        self.scans, self.limit, self.now, self.deadline = 0, limit, 0, 100
        self.after_scan = lambda: None
        self.info = defaultdict(int, scheduler=schedule.diagnostics(), stopped_by=None,
                                committed_updates=[], phases=[], tried=[])
        self.action = lambda v, e: dict(e, **{}) | {v: {v}}

    def scan(self):
        if self.scans >= self.limit:
            self.info['stopped_by'] = 'work_limit'; raise Stop
        self.scans += 1
        self.after_scan()
        self.check()

    def check(self):
        if self.now >= self.deadline:
            self.info['stopped_by'] = 'deadline'; raise Stop

    def valid(self, chains, *, complete):
        return valid(chains, self.source, self.target, complete)

    def insert(self, v, entry):
        self.info['tried'].append(v)
        return self.action(v, entry)


def source_helpers():
    tree = ast.parse((SRC / 'ready_lifting_construction.py').read_text())
    names = {'_reduce', '_trial_requirements', '_set_required'}
    module = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    import heapq
    env = dict(heapq=heapq)
    exec(compile(module, '<exact-new-source-helpers>', 'exec'), env)
    return tree, env


TREE, HELPERS = source_helpers()


def run_lift(engine, journal, chains, required, original, configure=None):
    """Execute the exact new lift loop, with existing physical proposals stubbed."""
    loop = next(n for n in ast.walk(TREE) if isinstance(n, ast.While)
                and isinstance(n.test, ast.Attribute) and n.test.attr == 'remaining')
    # Public constructor, native/core setup and branch stage are never executed.
    function = ast.parse('def run(engine, journal, chains, required, original, scheduler):\n'
                         '    info=engine.info\n'
                         '    valid=False\n'
                         '    def phase(name): info["phases"].append(name)\n'
                         '    try:\n        pass\n'
                         '    except Stop:\n        pass\n'
                         '    scheduler.stop()\n'
                         '    return chains, required, valid\n').body[0]
    function.body[3].body = [copy.deepcopy(loop)]
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    env = dict(HELPERS, Stop=Stop, _helpers=types.SimpleNamespace(SCANS=20_000_000),
               transfer_site=lambda *a: (None, {}), blocked_reinsert=lambda *a: (None, None),
               _snapshot_demand=lambda *a: [], _prune_released=lambda e, c, r: (c, 0))
    if configure:
        configure(env)
    exec(compile(module, '<exact-new-lift-loop>', 'exec'), env)
    ready = schedule.ReadySchedule(engine, journal, engine.info['scheduler'])
    return env['run'](engine, journal, chains, required, original, ready)


class ReadyLiftingChecks(unittest.TestCase):
    def test_inherited_source_bodies_and_branch_ast_are_unchanged(self):
        old = ast.parse((SRC / 'site_transfer_construction.py').read_text())
        old_funcs = {n.name: n for n in old.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        new_funcs = {n.name: n for n in TREE.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        for name in old_funcs.keys() - {'reduced_core_embed'}:
            self.assertEqual(ast.dump(old_funcs[name]), ast.dump(new_funcs[name]), name)
        a = ast.parse((SRC / 'branched_path_construction.py').read_text())
        b = ast.parse((SRC / 'ready_branched_path_construction.py').read_text())
        for tree in [a, b]:
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    n.value = n.value.replace('ready_a053_retained_branch_path', 'a053_retained_branch_path').replace('fixed ready-A053', 'fixed A053')
        for name in ['_FinalMeter', 'branched_path_embed']:
            self.assertEqual(ast.dump(next(n for n in a.body if getattr(n, 'name', None) == name)),
                             ast.dump(next(n for n in b.body if getattr(n, 'name', None) == name)))
        for file, sha in [('site_transfer_construction.py', '801432d5e5d1fc1918e7eb933a3af443064ee0833030a5b962773f2b50f700a1'),
                          ('branched_path_construction.py', '3d2f6672e51a450a24a360bb562d9f6c44c325c92130d74c23c4bb505592da9b'),
                          ('branched_path_reconstruction.py', '914b6994dd54c5fa9bcc8257c6225926e66f859f0d5569740064a7ac79c882c3')]:
            self.assertEqual(hashlib.sha256((SRC/file).read_bytes()).hexdigest(), sha)

    def test_commuting_rows_shared_fill_creator_and_original_final_R(self):
        # Exact seven-node reducer fixture: K5 minus a--b plus two shared leaves.
        edges = [(a, b) for a in range(5) for b in range(a+1, 5) if (a, b) != (0, 1)]
        edges += [(v, w) for v in [5, 6] for w in [0, 1]]
        original = adjacency(range(7), edges)
        target = adjacency(range(7), edges+[(0, 1)])
        e = Engine(original, target)
        core, journal, initial, _ = HELPERS['_reduce'](e)
        self.assertEqual([r['vertex'] for r in journal], [5, 6])
        self.assertEqual(journal[0]['created_fill'], ((0, 1),))
        self.assertEqual(journal[1]['created_fill'], ())
        before = copy.deepcopy(initial)
        for order in ([0, 1], [1, 0]):
            r, chains = initial, {v: {v} for v in core}
            for i in order:
                row = journal[i]
                self.assertTrue(set(row['neighbors']) <= chains.keys())
                r = HELPERS['_trial_requirements'](r, row, e)
                chains = chains | {row['vertex']: {row['vertex']}}
                self.assertTrue(valid(chains, r, target))
            self.assertEqual(r, original)
            self.assertTrue(valid(chains, original, target, complete=True))
        self.assertEqual(initial, before)
        e = Engine(initial, target)
        chains, r, passed = run_lift(e, journal, {v: {v} for v in core}, initial, original)
        self.assertTrue(passed)
        self.assertEqual(r, original)
        self.assertEqual(e.info['scheduler']['processed_row_ids'], [1, 0])
        self.assertTrue(valid(chains, original, target, complete=True))

    def test_full_filled_dependency_zero_key_and_no_choice(self):
        target = adjacency(range(6), [(0, 1), (1, 2), (0, 3), (2, 4)])
        journal = [dict(vertex=3, neighbors=(0, 4), created_fill=()),
                   dict(vertex=4, neighbors=(2,), created_fill=())]
        e = Engine(adjacency(range(5), []), target)
        s = schedule.ReadySchedule(e, journal, e.info['scheduler'])
        i, rec = s.choose({0: {0}, 2: {2}})
        self.assertEqual(i, 1); self.assertIsNone(rec['direct_singletons'])
        self.assertEqual(rec['keys'], []); self.assertEqual(e.info['scheduler']['bigint_operations_completed'], 0)
        s.prepare_commit(i, rec); s.commit(i, rec)
        i, _ = s.choose({0: {0}, 2: {2}, 4: {4}})
        self.assertEqual(i, 0)
        # A zero direct domain wins over a nonempty one; no feasibility claim follows.
        journal = [dict(vertex=3, neighbors=(0, 2), created_fill=()),
                   dict(vertex=4, neighbors=(0,), created_fill=())]
        target = adjacency(range(6), [(0, 1), (2, 4)])
        e = Engine(adjacency(range(5), []), target)
        s = schedule.ReadySchedule(e, journal, e.info['scheduler'])
        i, rec = s.choose({0: {0}, 2: {2}})
        self.assertEqual((i, rec['direct_singletons']), (0, 0))
        self.assertEqual([x['direct_singletons'] for x in rec['keys']], [0, 1])
        self.assertEqual(e.info['scheduler']['first_departure']['legacy_pending_index'], 1)

    def test_failed_selected_row_never_retries_and_prior_nonprefix_R_survives(self):
        target = adjacency(range(8), [(a, b) for a in range(8) for b in range(a+1, 8)])
        original = adjacency(range(5), [(0, 2), (0, 3), (1, 3), (1, 4)])
        journal = [dict(vertex=3, neighbors=(0, 1), created_fill=()),
                   dict(vertex=4, neighbors=(1,), created_fill=())]
        # Make row0 more constrained than legacy row1, then block only row1.
        target[0].remove(7); target[7].remove(0)
        e = Engine(original, target)
        saved = {0: {0}, 1: {1}, 2: {2}}
        e.action = lambda v, c: (c | {v: {v}}) if v == 3 else None
        chains, r, passed = run_lift(e, journal, copy.deepcopy(saved), copy.deepcopy(original), original)
        self.assertFalse(passed); self.assertEqual(e.info['tried'], [3, 4])
        self.assertEqual(e.info['scheduler']['processed_row_ids'], [0])
        self.assertEqual(e.info['failed_insertion']['journal_index'], 1)
        self.assertEqual(set(chains), {0, 1, 2, 3}); self.assertEqual(r, original)
        self.assertTrue(valid(chains, r, target)); self.assertEqual(saved, {0: {0}, 1: {1}, 2: {2}})
        # Failure on the first choice must not fall through to the other ready row.
        e = Engine(original, target); e.action = lambda *a: None
        chains, r, passed = run_lift(e, journal, copy.deepcopy(saved), copy.deepcopy(original), original)
        self.assertEqual(e.info['tried'], [3]); self.assertEqual(chains, saved)
        self.assertEqual(e.info['scheduler']['processed_row_ids'], [])

    def test_selected_insertion_and_admission_deadline_rollback(self):
        target = adjacency(range(4), [(a, b) for a in range(4) for b in range(a+1, 4)])
        original = adjacency(range(4), [(0, 2), (1, 2), (0, 3), (1, 3)])
        required = copy.deepcopy(original); required[0].add(1); required[1].add(0)
        journal = [dict(vertex=2, neighbors=(0, 1), created_fill=((0, 1),)),
                   dict(vertex=3, neighbors=(0, 1), created_fill=())]
        entry = {0: {0}, 1: {1}}
        for boundary in ['insertion', 'admission']:
            e = Engine(required, target)
            def action(v, c):
                if v == 2 and boundary == 'insertion':
                    e.now = e.deadline; e.check()
                return c | {v: {v}}
            e.action = action
            def after():
                rec = e.info['scheduler']['selections'][-1]
                if boundary == 'admission' and rec['selected_row'] == 0 and e.info['scheduler']['work_by_kind'].get('retirement', 0) > 3:
                    e.now = e.deadline
            e.after_scan = after
            chains, r, _ = run_lift(e, journal, copy.deepcopy(entry), copy.deepcopy(required), original)
            self.assertEqual(e.info['scheduler']['processed_row_ids'], [1])
            self.assertEqual(chains, entry | {3: {3}})
            self.assertIn(1, r[0]); self.assertTrue(valid(chains, r, target))
            self.assertFalse(e.info['scheduler']['selections'][-1]['committed'])
            self.assertEqual(e.info['stopped_by'], 'deadline')

    def test_interrupted_keys_have_no_winner_and_all_word_charges_survive(self):
        target = adjacency(range(65), [(0, 2), (0, 3), (1, 4)])
        journal = [dict(vertex=8, neighbors=(0,), created_fill=()),
                   dict(vertex=9, neighbors=(1,), created_fill=())]
        for clock_stop in [False, True]:
            e = Engine(adjacency(range(10), []), target)
            s = schedule.ReadySchedule(e, journal, e.info['scheduler'])
            def after():
                if s.current and len(s.current['keys']) == 1:
                    if clock_stop: e.now = e.deadline
                    else: e.limit = e.scans
            e.after_scan = after
            with self.assertRaises(Stop): s.choose({0: {0}, 1: {1}})
            rec = s.current
            self.assertTrue(rec['ready_complete']); self.assertFalse(rec['keys_complete'])
            self.assertEqual(len(rec['keys']), 1); self.assertIsNone(rec['selected_row'])
            self.assertEqual(s.processed, set())
            self.assertEqual(e.scans, s.info['work'])
            self.assertEqual(sum(s.info['work_by_kind'].values()), s.info['work'])
            self.assertGreater(s.words, 1)


if __name__ == '__main__':
    unittest.main()
