"""§4.17 T3a: the mm-first beta arm on the Z12 deg-10 ladder.

Arms {minorminer, p3-mm-beta-fb, p3-mm-beta-mf} x cells n in {100,140,180}
(p = 10/(n-1)) x inst seeds 101-105 x algo seeds 0-14, 60 s, target
zephyr_graph(12). Same row schema + terminal_polish acl_spur convention as
t1c_arms.py; ALL pairing is within-batch at shared (inst_seed, algo_seed) —
the script route.

Summary prints the §4.17 T3 bars verbatim:
  (1) mf success == minorminer EXACTLY per cell at shared seeds;
  (2) mf vs minorminer: median dACL_spur < -1% AND >= 60%W on >= 2/3 cells;
  (3) mf vs -fb at shared seeds: median <= 0 and never a success deficit.

Usage: .venv/bin/python docs/paper3/data/t3_beta_mf.py [--workers N]
       [--smoke] [--resume]
"""
from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _runner_common import make_instance, terminal_polish  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "t3_beta_mf_z12.csv")
SUMMARY_PATH = os.path.join(HERE, "t3_beta_mf_z12_summary.txt")

FIELDS = ["topo", "n", "p", "inst_seed", "arm", "family", "algo_seed",
          "switch_val", "status", "success", "acl", "acl_spur", "max_chain",
          "qubits", "wall", "n_edges", "err"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed"]

TOPO = "Z12"
CELLS = [(n, 10.0 / (n - 1)) for n in (100, 140, 180)]
INST_SEEDS = (101, 102, 103, 104, 105)
ALGO_SEEDS = tuple(range(15))
ARMS = ("minorminer", "p3-mm-beta-fb", "p3-mm-beta-mf")
TIMEOUT = 60.0
POLISH_DEADLINE_S = 5.0

_G = {}


def _init_worker():
    import dwave_networkx as dnx
    from ember_qc.embedding_backend import build_adjacency
    tgt = dnx.zephyr_graph(12)
    _G["target"] = tgt
    _G["adj"] = build_adjacency(tgt)


def _acl(emb) -> float:
    return sum(len(c) for c in emb.values()) / len(emb)


def run_one(task):
    n, p, inst_seed, arm, algo_seed = task
    from ember_qc.benchmark import benchmark_one
    from ember_qc.embedding_backend import is_valid_embedding

    src = make_instance(n, p, inst_seed)
    row = {"topo": TOPO, "n": n, "p": p, "inst_seed": inst_seed, "arm": arm,
           "family": "arm", "algo_seed": algo_seed, "switch_val": "",
           "status": "", "success": 0, "acl": "", "acl_spur": "",
           "max_chain": "", "qubits": "", "wall": "",
           "n_edges": src.number_of_edges(), "err": ""}
    t0 = time.perf_counter()
    try:
        r = benchmark_one(src, _G["target"], arm, timeout=TIMEOUT,
                          seed=int(algo_seed))
    except Exception as e:
        row.update(status="CRASH", wall=round(time.perf_counter() - t0, 4),
                   err=f"{type(e).__name__}: {e}"[:200])
        return row
    row["wall"] = round(r.wall_time if r.wall_time is not None
                        else time.perf_counter() - t0, 4)
    emb = r.embedding or {}
    if emb and is_valid_embedding(emb, src, _G["target"], adj=_G["adj"]):
        chains = list(emb.values())
        row.update(status="SUCCESS", success=1, acl=round(_acl(emb), 4),
                   max_chain=max(len(c) for c in chains),
                   qubits=sum(len(c) for c in chains))
        pol = terminal_polish(emb, src, _G["target"],
                              deadline_s=POLISH_DEADLINE_S, adj=_G["adj"])
        row["acl_spur"] = round(_acl(pol), 4)
    else:
        row["status"] = "TIMEOUT" if row["wall"] >= TIMEOUT - 0.05 else "FAILURE"
        row["err"] = (getattr(r, "error", "") or "")[:200]
    return row


def summarize():
    with open(CSV_PATH, newline="") as fh:
        rows = list(csv.DictReader(fh))
    by = {}
    for r in rows:
        by.setdefault((r["n"], r["inst_seed"], r["algo_seed"]), {})[r["arm"]] = r
    lines = ["T3a mm-first beta on the Z12 deg-10 ladder — §4.17 bars", ""]
    out = lines.append
    bar1_all, bar2_cells, bar3_ok = True, 0, True
    for n, p in CELLS:
        keys = [k for k in by if k[0] == str(n)]
        mm_ok = sum(1 for k in keys if by[k].get("minorminer", {}).get("success") == "1")
        mf_ok = sum(1 for k in keys if by[k].get("p3-mm-beta-mf", {}).get("success") == "1")
        fb_ok = sum(1 for k in keys if by[k].get("p3-mm-beta-fb", {}).get("success") == "1")
        mm_set = {k for k in keys if by[k].get("minorminer", {}).get("success") == "1"}
        mf_set = {k for k in keys if by[k].get("p3-mm-beta-mf", {}).get("success") == "1"}
        exact = mm_set == mf_set
        bar1_all &= exact

        def paired(a, b):
            ds, base = [], []
            for k in keys:
                ra, rb = by[k].get(a), by[k].get(b)
                if (ra and rb and ra["success"] == "1" and rb["success"] == "1"
                        and ra["acl_spur"] and rb["acl_spur"]):
                    ds.append(float(ra["acl_spur"]) - float(rb["acl_spur"]))
                    base.append(float(rb["acl_spur"]))
            return ds, base

        ds, base = paired("p3-mm-beta-mf", "minorminer")
        if ds:
            med = statistics.median(ds)
            pct = 100.0 * med / statistics.median(base)
            winr = 100.0 * sum(1 for d in ds if d < 0) / len(ds)
            cell_ok = pct < -1.0 and winr >= 60
            bar2_cells += cell_ok
        else:
            med = pct = winr = float("nan")
            cell_ok = False
        dfb, _ = paired("p3-mm-beta-mf", "p3-mm-beta-fb")
        med_fb = statistics.median(dfb) if dfb else float("nan")
        fb_deficit = mf_ok < fb_ok
        bar3_ok &= (not fb_deficit) and (not dfb or med_fb <= 0)
        out(f"n={n:3d}: mm {mm_ok:2d}/{len(keys):2d}  fb {fb_ok:2d}  "
            f"mf {mf_ok:2d}  succ-set==mm {'YES' if exact else 'NO'} | "
            f"mf vs mm med {med:+.3f} ({pct:+.2f}%) W {winr:.0f}% "
            f"({len(ds)}p) {'CELL-OK' if cell_ok else ''} | "
            f"mf vs fb med {med_fb:+.3f} ({len(dfb)}p)")
    out("")
    out(f"BAR1 success == stock exactly, every cell: "
        f"{'PASS' if bar1_all else 'FAIL'}")
    out(f"BAR2 median < -1% AND >=60%W on >=2/3 cells: {bar2_cells}/3 -> "
        f"{'PASS' if bar2_cells >= 2 else 'FAIL'}")
    out(f"BAR3 vs -fb: median <= 0 and no success deficit: "
        f"{'PASS' if bar3_ok else 'FAIL'}")
    text = "\n".join(lines)
    print("\n" + text)
    with open(SUMMARY_PATH, "w") as fh:
        fh.write(text + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    cells, insts, seeds = CELLS, INST_SEEDS, ALGO_SEEDS
    if args.smoke:
        cells, insts, seeds = cells[:1], insts[:1], seeds[:2]

    done = set()
    if args.resume and os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="") as fh:
            done = {tuple(r[k] for k in KEY_FIELDS)
                    for r in csv.DictReader(fh)}
    tasks = [(n, p, i, a, s) for n, p in cells for i in insts
             for a in ARMS for s in seeds
             if (TOPO, str(n), str(p), str(i), a, str(s)) not in done]
    print(f"{len(tasks)} tasks ({len(done)} already done)", flush=True)

    from ember_qc.algorithms.minorminer_forked import _find_so
    if _find_so() is None:
        sys.exit("fork .so not built (scripts/build_mm_fork.sh)")

    new_file = not (os.path.exists(CSV_PATH) and args.resume)
    t0 = time.time()
    with open(CSV_PATH, "a" if args.resume else "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        with Pool(args.workers, initializer=_init_worker) as pool:
            for k, row in enumerate(pool.imap_unordered(run_one, tasks), 1):
                w.writerow(row)
                fh.flush()
                print(f"[{k}/{len(tasks)}] n{row['n']} i{row['inst_seed']} "
                      f"{row['arm']} s{row['algo_seed']}: {row['status']} "
                      f"{row['wall']}s", flush=True)
    print(f"all tasks done in {time.time() - t0:.0f}s")
    if not args.smoke:
        summarize()
    print("T3_BETA_MF_DONE")


if __name__ == "__main__":
    main()
