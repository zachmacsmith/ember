"""
docs/paper2/data/restrict_smoke.py
===================================
The bar_domains handoff smoke after the fork's restrict_chains fixes
(notes s3.60). Diagnostic only, no pre-registered bars: records that the
formerly-hanging configurations terminate cleanly and that the parked
seeds+domains handoff embeds within domains. Recorded result of the
initial run (2026-08-03, single seed, load ~60): unseeded restricted
K100/P16 fails fast and clean at margins 1-3 (over-constrained without
seeds — correct best-effort behavior, formerly a hang); seeded+restricted
K100/P16 embeds legally within domains at margin 2 (12.72, 23.6 s) and
margin 3 (11.81, 14.0 s — better than the s3.58 P16 board att 13.14 /
mm 14.09, a single-seed diagnostic, NOT a claim); K60 margin 2 in 1.6 s.
The real strip-minorminer-down probe is its own future round.

Run:  nohup .venv/bin/python docs/paper2/data/restrict_smoke.py \
        > docs/paper2/data/restrict_smoke.log 2>&1 &
"""
import sys, time
import networkx as nx
import numpy as np
import dwave_networkx as dnx
from ember_qc.algorithms.factored.field import (
    TileGrid, alternate_arrange, bar_domains, derive_bars_stair,
    stair_step, wire_seeds_iv)
from ember_qc.algorithms.factored.placement import target_layout, source_positions
from ember_qc.algorithms.minorminer_forked import _load_fork
fork = _load_fork()

def setup(n, tgt, grid, margin):
    src = nx.complete_graph(n)
    adj = {v: [u for u in range(n) if u != v] for v in range(n)}
    pos = target_layout(tgt)
    coords = np.array(list(pos.values()))
    cent = source_positions(src, coords.min(axis=0), coords.max(axis=0))
    tp = {v: grid.to_tile(p) for v, p in cent.items()}
    for _ in range(8):
        tp = stair_step(tp, adj, eta=0.5)
    tp, _ = alternate_arrange(tp, adj, grid, iters=8, kappa=13.0)
    bars = derive_bars_stair(tp, adj, kappa=13.0, bounds=(grid.W, grid.H))
    doms = bar_domains(grid, tp, bars, adj, kappa=13.0, margin=margin)
    seeds = wire_seeds_iv(grid, tp, bars)
    return src, doms, seeds


tgt = dnx.pegasus_graph(16)
grid = TileGrid(tgt, target_layout(tgt))
edges = list(tgt.edges())
for n, margin, seeded in ((100, 1, False), (100, 2, False), (100, 3, False),
                          (100, 2, True), (100, 3, True), (60, 2, True)):
    src, doms, seeds = setup(n, tgt, grid, margin)
    kw = dict(restrict_chains=doms, chainlength_patience=10,
              random_seed=0, timeout=30)
    if seeded:
        kw["initial_chains"] = {v: c for v, c in seeds.items() if v in doms}
    t0 = time.perf_counter()
    try:
        emb = fork.find_embedding(src, edges, **kw)
    except Exception as exc:
        print(f"n={n} m={margin} seeded={seeded}: EXC {str(exc)[:40]} "
              f"({time.perf_counter()-t0:.1f}s)", flush=True)
        continue
    dt = time.perf_counter() - t0
    ok = bool(emb)
    acl = round(sum(len(c) for c in emb.values()) / len(emb), 2) if ok else None
    out = (sum(1 for v, c in emb.items()
               if v in doms and not set(c) <= set(doms[v])) if ok else "-")
    print(f"n={n} m={margin} seeded={seeded}: {dt:.1f}s legal={ok} acl={acl} "
          f"outside={out}", flush=True)
print("done-restrict-smoke", flush=True)
