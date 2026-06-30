"""
docs/paper/data/run_sweep_opt.py
================================
Optimized-Reweave counterpart of run_sweep.py for the paper's "Optimizations"
section. Identical grid / instances / seeds as run_sweep.py (so results are
directly comparable), but measures the OPTIMIZED Reweave family alongside the
baselines and the preliminary engine:

  minorminer, minorminer-layout,
  reweave-base       (the preliminary engine — same code path as the original
                         `reweave` in run_sweep.py; included for a same-run
                         preliminary-vs-optimized comparison),
  reweave            (optimized: bounded routing + dirty-set + spur),
  reweave-thorough   (optimized best-of-4),
  reweave-stacked    (optimized + multilevel placement).

Writes raw_results_opt.csv and summary_opt.csv (the preliminary summary.csv is
left untouched). Quality numbers (ACL, std, qubits) are deterministic per seed;
wall-clock is machine-dependent.

Usage:  .venv/bin/python docs/paper/data/run_sweep_opt.py [n_workers] [timeout]
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
ALGOS = ["minorminer", "minorminer-layout", "reweave-base",
         "reweave", "reweave-thorough", "reweave-stacked"]
SEEDS = list(range(5))


def build_targets() -> dict:
    import dwave_networkx as dnx
    from ember_qc.faults import simulate_faults
    p6 = dnx.pegasus_graph(6)
    z4 = dnx.zephyr_graph(4)
    return {
        "pegasus_6": p6,
        "pegasus_6_broken5": simulate_faults(p6, fault_rate=0.05, fault_seed=FAULT_SEED),
        "zephyr_4": z4,
    }


def build_sources() -> dict:
    src = {}
    for n in (20, 30, 40):
        for d in (0.3, 0.5, 0.7):
            g = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, d, seed=INSTANCE_SEED))
            src[f"ER_n{n}_d{d}"] = (g, "ER", n, d)
    for n in (30, 40):
        for k in (4, 6):
            g = nx.convert_node_labels_to_integers(nx.random_regular_graph(k, n, seed=INSTANCE_SEED))
            src[f"REG_n{n}_k{k}"] = (g, "REG", n, k)
        for m in (3, 5):
            g = nx.convert_node_labels_to_integers(nx.barabasi_albert_graph(n, m, seed=INSTANCE_SEED))
            src[f"BA_n{n}_m{m}"] = (g, "BA", n, m)
    return src


PEG_ONLY_PREFIXES = ("REG_", "BA_")

_TARGETS: dict = {}
_TIMEOUT = 30.0


def _init(timeout: float) -> None:
    global _TARGETS, _TIMEOUT
    _TARGETS = build_targets()
    _TIMEOUT = timeout


def _run(task):
    from ember_qc.benchmark import benchmark_one
    src_name, src_graph, tgt_name, algo, seed = task
    tgt = _TARGETS[tgt_name]
    r = benchmark_one(src_graph, tgt, algo, timeout=_TIMEOUT, seed=seed,
                      graph_name=src_name, topology_name=tgt_name)
    return {
        "source": src_name, "target": tgt_name, "algorithm": algo, "seed": seed,
        "success": int(bool(r.success)), "valid": int(bool(r.is_valid)),
        "avg_chain_length": r.avg_chain_length, "max_chain_length": r.max_chain_length,
        "total_qubits_used": r.total_qubits_used, "wall_time": r.wall_time,
        "problem_nodes": r.problem_nodes, "problem_edges": r.problem_edges,
    }


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 2)
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

    sources = build_sources()
    target_names = ["pegasus_6", "pegasus_6_broken5", "zephyr_4"]

    tasks = []
    for sname, (g, fam, n, d) in sources.items():
        tnames = ["pegasus_6"] if sname.startswith(PEG_ONLY_PREFIXES) else target_names
        for tname in tnames:
            for algo in ALGOS:
                for seed in SEEDS:
                    tasks.append((sname, g, tname, algo, seed))

    print(f"opt sweep: {len(sources)} sources × targets × {len(ALGOS)} algos × "
          f"{len(SEEDS)} seeds = {len(tasks)} trials; workers={n_workers}, timeout={timeout}s",
          flush=True)

    t0 = time.perf_counter()
    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init, initargs=(timeout,)) as ex:
        for row in ex.map(_run, tasks, chunksize=1):
            rows.append(row)
            done += 1
            if done % 60 == 0:
                print(f"  {done}/{len(tasks)}  ({time.perf_counter()-t0:.0f}s)", flush=True)
    print(f"all {len(tasks)} trials done in {time.perf_counter()-t0:.0f}s", flush=True)

    raw_path = os.path.join(HERE, "raw_results_opt.csv")
    with open(raw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    groups: dict = {}
    for r in rows:
        groups.setdefault((r["source"], r["target"], r["algorithm"]), []).append(r)
    summary = []
    for (sname, tname, algo), rs in sorted(groups.items()):
        ok = [r for r in rs if r["success"] and r["valid"]]
        acls = [r["avg_chain_length"] for r in ok]
        qubits = [r["total_qubits_used"] for r in ok]
        maxc = [r["max_chain_length"] for r in ok]
        times = [r["wall_time"] for r in rs]
        summary.append({
            "source": sname, "target": tname, "algorithm": algo,
            "n_seeds": len(rs), "n_success": len(ok),
            "success_rate": round(len(ok) / len(rs), 3) if rs else 0.0,
            "acl_mean": round(st.mean(acls), 3) if acls else "",
            "acl_std": round(st.pstdev(acls), 3) if len(acls) > 1 else (0.0 if acls else ""),
            "maxchain_mean": round(st.mean(maxc), 2) if maxc else "",
            "qubits_mean": round(st.mean(qubits), 1) if qubits else "",
            "time_mean": round(st.mean(times), 3) if times else "",
            "time_std": round(st.pstdev(times), 3) if len(times) > 1 else 0.0,
            "problem_nodes": rs[0]["problem_nodes"], "problem_edges": rs[0]["problem_edges"],
        })
    sum_path = os.path.join(HERE, "summary_opt.csv")
    with open(sum_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)

    print(f"wrote {raw_path}\nwrote {sum_path}\nTOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
