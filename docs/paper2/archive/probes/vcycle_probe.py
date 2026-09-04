"""
docs/paper2/data/vcycle_probe.py
=================================
The V-cycle round, V0 (notes s3.62): source-side twin-first coarsening
(closed-neighborhood Jaccard, the ledger derivation) as a multilevel
INIT — spectral is never consulted; the coarsest level sits on a
deterministic circle and positions inherit down. Fine-level machinery
unchanged. This probe tests the core hypothesis: global structure
(block separation, clump adjacency) decided at the coarse level, where
it is a single local move.

Arms (3 seeds x 60 s, paired): base = zero-kwarg default (spectral
init); vc = vcycle=True. base is the control (the claim is about the
init, not about minorminer).

PRE-REGISTERED BARS (from the ledger entry, recorded 2026-08-03):
- PRIMARY: turan <= 8.5 under vc (spectral-FREE — erasing the s3.40
  recorded miss where random init stalled at 9.93; base band 9.06-9.13).
- GUARDS: K100 / K140 / spin_glass / ER within noise of base
  (8.12 / 10.91 / 12.88 / 4.76); K_n coarsening is provably total
  (one supernode), so any clique regression indicts the expansion
  spread, not the score.
- SPARSE: regular_n316 / ws_n486 within noise of base (2.86 / 3.12) —
  coarsening must not tax the liquid/sparse regime (s3.21 null).
- FAILURE RULE: primary miss -> report + discuss; V1 (weighted coarse
  arrange) is the named next arm, not auto-built.

Run:  nohup .venv/bin/python docs/paper2/data/vcycle_probe.py \
        > docs/paper2/data/vcycle_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "vcycle_probe.csv")
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
    kw = {"vcycle": True} if arm == "vc" else {}
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
            for arm in ("base", "vc") for s in SEEDS]
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
        for arm in ("base", "vc"):
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
    print("done-vcycle-probe", flush=True)


if __name__ == "__main__":
    main()
