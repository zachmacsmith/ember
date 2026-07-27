#!/usr/bin/env python
"""Core figures for paper3 from the E0 density-resolved crossover map (notes.md
S4.1 + S4.1b; protocol.md rules 3-4).

Reads ONLY docs/paper3/data/e0_crossover.csv; writes ONLY docs/paper3/figures/.
Deterministic (no RNG; SOURCE_DATE_EPOCH pinned for byte-stable PDFs).

Regenerate:  .venv/bin/python docs/paper3/data/fig_crossover.py

Figures
  fig_crossover_map  (n, p) grid per topology, cell = best non-MM arm's median
                     paired dACL_spur% vs minorminer, winner letter, frontier
                     hatch, all-fail grey, p*(n) boundary.   [S4.1 outputs 1-2]
  fig_ladders        P16 n in {100,140,180}: median acl_spur vs p per arm with
                     IQR bands - "template flat, MM climbs". [S4.1 output 2]
  fig_frontier       success counts at the past-cliff cells. [S4.1 outputs 3-4]

Conventions (protocol.md): acl_spur column for every arm (rule 3); paired
deltas on both-succeed (instance, seed) pairs only, deterministic arms
(algo_seed = -1) pair against every minorminer run on the same instance
(rule 4); success rates reported separately and unpaired.  `clique` is
collapsed into `template` (identical acl_spur on all co-successes, S4.1);
"best non-MM arm" ranges over the three strategy families of S4.1 -
template (constructive), clmm (seeded search), attraction (alt-search).
pssa (== template +/- light polish per S4.1) and the mmfork-cuthill control
are excluded from "best" but keep their own rows in fig_frontier / the CSV.
"""

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "0")  # byte-stable PDF metadata

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import matplotlib.patheffects as pe

# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
CSV = HERE / "e0_crossover.csv"
FIGDIR = HERE.parent / "figures"
FIGDIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# style — dataviz-skill reference palette (light mode), one system for all figs
# ---------------------------------------------------------------------------
INK = "#0b0b0b"       # primary ink
INK2 = "#52514e"      # secondary ink
MUTED = "#898781"     # axis / muted labels
GRID = "#e1e0d9"      # hairline grid
AXISC = "#c3c2b7"     # baseline / axis rule
FAILGREY = "#b9b8b0"  # all-arms-fail cells
NEUTRAL0 = "#f0efec"  # diverging midpoint

BLUE = "#2a78d6"      # slot 1  — template / constructive family
ORANGE = "#eb6834"    # slot 2  — clmm (clique-seeded search)
AQUA = "#1baf7a"      # slot 3  — attraction (alt-search)
YELLOW = "#eda100"    # slot 4  — pssa
RED = "#e34948"       # diverging pole only (MM better)

ARM_COLOR = {
    "minorminer": INK2,       # the baseline wears the neutral dark
    "template": BLUE,
    "clmm": ORANGE,
    "attraction": AQUA,
    "pssa": YELLOW,
}
ARM_LABEL = {
    "minorminer": "minorminer",
    "template": "template",
    "clmm": "CLMM",
    "attraction": "attraction",
    "pssa": "PSSA",
}
CODE = {"template": "T", "clmm": "C", "attraction": "A"}

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
    "hatch.linewidth": 0.55,
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


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
raw = pd.read_csv(CSV)

# clique == template on acl_spur (S4.1: identical in every co-success) — verify, collapse
_t = raw[(raw.arm == "template") & (raw.success == 1)].set_index(["topo", "n", "p", "inst_seed"]).acl_spur
_c = raw[(raw.arm == "clique") & (raw.success == 1)].set_index(["topo", "n", "p", "inst_seed"]).acl_spur
_j = _t.to_frame("t").join(_c.to_frame("c"), how="inner")
assert len(_j) > 0 and (_j.t - _j.c).abs().max() == 0.0, "clique != template on acl_spur — S4.1 premise broken"
df = raw[raw.arm != "clique"].copy()

