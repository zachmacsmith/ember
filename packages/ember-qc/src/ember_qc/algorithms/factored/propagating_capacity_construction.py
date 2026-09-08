"""Exploratory joint connected-chain insertion with extension-frontier protection.

Standalone standard-library constructor, specified in b_conflict_directed_releases.md.
This module copies only basic graph/budget/validity helpers from rejected B001;
it neither imports nor calls its constructor or rooted-union proposal.
"""
from collections import deque
from itertools import combinations
import heapq
import math
import random
import time

ROOTS = 64
BRANCHES = 4
SCANS = 20_000_000
PROPAGATION_CALL = 200_000
PROPAGATION_TOTAL = 5_000_000
VALUES = 4
MATCHING_QUERY = 100_000
MATCHING_TOTAL = 2_000_000
GROWTH_STEPS = 4
GROWTH_SITES = 4
GROWTH_QUERY = 500_000
GROWTH_TOTAL = 3_000_000
REPAIR_QUERY = 1_000_000
REPAIR_TOTAL = 5_000_000

class _RepairLimit(Exception):
    pass

class _GrowthLimit(Exception):
    pass

class _MatchingQueryLimit(Exception):
    pass

class _PropagationLimit(Exception):
    pass

class _Stop(Exception):
    pass

class _Engine:
    def __init__(self, source, target, deadline, seed, info):
        self.deadline, self.info = deadline, info
        self.scans = 0
        try:
            self.source = self.graph(source)
            self.target = self.graph(target)
        except BaseException:
            info['scan_count'] = self.scans
            raise
        rng = random.Random(seed)
        vs, qs = sorted(self.source), sorted(self.target)
        rng.shuffle(vs); rng.shuffle(qs)
        self.vrank = {v: i for i, v in enumerate(vs)}
        self.qrank = {q: i for i, q in enumerate(qs)}

    def check(self):
        if time.perf_counter() >= self.deadline:
            self.info['stopped_by'] = 'deadline'
            self.info['scan_count'] = self.scans
            raise _Stop

    def scan(self):
        if self.scans >= SCANS:
            self.info['stopped_by'] = 'work_limit'
            self.info['scan_count'] = self.scans
            raise _Stop
        self.scans += 1
        if self.scans % 256 == 0:
            self.check()

    def graph(self, graph):
        self.check()
        if graph.is_directed() or graph.is_multigraph():
            raise ValueError('simple undirected graphs required')
        nodes = list(graph)
        if any(type(v) is not int for v in nodes):
            raise ValueError('ordinary integer graph labels required')
        adj = {}
        for v in sorted(nodes):
            self.check()
            row = []
            for w in graph[v]:
                self.scan()
                if type(w) is not int or w == v:
                    raise ValueError('loop or invalid neighbor')
                row.append(w)
            adj[v] = tuple(sorted(row))
        return adj

    def occupied(self, chains):
        self.check()
        return {q: v for v, chain in chains.items() for q in chain}

    def boundary(self, chain, free):
        out = set()
        for q in chain:
            for p in self.target[q]:
                self.scan()
                if p in free:
                    out.add(p)
        return out

    def valid(self, chains, *, complete):
        self.check()
        if (complete and set(chains) != set(self.source)) or not set(chains) <= set(self.source):
            return False
        owner = {}
        for v, c in chains.items():
            if not c:
                return False
            for q in c:
                if q not in self.target or q in owner:
                    return False
                owner[q] = v
            start = next(iter(c))
            seen, stack = {start}, [start]
            while stack:
                q = stack.pop()
                for p in self.target[q]:
                    self.scan()
                    if p in c and p not in seen:
                        seen.add(p); stack.append(p)
            if seen != set(c):
                return False
        contacts = set()
        for q, v in owner.items():
            for p in self.target[q]:
                self.scan()
                if p in owner and owner[p] != v:
                    contacts.add((v, owner[p]))
        for v in chains:
            if any(w in chains and (v, w) not in contacts for w in self.source[v]):
                return False
        self.check()
        return True


