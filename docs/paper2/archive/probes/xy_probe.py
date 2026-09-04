"""
docs/paper2/data/xy_probe.py
=============================
s3.121 — the joint two-axis singleton reinsertion (`xy_singles`): evict
one variable from BOTH carried orders, re-insert at the exact optimum
over all (x-slot, y-slot) pairs — the fold's atom (s3.87): a 2-D
relocation whose 1-D halves are individually net-negative, so per-axis
moves cannot compose it. Replaces the ladder's scale-1 sweep
(subsumption). One flip vs the shipped default.

PRE-REGISTERED BAR (recorded before the run):
 - movers: regular_n316 and/or ws_n486 win beyond tol
   (tol = max(0.3, 0.05*ctl)); mechanism check: ws max_edge_span
   drops vs control (the s3.87 shortcut collapse).
 - guards: turan 6.000-class held at 10 seeds (crystal intact),
   K100/K140/spin_glass/grid/honeycomb/king/ER in-tol, no feasibility
   loss anywhere, wall <= 1.10*ctl + 1s.
Deep seeds on THREE deciders this round: turan, ws, regular (regular
is a predicted mover).

Run:  nohup .venv/bin/python docs/paper2/data/xy_probe.py \
        > docs/paper2/data/xy_probe.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "xy_probe.csv")
SEEDS = (0, 1, 2)
DEEP_SEEDS = tuple(range(10))
TIMEOUT = 60
ARMS = ("plane", "xy")
KW = {
    "plane": {},                        # the shipped default
    "xy": {"xy_singles": True},         # the one flip
}

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
]

DEEP_CELLS = (("turan_n162", "Z12"), ("ws_n486", "Z12"),
              ("regular_n316", "Z12"))


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
    assert not unknown, f"typo'd kwargs would silently measure control: {unknown}"
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
                init_wall=d.get("init_wall"),
                arrange_wall=d.get("arrange_wall"),
                passes=d.get("seat_passes"),
                traj=("|".join(str(x) for x in d.get("accept_traj", []))
                      or None),
                pen=d.get("seat_pen"),
                int_acc=d.get("interleave_accepts"),
                int_dec=d.get("interleave_declines"),
                int_noop=d.get("interleave_noops"),
                readouts=d.get("readouts"),
                mono_swaps=d.get("mono_swaps"),
                bm_wall=d.get("bookmark_wall"),
                bm_ro=d.get("bookmark_readouts"),
                hier_acc=d.get("hier_accepts"),
                pair_acc=d.get("pair_accepts"),
                xy_acc=d.get("xy_accepts"),
                proj_iters=d.get("proj_iters"),
                proj_pen=d.get("proj_pen"),
                plane_stair=d.get("plane_stair"),
                max_edge_span=d.get("max_edge_span"),
                mm_skipped=d.get("mm_skipped"),
                ball_acc=d.get("ball_accepts"),
                deficit=d.get("deficit_edges"),
                cmiss=d.get("convert_miss"),
                cert=d.get("certified"),
                time=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD)
    if smoke:
        cells = [c for c in cells
                 if c[0] in ("ws_n486", "turan_n162") and c[1] == "Z12"]
    rows = []
    jobs = []
    for c, f, g in cells:
        seeds = (DEEP_SEEDS if (c, f) in DEEP_CELLS and not smoke
                 else SEEDS)
        seeds = seeds[:1] if smoke else seeds
        jobs += [(c, f, g, arm, s) for arm in ARMS for s in seeds]
    print(f"{len(cells)} cells, {len(jobs)} jobs; load {os.getloadavg()}",
          flush=True)
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['arm']:<6} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} xy={row['xy_acc']} "
                  f"acc={row['int_acc']} ro={row['readouts']} "
                  f"mes={row['max_edge_span']} def={row['deficit']} "
                  f"skip={row['mm_skipped']} ({row['time']}s)",
                  flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    ctl = ARMS[0]
    print(f"\nsummary (mean ACL; d = arm - {ctl}, negative = wins):")
    bar_fail = []
    for cell, fabric, _ in cells:
        m = {}
        for arm in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm]
            m[arm] = (mean([r["final_acl"] for r in sel]),
                      sum(1 for r in sel if r["final_acl"]),
                      mean([r["max_chain"] for r in sel]),
                      mean([r["time"] for r in sel]),
                      mean([r["max_edge_span"] for r in sel]),
                      mean([r["xy_acc"] for r in sel]))
        de = m[ctl]
        line = f"{fabric} {cell:<18} {ctl}={de[0]}({de[1]}) mx={de[2]}"
        for arm in ARMS[1:]:
            o = m[arm]
            delta = (round(o[0] - de[0], 3)
                     if o[0] is not None and de[0] is not None else None)
            line += (f" | {arm}={o[0]}({o[1]}) mx={o[2]} mes={o[4]}"
                     f" xy={o[5]}"
                     + (f" d={delta:+.3f}" if delta is not None else ""))
            if delta is not None and de[0] is not None:
                tol = max(0.3, 0.05 * de[0])
                if delta > tol or (o[1] < de[1]):
                    bar_fail.append((fabric, cell, arm, delta))
            if (o[3] is not None and de[3] is not None
                    and o[3] > 1.10 * de[3] + 1.0):
                bar_fail.append((fabric, cell, arm, f"wall {de[3]}->{o[3]}"))
        print(line)
    for c in ("turan_n162", "ws_n486", "regular_n316"):
        acl = {arm: mean([r["final_acl"] for r in rows
                          if r["cell"] == c and r["fabric"] == "Z12"
                          and r["arm"] == arm]) for arm in ARMS}
        mx = {arm: mean([r["max_chain"] for r in rows
                         if r["cell"] == c and r["fabric"] == "Z12"
                         and r["arm"] == arm]) for arm in ARMS}
        mes = {arm: mean([r["max_edge_span"] for r in rows
                          if r["cell"] == c and r["fabric"] == "Z12"
                          and r["arm"] == arm]) for arm in ARMS}
        print(f"\nBAR {c}/Z12: acl {acl} mx {mx} mes {mes}")
    print("BAR board:", "FAIL " + str(bar_fail) if bar_fail else "PASS",
          flush=True)
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
