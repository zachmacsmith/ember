"""Joint path reassignment retaining each owner's fixed off-route branches.

The caller supplies a valid complete minor and the existing authoritative
structural validator. This module never constructs an initial embedding.
"""
from collections import Counter, deque
from collections.abc import Mapping, Sequence
import math
import time

SEEDS = 8
OWNERS = 128
ROUTE = 512
ATTEMPTS = 32
WORK = 1_000_000


class _Stop(Exception):
    def __init__(self, reason):
        self.reason = reason


class _Meter:
    def __init__(self, deadline, limit):
        self.deadline, self.limit = deadline, limit
        self.started = self.phase_started = time.perf_counter()
        self.phase = 'setup'
        self.work = 0
        self.counts, self.by_stage, self.walls = Counter(), Counter(), Counter()

    def timely(self):
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise _Stop('deadline')

    def tick(self, kind='site'):
        self.timely()
        if self.work >= self.limit:
            raise _Stop('work_limit')
        self.work += 1
        self.counts[kind] += 1
        self.by_stage[self.phase] += 1

    def set_phase(self, phase):
        now = time.perf_counter()
        self.walls[self.phase] += now - self.phase_started
        self.phase, self.phase_started = phase, now

    def copy(self, values):
        result = []
        for value in values:
            self.tick('copy')
            result.append(value)
        return result

    def finish(self):
        ended = time.perf_counter()
        self.walls[self.phase] += ended - self.phase_started
        return dict(work=self.work, work_limit=self.limit, work_counts=dict(self.counts),
                    work_by_stage=dict(self.by_stage), wall_by_stage=dict(self.walls),
                    wall=ended-self.started, ended=ended,
                    timely=self.deadline is None or ended < self.deadline,
                    deadline_overrun=max(0., ended-self.deadline) if self.deadline is not None else 0.)


class _ReadSequence(Sequence):
    def __init__(self, values, meter):
        self.values, self.meter = values, meter

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        self.meter.tick('validation_site')
        return self.values[index]

    def __iter__(self):
        for value in self.values:
            self.meter.tick('validation_site')
            yield value


class _ReadMap(Mapping):
    def __init__(self, values, meter):
        self.values, self.meter = values, meter

    def __iter__(self):
        for value in self.values:
            self.meter.tick('validation_key')
            yield value

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        self.meter.tick('validation_lookup')
        return _ReadSequence(self.values[key], self.meter)


class _ReadSource:
    def __init__(self, source, ranks, meter):
        self.source, self.ranks, self.meter = source, ranks, meter

    def __iter__(self):
        for v in self.source:
            self.meter.tick('validation_key')
            yield v

    def edges(self):
        for v, neighbors in self.source.items():
            for w in neighbors:
                self.meter.tick('validation_edge')
                if self.ranks[v] < self.ranks[w]:
                    yield v, w


