"""Trace where the V-cycle fails across the eval grid (scratch)."""
import warnings, time
warnings.filterwarnings("ignore")
import networkx as nx
import dwave_networkx as dnx

import ember_qc.algorithms.multilevel as M
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding

def trace(src, target, seed=0, coarse_target=8, n_restarts=4, fm_rounds=2, deadline=None):
    adj = build_adjacency(target)
    all_q = set(adj)
    tele = M._Tele()
    import random
    rng = random.Random((seed*2654435761+12345)&0xFFFFFFFF)
    graphs, cmaps = M._build_hierarchy(src, rng, coarse_target, 8, deadline)
    sizes = [g.number_of_nodes() for g in graphs]
    print(f"  hierarchy sizes (fine->coarse): {sizes}")
    emb = M._base_embed(graphs[-1], target, adj, seed, n_restarts, deadline, tele)
    if emb is None:
        print("  base embed FAILED"); return
    print(f"  base embed ok: coarsest n={graphs[-1].number_of_nodes()} "
          f"acl={sum(len(c) for c in emb.values())/len(emb):.2f}")
    for i in range(len(graphs)-2, -1, -1):
        h = graphs[i]
        fine = M._interpolate(emb, cmaps[i], adj, all_q)
        if fine is None:
            print(f"  level {i} (n={h.number_of_nodes()}): INTERPOLATE failed"); return
        edges = sorted((min(u,v),max(u,v)) for u,v in h.edges())
        # count uncovered before repair
        def covered(a,b):
            cb=set(fine[b]); return any(w in cb for q in fine[a] for w in adj[q])
        unc = sum(1 for (u,v) in edges if not covered(u,v))
        ok = M._repair_edges(fine, edges, adj, deadline, tele)
        if not ok:
            print(f"  level {i} (n={h.number_of_nodes()} e={len(edges)}): "
                  f"REPAIR failed ({unc} uncovered after split)"); return
        nbrs = {v:list(h.neighbors(v)) for v in fine}
        M._trim(fine, nbrs, adj, deadline)
        M._fm_rebalance(fine, nbrs, adj, deadline, fm_rounds)
        valid = is_valid_embedding(fine, h, target, adj=adj)
        acl = sum(len(c) for c in fine.values())/len(fine)
        print(f"  level {i} (n={h.number_of_nodes()} e={len(edges)}): "
              f"{unc} uncovered after split -> repaired, valid={valid} acl={acl:.2f}")
        if not valid:
            print("    -> INVALID after refine"); return
        emb = fine
    print(f"  V-CYCLE SUCCESS final acl={sum(len(c) for c in emb.values())/len(emb):.2f}")

P6 = dnx.pegasus_graph(6)
Z4 = dnx.zephyr_graph(4)
for (n,d) in [(20,0.3),(20,0.5),(20,0.7),(30,0.3),(30,0.5),(30,0.7)]:
    src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n,d,seed=12345))
    print(f"\nER n={n} d={d} edges={src.number_of_edges()} -> P6")
    trace(src, P6, seed=0)

print("\n--- coarse_target sweep on ER30 d0.5 ---")
src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(30,0.5,seed=12345))
for ct in [4, 10, 15, 20]:
    print(f"coarse_target={ct}:")
    trace(src, P6, seed=0, coarse_target=ct)
