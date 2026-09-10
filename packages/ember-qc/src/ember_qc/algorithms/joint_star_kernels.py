"""C019 integer array kernels; every import and cold JIT is caller-clocked."""
import numpy as np
from numba import njit

INF = 1 << 62


@njit(cache=False, boundscheck=True)
def bfs_batch(starts, adjacency, available, distance, parent, queue, head, tail, work):
    """C018 BFS operation, resumed after at most 256 dequeues for observation."""
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
def contact_counts(starts, adjacency, owner, chain, neighbor_index, degree, work):
    """C018 exact actual-coupler count, including all selected owner changes."""
    counts = np.zeros(degree, dtype=np.int64)
    for q in chain:
        for j in range(starts[q], starts[q + 1]):
            v = owner[adjacency[j]]; work[1] += 1
            if v >= 0:
                k = neighbor_index[v]
                if k >= 0:
                    counts[k] += 1
    return counts


@njit(cache=False, boundscheck=True)
def cost_batch(cache, neighbors, weights, output, begin, end, work):
    for q in range(begin, end):
        value = 0
        for j in range(len(neighbors)):
            value += weights[j] * max(0, cache[neighbors[j], q] - 1)
            work[0] += 1
        output[q] = value


@njit(cache=False, boundscheck=True)
def cardinality(required, histogram):
    """Maximum matching count for nested physical-degree domains."""
    capacity = histogram.copy(); site_degree = 0; count = 0
    for demand in required:  # ascending source degrees
        site_degree = max(site_degree, demand)
        while site_degree < len(capacity) and capacity[site_degree] == 0:
            site_degree += 1
        if site_degree == len(capacity):
            break
        capacity[site_degree] -= 1; count += 1
    return count


@njit(cache=False, boundscheck=True)
def proxy_tail(minima, assigned):
    ordered = np.sort(minima); result = 0
    for i in range(assigned):
        if ordered[i] == INF:
            raise RuntimeError('cardinality exceeds leaves with finite domain')
        result += ordered[i]
    return result


@njit(cache=False, boundscheck=True)
def root_batch(starts, adjacency, available, degrees, maximum_degree, demands,
               required, costs, baseline, center_cost, sites, begin, end, work):
    k = len(demands); base = 1 + k + baseline.sum()
    deficits = np.empty(end - begin, dtype=np.int64)
    scores = np.empty(end - begin, dtype=np.int64)
    for ii in range(begin, end):
        r = sites[ii]
        histogram = np.zeros(maximum_degree + 1, dtype=np.int64)
        minima = np.full(k, INF, dtype=np.int64)
        for jj in range(starts[r], starts[r + 1]):
            q = adjacency[jj]; work[0] += 1
            if not available[q]:
                continue
            histogram[degrees[q]] += 1
            for v in range(k):
                work[1] += 1
                if degrees[q] >= demands[v]:
                    minima[v] = min(minima[v], costs[v, q] - baseline[v])
        assigned = cardinality(required, histogram)
        deficits[ii - begin] = k - assigned
        scores[ii - begin] = base + center_cost[r] + proxy_tail(minima, assigned)
    return deficits, scores


@njit(cache=False, boundscheck=True)
def boundary_summary(sites, degrees, maximum_degree, demands, costs, baseline, work):
    k = len(demands)
    histogram = np.zeros(maximum_degree + 1, dtype=np.int64)
    first = np.full(k, INF, dtype=np.int64)
    first_site = np.full(k, -1, dtype=np.int64)
    second = np.full(k, INF, dtype=np.int64)
    for q in sites:  # seeded target rank, so equal minima have stable sites
        histogram[degrees[q]] += 1
        for v in range(k):
            work[0] += 1
            if degrees[q] < demands[v]:
                continue
            value = costs[v, q] - baseline[v]
            if value < first[v]:
                second[v] = first[v]; first[v] = value; first_site[v] = q
            elif value < second[v]:
                second[v] = value
    return histogram, first, first_site, second


@njit(cache=False, boundscheck=True)
def growth_batch(starts, adjacency, available, tree, boundary, degrees, demands,
                 required, costs, baseline, cache, center_neighbors, center_weights,
                 near, size, histogram, first, first_site, second, sites, begin, end, work):
    k = len(demands); base = size + 1 + k + baseline.sum()
    deficits = np.empty(end - begin, dtype=np.int64)
    scores = np.empty(end - begin, dtype=np.int64)
    for ii in range(begin, end):
        q = sites[ii]; hist = histogram.copy(); hist[degrees[q]] -= 1
        minima = first.copy()
        for v in range(k):
            if first_site[v] == q:
                minima[v] = second[v]
        for jj in range(starts[q], starts[q + 1]):
            p = adjacency[jj]; work[0] += 1
            if not available[p] or tree[p] or boundary[p]:
                continue
            hist[degrees[p]] += 1
            for v in range(k):
                work[1] += 1
                if degrees[p] >= demands[v]:
                    minima[v] = min(minima[v], costs[v, p] - baseline[v])
        assigned = cardinality(required, hist); center_value = 0
        for j in range(len(center_neighbors)):
            distance = min(near[j], cache[center_neighbors[j], q])
            center_value += center_weights[j] * max(0, distance - 1)
            work[1] += 1
        deficits[ii - begin] = k - assigned
        scores[ii - begin] = base + center_value + proxy_tail(minima, assigned)
    return deficits, scores


@njit(cache=False, boundscheck=True)
def hungarian_step(cost, allowed, weighted, penalty, u, v, p, way, minimum, used, column, work):
    """One complete rectangular column scan; caller observes clock between scans."""
    real_columns = cost.shape[1]; columns = len(p) - 1
    used[column] = True; row = p[column]; delta = INF; next_column = -1
    for j in range(1, columns + 1):
        if used[j]:
            continue
        work[0] += 1
        permitted = j > real_columns or allowed[row - 1, j - 1]
        if permitted:
            value = penalty if j > real_columns else (cost[row - 1, j - 1] if weighted else 0)
            reduced = value - u[row] - v[j]
            if reduced < minimum[j]:
                minimum[j] = reduced; way[j] = column
        # Existing slack can reach a column even when this row's edge is absent.
        if minimum[j] < delta:
            delta = minimum[j]; next_column = j
    if next_column < 0 or delta == INF:
        raise RuntimeError('dummy-completed assignment lost an augmenting path')
    for j in range(columns + 1):
        if used[j]:
            u[p[j]] += delta; v[j] -= delta
        elif minimum[j] < INF:
            minimum[j] -= delta
    return next_column
