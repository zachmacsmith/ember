"""Original physical requirements with one soft virtual-neighbor guide.

One immutable original requirement graph, one at-most-once induced-core
native call, and one partial minor. Fill guides elimination and placement
without adding physical requirements. There is no alternate constructor on
failed lifting. Native
imports eagerly, as in the pilot baseline; edgeless cores avoid its invocation.
"""
from collections import deque
import heapq
import math
import time

from ember_qc.algorithms.factored.native import native_embed as _native_embed

from ember_qc.algorithms.factored.blocked_reinsertion import blocked_reinsert, _helpers

_HELPER_SHA = 'f29cdef92e5e0d6ce51594c7a13dfe2b234c3dfa15e25e4b5b0022d92c5f678d'
_Stop = _helpers._Stop

CORE_CONFIG = dict(construction='search', max_asks=1000, polish_passes=4,
                   beam_width=1, max_groups=512, polish_group_sizes=[1, 2, 3, 4],
                   polish_boundary_sites=16, polish_group_policy='round_robin',
                   polish_objective='qubits_contacts', initialization='spectral',
                   final_cleanup='deletion', vacancy_refinement='cyclic')


class _Expansion(_helpers._Builder):
    def scan(self):
        before = self.scans
        try:
            super().scan()
        finally:
            stage = self.info['stage']
            counts = self.info['scans_by_stage']
            counts[stage] = counts.get(stage, 0) + self.scans - before

    def valid(self, chains, *, complete):
        start = time.perf_counter()
        try:
            return super().valid(chains, complete=complete)
        finally:
            self.info['validation_calls'] += 1
            self.info['validation_wall'] += time.perf_counter() - start

    def guide_distances(self, v, chains, purpose='insertion'):
        eligible = [w for w in self.virtual_neighbors.get(v, ()) if w in chains]
        if not eligible:
            self.info['guidance_skips'] += 1
            return None
        guide = min(eligible, key=self.vrank.__getitem__)
        began = self.scans
        started = time.perf_counter()
        record = dict(vertex=v, guide=guide, purpose=purpose,
                      inside_repair=getattr(self, 'repair_end', None) is not None,
                      scan_start=began, scans=0, sites=0, complete=False, wall=0.)
        self.info['guidance_calls'] += 1
        distances = {}
        try:
            self.check()
            queue = deque()
            for q in sorted(chains[guide], key=self.qrank.__getitem__):
                self.scan()
                distances[q] = 0
                queue.append(q)
            while queue:
                self.check()
                q = queue.popleft()
                for p in self.target[q]:
                    self.scan()
                    if p not in distances:
                        distances[p] = distances[q] + 1
                        queue.append(p)
            self.check()
            record['complete'] = True
            return distances
        finally:
            record.update(scan_end=self.scans, scans=self.scans-began,
                          sites=len(distances), wall=time.perf_counter()-started)
            self.info['guidance_scans'] += record['scans']
            self.info['guidance_wall'] += record['wall']
            self.info['guidance_records'].append(record)

    def insert(self, v, entry, frozen=frozenset()):
        self.info['insertion_queries'] += 1
        prepared = self.prepare(v, entry, frozen)
        if prepared is None:
            self.info['preparation_failures'] += 1
            return None
        distances = self.guide_distances(v, prepared)
        def guidance(q):
            return 0 if distances is None else max(0, distances.get(q, math.inf)-1)
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
        pool.sort(key=lambda q: (-direct(q), guidance(q), price(q),
                                -(self.adj_bits[q] & free).bit_count(), self.qrank[q]))
        roots = []
        for q in pool[:_helpers.ROOTS]:
            self.check()
            trial = dict(prepared); trial[v] = {q}
            qb = dict(bounds); qb[v] = self.adj_bits[q]
            qf = free ^ self.bit[q]
            if not self.frontier_ok(trial, qb, qf):
                continue
            key = (-direct(q), tuple(-n for n in self.domains(trial, qb, qf)),
                   guidance(q), price(q), self.qrank[q])
            roots.append((key, q))
        roots.sort()
        best, best_key = None, None
        for _, root in roots[:_helpers.BRANCHES]:
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
                   tuple(-n for n in self.domains(trial, tb, tf)), guidance(root), self.qrank[root])
            if best_key is None or key < best_key:
                best, best_key = trial, key
        self.check()
        return best


