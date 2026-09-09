"""B024: joint initial placement before frozen B023 construction.

Standard-library-only experimental constructor. Connectivity is invariant;
missing logical contacts and overlapping ownership are not embedding evidence.
See notes/codex/tracks/b_024_policy.md for the fixed pre-code policy.
"""
from collections import Counter, deque
from contextlib import contextmanager
from heapq import heappop, heappush
from math import isfinite
from random import Random
from time import perf_counter


class _Stop(Exception):
    pass


class _Meter:
    def __init__(self, deadline, limit=19_000_000):
        self.deadline, self.limit = deadline, limit
        self.work = 0
        self.units, self.seconds = Counter(), Counter()
        self.stage = "setup"
        self.last = perf_counter()

    def clock(self):
        now = perf_counter()
        if now >= self.deadline:
            raise _Stop("final_deadline" if self.stage == "finalize" else "search_deadline")
        return now

    def step(self):
        if self.work >= self.limit:
            raise _Stop("final_work_limit" if self.stage == "finalize" else "search_work_limit")
        if self.work % 64 == 0:
            self.clock()
        self.work += 1
        self.units[self.stage] += 1

    def walk(self, values):
        for value in values:
            self.step()
            yield value

    def switch(self, stage):
        now = perf_counter()
        self.seconds[self.stage] += now - self.last
        self.stage, self.last = stage, now

    @contextmanager
    def phase(self, stage):
        previous = self.stage
        self.switch(stage)
        try:
            yield
        finally:
            self.switch(previous)


def _adjacency(graph, meter):
    if not isinstance(graph, dict):
        if graph.is_directed() or graph.is_multigraph():
            raise ValueError("simple undirected graph required")
        graph = {u: tuple(meter.walk(graph[u])) for u in meter.walk(graph)}
    answer = {}
    for u, neighbors in graph.items():
        meter.step()
        if type(u) is not int or not isinstance(neighbors, (tuple, list, set, frozenset)):
            raise ValueError("integer IDs and finite adjacency containers required")
        row = set()
        for v in meter.walk(neighbors):
            if type(v) is not int or v == u or v in row:
                raise ValueError("simple loopless integer graph required")
            row.add(v)
        answer[u] = row
    for u, row in answer.items():
        for v in meter.walk(row):
            if v not in answer or u not in answer[v]:
                raise ValueError("complete symmetric adjacency required")
    return answer


def _edge(u, v):
    return (u, v) if u < v else (v, u)


class _State:
    def __init__(self, chains, owners, contacts, Q, M, O, F):
        self.chains, self.owners, self.contacts = chains, owners, contacts
        self.Q, self.M, self.O, self.F = Q, M, O, F

    def score(self):
        return dict(qubits=self.Q, missing=self.M, overlap=self.O, energy=self.F)


