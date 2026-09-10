"""B029 private routing copy: unchanged search, finalized array export.

This module is imported lazily by the standalone constructor, inside its clock.
All JIT, packing, private array and dictionary work belongs to the current call.
No embedding constructor or solver is imported here.
"""
from heapq import heappop, heappush
from time import perf_counter

import numpy as np
from numba import njit, types
from numba.typed import List


INF = (1 << 63) - 1
FORBIDDEN = -1
NO_PARENT = -1
UNKNOWN_PARENT = -2
CHUNK_POPS = 256
HEAP_TYPE = types.UniTuple(types.int64, 5)
WORK_NAMES = ('heap_push', 'heap_pop', 'settled_label', 'boundary_adjacency',
              'routing_adjacency')


def range_safe(n, degree, max_cost, directed_edges):
    """Use Python integers before any conversion to a compiled fixed width."""
    values = (n, degree, max_cost, directed_edges)
    if any(type(x) is not int or x < 0 for x in values):
        return False
    # An allowed path costs at most n*max_cost; summation and tentative
    # relaxation fit this larger bound. Work counters also have finite bounds.
    return (n > 0 and degree > 0 and max_cost > 0
            and max(values) < INF
            and (degree + 1) * n * max_cost < INF
            and degree * (n + 2 * directed_edges + 1) < INF)


@njit(cache=False, boundscheck=True)
def _seed_neighbor(j, source_rank, sites, starts, adjacency, costs, distance,
                   parent, discovered, discovery_counts, heap, work):
    boundary_count = 0
    for site in sites:
        for index in range(starts[site], starts[site + 1]):
            q = adjacency[index]
            work[3] += 1
            weight = costs[q]
            if weight != FORBIDDEN and distance[j, q] == INF:
                distance[j, q] = weight
                parent[j, q] = NO_PARENT
                discovered[j, discovery_counts[j]] = q
                discovery_counts[j] += 1
                heappush(heap, (weight, source_rank, q, j, q))
                work[0] += 1
                boundary_count += 1
    return boundary_count


@njit(cache=False, boundscheck=True)
def _advance(starts, adjacency, costs, source_ranks, distance, settled, parent,
             discovered, discovery_counts, settlement_order, settlement_counts,
             sums, counts, heap, control, work, pop_allowance):
    """Return to Python for clock observation; never discard an unfinished heap."""
    degree = len(source_ranks)
    processed = 0
    while len(heap) > 0 and processed < pop_allowance:
        value, _, _, j, q = heappop(heap)
        processed += 1
        work[1] += 1
        control[3] = j
        if settled[j, q] != INF or distance[j, q] != value:
            continue
        # Keep B027's stale rejection BEFORE the strict stopping test.
        if control[1] >= 0 and value > control[0]:
            control[2] = 1
            return True
        settled[j, q] = value
        settlement_order[j, settlement_counts[j]] = q
        settlement_counts[j] += 1
        work[2] += 1
        sums[q] += value
        counts[q] += 1
        if counts[q] == degree:
            score = sums[q] - (degree - 1) * costs[q]
            if (control[1] < 0 or score < control[0]
                    or (score == control[0] and q < control[1])):
                control[0] = score
                control[1] = q
        for index in range(starts[q], starts[q + 1]):
            p = adjacency[index]
            work[4] += 1
            weight = costs[p]
            if weight == FORBIDDEN or settled[j, p] != INF:
                continue
            candidate = value + weight
            if candidate < distance[j, p]:
                if distance[j, p] == INF:
                    discovered[j, discovery_counts[j]] = p
                    discovery_counts[j] += 1
                distance[j, p] = candidate
                parent[j, p] = q
                heappush(heap, (candidate, source_ranks[j], p, j, p))
                work[0] += 1
    return len(heap) == 0


def _record_work(meter, work, previous):
    """Publish all observed kernel counts before checking the clock.

    Calling step repeatedly could stop midway and lose already-executed work.
    These are the same semantic operations, with a different polling schedule.
    """
    total = 0
    for i, name in enumerate(WORK_NAMES):
        delta = int(work[i]) - previous[i]
        if delta < 0:
            raise RuntimeError('compiled work counter moved backwards')
        meter.kinds[name] += delta
        previous[i] += delta
        total += delta
    meter.units[meter.stage] += total
    meter.total += total
    meter.pending += total


def _target(engine):
    if hasattr(engine, '_b029_target'):
        return engine._b029_target
    m = engine.m
    with m.phase('routing_target_pack'):
        starts, adjacency = [0], []
        for q in engine.qorder:
            for p in engine.adj[q]:
                adjacency.append(engine.rank[p])
                m.step('compiled_target_arc')
            starts.append(len(adjacency))
        result = (np.asarray(starts, dtype=np.int64),
                  np.asarray(adjacency, dtype=np.int64))
        m.step('compiled_target_copy', len(starts) + len(adjacency))
        m.clock()
        for array in result:
            array.flags.writeable = False
        engine._b029_target = result
        return result


