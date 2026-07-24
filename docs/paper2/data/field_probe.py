"""
docs/paper2/data/field_probe.py
================================
Decides the default coarse field for the attraction embedder (notes §3.25):
v3.1 one-bin push (control) vs the VLSI field (typed tile grid + smeared
demand + hinge²+μ Poisson repulsion; field.py). Cells chosen from the §3.23
sweep's verdict classes:

  K100                 — dense loss case (complete 101-300 was +8.2)
  ER n=100, deg 10     — parity guard (was +1.24 band)
  regular_n316_d4_s1   — structured win guard (sweep: att 3.56 vs mm 4.07)
  ws_n486_k4_b0.30_s0  — structured win guard (sweep: att 3.47 vs mm 4.10)

Arms: push / poisson / mm-full, 3 seeds, P16, 60 s. Pre-registered decision
rule (attraction.md): poisson becomes the default iff it improves the dense
cell without regressing the win cells beyond noise.

Run:  .venv/bin/python docs/paper2/data/field_probe.py
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
CSV_PATH = os.path.join(HERE, "field_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

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
    for name, src in cells():
        for s in SEEDS:
            for arm, kw in (("push", dict(field="push")),
                            ("poisson", dict(field="poisson"))):
                t0 = time.perf_counter()
                r = attract_embed(src, target, timeout=TIMEOUT, seed=s, **kw)
                rows.append(dict(
                    cell=name, arm=arm, seed=s,
                    final_acl=round(acl(r["embedding"]), 3) if r["embedding"] else None,
                    legal_acl=r.get("legal_acl"), rounds=r.get("rounds"),
                    time=round(time.perf_counter() - t0, 1),
                    diag=str(r.get("field_diag", ""))))
            t0 = time.perf_counter()
            emb = minorminer.find_embedding(src, T_edges, random_seed=s,
                                            timeout=TIMEOUT)
            rows.append(dict(cell=name, arm="mm-full", seed=s,
                             final_acl=round(acl(emb), 3) if emb else None,
                             legal_acl=None, rounds=None,
                             time=round(time.perf_counter() - t0, 1), diag=""))
            print(f"{name} seed {s}: " + "  ".join(
                f"{r['arm']}={r['final_acl']}({r['time']}s)"
                for r in rows[-3:]), flush=True)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    for name, _ in cells():
        line = [name]
        for arm in ("push", "poisson", "mm-full"):
            ok = [r["final_acl"] for r in rows
                  if r["cell"] == name and r["arm"] == arm and r["final_acl"]]
            line.append(f"{arm}: " + (
                f"{sum(ok)/len(ok):.2f} ({len(ok)}/3)" if ok else "fail"))
        print("  ".join(line))


if __name__ == "__main__":
    main()
