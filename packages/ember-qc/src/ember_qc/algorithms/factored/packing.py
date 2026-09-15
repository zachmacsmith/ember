"""Exact conditional packing for the native three-order model.

The moved-axis order and the other coordinates are fixed. Both capacity
directions become forward coordinate-separation constraints. A minimum-weight
closure of coordinate thresholds minimizes (outside reservations, reservations)
exactly. Residual source reachability chooses the componentwise-smallest optimum.

All graph construction and flow arithmetic use checked int64 capacities. In
particular, this module does not use scipy's int32 maximum-flow implementation.
"""
from __future__ import annotations

import time

import numpy as np
from numba import njit


_I64_MAX = int(np.iinfo(np.int64).max)


@njit(cache=True)
def _predecessors(own_lo, own_hi, opposite_lines, first, last, capacity):
    n = len(own_lo)
    same = np.full(n, -1, np.int64)
    cross = np.full(n, -1, np.int64)
    if n > capacity:
        # Compress elementary brick segments: a long interval need not allocate
        # memory proportional to the coordinate magnitude.
        endpoints = np.unique(np.concatenate((own_lo, own_hi + 1)))
        counts = np.zeros(len(endpoints) - 1, np.int64)
        recent = np.zeros((len(endpoints) - 1, capacity), np.int64)
        for j in range(n):
            a = np.searchsorted(endpoints, own_lo[j])
            b = np.searchsorted(endpoints, own_hi[j] + 1)
            pred = -1
            for q in range(a, b):
                c = counts[q]
                slot = c % capacity
                if c >= capacity:
                    pred = max(pred, recent[q, slot])
                recent[q, slot] = j
                counts[q] = c + 1
            same[j] = pred
    indices = np.argsort(opposite_lines)
    a = 0
    while a < len(indices):
        b = a + 1
        while b < len(indices) and opposite_lines[indices[b]] == opposite_lines[indices[a]]:
            b += 1
        if b - a > capacity:
            starts = np.sort(first[indices[a:b]])
            ends = np.sort(last[indices[a:b]])
            for k in range(capacity, b - a):
                j = starts[k]
                cross[j] = max(cross[j], ends[k - capacity])
        a = b
    return same, cross


