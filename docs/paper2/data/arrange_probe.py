"""
docs/paper2/data/arrange_probe.py
==================================
Mini-probe for the product-mode arms (notes s3.32). The domains arm is dead
on arrival — stock minorminer's restrict_chains hangs/segfaults with
non-trivial domains (isolated repro, s3.32) — so the arms are:

  arrange       span state + alternating 1-D dynamics + wire seeds (rounds)
  arrange-1shot same, converge-once-then-route (max_rounds=1) — the s3.31
                transfer-economics protocol for comfortable-dense

Cells: K100, K140 (cliff), ws_n486 (win guard). 3 seeds, 60 s, parallel
workers (machine is shared: niced, bounded). Baselines (point, span-tb,
mm-full) are read from span_probe.csv — same cells and seeds, not rerun.

Run:  .venv/bin/python docs/paper2/data/arrange_probe.py
"""

import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "arrange_probe.csv")
BASE_CSV = os.path.join(HERE, "span_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = ("turan_n162", "spin_glass_n163")  # deferred irregular-dense run

ARMS = [
    ("stair", {"state": "span", "span_dynamics": "arrange",
               "seed_mode": "wire", "readout": "stair"}),
    ("stair-1shot", {"state": "span", "span_dynamics": "arrange",
                     "seed_mode": "wire", "readout": "stair",
                     "max_rounds": 1, "round_frac": 0.5}),
    # s3.32 arms retained for the irregular-dense cells (never probed there)
    ("arrange", {"state": "span", "span_dynamics": "arrange",
                 "seed_mode": "wire"}),
    ("arrange-1shot", {"state": "span", "span_dynamics": "arrange",
                       "seed_mode": "wire", "max_rounds": 1,
                       "round_frac": 0.5}),
]


def _load_cell(name):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    ids = {"ws_n486": 17188,        # s3.31 win guard
           "turan_n162": 2647,      # irregular dense (s3.23 loss family)
           "spin_glass_n163": 37309}  # irregular dense, d0.30
    if name in ids:
        from ember_qc.load_graphs import load_graph
        return nx.convert_node_labels_to_integers(load_graph(ids[name]))
    raise ValueError(name)


def _run(job):
    cell, arm, kw, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load_cell(cell)
    target = dnx.pegasus_graph(16)
    t0 = time.perf_counter()
    if arm == "mm-full":
        import minorminer
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
        r = {}
    else:
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
        emb = r.get("embedding") or {}
    return dict(cell=cell, arm=arm, seed=seed,
                final_acl=round(sum(len(c) for c in emb.values()) / len(emb), 3)
                if emb else None,
                rounds=r.get("rounds"),
                time=round(time.perf_counter() - t0, 1),
                diag=str(r.get("field_diag", "")))


def main():
    jobs = [(cell, arm, kw, s) for cell in CELLS for s in SEEDS
            for arm, kw in ARMS]
    # mm-full baselines for the cells absent from span_probe.csv
    jobs += [(cell, "mm-full", {}, s)
             for cell in ("turan_n162", "spin_glass_n163") for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=40) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} ({row['time']}s)", flush=True)
            rows.append(row)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    base = {}
    if os.path.exists(BASE_CSV):
        with open(BASE_CSV) as fh:
            for r in csv.DictReader(fh):
                if r["cell"] in CELLS and r["arm"] in ("point", "span-tb",
                                                       "mm-full"):
                    base.setdefault((r["cell"], r["arm"]), []).append(
                        float(r["final_acl"]) if r["final_acl"] else None)

    print("\nsummary (means over legal seeds; baselines from span_probe.csv):")
    for cell in CELLS:
        parts = [f"{cell:9s}"]
        for arm in ("point", "span-tb", "mm-full"):
            vals = [v for v in base.get((cell, arm), []) if v is not None]
            vals += [r["final_acl"] for r in rows
                     if r["cell"] == cell and r["arm"] == arm
                     and r["final_acl"]]
            parts.append(f"{arm}={sum(vals)/len(vals):.2f}({len(vals)})"
                         if vals else f"{arm}=fail")
        for arm, _ in ARMS:
            vals = [r["final_acl"] for r in rows
                    if r["cell"] == cell and r["arm"] == arm and r["final_acl"]]
            parts.append(f"{arm}={sum(vals)/len(vals):.2f}({len(vals)})"
                         if vals else f"{arm}=fail")
        print("  ".join(parts))


if __name__ == "__main__":
    main()
