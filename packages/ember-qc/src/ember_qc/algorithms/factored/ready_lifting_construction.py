"""A053 insertion bodies with dependency-ready direct-singleton scheduling.

One immutable original source, one at-most-once native core call, and one
partial minor. There is no alternate constructor on failed lifting. Native
imports eagerly, as in the pilot baseline; edgeless cores avoid its invocation.
"""
import heapq
from ember_qc.algorithms.factored.ready_lifting_schedule import ReadySchedule, diagnostics as _schedule_diagnostics
from ember_qc.algorithms.factored.site_transfer import transfer_site, TransferLimit
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
        if getattr(self, "transfer_end", None) is not None and self.scans >= self.transfer_end:
            self.check()
            if self.scans >= _helpers.SCANS:
                self.info["stopped_by"] = "work_limit"
                raise _Stop
            raise TransferLimit
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


def _reduce(engine):
    """Return exact filled core, journal, and all-node requirement adjacency."""
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
    required = {v: set(work.get(v, ())) for v in original}
    for row in journal:
        engine.check()
        v = row['vertex']
        for w in row['neighbors']:
            engine.scan()
            required[v].add(w); required[w].add(v)
    engine.check()
    return work, journal, required, anchors


def _trial_requirements(required, row, engine):
    trial = dict(required)
    changed = {v for pair in row['created_fill'] for v in pair}
    for v in changed:
        engine.check()
        trial[v] = set(required[v])
    for a, b in row['created_fill']:
        engine.scan()
        if b not in trial[a] or a not in trial[b]:
            raise RuntimeError('journal fill edge missing before reversal')
        trial[a].remove(b); trial[b].remove(a)
    return trial


def _set_required(engine, required):
    # No stale demand/ownership cache: immutable sorted adjacency for this stage.
    engine.check()
    engine.source = {v: tuple(sorted(row)) for v, row in required.items()}
    engine.check()


def _place_anchors(engine, core, original, chains):
    for v in sorted(core, key=lambda u: (-len(original[u]), engine.vrank[u])):
        engine.check()
        _, masks, bounds, free = engine.state(chains)
        pool = []
        for q in engine.target:
            engine.scan()
            if engine.bit[q] & free:
                pool.append(q)
        pool.sort(key=lambda q: (-(engine.adj_bits[q] & free).bit_count(), engine.qrank[q]))
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


def _prune_released(engine, trial, row):
    """Only endpoints of removed fill can have these newly relaxed contacts."""
    endpoints = {v for edge in row['created_fill'] for v in edge}
    if not endpoints:
        return trial, 0
    shortened = engine.prune(trial, endpoints)
    if shortened != trial and not engine.valid(shortened, complete=False):
        raise RuntimeError('invalid released-fill endpoint pruning')
    engine.check()
    return shortened, sum(map(len, trial.values()))-sum(map(len, shortened.values()))


