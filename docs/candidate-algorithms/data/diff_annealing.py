"""Generate the tau-annealing trend and init ablation cited in diff-softassign.md.
Run: .venv/bin/python docs/candidate-algorithms/data/diff_annealing.py
Deterministic (seed 0). Prints two tables."""
import warnings; warnings.filterwarnings("ignore")
import networkx as nx, dwave_networkx as dnx
import minorminer
from ember_qc.algorithms.diffembed import embed_diff_softassign

tgt = dnx.pegasus_graph(6)
src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(20, 0.5, seed=12345))
mm = minorminer.find_embedding(src, list(tgt.edges()), random_seed=0, timeout=30, verbose=0)
mm_acl = sum(len(c) for c in mm.values()) / len(mm)
print(f"# Instance: ER n=20 d=0.5 -> Pegasus-6 (m={tgt.number_of_nodes()} qubits). minorminer ACL = {mm_acl:.3f}\n")

print("## tau-annealing trend (init=random, seed=0): ACL after round->repair at each level")
print(f"{'level':>5} {'tau':>7} {'loss':>9} {'valid':>6} {'ACL_round':>10}")
r = embed_diff_softassign(src, tgt, timeout=120, seed=0, return_trace=True, init="random")
for t in r["trace"]:
    print(f"{t['level']:>5} {t['tau']:>7.3f} {t['loss']:>9.3f} {str(t['valid']):>6} "
          f"{('' if t['acl'] is None else format(t['acl'],'.3f')):>10}")
print(f"-> returned ACL (best valid across levels) = "
      f"{sum(len(c) for c in r['embedding'].values())/max(1,len(r['embedding'])):.3f}\n")

print("## init ablation (seed=0): final returned ACL / validity")
print(f"{'init':>9} {'final_ACL':>10} {'qubits':>7} {'valid_levels':>13} {'time_s':>7}")
for init in ["mm", "spectral", "random"]:
    r = embed_diff_softassign(src, tgt, timeout=120, seed=0, return_trace=True, init=init)
    emb = r["embedding"]
    acl = sum(len(c) for c in emb.values())/max(1,len(emb)) if emb else float('nan')
    trace = r["trace"]
    vl = f"{sum(1 for t in trace if t['valid'])}/{len(trace)}"
    print(f"{init:>9} {acl:>10.3f} {sum(len(c) for c in emb.values()):>7} {vl:>13} {r['time']:>7.2f}")
