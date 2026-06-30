"""
docs/candidate-algorithms/data/mmfork_timing.py
===============================================
Wall-clock timing for the search-guidance algorithms vs the baselines, to answer
"are the new (stacked / unstacked) embedders faster or slower than minorminer and
minorminer-layout?". Matches the paper's timing methodology (mean seconds per
embedding, Table tab:timing): all algorithms run back-to-back on each (cell, seed)
so the time *ratios* are robust to CPU contention (every algo is slowed equally).

  minorminer          compiled-C++ baseline (=1.0x)
  minorminer-layout   layout-aware baseline
  mmfork              the fork with no var_order (== stock MM; control)
  mmfork-cuthill      a single fixed order (the order is computed once -> ~free)
  mmfork-portfolio    runs the 5 good orders + default -> expect ~6x
  reweave             MM base + LNS improver (~1.3x per the paper)
  reweave+mmfork      Reweave seeded from mmfork-portfolio (stacked)

Usage:  python mmfork_timing.py [--smoke] [timeout]
Writes  mmfork_timing.csv  and prints per-cell seconds + overall ratio vs MM.
"""
from __future__ import annotations

import csv
import os
import statistics as st
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

from ember_qc.benchmark import benchmark_one  # noqa: E402
from ember_qc.algorithms.reweave import embed_reweave  # noqa: E402
from ember_qc.algorithms.reweave_opt import _OptimizedRouter  # noqa: E402

# the standard grid (matches Table tab:mmfork) + the two stacking cells
GRID = [
    ("ER", 20, 0.5, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6"), ("ER", 40, 0.7, "pegasus_6"),
    ("ER", 60, 0.5, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6_broken5"),
    ("ER", 30, 0.5, "zephyr_4"),
]
SMOKE = [("ER", 20, 0.5, "pegasus_6"), ("ER", 40, 0.7, "pegasus_6")]
LAB = {"pegasus_6": "P6", "pegasus_6_broken5": "P6brk", "zephyr_4": "Z4"}
ALGOS = ["minorminer", "minorminer-layout", "mmfork", "mmfork-cuthill",
         "mmfork-portfolio", "reweave", "reweave+mmfork"]


def _time(algo, src, tgt, timeout, seed):
    if algo == "reweave+mmfork":
        r = embed_reweave(src, tgt, timeout=timeout, seed=seed,
                          router_cls=_OptimizedRouter, base_method="mmfork-portfolio")
        return r.get("time", float("nan")), bool(r.get("embedding"))
    r = benchmark_one(src, tgt, algo, timeout=timeout, seed=seed)
    return r.wall_time, bool(r.is_valid)


def main():
    smoke = "--smoke" in sys.argv
    rest = [a for a in sys.argv[1:] if a != "--smoke"]
    timeout = float(rest[0]) if rest else 30.0
    grid = SMOKE if smoke else GRID
    seeds = [0, 1] if smoke else [0, 1, 2]
    targets = make_targets()

    rows = []
    per = {a: [] for a in ALGOS}
    print(f"wall-clock seconds/embedding (timeout={timeout}s, {len(seeds)} seeds, back-to-back)\n")
    print(f"{'cell':16s} " + " ".join(f"{a.replace('minorminer','mm').replace('mmfork','mf'):>14s}" for a in ALGOS))
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p); tgt = targets[tname]
        cell = f"{fam}_n{n}_d{p}_{LAB[tname]}"
        cell_t = {a: [] for a in ALGOS}
        for s in seeds:
            for a in ALGOS:  # back-to-back -> robust ratios
                t, ok = _time(a, src, tgt, timeout, s)
                cell_t[a].append(t)
                per[a].append(t)
                rows.append({"cell": cell, "algo": a, "seed": s, "time": t, "valid": int(ok)})
        print(f"{cell:16s} " + " ".join(f"{st.mean(cell_t[a]):>14.2f}" for a in ALGOS))

    with open(os.path.join(HERE, "mmfork_timing.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cell", "algo", "seed", "time", "valid"])
        w.writeheader(); w.writerows(rows)

    base = st.mean(per["minorminer"])
    print("\n=== OVERALL (mean s, ratio vs minorminer) ===")
    print(f"{'algo':20s} {'mean s':>8s} {'xMM':>7s}")
    for a in ALGOS:
        m = st.mean(per[a])
        print(f"{a:20s} {m:>8.2f} {m/base:>6.2f}x")
    print("\nwrote mmfork_timing.csv")


if __name__ == "__main__":
    main()
