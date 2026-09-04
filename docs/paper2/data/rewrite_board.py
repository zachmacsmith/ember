"""
docs/paper2/data/rewrite_board.py
=================================
s3.127 — the paired board of the rewrite. Arms:

  new        the rewrite, tail="none": the engine's own answer at a
             WORK budget (max_asks per cell), timeout as a safety net
  new+mm     the rewrite, tail="mm", 60 s wall (the shipped shape)
  mm         stock minorminer, 60 s wall, same seed
  old        the archived default (a worktree at the archive commit),
             60 s wall — run SEPARATELY with the archived source first
             on PYTHONPATH:
               PYTHONPATH=/data/max/ember-archive/packages/ember-qc/src \\
               .venv/bin/python docs/paper2/data/rewrite_board.py old
             (the archived engine ignores unknown kwargs; the old
             engine's init is its own default there)

Paired by (cell, seed). Summary: mean ACL, max chain, success count
per arm, and d = arm - mm.

Run:  nohup .venv/bin/python docs/paper2/data/rewrite_board.py [arm ...]
        > docs/paper2/data/rewrite_board.log 2>&1 &
Then: .venv/bin/python docs/paper2/data/rewrite_board.py summary
Sentinel: done-board.
"""
import csv
import glob
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
WALL = 60
SEEDS = (0, 1, 2)
DEEP_SEEDS = tuple(range(10))
BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
]
DEEP_CELLS = ("turan_n162", "ws_n486", "regular_n316", "ER100_d10")
BUDGET = {"K100": 10000, "K140": 12000, "ER100_d10": 8000,
          "turan_n162": 15000, "spin_glass_n163": 12000,
          "regular_n316": 8000, "ws_n486": 6000, "grid_200": 8000,
          "honeycomb_200": 8000, "king_graph_196": 8000}
ARMS = ("new", "new+mm", "mm")


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
    tgt = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    d = {}
    err = None
    if arm == "mm":
        import minorminer
        emb = minorminer.find_embedding(src, list(tgt.edges()),
                                        random_seed=seed, timeout=WALL)
        emb = emb or {}
    else:
        from ember_qc.algorithms.factored import attract_embed
        if arm == "new":
            r = attract_embed(src, tgt, timeout=1800, seed=seed,
                              tail="none", max_asks=BUDGET[cell])
        elif arm == "new+mm":
            r = attract_embed(src, tgt, timeout=WALL, seed=seed, tail="mm")
        else:   # old: the archived default from the worktree
            r = attract_embed(src, tgt, timeout=WALL, seed=seed)
        emb = r.get("embedding") or {}
        d = r.get("diag", {})
        err = (r.get("error") or "")[:60] or None
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    return dict(cell=cell, arm=arm, seed=seed, acl=acl, max_chain=mx,
                legal_acl=d.get("legal_acl"), stopped_by=d.get("stopped_by"),
                asks=d.get("asks"), bookmark_asks=d.get("bookmark_asks"),
                pen=d.get("pen"), certified=d.get("certified"),
                mm_skipped=d.get("mm_skipped"), error=err,
                wall=round(time.perf_counter() - t0, 1))


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def summary():
    rows = []
    for f in glob.glob(os.path.join(HERE, "rewrite_board_*.csv")):
        with open(f) as fh:
            for r in csv.DictReader(fh):
                for k in ("acl", "legal_acl"):
                    r[k] = float(r[k]) if r[k] not in ("", "None") else None
                r["max_chain"] = (int(float(r["max_chain"]))
                                  if r["max_chain"] not in ("", "None")
                                  else None)
                rows.append(r)
    arms = sorted({r["arm"] for r in rows},
                  key=lambda a: ("mm", "old", "new", "new+mm").index(a)
                  if a in ("mm", "old", "new", "new+mm") else 9)
    print("paired board — mean ACL (successes) / mean max chain; "
          "d = arm − mm on the seeds both have")
    for cell, _f, _g in BOARD:
        line = f"{cell:<16}"
        mm_by_seed = {r["seed"]: r["acl"] for r in rows
                      if r["cell"] == cell and r["arm"] == "mm"}
        for arm in arms:
            sel = [r for r in rows if r["cell"] == cell and r["arm"] == arm]
            if not sel:
                continue
            paired = [(r["acl"], mm_by_seed.get(r["seed"])) for r in sel
                      if r["acl"] is not None
                      and mm_by_seed.get(r["seed"]) is not None]
            dlt = (round(sum(a - b for a, b in paired) / len(paired), 3)
                   if paired and arm != "mm" else None)
            line += (f" | {arm}={_mean([r['acl'] for r in sel])}"
                     f"({sum(1 for r in sel if r['acl'])}/{len(sel)})"
                     f" mx={_mean([r['max_chain'] for r in sel])}"
                     + (f" d={dlt:+.3f}" if dlt is not None else ""))
        print(line)


def main():
    args = sys.argv[1:]
    if args == ["summary"]:
        summary()
        return
    arms = tuple(a for a in args if a in ARMS + ("old",)) or ARMS
    tag = "-".join(arms).replace("+", "")
    jobs = []
    for c, f, g in BOARD:
        seeds = DEEP_SEEDS if c in DEEP_CELLS else SEEDS
        for arm in arms:
            for s in seeds:
                jobs.append((c, f, g, arm, s))
    print(f"board {tag}: arms {arms}, {len(jobs)} jobs; load "
          f"{os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=min(24, len(jobs))) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']:<16} {row['arm']:<7} s{row['seed']}: "
                  f"acl={row['acl']} mx={row['max_chain']} "
                  f"lacl={row['legal_acl']} stop={row['stopped_by']} "
                  f"bm={row['bookmark_asks']}/{row['asks']} pen={row['pen']} "
                  f"cert={row['certified']} mmskip={row['mm_skipped']} "
                  f"err={row['error']} ({row['wall']}s)", flush=True)
            rows.append(row)
    out = os.path.join(HERE, f"rewrite_board_{tag}.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out)
    summary()
    print("load at end:", os.getloadavg(), flush=True)
    print("done-board", flush=True)


if __name__ == "__main__":
    main()
