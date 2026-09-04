"""
docs/paper2/data/accept_work_probe.py
======================================
Max's question after the s3.113 board: how long did each acceptance
policy take to FIND its answer (not to stop)? The bookmark counters
(`bookmark_wall`, `bookmark_readouts` — when the returned state was
last improved) separate work-to-answer from post-answer churn: churn
after the answer is harvestable budget, churn instead of the answer is
the indictment. Cells: the two deciders (turán deep, ws deep) plus the
two acceptance-sensitive losses (grid, ER). Arms: the two policies
head-to-head (no default arm — this compares policies, not engines).

Run:  nohup .venv/bin/python docs/paper2/data/accept_work_probe.py \
        > docs/paper2/data/accept_work_probe.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "accept_work_probe.csv")
SEEDS = (0, 1, 2)
DEEP_SEEDS = tuple(range(10))
TIMEOUT = 60
ARMS = ("orders", "orders-audit")
KW = {"orders": {"engine": "orders"},
      "orders-audit": {"engine": "orders-audit"}}

BOARD = [
    ("turan_n162", "Z12", 2647), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("ER100_d10", "Z12", None),
]


def _load(name, gid):
    import networkx as nx
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, gid, arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    from ember_qc.algorithms.factored.placement import AttractConfig
    from dataclasses import fields
    kw = KW[arm]
    known = {f.name for f in fields(AttractConfig)}
    assert not set(kw) - known, "typo'd kwargs"
    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    d = r.get("diag", {})
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                max_chain=max((len(c) for c in emb.values()),
                              default=None),
                pen=d.get("seat_pen"),
                bm_wall=d.get("bookmark_wall"),
                bm_ro=d.get("bookmark_readouts"),
                arrange_wall=d.get("arrange_wall"),
                readouts=d.get("readouts"),
                int_acc=d.get("interleave_accepts"),
                int_dec=d.get("interleave_declines"),
                passes=d.get("seat_passes"),
                time=round(time.perf_counter() - t0, 1))


def main():
    jobs = []
    for c, f, g in BOARD:
        seeds = DEEP_SEEDS if c in ("turan_n162", "ws_n486") else SEEDS
        jobs += [(c, g, arm, s) for arm in ARMS for s in seeds]
    print(f"{len(jobs)} jobs; load {os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']:<12} {row['arm']:<12} seed {row['seed']}:"
                  f" acl={row['final_acl']} bm_wall={row['bm_wall']}"
                  f" bm_ro={row['bm_ro']} ro={row['readouts']}"
                  f" arr={row['arrange_wall']}", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(float(v) for v in vals) / len(vals), 2) \
            if vals else None

    print("\nwork-to-answer (mean over seeds):")
    for cell, _f, _g in BOARD:
        line = f"{cell:<12}"
        for arm in ARMS:
            sel = [r for r in rows
                   if r["cell"] == cell and r["arm"] == arm]
            line += (f" | {arm}: acl={mean([r['final_acl'] for r in sel])}"
                     f" bm_wall={mean([r['bm_wall'] for r in sel])}s"
                     f" bm_ro={mean([r['bm_ro'] for r in sel])}"
                     f" total_ro={mean([r['readouts'] for r in sel])}")
        print(line, flush=True)
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
