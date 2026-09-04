"""
docs/paper2/data/refine_probe.py
=================================
Scoring probe for the 2026-07-29 local-interpolation refinements (edge
monotonization / arm-length gating / value-priced insertion). Bars
PRE-REGISTERED in the plan file before any run:

- GUARDS: dense cells reproduce s3.38 within the mm2-measured null (K100
  13.41, K140 18.55 3/3, spin_glass 17.22 3/3, turan 8.40); sparse guards
  within noise of 3.56 / 3.76 / 5.88.
- PAYOFF: wsc c3xK32 gap to mm closes from -1.46 toward <= ~0.5 OR shows no
  improvement (clean patches-too-small verdict); c3xK64 win holds.
- EMERGENCE: random-init turan <= ~8.5 (separate in-process check below).
- WALL-TIME: mono_time small next to the arrange/insertion phase.

Arms: default (refined pipeline), mm (stock), mm2 (stock at a derived seed
— the passthrough noise null, paper3 protocol trick). 3 seeds x 60 s, P16,
8 niced workers.

Run:  nohup .venv/bin/python docs/paper2/data/refine_probe.py \
        > docs/paper2/data/refine_probe.log 2>&1 &
"""

import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "refine_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

CELLS = {
    "K100": None, "K140": None, "ER100_d10": None,
    "turan_n162": 2647, "spin_glass_n163": 37309,
    "regular_n316": 13096, "ws_n486": 17188,
    "wsc_c3_sz32_n96": 33571, "wsc_c5_sz32_n160": 33601,
    "wsc_c8_sz32_n256": 33640, "wsc_c3_sz64_n192": 33574,
}

ARMS = [("default", {}), ("mm", None), ("mm2", "derived")]


def _load_cell(name, gid):
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
    cell, gid, arm, kw, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    src = _load_cell(cell, gid)
    target = dnx.pegasus_graph(16)
    t0 = time.perf_counter()
    if kw is None or kw == "derived":
        import minorminer
        s = seed if kw is None else seed * 7919 + 7777
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=s, timeout=TIMEOUT) or {}
        r = {}
    else:
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
        emb = r.get("embedding") or {}
    return dict(cell=cell, arm=arm, seed=seed,
                final_acl=round(sum(len(c) for c in emb.values()) / len(emb),
                                3) if emb else None,
                rounds=r.get("rounds"),
                time=round(time.perf_counter() - t0, 1),
                diag=str(r.get("diag", "")))


def _random_init_turan():
    """In-process emergence check (s3.36 standard): drive the field layer
    from a RANDOM init on turan_n162, wire-seed, route+polish x3."""
    import numpy as np
    import networkx as nx
    import dwave_networkx as dnx
    import minorminer as mm
    from ember_qc.load_graphs import load_graph
    from ember_qc.algorithms.factored.field import (
        TileGrid, alternate_arrange, derive_bars_stair, stair_step,
        wire_seeds_iv)
    from ember_qc.algorithms.factored.placement import target_layout
    from ember_qc.algorithms.factored.polish import spur_prune
    from ember_qc.embedding_backend import build_adjacency

    src = nx.convert_node_labels_to_integers(load_graph(2647))
    nodes = sorted(src.nodes())
    src_adj = {v: sorted(src.neighbors(v)) for v in nodes}
    target = dnx.pegasus_graph(16)
    grid = TileGrid(target, target_layout(target))
    adj = build_adjacency(target)
    T_edges = list(target.edges())
    rng = np.random.default_rng(1234)
    tp = {v: np.array([1.5 + 13.0 * rng.random(),
                       1.5 + 13.0 * rng.random()]) for v in nodes}
    tp = stair_step(tp, src_adj, eta=0.3)
    tp, info = alternate_arrange(tp, src_adj, grid, iters=8, insert_sweeps=8)
    bars = derive_bars_stair(tp, src_adj, bounds=(grid.W, grid.H))
    seeds = wire_seeds_iv(grid, tp, bars)
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
    print(f"turan-random-init: ACLs={acls} "
          f"mean={sum(ok)/len(ok):.2f} " if ok else "FAIL",
          f"E={info['E'][-1]:.0f} mono_swaps={info['mono_swaps']} "
          f"mono_t={info['mono_time']}s reverts={info['insert_reverts']}",
          flush=True)


def main():
    jobs = [(cell, gid, arm, kw, s) for cell, gid in CELLS.items()
            for s in SEEDS for arm, kw in ARMS]
    rows = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} ({row['time']}s) {row['diag']}",
                  flush=True)
            rows.append(row)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    print("\nsummary (mean over legal seeds; n legal in parens):")
    for cell in CELLS:
        parts = [f"{cell:18s}"]
        for arm, _ in ARMS:
            vals = [r["final_acl"] for r in rows
                    if r["cell"] == cell and r["arm"] == arm
                    and r["final_acl"]]
            parts.append(f"{arm}={sum(vals)/len(vals):.2f}({len(vals)})"
                         if vals else f"{arm}=FAIL(0)")
        print("  ".join(parts))

    _random_init_turan()
    print("done-refine", flush=True)


if __name__ == "__main__":
    main()
