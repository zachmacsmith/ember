"""One disjoint partial-contact trajectory with independent growth and deletion."""
from collections import Counter, deque
import hashlib
import math
from pathlib import Path
import random
import time
import types

_path = Path(__file__).with_name('quotient_reconfiguration.py')
_raw = _path.read_bytes()
if hashlib.sha256(_raw).hexdigest() != '4fc12515fb088be951e8270dad0bc06d64b49a1b9db86037d4592776c507fec1':
    raise ImportError('Unexpected quotient helper source')
_helpers = types.ModuleType('_variable_region_helpers')
_helpers.__file__ = str(_path)
exec(compile(_raw, str(_path), 'exec'), _helpers.__dict__)
for _name in ('_Expired', '_Failed', '_Meter', '_adjacency', '_bfs', '_articulations', '_valid', '_trim'):
    globals()[_name] = getattr(_helpers, _name)


class _State(_helpers._State):
    def __init__(self, regions, src, adj, meter):
        super().__init__(regions, src, adj, meter)
        self.q = sum(map(len, regions))
        self.full_target = set(range(len(adj)))

    def removable(self, q):
        u = self.owner[q]
        if u < 0 or len(self.regions[u]) <= 1:
            return False
        cached = self.cut_cache.get(u)
        if cached is None or cached[0] != self.version[u]:
            self.meter.tick('articulation_cache_builds')
            cached = self.version[u], _articulations(self.regions[u], self.adj, self.meter)
            self.cut_cache[u] = cached
        return q not in cached[1]

    def distance(self, w):
        cached = self.distance_cache.get(w)
        if cached is None or cached[0] != self.version[w]:
            self.meter.tick('distance_cache_builds')
            cached = self.version[w], _bfs(self.full_target, self.adj, sorted(self.regions[w]), self.meter)
            self.distance_cache[w] = cached
        else:
            self.meter.tick('distance_cache_hits')
        return cached[1]

    def resize_delta(self, u, q, sign):
        assert sign in (-1, 1)
        assert self.owner[q] == (-1 if sign == 1 else u)
        change = Counter()
        for p in self.adj[q]:
            self.meter.tick('resize_score_adjacency')
            v = self.owner[p]
            if v >= 0 and v != u:
                change[tuple(sorted((u, v)))] += sign
        delta = 0
        for (a, b), d in change.items():
            assert self.count[a][b] + d >= 0
            if (a, b) in self.edges:
                delta += int(self.count[a][b] + d == 0) - int(self.count[a][b] == 0)
        return delta, dict(change)

    def resize(self, u, q, sign, change):
        self.meter.check()
        if sign == 1:
            self.regions[u].add(q)
            self.owner[q] = u
        else:
            self.regions[u].remove(q)
            self.owner[q] = -1
        self.q += sign
        for (a, b), d in change.items():
            self.count[a][b] += d
            self.count[b][a] += d
            if (a, b) in self.edges:
                self._update_missing((a, b))
        self.version[u] += 1
        cost = len(change) + 4
        self.meter.work['resize_commit_records'] += cost
        self.meter.units += cost


