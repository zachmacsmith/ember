"""
Bake-off evaluation: benchmark every algorithm on the HELD-OUT test graphs
(data/learn/test.jsonl — instance-disjoint from training) through ember_qc's
benchmark_one, and report the headline comparison vs RW/MM:
  * ACL mean (quality)              -> lower is better
  * ACL std across seeds per graph  -> run-to-run variance (RW's headline edge)
  * success rate, wall-clock
Multiple seeds per (graph, algo) expose MM's decode variance.

CLI:
  EMBER_LEARN_CKPT_DIR=ckpts python -m ember_qc_learn.evaluate \
      --data data/learn --out data/learn/eval --workers 32 --seeds 3
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics as st
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

warnings.filterwarnings("ignore")

DEFAULT_ALGOS = [
    "minorminer", "minorminer-layout", "reweave", "reweave-thorough",
    "learned-gnn-seed", "learned-gnn-seed-direct",
    "learned-retrieve", "learned-vae", "learned-obj",
]

_TARGETS: Dict = {}
_TIMEOUT = 20.0


def _init(timeout: float, ckpt_dir: str) -> None:
    global _TARGETS, _TIMEOUT
    if ckpt_dir:
        os.environ["EMBER_LEARN_CKPT_DIR"] = ckpt_dir
    import warnings as w; w.filterwarnings("ignore")
    import ember_qc  # noqa: F401
    import ember_qc_learn  # noqa: F401  (register learned-*)
    import dwave_networkx as dnx
    _TARGETS = {"pegasus_6": dnx.pegasus_graph(6), "zephyr_4": dnx.zephyr_graph(4)}
    _TIMEOUT = timeout


def _run(task) -> Dict:
    import networkx as nx
    from ember_qc.benchmark import benchmark_one
    rec, target, algo, seed = task
    H = nx.Graph(); H.add_nodes_from(range(rec["n"]))
    H.add_edges_from((int(u), int(v)) for u, v in rec["edges"])
    r = benchmark_one(H, _TARGETS[target], algo, timeout=_TIMEOUT, seed=seed,
                      graph_name=rec["id"], topology_name=target)
    return {"id": rec["id"], "family": rec["family"], "n": rec["n"], "param": rec["param"],
            "target": target, "algorithm": algo, "seed": seed,
            "valid": int(bool(r.is_valid)), "success": int(bool(r.success)),
            "acl": r.avg_chain_length if r.is_valid else "",
            "maxchain": r.max_chain_length if r.is_valid else "",
            "qubits": r.total_qubits_used if r.is_valid else "",
            "time": r.wall_time}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/learn")
    ap.add_argument("--out", default="data/learn/eval")
    ap.add_argument("--algos", nargs="*", default=DEFAULT_ALGOS)
    ap.add_argument("--targets", nargs="*", default=["pegasus_6", "zephyr_4"])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--ckpt-dir", default=os.environ.get("EMBER_LEARN_CKPT_DIR", "ckpts"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    recs = [json.loads(l) for l in open(os.path.join(args.data, "test.jsonl"))]
    tasks = []
    for rec in recs:
        for target in args.targets:
            if target not in rec.get("labels", {}) or "embedding" not in rec["labels"][target]:
                continue  # only graphs RW could embed into this target
            for algo in args.algos:
                for seed in range(args.seeds):
                    tasks.append((rec, target, algo, seed))
    print(f"eval: {len(recs)} test graphs × {len(args.targets)} targets × {len(args.algos)} algos "
          f"× {args.seeds} seeds = {len(tasks)} trials; workers={args.workers}", flush=True)

    t0 = time.perf_counter(); rows = []; done = 0
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init,
                             initargs=(args.timeout, args.ckpt_dir)) as ex:
        for row in ex.map(_run, tasks, chunksize=1):
            rows.append(row); done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(tasks)} ({time.perf_counter()-t0:.0f}s)", flush=True)
    raw = os.path.join(args.out, "raw_eval.csv")
    with open(raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # ---- aggregate: per (target, algo) headline + per-graph across-seed variance ----
    by_algo: Dict = {}
    pergraph: Dict = {}      # (target, algo, id) -> [acl per seed]
    for r in rows:
        by_algo.setdefault((r["target"], r["algorithm"]), []).append(r)
        if r["valid"] and r["acl"] != "":
            pergraph.setdefault((r["target"], r["algorithm"], r["id"]), []).append(r["acl"])
    summary = []
    for (target, algo), rs in sorted(by_algo.items()):
        ok = [r for r in rs if r["valid"] and r["acl"] != ""]
        acls = [r["acl"] for r in ok]
        # mean of per-graph across-seed std = MM-style run-to-run variance
        seed_stds = [st.pstdev(v) for (t, a, _), v in pergraph.items()
                     if t == target and a == algo and len(v) > 1]
        summary.append({
            "target": target, "algorithm": algo, "n_trials": len(rs),
            "success_rate": round(len(ok) / len(rs), 3) if rs else 0.0,
            "acl_mean": round(st.mean(acls), 3) if acls else "",
            "acl_std_overall": round(st.pstdev(acls), 3) if len(acls) > 1 else "",
            "acl_std_perseed_mean": round(st.mean(seed_stds), 4) if seed_stds else "",
            "time_mean": round(st.mean([r["time"] for r in rs]), 4),
        })
    sm = os.path.join(args.out, "summary_eval.csv")
    with open(sm, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
    print(f"\nwrote {raw}\nwrote {sm}\nTOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)
    # quick console headline (pegasus_6)
    print("\n== pegasus_6 headline (lower ACL better) ==")
    print(f"{'algorithm':26s}{'succ':>6s}{'ACL':>8s}{'ACLstd/seed':>13s}{'time':>9s}")
    for s in summary:
        if s["target"] == "pegasus_6":
            print(f"{s['algorithm']:26s}{s['success_rate']:>6}{str(s['acl_mean']):>8}"
                  f"{str(s['acl_std_perseed_mean']):>13}{str(s['time_mean']):>9}")


if __name__ == "__main__":
    main()
