"""One bounded connected-center / singleton-leaf refinement proposal.

Internal preconditions match the audited singleton core: original simple,
undirected, loopless graphs in a fixed contact context; a validated incumbent;
immutable incumbent mappings and chain lists. This module schedules no visits,
constructs no whole embedding, and calls no other proposal algorithm.

Every speculative footprint and assignment is query-local. Static eligibility
is memoized only after a complete decision, against fixed outside ownership.
Budget interruption discards the whole query. A maximum assignment certifies
only one fixed footprint; exhausting the growth heuristic proves no exclusion.
"""
from collections import deque
from dataclasses import dataclass, field
import time

from ember_qc.algorithms.factored.induced_star_relocation import (
    _FREE, _Interrupted, _SharedBudget, _take, _check, _complete, _key,
    build_owner_cache, refresh_owner_cache,
)


class _InvalidGroup(Exception):
    pass


def _diagnostics():
    return dict(reason=None, complete=False, accepted=0, qubits_saved=0,
                member_growth=0, equal_size_moves=0, contact_redundancy_gain=0,
                complete_proposals=0, leaves=0, demand_classes=0,
                roots_generated=0, root_duplicates=0, root_candidates=0,
                root=None, root_score=None, root_seed=None,
                eligibility_checks=0, memo_hits=0, memo_entries=0,
                assignment_checks=0, maximum_assignments=0,
                covering_assignments=0, exhausted_augmenting_searches=0,
                successful_augmentations=0, direct_assignments=0,
                class_site_edges=0, state_copies=0, copied_records=0,
                successor_candidates=0, successor_trials=0,
                completed_successors=0, first_zero_successors=0,
                steering_searches=0, steering_nodes=0, steering_steps=0,
                footprint_peak=0, boundary_peak=0, assigned_sites_peak=0,
                hall_demand_peak=0, hall_sites_peak=0, growth=[],
                last_fixed_footprint=None, stopped_detail=None)


def select_connected_star(embedding, ctx, center, budget):
    """One fixed greedy independent leaf subset; center degree has no upper cap."""
    try:
        _take(budget, 'selection')
        if center not in ctx.src_adj:
            return None, {'reason': 'invalid_center', 'complete': True}
        neighbors = ctx.src_adj[center]
        if len(neighbors) < 2:
            return None, {'reason': 'center_degree', 'complete': True}
        candidates = []
        for v in neighbors:
            _take(budget, 'selection')
            if len(ctx.src_adj[v]) <= ctx.max_degree:
                candidates.append(v)
        candidates.sort(key=lambda v: (1 - len(embedding[v]), len(ctx.src_adj[v])))
        _check(budget)
        leaves, blocked = [], set()
        for v in candidates:
            _take(budget, 'selection')
            if v in blocked:
                continue
            leaves.append(v)
            for w in ctx.src_adj[v]:
                _take(budget, 'selection')
                blocked.add(w)
        if len(leaves) < 2:
            return None, {'reason': 'too_few_leaves', 'complete': True}
        group = (center, *leaves)
        old_q = 0
        for v in group:
            _take(budget, 'selection')
            old_q += len(embedding[v])
        ceiling = old_q - len(leaves) - 1
        if ceiling < 1:
            return None, {'reason': 'zero_excess', 'complete': True}
        degree, delta = len(neighbors), ctx.max_degree
        if ((delta <= 2 and degree > delta)
                or (delta > 2 and degree > (delta - 2) * ceiling + 2)):
            return None, {'reason': 'center_capacity', 'complete': True}
        _complete(budget)
        return group, {'reason': 'selected', 'complete': True}
    except _Interrupted as error:
        return None, {'reason': str(error), 'complete': False}


@dataclass(frozen=True)
class _Demand:
    leaves: tuple
    frozen: tuple
    frozen_set: frozenset

    @property
    def count(self):
        return len(self.leaves)


@dataclass
class _State:
    footprint: set = field(default_factory=set)
    boundary: set = field(default_factory=set)
    coverage: dict = field(default_factory=dict)
    assignment: dict = field(default_factory=dict)
    counts: list = field(default_factory=list)
    edge_boundary: int = 0
    maximum: bool = False
    hall_classes: tuple = ()
    hall_sites: frozenset = frozenset()


