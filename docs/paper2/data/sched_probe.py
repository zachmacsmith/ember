"""
docs/paper2/data/sched_probe.py
===============================
s3.126 — the order-invariance instrument (Max's principle, never run):
does the plane engine's ENDPOINT depend on the order the questions are
asked, or on the init? Per cell, no tail, WORK budget (`max_asks` DP
evaluations — the box's load never enters the data), read the endpoint
distribution of pre-tail ACL / max chain across draws.

Groups (all tail="none", default engine):
  ladder      the shipped schedule (1 run, deterministic control)
  rung        random order WITHIN each rung (coarsest-first kept,
              pairs last), sched_seed = draw
  bag         one flat random bag of every slot of the pass
  rinit       init_mode="random" (seed = draw), ladder schedule
  rinit+bag   both randomized (paired draws)
`as-` prefix: the same group under arm_cost + strip (later board).

Reads (pre-registered, not a bar): a cell is ORDER-invariant if the
bag group's range of legal_acl <= max(0.3, 0.05*ladder) and its mean
equals ladder within that; INIT-invariant likewise for rinit. Cells
failing order-invariance are family/evaluator defects to name, not
schedule findings. Any stopped_by == "deadline" row is a calibration
failure (TIMEOUT is a safety net only).

Run:  nohup .venv/bin/python docs/paper2/data/sched_probe.py \
        [smoke] [group ...] [budget=N] [draws=K] \
        > docs/paper2/data/sched_probe.log 2>&1 &
Sentinel: done-probe.
"""
import csv
import os
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 1800          # safety only; placement deadline = 900 s
DRAWS = 5
SMOKE_ASKS = 3000
DEFAULT_ASKS = 3000
# per-cell work budgets (DP asks), filled from the smoke calibration:
# max(2 x ladder's fixpoint asks, asks/s x 60 s), rounded to 500
# smoke (load ~120): asks/s turán 95, ws 42, grid 130; all three were
# budget-bound at 3000 asks after 1-2 passes (no fixpoint), and the
# turán crystal needs ~12k asks (240 s at ~100 asks/s), so budgets are
# set by what the ladder needs to reach its known answer, not by 60 s
BUDGET = {
    "K100": 10000, "K140": 12000, "ER100_d10": 8000,
    "turan_n162": 15000, "spin_glass_n163": 12000,
    "regular_n316": 8000, "ws_n486": 6000,
    "grid_200": 8000, "honeycomb_200": 8000, "king_graph_196": 8000,
}
GROUPS = ("ladder", "rung", "bag", "rinit", "rinit+bag")
BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
]
SMOKE_CELLS = ("grid_200", "ws_n486", "turan_n162")
SMOKE_GROUPS = ("ladder", "bag", "rinit")
DIAG_KEYS = (
    "init_wall", "arrange_wall", "seat_passes", "asks", "bookmark_asks",
    "stopped_by", "sched", "interleave_accepts", "interleave_declines",
    "interleave_noops", "readouts", "bookmark_readouts", "legal_acl",
    "legal_max_chain", "judge", "judge_pen", "plane_stair", "plane_bars",
    "strip_miss", "projection_misses", "proj_pen", "convert_miss",
    "mm_skipped", "certified", "adopt_worse")


def _kw(group, draw):
    base = group[3:] if group.startswith("as-") else group
    kw = {"tail": "none"}
    if group.startswith("as-"):
        kw.update(arm_cost=True, strip=True)
    seed = 0
    if base in ("rung", "bag"):
        kw.update(sched=base, sched_seed=draw)
    elif base == "rinit":
        kw.update(init_mode="random")
        seed = draw
    elif base == "rinit+bag":
        kw.update(init_mode="random", sched="bag", sched_seed=draw)
        seed = draw
    elif base != "ladder":
        raise ValueError(group)
    return kw, seed


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
    cell, fabric, gid, group, draw, budget = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    from ember_qc.algorithms.factored.placement import AttractConfig
    from dataclasses import fields
    kw, seed = _kw(group, draw)
    kw["max_asks"] = int(budget)
    known = {f.name for f in fields(AttractConfig)}
    unknown = set(kw) - known
    assert not unknown, f"typo'd kwargs would silently measure control: {unknown}"
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = r.get("diag", {})
    row = dict(cell=cell, fabric=fabric, gid=gid, group=group, draw=draw,
               seed=seed, sched=kw.get("sched", "ladder"),
               sched_seed=kw.get("sched_seed", 0),
               init_mode=kw.get("init_mode", "spectral"),
               max_asks=int(budget), final_acl=acl, max_chain=mx,
               traj=("|".join(str(x) for x in d.get("accept_traj", []))
                     or None))
    for k in DIAG_KEYS:
        row[k] = d.get(k)
    row["error"] = (r.get("error") or "")[:80] or None
    row["time"] = round(time.perf_counter() - t0, 1)
    return row


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def _std(vals):
    vals = [v for v in vals if v is not None]
    return round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0


