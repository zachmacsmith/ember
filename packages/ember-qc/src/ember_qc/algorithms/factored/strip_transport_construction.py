"""B031: valid-prefix construction with finite vacant-strip transport on Z12.

See b_031_local_strip_transport_design.md and b_031_implementation_contract.md.
Only the B028 meter/adjacency reader and original validator are reused. No other
constructor, embedding solver, saved embedding or source-family rule is used.
"""
from collections import Counter, deque
import importlib.util
from math import isfinite
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


class _InputError(ValueError):
    pass


def _coord(q):
    q, z = divmod(q, 12)
    q, j = divmod(q, 2)
    q, k = divmod(q, 4)
    u, w = divmod(q, 25)
    return u, w, k, j, z


def _linear(c):
    u, w, k, j, z = c
    if not (u in (0, 1) and 0 <= w <= 24 and 0 <= k < 4 and
            j in (0, 1) and 0 <= z < 12):
        raise ValueError('strip image outside original Z12')
    return (((u*25+w)*4+k)*2+j)*12+z


def _orient(c, direction, inverse=False):
    """P = Rx^reflect S^swap; inverse reverses this order."""
    u, w, k, j, z = c
    swap, reflect = divmod(direction, 2)
    if swap and not inverse:
        u = 1-u
    if reflect:
        if u == 0:
            w = 24-w
        else:
            j, z = 1-j, 11-z
    if swap and inverse:
        u = 1-u
    return u, w, k, j, z


def _moved(c, A, B):
    u, w, k, j, z = c
    return 2*A <= w < 2*B if u == 0 else A <= z < B


def _shift(c, A, B):
    u, w, k, j, z = c
    if _moved(c, A, B):
        if u == 0:
            w += 2
        else:
            z += 1
    return u, w, k, j, z


class _State:
    """Private immutable-by-convention value; callers never edit its containers."""
    def __init__(self, chains, labels):
        self.chains, self.labels = tuple(chains), tuple(labels)
        self.introduced = frozenset(u for u, c in enumerate(self.chains) if c)
        self.Q = sum(map(len, self.chains))


class _Transaction:
    def __init__(self, state, vertex, root, origin, bridge_Q, entry_Q, cut=None):
        self.state, self.vertex, self.root = state, vertex, root
        self.origin, self.bridge_Q, self.entry_Q, self.cut = origin, bridge_Q, entry_Q, cut

    def scalar(self):
        return dict(vertex_index=self.vertex, root=self.root, origin=self.origin,
                    bridge_Q=self.bridge_Q, birth_Q=self.state.Q-self.entry_Q-self.bridge_Q,
                    total_added_Q=self.state.Q-self.entry_Q, Q=self.state.Q,
                    introduced=len(self.state.introduced), cut=self.cut)

    def key(self, rank):
        return (self.state.Q, *(self.cut if self.cut is not None else (-1, -1, -1)), rank[self.root])


