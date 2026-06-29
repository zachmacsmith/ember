"""Definitive fair, equal-budget comparison on the test set:
  cold single MM | cold best-of-8 MM | Procrustes single | Procrustes best-of-8 (perturbed).
Tests both the single-shot value and whether a LEARNED layout makes restarts smarter."""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, torch, networkx as nx, dwave_networkx as dnx, statistics as st
from concurrent.futures import ProcessPoolExecutor
from torch_geometric.loader import DataLoader
from ember_qc_learn.dataset import EmbedDataset
from ember_qc_learn.features import target_geometry, SOURCE_FEATURE_DIM
from ember_qc_learn.models.base import build_model
import ember_qc_learn.models.gnn_seed  # noqa

dev=torch.device("cuda" if torch.cuda.is_available() else "cpu")
def ploss_g(p,y):
    pc=p-p.mean(0,keepdim=True); yc=y-y.mean(0,keepdim=True)
    U,S,Vh=torch.linalg.svd(pc.t()@yc); R=U@Vh; s=S.sum()/((pc**2).sum()+1e-8)
    return ((s*(pc@R)-yc)**2).mean()
def ploss(model,batch):
    P=model(batch); Y=batch.y; b=batch.batch
    ls=[ploss_g(P[b==g],Y[b==g]) for g in b.unique() if (b==g).sum()>=3]
    return torch.stack(ls).mean() if ls else P.sum()*0

geo=target_geometry(dnx.pegasus_graph(6),"pegasus_6")
tr=EmbedDataset("data/learn/train.jsonl","pegasus_6",geo=geo)
te=EmbedDataset("data/learn/test.jsonl","pegasus_6",geo=geo)
torch.manual_seed(0)
model=build_model("gnn-seed",in_dim=SOURCE_FEATURE_DIM,hidden=160,layers=5,conv="sage",dropout=0.1).to(dev)
opt=torch.optim.Adam(model.parameters(),lr=2e-3,weight_decay=1e-5)
ld=DataLoader(tr.examples,batch_size=32,shuffle=True)
for ep in range(90):
    model.train()
    for bt in ld: bt=bt.to(dev); opt.zero_grad(); l=ploss(model,bt); l.backward(); opt.step()
print("Procrustes trained (90ep)",flush=True)
# predict layouts for all test graphs (min-max normalized [0,1])
model.eval(); layouts={}
for d,m in zip(te.examples,te.meta):
    bt=next(iter(DataLoader([d],batch_size=1))).to(dev)
    with torch.no_grad(): P=model(bt).cpu().numpy()
    lo,hi=P.min(0),P.max(0); span=np.where(hi-lo>1e-6,hi-lo,1.0)
    layouts[m["id"]]=((P-lo)/span)

QC=geo["coords"]; QN=geo["qubit_nodes"]; _EDGES=None
def _init():
    global _EDGES
    import warnings as w; w.filterwarnings("ignore")
    _EDGES=list(dnx.pegasus_graph(6).edges())
def _acl(e): return sum(len(c) for c in e.values())/len(e) if e else None
def _seed(Pn, snodes, jitter, rng):
    from ember_qc_learn.decode import coords_to_qubit_scores, seed_chains_from_scores
    L=0.5+(Pn-0.5)*0.3
    if jitter: L=L+rng.normal(0,0.04,L.shape)
    return seed_chains_from_scores(coords_to_qubit_scores(L,QC),QN,snodes)
def _run(task):
    import minorminer
    rec, meth = task
    H=nx.Graph(); H.add_nodes_from(range(rec["n"])); H.add_edges_from((u,v) for u,v in rec["edges"])
    snodes=sorted(H.nodes()); Pn=np.array(rec["_layout"])
    def mm(seed,init=None):
        kw=dict(random_seed=seed,timeout=25,verbose=0)
        if init: kw["initial_chains"]=init
        return _acl(minorminer.find_embedding(H,_EDGES,**kw))
    rng=np.random.default_rng(0)
    if meth=="cold1": return (rec["id"],meth,mm(0))
    if meth=="cold8": return (rec["id"],meth,min([a for a in (mm(i) for i in range(8)) if a] or [None]))
    if meth=="proc1": return (rec["id"],meth,mm(0,_seed(Pn,snodes,False,rng)))
    if meth=="proc8":
        accs=[mm(i,_seed(Pn,snodes,i>0,np.random.default_rng(i))) for i in range(8)]
        return (rec["id"],meth,min([a for a in accs if a] or [None]))

recs=[json.loads(l) for l in open("data/learn/test.jsonl")]
recs=[r for r in recs if r.get("labels",{}).get("pegasus_6",{}).get("embedding")]
for r in recs: r["_layout"]=layouts[r["id"]].tolist()
tasks=[(r,m) for r in recs for m in ["cold1","cold8","proc1","proc8"]]
print(f"{len(recs)} test graphs x 4 methods",flush=True)
out=[]
with ProcessPoolExecutor(max_workers=28,initializer=_init) as ex:
    for r in ex.map(_run,tasks,chunksize=2): out.append(r)
perg={}; agg={}
for gid,meth,a in out:
    if a: agg.setdefault(meth,[]).append(a); perg.setdefault((gid),{})[meth]=a
print(f"\n{'method':24s}{'mean ACL':>10s}")
for m,lab in [("cold1","single cold MM"),("cold8","best-of-8 cold MM"),("proc1","Procrustes single"),("proc8","Procrustes best-of-8")]:
    print(f"{lab:24s}{st.mean(agg[m]):>10.3f}")

# significance: paired per-graph, Procrustes vs cold (single and best-of-8)
from scipy.stats import wilcoxon
def paired(mA, mB):
    pairs=[(perg[g][mA], perg[g][mB]) for g in perg if mA in perg[g] and mB in perg[g]]
    a=[x for x,_ in pairs]; b=[y for _,y in pairs]
    win=sum(1 for x,y in pairs if x<y-1e-9); tie=sum(1 for x,y in pairs if abs(x-y)<=1e-9); loss=len(pairs)-win-tie
    try: p=wilcoxon([x-y for x,y in pairs]).pvalue
    except Exception: p=float('nan')
    return len(pairs), win, tie, loss, p
for mA,mB,lab in [("proc1","cold1","single-shot: Procrustes vs cold MM"),
                  ("proc8","cold8","best-of-8: Procrustes vs cold MM")]:
    n,w,t,l,p=paired(mA,mB)
    print(f"{lab}: n={n} Procrustes-wins={w} tie={t} loss={l}  Wilcoxon p={p:.2e}")
