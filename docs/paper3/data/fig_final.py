#!/usr/bin/env python
"""Final two figures for paper3: the M4 frozen-eval forest and the M5 verdicts.

Reads ONLY docs/paper3/data/{m4_eval.csv, m4_headline.txt}; writes ONLY
docs/paper3/figures/.  Deterministic (fixed bootstrap seeds via crc32;
SOURCE_DATE_EPOCH pinned for byte-stable PDFs).

Regenerate:  .venv/bin/python docs/paper3/data/fig_final.py

Figures
  fig_m4_forest    forest plot of the M4 headline (§4.10 / m4_headline.txt
                   Table 1): per frozen eval cell, median paired ΔACL_spur%
                   vs minorminer for {p3-ate, p3-clmm, p3-mmpolish} with
                   bootstrap 95% CIs over the paired deltas; filled marker =
                   Holm-corrected p < 0.05 (either direction).
  fig_m5_verdicts  the M5 full-library category outcome summary (§4.11):
                   WIN/tie/LOSS counts over the 35 graph categories on
                   P16-merged / Z12 / C16 for the three arms.

Conventions (protocol.md): acl_spur column (rule 3); paired deltas on
both-succeed (inst_seed, algo_seed) pairs only (rule 4; all three arms are
seeded, so pairing is a literal join).  Plotted per-cell value = median of
the PER-PAIR Δ% (the fig_crossover.py convention); m4_headline.txt's d%
column is median(Δ)/median(MM) — the two agree within 0.5 pp everywhere
(asserted below).  Significance is NOT recomputed: Holm-corrected Wilcoxon
flags are parsed from m4_headline.txt Table 1.
"""

import os
import re
import zlib
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "0")  # byte-stable PDF metadata

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
CSV = HERE / "m4_eval.csv"
HEADLINE = HERE / "m4_headline.txt"
FIGDIR = HERE.parent / "figures"
FIGDIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# style — same dataviz-skill reference palette as fig_crossover.py
# ---------------------------------------------------------------------------
INK = "#0b0b0b"       # primary ink
INK2 = "#52514e"      # secondary ink
MUTED = "#898781"     # axis / muted labels
GRID = "#e1e0d9"      # hairline grid (also the neutral "tie" fill)
AXISC = "#c3c2b7"     # baseline / axis rule
NEUTRAL0 = "#f0efec"  # light neutral (row stripes)

BLUE = "#2a78d6"      # template family → p3-ate; also the WIN pole (arm better)
ORANGE = "#eb6834"    # clmm family → p3-clmm
TEAL = "#0e7560"      # p3-mmpolish (new entity; CVD-checked vs BLUE/ORANGE:
                      # OKLab ΔE×100 ≥ 8.9 under protan/deutan/tritan, ≥ 18.9
                      # normal, 5.6:1 on white — violet fails vs BLUE, aqua is
                      # attraction's, yellow is pssa's)
RED = "#e34948"       # diverging pole only (MM better / LOSS)

ARMS3 = ["p3-ate", "p3-clmm", "p3-mmpolish"]
ARM_COLOR = {"p3-ate": BLUE, "p3-clmm": ORANGE, "p3-mmpolish": TEAL}
ARM_MARKER = {"p3-ate": "s", "p3-clmm": "D", "p3-mmpolish": "o"}
ARM_MS = {"p3-ate": 4.6, "p3-clmm": 3.9, "p3-mmpolish": 4.6}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],   # matplotlib-bundled → same render everywhere
    "font.size": 8.5,
    "axes.labelsize": 9.0,
    "axes.titlesize": 9.5,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "legend.fontsize": 8.0,
    "axes.edgecolor": AXISC,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "grid.linestyle": "-",
    "legend.frameon": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})


def save(fig, name):
    fig.savefig(FIGDIR / f"{name}.pdf")
    fig.savefig(FIGDIR / f"{name}.png", dpi=200)
    plt.close(fig)
    print(f"wrote {FIGDIR / name}.pdf + .png")


def cell_label(topo, n, p):
    return f"{topo} K{n}" if p >= 1.0 else f"{topo} ({n},{p:g})"


# ---------------------------------------------------------------------------
# figure 4 — fig_m4_forest
# ---------------------------------------------------------------------------
# display order per topology, sparse → dense (K_n frontier last)
CELL_ORDER = [(160, 0.05), (140, 0.12), (100, 0.2), (140, 0.2), (100, 0.3)]
K_CELLS = {"P16": [(140, 1.0), (180, 1.0)], "Z12": [(140, 1.0), (179, 1.0)]}
B_BOOT = 10_000