def reduced_core_embed(source_graph, target_graph, *, seed=0, timeout=60.0, deadline=None):
    started = time.perf_counter()
    if (type(seed) is not int or type(timeout) not in (int, float)
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('ordinary integer seed and finite positive timeout required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite absolute deadline required')
    deadline = min(deadline, started+timeout) if deadline is not None else started+timeout
    info = dict(algorithm='degree_three_ready_expansion_site_transfer', version=1, seed=seed,
                scheduler=_schedule_diagnostics(),
                stage='setup', stage_wall={}, scans_by_stage={}, scan_count=0,
                blocked_repair_queries=0, blocked_repair_scans=0, blocked_repair_records=[],
                blocked_repair_accepted=0, ordinary_insertion_queries=0,
                transfer_queries=0, transfer_accepted=0, transfer_scans=0, transfer_records=[],
                transfer_query_limit=50_000, transfer_total_limit=1_000_000, transfer_site_limit=64,
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
    scheduler = None
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
            core, journal, required, anchors = _reduce(engine)
            info.update(journal=journal, anchors=sorted(anchors), core_nodes=len(core),
                        core_edges=sum(map(len, core.values()))//2,
                        eliminated_vertices=len(journal), fill_edges=sum(len(r['created_fill']) for r in journal))
            _set_required(engine, required)
            phase('core')
            if info['core_edges']:
                # Supplied graph is copied; only the exact filled core is constructed.
                core_graph = source_graph.subgraph(core).copy()
                core_graph.remove_edges_from(list(core_graph.edges()))
                core_graph.add_edges_from((a, b) for a in core for b in core[a] if a < b)
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
                        raise RuntimeError('native core returned invalid filled-core minor')
                    engine.check()
                    chains = trial
            else:
                chains, failed_anchor = _place_anchors(engine, core, original, chains)
                if failed_anchor is not None:
                    info['stopped_by'] = 'anchor_blocked'
                    info['failed_anchor'] = failed_anchor
            if info['stopped_by'] is None:
                phase('expansion')
                scheduler = ReadySchedule(engine, journal, info['scheduler'])
                while scheduler.remaining:
                    row_id, selection = scheduler.choose(chains)
                    index = len(journal)-1-row_id
                    row = journal[row_id]
                    engine.check()
                    v = row['vertex']
                    trial_required = _trial_requirements(required, row, engine)
                    _set_required(engine, trial_required)
                    trial, transfer_record = transfer_site(engine, v, chains)
                    repair_record = None
                    transfer_used = trial is not None
                    if trial is None:
                        info['ordinary_insertion_queries'] += 1
                        trial = engine.insert(v, chains)
                        if trial is None:
                            trial, repair_record = blocked_reinsert(engine, v, chains, row['created_fill'])
                    if trial is None:
                        info['stopped_by'] = ('work_limit' if engine.scans >= _helpers.SCANS else 'insertion_blocked')
                        info['failed_insertion'] = dict(reverse_index=index, journal_index=row_id,
                                                        insertion_index=len(info['committed_updates']), **row)
                        info['failure_demands'] = _snapshot_demand(engine, trial_required, chains, row['neighbors'])
                        _set_required(engine, required)
                        break
                    if repair_record is None:
                        trial, released_pruned = _prune_released(engine, trial, row)
                    else:
                        # Frozen owners outside the released block stay unchanged.
                        released_pruned = repair_record.get('released_fill_qubits_pruned', 0)
                    # Both paths have certified against trial R, including future ports.
                    before = sum(map(len, chains.values()))
                    update = dict(vertex=v, journal_index=row_id,
                        insertion_index=len(info['committed_updates']),
                        qubits_added=sum(map(len, trial.values()))-before,
                        changed_existing=sum(w in chains and c != chains[w] for w, c in trial.items()),
                        chain_size=len(trial[v]), removed_fill=row['created_fill'],
                        released_fill_qubits_pruned=released_pruned,
                        insertion_operator='transfer' if transfer_used else 'repair' if repair_record is not None else 'ordinary')
                    scheduler.prepare_commit(row_id, selection)
                    engine.check()
                    info['committed_updates'].append(update)
                    chains, required = trial, trial_required
                    scheduler.commit(row_id, selection)
                    if transfer_used:
                        transfer_record.update(committed=True, committed_q=sum(map(len, trial.values())),
                                               released_fill_qubits_pruned=released_pruned)
                        info['transfer_accepted'] += 1
                    if repair_record is not None:
                        repair_record['committed'] = True
                        info['blocked_repair_accepted'] += 1
                else:
                    phase('final_validation')
                    engine.check()
                    recovered = all(set(required[v]) == set(original[v]) for v in original)
                    info['requirements_recovered'] = recovered
                    if not recovered:
                        raise RuntimeError('final requirements differ from original source')
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
    if scheduler is not None:
        scheduler.stop()
    if engine is not None:
        info['scan_count'] = engine.scans
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
