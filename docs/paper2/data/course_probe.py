"""
docs/paper2/data/course_probe.py
=================================
The s3.49 fix, measured (Max: "I would like to see the embeddings for the
dense graphs actually approaching template accuracy again"): Zephyr
course-resolved wires (`courses=True` — sub-lane = 2k+j, stride-2
same-course runs, kappa = fresh contacts per tile ~7.7) vs the folded
default, full routed protocol on Z12.

Arms: default (folded, the recorded arm), courses, courses_exact
(courses + wire_exact — exploratory: _couples is parity-correct in course
mode, first sound wire matching on Zephyr). 3 seeds x 60 s per (cell, arm).

PRE-REGISTERED BARS (written before any run; baselines: template
turan 6.00 / K100 8.00 / K140 11.00 / spin_glass 11.64 (zephyr_triad);
mm 12.01 / 10.28 / ~18.6 / 17.87; pipeline default (s3.47) turan 14.03 /
K100 12.21 / spin_glass 19.85(2/3) / ER 4.81):

- MINIMUM: courses turan < 12.01 (first search win over mm on the cell);
  no cell regresses beyond noise vs the paired default arm (same seed);
  spin_glass legality >= 2/3.
- TARGET/STRETCH: turan <= 9 (more than halfway to template 6.00);
  K100 <= 11 (below mm 10.28... strictly: below 11, mm-adjacent).
- INDEPENDENT GATES: full test suite green (535 passed, 2026-08-01);
  stride-1 invariance tests green (courses is a structural no-op on
  Pegasus/Chimera).
- FAILURE RULE: if courses lands near 14 on turan, the ceiling was not
  (only) the representation — stop, report, revisit s3.49 before tuning.

Decision rule: no default flip from this probe alone (house protocol —
flip is a separate discussion with the numbers on the table).

Run:  nohup .venv/bin/python docs/paper2/data/course_probe.py \
        > docs/paper2/data/course_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "contract_probe_routed.csv")
OUT = os.path.join(HERE, "course_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "K140": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
ARMS = [("default", {}),
        ("courses", {"courses": True}),
        ("courses_exact", {"courses": True, "wire_exact": True})]
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
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                time=round(time.perf_counter() - t0, 1),
                diag=str(r.get("diag", "")))


def main():
    jobs = [(c, g, arm, kw, s) for c, g in CELLS.items()
            for arm, kw in ARMS for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} ({row['time']}s)", flush=True)
            rows.append(row)

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    base = {}
    if os.path.exists(BASE):
        with open(BASE) as fh:
            for r in csv.DictReader(fh):
                if r["target"] == "Z12" and r["cell"] in CELLS \
                        and r["arm"] in ("mm", "mm2"):
                    base.setdefault((r["cell"], r["arm"]), []).append(
                        float(r["final_acl"]) if r["final_acl"] else None)

    print("\nsummary (mean over legal seeds; n legal in parens):")
    for cell in CELLS:
        parts = [f"{cell:16s}"]
        for arm, _ in ARMS:
            vals = [r["final_acl"] for r in rows
                    if r["cell"] == cell and r["arm"] == arm
                    and r["final_acl"]]
            parts.append(f"{arm}={sum(vals)/len(vals):.2f}({len(vals)})"
                         if vals else f"{arm}=FAIL(0)")
        for barm in ("mm", "mm2"):
            bv = [x for x in base.get((cell, barm), []) if x is not None]
            parts.append(f"{barm}={sum(bv)/len(bv):.2f}({len(bv)})"
                         if bv else f"{barm}=?")
        parts.append(f"tmpl={TEMPLATE[cell]}")
        print("  ".join(parts))
    print("done-course-probe", flush=True)


if __name__ == "__main__":
    main()
