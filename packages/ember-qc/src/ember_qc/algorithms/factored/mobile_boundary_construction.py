"""A063: one unchanged A061 construction, then original-contact reconstruction."""
import math
import time

from ember_qc.algorithms.factored.branched_path_construction import branched_path_embed as _base
from ember_qc.algorithms.factored.mobile_boundary_reconstruction import (
    mobile_boundary_reconstruction as _operator, _Meter, _ReadMap, _ReadSource, _Stop,
)
from ember_qc.embedding_backend import _is_valid_embedding as _validator


def mobile_boundary_embed(source, target, *, seed=0, timeout=60., deadline=None):
    started = time.perf_counter()
    if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('integer seed and positive finite timeout required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite absolute deadline required')
    absolute = min(started+timeout, deadline) if deadline is not None else started+timeout
    reserve = min(1., .05*timeout)
    info = dict(algorithm='a061_mobile_boundary', version='A063', base_calls=0,
                base_status=None, base_wall=None, base_cpu=None, base=None,
                before_qubits=None, retained_qubits=None, qubits_saved=None,
                stage_status='not_reached', stage_wall=None, stage_cpu=None,
                stage_deadline=absolute-reserve, final_reserve=reserve,
                operator=None, final_validated=None, final_validation_complete=False,
                final_validation_wall=None, final_validation_cpu=None,
                final_validation_work=None, error=None, adopted=False,
                original_deadline=absolute,
                import_timing='A061/operator imports precede pilot solver timer; process time retains them')
    response, current = {}, None
    status, fatal = 'TIMEOUT', False
    try:
        if time.perf_counter() >= absolute:
            info['stage_status'] = 'deadline_before_base'
        else:
            began, cpu = time.perf_counter(), time.process_time()
            info['base_calls'] = 1
            try:
                response = _base(source, target, seed=seed, timeout=timeout, deadline=absolute)
            finally:
                info.update(base_wall=time.perf_counter()-began, base_cpu=time.process_time()-cpu)
            if not isinstance(response, dict):
                info['base'] = repr(response)
                response = {}
                raise RuntimeError('base result is not a mapping')
            status = response.get('status', 'FAILURE')
            info.update(base_status=status, base=response.get('diag'))
            if status != 'SUCCESS':
                info['stage_status'] = 'base_not_successful'
            else:
                current = response.get('embedding')
                if not isinstance(current, dict):
                    raise RuntimeError('successful base map is not a dictionary')
                info['before_qubits'] = sum(map(len, current.values()))
                if time.perf_counter() >= absolute:
                    status = 'TIMEOUT'; info['stage_status'] = 'base_return_late'
                else:
                    if time.perf_counter() < info['stage_deadline']:
                        began, cpu = time.perf_counter(), time.process_time()
                        try:
                            candidate, operation = _operator(current, source.adj, target.adj,
                                seed=seed, deadline=info['stage_deadline'], validator=_validator)
                        finally:
                            info.update(stage_wall=time.perf_counter()-began,
                                        stage_cpu=time.process_time()-cpu)
                        info.update(operator=operation, stage_status=operation['status'])
                        if operation.get('error'):
                            current = operation.get('diagnostic_embedding', current)
                            fatal = True
                            status = 'FAILURE'
                            info['error'] = operation['error']
                        else:
                            current = candidate
                    else:
                        info['stage_status'] = 'insufficient_search_time'
                    if not fatal:
                        meter = _Meter(absolute)
                        began, cpu = time.perf_counter(), time.process_time()
                        try:
                            meter.phase_to('final_validation')
                            ranks = {}
                            for v in source:
                                meter.tick('source_rank'); ranks[v] = len(ranks)
                            valid = _validator(_ReadMap(current, meter),
                                               _ReadSource(source.adj, ranks, meter),
                                               _ReadMap(target.adj, meter))
                            meter.check()
                            info.update(final_validated=valid, final_validation_complete=True)
                            if not valid:
                                fatal = True; status = 'FAILURE'
                                info['error'] = 'final original-graph validation failed'
                        except _Stop:
                            status = 'TIMEOUT'
                        finally:
                            info.update(final_validation_wall=time.perf_counter()-began,
                                        final_validation_cpu=time.process_time()-cpu,
                                        final_validation_work=meter.work)
    except Exception as exc:
        fatal = True
        status = 'FAILURE'
        info['error'] = type(exc).__name__+': '+str(exc)
    if isinstance(current, dict):
        try:
            info['retained_qubits'] = sum(map(len, current.values()))
        except (TypeError, AttributeError):
            fatal = True; status = 'FAILURE'
            info['error'] = info['error'] or 'malformed retained map'
    if status == 'SUCCESS' and not fatal:
        info['qubits_saved'] = info['before_qubits']-info['retained_qubits']
        if info['qubits_saved'] < 0:
            fatal = True; status = 'FAILURE'
            info['error'] = 'operator increased total Q'
            info['qubits_saved'] = None
        else:
            info['adopted'] = info['qubits_saved'] > 0
    partial = current if current is not None else response.get('partial_embedding')
    if partial is None and isinstance(response.get('diag'), dict):
        partial = response['diag'].get('partial_embedding')
    result = dict(status=status, embedding=current if status == 'SUCCESS' and not fatal else {},
                  partial_embedding=partial if status != 'SUCCESS' or fatal else None,
                  diagnostic_embedding=partial if fatal else response.get('diagnostic_embedding'),
                  error=info['error'] or response.get('error'), diag=info)
    ended = time.perf_counter()
    if ended >= absolute:
        result.update(status='TIMEOUT', embedding={}, partial_embedding=partial)
        info.update(qubits_saved=None, adopted=False)
    info.update(wall=ended-started, ended=ended, deadline_overrun=max(0., ended-absolute))
    return result
