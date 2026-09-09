"""C011: C010 placement with wall-limited computation allocation.

Standalone heuristic: no external solver, constructor, chain-domain library,
systematic assignment search, or architecture-specific placement rule.
"""
from collections import Counter
from contextlib import contextmanager
import math
import random
import time


class _Stop(Exception):
    pass


class _InputError(ValueError):
    pass


class _Budget:
    def __init__(self, deadline, *, limit=20_000_000, clock=None):
        self.deadline, self.limit = deadline, limit
        self.clock = clock or time.perf_counter
        self.units, self.next_check = 0, 0
        self.work, self.stage_wall = Counter(), Counter()
        self.denied = None
        self.first_crossings = {}
        self.started = self.clock()

    def check(self):
        if self.clock() >= self.deadline:
            raise _Stop('deadline')

    def tick(self, name, amount=1):
        if self.units >= self.next_check or amount >= 256:
            self.check()
            self.next_check = self.units + 256
        before = self.units
        self.units += amount
        self.work[name] += amount
        if before <= 20_000_000:
            for label, threshold in (('search_reference_19M', 19_000_000), ('cumulative_20M', 20_000_000)):
                if before <= threshold < self.units:
                    self.first_crossings[label] = dict(threshold=threshold, name=name,
                        units_before=before, requested=amount, units_after=self.units,
                        phase='search' if self.limit == 19_000_000 else 'final',
                        elapsed_from_budget_start=self.clock()-self.started)

    def ordered(self, values, *, key=None, name='sort'):
        self.tick(name, len(values) * max(1, math.ceil(math.log2(len(values)+1))))
        answer = sorted(values, key=key)
        self.check()
        return answer

    @contextmanager
    def stage(self, name):
        start = self.clock()
        try:
            self.check()
            yield
            self.check()
        finally:
            self.stage_wall[name] += self.clock() - start


def _graph(graph, budget):
    if graph.is_directed() or graph.is_multigraph():
        raise _InputError('simple undirected graphs required')
    labels = list(graph.nodes)
    budget.tick('input_nodes', len(labels))
    ranks = {u: i for i, u in enumerate(labels)}
    adj = [set() for _ in labels]
    for u, v in graph.edges:
        budget.tick('input_edges')
        a, b = ranks[u], ranks[v]
        if a == b:
            raise _InputError('self-loops unsupported')
        adj[a].add(b)
        adj[b].add(a)
    return labels, tuple(tuple(budget.ordered(list(ns), name='input_sort')) for ns in adj)