P_RUNGS = [0.05, 0.08, 0.12, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]  # sampled ladder, log-ish
assert set(df.p.unique()) <= set(P_RUNGS)

BEST_ARMS = ["template", "clmm", "attraction"]  # the three S4.1 strategy families


def paired_deltas(cell, arm):
    """Paired dACL_spur% of `arm` vs minorminer on both-succeed pairs (rule 4).

    Stochastic arms pair on (inst_seed, algo_seed); deterministic arms
    (algo_seed == -1) pair against every minorminer run on the same instance.
    """
    mm = cell[(cell.arm == "minorminer") & (cell.success == 1)]
    a = cell[(cell.arm == arm) & (cell.success == 1)]
    if mm.empty or a.empty:
        return []
    out = []
    if (cell[cell.arm == arm].algo_seed == -1).all():
        for inst, g in a.groupby("inst_seed"):
            av = g.acl_spur.iloc[0]
            for mv in mm[mm.inst_seed == inst].acl_spur:
                out.append((av - mv) / mv * 100.0)
    else:
        mmv = mm.set_index(["inst_seed", "algo_seed"]).acl_spur
        for _, r in a.iterrows():
            key = (r.inst_seed, r.algo_seed)
            if key in mmv.index:
                out.append((r.acl_spur - mmv.loc[key]) / mmv.loc[key] * 100.0)
    return out


def build_cells():
    """One row per sampled (topo, n, p) with class + best-arm stats."""
    rows = []
    for (topo, n, p), cell in df.groupby(["topo", "n", "p"]):
        mm = cell[cell.arm == "minorminer"]
        rec = dict(topo=topo, n=int(n), p=float(p),
                   mm_succ=int(mm.success.sum()), mm_att=len(mm))
        best_val, best_arm, npairs = None, None, 0
        for arm in BEST_ARMS:
            d = paired_deltas(cell, arm)
            if d and (best_val is None or np.median(d) < best_val):
                best_val, best_arm, npairs = float(np.median(d)), arm, len(d)
        rec.update(best_val=best_val, best_arm=best_arm, best_pairs=npairs)
        nonmm_succ = int(cell[cell.arm != "minorminer"].success.sum())
        if rec["mm_succ"] == 0 and nonmm_succ == 0:
            rec["cls"] = "allfail"
        elif rec["mm_succ"] == 0:
            rec["cls"] = "frontier"
            # winner among the three families: success rate, then median acl_spur,
            # then median wall time (the template's ms vs clmm's minutes)
            cand = []
            for arm in BEST_ARMS:
                a = cell[cell.arm == arm]
                s = a[a.success == 1]
                if len(s):
                    cand.append((-a.success.mean(), round(float(s.acl_spur.median()), 3),
                                 float(s.time.median()), arm))
            cand.sort()
            rec["best_arm"] = cand[0][3] if cand else None
        else:
            rec["cls"] = "paired"
        rows.append(rec)
    return pd.DataFrame(rows)


CELLS = build_cells()

# every sampled cell with n >= 260 fails on all arms (S4.1) → collapsed map column
assert (CELLS[CELLS.n >= 260].cls == "allfail").all(), "n>=260 cells no longer all-fail; un-collapse the 260+ column"

# ---------------------------------------------------------------------------
# figure 1 — fig_crossover_map
# ---------------------------------------------------------------------------
MAP_COLS = {
    "P16": [40, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240, "260+"],
    "Z12": [40, 60, 80, 100, 120, 140, 160, 179, 180, 184, 189, 200, 220, 240, "260+"],
}
# p*(n) — S4.1 output 1 (+ S4.1b: p*(140) in (0.12, 0.2], drawn at 0.16)
PSTAR = {
    "P16": [(40, 0.7), (60, 0.5), (80, 0.5), (100, 0.3), (140, 0.16), (160, 0.12), (180, 0.3)],
    "Z12": [(40, 0.9), (60, 0.7), (80, 0.5), (100, 0.3), (140, 0.16), (160, 0.12)],
}

