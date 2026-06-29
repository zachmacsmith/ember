"""
docs/paper/data/make_figures.py
===============================
Render result figures for the PathFinder paper from the committed optimized
sweep (``summary_opt.csv``). These are *supplementary* matplotlib renderings of
the same numbers reported in the paper's tables (the paper's own in-text figures
are vector TikZ/pgfplots); they are handy for slides, the repo README, and a
quick visual read of the headline results. Writes PNG (150 dpi) + PDF to
``docs/paper/figures/``.

Dependencies: matplotlib + pandas (both from the ``ember-qc-analysis`` package,
or ``pip install matplotlib pandas``). Deterministic: a pure function of the
committed CSV.

Usage:  .venv/bin/python docs/paper/data/make_figures.py
"""
from __future__ import annotations

import os
import re

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.normpath(os.path.join(HERE, "..", "figures"))

# The four head-to-head algorithms the paper compares (the -base/-stacked engines
# are diagnostics, omitted here to keep the figures legible).
ALGOS = ["minorminer", "minorminer-layout", "pathfinder", "pathfinder-thorough"]
LABELS = {
    "minorminer": "minorminer (MM)",
    "minorminer-layout": "MM + p-norm layout",
    "pathfinder": "PathFinder",
    "pathfinder-thorough": "PathFinder-thorough",
}
COLORS = {
    "minorminer": "#555555",
    "minorminer-layout": "#1f77b4",
    "pathfinder": "#2ca02c",
    "pathfinder-thorough": "#d62728",
}
MARKERS = {"minorminer": "o", "minorminer-layout": "s",
           "pathfinder": "^", "pathfinder-thorough": "D"}
TARGET_LABELS = {
    "pegasus_6": "Pegasus $P_6$ (clean)",
    "pegasus_6_broken5": "Pegasus $P_6$ (5% faults)",
    "zephyr_4": "Zephyr $Z_4$",
}
NS = [20, 30, 40]
DENSITIES = [0.3, 0.5, 0.7]


