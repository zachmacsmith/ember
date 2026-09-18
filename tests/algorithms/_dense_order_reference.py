# Frozen dense reference: factored source hash
# fc4560cc54307c562841b93601141f907bcbc502e504e7ffd6396aaa8df5b0d6.
# Preserved verbatim below for differential tests; never used by production.
"""Exact interleavings in the native embedder's frozen coordinate picture.

A partition may borrow either side from any of the three orders, forward or
reversed, with identical canonically oriented strand pairs solved once. The
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

import time

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


def check_cost_bounds(n, edge_count, chip_m, maximum):
    """Cheap Python-integer bounds for an already validated source and slots.

    Trusted sweep callers may check these once and use ``checked=False`` for
    their queries: permutations and fixed-slot reassignment preserve the bounds.
    """
    n, edge_count, chip_m, maximum = map(int, (n, edge_count, chip_m, maximum))
    limit = int(np.iinfo(np.int64).max)
    if n < 0 or edge_count < 0 or maximum < 1:
        raise ValueError("invalid source size or coordinate maximum")
    if chip_m < 1:
        raise ValueError("chip_m must be positive")
    if chip_m > limit // 2:
        raise OverflowError("chip extent exceeds safe int64 arithmetic")
    # Partial spatial endpoint charges can be negative; bound their magnitude
    # as well as the nonnegative cost of complete reservations.
    if 2 * n * (maximum // 2 + 2) > limit:
        raise OverflowError("reserved-volume bounds exceed int64")
    if 3 * edge_count * max(n - 1, 0) > limit:
        raise OverflowError("rank-span bounds exceed int64")


def _check_inputs(orders, coords, indptr, indices, chip_m, monotone_axis=-1):
    if orders.ndim != 2 or orders.shape[0] != 3:
        raise ValueError("orders must have shape (3, n)")
    n = orders.shape[1]
    if coords.shape != (2, n):
        raise ValueError("coords must have shape (2, n)")
    if indptr.shape != (n + 1,) or indices.ndim != 1 or indices.size % 2:
        raise ValueError("source must be an undirected graph in CSR form")
    # Reject an unsafe chip extent before a compiled call can coerce it.
    check_cost_bounds(n, indices.size // 2, chip_m, 1)
    maximum = int(_check_arrays(orders, coords, indptr, indices, monotone_axis))
    check_cost_bounds(n, indices.size // 2, chip_m, maximum)


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
def _score_from_bounds(orders, coords, indptr, indices, chip_m, rank_axis, lo, hi):
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


@njit(cache=True)
def _score(orders, coords, indptr, indices, chip_m, rank_axis):
    lo, hi = _bounds(orders, coords, indptr, indices)
    return _score_from_bounds(orders, coords, indptr, indices, chip_m, rank_axis, lo, hi)


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
                   part, rest, pa, pb, chip_m, trank, lo, hi):
    p, q = part.size, rest.size
    n = orders.shape[1]
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
def _prepare_transitions(orders, coords, indptr, indices, axis, part, rest,
                          chip_m, trank, lo, hi):
    p, q = part.size, rest.size
    pa, pb = _partition_positions(p + q, part, rest)
    cuts = _cut_costs(part, rest, pa, pb, indptr, indices)
    if axis == 2:
        ca = _contact_costs(part, rest, pa, pb, coords, indptr, indices, chip_m)
        cb = _contact_costs(rest, part, pb, pa, coords, indptr, indices, chip_m)
    else:
        ca, cb = _spatial_costs(
            orders, coords, indptr, indices, axis, part, rest, pa, pb, chip_m,
            trank, lo, hi,
        )
    return cuts, ca, cb


@njit(cache=True)
def _fill(part, rest, cuts, ca, cb):
    """Fill the merge grid and trace its exact winner; no graph preparation."""
    p, q = part.size, rest.size
    # Only the preceding value row is live; retain parents for traceback.
    values = np.zeros((2, q + 1, 3), dtype=np.int64)
    parent = np.zeros((p + 1, q + 1), dtype=np.uint8)
    for i in range(p + 1):
        row, previous = i % 2, 1 - i % 2
        for j in range(q + 1):
            if i == 0 and j == 0:
                continue
            if i > 0:
                out = values[previous, j, 0] + ca[i - 1, j, 0]
                size = values[previous, j, 1] + ca[i - 1, j, 1]
                span = values[previous, j, 2] + cuts[i, j]
            else:
                out, size, span = 0, 0, 0
            if j > 0:
                bo = values[row, j - 1, 0] + cb[j - 1, i, 0]
                bs = values[row, j - 1, 1] + cb[j - 1, i, 1]
                br = values[row, j - 1, 2] + cuts[i, j]
                if i == 0 or _less(bo, bs, br, out, size, span):
                    out, size, span = bo, bs, br
                    parent[i, j] = 1
            values[row, j, 0] = out
            values[row, j, 1] = size
            values[row, j, 2] = span
    result = np.empty(p + q, dtype=np.int64)
    i, j = p, q
    for k in range(p + q - 1, -1, -1):
        if parent[i, j] == 0:
            i -= 1
            result[k] = part[i]
        else:
            j -= 1
            result[k] = rest[j]
    return result, values[p % 2, q].copy()


@njit(cache=True)
def _solve_prepared(orders, coords, indptr, indices, axis, part, rest, chip_m,
                    trank, lo, hi):
    cuts, ca, cb = _prepare_transitions(
        orders, coords, indptr, indices, axis, part, rest, chip_m, trank, lo, hi)
    return _fill(part, rest, cuts, ca, cb)


@njit(cache=True)
def _solve(orders, coords, indptr, indices, axis, part, rest, chip_m):
    """Compatibility entry point for a single fixed-strand merge and probes."""
    trank = _ranks(orders[2])
    lo, hi = _bounds(orders, coords, indptr, indices)
    return _solve_prepared(orders, coords, indptr, indices, axis, part, rest,
                           chip_m, trank, lo, hi)


@njit(cache=True)
def _direct_score(orders, coords, indptr, indices, axis, candidate, chip_m):
    """A whole-set strand has one possible order and needs no merge grid."""
    changed = orders.copy()
    placed = coords.copy()
    changed[axis] = candidate
    if axis < 2:
        for i in range(len(candidate)):
            placed[axis, candidate[i]] = coords[axis, orders[axis, i]]
    return _score(changed, placed, indptr, indices, chip_m, axis)


def interleave(orders, coords, indptr, indices, axis, unit, chip_m, *,
               donors=None, accept_equal=True, deadline=None, info=None,
               checked=True):
    """Compare canonical optimal tracebacks while borrowing either partition side.

    Proper ``unit`` and its complement name the same query. Canonical side B
    is smaller (lexicographically smaller sorted vertices on ties); A is its
    complement. All solves use A first and B second, fixing DP traceback ties
    and minimizing rolling-row width independently of the nomination side.
    Borrow one side's sequence from a CURRENT donor order, forward or reversed;
    keep the other side in destination order. Complete ordered pairs are solved
    once; we never borrow both sides in one solve.

    Equal-cost tracebacks prefer change, genuine borrowing, cyclic donor order,
    forward direction, then borrowed side A before B. A sequence matching either
    destination direction has no borrowed priority. Only each DP's canonical
    traceback is considered, not every tied path. Empty nominations and n <= 1
    are no-ops; whole-set nominations use direct scoring. Destination strands
    are always included, even when ``donors`` restricts borrowing.

    ``accept_equal=False`` retains strict-only adoption for controlled probes.
    Deadlines are checked between candidate kernels; interrupted queries return
    their best completed candidate, including the initial incumbent.
    ``checked=False`` requires validated inputs and checked cost bounds.
    Input arrays are never modified.
    """
    preparation_start = time.perf_counter()
    orders = np.asarray(orders, dtype=np.int64)
    coords = np.asarray(coords, dtype=np.int64)
    indptr = np.asarray(indptr, dtype=np.int64)
    indices = np.asarray(indices, dtype=np.int64)
    axis = int(axis)
    chip_m = int(chip_m)
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    if checked:
        _check_inputs(orders, coords, indptr, indices, chip_m, axis)
    n = orders.shape[1]
    allowed = {0, 1, 2} if donors is None else {int(donor) for donor in donors}
    if not allowed <= {0, 1, 2}:
        raise ValueError("donors must contain only axes 0, 1, and 2")
    allowed.add(axis)
    selected = np.zeros(n, dtype=np.bool_)
    for v in unit:
        if not 0 <= int(v) < n:
            raise ValueError("unit contains an invalid vertex")
        selected[int(v)] = True
    size = int(np.count_nonzero(selected))
    whole = size == n and n > 1
    if whole:
        selected[:] = False  # special query: A = V, B = empty
    elif 0 < size < n:
        # Equal-size complements are disjoint: the one containing zero is
        # lexicographically smaller when each side is sorted by vertex id.
        if 2 * size > n or (2 * size == n and not selected[0]):
            selected = ~selected
    order = orders[axis]
    own = (np.ascontiguousarray(order[~selected[order]]),
           np.ascontiguousarray(order[selected[order]]))
    own_pair = (own[0].tobytes(), own[1].tobytes())
    own_keys = [{strand.tobytes(), strand[::-1].tobytes()} for strand in own]
    # Roles, spatial bounds and baseline stay fixed across both directions.
    trank = _ranks(orders[2])
    lo, hi = _bounds(orders, coords, indptr, indices)
    baseline = tuple(int(v) for v in _score_from_bounds(
        orders, coords, indptr, indices, chip_m, axis, lo, hi))
    metrics = dict(baseline_score=baseline, score=baseline, donor=axis,
                   donor_mask=1 << axis, borrowed=False, strict=False,
                   borrow_side=-1, borrow_size=0, candidate_pairs=0,
                   candidate_duplicates=0, complete=True, strand_solves=0, dp_cells=0,
                   direct_scores=0, preparation_wall=0.0, dp_wall=0.0,
                   transition_wall=0.0, direct_wall=0.0)
    if info is None:
        info = {}
    donor_order = ((axis + 1) % 3, (axis + 2) % 3, axis)
    candidates = {}
    if size and n > 1:
        sides = (0,) if whole else (0, 1)
        for priority, donor in enumerate(donor_order):
            if donor not in allowed:
                continue
            donor_ordered = orders[donor]
            strands = (donor_ordered[~selected[donor_ordered]],
                       donor_ordered[selected[donor_ordered]])
            for flipped in (False, True):
                for side in sides:
                    strand = strands[side]
                    strand = np.ascontiguousarray(strand[::-1] if flipped else strand)
                    strand_key = strand.tobytes()
                    key = ((strand_key, own_pair[1]) if side == 0 else
                           (own_pair[0], strand_key))
                    borrowed = strand_key not in own_keys[side]
                    provenance = (not borrowed, priority, flipped, side)
                    previous = candidates.get(key)
                    mask = 1 << donor
                    if previous is not None:
                        metrics["candidate_duplicates"] += 1
                        mask |= previous["mask"]
                        if provenance >= previous["provenance"]:
                            previous["mask"] = mask
                            continue
                    candidates[key] = dict(
                        part=strand if side == 0 else own[0],
                        rest=strand if side == 1 else own[1], donor=donor,
                        priority=priority, flipped=flipped, side=side,
                        size=strand.size, mask=mask, borrowed=borrowed,
                        provenance=provenance, incumbent_family=key == own_pair,
                    )
    metrics["candidate_pairs"] = len(candidates)
    # Enumeration follows the selected provenance, not the first pair alias.
    candidates = sorted(candidates.values(), key=lambda c:
                        (c["priority"], c["flipped"], c["side"]))
    metrics["preparation_wall"] = time.perf_counter() - preparation_start
    best, result, chosen = baseline, None, None
    best_tie = (1, 1, 2, False, 0)  # the unchanged incumbent
    for candidate in candidates:
        part, rest = candidate["part"], candidate["rest"]
        # The full-set incumbent score is already known and needs no kernel.
        if whole and candidate["incumbent_family"]:
            proposed, cost = part, baseline
        else:
            if deadline is not None and time.perf_counter() >= deadline:
                metrics["complete"] = False
                break
            if whole:
                direct_start = time.perf_counter()
                proposed = part
                cost = _direct_score(orders, coords, indptr, indices, axis, part, chip_m)
                metrics["direct_wall"] += time.perf_counter() - direct_start
                metrics["direct_scores"] += 1
            else:
                transition_start = time.perf_counter()
                cuts, ca, cb = _prepare_transitions(
                    orders, coords, indptr, indices, axis, part, rest, chip_m,
                    trank, lo, hi,
                )
                elapsed = time.perf_counter() - transition_start
                metrics["transition_wall"] += elapsed
                metrics["preparation_wall"] += elapsed
                dp_start = time.perf_counter()
                proposed, cost = _fill(part, rest, cuts, ca, cb)
                metrics["dp_wall"] += time.perf_counter() - dp_start
                metrics["strand_solves"] += 1
                metrics["dp_cells"] += (part.size + 1) * (rest.size + 1) - 1
            cost = tuple(int(v) for v in cost)
        if candidate["incumbent_family"] and cost > baseline:
            raise AssertionError("destination merge lost its available incumbent")
        changed = not np.array_equal(proposed, order)
        tie = (not changed, not candidate["borrowed"], candidate["priority"],
               candidate["flipped"], candidate["side"])
        if cost < best or (cost == best and tie < best_tie):
            best, result, chosen, best_tie = cost, proposed, candidate, tie
    strict = best < baseline
    if result is None or np.array_equal(result, order) or (not accept_equal and not strict):
        metrics["score"] = baseline
        info.update(metrics)
        return None, False
    metrics.update(score=best, donor=chosen["donor"], donor_mask=chosen["mask"],
                   borrowed=chosen["borrowed"], strict=strict,
                   borrow_side=chosen["side"], borrow_size=chosen["size"])
    info.update(metrics)
    return result, bool(chosen["flipped"])
