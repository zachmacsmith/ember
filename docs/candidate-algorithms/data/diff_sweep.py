import warnings; warnings.filterwarnings('ignore')
import numpy as np, networkx as nx, dwave_networkx as dnx
import minorminer
from ember_qc.algorithms.diffembed import embed_diff_softassign

tgt = dnx.pegasus_graph(6)
insts = [(20,0.5),(30,0.5),(30,0.7)]
refs = {}
for (n,d) in insts:
    s = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n,d,seed=12345))
    mm = minorminer.find_embedding(s, list(tgt.edges()), random_seed=0, timeout=30, verbose=0)
    refs[(n,d)] = (s, round(sum(len(c) for c in mm.values())/len(mm),3))

configs = {
  'A_lock':   dict(init_logit=6.0, lr=0.05, inner_steps=25, n_levels=7, w_cont=0.1, w_load=1.5, w_spread=0.05),
  'B_gentle': dict(init_logit=4.0, lr=0.03, inner_steps=25, n_levels=7, w_cont=0.05, w_load=2.0, w_spread=0.0),
  'C_explore':dict(init_logit=4.0, lr=0.08, inner_steps=30, n_levels=8, w_cont=0.2, w_load=1.0, w_spread=0.1),
}
for cname, cfg in configs.items():
    print(f'### config {cname}: {cfg}')
    for (n,d) in insts:
        s, mmacl = refs[(n,d)]
        for init in ['mm','random']:
            r = embed_diff_softassign(s, tgt, timeout=60, seed=0, return_trace=True, init=init, **cfg)
            emb=r['embedding']; acl=round(sum(len(c) for c in emb.values())/max(1,len(emb)),3) if emb else None
            tt=r["time"]; nvalid=sum(1 for t in r['trace'] if t['valid']); ntot=len(r['trace'])
            acls=[t['acl'] for t in r['trace'] if t['acl'] is not None]
            print(f'  n{n} d{d} MM={mmacl} | init={init:6s} final={acl} valid_levels={nvalid}/{ntot} level_acls={acls} t={tt:.1f}s')
    print()
