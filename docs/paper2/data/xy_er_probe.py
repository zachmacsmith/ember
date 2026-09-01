"""
docs/paper2/data/xy_er_probe.py
================================
s3.121 bug-hunt step 2 (pre-registered in the round plan): is ER's
+0.48 under xy_singles a PRICING FICTION (the move proposes judge-
regressions the ramp seam manufactures) or ACCEPT-ALL CHURN (sound
proposals, budget burned)? Discriminator: the audit arm declines any
judge-worse proposal, so
  - fiction  => audit+xy ~= audit (the fictions get declined, cheap)
               while plane+xy regresses;
  - churn    => audit+xy also pays (or the xy sweep starves audit's
               budget), and plane+xy's damage tracks readout volume.
ER100_d10 only, 4 arms x 3 seeds.

Run:  nohup .venv/bin/python docs/paper2/data/xy_er_probe.py \
        > docs/paper2/data/xy_er_probe.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "xy_er_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
ARMS = ("plane", "xy", "audit", "audit-xy")
KW = {
    "plane": {},
    "xy": {"xy_singles": True},
    "audit": {"engine": "plane-audit"},
    "audit-xy": {"engine": "plane-audit", "xy_singles": True},
}


def _run(job):
    arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    import networkx as nx
    from ember_qc.algorithms.factored import attract_embed
    from ember_qc.algorithms.factored.placement import AttractConfig
    from dataclasses import fields
    kw = KW[arm]
    known = {f.name for f in fields(AttractConfig)}
    assert not set(kw) - known
    src = nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    target = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    d = r.get("diag", {})
    return dict(arm=arm, seed=seed, final_acl=acl,
                max_chain=max((len(c) for c in emb.values()),
                              default=None),
                passes=d.get("seat_passes"),
                int_acc=d.get("interleave_accepts"),
                int_dec=d.get("interleave_declines"),
                int_noop=d.get("interleave_noops"),
                xy_acc=d.get("xy_accepts"),
                pair_acc=d.get("pair_accepts"),
                readouts=d.get("readouts"),
                bm_wall=d.get("bookmark_wall"),
                arrange_wall=d.get("arrange_wall"),
                traj=("|".join(str(x) for x in d.get("accept_traj", []))
                      or None),
                time=round(time.perf_counter() - t0, 1))


def main():
    jobs = [(arm, s) for arm in ARMS for s in SEEDS]
    print(f"{len(jobs)} jobs; load {os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(row, flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    print("\nER100_d10/Z12 means:")
    for arm in ARMS:
        sel = [r for r in rows if r["arm"] == arm]
        print(f"  {arm:<9} acl={mean([r['final_acl'] for r in sel])} "
              f"mx={mean([r['max_chain'] for r in sel])} "
              f"acc={mean([r['int_acc'] for r in sel])} "
              f"dec={mean([r['int_dec'] for r in sel])} "
              f"xy={mean([r['xy_acc'] for r in sel])} "
              f"aw={mean([r['arrange_wall'] for r in sel])}")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
