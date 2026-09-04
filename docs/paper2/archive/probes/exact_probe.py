"""
docs/paper2/data/exact_probe.py
================================
The exact-seeds round (s3.54; Max: "let's see what we can do in terms of
exact seeds. I expect hiccups but I think it's the best we can do for
now"): validity by construction on Zephyr — extend claims along their
wires until every source edge has a physical coupler (corner + edge +
bridge passes, boundary-line avoidance), and SKIP minorminer
legalization when the deficit hits zero. Aim: abolish the router-slack
tax (the s3.53 E-vs-routed inversion).

Design-round measurements on record: turan probe-geometry deficit
458 -> 0 (valid, seed ACL 10.28); K100 130 -> 0 (valid); K100
shake1-geometry gates valid at seed ACL 8.89 (routed champion 9.67);
turan shake1 remains deficit>0 -> router with better warm start.
Boundary-parity discovery: lines 0/2m have HALF crossing capacity.

Arms (all courses=True; 3 seeds x 60 s):
- base   : shake_cycles=1                 (turan 7.70 reference)
- dshake : shake_cycles=1, order_shake=1  (turan 7.19 reference)
- exact  : shake_cycles=1, exact_seeds
- exact0 : shake_cycles=0, exact_seeds    (design-round gate-fires arm)
- exact4 : shake_cycles=4, exact_seeds
- cover4 : shake_cycles=4, exact_seeds, cover_select

PRE-REGISTERED BARS (before any run):
- MECHANISM: mm_skips >= 1 fires on >= 2 dense cells in some exact arm;
  deficit fields populated; K140 unplaced == 0 under boundary avoidance.
- MINIMUM: no exact arm regresses beyond noise vs its paired non-exact
  arm on any cell; best exact-arm turan <= 7.19.
- TARGET: turan <= 6.5; E-inversion healed (cover4 vs exact4
  directional read: lower-E selections no longer route worse).
- WATCH: ER (prediction: exactness helps liquid cells via less
  negotiation); K140 under boundary avoidance.
- FAILURE RULE: gate never fires anywhere -> completion missed a
  structural cause; stop and dissect the residual.
- No default flips from this probe.

Run:  nohup .venv/bin/python docs/paper2/data/exact_probe.py \
        > docs/paper2/data/exact_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "exact_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "K140": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
ARMS = [("base", {"courses": True, "shake_cycles": 1}),
        ("dshake", {"courses": True, "shake_cycles": 1, "order_shake": 1}),
        ("exact", {"courses": True, "shake_cycles": 1,
                   "exact_seeds": True}),
        ("exact0", {"courses": True, "shake_cycles": 0,
                    "exact_seeds": True}),
        ("exact4", {"courses": True, "shake_cycles": 4,
                    "exact_seeds": True}),
        ("cover4", {"courses": True, "shake_cycles": 4,
                    "exact_seeds": True, "cover_select": True})]
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

    print("\nsummary (ACL mean over legal seeds (n); s = mm_skips mean; "
          "d = residual deficit mean):")
    for cell in CELLS:
        parts = [f"{cell:16s}"]
        for arm, _ in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["arm"] == arm and r["final_acl"]]
            if sel:
                acl = f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                sk = [r["skips"] for r in sel if r["skips"] is not None]
                df = [r["deficit"] for r in sel if r["deficit"] is not None]
                tag = ""
                if sk:
                    tag = (f" s{sum(sk)/len(sk):.1f}"
                           f" d{sum(df)/len(df):.0f}" if df
                           else f" s{sum(sk)/len(sk):.1f}")
                parts.append(f"{arm}={acl}({len(sel)}){tag}")
            else:
                parts.append(f"{arm}=FAIL(0)")
        parts.append(f"tmpl={TEMPLATE[cell]}")
        print("  ".join(parts))
    print("done-exact-probe", flush=True)


if __name__ == "__main__":
    main()
