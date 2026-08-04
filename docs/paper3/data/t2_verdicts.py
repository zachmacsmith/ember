"""§4.16 T2 verdict analyzer — the pre-registered noise-calibrated bars.

m5_analyze.py's built-in bars are the M5-era ±1 pt / ±0.10 (pre item 10);
§4.16 pre-registers the calibrated apparatus instead:
  - success drops REAL only above max(2.6 pt, 3 graphs) per family
    (2.6 pt ~ 95th pct of the measured sd-1.57 pt cross-batch null);
  - family ACL bars readable only at >= 10 both-succeed pairs
    (violation = mean dACL > +0.10, the M5 convention);
  - positive claims (p3-ember): dense-structured category wins
    (kneser/turan/complete/spin_glass: median% < -0.5 AND >= 55%W),
    mmpolish-class small wins on >= 5 families (same rule), and
    hardware_native retirement (success >= MM, mean dACL <= 0);
  - p3-mm-beta-fb: success within the null on EVERY family; ACL claim
    needs >= 3 below-gate families each median% < -0.5 AND >= 55%W.

Pairing: (graph_id, graph_name) vs the archived m5full_z12 minorminer rows
("(instance, trial) [CLI]" regime — cross-arm rows never share derived
seeds, errata 4.12.10).

Usage: .venv/bin/python docs/paper3/data/t2_verdicts.py
       [--t2 results/t2_z12/batch/results.db]
       [--baseline results/m5full_z12/batch/results.db]
Writes docs/paper3/data/t2_verdicts_summary.txt.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

DACL_BAR = 0.10
NULL_PT = 2.6
NULL_GRAPHS = 3
MIN_ACL_PAIRS = 10

DENSE_STRUCTURED = ("kneser", "turan", "complete", "spin_glass")


def load_categories():
    """graph_id -> manifest category (m5_analyze's exact resolution)."""
    import sys
    sys.path.insert(0, HERE)
    from m5_analyze import load_categories as _lc
    return _lc()


def load(db, arms=None):
    con = sqlite3.connect(db)
    q = ("SELECT graph_id, graph_name, algorithm, success, avg_chain_length "
         "FROM runs")
    out = defaultdict(dict)
    for gid, gname, algo, succ, acl in con.execute(q):
        if arms and algo not in arms:
            continue
        out[(gid, gname)][algo] = (int(bool(succ)), acl)
    con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t2", default=os.path.join(
        ROOT, "results", "t2_z12", "batch", "results.db"))
    ap.add_argument("--baseline", default=os.path.join(
        ROOT, "results", "m5full_z12", "batch", "results.db"))
    args = ap.parse_args()

    t2 = load(args.t2)
    base = load(args.baseline, arms={"minorminer"})
    cats = load_categories()

    lines = []
    out = lines.append
    out("=" * 96)
    out("T2 §4.16 verdicts — noise-calibrated bars (item 10): success drop "
        "REAL only above max(2.6 pt, 3 graphs);")
    out("ACL readable at >=10 pairs (violation = mean dACL > +0.10). Pairing "
        "(graph_id, graph_name) vs archived MM")
    out("rows — '(instance, trial) [CLI]' regime, sd-1.57 pt/family null "
        "(errata 4.12.10).")
    out("=" * 96)

    for arm in ("p3-ember", "p3-mm-beta-fb"):
        fam = defaultdict(lambda: {"n": 0, "arm_ok": 0, "mm_ok": 0,
                                   "d": [], "dpct": []})
        for key, algos in t2.items():
            if arm not in algos or key not in base:
                continue
            mm = base[key]["minorminer"]
            a = algos[arm]
            f = fam[cats.get(key[0], "?")]
            f["n"] += 1
            f["arm_ok"] += a[0]
            f["mm_ok"] += mm[0]
            if a[0] and mm[0] and a[1] and mm[1]:
                f["d"].append(a[1] - mm[1])
                f["dpct"].append(100.0 * (a[1] - mm[1]) / mm[1])

        real_drops, acl_viol, small_wins = [], [], []
        out(f"\n--- {arm} ---")
        hn = None
        for name in sorted(fam):
            f = fam[name]
            n = f["n"]
            drop_g = f["mm_ok"] - f["arm_ok"]
            drop_pt = 100.0 * drop_g / n if n else 0.0
            thr_g = max(NULL_PT / 100.0 * n, NULL_GRAPHS)
            drop_real = drop_g > thr_g
            pairs = len(f["d"])
            mean_d = statistics.mean(f["d"]) if pairs else None
            med_pct = statistics.median(f["dpct"]) if pairs else None
            winr = (100.0 * sum(1 for x in f["d"] if x < 0) / pairs
                    if pairs else None)
            acl_bad = (pairs >= MIN_ACL_PAIRS and mean_d is not None
                       and mean_d > DACL_BAR)
            if drop_real:
                real_drops.append((name, drop_g, drop_pt, thr_g))
            if acl_bad:
                acl_viol.append((name, mean_d, pairs))
            if (pairs >= MIN_ACL_PAIRS and med_pct is not None
                    and med_pct < -0.5 and winr >= 55):
                small_wins.append((name, med_pct, winr, pairs))
            if name == "hardware_native":
                hn = (f["arm_ok"], f["mm_ok"], mean_d, pairs)
            flag = ""
            if drop_real:
                flag += f"  DROP-REAL ({drop_g}g > {thr_g:.1f}g)"
            if acl_bad:
                flag += f"  ACL-VIOL (+{mean_d:.3f} @ {pairs}p)"
            if abs(drop_pt) > 0.9 or acl_bad or drop_real or pairs < 3:
                out(f"  {name:22s} n={n:5d} succ {f['arm_ok']:5d} vs "
                    f"{f['mm_ok']:5d} ({-drop_pt:+.1f} pt) "
                    f"meanD {mean_d if mean_d is None else round(mean_d, 3)} "
                    f"@ {pairs}p{flag}")

        out(f"  families: {len(fam)}; REAL success drops: "
            f"{len(real_drops)} {[(n, g) for n, g, _, _ in real_drops]}")
        out(f"  ACL violations (>=10p): "
            f"{[(n, round(d, 3), p) for n, d, p in acl_viol]}")
        out(f"  null expectation at 95th-pct threshold: ~{0.05 * len(fam):.1f} "
            f"family tails by chance")

        if arm == "p3-ember":
            ds = [w for w in small_wins if w[0] in DENSE_STRUCTURED]
            out(f"  POSITIVE dense-structured wins "
                f"(med<-0.5% & >=55%W): {[(n, round(m, 2), round(w)) for n, m, w, _ in ds]}"
                f" -> {'PASS' if len(ds) == len(DENSE_STRUCTURED) else 'CHECK'}"
                f" ({len(ds)}/{len(DENSE_STRUCTURED)})")
            out(f"  POSITIVE mmpolish-class small wins on >=5 families: "
                f"{len(small_wins)} families -> "
                f"{'PASS' if len(small_wins) >= 5 else 'FAIL'}")
            out(f"    {[(n, round(m, 2), round(w)) for n, m, w, _ in sorted(small_wins, key=lambda t: t[1])[:12]]}")
            if hn:
                ok = hn[0] >= hn[1] and (hn[2] is None or hn[2] <= 0)
                out(f"  POSITIVE hardware_native retired: succ {hn[0]} vs "
                    f"{hn[1]}, meanD {hn[2] if hn[2] is None else round(hn[2], 3)} @ {hn[3]}p -> "
                    f"{'PASS' if ok else 'FAIL'}")
            out(f"  BAR success-within-null everywhere: "
                f"{'PASS' if not real_drops else 'FAIL ' + str([n for n, *_ in real_drops])}")
            out(f"  BAR no ACL violation: "
                f"{'PASS' if not acl_viol else 'FAIL ' + str([n for n, *_ in acl_viol])}")
        else:
            out(f"  BAR (-fb) success within null on EVERY family: "
                f"{'PASS' if not real_drops else 'FAIL ' + str([n for n, *_ in real_drops])}")
            out(f"  ACL-claim families (med<-0.5% & >=55%W, >=3 needed): "
                f"{[(n, round(m, 2), round(w)) for n, m, w, _ in small_wins]}")

    text = "\n".join(lines)
    print(text)
    with open(os.path.join(HERE, "t2_verdicts_summary.txt"), "w") as fh:
        fh.write(text + "\n")


if __name__ == "__main__":
    main()
