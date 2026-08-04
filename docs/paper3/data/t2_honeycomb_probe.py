"""§4.16 results-side diagnostic (pre-registered in the §4.16 results note):
the honeycomb success-bar trip — cliff-seed noise or a real ember cost?

The 7 gross MM-succ/ember-fail T2 honeycomb graphs (net −5 after 2 reverse
flips) are all n=1870–2318 near the Z12 pigeonhole edge, MM walls 15–56 s at
the succeeding seed. Probe: those graphs x fresh algo seeds {50,51,52} x
{minorminer, p3-ember}, 60 s — 42 rows — plus one deterministic try_native
wall per graph (the glasgow miss tax, no seed).

PRE-REGISTERED READ: REAL iff ember total successes < MM total − 2 over the
21 (graph, seed) pairs (beyond one graph-seed flip); otherwise the T2 trip
is recorded as the null's tail amplified by the measured native-stage tax.

Run on hyde06 (library cache warm):
  .venv/bin/python docs/paper3/data/t2_honeycomb_probe.py --workers 14
"""
from __future__ import annotations

import argparse
import csv
import os
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "t2_honeycomb_probe.csv")

GIDS = (32426, 32432, 32442, 32447, 32472, 32475, 32502)
SEEDS = (50, 51, 52)
ARMS = ("minorminer", "p3-ember")
TIMEOUT = 60.0

_G = {}


def _init():
    import dwave_networkx as dnx
    from ember_qc.load_graphs import load_graph
    _G["tgt"] = dnx.zephyr_graph(12)
    _G["src"] = {gid: load_graph(gid) for gid in GIDS}


def run_one(task):
    gid, arm, seed = task
    from ember_qc.benchmark import benchmark_one
    src = _G["src"][gid]
    t0 = time.perf_counter()
    r = benchmark_one(src, _G["tgt"], arm, timeout=TIMEOUT, seed=seed)
    return {"graph_id": gid, "arm": arm, "seed": seed,
            "success": int(bool(r.success)),
            "acl": round(r.avg_chain_length, 4) if r.success else "",
            "wall": round(r.wall_time if r.wall_time is not None
                          else time.perf_counter() - t0, 2)}


def native_tax():
    from ember_qc.algorithms.paper3.native import try_native
    rows = []
    for gid in GIDS:
        src = _G["src"][gid]
        t0 = time.perf_counter()
        emb = try_native(src, _G["tgt"], t0 + 60.0)
        rows.append((gid, src.number_of_nodes(), src.number_of_edges(),
                     round(time.perf_counter() - t0, 3), emb is not None))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=14)
    args = ap.parse_args()

    _init()
    print("deterministic native-stage tax (gid, n, m, wall_s, hit):")
    for row in native_tax():
        print(f"  {row}")

    tasks = [(g, a, s) for g in GIDS for a in ARMS for s in SEEDS]
    t0 = time.time()
    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["graph_id", "arm", "seed",
                                           "success", "acl", "wall"])
        w.writeheader()
        with Pool(args.workers, initializer=_init) as pool:
            for k, row in enumerate(pool.imap_unordered(run_one, tasks), 1):
                w.writerow(row)
                fh.flush()
                print(f"[{k}/{len(tasks)}] {row}", flush=True)
    with open(CSV_PATH, newline="") as fh:
        rows = list(csv.DictReader(fh))
    mm = sum(int(r["success"]) for r in rows if r["arm"] == "minorminer")
    em = sum(int(r["success"]) for r in rows if r["arm"] == "p3-ember")
    n = len(GIDS) * len(SEEDS)
    verdict = "REAL" if em < mm - 2 else "NULL-TAIL"
    print(f"\nprobe: MM {mm}/{n}  ember {em}/{n}  -> {verdict} "
          f"(pre-registered: REAL iff ember < MM - 2)")
    print(f"done in {time.time() - t0:.0f}s")
    print("HONEYCOMB_PROBE_DONE")


if __name__ == "__main__":
    main()
