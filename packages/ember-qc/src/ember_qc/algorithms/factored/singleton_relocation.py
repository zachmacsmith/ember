"""Bounded singleton proposals against the current frozen logical contacts.

The caller supplies a validated embedding of simple, undirected, loopless
graphs. This is a local proposal generator, not an embedding constructor. The
cache is usable only for the exact incumbent it describes; failed maintenance
invalidates it. Every physical adjacency scan uses the supplied work budget.
"""
from dataclasses import dataclass


@dataclass
class SingletonCache:
    owner: dict
    volume: dict
    ordered: dict
    queue: list
    embedding: object
    valid: bool = True


def _zero_eligible(embedding, ctx, v):
    neighbors = ctx.src_adj[v]
    return (len(embedding[v]) == 1 and len(neighbors) <= ctx.max_degree
            and any(len(embedding[w]) > 1 for w in neighbors))


def build_singleton_cache(embedding, ctx, budget):
    """Build once, charging one unit per source and occupied physical vertex."""
    owner, volume, ordered, queue = {}, {}, {}, []
    for v in ctx.nodes:
        if not budget.pop():
            return None
        if _zero_eligible(embedding, ctx, v):
            queue.append(v)
        total = 0
        for q in embedding[v]:
            if not budget.pop():
                return None
            owner[q] = v
            total += len(ctx.adj[q])
        volume[v] = total
        ordered[v] = tuple(sorted(embedding[v], key=ctx.rank.__getitem__))
    return SingletonCache(owner, volume, ordered, queue, embedding)


def refresh_singleton_cache(cache, old_embedding, embedding, selected, ctx, budget):
    """Refresh ownership atomically in validity status, including owner transfers.

    Partial maintenance may alter the dictionaries but always leaves valid=False.
    Callers must discard such a cache. Accepted embeddings are never modified.
    """
    if not cache.valid or cache.embedding is not old_embedding:
        cache.valid = False
        return False
    cache.valid = False
    for v in selected:
        for q in old_embedding[v]:
            if not budget.pop():
                return False
            del cache.owner[q]
    for v in selected:
        total = 0
        for q in embedding[v]:
            if not budget.pop():
                return False
            cache.owner[q] = v
            total += len(ctx.adj[q])
        cache.volume[v] = total
        cache.ordered[v] = tuple(sorted(embedding[v], key=ctx.rank.__getitem__))
    cache.embedding = embedding
    cache.valid = True
    return True


def direct_singleton(embedding, ctx, v, cache, budget, objective='qubits_contacts'):
    """Return a certified improving site and exact local score diagnostics.

    A truncated search may return its best fully inspected proposal. The caller
    must check the shared deadline again before committing it. Equal-score ties
    keep first discovery in stable seed-chain/target-adjacency order.
    """
    if not cache.valid or cache.embedding is not embedding:
        raise ValueError('singleton owner cache is stale')
    if objective not in ('qubits', 'qubits_contacts'):
        raise ValueError('unknown contact objective')
    info = {'reason': None, 'complete': False, 'candidates': 0,
            'old_redundancy': None, 'new_redundancy': None,
            'qubits_saved': 0, 'contact_redundancy_gain': 0}

    def finish(site, reason, complete=False):
        info['reason'], info['complete'] = reason, complete
        if site is not None:
            info['qubits_saved'] = len(embedding[v]) - 1
            info['contact_redundancy_gain'] = (
                info['new_redundancy'] - info['old_redundancy'])
        return site, info

    neighbors = ctx.src_adj[v]
    degree = len(neighbors)
    if degree > ctx.max_degree:
        return finish(None, 'degree_bound', True)
    if not budget.pop():
        return finish(None, budget.stopped_by or 'work_limit')
    old = embedding[v]
    if len(old) == 1:
        if objective == 'qubits':
            return finish(None, 'size_bound', True)
        if all(len(embedding[w]) == 1 for w in neighbors):
            return finish(None, 'singleton_neighbors', True)
    required = set(neighbors)
    old_count = 0
    own_min = None
    for p in old:
        if not budget.pop():
            return finish(None, budget.stopped_by or 'work_limit')
        old_count += sum(cache.owner.get(q) in required for q in ctx.adj[p])
        if own_min is None or ctx.rank[p] < ctx.rank[own_min]:
            own_min = p
    info['old_redundancy'] = old_count - degree
    if not neighbors:
        info['new_redundancy'] = 0
        return finish(own_min, 'isolated_shortening', True)
    upper = ctx.max_degree - degree
    if len(old) == 1 and info['old_redundancy'] >= upper:
        return finish(None, 'redundancy_bound', True)
    # src_adj is already in stable logical order; min keeps its first tie.
    seed = min(neighbors, key=cache.volume.__getitem__)
    seen = set()
    best, best_score = None, None
    for p in cache.ordered[seed]:
        if not budget.pop():
            return finish(best, budget.stopped_by or 'work_limit')
        for q in ctx.adj[p]:
            if q in seen:
                continue
            seen.add(q)
            if (q in cache.owner and cache.owner[q] != v) or len(ctx.adj[q]) < degree:
                continue
            if not budget.pop():
                return finish(best, budget.stopped_by or 'work_limit')
            info['candidates'] += 1
            contacts = set()
            count = 0
            for r in ctx.adj[q]:
                owner = cache.owner.get(r)
                if owner in required:
                    contacts.add(owner)
                    count += 1
            if contacts != required:
                continue
            score = count - degree
            if len(old) == 1 and score <= info['old_redundancy']:
                continue
            if best_score is None or score > best_score:
                best, best_score = q, score
                info['new_redundancy'] = score
            if score == upper:
                return finish(best, 'redundancy_bound', True)
    return finish(best, 'scanned', True)


