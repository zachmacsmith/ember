"""Apples-to-apples on the SAME random sample of test graphs:
  single MM  vs  best-of-8 cold MM  vs  learned-vae (which the analysis showed =
  best-of-8 MM from a constant central seed). If vae ~= best-of-8 cold MM, the
  'learning' contributes nothing beyond the best-of-K wrapper."""
import warnings; warnings.filterwarnings("ignore")
import json, os, random, statistics as st
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import networkx as nx
import dwave_networkx as dnx

os.environ["EMBER_LEARN_CKPT_DIR"] = os.path.abspath("ckpts")
N = 120
_EDGES = None

def _init():
    global _EDGES
    import warnings as w; w.filterwarnings("ignore")
    import ember_qc, ember_qc_learn  # noqa  (register learned-vae)
    _EDGES = list(dnx.pegasus_graph(6).edges())

def _acl(e): return sum(len(c) for c in e.values())/len(e) if e else None

def _run(task):
    import minorminer
    from ember_qc.registry import get_algorithm
    rec, s = task
    H = nx.Graph(); H.add_nodes_from(range(rec["n"]))
    H.add_edges_from((u, v) for u, v in rec["edges"])
    o = {"id": rec["id"], "n": rec["n"], "seed": s}
    e = minorminer.find_embedding(H, _EDGES, random_seed=s, timeout=20, verbose=0)
    o["single"] = _acl(e)
    accs = []
    for i in range(8):
        e = minorminer.find_embedding(H, _EDGES, random_seed=s*8 + i, timeout=20, verbose=0)
        a = _acl(e)
        if a: accs.append(a)
    o["bo8"] = min(accs) if accs else None
    P6 = dnx.pegasus_graph(6)
    r = get_algorithm("learned-vae").embed(H, P6, timeout=20, seed=s) or {}
    o["vae"] = _acl(r.get("embedding"))
    return o

def main():
    recs = [json.loads(l) for l in open("data/learn/test.jsonl")]
    recs = [r for r in recs if r.get("labels", {}).get("pegasus_6", {}).get("embedding")]
    random.Random(7).shuffle(recs)
    recs = recs[:N]
    tasks = [(r, s) for r in recs for s in range(3)]
    print(f"{len(recs)} random test graphs x 3 seeds (sizes {min(r['n'] for r in recs)}-{max(r['n'] for r in recs)})", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=8, initializer=_init) as ex:
        for r in ex.map(_run, tasks, chunksize=2):
            rows.append(r)
    def stat(key):
        vals = [r[key] for r in rows if r.get(key)]
        perg = defaultdict(list)
        for r in rows:
            if r.get(key): perg[r["id"]].append(r[key])
        return st.mean(vals), st.mean([st.pstdev(v) for v in perg.values() if len(v) > 1])
    print(f"\n{'method':26s}{'mean ACL':>10s}{'std/seed':>10s}")
    for k, lab in [("single", "single MM"), ("bo8", "best-of-8 cold MM"), ("vae", "learned-vae")]:
        m, s = stat(k); print(f"{lab:26s}{m:>10.3f}{s:>10.4f}")
    # head-to-head: vae vs best-of-8 cold MM, per graph
    pv = {r["id"]: [] for r in rows}; pb = {r["id"]: [] for r in rows}
    for r in rows:
        if r.get("vae"): pv[r["id"]].append(r["vae"])
        if r.get("bo8"): pb[r["id"]].append(r["bo8"])
    diffs = [st.mean(pv[g]) - st.mean(pb[g]) for g in pv if pv[g] and pb[g]]
    wins = sum(1 for d in diffs if d < -1e-9); ties = sum(1 for d in diffs if abs(d) <= 1e-9)
    print(f"\nvae vs best-of-8 cold MM (per graph): vae better {wins}, tie {ties}, "
          f"worse {len(diffs)-wins-ties}; mean diff {st.mean(diffs):+.4f}")

if __name__ == "__main__":
    main()