class _Context:
    def __init__(self, source, target, meter, seed=0):
        self.m = meter
        with meter.phase("normalization"):
            self.G = _adjacency(source, meter)
            self.H = _adjacency(target, meter)
            self.vertices = sorted(meter.walk(self.G))
            self.qorder = sorted(meter.walk(self.H))
            Random(seed).shuffle(self.qorder)
            self.rank = {q: i for i, q in enumerate(meter.walk(self.qorder))}
            self.adj = {q: tuple(sorted(meter.walk(self.H[q]), key=self.rank.__getitem__))
                        for q in meter.walk(self.qorder)}
            if len(self.G) > len(self.H):
                raise ValueError("more source vertices than target sites")
            self.edges = []
            for u in self.vertices:
                for v in sorted(meter.walk(self.G[u])):
                    if u < v:
                        self.edges.append((u, v))
            self.edge_order = list(meter.walk(self.edges))
            Random(seed).shuffle(self.edge_order)
            self.mu = {e: 1 for e in meter.walk(self.edges)}
            self.lam = {}
        self.state = None
        self.moves = []
        self.stats = Counter()
        self.cursor = 0

    def initialize(self):
        m = self.m
        with m.phase("initialization"):
            order, seen = [], set()
            for root in sorted(m.walk(self.vertices), key=lambda u: (-len(self.G[u]), u)):
                if root in seen:
                    continue
                seen.add(root)
                queue = [root]
                for u in queue:
                    m.step(); order.append(u)
                    for v in sorted(m.walk(self.G[u]), key=lambda v: (-len(self.G[v]), v)):
                        if v not in seen:
                            seen.add(v); queue.append(v)
            physical = []
            if self.qorder:
                root = min(m.walk(self.qorder), key=lambda q: (-len(self.H[q]), self.rank[q]))
                physical = [root]; seen = {root}
                for q in physical:
                    m.step()
                    for p in m.walk(self.adj[q]):
                        if p not in seen:
                            seen.add(p); physical.append(p)
                if len(physical) != len(self.H):
                    raise ValueError("disconnected target unsupported")
            chains = {u: frozenset((q,)) for u, q in m.walk(zip(order, physical))}
            self.install(chains)
            return dict(source_order=order, target_order=physical,
                        edge_order=list(m.walk(self.edge_order)))

    def prepare_placement(self, row):
        """One private exact-distance permutation preparation; no prefix output."""
        m = self.m; entry = self.state; began = m.work; started = perf_counter()
        row.update(complete=False, published=False, bfs_roots_complete=0,
                   pairs_visited=0, passes_completed=0, swaps=[],
                   active_root=None, active_pair=None, active_pass=None)
        try:
            row['active_stage'] = 'placement_setup'
            with m.phase('placement_setup'):
                pi = {}
                for u in m.walk(self.vertices):
                    if len(entry.chains[u]) != 1:
                        raise ValueError('placement requires singleton entry')
                    pi[u] = next(m.walk(entry.chains[u]))
                sites = sorted(m.walk(pi.values()), key=self.rank.__getitem__)
                if len(set(m.walk(sites))) != len(self.vertices):
                    raise ValueError('placement entry overlaps')
                row.update(sites=list(m.walk(sites)), entry_assignment=list(m.walk(sorted(pi.items()))),
                           entry_missing=entry.M)
            distances = {}
            row['active_stage'] = 'placement_distance'
            with m.phase('placement_distance'):
                for root in sites:
                    m.clock(); row['active_root'] = root
                    pending = set(m.walk(sites)); pending.discard(root)
                    seen = {root: 0}; queue = deque([root]); exact = {root: 0}
                    while queue and pending:
                        m.step(); q = queue.popleft()
                        for p in m.walk(self.adj[q]):
                            if p in seen:
                                continue
                            seen[p] = seen[q]+1; queue.append(p)
                            if p in pending:
                                m.step(); exact[p] = seen[p]; pending.remove(p)
                                if not pending:
                                    break
                    if pending:
                        raise ValueError('unreachable initial target sites')
                    distances[root] = exact
                    row['bfs_roots_complete'] += 1
                    m.clock()
                row['active_root'] = None
            def distance(a, c):
                m.step()
                return distances[a][c]
            def cost(assignment):
                return sum(distance(assignment[u], assignment[v]) for u, v in m.walk(self.edges))
            row['active_stage'] = 'placement_optimize'
            with m.phase('placement_optimize'):
                value = cost(pi)
                row['entry_distance_cost'] = row['private_distance_cost'] = value
                for sweep in range(2):
                    m.clock(); row['active_pass'] = sweep
                    for i, u in enumerate(m.walk(self.vertices)):
                        for v in m.walk(self.vertices[i+1:]):
                            row['active_pair'] = (u, v); row['pairs_visited'] += 1
                            pu, pv = pi[u], pi[v]; delta = 0
                            for w in sorted(m.walk(self.G[u])):
                                if w != v:
                                    delta += distance(pv, pi[w])-distance(pu, pi[w])
                            for w in sorted(m.walk(self.G[v])):
                                if w != u:
                                    delta += distance(pu, pi[w])-distance(pv, pi[w])
                            if delta < 0:
                                m.step()
                                pi[u], pi[v] = pv, pu; value += delta
                                row['swaps'].append(dict(pass_index=sweep, pair=(u, v), delta=delta, cost=value))
                                row['private_distance_cost'] = value
                    row['passes_completed'] += 1; m.clock()
                row['active_pair'] = row['active_pass'] = None
                checked_cost = cost(pi)
                if checked_cost != value:
                    raise ValueError('placement delta/cost mismatch')
            row['active_stage'] = 'placement_recount'
            with m.phase('placement_recount'):
                private = object.__new__(_Context)
                private.__dict__.update(m.walk(self.__dict__.items()))
                private.install({u: frozenset((pi[u],)) for u in m.walk(self.vertices)})
                if private.state.Q != len(self.vertices) or private.state.O or set(m.walk(private.state.owners)) != set(m.walk(sites)):
                    raise ValueError('placement changed its initial footprint')
                row.update(proposed_assignment=list(m.walk(sorted(pi.items()))),
                           final_distance_cost=value, proposed_missing=private.state.M,
                           accepted_swaps=len(row['swaps']))
                m.clock()
                self.state = private.state
                row['published'] = row['complete'] = True
        except _Stop as exc:
            row['stopped_by'] = str(exc)
            row['interrupted_stage'] = row.get('active_stage')
            raise
        except Exception as exc:
            row['error'] = repr(exc)
            row['interrupted_stage'] = row.get('active_stage')
            raise
        finally:
            row.update(work=m.work-began, wall=perf_counter()-started)

    def components(self, sites):
        m = self.m
        unseen = set(m.walk(sites)); result = []
        for root in sorted(m.walk(sites), key=self.rank.__getitem__):
            if root not in unseen:
                continue
            unseen.remove(root); component = {root}; queue = [root]
            for q in queue:
                m.step()
                for p in m.walk(self.adj[q]):
                    if p in unseen:
                        unseen.remove(p); component.add(p); queue.append(p)
            result.append(frozenset(component))
        return result

    def counts_for(self, owner, sites, ownership):
        m = self.m
        counts = {_edge(owner, v): 0 for v in m.walk(self.G[owner])}
        for q in m.walk(sites):
            for p in m.walk(self.adj[q]):
                for v in m.walk(ownership.get(p, ())):
                    if v in self.G[owner]:
                        counts[_edge(owner, v)] += 1
        return counts

    def install(self, chains):
        """Initial/test state only; validate connectivity and compute all counters."""
        m = self.m
        if set(m.walk(chains)) != set(m.walk(self.G)):
            raise ValueError("source coverage")
        owners = {}
        saved = {}
        for u in m.walk(self.vertices):
            c = frozenset(m.walk(chains[u]))
            if not c or any(q not in self.H for q in m.walk(c)) or len(self.components(c)) != 1:
                raise ValueError("invalid connected chain")
            saved[u] = c
            for q in m.walk(c):
                owners.setdefault(q, set()).add(u)
        owners = {q: frozenset(m.walk(us)) for q, us in m.walk(owners.items())}
        contacts = {}
        for u in m.walk(self.vertices):
            for e, count in m.walk(self.counts_for(u, saved[u], owners).items()):
                if e[0] == u:
                    contacts[e] = count
        Q = sum(len(c) for c in m.walk(saved.values()))
        O = sum(len(us)-1 for us in m.walk(owners.values()))
        M = sum(count == 0 for count in m.walk(contacts.values()))
        F = Q + sum(self.lam.get(q, 1)*(len(us)-1) for q, us in m.walk(owners.items()))
        F += sum(self.mu[e] for e, count in m.walk(contacts.items()) if count == 0)
        self.state = _State(saved, owners, contacts, Q, M, O, F)

    def price_edge(self, e):
        with self.m.phase("prices"):
            self.m.step(); self.m.clock()
            self.mu[e] += 1
            self.state.F += int(self.state.contacts[e] == 0)
            self.stats['edge_price_updates'] += 1

    def price_site(self, q):
        with self.m.phase("prices"):
            excess = len(self.state.owners[q])-1
            self.m.step(); self.m.clock()
            self.lam[q] = self.lam.get(q, 1)+excess
            self.state.F += excess*excess
            self.stats['site_price_updates'] += 1

    def replacement(self, owner, sites):
        """Exact local delta; callers supply a connected nonempty replacement."""
        m, old = self.m, self.state
        with m.phase("scoring"):
            new = frozenset(m.walk(sites))
            if not new:
                raise ValueError("empty replacement")
            counts = self.counts_for(owner, new, old.owners)
            lost, restored = [], []
            M, O = old.M, old.O
            Q = old.Q + len(new)-len(old.chains[owner])
            F = old.F + Q-old.Q
            for e, count in m.walk(counts.items()):
                change = int(count == 0)-int(old.contacts[e] == 0)
                M += change; F += self.mu[e]*change
                if change == 1:
                    lost.append(e)
                elif change == -1:
                    restored.append(e)
            changed = set(m.walk(old.chains[owner])) ^ set(m.walk(new))
            owner_patch = {}
            for q in m.walk(changed):
                before = old.owners.get(q, frozenset())
                after = set(m.walk(before))
                if q in new:
                    after.add(owner)
                else:
                    after.remove(owner)
                delta = max(0, len(after)-1)-max(0, len(before)-1)
                O += delta; F += self.lam.get(q, 1)*delta
                owner_patch[q] = frozenset(after)
            return dict(owner=owner, sites=new, counts=counts, owner_patch=owner_patch,
                        score=dict(qubits=Q, missing=M, overlap=O, energy=F),
                        lost=sorted(lost), restored=sorted(restored))

    def publish(self, proposal, row):
        m, old = self.m, self.state
        with m.phase("publication"):
            chains = dict(m.walk(old.chains.items()))
            owners = dict(m.walk(old.owners.items()))
            contacts = dict(m.walk(old.contacts.items()))
            chains[proposal['owner']] = proposal['sites']
            for q, us in m.walk(proposal['owner_patch'].items()):
                if us:
                    owners[q] = us
                else:
                    owners.pop(q, None)
            contacts.update(m.walk(proposal['counts'].items()))
            s = proposal['score']
            state = _State(chains, owners, contacts, s['qubits'], s['missing'], s['overlap'], s['energy'])
            row.update(owner=proposal['owner'], after=s,
                       lost_contacts=list(m.walk(proposal['lost'])),
                       restored_contacts=list(m.walk(proposal['restored'])))
            m.clock()
            self.state = state
            row['committed'] = True
        self.stats['commits'] += 1
        self.stats['lost_contacts'] += len(proposal['lost'])
        self.stats['restored_contacts'] += len(proposal['restored'])
        self.stats['energy_increasing_commits'] += int(state.F > old.F)

    def route_sites(self, owner, other):
        m, state = self.m, self.state
        with m.phase("routing"):
            boundary = set()
            for q in m.walk(state.chains[other]):
                boundary.update(m.walk(self.adj[q]))
            distances, previous, heap = {}, {}, []
            for q in sorted(m.walk(state.chains[owner]), key=self.rank.__getitem__):
                distances[q] = 0; previous[q] = None
                m.step(); heappush(heap, (0, self.rank[q], q))
            terminal = None
            while heap:
                m.step(); distance, _, q = heappop(heap)
                if distance != distances[q]:
                    continue
                if q in boundary:
                    terminal = q; break
                for p in m.walk(self.adj[q]):
                    increment = 0 if p in state.chains[owner] else 1 + (
                        self.lam.get(p, 1) if state.owners.get(p) else 0)
                    value = distance + increment
                    if value < distances.get(p, float('inf')):
                        distances[p] = value; previous[p] = q
                        m.step(); heappush(heap, (value, self.rank[p], p))
            if terminal is None:
                return None
            new = set(m.walk(state.chains[owner])); q = terminal
            while q is not None:
                m.step(); new.add(q); q = previous[q]
            return frozenset(new)

    def _action(self, kind, key, generate):
        m = self.m; started = perf_counter(); began = m.work
        row = dict(kind=kind, selected=key, before=self.state.score(), committed=False,
                   complete=False, generated=0, scored=0, proposal_scores=[])
        self.moves.append(row)
        winner = None; winning_rank = None
        try:
            m.clock()
            for owner, sites in generate():
                row['generated'] += 1
                p = self.replacement(owner, sites)
                s = p['score']; row['scored'] += 1
                row['proposal_scores'].append(s)
                rank = (s['energy'], s['overlap'], s['missing'], s['qubits'], owner)
                if kind == 'erase':
                    with m.phase('scoring'):
                        rank += (tuple(sorted(self.rank[q] for q in m.walk(sites))),)
                if winning_rank is None or rank < winning_rank:
                    winning_rank, winner = rank, p
            if winner is not None:
                self.publish(winner, row)
            else:
                m.clock()
            row['complete'] = True
        except _Stop as exc:
            row['stopped_by'] = str(exc)
            row['discarded_scored'] = row['scored']
            raise
        except Exception as exc:
            row['error'] = repr(exc)
            row['discarded_scored'] = row['scored']
            raise
        finally:
            row.update(work=m.work-began, wall=perf_counter()-started)
        return row

    def route(self, e):
        if self.state.contacts[e]:
            raise ValueError("routing requires a missing edge")
        self.stats['routing_attempts'] += 1
        def generate():
            u, v = e
            for owner, other in ((u, v), (v, u)):
                sites = self.route_sites(owner, other)
                if sites is not None:
                    yield owner, sites
        return self._action('route', e, generate)

    def conflict(self):
        with self.m.phase('schedule'):
            later = earlier = None
            for q, owners in self.m.walk(self.state.owners.items()):
                if len(owners) <= 1:
                    continue
                rank = self.rank[q]
                if rank >= self.cursor and (later is None or rank < self.rank[later]):
                    later = q
                if earlier is None or rank < self.rank[earlier]:
                    earlier = q
            q = later if later is not None else earlier
            if q is not None:
                self.cursor = (self.rank[q]+1) % len(self.qorder)
            return q

    def erase(self, q):
        if len(self.state.owners.get(q, ())) <= 1:
            raise ValueError("erasure requires overlapping ownership")
        self.stats['erasure_visits'] += 1
        def generate():
            with self.m.phase('erasure'):
                owners = sorted(self.m.walk(self.state.owners[q]))
            for owner in owners:
                with self.m.phase('erasure'):
                    chain = self.state.chains[owner]
                    if len(chain) > 1:
                        reduced = set(self.m.walk(chain)); reduced.remove(q)
                        choices = self.components(reduced)
                    else:
                        free = None
                        for p in self.m.walk(self.qorder):
                            if p not in self.state.owners:
                                free = p; break
                        choices = [frozenset((free,))] if free is not None else [
                            frozenset((p,)) for p in self.m.walk(self.adj[q])]
                for sites in choices:
                    yield owner, sites
        return self._action('erase', q, generate)

    def search(self):
        if self.state.M == self.state.O == 0:
            return 'initially_feasible'
        for sweep in range(8):
            for e in self.edge_order:
                with self.m.phase('schedule'):
                    self.m.step(); self.m.clock()
                    self.stats['edge_visits'] += 1
                if self.state.contacts[e] == 0:
                    self.price_edge(e); self.route(e)
                if self.state.M == self.state.O == 0:
                    return 'feasible_after_route'
                q = self.conflict()
                if q is not None:
                    self.price_site(q); self.erase(q)
                if self.state.M == self.state.O == 0:
                    return 'feasible_after_erasure'
            self.stats['completed_passes'] += 1
        return 'pass_limit'

    def cleanup(self):
        """One source-ordered leaf-pruning pass; every published prefix is valid."""
        if self.state.M or self.state.O:
            return
        for u in self.vertices:
            with self.m.phase('cleanup'):
                heap = []
                for q in self.m.walk(self.state.chains[u]):
                    self.m.step(); heappush(heap, (self.rank[q], q))
            while heap:
                with self.m.phase('cleanup'):
                    self.m.step(); _, q = heappop(heap)
                    c = self.state.chains[u]
                    if q not in c or len(c) == 1:
                        continue
                    neighbors = [p for p in self.m.walk(self.adj[q]) if p in c]
                    if len(neighbors) > 1:
                        continue
                    new = set(self.m.walk(c)); new.remove(q)
                p = self.replacement(u, new)
                if p['score']['missing'] or p['score']['overlap']:
                    continue
                row = dict(kind='cleanup', selected=q, before=self.state.score(), committed=False)
                self.moves.append(row)
                self.publish(p, row)
                self.stats['cleanup_deletions'] += 1
                with self.m.phase('cleanup'):
                    for neighbor in self.m.walk(neighbors):
                        self.m.step(); heappush(heap, (self.rank[neighbor], neighbor))

    def snapshot(self):
        return dict(chains={u: sorted(self.m.walk(self.state.chains[u]), key=self.rank.__getitem__)
                            for u in self.m.walk(self.vertices)},
                    score=self.state.score(), site_prices=dict(self.m.walk(self.lam.items())),
                    edge_prices=[(e, price) for e, price in self.m.walk(self.mu.items()) if price != 1])

    def validate(self):
        """Full original-edge validation; counters alone never certify a minor."""
        m = self.m
        if set(m.walk(self.state.chains)) != set(m.walk(self.G)):
            return 'source_coverage'
        owner = {}
        for u in m.walk(self.vertices):
            chain = self.state.chains[u]
            if not chain:
                return 'empty_chain'
            for q in m.walk(chain):
                if q not in self.H:
                    return 'unknown_target_site'
                if q in owner:
                    return 'overlap'
                owner[q] = u
            if len(self.components(chain)) != 1:
                return 'disconnected_chain'
        found = set()
        for q, u in m.walk(owner.items()):
            for p in m.walk(self.adj[q]):
                v = owner.get(p)
                if v is not None and v in self.G[u]:
                    found.add(_edge(u, v))
        if found != set(m.walk(self.edges)):
            return 'missing_contact'
        return None