class _Problem:
    """One fixed block, immutable outside ownership, and known-only static memo."""
    def __init__(self, embedding, ctx, group, cache, budget, info):
        self.embedding, self.ctx, self.cache = embedding, ctx, cache
        self.budget, self.info = budget, info
        self.group, self.selected = [], set()
        self.old_q = 0
        for v in group:
            _take(budget, 'obligations')
            if v not in ctx.src_adj or v in self.selected:
                raise _InvalidGroup('invalid_group')
            self.group.append(v)
            self.selected.add(v)
            self.old_q += len(embedding[v])
        if len(self.group) < 3:
            raise _InvalidGroup('invalid_group')
        self.center, self.k = self.group[0], len(self.group) - 1
        self.ceiling = self.old_q - self.k - 1
        self.frozen = {}
        for v in self.group:
            external, internal = [], set()
            for w in ctx.src_adj[v]:
                _take(budget, 'obligations')
                if w in self.selected:
                    internal.add(w)
                else:
                    external.append(w)
            if v == self.center:
                if len(internal) != self.k:
                    raise _InvalidGroup('not_induced_star')
            elif internal != {self.center}:
                raise _InvalidGroup('not_induced_star')
            elif len(ctx.src_adj[v]) > ctx.max_degree:
                raise _InvalidGroup('leaf_degree')
            self.frozen[v] = tuple(external)
        self.center_frozen = set()
        for v in self.frozen[self.center]:
            _take(budget, 'obligations')
            self.center_frozen.add(v)
        classes, indices, self.leaf_class = [], {}, {}
        for v in self.group[1:]:
            _take(budget, 'classes')
            key = frozenset(self.frozen[v])  # Each leaf has at most Delta obligations.
            if key not in indices:
                indices[key] = len(classes)
                classes.append([[], self.frozen[v], key])
            index = indices[key]
            classes[index][0].append(v)
            self.leaf_class[v] = index
        self.classes = []
        for leaves, external, key in classes:
            ordered = []
            for v in leaves:
                _take(budget, 'classes')
                ordered.append(v)
            ordered.sort(key=_key)
            _check(budget)
            self.classes.append(_Demand(tuple(ordered), external, key))
        self.memo = {}
        info['group'] = self.group
        info['leaves'], info['demand_classes'] = self.k, len(self.classes)
        info['center_ceiling'] = self.ceiling
        _complete(budget)

    def available(self, q):
        owner = self.cache.owner.get(q, _FREE)
        return q in self.ctx.adj and (owner is _FREE or owner in self.selected)

    def eligible(self, index, q):
        _take(self.budget, 'eligibility')
        self.info['eligibility_checks'] += 1
        key = (index, q)
        if key in self.memo:
            self.info['memo_hits'] += 1
            return self.memo[key]
        demand = self.classes[index]
        answer = self.available(q) and len(self.ctx.adj[q]) >= len(demand.frozen) + 1
        if answer and demand.frozen:
            _take(self.budget, 'adjacency')
            contacts = {self.cache.owner.get(p, _FREE) for p in self.ctx.adj[q]}
            for w in demand.frozen:
                _take(self.budget, 'eligibility_contacts')
                if w not in contacts:
                    answer = False
                    break
        # An interruption before this paid write never publishes an unknown.
        _take(self.budget, 'memo')
        self.memo[key] = answer
        self.info['memo_entries'] += 1
        return answer


def _ordered(values, problem, stage):
    ordered = []
    for q in values:
        _take(problem.budget, stage)
        ordered.append(q)
    ordered.sort(key=problem.ctx.rank.__getitem__)
    _complete(problem.budget)
    return ordered


def _copy_state(state, problem):
    result = _State()
    for key in ('footprint', 'boundary'):
        for q in getattr(state, key):
            _take(problem.budget, 'copy')
            problem.info['copied_records'] += 1
            getattr(result, key).add(q)
    for key in ('coverage', 'assignment'):
        for q, value in getattr(state, key).items():
            _take(problem.budget, 'copy')
            problem.info['copied_records'] += 1
            getattr(result, key)[q] = value
    for count in state.counts:
        _take(problem.budget, 'copy')
        problem.info['copied_records'] += 1
        result.counts.append(count)
    _take(problem.budget, 'copy')
    problem.info['copied_records'] += 1
    result.edge_boundary = state.edge_boundary
    problem.info['state_copies'] += 1
    _complete(problem.budget)
    return result


