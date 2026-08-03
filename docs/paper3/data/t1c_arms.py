"""§4.15 T1c (arm rows): p3-mm-beta / p3-mm-beta-fb on the Z12 deg-10 ladder.

Complements p6_probes.py --topo Z12 --confirm-beta (the 900 switch rows):
this runner adds the 150 REGISTERED-ARM rows the pre-registration lists —
cells n in {100, 140, 180} at p = 10/(n-1), instance seeds 101-105, algo
seeds 0-4, 60 s, target zephyr_graph(12). Same row schema and acl_spur
convention as p6_probes (terminal_polish; rule 3), so rows pair against the
p6 stock switch rows at identical (inst_seed, algo_seed) — the script route.

Run AFTER the p6 confirm-beta batch; the summary pairs vs its CSV when
present and prints the §4.15 arm bars:
  - p3-mm-beta-fb: success == stock exactly per cell (the fallback guarantee)
  - p3-mm-beta: engaged below the 0.11 gate on every ladder cell (density
    0.101 / 0.072 / 0.056); ACL read is informational at 5 seeds (T2 owns
    the confirm).

Usage: .venv/bin/python docs/paper3/data/t1c_arms.py [--workers N] [--smoke]
       [--resume]
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
CSV_PATH = os.path.join(HERE, "t1c_arms_z12.csv")
SUMMARY_PATH = os.path.join(HERE, "t1c_arms_z12_summary.txt")
P6_CSV = os.path.join(HERE, "p6_probes_confirm_beta_z12.csv")

FIELDS = ["topo", "n", "p", "inst_seed", "arm", "family", "algo_seed",
          "switch_val", "status", "success", "acl", "acl_spur", "max_chain",
          "qubits", "wall", "n_edges", "err"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed"]

TOPO = "Z12"
CELLS = [(n, 10.0 / (n - 1)) for n in (100, 140, 180)]
INST_SEEDS = (101, 102, 103, 104, 105)
ALGO_SEEDS = (0, 1, 2, 3, 4)
ARMS = ("p3-mm-beta", "p3-mm-beta-fb")
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
    except Exception as e:   # belt: benchmark_one never raises
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
    stock = {}
    if os.path.exists(P6_CSV):
        with open(P6_CSV, newline="") as fh:
            for r in csv.DictReader(fh):
                if r["arm"] == "stock" and int(r["algo_seed"]) in ALGO_SEEDS:
                    stock[(r["n"], r["inst_seed"], r["algo_seed"])] = r
    lines = ["T1c arm rows (Z12 deg-10 ladder) — §4.15 beta-arm bars", ""]
    out = lines.append
    for n, p in CELLS:
        srows = [r for r in stock.values() if r["n"] == str(n)]
        s_ok = sum(1 for r in srows if r["success"] == "1")
        for arm in ARMS:
            arows = [r for r in rows if r["arm"] == arm and r["n"] == str(n)]
            a_ok = sum(1 for r in arows if r["success"] == "1")
            deltas = []
            for r in arows:
                s = stock.get((r["n"], r["inst_seed"], r["algo_seed"]))
                if (s and r["success"] == "1" and s["success"] == "1"
                        and r["acl_spur"] and s["acl_spur"]):
                    deltas.append(float(r["acl_spur"]) - float(s["acl_spur"]))
            med = (f"med dACL_spur {statistics.median(deltas):+7.3f} "
                   f"(pairs {len(deltas)})" if deltas else "no stock pairs")
            out(f"n={n:3d}: {arm:15s} success {a_ok:2d}/{len(arows):2d} "
                f"(stock {s_ok:2d}/{len(srows):2d})  {med}")
        if srows:
            fb = [r for r in rows if r["arm"] == "p3-mm-beta-fb"
                  and r["n"] == str(n)]
            fb_ok = sum(1 for r in fb if r["success"] == "1")
            keys_fb = {(r["inst_seed"], r["algo_seed"]) for r in fb}
            s_sub = sum(1 for r in stock.values() if r["n"] == str(n)
                        and (r["inst_seed"], r["algo_seed"]) in keys_fb
                        and r["success"] == "1")
            verdict = "PASS" if fb_ok == s_sub else "FAIL"
            out(f"        bar[-fb success == stock at shared seeds]: "
                f"{fb_ok} vs {s_sub} -> {verdict}")
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

    cells, insts, seeds, arms = CELLS, INST_SEEDS, ALGO_SEEDS, ARMS
    if args.smoke:
        cells, insts, seeds = cells[:1], insts[:1], seeds[:1]

    done = set()
    if args.resume and os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="") as fh:
            done = {tuple(r[k] for k in KEY_FIELDS)
                    for r in csv.DictReader(fh)}
    tasks = [(n, p, i, a, s) for n, p in cells for i in insts
             for a in arms for s in seeds
             if (TOPO, str(n), str(p), str(i), a, str(s)) not in done]
    print(f"{len(tasks)} tasks ({len(done)} already done)", flush=True)

    new_file = not os.path.exists(CSV_PATH)
    t0 = time.time()
    with open(CSV_PATH, "a", newline="") as fh:
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
    print("T1C_ARMS_DONE")


if __name__ == "__main__":
    main()