def _acceleration(engine):
    if not hasattr(engine, 'acceleration'):
        engine.acceleration = dict(version='B029', queries=0, completed_queries=0,
            incomplete_queries=0, arithmetic_fallbacks=0, compiled_dispatches=0,
            compile_dispatches=0, compilation_attempts=0,
            first_dispatch_wall=None, compile_dispatch_wall=0.0,
            kernel_wall=0.0, max_dispatch_wall=0.0, max_warm_dispatch_wall=0.0,
            allocation_wall=0.0, conversion_wall=0.0, query_wall=0.0,
            cache=False, boundscheck=True, chunk_pops=CHUNK_POPS,
            target_packing='once per engine',
            counter_note='routing semantic counts retained; packed cost sites counted separately')
    return engine.acceleration


def joint_root(engine, neighbors, chains, occupancy, quality):
    m = engine.m
    total = _acceleration(engine)
    total['queries'] += 1
    row = dict(complete=False, fallback=False, dispatches=0,
               compilation_dispatches=0, compilation_attempts=0, kernel_wall=0.0,
               allocation_wall=0.0, conversion_wall=0.0,
               max_dispatch_wall=0.0, max_warm_dispatch_wall=0.0)
    total['last_query'] = row
    if engine.last_visit is not None:
        engine.last_visit['compiled_query'] = row
    started = perf_counter()
    work = np.zeros(len(WORK_NAMES), dtype=np.int64)
    previous = [0] * len(WORK_NAMES)
    control = None
    try:
        starts, adjacency = _target(engine)
        n, degree = len(engine.qorder), len(neighbors)
        with m.phase('routing_query_pack'):
            costs_python = []
            for q in engine.qorder:
                count = len(occupancy.get(q, engine.state.owners.get(q, ())))
                value = (FORBIDDEN if quality and count else
                         1 + (0 if quality else engine.prices.get(q, 1) * count))
                if type(value) is not int or value < FORBIDDEN or value == 0:
                    raise ValueError('invalid compiled site cost')
                costs_python.append(value)
                m.step('compiled_cost_site')
            maximum = max((v for v in costs_python if v != FORBIDDEN), default=1)
            row['range_bound'] = (degree + 1) * n * maximum
            safe = range_safe(n, degree, maximum, len(adjacency))
            m.clock()
            if not safe:
                row['fallback'] = True
                total['arithmetic_fallbacks'] += 1
                with m.phase('routing_arithmetic_fallback'):
                    result = engine._python_joint_root(neighbors, chains, occupancy, quality)
                with m.phase('routing_fallback_pack'):
                    result = pack_python(engine, neighbors, costs_python, result, starts, adjacency)
                row['complete'] = True
                return result
            costs = np.asarray(costs_python, dtype=np.int64)
            source_ranks = np.asarray([engine.srank[v] for v in neighbors], dtype=np.int64)
            sites = []
            for v in neighbors:
                ranks = [engine.rank[q] for q in m.ordered(chains[v], engine.rank.__getitem__)]
                sites.append(np.asarray(ranks, dtype=np.int64))
                m.step('compiled_boundary_copy', len(ranks))
            if any(not 0 <= int(x) < n for a in sites for x in a):
                raise ValueError('foreign compiled boundary index')
            m.step('compiled_query_copy', n + degree)
        before = perf_counter()
        try:
            with m.phase('routing_allocation'):
                distance = np.full((degree, n), INF, dtype=np.int64)
                settled = np.full((degree, n), INF, dtype=np.int64)
                parent = np.full((degree, n), UNKNOWN_PARENT, dtype=np.int64)
                discovered = np.full((degree, n), -1, dtype=np.int64)
                settlement_order = np.full((degree, n), -1, dtype=np.int64)
                discovery_counts = np.zeros(degree, dtype=np.int64)
                settlement_counts = np.zeros(degree, dtype=np.int64)
                sums = np.zeros(n, dtype=np.int64)
                counts = np.zeros(n, dtype=np.int64)
                control = np.asarray([INF, -1, 0, -1], dtype=np.int64)
                heap = List.empty_list(HEAP_TYPE)
                m.step('compiled_array_item', 5 * degree * n + 2 * degree + 2 * n + 4)
                m.clock()
        finally:
            elapsed = perf_counter() - before
            row['allocation_wall'] += elapsed
            total['allocation_wall'] += elapsed

        def dispatch(function, args):
            m.clock()
            compiled_before = len(function.signatures)
            before = perf_counter()
            failure = None
            try:
                return function(*args)
            except BaseException as exc:
                failure = exc
                row['dispatch_error'] = repr(exc)
                raise
            finally:
                elapsed = perf_counter() - before
                compiled_after = len(function.signatures)
                compiled = compiled_after > compiled_before
                compilation_attempted = compiled or compiled_before == 0
                _record_work(m, work, previous)
                row['dispatches'] += 1
                row['kernel_wall'] += elapsed
                row['max_dispatch_wall'] = max(row['max_dispatch_wall'], elapsed)
                row['compilation_dispatches'] += int(compiled)
                row['compilation_attempts'] += int(compilation_attempted)
                row['last_signatures_before'] = compiled_before
                row['last_signatures_after'] = compiled_after
                total['compiled_dispatches'] += 1
                total['compilation_attempts'] += int(compilation_attempted)
                total['kernel_wall'] += elapsed
                total['max_dispatch_wall'] = max(total['max_dispatch_wall'], elapsed)
                if total['first_dispatch_wall'] is None:
                    total['first_dispatch_wall'] = elapsed
                if compilation_attempted:
                    total['compile_dispatches'] += int(compiled)
                    total['compile_dispatch_wall'] += elapsed
                else:
                    row['max_warm_dispatch_wall'] = max(row['max_warm_dispatch_wall'], elapsed)
                    total['max_warm_dispatch_wall'] = max(total['max_warm_dispatch_wall'], elapsed)
                if engine.last_visit is not None:
                    if control[3] >= 0:
                        engine.last_visit['current_neighbor'] = neighbors[int(control[3])]
                    if control[1] >= 0:
                        engine.last_visit['best_root_so_far'] = engine.qorder[int(control[1])]
                if failure is None:
                    m.clock()

        boundary = 0
        with m.phase('routing_seed'):
            for j, v in enumerate(neighbors):
                if engine.last_visit is not None:
                    engine.last_visit['current_neighbor'] = v
                count = dispatch(_seed_neighbor, (np.int64(j), source_ranks[j], sites[j],
                    starts, adjacency, costs, distance, parent, discovered,
                    discovery_counts, heap, work))
                boundary += int(count)
                if not count:
                    row['complete'] = True
                    return None
        with m.phase('routing_kernel'):
            done = False
            while not done:
                done = dispatch(_advance, (starts, adjacency, costs, source_ranks,
                    distance, settled, parent, discovered, discovery_counts,
                    settlement_order, settlement_counts, sums, counts, heap,
                    control, work, np.int64(CHUNK_POPS)))
        if control[1] < 0:
            row['complete'] = True
            return None
        before = perf_counter()
        try:
            with m.phase('routing_array_export'):
                mask = settled != INF
                for array in (costs, settled, parent, mask):
                    array.flags.writeable = False
                result = dict(anchor=int(control[1]), neighbors=tuple(neighbors),
                    starts=starts, adjacency=adjacency, costs=costs,
                    settled=settled, settled_mask=mask, parent=parent,
                    native_safe=True,
                    stats=dict(root_score=int(control[0]), labels=int(work[2]), pushes=int(work[0]),
                         pops=int(work[1]), early_stopped=bool(control[2]), boundary_sites=boundary))
                m.step('compiled_export_mask_item', n * degree)
                m.clock()
        finally:
            elapsed = perf_counter() - before
            row['conversion_wall'] += elapsed
            total['conversion_wall'] += elapsed
        row['complete'] = True
        return result
    finally:
        row['wall'] = perf_counter() - started
        row['semantic_work'] = dict(zip(WORK_NAMES, map(int, work)))
        total['query_wall'] += row['wall']
        total['completed_queries'] += int(row['complete'])
        total['incomplete_queries'] += int(not row['complete'])


def pack_python(engine, neighbors, costs_python, route, starts, adjacency):
    """Exact integer fallback using the same route/evaluation operators."""
    if route is None:
        return None
    root, distances, parents, stats = route
    degree, n = len(neighbors), len(engine.qorder)
    settled = np.empty((degree, n), dtype=object); settled.fill(0)
    mask = np.zeros((degree, n), dtype=np.bool_)
    parent = np.full((degree, n), UNKNOWN_PARENT, dtype=np.int64)
    for j, v in enumerate(neighbors):
        for q, value in distances[v].items():
            k = engine.rank[q]; settled[j, k] = value; mask[j, k] = True
            engine.m.step('fallback_settled_export')
        for q, p in parents[v].items():
            parent[j, engine.rank[q]] = NO_PARENT if p is None else engine.rank[p]
            engine.m.step('fallback_parent_export')
    costs = np.asarray(costs_python, dtype=object)
    for array in (costs, settled, mask, parent):
        array.flags.writeable = False
    engine.m.clock()
    return dict(anchor=engine.rank[root], neighbors=tuple(neighbors), starts=starts,
                adjacency=adjacency, costs=costs, settled=settled, settled_mask=mask,
                parent=parent, native_safe=False, stats=stats)
