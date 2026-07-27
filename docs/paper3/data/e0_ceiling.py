"""
docs/paper3/data/e0_ceiling.py
===============================
E0 ceiling: the best-of-K deflator control (protocol rule 2 — a MEASUREMENT of
the multi-run freebie, never a proposed algorithm). Stock minorminer at equal
wall-clock, sequential restarts:

    1 x 60 s   vs   best-of-3 x 20 s   vs   best-of-6 x 10 s   vs
    best-of-12 x 5 s

Per (cell, inst_seed, base_seed): each restart k uses seed base_seed*100+k;
the reported embedding is the successful restart with the lowest RAW acl; the
row records that run's acl, its acl_spur (terminal spur-prune, protocol rule
3), and the number of successful restarts. The summary pairs every K>1 arm
against the single-60s arm by (inst_seed, base_seed) on both-succeed pairs —
what the best-of-K freebie is worth at equal wall-clock.

Cells via --cells "topo:n:p,..." (default below). Instance seeds 101-105 (DEV),
base algo seeds 0-4. MM-family only, so no watchdog (protocol route choice).
Writes one flushed row per (cell, inst, base, K) to e0_ceiling.csv next to this
file (resume with --resume); prints + writes e0_ceiling_summary.txt.

Run:
  .venv/bin/python docs/paper3/data/e0_ceiling.py --workers 8            # full
  .venv/bin/python docs/paper3/data/e0_ceiling.py --smoke --workers 2    # local
Flags: --workers N | --smoke | --resume | --cells "topo:n:p,..."
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import csv
import multiprocessing
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _runner_common import (  # noqa: E402
    acl, append_row, build_target, clean_err, load_done_keys, make_instance,
    stringify_key, terminal_polish,
)

from ember_qc.benchmark import benchmark_one  # noqa: E402
from ember_qc.embedding_backend import build_adjacency  # noqa: E402

CSV_PATH = os.path.join(HERE, "e0_ceiling.csv")
SUMMARY_PATH = os.path.join(HERE, "e0_ceiling_summary.txt")

DEFAULT_CELLS = ("P16:100:0.5,P16:140:0.3,P16:100:0.9,P16:220:0.12,"
                 "Z12:100:0.5,Z12:140:0.3")
INST_SEEDS = (101, 102, 103, 104, 105)   # DEV registry (protocol rule 4)
BASE_SEEDS = (0, 1, 2, 3, 4)
SCHEDULE = [(1, 60.0), (3, 20.0), (6, 10.0), (12, 5.0)]   # (K, per-run s)
POLISH_DEADLINE_S = 5.0

SMOKE_SCHEDULE = [(1, 10.0), (3, 10.0 / 3.0)]   # 10 s total budget
SMOKE_CELLS = "P16:100:0.5"
SMOKE_INST_SEEDS = (101,)
SMOKE_BASE_SEEDS = (0, 1)

FIELDS = ["topo", "n", "p", "inst_seed", "arm", "base_seed", "K", "per_run_s",
          "status", "success", "n_success", "acl", "acl_spur", "max_chain",
          "qubits", "time", "err"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "arm", "base_seed"]


def arm_name(K, per_run_s):
    return f"mm-bo{K}x{per_run_s:g}"


def parse_cells(spec):
    cells = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        topo, n, p = part.split(":")
        if topo not in ("P16", "Z12"):
            raise ValueError(f"unknown topology in --cells: {topo!r}")
        cells.append((topo, int(n), float(p)))
    return cells


# ──────────────────────────────────────────────────────────────────────────────
# Worker
# ──────────────────────────────────────────────────────────────────────────────

_G = {}   # topo -> {"target", "adj"}


def _init_worker(topo_names):
    for t in topo_names:
        tgt = build_target(t)
        _G[t] = {"target": tgt, "adj": build_adjacency(tgt)}


def run_task(task):
    topo, n, p, inst_seed, base_seed, K, per_run_s = task
    src = make_instance(n, p, inst_seed)
    g = _G[topo]
    row = {"topo": topo, "n": n, "p": p, "inst_seed": inst_seed,
           "arm": arm_name(K, per_run_s), "base_seed": base_seed, "K": K,
           "per_run_s": round(per_run_s, 4), "status": "", "success": 0,
           "n_success": 0, "acl": "", "acl_spur": "", "max_chain": "",
           "qubits": "", "time": "", "err": ""}
    t0 = time.perf_counter()
    best = None
    n_success = 0
    last_err = ""
    for k in range(K):
        seed = base_seed * 100 + k
        r = benchmark_one(src, g["target"], "minorminer",
                          timeout=per_run_s, seed=seed)
        if r.success and r.is_valid and r.embedding:
            n_success += 1
            if best is None or r.avg_chain_length < best.avg_chain_length:
                best = r
        else:
            last_err = r.error or r.status
    row["time"] = round(time.perf_counter() - t0, 4)
    row["n_success"] = n_success
    if best is None:
        row["status"] = "FAILURE"
        row["err"] = clean_err(last_err)
        return row
    row["status"] = "SUCCESS"
    row["success"] = 1
    row["acl"] = round(best.avg_chain_length, 4)
    row["max_chain"] = best.max_chain_length
    row["qubits"] = best.total_qubits_used
    pol = terminal_polish(best.embedding, src, g["target"],
                          deadline_s=POLISH_DEADLINE_S, adj=g["adj"])
    row["acl_spur"] = round(acl(pol), 4)
    return row


# ──────────────────────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────────────────────

def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    out("=" * 100)
    out("E0 ceiling summary — the best-of-K freebie at equal wall-clock "
        "(protocol rule 2 deflator)")
    out("dACL = best-of-K arm - single-run arm, paired by (inst_seed, "
        "base_seed) on both-succeed pairs")
    out("=" * 100)
    cells = sorted({(r["topo"], float(r["p"]), int(r["n"])) for r in rows},
                   key=lambda c: (c[0], -c[1], c[2]))
    for topo, p, n in cells:
        cell = [r for r in rows
                if r["topo"] == topo and float(r["p"]) == p and int(r["n"]) == n]
        # Group by the STORED arm string (never reconstruct the name from the
        # CSV-rounded per_run_s), ordered by K.
        arm_rows = {}
        for r in cell:
            arm_rows.setdefault((int(r["K"]), r["arm"]), []).append(r)
        arms = sorted(arm_rows)
        base_arm = min(arms)[1]   # smallest-K arm is the baseline
        base_ok = {(r["inst_seed"], r["base_seed"]):
                   (float(r["acl"]), float(r["acl_spur"]))
                   for r in cell if r["arm"] == base_arm
                   and r["success"] == "1" and r["acl_spur"]}
        out("")
        out(f"-- {topo}  n={n}  p={p:g}   (baseline arm: {base_arm})")
        for K, name in arms:
            arows = arm_rows[(K, name)]
            n_ok = sum(1 for r in arows if r["success"] == "1")
            times = [float(r["time"]) for r in arows if r["time"]]
            mean_t = statistics.mean(times) if times else float("nan")
            succ_counts = [int(r["n_success"]) for r in arows]
            base = (f"  {name:12s} success {n_ok}/{len(arows)}  "
                    f"mean restarts-ok {statistics.mean(succ_counts):4.1f}/{K}"
                    f"  mean time {mean_t:6.1f}s")
            if name == base_arm:
                accs = [float(r["acl"]) for r in arows if r["success"] == "1"]
                sps = [float(r["acl_spur"]) for r in arows
                       if r["success"] == "1" and r["acl_spur"]]
                if accs:
                    base += (f"   acl mean {statistics.mean(accs):.3f}  "
                             f"acl_spur mean {statistics.mean(sps):.3f}")
                out(base)
                continue
            pairs = [((float(r["acl"]), float(r["acl_spur"])),
                      base_ok[(r["inst_seed"], r["base_seed"])])
                     for r in arows
                     if r["success"] == "1" and r["acl_spur"]
                     and (r["inst_seed"], r["base_seed"]) in base_ok]
            if pairs:
                d_raw = [a[0] - b[0] for a, b in pairs]
                d_spur = [a[1] - b[1] for a, b in pairs]
                win = sum(1 for d in d_raw if d < 0)
                loss = sum(1 for d in d_raw if d > 0)
                base += (f"   pairs {len(pairs):2d}  dACL mean "
                         f"{statistics.mean(d_raw):+7.3f} median "
                         f"{statistics.median(d_raw):+7.3f}  "
                         f"dACL_spur mean {statistics.mean(d_spur):+7.3f}  "
                         f"W/L/T {win}/{loss}/{len(d_raw) - win - loss}")
            else:
                base += "   [no both-succeed pairs vs baseline]"
            out(base)
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true",
                    help="single cell, K in {1,3}, 10 s total budget")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--cells", default=DEFAULT_CELLS,
                    help='comma list "topo:n:p" (topo in {P16, Z12})')
    return ap.parse_args()


def main():
    args = parse_args()
    if args.smoke:
        cells = parse_cells(SMOKE_CELLS)
        inst_seeds, base_seeds = SMOKE_INST_SEEDS, SMOKE_BASE_SEEDS
        schedule = SMOKE_SCHEDULE
    else:
        cells = parse_cells(args.cells)
        inst_seeds, base_seeds = INST_SEEDS, BASE_SEEDS
        schedule = SCHEDULE
    topos = tuple(sorted({c[0] for c in cells}))

    tasks = [(topo, n, p, i, b, K, per)
             for (topo, n, p) in cells
             for i in inst_seeds
             for b in base_seeds
             for (K, per) in schedule]
    total_planned = len(tasks)
    if args.resume:
        done = load_done_keys(CSV_PATH, KEY_FIELDS)
        tasks = [t for t in tasks
                 if stringify_key(t[0], t[1], t[2], t[3],
                                  arm_name(t[5], t[6]), t[4]) not in done]
        print(f"resume: {total_planned - len(tasks)} of {total_planned} tasks "
              f"already in {os.path.basename(CSV_PATH)}")
    print(f"cells={cells}  inst_seeds={inst_seeds}  base_seeds={base_seeds}  "
          f"schedule={[(K, round(s, 2)) for K, s in schedule]}  "
          f"tasks to run={len(tasks)}  workers={args.workers}")

    t0 = time.time()
    if tasks:
        # Same executor pattern as e0_crossover (uniform across e* runners).
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=_init_worker,
                                 initargs=(topos,)) as ex:
            futures = {ex.submit(run_task, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futures), 1):
                try:
                    row = fut.result()
                except Exception as exc:   # never let one row kill the batch
                    topo, n, p, inst_seed, base_seed, K, per = futures[fut]
                    row = {"topo": topo, "n": n, "p": p,
                           "inst_seed": inst_seed,
                           "arm": arm_name(K, per), "base_seed": base_seed,
                           "K": K, "per_run_s": round(per, 4),
                           "status": "CRASH", "success": 0, "n_success": 0,
                           "acl": "", "acl_spur": "", "max_chain": "",
                           "qubits": "", "time": "",
                           "err": clean_err(f"runner: {exc!r}")}
                append_row(CSV_PATH, FIELDS, row)
                a = f"acl={row['acl']}/{row['acl_spur']}" if row["success"] else ""
                print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                      f"{row['topo']} n{row['n']} p{row['p']:g} "
                      f"i{row['inst_seed']} {row['arm']} b{row['base_seed']}: "
                      f"{row['status']} ok{row['n_success']}/{row['K']} {a} "
                      f"{row['time']}s", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; "
          f"rows appended to {CSV_PATH}\n")

    text = summarize(CSV_PATH)
    print(text)
    with open(SUMMARY_PATH, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
