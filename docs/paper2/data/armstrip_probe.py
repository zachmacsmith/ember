"""
docs/paper2/data/armstrip_probe.py
==================================
s3.125 — two switches on the plane engine, measured one flip at a time
against the shipped default (`plane`), paired by (cell, seed):

  `arm_cost`  one bar (stride junctions) per ACTIVE arm in the plane
              objective, judge and interleaver alike (the span-only
              stair priced a contact-bearing point arm at 0; grid_200
              stair 1.2/var vs real 1.965).
  `strip`     the plane is the chip's real columns x unbounded rows;
              rows beyond the chip and clamp misses are the
              capacity-first lexicographic key.

Arms: plane, arm, strip, arm+strip, and their `-nt` twins
(tail="none": the plane's own answer, read with legal_acl).

PRE-REGISTERED BAR (tailed arms vs plane): no ACL regression beyond
tol (max(0.3, 0.05*ctl)); no feasibility loss; wall <= 1.10*ctl + 1s.
CLAIMS (read, not gated): (a) arm-nt: grid/honeycomb/king legal_acl
falls from the ~2.0 plane floor toward the polished value; K100
byte-identical; (b) strip: final_width_x <= W always; strip_miss and
judge_pen at the bookmark; ws legal_max_chain; (c) turán at 240 s for
both switches (60 s under load is a budget measurement).

Run:  nohup .venv/bin/python docs/paper2/data/armstrip_probe.py \
        [smoke] [arm ...] > docs/paper2/data/armstrip_probe.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = (0, 1, 2)
DEEP_SEEDS = tuple(range(10))
TIMEOUT = 60
ALL_ARMS = ("plane", "arm", "strip", "arm+strip",
            "plane-nt", "arm-nt", "strip-nt", "arm+strip-nt")
_A = {"arm_cost": True}
_S = {"strip": True}
_AS = {"arm_cost": True, "strip": True}
KW = {
    "plane": {}, "arm": _A, "strip": _S, "arm+strip": _AS,
    "plane-nt": {"tail": "none"}, "arm-nt": {**_A, "tail": "none"},
    "strip-nt": {**_S, "tail": "none"},
    "arm+strip-nt": {**_AS, "tail": "none"},
}

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
]
SMOKE_CELLS = ("grid_200", "ws_n486", "turan_n162")
DEEP_CELLS = (("turan_n162", "Z12"), ("ws_n486", "Z12"),
              ("regular_n316", "Z12"), ("ER100_d10", "Z12"))
LONG_CELLS = ("turan_n162",)      # also run at 240 s (budget caveat)
LONG_TIMEOUT = 240

DIAG_KEYS = (
    "init_wall", "arrange_wall", "seat_passes", "interleave_accepts",
    "interleave_declines", "interleave_noops", "readouts",
    "bookmark_wall", "bookmark_readouts", "legal_acl", "legal_max_chain",
    "judge", "judge_pen", "plane_stair", "plane_bars", "strip_miss",
    "strip_iters", "final_width_x", "final_width_y", "projection_misses",
    "unb_miss", "proj_pen", "max_edge_span", "mm_skipped",
    "ball_accepts", "deficit_edges", "convert_miss", "certified",
    "adopt_worse")


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
    cell, fabric, gid, arm, seed, timeout = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    from ember_qc.algorithms.factored.placement import AttractConfig
    from dataclasses import fields
    kw = KW[arm]
    known = {f.name for f in fields(AttractConfig)}
    unknown = set(kw) - known
    assert not unknown, f"typo'd kwargs would silently measure control: {unknown}"
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=timeout, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = r.get("diag", {})
    row = dict(cell=cell, fabric=fabric, gid=gid, arm=arm, seed=seed,
               timeout=timeout, final_acl=acl, max_chain=mx,
               traj=("|".join(str(x) for x in d.get("accept_traj", []))
                     or None))
    for k in DIAG_KEYS:
        row[k] = d.get(k)
    row["error"] = (r.get("error") or "")[:80] or None
    row["time"] = round(time.perf_counter() - t0, 1)
    return row


def main():
    args = [a for a in sys.argv[1:]]
    smoke = "smoke" in args
    arms = tuple(a for a in args if a in KW) or ALL_ARMS
    tag = "smoke" if smoke else "board"
    out = os.path.join(HERE, f"armstrip_probe_{tag}.csv")
    cells = list(BOARD)
    if smoke:
        cells = [c for c in cells if c[0] in SMOKE_CELLS]
    jobs = []
    for c, f, g in cells:
        seeds = (DEEP_SEEDS if (c, f) in DEEP_CELLS and not smoke
                 else SEEDS)
        seeds = seeds[:1] if smoke else seeds
        for arm in arms:
            for s in seeds:
                jobs.append((c, f, g, arm, s, TIMEOUT))
                if c in LONG_CELLS:
                    jobs.append((c, f, g, arm, s, LONG_TIMEOUT))
    print(f"{tag}: {len(cells)} cells, arms {arms}, {len(jobs)} jobs; "
          f"load {os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=min(24, len(jobs))) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<16} {row['arm']:<13} "
                  f"seed {row['seed']} t={row['timeout']}: "
                  f"{row['final_acl']} mx={row['max_chain']} "
                  f"lacl={row['legal_acl']} lmx={row['legal_max_chain']} "
                  f"stair={row['plane_stair']} bars={row['plane_bars']} "
                  f"pen={row['judge_pen']} smiss={row['strip_miss']} "
                  f"sit={row['strip_iters']} fw={row['final_width_x']}x"
                  f"{row['final_width_y']} cmiss={row['convert_miss']} "
                  f"cert={row['certified']} mmskip={row['mm_skipped']} "
                  f"err={row['error']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    ctl = "plane"
    print(f"\nsummary (mean over seeds at 60 s; d = arm - {ctl}, "
          f"negative = wins; lacl = pre-tail):")
    bar_fail = []
    for cell, fabric, _ in cells:
        m = {}
        for arm in arms:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm
                   and r["timeout"] == TIMEOUT]
            m[arm] = (mean([r["final_acl"] for r in sel]),
                      sum(1 for r in sel if r["final_acl"]),
                      mean([r["max_chain"] for r in sel]),
                      mean([r["time"] for r in sel]),
                      mean([r["legal_acl"] for r in sel]),
                      mean([r["legal_max_chain"] for r in sel]))
        if ctl not in m:
            continue
        de = m[ctl]
        line = (f"{fabric} {cell:<16} {ctl}={de[0]}({de[1]}) mx={de[2]} "
                f"lacl={de[4]} lmx={de[5]}")
        for arm in arms:
            if arm == ctl:
                continue
            o = m[arm]
            delta = (round(o[0] - de[0], 3)
                     if o[0] is not None and de[0] is not None else None)
            line += (f" | {arm}={o[0]}({o[1]}) mx={o[2]} lacl={o[4]} "
                     f"lmx={o[5]}"
                     + (f" d={delta:+.3f}" if delta is not None else ""))
            if arm.endswith("-nt"):
                continue
            if delta is not None and de[0] is not None:
                tol = max(0.3, 0.05 * de[0])
                if delta > tol or (o[1] < de[1]):
                    bar_fail.append((fabric, cell, arm, delta))
            if (o[3] is not None and de[3] is not None
                    and o[3] > 1.10 * de[3] + 1.0):
                bar_fail.append((fabric, cell, arm, f"wall {de[3]}->{o[3]}"))
        print(line)
    for cell in LONG_CELLS:
        sel = [r for r in rows if r["cell"] == cell
               and r["timeout"] == LONG_TIMEOUT]
        if sel:
            print(f"\n{cell} at {LONG_TIMEOUT}s:", {
                arm: (mean([r["final_acl"] for r in sel if r["arm"] == arm]),
                      mean([r["legal_acl"] for r in sel if r["arm"] == arm]))
                for arm in arms})
    print("BAR board:", "FAIL " + str(bar_fail) if bar_fail else "PASS",
          flush=True)
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