def _reduce(engine):
    """Return filled ordering core/journal and immutable original requirements."""
    original = engine.source
    work = {v: set(row) for v, row in original.items()}
    unseen = set(work)
    anchors = set()
    while unseen:
        engine.check()
        first = min(unseen, key=engine.vrank.__getitem__)
        component, stack = {first}, [first]
        unseen.remove(first)
        while stack:
            v = stack.pop()
            for w in original[v]:
                engine.scan()
                if w in unseen:
                    unseen.remove(w); component.add(w); stack.append(w)
        anchors.add(min(component, key=lambda v: (-len(original[v]), engine.vrank[v])))
    heap = [(len(row), engine.vrank[v], v) for v, row in work.items()
            if v not in anchors and len(row) <= 3]
    heapq.heapify(heap)
    journal = []
    while heap:
        engine.check()
        degree, _, v = heapq.heappop(heap)
        if v not in work or len(work[v]) != degree:
            continue
        neighbors = tuple(sorted(work[v]))
        fill = []
        for i, a in enumerate(neighbors):
            for b in neighbors[i+1:]:
                engine.scan()
                if b not in work[a]:
                    work[a].add(b); work[b].add(a); fill.append((a, b))
        for w in neighbors:
            engine.scan()
            work[w].remove(v)
        del work[v]
        journal.append({'vertex': v, 'neighbors': neighbors, 'created_fill': tuple(fill)})
        for w in neighbors:
            if w not in anchors and len(work[w]) <= 3:
                heapq.heappush(heap, (len(work[w]), engine.vrank[w], w))
    required = {v: set(row) for v, row in original.items()}
    engine.check()
    return work, journal, required, anchors


def _set_required(engine, required):
    # No stale demand/ownership cache: immutable sorted adjacency for this stage.
    engine.check()
    engine.source = {v: tuple(sorted(row)) for v, row in required.items()}
    engine.check()


def _setup_guides(engine, core, ordering_core, journal, original):
    began = engine.scans
    started = time.perf_counter()
    try:
        virtual = {}
        for row in journal:
            engine.check()
            v = row['vertex']
            neighbors = []
            for w in row['neighbors']:
                engine.scan()
                if w not in original[v]:
                    neighbors.append(w)
            virtual[v] = tuple(neighbors)
        order = []
        if not any(core.values()):
            unseen = set(core)
            while unseen:
                engine.check()
                first = min(unseen, key=lambda v: (-len(original[v]), engine.vrank[v]))
                unseen.remove(first)
                heap = [(-len(original[first]), engine.vrank[first], first, None)]
                while heap:
                    engine.check()
                    _, _, v, parent = heapq.heappop(heap)
                    order.append(v)
                    virtual[v] = () if parent is None else (parent,)
                    for w in sorted(ordering_core[v], key=engine.vrank.__getitem__):
                        engine.scan()
                        if w in unseen:
                            unseen.remove(w)
                            heapq.heappush(heap, (-len(original[w]), engine.vrank[w], w, v))
        engine.check()
        engine.virtual_neighbors = virtual
        engine.core_order = order
        engine.info['core_guide_order'] = order
        engine.info['virtual_neighbors'] = virtual
    finally:
        engine.info['guidance_setup_scans'] += engine.scans-began
        engine.info['guidance_setup_wall'] += time.perf_counter()-started


def _place_anchors(engine, core, original, chains):
    for v in engine.core_order:
        engine.check()
        distances = engine.guide_distances(v, chains, 'edgeless_core')
        def guidance(q):
            return 0 if distances is None else max(0, distances.get(q, math.inf)-1)
        _, masks, bounds, free = engine.state(chains)
        pool = []
        for q in engine.target:
            engine.scan()
            if engine.bit[q] & free:
                pool.append(q)
        pool.sort(key=lambda q: (guidance(q), -(engine.adj_bits[q] & free).bit_count(), engine.qrank[q]))
        placed = False
        for q in pool:
            engine.check()
            trial_bounds = dict(bounds); trial_bounds[v] = engine.adj_bits[q]
            trial_free = free ^ engine.bit[q]
            trial = dict(chains); trial[v] = {q}
            if engine.frontier_ok(trial, trial_bounds, trial_free):
                engine.check()
                chains[v] = {q}; placed = True
                engine.info['anchors_placed'] += 1
                break
        if not placed:
            return chains, v
    return chains, None


