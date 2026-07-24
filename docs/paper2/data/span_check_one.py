"""One-off finalist check for a single span-sweep combo (defaults: the
stock-capacity ak=1 config, which ranks below the derate=0.65 viol=0 ties in
the sweep's violation ordering but carries ~2/3 of their implied bar length).

Run: .venv/bin/python docs/paper2/data/span_check_one.py [ak eta thr derate]
"""
import sys
import numpy as np
import networkx as nx
import dwave_networkx as dnx
import minorminer as mm

from ember_qc.algorithms.factored.field import (
    PoissonField, TileGrid, assign_rows_cols, bar_force_iv, bar_widths,
    deposit_bars, derive_bars, span_energy, span_step, wire_seeds_iv)
from ember_qc.algorithms.factored.placement import (
    source_positions, target_layout)
from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.embedding_backend import build_adjacency

n = 100
ak, eta, thr, derate = ((int(sys.argv[1]), float(sys.argv[2]),
                         float(sys.argv[3]), float(sys.argv[4]))
                        if len(sys.argv) > 4 else (1, 0.3, 2.0, 1.0))

target = dnx.pegasus_graph(16)
grid = TileGrid(target, target_layout(target))
adj = build_adjacency(target)
T_edges = list(target.edges())
src = nx.complete_graph(n)
src_adj = {v: [u for u in range(n) if u != v] for v in range(n)}
cent0 = source_positions(src, np.zeros(2), np.ones(2))
saved_cap = grid.cap.copy()
bounds = (grid.W, grid.H)

pf = PoissonField(grid, hinge_w=1.0, mu_alpha=0.0)
grid.cap = saved_cap * derate
tp = {v: np.array([7.5, 7.5]) +
      (grid.to_tile(cent0[v]) - grid.to_tile(np.array([0.5, 0.5]))) * 0.3
      for v in cent0}
for step in range(300):
    tp = span_step(tp, src_adj, eta=eta)
    if step >= 50 and (step - 50) % ak == 0:
        bars = derive_bars(tp, src_adj, bounds=bounds)
        tp, _ = assign_rows_cols(tp, bar_widths(bars), grid, threshold=thr)
    bars = derive_bars(tp, src_adj, bounds=bounds)
    demand = deposit_bars(grid, tp, bars)
    psi = pf.potential(demand)
    dp = bar_force_iv(grid, psi, tp, bars, scale=0.5)
    tp = {v: tp[v] + dp[v] for v in tp}
grid.cap = saved_cap

bars = derive_bars(tp, src_adj, bounds=bounds)
demand = deposit_bars(grid, tp, bars)
viol = float(np.maximum(0.0, demand - grid.cap).sum())
print(f"combo ak={ak} eta={eta} thr={thr} derate={derate}: "
      f"E={span_energy(tp, src_adj):.0f} viol={viol:.0f}")

seeds = wire_seeds_iv(grid, tp, bars)
widths = bar_widths(bars)
unseeded = sum(1 for v in tp
               if max(widths[v]) >= 1.0 and len(seeds.get(v, [])) <= 1)
emb = mm.find_embedding(src, T_edges, initial_chains=seeds,
                        chainlength_patience=0, random_seed=0, timeout=60)
if not emb:
    print(f"unseeded={unseeded} -> route FAILED")
else:
    emb = spur_prune(emb, {v: sorted(src.neighbors(v)) for v in src}, adj)
    legal = sum(len(c) for c in emb.values()) / len(emb)
    pol = mm.find_embedding(src, T_edges, initial_chains=emb,
                            skip_initialization=True, random_seed=0,
                            timeout=60)
    acl = (sum(len(c) for c in pol.values()) / len(pol)) if pol else None
    print(f"unseeded={unseeded} -> legal ACL={legal:.2f}, polished "
          f"ACL={acl:.2f} (cross-emergent 13.46, mm ~13.6, template 9.78)")
