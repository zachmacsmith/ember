"""
docs/paper2/data/zephyr_triad.py
=================================
The s3.48 Zephyr diagnosis triad (plan-registered readings, no bars):
Part 1: wire_exact=True on Z12 (the s3.37 matching on the fabric whose
        junction-completeness it assumed; never measured there).
Part 2: template truth — busclique Z12 numbers for our cells.
Part 3: chain shapes — segments-per-chain decomposition of mm's and our
        embeddings (is the single-bend L the right Zephyr shape?).

Run:  nohup .venv/bin/python docs/paper2/data/zephyr_triad.py \
        > docs/paper2/data/zephyr_triad.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "contract_probe_routed.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
PIPE47 = {"K100": 12.21, "ER100_d10": 4.81,
          "turan_n162": 14.03, "spin_glass_n163": 19.85}


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run_exact(job):
    cell, gid, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    r = attract_embed(src, dnx.zephyr_graph(12, 4), timeout=TIMEOUT,
                      seed=seed, wire_exact=True)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, seed=seed, final_acl=acl,
                designated=r.get("diag", {}).get("designated"))


def part1():
    print("===== Part 1: wire_exact=True on Z12", flush=True)
    jobs = [(c, g, s) for c, g in CELLS.items() for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for row in ex.map(_run_exact, jobs):
            print(f"  {row['cell']} seed {row['seed']}: {row['final_acl']} "
                  f"designated={row['designated']}", flush=True)
            rows.append(row)
    base = {}
    if os.path.exists(BASE):
        with open(BASE) as fh:
            for r in csv.DictReader(fh):
                if r["target"] == "Z12" and r["cell"] in CELLS \
                        and r["arm"] in ("mm", "mm2"):
                    base.setdefault((r["cell"], r["arm"]), []).append(
                        float(r["final_acl"]) if r["final_acl"] else None)
    print("  summary:")
    for cell in CELLS:
        vals = [r["final_acl"] for r in rows
                if r["cell"] == cell and r["final_acl"]]
        des = next((r["designated"] for r in rows if r["cell"] == cell
                    and r["designated"]), "?")
        parts = [f"  {cell:16s}",
                 f"exact={sum(vals)/len(vals):.2f}({len(vals)})"
                 if vals else "exact=FAIL(0)",
                 f"pipe47={PIPE47[cell]}", f"designated={des}"]
        for arm in ("mm", "mm2"):
            bv = [x for x in base.get((cell, arm), []) if x is not None]
            parts.append(f"{arm}={sum(bv)/len(bv):.2f}" if bv else f"{arm}=?")
        print("  ".join(parts), flush=True)


def part2():
    print("\n===== Part 2: template truth (busclique on Z12)", flush=True)
    import networkx as nx
    import dwave_networkx as dnx
    from minorminer import busclique
    from ember_qc.algorithms.factored.polish import spur_prune
    from ember_qc.embedding_backend import build_adjacency
    target = dnx.zephyr_graph(12, 4)
    bc = busclique.busgraph_cache(target)
    big = bc.largest_clique()
    print(f"  Z12 K_max = {len(big)}", flush=True)
    adj = build_adjacency(target)
    for k in (100, 140):
        emb = bc.find_clique_embedding(k)
        if not emb:
            print(f"  K{k}: no template", flush=True)
            continue
        acl = sum(len(c) for c in emb.values()) / len(emb)
        print(f"  K{k} template ACL = {acl:.2f}", flush=True)
    # restriction bound for the irregular cells: relabel K_n template
    # chains to source vertices (degree-descending) and spur_prune
    for cell, gid in (("turan_n162", 2647), ("spin_glass_n163", 37309)):
        src = _load(cell, gid)
        n = src.number_of_nodes()
        emb = bc.find_clique_embedding(n)
        if not emb:
            print(f"  {cell}: no K{n} template on Z12", flush=True)
            continue
        order = sorted(src.nodes(),
                       key=lambda v: (-src.degree(v), v))
        chains = {v: list(emb[i]) for i, v in enumerate(order)}
        src_adj = {v: sorted(src.neighbors(v)) for v in src}
        pruned = spur_prune(chains, src_adj, adj,
                            deadline=time.perf_counter() + 60)
        acl = sum(len(c) for c in pruned.values()) / len(pruned)
        print(f"  {cell}: K{n}-restriction template ACL = {acl:.2f}",
              flush=True)


def _segments(chain, wire_of):
    """Decompose a chain into maximal same-wire runs (segment count)."""
    wires = {}
    for q in chain:
        w = wire_of.get(q)
        if w is not None:
            wires.setdefault(w, 0)
        wires[w] = wires.get(w, 0) + 1
    return len(wires), (np.mean(list(wires.values())) if wires else 0.0)


def part3():
    print("\n===== Part 3: chain shapes on Z12 (segments per chain)",
          flush=True)
    import networkx as nx
    import dwave_networkx as dnx
    import minorminer as mm
    from ember_qc.algorithms.factored.field import _tile_orient
    from ember_qc.algorithms.factored import attract_embed
    target = dnx.zephyr_graph(12, 4)
    tio = _tile_orient(target)
    # wire identity: (u, line) with line = w; sub k folds into the wire
    wire_of = {}
    for q, (tx, ty, u, k) in tio.items():
        line = ty if u == 1 else tx
        wire_of[q] = (u, line, k)
    T_edges = list(target.edges())
    for cell, gid in CELLS.items():
        src = _load(cell, gid)
        for arm in ("mm", "ours"):
            if arm == "mm":
                emb = mm.find_embedding(src, T_edges, random_seed=0,
                                        timeout=TIMEOUT) or {}
            else:
                r = attract_embed(src, target, timeout=TIMEOUT, seed=0)
                emb = r.get("embedding") or {}
            if not emb:
                print(f"  {cell:16s} {arm}: FAIL", flush=True)
                continue
            segs = []
            seglens = []
            lens = []
            for c in emb.values():
                ns, ml = _segments(c, wire_of)
                segs.append(ns)
                seglens.append(ml)
                lens.append(len(c))
            print(f"  {cell:16s} {arm}: ACL={np.mean(lens):.2f} "
                  f"segs/chain mean={np.mean(segs):.2f} "
                  f"med={np.median(segs):.0f} max={max(segs)} "
                  f"seg_len={np.mean(seglens):.2f}", flush=True)


if __name__ == "__main__":
    part2()
    part3()
    part1()
    print("done-triad", flush=True)
