"""Probe smarter early-termination targets on n40 d0.7.

Monkeypatch the bounded router's _assemble to try different `targets=` choices
and measure ACL drift + visit savings vs the region-only (no early-stop) bound.
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import sys, os, time, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source
from ember_qc.embedding_backend import (is_valid_embedding, reconstruct_path,
                                         weighted_multisource_dijkstra as wmd)
from ember_qc.algorithms.pathfinder import embed_pathfinder, _BIG
from ember_qc.algorithms.pf_bounded import PathFinderBoundedRouter

targets = make_targets(); src = make_source("ER", 40, 0.7); tgt = targets["pegasus_6"]
SEEDS = [0, 1, 2]

# We inject a per-call "v_old" by remembering the seed footprint passed to _bfs_ball.
# Simpler: re-derive in a subclass that knows v during _steiner_route.
class Probe(PathFinderBoundedRouter):
    target_mode = "none"   # set per run
    def _steiner_route(self, v, cost, forbidden_extra=None):
        self._cur_vold = set(self.chains.get(v, ()))
        return super()._steiner_route(v, cost, forbidden_extra)
    def _assemble(self, placed, cost, forbidden_extra, chain_set, boundary, adj, region):
        mode = self.target_mode
        if region is None or mode == "none":
            return _assemble_base(self, placed, cost, forbidden_extra, chain_set,
                                  boundary, adj, region, targets_fn=None)
        vold = getattr(self, "_cur_vold", set()) & region
        union_b = set()
        for u in placed: union_b |= boundary[u]
        def targets_fn(u):
            if mode == "vold":
                tg = vold - boundary[u] - (forbidden_extra | chain_set[u])
            elif mode == "vold_or_bnd":
                tg = vold if vold else (union_b - boundary[u])
                tg = tg - (forbidden_extra | chain_set[u])
            else:
                tg = set()
            return tg or None
        return _assemble_base(self, placed, cost, forbidden_extra, chain_set,
                              boundary, adj, region, targets_fn=targets_fn)

def _assemble_base(self, placed, cost, forbidden_extra, chain_set, boundary, adj,
                   region, targets_fn):
    dist_by_u, pred_by_u = {}, {}
    for u in placed:
        b = boundary[u]
        if not b: continue
        forbidden = forbidden_extra | chain_set[u]
        tg = targets_fn(u) if targets_fn else None
        dist, pred = wmd(adj, b, cost, forbidden=forbidden, targets=tg,
                         visit_counter=self._visits)
        if dist: dist_by_u[u] = dist; pred_by_u[u] = pred
    if not dist_by_u: return None
    reach, total = {}, {}
    for dist in dist_by_u.values():
        for q, d in dist.items():
            reach[q] = reach.get(q, 0) + 1; total[q] = total.get(q, 0.0) + d
    root = max(reach, key=lambda q: (reach[q], -total[q], -q))
    tree = {root}
    for u in sorted(dist_by_u, key=lambda u: (dist_by_u[u].get(root, _BIG), u)):
        dist = dist_by_u[u]; best_t, best_d = None, _BIG
        for t in tree:
            d = dist.get(t, _BIG)
            if d < best_d or (d == best_d and (best_t is None or t < best_t)):
                best_d, best_t = d, t
        if best_t is None or best_d >= _BIG: continue
        tree.update(reconstruct_path(pred_by_u[u], best_t))
    return sorted(tree)

def run(mode):
    accv = []
    for s in SEEDS:
        Probe.target_mode = mode
        t0 = time.perf_counter()
        r = embed_pathfinder(src, tgt, timeout=60.0, seed=s, router_cls=Probe,
                             base_method="minorminer", region_radius=1,
                             region_max_expand=2, early_stop=False, region_enabled=True)
        dt = time.perf_counter() - t0
        emb = r.get("embedding") or {}
        valid = bool(emb) and is_valid_embedding(emb, src, tgt)
        acl = sum(len(c) for c in emb.values())/len(emb) if emb else float("nan")
        accv.append((valid, acl, dt, r.get("target_node_visits", 0)))
    return (all(a[0] for a in accv), st.mean(a[1] for a in accv),
            st.mean(a[2] for a in accv), st.mean(a[3] for a in accv))

print("R=1, varying early-termination target (paired):")
ref = run("none")
print(f"  none(region only): valid={ref[0]} ACL={ref[1]:.3f} t={ref[2]:.2f} vis={ref[3]:.0f}")
for mode in ("vold", "vold_or_bnd"):
    v, a, t, vis = run(mode)
    print(f"  {mode:12s}:    valid={v} ACL={a:.3f} ({100*(a-ref[1])/ref[1]:+.1f}%) "
          f"t={t:.2f} (x{t/ref[2]:.2f}) vis={vis:.0f} (x{vis/ref[3]:.2f})")
