"""
docs/paper2/data/consolidation3_probe.py
=========================================
The s3.66 guard probe: the consolidated pipeline (one accounting via
arm_books, effective config, coarsen at its shipped cell, vcycle DEFAULT
ON) must reproduce the measured vc-arm board; mm paired control; first
max-chain (tail) data recorded per the s3.65 doctrine.

Arms (3 seeds x 60 s): att = new default (vcycle on), att_legacy =
vcycle=False (the old default), mm = stock minorminer.
Cells: the 7-cell Z12 board + P16 spot (turan/K100/ws — the flip changes
Pegasus too: first vcycle-on-P16 data).

PRE-REGISTERED BARS (OUTCOME-FIRST — the s3.66 doctrine; gates are
diagnostics, not bars):
- Z12 att vs the measured vc arm (s3.62-64): K100 <= 7.9, K140 <= 10.7,
  turan <= 8.3 (spot-check measured 7.41 post-unification), ER <= 4.95,
  spin_glass <= 12.6 (the accounting fix shifts its gate energies by
  design), regular <= 2.9, ws <= 2.95.
- P16 att: no regression vs s3.61/s3.58 (turan <= 8.6, K100 <= 13.9,
  ws <= 3.9) — note vcycle now ACTIVE on P16 (fabric-agnostic init).
- mm controls replicate (shared-box rule; box currently free).
- max_chain: recorded and reported vs mm per cell — first tail data,
  NO bar (baseline-setting).
- Sentinel is the invariant "done-probe" (the twice-bitten lesson).

Run:  nohup .venv/bin/python docs/paper2/data/consolidation3_probe.py \
        > docs/paper2/data/consolidation3_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "consolidation3_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
]
BASE_REF = {"K100": 8.12, "K140": 10.91, "ER100_d10": 4.76,
            "turan_n162": 9.06, "spin_glass_n163": 12.88,
            "regular_n316": 2.86, "ws_n486": 3.12}


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
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    t0 = time.perf_counter()
    if arm == "mm":
        import minorminer
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
        skipped = deficit = None
    else:
        from ember_qc.algorithms.factored import attract_embed
        kw = {"vcycle": False} if arm == "att_legacy" else {}
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
        emb = r.get("embedding") or {}
        d = r.get("diag", {})
        skipped, deficit = d.get("mm_skipped"), d.get("deficit_edges")
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    return dict(cell=cell, fabric=fabric, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx, skipped=skipped,
                deficit=deficit, time=round(time.perf_counter() - t0, 1))


def main():
    print("load at start:", os.getloadavg(), flush=True)
    jobs = [(c, f, g, arm, s) for c, f, g in CELLS
            for arm in ("att", "att_legacy", "mm") for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']} {row['arm']} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} skip={row['skipped']} "
                  f"d={row['deficit']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nsummary (ACL mean over legal seeds (n)):")
    for cell, fabric, _ in CELLS:
        parts = [f"{fabric} {cell:16s}"]
        for arm in ("att", "att_legacy", "mm"):
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric
                   and r["arm"] == arm and r["final_acl"]]
            if sel:
                acl = f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                extra = ""
                mx = [r["max_chain"] for r in sel if r["max_chain"]]
                if mx:
                    extra += f" mx{sum(mx)/len(mx):.0f}"
                for key, tag in (("deficit", "d"),):
                    vals = [r[key] for r in sel if r[key] is not None]
                    if vals:
                        extra += f" {tag}{sum(vals)/len(vals):.0f}"
                parts.append(f"{arm}={acl}({len(sel)}){extra}")
            else:
                parts.append(f"{arm}=FAIL(0)")
        print("  ".join(parts))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