class _Engine:
    def __init__(self, source, target, seed, meter, began, ordinary_only, support):
        self.m, self.began, self.ordinary_only = meter, began, ordinary_only
        self.stop_type = support._Stop
        self.stats, self.births, self.transports, self.recoveries = Counter(), [], [], []
        self.prefix_progress, self.private_progress, self.events = [], [], []
        self.first_valid = self.pending = self.full_output = None
        self.state = self.initial = self.cert_target = self.validator = None
        rng = Random(seed)
        with meter.phase('normalization'):
            try:
                self.original_G = support._adjacency(source, meter)
                self.H = support._adjacency(target, meter)
            except ValueError as exc:
                raise _InputError(str(exc)) from exc
            if set(self.H) != set(range(4800)):
                raise _InputError('B031 requires original linear ideal-Z12 target IDs')
            self.vlabels = tuple(self.original_G)
            vindex = {v: i for i, v in enumerate(self.vlabels)}
            self.G = tuple(frozenset(vindex[v] for v in self.original_G[u]) for u in self.vlabels)
            self.n = len(self.G)
            source_order, self.qorder = list(range(self.n)), list(range(4800))
            rng.shuffle(source_order); rng.shuffle(self.qorder)
            self.srank = {u: i for i, u in enumerate(source_order)}
            self.rank = {q: i for i, q in enumerate(self.qorder)}
            self.adj = tuple(tuple(sorted(self.H[q], key=self.rank.__getitem__)) for q in range(4800))
            self.order = self.source_order()
            meter.clock()
        with meter.phase('geometry_setup'):
            self.coords = tuple(_coord(q) for q in range(4800))
            self.oriented = tuple(tuple(_orient(c, d) for c in self.coords) for d in range(4))
            meter.step('coordinate_setup', 4800*5)
            def central(q):
                u, w, k, j, z = self.coords[q]
                x, y = (w, 2*z+j+.5) if u == 0 else (2*z+j+.5, w)
                return ((x-12)**2+(y-12)**2, self.rank[q])
            self.center = min(self.qorder, key=central)
            # Full target distance fixes component-root ties without an active-area restriction.
            distances, queue = [-1]*4800, deque([self.center])
            distances[self.center] = 0
            while queue:
                q = queue.popleft()
                for r in self.adj[q]:
                    meter.step('center_distance_arc')
                    if distances[r] < 0:
                        distances[r] = distances[q]+1; queue.append(r)
            self.component_order = tuple(sorted(self.qorder, key=lambda q:
                (distances[q] if distances[q] >= 0 else 4801, self.rank[q])))
            self.state = _State([frozenset() for _ in self.G], [-1]*4800)
            self.initial = dict(self.snapshot(), target_center=self.center)
            meter.clock()

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

    def snapshot(self):
        if self.state is None:
            return None
        return dict(introduced=len(self.state.introduced), Q=self.state.Q,
                    complete=len(self.state.introduced) == self.n)

    def mapping(self, state):
        return {self.vlabels[u]: sorted(state.chains[u]) for u in sorted(state.introduced)}

    def certify(self, state):
        with self.m.phase('certification'):
            if self.validator is None:
                self.validator = _load('validator', Path(__file__).resolve().parents[2]/'validation.py')
                import networkx as nx
                self.nx = nx
                self.cert_target = nx.Graph()
                self.cert_target.add_nodes_from(self.H)
                self.cert_target.add_edges_from((q, r) for q in self.H for r in self.H[q] if q < r)
                self.m.step('certificate_target_arc', sum(map(len, self.H.values())))
                self.m.clock()
            original = self.nx.Graph()
            original.add_nodes_from(self.vlabels[u] for u in state.introduced)
            original.add_edges_from((self.vlabels[u], self.vlabels[v]) for u in state.introduced
                                    for v in self.G[u] if v in state.introduced and u < v)
            raw = self.mapping(state)
            self.m.step('certificate_source_and_chain', state.Q+len(state.introduced))
            checked = self.validator.validate_layer1(raw, original, self.cert_target)
            self.m.clock()
            if not checked.passed:
                raise RuntimeError('B031 private certificate failed: '+str(checked))
            return raw

    def witnesses(self, state):
        """A fresh certificate R, not permanent endpoint constraints."""
        with self.m.phase('witnesses'):
            edges, contacts = [], {}
            for u in sorted(state.introduced, key=self.srank.__getitem__):
                chain = state.chains[u]
                root = min(chain, key=self.rank.__getitem__)
                seen, queue = {root}, deque([root])
                while queue:
                    q = queue.popleft()
                    for r in self.adj[q]:
                        self.m.step('witness_arc')
                        v = state.labels[r]
                        if v == u and r not in seen:
                            seen.add(r); queue.append(r); edges.append((q, r))
                        elif v >= 0 and v != u and v in self.G[u]:
                            edge = (min(u, v), max(u, v))
                            if edge not in contacts:
                                contacts[edge] = (q, r)
                if len(seen) != len(chain):
                    raise RuntimeError('disconnected public prefix')
            expected = sum(v in state.introduced and u < v for u in state.introduced for v in self.G[u])
            if len(contacts) != expected:
                raise RuntimeError('missing public source contact')
            edges.extend(contacts[e] for e in sorted(contacts))
            self.m.clock()
            return tuple(edges)

    def transport(self, state, R, direction, A, B):
        """Prepare one geometry proposal; actual adjacency is the authority."""
        with self.m.phase('transport_geometry'):
            coords = self.oriented[direction]
            image, shifted = {}, set()
            for u in state.introduced:
                for q in state.chains[u]:
                    self.m.step('transport_site')
                    c = coords[q]
                    if (c[0] == 0 and c[1] in (2*B, 2*B+1)) or (c[0] == 1 and c[4] == B):
                        return None, 'occupied_destination_band', None
                    if _moved(c, A, B):
                        shifted.add(q)
                    image[q] = _linear(_orient(_shift(c, A, B), direction, inverse=True))
            if not shifted:
                return None, 'identical_map', 0
            bridge = {}
            for q, r in R:
                self.m.step('transport_required_edge')
                if (q in shifted) == (r in shifted):
                    continue
                left, right = (r, q) if q in shifted else (q, r)
                c = coords[left]
                if c[0] != 1 or c[4] != A-1 or right not in shifted:
                    return None, 'unexpected_cut_edge', None
                b = _linear(_orient((c[0], c[1], c[2], c[3], A), direction, inverse=True))
                bridge[left] = b
            chains = [set() for _ in self.G]
            labels = [-1]*4800
            for q, r in image.items():
                self.m.step('transport_copy_site')
                if labels[r] >= 0:
                    return None, 'image_collision', None
                u = state.labels[q]; labels[r] = u; chains[u].add(r)
            for q, b in bridge.items():
                self.m.step('transport_bridge')
                if labels[b] >= 0 or b not in self.H[image[q]]:
                    return None, 'bridge_collision_or_missing_edge', None
                u = state.labels[q]; labels[b] = u; chains[u].add(b)
            for q, r in R:
                self.m.step('transport_required_image')
                fq, fr = image[q], image[r]
                if fr in self.H[fq]:
                    continue
                if q in bridge and fr in self.H[bridge[q]]:
                    continue
                if r in bridge and fq in self.H[bridge[r]]:
                    continue
                return None, 'missing_required_image_coupler', None
            result = _State([frozenset(c) for c in chains], labels)
            if result.Q != state.Q+len(bridge):
                raise RuntimeError('transport Q accounting disagreement')
            self.m.clock()
            return result, 'prepared', len(bridge)

    def prepare_birth(self, state, vertex, sites, root, origin, bridge_Q, entry_Q, cut):
        with self.m.phase('birth_copy'):
            if state.chains[vertex] or not sites:
                raise RuntimeError('invalid private birth domain')
            labels, chains = list(state.labels), list(state.chains)
            self.m.step('birth_copy_item', len(labels)+len(chains))
            for q in sites:
                self.m.step('birth_site')
                if labels[q] >= 0:
                    raise RuntimeError('private birth overlaps an owner')
                labels[q] = vertex
            chains[vertex] = frozenset(sites)
            candidate = _Transaction(_State(chains, labels), vertex, root, origin, bridge_Q, entry_Q, cut)
            self.m.clock()
            return candidate

    def retain(self, candidate):
        if self.pending is None or candidate.key(self.rank) < self.pending.key(self.rank):
            row = candidate.scalar()
            row.update(vertex=self.vlabels[candidate.vertex], elapsed=perf_counter()-self.began, certified=False,
                       full_source=len(candidate.state.introduced) == self.n,
                       selection_key=candidate.key(self.rank))
            self.m.clock()
            self.pending = candidate
            self.private_progress.append(row)
            self.stats['private_incumbent_improvements'] += 1

    def birth(self, state, vertex, *, origin='ordinary', bridge_Q=0, entry_Q=None, cut=None):
        """Min union of fixed BFS paths. None does not imply no Steiner tree."""
        if entry_Q is None:
            entry_Q = state.Q
        started, cpu = perf_counter(), process_time()
        row = dict(vertex=self.vlabels[vertex], origin=origin, cut=cut, entry_Q=entry_Q,
                   base_Q=state.Q, bridge_Q=bridge_Q, complete=False,
                   reachable_roots=0, materialized_roots=0, pruned_roots=0,
                   fields=0, best_birth_Q=None)
        try:
            neighbors = sorted(self.G[vertex] & state.introduced, key=self.srank.__getitem__)
            row['introduced_neighbors'] = len(neighbors)
            if not neighbors:
                with self.m.phase('component_birth'):
                    root = next((q for q in self.component_order if state.labels[q] < 0), None)
                    self.m.clock()
                if root is not None:
                    candidate = self.prepare_birth(state, vertex, {root}, root, origin, bridge_Q, entry_Q, cut)
                    self.retain(candidate)
                    row.update(reachable_roots=1, materialized_roots=1, best_birth_Q=1)
                row.update(complete=True, reason='component_root' if root is not None else 'no_free_site')
                return
            fields = []
            with self.m.phase('birth_bfs'):
                for u in neighbors:
                    parent = [-1]*4800
                    terminals = sorted(state.chains[u], key=self.rank.__getitem__)
                    queue = deque(terminals)
                    for q in terminals:
                        parent[q] = q
                    while queue:
                        q = queue.popleft()
                        for r in self.adj[q]:
                            self.m.step('birth_bfs_arc')
                            if state.labels[r] < 0 and parent[r] < 0:
                                parent[r] = q; queue.append(r)
                    fields.append(parent); row['fields'] += 1
                    self.m.clock()
            with self.m.phase('birth_union'):
                for root in self.qorder:
                    self.m.step('birth_root')
                    if state.labels[root] >= 0 or any(p[root] < 0 for p in fields):
                        continue
                    row['reachable_roots'] += 1
                    limit = None if self.pending is None else self.pending.state.Q-state.Q
                    tie = (*(cut if cut is not None else (-1, -1, -1)), self.rank[root])
                    prune_equal = self.pending is not None and tie >= self.pending.key(self.rank)[1:]
                    if limit is not None and (limit < 1 or (limit == 1 and prune_equal)):
                        row['pruned_roots'] += 1
                        continue
                    union, pruned = set(), False
                    for parent in fields:
                        q = root
                        while state.labels[q] < 0:
                            self.m.step('birth_union_site')
                            union.add(q)
                            if limit is not None and (len(union) > limit or
                                                      (len(union) == limit and prune_equal)):
                                pruned = True; break
                            q = parent[q]
                            if q < 0:
                                raise RuntimeError('canonical BFS path lost its terminal')
                        if pruned:
                            break
                    if pruned:
                        row['pruned_roots'] += 1
                        continue
                    row['materialized_roots'] += 1
                    candidate = self.prepare_birth(state, vertex, union, root, origin, bridge_Q, entry_Q, cut)
                    self.retain(candidate)
                    if row['best_birth_Q'] is None or len(union) < row['best_birth_Q']:
                        row['best_birth_Q'] = len(union)
                    self.m.clock()
            row.update(complete=True, reason='reachable' if row['reachable_roots'] else 'no_clean_common_root')
        finally:
            row.update(wall=perf_counter()-started, cpu=process_time()-cpu,
                       elapsed=perf_counter()-self.began)
            if not row['complete']:
                exc = sys.exc_info()[1]
                row['interrupted_stage' if isinstance(exc, self.stop_type) else 'error'] = str(exc)
            self.births.append(row)
            self.stats['birth_queries'] += 1

    def recover(self, vertex):
        row = dict(vertex=self.vlabels[vertex], started=perf_counter()-self.began,
                   enumeration_complete=False, prepared_maps=None, first_query_elapsed=None,
                   complete=False)
        self.recoveries.append(row)
        with self.m.phase('transport_control'):
            try:
                answer = self._recover(vertex, row)
                row['complete'] = True
                return answer
            finally:
                row['elapsed'] = perf_counter()-self.began
                if not row['complete']:
                    exc = sys.exc_info()[1]
                    row['interrupted_stage' if isinstance(exc, self.stop_type) else 'error'] = str(exc)

    def _recover(self, vertex, recovery):
        entry = self.state
        R, proposals = self.witnesses(entry), []
        # Every finite geometry proposal gets a scalar receipt, including rejections.
        for direction in range(4):
            for A in range(11):
                for B in range(A+1, 12):
                    started, cpu = perf_counter(), process_time()
                    row = dict(vertex=self.vlabels[vertex], direction=direction, A=A, B=B,
                               complete=False, bridge_Q=None, query=None)
                    try:
                        candidate, reason, added = self.transport(entry, R, direction, A, B)
                        row.update(complete=True, geometry=reason, bridge_Q=added)
                        self.stats['transport_'+reason] += 1
                        if candidate is not None:
                            proposals.append((added, direction, A, B, candidate, row))
                    finally:
                        row.update(geometry_wall=perf_counter()-started, geometry_cpu=process_time()-cpu)
                        if not row['complete']:
                            exc = sys.exc_info()[1]
                            row['interrupted_stage' if isinstance(exc, self.stop_type) else 'error'] = str(exc)
                        self.transports.append(row)
        with self.m.phase('transport_order'):
            proposals.sort(key=lambda p: p[:4])
            self.m.step('transport_sort_item', len(proposals)); self.m.clock()
        recovery.update(enumeration_complete=True, prepared_maps=len(proposals),
                        enumeration_finished=perf_counter()-self.began)
        for added, direction, A, B, state, row in proposals:
            self.m.clock()
            lower_key = (entry.Q+added+1, direction, A, B, 0)
            if self.pending is not None and lower_key >= self.pending.key(self.rank):
                row['query'] = 'local_Q_bound'
                self.stats['transport_local_Q_bound'] += 1
                continue
            row['query'] = 'started'
            if recovery['first_query_elapsed'] is None:
                recovery['first_query_elapsed'] = perf_counter()-self.began
            self.birth(state, vertex, origin='transport', bridge_Q=added,
                       entry_Q=entry.Q, cut=[direction, A, B])
            row['query'] = self.births[-1]['reason']
            self.stats['transport_birth_queries'] += 1
        self.m.clock()
        return bool(proposals)

    def publish(self, transaction, *, salvage=False):
        raw = self.certify(transaction.state)
        row = transaction.scalar()
        row.update(vertex=self.vlabels[transaction.vertex], elapsed=perf_counter()-self.began,
                   salvage=salvage, certified=True)
        complete = len(transaction.state.introduced) == self.n
        event = dict(elapsed=row['elapsed'], Q=transaction.state.Q,
                     ACL=transaction.state.Q/self.n if self.n else None, salvage=salvage)
        self.m.clock()
        # No fallible search/certificate operation follows this atomic publication.
        self.state = transaction.state
        self.pending = None
        self.prefix_progress.append(row)
        self.stats['published_births'] += 1
        if transaction.origin == 'transport':
            self.stats['published_transports'] += 1
        if complete:
            self.full_output = raw
            self.first_valid = event
            self.events.append(event)

    def run(self):
        if self.n > 4800:
            return 'more_source_vertices_than_target'
        if not self.n:
            raw = self.certify(self.state)
            self.m.clock(); self.full_output = raw
            self.first_valid = dict(elapsed=perf_counter()-self.began, Q=0, ACL=None, salvage=False)
            self.events.append(self.first_valid)
            return 'complete_empty_source'
        for vertex in self.order:
            self.m.clock()
            if self.pending is not None:
                raise RuntimeError('pending birth crossed a publication boundary')
            self.birth(self.state, vertex)
            if self.pending is None:
                self.stats['blocked_births'] += 1
                if self.ordinary_only:
                    return 'ordinary_birth_blocked'
                feasible = self.recover(vertex)
                if self.pending is None:
                    return 'transport_births_blocked' if feasible else 'no_feasible_nonidentical_transport'
            self.publish(self.pending)
        return 'complete'


