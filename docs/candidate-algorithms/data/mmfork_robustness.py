"""
docs/candidate-algorithms/data/mmfork_robustness.py
===================================================
Two questions the paper section must answer about the search-guidance algorithms:

  (1) SUCCESS RATE / drop-in safety — does fixing a vertex order make minorminer
      FAIL where stock MM would succeed? (A single fixed order, reused across all
      `tries` restarts, removes the order diversity MM relies on near the
      feasibility boundary.) We compare success rate of stock MM vs mmfork-cuthill
      (single order, with and without the stock-MM fallback) vs mmfork-portfolio
      (which always includes a stock-MM run) on cells spanning easy -> infeasible.

  (2) STACKING with Reweave — Reweave warm-starts from a base embedder and then
      runs LNS. Seeding it from a better-ordered MM (mmfork-portfolio) instead of
      stock MM should compose (better base + same improvement). We measure
      reweave(base=minorminer) vs reweave(base=mmfork-portfolio).

Reports, per algo: success rate (valid / total) and mean ACL on successes.

Usage:  python mmfork_robustness.py [--smoke]
Writes  mmfork_robustness.csv.
"""
from __future__ import annotations

import csv
import os
import statistics as st
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

from ember_qc.registry import ALGORITHM_REGISTRY  # noqa: E402
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.reweave import embed_reweave  # noqa: E402
from ember_qc.algorithms.reweave_opt import _OptimizedRouter  # noqa: E402
from ember_qc.algorithms.search_orders import ORDERINGS  # noqa: E402
from ember_qc.algorithms.minorminer_forked import forked_find_embedding  # noqa: E402


def _embed(algo_name, src, tgt, timeout, seed):
    """Run a registered algorithm (or a special variant) and return its embedding."""
    if algo_name == "mmfork-cuthill-nofb":
        # cuthill order with NO stock-MM fallback: isolates the fixed-order risk.
        r = forked_find_embedding(src, tgt, order=ORDERINGS["cuthill"](src),
                                  seed=seed, timeout=timeout, fallback=False)
        return (r or {}).get("embedding") or None
    if algo_name == "reweave+mmfork":
        r = embed_reweave(src, tgt, timeout=timeout, seed=seed,
                          router_cls=_OptimizedRouter, base_method="mmfork-portfolio")
        return (r or {}).get("embedding") or None
    res = ALGORITHM_REGISTRY[algo_name].embed(src, tgt, timeout=timeout, seed=seed)
    return (res or {}).get("embedding") or None

# bracket MM's feasibility boundary (easy -> partial -> infeasible) on P6, plus a
# broken target, so the success-rate comparison is meaningful.
GRID = [
    ("ER", 40, 0.5, "pegasus_6"),
    ("ER", 60, 0.5, "pegasus_6"),
    ("ER", 70, 0.5, "pegasus_6"),
    ("ER", 60, 0.6, "pegasus_6"),
    ("ER", 50, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6_broken5"),
]
SMOKE = [("ER", 40, 0.5, "pegasus_6"), ("ER", 70, 0.5, "pegasus_6")]
LAB = {"pegasus_6": "P6", "pegasus_6_broken5": "P6brk"}
SEEDS = [0, 1, 2, 3, 4]


def main():
    smoke = "--smoke" in sys.argv
    grid = SMOKE if smoke else GRID
    seeds = SEEDS[:2] if smoke else SEEDS
    targets = make_targets()

    rows = []
    algos = ["minorminer", "mmfork-cuthill-nofb", "mmfork-cuthill",
             "mmfork-portfolio", "reweave", "reweave+mmfork"]
    print(f"{'cell':16s} " + " ".join(f"{a:18s}" for a in algos))
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p)
        tgt = targets[tname]
        adj = build_adjacency(tgt)
        cell = f"{fam}_n{n}_d{p}_{LAB[tname]}"
        per = {a: {"succ": 0, "acl": []} for a in algos}
        for s in seeds:
            for a in algos:
                emb = _embed(a, src, tgt, 15.0, s)
                ok = bool(emb) and is_valid_embedding(emb, src, tgt, adj=adj)
                if ok:
                    per[a]["succ"] += 1
                    per[a]["acl"].append(sum(len(c) for c in emb.values()) / len(emb))
        cells_out = []
        for a in algos:
            sc = per[a]["succ"]
            acl = st.mean(per[a]["acl"]) if per[a]["acl"] else None
            acls = f"{acl:.2f}" if acl is not None else "  - "
            cells_out.append(f"{sc}/{len(seeds)} {acls:>5s}")
            rows.append({"cell": cell, "algo": a, "succ": sc, "n": len(seeds),
                         "acl": acl})
        print(f"{cell:16s} " + " ".join(f"{c:18s}" for c in cells_out))

    with open(os.path.join(HERE, "mmfork_robustness.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cell", "algo", "succ", "n", "acl"])
        w.writeheader(); w.writerows(rows)

    # overall success + mean ACL
    print("\n=== OVERALL ===")
    print(f"{'algo':18s} {'success':>9s} {'meanACL':>8s}")
    for a in algos:
        rs = [r for r in rows if r["algo"] == a]
        succ = sum(r["succ"] for r in rs); ntot = sum(r["n"] for r in rs)
        acls = [r["acl"] for r in rs if r["acl"] is not None]
        ma = f"{st.mean(acls):.3f}" if acls else "-"
        print(f"{a:18s} {succ:>4d}/{ntot:<4d} {ma:>8s}")
    print("\nwrote mmfork_robustness.csv")


if __name__ == "__main__":
    main()
