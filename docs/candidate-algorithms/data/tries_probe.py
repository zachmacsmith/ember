"""
docs/candidate-algorithms/data/tries_probe.py
=============================================
Does a good fixed order let minorminer use FEWER restarts (`tries`) at the same
quality — i.e. is `mmfork-cuthill-fast` actually faster than stock minorminer?

A fixed Cuthill order removes the run-to-run diversity that minorminer's restarts
provide (the search-guidance study found `tries=10`≈`tries=1` on small targets),
so fewer tries may reach the same ACL. We sweep `tries ∈ {1,2,3,5,10}` for the
Cuthill-ordered forked search and report ACL and wall-clock (relative to
`tries=10`) on small (P6) and large (P16) targets — the speedup, if any, should
grow with target size where each try is expensive.

Usage:  python tries_probe.py [--smoke]
Writes  tries_probe.csv.
"""
from __future__ import annotations

import csv
import os
import statistics as st
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import networkx as nx  # noqa: E402
import dwave_networkx as dnx  # noqa: E402

from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.search_orders import ORDERINGS  # noqa: E402
from ember_qc.algorithms.minorminer_forked import forked_find_embedding  # noqa: E402

TRIES = [1, 2, 3, 5, 10]
SEEDS = [0, 1, 2]
# (target_label, m, source n, density)
CELLS = [
    ("P6", 6, 40, 0.5), ("P6", 6, 40, 0.7), ("P6", 6, 60, 0.5),
    ("P16", 16, 40, 0.3), ("P16", 16, 80, 0.3),
]
SMOKE = [("P6", 6, 40, 0.5), ("P16", 16, 40, 0.3)]


def main():
    smoke = "--smoke" in sys.argv
    cells = SMOKE if smoke else CELLS
    seeds = SEEDS[:2] if smoke else SEEDS
    targets = {}
    rows = []
    print(f"{'cell':14s} {'tries':>5s} {'ACL':>6s} {'t(s)':>7s} {'t/tries10':>10s}")
    for (lab, m, n, d) in cells:
        if lab not in targets:
            targets[lab] = dnx.pegasus_graph(m)
        tgt = targets[lab]; adj = build_adjacency(tgt)
        src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, d, seed=11))
        order = ORDERINGS["cuthill"](src)
        cell = f"{lab}_n{n}_d{d}"
        base_t = None
        for T in TRIES:
            acls, times = [], []
            for s in seeds:
                r = forked_find_embedding(src, tgt, order=order, seed=s, timeout=120, tries=T)
                e = r.get("embedding")
                if e and is_valid_embedding(e, src, tgt, adj=adj):
                    acls.append(sum(len(c) for c in e.values()) / len(e))
                times.append(r.get("time", float("nan")))
            acl = st.mean(acls) if acls else None
            tm = st.mean(times)
            if T == 10:
                base_t = tm
            ratio = (tm / base_t) if base_t else float("nan")
            rows.append({"cell": cell, "tries": T, "acl": acl, "time": tm})
            acls_s = f"{acl:.3f}" if acl is not None else "fail"
            print(f"{cell:14s} {T:>5d} {acls_s:>6s} {tm:>7.2f} {ratio:>9.2f}x")
        print()

    with open(os.path.join(HERE, "tries_probe.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cell", "tries", "acl", "time"])
        w.writeheader(); w.writerows(rows)
    print("wrote tries_probe.csv")


if __name__ == "__main__":
    main()
