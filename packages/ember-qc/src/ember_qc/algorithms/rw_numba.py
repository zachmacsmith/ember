"""
Experimental (NEGATIVE RESULT — not used in production; not auto-imported).

numba-compiled node-weighted Dijkstra for Reweave routing, tested two ways:
  * over the FULL target graph  -> ~24% SLOWER than the bounded pure-Python router
    (it explores the whole fabric per route instead of a small region);
  * over the BOUNDED region with a persistent +inf cost array so per-route setup
    is O(region) not O(N), composed with dirty-set + spur (== the production
    `reweave` recipe but with the compiled kernel) -> a WASH, within noise of
    pure-Python `reweave` (e.g. n40 d0.7 Pegasus-6: 1.74s vs 1.74s; identical
    or marginally better ACL; valid; deterministic).

Conclusion: compiling the routing inner loop does not speed up the optimized
Reweave. Bounded-region routing has already shrunk each Dijkstra to a small
neighbourhood where the compiled kernel's per-node win is cancelled by call/setup
overhead, and the compiled-C++ `minorminer` base call dominates total runtime
(70-84%, profiled). Reweave's wall-clock is >= minorminer's by construction
(it runs minorminer then improves), so this is a fairness check, not a regression:
the ~1.3x overhead is the improvement pass, not interpreter overhead. A C++
rewrite of the same kernel would hit the same ceiling.

Kept (un-registered, importable via `import ember_qc.algorithms.rw_numba`) only as
the reproducible artifact behind the paper's Limitations finding. Registers the
`reweave-numba` algorithm on import for measurement; `__init__.py` does NOT
import this module, so production stays pure-Python and numba stays optional.
"""
from __future__ import annotations

import numpy as np

from ember_qc.registry import register_algorithm
from ember_qc.algorithms.reweave import ReweaveRouter, _ReweaveBase
from ember_qc.algorithms.rw_bounded import ReweaveBoundedRouter
from ember_qc.algorithms.rw_dirtyset import DirtySetRouter
from ember_qc.algorithms.rw_spur import SpurRouter
from ember_qc.embedding_backend import reconstruct_path

_BIG = 1.0e18

try:
    from numba import njit
    HAVE_NUMBA = True
except Exception:  # pragma: no cover
    HAVE_NUMBA = False


if HAVE_NUMBA:
    @njit(cache=True)
    def _msd(indptr, indices, cost, sources, dist, pred, hk, ht, hidx, touched):
        BIG = 1.0e18
        hsize = 0; counter = 0; nt = 0
        for j in range(sources.shape[0]):
            s = sources[j]; c = cost[s]
            if c < dist[s]:
                if dist[s] >= BIG:
                    touched[nt] = s; nt += 1
                dist[s] = c; pred[s] = -1
                hk[hsize] = c; ht[hsize] = counter; hidx[hsize] = s; counter += 1
                i = hsize; hsize += 1
                while i > 0:
                    p = (i - 1) // 2
                    if hk[p] < hk[i] or (hk[p] == hk[i] and ht[p] <= ht[i]): break
                    hk[p], hk[i] = hk[i], hk[p]; ht[p], ht[i] = ht[i], ht[p]; hidx[p], hidx[i] = hidx[i], hidx[p]
                    i = p
        while hsize > 0:
            d = hk[0]; u = hidx[0]; hsize -= 1
            hk[0] = hk[hsize]; ht[0] = ht[hsize]; hidx[0] = hidx[hsize]
            i = 0
            while True:
                l = 2 * i + 1; r = 2 * i + 2; sm = i
                if l < hsize and (hk[l] < hk[sm] or (hk[l] == hk[sm] and ht[l] < ht[sm])): sm = l
                if r < hsize and (hk[r] < hk[sm] or (hk[r] == hk[sm] and ht[r] < ht[sm])): sm = r
                if sm == i: break
                hk[sm], hk[i] = hk[i], hk[sm]; ht[sm], ht[i] = ht[i], ht[sm]; hidx[sm], hidx[i] = hidx[i], hidx[sm]
                i = sm
            if d > dist[u]: continue
            for ei in range(indptr[u], indptr[u + 1]):
                w = indices[ei]; cw = cost[w]
                if cw >= BIG: continue
                nd = d + cw
                if nd < dist[w]:
                    if dist[w] >= BIG:
                        touched[nt] = w; nt += 1
                    dist[w] = nd; pred[w] = u
                    hk[hsize] = nd; ht[hsize] = counter; hidx[hsize] = w; counter += 1
                    i = hsize; hsize += 1
                    while i > 0:
                        p = (i - 1) // 2
                        if hk[p] < hk[i] or (hk[p] == hk[i] and ht[p] <= ht[i]): break
                        hk[p], hk[i] = hk[i], hk[p]; ht[p], ht[i] = ht[i], ht[p]; hidx[p], hidx[i] = hidx[i], hidx[p]
                        i = p
        return nt


