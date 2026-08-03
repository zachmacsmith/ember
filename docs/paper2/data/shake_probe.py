"""
docs/paper2/data/shake_probe.py
================================
The shake round (s3.52; Max's magnet-ball design after the s3.51
frozen-fixed-point diagnosis): settle-and-reshake geometry cycles — the
s3.41 shell transplanted onto stair-E in the course representation —
plus the masked line-pool capacity flip, each measured as its own arm.

Pre-validation measurements on record (design round, turan/Z12-course):
stock geometry E 3088 (frozen over 8 geo cycles); shell cycle 0 alone
2674; full 4-cycle shell 3.76 s. Masked pool alone WORSENED pack-level
E (3088 -> 3703, one seed, unrouted) — hence its own report-only arm.

Arms (all with courses=True; 3 seeds x 60 s):
- courses     : fresh paired control (identical config to s3.50's arm)
- shake1      : shake_cycles=1 — "more stair steps before the first
                pack" only; attribution for steps-vs-reshake
- shake       : shake_cycles=4 — THE REGISTERED ARM
- pool        : masked_pool=True — capacity flip alone (report-only)
- shake_pool  : shake_cycles=4 + masked_pool=True

PRE-REGISTERED BARS (written before any run; per-flip, paired by seed):
- MINIMUM: shake turan < courses turan (paired) and <= 9.0; no cell
  regresses beyond noise vs courses; spin_glass 3/3 in the shake arm.
- STRETCH: turan <= 7.5 (lane arithmetic ~7; template 6.00);
  K100 <= 10.28 (beats mm).
- ATTRIBUTION: shake1 vs shake separates contraction-before-commit from
  the reshake cycles proper. pool arms carry NO registered claim.
- FAILURE RULE: shake turan ~= courses turan -> the freeze diagnosis is
  incomplete; stop and re-diagnose before more mechanism.
- No default flips from this probe (house protocol).

Cross-run reference (s3.50 course_probe, quoted, NOT paired): courses
turan 10.02 / K100 10.57 / K140 14.04 (3/3) / spin_glass 14.01 (3/3) /
ER 5.09; mm 12.01 / 10.28 / 18.27(2/3) / 17.87 / 4.97; template 6.00 /
8.00 / 11.00 / 11.64 / -.

Run:  nohup .venv/bin/python docs/paper2/data/shake_probe.py \
        > docs/paper2/data/shake_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shake_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "K140": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
ARMS = [("courses", {"courses": True}),
        ("shake1", {"courses": True, "shake_cycles": 1}),
        ("shake", {"courses": True, "shake_cycles": 4}),
        ("pool", {"courses": True, "masked_pool": True}),
        ("shake_pool", {"courses": True, "shake_cycles": 4,
                        "masked_pool": True})]
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
    e0 = r.get("round_E") or [None]
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                geo_E=e0[0], time=round(time.perf_counter() - t0, 1))


def main():
    jobs = [(c, g, arm, kw, s) for c, g in CELLS.items()
            for arm, kw in ARMS for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} E={row['geo_E']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print("\nsummary (ACL mean over legal seeds (n) | geometry E of "
          "round 0):")
    for cell in CELLS:
        parts = [f"{cell:16s}"]
        for arm, _ in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["arm"] == arm and r["final_acl"]]
            es = [r["geo_E"] for r in rows if r["cell"] == cell
                  and r["arm"] == arm and r["geo_E"] is not None]
            acl = (f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                   f"({len(sel)})" if sel else "FAIL(0)")
            emean = f"E{sum(es)/len(es):.0f}" if es else "E?"
            parts.append(f"{arm}={acl} {emean}")
        parts.append(f"tmpl={TEMPLATE[cell]}")
        print("  ".join(parts))
    print("done-shake-probe", flush=True)


if __name__ == "__main__":
    main()
