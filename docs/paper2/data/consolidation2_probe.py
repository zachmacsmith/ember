"""
docs/paper2/data/consolidation2_probe.py
=========================================
Consolidation 2 verification (notes s3.58): the deletion round flipped the
default to the measured s3.57 ovl_nos arm (courses + CONTRACT_STEPS=16
contraction + insertion + exact_seeds + snap_claims + overload_lam=1,
stride-gated) and deleted every losing switch. This probe confirms the
flipped default reproduces the standing boards with NO knobs passed, on
both fabrics, paired against stock minorminer.

Arms (3 seeds x 60 s, paired):
- att : attract_embed(src, target)  — the new default, zero kwargs
- mm  : stock minorminer.find_embedding, random_seed paired

Cells: Z12 dense board (K100, K140, ER100_d10, turan_n162,
spin_glass_n163), Z12 off-template (regular_n316, ws_n486, wsc_c8xK32,
wsc_c3xK64), P16 regression guard (K100, turan_n162, spin_glass_n163,
regular_n316, ws_n486 — the one cross-fabric change is the hardwired
contraction; the stride gate keeps everything else byte-identical there).

PRE-REGISTERED BARS:
- MECHANISM (Z12): the exactness gate fires s1 d0 on K100/K140/turan 3/3;
  extensions 0 wherever the gate fires (snap default).
- MINIMUM (Z12 board, = s3.54-s3.57 values + noise): K100 <= 8.9 (8.73),
  K140 <= 11.6 (11.40), turan <= 8.1 (7.90 — the constructed number; the
  negotiated 7.19 needed the deleted order_shake and is formally traded),
  spin_glass <= 12.8 (12.47), ER100 <= 4.95 (~4.76).
- OFF-TEMPLATE (Z12, = s3.55): att beats or ties mm on >= 3/4 of
  regular/ws/wsc cells; ws_n486 <= ~3.15.
- P16 GUARD (= s3.38 consolidation-probe values + noise): K100 <= 13.9,
  turan <= 8.6, spin_glass <= 18.0, regular_n316 <= 3.7, ws_n486 <= 3.9.
  A clean-control miss here implicates the contraction step (the only
  un-gated change) — the recorded fallback is stride-gating it.
- SCORING RULE (shared box; the s3.52/s3.55 discipline): scorable only if
  the paired mm control replicates its recorded values (Z12 mm: K100
  10.28 / K140 18.27(2/3) / ER 4.97 / turan 12.01 / spin_glass 17.87).
  A bar miss WITH an inflated mm control = contention -> rerun on a
  quieter window, not a verdict. Load is recorded at start and end.
- No further default changes from this probe (the flip already happened;
  a failed bar reopens the flip, it does not tune it).

Run:  nohup .venv/bin/python docs/paper2/data/consolidation2_probe.py \
        > docs/paper2/data/consolidation2_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "consolidation2_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
# (cell, fabric) -> manifest gid (None = synthetic)
CELLS = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("wsc_c8xK32", "Z12", 33640), ("wsc_c3xK64", "Z12", 33574),
    ("K100", "P16", None),
    ("turan_n162", "P16", 2647), ("spin_glass_n163", "P16", 37309),
    ("regular_n316", "P16", 13096), ("ws_n486", "P16", 17188),
]
TEMPLATE = {("K100", "Z12"): "8.00", ("K140", "Z12"): "11.00",
            ("turan_n162", "Z12"): "6.00",
            ("spin_glass_n163", "Z12"): "11.64"}


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


def _target(fabric):
    import dwave_networkx as dnx
    return (dnx.zephyr_graph(12, 4) if fabric == "Z12"
            else dnx.pegasus_graph(16))


def _run(job):
    cell, fabric, gid, arm, seed = job
    os.nice(10)
    src = _load(cell, gid)
    target = _target(fabric)
    t0 = time.perf_counter()
    if arm == "att":
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
        emb = r.get("embedding") or {}
        d = r.get("diag", {})
        skips, deficit, ext = (d.get("mm_skips"), d.get("deficit_edges"),
                               d.get("extensions"))
    else:
        import minorminer
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
        skips = deficit = ext = None
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, fabric=fabric, arm=arm, seed=seed, final_acl=acl,
                skips=skips, deficit=deficit, ext=ext,
                time=round(time.perf_counter() - t0, 1))


def main():
    print("load at start:", os.getloadavg(), flush=True)
    jobs = [(c, f, g, arm, s) for c, f, g in CELLS
            for arm in ("att", "mm") for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']} {row['arm']} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"s={row['skips']} d={row['deficit']} e={row['ext']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nsummary (ACL mean over legal seeds (n); s=skips d=deficit "
          "e=extensions):")
    for cell, fabric, _ in CELLS:
        parts = [f"{fabric} {cell:16s}"]
        for arm in ("att", "mm"):
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm
                   and r["final_acl"]]
            if sel:
                acl = f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                extra = ""
                for key, tag in (("skips", "s"), ("deficit", "d"),
                                 ("ext", "e")):
                    vals = [r[key] for r in sel if r[key] is not None]
                    if vals:
                        extra += f" {tag}{sum(vals)/len(vals):.0f}"
                parts.append(f"{arm}={acl}({len(sel)}){extra}")
            else:
                parts.append(f"{arm}=FAIL(0)")
        parts.append(f"tmpl={TEMPLATE.get((cell, fabric), '-')}")
        print("  ".join(parts))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-consolidation2-probe", flush=True)


if __name__ == "__main__":
    main()
