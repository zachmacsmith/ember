"""Quick-verify + parameter sweep for the rw_bounded (S3) variant.

1. Contract check: variant registers, returns valid embeddings.
2. ACL/identity check vs baseline on a few (cell, seed) pairs.
3. Radius x early_stop sweep on the n40 d0.7 key speed cell (paired timing).
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import sys, os, time, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source

import ember_qc.algorithms.rw_bounded as pfb  # noqa: F401  (registers)
from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.reweave import embed_reweave, ReweaveRouter
from ember_qc.algorithms.rw_bounded import ReweaveBoundedRouter

print("registered reweave-bounded:", "reweave-bounded" in ALGORITHM_REGISTRY)
print("registered reweave-bounded-region:", "reweave-bounded-region" in ALGORITHM_REGISTRY)

targets = make_targets()

def run(router_cls, src, tgt, seed, **params):
    t0 = time.perf_counter()
    r = embed_reweave(src, tgt, timeout=60.0, seed=seed,
                         router_cls=router_cls, base_method="minorminer", **params)
    dt = time.perf_counter() - t0
    emb = r.get("embedding") or {}
    valid = bool(emb) and is_valid_embedding(emb, src, tgt)
    acl = (sum(len(c) for c in emb.values()) / len(emb)) if emb else float("nan")
    return valid, acl, dt, r.get("target_node_visits", 0)

print("\n== identity / validity check (paired, baseline vs variant) ==")
for (fam, n, p, tn) in [("ER",20,0.5,"pegasus_6"), ("ER",30,0.7,"pegasus_6"), ("ER",30,0.5,"zephyr_4")]:
    src = make_source(fam, n, p); tgt = targets[tn]
    for s in (0,1):
        bv, ba, bt, bvis = run(ReweaveRouter, src, tgt, s)
        vv, va, vt, vvis = run(ReweaveBoundedRouter, src, tgt, s,
                               region_radius=2, region_max_expand=2, early_stop=True)
        rv, ra, rt, rvis = run(ReweaveBoundedRouter, src, tgt, s,
                               region_radius=2, region_max_expand=2, early_stop=False)
        print(f"{fam}_n{n}_d{p}_{tn} s{s}: "
              f"base(valid={bv},ACL={ba:.3f},t={bt:.2f},vis={bvis}) | "
              f"bounded(valid={vv},ACL={va:.3f},t={vt:.2f},vis={vvis}) | "
              f"region-only(valid={rv},ACL={ra:.3f},t={rt:.2f},vis={rvis})")

print("\n== radius x early_stop sweep on n40 d0.7 (paired vs baseline) ==")
src = make_source("ER", 40, 0.7); tgt = targets["pegasus_6"]
SEEDS = [0, 1, 2]
# baseline per seed
base = {}
for s in SEEDS:
    base[s] = run(ReweaveRouter, src, tgt, s)
bm_acl = st.mean(base[s][1] for s in SEEDS)
bm_t = st.mean(base[s][2] for s in SEEDS)
bm_vis = st.mean(base[s][3] for s in SEEDS)
print(f"baseline:                 ACL={bm_acl:.3f}  t={bm_t:.2f}  vis={bm_vis:.0f}")
for R in (1, 2, 3):
    for es in (True, False):
        accv = []
        for s in SEEDS:
            accv.append(run(ReweaveBoundedRouter, src, tgt, s,
                            region_radius=R, region_max_expand=2, early_stop=es))
        allvalid = all(a[0] for a in accv)
        macl = st.mean(a[1] for a in accv)
        mt = st.mean(a[2] for a in accv)
        mvis = st.mean(a[3] for a in accv)
        dacl = 100*(macl - bm_acl)/bm_acl
        print(f"R={R} early_stop={str(es):5s}: valid={allvalid} ACL={macl:.3f} "
              f"({dacl:+.1f}%)  t={mt:.2f} (x{mt/bm_t:.2f})  vis={mvis:.0f} (x{mvis/bm_vis:.2f})")
