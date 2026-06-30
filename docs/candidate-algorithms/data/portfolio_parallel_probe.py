"""
docs/candidate-algorithms/data/portfolio_parallel_probe.py
==========================================================
`mmfork-portfolio` runs ~6 ordered searches and keeps the best (~6x minorminer
serially). Its configs are independent, so they parallelize. This probe measures
the STANDALONE speedup of running them concurrently (one embedding using several
cores) — serial vs a fork-based process pool (minorminer holds the GIL, so threads
do not parallelize the C++ search). ACL is identical (same configs, best kept);
only wall-clock changes.

Usage:  python portfolio_parallel_probe.py [--smoke]
Writes  portfolio_parallel_probe.csv.
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
from ember_qc.algorithms.minorminer_forked import _portfolio_best, _PORTFOLIO  # noqa: E402

SEEDS = [0, 1, 2]
NCONF = len(_PORTFOLIO) + 1   # configs = default + the good orders
CELLS = [("P6", 6, 40, 0.5), ("P6", 6, 60, 0.5), ("P16", 16, 40, 0.3), ("P16", 16, 80, 0.3)]
SMOKE = [("P6", 6, 40, 0.5)]


def _acl(e):
    return sum(len(c) for c in e.values()) / len(e) if e else None


def main():
    smoke = "--smoke" in sys.argv
    cells = SMOKE if smoke else CELLS
    seeds = SEEDS[:1] if smoke else SEEDS
    targets = {}
    rows = []
    print(f"portfolio: serial vs process-parallel ({NCONF} configs)\n")
    print(f"{'cell':14s} {'serial s':>9s} {'par s':>8s} {'speedup':>8s} {'ACL match':>10s}")
    for (lab, m, n, d) in cells:
        if lab not in targets:
            targets[lab] = dnx.pegasus_graph(m)
        tgt = targets[lab]; adj = build_adjacency(tgt)
        src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, d, seed=11))
        cell = f"{lab}_n{n}_d{d}"
        s_times, p_times, match = [], [], True
        for s in seeds:
            bs, ts = _portfolio_best(src, tgt, s, 120, 1, "thread")          # serial
            bp, tp = _portfolio_best(src, tgt, s, 120, NCONF, "process")     # parallel (fork)
            s_times.append(ts); p_times.append(tp)
            if bs and bp:
                match &= abs((_acl(bs) or 0) - (_acl(bp) or 0)) < 1e-6
            valid = bool(bp) and is_valid_embedding(bp, src, tgt, adj=adj)
            match &= valid
        ms, mp = st.mean(s_times), st.mean(p_times)
        rows.append({"cell": cell, "serial_s": round(ms, 3), "par_s": round(mp, 3),
                     "speedup": round(ms / mp, 2) if mp else None, "acl_match": int(match)})
        print(f"{cell:14s} {ms:>9.2f} {mp:>8.2f} {ms/mp:>7.2f}x {str(match):>10s}")

    with open(os.path.join(HERE, "portfolio_parallel_probe.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cell", "serial_s", "par_s", "speedup", "acl_match"])
        w.writeheader(); w.writerows(rows)
    print("\nwrote portfolio_parallel_probe.csv")


if __name__ == "__main__":
    main()
