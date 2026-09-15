"""Demand-derived bars and the single conservative accounting for the native core.

Axis 0 owns vertical bars (their x coordinate); axis 1 owns horizontal bars.
Each bar's targets are coordinates on the OTHER axis. Node IDs here are dense
integers; the adapter preserves the caller's labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from numba import njit


@dataclass
class Source:
    labels: tuple
    isolates: tuple
    indptr: np.ndarray
    indices: np.ndarray

    @classmethod
    def from_graph(cls, graph):
        if graph.is_directed() or graph.is_multigraph():
            raise ValueError("native attraction requires a simple undirected source")
        if any(u == v for u, v in graph.edges()):
            raise ValueError("native attraction does not support source self-loops")
        labels = tuple(v for v in graph if graph.degree(v))
        isolates = tuple(v for v in graph if not graph.degree(v))
        ids = {v: i for i, v in enumerate(labels)}
        ptr = [0]
        indices = []
        for v in labels:
            indices.extend(sorted(ids[u] for u in graph.neighbors(v)))
            ptr.append(len(indices))
        return cls(labels, isolates, np.asarray(ptr, dtype=np.int64),
                   np.asarray(indices, dtype=np.int64))


@dataclass
class Book:
    active: np.ndarray
    lo: np.ndarray
    hi: np.ndarray
    target_ptr: np.ndarray
    target_idx: Tuple[np.ndarray, np.ndarray]
    outside: int
    reserved: int

    @property
    def score(self):
        return self.outside, self.reserved

    @property
    def guard_lo(self):
        return (self.lo - 1) // 2

    @property
    def guard_hi(self):
        return self.hi // 2


@njit(cache=True)
def _book(orders, coords, indptr, indices, chip_m):
    n = orders.shape[1]
    trank = np.empty(n, dtype=np.int64)
    for i in range(n):
        trank[orders[2, i]] = i
    active = np.zeros((2, n), dtype=np.bool_)
    for v in range(n):
        for k in range(indptr[v], indptr[v + 1]):
            u = indices[k]
            active[0 if trank[u] < trank[v] else 1, v] = True
    ptr = np.zeros((2, n + 1), dtype=np.int64)
    # Each orientation has one target per source edge plus mixed corners.
    target0 = np.empty(len(indices) // 2 + n, dtype=np.int64)
    target1 = np.empty(len(indices) // 2 + n, dtype=np.int64)
    lo = np.ones((2, n), dtype=np.int64)
    hi = np.zeros((2, n), dtype=np.int64)
    outside = 0
    reserved = 0
    for axis in range(2):
        targets = target0 if axis == 0 else target1
        count = 0
        for v in range(n):
            ptr[axis, v] = count
            if not active[axis, v]:
                continue
            a = np.iinfo(np.int64).max
            b = -1
            if active[1 - axis, v]:
                targets[count] = v
                count += 1
                a = coords[1 - axis, v]
                b = a
            for k in range(indptr[v], indptr[v + 1]):
                u = indices[k]
                belongs = trank[u] < trank[v] if axis == 0 else trank[u] > trank[v]
                if belongs:
                    targets[count] = u
                    count += 1
                    p = coords[1 - axis, u]
                    a = min(a, p)
                    b = max(b, p)
            lo[axis, v] = a
            hi[axis, v] = b
            low = (a - 1) // 2
            high = b // 2
            width = high - low + 1
            reserved += width
            if coords[axis, v] > 2 * chip_m - 1:
                outside += width
            else:
                outside += max(high - chip_m + 1, 0) - max(low - chip_m, 0)
        ptr[axis, n] = count
    return (active, lo, hi, ptr, target0[:ptr[0, n]],
            target1[:ptr[1, n]], outside, reserved)


def make_book(orders, coords, indptr, indices, chip_m):
    active, lo, hi, ptr, idx0, idx1, outside, reserved = _book(
        orders, coords, indptr, indices, chip_m)
    return Book(active, lo, hi, ptr, (idx0, idx1), int(outside), int(reserved))


@njit(cache=True)
def complete_coordinates(orders, coords, active, capacity):
    """Fill dormant slots once, before freezing a proposal sweep's slots."""
    result = coords.copy()
    n = orders.shape[1]
    for axis in range(2):
        previous = -1
        first = -1
        for j in range(n):
            v = orders[axis, j]
            if not active[axis, v]:
                continue
            if first < 0:
                first = j
                for k in range(j):
                    result[axis, orders[axis, k]] = coords[axis, v]
            elif previous + 1 < j:
                left = coords[axis, orders[axis, previous]]
                right = coords[axis, v]
                for k in range(previous + 1, j):
                    result[axis, orders[axis, k]] = left + (
                        (right - left) * (k - previous) // (j - previous))
            previous = j
        if first < 0:
            for j in range(n):
                result[axis, orders[axis, j]] = 1 + j // capacity
        else:
            for j in range(previous + 1, n):
                result[axis, orders[axis, j]] = result[axis, orders[axis, previous]]
    return result


def capacity_ok(book, coords, capacity, extent_m):
    """Independent event-scan certificate; used at decoder/output boundaries."""
    guard_lo, guard_hi = book.guard_lo, book.guard_hi
    for axis in range(2):
        events = {}
        for v in np.flatnonzero(book.active[axis]):
            lane = int(coords[axis, v])
            a, b = int(guard_lo[axis, v]), int(guard_hi[axis, v])
            if not 1 <= lane <= 2 * extent_m - 1 or not 0 <= a <= b < extent_m:
                return False
            line = events.setdefault(lane, {})
            line[a] = line.get(a, 0) + 1
            line[b + 1] = line.get(b + 1, 0) - 1
        for line in events.values():
            depth = 0
            for p in sorted(line):
                depth += line[p]
                if depth > capacity:
                    return False
    return True


def packing_problem(axis, orders, coords, book):
    """Compile one conditional pack, keeping all endpoint identities explicit."""
    order = orders[axis][book.active[axis, orders[axis]]]
    rank = np.full(orders.shape[1], -1, dtype=np.int64)
    rank[order] = np.arange(len(order), dtype=np.int64)
    opposite = np.flatnonzero(book.active[1 - axis])
    first = np.empty(len(opposite), dtype=np.int64)
    last = np.empty(len(opposite), dtype=np.int64)
    ptr, idx = book.target_ptr[1 - axis], book.target_idx[1 - axis]
    for i, v in enumerate(opposite):
        targets = rank[idx[ptr[v]:ptr[v + 1]]]
        if not len(targets) or np.any(targets < 0):
            raise AssertionError("active bar has a missing target")
        first[i], last[i] = targets.min(), targets.max()
    return (order, book.guard_lo[axis, order], book.guard_hi[axis, order],
            coords[1 - axis, opposite], first, last)
