"""
docs/paper/data/run_sweep_instances.py
=======================================
Multi-instance sweep for statistical rigor (reviewer point: the headline variance
claim must not rest on ONE graph per cell). For every (family, size, density)
cell we draw K independent graph instances (distinct seeds) and run each through
all algorithms with several algorithm seeds, so the analysis can separate
graph-draw variance from algorithm-seed variance and report confidence intervals
and paired significance tests across instances.

Covers, in one run, the algorithms behind the paper's main, optimized, and
search-guidance tables:
  minorminer, minorminer-layout, reweave-base, reweave, reweave-thorough,
  reweave-stacked, mmfork-cuthill, mmfork-portfolio, reweave-mmfork-cuthill.

Writes raw_results_instances.csv (one row per cell x instance x target x algo x
seed, with an `instance` column) and summary_instances.csv (a quick per-(cell,
target,algo) mean). The rigorous aggregation (CIs + Wilcoxon) lives in analyze.py.

Usage:  python run_sweep_instances.py [n_workers] [timeout_s] [K_instances] [n_seeds]
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
FAULT_SEED = 7
ALGOS = ["minorminer", "minorminer-layout", "reweave-base", "reweave",
         "reweave-thorough", "reweave-stacked", "mmfork-cuthill",
         "mmfork-portfolio", "reweave-mmfork-cuthill"]
PEG_ONLY_PREFIXES = ("REG_", "BA_")


def build_targets() -> dict:
    import dwave_networkx as dnx
    from ember_qc.faults import simulate_faults
    p6 = dnx.pegasus_graph(6)
    return {
        "pegasus_6": p6,
        "pegasus_6_broken5": simulate_faults(p6, fault_rate=0.05, fault_seed=FAULT_SEED),
        "zephyr_4": dnx.zephyr_graph(4),
    }


def build_sources(K: int) -> list:
    """K instances per cell; returns [(cell, graph, instance_id, fam, n, d)]."""
    out = []

    def add(cell, fam, n, p, gen):
        for i in range(K):
            g = nx.convert_node_labels_to_integers(gen(seed=INSTANCE_SEED + i * 100003))
            out.append((cell, g, i, fam, n, p))

    for n in (20, 30, 40):
        for d in (0.3, 0.5, 0.7):
            add(f"ER_n{n}_d{d}", "ER", n, d,
                lambda seed, n=n, d=d: nx.gnp_random_graph(n, d, seed=seed))
    for n in (30, 40):
        for k in (4, 6):
            add(f"REG_n{n}_k{k}", "REG", n, k,
                lambda seed, k=k, n=n: nx.random_regular_graph(k, n, seed=seed))
        for m in (3, 5):
            add(f"BA_n{n}_m{m}", "BA", n, m,
                lambda seed, n=n, m=m: nx.barabasi_albert_graph(n, m, seed=seed))
    return out


_TARGETS: dict = {}
_TIMEOUT = 30.0


def _init(timeout: float) -> None:
    global _TARGETS, _TIMEOUT
    _TARGETS = build_targets()
    _TIMEOUT = timeout


def _run(task):
    from ember_qc.benchmark import benchmark_one
    cell, src_graph, inst, tgt_name, algo, seed = task
    r = benchmark_one(src_graph, _TARGETS[tgt_name], algo, timeout=_TIMEOUT, seed=seed,
                      graph_name=f"{cell}#{inst}", topology_name=tgt_name)
    return {
        "cell": cell, "instance": inst, "target": tgt_name, "algorithm": algo, "seed": seed,
        "success": int(bool(r.success)), "valid": int(bool(r.is_valid)),
        "avg_chain_length": r.avg_chain_length, "max_chain_length": r.max_chain_length,
        "total_qubits_used": r.total_qubits_used, "wall_time": r.wall_time,
        "problem_nodes": r.problem_nodes, "problem_edges": r.problem_edges,
    }


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 2)
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    K = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    seeds = list(range(int(sys.argv[4]) if len(sys.argv) > 4 else 3))

    sources = build_sources(K)
    target_names = ["pegasus_6", "pegasus_6_broken5", "zephyr_4"]
    tasks = []
    for (cell, g, inst, fam, n, d) in sources:
        tnames = ["pegasus_6"] if cell.startswith(PEG_ONLY_PREFIXES) else target_names
        for tname in tnames:
            for algo in ALGOS:
                for s in seeds:
                    tasks.append((cell, g, inst, tname, algo, s))

    print(f"instance sweep: K={K} instances, {len(ALGOS)} algos, {len(seeds)} seeds "
          f"= {len(tasks)} trials; workers={n_workers}, timeout={timeout}s", flush=True)

    t0 = time.perf_counter()
    rows = []
    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init, initargs=(timeout,)) as ex:
        for i, row in enumerate(ex.map(_run, tasks, chunksize=1)):
            rows.append(row)
            if (i + 1) % 500 == 0:
                print(f"  {i+1}/{len(tasks)}  ({time.perf_counter()-t0:.0f}s)", flush=True)
    print(f"all {len(tasks)} trials in {time.perf_counter()-t0:.0f}s", flush=True)

    raw = os.path.join(HERE, "raw_results_instances.csv")
    with open(raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # quick per-(cell,target,algo) mean over instances+seeds (rigorous stats in analyze.py)
    g: dict = {}
    for r in rows:
        g.setdefault((r["cell"], r["target"], r["algorithm"]), []).append(r)
    summ = []
    for (cell, tname, algo), rs in sorted(g.items()):
        ok = [r for r in rs if r["success"] and r["valid"]]
        acls = [r["avg_chain_length"] for r in ok]
        summ.append({"cell": cell, "target": tname, "algorithm": algo,
                     "n_trials": len(rs), "n_success": len(ok),
                     "acl_mean": round(st.mean(acls), 4) if acls else "",
                     "acl_std": round(st.pstdev(acls), 4) if len(acls) > 1 else 0.0,
                     "time_mean": round(st.mean([r["wall_time"] for r in rs]), 4)})
    with open(os.path.join(HERE, "summary_instances.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)
    print(f"wrote {raw}\nwrote summary_instances.csv\nTOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
