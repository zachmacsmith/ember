"""
docs/paper2/data/vcycle2_probe.py
=================================
The V-cycle round, V1 (notes s3.63): two-stage flatten (Max's call —
one coarsening round, no hierarchy), coarse placement by
spectral-of-the-COARSE-graph (circle fallback on degenerate spectra),
weight-proportional child regions (block spans decided at the coarse
level, minimal form). V0's results to beat: gates fired on all five
dense cells (K100 7.79 / K140 10.52 / ER 4.71 / turan 9.19 /
spin_glass 12.78, all s1 d0) but sparse regressed (regular 3.46 vs
2.86) and turan missed its number.

Arms (3 seeds x 60 s, paired): base = zero-kwarg default; vc =
vcycle=True.

PRE-REGISTERED BARS:
- PRIMARY: turan <= 8.5 under vc, GATE-VALID (s1 d0).
- GATE GUARD: all five V0 gates persist (s1 d0 on K100/K140/ER/turan/
  spin_glass) — losing a gate = regression regardless of ACL.
- RECORD GUARDS: K100 <= 7.9, K140 <= 10.7, ER <= 4.8,
  spin_glass <= 12.9.
- SPARSE (the V1 spectral-of-coarse claim): regular_n316 <= 2.95,
  ws_n486 <= 3.2 — the V0 regression healed.
- FAILURE RULE: sparse still regressed -> report + discuss
  (engage-on-compression is the named next arm); turan number missed
  with gates held -> weighted coarse arrange is the next round.
- ALL bars pass -> propose the vcycle default flip (NOT auto-flipped).

RERUN (same day): first run measured the single-supernode bug (K100
9.62 — off-center clipped disc; fixed: n==1 -> centered V0-compact
disc) and gate losses on ER/spin_glass under the spectral spread. This
rerun adds arm vc_c = COARSE_SPAN 0.26 (compactness arm: can V0's
gate-completing compactness coexist with spectral's shape?). Same bars.

Run:  nohup .venv/bin/python docs/paper2/data/vcycle2_probe.py \
        > docs/paper2/data/vcycle2_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vcycle2_probe.csv")
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
    # always reset per-arm (the s3.61 contamination lesson)
    C.COARSE_SPAN = 0.26 if arm == "vc_c" else 0.4
    kw = {"vcycle": True} if arm in ("vc", "vc_c") else {}
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
            for arm in ("base", "vc", "vc_c") for s in SEEDS]
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
        for arm in ("base", "vc", "vc_c"):
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
