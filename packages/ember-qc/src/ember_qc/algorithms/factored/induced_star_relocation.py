"""Bounded singleton placement of one induced source star in a valid incumbent.

Internal contract: the caller has validated an embedding of simple, undirected,
loopless graphs and supplies the original fixed contact context. Incumbent maps
and chain lists are immutable. This is a local proposal, never a constructor.

Low-level operations accept a budget with ``pop()``, ``check()`` and
``stopped_by``. An optional ``charge(stage)`` method records finer work stages.
StarSearch adds the fixed query ceiling and an auxiliary ceiling to the caller's
active visit budget. The caller alone schedules visits and commits replacements.
"""
from collections import deque
from dataclasses import dataclass
import time


QUERY_LIMIT = 2048
_FREE = object()


class _Interrupted(Exception):
    pass


def _take(budget, stage):
    charge = getattr(budget, 'charge', None)
    ok = charge(stage) if charge is not None else budget.pop()
    if not ok:
        raise _Interrupted(budget.stopped_by or 'work_limit')


def _check(budget):
    if not budget.check():
        raise _Interrupted(budget.stopped_by or 'work_limit')


def _complete(budget):
    # All charged work is finished. Using the last allowed unit is legal; a
    # deadline still prevents publication. No partial computation calls this.
    if not budget.check() and budget.stopped_by not in {
            'work_limit', 'auxiliary_limit', 'query_limit', 'scan_limit'}:
        raise _Interrupted(budget.stopped_by or 'interrupted')


def _key(value):
    # The context uses this same stable mixed-label order; no global rank map.
    return type(value).__name__, repr(value)


@dataclass
class OwnerCache:
    owner: dict
    embedding: object
    valid: bool = True


def build_owner_cache(embedding, ctx, budget):
    """Return a complete owner map or None; incomplete setup is never published."""
    owner = {}
    try:
        for v, chain in embedding.items():
            _take(budget, 'setup')
            for q in chain:
                _take(budget, 'setup')
                if q not in ctx.adj or q in owner:
                    raise ValueError('owner setup requires a valid incumbent')
                owner[q] = v
        _complete(budget)
    except _Interrupted:
        return None
    return OwnerCache(owner, embedding)


def refresh_owner_cache(cache, old_embedding, embedding, selected, ctx, budget):
    """Remove all old owners before adding new; failure invalidates the cache.

    The accepted embedding is never changed. A caller must discard an invalid
    cache, including one partially updated before an interruption.
    """
    if not cache.valid or cache.embedding is not old_embedding:
        cache.valid = False
        return False
    cache.valid = False
    try:
        group = []
        for v in selected:
            _take(budget, 'refresh')
            group.append(v)
            for q in old_embedding[v]:
                _take(budget, 'refresh')
                if cache.owner.get(q, _FREE) != v:
                    return False
                del cache.owner[q]
        for v in group:
            _take(budget, 'refresh')
            for q in embedding[v]:
                _take(budget, 'refresh')
                if q not in ctx.adj or q in cache.owner:
                    return False
                cache.owner[q] = v
        _complete(budget)
    except _Interrupted:
        return False
    cache.embedding = embedding
    cache.valid = True
    return True


def select_star(embedding, ctx, center, budget):
    """Select the fixed greedy independent leaf subset; no subset search."""
    try:
        _take(budget, 'selection')
        neighbors = ctx.src_adj[center]
        if not 2 <= len(neighbors) <= ctx.max_degree:
            return None, {'reason': 'center_degree', 'complete': True}
        candidates = []
        for v in neighbors:
            _take(budget, 'selection')
            if len(ctx.src_adj[v]) <= ctx.max_degree:
                candidates.append(v)
        # src_adj is in stable logical order; stable sort preserves that tie.
        candidates.sort(key=lambda v: (1 - len(embedding[v]), len(ctx.src_adj[v])))
        _check(budget)
        leaves = []
        for v in candidates:
            _take(budget, 'selection')
            independent = True
            for w in leaves:
                _take(budget, 'selection')
                if w in ctx.src_adj[v]:
                    independent = False
                    break
            if independent:
                leaves.append(v)
        if len(leaves) < 2:
            return None, {'reason': 'too_few_leaves', 'complete': True}
        group = (center, *leaves)
        excess = 0
        for v in group:
            _take(budget, 'selection')
            excess += len(embedding[v]) - 1
        if excess <= 0:
            return None, {'reason': 'zero_excess', 'complete': True}
        _complete(budget)
        return group, {'reason': 'selected', 'complete': True}
    except _Interrupted as error:
        return None, {'reason': str(error), 'complete': False}


