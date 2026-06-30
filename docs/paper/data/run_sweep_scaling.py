"""
docs/paper/data/run_sweep_scaling.py
====================================
Hardware-SCALE study: how every method behaves on the ACTUAL D-Wave hardware
topologies as the problem grows from small to large. Unlike run_sweep_opt.py
(small pegasus_6 = 680 qubits), this targets the full-size graphs:

  pegasus_graph(16)  = 5640 qubits  (D-Wave Advantage)
  zephyr_graph(15)   = 7440 qubits  (D-Wave Advantage2)

each with ~5% simulated dead qubits (a realistic working graph). The source
problem size n is swept small->large under two regimes so "bigger" is clean:
  - ER, fixed density d=0.3   (per-vertex degree grows with n -> harder fast)
  - d-regular, fixed degree k=6 (constant local structure -> scales much further)

Methods: minorminer, minorminer-layout, reweave, reweave-thorough,
mmfork-cuthill, mmfork-cuthill-fast, mmfork-portfolio, reweave-mmfork-cuthill.

Records ACL (mean/std over seeds), success rate, and wall-clock vs n, so we can
plot ACL-vs-n / time-vs-n / success-vs-n and ask whether the ordering advantage
widens with n and whether any method that is slower at small n scales better.

Writes raw_results_scaling.csv and summary_scaling.csv. Designed for the cluster
(many workers). The mmfork* algos need the fork built (scripts/build_mm_fork.sh).

Usage:  python run_sweep_scaling.py [n_workers] [timeout_s]
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

ALGOS = ["minorminer", "minorminer-layout", "reweave", "reweave-thorough",
         "mmfork-cuthill", "mmfork-cuthill-fast", "mmfork-portfolio",
         "reweave-mmfork-cuthill"]
SEEDS = list(range(3))

# n sweeps (small -> large). ER d=0.3 gets dense fast so it tops out sooner; the
# sparse d-regular regime scales much further. Cells past the feasibility frontier
# simply fail and are recorded as such.
ER_NS = [20, 40, 80, 120, 160]
REG_NS = [40, 80, 160, 320, 480]

TARGET_NAMES = ["pegasus16_broken", "zephyr15_broken"]


def build_targets() -> dict:
    import dwave_networkx as dnx
    from ember_qc.faults import simulate_faults
    p16 = dnx.pegasus_graph(16)
    z15 = dnx.zephyr_graph(15)
    return {
        "pegasus16": p16,
        "pegasus16_broken": simulate_faults(p16, fault_rate=0.05, fault_seed=FAULT_SEED),
        "zephyr15": z15,
        "zephyr15_broken": simulate_faults(z15, fault_rate=0.05, fault_seed=FAULT_SEED),
    }


def build_sources(K: int = 1) -> list:
    """K instances per cell; returns [(cell, graph, instance_id, fam, n, d)]."""
    out = []
    for i in range(K):
        seed = INSTANCE_SEED + i * 100003
        for n in ER_NS:
            g = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, 0.3, seed=seed))
            out.append((f"ERd0.3_n{n}", g, i, "ER", n, 0.3))
        for n in REG_NS:
            g = nx.convert_node_labels_to_integers(nx.random_regular_graph(6, n, seed=seed))
            out.append((f"REGk6_n{n}", g, i, "REG", n, 6))
    return out


_TARGETS: dict = {}
_TIMEOUT = 300.0


def _init(timeout: float) -> None:
    global _TARGETS, _TIMEOUT
    _TARGETS = build_targets()
    _TIMEOUT = timeout


def _run(task):
    from ember_qc.benchmark import benchmark_one
    src_name, src_graph, inst, tgt_name, algo, seed = task
    tgt = _TARGETS[tgt_name]
    r = benchmark_one(src_graph, tgt, algo, timeout=_TIMEOUT, seed=seed,
                      graph_name=f"{src_name}#{inst}", topology_name=tgt_name)
    return {
        "source": src_name, "instance": inst, "target": tgt_name, "algorithm": algo, "seed": seed,
        "n": src_graph.number_of_nodes(),
        "success": int(bool(r.success)), "valid": int(bool(r.is_valid)),
        "avg_chain_length": r.avg_chain_length, "max_chain_length": r.max_chain_length,
        "total_qubits_used": r.total_qubits_used, "wall_time": r.wall_time,
        "problem_nodes": r.problem_nodes, "problem_edges": r.problem_edges,
    }


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 2)
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    K = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    sources = build_sources(K)
    tasks = []
    for (cell, g, inst, fam, n, d) in sources:
        for tname in TARGET_NAMES:
            for algo in ALGOS:
                for seed in SEEDS:
                    tasks.append((cell, g, inst, tname, algo, seed))

    print(f"scaling sweep: K={K} instances × {len(TARGET_NAMES)} targets × "
          f"{len(ALGOS)} algos × {len(SEEDS)} seeds = {len(tasks)} trials; "
          f"workers={n_workers}, timeout={timeout}s", flush=True)

    t0 = time.perf_counter()
    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init, initargs=(timeout,)) as ex:
        for row in ex.map(_run, tasks, chunksize=1):
            rows.append(row)
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(tasks)}  ({time.perf_counter()-t0:.0f}s)", flush=True)
    print(f"all {len(tasks)} trials done in {time.perf_counter()-t0:.0f}s", flush=True)

    raw_path = os.path.join(HERE, "raw_results_scaling.csv")
    with open(raw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    groups: dict = {}
    for r in rows:
        groups.setdefault((r["source"], r["target"], r["algorithm"]), []).append(r)
    summary = []
    for (sname, tname, algo), rs in sorted(groups.items()):
        ok = [r for r in rs if r["success"] and r["valid"]]
        acls = [r["avg_chain_length"] for r in ok]
        maxc = [r["max_chain_length"] for r in ok]
        qubits = [r["total_qubits_used"] for r in ok]
        times = [r["wall_time"] for r in rs]
        # time over SUCCESSFUL runs too (capped/failed runs distort the time curve)
        ok_times = [r["wall_time"] for r in ok]
        # 95% CI for the mean ACL across INSTANCES (per-instance mean first, then SEM)
        per_inst: dict = {}
        for r in ok:
            per_inst.setdefault(r["instance"], []).append(r["avg_chain_length"])
        inst_means = [st.mean(v) for v in per_inst.values()]
        acl_ci = (1.96 * st.pstdev(inst_means) / (len(inst_means) ** 0.5)) if len(inst_means) > 1 else 0.0
        summary.append({
            "source": sname, "target": tname, "algorithm": algo, "n": rs[0]["n"],
            "n_seeds": len(rs), "n_success": len(ok), "n_instances": len(inst_means),
            "success_rate": round(len(ok) / len(rs), 3) if rs else 0.0,
            "acl_mean": round(st.mean(acls), 3) if acls else "",
            "acl_ci": round(acl_ci, 3),
            "acl_std": round(st.pstdev(acls), 3) if len(acls) > 1 else (0.0 if acls else ""),
            "maxchain_mean": round(st.mean(maxc), 2) if maxc else "",
            "qubits_mean": round(st.mean(qubits), 1) if qubits else "",
            "time_mean": round(st.mean(times), 3) if times else "",
            "time_mean_ok": round(st.mean(ok_times), 3) if ok_times else "",
            "time_std": round(st.pstdev(times), 3) if len(times) > 1 else 0.0,
            "problem_nodes": rs[0]["problem_nodes"], "problem_edges": rs[0]["problem_edges"],
        })
    sum_path = os.path.join(HERE, "summary_scaling.csv")
    with open(sum_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)

    print(f"wrote {raw_path}\nwrote {sum_path}\nTOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
