"""
docs/paper2/data/emergence_check.py
====================================
The s3.35 emergence check: ONE configuration (stair readout + diagonal
alignment + optional order-swaps), every cell class, no topology detection.
Pre-registered bars in attraction.md (K100 routed <= 11.2 primary; turan
block emergence via swaps; K140 / spin_glass no regression).

Run:  .venv/bin/python docs/paper2/data/emergence_check.py
"""
import time

import networkx as nx
import dwave_networkx as dnx
import minorminer as mm
import numpy as np

from ember_qc.load_graphs import load_graph
from ember_qc.algorithms.factored.field import (
    TileGrid, alternate_arrange, derive_bars_stair, stair_energy,
    stair_step, wire_seeds_iv, wire_seeds_matched)
import time as _time
from ember_qc.algorithms.factored.placement import (
    source_positions, target_layout)
from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.embedding_backend import build_adjacency

target = dnx.pegasus_graph(16)
grid = TileGrid(target, target_layout(target))
adj = build_adjacency(target)
T_edges = list(target.edges())
bounds = (grid.W, grid.H)


def cell(name, src, swaps=0, insert=0, init="spectral", exact=False):
    src = nx.convert_node_labels_to_integers(src)
    nodes = sorted(src.nodes())
    src_adj = {v: sorted(src.neighbors(v)) for v in nodes}
    if init == "random":
        rng = np.random.default_rng(1234)
        tp = {v: np.array([1.5 + 13.0 * rng.random(),
                           1.5 + 13.0 * rng.random()]) for v in nodes}
    else:
        cent0 = source_positions(src, np.zeros(2), np.ones(2))
        tp = {v: np.array([7.5, 7.5]) + (grid.to_tile(cent0[v])
              - grid.to_tile(np.array([0.5, 0.5]))) * 0.3 for v in cent0}
    tp = stair_step(tp, src_adj, eta=0.3)
    t0 = _time.time()
    tp_noins, _ = alternate_arrange(tp, src_adj, grid, iters=8,
                                    readout="stair", seed=0)
    t_arr = _time.time() - t0
    t0 = _time.time()
    tp, info = alternate_arrange(tp, src_adj, grid, iters=8,
                                 readout="stair", swap_sweeps=swaps,
                                 swap_temp=0.5, seed=0,
                                 insert_sweeps=insert)
    t_full = _time.time() - t0
    t_ins = max(0.0, t_full - t_arr)
    sep = ""
    if nx.is_bipartite(src):
        import networkx.algorithms.bipartite as bp
        blkA, blkB = bp.sets(src)
        order = sorted(nodes, key=lambda v: (float(tp[v][1]), v))
        rk = {v: i for i, v in enumerate(order)}
        gap = abs(np.mean([rk[v] for v in blkA])
                  - np.mean([rk[v] for v in blkB]))
        sep = f" blocksep={gap:.1f}/{len(nodes)/2:.0f}"
    bars = derive_bars_stair(tp, src_adj, bounds=bounds)
    if exact:
        t0 = _time.time()
        seeds, sat, tot = wire_seeds_matched(grid, tp, bars, src_adj)
        t_match = _time.time() - t0
        satmsg = f" designated={sat}/{tot} t_match={t_match:.2f}s"
    else:
        seeds = wire_seeds_iv(grid, tp, bars)
        _s2, sat, tot = wire_seeds_matched(grid, tp, bars, src_adj, sweeps=0)
        satmsg = f" designated={sat}/{tot} (greedy)"
    n = len(nodes)
    seed_acl = sum(len(c) for c in seeds.values()) / len(seeds)
    conn = sum(1 for v, c in seeds.items()
               if nx.is_connected(target.subgraph(c)))
    edges = list(src.edges())
    cov = sum(1 for (u, v) in edges
              if any(b in adj.get(a, ()) for a in seeds[u] for b in seeds[v]))
    acls = []
    for rs in (0, 1, 2):
        emb = mm.find_embedding(src, T_edges, initial_chains=seeds,
                                chainlength_patience=0, random_seed=rs,
                                timeout=60)
        if not emb:
            acls.append(None)
            continue
        emb = spur_prune(emb, src_adj, adj)
        pol = mm.find_embedding(src, T_edges, initial_chains=emb,
                                skip_initialization=True, random_seed=rs,
                                timeout=60)
        acls.append(round(sum(len(c) for c in pol.values()) / len(pol), 2)
                    if pol else None)
    ok = [a for a in acls if a is not None]
    mean = f"{sum(ok)/len(ok):.2f}" if ok else "FAIL"
    print(f"{name} init={init} insert={insert} exact={exact}: "
          f"E={stair_energy(tp, src_adj):.0f} "
          f"assigned={info['assigned']} seedACL={seed_acl:.1f} "
          f"conn={conn}/{n} cov={cov}/{len(edges)} ACLs={acls} mean={mean}"
          f"{sep}{satmsg} t_arr={t_arr:.2f}s t_ins={t_ins:.2f}s",
          flush=True)


for exact in (False, True):
    cell("K100", nx.complete_graph(100), insert=8, exact=exact)
    cell("K140", nx.complete_graph(140), insert=8, exact=exact)
    cell("turan_n162", load_graph(2647), insert=8, exact=exact)
    cell("spin_glass_n163", load_graph(37309), insert=8, exact=exact)
print("done-emergence", flush=True)
