"""Exact interleavings in the native embedder's frozen coordinate picture.

An order is merged with a selected subsequence, forward or reversed.  The
three integer costs are outside-chip reserved volume, reserved volume, and
source-edge rank span.  No packing, capacity test, or physical conversion
occurs here.  Coordinates belong to the current occupants of fixed slots;
the caller applies the returned order to those slots.

Spatial moves charge interval starts and ends when their endpoints are
emitted.  Contact-order moves charge a vertex's complete arms when it is
emitted.  In both cases a prefix pair is a sufficient state.  Preparation
and the dynamic program take O(|unit| * |rest| + n + |E|) work and use
separate int64 cost components rather than a scalar lexicographic weight.
"""

from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def _check_arrays(orders, coords, indptr, indices, monotone_axis):
    """Linear validation also keeps unchecked compiled indexing safe."""
    n = orders.shape[1]
    for axis in range(3):
        seen = np.zeros(n, dtype=np.bool_)
        for i in range(n):
            v = orders[axis, i]
            if v < 0 or v >= n or seen[v]:
                raise ValueError("each order must be a permutation of the vertices")
            seen[v] = True
    maximum = np.int64(1)
    for axis in range(2):
        for v in range(n):
            if coords[axis, v] < 1:
                raise ValueError("coordinates must be positive")
            maximum = max(maximum, coords[axis, v])
    if 0 <= monotone_axis < 2:
        for i in range(1, n):
            if (coords[monotone_axis, orders[monotone_axis, i]]
                    < coords[monotone_axis, orders[monotone_axis, i - 1]]):
                raise ValueError("spatial slots must be nondecreasing in their order")
    if indptr[0] != 0 or indptr[n] != indices.size:
        raise ValueError("invalid CSR offsets")
    for v in range(n):
        if (indptr[v] < 0 or indptr[v] > indptr[v + 1]
                or indptr[v + 1] > indices.size):
            raise ValueError("invalid CSR offsets")
        for e in range(indptr[v], indptr[v + 1]):
            if indices[e] < 0 or indices[e] >= n or indices[e] == v:
                raise ValueError("invalid CSR neighbor")
    return maximum


