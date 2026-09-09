"""C012: one monotone Zephyr frontier, original-contact births and proper suffixes.

Experimental restrictions: fixed sweep/window/roots, greedy paths, no whole-tree
rip-up, no backward sweep. Work counters are diagnostic; the absolute clock binds.
"""
from collections import Counter, deque
from contextlib import contextmanager
import math
import random
import time


class _Deadline(Exception):
    pass


class _InputError(ValueError):
    pass


class _Budget:
    def __init__(self, deadline, clock=None):
        self.deadline = deadline
        self.clock = clock or time.perf_counter
        self.work = Counter()
        self.stage_wall = Counter()
        self.stage_cpu = Counter()
        self.active = 'input'

    def check(self):
        if self.clock() >= self.deadline:
            raise _Deadline(self.active)

    def tick(self, name, count=1):
        self.check()
        self.work[name] += count

    @contextmanager
    def stage(self, name):
        old = self.active
        self.active = name
        wall, cpu = self.clock(), time.process_time()
        try:
            self.check()
            yield
        finally:
            self.stage_wall[name] += self.clock()-wall
            self.stage_cpu[name] += time.process_time()-cpu
            self.active = old

    @contextmanager
    def event(self, ledger, row):
        row.update(status='started', work_before=sum(self.work.values()))
        ledger.append(row)
        wall, cpu = self.clock(), time.process_time()
        try:
            yield row
        except _Deadline:
            row['status'] = 'interrupted'
            raise
        except Exception as exc:
            row.update(status='error', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            row.update(wall=self.clock()-wall, cpu=time.process_time()-cpu,
                       work_after=sum(self.work.values()))


def _edge_kind(a, b):
    if a[0] == b[0]:
        if a[:4] == b[:4] and abs(a[4]-b[4]) == 1:
            return 'external'
        if a[:3] == b[:3] and a[3] != b[3]:
            zero, one = (a, b) if a[3] == 0 else (b, a)
            if zero[4]-one[4] in (0, 1):
                return 'odd'
        return None
    v, h = (a, b) if a[0] == 0 else (b, a)
    if (v[1] in (2*h[4]+1, 2*h[4]+1+(2*h[3]-1)) and
            h[1] in (2*v[4]+1, 2*v[4]+1+(2*v[3]-1))):
        return 'cross_orientation'
    return None


def _graph(graph, budget):
    if graph.is_directed() or graph.is_multigraph():
        raise _InputError('simple undirected graphs required')
    labels = list(graph.nodes)
    inverse = {v: i for i, v in enumerate(labels)}
    adjacency = [set() for _ in labels]
    budget.tick('input_nodes', len(labels))
    for a, b in graph.edges:
        budget.tick('input_edges')
        if a == b:
            raise _InputError('self loop')
        u, v = inverse[a], inverse[b]
        adjacency[u].add(v)
        adjacency[v].add(u)
    return labels, adjacency


def _geometry(graph, labels, adjacency, budget):
    meta = graph.graph
    m, t = meta.get('rows'), meta.get('tile')
    if meta.get('family') != 'zephyr' or type(m) is not int or type(t) is not int or min(m, t) < 1:
        raise _InputError('verified Zephyr metadata required')
    result = []
    for q in labels:
        budget.tick('coordinate_sites')
        if meta.get('labels', 'int') == 'coordinate':
            value = q
        else:
            if type(q) is not int or not 0 <= q < 4*t*m*(2*m+1):
                raise _InputError('invalid Zephyr integer label')
            r, z = divmod(q, m)
            r, j = divmod(r, 2)
            r, k = divmod(r, t)
            u, w = divmod(r, 2*m+1)
            value = (u, w, k, j, z)
        if (not isinstance(value, (tuple, list)) or len(value) != 5 or
                any(type(x) is not int for x in value)):
            raise _InputError('invalid Zephyr coordinate')
        u, w, k, j, z = value
        if not (u in (0, 1) and 0 <= w <= 2*m and 0 <= k < t and j in (0, 1) and 0 <= z < m):
            raise _InputError('Zephyr coordinate outside bounds')
        saved = graph.nodes[q].get('zephyr_index')
        if saved is not None and tuple(saved) != tuple(value):
            raise _InputError('coordinate metadata disagrees with label')
        result.append(tuple(value))
    if len(set(result)) != len(result):
        raise _InputError('duplicate coordinates')
    for q, ns in enumerate(adjacency):
        for p in ns:
            budget.tick('coordinate_couplers')
            if not _edge_kind(result[q], result[p]):
                raise _InputError('actual coupler incompatible with Zephyr coordinates')
    return m, result


class _State:
    def __init__(self, source, target, coords, m, seed, budget):
        self.source, self.target, self.coords, self.m = source, target, coords, m
        self.b = budget
        rng = random.Random(seed)
        self.sweep = rng.randrange(4)
        axis, reflected = divmod(self.sweep, 2)
        self.strip = []
        for u, w, k, j, z in coords:
            s = w if u == axis else 2*z+j
            self.strip.append(2*m-s if reflected else s)
        ss, tt = list(range(len(source))), list(range(len(target)))
        rng.shuffle(ss)
        rng.shuffle(tt)
        self.srank = {u: i for i, u in enumerate(ss)}
        self.trank = {q: i for i, q in enumerate(tt)}
        self.ordered_adj = []
        for q, ns in enumerate(target):
            self.ordered_adj.append(sorted(ns, key=self.trank.__getitem__))
            budget.tick('target_adjacency_order', len(ns))
            if any(abs(self.strip[q]-self.strip[p]) > 2 for p in ns):
                raise _InputError('actual coupler exceeds strip bound')
        self.windows = {}
        for c in range(2*m+1):
            for carrying in (False, True):
                hi = min(c+(3 if carrying else 2), 2*m)
                budget.tick('window_index_sites', len(target))
                self.windows[c, carrying] = frozenset(q for q, pos in enumerate(self.strip) if c <= pos <= hi)
        self.I, self.chains, self.trees, self.roots = set(), {}, {}, {}
        self.owner = [-1]*len(target)
        self.contacts = Counter()
        self.cut, self.generation = 0, 0

    def ordered(self, values):
        self.b.tick('ordered_records', len(values))
        out = sorted(values, key=self.trank.__getitem__)
        self.b.check()
        return out

    def window(self, cut=None, carry=False):
        c = self.cut if cut is None else cut
        self.b.tick('window_lookups')
        return self.windows.get((c, carry), frozenset())

    def fork(self):
        other = object.__new__(_State)
        other.__dict__ = self.__dict__.copy()
        other.I = self.I.copy()
        other.chains = {u: c.copy() for u, c in self.chains.items()}
        other.trees = {u: e.copy() for u, e in self.trees.items()}
        other.roots = self.roots.copy()
        other.owner = self.owner.copy()
        other.contacts = self.contacts.copy()
        self.b.tick('private_copy_records', len(self.owner)+len(self.contacts)+
                    sum(len(c)+len(self.trees[u])+2 for u, c in self.chains.items()))
        return other

    def publish(self, other):
        self.b.check()
        self.I, self.chains, self.trees, self.roots = other.I, other.chains, other.trees, other.roots
        self.owner, self.contacts, self.cut = other.owner, other.contacts, other.cut
        self.generation += 1

    def live(self, u):
        return bool(self.source[u]-self.I)

    def port(self, u, cut=None, added=()):
        free_domain = self.window(cut, carry=True)
        claimed = set(added)
        for q in self.chains[u] | claimed:
            for p in self.ordered_adj[q]:
                self.b.tick('port_edges')
                if p in free_domain and self.owner[p] < 0 and p not in claimed:
                    return True
        return False

    def claim(self, u, path):
        chain = self.chains.setdefault(u, set())
        tree = self.trees.setdefault(u, set())
        parent = None
        for q in path:
            self.b.tick('claim_sites')
            if q in chain:
                parent = q
                continue
            if self.owner[q] >= 0:
                raise RuntimeError('claim overlaps another owner')
            if chain and (parent is None or parent not in chain or q not in self.target[parent]):
                raise RuntimeError('claim path not anchored')
            if not chain:
                self.roots[u] = q
            else:
                tree.add(tuple(sorted((q, parent))))
            for p in self.ordered_adj[q]:
                self.b.tick('claim_contact_edges')
                v = self.owner[p]
                if v in self.source[u]:
                    self.contacts[tuple(sorted((u, v)))] += 1
            chain.add(q)
            self.owner[q], parent = u, q

    def release(self, u, suffix):
        if self.roots[u] in suffix or not self.chains[u]-set(suffix):
            raise RuntimeError('release includes protected root or whole chain')
        for q in suffix:
            self.b.tick('released_sites')
            for p in self.ordered_adj[q]:
                self.b.tick('release_contact_edges')
                v = self.owner[p]
                if v in self.source[u]:
                    key = tuple(sorted((u, v)))
                    self.contacts[key] -= 1
                    if self.contacts[key] == 0:
                        del self.contacts[key]
            self.owner[q] = -1
            self.chains[u].remove(q)
        removed = set(suffix)
        self.trees[u] = {e for e in self.trees[u] if not (set(e) & removed)}

    def connected(self, chain):
        if not chain:
            return False
        seen = {min(chain, key=self.trank.__getitem__)}
        todo = list(seen)
        while todo:
            q = todo.pop()
            for p in self.ordered_adj[q]:
                self.b.tick('connectivity_edges')
                if p in chain and p not in seen:
                    seen.add(p)
                    todo.append(p)
        return seen == chain

    def certify(self, changed):
        for u in sorted(changed, key=self.srank.__getitem__):
            self.b.tick('certificate_owner')
            chain = self.chains[u]
            if not self.connected(chain):
                return 'disconnected_chain'
            if self.roots[u] not in chain or len(self.trees[u]) != len(chain)-1:
                return 'construction_tree'
            for q in chain:
                self.b.tick('certificate_membership')
                if self.owner[q] != u:
                    return 'ownership'
            tree_adj = {q:set() for q in chain}
            for a, b in self.trees[u]:
                self.b.tick('certificate_tree_edge')
                if a not in chain or b not in chain or b not in self.target[a]:
                    return 'construction_tree'
                tree_adj[a].add(b)
                tree_adj[b].add(a)
            seen = {self.roots[u]}
            todo = list(seen)
            while todo:
                q = todo.pop()
                self.b.tick('certificate_tree_visit')
                new = tree_adj[q]-seen
                seen.update(new)
                todo.extend(new)
            if seen != chain:
                return 'construction_tree'
            for v in self.source[u] & self.I:
                self.b.tick('certificate_original_contact')
                if self.contacts[tuple(sorted((u, v)))] < 1:
                    return 'lost_original_contact'
        window = self.window()
        for u in sorted(self.I, key=self.srank.__getitem__):
            if self.live(u):
                if not self.chains[u] & window:
                    return 'lost_frontier'
                if not self.port(u):
                    return 'lost_live_port'
        self.b.check()
        return None

    def paths(self, u, allowed, contact_goals=None):
        """All canonical BFS paths; target ranks fix ties, not an exact router."""
        parents = {q: None for q in self.chains[u]}
        distances = {q: 0 for q in parents}
        todo = deque(self.ordered(parents))
        free_order, stop_distance = [], None
        while todo:
            q = todo.popleft()
            if stop_distance is not None and distances[q] > stop_distance:
                break
            self.b.tick('bfs_sites')
            if self.owner[q] != u:
                free_order.append(q)
                if contact_goals is not None:
                    self.b.tick('bfs_goal_edges', len(self.target[q]))
                    if {self.owner[p] for p in self.target[q]} & contact_goals:
                        stop_distance = distances[q]
            if stop_distance is not None:
                continue
            for p in self.ordered_adj[q]:
                self.b.tick('bfs_edges')
                if p in parents or p not in allowed or self.owner[p] >= 0:
                    continue
                parents[p] = q
                distances[p] = distances[q]+1
                todo.append(p)
        free_order.sort(key=lambda q: (distances[q], self.trank[q]))
        self.b.tick('bfs_order_records', len(free_order))
        return parents, distances, free_order

    @staticmethod
    def path(parents, q):
        result = [q]
        while parents[result[-1]] is not None:
            result.append(parents[result[-1]])
        return list(reversed(result))

    def grow(self, u, required, allowed, receipt):
        while True:
            missing = {v for v in required if self.contacts[tuple(sorted((u, v)))] < 1}
            if not missing:
                return True
            parents, distances, order = self.paths(u, allowed, contact_goals=missing)
            choices = []
            best_distance = None
            for q in order:
                if best_distance is not None and distances[q] > best_distance:
                    break
                touched = {self.owner[p] for p in self.target[q]} & missing
                self.b.tick('goal_contact_edges', len(self.target[q]))
                if touched:
                    best_distance = distances[q]
                    v = min(touched, key=self.srank.__getitem__)
                    choices.append((self.srank[v], self.trank[q], q))
            if not choices:
                return False
            q = min(choices)[2]
            path = self.path(parents, q)
            self.b.tick('path_records', len(path))
            self.claim(u, path)
            receipt.append(dict(owner=u, path=path, added=len(path)-1))


def _roots(state, v, allowed):
    ns = state.source[v] & state.I
    free = {q for q in allowed if state.owner[q] < 0}
    state.b.tick('root_free_sites', len(allowed))
    if ns:
        boundaries = []
        for u in sorted(ns, key=state.srank.__getitem__):
            boundary = set()
            for q in state.chains[u]:
                state.b.tick('pivot_boundary_edges', len(state.target[q]))
                boundary.update(state.target[q] & free)
            boundaries.append((len(boundary), state.srank[u], boundary))
        roots = min(boundaries, key=lambda x: x[:2])[2]
    else:
        roots = free
    carry = state.window(carry=True)
    scored = []
    for q in roots:
        state.b.tick('root_score_edges', len(state.target[q]))
        touches = {state.owner[p] for p in state.target[q]} & ns
        available = sum(state.owner[p] < 0 and p in carry for p in state.target[q])
        scored.append((-len(touches), -available, state.strip[q], state.trank[q], q))
    state.b.tick('root_sort_records', len(scored))
    return [r[-1] for r in sorted(scored)]


def _suffixes(state, v, allowed):
    result = {}
    for u in sorted(state.source[v] & state.I, key=state.srank.__getitem__):
        state.b.tick('suffix_owners')
        if not state.live(u):
            continue
        tree = {q: set() for q in state.chains[u]}
        for a, b in state.trees[u]:
            state.b.tick('suffix_tree_edges')
            tree[a].add(b)
            tree[b].add(a)
        candidates = []
        for leaf in state.ordered(tree):
            if len(tree[leaf]) != 1:
                continue
            suffix, previous, q = [], None, leaf
            while q in allowed and q != state.roots[u] and len(tree[q]) <= 2:
                state.b.tick('suffix_sites')
                suffix.append(q)
                following = tree[q]-{previous}
                if not following:
                    raise RuntimeError('suffix has no protected anchor')
                previous, q = q, next(iter(following))
            if suffix and state.connected(state.chains[u]-set(suffix)):
                candidates.append((-state.strip[leaf], -len(suffix), state.trank[leaf], suffix))
        if candidates:
            result[u] = min(candidates, key=lambda x: x[:3])[-1]
    return result


def _birth(state, v, joint, row):
    allowed = state.window()
    base = state
    suffixes = _suffixes(state, v, allowed) if joint else {}
    row['released'] = suffixes
    if joint:
        if not suffixes:
            row['status'] = 'no_eligible_suffix'
            return None
        base = state.fork()
        for u, suffix in suffixes.items():
            base.release(u, suffix)
    roots = _roots(base, v, allowed)
    row.update(generated_roots=len(roots), roots=[])
    for q in roots:
        state.b.tick('root_attempts')
        trial = dict(root=q, status='started', contact_paths=[], restoration_paths=[])
        row['roots'].append(trial)
        working = base.fork()
        working.I.add(v)
        working.claim(v, [q])
        if not working.grow(v, state.source[v] & state.I, allowed, trial['contact_paths']):
            trial['status'] = 'birth_no_route'
            continue
        restored = True
        for u in sorted(suffixes, key=state.srank.__getitem__):
            if not working.grow(u, state.source[u] & working.I, allowed, trial['restoration_paths']):
                restored = False
                break
        if not restored:
            trial['status'] = 'restoration_no_route'
            continue
        reason = working.certify(set(suffixes) | {v})
        if reason:
            trial['status'] = reason
            continue
        state.b.check()
        trial['status'] = 'certified'
        row.update(status='committed', birth_Q=len(working.chains[v]),
                   released_Q=sum(map(len, suffixes.values())),
                   restoration_Q=sum(r['added'] for r in trial['restoration_paths']),
                   Q_before=sum(map(len, state.chains.values())),
                   Q_after=sum(map(len, working.chains.values())))
        return working
    row['status'] = 'roots_exhausted'
    return None


def _carry(state, row):
    next_cut = state.cut+1
    if next_cut > 2*state.m:
        row['status'] = 'schedule_exhausted'
        return None
    allowed, next_window = state.window(carry=True), state.window(next_cut)
    endangered = []
    for u in sorted(state.I, key=state.srank.__getitem__):
        state.b.tick('carry_owner')
        if state.live(u) and (not state.chains[u] & next_window or not state.port(u, next_cut)):
            parents, distances, order = state.paths(u, allowed)
            goals = [q for q in order if q in next_window]
            endangered.append((len(goals), min((distances[q] for q in goals), default=math.inf), state.srank[u], u))
    endangered.sort()
    row.update(endangered=[dict(owner=u, reachable=count, distance=dist if count else None)
                           for count, dist, rank, u in endangered], paths=[])
    work = state.fork()
    for count, distance, rank, u in endangered:
        if not count:
            row.update(status='no_reachable_carry', failed_owner=u)
            return None
        parents, distances, order = work.paths(u, allowed)
        chosen = None
        for q in order:
            state.b.tick('carry_destinations')
            if q not in next_window:
                continue
            path = work.path(parents, q)
            if work.port(u, next_cut, path[1:]):
                chosen = path
                break
        if chosen is None:
            row.update(status='no_carry_with_port', failed_owner=u)
            return None
        work.claim(u, chosen)
        row['paths'].append(dict(owner=u, path=chosen, added=len(chosen)-1))
    work.cut = next_cut
    reason = work.certify({u for _, _, _, u in endangered})
    if reason:
        row['status'] = reason
        return None
    state.b.check()
    row.update(status='committed', Q_before=sum(map(len, state.chains.values())),
               Q_after=sum(map(len, work.chains.values())), added=sum(p['added'] for p in row['paths']))
    return work


def _run(state, diag):
    while len(state.I) < len(state.source):
        state.b.tick('source_schedule_records', len(state.source))
        order = sorted(set(range(len(state.source)))-state.I,
                       key=lambda u: (-len(state.source[u] & state.I), len(state.source[u]-state.I), state.srank[u]))
        state.b.check()
        published = False
        for v in order:
            for joint in (False, True):
                kind = 'joint_birth' if joint else 'ordinary_birth'
                with state.b.event(diag['events'], dict(kind=kind, source=v, cut=state.cut,
                                                     generation=state.generation)) as row:
                    with state.b.stage(kind):
                        other = _birth(state, v, joint, row)
                    if other is not None:
                        state.publish(other)
                        row['generation_after'] = state.generation
                        published = True
                if published:
                    break
            if published:
                break
        if published:
            continue
        with state.b.event(diag['events'], dict(kind='carry', cut=state.cut,
                                             generation=state.generation)) as row:
            with state.b.stage('carry'):
                other = _carry(state, row)
            if other is None:
                return row['status']
            state.publish(other)
            row['generation_after'] = state.generation
    return 'complete_introduced_source'


def _final(state, source_labels, target_labels, response):
    b = state.b
    result, owners, missing = {}, {}, []
    connected = True
    for u in range(len(state.source)):
        chain = state.chains.get(u, set())
        connected &= state.connected(chain)
        for q in chain:
            b.tick('final_memberships')
            if q in owners or not 0 <= q < len(state.target):
                raise RuntimeError('invalid final ownership')
            owners[q] = u
        b.tick('final_output_records', len(chain)+1)
        result[source_labels[u]] = [target_labels[q] for q in state.ordered(chain)]
    actual = Counter()
    for q, u in owners.items():
        for p in state.target[q]:
            b.tick('final_contact_edges')
            if p in owners and u < owners[p] and owners[p] in state.source[u]:
                actual[(u, owners[p])] += 1
    for u, ns in enumerate(state.source):
        for v in ns:
            b.tick('final_original_edges')
            if u < v and not actual[(u, v)]:
                missing.append([u, v])
    if actual != +state.contacts:
        raise RuntimeError('incremental contact counts disagree with final recount')
    valid = connected and not missing and len(state.I) == len(state.source)
    response['diagnostic_embedding'] = result
    response['diag']['final'] = dict(valid=valid, connected_nonempty=connected, missing_edges=missing,
                                    missing=len(missing), qubits=len(owners), introduced=len(state.I))
    response['diag']['state'] = dict(cut=state.cut, generation=state.generation, introduced=sorted(state.I),
        live=sorted(u for u in state.I if state.live(u)),
        chains={u:state.ordered(c) for u,c in state.chains.items()}, roots=state.roots.copy(),
        trees={u:sorted(e) for u,e in state.trees.items()})
    b.check()
    if valid and not response.get('error') and not response['diag']['fatal_error']:
        response['embedding'], response['status'] = result, 'SUCCESS'


def frontier_embed(source, target, *, seed=0, timeout=60., deadline=None):
    started, cpu = time.perf_counter(), time.process_time()
    response = dict(status='FAILURE', embedding={}, diag=dict(algorithm='zephyr_frontier', policy='C012',
        events=[], fatal_error=False, work_limit=None, label_order='diagnostic IDs are supplied node ranks',
        restrictions=['one_monotone_sweep','three_strip_birth_window','fixed_roots','proper_suffix_only','closed_owners_fixed']))
    state, b, absolute = None, None, None
    try:
        if type(seed) is not int or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout <= 0:
            raise _InputError('integer seed and positive finite timeout required')
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise _InputError('finite deadline required')
        absolute = min(started+timeout, deadline) if deadline is not None else started+timeout
        reserve = min(.5, timeout/10)
        b = _Budget(absolute-reserve)
        response['diag'].update(deadline=absolute, search_deadline=b.deadline, final_reserve=reserve)
        with b.stage('input_geometry'):
            source_labels, src = _graph(source, b)
            target_labels, adj = _graph(target, b)
            if len(src) > len(adj):
                raise _InputError('source vertex count exceeds target count')
            m, coords = _geometry(target, target_labels, adj, b)
            state = _State(src, adj, coords, m, seed, b)
            response['diag'].update(sweep=state.sweep, source_ranks=state.srank, target_ranks=state.trank,
                                   initial=dict(introduced=[], qubits=0, cut=0))
        response['diag']['stop_reason'] = _run(state, response['diag'])
    except _Deadline as exc:
        response['diag']['stop_reason'] = 'search_deadline'
        response['diag']['interrupted_stage'] = str(exc)
    except Exception as exc:
        expected = isinstance(exc, _InputError)
        response.update(status='FAILURE' if expected else 'ERROR', error=f'{type(exc).__name__}: {exc}')
        response['diag'].update(fatal_error=not expected, exception=dict(type=type(exc).__name__, message=str(exc), expected_input=expected))
    if b is not None:
        b.deadline = absolute
        if state is not None:
            try:
                with b.stage('final_validation_output'):
                    _final(state, source_labels, target_labels, response)
            except _Deadline:
                response['embedding'] = {}
                response['diag']['final_stop'] = 'deadline'
            except Exception as exc:
                response.update(status='ERROR', embedding={}, error=f'{type(exc).__name__}: {exc}')
                response['diag'].update(fatal_error=True, exception=dict(type=type(exc).__name__, message=str(exc), expected_input=False))
        response['diag'].update(work=dict(b.work), total_work=sum(b.work.values()),
                                stage_wall=dict(b.stage_wall), stage_cpu=dict(b.stage_cpu))
    finished = time.perf_counter()
    response['time'] = finished-started
    response['diag'].update(wall=finished-started, cpu=time.process_time()-cpu, finished=finished)
    if absolute is not None and finished >= absolute:
        response['embedding'] = {}
        if not response['diag']['fatal_error']:
            response['status'] = 'TIMEOUT'
    return response
