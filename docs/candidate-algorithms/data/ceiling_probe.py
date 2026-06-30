"""
docs/candidate-algorithms/data/ceiling_probe.py
================================================
Search-guidance HONESTY GATE.  Before inventing ordering / rip-up heuristics we
measure how much average-chain-length (ACL) any such heuristic could *possibly*
buy, by sampling the search-control choices randomly and reading off the spread.

Three signals per (source, target) cell, each over K random samples:

  1. MM stochastic ceiling     minorminer with K different random_seeds.
                               single (seed 0) vs best-of-K vs mean+/-std.
                               The total opportunity in MM's stochastic search
                               (variable order + routing randomness combined).

  2. construction-order ceiling  Reweave negotiated cold start (pre-LNS), run
                               with K random *vertex orders* (the routing is
                               deterministic given the order, so the ACL spread
                               is purely the construction-order effect).

  3. order ceiling after LNS    the same K random-order cold starts, but now
                               followed by Reweave's LNS improver — shows how
                               much of the construction-order variance the
                               improver absorbs.

Read-off: gap% = 100*(mean - best_of_K)/mean is "what a perfect one-shot picker
saves over an average random choice".  A large gap on (1)/(2) means ordering is
worth guiding; a gap that collapses on (3) means the improver already absorbs it
(so ordering matters most for cheap one-shot constructive embedding, less for the
warm-started improver).

Usage:  python ceiling_probe.py [K] [timeout_s] [--smoke]
Writes  ceiling_probe.csv  in this directory and prints a summary table.
"""
from __future__ import annotations

import csv
import os
import statistics as st
import sys
import time
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

from ember_qc.benchmark import benchmark_one  # noqa: E402
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.reweave import embed_reweave  # noqa: E402
from ember_qc.algorithms.reweave_opt import _OptimizedRouter  # noqa: E402

# Grid: a few ER cells spanning size/density + a broken target and Zephyr.
GRID = [
    ("ER", 20, 0.5, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6"),
    ("ER", 30, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6"),
    ("ER", 30, 0.5, "zephyr_4"),
]
SMOKE = [("ER", 20, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6")]
LAB = {"pegasus_6": "P6", "pegasus_6_broken5": "P6brk", "zephyr_4": "Z4"}


class _RandOrderCold(_OptimizedRouter):
    """Optimized Reweave router whose cold-start vertex order is a random
    permutation (seeded by the router seed) instead of the BFS order."""

    def _bfs_order(self):
        order = list(self.src_nodes)
        self.rng.shuffle(order)
        return order


def _acl(emb):
    if not emb:
        return None
    return sum(len(c) for c in emb.values()) / len(emb)


def _summ(acls):
    """min (best-of-K), mean, pstdev, and gap% = 100*(mean-min)/mean."""
    acls = [a for a in acls if a is not None]
    if not acls:
        return dict(n=0, best=None, mean=None, std=None, gap=None)
    best, mean = min(acls), st.mean(acls)
    std = st.pstdev(acls) if len(acls) > 1 else 0.0
    gap = 100.0 * (mean - best) / mean if mean else 0.0
    return dict(n=len(acls), best=best, mean=mean, std=std, gap=gap)


def _cold_acls(src, tgt, K, timeout, with_lns):
    """K random-order cold starts.  with_lns=False reads the raw cold-start
    embedding (pre-LNS); with_lns=True runs the full reweave-cold improver."""
    adj = build_adjacency(tgt)
    out = []
    for k in range(K):
        if with_lns:
            res = embed_reweave(src, tgt, timeout=timeout, seed=k,
                                router_cls=_RandOrderCold, base_method=None)
            emb = res.get("embedding")
        else:
            r = _RandOrderCold(src, tgt, seed=k, base_method=None)
            emb = r._cold_start(time.perf_counter() + timeout)
        if emb and is_valid_embedding(emb, src, tgt, adj=adj):
            out.append(_acl(emb))
        else:
            out.append(None)
    return out


def main():
    args = [a for a in sys.argv[1:] if a != "--smoke"]
    smoke = "--smoke" in sys.argv
    K = int(args[0]) if len(args) > 0 else 16
    timeout = float(args[1]) if len(args) > 1 else 20.0
    grid = SMOKE if smoke else GRID
    if smoke:
        K = min(K, 6)

    targets = make_targets()
    rows = []
    print(f"\nceiling probe  K={K}  timeout={timeout}s\n")
    hdr = f"{'cell':16s} {'signal':18s} {'n':>3s} {'single':>7s} {'best':>7s} {'mean':>7s} {'std':>6s} {'gap%':>6s}"
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p)
        tgt = targets[tname]
        cell = f"{fam}_n{n}_d{p}_{LAB[tname]}"

        # 1. MM stochastic ceiling (K random seeds)
        mm = []
        single_mm = None
        for k in range(K):
            r = benchmark_one(src, tgt, "minorminer", timeout=timeout, seed=k,
                              graph_name=cell, topology_name=tname)
            a = r.avg_chain_length if (r.success and r.is_valid) else None
            mm.append(a)
            if k == 0:
                single_mm = a

        # 2. construction-order ceiling (raw cold start, K random orders)
        cold_raw = _cold_acls(src, tgt, K, timeout, with_lns=False)
        # 3. order ceiling after LNS
        cold_lns = _cold_acls(src, tgt, K, timeout, with_lns=True)

        print("-" * 74)
        print(hdr)
        for name, acls, single in [
            ("MM (rand seed)", mm, single_mm),
            ("cold-order raw", cold_raw, cold_raw[0]),
            ("cold-order +LNS", cold_lns, cold_lns[0]),
        ]:
            s = _summ(acls)
            rows.append(dict(cell=cell, signal=name, K=K, **s))
            sgl = f"{single:.3f}" if single is not None else "-"
            if s["best"] is None:
                print(f"{cell:16s} {name:18s} {s['n']:>3d} {sgl:>7s} {'fail':>7s}")
                continue
            print(f"{cell:16s} {name:18s} {s['n']:>3d} {sgl:>7s} "
                  f"{s['best']:>7.3f} {s['mean']:>7.3f} {s['std']:>6.3f} {s['gap']:>6.1f}")
        print()

    with open(os.path.join(HERE, "ceiling_probe.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cell", "signal", "K", "n", "best", "mean", "std", "gap"])
        w.writeheader()
        w.writerows(rows)
    print("=" * 74)
    print("wrote ceiling_probe.csv")
    # headline: average gap% per signal across cells
    for name in ["MM (rand seed)", "cold-order raw", "cold-order +LNS"]:
        gaps = [r["gap"] for r in rows if r["signal"] == name and r["gap"] is not None]
        if gaps:
            print(f"  mean gap% [{name:18s}] = {st.mean(gaps):+.1f}%  "
                  f"(best-of-{K} vs random-mean)")


if __name__ == "__main__":
    main()
