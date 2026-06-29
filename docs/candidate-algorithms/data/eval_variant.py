"""
docs/candidate-algorithms/data/eval_variant.py
==============================================
Measure ONE PathFinder optimization variant against the FROZEN baseline
`pathfinder` (and `minorminer`), the same way candidates were measured.

The key metrics are the variant-vs-baseline deltas:
  - quality variants: ACL % change and ACL-std change (lower = better),
  - speed variants:   a TIME RATIO (variant/baseline). Baseline and variant are
    run back-to-back on the same (cell, seed), so the ratio is robust to the CPU
    contention of several agents running at once (both are slowed equally).

Usage:
    python eval_variant.py <module> <variant_name> [baseline_algo] [timeout] [--smoke]
      <module>        dotted suffix under ember_qc.algorithms (e.g. "pf_spur")
      <variant_name>  the @register_algorithm name (e.g. "pathfinder-spur")
      baseline_algo   algo to delta against (default "pathfinder"; use
                      "pathfinder-thorough" for the parallel-restarts variant)
Writes <variant_name>_variant_{raw,summary}.csv and prints the comparison.
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

SEEDS = [0, 1, 2]
# spans sizes/densities/targets; the n40 d0.7 cell is where pure-Python routing
# dominates, giving the clearest speed signal.
GRID = [
    ("ER", 20, 0.5, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6"), ("ER", 40, 0.7, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6_broken5"),
    ("ER", 30, 0.5, "zephyr_4"),
]
SMOKE = [("ER", 20, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6")]


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    module, variant = sys.argv[1], sys.argv[2]
    baseline = "pathfinder"
    timeout = 60.0
    smoke = "--smoke" in sys.argv
    rest = [a for a in sys.argv[3:] if a != "--smoke"]
    if rest and not rest[0].replace(".", "").isdigit():
        baseline = rest.pop(0)
    if rest:
        timeout = float(rest[0])

    importlib.import_module(f"ember_qc.algorithms.{module}")
    from ember_qc.registry import ALGORITHM_REGISTRY
    from ember_qc.benchmark import benchmark_one
    if variant not in ALGORITHM_REGISTRY:
        print(f"ERROR: '{variant}' not registered after importing {module}. "
              f"Registered: {sorted(ALGORITHM_REGISTRY)}"); sys.exit(2)

    grid = SMOKE if smoke else GRID
    targets = make_targets()
    algos = list(dict.fromkeys(["minorminer", baseline, variant]))
    lab = {"pegasus_6": "P6", "pegasus_6_broken5": "P6brk", "zephyr_4": "Z4"}

    raw = []
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p)
        cell = f"{fam}_n{n}_d{p}_{lab[tname]}"
        for s in SEEDS:
            # run all algos on this (cell, seed) adjacently -> robust time ratios
            for a in algos:
                r = benchmark_one(src, targets[tname], a, timeout=timeout, seed=s,
                                  graph_name=cell, topology_name=tname)
                raw.append({"cell": cell, "algorithm": a, "seed": s,
                            "success": int(bool(r.success)), "valid": int(bool(r.is_valid)),
                            "acl": r.avg_chain_length, "qubits": r.total_qubits_used,
                            "time": r.wall_time})

    with open(os.path.join(HERE, f"{variant}_variant_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(raw[0].keys())); w.writeheader(); w.writerows(raw)

    # aggregate per (cell, algo)
    g = {}
    for r in raw:
        g.setdefault((r["cell"], r["algorithm"]), []).append(r)
    summ = {}
    for (cell, a), rs in g.items():
        ok = [r for r in rs if r["success"] and r["valid"]]
        acl = [r["acl"] for r in ok]
        summ[(cell, a)] = {"succ": len(ok), "n": len(rs),
                           "acl": st.mean(acl) if acl else None,
                           "std": st.pstdev(acl) if len(acl) > 1 else (0.0 if acl else None),
                           "time": st.mean([r["time"] for r in rs])}
    with open(os.path.join(HERE, f"{variant}_variant_summary.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cell", "algorithm", "n_success", "acl_mean", "acl_std", "time_mean"])
        for (cell, a), d in summ.items():
            w.writerow([cell, a, d["succ"], d["acl"], d["std"], round(d["time"], 4)])

    # report
    cells = list(dict.fromkeys(c for (c, a) in summ))
    print(f"\nbaseline = {baseline}   variant = {variant}\n")
    print(f"{'cell':18s} {'algo':22s} {'succ':>5s} {'ACL':>7s} {'std':>6s} {'t(s)':>7s}")
    print("-" * 70)
    dacl_v_b = []; dstd_v_b = []; tratio = []; dacl_v_mm = []
    for cell in cells:
        for a in algos:
            d = summ[(cell, a)]
            acls = f"{d['acl']:.3f}" if d['acl'] is not None else "fail"
            stds = f"{d['std']:.3f}" if d['std'] is not None else "-"
            print(f"{cell:18s} {a:22s} {d['succ']}/{d['n']:<3d} {acls:>7s} {stds:>6s} {d['time']:>7.3f}")
        b, v, mm = summ[(cell, baseline)], summ[(cell, variant)], summ[(cell, "minorminer")]
        if b["acl"] and v["acl"]:
            da = 100 * (v["acl"] - b["acl"]) / b["acl"]; dacl_v_b.append(da)
            ds = (v["std"] - b["std"]); dstd_v_b.append(ds)
            tr = v["time"] / b["time"] if b["time"] > 0 else float("nan"); tratio.append(tr)
            print(f"  -> variant vs {baseline}: ACL {da:+.1f}%  std {ds:+.3f}  time x{tr:.2f}")
        if mm["acl"] and v["acl"]:
            dacl_v_mm.append(100 * (v["acl"] - mm["acl"]) / mm["acl"])
        print()
    print("=" * 70)
    if dacl_v_b:
        print(f"GRID MEAN  variant vs {baseline}:  ACL {st.mean(dacl_v_b):+.1f}%  "
              f"std {st.mean(dstd_v_b):+.3f}  time x{st.mean(tratio):.2f}")
    if dacl_v_mm:
        print(f"GRID MEAN  variant vs minorminer: ACL {st.mean(dacl_v_mm):+.1f}%")


if __name__ == "__main__":
    main()
