"""
docs/paper3/data/dev_suite.py
==============================
M3 shared dev-suite runner: every candidate arm on the FROZEN 14-cell dev suite
(protocol.md "Frozen dev suite", E0 §4.1 output 5), paired by literal
(inst_seed, algo_seed) through the script route (protocol rule 1).

Arms (select with --arms, comma-separated; default all):

  minorminer      stock minorminer 0.2.22 via benchmark_one (reference arm 1)
  mmfork-cuthill  the C++ fork guided by Cuthill-McKee, fallback=False (control)
  p3-template     P1 template arm (deterministic below K_max -> one run per
                  instance, recorded algo_seed -1; reference arm 2)
  p3-ate          P1 product arm (template + stock MM selector; seeded)
  p3-clmm         P2 faithful CLMM (seeded)
  p3-clmm-core    P2 degeneracy-core seeding (seeded)
  p3-mmpolish     P5 stock MM + anytime exact-repair polish (seeded)
  pssa            registry pssa (context arm; seeded)
  attraction      registry attraction (context arm; seeded)

Watchdog policy: EVERY arm except minorminer / mmfork-cuthill runs in a
per-run subprocess with a hard kill at timeout+30 s. The p3-* arms are
cooperative by contract, but the watchdog is cheap insurance (protocol route
choice: a hang stalls a whole batch); the two MM-family reference arms stay
exempt per protocol.

Every successful embedding from every arm gets the same deadline-bounded
terminal spur-prune; the CSV records both `acl` (raw) and `acl_spur`
(protocol rule 3). An extra `arm_meta` column carries compact JSON from the
arm's result metadata (e.g. p3-ate's winner + both internal ACLs).

Suite (frozen 2026-07-27; instance seeds 101-105, K_n cells 1 instance;
algo seeds 0-4, deterministic arms once; 60 s):
  P16: (100,0.2) (100,0.3) (140,0.12) (140,0.2) (140,1.0) (180,1.0) (160,0.05)
  Z12: (100,0.2) (100,0.3) (140,0.12) (140,0.2) (140,1.0) (179,1.0) (160,0.05)

Summary: per-cell paired dACL_spur vs BOTH reference arms (minorminer and
p3-template), win/loss/tie counts, success rates unpaired (rule 4).

Run:
  .venv/bin/python docs/paper3/data/dev_suite.py --workers 48          # hyde06
  .venv/bin/python docs/paper3/data/dev_suite.py --smoke --workers 4   # local
Flags: --workers N | --smoke | --resume | --topo P16|Z12|both | --arms a,b,...
--smoke writes to dev_suite_smoke.csv (smoke rows share cells with the full
grid at a shorter budget and must never enter the full CSV's resume keys).
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import csv
import json
import multiprocessing
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _runner_common import (  # noqa: E402
    acl, append_row, build_target, clean_err, load_done_keys, make_instance,
    run_arm_watchdogged, stringify_key, terminal_polish,
)

from ember_qc.benchmark import benchmark_one  # noqa: E402
from ember_qc.registry import ALGORITHM_REGISTRY  # noqa: E402
from ember_qc.embedding_backend import build_adjacency  # noqa: E402

CSV_PATH = os.path.join(HERE, "dev_suite.csv")
SUMMARY_PATH = os.path.join(HERE, "dev_suite_summary.txt")

TIMEOUT = 60.0                 # s per attempt (protocol rule 5)
WATCHDOG_GRACE = 30.0          # hard kill at timeout + grace (protocol)
POLISH_DEADLINE_S = 5.0        # terminal spur-prune budget (acl_spur)
INST_SEEDS = (101, 102, 103, 104, 105)   # DEV registry (protocol rule 4)
ALGO_SEEDS = (0, 1, 2, 3, 4)             # DEV algorithm seeds
DET_SEED = -1                  # recorded algo_seed for deterministic arms

# The frozen dev suite (protocol.md; E0 §4.1 output 5).
DEV_SUITE = {
    "P16": [(100, 0.2), (100, 0.3), (140, 0.12), (140, 0.2), (140, 1.0),
            (180, 1.0), (160, 0.05)],
    "Z12": [(100, 0.2), (100, 0.3), (140, 0.12), (140, 0.2), (140, 1.0),
            (179, 1.0), (160, 0.05)],
}

ARMS = ("minorminer", "mmfork-cuthill", "minorminer-layout", "p3-template",
        "p3-ate", "p3-clmm", "p3-clmm-core", "p3-mmpolish", "pssa", "attraction")
DETERMINISTIC_ARMS = {"p3-template"}          # once per instance, algo_seed -1
NO_WATCHDOG = {"minorminer", "mmfork-cuthill"}  # MM-family, protocol-exempt
REFERENCE_ARMS = ("minorminer", "p3-template")

# Smoke covers the three watch items: a plain cell, a K_n cell (make_instance
# p=1.0 path), and (160,0.05) (mmfork-cuthill sparse/disconnected-fix path).
SMOKE_CELLS = [("P16", 100, 0.3), ("P16", 140, 1.0), ("P16", 160, 0.05)]
SMOKE_TIMEOUT = 10.0

FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed", "status",
          "success", "acl", "acl_spur", "acl_pre", "max_chain", "qubits",
          "time", "n_edges", "err", "arm_meta"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed"]


# ──────────────────────────────────────────────────────────────────────────────
# Worker state
# ──────────────────────────────────────────────────────────────────────────────

_G = {}   # topo -> {"target", "adj"}


def _init_worker(topo_names):
    for t in topo_names:
        tgt = build_target(t)
        _G[t] = {"target": tgt, "adj": build_adjacency(tgt)}


def compact_meta(md, limit=300):
    """Scalar-only, compact-JSON view of an arm's result metadata."""
    if not md or not isinstance(md, dict):
        return ""
    flat = {k: v for k, v in md.items()
            if isinstance(v, (int, float, str, bool, type(None)))}
    if not flat:
        return ""
    try:
        s = json.dumps(flat, separators=(",", ":"), default=str)
    except Exception:
        return ""
    return s[:limit]


