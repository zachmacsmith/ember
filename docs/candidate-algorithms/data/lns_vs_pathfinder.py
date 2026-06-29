"""Scratch: lns-cpsat vs pathfinder vs minorminer on a few cells (writeup aside).

Both lns-cpsat and pathfinder are MM-seeded improvers; this checks how the exact
CP-SAT repair compares to pathfinder's heuristic negotiated rip-up-reroute.
"""
import sys
import statistics as st
import networkx as nx
import dwave_networkx as dnx

import ember_qc.algorithms.lns_cpsat   # noqa
import ember_qc.algorithms.pathfinder  # noqa
from ember_qc.benchmark import benchmark_one

p6 = dnx.pegasus_graph(6)
z4 = dnx.zephyr_graph(4)
TGT = {"P6": p6, "Z4": z4}
TO = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
SEEDS = [0, 1, 2]
cells = [("ER", 30, 0.5, "P6"), ("ER", 30, 0.7, "P6"), ("ER", 30, 0.5, "Z4")]
algos = ["minorminer", "pathfinder", "lns-cpsat"]

print(f"timeout={TO}s  seeds={SEEDS}\n")
print(f"{'cell':16s} {'algo':12s} {'ACLmean':>8s} {'ACLstd':>7s} {'qubits':>7s} {'t(s)':>6s}")
print("-"*62)
for fam, n, p, tk in cells:
    g = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, p, seed=12345))
    tgt = TGT[tk]
    label = f"{fam}_n{n}_d{p}_{tk}"
    for a in algos:
        acls, qs, ts, ok = [], [], [], 0
        for s in SEEDS:
            r = benchmark_one(g, tgt, a, timeout=TO, seed=s, graph_name=label, topology_name=tk)
            if r.success and r.is_valid:
                ok += 1; acls.append(r.avg_chain_length); qs.append(r.total_qubits_used)
            ts.append(r.wall_time)
        am = round(st.mean(acls), 3) if acls else None
        asd = round(st.pstdev(acls), 3) if len(acls) > 1 else 0.0
        qm = round(st.mean(qs), 1) if qs else None
        print(f"{label:16s} {a:12s} {str(am):>8s} {str(asd):>7s} {str(qm):>7s} {st.mean(ts):>6.1f}  ok={ok}/{len(SEEDS)}")
    print()