def _add_center(state, q, problem, initial=False):
    """Mutate a private trial only; return genuinely new boundary sites."""
    budget, ctx = problem.budget, problem.ctx
    if not problem.available(q) or q in state.footprint or (not initial and q not in state.boundary):
        raise _InvalidGroup('invalid_center_extension')
    state.maximum = False
    _take(budget, 'state_edits')
    state.boundary.discard(q)
    if q in state.assignment:
        _take(budget, 'assignment_edits')
        previous = state.assignment.pop(q)
        _take(budget, 'assignment_edits')
        state.counts[previous] -= 1
    _take(budget, 'adjacency')
    inward = sum(p in state.footprint for p in ctx.adj[q])
    _take(budget, 'state_edits')
    state.edge_boundary += len(ctx.adj[q]) - 2 * inward
    _take(budget, 'state_edits')
    state.footprint.add(q)
    new_sites = []
    _take(budget, 'adjacency')
    for p in ctx.adj[q]:
        owner = problem.cache.owner.get(p, _FREE)
        if owner in problem.center_frozen:
            _take(budget, 'state_edits')
            state.coverage[owner] = state.coverage.get(owner, 0) + 1
        if p not in state.footprint and p not in state.boundary and problem.available(p):
            _take(budget, 'state_edits')
            state.boundary.add(p)
            new_sites.append(p)
    problem.info['footprint_peak'] = max(problem.info['footprint_peak'], len(state.footprint))
    problem.info['boundary_peak'] = max(problem.info['boundary_peak'], len(state.boundary))
    return new_sites  # ctx.adj already uses stable physical order.


def _direct_fill(state, new_sites, problem):
    for q in new_sites:
        _take(problem.budget, 'direct_fill')
        for index, demand in enumerate(problem.classes):
            _take(problem.budget, 'class_site_edges')
            problem.info['class_site_edges'] += 1
            if state.counts[index] < demand.count and problem.eligible(index, q):
                _take(problem.budget, 'assignment_edits')
                state.assignment[q] = index
                _take(problem.budget, 'assignment_edits')
                state.counts[index] += 1
                problem.info['direct_assignments'] += 1
                break


def _maximum_assignment(state, problem):
    """Complete multisource capacitated augmentation on one fixed boundary."""
    budget, info = problem.budget, problem.info
    state.maximum = False
    info['assignment_checks'] += 1
    sites = _ordered(state.boundary, problem, 'boundary_order')
    while len(state.assignment) < problem.k:
        queue, parent_class, parent_site = deque(), {}, {}
        for index, demand in enumerate(problem.classes):
            _take(budget, 'matching_queue')
            if state.counts[index] < demand.count:
                parent_class[index] = _FREE
                queue.append(index)
        end = _FREE
        while queue and end is _FREE:
            _take(budget, 'matching_queue')
            index = queue.popleft()
            for q in sites:
                _take(budget, 'class_site_edges')
                info['class_site_edges'] += 1
                if q in parent_site or not problem.eligible(index, q):
                    continue
                _take(budget, 'matching_records')
                parent_site[q] = index
                owner = state.assignment.get(q, _FREE)
                if owner is _FREE:
                    end = q
                    break
                # Owned sites are visited too, so an exhausted search has the
                # full Hall neighborhood, including saturated self-class arcs.
                if owner not in parent_class:
                    _take(budget, 'matching_queue')
                    parent_class[owner] = q
                    queue.append(owner)
        if end is _FREE:
            classes, neighbors, demand = [], set(), 0
            for index in sorted(parent_class):
                _take(budget, 'hall')
                classes.append(index)
                demand += problem.classes[index].count
            for q in parent_site:
                _take(budget, 'hall')
                neighbors.add(q)
            if demand <= len(neighbors):
                raise RuntimeError('completed augmenting search has no Hall shortage')
            state.hall_classes, state.hall_sites = tuple(classes), frozenset(neighbors)
            info['hall_demand_peak'] = max(info['hall_demand_peak'], demand)
            info['hall_sites_peak'] = max(info['hall_sites_peak'], len(neighbors))
            info['exhausted_augmenting_searches'] += 1
            break
        # Reverse only a complete path. An interrupted private update is never
        # scored or returned; its caller discards the candidate state entirely.
        while end is not _FREE:
            _take(budget, 'matching_path')
            index = parent_site[end]
            previous = parent_class[index]
            old_owner = state.assignment.get(end, _FREE)
            _take(budget, 'assignment_edits')
            state.assignment[end] = index
            _take(budget, 'assignment_edits')
            state.counts[index] += 1
            if old_owner is not _FREE:
                _take(budget, 'assignment_edits')
                state.counts[old_owner] -= 1
            end = previous
        info['successful_augmentations'] += 1
    _complete(budget)
    state.maximum = True
    info['maximum_assignments'] += 1
    if len(state.assignment) == problem.k:
        state.hall_classes, state.hall_sites = (), frozenset()
        info['covering_assignments'] += 1
    info['assigned_sites_peak'] = max(info['assigned_sites_peak'], len(state.assignment))


