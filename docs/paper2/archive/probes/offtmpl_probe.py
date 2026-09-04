"""
docs/paper2/data/offtmpl_probe.py
==================================
The identity audit (s3.55; Max: "we need to make sure that all of our
policies are helping on graphs for which templates don't exist or are
not near-optimal. this is like the whole point of the algorithm. if we
collapse into worse templates we are nothing.")

Board: Z12 cells where busclique has NO native template — liquid (ER),
sparse structured (regular n316, watts-strogatz n486: n far beyond any
clique cover's usefulness), and multi-patch (weak-strong-cluster c8xK32,
c3xK64 — busclique cannot address disjoint-clique graphs). Arms: stock
minorminer (fresh paired baseline) vs the current switch stack, one
increment at a time.

Arms (3 seeds x 60 s):
- mm     : stock minorminer (random_seed, timeout)
- base   : courses=True, shake_cycles=1
- dshake : + order_shake=1
- exact  : + exact_seeds=True

PRE-REGISTERED READING (before any run):
- IDENTITY BAR: the switch stack (best of base/dshake/exact) beats or
  ties mm on >= 4 of 5 off-template cells; nothing regresses vs the
  s3.38/s3.40-era P16 story (we historically win regular/ws/wsc-K64).
- EXACTNESS OFF-TEMPLATE: exact must not regress beyond noise vs dshake
  on any cell (completion is finishing, not template-ness — this bar is
  the direct test of Max's worry).
- FAILURE RULE: if mm wins the off-template board, the recent dense
  tuning overfit — record and redirect immediately.

Run:  nohup .venv/bin/python docs/paper2/data/offtmpl_probe.py \
        > docs/paper2/data/offtmpl_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "offtmpl_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"ER100_d10": None, "regular_n316": 13096, "ws_n486": 17188,
         "wsc_c8xK32": 33640, "wsc_c3xK64": 33574}
ARMS = [("mm", None),
        ("base", {"courses": True, "shake_cycles": 1}),
        ("dshake", {"courses": True, "shake_cycles": 1, "order_shake": 1}),
        ("exact", {"courses": True, "shake_cycles": 1, "order_shake": 1,
                   "exact_seeds": True})]


def _load(name, gid):
    import networkx as nx
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, gid, arm, kw, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    if kw is None:
        import minorminer
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
        d = {}
    else:
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
        emb = r.get("embedding") or {}
        d = r.get("diag", {})
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                skips=d.get("mm_skips"), deficit=d.get("deficit_edges"),
                time=round(time.perf_counter() - t0, 1))


def main():
    jobs = [(c, g, arm, kw, s) for c, g in CELLS.items()
            for arm, kw in ARMS for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} skips={row['skips']} "
                  f"def={row['deficit']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nsummary (mean over legal seeds (n)):")
    for cell in CELLS:
        parts = [f"{cell:14s}"]
        for arm, _ in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["arm"] == arm and r["final_acl"]]
            parts.append(f"{arm}={sum(r['final_acl'] for r in sel)/len(sel):.2f}({len(sel)})"
                         if sel else f"{arm}=FAIL(0)")
        print("  ".join(parts))
    print("done-offtmpl-probe", flush=True)


if __name__ == "__main__":
    main()
