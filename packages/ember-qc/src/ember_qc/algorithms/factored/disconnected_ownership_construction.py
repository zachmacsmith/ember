"""B030: sparse disjoint ownership with temporary disconnected components.

The precise policy is notes/codex/tracks/b_030_exact_contract.md. One evolving
state, one valid incumbent, no external embedding constructor or solver.
"""
from collections import Counter, deque
from heapq import heappop, heappush
import importlib.util
from math import isfinite, log
from pathlib import Path
from random import Random
import sys
from time import perf_counter, process_time


def _load(suffix, path):
    name = __name__ + '_' + suffix
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]


def _uniform(values, draw):
    return values[min(len(values)-1, int(draw * len(values)))] if len(values) else None


class _State:
    def __init__(self, chains, labels, components, debts, missing, distances):
        self.chains, self.labels = chains, labels
        self.components, self.debts = components, debts
        self.missing, self.distances = missing, distances
        self.Q = sum(map(len, chains))


class _Engine:
    def __init__(self, source, target, seed, meter, began, connected_only, support):
        self.m, self.began, self.connected_only = meter, began, connected_only
        self.stop_type = support._Stop
        self.stats, self.receipts, self.traces, self.events, self.sweeps = Counter(), [], [], [], []
        self.last_trace = self.initial = self.first_valid = self.incumbent = None
        self.state, self.cert_graphs = None, None
        self.rng = Random(seed)
        with meter.phase('normalization'):
            original = support._adjacency(source, meter)
            self.H = support._adjacency(target, meter)
            if set(self.H) != set(range(4800)):
                raise ValueError('B030 requires original linear ideal-Z12 target IDs')
            self.vlabels = tuple(original)
            vindex = {v: i for i, v in enumerate(self.vlabels)}
            self.G = tuple(frozenset(vindex[v] for v in original[u]) for u in self.vlabels)
            self.original_G = original
            self.n = len(self.G)
            self.edges = tuple((u, v) for u in range(self.n) for v in sorted(self.G[u]) if u < v)
            self.incident = [[] for _ in self.G]
            for i, (u, v) in enumerate(self.edges):
                self.incident[u].append(i); self.incident[v].append(i)
            self.lam, self.gamma = [1] * len(self.edges), [1] * self.n
            source_rank_order, self.qorder = list(range(self.n)), list(range(4800))
            self.rng.shuffle(source_rank_order); self.rng.shuffle(self.qorder)
            self.srank = {u: i for i, u in enumerate(source_rank_order)}
            self.rank = {q: i for i, q in enumerate(self.qorder)}
            self.adj = tuple(tuple(sorted(self.H[q], key=self.rank.__getitem__)) for q in range(4800))
            self.order = self.source_order()
            meter.clock()
        with meter.phase('array_import'):
            arrays = _load('arrays', Path(__file__).with_name('disconnected_ownership_arrays.py'))
        self.np = arrays.np
        self.arrays = arrays.Arrays(self.H, self.rank, meter)

    def source_order(self):
        unseen, result = set(range(self.n)), []
        key = lambda u: (-len(self.G[u]), self.srank[u])
        while unseen:
            root = min(unseen, key=key); unseen.remove(root)
            queue = deque([root])
            while queue:
                u = queue.popleft(); result.append(u)
                for v in sorted(self.G[u], key=key):
                    self.m.step('source_bfs_arc')
                    if v in unseen:
                        unseen.remove(v); queue.append(v)
        return tuple(result)

    def components(self, sites):
        with self.m.phase('components'):
            unseen, answer = set(sites), []
            while unseen:
                q = min(unseen, key=self.rank.__getitem__)
                unseen.remove(q); reached, queue = {q}, deque([q])
                while queue:
                    r = queue.popleft()
                    for s in self.adj[r]:
                        self.m.step('component_arc')
                        if s in unseen:
                            unseen.remove(s); reached.add(s); queue.append(s)
                answer.append(frozenset(reached))
            return tuple(answer)

    def debt(self, components):
        with self.m.phase('component_debt'):
            if len(components) <= 1:
                return 0
            # Components already have increasing minimum-target-rank order.
            best, total = {}, 0
            for j in range(1, len(components)):
                best[j] = max(0, self.arrays.distance(components[0], components[j])-1)
            while best:
                j = min(best, key=lambda i: (best[i], i))
                total += best.pop(j)
                for k in best:
                    best[k] = min(best[k], max(0, self.arrays.distance(components[j], components[k])-1))
                    self.m.step('component_mst_edge')
            if total < len(components)-1:
                raise ValueError('invalid distance debt for distinct owner components')
            return total

    def edge_values(self, left, right):
        with self.m.phase('edge_debt'):
            supported = False
            for q in sorted(left, key=self.rank.__getitem__):
                for r in self.adj[q]:
                    self.m.step('contact_arc')
                    if r in right:
                        supported = True; break
                if supported:
                    break
            distance = max(0, self.arrays.distance(left, right)-1)
            if bool(distance) == supported:
                raise ValueError('actual contact and exact distance disagree')
            return int(not supported), distance

    def prepare(self, changes):
        """Construct a complete private state, without modifying current ownership."""
        with self.m.phase('private_state'):
            if self.state is None:
                if set(changes) != set(range(self.n)):
                    raise ValueError('initial state must cover every owner')
                chains, comps, debts = [None]*self.n, [None]*self.n, [0]*self.n
                labels = self.np.full(4800, -1, dtype=self.np.int32)
                missing, distances = [0]*len(self.edges), [0]*len(self.edges)
            else:
                chains, comps, debts = list(self.state.chains), list(self.state.components), list(self.state.debts)
                labels = self.state.labels.copy()
                missing, distances = list(self.state.missing), list(self.state.distances)
                for u in changes:
                    for q in chains[u]:
                        labels[q] = -1
                        self.m.step('vacated_owner_site')
            for u, values in sorted(changes.items()):
                sites = frozenset(values)
                if not sites or any(type(q) is not int or q not in self.H for q in sites):
                    raise ValueError('empty owner or foreign site')
                for q in sites:
                    if labels[q] != -1:
                        raise ValueError('private ownership collision')
                    labels[q] = u; self.m.step('installed_owner_site')
                chains[u] = sites
                comps[u] = self.components(sites)
                debts[u] = self.debt(comps[u])
            affected = {e for u in changes for e in self.incident[u]}
            for e in sorted(affected):
                u, v = self.edges[e]
                missing[e], distances[e] = self.edge_values(chains[u], chains[v])
            labels.flags.writeable = False
            candidate = _State(tuple(chains), labels, tuple(comps), tuple(debts), tuple(missing), tuple(distances))
            if candidate.Q != int(self.np.count_nonzero(labels >= 0)):
                raise ValueError('chain membership and occupied-site count disagree')
            self.m.clock()
            return candidate

    def energy(self, state):
        return (state.Q + sum(p*(m+d) for p, m, d in zip(self.lam, state.missing, state.distances))
                + sum(p*d for p, d in zip(self.gamma, state.debts)))

    def snapshot(self, state=None):
        state = self.state if state is None else state
        if state is None:
            return None
        return dict(Q=state.Q, M=sum(state.missing), D=sum(state.distances), P=sum(state.debts),
                    component_excess=sum(len(c)-1 for c in state.components),
                    fragmented_owners=sum(len(c)>1 for c in state.components), E=self.energy(state))

    def mapping(self, state):
        return {v: sorted(state.chains[u], key=self.rank.__getitem__) for u, v in enumerate(self.vlabels)}

    def certify(self, state):
        with self.m.phase('validation'):
            validator = _load('validator', Path(__file__).parents[2] / 'validation.py')
            if self.cert_graphs is None:
                source, target = validator.nx.Graph(), validator.nx.Graph()
                source.add_nodes_from(self.vlabels)
                source.add_edges_from((self.vlabels[u], self.vlabels[v]) for u, v in self.edges)
                target.add_nodes_from(self.H)
                target.add_edges_from((q, r) for q in self.H for r in self.H[q] if q < r)
                self.m.step('validation_graph_setup', len(self.H)+sum(map(len, self.H.values())))
                self.m.clock()
                self.cert_graphs = source, target
            mapping = self.mapping(state)
            result = validator.validate_layer1(mapping, *self.cert_graphs)
            self.m.clock()
            if not result.passed:
                raise ValueError('existing validator rejected state: ' + str(result))
            return mapping

    def incumbent_check(self):
        if any(self.state.missing) or any(len(c) != 1 for c in self.state.components):
            return
        if self.incumbent is not None and self.state.Q >= self.incumbent.Q:
            return
        self.certify(self.state)
        event = dict(elapsed=perf_counter()-self.began, Q=self.state.Q,
                     acl=self.state.Q/self.n if self.n else None,
                     slot=self.stats['slots_started'], **({'first': True} if self.incumbent is None else {}))
        with self.m.phase('incumbent_publication'):
            self.m.clock()
            self.incumbent = self.state
            if self.first_valid is None:
                self.first_valid = dict(event)
            self.events.append(event)

    def initialize(self):
        with self.m.phase('initialization'):
            if self.n > 4800:
                return False
            def center(q):
                u, w, k, j, z = map(int, self.arrays.coords[q])
                x, y = (w, 2*z+j+.5) if u == 0 else (2*z+j+.5, w)
                return ((x-12)**2+(y-12)**2, self.rank[q])
            root = min(self.H, key=center)
            seen, queue, order = {root}, deque([root]), []
            while queue and len(order) < self.n:
                q = queue.popleft(); order.append(q)
                for r in self.adj[q]:
                    self.m.step('initial_target_bfs_arc')
                    if r not in seen:
                        seen.add(r); queue.append(r)
            if len(order) != self.n:
                raise ValueError('target component too small')
            self.state = self.prepare({u: frozenset([int(q)]) for u, q in zip(self.order, order)})
            self.initial = self.snapshot()
            self.initial['target_root'] = root
            self.incumbent_check()
            return True

    def patch(self, u, focus, draw, row):
        sites = sorted(self.state.chains[u], key=self.rank.__getitem__)
        q = _uniform(sites, focus)
        patch = [q] + [r for r in self.adj[q] if self.state.labels[r] >= 0 and
                       (int(self.state.labels[r]) == u or int(self.state.labels[r]) in self.G[u])]
        patch = sorted(set(patch), key=self.rank.__getitem__)
        offsets, mapped = self.arrays.translations(patch, self.state.labels)
        row.update(focus=q, patch_size=len(patch), destinations=len(mapped))
        scores = self.arrays.guide(patch, mapped, self.state.chains, self.state.labels, self.G)
        selected = self.arrays.sample(scores, draw)
        if selected is None:
            return None
        row.update(offset=list(map(int, offsets[selected])), guide=float(scores[selected]))
        return self.patch_changes(patch, list(map(int, mapped[selected])))

    def patch_changes(self, patch, destinations):
        if len(patch) != len(destinations) or len(set(destinations)) != len(destinations):
            raise ValueError('noninjective patch')
        patch_set = set(patch)
        if any(q not in self.H or (self.state.labels[q] >= 0 and q not in patch_set) for q in destinations):
            raise ValueError('occupied or foreign patch destination')
        image = dict(zip(patch, destinations))
        for q in patch:
            for r in self.adj[q]:
                self.m.step('selected_patch_arc')
                if r in image and image[r] not in self.H[image[q]]:
                    raise ValueError('patch internal edge lost')
        changed = {int(self.state.labels[q]) for q in patch}
        if -1 in changed:
            raise ValueError('patch contains free site')
        changes = {u: set(self.state.chains[u])-patch_set for u in changed}
        for q, r in zip(patch, destinations):
            changes[int(self.state.labels[q])].add(r)
        return changes

    def label(self, u, subtype, focus, draw, row):
        old = self.state.chains[u]
        row['subtype'] = subtype
        if subtype == 0:
            q = _uniform(sorted(old, key=self.rank.__getitem__), focus)
            eligible = self.arrays.ranked[self.state.labels[self.arrays.ranked] != u]
            scores = self.arrays.guide([q], eligible[:, None], self.state.chains, self.state.labels, self.G)
            selected = self.arrays.sample(scores, draw)
            row.update(focus=q, destinations=len(eligible))
            if selected is None:
                return None
            r = int(eligible[selected]); v = int(self.state.labels[r])
            row.update(destination=r, guide=float(scores[selected]))
            changes = {u: old-{q} | {r}}
            if v >= 0:
                changes[v] = self.state.chains[v]-{r} | {q}
            return changes
        if subtype == 3:
            eligible = sorted(old, key=self.rank.__getitem__) if len(old) > 1 else []
        else:
            boundary = set()
            for q in old:
                for r in self.adj[q]:
                    self.m.step('label_boundary_arc'); boundary.add(r)
            if subtype == 1:
                eligible = [q for q in boundary if self.state.labels[q] == -1]
            else:
                eligible = [q for q in boundary if self.state.labels[q] >= 0
                            and self.state.labels[q] != u
                            and len(self.state.chains[int(self.state.labels[q])]) > 1]
            eligible.sort(key=self.rank.__getitem__)
        row['destinations'] = len(eligible)
        r = _uniform(eligible, draw)
        if r is None:
            return None
        row['destination'] = r
        if subtype == 3:
            return {u: old-{r}}
        changes = {u: old | {r}}
        if subtype == 2:
            v = int(self.state.labels[r]); changes[v] = self.state.chains[v]-{r}
        return changes

    def merge(self, u, focus, row):
        components = self.state.components[u]
        row['component_count'] = len(components)
        if len(components) < 2:
            return None
        component = _uniform(components, focus)
        goal = self.state.chains[u]-component
        with self.m.phase('free_merge'):
            distance, parent, heap = {}, {}, []
            for q in sorted(component, key=self.rank.__getitem__):
                distance[q], parent[q] = 0, None
                heappush(heap, (0, self.rank[q], q))
            target = None
            while heap:
                cost, _, q = heappop(heap); self.m.step('merge_heap_pop')
                if cost != distance[q]:
                    continue
                if q in goal:
                    target = q; break
                for r in self.adj[q]:
                    self.m.step('merge_arc')
                    owner = int(self.state.labels[r])
                    if owner >= 0 and owner != u:
                        continue
                    candidate = cost + int(owner < 0)
                    if candidate < distance.get(r, float('inf')):
                        distance[r], parent[r] = candidate, q
                        heappush(heap, (candidate, self.rank[r], r))
            row['free_route_exhausted'] = target is None
            if target is None:
                return None
            path, q = [], target
            while q is not None:
                path.append(q); q = parent[q]; self.m.step('merge_path_site')
            path.reverse()
            added = set(path)-self.state.chains[u]
            if len(added) != distance[target] or not added:
                raise ValueError('incorrect actual merge cost')
            row.update(merge_cost=len(added), merge_path=path)
            return {u: self.state.chains[u] | added}

    def admit(self, candidate, draw, row):
        delta = self.energy(candidate)-self.energy(self.state)
        row.update(candidate=self.snapshot(candidate), delta_E=delta, log_draw=log(1.-draw))
        if self.connected_only and any(len(c) != 1 for c in candidate.components):
            row['reason'] = 'connected_ablation'; return False
        if delta > 0 and not row['log_draw'] < -delta:
            row['reason'] = 'metropolis'; return False
        if candidate.chains == self.state.chains:
            row['reason'] = 'identical_state'; return False
        with self.m.phase('publication'):
            self.m.clock()
            self.state = candidate
            row.update(accepted=True, reason='accepted')
        return True

    def visit(self, u, operator, sweep):
        draws = tuple(self.rng.random() for _ in range(3))
        self.stats['slots_started'] += 1; self.stats[operator+'_started'] += 1
        start, cpu = perf_counter(), process_time()
        row = dict(index=self.stats['slots_started'], owner=self.vlabels[u], operator=operator,
                   sweep=sweep, before=self.snapshot(), accepted=False, complete=False,
                   started=start-self.began)
        trace = {'index': row['index']}
        before = self.state
        try:
            if operator == 'PATCH':
                changes = self.patch(u, draws[0], draws[1], row)
            elif operator == 'LABEL':
                changes = self.label(u, sweep % 4, draws[0], draws[1], row)
            else:
                changes = self.merge(u, draws[0], row)
            if changes is None:
                row['reason'] = 'no_proposal'; self.stats[operator+'_no_proposal'] += 1
            else:
                self.stats[operator+'_proposals'] += 1
                trace['changes'] = {str(self.vlabels[v]): dict(before=sorted(before.chains[v]), after=sorted(changes[v]))
                                    for v in sorted(changes)}
                candidate = self.prepare(changes)
                self.stats[operator+'_scored'] += 1
                if self.admit(candidate, draws[2], row):
                    self.stats[operator+'_accepted'] += 1
                    self.incumbent_check()
                else:
                    self.stats[operator+'_rejected_'+row['reason']] += 1
            self.m.clock()
            row['complete'] = True
            self.stats[operator+'_completed'] += 1
        finally:
            row.update(wall=perf_counter()-start, cpu=process_time()-cpu,
                       elapsed=perf_counter()-self.began, after=self.snapshot())
            if not row['complete']:
                exc = sys.exc_info()[1]
                if isinstance(exc, self.stop_type):
                    row['interrupted_stage'] = str(exc)
                    self.stats[operator+'_interrupted'] += 1
                else:
                    row['error'] = repr(exc)
                    self.stats[operator+'_errors'] += 1
            self.receipts.append(row)
            self.last_trace = trace
            if len(self.traces) < 16:
                self.traces.append(trace)

    def run(self):
        if not self.initialize():
            return 'more_source_vertices_than_target'
        sweep = 0
        while True:
            self.m.clock()
            if self.incumbent is not None and self.incumbent.Q == self.n:
                return 'certified_Q_equals_n'
            for slot in range(self.n):
                u = self.order[(slot+sweep) % self.n]
                for operator in ('PATCH', 'LABEL', 'MERGE'):
                    self.visit(u, operator, sweep)
                    if self.incumbent is not None and self.incumbent.Q == self.n:
                        return 'certified_Q_equals_n'
            with self.m.phase('price_update'):
                before = self.snapshot()
                lam = [p+int(m) for p, m in zip(self.lam, self.state.missing)]
                gamma = [p+int(len(c)>1) for p, c in zip(self.gamma, self.state.components)]
                self.m.clock()
                self.lam, self.gamma = lam, gamma
                sweep += 1; self.stats['completed_sweeps'] = sweep
                self.sweeps.append(dict(sweep=sweep, elapsed=perf_counter()-self.began,
                                        before_price_update=before, after_price_update=self.snapshot()))


