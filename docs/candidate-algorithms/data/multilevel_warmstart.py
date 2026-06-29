"""Does a multilevel-projected layout warm-start beat cold minorminer? (scratch)"""
import warnings, time, statistics as st
warnings.filterwarnings("ignore")
import networkx as nx
import dwave_networkx as dnx
import minorminer

import ember_qc.algorithms.multilevel as M
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding


def project_layout(src, target, adj, all_q, seed, coarse_target=8):
    """Full V-cycle projection (Voronoi split every level, NO edge repair) ->
    a disjoint+connected level-0 layout to warm-start MM."""
    import random
    tele = M._Tele()
    rng = random.Random((seed*2654435761+12345)&0xFFFFFFFF)
    graphs, cmaps = M._build_hierarchy(src, rng, coarse_target, 8, None)
    emb = M._base_embed(graphs[-1], target, adj, seed, 4, None, tele)
    if emb is None:
        return None, len(graphs)-1
    for i in range(len(graphs)-2, -1, -1):
        fine = M._interpolate(emb, cmaps[i], adj, all_q)
        if fine is None:
            return None, len(graphs)-1
        emb = fine
    return emb, len(graphs)-1


def acl(emb):
    return sum(len(c) for c in emb.values())/len(emb) if emb else 0.0


def run(src, target, seed, timeout=10.0):
    adj = build_adjacency(target); all_q = set(adj)
    edgelist = list(target.edges())
    # cold MM
    t0=time.perf_counter()
    cold = minorminer.find_embedding(src, edgelist, random_seed=seed, timeout=timeout, verbose=0)
    tc=time.perf_counter()-t0
    cold = {int(k):[int(q) for q in v] for k,v in cold.items()} if cold else {}
    cold_valid = bool(cold) and is_valid_embedding(cold, src, target, adj=adj)
    # warm: project then MM initial_chains
    t0=time.perf_counter()
    layout, lv = project_layout(src, target, adj, all_q, seed)
    if layout is None:
        warm, warm_valid, tw = {}, False, time.perf_counter()-t0
    else:
        try:
            warm = minorminer.find_embedding(src, edgelist, random_seed=seed,
                    timeout=timeout, verbose=0, initial_chains=layout)
        except Exception as e:
            warm = {}
        tw=time.perf_counter()-t0
        warm = {int(k):[int(q) for q in v] for k,v in warm.items()} if warm else {}
        warm_valid = bool(warm) and is_valid_embedding(warm, src, target, adj=adj)
    return (cold_valid, acl(cold) if cold_valid else None, tc,
            warm_valid, acl(warm) if warm_valid else None, tw, lv,
            acl(layout) if layout else None)


P6 = dnx.pegasus_graph(6)
print(f"{'cell':18s} {'cold':>16s} {'warm(proj+MM)':>18s} {'layoutACL':>9s} {'lv':>3s}")
for (n,d) in [(20,0.3),(20,0.5),(20,0.7),(30,0.3),(30,0.5),(30,0.7)]:
    src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n,d,seed=12345))
    cvs, cas, was, wvs, wac, lac = [], [], [], [], [], []
    lv=None
    for s in [0,1,2]:
        cv,ca,tc,wv,wa,tw,lvl,la = run(src,P6,s)
        cvs.append(cv);
        if ca: cas.append(ca)
        wvs.append(wv)
        if wa: was.append(wa)
        if la: lac.append(la)
        lv=lvl
    cold_acl = f"{st.mean(cas):.2f}" if cas else "--"
    warm_acl = f"{st.mean(was):.2f}" if was else "--"
    lay_acl = f"{st.mean(lac):.2f}" if lac else "--"
    print(f"ER_n{n}_d{d:<4}  {sum(cvs)}/3 acl={cold_acl:>5s}   {sum(wvs)}/3 acl={warm_acl:>5s}     {lay_acl:>9s} {str(lv):>3s}")