def parse_headline_table1():
    """(cell label, arm) -> row dict for the three arms, from m4_headline.txt.

    Columns are aligned with >= 2 spaces; multi-word fields ("n/a [no pairs]",
    "1.000 [all-tie]") contain single spaces only, so a 2+-space split is exact.
    """
    txt = HEADLINE.read_text()
    body = txt.split("Table 1 —")[1].split("====")[0]
    out = {}
    for line in body.splitlines():
        f = re.split(r"\s{2,}", line.strip())
        if len(f) == 12 and f[1] in ARMS3:
            out[(f[0], f[1])] = dict(
                n=int(f[2]), med=f[3], dpct=f[4], p_holm=f[8],
                succ_arm=f[10], succ_mm=f[11])
    assert len(out) == 14 * 3, f"expected 42 Table 1 rows, parsed {len(out)}"
    return out


def paired_pct_deltas(cell, arm):
    """Per-pair (arm − MM)/MM × 100 on acl_spur, both-succeed, joined on
    (inst_seed, algo_seed).  All three arms are seeded (algo_seed 10-14)."""
    assert (cell[cell.arm == arm].algo_seed != -1).all(), f"{arm} not seeded?"
    mm = cell[(cell.arm == "minorminer") & (cell.success == 1)]
    mm = mm.set_index(["inst_seed", "algo_seed"]).acl_spur
    out_abs, out_pct = [], []
    for _, r in cell[(cell.arm == arm) & (cell.success == 1)].iterrows():
        key = (r.inst_seed, r.algo_seed)
        if key in mm.index:
            out_abs.append(r.acl_spur - mm.loc[key])
            out_pct.append((r.acl_spur - mm.loc[key]) / mm.loc[key] * 100.0)
    return out_abs, out_pct


