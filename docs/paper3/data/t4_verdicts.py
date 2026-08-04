"""§4.17 T4 verdict analyzer — p3-mm-beta-mf at library scale.

Calibrated bars (item 10, identical to t2_verdicts.py): success drops REAL
only above max(2.6 pt, 3 graphs) per family; family ACL readable only at
>= 10 both-succeed pairs (violation = mean dACL > +0.10).

Reads three DBs: the T4 batch (p3-mm-beta-mf), the archived m5full_z12
baseline (minorminer — the primary comparison), and the archived t2_z12
batch (p3-mm-beta-fb — the redesign delta). All pairing on
(graph_id, graph_name); "(instance, trial)" [CLI] regime (errata 4.12.10).

§4.17 T4 BARS (mf vs minorminer):
  (1) success within the null on EVERY family — the five §4.16 -fb kill
      families (planted_solution, honeycomb, kagome, frustrated_square,
      king_graph) called out explicitly;
  (2) no ACL violation at >= 10 pairs — bcc_lattice and spin_glass called
      out explicitly;
  (3) POSITIVE: >= 3 below-gate families (median problem_density < 0.11)
      each median dACL% < -0.5 AND >= 55%W.
Plus the informational mf-vs-fb delta table.

Usage: .venv/bin/python docs/paper3/data/t4_verdicts.py
       [--t4 results/t4_z12/batch/results.db]
Writes docs/paper3/data/t4_verdicts_summary.txt.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

DACL_BAR = 0.10
NULL_PT = 2.6
NULL_GRAPHS = 3
MIN_ACL_PAIRS = 10
GATE = 0.11

KILL_FAMILIES = ("planted_solution", "honeycomb", "kagome",
                 "frustrated_square", "king_graph")
ACL_WATCH = ("bcc_lattice", "spin_glass")


def load_categories():
    sys.path.insert(0, HERE)
    from m5_analyze import load_categories as _lc
    return _lc()


def load(db, arm):
    con = sqlite3.connect(db)
    out = {}
    for gid, gname, succ, acl, dens in con.execute(
            "SELECT graph_id, graph_name, success, avg_chain_length, "
            "problem_density FROM runs WHERE algorithm=?", (arm,)):
        out[(gid, gname)] = (int(bool(succ)), acl, dens)
    con.close()
    return out


def compare(t4, base, cats, tag, lines):
    out = lines.append
    fam = defaultdict(lambda: {"n": 0, "a_ok": 0, "b_ok": 0, "d": [],
                               "dpct": [], "dens": []})
    for key, a in t4.items():
        if key not in base:
            continue
        b = base[key]
        f = fam[cats.get(key[0], "?")]
        f["n"] += 1
        f["a_ok"] += a[0]
        f["b_ok"] += b[0]
        if a[2] is not None:
            f["dens"].append(a[2])
        if a[0] and b[0] and a[1] and b[1]:
            f["d"].append(a[1] - b[1])
            f["dpct"].append(100.0 * (a[1] - b[1]) / b[1])

    real_drops, acl_viol, wins_below_gate, wins_all = [], [], [], []
    out(f"\n--- p3-mm-beta-mf vs {tag} ---")
    for name in sorted(fam):
        f = fam[name]
        n = f["n"]
        drop_g = f["b_ok"] - f["a_ok"]
        drop_pt = 100.0 * drop_g / n if n else 0.0
        thr_g = max(NULL_PT / 100.0 * n, NULL_GRAPHS)
        drop_real = drop_g > thr_g
        pairs = len(f["d"])
        mean_d = statistics.mean(f["d"]) if pairs else None
        med_pct = statistics.median(f["dpct"]) if pairs else None
        winr = (100.0 * sum(1 for x in f["d"] if x < 0) / pairs
                if pairs else None)
        med_dens = statistics.median(f["dens"]) if f["dens"] else None
        below = med_dens is not None and med_dens < GATE
        acl_bad = (pairs >= MIN_ACL_PAIRS and mean_d is not None
                   and mean_d > DACL_BAR)
        if drop_real:
            real_drops.append((name, drop_g))
        if acl_bad:
            acl_viol.append((name, mean_d, pairs))
        if (pairs >= MIN_ACL_PAIRS and med_pct is not None
                and med_pct < -0.5 and winr >= 55):
            wins_all.append((name, med_pct, winr, pairs))
            if below:
                wins_below_gate.append((name, med_pct, winr, pairs))
        interesting = (drop_real or acl_bad or abs(drop_pt) > 0.9
                       or name in KILL_FAMILIES or name in ACL_WATCH
                       or (med_pct is not None and med_pct < -0.5
                           and pairs >= MIN_ACL_PAIRS))
        if interesting:
            flag = ("  DROP-REAL" if drop_real else "") + \
                   (f"  ACL-VIOL (+{mean_d:.3f})" if acl_bad else "") + \
                   ("  [below-gate]" if below else "")
            out(f"  {name:22s} n={n:5d} succ {f['a_ok']:5d} vs {f['b_ok']:5d} "
                f"({-drop_pt:+.1f} pt) meanD "
                f"{mean_d if mean_d is None else round(mean_d, 3)} "
                f"med% {med_pct if med_pct is None else round(med_pct, 2)} "
                f"W {winr if winr is None else round(winr)} @ {pairs}p{flag}")
    tot_a = sum(f["a_ok"] for f in fam.values())
    tot_b = sum(f["b_ok"] for f in fam.values())
    out(f"  totals: {tot_a} vs {tot_b} ({tot_a - tot_b:+d}); families "
        f"{len(fam)}; null expectation ~{0.05 * len(fam):.1f} tails")
    return real_drops, acl_viol, wins_below_gate, wins_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t4", default=os.path.join(
        ROOT, "results", "t4_z12", "batch", "results.db"))
    ap.add_argument("--mm", default=os.path.join(
        ROOT, "results", "m5full_z12", "batch", "results.db"))
    ap.add_argument("--t2", default=os.path.join(
        ROOT, "results", "t2_z12", "batch", "results.db"))
    args = ap.parse_args()

    cats = load_categories()
    mf = load(args.t4, "p3-mm-beta-mf")
    mm = load(args.mm, "minorminer")
    fb = load(args.t2, "p3-mm-beta-fb")

    lines = ["=" * 96,
             "T4 §4.17 verdicts — p3-mm-beta-mf, calibrated bars "
             "(drop real > max(2.6 pt, 3 graphs); ACL at >= 10 pairs)",
             "=" * 96]
    out = lines.append

    drops, viols, wins_bg, wins_all = compare(mf, mm, cats, "minorminer",
                                              lines)
    out("")
    kill_hit = [d for d in drops if d[0] in KILL_FAMILIES]
    watch_hit = [v for v in viols if v[0] in ACL_WATCH]
    out(f"BAR1 success within null on EVERY family: "
        f"{'PASS' if not drops else 'FAIL ' + str(drops)}"
        f"  (the five §4.16 -fb kill families: "
        f"{'all clear' if not kill_hit else str(kill_hit)})")
    out(f"BAR2 no ACL violation at >=10 pairs: "
        f"{'PASS' if not viols else 'FAIL ' + str([(n, round(d, 3)) for n, d, _ in viols])}"
        f"  (bcc_lattice/spin_glass: "
        f"{'clear' if not watch_hit else str(watch_hit)})")
    out(f"BAR3 >=3 below-gate families med<-0.5% & >=55%W: "
        f"{len(wins_bg)} -> {'PASS' if len(wins_bg) >= 3 else 'FAIL'} "
        f"{[(n, round(m, 2), round(w)) for n, m, w, _ in wins_bg]}")
    out(f"(all small-win families, any density: "
        f"{[(n, round(m, 2), round(w)) for n, m, w, _ in wins_all]})")

    compare(mf, fb, cats, "p3-mm-beta-fb [redesign delta, informational]",
            lines)

    text = "\n".join(lines)
    print(text)
    with open(os.path.join(HERE, "t4_verdicts_summary.txt"), "w") as fh:
        fh.write(text + "\n")


if __name__ == "__main__":
    main()