def _arm_registry(arm, src, topo, algo_seed, timeout):
    """Any registered algorithm through benchmark_one (protocol rule 1)."""
    kwargs = {"seed": int(algo_seed) if algo_seed >= 0 else 0}
    if arm.startswith("mmfork"):
        kwargs["fallback"] = False   # pure arm, never silently stock (protocol)
    r = benchmark_one(src, _G[topo]["target"], arm, timeout=timeout, **kwargs)
    ok = bool(r.success and r.is_valid and r.embedding)
    return {"success": ok, "status": r.status,
            "acl": r.avg_chain_length if ok else None,
            "max_chain": r.max_chain_length if ok else None,
            "qubits": r.total_qubits_used if ok else None,
            "time": r.wall_time,
            "embedding": r.embedding if ok else None,
            "metadata": r.metadata or {},
            "err": r.error or ""}


def run_task(task):
    topo, n, p, inst_seed, arm, algo_seed, timeout = task
    src = make_instance(n, p, inst_seed)
    g = _G[topo]
    row = {"topo": topo, "n": n, "p": p, "inst_seed": inst_seed, "arm": arm,
           "algo_seed": algo_seed, "status": "", "success": 0, "acl": "",
           "acl_spur": "", "acl_pre": "", "max_chain": "", "qubits": "",
           "time": "", "n_edges": src.number_of_edges(), "err": "",
           "arm_meta": ""}

    if arm.startswith("mmfork"):
        ok, msg = ALGORITHM_REGISTRY[arm].is_available()
        if not ok:
            row.update(status="UNAVAILABLE", err=clean_err(msg))
            return row

    if arm in NO_WATCHDOG:
        wstatus, res, werr = "OK", _arm_registry(arm, src, topo, algo_seed,
                                                 timeout), ""
    else:
        wstatus, res, werr = run_arm_watchdogged(
            _arm_registry, timeout, grace_s=WATCHDOG_GRACE,
            args=(arm, src, topo, algo_seed, timeout))

    if wstatus != "OK" or res is None:
        row["status"] = "WATCHDOG_KILLED" if wstatus == "KILLED" else "CRASH"
        row["time"] = round(timeout + WATCHDOG_GRACE, 4) if wstatus == "KILLED" else ""
        row["err"] = clean_err(werr or "arm returned no result")
        return row

    row["status"] = res.get("status", "FAILURE")
    row["time"] = round(float(res.get("time") or 0.0), 4)
    row["err"] = clean_err(res.get("err", ""))
    row["arm_meta"] = compact_meta(res.get("metadata"))
    if res.get("success") and res.get("embedding"):
        row["success"] = 1
        row["acl"] = round(res["acl"], 4)
        row["max_chain"] = res.get("max_chain", "")
        row["qubits"] = res.get("qubits", "")
        pol = terminal_polish(res["embedding"], src, g["target"],
                              deadline_s=POLISH_DEADLINE_S, adj=g["adj"])
        row["acl_spur"] = round(acl(pol), 4)
    return row


# ──────────────────────────────────────────────────────────────────────────────
# Task construction
# ──────────────────────────────────────────────────────────────────────────────