NORM = TwoSlopeNorm(vmin=-34.0, vcenter=0.0, vmax=5.0)  # data: min -33.4, max +1.4
CMAP = LinearSegmentedColormap.from_list("headroom", [
    (0.00, "#0d366b"), (0.10, "#104281"), (0.22, "#2a78d6"), (0.34, "#5598e7"),
    (0.42, "#86b6ef"), (0.47, "#cde2fb"), (0.50, NEUTRAL0), (0.56, "#f6ddd8"),
    (0.72, "#f0aca4"), (0.86, "#e97b74"), (1.00, RED),
])

_P_CENTER = {p: i + 0.5 for i, p in enumerate(P_RUNGS)}


def p_to_y(p):
    """Ordinal-row y for probability p (log-interp between neighboring rungs)."""
    if p in _P_CENTER:
        return _P_CENTER[p]
    lo = max(r for r in P_RUNGS if r < p)
    hi = min(r for r in P_RUNGS if r > p)
    f = (math.log(p) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return _P_CENTER[lo] + f * (_P_CENTER[hi] - _P_CENTER[lo])


def _text_color(rgba):
    r, g, b = rgba[:3]
    return "white" if (0.2126 * r + 0.7152 * g + 0.0722 * b) < 0.45 else INK


def draw_map_panel(ax, topo):
    cols = MAP_COLS[topo]
    ncol = len(cols)
    colx = {c: i for i, c in enumerate(cols)}
    GAP = 0.07
    # letters at cells whose center a p* vertex occupies get nudged down
    vertex_cells = {(n, pv) for n, pv in PSTAR[topo] if pv in P_RUNGS}
    drawn_260 = set()  # collapse all n>=260 cells into one grey tile per row
    for _, c in CELLS[CELLS.topo == topo].iterrows():
        col = "260+" if c.n >= 260 else c.n
        i = colx[col]
        j = P_RUNGS.index(c.p)
        if col == "260+":
            if j in drawn_260:
                continue
            drawn_260.add(j)
        x0, y0 = i + GAP, j + GAP
        w = h = 1 - 2 * GAP
        if c.cls == "allfail" or col == "260+":
            ax.add_patch(Rectangle((x0, y0), w, h, facecolor=FAILGREY, edgecolor="none"))
            continue
        if c.cls == "frontier":
            ax.add_patch(Rectangle((x0, y0), w, h, facecolor="white",
                                   edgecolor=BLUE, hatch="////", linewidth=0.7))
            ax.text(i + 0.5, j + 0.5, CODE[c.best_arm], ha="center", va="center",
                    fontsize=6.8, fontweight="bold", color=INK,
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
            continue
        # paired cell
        fill = CMAP(NORM(c.best_val))
        ax.add_patch(Rectangle((x0, y0), w, h, facecolor=fill,
                               edgecolor=GRID, linewidth=0.4))
        if c.best_arm is not None:
            if (c.n, c.p) in vertex_cells:
                # p* vertex sits on this cell's center: nudge the letter down and
                # draw it above the dashed line with a fill-colored halo
                ax.text(i + 0.5, j + 0.26, CODE[c.best_arm], ha="center",
                        va="center", fontsize=6.4, fontweight="bold",
                        color=_text_color(fill), zorder=6,
                        path_effects=[pe.withStroke(linewidth=2.0, foreground=fill)])
            else:
                ax.text(i + 0.5, j + 0.5, CODE[c.best_arm], ha="center",
                        va="center", fontsize=6.8, fontweight="bold",
                        color=_text_color(fill))
    # p*(n) boundary
    px = [colx[n] + 0.5 for n, _ in PSTAR[topo]]
    py = [p_to_y(pv) for _, pv in PSTAR[topo]]
    ax.plot(px, py, color=INK, lw=1.3, ls=(0, (4, 2.2)), marker="o", ms=3.2,
            mfc=INK, mec="white", mew=0.6, zorder=5, solid_capstyle="round",
            path_effects=[pe.Stroke(linewidth=2.9, foreground="white"), pe.Normal()])
    lx, ly = {"P16": (0.14, 5.55), "Z12": (0.18, 8.12)}[topo]
    ax.text(lx, ly, "p*(n)", fontsize=7.6, fontstyle="italic", color=INK, zorder=6,
            path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    # frame / ticks
    ax.set_xlim(0, ncol)
    ax.set_ylim(0, len(P_RUNGS))
    ax.set_xticks([i + 0.5 for i in range(ncol)])
    xlabels = [("≥260" if c == "260+" else str(c)) for c in cols]
    xlabels = [(f"\n{t}" if i % 2 else t) for i, t in enumerate(xlabels)]  # stagger
    ax.set_xticklabels(xlabels, fontsize=7.2, linespacing=0.9)
    ax.set_yticks([i + 0.5 for i in range(len(P_RUNGS))])
    ax.set_yticklabels(["0.05", "0.08", "0.12", "0.2", "0.3", "0.5", "0.7", "0.9",
                        "1.0 (K$_n$)"])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title({"P16": "Pegasus P16", "Z12": "Zephyr Z12"}[topo], loc="left",
                 fontweight="bold", pad=6)


def fig_crossover_map():
    fig = plt.figure(figsize=(7.2, 4.65))
    gs = fig.add_gridspec(1, 3, width_ratios=[12, 15, 0.5], wspace=0.16,
                          left=0.095, right=0.925, top=0.915, bottom=0.245)
    axP = fig.add_subplot(gs[0, 0])
    axZ = fig.add_subplot(gs[0, 1])
    cax = fig.add_subplot(gs[0, 2])
    draw_map_panel(axP, "P16")
    draw_map_panel(axZ, "Z12")
    axP.set_ylabel("edge probability p  (sampled rungs; 1.0 = K$_n$)")
    axZ.set_yticklabels([])
    fig.supxlabel("graph size n (vertices)", y=0.148, fontsize=9, color=INK)

    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=NORM)
    cb = fig.colorbar(sm, cax=cax)
    cb.set_ticks([-30, -20, -10, -5, 0, 5])
    cb.set_ticklabels(["−30", "−20", "−10", "−5", "0", "+5"])
    cb.ax.tick_params(labelsize=7.2, length=0)
    cb.outline.set_edgecolor(AXISC)
    cb.outline.set_linewidth(0.6)
    cb.set_label("best non-MM arm: median paired ΔACL$_{spur}$ vs minorminer (%)",
                 fontsize=7.6, color=INK2)
    cb.ax.text(0.5, -0.045, "non-MM\nbetter", transform=cb.ax.transAxes, ha="center",
               va="top", fontsize=6.4, color=MUTED)
    cb.ax.text(0.5, 1.045, "MM\nbetter", transform=cb.ax.transAxes, ha="center",
               va="bottom", fontsize=6.4, color=MUTED)

    handles = [
        Patch(facecolor="white", edgecolor=BLUE, hatch="////", linewidth=0.7),
        Patch(facecolor=FAILGREY, edgecolor="none"),
        Line2D([], [], color=INK, lw=1.3, ls=(0, (4, 2.2)), marker="o", ms=3.2,
               mfc=INK, mec="white"),
    ]
    labels = [
        "frontier: minorminer 0-for-all (letter = arm that embeds)",
        "every arm fails (60 s)",
        "p*(n): template-beats-MM crossover",
    ]
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.062),
               ncol=3, fontsize=6.8, handlelength=1.5, columnspacing=1.0,
               handletextpad=0.5)
    fig.text(0.5, 0.036,
             "cell letter = best of the three §4.1 families:  T template (constructive)  ·  "
             "C CLMM (clique-seeded search)  ·  A attraction (alt-search)",
             ha="center", fontsize=6.8, color=INK2)
    fig.text(0.5, 0.012,
             "cell value = median paired ΔACL$_{spur}$% on both-succeed pairs  ·  "
             "blank = unsampled  ·  ≥260 column: all sampled cells n = 260–600 fail on every arm",
             ha="center", fontsize=6.8, color=INK2)
    save(fig, "fig_crossover_map")


