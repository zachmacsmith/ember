"""Exploratory joint connected-chain insertion with extension-frontier protection.

Standalone standard-library constructor, specified in b_bounded_cost.md.
This module copies only basic graph/budget/validity helpers from rejected B001;
it neither imports nor calls its constructor or rooted-union proposal.
"""
import heapq
import math
import random
import time

ROOTS = 64
BRANCHES = 4
SCANS = 20_000_000

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


def frontier_embed(source_graph, target_graph, *, timeout=60.0, deadline=None, seed=0):
    started = time.perf_counter()
    if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('finite positive timeout and integer seed required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite deadline required')
    deadline = min(started+timeout, deadline) if deadline is not None else started+timeout
    info = dict(algorithm='bounded_joint_frontier_trees', version=3, seed=seed,
                insertion_queries=0, root_branches=0, path_queries=0,
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
            while pending:
                engine.check()
                v = max(pending, key=lambda u: (sum(w in chains for w in engine.source[u]),
                                                len(engine.source[u]), -engine.vrank[u]))
                trial = engine.insert(v, chains)
                if trial is None:
                    info['stopped_by'] = 'construction_blocked'
                    break
                engine.check()
                info['committed_updates'].append(dict(vertex=v,
                    qubits_added=sum(map(len, trial.values()))-sum(map(len, chains.values())),
                    changed_existing=sum(w in chains and c != chains[w] for w, c in trial.items())))
                chains = trial
                pending.remove(v)
                info['construction_order'].append(v)
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
