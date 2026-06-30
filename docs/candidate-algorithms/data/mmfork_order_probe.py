"""
docs/candidate-algorithms/data/mmfork_order_probe.py
====================================================
The decisive ordering experiment on minorminer's FULL search.

We forked minorminer (external/minorminer-fork) to add a ``var_order=`` parameter
that injects a user-supplied vertex order into ``find_embedding`` (the complete
heuristicEmbedding: tear-and-replace + ``tries`` restarts), not just the greedy
``quickpass``. With ``var_order`` unset the fork is byte-identical to stock
minorminer 0.2.22 (parity-tested). This probe asks the question the whole effort
turns on:

    Does guiding minorminer's full search with a better vertex order beat its
    default (randomized RPFS) ordering — on ACL and/or run-to-run variance?

For each cell and seed we run the fork with no var_order (== stock, the baseline)
and with ``var_order`` set to each deterministic ordering from
``ember_qc.algorithms.search_orders``. We report this at ``tries=10`` (how
minorminer is normally used — a fixed order vs 10 random-order restarts) and at
``tries=1`` (single construction — the pure per-run order effect).

Usage:  python mmfork_order_probe.py [--smoke] [tries]
Writes  mmfork_order_probe.csv  and prints per-order %delta vs default.
"""
from __future__ import annotations

import csv
import math
import os
import statistics as st
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

# Import the forked _minorminer extension (built in-place); fall back loudly.
FORK = "/Users/dabh/ember/external/minorminer-fork/minorminer"
sys.path.insert(0, FORK)
import _minorminer as mmfork  # noqa: E402
from ember_qc.algorithms.search_orders import ORDERINGS  # noqa: E402
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402

DEF = dict(max_no_improvement=10, timeout=1000, max_beta=None, inner_rounds=None,
           chainlength_patience=10, max_fill=None, threads=1, return_overlap=False,
           skip_initialization=False, verbose=0, interactive=False)

GRID = [
    ("ER", 30, 0.7, "pegasus_6"), ("ER", 40, 0.5, "pegasus_6"),
    ("ER", 40, 0.7, "pegasus_6"), ("ER", 50, 0.5, "pegasus_6"),
    ("ER", 60, 0.4, "pegasus_6"), ("ER", 30, 0.5, "zephyr_4"),
]
SMOKE = [("ER", 30, 0.7, "pegasus_6"), ("ER", 40, 0.5, "pegasus_6")]
LAB = {"pegasus_6": "P6", "zephyr_4": "Z4"}
SEEDS = [0, 1, 2, 3]
ORDER_NAMES = ["degeneracy", "minfill", "mcs", "cuthill", "spectral", "community", "bfs"]


def _acl(e):
    e = {k: v for k, v in e.items() if v}
    return sum(len(c) for c in e.values()) / len(e) if e else None


def run(tries: int, grid):
    targets = make_targets()
    rows = []
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p)
        tgt = targets[tname]
        adj = build_adjacency(tgt)
        S, T = list(src.edges()), list(tgt.edges())
        cell = f"{fam}_n{n}_d{p}_{LAB[tname]}"
        orders = {nm: ORDERINGS[nm](src) for nm in ORDER_NAMES}
        for s in SEEDS:
            # baseline: no var_order (== stock minorminer)
            e = mmfork.find_embedding(S, T, random_seed=s, tries=tries, **DEF)
            base = _acl(e) if is_valid_embedding({k: v for k, v in e.items() if v}, src, tgt, adj=adj) else None
            rows.append({"cell": cell, "order": "default", "seed": s, "tries": tries, "acl": base})
            for nm in ORDER_NAMES:
                e = mmfork.find_embedding(S, T, random_seed=s, tries=tries, var_order=orders[nm], **DEF)
                e = {k: v for k, v in e.items() if v}
                a = _acl(e) if is_valid_embedding(e, src, tgt, adj=adj) else None
                rows.append({"cell": cell, "order": nm, "seed": s, "tries": tries, "acl": a})
    return rows


def summarize(rows, tries):
    cells = list(dict.fromkeys(r["cell"] for r in rows))
    orders = ["default"] + ORDER_NAMES
    # per-order grid mean and mean %delta vs default (paired per cell)
    print(f"\n===== tries={tries} =====")
    print(f"{'order':12s} {'meanACL':>8s} {'std(seed)':>9s} {'vsDflt%':>8s} {'wins':>6s} {'nvalid':>7s}")
    bycell = {}
    for r in rows:
        bycell.setdefault((r["cell"], r["order"]), []).append(r["acl"])
    agg = {}
    for o in orders:
        deltas, acls, stds, wins, nvalid, ncmp = [], [], [], 0, 0, 0
        for c in cells:
            vals = [x for x in bycell.get((c, o), []) if x is not None]
            dvals = [x for x in bycell.get((c, "default"), []) if x is not None]
            nvalid += len(vals)
            if vals:
                acls.append(st.mean(vals)); stds.append(st.pstdev(vals) if len(vals) > 1 else 0.0)
            if vals and dvals:
                dm, bm = st.mean(dvals), st.mean(vals)
                deltas.append(100 * (bm - dm) / dm); ncmp += 1
                if bm < dm - 1e-9:
                    wins += 1
        agg[o] = (st.mean(acls) if acls else None, st.mean(stds) if stds else None,
                  st.mean(deltas) if deltas else None, wins, ncmp, nvalid)
    for o in orders:
        m, sd, d, wins, ncmp, nv = agg[o]
        ms = f"{m:.3f}" if m is not None else "fail"
        sds = f"{sd:.3f}" if sd is not None else "-"
        ds = f"{d:+.1f}" if d is not None else "-"
        print(f"{o:12s} {ms:>8s} {sds:>9s} {ds:>8s} {wins:>4d}/{ncmp:<2d} {nv:>7d}")
    return agg


def main():
    smoke = "--smoke" in sys.argv
    rest = [a for a in sys.argv[1:] if a != "--smoke"]
    tries_list = [int(rest[0])] if rest else ([10] if smoke else [10, 1])
    grid = SMOKE if smoke else GRID
    allrows = []
    for tr in tries_list:
        rows = run(tr, grid)
        allrows += rows
        summarize(rows, tr)
    with open(os.path.join(HERE, "mmfork_order_probe.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cell", "order", "seed", "tries", "acl"])
        w.writeheader(); w.writerows(allrows)
    print("\nwrote mmfork_order_probe.csv")


if __name__ == "__main__":
    main()
