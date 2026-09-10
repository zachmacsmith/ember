"""A065: unchanged A064 search with exact compiled root ranking."""
import math
import time

from ember_qc.algorithms.factored.mobile_boundary_reconstruction import (
    _Context as _PythonContext, _Meter, _Stop,
)
from ember_qc.algorithms.factored.interleaved_boundary_reconstruction import _Search


class _Context(_PythonContext):
    def roots(self, current, u, reduced, free, boundary, record):
        self.m.phase_to('root_search')
        row = dict(wall={}, cpu={})
        record['compiled_root'] = row
        began, cpu = time.perf_counter(), time.process_time()
        try:
            from ember_qc.algorithms.factored.compiled_boundary_roots import roots
        finally:
            row['wall']['import'] = time.perf_counter()-began
            row['cpu']['import'] = time.process_time()-cpu
        self.m.check()
        return roots(self, current, u, reduced, free, boundary, record)


def compiled_boundary_reconstruction(embedding, source_adj, target_adj, *, seed=0,
                                       deadline, validator):
    """Return one last certified incumbent; fatal errors have no credited map."""
    if type(seed) is not int or not isinstance(deadline, (int, float)) or not math.isfinite(deadline):
        raise ValueError('integer seed and finite absolute deadline required')
    m = _Meter(deadline)
    info = dict(algorithm='compiled_boundary_reconstruction', version='A065',
                status='started', error=None, input_copy_complete=False, input_validated=False,
                rounds_started=0, rounds_completed=0, rounds=[], queries=[], commits=[], epochs=[],
                epoch=0, accepted=0, before_qubits=None, after_qubits=None,
                stopped_phase=None, diagnostic_embedding=None)
    current, search, result = None, None, embedding
    try:
        m.check()
        ctx = _Context(source_adj, target_adj, seed, validator, m)
        chains = ctx.read_entry(embedding)
        result = ctx.externalize(chains)
        info['input_copy_complete'] = True
        ctx.certify(chains)
        current = ctx.bundle(chains)
        result = current.external
        info.update(input_validated=True, before_qubits=current.qubits)
        search = _Search(ctx, current, info)
        search.run()
    except _Stop:
        info.update(status='deadline', stopped_phase=m.phase)
    except Exception as exc:
        info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_phase=m.phase)
    finally:
        if search is not None:
            current = search.current
            result = current.external
            try:
                search.cleanup()
            except _Stop:
                info['cleanup_deadline'] = True
                if info['status'] not in ('error', 'deadline'):
                    info.update(status='deadline', stopped_phase=m.phase)
            except Exception as exc:
                info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_phase=m.phase)
    if info['error'] is not None:
        info['diagnostic_embedding'] = current.external if current is not None else embedding
        result = {}
    info['after_qubits'] = current.qubits if current is not None else None
    info.update(m.finish())
    if info['ended'] >= deadline and info['status'] not in ('error', 'deadline'):
        info.update(status='deadline', stopped_phase=m.phase)
    return result, info