class _State:
    def __init__(self, src, target, budget, seed=0):
        self.src, self.target, self.b = src, target, budget
        self.words = max(1, (len(target)+63)//64)
        self.owners = list(range(len(src)))
        self.aux = [{} for _ in src]
        self.original_edges = []
        for u, ns in enumerate(src):
            for v in ns:
                budget.tick('aux_input_incidence')
                if u < v:
                    eid = len(self.original_edges)
                    self.original_edges.append((u, v))
                    self.aux[u][v] = self.aux[v][u] = eid
        self.placement, self.timestamps = {}, {}
        self.used = self.serial = self.generation = 0
        self.internal_count = 0
        self.order = list(range(len(target)))
        budget.tick('target_permutation', len(target))
        random.Random(seed).shuffle(self.order)
        self.rank = [0]*len(target)
        for i, q in enumerate(self.order):
            self.rank[q] = i
        self.target_bits = [self.mask(ns, 'target_mask_union') for ns in target]
        self.maximum_degree = max(map(len, target), default=0)
        buckets = [0]*(self.maximum_degree+1)
        for q, ns in enumerate(target):
            budget.tick('target_degree_records')
            self.bitwork('degree_bucket_union')
            buckets[len(ns)] |= 1 << q
        self.degree_bits = [0]*len(buckets)
        mask = 0
        for degree in range(self.maximum_degree, -1, -1):
            self.bitwork('degree_cumulative_union')
            mask |= buckets[degree]
            self.degree_bits[degree] = mask
        budget.check()

    def bitwork(self, name, count=1):
        self.b.tick(name, count*self.words)

    def mask(self, values, name):
        result = 0
        for q in values:
            self.b.tick('mask_members')
            self.bitwork(name)
            result |= 1 << q
        return result

    def domains(self, x, placement=None, used=None, extra=None):
        p = self.placement if placement is None else placement
        occupied = self.used if used is None else used
        if extra is not None:
            self.bitwork('prospective_occupied_union')
            occupied |= 1 << extra[1]
        self.b.tick('domain_clones')
        degree = len(self.aux[x])
        g = self.degree_bits[degree] if degree <= self.maximum_degree else 0
        self.bitwork('domain_copy')
        a, placed_neighbors = g, 0
        for y in self.aux[x]:
            self.b.tick('domain_aux_incidence')
            q = extra[1] if extra is not None and y == extra[0] else p.get(y)
            if q is not None:
                placed_neighbors += 1
                self.bitwork('domain_neighbor_intersection')
                a &= self.target_bits[q]
        self.bitwork('domain_occupied_difference', 2)
        d = a & ~occupied
        self.bitwork('domain_count')
        return g, a, d, d.bit_count(), placed_neighbors

    def select(self, candidates=None, placement=None, used=None):
        p = self.placement if placement is None else placement
        best = None
        for x in range(len(self.owners)) if candidates is None else candidates:
            self.b.tick('selection_clone_records')
            if x in p:
                continue
            domains = self.domains(x, p, used)
            key = (-domains[4], domains[3], -len(self.aux[x]), self.owners[x], x)
            if best is None or key < best[0]:
                best = key, x, domains
        self.b.check()
        return None if best is None else best[1:]

    def choose(self, x, domains, row, placement=None, used=None):
        p = self.placement if placement is None else placement
        occupied = self.used if used is None else used
        row.update(clone=x, owner=self.owners[x], admissible=domains[3],
                   prefix=[], ranking_complete=False, selected=None)
        if not domains[2]:
            row['ranking_complete'] = True
            return None
        best = None
        for q in self.order:
            self.b.tick('candidate_order_scan')
            if not (domains[2] >> q) & 1:
                continue
            supports = []
            for y in self.aux[x]:
                self.b.tick('support_aux_incidence')
                if y not in p:
                    supports.append(self.domains(y, p, occupied, (x, q))[3])
            minimum, total = min(supports, default=0), sum(supports)
            self.b.tick('scored_candidate_record')
            row['prefix'].append([q, minimum, total])
            key = (minimum, total, -self.rank[q])
            if best is None or key > best[0]:
                best = key, q
            if len(row['prefix']) == 32:
                break
        self.b.check()
        row['ranking_complete'], row['selected'] = True, best[1]
        return best[1]

    def publish_single(self, x, q):
        self.b.tick('placement_copy_records', len(self.placement)+len(self.timestamps))
        p, ts = dict(self.placement), dict(self.timestamps)
        p[x], ts[x] = q, self.serial+1
        self.bitwork('placement_occupied_union')
        used = self.used | (1 << q)
        self.b.check()
        self.placement, self.timestamps, self.used = p, ts, used
        self.serial += 1
        self.generation += 1

    def conflict_pool(self, x, a, row):
        neighbors = []
        for y in self.aux[x]:
            self.b.tick('conflict_neighbor_records')
            if y in self.placement:
                neighbors.append(y)
        key = lambda y: (-self.timestamps[y], y)
        neighbors = self.b.ordered(neighbors, key=key, name='conflict_neighbor_sort')
        occupants = []
        for y, q in self.placement.items():
            self.b.tick('conflict_occupant_records')
            if (a >> q) & 1 and y not in self.aux[x]:
                occupants.append(y)
        occupants = self.b.ordered(occupants, key=key, name='conflict_occupant_sort')
        row['pool'] = neighbors + occupants
        return row['pool']

    def certify_block(self, changed, p):
        # Outside placements are unchanged. Check every changed incidence and
        # injectivity against the whole view, without rescanning target edges.
        self.b.tick('block_occupancy_records', len(p))
        if len(set(p.values())) != len(p):
            return False
        for x in changed:
            self.b.tick('block_clone_records')
            if x not in p or not 0 <= p[x] < len(self.target):
                return False
            for y in self.aux[x]:
                self.b.tick('block_incidence_checks')
                if y in p and not ((self.target_bits[p[x]] >> p[y]) & 1):
                    return False
        self.b.check()
        return True

    def revise(self, x, a, record):
        pool = self.conflict_pool(x, a, record)
        record['attempts'] = []
        for i, pivot in enumerate(pool[:4]):
            block = [pool[(i+j) % len(pool)] for j in range(min(4, len(pool)))]
            row = dict(pivot=pivot, released=block, choices=[], committed=False,
                       stage='copy', status='interrupted', work_start=self.b.units)
            record['attempts'].append(row)
            start = self.b.clock()
            try:
                self.b.tick('revision_copy_records', len(self.placement)+len(self.timestamps))
                p, ts = dict(self.placement), dict(self.timestamps)
                used = self.used
                for y in block:
                    self.b.tick('revision_release_records')
                    self.bitwork('revision_release_difference', 2)
                    used &= ~(1 << p.pop(y))
                    ts.pop(y)
                todo, serial = [x]+block, self.serial
                row['stage'] = 'placement'
                while todo:
                    if x in todo:
                        y, d = x, self.domains(x, p, used)
                    elif pivot in todo:
                        y, d = pivot, self.domains(pivot, p, used)
                    else:
                        y, d = self.select(todo, p, used)
                    choice = {}
                    row['choices'].append(choice)
                    q = self.choose(y, d, choice, p, used)
                    if q is None:
                        row.update(status='no_admissible_site', failed_clone=y)
                        break
                    self.b.tick('revision_private_placement')
                    self.bitwork('revision_occupied_union')
                    used |= 1 << q
                    p[y], ts[y] = q, serial+1
                    serial += 1
                    todo.remove(y)
                if todo:
                    continue
                row['stage'] = 'certificate'
                if not self.certify_block([x]+block, p):
                    raise ValueError('private revision certificate failed')
                self.b.check()
                self.placement, self.timestamps, self.used = p, ts, used
                self.serial, self.generation = serial, self.generation+1
                row.update(committed=True, status='committed', stage='published')
                return True
            finally:
                row.update(work_end=self.b.units, wall=self.b.clock()-start)
        return False

    def split(self, x, record):
        row = dict(clone=x, owner=self.owners[x], degree=len(self.aux[x]),
                   committed=False, status='interrupted', supports=[], partition=[],
                   work_start=self.b.units, stage='eligibility')
        record['split'] = row
        start = self.b.clock()
        try:
            if x in self.placement:
                raise ValueError('only an unplaced clone may split')
            if len(self.aux[x]) < 2 or len(self.owners) >= len(self.target):
                row['status'] = 'ineligible'
                return False
            row['stage'] = 'support'
            degree = len(self.aux[x])
            g = self.degree_bits[degree] if degree <= self.maximum_degree else 0
            self.bitwork('split_unoccupied_difference', 2)
            base = g & ~self.used
            incidences = []
            for y, eid in self.aux[x].items():
                self.b.tick('split_incidence_records')
                boundary = 0
                if base:
                    if y in self.placement:
                        self.bitwork('split_boundary_copy')
                        boundary = self.target_bits[self.placement[y]]
                    else:
                        bits = self.domains(y)[2]
                        for q in self.order:
                            self.b.tick('split_support_order_scan')
                            if (bits >> q) & 1:
                                self.bitwork('split_boundary_union')
                                boundary |= self.target_bits[q]
                self.bitwork('split_support_intersection_count', 2)
                support = (base & boundary).bit_count()
                row['supports'].append([eid, y, support])
                edge_rank = (0, eid) if eid >= 0 else (1, -eid)
                incidences.append((support, edge_rank, y, eid))
            incidences = self.b.ordered(incidences, name='split_incidence_sort')
            row['stage'] = 'copy'
            self.b.tick('split_graph_copy_records', len(self.aux)+len(self.owners))
            aux, owners = list(self.aux), list(self.owners)
            new = len(owners)
            owners.append(owners[x])
            aux[x] = {}
            aux.append({})
            for i, (_, _, y, eid) in enumerate(incidences):
                self.b.tick('split_incidence_assignment')
                destination = x if i % 2 == 0 else new
                row['partition'].append([eid, y, destination])
                aux[destination][y] = eid
                if destination == new:
                    self.b.tick('split_neighbor_copy_records', len(aux[y]))
                    ns = dict(aux[y])
                    del ns[x]
                    ns[new] = eid
                    aux[y] = ns
            internal = -(self.internal_count+1)
            self.b.tick('split_internal_records', 2)
            aux[x][new] = aux[new][x] = internal
            row.update(new_clone=new, new_degrees=[len(aux[x]), len(aux[new])],
                       internal_edge=internal)
            self.b.check()
            self.aux, self.owners = aux, owners
            self.internal_count += 1
            self.generation += 1
            row.update(committed=True, status='committed', stage='published')
            return True
        finally:
            row.update(work_end=self.b.units, wall=self.b.clock()-start)


def _run(state, diag):
    diag.setdefault('visits', [])
    while len(state.placement) < len(state.owners):
        row = dict(generation=state.generation, clone_count=len(state.owners),
                   placed=len(state.placement), stage='selection', committed=False,
                   work_start=state.b.units, status='interrupted')
        diag['visits'].append(row)
        start = state.b.clock()
        try:
            x, domains = state.select()
            row.update(clone=x, owner=state.owners[x], admissible=domains[3])
            if domains[2]:
                row['stage'] = 'ranking'
                row['choice'] = {}
                q = state.choose(x, domains, row['choice'])
                state.publish_single(x, q)
                row.update(status='placed', committed=True, stage='published')
            else:
                kind = 'degree' if not domains[0] else ('adjacency' if not domains[1] else 'occupancy')
                row.update(conflict=kind, stage='revision')
                if kind != 'degree' and state.revise(x, domains[1], row):
                    row.update(status='revised', committed=True, stage='published')
                    continue
                row['stage'] = 'split'
                if not state.split(x, row):
                    row.update(status='unresolved', stage='stopped')
                    return 'unresolved_conflict'
                row.update(status='split', committed=True, stage='published')
        finally:
            row.update(work_end=state.b.units, wall=state.b.clock()-start,
                       generation_after=state.generation)
    return 'complete_auxiliary_placement'


def _snapshot(state):
    b = state.b
    chains = [[] for _ in state.src]
    b.tick('snapshot_owner_records', len(state.owners))
    for x, q in state.placement.items():
        b.tick('snapshot_placement_records')
        chains[state.owners[x]].append(q)
    edges = []
    for x, ns in enumerate(state.aux):
        for y, eid in ns.items():
            b.tick('snapshot_aux_incidence')
            if x < y:
                edges.append([eid, x, y])
    snapshot = dict(owners=list(state.owners), auxiliary_edges=edges,
                    placements=[[x, q, state.timestamps[x]] for x, q in state.placement.items()],
                    generation=state.generation, clone_count=len(state.owners),
                    placed=len(state.placement), internal_edges=state.internal_count)
    b.check()
    return chains, snapshot


def _stats(chains, src, target, b):
    """Original-edge recount independent of clone constraints and domain masks."""
    if len(chains) != len(src):
        raise ValueError('wrong original source keys')
    owner, boundaries = {}, []
    connected, overlap = True, 0
    for u, chain in enumerate(chains):
        allowed = set()
        for q in chain:
            b.tick('final_membership_records')
            if type(q) is not int or not 0 <= q < len(target):
                raise ValueError('invalid target member')
            if q in allowed:
                raise ValueError('duplicate chain member')
            allowed.add(q)
            if q in owner:
                overlap += 1
            owner[q] = u
        boundary = set()
        for q in chain:
            for p in target[q]:
                b.tick('final_boundary_adjacency')
                boundary.add(p)
        boundaries.append(boundary)
        reached = set(chain[:1])
        queue = list(reached)
        for q in queue:
            for p in target[q]:
                b.tick('final_connectivity_adjacency')
                if p in allowed and p not in reached:
                    reached.add(p)
                    queue.append(p)
        connected &= bool(chain) and len(reached) == len(allowed)
    missing = []
    for u, ns in enumerate(src):
        for v in ns:
            if u < v:
                b.tick('final_original_edges')
                found = False
                for q in chains[v]:
                    b.tick('final_contact_memberships')
                    if q in boundaries[u]:
                        found = True
                        break
                if not found:
                    missing.append([u, v])
    b.check()
    return dict(valid=connected and not overlap and not missing,
                connected_nonempty=connected, overlap_excess=overlap,
                qubits=sum(map(len, chains)), missing=len(missing), missing_edges=missing)


def _materialize(chains, source_labels, target_labels, b):
    result = {}
    for u, chain in enumerate(chains):
        b.tick('output_records', len(chain)+1)
        result[source_labels[u]] = [target_labels[q] for q in chain]
    return result


def _exception(response, exc):
    expected = isinstance(exc, _InputError)
    response.update(status='FAILURE' if expected else 'ERROR', embedding={},
                    error=f'{type(exc).__name__}: {exc}')
    response['diag'].update(fatal_error=not expected,
                            exception=dict(type=type(exc).__name__, message=str(exc),
                                           expected_input=expected))


def _finish(response, state, source_labels, target_labels, deadline):
    b = state.b
    response['embedding'] = {}
    if response['status'] == 'SUCCESS':
        response['status'] = 'FAILURE'
    try:
        with b.stage('final_validation_output'):
            chains, snapshot = _snapshot(state)
            response['diag']['state'] = snapshot
            response['diag']['final_chains'] = chains
            stats = _stats(chains, state.src, state.target, b)
            response['diag']['final'] = stats
            raw = _materialize(chains, source_labels, target_labels, b)
            response['diagnostic_embedding'] = raw
            complete = len(state.placement) == len(state.owners)
            b.check()
            if (stats['valid'] and complete and not response.get('error')
                    and not response['diag'].get('fatal_error')):
                response.update(status='SUCCESS', embedding=raw)
    except _Stop as exc:
        response['diag']['final_stop'] = str(exc)
        if not response['diag'].get('fatal_error'):
            response['status'] = 'TIMEOUT' if b.clock() >= deadline else 'FAILURE'
        response['embedding'] = {}
    except Exception as exc:
        _exception(response, exc)
    if b.clock() >= deadline:
        response['embedding'] = {}
        if not response['diag'].get('fatal_error'):
            response['status'] = 'TIMEOUT'


def clone_embed(source, target, *, seed=0, timeout=15., deadline=None):
    start = time.perf_counter()
    response = dict(status='FAILURE', embedding={}, diag=dict(
        algorithm='wall_adaptive_clones', policy='C011', visits=[], fatal_error=False,
        source_label_order='supplied node order; diagnostic clone/target IDs are ranks',
        search_limit=None, total_limit=None, final_reserve=0.5,
        diagnostic_search_threshold=19_000_000, diagnostic_total_threshold=20_000_000))
    b, state, absolute = None, None, None
    source_labels, target_labels = [], []
    try:
        if type(seed) is not int or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise _InputError('integer seed and positive finite timeout required')
        if deadline is not None and (not isinstance(deadline, (int, float)) or not math.isfinite(deadline)):
            raise _InputError('finite absolute deadline required')
        absolute = min(start+timeout, deadline) if deadline is not None else start+timeout
        search_deadline = absolute-0.5
        response['diag'].update(deadline=absolute, search_deadline=search_deadline)
        b = _Budget(search_deadline, limit=19_000_000)
        with b.stage('input'):
            source_labels, src = _graph(source, b)
            target_labels, adj = _graph(target, b)
            if len(src) > len(adj):
                raise _InputError('source node count exceeds target capacity')
        with b.stage('initialization'):
            state = _State(src, adj, b, seed)
        with b.stage('placement_and_splitting'):
            response['diag']['stop_reason'] = _run(state, response['diag'])
    except _Stop as exc:
        response['diag']['stop_reason'] = str(exc)
    except Exception as exc:
        _exception(response, exc)
    if b is not None:
        response['diag']['search_work'] = b.units
        b.limit, b.deadline = 20_000_000, absolute
        if state is not None:
            _finish(response, state, source_labels, target_labels, absolute)
        response['diag'].update(work=dict(b.work), total_work=b.units, denied=b.denied,
                                first_crossings=dict(b.first_crossings),
                                stage_wall=dict(b.stage_wall))
    finish = time.perf_counter()
    response['time'] = finish-start
    response['diag'].update(wall=finish-start, finished=finish)
    if absolute is not None and finish >= absolute and not response['diag'].get('fatal_error'):
        response['status'], response['embedding'] = 'TIMEOUT', {}
    return response
