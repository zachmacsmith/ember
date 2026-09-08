"""Experimental direct connected-tree construction; standard library only.

One partial minor is grown using physical contact demands and free boundary
capacity. No external embedder, geometric converter or cached start is used.
The finite search is deliberately incomplete; see tracks/b_construction.md.
"""
import heapq
import math
import random
import time


ROOTS = 64
UNIONS = 8
SCANS = 20_000_000
SWEEPS = 2


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
            raise _Stop

    def scan(self):
        if self.scans >= SCANS:
            self.info['stopped_by'] = 'work_limit'
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

    def prepare(self, chains):
        owners = self.occupied(chains)
        free = set(self.target).difference(owners)
        bounds, pressure, remaining = {}, {}, {}
        for w, chain in chains.items():
            self.check()
            bounds[w] = self.boundary(chain, free)
            remaining[w] = sum(u not in chains for u in self.source[w])
            price = remaining[w] / max(1, len(bounds[w]))
            if price:
                for q in bounds[w]:
                    pressure[q] = pressure.get(q, 0.) + price
        return owners, free, bounds, pressure, remaining

    def distances(self, terminal, free, roots, cost):
        """Reverse multi-source vertex-weighted paths, stopped at all roots."""
        dist, parent, heap = {}, {}, []
        for q in sorted(terminal, key=self.qrank.__getitem__):
            dist[q], parent[q] = cost(q), None
            heap.append((dist[q], self.qrank[q], q))
        heapq.heapify(heap)
        left = set(roots)
        while heap and left:
            self.check()
            d, _, q = heapq.heappop(heap)
            if d != dist[q]:
                continue
            left.discard(q)
            if not left:
                break
            for p in self.target[q]:
                self.scan()
                if p not in free:
                    continue
                nd = d + cost(p)
                if nd < dist.get(p, math.inf):
                    dist[p], parent[p] = nd, q
                    heapq.heappush(heap, (nd, self.qrank[p], p))
        return dist, parent

    def prune(self, tree, required, bounds, future, free):
        """Delete tree leaves only, preserving contacts and required free ports."""
        tree = set(tree)
        while len(tree) > 1:
            removed = False
            for q in sorted(tree, key=self.qrank.__getitem__, reverse=True):
                self.check()
                degree = 0
                for p in self.target[q]:
                    self.scan()
                    degree += p in tree
                if degree > 1:
                    continue
                if any(q in bounds[w] and len(tree & bounds[w]) == 1 for w in required):
                    continue
                candidate = tree - {q}
                if future and len(self.boundary(candidate, free-candidate)) < future:
                    continue
                tree = candidate
                removed = True
            if not removed:
                break
        return tree

    def reserve(self, tree, future, free, cost):
        """Open enough distinct free sites for still unplaced logical neighbors."""
        tree = set(tree)
        boundary = self.boundary(tree, free-tree)
        while len(boundary) < future:
            self.check()
            if not boundary:
                return None
            choices = []
            for q in boundary:
                new = set()
                for p in self.target[q]:
                    self.scan()
                    if p in free and p not in tree and p not in boundary:
                        new.add(p)
                choices.append((-len(new), cost(q), self.qrank[q], q, new))
            _, _, _, q, new = min(choices, key=lambda x: x[:3])
            tree.add(q)
            boundary.remove(q)
            boundary.update(new)
        return tree

    def propose(self, v, chains):
        self.info['tree_queries'] += 1
        self.check()
        _, free, bounds, pressure, remaining = self.prepare(chains)
        if not free:
            return None
        required = sorted((w for w in self.source[v] if w in chains),
                          key=lambda w: (len(bounds[w])/max(1, remaining[w]), self.vrank[w]))
        future = sum(w not in chains for w in self.source[v])
        if any(not bounds[w] for w in required):
            self.info['blocked_contact_queries'] += 1
            return None
        cost = lambda q: 1. + pressure.get(q, 0.)
        root_pool = bounds[required[0]] if required else free
        def root_key(q):
            usable = 0
            for p in self.target[q]:
                self.scan()
                usable += p in free
            return (cost(q), -usable, self.qrank[q])
        roots = sorted(root_pool, key=root_key)[:ROOTS]
        paths = [self.distances(bounds[w], free, roots, cost) for w in required]
        viable = [q for q in roots if all(q in ds for ds, _ in paths)]
        viable.sort(key=lambda q: (sum(ds[q]-cost(q) for ds, _ in paths)+cost(q),
                                   self.qrank[q]))
        best, best_key = None, None
        for root in viable[:UNIONS]:
            self.check()
            tree = {root}
            for _, parent in paths:
                q = root
                while q is not None:
                    self.check()
                    tree.add(q)
                    q = parent[q]
            tree = self.prune(tree, required, bounds, 0, free)
            tree = self.reserve(tree, future, free, cost)
            if tree is None:
                continue
            tree = self.prune(tree, required, bounds, future, free)
            key = (len(tree), sum(cost(q) for q in tree),
                   -len(self.boundary(tree, free-tree)), self.qrank[root])
            if best_key is None or key < best_key:
                best, best_key = tree, key
        self.check()
        return best

    def displacement(self, v, chains):
        """One complete private release/rebuild transaction; never mutate entry."""
        self.info['displacement_attempts'] += 1
        owners, free, bounds, _, _ = self.prepare(chains)
        scores = {}
        for w in self.source[v]:
            if w not in chains:
                continue
            severity = 1. / (1+len(bounds[w]))
            for q in chains[w]:
                for p in self.target[q]:
                    self.scan()
                    blocker = owners.get(p)
                    if blocker is not None and blocker != w:
                        scores[blocker] = scores.get(blocker, 0.) + severity
        chosen = sorted(scores, key=lambda w: (-scores[w]/len(chains[w]),
                                               len(chains[w]), self.vrank[w]))[:2]
        if not chosen:
            return None
        trial = {w: c for w, c in chains.items() if w not in chosen}
        pending = set(chosen) | {v}
        first = True
        while pending:
            w = v if first else max(pending, key=lambda u: (
                sum(z in trial for z in self.source[u]), len(self.source[u]), -self.vrank[u]))
            first = False
            tree = self.propose(w, trial)
            if tree is None:
                return None
            trial[w] = tree
            pending.remove(w)
        if not self.valid(trial, complete=False):
            raise RuntimeError('invalid private displacement transaction')
        self.check()
        self.info['displacement_commits'] += 1
        return trial

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