class _Builder(_Engine):
    def __init__(self, source, target, deadline, seed, info):
        super().__init__(source, target, deadline, seed, info)
        self.bit = {q: 1 << i for i, q in enumerate(self.target)}
        self.all_bits = sum(self.bit.values())
        self.adj_bits = {}
        for q, row in self.target.items():
            self.check()
            mask = 0
            for p in row:
                self.scan()
                mask |= self.bit[p]
            self.adj_bits[q] = mask
        self.delta = max(map(len, self.target.values()), default=0)
        self.qsites = tuple(self.target)

    def state(self, chains):
        self.check()
        owners, masks, bounds = {}, {}, {}
        used = 0
        for v, chain in chains.items():
            cm, cb = 0, 0
            for q in chain:
                cm |= self.bit[q]
                cb |= self.adj_bits[q]
                owners[q] = v
            masks[v], bounds[v] = cm, cb
            used |= cm
        return owners, masks, bounds, self.all_bits ^ used

    def future(self, v, chains):
        return sum(w not in chains for w in self.source[v])

    def frontier_ok(self, chains, bounds, free):
        self.check()
        return all(not self.future(v, chains) or bounds[v] & free for v in chains)

    def domains(self, chains, bounds, free):
        sizes = []
        for v in self.source:
            self.check()
            if v in chains or len(self.source[v]) > self.delta:
                continue
            placed = [w for w in self.source[v] if w in chains]
            if not placed:
                continue
            mask = free
            for w in placed:
                mask &= bounds[w]
            sizes.append(mask.bit_count())
        return tuple(sorted(sizes))

    def contacts(self, v, chains, bounds=None, masks=None):
        if bounds is None:
            _, masks, bounds, _ = self.state(chains)
        return {w for w in self.source[v] if w in chains and bounds[v] & masks[w]}

    def prepare(self, v, entry, frozen=frozenset()):
        """Stage urgent old-chain growth; published entry is never changed."""
        trial = self.copy_chains(entry)
        for w in sorted((u for u in self.source[v] if u in trial), key=self.vrank.__getitem__):
            after = sum(z not in trial and z != v for z in self.source[w])
            if not after:
                continue
            while True:
                self.check()
                owners, _, bounds, free = self.state(trial)
                mask = bounds[w] & free
                if mask.bit_count() >= 2:
                    break
                if not mask or w in frozen:
                    return None
                # There is one extension port. On a degree-two corridor this
                # may not open a second: finite growth or the common cap ends it.
                q = next(q for q in self.target if self.bit[q] & mask)
                trial[w].add(q)
                self.info['staged_extension_sites'] += 1
                self.scan()
        return trial

    def prices(self, chains, owners, bounds, free):
        weights = {v: self.future(v, chains)/max(1, (bounds[v] & free).bit_count())
                   for v in chains}
        cache = {}
        def price(q):
            if q not in cache:
                touching = set()
                for p in self.target[q]:
                    self.scan()
                    if p in owners:
                        touching.add(owners[p])
                pressure = sum(weights[v] for v in touching)
                cache[q] = 1. + pressure/(1. + pressure)
            return cache[q]
        return price

    def unusable_ports(self, v, chains, bounds, free, missing):
        """Necessary exclusion for every eligible two-ended ownership cut."""
        self.info.setdefault('port_filter_records', [])
        self.info.setdefault('port_filter_units', 0)
        self.info.setdefault('port_owner_checks', 0)
        self.info.setdefault('port_source_checks', 0)
        started, began = self.scans, time.perf_counter()
        protected = {}
        record = dict(vertex=v, missing=sorted(missing), status='started', blocked_sites=[])
        try:
            self.check()
            for u in chains:
                self.scan(); self.info['port_owner_checks'] += 1
                if u == v:
                    continue
                mask = bounds[u] & free
                if not mask or mask & (mask-1):
                    continue
                pending = False
                for w in self.source[u]:
                    self.scan(); self.info['port_source_checks'] += 1
                    if w not in chains:
                        pending = True
                        break
                if pending:
                    q = self.qsites[mask.bit_length()-1]
                    protected.setdefault(q, set()).add(u)
            blocked = {q for q, owners in protected.items()
                       if len(owners)>1 or not owners <= missing}
            self.check()
            record.update(status='complete', blocked_sites=sorted(blocked),
                          protected_owners={q: sorted(owners) for q, owners in protected.items()})
            return blocked
        except _Stop:
            record['status'] = self.info.get('stopped_by') or 'interrupted'
            raise
        except _RepairLimit:
            record['status'] = 'repair_limit'
            raise
        finally:
            record.update(units=self.scans-started, wall=time.perf_counter()-began)
            self.info['port_filter_units'] += record['units']
            self.info['port_filter_records'].append(record)

    def path(self, v, chains, missing):
        owners, _, bounds, free = self.state(chains)
        blocked = self.unusable_ports(v, chains, bounds, free, missing)
        price = self.prices(chains, owners, bounds, free)
        dist, parent, heap = {}, {}, []
        for q in sorted(chains[v], key=self.qrank.__getitem__):
            dist[q], parent[q] = 0., None
            heap.append((0., self.qrank[q], q))
        heapq.heapify(heap)
        while heap:
            self.check()
            d, _, q = heapq.heappop(heap)
            if d != dist[q]:
                continue
            hits = set()
            for p in self.target[q]:
                self.scan()
                if owners.get(p) in missing:
                    hits.add(owners[p])
            if hits:
                w = min(hits, key=self.vrank.__getitem__)
                path = []
                while parent[q] is not None:
                    path.append(q)
                    q = parent[q]
                path.reverse()
                return w, path
            for p in self.target[q]:
                self.scan()
                if p in owners or p in blocked:
                    continue
                nd = d + price(p)
                if nd < dist.get(p, math.inf):
                    dist[p], parent[p] = nd, q
                    heapq.heappush(heap, (nd, self.qrank[p], p))
        return None

    def cut(self, v, w, path, chains, required, frozen=frozenset()):
        """Choose one connected ownership cut; every candidate has identical Q."""
        best, best_key = None, None
        cuts = (len(path),) if w in frozen else range(len(path), -1, -1)
        for cut in cuts:
            self.check()
            trial = dict(chains)
            trial[v] = chains[v] | set(path[:cut])
            trial[w] = chains[w] | set(path[cut:])
            _, masks, bounds, free = self.state(trial)
            if not self.frontier_ok(trial, bounds, free):
                continue
            missing = len(required-self.contacts(v, trial, bounds, masks))
            key = (missing, tuple(-n for n in self.domains(trial, bounds, free)), -cut)
            if best_key is None or key < best_key:
                best, best_key = trial, key
        return best

    def prune(self, chains, changed):
        """Safe local deletion, including non-articulation sites in a cycle."""
        chains = dict(chains)
        for v in sorted(changed, key=lambda u: (-len(chains[u]), self.vrank[u])):
            while len(chains[v]) > 1:
                removed = False
                for q in sorted(chains[v], key=self.qrank.__getitem__, reverse=True):
                    self.check()
                    remainder = chains[v] - {q}
                    if not remainder:
                        continue
                    first = next(iter(remainder))
                    seen, stack = {first}, [first]
                    bound = 0
                    while stack:
                        p = stack.pop()
                        bound |= self.adj_bits[p]
                        for r in self.target[p]:
                            self.scan()
                            if r in remainder and r not in seen:
                                seen.add(r); stack.append(r)
                    if seen != remainder:
                        continue
                    _, masks, _, free = self.state(chains)
                    if any(w in chains and not (bound & masks[w]) for w in self.source[v]):
                        continue
                    if self.future(v, chains) and not (bound & (free | self.bit[q])):
                        continue
                    chains[v] = remainder
                    removed = True
                    self.info['staged_pruned_sites'] += 1
                if not removed:
                    break
        return chains

    def insert(self, v, entry, frozen=frozenset()):
        self.info['insertion_queries'] += 1
        prepared = self.prepare(v, entry, frozen)
        if prepared is None:
            self.info['preparation_failures'] += 1
            return None
        owners, masks, bounds, free = self.state(prepared)
        required = set(self.source[v]) & prepared.keys()
        pool_mask = free
        if required:
            pool_mask = 0
            for w in required:
                pool_mask |= bounds[w]
            pool_mask &= free
        price = self.prices(prepared, owners, bounds, free)
        pool = [q for q in self.target if self.bit[q] & pool_mask]
        def direct(q):
            return sum(bool(self.adj_bits[q] & masks[w]) for w in required)
        pool.sort(key=lambda q: (-direct(q), price(q),
                                -(self.adj_bits[q] & free).bit_count(), self.qrank[q]))
        roots = []
        for q in pool[:ROOTS]:
            self.check()
            trial = dict(prepared); trial[v] = {q}
            qb = dict(bounds); qb[v] = self.adj_bits[q]
            qf = free ^ self.bit[q]
            if not self.frontier_ok(trial, qb, qf):
                continue
            key = (-direct(q), tuple(-n for n in self.domains(trial, qb, qf)),
                   price(q), self.qrank[q])
            roots.append((key, q))
        roots.sort()
        best, best_key = None, None
        for _, root in roots[:BRANCHES]:
            self.info['root_branches'] += 1
            trial = self.copy_chains(prepared)
            trial[v] = {root}
            while True:
                self.check()
                missing = required-self.contacts(v, trial)
                if not missing:
                    break
                self.info['path_queries'] += 1
                found = self.path(v, trial, missing)
                if found is None:
                    trial = None
                    break
                w, path = found
                if not path:
                    raise RuntimeError('missing contact yielded empty path')
                trial = self.cut(v, w, path, trial, required, frozen)
                if trial is None:
                    self.info['frontier_rejections'] += 1
                    break
            if trial is None:
                continue
            changed = {w for w in trial if w not in frozen and (w not in entry or trial[w] != entry[w])}
            trial = self.prune(trial, changed)
            _, _, tb, tf = self.state(trial)
            if not self.frontier_ok(trial, tb, tf) or not self.valid(trial, complete=False):
                raise RuntimeError('invalid completed private insertion')
            key = (sum(map(len, trial.values())),
                   tuple(-n for n in self.domains(trial, tb, tf)), self.qrank[root])
            if best_key is None or key < best_key:
                best, best_key = trial, key
        self.check()
        return best


    def scan(self):
        if self.scans >= SCANS:
            return super().scan()
        if getattr(self, 'repair_end', None) is not None and self.scans >= self.repair_end:
            raise _RepairLimit
        if getattr(self, 'growth_end', None) is not None and self.scans >= self.growth_end:
            raise _GrowthLimit
        super().scan()

    def copy_chains(self, chains, excluded=frozenset()):
        if getattr(self, 'repair_end', None) is None:
            return {u: set(c) for u, c in chains.items() if u not in excluded}
        copied = {}
        for u, chain in chains.items():
            self.scan()
            if u not in excluded:
                copied[u] = set()
                for q in chain:
                    self.scan()
                    copied[u].add(q)
        return copied

    def sites(self, mask):
        while mask:
            low = mask & -mask
            yield self.qsites[low.bit_length()-1]
            mask ^= low

    def propagation_unit(self):
        if self.scans >= self.propagation_end:
            raise _PropagationLimit
        self.scan()

    def neighborhood(self, mask, free):
        union = 0
        for q in self.sites(mask):
            self.propagation_unit()
            self.info['neighborhood_unions'] += 1
            union |= self.adj_bits[q]
            if union & free == free:
                break
        return union

    def arc_queue(self, domains, free):
        """Sound revisions only; interrupted neighborhood unions are discarded."""
        domains = dict(domains)
        remaining = PROPAGATION_TOTAL-self.info['propagation_units']
        started = self.scans
        self.propagation_end = started+min(PROPAGATION_CALL, max(0, remaining))
        record = dict(complete=False, units=0, revisions=0, removed_values=0, status='started')
        queue, queued, cache = deque(), set(), {}
        try:
            self.check()
            if any(not mask for mask in domains.values()):
                record['status'] = 'empty_input_domain'
                return domains, record
            for u in domains:
                for v in self.source[u]:
                    self.propagation_unit()
                    if v in domains:
                        queue.append((u, v)); queued.add((u, v))
            while queue:
                self.check()
                self.propagation_unit()
                u, v = queue.popleft(); queued.remove((u, v))
                mask = domains[v]
                if mask not in cache:
                    supported = self.neighborhood(mask, free)
                    if len(cache) >= 256:
                        cache.clear()
                    cache[mask] = supported
                revised = domains[u] & cache[mask]
                if revised == domains[u]:
                    continue
                record['removed_values'] += domains[u].bit_count()-revised.bit_count()
                record['revisions'] += 1
                domains[u] = revised
                if not revised:
                    record['status'] = 'empty_domain'
                    return domains, record
                for w in self.source[u]:
                    self.propagation_unit()
                    if w in domains and w != v and (w, u) not in queued:
                        queue.append((w, u)); queued.add((w, u))
            self.check()
            record.update(complete=True, status='complete')
            return domains, record
        except _PropagationLimit:
            record['status'] = 'propagation_limit'
            return domains, record
        except _RepairLimit:
            record['status'] = 'repair_limit'
            raise
        except _GrowthLimit:
            record['status'] = 'growth_limit'
            raise
        except _Stop:
            record['status'] = self.info.get('stopped_by') or 'interrupted'
            raise
        finally:
            record['units'] = self.scans-started
            self.info['propagation_units'] += record['units']
            self.info['propagation_records'].append(record)

    def singleton_domains(self, chains, promoted, omit_contact=None):
        self.check()
        started = self.scans
        self.info['domain_build_calls'] = self.info.get('domain_build_calls', 0)+1
        _, _, bounds, free = self.state(chains)
        domains = {}
        for u in self.source:
            self.check()
            if u in chains or u in promoted:
                continue
            mask = free
            for w in self.source[u]:
                self.scan(); self.info['domain_source_entries'] += 1
                if w in chains and w != omit_contact:
                    mask &= bounds[w]
            domains[u] = mask
        domains, record = self.arc_queue(domains, free)
        self.last_domain_result = (domains, record['complete'], self.scans-started, record['units'])
        return domains

    def matching(self, domains):
        """Complete maximum matching or an explicit unknown; all work charged."""
        self.info.setdefault('matching_units', 0)
        self.info.setdefault('matching_records', [])
        started, began = self.scans, time.perf_counter()
        remaining = MATCHING_TOTAL-self.info['matching_units']
        left, right = {}, {}
        record = dict(status='started', variables=len(domains), matched=0,
                      deficit=None, units=0, edge_scans=0)
        def unit():
            used = self.scans-started
            if used >= remaining:
                self.info['stopped_by'] = 'matching_work_limit'
                raise _Stop
            if used >= MATCHING_QUERY:
                raise _MatchingQueryLimit
            self.scan()
        try:
            self.check()
            for root in sorted(domains, key=lambda u: (domains[u].bit_count(), u)):
                unit()
                queue, seen, parent = deque([root]), {root}, {}
                finish = None
                while queue and finish is None:
                    unit()
                    u = queue.popleft()
                    for q in self.sites(domains[u]):
                        unit(); record['edge_scans'] += 1
                        if q in parent:
                            continue
                        parent[q] = u
                        if q not in right:
                            finish = q
                            break
                        v = right[q]
                        if v not in seen:
                            seen.add(v); queue.append(v)
                if finish is not None:
                    q = finish
                    while True:
                        unit()
                        u = parent[q]; previous = left.get(u)
                        left[u] = q; right[q] = u
                        if previous is None:
                            break
                        q = previous
            self.check()
            record.update(status='covering' if len(left)==len(domains) else 'deficit',
                          deficit=len(domains)-len(left))
            return record
        except _MatchingQueryLimit:
            record['status'] = 'query_limit'
            return record
        except _RepairLimit:
            record['status'] = 'repair_limit'
            raise
        except _GrowthLimit:
            record['status'] = 'growth_limit'
            raise
        except _Stop:
            record['status'] = self.info.get('stopped_by') or 'interrupted'
            raise
        finally:
            record.update(matched=len(left), units=self.scans-started, wall=time.perf_counter()-began)
            self.info['matching_units'] += record['units']
            self.info['matching_records'].append(record)

    def singleton(self, v, entry, promoted, domains):
        self.completed_singleton_domains = None
        _, _, bounds, free = self.state(entry)
        candidates = []
        for q in self.sites(domains[v]):
            self.check()
            counts = []
            for w in self.source[v]:
                self.scan(); self.info['value_support_tests'] += 1
                if w in domains:
                    counts.append((self.adj_bits[q]&domains[w]).bit_count())
            if counts and min(counts) == 0:
                continue
            key = (tuple(-n for n in sorted(counts)),
                   -(self.adj_bits[q]&free).bit_count(), self.qrank[q])
            candidates.append((key, q))
        candidates.sort()
        for _, q in candidates[:VALUES]:
            self.check()
            self.info['singleton_trials'] += 1
            trial = dict(entry); trial[v] = {q}
            qb = dict(bounds); qb[v] = self.adj_bits[q]
            if not self.frontier_ok(trial, qb, free ^ self.bit[q]):
                continue
            next_domains = self.singleton_domains(trial, promoted)
            if any(not mask for mask in next_domains.values()):
                self.info['rejected_empty_domains'] += 1
                continue
            if not self.last_domain_result[1]:
                self.info.setdefault('singleton_feasibility_rejections', []).append('propagation_incomplete')
                continue
            match = self.matching(next_domains)
            if match['status'] != 'covering':
                self.info.setdefault('singleton_feasibility_rejections', []).append(match['status'])
                continue
            if not self.valid(trial, complete=False):
                raise RuntimeError('invalid private singleton assignment')
            self.check()
            _, complete, units, propagation_units = self.last_domain_result
            if complete:
                self.completed_singleton_domains = (next_domains, dict(after_vertex=v,
                    domain_count=len(next_domains), origin_units=units,
                    origin_propagation_units=propagation_units))
            return trial
        return None


    def future_growth(self, v, base, promoted):
        """Grow only v; unresolved private work rolls back to valid base."""
        self.completed_singleton_domains = None
        remaining = GROWTH_TOTAL-self.info['growth_units']
        if remaining <= 0:
            self.info['growth_skipped_budget'] += 1
            return base, None
        started, began = self.scans, time.perf_counter()
        self.growth_end = started+min(GROWTH_QUERY, remaining)
        record = dict(vertex=v, status='started', units=0, trials=0, steps=0,
                      extra_sites=0, base_insertion_committed=False, extra_q_committed=False)
        self.info['growth_queries'] += 1
        try:
            self.check()
            future = []
            for w in self.source[v]:
                self.scan()
                if w not in base and w not in promoted:
                    future.append(w)
            if not future:
                record['status'] = 'no_singleton_neighbor'
                return base, record
            actual = self.singleton_domains(base, promoted)
            if not any(not mask for mask in actual.values()):
                if not self.last_domain_result[1]:
                    record['status'] = 'unresolved_propagation_limit'
                    return base, record
                match = self.matching(actual)
                if match['status'] == 'covering':
                    record['status'] = 'already_consistent'
                    return base, record
                if match['deficit'] is None:
                    record['status'] = 'unresolved_matching_limit'
                    return base, record
                record['initial_matching_deficit'] = match['deficit']
            record['initial_empty'] = sum(not mask for mask in actual.values())
            current = self.copy_chains(base)
            for step in range(GROWTH_STEPS):
                self.check()
                relaxed = self.singleton_domains(current, promoted, omit_contact=v)
                if any(not mask for mask in relaxed.values()):
                    record['status'] = 'relaxed_empty'
                    return base, record
                relaxed_match = self.matching(relaxed)
                if relaxed_match['status'] == 'deficit':
                    record['status'] = 'relaxed_hall_deficit'
                    return base, record
                if relaxed_match['deficit'] is None:
                    record['status'] = 'unresolved_matching_limit'
                    return base, record
                _, _, bounds, free = self.state(current)
                old_bound = bounds[v]
                def rank(q):
                    proposed_bound = old_bound | self.adj_bits[q]
                    available = free ^ self.bit[q]
                    counts = []
                    for w in future:
                        self.scan()
                        counts.append((relaxed[w] & proposed_bound & available).bit_count())
                    return (sum(n == 0 for n in counts), tuple(-n for n in sorted(counts)),
                            -(self.adj_bits[q] & available).bit_count(), self.qrank[q])
                pool = sorted(self.sites(old_bound & free), key=rank)
                best, best_key, unknown_trials = None, None, 0
                for q in pool[:GROWTH_SITES]:
                    self.check()
                    record['trials'] += 1
                    trial = dict(current); trial[v] = current[v] | {q}
                    self.completed_singleton_domains = None
                    _, _, tb, tf = self.state(trial)
                    if not self.frontier_ok(trial, tb, tf):
                        continue
                    actual = self.singleton_domains(trial, promoted)
                    counts = [mask.bit_count() for mask in actual.values()]
                    match = self.matching(actual)
                    if match['deficit'] is None:
                        unknown_trials += 1
                        continue
                    if self.last_domain_result[1] and match['status'] == 'covering':
                        # Local certificate: connected free growth preserves base's
                        # contacts, ownership and every frozen chain exactly.
                        if not base[v] <= trial[v] or any(trial[u] != base[u] for u in base if u != v):
                            raise RuntimeError('growth changed frozen chains')
                        self.check()
                        record.update(status='resolved', steps=step+1,
                                      extra_sites=len(trial[v])-len(base[v]),
                                      matching_deficit=0, propagation_complete=True)
                        return trial, record
                    key = (match['deficit'], tuple(-n for n in sorted(counts)), self.qrank[q])
                    if best_key is None or key < best_key:
                        best, best_key = trial, key
                if best is None:
                    record['status'] = ('unresolved_matching_limit' if unknown_trials
                                        else 'blocked_frontier')
                    return base, record
                current = best
                record['steps'] = step+1
            record['status'] = 'neighborhood_limit'
            return base, record
        except _RepairLimit:
            record['status'] = 'repair_limit'
            raise
        except _GrowthLimit:
            record['status'] = 'local_work_limit'
            return base, record
        except _Stop:
            record['status'] = self.info.get('stopped_by') or 'interrupted'
            raise
        except Exception as error:
            record.update(status='error', error=repr(error))
            raise
        finally:
            self.growth_end = None
            record.update(units=self.scans-started, wall=time.perf_counter()-began)
            self.info['growth_units'] += record['units']
            self.info['growth_records'].append(record)

    def repair_pool(self, v, entry, record):
        """Complete capped pool from immutable boundaries; arbitrary source degree."""
        self.check()
        _, _, bounds, free = self.state(entry)
        required = []
        for w in self.source[v]:
            self.scan()
            if w in entry:
                required.append(w)
        boundary = {}
        union = 0
        for w in required:
            self.scan()
            boundary[w] = bounds[w] & free
            union |= boundary[w]
        competitors, contested = [], 0
        for w in entry:
            self.scan()
            if w in boundary:
                continue
            mask = bounds[w] & free
            if not mask or mask & (mask-1) or not mask & union:
                continue
            pending = False
            for z in self.source[w]:
                self.scan()
                if z not in entry and z != v:
                    pending = True
                    break
            if not pending:
                continue
            hits = 0
            for r in required:
                self.scan()
                hits += bool(boundary[r] & mask)
            competitors.append(((-hits, len(entry[w]), self.vrank[w]), w))
            contested |= mask
        self.check()
        competitors.sort()
        ranked_required = sorted(required, key=lambda w: (
            not (boundary[w] and not boundary[w] & ~contested),
            len(entry[w]), self.vrank[w]))
        self.check()
        pool = [w for _, w in competitors[:2]] + ranked_required[:4]
        blocks = []
        for size in (1, 2):
            for positions in combinations(range(len(pool)), size):
                self.scan()
                block = tuple(pool[i] for i in positions)
                blocks.append(((sum(len(entry[w]) for w in block), size, positions), block))
        blocks.sort()
        self.check()
        record.update(required=required, required_ranked=ranked_required,
                      competitors_ranked=[w for _, w in competitors], pool=pool,
                      omitted_required=ranked_required[4:],
                      omitted_competitors=[w for _, w in competitors[2:]],
                      blocked_required=[w for w in ranked_required
                          if boundary[w] and not boundary[w] & ~contested],
                      ordered_blocks=[list(block) for _, block in blocks])
        return [block for _, block in blocks]

    def block_capacity(self, v, entry, selected, *, block_index=None):
        """Necessary final-block contact capacity; unknown never rejects."""
        self.info.setdefault('capacity_assessment_units', 0)
        self.info.setdefault('capacity_assessment_records', [])
        started, began = self.scans, time.perf_counter()
        record = dict(vertex=v, selected=list(selected), block_index=block_index,
                      status='started', admissible=None, rows=[])
        try:
            self.check()
            W = set(selected) | {v}
            frozen = self.copy_chains(entry, set(selected))
            _, _, bounds, free = self.state(frozen)
            present = set(frozen) | W
            protected, forbidden = {}, 0
            for u in frozen:
                self.scan()
                mask = bounds[u] & free
                demand, future = [], []
                for w in self.source[u]:
                    self.scan()
                    if w in W:
                        demand.append(w)
                    elif w not in present:
                        future.append(w)
                boundary = []
                for q in self.sites(mask):
                    self.scan(); boundary.append(q)
                row = dict(owner=u, boundary=boundary, selected_neighbors=demand,
                           remaining_future=future, d=len(demand), p=int(bool(future)))
                record['rows'].append(row)
                if mask and not mask & (mask-1) and future:
                    q = boundary[0]
                    protected.setdefault(q, []).append(u)
                    forbidden |= mask
            violations = []
            for row in record['rows']:
                self.scan()
                usable = []
                for q in row['boundary']:
                    self.scan()
                    if not self.bit[q] & forbidden:
                        usable.append(q)
                row.update(usable=usable,
                           contact_shortage=max(0, row['d']-len(usable)),
                           frontier_shortage=max(0, row['d']+row['p']-len(row['boundary'])))
                row['violated'] = bool(row['contact_shortage'] or row['frontier_shortage'])
                if row['violated']:
                    violations.append(row['owner'])
            self.check()
            record.update(status='complete', admissible=not violations,
                          violated_owners=violations, protected_sites=protected)
            return record
        except _RepairLimit:
            record['status'] = 'repair_limit'
            raise
        except _Stop:
            record['status'] = self.info.get('stopped_by') or 'interrupted'
            raise
        finally:
            record.update(units=self.scans-started, wall=time.perf_counter()-began)
            self.info['capacity_assessment_units'] += record['units']
            self.info['capacity_assessment_records'].append(record)

    def capacity_order(self, v, entry, blocks, record):
        """Complete assessment precedes a deterministic reordered vector."""
        record['reordered_blocks'] = None
        record['capacity_indices'] = []
        baseline = self.block_capacity(v, entry, (), block_index='baseline')
        record['baseline_capacity_index'] = len(self.info['capacity_assessment_records'])-1
        required = set(self.source[v]) & entry.keys()
        bottlenecks = set(baseline['violated_owners']) & required
        rows = {row['owner']: row for row in baseline['rows']}
        protectors = set()
        for u in bottlenecks:
            for q in rows[u]['boundary']:
                self.scan()
                for w in baseline['protected_sites'].get(q, ()):
                    self.scan()
                    if w != u:
                        protectors.add(w)
        pool = record['pool']; positions = {u:i for i,u in enumerate(pool)}
        record.update(bottleneck_required=sorted(bottlenecks), protecting_owners=sorted(protectors),
                      omitted_bottlenecks=sorted(bottlenecks-set(pool)),
                      omitted_protectors=sorted(protectors-set(pool)))
        survivors = []
        for index, selected in enumerate(blocks):
            self.check()
            assessment = self.block_capacity(v, entry, selected, block_index=index)
            record['capacity_indices'].append(len(self.info['capacity_assessment_records'])-1)
            members = set(selected)
            tier = 0 if members & bottlenecks else 1 if members & protectors else 2
            key = (tier, -len(members & bottlenecks), sum(len(entry[u]) for u in selected),
                   len(selected), tuple(sorted(positions[u] for u in selected)))
            assessment['priority'] = key
            if assessment['admissible']:
                survivors.append((key, index, selected))
        self.check()
        survivors.sort()
        self.check()
        record['reordered_blocks'] = [dict(original_index=index, selected=list(selected), priority=key)
                                      for key,index,selected in survivors]
        self.check()
        return [(index, selected) for _,index,selected in survivors]

    def component_obstruction(self, v, frozen):
        """Exact necessary first-v obstruction; partial classification is unknown."""
        self.info.setdefault('component_filter_units', 0)
        self.info.setdefault('component_filter_records', [])
        started, began = self.scans, time.perf_counter()
        record = dict(vertex=v, status='started', obstructed=None, components=[])
        try:
            self.check()
            owners, _, bounds, free = self.state(frozen)
            protected, forbidden = {}, 0
            for u in frozen:
                self.scan()
                mask = bounds[u] & free
                if not mask or mask & (mask-1):
                    continue
                pending = []
                for w in self.source[u]:
                    self.scan()
                    if w not in frozen and w != v:
                        pending.append(w)
                if pending:
                    q = self.qsites[mask.bit_length()-1]
                    protected.setdefault(q, []).append(dict(owner=u, pending=pending))
                    forbidden |= mask
            allowed = free & ~forbidden
            required = set()
            for u in self.source[v]:
                self.scan()
                if u in frozen:
                    required.add(u)
            record.update(protected=protected, required=sorted(required))
            if not required:
                self.check()
                record.update(status='complete', obstructed=not bool(allowed),
                              reason='zero_required')
                return record['obstructed']
            contact_masks = {}
            for u in required:
                self.scan()
                contact_masks[u] = bounds[u] & allowed
            anchor = min(required, key=lambda u: (contact_masks[u].bit_count(), self.vrank[u]))
            seeds = sorted(self.sites(contact_masks[anchor]), key=self.qrank.__getitem__)
            record.update(anchor=anchor, seed_sites=seeds)
            seen = set()
            for root in seeds:
                self.scan()
                if root in seen:
                    continue
                component = dict(root=root, members=[], touches=[], exhausted=False)
                record['components'].append(component)
                touches = set()
                queue = deque([root]); seen.add(root)
                while queue:
                    self.scan()
                    q = queue.popleft(); component['members'].append(q)
                    for p in self.target[q]:
                        self.scan()
                        owner = owners.get(p)
                        if owner in required:
                            touches.add(owner)
                            component['touches'] = sorted(touches)
                            if touches == required:
                                self.check()
                                record.update(status='complete', obstructed=False,
                                              reason='connected_contact_witness')
                                return False
                        if self.bit[p] & allowed and p not in seen:
                            seen.add(p); queue.append(p)
                component['exhausted'] = True
            self.check()
            record.update(status='complete', obstructed=True,
                          reason='no_covering_component')
            return True
        except _RepairLimit:
            record['status'] = 'repair_limit'
            raise
        except _Stop:
            record['status'] = self.info.get('stopped_by') or 'interrupted'
            raise
        finally:
            record.update(units=self.scans-started, wall=time.perf_counter()-began)
            self.info['component_filter_units'] += record['units']
            self.info['component_filter_records'].append(record)

    def repair(self, v, entry, promoted):
        """Blocked-only first complete reconstruction; no recursive repair."""
        self.completed_singleton_domains = None
        self.info.setdefault('repair_records', [])
        self.info.setdefault('repair_units', 0)
        self.info.setdefault('repair_queries', 0)
        self.info.setdefault('repair_skipped_budget', 0)
        remaining = REPAIR_TOTAL-self.info['repair_units']
        if remaining <= 0:
            self.info['repair_skipped_budget'] += 1
            return None, None
        started, began = self.scans, time.perf_counter()
        self.repair_end = started+min(REPAIR_QUERY, remaining)
        record = dict(vertex=v, status='started', units=0, blocks=[],
                      accepted=False, selected=[], qubits=None, growth_indices=[])
        self.info['repair_queries'] += 1
        active = None
        try:
            self.check()
            blocks = self.repair_pool(v, entry, record)
            ordered = self.capacity_order(v, entry, blocks, record)
            for priority_index, (index, selected) in enumerate(ordered):
                self.check()
                active = dict(index=index, selected=list(selected), order=[],
                              priority_index=priority_index, status='started', units=0, growth_indices=[])
                record['blocks'].append(active)
                block_start = self.scans
                try:
                    movable = set(selected) | {v}
                    frozen = set(entry)-movable
                    trial = self.copy_chains(entry, set(selected))
                    active['component_filter_index'] = len(self.info.get('component_filter_records', []))
                    if self.component_obstruction(v, trial):
                        active['status'] = 'component_obstructed'
                        continue
                    todo, u = set(selected), v
                    local_promoted = set(promoted) | set(selected)
                    while True:
                        self.completed_singleton_domains = None
                        active['order'].append(u)
                        base = self.insert(u, trial, frozen)
                        if base is None:
                            active['status'] = 'reconstruction_blocked'
                            break
                        trial, growth = self.future_growth(u, base, local_promoted)
                        if growth is not None:
                            growth_index = len(self.info['growth_records'])-1
                            active['growth_indices'].append(growth_index)
                            growth.update(repair_query=self.info['repair_queries']-1,
                                          repair_block=index, repair_committed=False,
                                          proposed_extra_sites=sorted(trial[u]-base[u]))
                        if not todo:
                            break
                        def rank(w):
                            hits = 0
                            for z in self.source[w]:
                                self.scan()
                                hits += z in trial
                            return (-hits, -len(self.source[w]), self.vrank[w])
                        u = min(todo, key=rank)
                        todo.remove(u)
                    if active['status'] != 'started':
                        continue
                    if set(trial) != set(entry) | {v} or any(trial[w] != entry[w] for w in frozen):
                        raise RuntimeError('repair coverage or frozen ownership changed')
                    if not self.valid(trial, complete=False):
                        raise RuntimeError('invalid repaired partial minor')
                    _, _, tb, tf = self.state(trial)
                    if not self.frontier_ok(trial, tb, tf):
                        raise RuntimeError('repair lost future frontier')
                    self.check()
                    active.update(status='complete', qubits=sum(map(len, trial.values())),
                                  frozen_equal=True, certificate=True)
                    record.update(status='complete', selected=list(selected),
                                  qubits=active['qubits'], growth_indices=active['growth_indices'])
                    return trial, record
                except _RepairLimit:
                    active['status'] = 'repair_limit'
                    raise
                except _Stop:
                    active['status'] = self.info.get('stopped_by') or 'interrupted'
                    raise
                except Exception as error:
                    active.update(status='error', error=repr(error))
                    raise
                finally:
                    active['units'] = self.scans-block_start
            record['status'] = ('all_blocks_failed' if ordered else
                                'all_blocks_capacity_rejected' if blocks else 'empty_pool')
            return None, record
        except _RepairLimit:
            record['status'] = 'local_work_limit'
            return None, record
        except _Stop:
            record['status'] = self.info.get('stopped_by') or 'interrupted'
            raise
        except Exception as error:
            record.update(status='error', error=repr(error))
            raise
        finally:
            self.completed_singleton_domains = None
            self.repair_end = None
            record.update(units=self.scans-started, wall=time.perf_counter()-began)
            self.info['repair_units'] += record['units']
            self.info['repair_records'].append(record)



