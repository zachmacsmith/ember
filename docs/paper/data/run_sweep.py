"""
docs/paper/data/run_sweep.py
============================
Expanded benchmark sweep for the Reweave ACM TQC article.

Drives Ember's atomic harness ``ember_qc.benchmark.benchmark_one`` (with its
four-layer validation and metric computation) over a grid of source graphs and
D-Wave targets, in parallel, and writes two CSVs under this directory:

  raw_results.csv  — one row per (source, target, algorithm, seed) trial
  summary.csv      — aggregated per (source, target, algorithm): success rate,
                     ACL mean/std, max-chain mean, qubits mean, wall-clock mean/std

Targets: clean Pegasus P6, broken Pegasus P6 (5% faulty qubits via Ember's
simulate_faults), and Zephyr Z4 (different topology family). Sources: an
Erdős–Rényi size×density grid plus a small d-regular / Barabási–Albert generality
set. One fixed instance per (family, n, d); variance is across the 5 algorithm
seeds (run-to-run variance on a fixed instance — MM's documented flaw).

Usage:  .venv/bin/python docs/paper/data/run_sweep.py [n_workers] [timeout]
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
INSTANCE_SEED = 12345          # fixes the source graph per (family, n, d)
FAULT_SEED = 7                 # fixes which qubits are broken
ALGOS = ["minorminer", "minorminer-layout", "reweave", "reweave-thorough"]
SEEDS = list(range(5))


# ── Target topologies (rebuilt once per worker; broken graph is seed-deterministic)

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


# ── Source graphs (one fixed instance per cell) ────────────────────────────────

def build_sources() -> dict:
    """Return {name: (graph, family, n, d_or_param)}. ER on all targets; the
    d-regular / BA generality set only needs the clean-Pegasus column."""
    src = {}
    for n in (20, 30, 40):
        for d in (0.3, 0.5, 0.7):
            g = nx.convert_node_labels_to_integers(
                nx.gnp_random_graph(n, d, seed=INSTANCE_SEED))
            src[f"ER_n{n}_d{d}"] = (g, "ER", n, d)
    # generality set (clean Pegasus only — see PEG_ONLY below)
    for n in (30, 40):
        for k in (4, 6):
            g = nx.convert_node_labels_to_integers(
                nx.random_regular_graph(k, n, seed=INSTANCE_SEED))
            src[f"REG_n{n}_k{k}"] = (g, "REG", n, k)
        for m in (3, 5):
            g = nx.convert_node_labels_to_integers(
                nx.barabasi_albert_graph(n, m, seed=INSTANCE_SEED))
            src[f"BA_n{n}_m{m}"] = (g, "BA", n, m)
    return src


PEG_ONLY_PREFIXES = ("REG_", "BA_")  # generality set runs on clean Pegasus only


# ── Worker ─────────────────────────────────────────────────────────────────────

_TARGETS: dict = {}
_TIMEOUT = 20.0


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
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

    sources = build_sources()
    target_names = ["pegasus_6", "pegasus_6_broken5", "zephyr_4"]

    tasks = []
    for sname, (g, fam, n, d) in sources.items():
        tnames = ["pegasus_6"] if sname.startswith(PEG_ONLY_PREFIXES) else target_names
        for tname in tnames:
            for algo in ALGOS:
                for seed in SEEDS:
                    tasks.append((sname, g, tname, algo, seed))

    print(f"sweep: {len(sources)} sources × targets × {len(ALGOS)} algos × "
          f"{len(SEEDS)} seeds = {len(tasks)} trials; workers={n_workers}, timeout={timeout}s",
          flush=True)

    t0 = time.perf_counter()
    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init,
                             initargs=(timeout,)) as ex:
        for row in ex.map(_run, tasks, chunksize=1):
            rows.append(row)
            done += 1
            if done % 40 == 0:
                print(f"  {done}/{len(tasks)}  ({time.perf_counter()-t0:.0f}s)", flush=True)
    print(f"all {len(tasks)} trials done in {time.perf_counter()-t0:.0f}s", flush=True)

    # raw CSV
    raw_path = os.path.join(HERE, "raw_results.csv")
    with open(raw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # aggregate per (source, target, algorithm)
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["source"], r["target"], r["algorithm"]), []).append(r)

    summary = []
    for (sname, tname, algo), rs in sorted(groups.items()):
        ok = [r for r in rs if r["success"] and r["valid"]]
        n_seeds = len(rs)
        acls = [r["avg_chain_length"] for r in ok]
        qubits = [r["total_qubits_used"] for r in ok]
        maxc = [r["max_chain_length"] for r in ok]
        times = [r["wall_time"] for r in rs]  # timing over all trials
        summary.append({
            "source": sname, "target": tname, "algorithm": algo,
            "n_seeds": n_seeds, "n_success": len(ok),
            "success_rate": round(len(ok) / n_seeds, 3) if n_seeds else 0.0,
            "acl_mean": round(st.mean(acls), 3) if acls else "",
            "acl_std": round(st.pstdev(acls), 3) if len(acls) > 1 else (0.0 if acls else ""),
            "maxchain_mean": round(st.mean(maxc), 2) if maxc else "",
            "qubits_mean": round(st.mean(qubits), 1) if qubits else "",
            "time_mean": round(st.mean(times), 3) if times else "",
            "time_std": round(st.pstdev(times), 3) if len(times) > 1 else 0.0,
            "problem_nodes": rs[0]["problem_nodes"], "problem_edges": rs[0]["problem_edges"],
        })

    sum_path = os.path.join(HERE, "summary.csv")
    with open(sum_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    print(f"wrote {raw_path}\nwrote {sum_path}", flush=True)
    print(f"TOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