class NumbaBoundedRouter(ReweaveBoundedRouter):
    """Bounded-region routing with the compiled Dijkstra over the region (persistent
    +inf cost array => O(region) per-route setup)."""

    def __init__(self, source, target, **kwargs):
        super().__init__(source, target, **kwargs)
        q = self.qubits
        self._n = len(q)
        self._idx = {node: i for i, node in enumerate(q)}
        self._node = list(q)
        indptr = np.empty(self._n + 1, dtype=np.int64)
        ind = []
        indptr[0] = 0
        for i, node in enumerate(q):
            for w in self.adj[node]:
                ind.append(self._idx[w])
            indptr[i + 1] = len(ind)
        self._indptr = indptr
        self._indices = np.asarray(ind, dtype=np.int64)
        nnz = self._indices.shape[0]
        self._dist = np.full(self._n, _BIG, dtype=np.float64)
        self._pred = np.full(self._n, -1, dtype=np.int64)
        self._cost = np.full(self._n, _BIG, dtype=np.float64)   # persistent +inf
        cap = self._n + nnz + 8
        self._hk = np.empty(cap, dtype=np.float64)
        self._ht = np.empty(cap, dtype=np.int64)
        self._hidx = np.empty(cap, dtype=np.int64)
        self._touched = np.empty(cap, dtype=np.int64)

    def _steiner_route(self, v, cost, forbidden_extra=None):
        if not HAVE_NUMBA or not self.region_enabled:
            return super()._steiner_route(v, cost, forbidden_extra)
        self.routes_built += 1
        forbidden_extra = forbidden_extra or set()
        placed = [u for u in self.src_adj[v] if self.chains.get(u)]
        if not placed:
            return [self._seed_qubit()]

        chain_set = {u: set(self.chains[u]) for u in placed}
        boundary = {}
        for u in placed:
            cu = chain_set[u]
            b = {w for q in self.chains[u] for w in self.adj[q] if w not in cu}
            boundary[u] = b - forbidden_extra
        center = set(self.chains.get(v, ()))
        seed = set(center)
        for u in placed:
            seed |= chain_set[u]

        idx, node = self._idx, self._node
        ca, dist, pred, touched = self._cost, self._dist, self._pred, self._touched
        radius = self.region_radius
        for _ in range(self.region_max_expand + 1):
            region = self._bfs_ball(seed, radius)
            # set region costs (O(region)); forbidden_extra -> +inf
            for qn in region:
                ca[idx[qn]] = _BIG if qn in forbidden_extra else cost.get(qn, 1.0)
            dist_by_u, pred_by_u = {}, {}
            for u in placed:
                b = boundary[u] & region
                if not b:
                    continue
                saved = [(idx[qn], ca[idx[qn]]) for qn in chain_set[u] if qn in region]
                for qn in chain_set[u]:
                    if qn in region:
                        ca[idx[qn]] = _BIG
                src = np.fromiter((idx[w] for w in sorted(b)), dtype=np.int64, count=len(b))
                nt = _msd(self._indptr, self._indices, ca, src, dist, pred,
                          self._hk, self._ht, self._hidx, touched)
                self._visits[0] += nt
                du, pu = {}, {}
                for k in range(nt):
                    qi = int(touched[k]); qn = node[qi]
                    du[qn] = dist[qi]
                    pp = int(pred[qi]); pu[qn] = node[pp] if pp >= 0 else None
                    dist[qi] = _BIG; pred[qi] = -1
                for qi, cv in saved:
                    ca[qi] = cv
                if du:
                    dist_by_u[u] = du; pred_by_u[u] = pu
            # reset region costs to +inf (O(region))
            for qn in region:
                ca[idx[qn]] = _BIG

            if dist_by_u:
                tree = self._assemble_tree(dist_by_u, pred_by_u)
                ts = set(tree)
                if all(not boundary[u] or not ts.isdisjoint(boundary[u]) for u in placed):
                    return tree
            radius *= 2
        # unbounded fallback (pure-Python baseline) — guarantees coverage
        return ReweaveRouter._steiner_route(self, v, cost, forbidden_extra)

    @staticmethod
    def _assemble_tree(dist_by_u, pred_by_u):
        reach, total = {}, {}
        for dist in dist_by_u.values():
            for q, dd in dist.items():
                reach[q] = reach.get(q, 0) + 1; total[q] = total.get(q, 0.0) + dd
        root = max(reach, key=lambda q: (reach[q], -total[q], -q))
        tree = {root}
        for u in sorted(dist_by_u, key=lambda u: (dist_by_u[u].get(root, _BIG), u)):
            dist = dist_by_u[u]
            best_t, best_d = None, _BIG
            for t in tree:
                d = dist.get(t, _BIG)
                if d < best_d or (d == best_d and (best_t is None or t < best_t)):
                    best_d, best_t = d, t
            if best_t is None or best_d >= _BIG:
                continue
            tree.update(reconstruct_path(pred_by_u[u], best_t))
        return sorted(tree)


class _NumbaOptRouter(SpurRouter, DirtySetRouter, NumbaBoundedRouter):
    """numba Dijkstra over the bounded region + dirty-set + spur."""
    pass


@register_algorithm("reweave-numba")
class ReweaveNumba(_ReweaveBase):
    _params = {"router_cls": _NumbaOptRouter, "base_method": "minorminer"}
