"""
docs/paper2/data/span_probe.py
===============================
Decides whether the span state (derived extents, notes s3.31) becomes the
default. Pre-registered bar (attraction.md ledger, set BEFORE running):
K100 <= 13.46 polished (the s3.30 cross-emergent result) at near-default
settings -- no schedule zoo; irregular-dense (biK48_96) beats point; no
regression on the win guards (regular_n316 ~3.5, ws_n486 ~3.1); K140
feasibility >= point's. Stretch: K100 <= ~11.2 (within 15% of template 9.78).

Arms: point (control), span (pure defaults -- the state flip alone),
span-tb (the testbed-decided configuration, recorded BEFORE this probe ran:
wire seeds + geo_iters=30 + cap_derate=0.65 + assign_every=5; the 24-combo
sweep found dynamics insensitive to eta/threshold, cadence ak=5 and the
0.65 derate the only live choices, finalist ACL 13.15), cross (legacy arm,
for the record), mm-full. Attribution caveat on record: span-tb vs span
confounds seeds/depth/derate; a follow-up ablation isolates them only if
span-tb clears the bar. geo_iters=30 for span is principled, not tuned: the
span coarse model takes no fine-level calibration (positions are its only
input), so the s3.24 trust-region argument for geo_iters=1 does not apply.

Run:  .venv/bin/python docs/paper2/data/span_probe.py
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
CSV_PATH = os.path.join(HERE, "span_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

ARMS = [
    ("point", {}),
    ("span", {"state": "span"}),
    ("span-tb", {"state": "span", "seed_mode": "wire", "geo_iters": 30,
                 "cap_derate": 0.65, "assign_every": 5}),
    ("cross", {"state": "cross"}),
]

acl = lambda e: sum(len(c) for c in e.values()) / len(e)


def cells():
    yield "K100", nx.complete_graph(100)
    yield "K140", nx.complete_graph(140)
    yield "biK48_96", nx.convert_node_labels_to_integers(load_graph(1350))
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
