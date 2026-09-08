"""Track C002: connected matching, admissible split seeds and soft balancing.

This module uses structural helpers from V1, never its embedding constructor.
"""
from collections import Counter
import hashlib
import math
from pathlib import Path
import random
import time
import types


# Pilot constructors are loaded as standalone files, without importing the
# Ember package. Bind only exact, frozen sibling utility bytes; no V1 call.
_helper_path = Path(__file__).with_name('multilevel_regions.py')
_helper_bytes = _helper_path.read_bytes()
if hashlib.sha256(_helper_bytes).hexdigest() != '1f8d947b232ef458e4d908f138bce8d5d1a9b00d5cb4b983929f7feb5759d973':
    raise ImportError('Multilevel structural helper source identity changed')
_helpers = types.ModuleType('_multilevel_structural_helpers_v1')
_helpers.__file__ = str(_helper_path)
exec(compile(_helper_bytes, str(_helper_path), 'exec'), _helpers.__dict__)
for _name in ('_Expired', '_Failed', '_Meter', '_adjacency', '_bfs', '_tree',
              '_connected', '_articulations', '_valid', '_trim'):
    globals()[_name] = getattr(_helpers, _name)


def _hierarchy(src, lower, rng, meter, diag):
    n = len(src)
    members = {i: frozenset([i]) for i in range(n)}
    weight = dict(enumerate(lower))
    active = list(range(n))
    source_owner = list(range(n))
    merges = []
    next_id = n
    while len(active) > 1:
        meter.check()
        links = {v: Counter() for v in active}
        for u, neighbors in enumerate(src):
            for v in neighbors:
                meter.tick('coarsening_source_adjacency')
                a, b = source_owner[u], source_owner[v]
                if a != b:
                    links[a][b] += 1
        tie = list(active)
        rng.shuffle(tie)
        rank = {v: i for i, v in enumerate(tie)}
        order = sorted(active, key=lambda a: (weight[a], rank[a]))
        unused = set(active)
        new = []
        for a in order:
            meter.tick('coarsening_aggregates')
            if a not in unused:
                continue
            unused.remove(a)
            if not unused:
                new.append(a)
                continue
            linked = [b for b in links[a] if b in unused]
            if not linked and any(links[v] for v in active):
                new.append(a)
                continue
            b = min(linked or unused, key=lambda b: (-links[a][b], weight[b], rank[b]))
            unused.remove(b)
            c = next_id
            next_id += 1
            members[c] = members[a] | members[b]
            weight[c] = weight[a] + weight[b]
            merges.append((c, a, b))
            for u in members[c]:
                meter.tick('coarsening_owner_updates')
                source_owner[u] = c
            new.append(c)
        active = new
        diag['coarsening_levels'] += 1
    return active[0], members, weight, merges