def _matching(leaves, domains, budget, info):
    """One covering matching via iterative augmenting paths, or None.

    Left identities are integer positions; right identities are physical labels.
    They never share a graph namespace, even when original labels coincide.
    """
    order = sorted(range(len(leaves)), key=lambda i: (len(domains[i]), _key(leaves[i])))
    _check(budget)
    right_owner, left_site = {}, {}
    for start in order:
        _take(budget, 'matching')
        queue, visited_left = deque([start]), {start}
        parent = {}
        end = _FREE
        while queue and end is _FREE:
            left = queue.popleft()
            _take(budget, 'matching')
            for q in domains[left]:
                _take(budget, 'matching')
                info['matching_edges'] += 1
                if q in parent:
                    continue
                parent[q] = left
                previous = right_owner.get(q, _FREE)
                if previous is _FREE:
                    end = q
                    break
                if previous not in visited_left:
                    visited_left.add(previous)
                    queue.append(previous)
        if end is _FREE:
            return None
        while end is not _FREE:
            _take(budget, 'matching')
            left = parent[end]
            previous = left_site.get(left, _FREE)
            right_owner[end] = left
            left_site[left] = end
            end = previous
    return {leaf: left_site[i] for i, leaf in enumerate(leaves)}


def _certificate(embedding, ctx, selected, sites, cache, budget):
    """Independently recheck all incident edges and score their actual couplers."""
    selected_set = set(selected)
    new_owner = {}
    old_qubits = 0
    for v in selected:
        _take(budget, 'certificate')
        q = sites[v]
        if (q not in ctx.adj or q in new_owner
                or cache.owner.get(q, _FREE) not in selected_set | {_FREE}):
            return None
        new_owner[q] = v
        old_qubits += len(embedding[v])
    if old_qubits <= len(selected):
        return None

    def proposed_owner(q):
        if q in new_owner:
            return new_owner[q]
        old = cache.owner.get(q, _FREE)
        return _FREE if old in selected_set else old

    counts = []
    for new in (False, True):
        internal = external = internal_edges = external_edges = 0
        for v in selected:
            required = set()
            for w in ctx.src_adj[v]:
                _take(budget, 'scoring')
                required.add(w)
                if w in selected_set:
                    internal_edges += 1
                else:
                    external_edges += 1
            reached = set()
            chain = (sites[v],) if new else embedding[v]
            for p in chain:
                _take(budget, 'scoring')
                for q in ctx.adj[p]:
                    w = proposed_owner(q) if new else cache.owner.get(q, _FREE)
                    if w in required:
                        reached.add(w)
                        if w in selected_set:
                            internal += 1
                        else:
                            external += 1
            _take(budget, 'certificate')
            if reached != required:
                return None
        counts.append(internal // 2 + external - internal_edges // 2 - external_edges)
    _complete(budget)
    return {'qubits_saved': old_qubits - len(selected),
            'old_redundancy': counts[0], 'new_redundancy': counts[1],
            'contact_redundancy_gain': counts[1] - counts[0]}


def query_star(embedding, ctx, group, cache, budget):
    """Return a certified selected-only singleton map or None and diagnostics.

    A failed/truncated query does not mutate the incumbent or cache. ``complete``
    means accepted or a completed decision for this fixed block, never exhaustive
    search over different blocks. The caller must recheck its deadline at commit.
    """
    info = {'group': list(group), 'reason': None, 'complete': False,
            'accepted': 0, 'qubits_saved': 0, 'contact_redundancy_gain': 0,
            'roots_generated': 0, 'root_duplicates': 0, 'roots_eligible': 0,
            'roots_matched': 0, 'matching_edges': 0, 'domain_edges': 0,
            'site_masks': 0, 'root_seed': None, 'complete_proposals': 0}

    def finish(result, reason, complete=False):
        info['reason'], info['complete'] = reason, complete
        return result, info

    if not cache.valid or cache.embedding is not embedding:
        cache.valid = False
        return finish(None, 'stale_cache')
    try:
        selected, excess = set(), 0
        for v in group:
            _take(budget, 'obligations')
            if v in selected or v not in ctx.src_adj:
                return finish(None, 'invalid_group', True)
            selected.add(v)
            excess += len(embedding[v]) - 1
        if len(group) < 3 or excess <= 0:
            return finish(None, 'invalid_group', True)
        center, leaves = group[0], tuple(group[1:])
        frozen = {}
        for v in group:
            _take(budget, 'obligations')
            if len(ctx.src_adj[v]) > ctx.max_degree:
                return finish(None, 'degree_bound', True)
            external = set()
            for w in ctx.src_adj[v]:
                _take(budget, 'obligations')
                if w in selected:
                    if v != center and w != center:
                        return finish(None, 'not_induced_star', True)
                else:
                    external.add(w)
            if v != center and center not in ctx.src_adj[v]:
                return finish(None, 'not_induced_star', True)
            frozen[v] = external

        masks = {}

        def mask(p):
            if p in masks:
                return masks[p]
            _take(budget, 'eligibility')
            mask_value = 0
            owner = cache.owner.get(p, _FREE)
            if owner is _FREE or owner in selected:
                _take(budget, 'eligibility')
                contacts = {cache.owner.get(q, _FREE) for q in ctx.adj[p]}
                contacts.discard(_FREE)
                contacts.difference_update(selected)
                degree = len(ctx.adj[p])
                for i, v in enumerate(group):
                    _take(budget, 'eligibility')
                    if degree >= len(ctx.src_adj[v]) and frozen[v] <= contacts:
                        mask_value |= 1 << i
            masks[p] = mask_value
            info['site_masks'] += 1
            return mask_value

        seed_options = []
        for i, v in enumerate(group):
            for w in frozen[v]:
                _take(budget, 'root_generation')
                hops = 1 if i == 0 else 2
                seed_options.append((len(embedding[w]) * ctx.max_degree ** hops,
                                     hops, _key(v), _key(w), i, w))
        seed = min(seed_options) if seed_options else None
        if seed is not None:
            info['root_seed'] = {'selected_vertex': group[seed[4]],
                                 'frozen_vertex': seed[5], 'hops': seed[1],
                                 'estimated_walks': seed[0]}
        _check(budget)

        def walks():
            if seed is None:
                yield from ctx.adj
                return
            chain = []
            for p in embedding[seed[5]]:
                _take(budget, 'root_generation')
                chain.append(p)
            chain.sort(key=ctx.rank.__getitem__)
            _check(budget)
            for p in chain:
                _take(budget, 'root_generation')
                for q in ctx.adj[p]:
                    if seed[1] == 1:
                        yield q
                    else:
                        _take(budget, 'root_generation')
                        if mask(q) & (1 << seed[4]):
                            _take(budget, 'root_generation')
                            yield from ctx.adj[q]

        seen = set()
        for root in walks():
            _take(budget, 'root_generation')
            info['roots_generated'] += 1
            if root in seen:
                info['root_duplicates'] += 1
                continue
            seen.add(root)
            if not mask(root) & 1:
                continue
            info['roots_eligible'] += 1
            domains = [[] for _ in leaves]
            union = set()
            _take(budget, 'domains')
            for q in ctx.adj[root]:
                _take(budget, 'domains')
                if q == root:
                    continue
                eligible = mask(q) >> 1
                while eligible:
                    bit = eligible & -eligible
                    index = bit.bit_length() - 1
                    _take(budget, 'domains')
                    domains[index].append(q)
                    union.add(q)
                    info['domain_edges'] += 1
                    eligible ^= bit
            if any(not domain for domain in domains) or len(union) < len(leaves):
                continue
            matched = _matching(leaves, domains, budget, info)
            if matched is None:
                continue
            info['roots_matched'] += 1
            info['complete_proposals'] += 1
            sites = {center: root, **matched}
            certificate = _certificate(embedding, ctx, group, sites, cache, budget)
            if certificate is None:
                return finish(None, 'certificate_failed')
            replacement = {}
            for v in group:
                _take(budget, 'certificate')
                replacement[v] = [sites[v]]
            _complete(budget)
            info.update(certificate)
            info['accepted'] = 1
            return finish(replacement, 'accepted', True)
        _complete(budget)
        return finish(None, 'exhaustive_no_match', True)
    except _Interrupted as error:
        return finish(None, str(error))


class _SharedBudget:
    def __init__(self, search, visit, kind, limit=None):
        self.search, self.visit, self.kind, self.limit = search, visit, kind, limit
        self.expansions = 0
        self.stopped_by = None
        self.stages = {}

    def check(self):
        if not self.visit.check():
            self.stopped_by = self.visit.stopped_by or 'work_limit'
        elif self.search.info['work'] >= self.search.info['work_limit']:
            self.stopped_by = 'auxiliary_limit'
        elif self.limit is not None and self.expansions >= self.limit:
            self.stopped_by = 'query_limit'
        else:
            return True
        return False

    def charge(self, stage):
        if not self.check() or not self.visit.pop():
            if self.stopped_by is None:
                self.stopped_by = self.visit.stopped_by or 'work_limit'
            return False
        self.expansions += 1
        self.search.info['work'] += 1
        self.search.info[self.kind + '_work'] += 1
        self.stages[stage] = self.stages.get(stage, 0) + 1
        if self.kind == 'query':
            total = self.search.info['query_stage_work']
            total[stage] = total.get(stage, 0) + 1
        return True

    def pop(self):
        return self.charge(self.kind)


class StarSearch:
    """One lazy cache and auxiliary allowance for a contact-polish call.

    Construct with ``max_expansions // 20``. Constructor work is constant.
    ``propose`` charges the supplied active visit directly; its returned work is
    descriptive and must not be charged to that visit a second time. Aggregate
    ``info['work']`` equals setup+query+refresh and includes rejected work.
    Certified-proposal counters describe returned proposals, not caller commits;
    the scheduler records actual acceptance after its final deadline check.
    Refresh is a no-op before cache construction. Once disabled, no rebuild is
    attempted in this search object. Query-local maps never persist here.
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
                     'proposal_wall': 0.0, 'setup_wall': 0.0, 'refresh_wall': 0.0,
                     'last_refresh_work': 0, 'last_refresh_wall': 0.0,
                     'last_refresh_reason': None,
                     'reasons': {}}

    def _disable(self, reason):
        if self.cache is not None:
            self.cache.valid = False
        self.cache = None
        self.info['disabled_reason'] = reason

    def propose(self, embedding, center, visit_budget):
        start = time.perf_counter()
        old_work, old_setup = self.info['work'], self.info['setup_work']
        old_setup_wall = self.info['setup_wall']
        query = _SharedBudget(self, visit_budget, 'query', QUERY_LIMIT)
        self.info['considerations'] += 1
        group = None

        def finish(result, move):
            move = dict(move)
            move.setdefault('group', list(group) if group else [])
            move.setdefault('accepted', 0)
            move.setdefault('qubits_saved', 0)
            move.setdefault('contact_redundancy_gain', 0)
            move.setdefault('complete_proposals', 0)
            move['member_growth'] = move['equal_size_moves'] = 0
            move['query_work'] = query.expansions
            move['setup_work'] = self.info['setup_work'] - old_setup
            move['expansions'] = self.info['work'] - old_work
            move['stage_work'] = dict(query.stages)
            move['wall'] = time.perf_counter() - start
            move['setup_wall'] = self.info['setup_wall'] - old_setup_wall
            move['query_wall'] = move['wall'] - move['setup_wall']
            self.info['proposal_wall'] += move['wall']
            reasons = self.info['reasons']
            reasons[move['reason']] = reasons.get(move['reason'], 0) + 1
            self.info['certified_proposals'] += move['accepted']
            self.info['proposed_qubits_saved'] += move['qubits_saved']
            self.info['proposed_contact_redundancy_gain'] += move['contact_redundancy_gain']
            return result, move

        if self.info['disabled_reason'] is not None:
            return finish(None, {'reason': 'disabled', 'complete': False})
        if self.info['work'] >= self.info['work_limit']:
            self._disable('auxiliary_limit')
            return finish(None, {'reason': 'auxiliary_limit', 'complete': False})
        if self.cache is not None and (not self.cache.valid or self.cache.embedding is not embedding):
            self._disable('stale_cache')
            return finish(None, {'reason': 'stale_cache', 'complete': False})
        group, selection = select_star(embedding, self.ctx, center, query)
        if group is None:
            return finish(None, selection)
        if not self.setup_attempted:
            self.setup_attempted = True
            setup = _SharedBudget(self, visit_budget, 'setup')
            setup_start = time.perf_counter()
            self.cache = build_owner_cache(embedding, self.ctx, setup)
            self.info['setup_wall'] += time.perf_counter() - setup_start
            if self.cache is None:
                self._disable('setup_' + (setup.stopped_by or 'incomplete'))
                return finish(None, {'reason': self.info['disabled_reason'], 'complete': False})
            self.info['cache_builds'] += 1
        self.info['queries'] += 1
        result, move = query_star(embedding, self.ctx, group, self.cache, query)
        return finish(result, move)

    def refresh(self, old_embedding, embedding, selected, visit_budget):
        self.info['last_refresh_work'] = 0
        self.info['last_refresh_wall'] = 0.0
        self.info['last_refresh_reason'] = 'not_built_or_disabled'
        if self.cache is None:
            return True
        start = time.perf_counter()
        budget = _SharedBudget(self, visit_budget, 'refresh')
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