class _AuxBudget:
    """Charge one shared group budget and one call-wide auxiliary allowance."""
    def __init__(self, search, group_budget, kind, limit=None):
        self.search, self.group_budget = search, group_budget
        self.kind, self.limit = kind, limit
        self.expansions = 0
        self.stopped_by = None

    def check(self):
        if not self.group_budget.check():
            self.stopped_by = self.group_budget.stopped_by
            return False
        if self.search.info['work'] >= self.search.info['work_limit']:
            self.stopped_by = 'auxiliary_limit'
            return False
        if self.limit is not None and self.expansions >= self.limit:
            self.stopped_by = 'scan_limit'
            return False
        return True

    def pop(self):
        if not self.check():
            return False
        if not self.group_budget.pop():
            self.stopped_by = self.group_budget.stopped_by
            return False
        self.expansions += 1
        self.search.info['work'] += 1
        self.search.info[self.kind] += 1
        return True


class SingletonSearch:
    """One optional, bounded proposal stage within the caller's group visits."""
    def __init__(self, ctx, work_limit, extra_limit):
        self.ctx = ctx
        self.cache = None
        self.queue_index = 0
        self.setup_attempted = False
        self.extra_limit = extra_limit
        self.info = {
            'work_limit': work_limit, 'work': 0, 'setup_work': 0,
            'refresh_work': 0, 'queue_work': 0, 'scan_work': 0,
            'cache_builds': 0, 'cache_refreshes': 0, 'disabled_reason': None,
            'direct_visits': 0, 'extra_slots': 0, 'extra_visits': 0,
            'candidates': 0, 'complete_scans': 0, 'proven_stops': 0,
            'truncated_scans': 0,
            'degree_skips': 0, 'exact_skips': 0,
            'accepted': 0, 'qubits_saved': 0, 'equal_size_moves': 0,
            'contact_redundancy_gain': 0, 'reasons': {},
            'ordinary_groups_tried': 0, 'ordinary_groups_displaced': 0,
            'visit_work_peak': 0,
        }

    def _disable(self, reason):
        if self.cache is not None:
            self.cache.valid = False
        self.cache = None
        self.info['disabled_reason'] = reason

    def active(self):
        if self.info['disabled_reason'] is not None:
            return False
        if self.info['work'] >= self.info['work_limit']:
            self._disable('auxiliary_limit')
            return False
        return True

    def _ensure_cache(self, embedding, group_budget):
        if not self.active():
            return False
        if not self.setup_attempted:
            self.setup_attempted = True
            budget = _AuxBudget(self, group_budget, 'setup_work')
            self.cache = build_singleton_cache(embedding, self.ctx, budget)
            if self.cache is None:
                self._disable('setup_' + (budget.stopped_by or 'incomplete'))
                return False
            self.info['cache_builds'] += 1
        return self.cache is not None

    def propose(self, embedding, v, group_budget, objective, scan_limit=256):
        if len(self.ctx.src_adj[v]) > self.ctx.max_degree:
            self.info['degree_skips'] += 1
            return None, None
        if not self._ensure_cache(embedding, group_budget):
            return None, None
        budget = _AuxBudget(self, group_budget, 'scan_work', scan_limit)
        site, move = direct_singleton(embedding, self.ctx, v, self.cache, budget, objective)
        self.info['direct_visits'] += 1
        self.info['candidates'] += move['candidates']
        if move['reason'] == 'scanned':
            self.info['complete_scans'] += 1
        elif move['complete']:
            self.info['proven_stops'] += 1
        else:
            self.info['truncated_scans'] += 1
        if move['reason'] in ('size_bound', 'singleton_neighbors', 'redundancy_bound') and site is None:
            self.info['exact_skips'] += 1
        reasons = self.info['reasons']
        reasons[move['reason']] = reasons.get(move['reason'], 0) + 1
        return site, move

    def refresh(self, old_embedding, embedding, group, group_budget):
        if self.cache is None:
            return
        budget = _AuxBudget(self, group_budget, 'refresh_work')
        if refresh_singleton_cache(self.cache, old_embedding, embedding, group,
                                   self.ctx, budget):
            self.info['cache_refreshes'] += 1
        else:
            self._disable('refresh_' + (budget.stopped_by or 'stale'))

    def extra_available(self):
        return (self.active() and self.info['extra_slots'] < self.extra_limit
                and (not self.setup_attempted or
                     (self.cache is not None and self.queue_index < len(self.cache.queue))))

    def next_extra(self, embedding, group_budget):
        """Return an eligible vertex and unused part of its 256 scan units."""
        if not self.extra_available():
            return None, 256
        self.info['extra_slots'] += 1
        if not self._ensure_cache(embedding, group_budget):
            return None, 256
        if not self.cache.valid or self.cache.embedding is not embedding:
            raise ValueError('singleton owner cache is stale')
        budget = _AuxBudget(self, group_budget, 'queue_work', 256)
        while self.queue_index < len(self.cache.queue):
            if not budget.pop():
                break
            v = self.cache.queue[self.queue_index]
            self.queue_index += 1
            if _zero_eligible(embedding, self.ctx, v):
                self.info['extra_visits'] += 1
                return v, 256 - budget.expansions
        return None, 256 - budget.expansions
