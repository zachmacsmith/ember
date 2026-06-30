"""
docs/paper/data/make_scaling_figures.py
=======================================
Turn the hardware-scale sweep (``summary_scaling.csv`` from run_sweep_scaling.py)
into (a) pgfplots ``\\addplot`` coordinate blocks for the paper's in-text scaling
figures and (b) supplementary matplotlib PNG/PDFs for a quick visual read.

Plots, per target (Advantage P16, Advantage2 Z15) and per source regime
(ER d=0.3, d-regular k=6): ACL vs n, wall-clock vs n (relative to minorminer),
and success-rate vs n — answering whether the ordering advantage widens with n
and how each method scales.

Usage:  python make_scaling_figures.py
Prints pgfplots blocks to stdout (also -> scaling_pgfplots.tex) and writes
figures/scaling_*.png.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.normpath(os.path.join(HERE, "..", "figures"))

ALGOS = ["minorminer", "minorminer-layout", "reweave", "reweave-thorough",
         "mmfork-cuthill", "mmfork-cuthill-fast", "mmfork-portfolio",
         "reweave-mmfork-cuthill"]
SHORT = {"minorminer": "MM", "minorminer-layout": "MM-layout", "reweave": "Reweave",
         "reweave-thorough": "Reweave-thorough", "mmfork-cuthill": "mmfork-cuthill",
         "mmfork-cuthill-fast": "mmfork-cuthill-fast", "mmfork-portfolio": "mmfork-portfolio",
         "reweave-mmfork-cuthill": "reweave+cuthill"}
TARGETS = {"pegasus16_broken": "Advantage $P_{16}$", "zephyr15_broken": "Advantage2 $Z_{15}$"}
REGIMES = {"ERd0.3": "ER $d{=}0.3$", "REGk6": "d-regular $k{=}6$"}


def load():
    path = os.path.join(HERE, "summary_scaling.csv")
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            r["regime"] = r["source"].split("_n")[0]
            rows.append(r)
    return rows


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def series(rows, target, regime, algo, col):
    """Sorted [(n, value)] for one (target, regime, algo, column)."""
    pts = []
    for r in rows:
        if r["target"] == target and r["regime"] == regime and r["algorithm"] == algo:
            n, v = _f(r["n"]), _f(r[col])
            if n is not None and v is not None:
                pts.append((int(n), v))
    return sorted(pts)


def emit_pgfplots(rows):
    out = []
    for target in TARGETS:
        for regime in REGIMES:
            for metric, col, lbl in [("acl", "acl_mean", "mean ACL"),
                                     ("timerel", "time_mean_ok", "time / MM"),
                                     ("success", "success_rate", "success rate")]:
                out.append(f"%% {TARGETS[target]} | {REGIMES[regime]} | {lbl}  (n on x)")
                # MM baseline for relative time
                mm = dict(series(rows, target, regime, "minorminer", "time_mean_ok"))
                for algo in ALGOS:
                    pts = series(rows, target, regime, algo, col)
                    if not pts:
                        continue
                    if metric == "timerel":
                        pts = [(n, (v / mm[n]) if mm.get(n) else None) for n, v in pts]
                        pts = [(n, v) for n, v in pts if v is not None]
                    coords = " ".join(f"({n},{v:.3f})" for n, v in pts)
                    out.append(f"\\addplot coordinates {{{coords}}};  "
                               f"\\addlegendentry{{{SHORT[algo]}}}")
                out.append("")
    text = "\n".join(out)
    with open(os.path.join(HERE, "scaling_pgfplots.tex"), "w") as f:
        f.write(text)
    print(text)


def matplotlib_png(rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"(matplotlib unavailable: {exc})")
        return
    os.makedirs(FIGDIR, exist_ok=True)
    for target in TARGETS:
        fig, axes = plt.subplots(2, 3, figsize=(15, 8))
        for j, regime in enumerate(REGIMES):
            mm = dict(series(rows, target, regime, "minorminer", "time_mean_ok"))
            for algo in ALGOS:
                acl = series(rows, target, regime, algo, "acl_mean")
                tm = series(rows, target, regime, algo, "time_mean_ok")
                tm = [(n, v / mm[n]) for n, v in tm if mm.get(n)]
                if acl:
                    axes[j, 0].plot(*zip(*acl), marker="o", ms=4, label=SHORT[algo])
                if tm:
                    axes[j, 1].plot(*zip(*tm), marker="o", ms=4, label=SHORT[algo])
                sc = series(rows, target, regime, algo, "success_rate")
                if sc:
                    axes[j, 2].plot(*zip(*sc), marker="o", ms=4, label=SHORT[algo])
            axes[j, 0].set(title=f"{REGIMES[regime]}: ACL vs n", xlabel="n", ylabel="ACL")
            axes[j, 1].set(title="time / MM vs n", xlabel="n", ylabel="x MM")
            axes[j, 2].set(title="success vs n", xlabel="n", ylabel="rate")
            axes[j, 0].legend(fontsize=7)
        fig.suptitle(TARGETS[target])
        fig.tight_layout()
        p = os.path.join(FIGDIR, f"scaling_{target}.png")
        fig.savefig(p, dpi=130); plt.close(fig)
        print(f"wrote {p}")


def main():
    rows = load()
    emit_pgfplots(rows)
    matplotlib_png(rows)


if __name__ == "__main__":
    main()
