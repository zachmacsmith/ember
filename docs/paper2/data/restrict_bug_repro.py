import sys, time
import networkx as nx, dwave_networkx as dnx, minorminer
import numpy as np
from ember_qc.algorithms.factored.field import (TileGrid, derive_bars,
    bar_domains, alternate_arrange)
from ember_qc.algorithms.factored.placement import target_layout, source_positions

n = int(sys.argv[1]); trial = int(sys.argv[2])
tgt = dnx.pegasus_graph(16)
grid = TileGrid(tgt, target_layout(tgt))
src = nx.complete_graph(n)
src_adj = {v: [u for u in range(n) if u != v] for v in range(n)}
cent0 = source_positions(src, np.zeros(2), np.ones(2))
tp = {v: np.array([7.5, 7.5]) + (grid.to_tile(cent0[v])
      - grid.to_tile(np.array([0.5, 0.5]))) * 0.3 for v in cent0}
tp, info = alternate_arrange(tp, src_adj, grid, iters=8, derate=0.85)
bars = derive_bars(tp, src_adj, bounds=(grid.W, grid.H))
doms = bar_domains(grid, tp, bars, src_adj, margin=1)
t0 = time.time()
emb = minorminer.find_embedding(src, list(tgt.edges()), restrict_chains=doms,
                                chainlength_patience=0, random_seed=trial,
                                timeout=20)
print(f"n={n} trial={trial}: {time.time()-t0:.1f}s legal={bool(emb)} "
      f"legalACL={round(sum(map(len,emb.values()))/len(emb),2) if emb else None}",
      flush=True)