def frontier_embed(source_graph, target_graph, *, timeout=60.0, deadline=None, seed=0):
    started = time.perf_counter()
    if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('finite positive timeout and integer seed required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite deadline required')
    deadline = min(started+timeout, deadline) if deadline is not None else started+timeout
    info = dict(algorithm='capacity_prioritized_reconstruction_trees', version=17, seed=seed,
                insertion_queries=0, root_branches=0, path_queries=0,
                propagation_units=0, propagation_records=[], neighborhood_unions=0,
                domain_build_calls=0, domain_reuse_hits=0, domain_reuse_records=[],
                growth_queries=0, growth_units=0, growth_records=[], growth_skipped_budget=0,
                growth_accepted=0, growth_query_limit=GROWTH_QUERY, growth_total_limit=GROWTH_TOTAL,
                matching_units=0, matching_records=[], matching_query_limit=MATCHING_QUERY,
                matching_total_limit=MATCHING_TOTAL, singleton_feasibility_rejections=[],
                port_filter_units=0, port_filter_records=[], port_owner_checks=0, port_source_checks=0,
                repair_units=0, repair_records=[], repair_queries=0, repair_accepted=0,
                component_filter_units=0, component_filter_records=[],
                capacity_assessment_units=0, capacity_assessment_records=[],
                repair_skipped_budget=0, repair_query_limit=REPAIR_QUERY, repair_total_limit=REPAIR_TOTAL,
                domain_source_entries=0, value_support_tests=0, singleton_trials=0,
                rejected_empty_domains=0, promotions=[],
                work_unit_definition='adjacency/domain edge, domain union, queue or matching update, port-owner/obligation check, value support test, or repair owner/site copy or selection check',
                propagation_call_limit=PROPAGATION_CALL, propagation_total_limit=PROPAGATION_TOTAL,
                preparation_failures=0, frontier_rejections=0,
                staged_extension_sites=0, staged_pruned_sites=0,
                construction_order=[], committed_updates=[], stage='setup',
                stopped_by=None, error=None, scan_count=0, work_limit=SCANS,
                root_limit=ROOTS, branch_limit=BRANCHES, valid=False)
    engine, chains, valid = None, {}, False
    try:
        engine = _Builder(source_graph, target_graph, deadline, seed, info)
        if len(engine.source) > len(engine.target):
            info['stopped_by'] = 'insufficient_sites'
        else:
            info['stage'] = 'construction'
            pending = set(engine.source)
            pending_domains = None
            promoted = {u for u in pending if len(engine.source[u]) > engine.delta}
            info['promotions'] = [dict(vertex=u, reason='degree_bound') for u in sorted(promoted)]
            while pending:
                engine.check()
                if pending_domains is None:
                    domains = engine.singleton_domains(chains, promoted)
                else:
                    domains, origin = pending_domains
                    info['domain_reuse_hits'] += 1
                    info['domain_reuse_records'].append(origin)
                pending_domains = None
                was_singleton = False
                growth_record = None
                repair_record = None
                empty = [u for u, mask in domains.items() if not mask]
                if empty:
                    v = max(empty, key=lambda u: (len(engine.source[u]), -engine.vrank[u]))
                    promoted.add(v); info['promotions'].append(dict(vertex=v, reason='empty_domain'))
                    continue
                if promoted & pending:
                    engine.completed_singleton_domains = None
                    v = max(promoted & pending, key=lambda u: (sum(w in chains for w in engine.source[u]),
                                                               len(engine.source[u]), -engine.vrank[u]))
                    trial = engine.insert(v, chains)
                    if trial is None:
                        trial, repair_record = engine.repair(v, chains, promoted)
                        if trial is None:
                            info['stopped_by'] = 'construction_blocked'
                            break
                    else:
                        trial, growth_record = engine.future_growth(v, trial, promoted)
                else:
                    was_singleton = True
                    v = min(domains, key=lambda u: (domains[u].bit_count(),
                            -sum(w in chains for w in engine.source[u]), -len(engine.source[u]), engine.vrank[u]))
                    trial = engine.singleton(v, chains, promoted, domains)
                    if trial is None:
                        promoted.add(v); info['promotions'].append(dict(vertex=v, reason='value_trials'))
                        continue
                engine.check()
                if repair_record is not None:
                    repair_record['accepted'] = True
                    info['repair_accepted'] += 1
                    for i in repair_record['growth_indices']:
                        g = info['growth_records'][i]
                        extra = set(g['proposed_extra_sites'])
                        retained = extra & trial[g['vertex']]
                        g.update(repair_committed=True, base_insertion_committed=True,
                                 retained_extra_sites=sorted(retained),
                                 extra_q_committed=bool(extra) and retained == extra)
                        if g['extra_q_committed']:
                            info['growth_accepted'] += 1
                if growth_record is not None:
                    growth_record['base_insertion_committed'] = True
                    if growth_record['status'] == 'resolved':
                        growth_record['extra_q_committed'] = True
                        info['growth_accepted'] += 1
                info['committed_updates'].append(dict(vertex=v,
                    qubits_added=sum(map(len, trial.values()))-sum(map(len, chains.values())),
                    changed_existing=sum(w in chains and c != chains[w] for w, c in trial.items())))
                chains = trial
                pending.remove(v)
                info['construction_order'].append(v)
                if pending and was_singleton:
                    pending_domains = engine.completed_singleton_domains
            if not pending:
                info['stage'] = 'final_validation'
                valid = engine.valid(chains, complete=True)
                if not valid:
                    raise RuntimeError('invalid completed minor')
                info['stopped_by'] = 'completed'
    except _Stop:
        pass
    except (ValueError, TypeError) as error:
        info.update(stopped_by='invalid_input', error=str(error))
    except Exception as error:
        info.update(stopped_by='internal_error', error=repr(error))
    if engine is not None:
        info['scan_count'] = engine.scans
    materialized = {v: sorted(c) for v, c in chains.items()}
    info.update(valid=valid, complete=valid, qubits=sum(map(len, materialized.values())))
    ended = time.perf_counter()
    info.update(wall=ended-started, deadline=deadline, deadline_overrun=max(0., ended-deadline))
    status = ('TIMEOUT' if ended >= deadline else 'SUCCESS' if valid else
              'INVALID_INPUT' if info['stopped_by'] == 'invalid_input' else 'FAILURE')
    info['partial_embedding'] = materialized if status != 'SUCCESS' else None
    return dict(embedding=materialized if status == 'SUCCESS' else {}, status=status, diag=info)