def main():
    args = sys.argv[1:]
    smoke = "smoke" in args
    groups = tuple(a for a in args if a in GROUPS
                   or (a.startswith("as-") and a[3:] in GROUPS))
    budget_all = None
    draws = DRAWS
    for a in args:
        if a.startswith("budget="):
            budget_all = int(a.split("=", 1)[1])
        if a.startswith("draws="):
            draws = int(a.split("=", 1)[1])
    if smoke:
        groups = groups or SMOKE_GROUPS
        cells = [c for c in BOARD if c[0] in SMOKE_CELLS]
        draws = 1
        budget_all = budget_all or SMOKE_ASKS
    else:
        groups = groups or GROUPS
        cells = list(BOARD)
    tag = "smoke" if smoke else "board"
    out = os.path.join(HERE, f"sched_probe_{tag}.csv")
    jobs = []
    for c, f, g in cells:
        budget = budget_all or BUDGET.get(c, DEFAULT_ASKS)
        for grp in groups:
            nd = 1 if grp.endswith("ladder") else draws
            for d in range(1, nd + 1):
                jobs.append((c, f, g, grp, d, budget))
    print(f"{tag}: {len(cells)} cells, groups {groups}, draws {draws}, "
          f"{len(jobs)} jobs; load {os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=min(24, len(jobs))) as ex:
        for row in ex.map(_run, jobs):
            aw = row["arrange_wall"] or 0.0
            rate = round(row["asks"] / aw, 1) if (row["asks"] and aw) else None
            print(f"{row['fabric']} {row['cell']:<16} {row['group']:<10} "
                  f"d{row['draw']}: lacl={row['legal_acl']} "
                  f"lmx={row['legal_max_chain']} asks={row['asks']} "
                  f"bm={row['bookmark_asks']} stop={row['stopped_by']} "
                  f"passes={row['seat_passes']} aw={aw} asks/s={rate} "
                  f"stair={row['plane_stair']} cmiss={row['convert_miss']} "
                  f"cert={row['certified']} mmskip={row['mm_skipped']} "
                  f"err={row['error']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print("\nsummary per (cell, group): legal_acl mean/std/min/max, "
          "legal_max_chain mean/max, asks, bookmark_asks, stopped_by")
    order_map, init_map, agree = [], [], []
    for cell, fabric, _ in cells:
        lad = [r for r in rows if r["cell"] == cell and r["group"] == "ladder"]
        lad_acl = _mean([r["legal_acl"] for r in lad])
        tol = max(0.3, 0.05 * lad_acl) if lad_acl else 0.3
        print(f"{fabric} {cell:<16} ladder lacl={lad_acl} "
              f"lmx={_mean([r['legal_max_chain'] for r in lad])} "
              f"asks={_mean([r['asks'] for r in lad])} "
              f"stop={Counter(r['stopped_by'] for r in lad)}")
        cell_ok = lad_acl is not None
        for grp in groups:
            if grp == "ladder":
                continue
            sel = [r for r in rows if r["cell"] == cell and r["group"] == grp]
            acls = [r["legal_acl"] for r in sel if r["legal_acl"] is not None]
            if not acls:
                print(f"    {grp:<10} no legal results")
                cell_ok = False
                continue
            rng_ = round(max(acls) - min(acls), 3)
            m = _mean(acls)
            dl = round(m - lad_acl, 3) if lad_acl is not None else None
            print(f"    {grp:<10} n={len(acls)} lacl={m} sd={_std(acls)} "
                  f"min={min(acls)} max={max(acls)} range={rng_} "
                  f"d={dl:+.3f} " if dl is not None else
                  f"    {grp:<10} n={len(acls)} lacl={m} range={rng_} ",
                  end="")
            print(f"lmx={_mean([r['legal_max_chain'] for r in sel])}/"
                  f"{max(r['legal_max_chain'] or 0 for r in sel)} "
                  f"asks={_mean([r['asks'] for r in sel])} "
                  f"bm={_mean([r['bookmark_asks'] for r in sel])} "
                  f"stop={dict(Counter(r['stopped_by'] for r in sel))}")
            bad = rng_ > tol or (dl is not None and abs(dl) > tol)
            if bad:
                (order_map if "bag" in grp or "rung" in grp
                 else init_map).append((cell, grp, m, rng_, dl))
                cell_ok = False
        if cell_ok:
            agree.append(cell)
    print("\nMAP — order-sensitive (bag/rung range or mean beyond tol):")
    for t in order_map:
        print("   ", t)
    print("MAP — init-sensitive (rinit range or mean beyond tol):")
    for t in init_map:
        print("   ", t)
    print("MAP — order- and init-free cells (every group within tol of ladder):",
          agree)
    dl_rows = [r for r in rows if r["stopped_by"] == "deadline"]
    if dl_rows:
        print("CALIBRATION FAILURE — deadline-bound rows:",
              [(r["cell"], r["group"], r["draw"]) for r in dl_rows])
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
