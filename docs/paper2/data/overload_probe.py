"""
docs/paper2/data/overload_probe.py
===================================
The overload-gate round (s3.57; Max: "feasibility is part of the
energy... let's figure out the good way to put the penalty in the
energy and see if that fixes turan and nothing else breaks").

efn2 = stair_E + lam * hinge^2(claim-layer line overload), riding every
existing gate (no new iterations). Design-round measurements: dose-
response is a STEP (lam=0 broken d729 at LOWER stair-E — E-blindness in
one number; lam=1-2 repaired, +6 tiles E = 0.2%, the previously-
reverted depth-repairing composite now accepted; lam>=4 over-trades,
routed 8.28); repaired os=0 geometry routed 7.90 — beats the 8.04
record; guards byte-identical at lam in {2,8}; cost +0.1-0.2 s.

Arms (all courses, shake_cycles=1, exact_seeds, snap_claims; 3 seeds x
60 s):
- control : order_shake=1, overload_lam=0    (the 8.04 turan record)
- ovl     : order_shake=1, overload_lam=1
- ovl_nos : order_shake=0, overload_lam=1    (validation's routed
            winner ~7.90: with the penalty, the order step is
            unnecessary on turan and its geometry is better)
dshake non-exact reference: 7.19 (quoted, not re-run).

PRE-REGISTERED BARS:
- MECHANISM: gate fires (s1 d0) on turan in every exact arm; ovl arms'
  turan geometry has overload 0 (no d729-class residue).
- MINIMUM: turan best ovl arm <= 8.0 (validation predicts 7.90);
  K100/K140/spin_glass/ER within noise of snap-round values
  (8.74 / 11.41 / 12.66 / 4.76).
- STRETCH: turan <= 7.19 — validity by construction meets the
  non-exact record.
- KNOWN LIMIT on record: spin_glass's 10v8 column is unrepairable by
  the current move set (evaluation-only term); persists by design.
- No default flips.

Run:  nohup .venv/bin/python docs/paper2/data/overload_probe.py \
        > docs/paper2/data/overload_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "overload_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "K140": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
BASE = {"courses": True, "shake_cycles": 1, "exact_seeds": True,
        "snap_claims": True}
ARMS = [("control", dict(BASE, order_shake=1)),
        ("ovl", dict(BASE, order_shake=1, overload_lam=1.0)),
        ("ovl_nos", dict(BASE, overload_lam=1.0))]
TEMPLATE = {"K100": "8.00", "K140": "11.00", "ER100_d10": "-",
            "turan_n162": "6.00", "spin_glass_n163": "11.64"}


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
    cell, gid, arm, kw, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    d = r.get("diag", {})
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
    print("\nsummary (ACL mean over legal seeds (n); s=skips d=deficit):")
    for cell in CELLS:
        parts = [f"{cell:16s}"]
        for arm, _ in ARMS:
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
        parts.append(f"tmpl={TEMPLATE[cell]}")
        print("  ".join(parts))
    print("done-overload-probe", flush=True)


if __name__ == "__main__":
    main()
