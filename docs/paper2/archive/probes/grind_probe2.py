"""
docs/paper2/data/grind_probe2.py
===============================
s3.94 kill-the-grinder RE-MEASURE on the s3.93 baseline (unbounded_pack now default; the s3.91 verdict was fed by the broken bounded packer). Arms:

  default : shipped (mm grind + 1-sweep ball)
  ball    : tail="ball" — grind deleted, stock ball to fixpoint
  ballS   : + ball_singles — ball' (the |S|=1 exact-cross question,
            cross._place_cross; profiled 1.2 ms/question)
  ballSF  : + fold_moves — s3.89 placement folds replace the grind's
            fold-by-accident contribution (P16-dense fold defect is a
            known caveat on the 3 informational P16 cells)

Pre-registered readout: the ship question is whether a no-grind arm
holds the whole Z12 board (ACL and max chain, tol = max(0.3,
0.05 x default)); every cell where ALL no-grind arms lose beyond tol
names the grind's remaining irreplaceable contribution. Smoke
expectations (seed 0): K100 holds at 6x speedup (7.82/3.7 s vs
7.84/21 s); ws and grid regress (4.08 vs 2.92; 1.19 vs 1.03) — the
probe maps the boundary properly. Profiled context: ball's liquid wall
hog is sph_tree's Dijkstra fallback (41 ms/tree), not the singles.

Run:  nohup .venv/bin/python docs/paper2/data/grind_probe.py \
        > docs/paper2/data/grind_probe2.log 2>&1 &
Smoke: add `smoke` argv. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "grind_probe2.csv")
SEEDS = (0, 1, 2)
DEEP_SEEDS = tuple(range(10))
TIMEOUT = 60
ARMS = ("default", "ball", "ballS", "ballSF")
KW = {
    "default": {},
    "ball": {"tail": "ball"},
    "ballS": {"tail": "ball", "ball_singles": True},
    "ballSF": {"tail": "ball", "ball_singles": True, "fold_moves": True},
}

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
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
    from ember_qc.algorithms.factored.placement import AttractConfig
    from dataclasses import fields
    kw = KW[arm]
    known = {f.name for f in fields(AttractConfig)}
    unknown = set(kw) - known
    assert not unknown, f"typo'd kwargs measure the control: {unknown}"
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = r.get("diag", {})
    return dict(cell=cell, fabric=fabric, gid=gid, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx,
                ball_acc=d.get("ball_accepts"),
                mm_skipped=d.get("mm_skipped"),
                fold_acc=d.get("fold_accepts"),
                time=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD)
    if smoke:
        cells = [c for c in cells
                 if c[0] in ("ws_n486", "K100") and c[1] == "Z12"]
    rows = []
    jobs = []
    for c, f, g in cells:
        seeds = (DEEP_SEEDS if (c, f) in (("turan_n162", "Z12"),
                                          ("ws_n486", "Z12"))
                 and not smoke else SEEDS)
        seeds = seeds[:1] if smoke else seeds
        jobs += [(c, f, g, arm, s) for arm in ARMS for s in seeds]
    print(f"{len(cells)} cells, {len(jobs)} jobs; load {os.getloadavg()}",
          flush=True)
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['arm']:<8} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} bacc={row['ball_acc']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    print("\nsummary (mean ACL; d = arm - default, negative = wins):")
    grind_needed = []
    for cell, fabric, _ in cells:
        m = {}
        for arm in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm]
            m[arm] = (mean([r["final_acl"] for r in sel]),
                      sum(1 for r in sel if r["final_acl"]),
                      mean([r["max_chain"] for r in sel]),
                      mean([r["time"] for r in sel]))
        de = m["default"]
        line = f"{fabric} {cell:<18} default={de[0]}({de[1]}) mx={de[2]}"
        all_lose = de[0] is not None
        for arm in ARMS[1:]:
            o = m[arm]
            delta = (round(o[0] - de[0], 3)
                     if o[0] is not None and de[0] is not None else None)
            line += (f" | {arm}={o[0]} mx={o[2]} t={o[3]}"
                     + (f" d={delta:+.3f}" if delta is not None else ""))
            if delta is not None:
                tol = max(0.3, 0.05 * de[0])
                if delta <= tol and o[1] >= de[1]:
                    all_lose = False
        print(line)
        if all_lose:
            grind_needed.append((fabric, cell))
    print("\ngrind irreplaceable on:", grind_needed or "NOWHERE",
          flush=True)
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
