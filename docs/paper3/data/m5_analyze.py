"""
docs/paper3/data/m5_analyze.py
===============================
M5 analysis — the structured/lattice no-regression verdict
(experiments/m5_noregress.yaml; pattern: docs/paper2/data/analyze_fullember.py).

Reads a CLI batch's results.db, pairs runs on (graph_id, graph_name), buckets
by manifest category x size band, and reports per p3 arm vs minorminer:
both/only-arm/only-MM/neither counts, mean+median dACL, win/loss/tie, success
rates, median wall times — then prints the PRE-REGISTERED M5 bar verdict per
family (= manifest category):

  FAIL iff, for any p3 arm vs minorminer within a family,
    mean dACL (both-succeed pairs)  >  +0.10        OR
    success-rate drop               >  1 percentage point.

Measurement caveats (printed with the output):
  * "(instance, trial) pairing [CLI]" — the CLI salts per-trial seeds with
    the algorithm name (protocol rule 1); this is a breadth sweep, never
    pooled with script-route statistics.
  * dACL is RAW avg_chain_length — the CLI computes no spur-pruned column,
    so the comparison is raw-vs-raw for every arm (rule 3 satisfied by using
    exactly one column, named here).
  * Wall times are within-batch context only (rule 5; the batch runs at 56
    workers, above the 48-worker bound for wall_time tables).

Run:
  .venv/bin/python docs/paper3/data/m5_analyze.py <batch_dir | results.db>
  .venv/bin/python docs/paper3/data/m5_analyze.py --selftest

--selftest builds a 20-row in-memory sqlite fixture (5 graphs x 4 arms,
two families) with one engineered dACL failure and one engineered
success-drop failure, runs the full analysis path against it, and asserts
the verdicts — no batch required. Exit 0 on success.

Exit codes: 0 = analysis ran (the verdict itself is a printed result, not an
exit code); nonzero only for missing/unreadable data or selftest failure.
"""

import os
import sqlite3
import sys
from collections import defaultdict

BASELINE = "minorminer"
P3_ARMS = ["p3-ate", "p3-clmm", "p3-mmpolish"]
ARMS = [BASELINE] + P3_ARMS

BANDS = [(0, 30, "n<=30"), (31, 100, "31-100"), (101, 300, "101-300"),
         (301, 1000, "301-1000"), (1001, 10 ** 9, "n>1000")]

DACL_BAR = 0.10          # mean dACL above this fails the family
DROP_BAR_PT = 1.0        # success-rate drop (pp) above this fails the family
EPS = 1e-9
SMALL_N = 10             # families with fewer paired graphs get a small-n tag


def band(n):
    for lo, hi, name in BANDS:
        if lo <= n <= hi:
            return name
    return "?"


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else float("nan")


def load_categories():
    """graph_id -> manifest category ('?' when the manifest is unavailable)."""
    try:
        from ember_qc.load_graphs import _manifest_by_id
        return {gid: e.get("category", "?") or "?"
                for gid, e in _manifest_by_id().items()}
    except Exception as e:  # analysis must still run without the package
        print(f"warning: manifest unavailable ({e!r}); categories = '?'")
        return {}


def load_per_graph(db):
    """(graph_id, graph_name) -> algo -> dict(succ, acl, wall, n).

    trials=1 by design; duplicate (graph, algo) rows (reruns/extra trials)
    are aggregated defensively (success = any; acl = mean of successful;
    wall = median) with a warning.
    """
    rows = db.execute(
        "SELECT graph_id, graph_name, algorithm, success, avg_chain_length, "
        "wall_time, problem_nodes FROM runs").fetchall()
    acc = defaultdict(lambda: defaultdict(
        lambda: {"succ": 0, "acls": [], "walls": [], "n": 0, "rows": 0}))
    for gid, gname, algo, succ, acl, wt, n in rows:
        if algo not in ARMS:
            continue
        a = acc[(gid, gname)][algo]
        a["rows"] += 1
        a["n"] = n or a["n"]
        if wt is not None:
            a["walls"].append(float(wt))
        if succ and acl is not None:
            a["succ"] = 1
            a["acls"].append(float(acl))
    dupes = sum(1 for g in acc.values() for a in g.values() if a["rows"] > 1)
    if dupes:
        print(f"warning: {dupes} (graph, algo) groups had >1 row; aggregated "
              f"(success=any, acl=mean of successful, wall=median)")
    out = {}
    for gkey, algos in acc.items():
        out[gkey] = {
            algo: {"succ": a["succ"],
                   "acl": (sum(a["acls"]) / len(a["acls"])) if a["acls"]
                   else None,
                   "wall": med(a["walls"]) if a["walls"] else None,
                   "n": a["n"]}
            for algo, a in algos.items()}
    return out


