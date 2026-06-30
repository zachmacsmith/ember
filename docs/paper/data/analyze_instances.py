"""
docs/paper/data/analyze_instances.py
====================================
Rigorous multi-instance analysis (#2): the headline claims must survive K
independent graph instances per cell, with confidence intervals and paired
significance tests -- not one graph per cell (variance across seeds only).

Consumes raw_results_instances.csv (cell x instance x target x algo x seed) and
reports, for the paper:
  - per-(cell,target,algo) mean ACL with a 95% CI ACROSS INSTANCES;
  - a variance decomposition: between-instance vs within-instance (seed);
  - never-regress: per-instance reweave/stacked vs minorminer;
  - paired Wilcoxon (every method vs minorminer) across instances, with effect
    sizes (reuse ember_qc_analysis.significance_tests);
  - aggregate % ACL change vs minorminer with a bootstrap CI;
and writes LaTeX rows (tab_instances_*.tex) carrying CIs + significance markers.

Usage:  python analyze_instances.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "packages",
                                "ember-qc-analysis", "src"))
from ember_qc_analysis.statistics import significance_tests  # noqa: E402

BASE = "minorminer"
METHODS = ["minorminer", "minorminer-layout", "reweave-base", "reweave",
           "reweave-thorough", "reweave-stacked", "mmfork-cuthill",
           "mmfork-portfolio", "reweave-mmfork-cuthill"]
PRETTY = {"minorminer": "minorminer", "minorminer-layout": "mm-layout",
          "reweave-base": "reweave-base", "reweave": "reweave",
          "reweave-thorough": "reweave-thorough", "reweave-stacked": "reweave-stacked",
          "mmfork-cuthill": "mmfork-cuthill", "mmfork-portfolio": "mmfork-portfolio",
          "reweave-mmfork-cuthill": "reweave+cuthill"}


def t_ci(vals, conf=0.95):
    v = np.asarray(vals, float)
    v = v[np.isfinite(v)]
    n = len(v)
    if n < 2:
        return (float(v.mean()) if n else float("nan")), 0.0
    h = stats.t.ppf(0.5 + conf / 2, n - 1) * v.std(ddof=1) / np.sqrt(n)
    return float(v.mean()), float(h)


def main():
    df = pd.read_csv(os.path.join(HERE, "raw_results_instances.csv"))
    df = df[(df["success"] == 1) & (df["valid"] == 1)].copy()
    # per-instance algorithm mean ACL (average over seeds) -- the fundamental unit
    inst = (df.groupby(["cell", "target", "instance", "algorithm"], as_index=False)
              .agg(acl=("avg_chain_length", "mean"),
                   acl_seedstd=("avg_chain_length", "std"),
                   maxchain=("max_chain_length", "mean"),
                   time=("wall_time", "mean")))
    inst["acl_seedstd"] = inst["acl_seedstd"].fillna(0.0)
    K = df["instance"].nunique()
    print(f"{len(df)} successful runs; K={K} instances/cell; "
          f"{df['cell'].nunique()} cells x {df['target'].nunique()} targets x "
          f"{df['algorithm'].nunique()} algos")

    # ---- 1. never-regress vs minorminer (per instance) ----
    print("\n=== never-regress vs minorminer (per cell x target x instance) ===")
    piv = inst.pivot_table(index=["cell", "target", "instance"],
                           columns="algorithm", values="acl")
    for m in ["reweave-base", "reweave", "reweave-thorough", "reweave-stacked",
              "reweave-mmfork-cuthill", "mmfork-cuthill", "mmfork-portfolio"]:
        if m not in piv:
            continue
        d = (piv[m] - piv[BASE]).dropna()
        worst = d.max()
        frac_reg = float((d > 1e-6).mean())
        print(f"  {PRETTY[m]:22s}: max ACL regression vs mm = {worst:+.3f} "
              f"qubits/chain; fraction of instances regressed = {frac_reg:.3f} "
              f"(n={len(d)})")

    # ---- 2. variance decomposition (between-instance vs within-instance) ----
    print("\n=== ACL variance: between-instance vs within-instance(seed) ===")
    rows = []
    for m in METHODS:
        sub = df[df["algorithm"] == m]
        # within-instance (seed) variance, averaged over (cell,target,instance)
        wi = (sub.groupby(["cell", "target", "instance"])["avg_chain_length"]
                 .var(ddof=1).dropna())
        # between-instance variance of per-instance means, averaged over (cell,target)
        pim = sub.groupby(["cell", "target", "instance"])["avg_chain_length"].mean()
        bi = pim.groupby(level=[0, 1]).var(ddof=1).dropna()
        rows.append((m, np.sqrt(wi.mean()), np.sqrt(bi.mean())))
        print(f"  {PRETTY[m]:22s}: within-instance std={np.sqrt(wi.mean()):.3f}  "
              f"between-instance std={np.sqrt(bi.mean()):.3f}")
    # headline: seed-variance reduction vs mm
    base_wi = np.sqrt(df[df.algorithm == BASE].groupby(["cell", "target", "instance"])
                      ["avg_chain_length"].var(ddof=1).dropna().mean())
    print(f"  -> within-instance(seed) std, minorminer = {base_wi:.3f}")
    for m, wi_std, _ in rows:
        if m != BASE and np.isfinite(wi_std) and base_wi > 0:
            print(f"     {PRETTY[m]:22s}: {100*(wi_std/base_wi-1):+.0f}% vs mm seed-std")

    # ---- 3. paired Wilcoxon vs minorminer across instances ----
    print("\n=== paired Wilcoxon vs minorminer (ACL), per (cell,target,instance) ===")
    sigdf = pd.DataFrame({
        "success": True, "algorithm": inst["algorithm"],
        "graph_name": (inst["cell"] + "|" + inst["target"] + "|" + inst["instance"].astype(str)),
        "avg_chain_length": inst["acl"],
    })
    res = significance_tests(sigdf, metric="avg_chain_length", min_pairs=5)
    pvals = {}
    for _, r in res.iterrows():
        a, b = r["algo_a"], r["algo_b"]
        if a != BASE and b != BASE:
            continue
        other = b if a == BASE else a
        # significance_tests assumes higher=better; for ACL lower=better, so set
        # direction ourselves from the paired per-instance differences.
        pdiff = (piv[other] - piv[BASE]).dropna()
        better = pdiff.mean() < 0          # lower ACL than minorminer
        pvals[other] = (r["p_value"], r.get("corrected_p", np.nan), better)
        print(f"  {PRETTY.get(other, other):22s}: median ACL diff={pdiff.median():+.3f} "
              f"{'BETTER' if better else 'worse'}  p={r['p_value']:.2e} "
              f"Holm={r.get('corrected_p', float('nan')):.2e} "
              f"r={r['effect_size']:+.2f} ({r['effect_magnitude']})")

    # ---- 4. aggregate % ACL change vs mm with bootstrap CI ----
    print("\n=== aggregate ACL change vs minorminer (paired per instance, bootstrap CI) ===")
    rng = np.random.default_rng(0)
    for m in METHODS:
        if m == BASE or m not in piv:
            continue
        pct = ((piv[m] - piv[BASE]) / piv[BASE] * 100).dropna().values
        if len(pct) < 5:
            continue
        boot = [rng.choice(pct, len(pct), replace=True).mean() for _ in range(2000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        print(f"  {PRETTY[m]:22s}: {pct.mean():+.2f}%  95% CI [{lo:+.2f}, {hi:+.2f}]  (n={len(pct)})")

    _write_tables(df, inst, piv, pvals, K)
    print(f"\nwrote tab_instances.tex to {HERE}")


def _stars(p, better):
    if not np.isfinite(p):
        return ""
    sig = "***" if p < 1e-3 else "**" if p < 1e-2 else "*" if p < 5e-2 else ""
    return ("$^{" + sig + "}$") if (sig and better) else (r"$^{\dagger}$" if sig else "")


def _write_tables(df, inst, piv, pvals, K):
    """tab:instances -- per algo, %ACL change vs mm (bootstrap 95% CI), seed std
    (ratio vs mm), and Holm-corrected paired-Wilcoxon significance, over K
    instances x all cells x targets. The single summary the rigor section needs."""
    rng = np.random.default_rng(0)
    base_seed = np.sqrt(df[df.algorithm == BASE]
                        .groupby(["cell", "target", "instance"])["avg_chain_length"]
                        .var(ddof=1).dropna().mean())
    order = ["reweave-base", "reweave", "reweave-thorough", "mmfork-cuthill",
             "mmfork-portfolio", "reweave-mmfork-cuthill", "reweave-stacked",
             "minorminer-layout"]
    lines = [r"\begin{tabular}{lcccc}", r"\toprule",
             r"method & $\Delta$ACL vs.\ MM & 95\% CI & seed std (ratio) & paired $p$ \\",
             r"\midrule"]
    for m in order:
        if m not in piv:
            continue
        pct = ((piv[m] - piv[BASE]) / piv[BASE] * 100).dropna().values
        if len(pct) < 5:
            continue
        boot = [rng.choice(pct, len(pct), replace=True).mean() for _ in range(4000)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        seed = np.sqrt(df[df.algorithm == m]
                       .groupby(["cell", "target", "instance"])["avg_chain_length"]
                       .var(ddof=1).dropna().mean())
        ratio = seed / base_seed if base_seed > 0 else float("nan")
        p, cp, better = pvals.get(m, (np.nan, np.nan, False))
        star = _stars(cp, better)
        pstr = f"{cp:.0e}".replace("e-0", "e{-}").replace("e-", "e{-}")
        lines.append(
            f"\\texttt{{{PRETTY[m]}}} & ${pct.mean():+.1f}\\%${star} & "
            f"$[{lo:+.1f},{hi:+.1f}]$ & ${seed:.3f}\\,({ratio:.2f}\\times)$ & "
            f"${pstr}$ \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    with open(os.path.join(HERE, "tab_instances.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
