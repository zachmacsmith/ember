"""B030 array operations; imported inside the constructor's measured deadline.

Only generic arrays and unweighted shortest paths are used. No embedder imports.
Every cache belongs to one target and is keyed by an immutable exact site set.
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


class Arrays:
    def __init__(self, target, rank, meter):
        self.m = meter
        self.n = len(target)
        self.rank = rank
        self.fields = {}
        rows, cols = [], []
        for q in range(self.n):
            for r in target[q]:
                rows.append(q); cols.append(r)
                meter.step('target_pack_arc')
        with meter.phase('array_target_setup'):
            rows, cols = np.asarray(rows), np.asarray(cols)
            self.csr = csr_matrix((np.ones(len(rows), dtype=np.uint8), (rows, cols)),
                                  shape=(self.n, self.n))
            self.links = np.zeros((self.n, self.n), dtype=np.bool_)
            self.links[rows, cols] = True
            ids = np.arange(self.n, dtype=np.int64)
            residual, z = np.divmod(ids, 12)
            residual, j = np.divmod(residual, 2)
            residual, k = np.divmod(residual, 4)
            u, w = np.divmod(residual, 25)
            self.coords = np.stack((u, w, k, j, z), axis=1)
            self.offsets = np.asarray([(a, b) for a in range(-24, 25)
                                      for b in range(-24, 25) if a or b], dtype=np.int64)
            self.ranked = np.asarray(sorted(target, key=rank.__getitem__), dtype=np.int64)
            meter.clock()

    def field(self, sites):
        key = frozenset(sites)
        if not key:
            raise ValueError('distance field needs a nonempty site set')
        with self.m.phase('distance_fields'):
            self.m.step('distance_field_request')
            if key not in self.fields:
                indices = np.asarray(sorted(key), dtype=np.int32)
                self.m.clock()
                self.m.kinds['distance_field_calls_started'] += 1
                values = dijkstra(self.csr, directed=False, indices=indices,
                                  unweighted=True, min_only=True)
                # Cooperative call: completed SciPy work is charged even on timeout.
                self.m.kinds['distance_field_calls_returned'] += 1
                self.m.step('distance_field_target_size', self.n)
                if not np.all(np.isfinite(values)):
                    raise ValueError('connected ideal target required')
                if not np.all(values == np.floor(values)):
                    raise ValueError('nonintegral unweighted distance')
                values.flags.writeable = False
                self.m.clock()
                self.fields[key] = values
                self.m.step('distance_field_created')
            else:
                self.m.step('distance_field_cache_hit')
            return self.fields[key]

    def distance(self, left, right):
        values = self.field(left)
        self.m.step('distance_target_site', len(right))
        result = int(min(values[q] for q in right))
        self.m.clock()
        return result

    def translations(self, patch, labels):
        """All feasible defined translations, retaining lexicographic offsets."""
        with self.m.phase('patch_destinations'):
            sites = np.asarray(patch, dtype=np.int64)
            u, w, k, j, z = self.coords[sites].T
            a, b = self.offsets.T
            parallel = np.where(u[None, :] == 0, a[:, None], b[:, None])
            orthogonal = np.where(u[None, :] == 0, b[:, None], a[:, None])
            ww = w[None, :] + orthogonal
            jj = np.bitwise_xor(j[None, :], parallel & 1)
            zz = z[None, :] + (parallel + j[None, :]) // 2
            valid = ((ww >= 0) & (ww < 25) & (zz >= 0) & (zz < 12)).all(axis=1)
            indices = np.flatnonzero(valid)
            mapped = ((((u[None, :] * 25 + ww[indices]) * 4 + k[None, :])
                       * 2 + jj[indices]) * 12 + zz[indices])
            inside = np.zeros(self.n, dtype=np.bool_); inside[sites] = True
            valid = ((labels[mapped] < 0) | inside[mapped]).all(axis=1)
            if len(patch) > 1:
                valid &= (np.diff(np.sort(mapped, axis=1), axis=1) != 0).all(axis=1)
            for i, q in enumerate(patch):
                for h in range(i):
                    if self.links[q, patch[h]]:
                        valid &= self.links[mapped[:, i], mapped[:, h]]
                    self.m.step('patch_internal_pair')
            self.m.step('translation_site_image', len(self.offsets) * len(patch))
            self.m.clock()
            return self.offsets[indices[valid]], mapped[valid]

    def guide(self, patch, mapped, chains, labels, source):
        """Mean unweighted residual-obligation distance; never admission energy."""
        with self.m.phase('proposal_guide'):
            if len(mapped) == 0:
                return np.empty(0)
            patch_set = frozenset(patch)
            groups = {}
            for column, q in enumerate(patch):
                groups.setdefault(int(labels[q]), []).append(column)
            total, terms = np.zeros(len(mapped), dtype=np.float64), 0
            for u in sorted(groups):
                for v in [u] + sorted(source[u]):
                    residual = chains[v] - patch_set
                    if not residual:
                        continue
                    values = self.field(residual)
                    distance = values[mapped[:, groups[u]]].min(axis=1)
                    total += np.maximum(0., distance - 1.)
                    terms += 1
                    self.m.step('guide_site_distance', len(mapped) * len(groups[u]))
            self.m.clock()
            return total / terms if terms else total

    def sample(self, scores, draw):
        with self.m.phase('proposal_sampling'):
            if not len(scores):
                return None
            weights = np.exp(-(scores - scores.min()))
            cumulative = np.cumsum(weights)
            if not np.isfinite(cumulative[-1]) or cumulative[-1] <= 0:
                raise ValueError('invalid proposal probability mass')
            index = min(len(scores)-1, int(np.searchsorted(
                cumulative, draw * cumulative[-1], side='right')))
            self.m.step('proposal_probability', len(scores))
            self.m.clock()
            return index