def _initialize(src, adj, rng, meter, diag):
    remaining, largest = set(range(len(adj))), set()
    while remaining:
        component = set(_bfs(remaining, adj, [min(remaining)], meter))
        remaining -= component
        if len(component) > len(largest):
            largest = component
    if len(largest) < len(src):
        raise _Failed('chosen largest component cannot hold the singleton initialization')
    first = _bfs(largest, adj, [min(largest)], meter)
    a = max(first, key=lambda q: (first[q], -q))
    second = _bfs(largest, adj, [a], meter)
    b = max(second, key=lambda q: (second[q], -q))
    d, center = second[b], b
    for _ in range(d // 2):
        meter.tick('center_path_vertices')
        center = min(p for p in adj[center] if p in second and second[p] == second[center] - 1)
    ranks = list(range(len(src)))
    rng.shuffle(ranks)
    tie = {u: i for i, u in enumerate(ranks)}
    order, seen = [], set()
    for root in sorted(ranks, key=lambda u: (-len(src[u]), tie[u])):
        meter.tick('source_root_candidates')
        if root in seen:
            continue
        seen.add(root)
        queue = deque([root])
        while queue:
            u = queue.popleft()
            order.append(u)
            neighbors = sorted(src[u], key=lambda v: (-len(src[v]), tie[v]))
            meter.tick('source_order_adjacency', len(neighbors))
            for v in neighbors:
                if v not in seen:
                    seen.add(v)
                    queue.append(v)
    selected, seen, queue = [center], {center}, deque([center])
    while len(selected) < len(src):
        meter.check()
        q = queue.popleft()
        neighbors = [p for p in adj[q] if p in largest and p not in seen]
        rng.shuffle(neighbors)
        meter.tick('initial_target_adjacency', len(adj[q]))
        for p in neighbors:
            seen.add(p)
            selected.append(p)
            queue.append(p)
            if len(selected) == len(src):
                break
    regions = [set() for _ in src]
    for u, q in zip(order, selected):
        regions[u].add(q)
    diag.update(source_bfs_order=order, initial_target_bfs_order=selected,
                target_center_rank=center, target_sweep_eccentricity=d,
                largest_target_component=len(largest), initial_regions=[sorted(r) for r in regions])
    meter.check()
    return regions, d


def _propose(state, kind, rng, meter, row, weight):
    """Complete the fixed eligible-score prefix; retain every partial record."""
    if kind == 'deletion':
        u, w = rng.randrange(state.n), None
    else:
        u, w = state.missing[rng.randrange(len(state.missing))]
        if rng.randrange(2):
            u, w = w, u
    row.update(source=u, destination=w, eligibility_checks=0, ineligible=0, scored=[])
    distance = {}
    if kind == 'swap':
        candidates = []
        for v in range(state.n):
            meter.tick('swap_candidate_owners')
            if v not in (u, w) and state.count[v][w] > 0:
                candidates.append(v)
    elif kind == 'deletion':
        candidates = sorted(state.regions[u])
    else:
        frontier = set()
        for q in sorted(state.regions[u]):
            for p in state.adj[q]:
                meter.tick('frontier_adjacency')
                owner = state.owner[p]
                if (owner == -1 if kind == 'addition' else owner not in (-1, u)):
                    frontier.add(p)
        candidates = sorted(frontier)
        if candidates:
            distance = state.distance(w)
    row['enumerated'] = len(candidates)
    rng.shuffle(candidates)
    rank = {q: i for i, q in enumerate(candidates)}
    meter.tick('candidate_order_records', len(candidates))
    if kind in ('transfer', 'addition'):
        candidates.sort(key=lambda q: (distance.get(q, math.inf), rank[q]))
    meter.check()
    best = None
    for q in candidates:
        row['eligibility_checks'] += 1
        meter.tick('proposal_eligibility_checks')
        if kind in ('transfer', 'deletion') and not state.removable(q):
            row['ineligible'] += 1
            continue
        if kind == 'swap':
            dm, change = state.swap_delta(u, q)
            dq = 0
        elif kind == 'transfer':
            dm, change = state.transfer_delta(q, u)
            dq = 0
        else:
            dq = 1 if kind == 'addition' else -1
            dm, change = state.resize_delta(u, q, dq)
        de = dm + dq * weight
        dist = distance.get(q) if kind in ('transfer', 'addition') else None
        score = dict(site_or_owner=q, delta_missing=dm, delta_qubits=dq,
                     delta_energy=de, distance=dist, seeded_rank=rank[q])
        row['scored'].append(score)
        key = de, (dist if dist is not None else math.inf) if kind in ('transfer', 'addition') else 0, rank[q]
        if best is None or key < best[0]:
            best = key, q, change, score
        if len(row['scored']) == 16:
            break
    meter.check()
    row['proposal_prefix_complete'] = True
    return best


def _search(state, rng, meter, diag, weight):
    diag.update(initial_missing_edges=len(state.missing), best_missing_edges=len(state.missing),
                initial_qubits=state.q, search_visits=0, visit_limit=4 * len(state.adj))
    counters = Counter()
    diag['search_counts'] = counters
    while state.missing and diag['search_visits'] < diag['visit_limit']:
        meter.check()
        step = diag['search_visits']
        kind = ('swap', 'transfer', 'addition', 'deletion')[step % 4]
        row = dict(visit=step, kind=kind, missing_before=len(state.missing), qubits_before=state.q,
                   status='started', proposal_prefix_complete=False, committed=False)
        diag['visits'].append(row)
        counters[kind + '_visits_started'] += 1
        before = time.perf_counter()
        try:
            best = _propose(state, kind, rng, meter, row, weight)
            if best is None:
                counters[kind + '_empty'] += 1
                row['status'] = 'empty'
            else:
                _, q, change, score = best
                row['selected'] = dict(score)
                de = score['delta_energy']
                draw = rng.random() if de > 0 else None
                row['acceptance_uniform'] = draw
                accepted = de <= 0 or draw < math.exp(-de / .5)
                if accepted:
                    u = row['source']
                    if kind == 'swap':
                        state.swap(u, q, change)
                    elif kind == 'transfer':
                        row['old_owner'] = state.owner[q]
                        state.transfer(q, u, change)
                    else:
                        state.resize(u, q, score['delta_qubits'], change)
                    row.update(status='committed', committed=True)
                    counters[kind + '_commits'] += 1
                    counters['uphill_commits'] += de > 0
                else:
                    row['status'] = 'rejected'
                    counters[kind + '_rejected'] += 1
            # A completed commit is recorded before observing its possible overrun.
            row.update(missing_after=len(state.missing), qubits_after=state.q)
            diag['search_visits'] += 1
            diag['best_missing_edges'] = min(diag['best_missing_edges'], len(state.missing))
            meter.check()
        except _Expired:
            row['interrupted'] = True
            if row['status'] == 'started':
                row['status'] = 'interrupted'
            raise
        finally:
            row.update(missing_after=len(state.missing), qubits_after=state.q,
                       wall=time.perf_counter() - before)
    diag['search_stop'] = 'complete_contacts' if not state.missing else 'visit_cap'


def _recount(chains, src, adj, meter):
    """Original-target contact recount, independent of the incremental matrix."""
    owner = {q: u for u, chain in chains.items() for q in chain}
    covered = set()
    for q, u in owner.items():
        for p in adj[q]:
            meter.tick('final_contact_adjacency')
            v = owner.get(p, -1)
            if v >= 0 and v != u:
                covered.add(tuple(sorted((u, v))))
    partial = [tuple(v for v in row if tuple(sorted((u, v))) in covered) for u, row in enumerate(src)]
    missing = [[u, v] for u, row in enumerate(src) for v in row if u < v and (u, v) not in covered]
    return partial, missing


def variable_embed(source, target, *, seed=0, timeout=30.0, deadline=None):
    """Return one timed trajectory; failed/late maps carry no embedding credit."""
    started = time.perf_counter()
    diag = dict(algorithm='variable_connected_regions_v1', seed=seed, stage='parameters',
                stage_wall={}, visits=[], trimming=[], trim_deletions=0,
                source_label_order='supplied node iteration; diagnostics use ranks')
    response = dict(embedding={}, status='FAILURE', diag=diag)
    state = meter = None
    chains = None
    source_labels, target_labels, src, adj = [], [], [], []
    complete = False
    absolute = None
    try:
        if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('ordinary integer seed and finite positive timeout required')
        if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
            raise ValueError('finite absolute deadline required')
        absolute = min(started + timeout, deadline) if deadline is not None else started + timeout
        reserve = min(.5, .1 * timeout)
        meter = _Meter(absolute - reserve, diag)
        diag.update(deadline=absolute, validation_reserve=reserve, search_cleanup_deadline=meter.deadline)
        rng = random.Random(seed)
        with meter.stage('input'):
            source_labels, src = _adjacency(source, meter)
            target_labels, adj = _adjacency(target, meter)
            delta = max(map(len, adj), default=0)
            lower = [max(1, (len(row) + delta - 5) // (delta - 2)) if delta > 2 else 1 for row in src]
            m, h = sum(map(len, src)) // 2, sum(map(len, adj)) // 2
            diag.update(source_nodes=len(src), target_nodes=len(adj), source_edges=m, target_edges=h,
                        maximum_target_degree=delta, degree_lower_bound=sum(lower))
            if len(src) > len(adj) or m > h or sum(lower) > len(adj):
                raise _Failed('necessary source vertex/edge/degree count bound')
            if delta <= 2 and any(len(row) > delta for row in src):
                raise _Failed('necessary source degree bound for maximum target degree at most two')
        if src:
            with meter.stage('singleton_initialization'):
                regions, d = _initialize(src, adj, rng, meter, diag)
                state = _State(regions, src, adj, meter)
                diag['occupancy_weight'] = 1. / (1 + d)
                diag['rng_after_initialization'] = repr(rng.getstate())
            with meter.stage('variable_reconfiguration'):
                _search(state, rng, meter, diag, diag['occupancy_weight'])
            if not state.missing:
                with meter.stage('entry_validation'):
                    chains = {u: set(r) for u, r in enumerate(state.regions)}
                    if not _valid(chains, src, adj, meter):
                        raise AssertionError('incremental missing contacts disagree with original validation')
                    complete = True
                    diag['entry_qubits'] = sum(map(len, chains.values()))
                try:
                    with meter.stage('trimming'):
                        _trim(chains, src, adj, meter, diag)
                    diag['trimming_stop'] = 'complete'
                except _Expired:
                    diag['trimming_stop'] = 'validation_reserve'
        else:
            chains, complete = {}, True
    except _Expired:
        response.update(status='TIMEOUT', error='construction allowance exhausted')
        diag.setdefault('search_stop', 'deadline')
    except _Failed as exc:
        response['error'] = str(exc)
    except Exception as exc:
        response.update(status='ERROR', error=type(exc).__name__ + ': ' + str(exc))

    # Use the reserved interval for the actual last state, never an unsaved best.
    try:
        if meter is not None:
            meter.deadline = absolute
            with meter.stage('final_validation'):
                if chains is None and state is not None:
                    chains = {u: set(r) for u, r in enumerate(state.regions)}
                if chains is not None:
                    partial, missing = _recount(chains, src, adj, meter)
                    structural = _valid(chains, partial, adj, meter)
                    if not structural:
                        raise AssertionError('invalid final partial-contact assignment')
                    diag.update(final_qubits=sum(map(len, chains.values())), last_missing_edges=len(missing),
                                final_missing_edges=missing, partial_contact_valid=True,
                                original_full_valid=not missing)
                    if state is not None and not complete and set(map(tuple, missing)) != set(state.missing):
                        raise AssertionError('final missing-contact recount disagrees with incremental state')
                    raw = {source_labels[u]: [target_labels[q] for q in sorted(chain)] for u, chain in chains.items()}
                    response['diagnostic_embedding'] = raw
                    if not missing and response['status'] not in ('ERROR', 'TIMEOUT'):
                        response.update(status='SUCCESS', embedding=raw)
                    elif response['status'] == 'FAILURE':
                        response.setdefault('error', 'visit cap with missing original contacts')
                    meter.check()
                diag['final_validation_complete'] = True
    except _Expired:
        response.update(status='TIMEOUT', error='final validation allowance exhausted')
    except Exception as exc:
        response.update(status='ERROR', error=type(exc).__name__ + ': ' + str(exc))
    if state is not None:
        diag['search_final_qubits'] = state.q
        diag['search_final_missing_edges'] = len(state.missing)
        diag['rng_final'] = repr(rng.getstate())
    diag['work'] = dict(meter.work) if meter else {}
    # Preserve even an incompletely certified map on interruption for diagnostics.
    if 'diagnostic_embedding' not in response and (chains is not None or state is not None):
        retained = chains if chains is not None else dict(enumerate(state.regions))
        response['diagnostic_embedding'] = {source_labels[u]: [target_labels[q] for q in sorted(r)] for u, r in retained.items()}
    observed = time.perf_counter()
    diag.update(wall=observed - started, deadline_overrun=max(0., observed - absolute) if absolute is not None else 0.)
    if absolute is not None and observed >= absolute:
        response.update(status='TIMEOUT', error='final bookkeeping exceeded common deadline')
    if response['status'] != 'SUCCESS':
        response['embedding'] = {}
    return response
