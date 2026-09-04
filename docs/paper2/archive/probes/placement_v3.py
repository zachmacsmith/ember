"""
docs/paper2/data/placement_v3.py
=================================
First probe of the pure attraction embedder (factored/placement.py — v3: no
minorminer anywhere in the pipeline) against stock minorminer. Instances match
the §3.18-3.20 placement-loop cells (ER avg degree 10, instance seed 12345)
so results are comparable with placement_loop*.csv.

Modes:
  --smoke        tiny instance into Pegasus-4, asserts validity
  --cell N       one (n=N, seed 0) run into Pegasus-16 vs stock mm, prints both
  (default)      3 cells x 5 seeds vs stock mm, writes placement_v3.csv

Run:   .venv/bin/python docs/paper2/data/placement_v3.py --smoke
"""

import csv
import os
import sys
import time

import networkx as nx
import dwave_networkx as dnx
import minorminer

from ember_qc.embedding_backend import is_valid_embedding
from ember_qc.algorithms.factored import attract_embed

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "placement_v3.csv")

INSTANCE_SEED = 12345
SEEDS = range(5)
NS = (100, 140, 180)

acl = lambda e: sum(len(c) for c in e.values()) / len(e)


def make_source(n):
    d = 10.0 / (n - 1)
    return nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(n, d, seed=INSTANCE_SEED))


def run_pair(src, target, T_edges, seed, timeout):
    """One attraction run and one stock-mm run; returns two result rows."""
    t0 = time.perf_counter()
    res = attract_embed(src, target, timeout=timeout, seed=seed)
    t_att = time.perf_counter() - t0
    att = dict(arm="attraction", seed=seed,
               final_acl=round(acl(res["embedding"]), 3) if res["embedding"] else None,
               legal_acl=res.get("legal_acl"), rounds=res.get("rounds"),
               time=round(t_att, 2))

    t0 = time.perf_counter()
    emb = minorminer.find_embedding(list(src.edges()), T_edges,
                                    random_seed=seed, timeout=timeout)
    t_mm = time.perf_counter() - t0
    mm = dict(arm="mm-full", seed=seed,
              final_acl=round(acl(emb), 3) if emb else None,
              legal_acl=None, rounds=None, time=round(t_mm, 2))
    return att, mm


def main():
    if "--smoke" in sys.argv:
        target = dnx.pegasus_graph(4)
        src = make_source(30)
        res = attract_embed(src, target, timeout=120, seed=0)
        assert res["embedding"], "smoke: attraction failed"
        assert is_valid_embedding(res["embedding"], src, target), "smoke: invalid"
        print(f"smoke OK: acl={acl(res['embedding']):.2f} "
              f"legal={res.get('legal_acl')} rounds={res.get('rounds')} "
              f"time={res['time']:.1f}s")
        return

    target = dnx.pegasus_graph(16)
    T_edges = list(target.edges())

    if "--cell" in sys.argv:
        n = int(sys.argv[sys.argv.index("--cell") + 1])
        src = make_source(n)
        att, mm = run_pair(src, target, T_edges, seed=0, timeout=1200)
        for r in (att, mm):
            print(f"{r['arm']:10s}: final {r['final_acl']}  legal {r['legal_acl']}"
                  f"  rounds {r['rounds']}  time {r['time']}s")
        return

    rows = []
    for n in NS:
        src = make_source(n)
        for seed in SEEDS:
            att, mm = run_pair(src, target, T_edges, seed, timeout=1200)
            for r in (att, mm):
                r["n"] = n
                rows.append(r)
            print(f"n={n} seed={seed}: att {att['final_acl']} ({att['time']}s) "
                  f"vs mm {mm['final_acl']} ({mm['time']}s)", flush=True)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["n", "arm", "seed", "final_acl",
                                           "legal_acl", "rounds", "time"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    for n in NS:
        for arm in ("attraction", "mm-full"):
            rs = [r for r in rows if r["n"] == n and r["arm"] == arm]
            ok = [r for r in rs if r["final_acl"]]
            if ok:
                m = sum(r["final_acl"] for r in ok) / len(ok)
                t = sum(r["time"] for r in ok) / len(ok)
                print(f"n={n} {arm:10s}: ACL {m:6.3f}  time {t:7.1f}s  "
                      f"ok {len(ok)}/{len(rs)}")


if __name__ == "__main__":
    main()
