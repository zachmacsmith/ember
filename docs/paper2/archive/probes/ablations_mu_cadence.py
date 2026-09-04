"""
docs/paper2/data/ablations_mu_cadence.py
=========================================
The two ablations owed by notes §3.24/§3.25, run together (notes §3.26 when
analyzed):

  mu ablation      — default (hinge²+μ) vs mu0 (hinge² only: does μ's memory
                     earn anything, or is Max's stale-shadow-price worry
                     borne out?) vs hinge0 (μ only).
  cadence ablation — geo_iters 1 (trust-region default) vs 10 (the v3
                     over-solving regression claim), each also with
                     vary_rng=False (frozen router RNG: rounds differ only by
                     geometry — clean attribution of trajectory gains to
                     steering rather than re-rolling).

Cells = the §3.25 probe cells (dense loss / parity / two win guards),
5 seeds, P16, 60 s, plus mm-full baseline. Paired by (cell, seed).

Run:  .venv/bin/python docs/paper2/data/ablations_mu_cadence.py
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
CSV_PATH = os.path.join(HERE, "ablations_mu_cadence.csv")
SEEDS = range(5)
TIMEOUT = 60

ARMS = [
    ("default", {}),                       # hinge²+μ, geo1, vary_rng
    ("mu0", {"mu_alpha": 0.0}),            # hinge² only
    ("hinge0", {"hinge_w": 0.0}),          # μ only
    ("geo10", {"geo_iters": 10}),          # v3 over-solving cadence
    ("geo1_frozen", {"vary_rng": False}),  # attribution: geometry-only rounds
    ("geo10_frozen", {"geo_iters": 10, "vary_rng": False}),
]

acl = lambda e: sum(len(c) for c in e.values()) / len(e)


def cells():
    yield "K100", nx.complete_graph(100)
    yield "ER100_d10", nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    yield "regular_n316", load_graph(13096)
    yield "ws_n486", load_graph(17188)


def main():
    target = dnx.pegasus_graph(16)
    T_edges = list(target.edges())
    rows = []
    t_start = time.time()
    for name, src in cells():
        for s in SEEDS:
            for arm, kw in ARMS:
                t0 = time.perf_counter()
                r = attract_embed(src, target, timeout=TIMEOUT, seed=s, **kw)
                rows.append(dict(
                    cell=name, arm=arm, seed=s,
                    final_acl=round(acl(r["embedding"]), 3)
                    if r["embedding"] else None,
                    legal_acl=r.get("legal_acl"),
                    rounds=r.get("rounds"),
                    time=round(time.perf_counter() - t0, 1),
                    diag=str(r.get("field_diag", ""))))
            t0 = time.perf_counter()
            emb = minorminer.find_embedding(src, T_edges, random_seed=s,
                                            timeout=TIMEOUT)
            rows.append(dict(cell=name, arm="mm-full", seed=s,
                             final_acl=round(acl(emb), 3) if emb else None,
                             legal_acl=None, rounds=None,
                             time=round(time.perf_counter() - t0, 1), diag=""))
            print(f"[{time.time()-t_start:6.0f}s] {name} seed {s} done",
                  flush=True)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    arm_names = [a for a, _ in ARMS] + ["mm-full"]
    for name, _ in cells():
        parts = [f"{name:14s}"]
        for arm in arm_names:
            ok = [r["final_acl"] for r in rows
                  if r["cell"] == name and r["arm"] == arm and r["final_acl"]]
            parts.append(f"{arm}={sum(ok)/len(ok):.2f}({len(ok)})"
                         if ok else f"{arm}=fail")
        print("  ".join(parts))


if __name__ == "__main__":
    main()
