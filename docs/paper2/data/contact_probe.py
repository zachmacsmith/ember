"""
docs/paper2/data/contact_probe.py
==================================
Stage-1 probe of the contact model (s3.45; bars pre-registered in the
plan). Z12 only (junctions honest). Cells span the bridge + the pinned
cell. Contact placement is deterministic; 3 routing seeds. mm/mm2
baselines quoted from contract_probe_routed.csv (same cells/protocol).

Run:  nohup .venv/bin/python docs/paper2/data/contact_probe.py \
        > docs/paper2/data/contact_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "contract_probe_routed.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, gid, seed = job
    os.nice(10)
    import networkx as nx
    import dwave_networkx as dnx
    import minorminer as mm
    from ember_qc.algorithms.factored.contact import (
        contact_place, contact_seeds, junction_caps)
    from ember_qc.algorithms.factored.field import TileGrid
    from ember_qc.algorithms.factored.placement import target_layout
    from ember_qc.algorithms.factored.polish import spur_prune
    from ember_qc.embedding_backend import build_adjacency

    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    grid = TileGrid(target, target_layout(target))
    t0 = time.perf_counter()
    contacts, info = contact_place(src, grid, steps=300, cycles=4)
    J, couplers = junction_caps(grid)
    seeds_c = contact_seeds(src, grid, contacts, couplers)
    place_t = round(time.perf_counter() - t0, 1)
    src_adj = {v: sorted(src.neighbors(v)) for v in sorted(src)}
    adj = build_adjacency(target)
    T_edges = list(target.edges())
    emb = mm.find_embedding(src, T_edges, initial_chains=seeds_c,
                            chainlength_patience=0, random_seed=seed,
                            timeout=TIMEOUT * 0.4) or {}
    if emb:
        emb = spur_prune(emb, src_adj, adj, deadline=t0 + TIMEOUT)
        emb = mm.find_embedding(
            src, T_edges, initial_chains=emb, skip_initialization=True,
            random_seed=seed,
            timeout=max(1.0, TIMEOUT - (time.perf_counter() - t0))) or emb
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, seed=seed, final_acl=acl, place_t=place_t,
                resid=info["residual_overload"], hpwl=info["final_hpwl"])


def main():
    jobs = [(c, g, s) for c, g in CELLS.items() for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} seed {row['seed']}: {row['final_acl']} "
                  f"(place {row['place_t']}s resid {row['resid']} "
                  f"hpwl {row['hpwl']})", flush=True)
            rows.append(row)

    base = {}
    if os.path.exists(BASE):
        with open(BASE) as fh:
            for r in csv.DictReader(fh):
                if r["target"] == "Z12" and r["cell"] in CELLS \
                        and r["arm"] in ("mm", "mm2"):
                    base.setdefault((r["cell"], r["arm"]), []).append(
                        float(r["final_acl"]) if r["final_acl"] else None)

    print("\nsummary (mean over legal seeds; baselines from "
          "contract_probe_routed.csv):")
    for cell in CELLS:
        vals = [r["final_acl"] for r in rows
                if r["cell"] == cell and r["final_acl"]]
        parts = [f"{cell:16s}",
                 f"contact={sum(vals)/len(vals):.2f}({len(vals)})"
                 if vals else "contact=FAIL(0)"]
        for arm in ("mm", "mm2"):
            bv = [x for x in base.get((cell, arm), []) if x is not None]
            parts.append(f"{arm}={sum(bv)/len(bv):.2f}({len(bv)})"
                         if bv else f"{arm}=?")
        print("  ".join(parts))
    print("done-contact", flush=True)


if __name__ == "__main__":
    main()
