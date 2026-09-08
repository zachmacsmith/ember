"""Exploratory joint connected-chain insertion with extension-frontier protection.

Standalone standard-library constructor, specified in b_future_domain_growth.md.
This module copies only basic graph/budget/validity helpers from rejected B001;
it neither imports nor calls its constructor or rooted-union proposal.
"""
from collections import deque
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
GROWTH_STEPS = 4
GROWTH_SITES = 4
GROWTH_QUERY = 500_000
GROWTH_TOTAL = 3_000_000

class _GrowthLimit(Exception):
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

    def prepare(self, v, entry):
        """Stage urgent old-chain growth; published entry is never changed."""
        trial = {w: set(c) for w, c in entry.items()}
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
                if not mask:
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

    def path(self, v, chains, missing):
        owners, _, bounds, free = self.state(chains)
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
                if p in owners:
                    continue
                nd = d + price(p)
                if nd < dist.get(p, math.inf):
                    dist[p], parent[p] = nd, q
                    heapq.heappush(heap, (nd, self.qrank[p], p))
        return None

    def cut(self, v, w, path, chains, required):
        """Choose one connected ownership cut; every candidate has identical Q."""
        best, best_key = None, None
        for cut in range(len(path), -1, -1):
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

    def insert(self, v, entry):
        self.info['insertion_queries'] += 1
        prepared = self.prepare(v, entry)
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
            trial = {w: set(c) for w, c in prepared.items()}
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
                trial = self.cut(v, w, path, trial, required)
                if trial is None:
                    self.info['frontier_rejections'] += 1
                    break
            if trial is None:
                continue
            changed = {w for w in trial if w not in entry or trial[w] != entry[w]}
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
        if getattr(self, 'growth_end', None) is not None and self.scans >= self.growth_end:
            raise _GrowthLimit
        super().scan()

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
                record['status'] = ('already_consistent' if self.last_domain_result[1]
                                    else 'unresolved_propagation_limit')
                return base, record
            record['initial_empty'] = sum(not mask for mask in actual.values())
            current = {u: set(c) for u, c in base.items()}
            for step in range(GROWTH_STEPS):
                self.check()
                relaxed = self.singleton_domains(current, promoted, omit_contact=v)
                if any(not mask for mask in relaxed.values()):
                    record['status'] = 'relaxed_empty'
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
                best, best_key = None, None
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
                    if self.last_domain_result[1] and all(counts):
                        # Local certificate: connected free growth preserves base's
                        # contacts, ownership and every frozen chain exactly.
                        if not base[v] <= trial[v] or any(trial[u] != base[u] for u in base if u != v):
                            raise RuntimeError('growth changed frozen chains')
                        self.check()
                        record.update(status='resolved', steps=step+1,
                                      extra_sites=len(trial[v])-len(base[v]))
                        return trial, record
                    key = (sum(n == 0 for n in counts), tuple(-n for n in sorted(counts)), self.qrank[q])
                    if best_key is None or key < best_key:
                        best, best_key = trial, key
                if best is None:
                    record['status'] = 'blocked_frontier'
                    return base, record
                current = best
                record['steps'] = step+1
            record['status'] = 'neighborhood_limit'
            return base, record
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



def frontier_embed(source_graph, target_graph, *, timeout=60.0, deadline=None, seed=0):
    started = time.perf_counter()
    if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('finite positive timeout and integer seed required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite deadline required')
    deadline = min(started+timeout, deadline) if deadline is not None else started+timeout
    info = dict(algorithm='future_domain_growth_trees', version=7, seed=seed,
                insertion_queries=0, root_branches=0, path_queries=0,
                propagation_units=0, propagation_records=[], neighborhood_unions=0,
                domain_build_calls=0, domain_reuse_hits=0, domain_reuse_records=[],
                growth_queries=0, growth_units=0, growth_records=[], growth_skipped_budget=0,
                growth_accepted=0, growth_query_limit=GROWTH_QUERY, growth_total_limit=GROWTH_TOTAL,
                domain_source_entries=0, value_support_tests=0, singleton_trials=0,
                rejected_empty_domains=0, promotions=[],
                work_unit_definition='adjacency entry, domain union, arc administration or value support test',
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
                        info['stopped_by'] = 'construction_blocked'
                        break
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
