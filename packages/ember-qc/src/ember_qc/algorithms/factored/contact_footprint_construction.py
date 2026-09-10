"""A061-derived construction with one constant footprint packing policy.

The two public entry points differ only in virtual inactive-arm booking. Each
constructs one core, lifts one state and invokes one unchanged path stage.
"""
import math
import time
from ember_qc.algorithms.factored.contact_footprint_native import footprint_native_embed as _native_embed
from ember_qc.algorithms.factored.site_transfer_construction import (
    _Expansion, _reduce, _trial_requirements, _set_required, _place_anchors,
    _snapshot_demand, _prune_released, CORE_CONFIG, _HELPER_SHA,
    transfer_site, blocked_reinsert, _helpers)
from ember_qc.algorithms.factored.branched_path_construction import (
    _FinalMeter, _operator, _ReadMap, _ReadSource, _validator, _Stop)

_CoreStop = _helpers._Stop

def _reduced_core_embed(source_graph, target_graph, *, seed=0, timeout=60.0, deadline=None, inactive_booking=False):
    started = time.perf_counter()
    if (type(seed) is not int or type(timeout) not in (int, float)
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('ordinary integer seed and finite positive timeout required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite absolute deadline required')
    deadline = min(deadline, started+timeout) if deadline is not None else started+timeout
    info = dict(algorithm='contact_footprint_core_expansion', version=1, inactive_booking=inactive_booking, seed=seed,
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
                core_clock='original absolute deadline passed through; geometry reserves measured downstream time',
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
                                             timeout=deadline-time.perf_counter(), deadline=deadline,
                                             inactive_booking=inactive_booking, **CORE_CONFIG)
                finally:
                    info['core_wall'] = time.perf_counter()-core_started
                info['core_status'] = response.get('status')
                info['core_diag'] = response.get('diag')
                if time.perf_counter() >= deadline:
                    info['core_failure'] = {k: v for k, v in response.items() if k != 'diag'}
                    info['core_late_embedding'] = response.get('embedding')
                    info['stopped_by'] = 'deadline'
                    raise _CoreStop
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
                for index, row in enumerate(reversed(journal)):
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
                        info['failed_insertion'] = dict(reverse_index=index, **row)
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
                    update = dict(vertex=v,
                        qubits_added=sum(map(len, trial.values()))-before,
                        changed_existing=sum(w in chains and c != chains[w] for w, c in trial.items()),
                        chain_size=len(trial[v]), removed_fill=row['created_fill'],
                        released_fill_qubits_pruned=released_pruned,
                        insertion_operator='transfer' if transfer_used else 'repair' if repair_record is not None else 'ordinary')
                    engine.check()
                    info['committed_updates'].append(update)
                    chains, required = trial, trial_required
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
    except _CoreStop:
        pass
    except (ValueError, TypeError) as error:
        info.update(stopped_by='invalid_input', error=str(error))
    except Exception as error:
        info.update(stopped_by='internal_error', error=repr(error))
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


def _embed(source, target, *, seed=0, timeout=60., deadline=None, inactive_booking=False):
    started = time.perf_counter()
    if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('integer seed and finite positive timeout required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite absolute deadline required')
    deadline = min(deadline, started+timeout) if deadline is not None else started+timeout
    info = dict(algorithm='contact_footprint_retained_branch_path', version=1, inactive_booking=inactive_booking, base_calls=0,
                base_status=None, base_wall=0., base=None, operator=None,
                stage_status='not_reached', stage_deadline=None, stage_allowance=None,
                stage_wall=None, pre_stage_bookkeeping_wall=None,
                before_qubits=None, retained_qubits=None, qubits_saved=None,
                final_validated=None, final_validation_work=0,
                final_validation_complete=False, final_validation_wall=None,
                adopted=False, error=None, deadline=deadline,
                import_timing='isolated footprint A053 and unchanged path helpers import eagerly outside pilot solver time')
    current = None
    response = {}
    status = 'TIMEOUT'
    try:
        if time.perf_counter() >= deadline:
            info['stage_status'] = 'original_deadline_before_base'
        else:
            base_started = time.perf_counter()
            info['base_calls'] = 1
            try:
                response = _reduced_core_embed(source, target, seed=seed, timeout=timeout,
                                               deadline=deadline, inactive_booking=inactive_booking)
            finally:
                info['base_wall'] = time.perf_counter()-base_started
            base_ended = time.perf_counter()
            info.update(base_status=response.get('status'), base=response.get('diag'))
            info['full_source_valid_handoff_at'] = (base_ended-started
                if response.get('status') == 'SUCCESS' else None)
            status = response.get('status', 'FAILURE')
            if status != 'SUCCESS':
                info['stage_status'] = 'base_not_successful'
            else:
                current = response.get('embedding')
                if not isinstance(current, dict):
                    raise ValueError('successful A053 output is not a mapping')
                info['before_qubits'] = sum(map(len, current.values()))
                if base_ended >= deadline:
                    status = 'TIMEOUT'
                    info['stage_status'] = 'base_return_late'
                else:
                    stage_started = time.perf_counter()
                    allowance = min(1., .2*(stage_started-started))
                    stage_deadline = min(deadline, stage_started+allowance)
                    info.update(stage_allowance=allowance, stage_deadline=stage_deadline,
                                pre_stage_bookkeeping_wall=stage_started-base_ended)
                    try:
                        current, operation = _operator(current, source.adj, target.adj,
                                                       validator=_validator, deadline=stage_deadline)
                    finally:
                        info['stage_wall'] = time.perf_counter()-stage_started
                    info.update(operator=operation, stage_status=operation['status'])
                    if operation.get('error'):
                        status = 'FAILURE'
                        info['error'] = operation['error']
                    # A local stop may retain an earlier fully certified map;
                    # this validation performs no renewed path work/search.
                    validation_started = time.perf_counter()
                    meter = _FinalMeter(deadline)
                    try:
                        ranks = {}
                        for v in source:
                            meter.tick()
                            ranks[v] = len(ranks)
                        valid = _validator(_ReadMap(current, meter),
                                           _ReadSource(source.adj, ranks, meter),
                                           _ReadMap(target.adj, meter))
                        info.update(final_validated=valid, final_validation_complete=True)
                        if not valid:
                            status = 'FAILURE'
                            info['error'] = 'final original-graph validation failed'
                    except _Stop:
                        status = 'TIMEOUT'
                    finally:
                        info.update(final_validation_work=meter.work,
                                    final_validation_wall=time.perf_counter()-validation_started)
    except Exception as exc:
        status = 'FAILURE'
        info['error'] = type(exc).__name__+': '+str(exc)
    if current is not None:
        info['retained_qubits'] = sum(map(len, current.values()))
    if status == 'SUCCESS':
        info['qubits_saved'] = info['before_qubits']-info['retained_qubits']
        info['adopted'] = info['qubits_saved'] > 0
    # Preserve unadopted base failure evidence, including its nested partial map.
    partial = current if current is not None else response.get('partial_embedding')
    if partial is None and isinstance(response.get('diag'), dict):
        partial = response['diag'].get('partial_embedding')
    result = dict(status=status, embedding=current if status == 'SUCCESS' else {},
                  partial_embedding=partial if status != 'SUCCESS' else None,
                  diagnostic_embedding=response.get('diagnostic_embedding'),
                  error=info['error'] or response.get('error'), diag=info)
    operation = info['operator'] or {}
    info['counted_added_work'] = operation.get('work', 0)+info['final_validation_work']
    ended = time.perf_counter()
    if ended >= deadline:
        result.update(status='TIMEOUT', embedding={}, partial_embedding=partial)
        info.update(qubits_saved=None, adopted=False)
    allocation = ((info.get('base') or {}).get('core_diag') or {}).get('allocation')
    info['constructor_allocation'] = None
    if allocation is not None and allocation.get('layout_returned_at') is not None:
        downstream = ended-allocation['layout_returned_at']
        info['constructor_allocation'] = dict(
            exposure=allocation['exposure'], max_asks=allocation['max_asks'],
            reserve_seconds=allocation['reserve_seconds'],
            downstream_wall=downstream,
            reserve_overrun=max(0., downstream-allocation['reserve_seconds']),
            original_deadline_overrun=max(0., ended-deadline),
            remaining_after_layout=allocation['remaining_after_layout'])
    info.update(wall=ended-started, ended=ended, deadline_overrun=max(0., ended-deadline))
    return result



def contact_footprint_embed(source, target, *, seed=0, timeout=60., deadline=None):
    return _embed(source, target, seed=seed, timeout=timeout, deadline=deadline,
                  inactive_booking=False)

def inactive_booking_embed(source, target, *, seed=0, timeout=60., deadline=None):
    return _embed(source, target, seed=seed, timeout=timeout, deadline=deadline,
                  inactive_booking=True)
