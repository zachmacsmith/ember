"""A065 exact A063 root scores. Imported lazily under the operator clock."""
from time import perf_counter, process_time

import numpy as np
from numba import njit

CHUNK_POPS = 256
INT_MAX = (1 << 63) - 1
WORK_NAMES = ('distance_array_items', 'root_bfs_pop', 'root_bfs_edge')


def range_safe(n, degree, arcs):
    return (all(type(x) is int and x >= 0 for x in (n, degree, arcs))
            and max(n, degree, arcs) < INT_MAX
            and degree * max(0, n-1) < INT_MAX
            and degree * (2*n + arcs) < INT_MAX)


@njit(cache=False, boundscheck=True)
def _advance(starts, adjacency, free, seeds, distance, queue, control,
             sums, maxima, reached, work, allowance):
    if control[2] == 0:
        distance[:] = -1
        work[0] += len(distance)
        for i in range(len(seeds)):
            q = seeds[i]
            distance[q] = 0
            queue[i] = q
        control[0], control[1], control[2] = 0, len(seeds), 1
    processed = 0
    while control[0] < control[1] and processed < allowance:
        q = queue[control[0]]
        control[0] += 1
        d = distance[q]
        sums[q] += d
        maxima[q] = max(maxima[q], d)
        reached[q] += 1
        processed += 1
        work[1] += 1
        work[2] += starts[q+1] - starts[q]
        for i in range(starts[q], starts[q+1]):
            p = adjacency[i]
            if free[p] and distance[p] < 0:
                distance[p] = d+1
                queue[control[1]] = p
                control[1] += 1
    return control[0] == control[1]


def _count(meter, counts):
    """Account for every completed operation before any clock can interrupt."""
    total = 0
    for name, count in counts.items():
        value = int(count)
        if value < 0:
            raise RuntimeError('negative compiled work delta')
        meter.counts[name] += value
        total += value
    meter.work += total
    meter.units[meter.phase] += total
    meter.next_check = meter.work + 256
    meter.check()


def _time(row, phase, function):
    began, cpu = perf_counter(), process_time()
    try:
        return function()
    finally:
        row['wall'][phase] = row['wall'].get(phase, 0.) + perf_counter()-began
        row['cpu'][phase] = row['cpu'].get(phase, 0.) + process_time()-cpu


def _target(ctx):
    if hasattr(ctx, '_a065_target'):
        return ctx._a065_target
    starts, adjacency = [0], []
    n = len(ctx.target)
    for ns in ctx.target:
        if any(type(p) is not int or not 0 <= p < n for p in ns):
            raise ValueError('invalid compiled target index')
        adjacency.extend(ns)
        starts.append(len(adjacency))
        _count(ctx.m, {'compiled_target_arc': len(ns), 'compiled_target_row': 1})
    if not range_safe(n, 0, len(adjacency)):
        raise ValueError('compiled target integer range exceeded')
    result = (np.asarray(starts, dtype=np.int64), np.asarray(adjacency, dtype=np.int64))
    _count(ctx.m, {'compiled_target_copy': len(starts)+len(adjacency)})
    ctx._a065_target = result
    return result


def _pack(ctx, reduced, free, boundary):
    n = len(ctx.target)
    mask = np.zeros(n, dtype=np.bool_)
    for q in free:
        if type(q) is not int or not 0 <= q < n:
            raise ValueError('invalid compiled free index')
        mask[q] = True
    _count(ctx.m, {'compiled_free_copy': len(free), 'compiled_free_array': n})
    groups = {v: [] for v in reduced}
    memberships = 0
    for q, owners in boundary.items():
        if type(q) is not int or not 0 <= q < n or not mask[q]:
            raise ValueError('invalid compiled seed index')
        for v in owners:
            if v not in groups:
                raise ValueError('foreign compiled boundary owner')
            groups[v].append(q)
            memberships += 1
    _count(ctx.m, {'compiled_boundary_key': len(boundary),
                   'compiled_boundary_membership': memberships})
    seeds = []
    for values in groups.values():
        ordered = ctx.m.ordered(values, key=ctx.qtie.__getitem__)
        seeds.append(np.asarray(ordered, dtype=np.int64))
        _count(ctx.m, {'compiled_seed_copy': len(ordered)})
    return mask, seeds