def boot_ci(deltas, key):
    """Percentile bootstrap 95% CI of the median; deterministic per-series
    seed from crc32 so results don't depend on iteration order."""
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    d = np.asarray(deltas)
    idx = rng.integers(0, len(d), size=(B_BOOT, len(d)))
    meds = np.median(d[idx], axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def build_forest_stats():
    df = pd.read_csv(CSV)
    tab = parse_headline_table1()
    rows = []  # one per (topo, cell) in display order
    n_sig = 0
    for topo in ["P16", "Z12"]:
        for (n, p) in CELL_ORDER + K_CELLS[topo]:
            cell = df[(df.topo == topo) & (df.n == n) & (df.p == p)]
            assert len(cell), f"cell missing: {topo} ({n},{p})"
            lab = cell_label(topo, n, p)
            arms = {}
            for arm in ARMS3:
                t = tab[(lab, arm)]
                d_abs, d_pct = paired_pct_deltas(cell, arm)
                assert len(d_pct) == t["n"], (lab, arm, len(d_pct), t["n"])
                if not d_pct:
                    arms[arm] = dict(n=0, succ_arm=t["succ_arm"],
                                     succ_mm=t["succ_mm"])
                    continue
                med_abs = float(np.median(d_abs))
                med_pct = float(np.median(d_pct))
                # cross-check vs the published table (abs exact to 3 dp;
                # pct within 0.5 pp — different convention, see docstring)
                assert abs(med_abs - float(t["med"])) < 5e-4 + 1e-9, (lab, arm)
                assert abs(med_pct - float(t["dpct"].rstrip("%"))) < 0.5, (lab, arm)
                lo, hi = boot_ci(d_pct, f"{topo}:{n}:{p}:{arm}")
                sig = t["p_holm"] != "n/a" and float(t["p_holm"]) < 0.05
                n_sig += sig
                arms[arm] = dict(n=len(d_pct), med=med_pct, lo=lo, hi=hi,
                                 sig=sig, all_tie=all(x == 0.0 for x in d_pct))
            rows.append(dict(topo=topo, n=n, p=p, label=lab, arms=arms))
    assert n_sig == 25, f"Holm-significant count changed: {n_sig} != 25"
    return rows


def fig_m4_forest():
    rows = build_forest_stats()
    XLIM = (-46.0, 21.0)
    LANE = {"p3-ate": +0.26, "p3-clmm": 0.0, "p3-mmpolish": -0.26}

    fig, ax = plt.subplots(figsize=(7.2, 5.7))
    fig.subplots_adjust(left=0.135, right=0.985, top=0.895, bottom=0.135)

    y = 0.0
    prev_topo = None
    ylabels, ygroup = [], []
    for i, row in enumerate(rows):
        if row["topo"] != prev_topo:
            if prev_topo is not None:
                y -= 1.0                       # gap between topology blocks
            ygroup.append((y - 0.05, {"P16": "Pegasus P16",
                                      "Z12": "Zephyr Z12"}[row["topo"]]))
            y -= 1.1
            prev_topo = row["topo"]
        if i % 2 == 1:                          # subtle row stripe
            ax.axhspan(y - 0.5, y + 0.5, color=NEUTRAL0, zorder=0.4, lw=0)
        lab = row["label"].split(" ", 1)[1].replace(",", ", ")
        ylabels.append((y, lab))
        a0 = row["arms"][ARMS3[0]]
        if a0["n"] == 0:                        # frontier: MM 0-for-all
            sa = " · ".join(f"{arm.split('-')[1]} "
                            f"{row['arms'][arm]['succ_arm']}" for arm in ARMS3)
            ax.text(XLIM[0] + 1.5, y, f"no both-succeed pairs — minorminer "
                    f"{a0['succ_mm']}; arms embed: {sa}  (Table 3)",
                    fontsize=6.8, color=INK2, va="center", fontstyle="italic")
            y -= 1.0
            continue
        for arm in ARMS3:
            s = row["arms"][arm]
            yy = y + LANE[arm]
            col = ARM_COLOR[arm]
            ax.hlines(yy, s["lo"], s["hi"], color=col, lw=1.6, zorder=3,
                      capstyle="round")
            if s["sig"]:
                ax.plot([s["med"]], [yy], ls="none", marker=ARM_MARKER[arm],
                        ms=ARM_MS[arm], mfc=col, mec="white", mew=0.7, zorder=4)
            else:
                ax.plot([s["med"]], [yy], ls="none", marker=ARM_MARKER[arm],
                        ms=ARM_MS[arm], mfc="white", mec=col, mew=1.1, zorder=4)
            if arm == "p3-ate" and s["all_tie"]:
                ax.text(-2.4, yy, "exact tie ×75 (ate defers to MM)",
                        fontsize=6.4, color=MUTED, va="center", ha="right")
        if row["p"] >= 1.0:                     # K_n cell
            ax.text(XLIM[1] - 0.8, y, "n = 5 pairs", fontsize=6.8, color=INK2,
                    va="center", ha="right", fontstyle="italic")
        y -= 1.0

    for yy, lab in ylabels:
        ax.text(-0.012, yy, lab, ha="right", va="center", fontsize=8.0,
                color=INK, transform=ax.get_yaxis_transform())
    for yy, lab in ygroup:
        ax.text(-0.012, yy, lab, ha="right", va="center", fontsize=8.5,
                color=INK, fontweight="bold",
                transform=ax.get_yaxis_transform())

    ax.axvline(0, color=MUTED, lw=1.0, zorder=1.2)
    ax.set_xlim(*XLIM)
    ax.set_ylim(y + 0.35, 0.75)
    ax.set_xticks([-40, -30, -20, -10, 0, 10, 20])
    ax.set_xticklabels(["−40", "−30", "−20", "−10", "0", "+10", "+20"])
    ax.set_yticks([])
    ax.grid(True, axis="x")
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=2.5)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("median paired ΔACL$_{spur}$ vs minorminer (%)")
    ax.text(0.01, -0.062, "← p3 arm better", transform=ax.transAxes,
            fontsize=6.8, color=MUTED, ha="left", va="top")
    ax.text(0.99, -0.062, "MM better →", transform=ax.transAxes,
            fontsize=6.8, color=MUTED, ha="right", va="top")

    handles = [Line2D([], [], color=ARM_COLOR[a], lw=1.6, marker=ARM_MARKER[a],
                      ms=ARM_MS[a], mfc=ARM_COLOR[a], mec="white", mew=0.7)
               for a in ARMS3]
    handles += [Line2D([], [], ls="none", marker="o", ms=4.6, mfc=INK2,
                       mec="white", mew=0.7),
                Line2D([], [], ls="none", marker="o", ms=4.6, mfc="white",
                       mec=INK2, mew=1.1)]
    labels = ARMS3 + ["filled: Holm p < 0.05", "hollow: not significant"]
    fig.legend(handles, labels, loc="upper center", ncol=5,
               bbox_to_anchor=(0.5, 0.985), columnspacing=1.3,
               handletextpad=0.5)
    fig.text(0.985, 0.030,
             "marker = median of per-pair Δ% · line = bootstrap 95% CI of the median "
             "(10,000 resamples, fixed seed) · pairs = both-succeed (instance, seed)",
             ha="right", fontsize=6.4, color=MUTED)
    fig.text(0.985, 0.010,
             "ER cells n = 75 pairs (15 instances × 5 seeds); K$_n$ cells n = 5 "
             "(MM cliff-seed variance dominates the K140 CIs; §4.12) · "
             "Holm across cells within each arm",
             ha="right", fontsize=6.4, color=MUTED)
    save(fig, "fig_m4_forest")