def demand_embed(source_graph, target_graph, *, timeout=60.0, deadline=None, seed=0):
    """Return a direct connected-tree embedding or an explicit bounded failure."""
    started = time.perf_counter()
    if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('finite positive timeout and integer seed required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite deadline required')
    deadline = min(started+timeout, deadline) if deadline is not None else started+timeout
    info = dict(algorithm='demand_connected_trees', version=1, seed=seed,
                tree_queries=0, blocked_contact_queries=0, displacement_attempts=0,
                displacement_commits=0, refinement_commits=0, refinement_sweeps=0,
                construction_order=[], stage='setup', stopped_by=None, error=None,
                work_limit=SCANS, root_limit=ROOTS, union_limit=UNIONS,
                scan_count=0, complete=False, valid=False, trajectory=[])
    engine, chains, valid_incumbent = None, {}, False
    try:
        engine = _Engine(source_graph, target_graph, deadline, seed, info)
        if len(engine.source) > len(engine.target):
            info['stopped_by'] = 'insufficient_sites'
        else:
            info['stage'] = 'construction'
            pending = set(engine.source)
            while pending:
                engine.check()
                v = max(pending, key=lambda u: (sum(w in chains for w in engine.source[u]),
                                                len(engine.source[u]), -engine.vrank[u]))
                tree = engine.propose(v, chains)
                if tree is None:
                    trial = engine.displacement(v, chains)
                    if trial is None:
                        info['stopped_by'] = 'construction_blocked'
                        break
                    chains = trial
                else:
                    chains[v] = tree
                pending.remove(v)
                info['construction_order'].append(v)
            if not pending:
                info['stage'] = 'construction_validation'
                valid_incumbent = engine.valid(chains, complete=True)
                if not valid_incumbent:
                    raise RuntimeError('constructed invalid minor')
                info['construction_qubits'] = sum(map(len, chains.values()))
                info['stage'] = 'refinement'
                for sweep in range(SWEEPS):
                    commits = 0
                    for v in sorted(chains, key=lambda u: (-len(chains[u]), engine.vrank[u])):
                        engine.check()
                        if len(chains[v]) == 1:
                            continue
                        fixed = {w: c for w, c in chains.items() if w != v}
                        tree = engine.propose(v, fixed)
                        if tree is not None and len(tree) < len(chains[v]):
                            saved = len(chains[v])-len(tree)
                            engine.check()
                            chains[v] = tree
                            commits += 1
                            info['refinement_commits'] += 1
                            info['trajectory'].append(dict(sweep=sweep, vertex=v, qubits_saved=saved))
                    info['refinement_sweeps'] += 1
                    if not commits:
                        break
                info['stopped_by'] = 'completed'
    except _Stop:
        pass
    except (ValueError, TypeError) as error:
        info.update(stopped_by='invalid_input', error=str(error))
    except Exception as error:
        info.update(stopped_by='internal_error', error=repr(error))
    if engine is not None:
        info['scan_count'] = engine.scans
    # Every commit preserves the partial minor by construction. A completed
    # incumbent remains valid if an unfinished refinement proposal is discarded.
    info['complete'] = valid_incumbent
    info['valid'] = valid_incumbent
    materialized = {v: sorted(c) for v, c in chains.items()}
    info['partial_embedding'] = materialized if not valid_incumbent else None
    info['qubits'] = sum(map(len, materialized.values()))
    ended = time.perf_counter()
    info.update(wall=ended-started, deadline=deadline,
                deadline_overrun=max(0., ended-deadline))
    if ended >= deadline:
        status = 'TIMEOUT'
    elif info['stopped_by'] in ('invalid_input', 'internal_error'):
        status = 'INVALID_INPUT' if info['stopped_by'] == 'invalid_input' else 'FAILURE'
    else:
        status = 'SUCCESS' if valid_incumbent else 'FAILURE'
    if status != 'SUCCESS':
        info['partial_embedding'] = materialized
    return dict(embedding=materialized if status == 'SUCCESS' else {}, status=status, diag=info)