def analyze(per_graph, cats):
    """Detail buckets per (arm, category, band) + family stats per (arm, cat)."""
    detail = defaultdict(lambda: dict(n=0, both=0, only_mm=0, only_arm=0,
                                      neither=0, dacl=[], win=0, loss=0,
                                      tie=0, t_arm=[], t_mm=[]))
    fam = defaultdict(lambda: dict(n=0, both=0, succ_mm=0, succ_arm=0,
                                   dacl=[]))
    for (gid, _gname), algos in per_graph.items():
        if BASELINE not in algos:
            continue
        mm = algos[BASELINE]
        cat = cats.get(gid, "?")
        for arm in P3_ARMS:
            if arm not in algos:
                continue
            a = algos[arm]
            key = (arm, cat, band(a["n"] or mm["n"] or 0))
            d = detail[key]
            f = fam[(arm, cat)]
            d["n"] += 1
            f["n"] += 1
            f["succ_mm"] += mm["succ"]
            f["succ_arm"] += a["succ"]
            if a["wall"] is not None:
                d["t_arm"].append(a["wall"])
            if mm["wall"] is not None:
                d["t_mm"].append(mm["wall"])
            if a["succ"] and mm["succ"]:
                d["both"] += 1
                f["both"] += 1
                delta = a["acl"] - mm["acl"]
                d["dacl"].append(delta)
                f["dacl"].append(delta)
                if delta < -1e-6:
                    d["win"] += 1
                elif delta > 1e-6:
                    d["loss"] += 1
                else:
                    d["tie"] += 1
            elif mm["succ"]:
                d["only_mm"] += 1
            elif a["succ"]:
                d["only_arm"] += 1
            else:
                d["neither"] += 1
    return detail, fam


def print_detail(detail):
    band_order = [b[2] for b in BANDS]
    for arm in P3_ARMS:
        keys = sorted((k for k in detail if k[0] == arm),
                      key=lambda k: (k[1], band_order.index(k[2])
                                     if k[2] in band_order else 99))
        if not keys:
            print(f"\n== {arm} vs {BASELINE}: no paired graphs ==")
            continue
        print(f"\n== {arm} vs {BASELINE} "
              f"(dACL = arm - mm, raw avg_chain_length, both-succeed) ==")
        print(f"{'category':<22}{'size':<10}{'graphs':>7}{'both':>6}"
              f"{'onlyMM':>7}{'onlyARM':>8}{'fail':>6}{'meanD':>8}"
              f"{'medD':>8}{'win/loss/tie':>14}{'medT arm/mm':>14}")
        for key in keys:
            g = detail[key]
            _arm, cat, bd = key
            mn = (sum(g["dacl"]) / len(g["dacl"])) if g["dacl"] else float("nan")
            md = med(g["dacl"])
            print(f"{cat:<22}{bd:<10}{g['n']:>7}{g['both']:>6}"
                  f"{g['only_mm']:>7}{g['only_arm']:>8}{g['neither']:>6}"
                  f"{mn:>8.3f}{md:>8.3f}"
                  f"{'%d/%d/%d' % (g['win'], g['loss'], g['tie']):>14}"
                  f"{med(g['t_arm']):>7.1f}/{med(g['t_mm']):<6.1f}")


