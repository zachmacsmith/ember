"""
docs/paper3/data/m4_eval.py
============================
M4 — the FROZEN-EVAL runner: the M3 survivors re-measured once, blind, on the
EVAL seed registries (protocol.md rule 4). Cells are the same frozen 14-cell
dev-suite (n, p) definitions (protocol.md "Frozen dev suite"); the novelty is
the seeds:

  * ER cells:  EVAL instance seeds 901-915 (K=15 FRESH instances per cell,
               never generated/run/inspected during M0-M3).
  * K_n cells: instance-invariant by construction (p=1.0 -> the complete
               graph; every instance seed yields the identical graph), so the
               eval novelty there is the ALGORITHM seeds only. One instance is
               run, recorded with inst_seed 901 (the eval registry's first
               entry) purely as a row label.
  * Algorithm seeds: EVAL registry 10-14 (dev used 0-4). Deterministic
               p3-template runs once per instance, recorded algo_seed -1.

Two stages, selected with --stage:

  main   (default) The 9-arm sweep on all 14 cells: minorminer,
         mmfork-cuthill (fallback=False), p3-template (deterministic),
         p3-ate, p3-clmm, p3-clmm-core, p3-mmpolish, pssa, attraction.
         Measurement code is IMPORTED from dev_suite.py (same run_task, same
         watchdog policy, same terminal spur-prune -> acl/acl_spur columns;
         protocol rules 3 and route choice) so dev and eval share one code
         path byte-for-byte. Writes m4_eval.csv.
         hyde06: --workers 48. ~6,314 rows; worst-case ~116 core-h ~ 2.5 h
         wall at 48 W (realistically less: most arms stop on patience).

  race   The §4.6 racer block re-run on eval seeds, on the 6 selection cells
         only — P16/Z12 x {(100,0.2), (100,0.3), (160,0.05)} — with the four
         m3_race.py modes IMPORTED unchanged (race8-seq / bestof8-seq /
         bestof8-par / race8-par; outer x 8-inner process structure; the two
         best-of-8 arms are THE rule-2 controls). base seeds = eval algo
         seeds 10-14; instance seeds 901-915. Writes m4_race.csv.
         hyde06: --outer-workers 5 (~41-46 procs). 450 combos x 4 modes =
         1,800 mode-runs; worst-case ~31 combo-serial h ~ 6.2 h wall at
         outer5 (realistically ~5 h: bestof8-par usually stops on patience).

EVAL DISCIPLINE (protocol rule 4). Non-smoke runs REFUSE to start without
--confirm-freeze: the flag asserts that the M4 tuning freeze has been recorded
in notes.md (an entry with the tuned config shas) BEFORE any eval instance is
generated. --smoke deliberately uses DEV instance seeds (101, 102) — a smoke
is a plumbing check and must not touch the eval instances early; the code path
being validated (make_instance, run_task, CSV plumbing) is seed-agnostic.

Run:
  .venv/bin/python docs/paper3/data/m4_eval.py --stage main --workers 48 --confirm-freeze
  .venv/bin/python docs/paper3/data/m4_eval.py --stage race --outer-workers 5 --confirm-freeze
  .venv/bin/python docs/paper3/data/m4_eval.py --smoke --workers 4          # local, stage main
  .venv/bin/python docs/paper3/data/m4_eval.py --smoke --stage race        # local, 1 combo

Flags: --stage main|race | --workers N (main) | --outer-workers N (race) |
--smoke | --resume | --topo P16|Z12|both | --arms a,b,... (main only) |
--confirm-freeze. Smoke writes to m4_eval_smoke.csv / m4_race_smoke.csv;
smoke keys never enter the full CSVs' resume sets.

Headline tables come from m4_analysis.py; the summary printed here is a
quick-look only (dev_suite/m3_race summarize reused verbatim).
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dev_suite as ds          # noqa: E402  (main-stage machinery, reused)
import m3_race as mr            # noqa: E402  (race-stage machinery, reused)
from _runner_common import (    # noqa: E402
    append_row, build_target, clean_err, load_done_keys, stringify_key,
)

# ── EVAL registries (protocol.md rule 4) ─────────────────────────────────────
EVAL_INST_SEEDS = tuple(range(901, 916))   # 901-915, K=15
EVAL_ALGO_SEEDS = (10, 11, 12, 13, 14)
TIMEOUT = 60.0                             # protocol rule 5

CSV_MAIN = os.path.join(HERE, "m4_eval.csv")
CSV_RACE = os.path.join(HERE, "m4_race.csv")
QUICKLOOK_MAIN = os.path.join(HERE, "m4_eval_quicklook.txt")
QUICKLOOK_RACE = os.path.join(HERE, "m4_race_quicklook.txt")

# The race stage runs on the 6 selection cells (§4.6). m3_race.CELLS is that
# exact list; assert rather than re-type so the two files cannot drift.
RACE_CELLS = tuple(mr.CELLS)
_EXPECTED_RACE_CELLS = {(t, n, p) for t in ("P16", "Z12")
                        for n, p in ((100, 0.2), (100, 0.3), (160, 0.05))}
assert set(RACE_CELLS) == _EXPECTED_RACE_CELLS, \
    "m3_race.CELLS changed — the M4 race stage is pinned to the 6 §4.6 cells"

# Smoke (local plumbing check): DEV instances on purpose — see docstring.
SMOKE_MAIN_CELLS = [("P16", 100, 0.3), ("P16", 160, 0.05)]
SMOKE_MAIN_INST = (101, 102)               # DEV registry (rule 4: no early eval)
SMOKE_MAIN_ALGO = (10,)                    # one eval-registry algo seed
SMOKE_MAIN_ARMS = ("minorminer", "p3-template", "p3-ate", "p3-clmm")
SMOKE_MAIN_TIMEOUT = 10.0
SMOKE_RACE_CELLS = [("P16", 100, 0.2)]
SMOKE_RACE_INST = (101,)
SMOKE_RACE_BASE = (10,)
SMOKE_RACE_BUDGET = 12.0

FREEZE_MSG = (
    "REFUSING to run: protocol rule 4 — EVAL seeds (instances 901-915, algo "
    "10-14) may only run AFTER the M4 tuning freeze is recorded in notes.md "
    "(a dated entry with the tuned config shas). If the freeze entry exists, "
    "re-run with --confirm-freeze.")


def _warm_busclique(topos):
    """Prelude: warm the busclique disk caches in the parent (as dev_suite/
    m3_race do); workers rebuild handles cheaply from the disk cache."""
    from minorminer.busclique import busgraph_cache
    for t in topos:
        t0 = time.perf_counter()
        tgt = build_target(t)
        m = len(busgraph_cache(tgt).largest_clique())
        print(f"prelude: {t} max clique = {m}  "
              f"[{time.perf_counter() - t0:.1f}s]")
        del tgt


def _require_fork_so():
    from ember_qc.algorithms.minorminer_forked import _find_so
    if _find_so() is None:
        sys.exit("fork .so missing (scripts/build_mm_fork.sh) — required by "
                 "mmfork-cuthill and by p3-race8's cuthill roster arm")


# ──────────────────────────────────────────────────────────────────────────────
# Stage main — dev_suite machinery on eval seeds
# ──────────────────────────────────────────────────────────────────────────────

def run_main(args):
    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    unknown = [a for a in arms if a not in ds.ARMS]
    if unknown:
        sys.exit(f"unknown arms {unknown}; valid: {list(ds.ARMS)}")
    if any(a.startswith("mmfork") for a in arms):
        _require_fork_so()

    topos = ("P16", "Z12") if args.topo == "both" else (args.topo,)
    if args.smoke:
        cells = SMOKE_MAIN_CELLS
        topos = tuple(sorted({c[0] for c in cells}))
        inst_seeds, algo_seeds, timeout = SMOKE_MAIN_INST, SMOKE_MAIN_ALGO, \
            SMOKE_MAIN_TIMEOUT
        arms = tuple(a for a in SMOKE_MAIN_ARMS if a in arms) or SMOKE_MAIN_ARMS
        csv_path = CSV_MAIN.replace(".csv", "_smoke.csv")
        quicklook = QUICKLOOK_MAIN.replace(".txt", "_smoke.txt")
    else:
        cells = [(t, n, p) for t in topos for n, p in ds.DEV_SUITE[t]]
        inst_seeds, algo_seeds, timeout = EVAL_INST_SEEDS, EVAL_ALGO_SEEDS, \
            TIMEOUT
        csv_path, quicklook = CSV_MAIN, QUICKLOOK_MAIN

    _warm_busclique(topos)

    # dev_suite.build_tasks applies the K_n rule (inst_seeds_for): p=1.0 cells
    # run one instance, recorded inst_seed = inst_seeds[0] (901 here).
    tasks = ds.build_tasks(cells, arms, inst_seeds, algo_seeds, timeout)
    total_planned = len(tasks)
    if args.resume:
        done = load_done_keys(csv_path, ds.KEY_FIELDS)
        tasks = [t for t in tasks if stringify_key(*t[:6]) not in done]
        print(f"resume: {total_planned - len(tasks)} of {total_planned} "
              f"already in {os.path.basename(csv_path)}")
    print(f"M4 stage=main  cells={len(cells)}  arms={len(arms)}  "
          f"tasks={len(tasks)}  timeout={timeout:g}s  workers={args.workers}")

    t0 = time.time()
    if tasks:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=ds._init_worker,
                                 initargs=(topos,)) as ex:
            futures = {ex.submit(ds.run_task, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futures), 1):
                try:
                    row = fut.result()
                except Exception as exc:   # never let one row kill the batch
                    topo, n, p, inst_seed, arm, algo_seed, _t = futures[fut]
                    row = dict.fromkeys(ds.FIELDS, "")
                    row.update(topo=topo, n=n, p=p, inst_seed=inst_seed,
                               arm=arm, algo_seed=algo_seed, status="CRASH",
                               success=0, err=clean_err(f"runner: {exc!r}"))
                append_row(csv_path, ds.FIELDS, row)
                a = (f"acl={row['acl']}/{row['acl_spur']}"
                     if row["success"] else "")
                print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                      f"{row['topo']} n{row['n']} p{row['p']:g} "
                      f"i{row['inst_seed']} {row['arm']} s{row['algo_seed']}: "
                      f"{row['status']} {a} {row['time']}s", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; csv: {csv_path}\n")

    print("QUICK-LOOK ONLY — M4 headline tables (Wilcoxon/Holm/variance/"
          "frontier/racer/time) come from m4_analysis.py:")
    text = ds.summarize(csv_path)
    print(text)
    with open(quicklook, "w") as fh:
        fh.write("QUICK-LOOK (dev_suite.summarize reused); headline: "
                 "m4_analysis.py\n" + text + "\n")
    print(f"\nquick-look -> {quicklook}")


# ──────────────────────────────────────────────────────────────────────────────
# Stage race — m3_race machinery on eval seeds, 6 selection cells
# ──────────────────────────────────────────────────────────────────────────────

def run_race(args):
    _require_fork_so()   # p3-race8's cuthill arm must not be silently skipped

    if args.smoke:
        cells = SMOKE_RACE_CELLS
        inst_seeds, base_seeds, budget = SMOKE_RACE_INST, SMOKE_RACE_BASE, \
            SMOKE_RACE_BUDGET
        csv_path = CSV_RACE.replace(".csv", "_smoke.csv")
        quicklook = QUICKLOOK_RACE.replace(".txt", "_smoke.txt")
    else:
        topos = ("P16", "Z12") if args.topo == "both" else (args.topo,)
        cells = [c for c in RACE_CELLS if c[0] in topos]
        inst_seeds, base_seeds, budget = EVAL_INST_SEEDS, EVAL_ALGO_SEEDS, \
            TIMEOUT
        csv_path, quicklook = CSV_RACE, QUICKLOOK_RACE
    topos = tuple(sorted({c[0] for c in cells}))

    _warm_busclique(topos)

    done = load_done_keys(csv_path, mr.KEY_FIELDS) if args.resume else set()
    combos = []
    for topo, n, p in cells:
        for i in inst_seeds:
            for b in base_seeds:
                modes = tuple(
                    m for m in mr.MODE_ORDER
                    if stringify_key(topo, n, p, i, b, m) not in done)
                if modes:
                    combos.append((topo, n, p, i, b, budget, modes))
    n_modes = sum(len(c[6]) for c in combos)
    print(f"M4 stage=race  cells={len(cells)}  combos={len(combos)}  "
          f"mode-runs={n_modes}  budget={budget:g}s  "
          f"outer-workers={args.outer_workers}  (each combo: <= {mr.K} inner "
          f"workers)")

    t0 = time.time()
    if combos:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.outer_workers,
                                 mp_context=ctx, initializer=mr._init_worker,
                                 initargs=(topos,)) as ex:
            futures = {ex.submit(mr.run_combo, c): c for c in combos}
            ndone = 0
            for fut in as_completed(futures):
                topo, n, p, i, b, _bud, modes = futures[fut]
                try:
                    rows = fut.result()
                except Exception as exc:
                    rows = []
                    for m in modes:
                        row = dict.fromkeys(mr.FIELDS, "")
                        row.update(topo=topo, n=n, p=p, inst_seed=i,
                                   base_seed=b, mode=m, status="CRASH",
                                   success=0, err=clean_err(f"runner: {exc!r}"))
                        rows.append(row)
                for row in rows:
                    ndone += 1
                    append_row(csv_path, mr.FIELDS, row)
                    a = (f"acl={row['acl']}/{row['acl_spur']}"
                         if row["success"] else "")
                    print(f"[{ndone}/{n_modes} {time.time() - t0:6.0f}s] "
                          f"{row['topo']} n{row['n']} p{row['p']:g} "
                          f"i{row['inst_seed']} b{row['base_seed']} "
                          f"{row['mode']}: {row['status']} {a} "
                          f"wall={row['wall']}s win={row['winner']}",
                          flush=True)
    print(f"\nall combos done in {time.time() - t0:.0f}s; csv: {csv_path}\n")

    print("QUICK-LOOK ONLY — M4 headline racer table comes from "
          "m4_analysis.py:")
    text = mr.summarize(csv_path)
    print(text)
    with open(quicklook, "w") as fh:
        fh.write("QUICK-LOOK (m3_race.summarize reused); headline: "
                 "m4_analysis.py\n" + text + "\n")
    print(f"\nquick-look -> {quicklook}")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="M4 frozen-eval runner (paper3; see module docstring)")
    ap.add_argument("--stage", choices=("main", "race"), default="main",
                    help="main = 9-arm sweep on the 14 cells; race = the "
                         "racer block on the 6 selection cells")
    ap.add_argument("--workers", type=int, default=8,
                    help="stage main: process-pool size (hyde06: 48)")
    ap.add_argument("--outer-workers", type=int, default=1,
                    help="stage race: combos in flight; each opens <= 8 "
                         "inner workers (hyde06: 5)")
    ap.add_argument("--smoke", action="store_true",
                    help="local plumbing check on DEV instances (rule 4: "
                         "never touches eval instances); main: 2 cells x "
                         "2 inst x 1 seed x 4 arms at 10 s; race: 1 combo "
                         "at 12 s")
    ap.add_argument("--resume", action="store_true",
                    help="skip key tuples already present in the stage CSV")
    ap.add_argument("--topo", choices=("P16", "Z12", "both"), default="both")
    ap.add_argument("--arms", default=",".join(ds.ARMS),
                    help=f"stage main only; subset of: {','.join(ds.ARMS)}")
    ap.add_argument("--confirm-freeze", action="store_true",
                    help="assert the M4 tuning freeze is recorded in "
                         "notes.md (required for any non-smoke run)")
    return ap.parse_args()


def main():
    args = parse_args()
    if not args.smoke and not args.confirm_freeze:
        sys.exit(FREEZE_MSG)
    if args.stage == "main":
        run_main(args)
    else:
        run_race(args)


if __name__ == "__main__":
    main()
