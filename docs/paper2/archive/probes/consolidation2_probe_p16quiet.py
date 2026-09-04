"""
QUIET-BOX RERUN (s3.58 owed item): same arms as p16gate, run when the
shared box is idle to close the turan cross-run-noise question.

docs/paper2/data/consolidation2_probe_p16quiet.py
=================================================
Follow-up to consolidation2_probe (notes s3.58): the P16 guard failed on
turan (10.44 vs bar <= 8.6, clean mm control 8.26) — implicating the
16-step contraction, the one cross-fabric change the stride gate did not
cover. The pre-registered fallback was applied: contraction is now
stride-gated too (CONTRACT_STEPS on stride>1, the pre-flip single step on
stride-1), making the ENTIRE consolidation-2 flip a structural no-op off
course-resolved Zephyr.

This rerun measures the att arm only on the P16 cells (mm controls were
clean in the main probe and are quoted, not re-run).

PRE-REGISTERED BARS (from the s3.38 consolidation-probe values + noise):
K100 <= 13.9, turan <= 8.6, spin_glass <= 18.0, regular_n316 <= 3.7,
ws_n486 <= 3.9. Scoring rule unchanged (shared box; the main probe's mm
controls anchor comparability).

Run:  nohup .venv/bin/python docs/paper2/data/consolidation2_probe_p16quiet.py \
        > docs/paper2/data/consolidation2_probe_p16quiet.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "consolidation2_probe_p16quiet.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = [("K100", None), ("turan_n162", 2647), ("spin_glass_n163", 37309),
         ("regular_n316", 13096), ("ws_n486", 17188)]
BARS = {"K100": 13.9, "turan_n162": 8.6, "spin_glass_n163": 18.0,
        "regular_n316": 3.7, "ws_n486": 3.9}


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, gid, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    target = dnx.pegasus_graph(16)
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, seed=seed, final_acl=acl,
                time=round(time.perf_counter() - t0, 1))


def main():
    print("load at start:", os.getloadavg(), flush=True)
    jobs = [(c, g, s) for c, g in CELLS for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"P16 {row['cell']} att seed {row['seed']}: "
                  f"{row['final_acl']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nsummary (ACL mean over legal seeds (n) vs bar):")
    for cell, _ in CELLS:
        sel = [r for r in rows if r["cell"] == cell and r["final_acl"]]
        acl = (f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
               if sel else "FAIL")
        print(f"  P16 {cell:16s} att={acl}({len(sel)})  bar<={BARS[cell]}")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-consolidation2-p16gate", flush=True)


if __name__ == "__main__":
    main()
