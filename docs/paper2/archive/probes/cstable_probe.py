"""
docs/paper2/data/cstable_probe.py
=================================
The contraction stopping rule (2026-08-08 build round): CONTRACT_STEPS=16
is a disguised density knob — pure attraction's continuous minimum is
collapse and the fixed count is the only counter-force. `contract_stable`
replaces it with a derived rule: stop when best stair-E goes unimproved
for 2 consecutive steps, cap W+H, deadline-checked — and runs UN-gated on
stride-1, so the P16 cells here double as the "can contraction be
un-gated on Pegasus?" question (the fixed 16 measured +2.0 ACL on P16
turan, s3.58; the honest rule may stop early enough not to hurt).

One flip vs the shipped default; paired by (cell, fabric, seed).

Run:  nohup .venv/bin/python docs/paper2/data/cstable_probe.py \
        > docs/paper2/data/cstable_probe.log 2>&1 &
Smoke: add `smoke` argv. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cstable_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
ARMS = ("default", "cstable")

CELLS = [
    ("turan_n162", "Z12", 2647), ("K100", "Z12", None),
    ("K140", "Z12", None), ("spin_glass_n163", "Z12", 37309),
    ("turan_n162", "P16", 2647), ("K100", "P16", None),
    ("ws_n486", "P16", 17188),
]


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
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
    kw = {"contract_stable": True} if arm == "cstable" else {}
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    return dict(cell=cell, fabric=fabric, gid=gid, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx,
                contract_steps=r.get("diag", {}).get("contract_steps"),
                E_contract=r.get("diag", {}).get("E_contract"),
                stair_E=r.get("stair_E"),
                time=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(CELLS)
    if smoke:
        cells = [c for c in cells if c[0] == "turan_n162"]
    seeds = SEEDS[:1] if smoke else SEEDS
    print(f"{len(cells)} cells x {len(ARMS)} arms x {len(seeds)} seeds; "
          f"load {os.getloadavg()}", flush=True)
    jobs = [(c, f, g, arm, s) for c, f, g in cells
            for arm in ARMS for s in seeds]
    rows = []
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['arm']:<8} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} steps={row['contract_steps']} "
                  f"E_c={row['E_contract']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    print("\nsummary (mean ACL; d = cstable - default, negative = wins):")
    for cell, fabric, _ in cells:
        m = {}
        for arm in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm]
            m[arm] = (mean([r["final_acl"] for r in sel]),
                      sum(1 for r in sel if r["final_acl"]),
                      mean([r["contract_steps"] for r in sel]))
        d, c = m["default"], m["cstable"]
        delta = (round(c[0] - d[0], 3)
                 if c[0] is not None and d[0] is not None else None)
        print(f"{fabric} {cell:<18} default={d[0]}({d[1]}) "
              f"cstable={c[0]}({c[1]}) steps={c[2]} "
              + (f"d={delta:+.3f}" if delta is not None else ""))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
