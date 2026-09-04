"""
docs/paper2/data/contract_probe_routed.py
==========================================
Phase B of the contraction Stage-1 probe (screen verdict: gate passed on
paper but the excluded-volume wall LEAKS via arm growth on dense cells —
growth_overfill 60-140 — so dense low-E settlements are partly fictional;
sparse/multi-patch settlements are clean, grow ~0. This phase measures
what the layouts are worth to the router either way).

Finalist arm (Phase A): spectral-spread / deg_weight=False / cycles=4.
Z12 primary: all cells x {contract, mm, mm2} x 3 seeds (fresh baselines —
none exist for Zephyr). P16 continuity: contract only, vs refine_probe's
recorded mm/mm2. 60 s, 8 niced workers.

Run:  nohup .venv/bin/python docs/paper2/data/contract_probe_routed.py \
        > docs/paper2/data/contract_probe_routed.log 2>&1 &
"""

import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "contract_probe_routed.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

CELLS = {
    "K100": None, "K140": None, "ER100_d10": None,
    "turan_n162": 2647, "spin_glass_n163": 37309,
    "wsc_c3_sz32_n96": 33571, "wsc_c3_sz64_n192": 33574,
    "regular_n316": 13096, "ws_n486": 17188,
}


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    tname, cell, gid, arm, seed = job
    os.nice(10)
    import numpy as np
    import networkx as nx
    import dwave_networkx as dnx
    import minorminer as mm

    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if tname == "Z12"
              else dnx.pegasus_graph(16))
    T_edges = list(target.edges())
    t0 = time.perf_counter()
    if arm in ("mm", "mm2"):
        s = seed if arm == "mm" else seed * 7919 + 7777
        emb = mm.find_embedding(src, T_edges, random_seed=s,
                                timeout=TIMEOUT) or {}
    else:
        from ember_qc.algorithms.factored.field import (
            TileGrid, contract_layout, derive_bars_stair, wire_seeds_iv)
        from ember_qc.algorithms.factored.placement import (
            source_positions, target_layout)
        from ember_qc.algorithms.factored.polish import spur_prune
        from ember_qc.embedding_backend import build_adjacency
        grid = TileGrid(target, target_layout(target))
        nodes = sorted(src.nodes())
        src_adj = {v: sorted(src.neighbors(v)) for v in nodes}
        cent = source_positions(src, np.zeros(2), np.ones(2))
        lo = np.array([0.5, 0.5])
        hi = np.array([grid.W - 1.5, grid.H - 1.5])
        pos = {v: lo + (np.asarray(cent[v]) - 0.1) / 0.8 * (hi - lo)
               for v in nodes}
        pos, info = contract_layout(pos, src_adj, grid, steps=300,
                                    deg_weight=False, cycles=4)
        bars = derive_bars_stair(pos, src_adj, bounds=(grid.W, grid.H))
        seeds_c = wire_seeds_iv(grid, pos, bars)
        adj = build_adjacency(target)
        emb = mm.find_embedding(src, T_edges, initial_chains=seeds_c,
                                chainlength_patience=0, random_seed=seed,
                                timeout=max(5.0, TIMEOUT * 0.4)) or {}
        if emb:
            emb = spur_prune(emb, src_adj, adj,
                             deadline=t0 + TIMEOUT)
            emb = mm.find_embedding(
                src, T_edges, initial_chains=emb,
                skip_initialization=True, random_seed=seed,
                timeout=max(1.0, TIMEOUT - (time.perf_counter() - t0))) \
                or emb
    return dict(target=tname, cell=cell, arm=arm, seed=seed,
                final_acl=round(sum(len(c) for c in emb.values()) / len(emb),
                                3) if emb else None,
                time=round(time.perf_counter() - t0, 1))


def main():
    jobs = [("Z12", cell, gid, arm, s) for cell, gid in CELLS.items()
            for arm in ("contract", "mm", "mm2") for s in SEEDS]
    jobs += [("P16", cell, gid, "contract", s)
             for cell, gid in CELLS.items() for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['target']} {row['cell']} {row['arm']} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print("\nsummary (mean over legal seeds; n legal in parens):")
    for tname in ("Z12", "P16"):
        arms = ("contract", "mm", "mm2") if tname == "Z12" else ("contract",)
        for cell in CELLS:
            parts = [f"{tname} {cell:18s}"]
            for arm in arms:
                vals = [r["final_acl"] for r in rows
                        if r["target"] == tname and r["cell"] == cell
                        and r["arm"] == arm and r["final_acl"]]
                parts.append(f"{arm}={sum(vals)/len(vals):.2f}({len(vals)})"
                             if vals else f"{arm}=FAIL(0)")
            print("  ".join(parts))
    print("done-contract-B", flush=True)


if __name__ == "__main__":
    main()