# ---------------------------------------------------------------------------
# figure 2 — fig_ladders  (P16; n = 100 / 140 / 180)
# ---------------------------------------------------------------------------
LADDER_NS = [100, 140, 180]
LADDER_ARMS = ["attraction", "clmm", "template", "minorminer"]  # draw order (mm on top)
ARM_MARKER = {"minorminer": "o", "template": "s", "clmm": "D", "attraction": "^"}
PSTAR_AT = {100: 0.3, 140: 0.16, 180: 0.3}


LINE_Z = {"attraction": 3.0, "clmm": 3.1, "template": 3.3, "minorminer": 3.6}
MARK_Z = {"attraction": 4.0, "template": 4.2, "minorminer": 4.8, "clmm": 5.5}
MARK_MS = {"attraction": 4.6, "template": 5.0, "minorminer": 4.8, "clmm": 3.3}


def fig_ladders():
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.05), sharey=True)
    fig.subplots_adjust(left=0.075, right=0.985, top=0.795, bottom=0.225, wspace=0.10)
    for ax, n in zip(axes, LADDER_NS):
        sub = df[(df.topo == "P16") & (df.n == n)]
        ax.set_xscale("log")
        ax.grid(True, axis="y")
        ax.set_axisbelow(True)
        # p* marker
        ps = PSTAR_AT[n]
        ax.axvline(ps, color=INK, lw=0.9, ls=(0, (4, 2.2)), zorder=1.5)
        ax.text(ps, 0.025, f" p* = {ps}", transform=ax.get_xaxis_transform(),
                ha="left", va="bottom", fontsize=6.8, fontstyle="italic", color=INK)
        for arm in LADDER_ARMS:
            a = sub[sub.arm == arm]
            pts = []
            for p, g in a.groupby("p"):
                s = g[g.success == 1].acl_spur
                if len(s):
                    pts.append((p, s.median(), s.quantile(0.25), s.quantile(0.75),
                                int(g.success.sum()), len(g)))
            if not pts:
                continue
            pts.sort()
            P, MED, Q1, Q3, K, N = map(np.array, zip(*pts))
            col = ARM_COLOR[arm]
            ax.fill_between(P, Q1, Q3, color=col, alpha=0.10, lw=0, zorder=2)
            ax.plot(P, MED, color=col, lw=1.9 if arm != "clmm" else 1.5,
                    zorder=LINE_Z[arm], solid_capstyle="round")
            full = K >= 0.8 * N
            ax.plot(P[full], MED[full], ls="none", marker=ARM_MARKER[arm],
                    ms=MARK_MS[arm], mfc=col, mec="white", mew=0.7,
                    zorder=MARK_Z[arm])
            ax.plot(P[~full], MED[~full], ls="none", marker=ARM_MARKER[arm],
                    ms=4.6, mfc="white", mec=col, mew=1.1, zorder=MARK_Z[arm])
            dy = -11 if arm == "minorminer" else 7
            halo = [pe.withStroke(linewidth=2.2, foreground="white")]
            for p, m, k, ntot in zip(P[~full], MED[~full], K[~full], N[~full]):
                ax.annotate(f"{k}/{ntot}", (p, m), xytext=(0, dy), fontsize=6.2,
                            textcoords="offset points", ha="center", color=INK2,
                            zorder=6, path_effects=halo)
            if arm == "minorminer" and K[-1] > 0 and N[-1] > 0:
                # mark the cliff: first fully-failed rung after the last success
                dead = sorted(d for d in set(a.p.unique()) - set(P) if d > P[-1])
                if dead:
                    ax.annotate(f"0/{N[-1]}", (dead[0], MED[-1]), xytext=(0, 0),
                                textcoords="offset points", ha="center",
                                va="center", fontsize=6.2, color=MUTED,
                                zorder=6, path_effects=halo)
        ax.set_title(f"P16 · n = {n}", loc="left", fontsize=9, fontweight="bold")
        ax.set_xlim(0.042, 1.25)
        ax.set_xticks([0.05, 0.1, 0.2, 0.5, 1.0])
        ax.set_xticklabels(["0.05", "0.1", "0.2", "0.5", "1"])
        ax.minorticks_off()
        ax.tick_params(axis="both", length=2.5)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    # direct labels where the story is (n=180): template flat, MM dies
    ax3 = axes[2]
    ax3.annotate("template", (0.78, 16.62), xytext=(0.52, 14.4), fontsize=7.2,
                 color=INK2,
                 arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.9,
                                 shrinkA=2, shrinkB=3))
    ax3.annotate("minorminer", (0.155, 16.9), xytext=(0.078, 19.8), fontsize=7.2,
                 color=INK2,
                 arrowprops=dict(arrowstyle="-", color=INK2, lw=0.9,
                                 shrinkA=2, shrinkB=4))
    ax3.text(0.046, 4.6, "attraction:\n15/15 at p = 0.08,\n0/15 beyond",
             fontsize=6.4, color=MUTED, ha="left", va="bottom", linespacing=1.4)
    axes[0].set_ylabel("ACL (qubits/chain), spur-pruned")
    axes[0].set_ylim(1.0, 25.0)
    fig.supxlabel("edge probability p (log scale)", y=0.075, fontsize=9, color=INK)
    handles = [Line2D([], [], color=ARM_COLOR[a], lw=1.9, marker=ARM_MARKER[a],
                      ms=4.4, mfc=ARM_COLOR[a], mec="white", mew=0.8)
               for a in ["minorminer", "template", "clmm", "attraction"]]
    fig.legend(handles, [ARM_LABEL[a] for a in ["minorminer", "template", "clmm", "attraction"]],
               loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.005),
               columnspacing=1.6, handletextpad=0.5)
    fig.text(0.985, 0.012,
             "line = median ACL$_{spur}$ over successful runs · band = IQR · "
             "open marker + k/N = partial success",
             ha="right", fontsize=6.4, color=MUTED)
    save(fig, "fig_ladders")


