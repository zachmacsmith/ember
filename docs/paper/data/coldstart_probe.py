"""
docs/paper/data/coldstart_probe.py
==================================
Backs the §3.4 aside: "a from-scratch (cold-start) router balloons chains." Runs
the standalone ``pathfinder-cold`` algorithm (no warm start) against
``minorminer`` on the clean-Pegasus Erdős–Rényi grid and prints the ACL ranges,
so the cold-start-vs-MM contrast in the paper is reproducible.

Usage:  python coldstart_probe.py
Reproducible (ACL is deterministic per seed); cold start may fail to legalize on
the densest cells within the time budget — those are reported as failures.
"""
from __future__ import annotations

import statistics as st
import warnings

warnings.filterwarnings("ignore")

import networkx as nx          # noqa: E402
import dwave_networkx as dnx   # noqa: E402
from ember_qc import benchmark_one  # noqa: E402

INSTANCE_SEED = 12345
SIZES = (20, 30, 40)
DENS = (0.3, 0.5, 0.7)
SEEDS = range(3)
TIMEOUT = 20.0


def main():
    p6 = dnx.pegasus_graph(6)
    cold_acls, mm_acls, fails = [], [], []
    for n in SIZES:
        for d in DENS:
            g = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, d, seed=INSTANCE_SEED))
            cold = [benchmark_one(g, p6, "pathfinder-cold", timeout=TIMEOUT, seed=s) for s in SEEDS]
            mm = [benchmark_one(g, p6, "minorminer", timeout=TIMEOUT, seed=s) for s in SEEDS]
            cok = [r.avg_chain_length for r in cold if r.success]
            mok = [r.avg_chain_length for r in mm if r.success]
            if cok:
                cold_acls.append(st.mean(cok))
            else:
                fails.append(f"n{n}_d{d}")
            if mok:
                mm_acls.append(st.mean(mok))
            print(f"  ER n{n} d{d}: cold-start ACL="
                  f"{(st.mean(cok) if cok else float('nan')):.2f}  minorminer ACL={st.mean(mok):.2f}")
    print()
    if cold_acls:
        print(f"cold-start ACL over succeeding cells: {min(cold_acls):.1f}–{max(cold_acls):.1f}")
    print(f"minorminer ACL same grid:             {min(mm_acls):.1f}–{max(mm_acls):.1f}")
    print(f"cold-start failed to legalize on: {fails or 'no cells'}")


if __name__ == "__main__":
    main()