def verdicts(fam):
    """(arm, category) -> (verdict, reason, stats)."""
    out = {}
    for (arm, cat), f in sorted(fam.items()):
        mean_d = (sum(f["dacl"]) / len(f["dacl"])) if f["dacl"] else None
        rate_mm = 100.0 * f["succ_mm"] / f["n"] if f["n"] else 0.0
        rate_arm = 100.0 * f["succ_arm"] / f["n"] if f["n"] else 0.0
        drop = rate_mm - rate_arm
        reasons = []
        if mean_d is not None and mean_d > DACL_BAR + EPS:
            reasons.append(f"mean dACL {mean_d:+.3f} > +{DACL_BAR:.2f}")
        if drop > DROP_BAR_PT + EPS:
            reasons.append(f"success drop {drop:.1f} pt > {DROP_BAR_PT:g} pt")
        out[(arm, cat)] = ("FAIL" if reasons else "PASS",
                           "; ".join(reasons),
                           dict(n=f["n"], both=f["both"], mean_d=mean_d,
                                rate_mm=rate_mm, rate_arm=rate_arm,
                                drop=drop))
    return out


def print_verdicts(v):
    print(f"\n== M5 pre-registered bar, per family (category) x arm ==")
    print(f"   FAIL iff mean dACL > +{DACL_BAR:.2f} (both-succeed) or "
          f"success drop > {DROP_BAR_PT:g} pt (paired graphs, unpaired "
          f"success rates)")
    print(f"{'arm':<14}{'family':<22}{'n':>6}{'both':>6}{'meanD':>9}"
          f"{'succ arm%':>10}{'succ mm%':>9}{'drop pt':>9}  verdict")
    overall_fail = []
    for (arm, cat), (verdict, reason, s) in sorted(v.items()):
        m = f"{s['mean_d']:+.3f}" if s["mean_d"] is not None else "n/a"
        tag = " (small n)" if s["n"] < SMALL_N else ""
        line = (f"{arm:<14}{cat:<22}{s['n']:>6}{s['both']:>6}{m:>9}"
                f"{s['rate_arm']:>10.1f}{s['rate_mm']:>9.1f}"
                f"{s['drop']:>9.1f}  {verdict}{tag}")
        if reason:
            line += f"  [{reason}]"
        print(line)
        if verdict == "FAIL":
            overall_fail.append((arm, cat, reason))
    print()
    if overall_fail:
        print(f"M5 VERDICT: FAIL — {len(overall_fail)} family x arm bar(s) "
              f"broken:")
        for arm, cat, reason in overall_fail:
            print(f"  - {arm} on {cat}: {reason}")
    else:
        print("M5 VERDICT: PASS — no family shows mean dACL > "
              f"+{DACL_BAR:.2f} or success drop > {DROP_BAR_PT:g} pt for any "
              f"p3 arm")
    return overall_fail


def run_analysis(db, cats, label):
    print(f"M5 no-regression analysis — {label}")
    print("Label: (instance, trial) pairing [CLI] (rule 1). Column: RAW "
          "avg_chain_length for every arm — the CLI computes no spur column; "
          "raw-vs-raw (rule 3).")
    print("Walls: within-batch context only (rule 5; 56-worker batch).")
    per_graph = load_per_graph(db)
    if not per_graph:
        sys.exit("no usable rows in the runs table")
    detail, fam = analyze(per_graph, cats)
    print(f"\npaired universe: {len(per_graph)} (graph_id, graph_name) "
          f"groups with a {BASELINE} row: "
          f"{sum(1 for g in per_graph.values() if BASELINE in g)}")
    print_detail(detail)
    v = verdicts(fam)
    print_verdicts(v)
    return detail, fam, v


# ──────────────────────────────────────────────────────────────────────────────
# Selftest — 20-row in-memory fixture, engineered verdicts
# ──────────────────────────────────────────────────────────────────────────────

