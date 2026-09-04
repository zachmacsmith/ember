"""
docs/paper2/data/units_probe.py
================================
The s3.71 generous-merging round: move units from THRESHOLD-FREE
coarsening (greedy score-rank matching, adjacency-only, no tau) vs the
s3.70 tau-aggregation units. The risk-asymmetry argument: over-merge
costs a rejected proposal at the gate; under-merge costs an
inexpressible joint move — and grid/honeycomb (pairs at 1/4, 1/3 < tau)
had NO usable units, which is the hypothesis for their inertness under
cluster moves.

PRE-REGISTERED BARS (from the approved plan):
- BAR1 (REQUIRED): board parity everywhere INCLUDING wall time
  (expander cells now have units — their proposals must die in the gate
  at parity cost; mean wall within +10% of the control arm per cell).
- BAR2 (REQUIRED, the point): grid/honeycomb improve toward the s3.69
  adjoint reference (-0.54/-0.90) now that patch units exist.
- BAR3 (guard): turan <= s3.70's 6.53 (10-seed on the deciding cell);
  triangular/king no worse than s3.70.
Decision: all pass => default stays ON (winners ship). BAR2 null with
BAR1/BAR3 clean => lattice residual confirmed init-time-only (decisive
info; default ON still fine by parity). BAR1/BAR3 fail => default back
to tau-units, verdict recorded.

Run:  nohup .venv/bin/python docs/paper2/data/units_probe.py \
        > docs/paper2/data/units_probe.log 2>&1 &
Smoke: add `smoke`. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "units_probe.csv")
TIMEOUT = 60
ARMS = ("tau", "units")   # cluster_units False / True; cluster_moves on in both

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
]
EXTRA = [("grid", 200, "Z12"), ("grid", 588, "Z12"),
         ("honeycomb", 200, "Z12"), ("honeycomb", 600, "Z12"),
         ("triangular_lattice", 400, "Z12"), ("king_graph", 196, "Z12")]
TURAN_SEEDS = tuple(range(10))   # deciding cell gets 10 seeds
SEEDS = (0, 1, 2)


def _resolve_extra():
    from ember_qc.load_graphs import _manifest_by_id, _graph_dedup_info
    man = _manifest_by_id()
    skip, _ = _graph_dedup_info()
    cells = []
    for cat, n_target, fab in EXTRA:
        cands = sorted((abs(e.get("nodes", 0) - n_target), g)
                       for g, e in man.items()
                       if e.get("category") == cat and g not in skip
                       and 40 <= e.get("nodes", 0) <= 1200)
        _, gid = cands[0]
        cells.append((f"{cat[:14]}_{man[gid]['nodes']}", fab, gid))
    return cells


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
    cell, fabric, gid, arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    kw = {"cluster_units": arm == "units"}
    t0 = time.perf_counter()
    from ember_qc.algorithms.factored import attract_embed
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = r.get("diag", {})
    return dict(cell=cell, fabric=fabric, gid=gid, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx,
                cl_acc=d.get("cluster_accepts"),
                cl_rev=d.get("cluster_reverts"),
                wall=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD) + _resolve_extra()
    jobs = []
    for c, f, g in cells:
        seeds = (TURAN_SEEDS if (c, f) == ("turan_n162", "Z12") and not smoke
                 else SEEDS[:1] if smoke else SEEDS)
        for arm in ARMS:
            for s in seeds:
                jobs.append((c, f, g, arm, s))
    if smoke:
        jobs = [j for j in jobs if j[0] in
                ("grid_200", "regular_n316", "turan_n162") and j[1] == "Z12"]
    print(f"{len(jobs)} jobs; load {os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['arm']:<6} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} acc/rev={row['cl_acc']}/"
                  f"{row['cl_rev']} w={row['wall']}s", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    print("\nsummary (mean ACL, mean wall; d = units - tau):")
    bar1_ok = True
    seen = []
    for cell, fabric, _ in cells:
        if (cell, fabric) in seen:
            continue
        seen.append((cell, fabric))
        m = {}
        for arm in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm]
            m[arm] = (mean([r["final_acl"] for r in sel]),
                      sum(1 for r in sel if r["final_acl"]),
                      mean([r["wall"] for r in sel]))
        if not m["tau"][1] and not m["units"][1]:
            continue
        line = [f"{fabric} {cell:<18}"]
        for arm in ARMS:
            a, nok, w = m[arm]
            line.append(f"{arm}={a:.2f}({nok},w{w:.0f})" if a
                        else f"{arm}=FAIL(0)")
        t, u = m["tau"], m["units"]
        if t[0] and u[0]:
            dv = u[0] - t[0]
            tol = max(0.3, 0.05 * t[0])
            board = (cell, fabric) in [(x, f) for x, f, _ in BOARD]
            wall_ok = (u[2] or 0) <= (t[2] or 1) * 1.10 + 1.0
            tag = "ok" if (dv <= tol and wall_ok) else (
                "REGRESS" if board else "regress")
            if board and (dv > tol or u[1] < t[1] or not wall_ok):
                bar1_ok = False
            line.append(f"d={dv:+.2f}[{tag}]")
        elif t[0] and not u[0]:
            if (cell, fabric) in [(x, f) for x, f, _ in BOARD]:
                bar1_ok = False
            line.append("[units lost success]")
        print("  ".join(line))
    tu = mean([r["final_acl"] for r in rows
               if r["cell"] == "turan_n162" and r["fabric"] == "Z12"
               and r["arm"] == "units"])
    print(f"\nBAR1 (board parity + wall): {'PASS' if bar1_ok else 'FAIL'}")
    if tu:
        print(f"BAR3 turan/Z12 units 10-seed mean: {tu:.3f} "
              f"({'PASS' if tu <= 6.53 + 0.1 else 'FAIL'} vs s3.70 6.53)")
    print("BAR2: read grid/honeycomb rows above vs adjoint refs "
          "(-0.54 grid_200, -0.90 honeycomb_200).")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