class _Context:
    def __init__(self, embedding, source, target, validator, meter):
        self.m, self.validator = meter, validator
        self.vrank = {v: i for i, v in enumerate(meter.copy(source))}
        self.qrank = {q: i for i, q in enumerate(meter.copy(target))}
        self.source = {v: tuple(sorted(meter.copy(row), key=self.vrank.__getitem__))
                       for v, row in source.items()}
        self.target = {q: tuple(sorted(meter.copy(row), key=self.qrank.__getitem__))
                       for q, row in target.items()}
        self.entry = {v: meter.copy(chain) for v, chain in embedding.items()}

    def certificate(self, embedding):
        self.m.set_phase('certificate')
        return self.validator(_ReadMap(embedding, self.m),
                              _ReadSource(self.source, self.vrank, self.m),
                              _ReadMap(self.target, self.m))

    def owner(self, embedding):
        result = {}
        for v, chain in embedding.items():
            for q in chain:
                self.m.tick()
                result[q] = v
        return result

    def qubits(self, embedding):
        total = 0
        for chain in embedding.values():
            self.m.tick('size_key')
            total += len(chain)
        return total

    def paths(self):
        self.m.set_phase('path_generation')
        lengths = {}
        for v, chain in self.entry.items():
            self.m.tick()
            if len(chain) > 1:
                lengths[v] = len(chain)
        seeds = sorted(lengths, key=lambda v: (-lengths[v], self.vrank[v]))[:SEEDS]
        paths, seen = [], set()
        for seed in seeds:
            path, members = [seed], {seed}
            while len(path) < OWNERS:
                candidates = []
                for end, v in enumerate((path[0], path[-1])):
                    for w in self.source[v]:
                        self.m.tick('source_edge')
                        if w in members:
                            continue
                        hits = 0
                        for z in self.source[w]:
                            self.m.tick('source_edge')
                            hits += z in members
                        if hits == 1:
                            candidates.append((-len(self.entry[w]), self.vrank[w], end, w))
                if not candidates:
                    break
                _, _, end, w = min(candidates)
                path.insert(0 if end == 0 else len(path), w)
                members.add(w)
            key = tuple(self.vrank[v] for v in path)
            if key[::-1] < key:
                path.reverse()
                key = key[::-1]
            self.m.tick('path_key')
            if len(path) > 1 and key not in seen:
                seen.add(key)
                paths.append(path)
        self.m.timely()
        return seeds, paths

    def bfs(self, members, start, goal):
        parent, queue = {start: None}, deque([start])
        while queue:
            q = queue.popleft()
            self.m.tick('bfs_site')
            if q == goal:
                path = []
                while q is not None:
                    self.m.tick('path_copy')
                    path.append(q)
                    q = parent[q]
                return path[::-1]
            for p in self.target[q]:
                self.m.tick('target_edge')
                if p in members and p not in parent:
                    parent[p] = q
                    queue.append(p)
        raise ValueError('connected entry chain has no internal witness')

    def witness(self, path, embedding):
        self.m.set_phase('extraction')
        selected = set(self.m.copy(path))
        members = {v: set(self.m.copy(embedding[v])) for v in path}
        links = []
        for v, w in zip(path, path[1:]):
            best = None
            for q in embedding[v]:
                self.m.tick()
                for p in self.target[q]:
                    self.m.tick('target_edge')
                    if p in members[w]:
                        key = self.qrank[q], self.qrank[p], q, p
                        if best is None or key[:2] < best[:2]:
                            best = key
            if best is None:
                raise ValueError('valid entry lacks path contact')
            links.append(best[2:])
        owner = self.owner(embedding)

        def outer(v):
            outside = []
            for w in self.source[v]:
                self.m.tick('source_edge')
                if w not in selected:
                    outside.append(w)
            if not outside:
                return min(members[v], key=self.qrank.__getitem__)
            w = outside[0]
            choices = []
            for q in embedding[v]:
                self.m.tick()
                for p in self.target[q]:
                    self.m.tick('target_edge')
                    if owner.get(p) == w:
                        choices.append(q)
                        break
            if not choices:
                raise ValueError('valid entry lacks outer contact')
            return min(choices, key=self.qrank.__getitem__)

        route = []
        for i, v in enumerate(path):
            start = links[i-1][1] if i else outer(v)
            end = links[i][0] if i < len(path)-1 else outer(v)
            route.extend(self.bfs(members[v], start, end))
            if len(route) > ROUTE:
                return None
        self.prepare_branches(path, route, embedding)
        return route

    def prepare_branches(self, path, route, embedding):
        """Fixed positive requirements for this path, never reused across paths."""
        self.m.set_phase('branch_requirements')
        route_set = set(self.m.copy(route))
        selected = set(self.m.copy(path))
        owner = self.owner(embedding)
        outside_domains = {}
        for q in route:
            for p in self.target[q]:
                self.m.tick('target_edge')
                if p in owner and owner[p] not in selected:
                    outside_domains.setdefault(owner[p], set()).add(q)
        self.residue, self.requirements, self.branch_info = {}, {}, []
        for v in path:
            residue = []
            for q in embedding[v]:
                self.m.tick()
                if q not in route_set:
                    residue.append(q)
            self.residue[v] = residue
            unseen = set(self.m.copy(residue))
            components, domains = [], []
            covered = set()
            for first in sorted(unseen, key=self.qrank.__getitem__):
                self.m.tick()
                if first not in unseen:
                    continue
                unseen.remove(first)
                component, queue, boundary = [], deque([first]), set()
                while queue:
                    q = queue.popleft()
                    self.m.tick('component_site')
                    component.append(q)
                    for p in self.target[q]:
                        self.m.tick('target_edge')
                        if p in unseen:
                            unseen.remove(p)
                            queue.append(p)
                        if p in route_set:
                            boundary.add(p)
                        if p in owner and owner[p] not in selected:
                            covered.add(owner[p])
                if not boundary:
                    raise ValueError('valid chain has detached off-route component')
                components.append(component)
                domains.append(boundary)
            uncovered = []
            for w in self.source[v]:
                self.m.tick('source_edge')
                if w not in selected and w not in covered:
                    uncovered.append(w)
                    domains.append(outside_domains.get(w, set()))
            self.requirements[v] = domains
            self.branch_info.append(dict(owner=v, residue=self.m.copy(residue),
                components=[self.m.copy(c) for c in components],
                uncovered_outside=uncovered, requirement_sizes=[len(d) for d in domains]))
        self.m.timely()

    def chords(self, route, owner_count):
        self.m.set_phase('generation')
        indices = {}
        for i, q in enumerate(route):
            self.m.tick()
            indices[q] = i
        chords = []
        for i, q in enumerate(route):
            for p in self.target[q]:
                self.m.tick('target_edge')
                j = indices.get(p, -1)
                if j > i+1 and len(route)-(j-i-1) >= owner_count:
                    chords.append((-(j-i-1), i, j))
        chords.sort()
        self.m.timely()
        return chords

    def allocate(self, path, route, embedding):
        self.m.set_phase('allocation')
        result, offset = {}, 0
        for i, v in enumerate(path):
            required = set(self.m.copy(range(len(self.requirements[v]))))
            chain = []
            while offset < len(route):
                q = route[offset]
                self.m.tick()
                chain.append(q)
                offset += 1
                for requirement in tuple(required):
                    self.m.tick('requirement_test')
                    if q in self.requirements[v][requirement]:
                        required.remove(requirement)
                remaining = len(path)-i-1
                if len(route)-offset < remaining:
                    return None, 'insufficient_suffix'
                if not required:
                    break
            if not chain or required:
                return None, 'side_contact'
            result[v] = self.m.copy(self.residue[v]) + self.m.copy(chain)
        candidate = {}
        for v, chain in embedding.items():
            self.m.tick('copy_key')
            candidate[v] = self.m.copy(result.get(v, chain))
        return (candidate, self.m.copy(route[:offset])), None