def inst_seeds_for(p, inst_seeds):
    """K_n cells are instance-seed-independent: run one instance."""
    return (inst_seeds[0],) if p >= 1.0 else tuple(inst_seeds)


def build_tasks(cells, arms, inst_seeds, algo_seeds, timeout):
    tasks = []
    for topo, n, p in cells:
        for inst_seed in inst_seeds_for(p, inst_seeds):
            for arm in arms:
                seeds = (DET_SEED,) if arm in DETERMINISTIC_ARMS else algo_seeds
                for s in seeds:
                    tasks.append((topo, n, p, inst_seed, arm, s, timeout))
    return tasks


# ──────────────────────────────────────────────────────────────────────────────
# Summary — paired vs BOTH reference arms (minorminer AND p3-template)
# ──────────────────────────────────────────────────────────────────────────────

def _pairs_vs_ref(arows, ref_by_pair, ref_by_inst, det_seed_str):
    """Both-succeed pairs of (arm_value, ref_value).

    Seeded arm rows pair per (inst_seed, algo_seed) against a seeded
    reference, or per inst_seed against a deterministic reference (one ref
    value per instance). Deterministic arm rows pair against every reference
    seed run on the same instance."""
    pairs = []
    for r in arows:
        if r["success"] != "1" or not r["acl_spur"]:
            continue
        a_val = float(r["acl_spur"])
        if r["algo_seed"] == det_seed_str:      # deterministic arm row
            if ref_by_pair is not None:
                pairs += [(a_val, v) for (i, _s), v in ref_by_pair.items()
                          if i == r["inst_seed"]]
            elif ref_by_inst is not None and r["inst_seed"] in ref_by_inst:
                pairs.append((a_val, ref_by_inst[r["inst_seed"]]))
        else:                                    # seeded arm row
            if ref_by_pair is not None:
                key = (r["inst_seed"], r["algo_seed"])
                if key in ref_by_pair:
                    pairs.append((a_val, ref_by_pair[key]))
            elif ref_by_inst is not None and r["inst_seed"] in ref_by_inst:
                pairs.append((a_val, ref_by_inst[r["inst_seed"]]))
    return pairs


def _fmt_pairs(tag, pairs):
    if not pairs:
        return f"{tag}: no pairs"
    deltas = [a - m for a, m in pairs]
    win = sum(1 for d in deltas if d < 0)
    loss = sum(1 for d in deltas if d > 0)
    tie = len(deltas) - win - loss
    ref_med = statistics.median(m for _a, m in pairs)
    med = statistics.median(deltas)
    pct = 100.0 * med / ref_med if ref_med else float("nan")
    return (f"{tag}: n={len(deltas):3d} med {med:+7.3f} ({pct:+6.1f}%) "
            f"W/L/T {win}/{loss}/{tie}")


def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    det = str(DET_SEED)
    lines = []
    out = lines.append
    out("=" * 100)
    out("M3 dev-suite summary — column: acl_spur (rule 3). dACL on both-succeed "
        "pairs (rule 4); success unpaired.")
    out("Two reference arms: vsMM = minorminer (paired per (inst, algo_seed)); "
        "vsTP = p3-template (deterministic,")
    out("one value per instance — every seeded row of an arm pairs against its "
        "instance's template value).")
    out("=" * 100)

    cells = sorted({(r["topo"], float(r["p"]), int(r["n"])) for r in rows},
                   key=lambda c: (c[0], -c[1], c[2]))
    arm_order = {a: i for i, a in enumerate(ARMS)}
    for topo, p, n in cells:
        cell = [r for r in rows
                if r["topo"] == topo and float(r["p"]) == p and int(r["n"]) == n]
        mm_ok = {(r["inst_seed"], r["algo_seed"]): float(r["acl_spur"])
                 for r in cell if r["arm"] == "minorminer"
                 and r["success"] == "1" and r["acl_spur"]}
        tp_ok = {r["inst_seed"]: float(r["acl_spur"])
                 for r in cell if r["arm"] == "p3-template"
                 and r["success"] == "1" and r["acl_spur"]}
        out("")
        out(f"-- {topo}  n={n}  p={p:g}"
            + ("" if mm_ok else "  [minorminer 0 successes]")
            + ("" if tp_ok else "  [p3-template 0 successes]"))
        arms_here = sorted({r["arm"] for r in cell},
                           key=lambda a: arm_order.get(a, 99))
        for arm in arms_here:
            arows = [r for r in cell if r["arm"] == arm]
            n_ok = sum(1 for r in arows if r["success"] == "1")
            times = sorted(float(r["time"]) for r in arows if r["time"])
            med_t = statistics.median(times) if times else float("nan")
            accs = [float(r["acl_spur"]) for r in arows
                    if r["success"] == "1" and r["acl_spur"]]
            base = (f"  {arm:14s} success {n_ok}/{len(arows)}  med t "
                    f"{med_t:7.2f}s  ")
            base += (f"acl_spur med {statistics.median(accs):7.3f}  "
                     if accs else "acl_spur med     n/a  ")
            parts = []
            if arm != "minorminer":
                parts.append(_fmt_pairs(
                    "vsMM", _pairs_vs_ref(arows, mm_ok, None, det)))
            if arm != "p3-template":
                parts.append(_fmt_pairs(
                    "vsTP", _pairs_vs_ref(arows, None, tp_ok, det)))
            out(base + "   ".join(parts))
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="M3 dev-suite runner (paper3; see module docstring)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true",
                    help="local check: 3 P16 cells, 1 inst, 1 seed, 10 s")
    ap.add_argument("--resume", action="store_true",
                    help="skip (topo,n,p,inst,arm,seed) keys already in the CSV")
    ap.add_argument("--topo", choices=("P16", "Z12", "both"), default="both")
    ap.add_argument("--arms", default=",".join(ARMS),
                    help=f"comma-separated subset of: {','.join(ARMS)}")
    return ap.parse_args()


