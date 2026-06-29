"""Scratch sanity checks for lns-cpsat (not a pytest)."""
import sys, time, io, contextlib
import networkx as nx
import dwave_networkx as dnx

import ember_qc.algorithms.lns_cpsat  # noqa: F401 -> registers
from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.benchmark import benchmark_one

algo = ALGORITHM_REGISTRY["lns-cpsat"]
print("version:", algo.version, "| name:", algo.name)

# 1) K6 into chimera(4): must be VALID via benchmark_one
src = nx.complete_graph(6)
tgt = dnx.chimera_graph(4)
r = benchmark_one(src, tgt, "lns-cpsat", timeout=20.0, seed=0,
                  graph_name="K6", topology_name="chimera_4")
print(f"\n[K6->chimera4] success={r.success} valid={r.is_valid} "
      f"ACL={r.avg_chain_length:.3f} qubits={r.total_qubits_used} "
      f"max={r.max_chain_length} t={r.wall_time:.2f}s status={r.status}")

# compare to minorminer on the same instance
rm = benchmark_one(src, tgt, "minorminer", timeout=20.0, seed=0,
                   graph_name="K6", topology_name="chimera_4")
print(f"[K6->chimera4] minorminer: valid={rm.is_valid} ACL={rm.avg_chain_length:.3f} "
      f"qubits={rm.total_qubits_used} t={rm.wall_time:.2f}s")

# 2) Determinism: identical embeddings for same seed (capture stdout too)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    e1 = algo.embed(src, tgt, timeout=20.0, seed=42)
    e2 = algo.embed(src, tgt, timeout=20.0, seed=42)
stdout_leak = buf.getvalue()
det = e1.get("embedding") == e2.get("embedding")
print(f"\n[determinism seed=42] identical={det}  stdout_leak={stdout_leak!r}")
print(f"  counters run1={ {k:e1.get(k) for k in ('target_node_visits','cost_function_evaluations','embedding_state_mutations','overlap_qubit_iterations')} }")
print(f"  counters run2={ {k:e2.get(k) for k in ('target_node_visits','cost_function_evaluations','embedding_state_mutations','overlap_qubit_iterations')} }")

# 3) Graceful failure: K20 into path_graph(2)
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    f = algo.embed(nx.complete_graph(20), nx.path_graph(2), timeout=2.0, seed=0)
print(f"\n[K20->path2] result={ {k:f[k] for k in ('embedding','success','status') if k in f} } "
      f"stdout_leak={buf2.getvalue()!r}")

# 4) Input immutability check
src2 = nx.complete_graph(6); tgt2 = dnx.chimera_graph(4)
ns, es = sorted(src2.nodes()), sorted(src2.edges())
nt, et = sorted(tgt2.nodes()), sorted(tgt2.edges())
algo.embed(src2, tgt2, timeout=5.0, seed=1)
print(f"\n[immutability] source_unchanged={sorted(src2.nodes())==ns and sorted(src2.edges())==es} "
      f"target_unchanged={sorted(tgt2.nodes())==nt and sorted(tgt2.edges())==et}")

# 5) Never-worse-than-MM on an ER instance into Pegasus
g = nx.convert_node_labels_to_integers(nx.gnp_random_graph(24, 0.5, seed=12345))
p6 = dnx.pegasus_graph(6)
rmm = benchmark_one(g, p6, "minorminer", timeout=30.0, seed=0, graph_name="ER", topology_name="p6")
rln = benchmark_one(g, p6, "lns-cpsat", timeout=30.0, seed=0, graph_name="ER", topology_name="p6")
print(f"\n[ER24 d0.5 -> P6] mm:   valid={rmm.is_valid} ACL={rmm.avg_chain_length:.3f} qubits={rmm.total_qubits_used} max={rmm.max_chain_length} t={rmm.wall_time:.1f}s")
print(f"[ER24 d0.5 -> P6] lns:  valid={rln.is_valid} ACL={rln.avg_chain_length:.3f} qubits={rln.total_qubits_used} max={rln.max_chain_length} t={rln.wall_time:.1f}s")
if rmm.is_valid and rln.is_valid:
    print(f"  -> lns ACL delta vs mm: {100*(rln.avg_chain_length-rmm.avg_chain_length)/rmm.avg_chain_length:+.1f}%  "
          f"never_worse={rln.avg_chain_length <= rmm.avg_chain_length + 1e-9}")