def _deficit(state, problem):
    if not state.maximum:
        raise RuntimeError('incomplete assignment cannot supply an exact score')
    return problem.k - len(state.assignment) + len(problem.center_frozen) - len(state.coverage)


def _bounds(state, problem):
    """Necessary relaxations using all distinct available boundary sites."""
    _take(problem.budget, 'bounds')
    remaining = problem.ceiling - len(state.footprint)
    growth = max(0, problem.ctx.max_degree - 2)
    if len(problem.ctx.src_adj[problem.center]) > state.edge_boundary + remaining * growth:
        return 'edge_boundary'
    if problem.k > len(state.boundary) + remaining * growth:
        return 'site_boundary'
    return None


def _choose_root(problem):
    budget, ctx, info = problem.budget, problem.ctx, problem.info
    seed = None
    for v in problem.group:
        for w in problem.frozen[v]:
            _take(budget, 'root_generation')
            hops = 1 if v == problem.center else 2
            option = (len(problem.embedding[w]) * ctx.max_degree ** hops,
                      hops, _key(v), _key(w), v, w)
            if seed is None or option[:4] < seed[:4]:
                seed = option
    if seed is not None:
        info['root_seed'] = dict(selected_vertex=seed[4], frozen_vertex=seed[5],
                                 hops=seed[1], estimated_walks=seed[0])

    def walks():
        if seed is None:
            yield from ctx.adj
            return
        for p in _ordered(problem.embedding[seed[5]], problem, 'root_generation'):
            _take(budget, 'adjacency')
            for q in ctx.adj[p]:
                if seed[1] == 1:
                    yield q
                else:
                    _take(budget, 'root_generation')
                    if problem.eligible(problem.leaf_class[seed[4]], q):
                        _take(budget, 'adjacency')
                        yield from ctx.adj[q]

    best, best_score, seen = _FREE, -1, set()
    upper = min(len(ctx.src_adj[problem.center]), ctx.max_degree)
    for root in walks():
        _take(budget, 'root_generation')
        info['roots_generated'] += 1
        if root in seen:
            info['root_duplicates'] += 1
            continue
        seen.add(root)
        if not problem.available(root):
            continue
        info['root_candidates'] += 1
        _take(budget, 'root_score')
        _take(budget, 'adjacency')
        owners, available = set(), 0
        for q in ctx.adj[root]:
            owner = problem.cache.owner.get(q, _FREE)
            if owner in problem.center_frozen:
                owners.add(owner)
            if problem.available(q):
                available += 1
        score = len(owners) + min(problem.k, available)
        if score > best_score:
            best, best_score = root, score
        if score == upper:
            break
    _complete(budget)
    if best is not _FREE:
        info['root'], info['root_score'] = best, best_score
    return best


