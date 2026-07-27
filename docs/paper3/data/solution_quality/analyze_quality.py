"""
docs/paper/data/analyze_quality.py
==================================
Analyze raw_solution_quality.csv: does shorter ACL -> better annealing solutions?

Produces, for the paper's "Solution quality on a simulator" section:
  - rank correlations ACL <-> {P(ground state), residual energy, chain breaks}
    across the whole (problem, embedding) cloud, at the reference chain strength
    and at each embedding's best chain strength;
  - paired Wilcoxon (reuse ember_qc_analysis.significance_tests) of every method
    vs minorminer on P(ground state), per (problem, target);
  - SA vs SVMC agreement on method ordering;
  - figures (figures/quality_*.pdf/png) and a LaTeX table (tab:solquality).

Usage:  python analyze_quality.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.normpath(os.path.join(HERE, "..", "figures"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "packages",
                                "ember-qc-analysis", "src"))
from ember_qc_analysis.statistics import significance_tests  # noqa: E402

REF_REL = 1.0
METHOD_ORDER = ["minorminer", "minorminer-layout", "reweave", "reweave-thorough",
                "mmfork-cuthill", "mmfork-portfolio"]
PRETTY = {"minorminer": "minorminer", "minorminer-layout": "mm-layout",
          "reweave": "reweave", "reweave-thorough": "reweave-thorough",
          "mmfork-cuthill": "mmfork-cuthill", "mmfork-portfolio": "mmfork-portfolio"}


def _corr(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5:
        return float("nan"), float("nan"), int(m.sum())
    r, p = stats.spearmanr(x[m], y[m])
    return float(r), float(p), int(m.sum())


def _fixed_effects(sub, metric, unit=("pid", "target")):
    """Within-problem (fixed-effects) association of ACL with `metric`.

    Pooled correlations over the (problem, embedding) cloud conflate problem
    difficulty with embedding quality (bigger/denser problems are harder AND
    longer-chained). Demeaning within each problem removes the confound; the
    per-problem rho distribution + sign test is the nonparametric counterpart.
    Also fits the demeaned linear slope: d(metric)/d(ACL) at fixed problem.
    """
    unit = [u for u in unit if u in sub.columns]
    acl_c = sub["acl"] - sub.groupby(unit)["acl"].transform("mean")
    met_c = sub[metric] - sub.groupby(unit)[metric].transform("mean")
    rho, p = stats.spearmanr(acl_c, met_c)
    slope = float(np.polyfit(acl_c, met_c, 1)[0]) if acl_c.std() > 0 else float("nan")
    rhos = []
    for _, g in sub.groupby(unit):
        if g["acl"].nunique() >= 3:
            r, _ = stats.spearmanr(g["acl"], g[metric])
            if np.isfinite(r):
                rhos.append(r)
    rhos = np.asarray(rhos)
    p_sign = stats.wilcoxon(rhos).pvalue if len(rhos) >= 10 else float("nan")
    return dict(rho=float(rho), p=float(p), slope=slope, n=len(sub),
                med_rho=float(np.median(rhos)), frac_neg=float(np.mean(rhos < 0)),
                n_problems=len(rhos), p_sign=float(p_sign))


def _sig_df(sub, metric):
    """Wrap rows for significance_tests: one paired unit per (pid,target)."""
    return pd.DataFrame({
        "success": True,
        "algorithm": sub["method"],
        "graph_name": sub["pid"].astype(str) + "_" + sub["target"],
        metric: sub[metric],
    })


def _paired_vs_mm(sub, metric, higher_better=True):
    # per (problem,target) mean of the metric, paired method vs minorminer
    unit = ["pid", "target"]
    pm = sub.groupby(unit + ["method"])[metric].mean().unstack("method")
    res = significance_tests(_sig_df(sub, metric), metric=metric, min_pairs=5)
    pvec = {tuple(sorted((r["algo_a"], r["algo_b"]))):
            (r["p_value"], r.get("corrected_p", np.nan), r["effect_size"], r["effect_magnitude"])
            for _, r in res.iterrows()}
    out = []
    for other in [m for m in METHOD_ORDER if m != "minorminer"]:
        if other not in pm or "minorminer" not in pm:
            continue
        diff = (pm[other] - pm["minorminer"]).dropna()
        if len(diff) < 5:
            continue
        better = diff.mean() > 0 if higher_better else diff.mean() < 0
        key = tuple(sorted(("minorminer", other)))
        p, cp, es, mag = pvec.get(key, (np.nan, np.nan, np.nan, ""))
        out.append((other, float(pm["minorminer"].mean()), float(pm[other].mean()),
                    p, cp, es, mag, 1.0 if better else -1.0))
    return out


def main():
    raw = os.path.join(HERE, "raw_solution_quality.csv")
    df = pd.read_csv(raw)
    os.makedirs(FIGDIR, exist_ok=True)
    sa = df[df["sampler"] == "SA"].copy()
    svmc = df[df["sampler"] == "SVMC"].copy()
    ref = sa[np.isclose(sa["chain_rel"], REF_REL)].copy()

    print(f"loaded {len(df)} rows: {len(sa)} SA, {len(svmc)} SVMC; "
          f"{ref['pid'].nunique()} problems, {ref['method'].nunique()} methods, "
          f"targets={sorted(ref['target'].unique())}")

    # ---- 1. ACL <-> quality: fixed-effects (primary) + pooled (descriptive) ----
    print("\n=== ACL <-> solution quality, WITHIN-PROBLEM (fixed effects; primary) ===")
    for metric, label in [("p_gs", "P(ground state)"), ("resid", "residual energy"),
                          ("chainbreak", "chain-break fraction")]:
        fe = _fixed_effects(ref, metric)
        print(f"  ACL vs {label:24s}: FE rho={fe['rho']:+.3f} p={fe['p']:.1e}  "
              f"slope={fe['slope']:+.3f}/ACL  per-problem median rho={fe['med_rho']:+.2f} "
              f"(frac<0={fe['frac_neg']:.2f}, sign p={fe['p_sign']:.1e}, "
              f"{fe['n_problems']} problems)")
    spread = ref.groupby(["pid", "target"])["acl"].agg(lambda x: x.max() - x.min())
    print(f"  within-problem ACL range: median={spread.median():.2f} mean={spread.mean():.2f}")
    print("\n=== pooled correlations (descriptive; conflate problem difficulty) ===")
    for metric, label in [("p_gs", "P(ground state)"), ("resid", "residual energy"),
                          ("chainbreak", "chain-break fraction")]:
        r, p, n = _corr(ref["acl"], ref[metric])
        print(f"  ACL vs {label:24s}: rho={r:+.3f}  p={p:.2e}  (n={n})")

    # best chain strength per (pid,target,method,eseed)
    keys = ["pid", "target", "method", "eseed", "acl", "maxchain", "fam", "n", "d"]
    best = (sa.groupby(keys, as_index=False)
              .agg(p_gs=("p_gs", "max"), resid=("resid", "min"),
                   chainbreak=("chainbreak", "min")))
    print("\n=== ACL <-> quality at each embedding's BEST chain strength ===")
    for metric, label in [("p_gs", "P(ground state)"), ("resid", "residual energy")]:
        r, p, n = _corr(best["acl"], best[metric])
        print(f"  ACL vs {label:24s}: rho={r:+.3f}  p={p:.2e}  (n={n})")

    # ---- 2. paired Wilcoxon vs minorminer (reference cs) ----
    print("\n=== paired Wilcoxon vs minorminer, P(ground state) @ reference cs ===")
    paired = _paired_vs_mm(ref, "p_gs", higher_better=True)
    for other, ma, mb, p, cp, es, mag, sign in paired:
        better = "BETTER" if sign > 0 else "worse "
        print(f"  {PRETTY.get(other, other):18s} {better} than mm  "
              f"(meanP {mb:.3f} vs {ma:.3f}; p={p:.1e}, Holm={cp:.1e}, r={es:+.2f} {mag})")

    # ---- 3. SA vs SVMC ordering agreement (reference cs) ----
    print("\n=== SA vs SVMC: per-method mean P(ground state) @ reference cs ===")
    msa = ref.groupby("method")["p_gs"].mean()
    msv = svmc.groupby("method")["p_gs"].mean()
    join = pd.DataFrame({"SA": msa, "SVMC": msv}).reindex(METHOD_ORDER)
    print(join.round(3).to_string())
    rho, pj = stats.spearmanr(join["SA"], join["SVMC"], nan_policy="omit")
    # per-(problem,embedding) agreement
    mkey = ["pid", "target", "method", "eseed"]
    j2 = (ref[mkey + ["p_gs"]].merge(svmc[mkey + ["p_gs"]], on=mkey, suffixes=("_sa", "_sv")))
    rho2, _ = stats.spearmanr(j2["p_gs_sa"], j2["p_gs_sv"])
    print(f"  method-mean ordering Spearman rho={rho:+.3f} (p={pj:.2e}); "
          f"per-embedding rho={rho2:+.3f} (n={len(j2)})")

    # ---- 4. per-method summary table (reference cs) ----
    summ = (ref.groupby("method")
               .agg(n=("p_gs", "size"), acl=("acl", "mean"),
                    p_gs=("p_gs", "mean"), resid=("resid", "mean"),
                    cbreak=("chainbreak", "mean"))
               .reindex(METHOD_ORDER))
    psig = {x[0]: (x[3], x[7]) for x in paired}   # method -> (p_value, sign)
    _write_table(summ, psig, msv)
    _figures(ref, sa, join)
    print(f"\nwrote tab_solquality.tex and figures to {FIGDIR}")

    # ---- 5. deployment-regime arm (best-known reference, larger n) ----
    large_path = os.path.join(HERE, "raw_solution_quality_large.csv")
    if os.path.exists(large_path):
        lg = pd.read_csv(large_path)
        lref = lg[np.isclose(lg["chain_rel"], REF_REL)].copy()
        print("\n=== LARGE ARM (best-known reference; deployment ACL regime) ===")
        print(f"  {lref['pid'].nunique()} problems; ACL range "
              f"[{lref['acl'].min():.2f}, {lref['acl'].max():.2f}]; "
              f"within-problem ACL range median="
              f"{lref.groupby('pid')['acl'].agg(lambda x: x.max()-x.min()).median():.2f}")
        for metric, label in [("p_gs", "P(best-known)"), ("resid", "residual energy"),
                              ("chainbreak", "chain-break fraction")]:
            fe = _fixed_effects(lref, metric, unit=("pid",))
            print(f"  ACL vs {label:24s}: FE rho={fe['rho']:+.3f} p={fe['p']:.1e}  "
                  f"slope={fe['slope']:+.3f}/ACL  per-problem median rho={fe['med_rho']:+.2f} "
                  f"(frac<0={fe['frac_neg']:.2f}, sign p={fe['p_sign']:.1e})")
        print("  per-method mean (reference chain strength):")
        lsumm = (lref.groupby("method")
                     .agg(acl=("acl", "mean"), p_gs=("p_gs", "mean"),
                          resid=("resid", "mean"), cbreak=("chainbreak", "mean"))
                     .reindex(METHOD_ORDER))
        print(lsumm.round(3).to_string())
        lpaired = _paired_vs_mm(lref.assign(target="p6"), "resid", higher_better=False)
        for other, ma, mb, p, cp, es, mag, sign in lpaired:
            print(f"    {PRETTY.get(other, other):18s} resid {mb:.3f} vs mm {ma:.3f} "
                  f"({'BETTER' if sign > 0 else 'worse'}; p={p:.1e}, r={es:+.2f} {mag})")


def _stars(p):
    if not np.isfinite(p):
        return ""
    return "$^{***}$" if p < 1e-3 else "$^{**}$" if p < 1e-2 else "$^{*}$" if p < 5e-2 else ""


def _write_table(summ, psig, msv):
    lines = [
        r"\begin{tabular}{lccccc}", r"\toprule",
        r"method & ACL & $P_{\mathrm{SA}}(\mathrm{GS})$ & $P_{\mathrm{SVMC}}(\mathrm{GS})$"
        r" & resid. & break \\",
        r"\midrule",
    ]
    for m in summ.index:
        if not np.isfinite(summ.loc[m, "p_gs"]):
            continue
        star = ""
        if m in psig:
            p, sign = psig[m]
            star = _stars(p) if sign > 0 else ""
        lines.append(
            f"\\texttt{{{PRETTY.get(m, m)}}} & {summ.loc[m,'acl']:.2f} & "
            f"{summ.loc[m,'p_gs']:.3f}{star} & {msv.get(m, float('nan')):.3f} & "
            f"{summ.loc[m,'resid']:.3f} & {summ.loc[m,'cbreak']:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    with open(os.path.join(HERE, "tab_solquality.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")


def _figures(ref, sa, join):
    # Figure 1: ACL vs P(GS) cloud, colored by method, with binned mean
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    for m in METHOD_ORDER:
        s = ref[ref["method"] == m]
        if len(s):
            ax.scatter(s["acl"], s["p_gs"], s=10, alpha=0.35, label=PRETTY.get(m, m))
    # binned mean trend
    bins = np.linspace(ref["acl"].min(), ref["acl"].max(), 9)
    idx = np.digitize(ref["acl"], bins)
    bx, by = [], []
    for b in range(1, len(bins)):
        s = ref[idx == b]
        if len(s) >= 5:
            bx.append(s["acl"].mean()); by.append(s["p_gs"].mean())
    ax.plot(bx, by, "k-o", lw=2, ms=4, label="binned mean")
    ax.set_xlabel("average chain length"); ax.set_ylabel(r"$P(\mathrm{ground\ state})$")
    ax.legend(fontsize=6, ncol=2, loc="upper right")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGDIR, f"quality_acl.{ext}"), dpi=150)
    plt.close(fig)

    # Figure 2: chain-strength sweep mechanism, by ACL tertile
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.0), sharex=True)
    q1, q2 = sa["acl"].quantile([1 / 3, 2 / 3])
    sa = sa.assign(aclbin=np.where(sa["acl"] <= q1, "short",
                          np.where(sa["acl"] <= q2, "medium", "long")))
    for label in ["short", "medium", "long"]:
        g = sa[sa["aclbin"] == label].groupby("chain_rel")
        axes[0].plot(g["p_gs"].mean().index, g["p_gs"].mean().values, "-o", ms=3, label=label)
        axes[1].plot(g["chainbreak"].mean().index, g["chainbreak"].mean().values, "-o", ms=3, label=label)
    axes[0].set_ylabel(r"$P(\mathrm{ground\ state})$"); axes[0].set_xlabel(r"chain strength / $\max|J|$")
    axes[1].set_ylabel("chain-break fraction"); axes[1].set_xlabel(r"chain strength / $\max|J|$")
    axes[0].legend(title="ACL", fontsize=6); axes[0].set_title("(a) solution quality")
    axes[1].set_title("(b) chain breaks")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGDIR, f"quality_chainstrength.{ext}"), dpi=150)
    plt.close(fig)

    # Figure 3: SA vs SVMC method-mean agreement
    fig, ax = plt.subplots(figsize=(3.4, 3.2))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, alpha=0.6)
    for m in join.index:
        ax.scatter(join.loc[m, "SA"], join.loc[m, "SVMC"], s=30)
        ax.annotate(PRETTY.get(m, m), (join.loc[m, "SA"], join.loc[m, "SVMC"]),
                    fontsize=6, xytext=(3, 2), textcoords="offset points")
    ax.set_xlabel(r"SA  $P(\mathrm{GS})$"); ax.set_ylabel(r"SVMC  $P(\mathrm{GS})$")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIGDIR, f"quality_sa_svmc.{ext}"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
