"""
docs/candidate-algorithms/data/eval_candidate.py
================================================
Evaluate a candidate embedding algorithm the SAME way Reweave was evaluated:
Ember's benchmark_one harness, the same source families / D-Wave targets, paired
against minorminer. Runs sequentially (no process pool) so it is robust to the
heavy third-party libs (torch / ortools / POT) and to several agents running at
once; embedding-quality numbers are deterministic per seed, wall-clock is
indicative under parallel load.

Usage:
    python eval_candidate.py <module> <algo_name> [timeout_s] [--smoke]

      <module>     dotted suffix under ember_qc.algorithms (e.g. "srgw")
      <algo_name>  the @register_algorithm name (e.g. "srgw")
      timeout_s    per-trial timeout (default 60)
      --smoke      tiny 2-cell x 2-seed grid for quick development checks

Writes  <algo_name>_raw.csv  and  <algo_name>_summary.csv  in this directory and
prints a per-cell comparison vs minorminer.
"""
from __future__ import annotations

import csv
import importlib
import os
import statistics as st
import sys
import warnings

warnings.filterwarnings("ignore")

import networkx as nx          # noqa: E402
import dwave_networkx as dnx   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_SEED = 12345
FAULT_SEED = 7
SEEDS = [0, 1, 2]

# (family, n, density-or-param, target_name) — same families/targets as the
# Reweave sweep, reduced so the expensive candidates stay tractable.
FULL_GRID = [
    ("ER", 20, 0.3, "pegasus_6"), ("ER", 20, 0.5, "pegasus_6"), ("ER", 20, 0.7, "pegasus_6"),
    ("ER", 30, 0.3, "pegasus_6"), ("ER", 30, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6_broken5"),
    ("ER", 30, 0.5, "zephyr_4"),
]
SMOKE_GRID = [("ER", 20, 0.5, "pegasus_6"), ("ER", 30, 0.5, "pegasus_6")]


def make_targets():
    from ember_qc.faults import simulate_faults
    p6 = dnx.pegasus_graph(6)
    return {
        "pegasus_6": p6,
        "pegasus_6_broken5": simulate_faults(p6, fault_rate=0.05, fault_seed=FAULT_SEED),
        "zephyr_4": dnx.zephyr_graph(4),
    }


def make_source(fam, n, p):
    if fam == "ER":
        g = nx.gnp_random_graph(n, p, seed=INSTANCE_SEED)
    elif fam == "REG":
        g = nx.random_regular_graph(int(p), n, seed=INSTANCE_SEED)
    elif fam == "BA":
        g = nx.barabasi_albert_graph(n, int(p), seed=INSTANCE_SEED)
    else:
        raise ValueError(fam)
    return nx.convert_node_labels_to_integers(g)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    module, algo = sys.argv[1], sys.argv[2]
    timeout = 60.0
    smoke = "--smoke" in sys.argv
    for a in sys.argv[3:]:
        if a != "--smoke":
            timeout = float(a)

    # Import the candidate module so its @register_algorithm runs.
    importlib.import_module(f"ember_qc.algorithms.{module}")
    from ember_qc.registry import ALGORITHM_REGISTRY
    from ember_qc.benchmark import benchmark_one
    if algo not in ALGORITHM_REGISTRY:
        print(f"ERROR: '{algo}' not registered after importing "
              f"ember_qc.algorithms.{module}. Registered: {sorted(ALGORITHM_REGISTRY)}")
        sys.exit(2)

    grid = SMOKE_GRID if smoke else FULL_GRID
    targets = make_targets()
    algos = ["minorminer", algo]
    label = {"pegasus_6": "P6", "pegasus_6_broken5": "P6-broken", "zephyr_4": "Z4"}

    raw = []
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p)
        cell = f"{fam}_n{n}_d{p}_{label[tname]}"
        for a in algos:
            for s in SEEDS:
                r = benchmark_one(src, targets[tname], a, timeout=timeout, seed=s,
                                  graph_name=cell, topology_name=tname)
                raw.append({"cell": cell, "target": tname, "algorithm": a, "seed": s,
                            "success": int(bool(r.success)), "valid": int(bool(r.is_valid)),
                            "acl": r.avg_chain_length, "maxchain": r.max_chain_length,
                            "qubits": r.total_qubits_used, "time": r.wall_time,
                            "status": r.status})

    with open(os.path.join(HERE, f"{algo}_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(raw[0].keys())); w.writeheader(); w.writerows(raw)

    # aggregate
    groups = {}
    for r in raw:
        groups.setdefault((r["cell"], r["algorithm"]), []).append(r)
    summ = []
    for (cell, a), rs in groups.items():
        ok = [r for r in rs if r["success"] and r["valid"]]
        acl = [r["acl"] for r in ok]
        summ.append({"cell": cell, "algorithm": a, "n_seeds": len(rs), "n_success": len(ok),
                     "success_rate": round(len(ok) / len(rs), 3),
                     "acl_mean": round(st.mean(acl), 3) if acl else "",
                     "acl_std": round(st.pstdev(acl), 3) if len(acl) > 1 else (0.0 if acl else ""),
                     "qubits_mean": round(st.mean([r["qubits"] for r in ok]), 1) if ok else "",
                     "time_mean": round(st.mean([r["time"] for r in rs]), 3)})
    with open(os.path.join(HERE, f"{algo}_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)

    # print paired comparison
    print(f"\n{'cell':22s} {'algo':16s} {'succ':>5s} {'ACL':>7s} {'std':>6s} {'qubits':>7s} {'t(s)':>7s}")
    print("-" * 74)
    by = {(r["cell"], r["algorithm"]): r for r in summ}
    cells = [c for c in dict.fromkeys(r["cell"] for r in summ)]
    for cell in cells:
        for a in algos:
            r = by[(cell, a)]
            print(f"{cell:22s} {a:16s} {r['n_success']}/{r['n_seeds']:<3d} "
                  f"{str(r['acl_mean']):>7s} {str(r['acl_std']):>6s} "
                  f"{str(r['qubits_mean']):>7s} {r['time_mean']:>7.2f}")
        mm, ca = by[(cell, "minorminer")], by[(cell, algo)]
        if mm["acl_mean"] != "" and ca["acl_mean"] != "":
            d = 100 * (ca["acl_mean"] - mm["acl_mean"]) / mm["acl_mean"]
            print(f"{'  -> ACL delta vs mm':22s} {d:+.1f}%")
        print()


if __name__ == "__main__":
    main()
