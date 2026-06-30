"""
docs/paper/data/scaling_coords.py
=================================
Emit pgfplots coordinates + text numbers for the scaling figures (fig:scaling,
fig:scalingacl) from raw_results_scaling.csv, instance-averaged with 95% CIs.

Time ratio  = mean(algo wall_time) / mean(mm wall_time)   per (target, algo, n).
ACL ratio   = mean over instances of (per-instance mean ACL_algo / ACL_mm),
              with a 95% CI across instances (for figure error bars).

Handles K=1 (no `instance` column) and K>=2 (with it). Usage: python scaling_coords.py
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "minorminer"
ALGOS = ["mmfork-cuthill", "reweave-mmfork-cuthill", "mmfork-portfolio"]
NS = [40, 80, 160, 320, 480]
TARGETS = ["zephyr15_broken", "pegasus16_broken"]
PRETTY = {"mmfork-cuthill": "mmfork-cuthill",
          "reweave-mmfork-cuthill": "reweave+cuthill",
          "mmfork-portfolio": "mmfork-portfolio"}


def main():
    df = pd.read_csv(os.path.join(HERE, "raw_results_scaling.csv"))
    if "instance" not in df.columns:
        df["instance"] = 0
    reg = df[df["source"].str.startswith("REG")].copy()
    ok = reg[(reg["success"] == 1) & (reg["valid"] == 1)]

    def time_ratio(tgt, algo, n):
        a = ok[(ok.target == tgt) & (ok.algorithm == algo) & (ok.n == n)]["wall_time"]
        m = ok[(ok.target == tgt) & (ok.algorithm == BASE) & (ok.n == n)]["wall_time"]
        if not len(a) or not len(m) or m.mean() == 0:
            return None
        return a.mean() / m.mean()

    def acl_ratio(tgt, algo, n):
        # per-instance paired ratio, averaged over instances; CI across instances
        per = []
        for inst in sorted(ok["instance"].unique()):
            a = ok[(ok.target == tgt) & (ok.algorithm == algo) & (ok.n == n) & (ok.instance == inst)]["avg_chain_length"]
            m = ok[(ok.target == tgt) & (ok.algorithm == BASE) & (ok.n == n) & (ok.instance == inst)]["avg_chain_length"]
            if len(a) and len(m) and m.mean() > 0:
                per.append(a.mean() / m.mean())
        if not per:
            return None
        per = np.array(per)
        ci = (stats.t.ppf(0.975, len(per) - 1) * per.std(ddof=1) / np.sqrt(len(per))) if len(per) > 1 else 0.0
        return per.mean(), ci

    print("=" * 60, "\nFIG:SCALING  (time/MM vs n, 6-regular; solid=Z15, dashed=P16)")
    for tgt in TARGETS:
        tag = "Z15 (solid)" if "zephyr" in tgt else "P16 (dashed)"
        print(f"  -- {tag} --")
        for algo in ALGOS:
            pts = " ".join(f"({n},{r:.2f})" for n in NS if (r := time_ratio(tgt, algo, n)) is not None)
            print(f"    {PRETTY[algo]:18s}: {pts}")

    print("=" * 60, "\nFIG:SCALINGACL  (ACL/MM vs n into P16, 6-regular) + error bars")
    tgt = "pegasus16_broken"
    for algo in ALGOS:
        cells = [(n, acl_ratio(tgt, algo, n)) for n in NS]
        pts = " ".join(f"({n},{v[0]:.3f})" for n, v in cells if v is not None)
        errs = " ".join(f"({n},{v[0]:.3f})+-(0,{v[1]:.3f})" for n, v in cells if v is not None)
        print(f"    {PRETTY[algo]:18s} coords: {pts}")
        print(f"    {'':18s} ebars : {errs}")

    print("=" * 60, "\nTEXT NUMBERS (n=40 -> n=320 ratios)")
    for tgt in TARGETS:
        tag = "Z15" if "zephyr" in tgt else "P16"
        for algo in ALGOS:
            r40, r320 = time_ratio(tgt, algo, 40), time_ratio(tgt, algo, 320)
            if r40 and r320:
                print(f"  {tag} {PRETTY[algo]:18s} time: {r40:.1f}x -> {r320:.1f}x")


if __name__ == "__main__":
    main()
