"""S4.14: K_n seed deepening (n=5 -> 20 pairs). Run: --workers 8 on idle host."""
from __future__ import annotations
import argparse, csv, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import networkx as nx
import dwave_networkx as dnx
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _runner_common import terminal_polish  # noqa: E402
from ember_qc.benchmark import benchmark_one  # noqa: E402

CELLS = [("P16", 140), ("P16", 180), ("Z12", 140), ("Z12", 179)]
ARMS = ("minorminer", "p3-ate", "p3-clmm", "p3-mmpolish")
SEEDS = tuple(range(15, 30))
TIMEOUT = 60.0
_G = {}

def _init():
    _G["P16"] = dnx.pegasus_graph(16)
    _G["Z12"] = dnx.zephyr_graph(12)

def run(task):
    topo, n, arm, s = task
    src = nx.complete_graph(n)
    t0 = time.perf_counter()
    r = benchmark_one(src, _G[topo], arm, timeout=TIMEOUT, seed=s)
    wall = time.perf_counter() - t0
    ok = int(bool(r.success))
    acl = r.avg_chain_length if ok else ""
    spur = ""
    if ok:
        emb = {int(k): list(v) for k, v in (r.embedding or {}).items()}
        if emb:
            p = terminal_polish(emb, src, _G[topo], deadline_s=5.0)
            spur = sum(len(c) for c in p.values()) / n
    return (topo, n, arm, s, ok, acl, spur, round(wall, 2))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    tasks = [(t, n, arm, s) for t, n in CELLS for arm in ARMS for s in SEEDS]
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "m6_k140.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["topo","n","arm","seed","success","acl","acl_spur","wall"])
        with ProcessPoolExecutor(max_workers=a.workers, initializer=_init) as ex:
            futs = {ex.submit(run, t): t for t in tasks}
            done = 0
            for f in as_completed(futs):
                w.writerow(f.result()); fh.flush(); done += 1
                print(f"[{done}/{len(tasks)}] {futs[f]} -> {f.result()[4:7]}", flush=True)
    print("K140_DEEPEN_DONE")

if __name__ == "__main__":
    main()
