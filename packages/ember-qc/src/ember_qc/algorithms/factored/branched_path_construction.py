"""One fixed A053 construction followed by bounded retained-branch path moves."""
import math
import time

from ember_qc.algorithms.factored.site_transfer_construction import reduced_core_embed as _base
from ember_qc.algorithms.factored.branched_path_reconstruction import (
    branched_path_reconstruction as _operator, _ReadMap, _ReadSource, _Stop,
)
from ember_qc.embedding_backend import _is_valid_embedding as _validator


class _FinalMeter:
    """Deadline-bounded final validation, separately reported from stage work."""
    def __init__(self, deadline):
        self.deadline, self.work = deadline, 0

    def tick(self, kind=None):
        if time.perf_counter() >= self.deadline:
            raise _Stop('deadline')
        self.work += 1


def branched_path_embed(source, target, *, seed=0, timeout=60., deadline=None):
    started = time.perf_counter()
    if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('integer seed and finite positive timeout required')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite absolute deadline required')
    deadline = min(deadline, started+timeout) if deadline is not None else started+timeout
    info = dict(algorithm='a053_retained_branch_path', version=1, base_calls=0,
                base_status=None, base_wall=0., base=None, operator=None,
                stage_status='not_reached', stage_deadline=None, stage_allowance=None,
                stage_wall=None, pre_stage_bookkeeping_wall=None,
                before_qubits=None, retained_qubits=None, qubits_saved=None,
                final_validated=None, final_validation_work=0,
                final_validation_complete=False, final_validation_wall=None,
                adopted=False, error=None, deadline=deadline,
                import_timing='fixed A053 and path helpers import eagerly outside pilot solver time')
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
                response = _base(source, target, seed=seed, timeout=timeout, deadline=deadline)
            finally:
                info['base_wall'] = time.perf_counter()-base_started
            base_ended = time.perf_counter()
            info.update(base_status=response.get('status'), base=response.get('diag'))
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
    info.update(wall=ended-started, ended=ended, deadline_overrun=max(0., ended-deadline))
    return result
