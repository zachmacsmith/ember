"""
docs/paper2/data/hunits_probe.py
=================================
s3.115 — Max's ER variance hypothesis, de-confounded from budget by
s3.114: the orders engine's interval units cannot express a gather of
a SCATTERED similar set (ER's variance clusters, king's patches);
`hier_units=True` offers the affinity hierarchy's groups as extra
units (one jointly-judged weave per group, coarsest first). Deciders:
ER100, king. Guards: turán/ws deep (must not regress), grid, regular.
Both acceptance policies carried (the gathers may interact with the
acceptance rule differently).

Run:  nohup .venv/bin/python docs/paper2/data/hunits_probe.py \
        > docs/paper2/data/hunits_probe.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "hunits_probe.csv")
SEEDS = (0, 1, 2)
DEEP_SEEDS = tuple(range(10))
TIMEOUT = 60
ARMS = ("orders", "orders-h", "audit", "audit-h")
KW = {
    "orders": {"engine": "orders"},
    "orders-h": {"engine": "orders", "hier_units": True},
    "audit": {"engine": "orders-audit"},
    "audit-h": {"engine": "orders-audit", "hier_units": True},
}

BOARD = [
    ("ER100_d10", "Z12", None), ("king_graph_196", "Z12", 32622),
    ("turan_n162", "Z12", 2647), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("regular_n316", "Z12", 13096),
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
                hier_acc=d.get("hier_accepts"),
                int_acc=d.get("interleave_accepts"),
                passes=d.get("seat_passes"),
                bm_wall=d.get("bookmark_wall"),
                readouts=d.get("readouts"),
                max_edge_span=d.get("max_edge_span"),
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
            print(f"{row['cell']:<15} {row['arm']:<9} seed {row['seed']}:"
                  f" acl={row['final_acl']} mx={row['max_chain']}"
                  f" hier={row['hier_acc']} pen={row['pen']}"
                  f" ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(float(v) for v in vals) / len(vals), 3) \
            if vals else None

    print("\nsummary (mean ACL; d = +hier - base, negative = hier wins):")
    for cell, _f, _g in BOARD:
        line = f"{cell:<15}"
        for base, harm in (("orders", "orders-h"), ("audit", "audit-h")):
            b = [r for r in rows if r["cell"] == cell and r["arm"] == base]
            h = [r for r in rows if r["cell"] == cell and r["arm"] == harm]
            mb, mh = mean([r["final_acl"] for r in b]), \
                mean([r["final_acl"] for r in h])
            d = (round(mh - mb, 3) if mb is not None and mh is not None
                 else None)
            line += (f" | {base}={mb} +h={mh}"
                     + (f" d={d:+.3f}" if d is not None else "")
                     + f" hacc={mean([r['hier_acc'] for r in h])}")
        print(line, flush=True)
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
