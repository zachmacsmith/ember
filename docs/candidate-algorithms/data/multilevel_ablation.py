"""Attribute multilevel's gains: cold-MM vs cold-MM+trim vs full multilevel.

If cold-MM+trim ~= multilevel on ACL, the ACL win is "just trimming". The
variance (cross-seed std) win is the part attributable to the multilevel
structure (consistent coarse layout), which trimming alone should not produce.
"""
import warnings, statistics as st
warnings.filterwarnings("ignore")
import networkx as nx
import dwave_networkx as dnx
import minorminer

import ember_qc.algorithms.multilevel as M
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding

SEEDS = [0, 1, 2, 3, 4]

def cold_mm(src, target, adj, seed, timeout=20.0):
    raw = minorminer.find_embedding(src, list(target.edges()), random_seed=seed,
                                    timeout=timeout, verbose=0)
    if not raw: return None
    emb = {int(k):[int(q) for q in v] for k,v in raw.items()}
    return emb if is_valid_embedding(emb, src, target, adj=adj) else None

def trimmed(emb, src, adj):
    e = {k:list(v) for k,v in emb.items()}
    nbrs = {v:list(src.neighbors(v)) for v in e}
    M._trim(e, nbrs, adj, None)
    return e

def acl(emb): return sum(len(c) for c in emb.values())/len(emb)

P6 = dnx.pegasus_graph(6)
algo = M.Multilevel()

print(f"{'cell':16s} {'cold-MM':>16s} {'cold-MM+trim':>16s} {'multilevel':>16s}")
for (n,d) in [(20,0.5),(30,0.3),(30,0.5),(30,0.7)]:
    src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n,d,seed=12345))
    adj = build_adjacency(P6)
    a_cold, a_trim, a_ml = [], [], []
    for s in SEEDS:
        c = cold_mm(src, P6, adj, s)
        if c:
            a_cold.append(acl(c))
            a_trim.append(acl(trimmed(c, src, adj)))
        r = algo.embed(src, P6, timeout=20.0, seed=s)
        if r["embedding"]:
            a_ml.append(acl(r["embedding"]))
    def fmt(xs): return f"{st.mean(xs):.3f}±{st.pstdev(xs):.3f}" if len(xs)>1 else "--"
    print(f"ER_n{n}_d{d:<4} {fmt(a_cold):>16s} {fmt(a_trim):>16s} {fmt(a_ml):>16s}")
