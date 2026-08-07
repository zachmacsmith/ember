"""
docs/paper2/data/consume_probe.py
==================================
The s3.73 consumption round: both-axes gathers + strict-descent cluster
acceptance + no per-cluster caps ("the energy is the schedule") vs the
s3.72 consumption (y-only, lateral accepts, one-shot cap), patched
process-locally via field.CLUSTER_SCHED as the control arm.

PRE-REGISTERED BARS (approved plan):
- BAR1 (REQUIRED): ACL parity-or-better per cell vs s372; placement
  inside its round_frac budget (walls reported, no +/-10% clause).
- BAR2 (REQUIRED): turan 10-seed <= 6.5. Branches: pass => the schedule
  was the defect; 6.5-6.7 with BAR1 clean => the gate-energy blind spot
  is isolated with data => next round prices claim-layer cost into
  cluster gates (named, not built).
- BAR3 (watch): lattice block under 2-D gathers (adjoint refs: grid
  -0.54, honeycomb -0.90).
- BAR4 (watch): expander composite counts + walls without the one-shot
  cap — churn must self-terminate.
Decision: BAR1+BAR2 pass => default confirmed, delete the control
branch; BAR2 second branch with BAR1 clean => default still confirmed
(correctness cleanups), blind-spot round named; BAR1 fail => verdict,
revert, rethink.

Run:  nohup .venv/bin/python docs/paper2/data/consume_probe.py \
        > docs/paper2/data/consume_probe.log 2>&1 &
Smoke: add `smoke`. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "consume_probe.csv")
TIMEOUT = 60
ARMS = ("s372", "s373")
TURAN_SEEDS = tuple(range(10))
SEEDS = (0, 1, 2)

SCHED = {"s372": {"strict": False, "oneshot": True, "axes": (1,)},
         "s373": {"strict": True, "oneshot": False, "axes": (1, 0)}}

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
    from ember_qc.algorithms.factored import field as F
    F.CLUSTER_SCHED = dict(SCHED[arm])
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    t0 = time.perf_counter()
    from ember_qc.algorithms.factored import attract_embed
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
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
        jobs = [j for j in jobs
                if j[0].startswith(("turan_n162", "regular", "grid_200"))
                and j[1] == "Z12"]
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

    print("\nsummary (mean ACL, mean wall; d = s373 - s372):")
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
        if not (m["s372"][1] or m["s373"][1]):
            continue
        line = [f"{fabric} {cell:<18}"]
        for arm in ARMS:
            a, nok, w = m[arm]
            line.append(f"{arm}={a:.2f}({nok},w{w:.0f})" if a
                        else f"{arm}=FAIL(0)")
        s, n = m["s372"], m["s373"]
        if s[0] and n[0]:
            dv = n[0] - s[0]
            tol = max(0.3, 0.05 * s[0])
            if dv > tol or n[1] < s[1]:
                bar1_ok = False
                line.append(f"d={dv:+.2f}[REGRESS]")
            else:
                line.append(f"d={dv:+.2f}[ok]")
        elif s[0] and not n[0]:
            bar1_ok = False
            line.append("[s373 lost success]")
        print("  ".join(line))
    tu = mean([r["final_acl"] for r in rows
               if r["cell"] == "turan_n162" and r["fabric"] == "Z12"
               and r["arm"] == "s373"])
    print(f"\nBAR1 (parity-or-better): {'PASS' if bar1_ok else 'FAIL'}")
    if tu:
        b2 = "PASS" if tu <= 6.5 else ("BLIND-SPOT BRANCH" if tu <= 6.75
                                       else "FAIL")
        print(f"BAR2 turan 10-seed (s373): {tu:.3f} [{b2}]")
    print("BAR3: lattice rows above. BAR4: expander acc/rev + walls.")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