def branched_path_reconstruction(embedding, source_adj, target_adj, *, validator,
                              deadline=None, work_limit=WORK):
    """Return the last complete map and finite-heuristic diagnostics.

    Adjacencies are immutable simple undirected maps in stable input order.
    ``validator(E, source_graph_view, target_adj_view)`` is the unchanged
    authoritative structural validator; all of its reads are metered.
    The valid supplied entry can be returned by alias if setup is interrupted.
    A late return is explicitly uncredited even when its retained map is valid.
    """
    if deadline is not None and not math.isfinite(deadline):
        raise ValueError('deadline must be finite or None')
    if type(work_limit) is not int or work_limit < 0 or work_limit > WORK:
        raise ValueError('work_limit must be an integer in [0, WORK]')
    m = _Meter(deadline, work_limit)
    current = embedding
    current_q = None
    info = dict(algorithm='retained_branch_joint_path', status='complete', input_validated=False, accepted=0, certified=0,
                before_qubits=None, after_qubits=None, qubits_saved=None, paths=[],
                seed_owners=[], paths_planned=0, stopped_stage=None, error=None,
                interrupted_certificate=False, proposal_incomplete=False)
    active = None
    try:
        ctx = _Context(embedding, source_adj, target_adj, validator, m)
        current = ctx.entry
        current_q = ctx.qubits(current)
        info['before_qubits'] = current_q
        if not ctx.certificate(current):
            raise ValueError('entry is not a valid complete minor')
        m.timely()
        info['input_validated'] = True
        seeds, paths = ctx.paths()
        info['seed_owners'], info['paths_planned'] = seeds, len(paths)
        for path in paths:
            record = dict(owners=path, status='complete', attempts=[], accepted=0,
                          work_start=m.work, initial_route=None)
            info['paths'].append(record)
            route = ctx.witness(path, current)
            if route is None:
                record.update(status='route_limit', work=m.work-record['work_start'])
                continue
            record['initial_route'] = m.copy(route)
            record['branches'] = ctx.branch_info
            chords, initial = [], True
            while len(record['attempts']) < ATTEMPTS:
                if initial:
                    candidate_route, shortcut = m.copy(route), None
                    initial = False
                else:
                    if not chords:
                        break
                    _, i, j = chords.pop(0)
                    candidate_route = m.copy(route[:i+1]) + m.copy(route[j:])
                    shortcut = [i, j]
                active = dict(shortcut=shortcut, before_route_sites=len(route),
                              candidate_route_sites=len(candidate_route), status='started',
                              work_start=m.work, certified=False, committed=False)
                record['attempts'].append(active)
                info['proposal_incomplete'] = True
                allocated, reason = ctx.allocate(path, candidate_route, current)
                if allocated is None:
                    if shortcut is None:
                        raise ValueError('unshortened witness lost valid-entry feasibility')
                    active['status'] = reason
                else:
                    candidate, used_route = allocated
                    before, after = current_q, ctx.qubits(candidate)
                    active.update(before_qubits=before, candidate_qubits=after)
                    if after >= before:
                        active['status'] = 'no_strict_gain'
                    else:
                        if not ctx.certificate(candidate):
                            raise ValueError('path certificate rejected a proposed minor')
                        active['certified'] = True
                        info['certified'] += 1
                        m.set_phase('publication')
                        saved_route = m.copy(used_route)
                        m.timely()
                        current, route, current_q = candidate, used_route, after
                        active.update(status='committed', committed=True, route=saved_route,
                                      assignment={v: current[v] for v in path})
                        record['accepted'] += 1
                        info['accepted'] += 1
                active['work'] = m.work-active['work_start']
                info['proposal_incomplete'] = False
                committed = active['committed']
                active = None
                if len(record['attempts']) < ATTEMPTS and (shortcut is None or committed):
                    chords = ctx.chords(route, len(path))
            if len(record['attempts']) == ATTEMPTS:
                record['status'] = 'attempt_limit'
            record['work'] = m.work-record['work_start']
        m.set_phase('publication')
        m.timely()
    except _Stop as exc:
        info.update(status=exc.reason, stopped_stage=m.phase,
                    interrupted_certificate=m.phase == 'certificate')
        if active is not None:
            active.update(status=exc.reason, work=m.work-active['work_start'])
        if info['paths'] and 'work' not in info['paths'][-1]:
            record = info['paths'][-1]
            record.update(status=exc.reason, work=m.work-record['work_start'])
    except Exception as exc:
        info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_stage=m.phase)
        if active is not None:
            active.update(status='error', work=m.work-active['work_start'])
    info['after_qubits'] = current_q
    if info['before_qubits'] is not None:
        info['qubits_saved'] = info['before_qubits']-info['after_qubits']
    info['returned_alias'] = current is embedding
    info.update(m.finish())
    if not info['timely']:
        info['status'] = 'late_output'
    return current, info
