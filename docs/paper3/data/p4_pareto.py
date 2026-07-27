"""
docs/paper3/data/p4_pareto.py
==============================
P4 kill gate — shortener-economics time-matched Pareto (proposals/shortener.md
drafted block). At FIXED wall-clock, do cheaper auditions (short_audit=1/2) or
skipped re-audits (dirty_skip=1) put any point on the time-quality Pareto
frontier stock MM does not dominate?

Cells (pegasus_16 only): ER(180, 0.1), ER(180, 0.3) — the drafted cells;
n=180@0.3 has MM 9/15 success in E0, fine, success is reported separately —
plus ER(140, 0.2) as an MM-comfortable cell. Instance seeds 101-105, algo
seeds 0-4, budgets {5, 15, 60, 180} s (explicit time sweep per protocol rule
5; per-attempt timeout == the budget).

Arms, all via forked_find_embedding(fallback=False) — pure fork arms, every
switch parity-guarded (byte-identical stock at defaults):

  stock    mmfork, every switch off (== stock minorminer 0.2.22)
  audit1   short_audit=1  (estimate-only audition)
  audit2   short_audit=2, audit_budget=3  (budgeted audition)
  dirty    dirty_skip=1   (negative cache over unchanged neighborhoods)

All four are MM-family (cooperative timeouts) -> no subprocess watchdog per
protocol route choice; MM's cooperative overshoot is ~one shortening sweep
(if a watchdog were used its grace stays 30 s — kills at budget+30, i.e.
210 s on the 180 s rows). Budget-180 rows are long: plan worker counts so the
tail does not serialize (<= 48 workers on hyde06 for the table run).

Both `acl` and `acl_spur` recorded (rule 3); CSV carries a `budget` column.

Summary per (cell, budget): paired dACL_spur vs stock (same inst_seed, same
algo_seed, same budget), win rate, median wall. Pre-registered Pareto bar: a
switch SURVIVES iff at >= 1 budget it (i) wins the paired median dACL_spur vs
stock with >= 60% both-succeed win rate, OR (ii) matches ACL_spur
(|median d| <= 1% of the stock median) at <= 0.5x the stock median wall
(wall compared within-batch only; headline re-measured workers=1 idle).

Run:
  .venv/bin/python docs/paper3/data/p4_pareto.py --workers 48       # hyde06
  .venv/bin/python docs/paper3/data/p4_pareto.py --smoke --workers 4
Flags: --workers N | --smoke | --resume
--smoke writes to p4_pareto_smoke.csv (smoke shares (cell, budget) keys with
the full grid and must never enter the full CSV's resume keys).
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
    acl, append_row, build_target, clean_err, embedding_metrics,
    load_done_keys, make_instance, stringify_key, terminal_polish,
)

from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.minorminer_forked import forked_find_embedding, _find_so  # noqa: E402

CSV_PATH = os.path.join(HERE, "p4_pareto.csv")
SUMMARY_PATH = os.path.join(HERE, "p4_pareto_summary.txt")

TOPO = "P16"
CELLS = [(180, 0.1), (180, 0.3), (140, 0.2)]
BUDGETS = (5.0, 15.0, 60.0, 180.0)
INST_SEEDS = (101, 102, 103, 104, 105)
ALGO_SEEDS = (0, 1, 2, 3, 4)
POLISH_DEADLINE_S = 5.0

# arm name -> forked_find_embedding switch kwargs
ARMS = {
    "stock":  {},
    "audit1": {"short_audit": 1},
    "audit2": {"short_audit": 2, "audit_budget": 3},
    "dirty":  {"dirty_skip": 1},
}
ARM_ORDER = ("stock", "audit1", "audit2", "dirty")

SMOKE_CELLS = [(140, 0.2)]
SMOKE_BUDGETS = (5.0, 15.0)

FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed", "budget",
          "status", "success", "acl", "acl_spur", "max_chain", "qubits",
          "wall", "n_edges", "err"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed", "budget"]


# ──────────────────────────────────────────────────────────────────────────────
# Worker
# ──────────────────────────────────────────────────────────────────────────────

_G = {}


def _init_worker(_unused=None):
    tgt = build_target(TOPO)
    _G[TOPO] = {"target": tgt, "adj": build_adjacency(tgt)}


def run_task(task):
    n, p, inst_seed, arm, algo_seed, budget = task
    src = make_instance(n, p, inst_seed)
    g = _G[TOPO]
    row = {"topo": TOPO, "n": n, "p": p, "inst_seed": inst_seed, "arm": arm,
           "algo_seed": algo_seed, "budget": budget, "status": "",
           "success": 0, "acl": "", "acl_spur": "", "max_chain": "",
           "qubits": "", "wall": "", "n_edges": src.number_of_edges(),
           "err": ""}
    t0 = time.perf_counter()
    try:
        r = forked_find_embedding(src, g["target"], seed=int(algo_seed),
                                  timeout=float(budget), fallback=False,
                                  **ARMS[arm])
    except Exception as e:  # forked_find_embedding never raises, but belt
        row["status"] = "CRASH"
        row["wall"] = round(time.perf_counter() - t0, 4)
        row["err"] = clean_err(f"{type(e).__name__}: {e}")
        return row
    wall = r.get("time", time.perf_counter() - t0)
    row["wall"] = round(float(wall), 4)
    emb = r.get("embedding") or {}
    if emb and is_valid_embedding(emb, src, g["target"], adj=g["adj"]):
        m = embedding_metrics(emb, g["target"])
        row.update(status="SUCCESS", success=1, acl=round(m["acl"], 4),
                   max_chain=m["max_chain"], qubits=m["qubits"])
        pol = terminal_polish(emb, src, g["target"],
                              deadline_s=POLISH_DEADLINE_S, adj=g["adj"])
        row["acl_spur"] = round(acl(pol), 4)
    else:
        row["status"] = ("TIMEOUT" if wall >= budget - 0.05
                         else r.get("status", "FAILURE"))
        row["err"] = clean_err(r.get("error", "") or
                               ("invalid embedding" if emb else ""))
    return row


# ──────────────────────────────────────────────────────────────────────────────
# Summary + the pre-registered Pareto verdict
# ──────────────────────────────────────────────────────────────────────────────

def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    out("=" * 100)
    out("P4 shortener-economics Pareto — column: acl_spur (rule 3); pairs on "
        "(inst_seed, algo_seed) within (cell, budget).")
    out("Bar: a switch SURVIVES iff at >=1 budget it wins median dACL_spur vs "
        "stock with >=60% win rate, or |median d| <= 1%")
    out("of stock median at <= 0.5x stock median wall (within-batch walls; "
        "headline re-measured at workers=1 idle).")
    out("=" * 100)

    cellbuds = sorted({(int(r["n"]), float(r["p"]), float(r["budget"]))
                       for r in rows})
    # arm -> list of (cell, budget, clause) survivals
    survives = {a: [] for a in ARM_ORDER if a != "stock"}
    for n, p, bud in cellbuds:
        cb = [r for r in rows if int(r["n"]) == n and float(r["p"]) == p
              and float(r["budget"]) == bud]
        stock_ok = {(r["inst_seed"], r["algo_seed"]): float(r["acl_spur"])
                    for r in cb if r["arm"] == "stock"
                    and r["success"] == "1" and r["acl_spur"]}
        stock_rows = [r for r in cb if r["arm"] == "stock"]
        stock_walls = sorted(float(r["wall"]) for r in stock_rows if r["wall"])
        stock_wall = statistics.median(stock_walls) if stock_walls else float("nan")
        stock_med = (statistics.median(stock_ok.values())
                     if stock_ok else float("nan"))
        out("")
        out(f"-- ER({n}, {p:g})  budget {bud:g}s   stock: success "
            f"{len(stock_ok)}/{len(stock_rows)}  acl_spur med {stock_med:7.3f}"
            f"  wall med {stock_wall:6.1f}s")
        for arm in ARM_ORDER:
            if arm == "stock":
                continue
            arows = [r for r in cb if r["arm"] == arm]
            if not arows:
                continue
            n_ok = sum(1 for r in arows if r["success"] == "1")
            walls = sorted(float(r["wall"]) for r in arows if r["wall"])
            med_w = statistics.median(walls) if walls else float("nan")
            pairs = [(float(r["acl_spur"]), stock_ok[(r["inst_seed"], r["algo_seed"])])
                     for r in arows
                     if r["success"] == "1" and r["acl_spur"]
                     and (r["inst_seed"], r["algo_seed"]) in stock_ok]
            base = (f"  {arm:7s} success {n_ok}/{len(arows)}  wall med "
                    f"{med_w:6.1f}s")
            if not pairs:
                out(base + "   [no both-succeed pairs]")
                continue
            deltas = [a - s for a, s in pairs]
            med_d = statistics.median(deltas)
            win = sum(1 for d in deltas if d < 0)
            winrate = win / len(deltas)
            pct = 100.0 * med_d / stock_med if stock_med else float("nan")
            clause = ""
            if med_d < 0 and winrate >= 0.60:
                clause = "WIN-CLAUSE"
            elif (abs(med_d) <= 0.01 * stock_med
                  and med_w <= 0.5 * stock_wall):
                clause = "SPEED-CLAUSE"
            if clause:
                survives[arm].append((f"ER({n},{p:g})@{bud:g}s", clause))
            out(base + f"   pairs {len(pairs):2d}  med d {med_d:+7.3f} "
                       f"({pct:+6.2f}%)  winrate {100 * winrate:5.1f}%"
                       + (f"   [{clause}]" if clause else ""))
    out("")
    out("PARETO VERDICT (pre-registered bar):")
    for arm in survives:
        if survives[arm]:
            pts = "; ".join(f"{c} {cl}" for c, cl in survives[arm])
            out(f"  {arm:7s} SURVIVES — {pts}")
        else:
            out(f"  {arm:7s} DIES — on no (cell, budget) point")
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="P4 shortener-economics time-matched Pareto (docstring)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true",
                    help="local check: ER(140,0.2), budgets {5,15}, 1 inst, "
                         "1 seed, all 4 arms")
    ap.add_argument("--resume", action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()
    if _find_so() is None:
        sys.exit("fork .so not built (scripts/build_mm_fork.sh) — every P4 "
                 "arm needs it")

    if args.smoke:
        cells, budgets = SMOKE_CELLS, SMOKE_BUDGETS
        inst_seeds, algo_seeds = (101,), (0,)
        csv_path = CSV_PATH.replace(".csv", "_smoke.csv")
        summary_path = SUMMARY_PATH.replace(".txt", "_smoke.txt")
    else:
        cells, budgets = CELLS, BUDGETS
        inst_seeds, algo_seeds = INST_SEEDS, ALGO_SEEDS
        csv_path, summary_path = CSV_PATH, SUMMARY_PATH

    tasks = []
    for n, p in cells:
        for i in inst_seeds:
            for s in algo_seeds:
                for bud in budgets:
                    for arm in ARM_ORDER:   # arms innermost: one interleaved queue
                        tasks.append((n, p, i, arm, s, bud))
    total_planned = len(tasks)
    if args.resume:
        done = load_done_keys(csv_path, KEY_FIELDS)
        tasks = [t for t in tasks
                 if stringify_key(TOPO, t[0], t[1], t[2], t[3], t[4], t[5])
                 not in done]
        print(f"resume: {total_planned - len(tasks)} of {total_planned} "
              f"already in {os.path.basename(csv_path)}")
    print(f"cells={len(cells)}  budgets={budgets}  tasks={len(tasks)}  "
          f"workers={args.workers}")

    t0 = time.time()
    if tasks:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=_init_worker) as ex:
            futures = {ex.submit(run_task, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futures), 1):
                try:
                    row = fut.result()
                except Exception as exc:
                    n, p, inst_seed, arm, algo_seed, bud = futures[fut]
                    row = dict.fromkeys(FIELDS, "")
                    row.update(topo=TOPO, n=n, p=p, inst_seed=inst_seed,
                               arm=arm, algo_seed=algo_seed, budget=bud,
                               status="CRASH", success=0,
                               err=clean_err(f"runner: {exc!r}"))
                append_row(csv_path, FIELDS, row)
                a = f"acl={row['acl']}/{row['acl_spur']}" if row["success"] else ""
                print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                      f"n{row['n']} p{row['p']:g} i{row['inst_seed']} "
                      f"{row['arm']} s{row['algo_seed']} b{row['budget']:g}: "
                      f"{row['status']} {a} {row['wall']}s", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; csv: {csv_path}\n")

    text = summarize(csv_path)
    print(text)
    with open(summary_path, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {summary_path}")


if __name__ == "__main__":
    main()
