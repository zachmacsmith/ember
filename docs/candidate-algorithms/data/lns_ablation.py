"""Scratch A/B: does the cluster phase add value beyond single-vertex pruning?

Compares, on a few ER instances into Pegasus-6:
  - full     : single-vertex worklist + cluster escape
  - single   : single-vertex worklist only (cluster phase disabled)
Reports best qubit total, wall time, #CP-SAT solves. Determinism re-checked.
"""
import sys, time
import networkx as nx
import dwave_networkx as dnx
import ember_qc.algorithms.lns_cpsat as M

p6 = dnx.pegasus_graph(6)
TO = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
cases = [(24, 0.5), (30, 0.5), (30, 0.7), (40, 0.7)]

def mm_total(g, tgt, seed=0):
    import minorminer
    emb = minorminer.find_embedding(g, list(tgt.edges()), random_seed=seed, timeout=10, verbose=0)
    return sum(len(c) for c in emb.values()), emb

print(f"timeout={TO}s   (mm_q = minorminer qubits)\n")
print(f"{'case':12s} {'mm_q':>5s} {'full_q':>6s} {'full_t':>6s} {'full_s':>6s} "
      f"{'sing_q':>6s} {'sing_t':>6s} {'sing_s':>6s}")
print("-"*64)
for n, p in cases:
    g = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, p, seed=12345))
    mmq, _ = mm_total(g, p6)

    # full
    t0 = time.perf_counter()
    r = M._LnsCpsatRun(g, p6, seed=0)
    best = r.run(time.perf_counter()+TO, mm_timeout=8.0)
    full_q = sum(len(c) for c in best.values()); full_t = time.perf_counter()-t0
    full_s = r.repair_solves

    # single-only: disable cluster phase
    t0 = time.perf_counter()
    r2 = M._LnsCpsatRun(g, p6, seed=0)
    r2._next_cluster_anchor = lambda tabu: None
    best2 = r2.run(time.perf_counter()+TO, mm_timeout=8.0)
    sing_q = sum(len(c) for c in best2.values()); sing_t = time.perf_counter()-t0
    sing_s = r2.repair_solves

    print(f"ER_n{n}_d{p}  {mmq:5d} {full_q:6d} {full_t:6.1f} {full_s:6d} "
          f"{sing_q:6d} {sing_t:6.1f} {sing_s:6d}")