def _finish(ctx, meter, info, absolute):
    """Shared final gate, also exercised with tiny supplied states in checks."""
    embedding = {}; status = 'FAILURE'
    meter.deadline, meter.limit = absolute, 20_000_000
    meter.switch('finalize')
    final_work, final_start = meter.work, perf_counter()
    try:
        if ctx is not None and ctx.state is not None:
            info['final'] = ctx.state.score()
            info['final_state'] = ctx.snapshot()
            if info['error'] is None:
                info['final_validation'] = ctx.validate()
                if info['final_validation'] is None:
                    for u in meter.walk(ctx.vertices):
                        embedding[u] = sorted(meter.walk(ctx.state.chains[u]), key=ctx.rank.__getitem__)
                    meter.clock(); status = 'SUCCESS'
        meter.clock()
    except _Stop as exc:
        info['finalization_stop'] = str(exc); embedding = {}; status = 'FAILURE'
    except Exception as exc:
        info['finalization_error'] = repr(exc); embedding = {}; status = 'FAILURE'
    meter.switch('administration')
    info.update(finalization_work=meter.work-final_work, finalization_wall=perf_counter()-final_start,
                work=meter.work, stage_units=dict(meter.units), stage_wall=dict(meter.seconds))
    return embedding, status


def contact_embed(source, target, *, timeout=20.0, deadline=None, seed=0):
    """Bounded constructor, returning only a timely independently valid minor."""
    began = perf_counter(); absolute = began+20.0
    info = dict(algorithm='joint-placement-construction', version='B024', seed=seed,
                error=None, stopped_by=None, limits=dict(global_work=20_000_000,
                    search_work=19_000_000, maximum_seconds=20.0, passes=8, clock_poll_units=64))
    meter = ctx = None
    embedding = {}; status = 'FAILURE'
    try:
        if type(seed) is not int or type(timeout) not in (int, float) or not isfinite(timeout) or timeout <= 0:
            raise ValueError('integer seed and positive finite timeout required')
        allowed = min(20.0, timeout)
        absolute = began+allowed
        if deadline is not None:
            if type(deadline) not in (int, float) or not isfinite(deadline):
                raise ValueError('finite absolute deadline required')
            absolute = min(absolute, deadline)
        reserve = min(1.0, .05*allowed)
        meter = _Meter(absolute-reserve)
        info.update(started=began, deadline=absolute, search_deadline=meter.deadline,
                    final_reserve_seconds=reserve)
        ctx = _Context(source, target, meter, seed)
        info['initialization_orders'] = ctx.initialize()
        info['placement'] = {}
        info['error'] = 'placement_not_complete'
        ctx.prepare_placement(info['placement'])
        info['error'] = None
        info['initial'] = ctx.state.score()
        info['initial_state'] = ctx.snapshot()
        info.update(initialization_work=meter.work, initialization_wall=perf_counter()-began)
        info['stopped_by'] = ctx.search()
        if ctx.state.M == ctx.state.O == 0:
            info.update(first_feasible=ctx.state.score(), first_feasible_wall=perf_counter()-began,
                        first_feasible_work=meter.work)
            ctx.cleanup()
    except _Stop as exc:
        info['stopped_by'] = str(exc)
    except (ValueError, TypeError, KeyError) as exc:
        info.update(stopped_by='invalid_input_or_state', error=str(exc))
    except Exception as exc:
        info.update(stopped_by='error', error=repr(exc))
    if meter is not None:
        embedding, status = _finish(ctx, meter, info, absolute)
    if ctx is not None:
        info.update(stats=dict(ctx.stats), moves=ctx.moves)
    ended = perf_counter()
    if ended >= absolute:
        status = 'TIMEOUT'; embedding = {}
    info.update(wall=ended-began, returned=ended, deadline=absolute,
                deadline_overrun=max(0.0, ended-absolute))
    return dict(status=status, embedding=embedding if status == 'SUCCESS' else {}, diag=info)
