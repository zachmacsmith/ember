"""
docs/paper/data/analyze.py
==========================
Regenerate EVERY statistic and table reported in the PathFinder article
(docs/paper/pathfinder.tex) from the sweep outputs in this directory. This is the
verification/transparency layer: each printed line is annotated with the paper
location it backs, and ``--latex`` re-emits the LaTeX rows for Tables 1--3 and the
appendix.

Usage:
    python analyze.py            # human-readable report (every reported number)
    python analyze.py --latex    # also print LaTeX rows for the paper's tables

Reads:  summary.csv, raw_results.csv  (produced by run_sweep.py)
Pure standard library (csv, statistics); no third-party deps.
"""
from __future__ import annotations

import csv
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALGOS = ["minorminer", "minorminer-layout", "pathfinder", "pathfinder-thorough"]


def load():
    summ = {(r["source"], r["target"], r["algorithm"]): r
            for r in csv.DictReader(open(os.path.join(HERE, "summary.csv")))}
    raw = list(csv.DictReader(open(os.path.join(HERE, "raw_results.csv"))))
    return summ, raw


def F(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pairs(summ):
    return sorted({(s, t) for (s, t, a) in summ})


# ---------------------------------------------------------------- report -------

def report(summ, raw):
    P = pairs(summ)
    print(f"# PathFinder results — regenerated from summary.csv / raw_results.csv")
    print(f"# {len(P)} (source,target) cells x {len(ALGOS)} algorithms x 5 seeds\n")

    # 100% success (Abstract; §5 "all four methods embed every instance")
    min_succ = min(F(summ[(s, t, a)]["success_rate"]) for s, t in P for a in ALGOS)
    print(f"[success] min success_rate over all cells = {min_succ:.3f}   "
          f"(paper: '100% success on every target')")

    # never-regress, per-seed (Abstract; §5 'maximum observed difference 0.000')
    perseed = {}
    for r in raw:
        perseed.setdefault((r["source"], r["target"], r["seed"]), {})[r["algorithm"]] = F(r["avg_chain_length"])
    bad = wp = 0
    for d in perseed.values():
        if "minorminer" in d and "pathfinder" in d:
            wp += 1
            if d["pathfinder"] - d["minorminer"] > 1e-9:
                bad += 1
    wmean = max(st.mean([F(summ[(s, t, "pathfinder")]["acl_mean"])]) - F(summ[(s, t, "minorminer")]["acl_mean"])
                for s, t in P)
    print(f"[never-regress] per-seed runs where pathfinder ACL > minorminer ACL: {bad}/{wp}")
    print(f"[never-regress] max mean-level (pathfinder-minorminer) over {len(P)} cells = {wmean:+.6f}   "
          f"(paper: 'maximum observed difference 0.000')")

    # thorough vs minorminer: ACL reductions (Abstract '1-11%, mean ~5%'; §5 ranges)
    def acl_delta(cells):
        out = []
        for s, t in cells:
            mm = F(summ[(s, t, "minorminer")]["acl_mean"])
            th = F(summ[(s, t, "pathfinder-thorough")]["acl_mean"])
            out.append(100 * (th - mm) / mm)
        return out
    allc = P
    er_all = [(s, t) for s, t in P if s.startswith("ER_")]
    er_cp = [(s, t) for s, t in P if s.startswith("ER_") and t == "pegasus_6"]
    er_cp_6 = [(s, t) for s, t in er_cp if s.split("_")[1] in ("n30", "n40")]
    for name, c in [("ALL 35", allc), ("ER all targets", er_all),
                    ("ER clean P6 (9 cells)", er_cp), ("ER clean P6 n30/n40 (Table 1, 6 cells)", er_cp_6)]:
        d = acl_delta(c)
        print(f"[ACL Δ thorough vs mm] {name:42s} {min(d):+.1f}%..{max(d):+.1f}%  mean {st.mean(d):+.1f}%")
    # biggest single ACL gain and which source (paper: '-10.6% on a d-regular source')
    worst = min(((100 * (F(summ[(s, t, 'pathfinder-thorough')]['acl_mean']) - F(summ[(s, t, 'minorminer')]['acl_mean']))
                  / F(summ[(s, t, 'minorminer')]['acl_mean']), s, t) for s, t in P))
    print(f"[ACL Δ] largest single reduction = {worst[0]:+.1f}% at {worst[1]} on {worst[2]}   "
          f"(paper: '-10.6% on a d-regular source')")

    # std reductions (Abstract '30 of 35, up to 77%'; §5 '8 of 9 clean P6, up to 76%')
    def std_stats(cells):
        red = inc = 0
        best = 0.0
        for s, t in cells:
            a = F(summ[(s, t, "minorminer")]["acl_std"])
            b = F(summ[(s, t, "pathfinder-thorough")]["acl_std"])
            if a in (None, 0.0) or b is None:
                continue
            dd = 100 * (b - a) / a
            if dd < 0:
                red += 1
            elif dd > 0:
                inc += 1
            best = min(best, dd)
        return red, inc, best
    r35 = std_stats(P)
    rcp = std_stats(er_cp)
    print(f"[std Δ] global: {r35[0]} reduced / {r35[1]} increased of {len(P)}; max reduction {r35[2]:.1f}%   "
          f"(paper: '30 of the 35 ... up to 77%')")
    print(f"[std Δ] clean-P6 ER: {rcp[0]} reduced / {rcp[1]} increased of {len(er_cp)}; max reduction {rcp[2]:.1f}%   "
          f"(paper: '8 of 9 ... up to 76%'; exception n40 d0.3)")

    # thorough is min ACL everywhere (Appendix)
    notmin = sum(1 for s, t in P
                 if F(summ[(s, t, "pathfinder-thorough")]["acl_mean"]) >
                 min(F(summ[(s, t, a)]["acl_mean"]) for a in ALGOS) + 1e-9)
    print(f"[min] cells where pathfinder-thorough is NOT lowest ACL: {notmin}/{len(P)}   "
          f"(paper: 'lowest ACL in all 35 cells')")


# ---------------------------------------------------------------- latex --------

def _row(summ, s, t):
    return " & ".join(f"{F(summ[(s, t, a)]['acl_mean']):.2f}\\,({F(summ[(s, t, a)]['acl_std']):.2f})"
                      for a in ALGOS)


def latex(summ):
    print("\n% ===== Table 1 (clean P6, n30/n40) — ACL(std), max, qubits =====")
    for n in (30, 40):
        for d in (0.3, 0.5, 0.7):
            s, t = f"ER_n{n}_d{d}", "pegasus_6"
            print(f"\\multirow{{4}}{{*}}{{$n{{=}}{n},d{{=}}{d}$}}")
            for a in ALGOS:
                r = summ[(s, t, a)]
                bold = "\\textbf{%s}" % f"{F(r['acl_mean']):.2f}" if a == "pathfinder-thorough" else f"{F(r['acl_mean']):.2f}"
                print(f" & \\texttt{{{a}}} & {bold} ({F(r['acl_std']):.2f}) & {F(r['maxchain_mean']):g} & {F(r['qubits_mean']):g} \\\\")
            print("\\midrule")

    print("\n% ===== Table 2 (clean P6 timing, mean s) =====")
    for n in (30, 40):
        for d in (0.3, 0.5, 0.7):
            s, t = f"ER_n{n}_d{d}", "pegasus_6"
            ts = " & ".join(f"{F(summ[(s, t, a)]['time_mean']):.2f}" for a in ALGOS)
            print(f"$n{{=}}{n},d{{=}}{d}$ & {ts} \\\\")

    print("\n% ===== Table 3 (ER_n40_d0.5 across topologies) =====")
    labels = {"pegasus_6": "Pegasus $P_6$", "pegasus_6_broken5": "broken $P_6$ ($5\\%$)", "zephyr_4": "Zephyr $Z_4$"}
    for t in ("pegasus_6", "pegasus_6_broken5", "zephyr_4"):
        print(f"\\multirow{{4}}{{*}}{{{labels[t]}}}")
        for a in ALGOS:
            r = summ[("ER_n40_d0.5", t, a)]
            bold = "\\textbf{%s}" % f"{F(r['acl_mean']):.2f}" if a == "pathfinder-thorough" else f"{F(r['acl_mean']):.2f}"
            print(f" & \\texttt{{{a}}} & {bold} ({F(r['acl_std']):.2f}) & {F(r['time_mean']):.2f} \\\\")
        print("\\midrule")

    print("\n% ===== Figure 3 coordinates (n40 clean P6, ACL vs density) =====")
    for a in ALGOS:
        coords = "".join(f"({d},{F(summ[(f'ER_n40_d{d}', 'pegasus_6', a)]['acl_mean'])})" for d in (0.3, 0.5, 0.7))
        print(f"\\addplot+[thick] coordinates {{{coords}}};  % {a}")

    print("\n% ===== Appendix Table (all 35 cells) =====")
    er = [f"ER_n{n}_d{d}" for n in (20, 30, 40) for d in (0.3, 0.5, 0.7)]
    gen = [f"REG_n{n}_k{k}" for n in (30, 40) for k in (4, 6)] + [f"BA_n{n}_m{m}" for n in (30, 40) for m in (3, 5)]

    def lbl(s):
        p = s.split("_")
        kind = {"ER": "ER", "REG": "reg", "BA": "BA"}[p[0]]
        return f"{kind} ${p[1][0]}{{=}}{p[1][1:]},{p[2][0]}{{=}}{p[2][1:]}$"
    for title, srcs, t in [("Pegasus $P_6$ (clean)", er + gen, "pegasus_6"),
                           ("broken Pegasus $P_6$ ($5\\%$ faults)", er, "pegasus_6_broken5"),
                           ("Zephyr $Z_4$", er, "zephyr_4")]:
        print(f"\\multicolumn{{5}}{{l}}{{\\emph{{{title}}}}}\\\\\n\\midrule")
        for s in srcs:
            if (s, t, "minorminer") in summ:
                print(f"{lbl(s)} & {_row(summ, s, t)} \\\\")
        print("\\midrule")


if __name__ == "__main__":
    summ, raw = load()
    report(summ, raw)
    if "--latex" in sys.argv:
        latex(summ)