@njit(cache=True)
def _domains(same, cross, limit):
    """Exact coordinate bounds; all predecessor arcs point forward in rank."""
    n = len(same)
    lower = np.ones(n, np.int64)
    upper = np.full(n, limit, np.int64)
    for j in range(n):
        if cross[j] >= j:
            return lower, upper, False
        lo = lower[j - 1] if j else 1
        if same[j] >= 0:
            lo = max(lo, lower[same[j]] + 1)
        if cross[j] >= 0:
            lo = max(lo, 2 * (lower[cross[j]] // 2) + 3)
        lower[j] = lo
        if lo > limit:
            return lower, upper, False
    for j in range(n - 1, -1, -1):
        if j:
            upper[j - 1] = min(upper[j - 1], upper[j])
        if same[j] >= 0:
            i = same[j]
            upper[i] = min(upper[i], upper[j] - 1)
        if cross[j] >= 0:
            i = cross[j]
            upper[i] = min(upper[i], 2 * ((upper[j] - 3) // 2) + 1)
    return lower, upper, True


@njit(cache=True)
def _coefficients(n, opposite_lines, first, last, chip_m):
    # First dimension: endpoint minima/maxima. Second: on-chip/off-chip lane.
    coeff = np.zeros((2, 2, n), np.int64)
    for k in range(len(first)):
        outside = 1 if opposite_lines[k] > 2 * chip_m - 1 else 0
        coeff[0, outside, first[k]] += 1
        coeff[1, outside, last[k]] += 1
    return coeff


@njit(cache=True)
def _unary_delta(i, line, coeff, width, own_outside, chip_m, weight):
    beta = line // 2
    beta_prev = (line - 1) // 2
    alpha = (line - 1) // 2
    alpha_prev = (line - 2) // 2
    db, da = beta - beta_prev, alpha - alpha_prev
    total = ((coeff[1, 0, i] + coeff[1, 1, i]) * db
             - (coeff[0, 0, i] + coeff[0, 1, i]) * da)
    outside = (coeff[1, 1, i] * db - coeff[0, 1, i] * da
               + coeff[1, 0, i] * (max(beta - chip_m + 1, 0)
                                    - max(beta_prev - chip_m + 1, 0))
               - coeff[0, 0, i] * (max(alpha - chip_m, 0)
                                    - max(alpha_prev - chip_m, 0)))
    if line == 2 * chip_m:
        outside += width[i] - own_outside[i]
    return weight * outside + total


@njit(cache=True)
def _add_arc(head, target, link, residual, used, u, v, capacity):
    target[used] = v
    residual[used] = capacity
    link[used] = head[u]
    head[u] = used
    target[used + 1] = u
    residual[used + 1] = 0
    link[used + 1] = head[v]
    head[v] = used + 1
    return used + 2


@njit(cache=True)
def _closure_graph(lower, upper, same, cross, coeff, width, own_outside,
                   chip_m, weight):
    n = len(lower)
    offset = np.zeros(n + 1, np.int64)
    for i in range(n):
        offset[i + 1] = offset[i] + upper[i] - lower[i]
    source = offset[n]
    sink = source + 1
    costs = np.empty(source, np.int64)
    absolute = np.int64(0)
    negative = np.int64(0)
    for i in range(n):
        for line in range(lower[i] + 1, upper[i] + 1):
            q = offset[i] + line - lower[i] - 1
            value = _unary_delta(i, line, coeff, width, own_outside, chip_m, weight)
            costs[q] = value
            absolute += abs(value)
            if value < 0:
                negative -= value
    infinite = absolute + 1
    # Unary + monotonic thresholds + order + two predecessor families. The
    # latter each originate in a subset of the existing variable thresholds.
    # A predecessor can serve several destinations, so reserve by rank*lines.
    max_forward = (2 * source + (3 * n) * (upper.max() if n else 0) + 1)
    head = np.full(source + 2, -1, np.int64)
    target = np.empty(2 * max_forward, np.int64)
    link = np.empty(2 * max_forward, np.int64)
    residual = np.empty(2 * max_forward, np.int64)
    used = 0
    for i in range(n):
        for line in range(lower[i] + 1, upper[i] + 1):
            q = offset[i] + line - lower[i] - 1
            value = costs[q]
            if value > 0:
                used = _add_arc(head, target, link, residual, used, q, sink, value)
            elif value < 0:
                used = _add_arc(head, target, link, residual, used, source, q, -value)
            if line > lower[i] + 1:
                used = _add_arc(head, target, link, residual, used, q, q - 1, infinite)
    for j in range(n):
        for kind in range(3):
            i = j - 1 if kind == 0 else (same[j] if kind == 1 else cross[j])
            if i < 0:
                continue
            for line in range(lower[i] + 1, upper[i] + 1):
                required = line if kind == 0 else (line + 1 if kind == 1
                                                    else 2 * (line // 2) + 3)
                if required <= lower[j]:
                    continue
                # Domain propagation guarantees the consequent is a variable
                # threshold, not a forced-false coordinate beyond upper[j].
                u = offset[i] + line - lower[i] - 1
                v = offset[j] + required - lower[j] - 1
                used = _add_arc(head, target, link, residual, used, u, v, infinite)
    return head, target[:used], link[:used], residual[:used], offset, infinite, negative


@njit(cache=True)
def _global_labels(head, target, link, residual, source, sink, height, current,
                   queue, excess, in_queue):
    """Residual distances to sink, then to source in the disconnected part.

    The second BFS lets disconnected excess return to the source without
    repeated global relabels resetting its progress.
    """
    n = len(head)
    height[:] = 2 * n + 1
    height[sink] = 0
    queue[0] = sink
    front, back = 0, 1
    while front < back:
        v = queue[front]
        front += 1
        e = head[v]
        while e >= 0:
            u = target[e]
            if u != source and height[u] == 2 * n + 1 and residual[e ^ 1] > 0:
                height[u] = height[v] + 1
                queue[back] = u
                back += 1
            e = link[e]
    height[source] = n
    queue[0] = source
    front, back = 0, 1
    while front < back:
        v = queue[front]
        front += 1
        e = head[v]
        while e >= 0:
            u = target[e]
            if height[u] == 2 * n + 1 and residual[e ^ 1] > 0:
                height[u] = height[v] + 1
                queue[back] = u
                back += 1
            e = link[e]
    current[:] = head
    in_queue[:] = False
    back = 0
    for v in range(n):
        if v != source and v != sink and excess[v] > 0:
            queue[back] = v
            in_queue[v] = True
            back += 1
    return back


@njit(cache=True)
def _push_relabel(head, target, link, residual, source, sink):
    """Int64 FIFO push-relabel; modifies residual capacities in place."""
    n = len(head)
    excess = np.zeros(n, np.int64)
    height = np.zeros(n, np.int64)
    current = head.copy()
    queue = np.empty(n, np.int64)
    in_queue = np.zeros(n, np.bool_)
    e = head[source]
    while e >= 0:
        amount = residual[e]
        if amount:
            residual[e] = 0
            residual[e ^ 1] += amount
            excess[target[e]] += amount
            excess[source] -= amount
        e = link[e]
    count = _global_labels(head, target, link, residual, source, sink,
                           height, current, queue, excess, in_queue)
    front, back = 0, count % n
    work = 0
    threshold = max(4 * len(target), n)
    while count:
        v = queue[front]
        front = (front + 1) % n
        count -= 1
        in_queue[v] = False
        while excess[v] > 0:
            e = current[v]
            if e < 0:
                best = 3 * n + 1
                e = head[v]
                while e >= 0:
                    if residual[e] > 0:
                        best = min(best, height[target[e]] + 1)
                    work += 1
                    e = link[e]
                if best == 3 * n + 1:
                    raise RuntimeError("positive preflow has no residual return path")
                height[v] = best
                current[v] = head[v]
                continue
            u = target[e]
            work += 1
            if residual[e] > 0 and height[v] == height[u] + 1:
                amount = min(excess[v], residual[e])
                residual[e] -= amount
                residual[e ^ 1] += amount
                excess[v] -= amount
                was_empty = excess[u] == 0
                excess[u] += amount
                if was_empty and u != source and u != sink and not in_queue[u]:
                    queue[back] = u
                    back = (back + 1) % n
                    count += 1
                    in_queue[u] = True
            else:
                current[v] = link[e]
        if work >= threshold and count:
            count = _global_labels(head, target, link, residual, source, sink,
                                   height, current, queue, excess, in_queue)
            front, back = 0, count % n
            work = 0
    reachable = np.zeros(n, np.bool_)
    reachable[source] = True
    queue[0] = source
    front, back = 0, 1
    while front < back:
        v = queue[front]
        front += 1
        e = head[v]
        while e >= 0:
            u = target[e]
            if residual[e] > 0 and not reachable[u]:
                reachable[u] = True
                queue[back] = u
                back += 1
            e = link[e]
    if reachable[sink]:
        raise RuntimeError("maximum-flow residual still reaches the sink")
    return excess[sink], reachable


@njit(cache=True)
def _objective(lines, own_lo, own_hi, opposite_lines, first, last, chip_m):
    outside = np.int64(0)
    total = np.int64(0)
    for i in range(len(lines)):
        width = own_hi[i] - own_lo[i] + 1
        total += width
        outside += (width if lines[i] > 2 * chip_m - 1 else
                    max(own_hi[i] - chip_m + 1, 0) - max(own_lo[i] - chip_m, 0))
    for j in range(len(first)):
        lo = (lines[first[j]] - 1) // 2
        hi = lines[last[j]] // 2
        width = hi - lo + 1
        total += width
        outside += (width if opposite_lines[j] > 2 * chip_m - 1 else
                    max(hi - chip_m + 1, 0) - max(lo - chip_m, 0))
    return outside, total


def _integer_array(values, name):
    arr = np.asarray(values)
    if arr.ndim != 1 or (arr.size and arr.dtype.kind not in "iu"):
        raise ValueError(f"{name} must be a one-dimensional integer array")
    if arr.size and (int(arr.min()) < 0 or int(arr.max()) >= _I64_MAX):
        raise ValueError(f"{name} is outside the supported nonnegative int64 range")
    return np.asarray(arr, dtype=np.int64)


def pack_axis(order, own_lo, own_hi, opposite_lines, first, last, *,
              capacity, chip_m, extent_m):
    """Return the smallest exact lexicographic optimum, or ``None`` if infeasible.

    ``own_lo/hi`` are inclusive reserved-brick intervals aligned with ``order``.
    Opposite bars have fixed lane coordinates and first/last endpoint RANKS in
    this order. Output coordinates range from 1 through ``2*extent_m-1``.
    The objective counts outside-chip reserved volume first, total volume second.
    """
    started = time.perf_counter()
    n = len(order)
    if len(set(order)) != n:
        raise ValueError("order contains duplicate variables")
    for name, value in (("capacity", capacity), ("chip_m", chip_m), ("extent_m", extent_m)):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    capacity, chip_m, extent_m = int(capacity), int(chip_m), int(extent_m)
    if chip_m > extent_m:
        raise ValueError("extent_m must include the physical chip")
    own_lo = _integer_array(own_lo, "own_lo")
    own_hi = _integer_array(own_hi, "own_hi")
    opposite_lines = _integer_array(opposite_lines, "opposite_lines")
    first = _integer_array(first, "first")
    last = _integer_array(last, "last")
    if len(own_lo) != n or len(own_hi) != n or np.any(own_hi < own_lo):
        raise ValueError("own intervals must be nonempty and aligned with order")
    if len(first) != len(last) or len(first) != len(opposite_lines):
        raise ValueError("opposite lines and endpoint ranks must have equal lengths")
    if (np.any(opposite_lines < 1) or np.any(last < first)
            or (len(last) and int(last.max()) >= n)):
        raise ValueError("invalid opposite lane or endpoint rank")

    # Bound every intermediate before entering compiled int64 arithmetic. Each
    # endpoint coordinate is monotone in the threshold expansion, so its total
    # variation is at most extent_m-1. No tuning constant enters the encoding.
    width_sum = sum(int(b) - int(a) + 1 for a, b in zip(own_lo, own_hi))
    maximum_total = width_sum + len(first) * extent_m
    weight = maximum_total + 1
    endpoint_variation = 2 * len(first) * (extent_m - 1)
    variation_bound = weight * (width_sum + endpoint_variation) + endpoint_variation
    limit = 2 * extent_m - 1
    if (maximum_total * (weight + 1) >= _I64_MAX or variation_bound >= _I64_MAX // 2
            or limit >= _I64_MAX or n * max(limit - 1, 0) >= np.iinfo(np.intp).max // 16):
        raise OverflowError("packing objective or threshold graph exceeds checked int64 bounds")
    info = {"pack_wall": 0.0, "flow_nodes": 0, "flow_arcs": 0,
            "objective": None, "infeasible": False, "encoding_weight": weight}

    def finish(lines):
        info["pack_wall"] = time.perf_counter() - started
        return lines, info

    if not n:
        info["objective"] = (0, 0)
        return finish(np.empty(0, dtype=np.int64))
    same, cross = _predecessors(own_lo, own_hi, opposite_lines, first, last, capacity)
    lower, upper, feasible = _domains(same, cross, limit)
    if not feasible:
        info["infeasible"] = True
        return finish(None)
    if np.array_equal(lower, upper):
        info["objective"] = tuple(map(int, _objective(
            lower, own_lo, own_hi, opposite_lines, first, last, chip_m)))
        return finish(lower)
    width = own_hi - own_lo + 1
    own_outside = np.maximum(own_hi - chip_m + 1, 0) - np.maximum(own_lo - chip_m, 0)
    coeff = _coefficients(n, opposite_lines, first, last, chip_m)
    graph_started = time.perf_counter()
    head, target, link, residual, offset, infinite, negative = _closure_graph(
        lower, upper, same, cross, coeff, width, own_outside, chip_m, weight)
    info["graph_wall"] = time.perf_counter() - graph_started
    source, sink = len(head) - 2, len(head) - 1
    flow_started = time.perf_counter()
    flow, reachable = _push_relabel(head, target, link, residual, source, sink)
    info["flow_wall"] = time.perf_counter() - flow_started
    if flow >= infinite:
        raise RuntimeError("propagated feasible domains produced an infeasible closure")
    lines = lower.copy()
    for i in range(n):
        lines[i] += int(np.count_nonzero(reachable[offset[i]:offset[i + 1]]))
    objective = tuple(map(int, _objective(lines, own_lo, own_hi, opposite_lines, first, last, chip_m)))
    base = tuple(map(int, _objective(lower, own_lo, own_hi, opposite_lines, first, last, chip_m)))
    if objective[0] * weight + objective[1] != base[0] * weight + base[1] + int(flow) - int(negative):
        raise RuntimeError("closure cut and decoded reservation objective disagree")
    info.update(objective=objective, flow_nodes=len(head), flow_arcs=len(target) // 2,
                encoding_infinite=int(infinite))
    return finish(lines)