def strip_embed(source, target, *, timeout=60., deadline=None, seed=0, ordinary_only=False):
    began, cpu_began = perf_counter(), process_time()
    support = meter = engine = None
    absolute = began
    info = dict(algorithm='strip-transport', version='B031', seed=seed, ordinary_only=ordinary_only,
                error=None, fatal=False, stopped_by=None, work_limit=None, query_limit=None,
                geometry_pairs_per_blocked_birth=264, root_policy='minimum_canonical_BFS_path_union',
                transport_trigger='no_clean_common_root')
    output, status = {}, 'FAILURE'
    try:
        if type(timeout) not in (float, int) or not isfinite(timeout) or timeout <= 0:
            raise _InputError('positive finite timeout required')
        if type(seed) is not int or type(ordinary_only) is not bool:
            raise _InputError('integer seed and boolean ablation required')
        absolute = began+timeout
        if deadline is not None:
            if type(deadline) not in (float, int) or not isfinite(deadline):
                raise _InputError('finite absolute deadline required')
            absolute = min(absolute, deadline)
        support = _load('support', Path(__file__).with_name('compiled_mobile_tree_construction.py'))
        imported = perf_counter()
        reserve = min(1., .05*timeout)
        meter = support._Meter(absolute-reserve)
        meter.seconds['support_import'] += imported-began
        info.update(started=began, deadline=absolute, search_deadline=meter.deadline,
                    final_reserve_seconds=reserve)
        meter.clock()
        engine = _Engine(source, target, seed, meter, began, ordinary_only, support)
        info['stopped_by'] = engine.run()
    except Exception as exc:
        if support is not None and isinstance(exc, support._Stop):
            info.update(stopped_by='search_deadline', interrupted_stage=str(exc))
        elif isinstance(exc, _InputError):
            info.update(stopped_by='input_error', error=repr(exc))
        else:
            info.update(stopped_by='error', error=repr(exc), fatal=True)
    if meter is not None:
        meter.deadline = absolute
        try:
            with meter.phase('finalization'):
                if engine is not None and info['error'] is None:
                    if (engine.full_output is None and engine.pending is not None and
                            len(engine.pending.state.introduced) == engine.n):
                        engine.publish(engine.pending, salvage=True)
                    if engine.full_output is not None:
                        output = {v: list(c) for v, c in engine.full_output.items()}
                        meter.step('output_copy_site', sum(map(len, output.values())))
                        meter.clock(); status = 'SUCCESS'
        except Exception as exc:
            output, status = {}, 'FAILURE'
            if isinstance(exc, support._Stop):
                info['finalization_stop'] = str(exc)
            else:
                info.update(finalization_error=repr(exc), fatal=True)
        # Evidence is preserved even after a deadline; late reporting cannot earn credit.
        try:
            if engine is not None:
                info.update(initial=engine.initial, final=engine.snapshot(), first_valid=engine.first_valid,
                            quality_progress=engine.events, prefix_progress=engine.prefix_progress,
                            private_progress=engine.private_progress, stats=dict(engine.stats),
                            births=engine.births, transports=engine.transports, recoveries=engine.recoveries,
                            pending=None if engine.pending is None else dict(engine.pending.scalar(),
                                vertex=engine.vlabels[engine.pending.vertex]),
                            initialization_order=[engine.vlabels[u] for u in engine.order],
                            private_final=engine.mapping(engine.state))
            meter.switch('administration')
            info.update(work=meter.total, stage_wall=dict(meter.seconds), stage_units=dict(meter.units),
                        operation_counts=dict(meter.kinds))
        except Exception as exc:
            info.update(reporting_error=repr(exc), fatal=True)
    returned = perf_counter()
    if returned >= absolute:
        output, status = {}, 'TIMEOUT'
    if info['stopped_by'] == 'input_error':
        output, status = {}, 'FAILURE'
    if info['fatal']:
        output, status = {}, 'ERROR'
    info.update(returned=returned, wall=returned-began, cpu=process_time()-cpu_began,
                deadline=absolute, deadline_overrun=max(0., returned-absolute))
    return dict(status=status, embedding=output if status == 'SUCCESS' else {}, diag=info,
                fatal=info['fatal'],
                error=(info['error'] or info.get('finalization_error') or info.get('reporting_error'))
                      if info['fatal'] else None)


def ordinary_embed(source, target, *, timeout=60., deadline=None, seed=0):
    return strip_embed(source, target, timeout=timeout, deadline=deadline,
                       seed=seed, ordinary_only=True)