def _snapshot_demand(engine, required, chains, vertices):
    """Metered diagnostics, sampled only at an actual blocked insertion."""
    _, _, bounds, free = engine.state(chains)
    out = []
    for v in sorted(vertices):
        engine.check()
        if v in chains:
            out.append(dict(vertex=v, chain_size=len(chains[v]),
                            pending=sum(w not in chains for w in required[v]),
                            distinct_free_sites=(bounds[v] & free).bit_count()))
    return out


def reduced_core_embed(source_graph, target_graph, *, seed=0, timeout=60.0, deadline=None):
    started = time.perf_counter()
    if (type(seed) is not int or type(timeout) not in (int, float)
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('ordinary integer seed and finite positive timeout required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite absolute deadline required')
    deadline = min(deadline, started+timeout) if deadline is not None else started+timeout
    info = dict(algorithm='degree_three_soft_fill_guidance', version=1, seed=seed,
                stage='setup', stage_wall={}, scans_by_stage={}, scan_count=0,
                requirements_policy='original_only', physical_fill_edges=0,
                guidance_policy='one_virtual_neighbor', guidance_calls=0, guidance_skips=0,
                guidance_scans=0, guidance_wall=0., guidance_records=[],
                guidance_setup_scans=0, guidance_setup_wall=0., guidance_total_scans=0,
                zero_placed_neighbor_insertions=0,
                blocked_repair_queries=0, blocked_repair_scans=0, blocked_repair_records=[],
                blocked_repair_accepted=0, ordinary_insertion_queries=0,
                blocked_repair_policy='critical_port_pool', repair_query_limit=1_000_000, repair_total_limit=5_000_000,
                work_limit=_helpers.SCANS, root_limit=_helpers.ROOTS, branch_limit=_helpers.BRANCHES,
                helper_sha256=_HELPER_SHA, core_config=dict(CORE_CONFIG),
                core_calls=0, core_wall=0., core_status=None, core_diag=None, core_failure=None,
                core_import_timing='eager module import outside pilot solver time',
                core_clock='relative inner allowance; original outer deadline gates every return',
                anchors_placed=0, insertion_queries=0, root_branches=0, path_queries=0,
                preparation_failures=0, frontier_rejections=0, staged_extension_sites=0,
                staged_pruned_sites=0, validation_calls=0, validation_wall=0.,
                journal=[], committed_updates=[], failed_insertion=None, failure_demands=None,
                requirements_recovered=False, valid=False, stopped_by=None, error=None)
    engine = None
    chains = {}
    required = {}
    original = {}
    valid = False
    active_started = time.perf_counter()

    def phase(name):
        nonlocal active_started
        now = time.perf_counter()
        old = info['stage']
        info['stage_wall'][old] = info['stage_wall'].get(old, 0.) + now-active_started
        info['stage'] = name
        active_started = now

    try:
        engine = _Expansion(source_graph, target_graph, deadline, seed, info)
        original = engine.source
        info.update(source_nodes=len(original), target_nodes=len(engine.target))
        if len(original) > len(engine.target):
            info['stopped_by'] = 'insufficient_sites'
        else:
            phase('reduction')
            ordering_core, journal, required, anchors = _reduce(engine)
            core_vertices = set(ordering_core)
            core = {v: set(original[v]) & core_vertices for v in ordering_core}
            engine.check()
            info.update(journal=journal, anchors=sorted(anchors), core_nodes=len(core),
                        core_edges=sum(map(len, core.values()))//2,
                        ordering_core_edges=sum(map(len, ordering_core.values()))//2,
                        eliminated_vertices=len(journal), fill_edges=sum(len(r['created_fill']) for r in journal))
            _set_required(engine, required)
            _setup_guides(engine, core, ordering_core, journal, original)
            phase('core')
            if info['core_edges']:
                # Keep every surviving vertex; require only original induced edges.
                core_graph = source_graph.subgraph(core).copy()
                engine.check()
                core_started = time.perf_counter()
                info['core_calls'] = 1
                try:
                    response = _native_embed(core_graph, target_graph.copy(), seed=seed,
                                             timeout=deadline-time.perf_counter(), **CORE_CONFIG)
                finally:
                    info['core_wall'] = time.perf_counter()-core_started
                info['core_status'] = response.get('status')
                info['core_diag'] = response.get('diag')
                if time.perf_counter() >= deadline:
                    info['core_failure'] = {k: v for k, v in response.items() if k != 'diag'}
                    info['core_late_embedding'] = response.get('embedding')
                    info['stopped_by'] = 'deadline'
                    raise _Stop
                if response.get('status') != 'SUCCESS':
                    info['core_failure'] = {k: v for k, v in response.items() if k != 'diag'}
                    info['stopped_by'] = 'core_failed'
                else:
                    raw = response.get('embedding')
                    if not isinstance(raw, dict) or set(raw) != set(core):
                        raise RuntimeError('native core returned incorrect source keys')
                    # Preserve duplicates until the primitive validator has rejected them.
                    if any(len(c) != len(set(c)) for c in raw.values()):
                        raise RuntimeError('native core returned duplicate qubits')
                    trial = {v: set(c) for v, c in raw.items()}
                    if not engine.valid(trial, complete=False):
                        raise RuntimeError('native core returned invalid original induced-core minor')
                    engine.check()
                    chains = trial
            else:
                chains, failed_anchor = _place_anchors(engine, core, original, chains)
                if failed_anchor is not None:
                    info['stopped_by'] = 'anchor_blocked'
                    info['failed_anchor'] = failed_anchor
            if info['stopped_by'] is None:
                phase('expansion')
                for index, row in enumerate(reversed(journal)):
                    engine.check()
                    v = row['vertex']
                    # R never changes; the journal's fill edges are ordering evidence.
                    placed_neighbors = [w for w in original[v] if w in chains]
                    if len(placed_neighbors) > 3:
                        raise RuntimeError('original placed degree exceeds filled elimination bound')
                    info['zero_placed_neighbor_insertions'] += not placed_neighbors
                    info['ordinary_insertion_queries'] += 1
                    trial = engine.insert(v, chains)
                    repair_record = None
                    if trial is None:
                        trial, repair_record = blocked_reinsert(engine, v, chains)
                    if trial is None:
                        info['stopped_by'] = ('work_limit' if engine.scans >= _helpers.SCANS else 'insertion_blocked')
                        info['failed_insertion'] = dict(reverse_index=index, **row)
                        info['failure_demands'] = _snapshot_demand(engine, required, chains, placed_neighbors)
                        break
                    # No synthetic physical requirement was imposed or released.
                    released_pruned = 0
                    before = sum(map(len, chains.values()))
                    update = dict(vertex=v,
                        qubits_added=sum(map(len, trial.values()))-before,
                        changed_existing=sum(w in chains and c != chains[w] for w, c in trial.items()),
                        chain_size=len(trial[v]), removed_fill=[], ordering_fill=row['created_fill'],
                        placed_original_neighbors=placed_neighbors,
                        released_fill_qubits_pruned=released_pruned,
                        insertion_operator='repair' if repair_record is not None else 'ordinary')
                    engine.check()
                    info['committed_updates'].append(update)
                    chains = trial
                    if repair_record is not None:
                        repair_record['committed'] = True
                        info['blocked_repair_accepted'] += 1
                else:
                    phase('final_validation')
                    engine.check()
                    recovered = all(set(required[v]) == set(original[v]) for v in original)
                    info['requirements_recovered'] = recovered
                    if not recovered:
                        raise RuntimeError('original physical requirements were mutated')
                    engine.source = original
                    valid = engine.valid(chains, complete=True)
                    if not valid:
                        raise RuntimeError('invalid completed original minor')
                    engine.check()
                    info['stopped_by'] = 'completed'
    except _Stop:
        pass
    except (ValueError, TypeError) as error:
        info.update(stopped_by='invalid_input', error=str(error))
    except Exception as error:
        info.update(stopped_by='internal_error', error=repr(error))
    if engine is not None:
        info['scan_count'] = engine.scans
        info['guidance_total_scans'] = info['guidance_setup_scans'] + info['guidance_scans']
    phase('publication')
    materialized = {v: sorted(c) for v, c in chains.items()}
    info.update(valid=valid, complete=valid, qubits=sum(map(len, materialized.values())),
                placed_vertices=len(materialized), partial_requirements={v: sorted(w for w in required.get(v, ()) if w in chains) for v in chains})
    ended = time.perf_counter()
    info['stage_wall']['publication'] = ended-active_started
    info.update(wall=ended-started, deadline=deadline, deadline_overrun=max(0., ended-deadline))
    status = ('TIMEOUT' if ended >= deadline else 'SUCCESS' if valid else
              'INVALID_INPUT' if info['stopped_by'] == 'invalid_input' else 'FAILURE')
    info['partial_embedding'] = materialized if status != 'SUCCESS' else None
    return dict(embedding=materialized if status == 'SUCCESS' else {}, status=status, diag=info)
