"""
docs/paper/data/ablation_probe.py
=================================
Answer the question posed in the paper's novelty section: of the two ideas
Reweave imports -- the SPH Steiner inner step and congestion pricing -- which
carries the improver's gain over minorminer?

2x2 factorial on the warm-started improver, everything else byte-identical:
  reweave               : SPH sharing ON,  congestion pricing ON  (production)
  reweave-ablate-paths  : SPH OFF (attach to root only, MM's inner step)
  reweave-ablate-nocong : pricing OFF (uniform shortcut cost, lns_penalty=0)
  reweave-ablate-both   : both OFF
plus minorminer (the shared base) for reference. Same seed => same MM base, so
differences isolate the improver ingredient.

Grid: the six LNS-active dense ER cells (n in {20,30,40} x d in {0.5,0.7}),
clean Pegasus P6, K=5 instances x 3 seeds. Writes ablation_probe.csv.

Usage:  python ablation_probe.py [n_workers]
"""
from __future__ import annotations

import csv
import os
import statistics as st
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
import networkx as nx  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INSTANCE_SEED = 12345
ALGOS = ["minorminer", "reweave", "reweave-ablate-paths",
         "reweave-ablate-nocong", "reweave-ablate-both"]
K = 5
SEEDS = [0, 1, 2]
TIMEOUT = 20.0

_TARGET = None


def _init():
    global _TARGET
    import dwave_networkx as dnx
    _TARGET = dnx.pegasus_graph(6)


def _run(task):
    from ember_qc.benchmark import benchmark_one
    cell, g, inst, algo, seed = task
    r = benchmark_one(g, _TARGET, algo, timeout=TIMEOUT, seed=seed,
                      graph_name=f"{cell}#{inst}", topology_name="pegasus_6")
    return {"cell": cell, "instance": inst, "algorithm": algo, "seed": seed,
            "success": int(bool(r.success)), "valid": int(bool(r.is_valid)),
            "avg_chain_length": r.avg_chain_length,
            "total_qubits_used": r.total_qubits_used, "wall_time": r.wall_time}


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 2)
    tasks = []
    for n in (20, 30, 40):
        for d in (0.5, 0.7):
            for i in range(K):
                g = nx.convert_node_labels_to_integers(
                    nx.gnp_random_graph(n, d, seed=INSTANCE_SEED + i * 100003))
                for algo in ALGOS:
                    for s in SEEDS:
                        tasks.append((f"ER_n{n}_d{d}", g, i, algo, s))
    print(f"ablation probe: {len(tasks)} trials, workers={n_workers}", flush=True)
    t0 = time.perf_counter()
    rows = []
    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init) as ex:
        for i, row in enumerate(ex.map(_run, tasks, chunksize=1)):
            rows.append(row)
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(tasks)} ({time.perf_counter()-t0:.0f}s)", flush=True)
    with open(os.path.join(HERE, "ablation_probe.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # paired per-(cell, instance) means vs minorminer
    pim: dict = {}
    for r in rows:
        if r["success"] and r["valid"]:
            pim.setdefault((r["cell"], r["instance"], r["algorithm"]), []).append(r["avg_chain_length"])
    print("\n%ACL vs minorminer (paired per cell x instance):")
    for algo in ALGOS[1:]:
        diffs = []
        for n in (20, 30, 40):
            for d in (0.5, 0.7):
                for i in range(K):
                    a = pim.get((f"ER_n{n}_d{d}", i, algo))
                    m = pim.get((f"ER_n{n}_d{d}", i, "minorminer"))
                    if a and m:
                        diffs.append((st.mean(a) - st.mean(m)) / st.mean(m) * 100)
        print(f"  {algo:24s}: {st.mean(diffs):+.2f}%  (n={len(diffs)})")
    print(f"TOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