def _split(region, req, minimum, weight, adj, owners, rng, meter, record):
    """Carve child A from B without disconnecting either or losing B contacts."""
    record.update(region_sites=len(region), minimum=minimum, required=[sorted(x) for x in req], attempts=[])
    if len(region) < sum(minimum):
        record['reason'] = 'insufficient_region_capacity'
        return None
    contact = {}
    for q in region:
        meter.tick('split_contact_sites')
        contact[q] = {owners[p] for p in adj[q] if p not in region and owners[p] >= 0}
        meter.tick('split_contact_adjacency', len(adj[q]))
    total = Counter(v for q in region for v in contact[q])
    if any(total[v] == 0 for needed in req for v in needed):
        record['reason'] = 'missing_parent_contact'
        return None
    desired = max(minimum[0], min(len(region)-minimum[1],
                  int(len(region) * weight[0] / sum(weight) + .5)))
    record['desired_child_a'] = desired
    shuffled = sorted(region)
    rng.shuffle(shuffled)
    rank = {q: i for i, q in enumerate(shuffled)}
    seed_order = sorted(region, key=lambda q: (-len(contact[q] & req[0]), rank[q]))
    if not req[0]:
        distance = _bfs(region, adj, [seed_order[0]], meter)
        first = max(region, key=lambda q: (distance[q], -rank[q]))
        seed_order.remove(first)
        seed_order.insert(0, first)
    cut = _articulations(region, adj, meter)
    eligible = []
    for q in seed_order:
        meter.tick('seed_prefilter_sites')
        if q not in cut and all(total[v] > 1 for v in contact[q] & req[1]):
            eligible.append(q)
    record['seed_pool'] = dict(ranked=len(seed_order), eligible=len(eligible), rejected=len(seed_order)-len(eligible))
    for seed in eligible[:6]:
        meter.check()
        attempt = {'seed': seed, 'transfers': 0, 'tree_rebuilds': 0, 'status': 'running'}
        record['attempts'].append(attempt)
        before = time.perf_counter()
        try:
            a, b = {seed}, region - {seed}
            if len(b) < minimum[1] or not _connected(b, adj, meter):
                attempt['status'] = 'seed_disconnects_donor'
                continue
            counts = total.copy()
            counts.subtract(contact[seed])
            if any(counts[v] < 1 for v in req[1]):
                attempt['status'] = 'seed_consumes_required_donor_contact'
                continue
            covered = contact[seed] & req[0]
            missing = req[0] - covered
            root = max(b, key=lambda q: rank[q])
            parent, children = _tree(b, adj, root, meter)
            frontier = set(adj[seed]) & b
            from_seed = _bfs(region, adj, [seed], meter)
            distance = {}
            needs_refresh = True
            while missing or len(a) < desired:
                meter.tick('split_growth_steps')
                if len(b) <= minimum[1]:
                    attempt['status'] = 'donor_capacity_exhausted'
                    break
                if needs_refresh:
                    goals = [q for q in b if contact[q] & missing]
                    meter.tick('split_distance_goal_scans', len(b))
                    distance = _bfs(b, adj, goals, meter) if missing else {}
                    needs_refresh = False
                allowed = []
                for q in frontier:
                    meter.tick('split_frontier_candidates')
                    if all(counts[v] > 1 for v in contact[q] & req[1]):
                        allowed.append(q)
                def score(q):
                    return (-len(contact[q] & missing), distance.get(q, len(region)) if missing else 0,
                            from_seed[q], rank[q])
                leaves = [q for q in allowed if children[q] == 0 and parent[q] is not None]
                rebuild = False
                if leaves:
                    q = min(leaves, key=score)
                else:
                    cut = _articulations(b, adj, meter)
                    movable = [q for q in allowed if q not in cut]
                    if not movable:
                        attempt['status'] = 'no_safe_boundary_transfer'
                        break
                    q = min(movable, key=score)
                    rebuild = True
                a.add(q)
                b.remove(q)
                counts.subtract(contact[q])
                newly = contact[q] & missing
                missing -= newly
                needs_refresh = bool(newly)
                frontier.discard(q)
                frontier.update(p for p in adj[q] if p in b)
                attempt['transfers'] += 1
                meter.tick('split_transfers')
                if rebuild:
                    root = root if root in b else min(b)
                    parent, children = _tree(b, adj, root, meter)
                    attempt['tree_rebuilds'] += 1
                else:
                    children[parent[q]] -= 1
                    del parent[q]
            if not missing and len(a) >= minimum[0] and len(b) >= minimum[1]:
                attempt['balanced_target_reached'] = len(a) >= desired
                attempt['balancing_stop'] = attempt['status'] if attempt['status'] != 'running' else None
                if not _connected(a, adj, meter) or not _connected(b, adj, meter):
                    raise AssertionError('connected-transfer invariant violated')
                if any(not any(v in contact[q] for q in a) for v in req[0]):
                    raise AssertionError('recipient contact invariant violated')
                if any(not any(v in contact[q] for q in b) for v in req[1]):
                    raise AssertionError('donor contact invariant violated')
                meter.check()
                attempt.update(status='accepted', child_sizes=[len(a), len(b)])
                record['reason'] = 'accepted'
                return a, b
            attempt.update(child_sizes=[len(a), len(b)], missing_contacts=sorted(missing))
        except _Expired:
            attempt['status'] = 'deadline'
            raise
        finally:
            attempt['wall'] = time.perf_counter() - before
    record['reason'] = 'local_seed_attempts_exhausted'
    return None



