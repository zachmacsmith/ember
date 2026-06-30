"""
docs/candidate-algorithms/data/learn_order.py
=============================================
The LEARNING arm of the search-guidance study: can a model pick / produce a good
vertex order per instance, capturing the (deterministic) portfolio's gain without
paying its ~6x cost?

Deterministic baseline (mmfork leaderboard):
  - best single fixed order (cuthill) ~ -1.6..-2.2% ACL vs stock minorminer;
  - portfolio (per-instance best of 5 good orders) ~ -5% ACL & half the variance,
    but ~6x the wall-clock (it runs every order).

Two cheap, local learned approaches (no GPU; ceiling-probe discipline — if these
don't beat the best fixed order, a heavy GNN almost certainly won't either):

  (A) ORDER SELECTOR — graph-level features -> which fixed order to use. Trained on
      cached per-order ACLs (no model-in-the-loop search). If it picks the
      per-instance winner it matches the portfolio at 1x cost.

  (B) PER-VERTEX LINEAR SCORE — features @ weights -> order, weights hill-climbed
      with the forked minorminer in the loop (decode-aware). Tests whether a
      *generated* order can beat the fixed heuristics.

Instance-disjoint train/test. Reports held-out test ACL for: stock MM, best fixed
order, oracle/portfolio, the selector, and the learned score. Writes
learn_order_results.json and (if it wins) search_weights.json for `mmfork-learned`.

Usage:  python learn_order.py [--smoke] [n_workers]
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import networkx as nx  # noqa: E402
import dwave_networkx as dnx  # noqa: E402

from ember_qc.algorithms.search_orders import ORDERINGS  # noqa: E402
from ember_qc.algorithms.learned_order import (  # noqa: E402
    FEATURES, vertex_feature_matrix, learned_order,
)

ORDER_SET = ["cuthill", "spectral", "mcs", "minfill", "degeneracy", "bfs"]
EVAL_SEEDS = [0, 1]
PKG_WEIGHTS = os.path.join(
    HERE, "..", "..", "..", "packages", "ember-qc", "src", "ember_qc",
    "algorithms", "search_weights.json")


# --------------------------------------------------------------------------- #
# instance generation (instance-disjoint splits via disjoint seed ranges)
# --------------------------------------------------------------------------- #
def gen_instances(split: str, smoke: bool):
    rng_cells = [(n, d) for n in (20, 30, 40, 50) for d in (0.3, 0.5, 0.7)]
    if smoke:
        rng_cells = [(20, 0.5), (30, 0.6)]
    base = 1000 if split == "train" else 9000
    count = (2 if smoke else (6 if split == "train" else 4))
    out = []
    k = 0
    for (n, d) in rng_cells:
        for r in range(count):
            g = nx.gnp_random_graph(n, d, seed=base + k)
            g = nx.convert_node_labels_to_integers(g)
            if nx.is_connected(g):
                out.append((f"{split}_n{n}_d{d}_r{r}", g))
            k += 1
    return out


def graph_level_features(G: nx.Graph) -> list:
    deg = [d for _, d in G.degree()]
    n = G.number_of_nodes()
    dens = nx.density(G)
    return [
        n / 50.0, dens,
        float(np.mean(deg)) / max(1, n), float(np.std(deg)) / max(1, n),
        float(np.mean(list(nx.clustering(G).values()))),
        (max(deg) - min(deg)) / max(1, n),
        nx.number_of_edges(G) / (n * n),
    ]


# --------------------------------------------------------------------------- #
# worker: evaluate one instance under default + each fixed order (mean over seeds)
# --------------------------------------------------------------------------- #
def _eval_instance(args):
    name, G, target_name = args
    sys.path.insert(0, "/Users/dabh/ember/external/minorminer-fork/minorminer")
    import _minorminer as mmfork
    from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
    tgt = dnx.pegasus_graph(6) if target_name == "P6" else dnx.zephyr_graph(4)
    adj = build_adjacency(tgt)
    S, T = list(G.edges()), list(tgt.edges())
    DEF = dict(max_no_improvement=10, timeout=1000, tries=10, chainlength_patience=10)

    def acl_for(order):
        vals = []
        for s in EVAL_SEEDS:
            kw = dict(DEF)
            if order is not None:
                kw["var_order"] = order
            e = mmfork.find_embedding(S, T, random_seed=s, **kw)
            e = {k: v for k, v in e.items() if v}
            if len(e) == G.number_of_nodes() and is_valid_embedding(e, G, tgt, adj=adj):
                vals.append(sum(len(c) for c in e.values()) / len(e))
        return float(np.mean(vals)) if vals else None

    orders = {nm: ORDERINGS[nm](G) for nm in ORDER_SET}
    res = {"name": name, "default": acl_for(None)}
    for nm in ORDER_SET:
        res[nm] = acl_for(orders[nm])
    res["glf"] = graph_level_features(G)
    return res


def build_dataset(split, smoke, workers):
    insts = gen_instances(split, smoke)
    tasks = [(nm, g, "P6") for nm, g in insts]
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(_eval_instance, tasks):
            rows.append(r)
    # attach the graphs (for per-vertex score eval) by name
    gmap = {nm: g for nm, g in insts}
    return rows, gmap


# --------------------------------------------------------------------------- #
# (A) order selector  &  (B) per-vertex linear score
# --------------------------------------------------------------------------- #
def best_order(row):
    cand = [(o, row[o]) for o in ORDER_SET if row[o] is not None]
    return min(cand, key=lambda x: x[1])[0] if cand else "cuthill"


def eval_score_weights(weights, gmap, rows, target_name="P6"):
    """Mean test ACL when each instance is embedded under learned_order(G, weights)."""
    sys.path.insert(0, "/Users/dabh/ember/external/minorminer-fork/minorminer")
    import _minorminer as mmfork
    from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
    tgt = dnx.pegasus_graph(6)
    adj = build_adjacency(tgt); T = list(tgt.edges())
    DEF = dict(max_no_improvement=10, timeout=1000, tries=10, chainlength_patience=10)
    vals = []
    for row in rows:
        G = gmap[row["name"]]
        order = learned_order(G, weights)
        seedvals = []
        for s in EVAL_SEEDS:
            e = mmfork.find_embedding(list(G.edges()), T, random_seed=s, var_order=order, **DEF)
            e = {k: v for k, v in e.items() if v}
            if len(e) == G.number_of_nodes() and is_valid_embedding(e, G, tgt, adj=adj):
                seedvals.append(sum(len(c) for c in e.values()) / len(e))
        if seedvals:
            vals.append(float(np.mean(seedvals)))
    return float(np.mean(vals)) if vals else float("inf")


def hillclimb_weights(gmap, train_rows, iters, seed=0):
    rng = np.random.RandomState(seed)
    d = len(FEATURES)
    # start from a sensible prior (degree+core up, ecc down) plus a couple random inits
    inits = [np.array([1, 1, 0, 0, 0, -1.0]), np.array([0, 1, 0, 0, 0, -1.0]),
             rng.randn(d), rng.randn(d)]
    best_w, best_v = None, float("inf")
    subset = train_rows[: min(len(train_rows), 12)]
    for w0 in inits:
        w = w0 / (np.linalg.norm(w0) + 1e-9)
        v = eval_score_weights(w, gmap, subset)
        if v < best_v:
            best_w, best_v = w.copy(), v
    scale = 0.6
    for it in range(iters):
        cand = best_w + scale * rng.randn(d)
        cand /= (np.linalg.norm(cand) + 1e-9)
        v = eval_score_weights(cand, gmap, subset)
        if v < best_v:
            best_w, best_v = cand, v
        else:
            scale *= 0.92
    return best_w, best_v


def main():
    smoke = "--smoke" in sys.argv
    rest = [a for a in sys.argv[1:] if a != "--smoke"]
    workers = int(rest[0]) if rest else 6
    t0 = time.time()

    print("building train dataset ...")
    train_rows, train_g = build_dataset("train", smoke, workers)
    print("building test dataset ...")
    test_rows, test_g = build_dataset("test", smoke, workers)
    print(f"datasets: {len(train_rows)} train, {len(test_rows)} test "
          f"({time.time()-t0:.0f}s)")

    # ---- references on TEST ----
    def mean(key_fn, rows):
        vs = [key_fn(r) for r in rows]
        vs = [v for v in vs if v is not None]
        return float(np.mean(vs)) if vs else None

    mm = mean(lambda r: r["default"], test_rows)
    fixed = {o: mean(lambda r: r[o], test_rows) for o in ORDER_SET}
    best_fixed_name = min(fixed, key=lambda o: fixed[o])
    oracle = mean(lambda r: min([r[o] for o in ORDER_SET if r[o] is not None] or [r["default"]]), test_rows)

    # ---- (A) order selector (logistic regression on graph-level features) ----
    sel_acl = None
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        Xtr = np.array([r["glf"] for r in train_rows]); ytr = [best_order(r) for r in train_rows]
        Xte = np.array([r["glf"] for r in test_rows])
        sc = StandardScaler().fit(Xtr)
        if len(set(ytr)) > 1:
            clf = LogisticRegression(max_iter=1000).fit(sc.transform(Xtr), ytr)
            pred = clf.predict(sc.transform(Xte))
        else:
            pred = [ytr[0]] * len(test_rows)
        picks = []
        for r, p in zip(test_rows, pred):
            picks.append(r[p] if r.get(p) is not None else r["default"])
        sel_acl = float(np.mean([v for v in picks if v is not None]))
        from collections import Counter
        print("selector predictions:", Counter(pred))
    except Exception as exc:
        print("selector skipped:", exc)

    # ---- (B) per-vertex learned score (hill-climb, mmfork in the loop) ----
    iters = 4 if smoke else 40
    w, wv = hillclimb_weights(train_g, train_rows, iters)
    score_acl = eval_score_weights(w, test_g, test_rows)

    # ---- report ----
    def pct(x): return f"{100*(x-mm)/mm:+.1f}%" if (x and mm) else "-"
    print("\n===== held-out TEST mean ACL =====")
    print(f"stock minorminer        {mm:.3f}   (baseline)")
    print(f"best fixed ({best_fixed_name:10s}) {fixed[best_fixed_name]:.3f}   {pct(fixed[best_fixed_name])}")
    print(f"oracle / portfolio      {oracle:.3f}   {pct(oracle)}")
    if sel_acl:
        print(f"(A) learned selector    {sel_acl:.3f}   {pct(sel_acl)}")
    print(f"(B) learned score        {score_acl:.3f}   {pct(score_acl)}")
    print(f"\nlearned weights {dict(zip(FEATURES, [round(float(x),3) for x in w]))}")

    out = {"mm": mm, "fixed": fixed, "best_fixed": best_fixed_name, "oracle": oracle,
           "selector": sel_acl, "score": score_acl,
           "weights": {f: float(x) for f, x in zip(FEATURES, w)},
           "n_train": len(train_rows), "n_test": len(test_rows)}
    with open(os.path.join(HERE, "learn_order_results.json"), "w") as f:
        json.dump(out, f, indent=2)
    # If the learned score beats the best fixed order, save weights for mmfork-learned.
    if score_acl < fixed[best_fixed_name]:
        with open(os.path.abspath(PKG_WEIGHTS), "w") as f:
            json.dump({f: float(x) for f, x in zip(FEATURES, w)}, f, indent=2)
        print(f"\nlearned score beats best fixed -> wrote {PKG_WEIGHTS}")
    print(f"\ntotal {time.time()-t0:.0f}s; wrote learn_order_results.json")


if __name__ == "__main__":
    main()