def load() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(HERE, "summary_opt.csv"))
    # parse ER source names: ER_n{n}_d{d}
    er = df["source"].str.extract(r"^ER_n(?P<n>\d+)_d(?P<density>[0-9.]+)$")
    df["n"] = pd.to_numeric(er["n"], errors="coerce")
    df["density"] = pd.to_numeric(er["density"], errors="coerce")
    for c in ("acl_mean", "acl_std", "time_mean"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _save(fig, name: str) -> None:
    os.makedirs(FIGDIR, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGDIR, f"{name}.{ext}"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {os.path.relpath(os.path.join(FIGDIR, name))}.{{png,pdf}}")


def fig_acl_vs_density(df: pd.DataFrame) -> None:
    """ACL mean (±std) vs density, one panel per n, ER into clean Pegasus."""
    er = df[(df["target"] == "pegasus_6") & df["n"].notna()]
    fig, axes = plt.subplots(1, len(NS), figsize=(12, 3.6), sharey=False)
    for ax, n in zip(axes, NS):
        for algo in ALGOS:
            sub = er[(er["algorithm"] == algo) & (er["n"] == n)].sort_values("density")
            if sub.empty:
                continue
            ax.errorbar(sub["density"], sub["acl_mean"], yerr=sub["acl_std"],
                        label=LABELS[algo], color=COLORS[algo], marker=MARKERS[algo],
                        capsize=3, lw=1.8, ms=6)
        ax.set_title(f"$n={n}$"); ax.set_xlabel("edge density")
        ax.set_xticks(DENSITIES); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("avg. chain length (ACL)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.08))
    fig.suptitle("Embedding quality: ACL vs density (ER sources, clean Pegasus $P_6$; lower is better)",
                 y=1.15, fontsize=11)
    _save(fig, "acl_vs_density")


def fig_acl_std_vs_density(df: pd.DataFrame) -> None:
    """ACL std (run-to-run variance) vs density — PathFinder's headline advantage."""
    er = df[(df["target"] == "pegasus_6") & df["n"].notna()]
    fig, axes = plt.subplots(1, len(NS), figsize=(12, 3.6), sharey=True)
    for ax, n in zip(axes, NS):
        for algo in ALGOS:
            sub = er[(er["algorithm"] == algo) & (er["n"] == n)].sort_values("density")
            if sub.empty:
                continue
            ax.plot(sub["density"], sub["acl_std"], label=LABELS[algo],
                    color=COLORS[algo], marker=MARKERS[algo], lw=1.8, ms=6)
        ax.set_title(f"$n={n}$"); ax.set_xlabel("edge density")
        ax.set_xticks(DENSITIES); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("ACL std. dev. (over 5 seeds)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.08))
    fig.suptitle("Run-to-run variance: ACL std vs density (lower = more reliable)",
                 y=1.15, fontsize=11)
    _save(fig, "acl_std_vs_density")


def fig_time_vs_mm(df: pd.DataFrame) -> None:
    """Wall-clock relative to minorminer (=1.0), ER into clean Pegasus."""
    er = df[(df["target"] == "pegasus_6") & df["n"].notna()].copy()
    mm = (er[er["algorithm"] == "minorminer"]
          .set_index(["n", "density"])["time_mean"])
    fig, axes = plt.subplots(1, len(NS), figsize=(12, 3.6), sharey=True)
    rel_algos = [a for a in ALGOS if a != "minorminer"]
    for ax, n in zip(axes, NS):
        for algo in rel_algos:
            sub = er[(er["algorithm"] == algo) & (er["n"] == n)].sort_values("density")
            if sub.empty:
                continue
            ratio = [row["time_mean"] / mm.get((row["n"], row["density"]), float("nan"))
                     for _, row in sub.iterrows()]
            ax.plot(sub["density"], ratio, label=LABELS[algo], color=COLORS[algo],
                    marker=MARKERS[algo], lw=1.8, ms=6)
        ax.axhline(1.0, color="#555555", ls="--", lw=1.2, label="minorminer (MM) = 1.0")
        ax.set_title(f"$n={n}$"); ax.set_xlabel("edge density")
        ax.set_xticks(DENSITIES); ax.grid(True, alpha=0.3)
    axes[0].set_ylabel(r"wall-clock $\div$ minorminer")
    handles, labels = axes[-1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.08))
    fig.suptitle("Speed: wall-clock relative to compiled minorminer (clean Pegasus $P_6$)",
                 y=1.15, fontsize=11)
    _save(fig, "time_vs_mm")


def fig_topology_robustness(df: pd.DataFrame) -> None:
    """Mean ACL (over ER cells) per algorithm across the three target topologies."""
    er = df[df["n"].notna()]
    targets = ["pegasus_6", "pegasus_6_broken5", "zephyr_4"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    import numpy as np
    x = np.arange(len(targets)); w = 0.2
    for i, algo in enumerate(ALGOS):
        means = []
        for t in targets:
            sub = er[(er["algorithm"] == algo) & (er["target"] == t)]
            means.append(sub["acl_mean"].mean())
        ax.bar(x + (i - 1.5) * w, means, w, label=LABELS[algo], color=COLORS[algo])
    ax.set_xticks(x); ax.set_xticklabels([TARGET_LABELS[t] for t in targets])
    ax.set_ylabel("mean ACL over ER cells"); ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.18)  # headroom so the legend clears the bars
    ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="upper center")
    ax.set_title("Robustness across topologies: mean ACL (lower is better)", pad=10)
    _save(fig, "topology_robustness")


def main() -> None:
    df = load()
    fig_acl_vs_density(df)
    fig_acl_std_vs_density(df)
    fig_time_vs_mm(df)
    fig_topology_robustness(df)
    print(f"\nall figures written to {FIGDIR}")


if __name__ == "__main__":
    main()