def ownership_embed(source, target, *, timeout=60., deadline=None, seed=0, connected_only=False):
    began = perf_counter()
    cpu_began = process_time()
    support = meter = engine = None
    absolute = began
    info = dict(algorithm='disconnected-ownership', version='B030', seed=seed,
                connected_only=connected_only, error=None, stopped_by=None,
                work_limit=None, sweep_limit=None, query_limit=None, trace_limit=16)
    output, status = {}, 'FAILURE'
    try:
        if type(timeout) not in (float, int) or not isfinite(timeout) or timeout <= 0:
            raise ValueError('positive finite timeout required')
        if type(seed) is not int or type(connected_only) is not bool:
            raise ValueError('integer seed and boolean ablation required')
        absolute = began+timeout
        if deadline is not None:
            if type(deadline) not in (float, int) or not isfinite(deadline):
                raise ValueError('finite absolute deadline required')
            absolute = min(absolute, deadline)
        support = _load('support', Path(__file__).with_name('compiled_mobile_tree_construction.py'))
        imported = perf_counter()
        reserve = min(1., .05*timeout)
        meter = support._Meter(absolute-reserve)
        meter.seconds['support_import'] += imported-began
        info.update(started=began, deadline=absolute, search_deadline=meter.deadline,
                    final_reserve_seconds=reserve)
        meter.clock()
        engine = _Engine(source, target, seed, meter, began, connected_only, support)
        info['stopped_by'] = engine.run()
    except Exception as exc:
        if support is not None and isinstance(exc, support._Stop):
            info.update(stopped_by='search_deadline', interrupted_stage=str(exc))
        else:
            info.update(stopped_by='error', error=repr(exc))
    if meter is not None:
        meter.deadline = absolute
        # Preserve already-observed failure evidence even if finalization is late.
        # This is reporting only; no new search or certificate is attempted here.
        if engine is not None:
            info.update(initial=engine.initial, final=engine.snapshot(), first_valid=engine.first_valid,
                        quality_progress=engine.events, stats=dict(engine.stats), receipts=engine.receipts,
                        sweeps=engine.sweeps, traces=engine.traces, last_trace=engine.last_trace,
                        detailed_traces_omitted=max(0, len(engine.receipts)-16),
                        initialization_order=[engine.vlabels[u] for u in engine.order],
                        private_final=engine.mapping(engine.state) if engine.state is not None else None,
                        distance_cache_entries=len(engine.arrays.fields))
        try:
            with meter.phase('finalization'):
                if engine is not None:
                    if info['error'] is None and engine.incumbent is not None:
                        output = engine.certify(engine.incumbent)
                        meter.clock(); status = 'SUCCESS'
                meter.clock()
        except Exception as exc:
            status, output = 'FAILURE', {}
            if support is not None and isinstance(exc, support._Stop):
                info['finalization_stop'] = str(exc)
            else:
                info['finalization_error'] = repr(exc)
        meter.switch('administration')
        info.update(work=meter.total, stage_wall=dict(meter.seconds), stage_units=dict(meter.units),
                    operation_counts=dict(meter.kinds))
    returned = perf_counter()
    if returned >= absolute:
        status, output = 'TIMEOUT', {}
    if info['error'] is not None:
        output = {}; status = 'FAILURE' if returned < absolute else 'TIMEOUT'
    info.update(returned=returned, wall=returned-began, cpu=process_time()-cpu_began,
                deadline=absolute, deadline_overrun=max(0., returned-absolute))
    return dict(status=status, embedding=output if status == 'SUCCESS' else {}, diag=info)


def connected_embed(source, target, *, timeout=60., deadline=None, seed=0):
    return ownership_embed(source, target, timeout=timeout, deadline=deadline,
                           seed=seed, connected_only=True)