def main():
    args = parse_args()
    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    unknown = [a for a in arms if a not in ARMS]
    if unknown:
        sys.exit(f"unknown arms {unknown}; valid: {list(ARMS)}")

    if any(a.startswith("mmfork") for a in arms):
        from ember_qc.algorithms.minorminer_forked import _find_so
        if _find_so() is None:
            sys.exit("mmfork arms selected but the fork .so is not built "
                     "(scripts/build_mm_fork.sh)")

    topos = ("P16", "Z12") if args.topo == "both" else (args.topo,)
    if args.smoke:
        cells = SMOKE_CELLS
        topos = tuple(sorted({c[0] for c in cells}))
        timeout, inst_seeds, algo_seeds = SMOKE_TIMEOUT, (101,), (0,)
        csv_path = CSV_PATH.replace(".csv", "_smoke.csv")
        summary_path = SUMMARY_PATH.replace(".txt", "_smoke.txt")
    else:
        cells = [(t, n, p) for t in topos for n, p in DEV_SUITE[t]]
        timeout, inst_seeds, algo_seeds = TIMEOUT, INST_SEEDS, ALGO_SEEDS
        csv_path, summary_path = CSV_PATH, SUMMARY_PATH

    # Prelude: warm the busclique disk caches in the parent (workers rebuild
    # their own handles; the disk cache makes that cheap).
    from minorminer.busclique import busgraph_cache
    for t in topos:
        t0 = time.perf_counter()
        tgt = build_target(t)
        m = len(busgraph_cache(tgt).largest_clique())
        print(f"prelude: {t} max clique = {m}  "
              f"[{time.perf_counter() - t0:.1f}s]")
        del tgt

    tasks = build_tasks(cells, arms, inst_seeds, algo_seeds, timeout)
    total_planned = len(tasks)
    if args.resume:
        done = load_done_keys(csv_path, KEY_FIELDS)
        tasks = [t for t in tasks if stringify_key(*t[:6]) not in done]
        print(f"resume: {total_planned - len(tasks)} of {total_planned} "
              f"already in {os.path.basename(csv_path)}")
    print(f"cells={len(cells)}  arms={len(arms)}  tasks={len(tasks)}  "
          f"timeout={timeout:g}s  workers={args.workers}")

    t0 = time.time()
    if tasks:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=_init_worker,
                                 initargs=(topos,)) as ex:
            futures = {ex.submit(run_task, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futures), 1):
                try:
                    row = fut.result()
                except Exception as exc:   # never let one row kill the batch
                    topo, n, p, inst_seed, arm, algo_seed, _t = futures[fut]
                    row = dict.fromkeys(FIELDS, "")
                    row.update(topo=topo, n=n, p=p, inst_seed=inst_seed,
                               arm=arm, algo_seed=algo_seed, status="CRASH",
                               success=0, err=clean_err(f"runner: {exc!r}"))
                append_row(csv_path, FIELDS, row)
                a = f"acl={row['acl']}/{row['acl_spur']}" if row["success"] else ""
                print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                      f"{row['topo']} n{row['n']} p{row['p']:g} "
                      f"i{row['inst_seed']} {row['arm']} s{row['algo_seed']}: "
                      f"{row['status']} {a} {row['time']}s", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; csv: {csv_path}\n")

    text = summarize(csv_path)
    print(text)
    with open(summary_path, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {summary_path}")


if __name__ == "__main__":
    main()