def multilevel_embed(source, target, *, seed=0, timeout=30.0, deadline=None):
    """Construct a minor under one common deadline; return explicit failure data."""
    started = time.perf_counter()
    diag = {'algorithm': 'multilevel_connected_regions_v2', 'seed': seed,
            'stage': 'parameters', 'stage_wall': {}, 'coarsening_levels': 0,
            'splits': [], 'trimming': [], 'trim_deletions': 0,
            'source_label_order': 'supplied node iteration, diagnostic IDs are ranks',
            'target_scope': 'largest connected component; no infeasibility claim on failure'}
    response = {'embedding': {}, 'status': 'FAILURE', 'diag': diag}
    regions, members, source_labels, target_labels, src, adj = {}, {}, [], [], [], []
    meter = None
    try:
        if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('finite positive timeout and ordinary integer seed required')
        if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
            raise ValueError('deadline must be a finite absolute timestamp')
        deadline = min(started + timeout, deadline) if deadline is not None else started + timeout
        diag['deadline'] = deadline
        meter = _Meter(deadline, diag)
        rng = random.Random(seed)
        with meter.stage('input'):
            source_labels, src = _adjacency(source, meter)
            target_labels, adj = _adjacency(target, meter)
            delta = max(map(len, adj), default=0)
            lower = [max(1, (len(neighbors)-2+delta-3)//(delta-2)) if delta > 2 else 1 for neighbors in src]
            diag.update(source_nodes=len(src), target_nodes=len(adj), maximum_target_degree=delta,
                        degree_lower_bound=sum(lower))
            if len(src) > len(adj) or sum(lower) > len(adj):
                raise _Failed('necessary target vertex capacity bound')
        if not src:
            response['status'] = 'SUCCESS'
        else:
            with meter.stage('coarsening'):
                root, members, weight, merges = _hierarchy(src, lower, rng, meter, diag)
            with meter.stage('initial_region'):
                remaining = set(range(len(adj)))
                largest = set()
                while remaining:
                    component = set(_bfs(remaining, adj, [min(remaining)], meter))
                    remaining -= component
                    if len(component) > len(largest):
                        largest = component
                if len(largest) < sum(lower):
                    raise _Failed('largest component has insufficient reserved capacity')
                regions[root] = largest
                owners = [-1] * len(adj)
                for q in largest:
                    owners[q] = root
                source_owner = [root] * len(src)
            with meter.stage('uncoarsening'):
                for parent_id, a, b in reversed(merges):
                    meter.check()
                    required = []
                    for child in (a, b):
                        wanted = set()
                        for u in members[child]:
                            for v in src[u]:
                                meter.tick('quotient_source_adjacency')
                                if source_owner[v] != parent_id:
                                    wanted.add(source_owner[v])
                        required.append(wanted)
                    row = {'parent': parent_id, 'children': [a, b],
                           'source_sizes': [len(members[a]), len(members[b])],
                           'index': len(diag['splits'])}
                    diag['splits'].append(row)
                    result = _split(regions[parent_id], required, [weight[a], weight[b]],
                                    [weight[a], weight[b]], adj, owners, rng, meter, row)
                    if result is None:
                        raise _Failed('split failed at aggregate ' + str(parent_id) + ': ' + row['reason'])
                    ra, rb = result
                    # Connected partition of connected parent guarantees an A--B
                    # edge, whether or not the corresponding source edge exists.
                    regions[a], regions[b] = ra, rb
                    del regions[parent_id]
                    for child in (a, b):
                        for u in members[child]:
                            source_owner[u] = child
                        for q in regions[child]:
                            owners[q] = child
                            meter.tick('uncoarsening_owner_updates')
            with meter.stage('entry_validation'):
                if not _valid(regions, src, adj, meter):
                    raise AssertionError('complete region partition is not a source minor')
                diag['entry_qubits'] = sum(map(len, regions.values()))
            with meter.stage('trimming'):
                _trim(regions, src, adj, meter, diag)
            with meter.stage('final_validation'):
                if not _valid(regions, src, adj, meter):
                    raise AssertionError('site deletion corrupted the minor')
                response['embedding'] = {source_labels[v]: [target_labels[q] for q in sorted(regions[v])] for v in range(len(src))}
                meter.check()
            response['status'] = 'SUCCESS'
    except _Expired:
        response['status'] = 'TIMEOUT'
        response['error'] = 'common construction deadline reached'
    except _Failed as exc:
        response['error'] = str(exc)
    except Exception as exc:
        response['status'] = 'ERROR'
        response['error'] = type(exc).__name__ + ': ' + str(exc)
    if response['status'] != 'SUCCESS':
        # Aggregate regions are diagnostics, not a mapping of original vertices.
        diag['partial_regions'] = [dict(aggregate=v, source_ranks=sorted(members.get(v, [])),
                                        target_ranks=sorted(region)) for v, region in sorted(regions.items())]
    diag['work'] = dict(meter.work) if meter else {}
    diag['wall'] = time.perf_counter() - started
    diag['deadline_overrun'] = max(0., time.perf_counter()-deadline) if meter else 0.
    if meter and time.perf_counter() >= deadline:
        response['status'] = 'TIMEOUT'
    return response