def _shortlist(state, problem):
    """Four successors by optimistic deficit, new Hall sites, physical rank."""
    shortlist = []
    covered = len(state.assignment) == problem.k
    hall = set()
    for index in state.hall_classes:
        _take(problem.budget, 'hall')
        hall.add(index)
    for x in _ordered(state.boundary, problem, 'boundary_order'):
        _take(problem.budget, 'successor_scan')
        problem.info['successor_candidates'] += 1
        new_eligible = new_hall = 0
        new_owners = set()
        _take(problem.budget, 'adjacency')
        for q in problem.ctx.adj[x]:
            owner = problem.cache.owner.get(q, _FREE)
            if owner in problem.center_frozen and owner not in state.coverage:
                new_owners.add(owner)
            # With complete leaf demand, both site terms of the fixed ranking
            # are already zero. Only new frozen-center contacts can change it.
            if covered:
                continue
            if (q in state.footprint or q in state.boundary or not problem.available(q)):
                continue
            any_eligible = hall_eligible = False
            for index in range(len(problem.classes)):
                _take(problem.budget, 'class_site_edges')
                problem.info['class_site_edges'] += 1
                if problem.eligible(index, q):
                    any_eligible = True
                    if index in hall:
                        hall_eligible = True
                if any_eligible and (hall_eligible or not hall):
                    break
            new_eligible += int(any_eligible)
            new_hall += int(hall_eligible)
        optimistic = (problem.k - min(problem.k, len(state.assignment) + new_eligible)
                      + len(problem.center_frozen) - len(state.coverage) - len(new_owners))
        _take(problem.budget, 'shortlist')
        shortlist.append((optimistic, -new_hall, problem.ctx.rank[x], x))
        shortlist.sort(key=lambda entry: entry[:3])  # At most five records.
        if len(shortlist) > 4:
            shortlist.pop()
    _complete(problem.budget)
    return shortlist


def _path_to_footprint(q, parents, problem):
    reverse, members = [], set()
    while parents[q] is not _FREE:
        _take(problem.budget, 'steering_path')
        reverse.append(q)
        members.add(q)
        q = parents[q]
    return reverse[-1] if reverse else _FREE, members


def _steering_step(state, problem):
    """One bounded BFS; a goal's leaf witness must not lie on its route."""
    budget, ctx, info = problem.budget, problem.ctx, problem.info
    info['steering_searches'] += 1
    remaining = problem.ceiling - len(state.footprint)
    queue, parents, depth = deque(), {}, {}
    for q in _ordered(state.footprint, problem, 'steering_queue'):
        _take(budget, 'steering_queue')
        queue.append(q)
        parents[q], depth[q] = _FREE, 0
    while queue:
        _take(budget, 'steering_queue')
        q = queue.popleft()
        info['steering_nodes'] += 1
        path = None
        _take(budget, 'adjacency')
        for p in ctx.adj[q]:
            owner = problem.cache.owner.get(p, _FREE)
            if depth[q] > 0 and owner in problem.center_frozen and owner not in state.coverage:
                first, _ = _path_to_footprint(q, parents, problem)
                return first
            if (depth[q] == 0 or p in state.footprint or p in state.boundary
                    or not problem.available(p)):
                continue
            for index in state.hall_classes:
                _take(budget, 'class_site_edges')
                info['class_site_edges'] += 1
                if not problem.eligible(index, p):
                    continue
                if path is None:
                    path = _path_to_footprint(q, parents, problem)
                if p not in path[1]:
                    return path[0]
                break  # This same physical site lies on the path for every class.
        if depth[q] >= remaining:
            continue
        _take(budget, 'adjacency')
        for p in ctx.adj[q]:
            if p not in parents and problem.available(p):
                _take(budget, 'steering_queue')
                parents[p], depth[p] = q, depth[q] + 1
                queue.append(p)
    _complete(budget)
    return _FREE


def _record_state(state, problem, operator, added):
    # These scalar diagnostics retain no speculative chain/domain tables.
    record = dict(operator=operator, added=added, center_size=len(state.footprint),
                  boundary_size=len(state.boundary), edge_boundary=state.edge_boundary,
                  assigned_leaves=len(state.assignment), deficit=_deficit(state, problem))
    problem.info['last_fixed_footprint'] = dict(record, maximum=True)
    if operator != 'trial':
        problem.info['growth'].append(record)
    return record


