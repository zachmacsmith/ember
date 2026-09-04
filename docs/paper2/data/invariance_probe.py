"""
docs/paper2/data/invariance_probe.py
====================================
s3.127 — the order- and init-invariance instrument on the rewrite. Per
cell, tail="none", WORK budget: draws over the bag seed (`sched_seed`,
question order) at a fixed init, and over the init seed (`seed`) at a
fixed bag; the endpoint distribution of pre-tail ACL and max chain.
The claim under test: the engine is order-free and init-free within
tol = max(0.3, 0.05 * mean) on every cell.

Run:  nohup .venv/bin/python docs/paper2/data/invariance_probe.py [smoke] \\
        [draws=K] > docs/paper2/data/invariance_probe.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 1800
DRAWS = 5
BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
]
SMOKE_CELLS = ("grid_200", "ws_n486", "turan_n162")
BUDGET = {"K100": 10000, "K140": 12000, "ER100_d10": 8000,
          "turan_n162": 15000, "spin_glass_n163": 12000,
          "regular_n316": 8000, "ws_n486": 6000, "grid_200": 8000,
          "honeycomb_200": 8000, "king_graph_196": 8000}
GROUPS = ("order", "init")   # vary sched_seed | vary seed


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
    cell, gid, group, draw = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    tgt = dnx.zephyr_graph(12, 4)
    seed, sseed = (0, draw) if group == "order" else (draw, 0)
    t0 = time.perf_counter()
    r = attract_embed(src, tgt, timeout=TIMEOUT, seed=seed,
                      sched_seed=sseed, tail="none", max_asks=BUDGET[cell])
    d = r.get("diag", {})
    return dict(cell=cell, group=group, draw=draw, seed=seed,
                sched_seed=sseed, legal_acl=r.get("legal_acl"),
                legal_max_chain=d.get("legal_max_chain"),
                asks=d.get("asks"), bookmark_asks=d.get("bookmark_asks"),
                stopped_by=d.get("stopped_by"), pen=d.get("pen"),
                stair=d.get("stair"), bars=d.get("bars"),
                certified=d.get("certified"), mm_skipped=d.get("mm_skipped"),
                error=(r.get("error") or "")[:60] or None,
                wall=round(time.perf_counter() - t0, 1))


def _mean(v):
    v = [x for x in v if x is not None]
    return round(sum(v) / len(v), 3) if v else None


def main():
    args = sys.argv[1:]
    smoke = "smoke" in args
    draws = next((int(a.split("=")[1]) for a in args
                  if a.startswith("draws=")), DRAWS)
    cells = [c for c in BOARD if (not smoke or c[0] in SMOKE_CELLS)]
    jobs = [(c, g, grp, d) for (c, _f, g) in cells for grp in GROUPS
            for d in range(1, draws + 1)]
    tag = "smoke" if smoke else "board"
    print(f"invariance {tag}: {len(jobs)} jobs; load {os.getloadavg()}",
          flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=min(24, len(jobs))) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']:<16} {row['group']:<5} d{row['draw']}: "
                  f"lacl={row['legal_acl']} lmx={row['legal_max_chain']} "
                  f"bm={row['bookmark_asks']}/{row['asks']} "
                  f"stop={row['stopped_by']} pen={row['pen']} "
                  f"bars={row['bars']} cert={row['certified']} "
                  f"err={row['error']} ({row['wall']}s)", flush=True)
            rows.append(row)
    out = os.path.join(HERE, f"invariance_probe_{tag}.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nMAP — per cell: order draws | init draws (mean, sd, range)")
    sensitive = []
    for cell, _f, _g in cells:
        line = f"{cell:<16}"
        for grp in GROUPS:
            acls = [r["legal_acl"] for r in rows
                    if r["cell"] == cell and r["group"] == grp
                    and r["legal_acl"] is not None]
            if not acls:
                line += f" | {grp}: none"
                continue
            m = _mean(acls)
            rng_ = round(max(acls) - min(acls), 3)
            sd = round(statistics.pstdev(acls), 3) if len(acls) > 1 else 0.0
            tol = max(0.3, 0.05 * m)
            flag = " SENSITIVE" if rng_ > tol else ""
            if flag:
                sensitive.append((cell, grp, m, rng_))
            stops = Counter(r["stopped_by"] for r in rows
                            if r["cell"] == cell and r["group"] == grp)
            line += (f" | {grp}: {m} sd={sd} range={rng_} "
                     f"lmx={_mean([r['legal_max_chain'] for r in rows if r['cell'] == cell and r['group'] == grp])} "
                     f"stop={dict(stops)}{flag}")
        print(line)
    print("sensitive:", sensitive if sensitive else "none")
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
