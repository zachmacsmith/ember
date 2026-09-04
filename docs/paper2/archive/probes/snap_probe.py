"""
docs/paper2/data/snap_probe.py
===============================
The snap round (s3.56): claim-time crossing alignment (aim, don't
repair) + the arm the s3.54 matrix never ran (dshake + exact_seeds).

Design-round corrections on record: turan's d729 was OVERSUBSCRIPTION
(4 columns at depth 9-12 vs 8 sub-lanes; 9 arms never colored; 9x81 =
729), NOT misalignment — snap cannot color the uncolorable; that
defect is the named turan blocker for a future packing round. What
snap does, simulated: pre-completion deficit 1212->729 / 523->0
(turan os=0/1), 502->26 (K100), 511->19 (K140); extensions 70-123 ->
0 everywhere; corners 100% direct. dshake+exact (os=1) completes
turan to d0 even unsnapped.

Arms (all courses=True, shake_cycles=1, order_shake=1; 3 seeds x 60 s):
- dshake   :                        (7.19 turan reference)
- exact_ds : exact_seeds            (the missing s3.54 arm)
- snap     : exact_seeds, snap_claims

PRE-REGISTERED BARS:
- MECHANISM: snap arm diag extensions == 0 on dense cells; gate
  (mm_skips) fires on turan in exact_ds and/or snap.
- MINIMUM: no cell regresses beyond noise vs s3.54 exact values
  (K100 8.73 / K140 11.40 / spin_glass 12.51 / ER ~4.76; dshake is a
  measured no-op on cliques, arms comparable); turan exact arms <= 7.70.
- STRETCH: turan <= 7.19 with the gate firing.
- HONESTY: amend the s3.54 d729 attribution in the round's notes entry
  regardless of outcome.
- No default flips.

Run:  nohup .venv/bin/python docs/paper2/data/snap_probe.py \
        > docs/paper2/data/snap_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "snap_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "K140": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
BASE = {"courses": True, "shake_cycles": 1, "order_shake": 1}
ARMS = [("dshake", dict(BASE)),
        ("exact_ds", dict(BASE, exact_seeds=True)),
        ("snap", dict(BASE, exact_seeds=True, snap_claims=True))]
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
                ext=d.get("extensions"),
                time=round(time.perf_counter() - t0, 1))


def main():
    jobs = [(c, g, arm, kw, s) for c, g in CELLS.items()
            for arm, kw in ARMS for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} skips={row['skips']} "
                  f"def={row['deficit']} ext={row['ext']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nsummary (ACL mean over legal seeds (n); s=skips d=deficit "
          "e=extensions):")
    for cell in CELLS:
        parts = [f"{cell:16s}"]
        for arm, _ in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["arm"] == arm and r["final_acl"]]
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
        parts.append(f"tmpl={TEMPLATE[cell]}")
        print("  ".join(parts))
    print("done-snap-probe", flush=True)


if __name__ == "__main__":
    main()