def _certify(state, problem):
    """Expand classes, then independently recheck original physical constraints."""
    budget, ctx = problem.budget, problem.ctx
    if not state.maximum or _deficit(state, problem) != 0:
        return None
    replacement = {problem.center: _ordered(state.footprint, problem, 'recovery')}
    class_sites = []
    for _ in problem.classes:
        _take(budget, 'recovery')
        class_sites.append([])
    for q, index in state.assignment.items():
        _take(budget, 'recovery')
        if not 0 <= index < len(class_sites):
            return None
        class_sites[index].append(q)
    for index, demand in enumerate(problem.classes):
        sites = class_sites[index]
        if len(sites) != demand.count:
            return None
        sites.sort(key=ctx.rank.__getitem__)
        _check(budget)
        for v, q in zip(demand.leaves, sites):
            _take(budget, 'recovery')
            replacement[v] = [q]
    new_owner, old_q, new_q, member_growth = {}, 0, 0, 0
    for v in problem.group:
        _take(budget, 'certificate')
        chain = replacement.get(v)
        if not chain or (v != problem.center and len(chain) != 1):
            return None
        old_q += len(problem.embedding[v])
        new_q += len(chain)
        member_growth += int(len(chain) > len(problem.embedding[v]))
        for q in chain:
            _take(budget, 'certificate')
            if q not in ctx.adj or q in new_owner or not problem.available(q):
                return None
            new_owner[q] = v
    if new_q >= old_q:
        return None
    # Connectivity is checked from actual target edges, independent of growth.
    center = replacement[problem.center]
    center_set = set()
    for q in center:
        _take(budget, 'certificate')
        center_set.add(q)
    reached, queue = {center[0]}, deque([center[0]])
    while queue:
        _take(budget, 'certificate')
        q = queue.popleft()
        _take(budget, 'adjacency')
        for p in ctx.adj[q]:
            if p in center_set and p not in reached:
                _take(budget, 'certificate')
                reached.add(p)
                queue.append(p)
    for q in center:
        _take(budget, 'certificate')
        if q not in reached:
            return None

    def owner(q, new):
        if new and q in new_owner:
            return new_owner[q]
        previous = problem.cache.owner.get(q, _FREE)
        return _FREE if new and previous in problem.selected else previous

    redundancies = []
    for new in (False, True):
        internal = external = internal_edges = external_edges = 0
        for v in problem.group:
            required = set()
            for w in ctx.src_adj[v]:
                _take(budget, 'scoring')
                required.add(w)
                if w in problem.selected:
                    internal_edges += 1
                else:
                    external_edges += 1
            found = set()
            chain = replacement[v] if new else problem.embedding[v]
            for q in chain:
                _take(budget, 'scoring')
                _take(budget, 'adjacency')
                for p in ctx.adj[q]:
                    w = owner(p, new)
                    if w in required:
                        found.add(w)
                        if w in problem.selected:
                            internal += 1
                        else:
                            external += 1
            for w in required:
                _take(budget, 'certificate_edges')
                if w not in found:
                    return None
        redundancies.append(internal // 2 + external - internal_edges // 2 - external_edges)
    _complete(budget)
    return replacement, dict(qubits_saved=old_q - new_q, member_growth=member_growth,
                             old_selected_qubits=old_q, new_selected_qubits=new_q,
                             old_redundancy=redundancies[0], new_redundancy=redundancies[1],
                             contact_redundancy_gain=redundancies[1] - redundancies[0])


def query_connected_star(embedding, ctx, group, cache, budget):
    """One root and one growing footprint; no singleton proposer or restarts."""
    info = _diagnostics()

    def finish(result, reason, complete=False, detail=None):
        info.update(reason=reason, complete=complete, stopped_detail=detail)
        return result, info

    if not cache.valid or cache.embedding is not embedding:
        return finish(None, 'stale_cache')
    try:
        problem = _Problem(embedding, ctx, group, cache, budget, info)
        if problem.ceiling < 1:
            return finish(None, 'zero_excess', True)
        root = _choose_root(problem)
        if root is _FREE:
            return finish(None, 'heuristic_no_proposal', True, 'no_root')
        state = _State()
        for _ in problem.classes:
            _take(budget, 'state_edits')
            state.counts.append(0)
        new_sites = _add_center(state, root, problem, initial=True)
        _direct_fill(state, new_sites, problem)
        _maximum_assignment(state, problem)
        _record_state(state, problem, 'root', root)
        while True:
            if _deficit(state, problem) == 0:
                info['complete_proposals'] += 1
                certificate = _certify(state, problem)
                if certificate is None:
                    return finish(None, 'certificate_failed')
                replacement, score = certificate
                _complete(budget)
                info.update(score)
                info['accepted'] = 1
                return finish(replacement, 'accepted', True)
            if len(state.footprint) >= problem.ceiling:
                return finish(None, 'heuristic_no_proposal', True, 'center_ceiling')
            bound = _bounds(state, problem)
            if bound is not None:
                return finish(None, 'heuristic_no_proposal', True, bound)
            shortlist = _shortlist(state, problem)
            best, best_key, zero = None, None, False
            for _, _, rank, x in shortlist:
                info['successor_trials'] += 1
                trial = _copy_state(state, problem)
                new_sites = _add_center(trial, x, problem)
                _direct_fill(trial, new_sites, problem)
                _maximum_assignment(trial, problem)
                info['completed_successors'] += 1
                _record_state(trial, problem, 'trial', x)
                deficit = _deficit(trial, problem)
                if deficit == 0:
                    info['first_zero_successors'] += 1
                    state, zero = trial, True
                    _record_state(state, problem, 'successor', x)
                    break  # First zero goes directly to the full certificate.
                key = (deficit, -len(trial.assignment), rank)
                if deficit < _deficit(state, problem) and (best_key is None or key < best_key):
                    best, best_key = (trial, x), key
            if zero:
                continue
            if best is not None:
                state, added = best
                _record_state(state, problem, 'successor', added)
                continue
            added = _steering_step(state, problem)
            if added is _FREE:
                return finish(None, 'heuristic_no_proposal', True, 'steering_exhausted')
            trial = _copy_state(state, problem)
            new_sites = _add_center(trial, added, problem)
            _direct_fill(trial, new_sites, problem)
            _maximum_assignment(trial, problem)
            state = trial
            info['steering_steps'] += 1
            _record_state(state, problem, 'steering', added)
    except _InvalidGroup as error:
        return finish(None, str(error), True)
    except _Interrupted as error:
        # No previously scored state is promoted after common-budget expiry.
        info['interrupted_stage'] = getattr(budget, 'last_stage', None)
        return finish(None, str(error))


class _StageBudget(_SharedBudget):
    """Audited live allowance, adding only the latest attempted stage label."""
    def charge(self, stage):
        self.last_stage = stage
        return super().charge(stage)


class ConnectedStarSearch:
    """Lazy owner cache and one caller-supplied whole-call auxiliary allowance.

    Graph/context and immutable-incumbent preconditions are stated above. The
    constructor is constant work. Pass ``global_work // 20`` as auxiliary_limit;
    each proposal also charges the supplied live ordinary visit directly. No
    separate per-query limit, singleton proposal, or scheduler exists here.

    ``info['work'] == setup_work + query_work + refresh_work``; selection is
    query work. Returned ``expansions`` and refresh work are descriptive, never
    charged again by the caller. Returned replacements contain only the selected
    source vertices. ``accepted`` means a fully certified proposal, not a later
    scheduler commit. A refresh failure disables future proposals and cannot
    undo the caller's already accepted embedding. Refresh before lazy setup is
    a no-op. Query-local states and eligibility memo never survive a proposal.
    """
    def __init__(self, ctx, auxiliary_limit):
        if (not isinstance(auxiliary_limit, int) or isinstance(auxiliary_limit, bool)
                or auxiliary_limit < 0):
            raise ValueError('auxiliary_limit must be a nonnegative integer')
        self.ctx, self.cache = ctx, None
        self.setup_attempted = False
        self.info = {'work_limit': auxiliary_limit, 'work': 0, 'setup_work': 0,
                     'query_work': 0, 'refresh_work': 0, 'query_stage_work': {},
                     'cache_builds': 0, 'cache_refreshes': 0, 'disabled_reason': None,
                     'considerations': 0, 'queries': 0, 'certified_proposals': 0,
                     'proposed_qubits_saved': 0, 'proposed_contact_redundancy_gain': 0,
                     'proposed_member_growth': 0,
                     'proposal_wall': 0.0, 'setup_wall': 0.0, 'refresh_wall': 0.0,
                     'last_refresh_work': 0, 'last_refresh_wall': 0.0,
                     'last_refresh_reason': None, 'reasons': {}}

    def _disable(self, reason):
        if self.cache is not None:
            self.cache.valid = False
        self.cache = None
        self.info['disabled_reason'] = reason

    def propose(self, embedding, center, visit):
        start = time.perf_counter()
        old_work, old_setup = self.info['work'], self.info['setup_work']
        old_setup_wall = self.info['setup_wall']
        query = _StageBudget(self, visit, 'query')
        self.info['considerations'] += 1
        group = None

        def finish(result, move):
            detail = _diagnostics()
            detail.update(move)
            detail.setdefault('group', list(group) if group else [])
            detail['query_work'] = query.expansions
            detail['setup_work'] = self.info['setup_work'] - old_setup
            detail['expansions'] = self.info['work'] - old_work
            detail['stage_work'] = dict(query.stages)
            detail['wall'] = time.perf_counter() - start
            detail['setup_wall'] = self.info['setup_wall'] - old_setup_wall
            detail['query_wall'] = detail['wall'] - detail['setup_wall']
            self.info['proposal_wall'] += detail['wall']
            reasons = self.info['reasons']
            reasons[detail['reason']] = reasons.get(detail['reason'], 0) + 1
            self.info['certified_proposals'] += detail['accepted']
            self.info['proposed_qubits_saved'] += detail['qubits_saved']
            self.info['proposed_contact_redundancy_gain'] += detail['contact_redundancy_gain']
            self.info['proposed_member_growth'] += detail['member_growth']
            return result, detail

        if self.info['disabled_reason'] is not None:
            return finish(None, {'reason': 'disabled'})
        if self.info['work'] >= self.info['work_limit']:
            self._disable('auxiliary_limit')
            return finish(None, {'reason': 'auxiliary_limit'})
        if self.cache is not None and (not self.cache.valid or self.cache.embedding is not embedding):
            self._disable('stale_cache')
            return finish(None, {'reason': 'stale_cache'})
        group, selection = select_connected_star(embedding, self.ctx, center, query)
        if group is None:
            return finish(None, selection)
        if not self.setup_attempted:
            self.setup_attempted = True
            setup = _StageBudget(self, visit, 'setup')
            setup_start = time.perf_counter()
            self.cache = build_owner_cache(embedding, self.ctx, setup)
            self.info['setup_wall'] += time.perf_counter() - setup_start
            if self.cache is None:
                self._disable('setup_' + (setup.stopped_by or 'incomplete'))
                return finish(None, {'reason': self.info['disabled_reason']})
            self.info['cache_builds'] += 1
        self.info['queries'] += 1
        result, move = query_connected_star(embedding, self.ctx, group, self.cache, query)
        return finish(result, move)

    def refresh(self, old_embedding, embedding, selected, visit):
        self.info['last_refresh_work'] = 0
        self.info['last_refresh_wall'] = 0.0
        self.info['last_refresh_reason'] = 'not_built_or_disabled'
        if self.cache is None:
            return True
        start = time.perf_counter()
        budget = _StageBudget(self, visit, 'refresh')
        ok = refresh_owner_cache(self.cache, old_embedding, embedding,
                                 selected, self.ctx, budget)
        elapsed = time.perf_counter() - start
        self.info['refresh_wall'] += elapsed
        self.info['last_refresh_work'] = budget.expansions
        self.info['last_refresh_wall'] = elapsed
        if not ok:
            self._disable('refresh_' + (budget.stopped_by or 'stale_or_incomplete'))
            self.info['last_refresh_reason'] = self.info['disabled_reason']
            return False
        self.info['cache_refreshes'] += 1
        self.info['last_refresh_reason'] = 'refreshed'
        return True