# ---------------------------------------------------------------------------
# figure 3 — fig_frontier
# ---------------------------------------------------------------------------
FRONTIER_CELLS = [
    ("P16", 180, 1.0, "K180"),
    ("P16", 180, 0.9, "n=180, p=0.9"),
    ("P16", 200, 0.2, "n=200, p=0.2"),
    ("Z12", 179, 1.0, "K179"),
    ("Z12", 180, 1.0, "K180"),
    ("Z12", 184, 1.0, "K184  (max clique)"),
    ("Z12", 180, 0.5, "n=180, p=0.5"),
    ("Z12", 200, 0.2, "n=200, p=0.2"),
    ("Z12", 220, 0.12, "n=220, p=0.12"),
]
FRONTIER_ARMS = ["minorminer", "clmm", "template", "pssa"]


def fig_frontier():
    fig, ax = plt.subplots(figsize=(7.2, 5.1))
    fig.subplots_adjust(left=0.19, right=0.985, top=0.895, bottom=0.115)
    LANE, CGAP, GGAP = 1.0, 1.5, 3.0
    y = 0.0
    ylabels, ygroup = [], []
    prev_topo = None
    for topo, n, p, label in FRONTIER_CELLS:
        if topo != prev_topo:
            if prev_topo is not None:
                y -= GGAP
            ygroup.append((y - 0.1, {"P16": "Pegasus P16", "Z12": "Zephyr Z12"}[topo]))
            y -= 1.6
            prev_topo = topo
        cell = df[(df.topo == topo) & (df.n == n) & (df.p == p)]
        y0 = y
        for arm in FRONTIER_ARMS:
            a = cell[cell.arm == arm]
            k, ntot = int(a.success.sum()), len(a)
            rate = k / ntot if ntot else 0.0
            col = ARM_COLOR[arm]
            if (a.status == "INFEASIBLE").all() and len(a):
                ax.plot([0], [y], marker="x", ms=4.5, color=MUTED, mew=1.2)
                ax.text(0.03, y, "infeasible (n > max clique)", fontsize=6.6,
                        color=MUTED, va="center", fontstyle="italic")
            else:
                ax.hlines(y, 0, rate, color=col, lw=1.5, alpha=0.55, zorder=2)
                ax.plot([rate], [y], marker="o", ms=6.4, mfc=col, mec="white",
                        mew=1.1, zorder=3)
                ax.text(rate + 0.035, y, f"{k}/{ntot}", fontsize=7.0, color=INK2,
                        va="center")
            y -= LANE
        ylabels.append(((y0 + y + LANE) / 2.0, label))
        y -= CGAP
    for yy, lab in ylabels:
        ax.text(-0.045, yy, lab, ha="right", va="center", fontsize=8.0, color=INK,
                transform=ax.get_yaxis_transform())
    for yy, lab in ygroup:
        ax.text(-0.045, yy, lab, ha="right", va="center", fontsize=8.5, color=INK,
                fontweight="bold", transform=ax.get_yaxis_transform())
    ax.set_xlim(-0.02, 2.02)
    ax.set_ylim(y + 0.4, 1.6)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"])
    ax.set_yticks([])
    ax.grid(True, axis="x")
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=2.5)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("success rate at 60 s  (embeds / attempts)")

    # callout: the ACL prize past MM's cliff (S4.1 output 4)
    kx = 1.26
    ky = ylabels[4][0]  # start beside the Z12 K-block
    ax.plot([kx - 0.05, kx - 0.05], [ky - 12.6, ky + 0.7], color=BLUE, lw=2.0,
            solid_capstyle="round")
    ax.text(kx, ky,
            "the frontier is not a consolation\n"
            "prize: at Z12 K184 — the busclique\n"
            "bound — template embeds at\n"
            "ACL$_{spur}$ 12.98 vs minorminer's\n"
            "own best dense anchor,\n"
            "K140 = 15.09\n"
            "(−14% ACL on +44 vertices)\n\n"
            "P16: K180 template 16.64\n"
            "vs minorminer K140 = 19.77",
            fontsize=7.4, color=INK2, va="top", linespacing=1.42)

    handles = [Line2D([], [], ls="none", marker="o", ms=6.4, mfc=ARM_COLOR[a],
                      mec="white", mew=1.1) for a in FRONTIER_ARMS]
    fig.legend(handles, [ARM_LABEL[a] for a in FRONTIER_ARMS], loc="upper center",
               ncol=4, bbox_to_anchor=(0.5, 0.975), columnspacing=1.6,
               handletextpad=0.4)
    fig.text(0.985, 0.022,
             "attempts: ER cells 15 = 3 instances × 5 seeds; K$_n$ cells 5 = 1 × 5; "
             "deterministic template: 3 (ER) / 1 (K$_n$)",
             ha="right", fontsize=6.4, color=MUTED)
    save(fig, "fig_frontier")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fig_crossover_map()
    fig_ladders()
    fig_frontier()
    print("done:", ", ".join(sorted(p.name for p in FIGDIR.glob("fig_*"))))
