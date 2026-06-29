"""Larger-instance spot check (the multilevel thesis claims gains grow at scale)."""
import warnings, time, statistics as st
warnings.filterwarnings("ignore")
import networkx as nx
import dwave_networkx as dnx
import minorminer

import ember_qc.algorithms.multilevel as M
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding

SEEDS = [0,1,2,3]
P6 = dnx.pegasus_graph(6)
adj = build_adjacency(P6)
algo = M.Multilevel()

def acl(e): return sum(len(c) for c in e.values())/len(e)

print(f"{'cell':16s} {'algo':12s} {'succ':>5s} {'ACL mean±std':>16s} {'maxACL':>7s} {'t(s)':>6s} {'lv':>3s}")
for (n,d,to) in [(50,0.2,60),(70,0.15,60),(90,0.12,60)]:
    src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n,d,seed=12345))
    for name in ["minorminer","multilevel"]:
        accs, ts, ok, mx, lv = [], [], 0, [], None
        for s in SEEDS:
            t0=time.perf_counter()
            if name=="minorminer":
                raw=minorminer.find_embedding(src,list(P6.edges()),random_seed=s,timeout=to,verbose=0)
                emb={int(k):[int(q) for q in v] for k,v in raw.items()} if raw else {}
            else:
                r=algo.embed(src,P6,timeout=to,seed=s); emb=r["embedding"]
                lv=(r.get("metadata") or {}).get("levels")
            ts.append(time.perf_counter()-t0)
            if emb and is_valid_embedding(emb,src,P6,adj=adj):
                ok+=1; accs.append(acl(emb)); mx.append(max(len(c) for c in emb.values()))
        m=f"{st.mean(accs):.3f}±{st.pstdev(accs):.3f}" if len(accs)>1 else (f"{accs[0]:.3f}" if accs else "--")
        print(f"ER_n{n}_d{d:<4} {name:12s} {ok}/{len(SEEDS):<3d} {m:>16s} {(st.mean(mx) if mx else 0):>7.1f} {st.mean(ts):>6.1f} {str(lv):>3s}")
    print()
