"""
docs/paper2/data/offsets_probe.py
=================================
s3.78: which property of the golden-angle sunflower does the
rank-flattening actually need? Three child-offset generators inside the
UNCHANGED disc expansion (COARSE_SPAN, radii, coarse spectral all
identical): spiral = even + decorrelated projections (low-discrepancy);
random = decorrelated but sqrt-n clumpy (seeded, deterministic);
grid = perfectly even but axis-ALIGNED (maximal rank ties). Predictions:
grid worst (alignment = rank degeneracy), random <= spiral (evenness is
the open question — "is the spiral better than random?", Max). Z12 only
(the disc path is stride-gated; P16 init is plain spectral).

Run:  nohup .venv/bin/python docs/paper2/data/offsets_probe.py \
        > docs/paper2/data/offsets_probe.log 2>&1 &
Smoke: add `smoke` argv. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "offsets_probe.csv")
SEEDS = (0, 1, 2)
TURAN_SEEDS = tuple(range(10))
TIMEOUT = 60
ARMS = ("spiral", "random", "grid")

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
]


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
    cell, fabric, gid, arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    kw = {} if arm == "spiral" else {"init_offsets": arm}
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = r.get("diag", {})
    return dict(cell=cell, fabric=fabric, gid=gid, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx, stair_E=r.get("stair_E"),
                assigned=d.get("assigned"),
                mm_skipped=d.get("mm_skipped"),
                time=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD)
    if smoke:
        cells = [c for c in cells
                 if c[0] in ("turan_n162", "grid_200") and c[1] == "Z12"]
    rows = []
    jobs = []
    for c, f, g in cells:
        seeds = (TURAN_SEEDS if (c, f) == ("turan_n162", "Z12")
                 and not smoke else SEEDS)
        seeds = seeds[:1] if smoke else seeds
        jobs += [(c, f, g, arm, s) for arm in ARMS for s in seeds]
    print(f"{len(cells)} cells, {len(jobs)} jobs; load {os.getloadavg()}",
          flush=True)
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['arm']:<8} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} E={row['stair_E']} "
                  f"skip={row['mm_skipped']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    print("\nsummary (mean ACL; d = random - spiral, negative = wins):")
    for cell, fabric, _ in cells:
        m = {}
        for arm in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm]
            m[arm] = (mean([r["final_acl"] for r in sel]),
                      sum(1 for r in sel if r["final_acl"]),
                      mean([r["max_chain"] for r in sel]),
                      mean([r["time"] for r in sel]))
        de, o = m["spiral"], m["random"]
        delta = (round(o[0] - de[0], 3)
                 if o[0] is not None and de[0] is not None else None)
        dg = m["grid"]
        print(f"{fabric} {cell:<18} spiral={de[0]}({de[1]}) "
              f"random={o[0]}({o[1]}) grid={dg[0]}({dg[1]}) "
              f"mx {de[2]}->{o[2]} t {de[3]}->{o[3]}s "
              + (f"d={delta:+.3f}" if delta is not None else ""))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
