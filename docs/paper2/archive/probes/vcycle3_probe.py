"""
docs/paper2/data/vcycle3_probe.py
==================================
V-cycle V2 — footprint-true initialization (notes s3.64): the 5-arm
mechanism ladder. M1/M2 wire-mass sizing (the moat fix), M3
tangent-tiling closure (no free constant), M4 diagonal-segment spreads
(the crystal's 1D-order form). Per-worker constants are ALWAYS set (the
s3.61 contamination lesson).

Arms (3 seeds x 60 s, paired):
  base  — no vcycle (spectral init default)
  vc1   — V1 as committed (count sizing, COARSE_SPAN 0.4, discs)
  vc2m  — + mass sizing
  vc2t  — + tangent tiling
  vc2x  — + segments (full V2)

PRE-REGISTERED BARS:
- MINIMUM (vc2x vs the V1 best-arm board, no regressions): K100 <= 7.9
  gated, K140 <= 10.7 gated, turan <= 8.5 gated, spin_glass <= 12.0,
  ER <= 4.85, regular <= 2.9, ws <= 2.95.
- STRETCH: spin_glass gated (the last d1 edge) and/or ER gated;
  spin_glass <= 11.7 (template-parity band).
- FLIP CONDITION: any single arm gates all five dense cells AND holds
  the sparse wins -> propose the vcycle default flip (NOT auto-flipped).
- FAILURE RULE: the ladder attributes the failing mechanism; report +
  discuss; no partial default changes.
- Theory note on record (Max): busclique is extremal in clique SIZE,
  not proven ACL-optimal below K_max — K100 7.79 < 8.00 already; the
  degree-counting LB (~6.2 on Z12 K100) leaves visible room. Circles
  vs crystals is a live question, measured here.

Run:  nohup .venv/bin/python docs/paper2/data/vcycle3_probe.py \
        > docs/paper2/data/vcycle3_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vcycle3_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = [
    ("K100", None), ("K140", None), ("ER100_d10", None),
    ("turan_n162", 2647), ("spin_glass_n163", 37309),
    ("regular_n316", 13096), ("ws_n486", 17188),
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
    cell, gid, arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    import ember_qc.algorithms.factored.coarsen as C
    # always set ALL constants per-arm (the s3.61 contamination lesson)
    cfgs = {
        "base": ("count", False, "disc"),
        "vc1":  ("count", False, "disc"),
        "vc2m": ("mass",  False, "disc"),
        "vc2t": ("mass",  True,  "disc"),
        "vc2x": ("mass",  True,  "segment"),
    }
    C.SIZING, C.TILING, C.SHAPE = cfgs[arm]
    C.COARSE_SPAN = 0.4
    kw = {} if arm == "base" else {"vcycle": True}
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    d = r.get("diag", {})
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                skips=d.get("mm_skips"), deficit=d.get("deficit_edges"),
                time=round(time.perf_counter() - t0, 1))


def main():
    print("load at start:", os.getloadavg(), flush=True)
    jobs = [(c, g, arm, s) for c, g in CELLS
            for arm in ("base", "vc1", "vc2m", "vc2t", "vc2x")
            for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} s={row['skips']} d={row['deficit']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nsummary (ACL mean over legal seeds (n)):")
    for cell, _ in CELLS:
        parts = [f"{cell:16s}"]
        for arm in ("base", "vc1", "vc2m", "vc2t", "vc2x"):
            sel = [r for r in rows if r["cell"] == cell
                   and r["arm"] == arm and r["final_acl"]]
            if sel:
                acl = f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                extra = ""
                for key, tag in (("skips", "s"), ("deficit", "d")):
                    vals = [r[key] for r in sel if r[key] is not None]
                    if vals:
                        extra += f" {tag}{sum(vals)/len(vals):.0f}"
                parts.append(f"{arm}={acl}({len(sel)}){extra}")
            else:
                parts.append(f"{arm}=FAIL(0)")
        parts.append(f"ref={BASE_REF[cell]}")
        print("  ".join(parts))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-vcycle2-probe", flush=True)


if __name__ == "__main__":
    main()
