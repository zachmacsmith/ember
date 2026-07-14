"""Where does stock minorminer spend its time at scale? Zero-code decomposition
using MM's own knobs on Pegasus-16 (5640 qubits), ER sources at avg degree ~10.

Arms per (n, seed):
  default   -- stock everything (tries=10, chainlength_patience=10, threads=1)
  legalize  -- chainlength_patience=0 (no shortening phase) -> splits
               legalization time vs shortening time
  threads4  -- threads=4: parallelizes ONLY the per-neighbor root-distance
               Dijkstras -> Amdahl share of the root-selection floods
  threads16 -- same, more cores
"""
import csv, os, time
import networkx as nx
import dwave_networkx as dnx
import minorminer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mm_time_budget.csv")
T16 = list(dnx.pegasus_graph(16).edges())
DEG = 10.0

rows = []
for n in (60, 100, 140, 180, 220):
    d = DEG / (n - 1)
    src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, d, seed=12345))
    S = list(src.edges())
    for seed in (0, 1):
        for arm, kw in [("default", {}),
                        ("legalize", {"chainlength_patience": 0}),
                        ("threads4", {"threads": 4}),
                        ("threads16", {"threads": 16})]:
            t0 = time.perf_counter()
            emb = minorminer.find_embedding(S, T16, random_seed=seed, timeout=300, **kw)
            dt = time.perf_counter() - t0
            ok = bool(emb)
            acl = sum(len(c) for c in emb.values()) / len(emb) if ok else None
            rows.append(dict(n=n, d=round(d, 4), seed=seed, arm=arm,
                             success=ok, time=round(dt, 3),
                             acl=round(acl, 3) if acl else None))
            print(f"n={n} seed={seed} {arm:9s}: {'ok' if ok else 'FAIL':4s} "
                  f"{dt:7.2f}s acl={acl if acl else '-'}", flush=True)

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("wrote", OUT)
