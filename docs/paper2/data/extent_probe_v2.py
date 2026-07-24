"""
docs/paper2/data/extent_probe_v2.py
====================================
Extent-state v2 probe (tip-potential field coupling + per-round sort
assignment; notes s3.29). Same pre-registered bar as v1: K100 <= ~11.2
(template 9.78, mm ~13.6), no win-guard regression, K140 >= 2/3 legal.
Arms add cross-v1 (assign off, no tip coupling) for one-flip attribution.

Run:  .venv/bin/python docs/paper2/data/extent_probe_v2.py
"""

import csv
import os
import time

import networkx as nx
import dwave_networkx as dnx
import minorminer

from ember_qc.load_graphs import load_graph
from ember_qc.algorithms.factored import attract_embed

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "extent_probe_v2.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

ARMS = [
    ("point", {}),
    ("cross-v1", {"state": "cross", "assign": False, "field_ext_w": 0.0}),
    ("cross2", {"state": "cross"}),
    ("cross2-bars", {"state": "cross", "seed_mode": "bars"}),
]

acl = lambda e: sum(len(c) for c in e.values()) / len(e)


def cells():
    yield "K100", nx.complete_graph(100)
    yield "K140", nx.complete_graph(140)
    yield "ER100_d10", nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    yield "regular_n316", load_graph(13096)
    yield "ws_n486", load_graph(17188)


def main():
    target = dnx.pegasus_graph(16)
    T_edges = list(target.edges())
    rows = []
    for name, src in cells():
        for s in SEEDS:
            for arm, kw in ARMS:
                t0 = time.perf_counter()
                r = attract_embed(src, target, timeout=TIMEOUT, seed=s, **kw)
                rows.append(dict(
                    cell=name, arm=arm, seed=s,
                    final_acl=round(acl(r["embedding"]), 3)
                    if r["embedding"] else None,
                    rounds=r.get("rounds"),
                    time=round(time.perf_counter() - t0, 1),
                    diag=str(r.get("field_diag", ""))))
            t0 = time.perf_counter()
            emb = minorminer.find_embedding(src, T_edges, random_seed=s,
                                            timeout=TIMEOUT)
            rows.append(dict(cell=name, arm="mm-full", seed=s,
                             final_acl=round(acl(emb), 3) if emb else None,
                             rounds=None,
                             time=round(time.perf_counter() - t0, 1), diag=""))
            print(f"{name} seed {s} done", flush=True)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    for name, _ in cells():
        parts = [f"{name:13s}"]
        for arm in [a for a, _ in ARMS] + ["mm-full"]:
            ok = [r["final_acl"] for r in rows
                  if r["cell"] == name and r["arm"] == arm and r["final_acl"]]
            parts.append(f"{arm}={sum(ok)/len(ok):.2f}({len(ok)})"
                         if ok else f"{arm}=fail")
        print("  ".join(parts))


if __name__ == "__main__":
    main()