def roots(ctx, current, u, reduced, free, boundary, record, *, chunk_pops=CHUNK_POPS):
    if type(chunk_pops) is not int or chunk_pops <= 0:
        raise ValueError('positive integer clock interval required')
    m = ctx.m
    row = record['compiled_root']
    row.update(complete=False, cache=False, boundscheck=True, chunk_pops=chunk_pops,
               dispatches=0, compilation_dispatches=0, compilation_attempts=0,
               max_dispatch_wall=0., max_noncompiling_dispatch_wall=0.,
               root_scores=None, array_payload_bytes=0)
    starts, adjacency = _time(row, 'target_pack', lambda: _target(ctx))
    n, degree = len(ctx.target), len(reduced)
    if not range_safe(n, degree, len(adjacency)):
        raise ValueError('compiled query integer range exceeded')
    mask, seeds = _time(row, 'query_pack', lambda: _pack(ctx, reduced, free, boundary))

    def allocate():
        return (np.zeros(n, dtype=np.int64), np.zeros(n, dtype=np.int64),
                np.zeros(n, dtype=np.int64), np.empty(n, dtype=np.int64),
                np.empty(n, dtype=np.int64), np.zeros(3, dtype=np.int64),
                np.zeros(3, dtype=np.int64))
    sums, maxima, reached, distance, queue, control, work = _time(row, 'allocation', allocate)
    row['array_payload_bytes'] = sum(a.nbytes for a in
        (mask, sums, maxima, reached, distance, queue, control, work, *seeds))
    row['target_payload_bytes'] = starts.nbytes + adjacency.nbytes
    _count(m, {'root_array_items': 3*n, 'compiled_scratch_items': 2*n+6})
    previous = [0, 0, 0]
    for seed in seeds:
        control[:] = 0
        done = False
        while not done:
            m.check()
            signatures_before = len(_advance.signatures)
            began, cpu = perf_counter(), process_time()
            try:
                done = _advance(starts, adjacency, mask, seed, distance, queue, control,
                                sums, maxima, reached, work, chunk_pops)
            finally:
                wall, cpu = perf_counter()-began, process_time()-cpu
                compiled = len(_advance.signatures) > signatures_before
                attempted = compiled or signatures_before == 0
                phase = 'compilation_dispatch' if attempted else 'kernel'
                row['wall'][phase] = row['wall'].get(phase, 0.) + wall
                row['cpu'][phase] = row['cpu'].get(phase, 0.) + cpu
                row['dispatches'] += 1
                row['compilation_dispatches'] += int(compiled)
                row['compilation_attempts'] += int(attempted)
                row['max_dispatch_wall'] = max(row['max_dispatch_wall'], wall)
                if not attempted:
                    row['max_noncompiling_dispatch_wall'] = max(row['max_noncompiling_dispatch_wall'], wall)
                delta = {name: int(work[i])-previous[i] for i, name in enumerate(WORK_NAMES)}
                previous[:] = [int(x) for x in work]
                _count(m, delta)

    def export():
        # Preserve the original old-root assertion and Python sort exactly.
        eligible = [q for q in free if reached[q] == degree]
        _count(m, {'root_candidate': len(free)})
        for q in current.chains[u]:
            if not 0 <= q < n or reached[q] != degree:
                raise RuntimeError('old-root contact reach invariant failed')
        _count(m, {'old_root_check': len(current.chains[u])})
        return m.ordered(eligible, key=lambda q: (int(sums[q]), int(maxima[q]), ctx.qtie[q]))
    answer = _time(row, 'export_sort', export)
    # Score vectors are retained only when the isolated checker explicitly asks.
    if getattr(ctx, '_a065_capture_scores', False):
        row['root_scores'] = [sums.tolist(), maxima.tolist(), reached.tolist()]
        _count(m, {'diagnostic_score_copy': 3*n})
    m.check()
    row['complete'] = True
    record.update(ranking_complete=True, eligible_roots=len(answer))
    return answer
