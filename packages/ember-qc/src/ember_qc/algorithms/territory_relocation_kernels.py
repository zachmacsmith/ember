"""C018 array kernels; lazy import/JIT belongs to the constructor clock."""
import numpy as np
from numba import njit


@njit(cache=False, boundscheck=True)
def bfs_batch(starts, adjacency, available, distance, parent, queue, head, tail, work):
    """Observe time every 256 dequeues; resume the entire remaining frontier."""
    end = min(tail, head + 256)
    while head < end:
        q = queue[head]; head += 1; work[0] += 1
        for j in range(starts[q], starts[q + 1]):
            p = adjacency[j]; work[1] += 1
            if available[p] and distance[p] < 0:
                distance[p] = distance[q] + 1; parent[p] = q
                queue[tail] = p; tail += 1
    return head, tail


@njit(cache=False, boundscheck=True)
def root_scores(cache, neighbors, weights, sites):
    scores = np.ones(len(sites), dtype=np.float64)
    for i in range(len(sites)):
        q = sites[i]
        for j in range(len(neighbors)):
            scores[i] += weights[j] * max(0, cache[neighbors[j], q] - 1)
    return scores


@njit(cache=False, boundscheck=True)
def endpoints(starts, adjacency, owner, discovery, neighbor_index, near, work):
    result = np.full(len(near), -1, dtype=np.int64)
    for q in discovery:
        for j in range(starts[q], starts[q + 1]):
            v = owner[adjacency[j]]; work[1] += 1
            if v >= 0:
                k = neighbor_index[v]
                if k >= 0 and near[k] > 1 and result[k] < 0:
                    result[k] = q
    return result


@njit(cache=False, boundscheck=True)
def extension_score(cache, neighbors, weights, near, path):
    updated = near.copy(); delta = float(len(path))
    for j in range(len(neighbors)):
        for q in path:
            updated[j] = min(updated[j], cache[neighbors[j], q])
        delta += weights[j] * (max(0, updated[j] - 1) - max(0, near[j] - 1))
    return delta, updated


@njit(cache=False, boundscheck=True)
def contact_counts(starts, adjacency, owner, chain, neighbor_index, degree, work):
    counts = np.zeros(degree, dtype=np.int64)
    for q in chain:
        for j in range(starts[q], starts[q + 1]):
            v = owner[adjacency[j]]; work[1] += 1
            if v >= 0:
                k = neighbor_index[v]
                if k >= 0:
                    counts[k] += 1
    return counts
