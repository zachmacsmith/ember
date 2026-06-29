"""
Render the learned-embedding bake-off results (from evaluate.py's summary_eval.csv /
raw_eval.csv) into figures + a markdown verdict table. The headline questions:
  * does any learned method match/beat PF/MM on ACL (quality)?
  * ... on ACL run-to-run variance?
  * at what wall-clock?

Usage:
  python -m ember_qc_learn.make_learn_figures --eval data/learn/eval --out docs/candidate-algorithms/learning
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics as st
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ORDER = ["minorminer", "minorminer-layout", "pathfinder", "pathfinder-thorough",
         "learned-gnn-seed", "learned-gnn-seed-direct", "learned-retrieve",
         "learned-vae", "learned-obj"]
COLORS = {"minorminer": "#555", "minorminer-layout": "#1f77b4", "pathfinder": "#2ca02c",
          "pathfinder-thorough": "#17a02c", "learned-gnn-seed": "#d62728",
          "learned-gnn-seed-direct": "#ff7f0e", "learned-retrieve": "#9467bd",
          "learned-vae": "#8c564b", "learned-obj": "#e377c2"}


def _read(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _f(x, d=float("nan")):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default="data/learn/eval")
    ap.add_argument("--out", default="docs/candidate-algorithms/learning")
    ap.add_argument("--target", default="pegasus_6")
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "figures"), exist_ok=True)

    summary = [r for r in _read(os.path.join(args.eval, "summary_eval.csv"))
               if r["target"] == args.target]
    summary.sort(key=lambda r: ORDER.index(r["algorithm"]) if r["algorithm"] in ORDER else 99)
    algos = [r["algorithm"] for r in summary]
    cols = [COLORS.get(a, "#333") for a in algos]

    # Fig 1: ACL mean + per-seed variance (two panels)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.5))
    a1.bar(range(len(algos)), [_f(r["acl_mean"]) for r in summary], color=cols)
    a1.set_xticks(range(len(algos))); a1.set_xticklabels(algos, rotation=40, ha="right", fontsize=8)
    a1.set_ylabel("mean ACL (lower=better)"); a1.set_title(f"Quality — {args.target}")
    a1.grid(True, axis="y", alpha=0.3)
    a2.bar(range(len(algos)), [_f(r["acl_std_perseed_mean"]) for r in summary], color=cols)
    a2.set_xticks(range(len(algos))); a2.set_xticklabels(algos, rotation=40, ha="right", fontsize=8)
    a2.set_ylabel("mean per-graph ACL std over seeds"); a2.set_title("Run-to-run variance (lower=better)")
    a2.grid(True, axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(args.out, "figures", "acl_and_variance.png"), dpi=150)
    plt.close(fig)

    # Fig 2: ACL ratio vs pathfinder-thorough, per source family (from raw)
    raw = [r for r in _read(os.path.join(args.eval, "raw_eval.csv"))
           if r["target"] == args.target and r["valid"] == "1" and r["acl"] != ""]
    # per (family, algo) mean ACL; ratio to PF-thorough
    fam_algo = defaultdict(list)
    for r in raw:
        fam_algo[(r["family"], r["algorithm"])].append(_f(r["acl"]))
    families = sorted({r["family"] for r in raw})
    fig, ax = plt.subplots(figsize=(11, 4.5))
    import numpy as np
    learned = [a for a in algos if a.startswith("learned")]
    x = np.arange(len(families)); w = 0.8 / max(len(learned), 1)
    for i, a in enumerate(learned):
        ratios = []
        for fam in families:
            mine = fam_algo.get((fam, a)); base = fam_algo.get((fam, "pathfinder-thorough"))
            ratios.append((st.mean(mine) / st.mean(base)) if mine and base else float("nan"))
        ax.bar(x + (i - len(learned)/2) * w, ratios, w, label=a, color=COLORS.get(a, "#333"))
    ax.axhline(1.0, color="k", ls="--", lw=1, label="pathfinder-thorough = 1.0")
    ax.set_xticks(x); ax.set_xticklabels(families); ax.set_ylabel("ACL ÷ PF-thorough")
    ax.set_title(f"Learned ACL relative to PathFinder-thorough by family — {args.target}")
    ax.legend(fontsize=8, ncol=2); ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(args.out, "figures", "acl_ratio_by_family.png"), dpi=150)
    plt.close(fig)

    # markdown verdict table
    lines = [f"## Bake-off results — {args.target}\n",
             "| algorithm | success | mean ACL | ACL std/seed | mean time (s) |",
             "|---|---|---|---|---|"]
    for r in summary:
        lines.append(f"| {r['algorithm']} | {r['success_rate']} | {r['acl_mean']} | "
                     f"{r['acl_std_perseed_mean']} | {r['time_mean']} |")
    with open(os.path.join(args.out, "results_table.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote figures + results_table.md to {args.out}")


if __name__ == "__main__":
    main()