# ---------------------------------------------------------------------------
# figure 5 — fig_m5_verdicts
# ---------------------------------------------------------------------------
# Category verdicts over the 35 graph families, verbatim from notes.md §4.11
# results (P16 merged verdict 2026-07-31; Z12 main batch 2026-07-29 /
# m5_z12_results.md; C16 main batch 2026-07-31): (WIN, tie, LOSS) per arm.
M5 = [
    ("Pegasus P16 — merged verdict", {
        "p3-ate":      (9, 22, 4),
        "p3-clmm":     (7, 24, 4),
        "p3-mmpolish": (18, 17, 0),
    }),
    ("Zephyr Z12", {
        "p3-ate":      (7, 22, 6),
        "p3-clmm":     (6, 27, 2),
        "p3-mmpolish": (17, 17, 1),
    }),
    ("Chimera C16", {
        "p3-ate":      (6, 26, 3),
        "p3-clmm":     (6, 21, 8),
        "p3-mmpolish": (15, 18, 2),
    }),
]
N_CAT = 35
WIN_C, TIE_C, LOSS_C = BLUE, GRID, RED


def fig_m5_verdicts():
    for _, arms in M5:
        for w, t, l in arms.values():
            assert w + t + l == N_CAT, "verdict counts must sum to 35"

    fig, ax = plt.subplots(figsize=(7.2, 3.65))
    fig.subplots_adjust(left=0.115, right=0.985, top=0.875, bottom=0.215)

    BARH = 0.62
    y = 0.0
    ylabels, ygroup = [], []
    for gi, (gname, arms) in enumerate(M5):
        if gi:
            y -= 0.9
        ygroup.append((y - 0.02, gname))   # drawn inside the axis, x = 0
        y -= 1.0
        for arm in ARMS3:
            w, t, l = arms[arm]
            ylabels.append((y, arm))
            for x0, width, col in [(0, w, WIN_C), (w, t, TIE_C),
                                   (w + t, l, LOSS_C)]:
                if width:
                    ax.add_patch(Rectangle((x0, y - BARH / 2), width, BARH,
                                           facecolor=col, edgecolor="white",
                                           linewidth=1.2, zorder=2.5))
            ax.text(w / 2, y, str(w), ha="center", va="center", fontsize=8.0,
                    fontweight="bold", color="white", zorder=3)
            ax.text(w + t / 2, y, str(t), ha="center", va="center",
                    fontsize=7.4, color=INK2, zorder=3)
            if l >= 3:
                ax.text(w + t + l / 2, y, str(l), ha="center", va="center",
                        fontsize=8.0, fontweight="bold", color="white",
                        zorder=3)
            elif l > 0:
                ax.text(N_CAT + 0.55, y, str(l), ha="left", va="center",
                        fontsize=7.4, color=INK2, zorder=3)
            else:
                ax.text(N_CAT + 0.55, y, "0 losses", ha="left", va="center",
                        fontsize=6.8, color=INK2, fontstyle="italic", zorder=3)
            y -= 0.85
    for yy, lab in ylabels:
        ax.text(-0.012, yy, lab, ha="right", va="center", fontsize=8.0,
                color=INK, transform=ax.get_yaxis_transform())
    for yy, lab in ygroup:                    # headers inside the plot area
        ax.text(0.0, yy, lab, ha="left", va="center", fontsize=8.5,
                color=INK, fontweight="bold", zorder=3)

    ax.set_xlim(0, 38.6)
    ax.set_ylim(y + 0.45, 0.55)
    ax.set_xticks([0, 5, 10, 15, 20, 25, 30, 35])
    ax.set_yticks([])
    ax.grid(True, axis="x")
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=2.5)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("graph categories (35 families per architecture)")

    handles = [Patch(facecolor=WIN_C, edgecolor="white"),
               Patch(facecolor=TIE_C, edgecolor=AXISC, linewidth=0.6),
               Patch(facecolor=LOSS_C, edgecolor="white")]
    fig.legend(handles, ["WIN — arm better than minorminer", "tie",
                         "LOSS — minorminer better"],
               loc="upper center", ncol=3, bbox_to_anchor=(0.5, 0.985),
               columnspacing=1.6, handletextpad=0.5)
    fig.text(0.985, 0.048,
             "§4.11 category verdicts over the full-library sweep (~595k rows); "
             "P16 merged = guarded re-run merged with the original batch",
             ha="right", fontsize=6.4, color=MUTED)
    fig.text(0.985, 0.012,
             "Residual losses decompose into the measured seed-noise null "
             "(sd 1.57 pt per family) + documented boundaries (§4.11)",
             ha="right", fontsize=6.4, color=MUTED)
    save(fig, "fig_m5_verdicts")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fig_m4_forest()
    fig_m5_verdicts()
    print("done:", ", ".join(sorted(
        p.name for p in FIGDIR.glob("fig_m*"))))
