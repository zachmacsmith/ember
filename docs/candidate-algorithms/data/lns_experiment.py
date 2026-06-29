"""Scratch: measure lns-cpsat vs minorminer headroom across instances."""
import sys, time
import networkx as nx
import dwave_networkx as dnx

import ember_qc.algorithms.lns_cpsat  # noqa
from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.benchmark import benchmark_one

p6 = dnx.pegasus_graph(6)
z4 = dnx.zephyr_graph(4)
TGT = {"P6": p6, "Z4": z4}

cases = [
    ("ER", 24, 0.5, "P6"),
    ("ER", 30, 0.5, "P6"),
    ("ER", 30, 0.7, "P6"),
    ("ER", 40, 0.5, "P6"),
    ("ER", 40, 0.7, "P6"),
    ("ER", 30, 0.5, "Z4"),
]
timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0

algo = ALGORITHM_REGISTRY["lns-cpsat"]
print(f"timeout={timeout}s per trial\n")
print(f"{'case':18s} {'mm_ACL':>7s} {'ln_ACL':>7s} {'mm_q':>5s} {'ln_q':>5s} "
      f"{'d%':>6s} {'solves':>6s} {'muts':>5s} {'t(s)':>6s}")
print("-" * 78)
for fam, n, p, tk in cases:
    g = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, p, seed=12345))
    tgt = TGT[tk]
    rmm = benchmark_one(g, tgt, "minorminer", timeout=timeout, seed=0,
                        graph_name="g", topology_name=tk)
    r = algo.embed(g, tgt, timeout=timeout, seed=0)
    rln = benchmark_one(g, tgt, "lns-cpsat", timeout=timeout, seed=0,
                        graph_name="g", topology_name=tk)
    d = (100*(rln.avg_chain_length - rmm.avg_chain_length)/rmm.avg_chain_length
         if rmm.is_valid and rln.is_valid and rmm.avg_chain_length else float('nan'))
    print(f"{fam}_n{n}_d{p}_{tk:3s}  {rmm.avg_chain_length:7.3f} {rln.avg_chain_length:7.3f} "
          f"{rmm.total_qubits_used:5d} {rln.total_qubits_used:5d} {d:+6.1f} "
          f"{r.get('cost_function_evaluations',0):6d} {r.get('embedding_state_mutations',0):5d} "
          f"{rln.wall_time:6.1f}  mm_valid={rmm.is_valid} ln_valid={rln.is_valid}")
