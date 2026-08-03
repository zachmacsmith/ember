"""§4.15 T1 verdict analyzer — prints the pre-registered bar table (P4 gate).

Reads the T1 outputs (rsync'd back from hyde06, or run in place on the run
host) and prints one PASS/FAIL line per §4.15 bar, with the numbers beside
each verdict. Sections are independent — missing inputs are reported and
skipped, so this can run incrementally as sub-batches land.

  T1a  docs/paper3/data/dev_suite.csv            (dev_suite.py --topo Z12)
  T1b  results/t1b_native/batch/results.db       (ember run t1b_native.yaml)
  T1c  docs/paper3/data/p6_probes_confirm_beta_z12.csv + t1c_arms_z12.csv
  T1d  docs/paper3/data/t1d_race9.csv            (t1d_race9.py; its own
       summary prints verdicts too — this reprints the §4.15 read)

--attribute additionally runs the deterministic native-tier attribution for
T1b (loads graphs 37600-37641 via the Ember library and calls try_native
locally — run where the library cache is warm, e.g. the run host).

Usage: .venv/bin/python docs/paper3/data/t1_verdicts.py [--attribute]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import statistics
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

DEV_CSV = os.path.join(HERE, "dev_suite.csv")
T1B_DB = os.path.join(ROOT, "results", "t1b_native", "batch", "results.db")
P6_CSV = os.path.join(HERE, "p6_probes_confirm_beta_z12.csv")
ARMS_CSV = os.path.join(HERE, "t1c_arms_z12.csv")
T1D_CSV = os.path.join(HERE, "t1d_race9.csv")

HW_IDS = list(range(37600, 37629)) + list(range(37630, 37642))


def _fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


# ── T1a ─────────────────────────────────────────────────────────────────────

def t1a():
    if not os.path.exists(DEV_CSV):
        print("T1a: dev_suite.csv missing — skipped\n")
        return
    with open(DEV_CSV, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["topo"] == "Z12"]
    print("=" * 78)
    print("T1a — p3-ember dev-cell bars (§4.15 i-iv)")
    print("=" * 78)

    def cell_rows(n, p, arm):
        return [r for r in rows if int(r["n"]) == n and float(r["p"]) == p
                and r["arm"] == arm]

    def paired(n, p, a, b):
        """(a - b) dACL_spur on both-succeed pairs, keyed (inst, seed);
        p3-template pairs per-instance (deterministic, seed -1)."""
        av = {(r["inst_seed"], r["algo_seed"]): _fnum(r["acl_spur"])
              for r in cell_rows(n, p, a) if r["success"] == "1"}
        bv = {(r["inst_seed"], r["algo_seed"]): _fnum(r["acl_spur"])
              for r in cell_rows(n, p, b) if r["success"] == "1"}
        ds, base = [], []
        for k, x in av.items():
            y = bv.get(k)
            if y is None and b == "p3-template":
                y = bv.get((k[0], "-1"))
            if x is not None and y is not None:
                ds.append(x - y)
                base.append(y)
        return ds, (statistics.median(base) if base else None)

    def med_pct(ds, base):
        if not ds or not base:
            return None, None, None
        med = statistics.median(ds)
        return med, 100.0 * med / base, 100.0 * sum(d < 0 for d in ds) / len(ds)

    cells = [(100, 0.2), (100, 0.3), (140, 0.12), (140, 0.2), (140, 1.0),
             (179, 1.0), (160, 0.05)]
    worst_vs_ate = None
    for n, p in cells:
        dm, base_m = paired(n, p, "p3-ember", "minorminer")
        da, base_a = paired(n, p, "p3-ember", "p3-ate")
        m_med, m_pct, m_w = med_pct(dm, base_m)
        a_med, a_pct, _ = med_pct(da, base_a)
        if a_pct is not None:
            worst_vs_ate = a_pct if worst_vs_ate is None else max(worst_vs_ate,
                                                                  a_pct)
        print(f"({n},{p}): vsMM med {m_med if m_med is None else round(m_med, 3)}"
              f" ({'-' if m_pct is None else round(m_pct, 2)}%) "
              f"W {'-' if m_w is None else round(m_w)}%  n={len(dm)} | "
              f"vsATE med {'-' if a_med is None else round(a_med, 3)} "
              f"({'-' if a_pct is None else round(a_pct, 2)}%) n={len(da)}")

    # (i) never worse than ate beyond +0.25% median on ANY cell
    print(f"bar(i) ember never > +0.25% median worse than ate: worst "
          f"{'-' if worst_vs_ate is None else round(worst_vs_ate, 3)}% -> "
          f"{verdict(worst_vs_ate is not None and worst_vs_ate <= 0.25)}")

    # (ii) sparse wins
    for n, p in ((160, 0.05), (100, 0.2)):
        ds, base = paired(n, p, "p3-ember", "minorminer")
        med, pct, w = med_pct(ds, base)
        ok = pct is not None and pct < -0.5 and w is not None and w >= 55
        print(f"bar(ii) ({n},{p}) median < -0.5% AND >=55%W: "
              f"{'-' if pct is None else round(pct, 2)}% / "
              f"{'-' if w is None else round(w)}%W -> {verdict(ok)}")

    # (iii) construct_s tax on (160,0.05) — §4.15 amendment 2
    def walls(n, p, arm, construct=False):
        out = []
        for r in cell_rows(n, p, arm):
            if r["success"] != "1":
                continue
            if construct:
                try:
                    meta = json.loads(r.get("arm_meta") or "{}")
                    v = meta.get("construct_s")
                except Exception:
                    v = None
            else:
                v = _fnum(r.get("wall") or r.get("time"))
            if v is not None:
                out.append(float(v))
        return out
    c = walls(160, 0.05, "p3-ember", construct=True)
    m = walls(160, 0.05, "minorminer")
    if c and m:
        tax = statistics.median(c) - statistics.median(m)
        print(f"bar(iii) (160,0.05) median construct_s - MM wall = "
              f"{tax:+.2f}s (<= +0.2s) -> {verdict(tax <= 0.2)}")
    else:
        print("bar(iii): construct_s or MM walls missing -> CHECK arm_meta")

    # (iv) K179 5/5
    ok179 = [r for r in cell_rows(179, 1.0, "p3-ember") if r["success"] == "1"]
    tot179 = cell_rows(179, 1.0, "p3-ember")
    print(f"bar(iv) K179 success {len(ok179)}/{len(tot179)} -> "
          f"{verdict(len(tot179) > 0 and len(ok179) == len(tot179))}")
    print()


# ── T1b ─────────────────────────────────────────────────────────────────────

def t1b(attribute: bool):
    if not os.path.exists(T1B_DB):
        print("T1b: results/t1b_native/batch/results.db missing — skipped\n")
        return
    con = sqlite3.connect(T1B_DB)
    cur = con.execute(
        "SELECT graph_id, graph_name, algorithm, trial, success, "
        "avg_chain_length, wall_time FROM runs")
    per = defaultdict(dict)
    for gid, gname, algo, trial, succ, acl, wall in cur:
        per[(gid, gname)].setdefault(algo, []).append((succ, acl, wall))
    con.close()
    print("=" * 78)
    print("T1b — native fast path on hardware_native (§4.15 v)")
    print("=" * 78)
    succ = defaultdict(int)
    tot = defaultdict(int)
    acl1 = defaultdict(int)
    deficits = []
    for key, algos in sorted(per.items()):
        for algo, runs in algos.items():
            for s, a, w in runs:
                tot[algo] += 1
                succ[algo] += int(bool(s))
                if s and a is not None and abs(a - 1.0) < 1e-9:
                    acl1[algo] += 1
        mm = sum(int(bool(s)) for s, _, _ in algos.get("minorminer", []))
        em = sum(int(bool(s)) for s, _, _ in algos.get("p3-ember", []))
        if em < mm:
            deficits.append((key[1], mm, em))
    for algo in sorted(tot):
        print(f"{algo:12s} success {succ[algo]:3d}/{tot[algo]:3d}   "
              f"ACL==1.0 rows: {acl1[algo]:3d}")
    drop_pt = (100.0 * (succ["minorminer"] - succ["p3-ember"])
               / max(1, tot["minorminer"]))
    ok = (succ["p3-ember"] >= succ["minorminer"]
          or (drop_pt <= 2.6 and len(deficits) < 3))
    print(f"bar(v) family success >= MM (deficits real only at >=3 graphs "
          f"AND > 2.6pt): ember {succ['p3-ember']} vs MM {succ['minorminer']} "
          f"({len(deficits)} deficit graphs, {drop_pt:+.1f}pt) -> {verdict(ok)}")
    if deficits:
        for g, mm, em in deficits[:10]:
            print(f"  deficit: {g}  MM {mm}/5 vs ember {em}/5")
    if attribute:
        print("native-tier attribution (deterministic, local):")
        from ember_qc.load_graphs import load_graph
        import dwave_networkx as dnx
        from ember_qc.algorithms.paper3.native import try_native
        tgt = dnx.zephyr_graph(12)
        counts = defaultdict(int)
        for gid in HW_IDS:
            try:
                g = load_graph(gid)
            except Exception as e:
                print(f"  {gid}: load failed ({type(e).__name__})")
                continue
            meta = {}
            emb = try_native(g, tgt, time.perf_counter() + 60.0, meta=meta)
            counts[meta.get("native", "miss")] += 1
            if emb is not None:
                bad = any(len(c) != 1 for c in emb.values())
                if bad:
                    print(f"  {gid}: HIT WITH CHAIN != 1 — BAR VIOLATION")
        print(f"  tiers: {dict(counts)}")
    print()


# ── T1c ─────────────────────────────────────────────────────────────────────

def t1c():
    if not os.path.exists(P6_CSV):
        print("T1c: p6_probes_confirm_beta_z12.csv missing — skipped\n")
        return
    with open(P6_CSV, newline="") as fh:
        rows = list(csv.DictReader(fh))
    print("=" * 78)
    print("T1c — beta family on the Z12 deg-10 ladder (§4.15)")
    print("=" * 78)
    by = defaultdict(dict)
    for r in rows:
        key = (r["n"], r["inst_seed"], r["algo_seed"])
        by[key][r["arm"]] = r
    arms = sorted({r["arm"] for r in rows} - {"stock"})
    confirms = {}
    for arm in arms:
        cells_pass = 0
        for n in ("100", "140", "180"):
            ds, sw, aw = [], 0, 0
            s_ok = a_ok = tot = 0
            for key, d in by.items():
                if key[0] != n or arm not in d or "stock" not in d:
                    continue
                a, s = d[arm], d["stock"]
                tot += 1
                s_ok += int(s["success"] == "1")
                a_ok += int(a["success"] == "1")
                if (a["success"] == "1" and s["success"] == "1"
                        and a["acl_spur"] and s["acl_spur"]):
                    ds.append(float(a["acl_spur"]) - float(s["acl_spur"]))
            if ds:
                base = statistics.median(
                    float(d["stock"]["acl_spur"]) for d in by.values()
                    if d.get("stock", {}).get("success") == "1"
                    and d["stock"]["n"] == n and d["stock"]["acl_spur"])
                med = statistics.median(ds)
                pct = 100.0 * med / base
                w = 100.0 * sum(x < 0 for x in ds) / len(ds)
                cell_ok = pct < -1.0 and w >= 60
                cells_pass += cell_ok
                print(f"{arm:10s} n={n}: med {med:+.3f} ({pct:+.2f}%) "
                      f"W {w:.0f}% pairs {len(ds)} | success {a_ok}/{tot} "
                      f"(stock {s_ok}/{tot}) {'CELL-OK' if cell_ok else ''}")
        confirms[arm] = cells_pass
        print(f"{arm}: cells passing median<-1% & >=60%W: {cells_pass}/3 -> "
              f"{'CONFIRM' if cells_pass >= 2 else 'NOT CONFIRMED'} (§4.8b rule)")
    if "ramp2" in confirms and "ramp2h" in confirms:
        r2 = [(r["n"], r["inst_seed"], r["algo_seed"], r["acl"], r["success"])
              for r in rows if r["arm"] == "ramp2"]
        r2h = [(r["n"], r["inst_seed"], r["algo_seed"], r["acl"], r["success"])
               for r in rows if r["arm"] == "ramp2h"]
        tie = sorted(r2) == sorted(r2h)
        print(f"ramp2h == ramp2 exact tie (amendment 3 expected): "
              f"{verdict(tie)} {'(instrumentation confirmed)' if tie else ''}")
    print("(t1c_arms summary is printed by t1c_arms.py; -fb bar lives there)")
    print()


# ── T1d ─────────────────────────────────────────────────────────────────────

def t1d():
    if not os.path.exists(T1D_CSV):
        print("T1d: t1d_race9.csv missing — skipped (runner prints verdicts)\n")
        return
    print("T1d: see t1d_race9 summary (its runner prints the §4.15 bars).\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attribute", action="store_true")
    args = ap.parse_args()
    t1a()
    t1b(args.attribute)
    t1c()
    t1d()


if __name__ == "__main__":
    main()
