"""
docs/candidate-algorithms/data/leaderboard.py
=============================================
Rank a LIST of search-guidance variants against the fixed baselines
(minorminer / reweave / charme) on one grid, with seeds, in one run.  This is
the multi-variant generalization of eval_variant.py: where that compares ONE
variant to a baseline, this builds the leaderboard the sprint produces.

Variants are given as `module:algo` (module imported to register the algo) or
just `algo` (already registered).  Baselines are always included.  All algos run
back-to-back on each (cell, seed) so wall-clock ratios are robust to the CPU
contention of several agents running at once (every algo is slowed equally).

Usage:
    python leaderboard.py [--smoke] [--timeout S] [--seeds N] \
        rw_order_degeneracy:reweave-degen  rw_ripup_congest:reweave-congest ...

Writes  leaderboard_raw.csv / leaderboard_summary.csv  and prints:
  - a per-cell table, and
  - a GRID leaderboard sorted by mean ACL (lower = better), each variant's
    %delta vs minorminer and vs reweave, std, success rate, and time ratio.
"""
from __future__ import annotations

import csv
import importlib
import os
import statistics as st
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

BASELINES = ["minorminer", "reweave", "charme"]
GRID = [
    ("ER", 20, 0.5, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6"), ("ER", 40, 0.7, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6_broken5"),
    ("ER", 30, 0.5, "zephyr_4"),
]
# Denser cells where Reweave's LNS is demonstrably active (RW beats its MM base by
# 3-5%), so the rip-up-selection lever has room to change the converged optimum.
DENSE = [
    ("ER", 30, 0.7, "pegasus_6"), ("ER", 40, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6"), ("ER", 50, 0.5, "pegasus_6"),
    ("ER", 60, 0.4, "pegasus_6"), ("ER", 40, 0.7, "zephyr_4"),
]
SMOKE = [("ER", 20, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6")]
LAB = {"pegasus_6": "P6", "pegasus_6_broken5": "P6brk", "zephyr_4": "Z4"}


def _parse_args(argv):
    smoke = "--smoke" in argv
    dense = "--dense" in argv
    timeout, seeds = 60.0, 3
    variants, rest = [], [a for a in argv if a not in ("--smoke", "--dense")]
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--timeout":
            timeout = float(rest[i + 1]); i += 2; continue
        if a == "--seeds":
            seeds = int(rest[i + 1]); i += 2; continue
        variants.append(a); i += 1
    return smoke, dense, timeout, seeds, variants


def _register(variants):
    """Import each `module:algo` so the algo lands in the registry; return the
    bare algo names (in given order), deduped, baselines first."""
    names = []
    for spec in variants:
        if ":" in spec:
            module, algo = spec.split(":", 1)
            importlib.import_module(f"ember_qc.algorithms.{module}")
        else:
            algo = spec
        names.append(algo)
    from ember_qc.registry import ALGORITHM_REGISTRY
    # Drop baselines whose backend isn't installed on this machine (e.g. charme
    # needs the ATOM binary + torch) so they don't pollute the board with fails.
    avail_baselines = []
    for b in BASELINES:
        algo = ALGORITHM_REGISTRY.get(b)
        ok = True
        if algo is not None and hasattr(type(algo), "is_available"):
            ok = bool(type(algo).is_available()[0])
        if ok:
            avail_baselines.append(b)
        else:
            print(f"(skipping unavailable baseline: {b})")
    ordered = list(dict.fromkeys(avail_baselines + names))
    missing = [a for a in ordered if a not in ALGORITHM_REGISTRY]
    if missing:
        print(f"ERROR: not registered: {missing}\n"
              f"registered: {sorted(ALGORITHM_REGISTRY)}")
        sys.exit(2)
    return ordered


def main():
    smoke, dense, timeout, n_seeds, variants = _parse_args(sys.argv[1:])
    algos = _register(variants)
    from ember_qc.benchmark import benchmark_one
    grid = SMOKE if smoke else (DENSE if dense else GRID)
    seeds = list(range(min(n_seeds, 2) if smoke else n_seeds))

    raw = []
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p)
        cell = f"{fam}_n{n}_d{p}_{LAB[tname]}"
        tgt = make_targets()[tname]
        for s in seeds:
            for a in algos:  # adjacent runs -> robust time ratios
                r = benchmark_one(src, tgt, a, timeout=timeout, seed=s,
                                  graph_name=cell, topology_name=tname)
                raw.append({"cell": cell, "algorithm": a, "seed": s,
                            "success": int(bool(r.success)), "valid": int(bool(r.is_valid)),
                            "acl": r.avg_chain_length, "max_chain": r.max_chain_length,
                            "qubits": r.total_qubits_used, "time": r.wall_time})

    with open(os.path.join(HERE, "leaderboard_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(raw[0].keys())); w.writeheader(); w.writerows(raw)

    # aggregate per (cell, algo) then per algo across the grid
    by_cell = {}
    for r in raw:
        by_cell.setdefault((r["cell"], r["algorithm"]), []).append(r)
    cell_summ = {}
    for (cell, a), rs in by_cell.items():
        ok = [r for r in rs if r["success"] and r["valid"]]
        acl = [r["acl"] for r in ok]
        cell_summ[(cell, a)] = {
            "succ": len(ok), "n": len(rs),
            "acl": st.mean(acl) if acl else None,
            "std": st.pstdev(acl) if len(acl) > 1 else (0.0 if acl else None),
            "time": st.mean([r["time"] for r in rs]),
        }

    cells = list(dict.fromkeys(c for (c, a) in cell_summ))
    print(f"\ntimeout={timeout}s  seeds={seeds}  cells={len(cells)}\n")
    print(f"{'cell':16s} {'algo':26s} {'succ':>6s} {'ACL':>7s} {'std':>6s} {'t(s)':>7s}")
    for cell in cells:
        print("-" * 72)
        for a in algos:
            d = cell_summ[(cell, a)]
            acls = f"{d['acl']:.3f}" if d['acl'] is not None else "fail"
            stds = f"{d['std']:.3f}" if d['std'] is not None else "-"
            print(f"{cell:16s} {a:26s} {d['succ']}/{d['n']:<3d} {acls:>7s} {stds:>6s} {d['time']:>7.3f}")

    # grid-level leaderboard: per-cell %delta vs MM and vs reweave, averaged
    print("\n" + "=" * 72)
    print("GRID LEADERBOARD (sorted by mean ACL; lower is better)\n")
    agg = {}
    for a in algos:
        dacl_mm, dacl_rw, acls, stds, times, succ, ntot = [], [], [], [], [], 0, 0
        for cell in cells:
            d, mm, rw = cell_summ[(cell, a)], cell_summ[(cell, "minorminer")], cell_summ[(cell, "reweave")]
            succ += d["succ"]; ntot += d["n"]
            if d["acl"] is not None:
                acls.append(d["acl"]); stds.append(d["std"]); times.append(d["time"])
                if mm["acl"]:
                    dacl_mm.append(100 * (d["acl"] - mm["acl"]) / mm["acl"])
                if rw["acl"]:
                    dacl_rw.append(100 * (d["acl"] - rw["acl"]) / rw["acl"])
        agg[a] = {
            "acl": st.mean(acls) if acls else None,
            "std": st.mean(stds) if stds else None,
            "dmm": st.mean(dacl_mm) if dacl_mm else None,
            "drw": st.mean(dacl_rw) if dacl_rw else None,
            "time": st.mean(times) if times else None,
            "succ": succ, "n": ntot,
        }
    rank = sorted([a for a in algos if agg[a]["acl"] is not None], key=lambda a: agg[a]["acl"])
    print(f"{'rank':>4s} {'algo':26s} {'ACL':>7s} {'std':>6s} {'vsMM%':>7s} {'vsRW%':>7s} {'succ':>7s} {'t(s)':>7s}")
    for i, a in enumerate(rank, 1):
        d = agg[a]
        print(f"{i:>4d} {a:26s} {d['acl']:>7.3f} {d['std']:>6.3f} "
              f"{d['dmm']:>+7.1f} {d['drw']:>+7.1f} {d['succ']}/{d['n']:<3d} {d['time']:>7.3f}")

    with open(os.path.join(HERE, "leaderboard_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "acl_mean", "acl_std", "delta_vs_mm_pct", "delta_vs_rw_pct",
                    "n_success", "n_total", "time_mean"])
        for a in algos:
            d = agg[a]
            w.writerow([a, d["acl"], d["std"], d["dmm"], d["drw"], d["succ"], d["n"], d["time"]])
    print("\nwrote leaderboard_raw.csv / leaderboard_summary.csv")


if __name__ == "__main__":
    main()