def selftest():
    db = sqlite3.connect(":memory:")
    db.execute("""CREATE TABLE runs (
        graph_id INTEGER, graph_name TEXT, algorithm TEXT, success INTEGER,
        avg_chain_length REAL, wall_time REAL, problem_nodes INTEGER)""")
    cats = {101: "complete", 102: "complete", 103: "complete",
            201: "grid", 202: "grid"}
    graphs = [(101, "gA1", 20), (102, "gA2", 25), (103, "gA3", 30),
              (201, "gB1", 150), (202, "gB2", 200)]
    acl = {
        # minorminer succeeds everywhere
        "minorminer": {101: 2.0, 102: 2.0, 103: 2.0, 201: 3.0, 202: 3.0},
        # p3-ate: PASS both families (mean dACL 0.000 / +0.025; no drops)
        "p3-ate": {101: 1.9, 102: 2.0, 103: 2.1, 201: 2.9, 202: 3.05},
        # p3-clmm: engineered dACL FAIL on 'complete' (mean +0.2167 > +0.10)
        "p3-clmm": {101: 2.3, 102: 2.2, 103: 2.15, 201: 2.95, 202: 3.0},
        # p3-mmpolish: engineered success-drop FAIL on 'grid' (fails gB1)
        "p3-mmpolish": {101: 1.95, 102: 1.95, 103: 1.95, 201: None,
                        202: 2.9},
    }
    n_rows = 0
    for algo, per in acl.items():
        for gid, gname, n in graphs:
            a = per[gid]
            succ = 0 if a is None else 1
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?)",
                       (gid, gname, algo, succ, a, 1.0 + 0.1 * gid % 7, n))
            n_rows += 1
    db.commit()
    assert n_rows == 20, n_rows

    _detail, fam, v = run_analysis(db, cats, "SELFTEST (20-row fixture)")

    expect = {("p3-ate", "complete"): "PASS", ("p3-ate", "grid"): "PASS",
              ("p3-clmm", "complete"): "FAIL", ("p3-clmm", "grid"): "PASS",
              ("p3-mmpolish", "complete"): "PASS",
              ("p3-mmpolish", "grid"): "FAIL"}
    for key, want in expect.items():
        got = v[key][0]
        assert got == want, f"{key}: expected {want}, got {got} ({v[key]})"
    # engineered numbers land where designed
    assert abs(v[("p3-clmm", "complete")][2]["mean_d"] - 0.21666) < 1e-3
    assert abs(v[("p3-mmpolish", "grid")][2]["drop"] - 50.0) < 1e-9
    assert fam[("p3-mmpolish", "grid")]["both"] == 1     # gB2 only
    print("\nSELFTEST OK — 20 rows, 6 family x arm verdicts as engineered "
          "(1 dACL FAIL, 1 success-drop FAIL, 4 PASS)")


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="M5 per-family no-regression analysis")
    ap.add_argument("path", nargs="?", help="batch dir or results.db")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--baseline-db", default=None,
                    help="second results.db whose rows (e.g. the archived "
                         "minorminer baseline) are unioned in — enables "
                         "cross-batch pairing (v1.2 T2; errata 4.12.10 regime)")
    ap.add_argument("--arms", default=None,
                    help="comma list of p3 arms to analyze (default: the "
                         "built-in P3_ARMS)")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.path:
        sys.exit("usage: m5_analyze.py <batch_dir | results.db> "
                 "[--baseline-db DB] [--arms a,b] | --selftest")
    if args.arms:
        global P3_ARMS, ARMS
        P3_ARMS = [a.strip() for a in args.arms.split(",") if a.strip()]
        ARMS = [BASELINE] + P3_ARMS
    path = args.path
    db_path = os.path.join(path, "results.db") if os.path.isdir(path) else path
    if not os.path.exists(db_path):
        sys.exit(f"results.db not found: {db_path}")
    db = sqlite3.connect(db_path)
    if args.baseline_db:
        base = args.baseline_db
        base = os.path.join(base, "results.db") if os.path.isdir(base) else base
        if not os.path.exists(base):
            sys.exit(f"baseline results.db not found: {base}")
        # Union the baseline rows into an in-memory copy so the whole analysis
        # sees one `runs` table (cross-batch pairing on graph_id).
        mem = sqlite3.connect(":memory:")
        db.backup(mem)
        mem.execute("ATTACH DATABASE ? AS base", (base,))
        cols = [r[1] for r in mem.execute("PRAGMA table_info(runs)")]
        collist = ", ".join(cols)
        # OR IGNORE: on key collision the analyzed batch's row wins and the
        # baseline's is dropped (baseline fills gaps, never overrides).
        mem.execute(f"INSERT OR IGNORE INTO runs ({collist}) "
                    f"SELECT {collist} FROM base.runs")
        mem.commit()
        db = mem
        db_path = f"{db_path} + baseline {base}"
    run_analysis(db, load_categories(), db_path)


if __name__ == "__main__":
    main()
