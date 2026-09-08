"""Variable connected regions, changing only addition to one atomic free path."""
from collections import Counter, deque
import hashlib
import math
from pathlib import Path
import time
import types

_path = Path(__file__).with_name('variable_regions.py')
_raw = _path.read_bytes()
_ELEMENTARY_SHA = '696ab4a6882bf33fa48db733facd0517aba2fffbcc0a3445fc389d96df6dfa68'
if hashlib.sha256(_raw).hexdigest() != _ELEMENTARY_SHA:
    raise ImportError('Unexpected elementary region source')
_elementary = types.ModuleType('_atomic_region_template')
_elementary.__file__ = str(_path)
exec(compile(_raw, str(_path), 'exec'), _elementary.__dict__)
_ordinary_propose = _elementary._propose


class _State(_elementary._State):
    def path_delta(self, u, path, record):
        """Stage one connected extension without changing any live state."""
        record['stage'] = 'path_score'
        path = tuple(path)
        if not path or len(set(path)) != len(path):
            raise AssertionError('nonempty simple path required')
        for i, q in enumerate(path):
            self.meter.tick('atomic_path_eligibility')
            if self.owner[q] != -1:
                raise AssertionError('path must be entirely unused')
            if i and q not in self.adj[path[i - 1]]:
                raise AssertionError('disconnected path')
        if not any(self.owner[p] == u for p in self.adj[path[0]]):
            raise AssertionError('path must attach to its growing owner')
        self.meter.tick('atomic_attachment_adjacency', len(self.adj[path[0]]))
        region = self.regions[u] | set(path)
        self.meter.tick('atomic_private_region_records', len(region))
        change = Counter()
        record['contact_adjacency'] = 0
        for q in path:
            for p in self.adj[q]:
                record['contact_adjacency'] += 1
                self.meter.tick('atomic_score_adjacency')
                v = self.owner[p]
                if v >= 0 and v != u:
                    change[tuple(sorted((u, v)))] += 1
        dm = 0
        for (a, b), amount in change.items():
            self.meter.tick('atomic_score_owner_pairs')
            if (a, b) in self.edges:
                dm += int(self.count[a][b] + amount == 0) - int(self.count[a][b] == 0)
        staged = self.version[u], region, dict(change)
        self.meter.check()
        record['stage'] = 'scored'
        return dm, staged

    def resize(self, u, q, sign, change):
        if not isinstance(q, tuple):
            return super().resize(u, q, sign, change)
        path, (version, region, changes) = q, change
        assert sign == len(path) and version == self.version[u]
        for site in path:
            if self.owner[site] != -1:
                raise AssertionError('staged path ownership changed')
        self.meter.tick('atomic_commit_preconditions', len(path))
        self.meter.check()
        # No cooperative interruption inside publication. Complete ownership,
        # contacts, versions and work before the unchanged search's clock check.
        self.regions[u] = region
        for site in path:
            self.owner[site] = u
        for (a, b), amount in changes.items():
            self.count[a][b] += amount
            self.count[b][a] += amount
            if (a, b) in self.edges:
                self._update_missing((a, b))
        self.q += len(path)
        self.version[u] += 1
        cost = len(path) + len(changes) + 3
        self.meter.work['atomic_commit_records'] += cost
        self.meter.units += cost


def _propose(state, kind, rng, meter, row, weight):
    if kind != 'addition':
        return _ordinary_propose(state, kind, rng, meter, row, weight)
    u, w = state.missing[rng.randrange(len(state.missing))]
    if rng.randrange(2):
        u, w = w, u
    row.update(source=u, destination=w, eligibility_checks=0, ineligible=0, scored=[])
    record = dict(stage='frontier', bfs_vertices=0, bfs_adjacency=0)
    row['atomic'] = record
    frontier = set()
    for q in sorted(state.regions[u]):
        for p in state.adj[q]:
            meter.tick('frontier_adjacency')
            if state.owner[p] == -1:
                frontier.add(p)
    roots = sorted(frontier)
    distance = state.distance(w) if roots else {}
    row['enumerated'] = len(roots)
    rng.shuffle(roots)
    rank = {q: i for i, q in enumerate(roots)}
    meter.tick('candidate_order_records', len(roots))
    roots.sort(key=lambda q: (distance.get(q, math.inf), rank[q]))
    meter.check()
    record.update(stage='bfs', roots=roots)
    parent = {q: None for q in roots}
    queue = deque(roots)
    found = None
    while queue:
        meter.check()
        q = queue.popleft()
        record['bfs_vertices'] += 1
        meter.tick('atomic_bfs_vertices')
        goal = False
        for p in state.adj[q]:
            record['bfs_adjacency'] += 1
            meter.tick('atomic_bfs_adjacency')
            if state.owner[p] == w:
                goal = True
            elif state.owner[p] == -1 and p not in parent:
                parent[p] = q
                queue.append(p)
        if goal:
            found = q
            break
    if found is None:
        meter.check()
        record['stage'] = 'no_free_path'
        row['proposal_prefix_complete'] = True
        return None
    path = []
    while found is not None:
        path.append(found)
        meter.tick('atomic_path_reconstruction')
        found = parent[found]
    path = tuple(reversed(path))
    record['path'] = list(path)
    row['eligibility_checks'] = 1
    dm, change = state.path_delta(u, path, record)
    dq = len(path)
    de = dm + dq * weight
    score = dict(site_or_owner=list(path), delta_missing=dm, delta_qubits=dq,
                 delta_energy=de, distance=distance[path[0]], seeded_rank=rank[path[0]])
    row['scored'].append(score)
    meter.check()
    row['proposal_prefix_complete'] = True
    return (de, distance[path[0]], rank[path[0]]), path, change, score


# One private copy of the common constructor/search code, with precisely these
# two bindings replaced. The separately imported elementary algorithm is intact;
# there is no second trajectory or elementary fallback invocation.
_elementary._State = _State
_elementary._propose = _propose


def atomic_embed(source, target, *, seed=0, timeout=30.0, deadline=None):
    started = time.perf_counter()
    valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    valid_deadline = deadline is None or (type(deadline) in (int, float) and math.isfinite(deadline))
    absolute = min(started + timeout, deadline) if valid_timeout and deadline is not None and valid_deadline else started + timeout if valid_timeout and valid_deadline else None
    result = _elementary.variable_embed(source, target, seed=seed, timeout=timeout,
                                        deadline=absolute if absolute is not None else deadline)
    result['diag'].update(algorithm='variable_connected_regions_atomic_growth_v1',
                          elementary_template_sha256=_ELEMENTARY_SHA)
    observed = time.perf_counter()
    result['diag']['wall'] = observed - started
    if absolute is not None:
        result['diag']['deadline_overrun'] = max(0., observed - absolute)
        if observed >= absolute:
            result.update(status='TIMEOUT', embedding={}, error='atomic wrapper exceeded common deadline')
    return result
