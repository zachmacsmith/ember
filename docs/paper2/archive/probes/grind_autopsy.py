"""
docs/paper2/data/grind_autopsy.py
=================================
s3.86: characterize WHAT minorminer's warm grind changes on our raw
seeds — distributions only, never specimens (Max: specimen-gazing
overfits). Per cell x seed: emb0 = pipeline with tail="none" (raw legal
pre-tail), emb1 = warm mm grind (30 s). Per-variable records to CSV for
statistics; printed output is aggregate tables per cell: length-delta
histogram, displacement histogram (tile centroid), shape-class
transitions (1-run / L / tree), in-place vs moved shrink split, cascade
fraction (changed chains with changed source-neighbours), max chain.
Readout map: in-place shrinks -> audition/selection story; long
relocations -> hulls/candidates too tight; cascades -> sequencing; one
repeated defect class -> the seeds (upstream hypothesis).

Run:  nohup .venv/bin/python docs/paper2/data/grind_autopsy.py \
        > docs/paper2/data/grind_autopsy.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "grind_autopsy.csv")
CELLS = [("turan_n162", 2647, (0, 1, 2, 3, 4)),
         ("ws_n486", 17188, (0, 1, 2, 3, 4)),
         ("regular_n316", 13096, (0, 1, 2)),
         ("grid_200", 1590, (0, 1, 2))]


def _load(gid):
    import networkx as nx
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, gid, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    import minorminer
    from ember_qc.algorithms.factored import attract_embed
    from ember_qc.algorithms.factored.field import TileGrid
    from ember_qc.algorithms.factored.placement import target_layout
    src = _load(gid)
    tgt = dnx.zephyr_graph(12, 4)
    r = attract_embed(src, tgt, timeout=60, seed=seed, tail="none")
    emb0 = {int(v): sorted(int(q) for q in c)
            for v, c in (r.get("embedding") or {}).items()}
    if not emb0:
        return []
    emb1 = minorminer.find_embedding(
        src, list(tgt.edges()), random_seed=seed, timeout=30,
        initial_chains=emb0, skip_initialization=True) or emb0
    emb1 = {int(v): sorted(int(q) for q in c) for v, c in emb1.items()}

    grid = TileGrid(tgt, target_layout(tgt), courses=True)
    rev = {}
    for (o, ln, s_), run in grid.wire_map.items():
        for p, q in run.items():
            rev[q] = (o, ln, s_, p)

    def geom(chain):
        tiles, keys = [], set()
        for q in chain:
            k = rev.get(q)
            if k is None:
                continue
            o, ln, s_, p = k
            tiles.append((p, ln) if o == 1 else (ln, p))
            keys.add((o, ln, s_))
        cx = sum(t[0] for t in tiles) / max(len(tiles), 1)
        cy = sum(t[1] for t in tiles) / max(len(tiles), 1)
        runs = len(keys)
        cls = "1run" if runs <= 1 else ("L" if runs == 2 else "tree")
        return cx, cy, cls

    rows = []
    changed = {v for v in emb0 if emb0[v] != emb1.get(v, [])}
    for v in sorted(emb0):
        c0, c1 = emb0[v], emb1.get(v, [])
        x0, y0, s0 = geom(c0)
        x1, y1, s1 = geom(c1)
        inter = len(set(c0) & set(c1))
        union = len(set(c0) | set(c1))
        nb_changed = sum(1 for u in src.neighbors(v) if u in changed)
        rows.append(dict(cell=cell, seed=seed, v=v, deg=src.degree(v),
                         len0=len(c0), len1=len(c1),
                         jac=round(inter / max(union, 1), 3),
                         disp=round(((x1 - x0) ** 2
                                     + (y1 - y0) ** 2) ** 0.5, 2),
                         cls0=s0, cls1=s1,
                         changed=int(v in changed),
                         nb_changed=nb_changed))
    return rows


def main():
    jobs = [(c, g, s) for c, g, seeds in CELLS for s in seeds]
    allrows = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for rows in ex.map(_run, jobs):
            if rows:
                r0 = rows[0]
                n_ch = sum(r["changed"] for r in rows)
                d = (sum(r["len1"] for r in rows)
                     - sum(r["len0"] for r in rows)) / len(rows)
                print(f"{r0['cell']} seed {r0['seed']}: "
                      f"{n_ch}/{len(rows)} chains changed, "
                      f"dACL {d:+.3f}", flush=True)
            allrows.extend(rows)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(allrows[0]))
        w.writeheader()
        w.writerows(allrows)

    print("\n===== aggregates per cell (changed chains only) =====")
    for cell, _g, _s in CELLS:
        sel = [r for r in allrows if r["cell"] == cell and r["changed"]]
        alln = [r for r in allrows if r["cell"] == cell]
        if not sel:
            print(f"{cell}: no changes")
            continue
        n = len(sel)
        dl = [r["len1"] - r["len0"] for r in sel]
        hist_dl = {b: 0 for b in ("<=-3", "-2", "-1", "0", "+1", ">=+2")}
        for x in dl:
            b = ("<=-3" if x <= -3 else str(x) if -2 <= x <= 1 and x != 0
                 else "0" if x == 0 else ">=+2")
            b = {"-2": "-2", "-1": "-1", "1": "+1"}.get(b, b)
            hist_dl[b] = hist_dl.get(b, 0) + 1
        disp = [r["disp"] for r in sel]
        hd = {"0": sum(1 for x in disp if x == 0),
              "<=1": sum(1 for x in disp if 0 < x <= 1),
              "<=3": sum(1 for x in disp if 1 < x <= 3),
              ">3": sum(1 for x in disp if x > 3)}
        trans = {}
        for r in sel:
            trans[(r["cls0"], r["cls1"])] = trans.get(
                (r["cls0"], r["cls1"]), 0) + 1
        inplace = sum(1 for r in sel
                      if r["len1"] < r["len0"] and r["disp"] <= 1)
        moved = sum(1 for r in sel
                    if r["len1"] < r["len0"] and r["disp"] > 1)
        casc = sum(1 for r in sel if r["nb_changed"] > 0) / n
        mx0 = max(r["len0"] for r in alln)
        mx1 = max(r["len1"] for r in alln)
        print(f"\n{cell}: {n} changed rows "
              f"(of {len(alln)}), mean deg changed "
              f"{sum(r['deg'] for r in sel)/n:.1f} vs all "
              f"{sum(r['deg'] for r in alln)/len(alln):.1f}")
        print(f"  len delta: {hist_dl}")
        print(f"  displacement: {hd}")
        print(f"  shape transitions: {trans}")
        print(f"  shrinks in-place(<=1 tile) {inplace} vs moved(>1) {moved}")
        print(f"  cascade fraction {casc:.2f}; max chain {mx0}->{mx1}")
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