def _check_inputs(orders, coords, indptr, indices, chip_m, monotone_axis=-1):
    if orders.ndim != 2 or orders.shape[0] != 3:
        raise ValueError("orders must have shape (3, n)")
    n = orders.shape[1]
    if coords.shape != (2, n):
        raise ValueError("coords must have shape (2, n)")
    if indptr.shape != (n + 1,) or indices.ndim != 1 or indices.size % 2:
        raise ValueError("source must be an undirected graph in CSR form")
    limit = int(np.iinfo(np.int64).max)
    if chip_m < 1:
        raise ValueError("chip_m must be positive")
    if chip_m > limit // 2:
        raise OverflowError("chip extent exceeds safe int64 arithmetic")
    maximum = int(_check_arrays(orders, coords, indptr, indices, monotone_axis))
    # Check in Python integers, before any compiled cost arithmetic.  This
    # includes partially emitted spatial nets, whose endpoint charges may
    # be negative even though completed interval costs are nonnegative.
    if 2 * n * (maximum // 2 + 2) > limit:
        raise OverflowError("reserved-volume bounds exceed int64")
    if 3 * (indices.size // 2) * max(n - 1, 0) > limit:
        raise OverflowError("rank-span bounds exceed int64")


@njit(cache=True)
def _less(a0, a1, a2, b0, b1, b2):
    return a0 < b0 or (a0 == b0 and (a1 < b1 or (a1 == b1 and a2 < b2)))


@njit(cache=True)
def _interval_cost(lo, hi, lane, chip_m):
    first = (lo - 1) // 2
    last = hi // 2
    total = last - first + 1
    if lane > 2 * chip_m - 1:
        return total, total
    outside = max(0, last - chip_m + 1) - max(0, first - chip_m)
    return outside, total


@njit(cache=True)
def _ranks(order):
    result = np.empty(order.size, dtype=np.int64)
    for i in range(order.size):
        result[order[i]] = i
    return result


@njit(cache=True)
def _bounds(orders, coords, indptr, indices):
    """Orientation 0 is vertical, 1 horizontal; inactive bounds are -1."""
    n = orders.shape[1]
    trank = _ranks(orders[2])
    lo = np.full((2, n), -1, dtype=np.int64)
    hi = np.full((2, n), -1, dtype=np.int64)
    for v in range(n):
        for e in range(indptr[v], indptr[v + 1]):
            u = indices[e]
            orientation = 1 if trank[v] < trank[u] else 0
            value = coords[1 - orientation, u]
            if lo[orientation, v] < 0:
                lo[orientation, v] = value
                hi[orientation, v] = value
            else:
                lo[orientation, v] = min(lo[orientation, v], value)
                hi[orientation, v] = max(hi[orientation, v], value)
        if lo[0, v] >= 0 and lo[1, v] >= 0:
            for orientation in range(2):
                value = coords[1 - orientation, v]
                lo[orientation, v] = min(lo[orientation, v], value)
                hi[orientation, v] = max(hi[orientation, v], value)
    return lo, hi


@njit(cache=True)
def _score(orders, coords, indptr, indices, chip_m, rank_axis):
    lo, hi = _bounds(orders, coords, indptr, indices)
    outside = np.int64(0)
    volume = np.int64(0)
    span = np.int64(0)
    n = orders.shape[1]
    for orientation in range(2):
        for v in range(n):
            if lo[orientation, v] >= 0:
                out, size = _interval_cost(
                    lo[orientation, v], hi[orientation, v],
                    coords[orientation, v], chip_m,
                )
                outside += out
                volume += size
    for axis in range(3):
        if rank_axis >= 0 and axis != rank_axis:
            continue
        rank = _ranks(orders[axis])
        for v in range(n):
            for e in range(indptr[v], indptr[v + 1]):
                u = indices[e]
                if v < u:
                    span += abs(rank[v] - rank[u])
    return outside, volume, span


def score_layout(orders, coords, indptr, indices, chip_m):
    """Return the full three-component objective (isolates contribute zero)."""
    orders = np.asarray(orders, dtype=np.int64)
    coords = np.asarray(coords, dtype=np.int64)
    indptr = np.asarray(indptr, dtype=np.int64)
    indices = np.asarray(indices, dtype=np.int64)
    chip_m = int(chip_m)
    _check_inputs(orders, coords, indptr, indices, chip_m)
    return tuple(int(x) for x in _score(
        orders, coords, indptr, indices, chip_m, -1,
    ))


@njit(cache=True)
def _partition_positions(n, part, rest):
    pa = np.full(n, -1, dtype=np.int64)
    pb = np.full(n, -1, dtype=np.int64)
    for i in range(part.size):
        pa[part[i]] = i
    for j in range(rest.size):
        pb[rest[j]] = j
    return pa, pb


@njit(cache=True)
def _cut_costs(part, rest, pa, pb, indptr, indices):
    """Rank span is the sum of source-edge cuts after successive emissions."""
    p, q = part.size, rest.size
    before_a = np.zeros((q, p + 1), dtype=np.int64)
    before_b = np.zeros(q, dtype=np.int64)
    for j in range(q):
        v = rest[j]
        for e in range(indptr[v], indptr[v + 1]):
            u = indices[e]
            if pa[u] >= 0:
                before_a[j, pa[u] + 1] += 1
            elif pb[u] < j:
                before_b[j] += 1
        for i in range(1, p + 1):
            before_a[j, i] += before_a[j, i - 1]
    cuts = np.zeros((p + 1, q + 1), dtype=np.int64)
    for i in range(1, p + 1):
        v = part[i - 1]
        prior = 0
        for e in range(indptr[v], indptr[v + 1]):
            u = indices[e]
            if 0 <= pa[u] < i - 1:
                prior += 1
        cuts[i, 0] = cuts[i - 1, 0] + indptr[v + 1] - indptr[v] - 2 * prior
    for i in range(p + 1):
        for j in range(1, q + 1):
            v = rest[j - 1]
            cuts[i, j] = (cuts[i, j - 1] + indptr[v + 1] - indptr[v]
                          - 2 * (before_b[j - 1] + before_a[j - 1, i]))
    return cuts


@njit(cache=True)
def _contact_costs(part, rest, pa, pb, coords, indptr, indices, chip_m):
    """Costs indexed by emitted part index and consumed-rest count."""
    p, q = part.size, rest.size
    costs = np.zeros((p, q + 1, 2), dtype=np.int64)
    for i in range(p):
        v = part[i]
        # Earlier neighbors supply horizontal arms; later neighbors vertical.
        early_count = np.zeros(q + 1, dtype=np.int64)
        early_min = np.full(q + 1, -1, dtype=np.int64)
        early_max = np.full(q + 1, -1, dtype=np.int64)
        late_count = np.zeros(q + 1, dtype=np.int64)
        late_min = np.full(q + 1, -1, dtype=np.int64)
        late_max = np.full(q + 1, -1, dtype=np.int64)
        ne, nl = 0, 0
        emin, emax, lmin, lmax = -1, -1, -1, -1
        for e in range(indptr[v], indptr[v + 1]):
            u = indices[e]
            if pa[u] >= 0:
                if pa[u] < i:
                    value = coords[1, u]
                    emin = value if ne == 0 else min(emin, value)
                    emax = max(emax, value)
                    ne += 1
                else:
                    value = coords[0, u]
                    lmin = value if nl == 0 else min(lmin, value)
                    lmax = max(lmax, value)
                    nl += 1
            else:
                j = pb[u]
                early_count[j + 1] = 1
                early_min[j + 1] = coords[1, u]
                early_max[j + 1] = coords[1, u]
                late_count[j] = 1
                late_min[j] = coords[0, u]
                late_max[j] = coords[0, u]
        for j in range(1, q + 1):
            if early_count[j - 1]:
                if early_count[j]:
                    early_min[j] = min(early_min[j], early_min[j - 1])
                    early_max[j] = max(early_max[j], early_max[j - 1])
                else:
                    early_min[j] = early_min[j - 1]
                    early_max[j] = early_max[j - 1]
                early_count[j] += early_count[j - 1]
        for j in range(q - 1, -1, -1):
            if late_count[j + 1]:
                if late_count[j]:
                    late_min[j] = min(late_min[j], late_min[j + 1])
                    late_max[j] = max(late_max[j], late_max[j + 1])
                else:
                    late_min[j] = late_min[j + 1]
                    late_max[j] = late_max[j + 1]
                late_count[j] += late_count[j + 1]
        for j in range(q + 1):
            has_v = ne + early_count[j] > 0
            has_h = nl + late_count[j] > 0
            outside, volume = 0, 0
            if has_v:
                low, high = emin, emax
                if early_count[j]:
                    low = early_min[j] if ne == 0 else min(low, early_min[j])
                    high = max(high, early_max[j])
                if has_h:
                    low = min(low, coords[1, v])
                    high = max(high, coords[1, v])
                out, size = _interval_cost(low, high, coords[0, v], chip_m)
                outside += out
                volume += size
            if has_h:
                low, high = lmin, lmax
                if late_count[j]:
                    low = late_min[j] if nl == 0 else min(low, late_min[j])
                    high = max(high, late_max[j])
                if has_v:
                    low = min(low, coords[0, v])
                    high = max(high, coords[0, v])
                out, size = _interval_cost(low, high, coords[1, v], chip_m)
                outside += out
                volume += size
            costs[i, j, 0] = outside
            costs[i, j, 1] = volume
    return costs


@njit(cache=True)
def _spatial_costs(orders, coords, indptr, indices, axis,
                   part, rest, pa, pb, chip_m):
    p, q = part.size, rest.size
    n = orders.shape[1]
    trank = _ranks(orders[2])
    lo, hi = _bounds(orders, coords, indptr, indices)
    # For each part: prefix/suffix range differences, separated by whether
    # the net's (fixed) anchoring lane is outside the chip.
    da = np.zeros((p, q + 2, 4), dtype=np.int64)
    db = np.zeros((q, p + 2, 4), dtype=np.int64)
    changing = 1 - axis
    for v in range(n):
        if lo[changing, v] < 0:
            continue
        amin, amax, bmin, bmax = p, -1, q, -1
        for e in range(indptr[v], indptr[v + 1]):
            u = indices[e]
            endpoint = trank[v] < trank[u] if axis == 0 else trank[u] < trank[v]
            if endpoint:
                if pa[u] >= 0:
                    amin = min(amin, pa[u])
                    amax = max(amax, pa[u])
                else:
                    bmin = min(bmin, pb[u])
                    bmax = max(bmax, pb[u])
        if lo[0, v] >= 0 and lo[1, v] >= 0:
            if pa[v] >= 0:
                amin = min(amin, pa[v])
                amax = max(amax, pa[v])
            else:
                bmin = min(bmin, pb[v])
                bmax = max(bmax, pb[v])
        outside = 1 if coords[changing, v] > 2 * chip_m - 1 else 0
        if amax >= 0:
            da[amin, 0, outside] += 1
            da[amin, bmin + 1, outside] -= 1
            da[amax, bmax + 1, 2 + outside] += 1
        if bmax >= 0:
            db[bmin, 0, outside] += 1
            db[bmin, amin + 1, outside] -= 1
            db[bmax, amax + 1, 2 + outside] += 1
    slots = coords[axis, orders[axis]]
    ca = np.zeros((p, q + 1, 2), dtype=np.int64)
    cb = np.zeros((q, p + 1, 2), dtype=np.int64)
    for side in range(2):
        sequence = part if side == 0 else rest
        diff = da if side == 0 else db
        cost = ca if side == 0 else cb
        opposite_size = q if side == 0 else p
        for i in range(sequence.size):
            v = sequence[i]
            counts = np.zeros(4, dtype=np.int64)
            unary_inside, unary_size = 0, 0
            if lo[axis, v] >= 0:
                unary_inside, unary_size = _interval_cost(
                    lo[axis, v], hi[axis, v], 1, chip_m,
                )
            for j in range(opposite_size + 1):
                for kind in range(4):
                    counts[kind] += diff[i, j, kind]
                value = slots[i + j]
                first = (value - 1) // 2
                last = value // 2
                volume = ((counts[0] + counts[1]) * (1 - first)
                          + (counts[2] + counts[3]) * last + unary_size)
                outside = (-counts[0] * max(0, first - chip_m)
                           + counts[1] * (1 - first)
                           + counts[2] * max(0, last - chip_m + 1)
                           + counts[3] * last)
                outside += unary_size if value > 2 * chip_m - 1 else unary_inside
                cost[i, j, 0] = outside
                cost[i, j, 1] = volume
    return ca, cb


@njit(cache=True)
def _solve(orders, coords, indptr, indices, axis, part, rest, chip_m):
    p, q = part.size, rest.size
    pa, pb = _partition_positions(p + q, part, rest)
    cuts = _cut_costs(part, rest, pa, pb, indptr, indices)
    if axis == 2:
        ca = _contact_costs(part, rest, pa, pb, coords, indptr, indices, chip_m)
        cb = _contact_costs(rest, part, pb, pa, coords, indptr, indices, chip_m)
    else:
        ca, cb = _spatial_costs(
            orders, coords, indptr, indices, axis, part, rest, pa, pb, chip_m,
        )
    values = np.zeros((p + 1, q + 1, 3), dtype=np.int64)
    parent = np.zeros((p + 1, q + 1), dtype=np.uint8)
    for i in range(p + 1):
        for j in range(q + 1):
            if i == 0 and j == 0:
                continue
            if i > 0:
                out = values[i - 1, j, 0] + ca[i - 1, j, 0]
                size = values[i - 1, j, 1] + ca[i - 1, j, 1]
                span = values[i - 1, j, 2] + cuts[i, j]
            else:
                out, size, span = 0, 0, 0
            if j > 0:
                bo = values[i, j - 1, 0] + cb[j - 1, i, 0]
                bs = values[i, j - 1, 1] + cb[j - 1, i, 1]
                br = values[i, j - 1, 2] + cuts[i, j]
                if i == 0 or _less(bo, bs, br, out, size, span):
                    out, size, span = bo, bs, br
                    parent[i, j] = 1
            values[i, j, 0] = out
            values[i, j, 1] = size
            values[i, j, 2] = span
    result = np.empty(p + q, dtype=np.int64)
    i, j = p, q
    for k in range(p + q - 1, -1, -1):
        if parent[i, j] == 0:
            i -= 1
            result[k] = part[i]
        else:
            j -= 1
            result[k] = rest[j]
    return result, values[p, q]


def interleave(orders, coords, indptr, indices, axis, unit, chip_m):
    """Return the best strict improvement over forward/reversed unit merges.

    ``orders`` has rows x, y, contact; ``coords`` has x/y rows indexed by
    vertex.  Spatial coordinates must be nondecreasing in their orders and
    positive.  The source is a simple undirected graph in symmetric CSR.
    Input arrays are never modified.  Unit input order and duplicates have
    no effect: its forward order is taken from the current master order.
    """
    orders = np.asarray(orders, dtype=np.int64)
    coords = np.asarray(coords, dtype=np.int64)
    indptr = np.asarray(indptr, dtype=np.int64)
    indices = np.asarray(indices, dtype=np.int64)
    axis = int(axis)
    chip_m = int(chip_m)
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    _check_inputs(orders, coords, indptr, indices, chip_m, axis)
    n = orders.shape[1]
    selected = np.zeros(n, dtype=np.bool_)
    for v in unit:
        if not 0 <= int(v) < n:
            raise ValueError("unit contains an invalid vertex")
        selected[int(v)] = True
    order = orders[axis]
    part = np.ascontiguousarray(order[selected[order]])
    if part.size == 0 or n < 2:
        return None, False
    rest = np.ascontiguousarray(order[~selected[order]])
    baseline = _score(orders, coords, indptr, indices, chip_m, axis)
    result, best = _solve(orders, coords, indptr, indices, axis, part, rest, chip_m)
    flipped = False
    if part.size > 1:
        reverse, reverse_cost = _solve(
            orders, coords, indptr, indices, axis,
            np.ascontiguousarray(part[::-1]), rest, chip_m,
        )
        if tuple(reverse_cost) < tuple(best):
            result, best, flipped = reverse, reverse_cost, True
    if tuple(best) < tuple(baseline):
        return result, flipped
    return None, False
