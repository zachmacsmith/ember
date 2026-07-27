"""
docs/paper3/data/m3_race.py
============================
M3 — the P3 racer vs THE rule-2 baseline (protocol.md rule 2; portfolio.md
"strict fairness frame": any multi-run scheme is measured against stock MM
given the identical multi-run privilege at equal wall-clock on equal cores).

Four modes per (cell, inst_seed, base_seed), run BACK-TO-BACK on one worker
(same host, same load window — rule 5 within-batch comparability):

  race8-seq    (a) p3-race8 roster, sequential: race(..., n_workers=1).
               One core, wall-honest (cooperative overshoot ~+5 s recorded).
  bestof8-seq  (b) race_baseline_bestofk K=8: 8 sequential stock-MM runs of
               budget/8 each, lowest raw ACL. The ONE-CORE rule-2 control.
  bestof8-par  (c) PARALLEL best-of-8 stock MM: 8 independent FULL-budget MM
               runs at the same derived seeds as (b) (base*1000+i), run
               concurrently on 8 worker processes; lowest raw ACL wins.
               The EIGHT-CORE rule-2 control (MM given the same cores).
  race8-par    (d) race(..., n_workers=8): the racer on the same 8 cores.

Pre-registered reads: (a) vs (b) [sequential fairness, 1 core] and (d) vs
(c) [parallel fairness, 8 cores]. (a)/(c), (b)/(d) etc. cross core counts and
are context only. Seed schedule: (b) and (c) share per-run seeds
base_seed*1000+i (race.py's _arm_seed derivation); (a)/(d) derive their arm
seeds identically inside race(). All modes are MM-family compositions
(cooperative timeouts) — no watchdog per protocol route choice.

Concurrency structure: an outer pool of --outer-workers processes; each outer
worker runs ONE (cell, inst, base) combo at a time, its four modes strictly
sequential; modes (c)/(d) open their own 8-process inner pool. Default
--outer-workers 1 => at most 1 combo in flight (<= 8 inner + 1 outer + parent
processes). The coordinator runs --outer-workers 5 on hyde06 (~45 cores).

Cells (P16 and Z12): (100, 0.2) and (160, 0.05) — the mid/sparse dev cells
where selection could matter — plus (100, 0.3) as the just-above-crossover
control. Instance seeds 101-105, base seeds 0-4, 60 s budget. Both `acl` and
`acl_spur` recorded for every mode (rule 3); `winner` records which internal
arm/run produced the returned embedding.

Run:
  .venv/bin/python docs/paper3/data/m3_race.py --outer-workers 5     # hyde06
  .venv/bin/python docs/paper3/data/m3_race.py --smoke              # local
Flags: --outer-workers N | --smoke | --resume | --topo P16|Z12|both
--smoke writes to m3_race_smoke.csv (smoke shares cells with the full grid at
a shorter budget and must never enter the full CSV's resume keys).
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
    acl, append_row, build_target, clean_err, embedding_metrics,
    load_done_keys, make_instance, stringify_key, terminal_polish,
)

from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.paper3.race import (  # noqa: E402
    race, race_baseline_bestofk, RACE8_SPEC, _arm_seed,
)

CSV_PATH = os.path.join(HERE, "m3_race.csv")
SUMMARY_PATH = os.path.join(HERE, "m3_race_summary.txt")

BUDGET = 60.0                  # s per mode (protocol rule 5)
SMOKE_BUDGET = 12.0
POLISH_DEADLINE_S = 5.0        # terminal spur-prune (acl_spur)
K = 8                          # roster size == len(RACE8_SPEC)
INST_SEEDS = (101, 102, 103, 104, 105)
BASE_SEEDS = (0, 1, 2, 3, 4)

CELLS = [(topo, n, p)
         for topo in ("P16", "Z12")
         for n, p in ((100, 0.2), (160, 0.05), (100, 0.3))]

MODE_ORDER = ("race8-seq", "bestof8-seq", "bestof8-par", "race8-par")

FIELDS = ["topo", "n", "p", "inst_seed", "base_seed", "mode", "status",
          "success", "acl", "acl_spur", "max_chain", "qubits", "wall",
          "winner", "n_edges", "err", "arm_meta"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "base_seed", "mode"]


# ──────────────────────────────────────────────────────────────────────────────
# Outer-worker state + the parallel-MM inner stage
# ──────────────────────────────────────────────────────────────────────────────

_G = {}      # topo -> {"target", "adj", "edges"}
_PAR = {}    # source/edges for the bestof8-par inner pool (fork-inherited)


def _init_worker(topo_names):
    for t in topo_names:
        tgt = build_target(t)
        _G[t] = {"target": tgt, "adj": build_adjacency(tgt),
                 "edges": list(tgt.edges())}


def _par_mm_run(args):
    """One full-budget stock-MM run (inner pool of mode c). Never raises."""
    t0 = time.perf_counter()
    try:
        import minorminer
        emb = minorminer.find_embedding(
            _PAR["source"], _PAR["edges"], timeout=float(args["timeout"]),
            random_seed=int(args["seed"]), verbose=0)
    except Exception as e:
        return {"run": args["run"], "seed": args["seed"], "embedding": {},
                "used": time.perf_counter() - t0,
                "err": f"{type(e).__name__}: {e}"}
    return {"run": args["run"], "seed": args["seed"],
            "embedding": {v: [int(q) for q in c] for v, c in emb.items()},
            "used": time.perf_counter() - t0, "err": ""}


def _compact(md, limit=600):
    try:
        return json.dumps(md, separators=(",", ":"), default=str)[:limit]
    except Exception:
        return ""


# ── mode implementations — each returns
#    {embedding|None, wall, winner, meta, err} ─────────────────────────────────

def _mode_race(src, g, budget, base_seed, n_workers):
    t0 = time.perf_counter()
    r = race(src, g["target"], budget, base_seed, RACE8_SPEC,
             n_workers=n_workers)
    wall = time.perf_counter() - t0
    w = r.get("winner")
    winner = f"{w['kind']}[{w['index']}]@{w['stage']}" if w else ""
    meta = {"final_survivor": r.get("final_survivor"),
            "elapsed_s": r.get("elapsed_s"),
            "arms": {str(a["index"]): [a["kind"], a["status"], a["acl_best"]]
                     for a in r.get("arms", [])}}
    return {"embedding": r["embedding"] or None, "wall": wall,
            "winner": winner, "meta": meta,
            "err": "" if r["success"] else "race: no valid embedding"}


def _mode_bestofk_seq(src, g, budget, base_seed):
    t0 = time.perf_counter()
    r = race_baseline_bestofk(src, g["target"], budget, base_seed, K)
    wall = time.perf_counter() - t0
    winner = f"mm[run{r['best_run']}]" if r["success"] else ""
    meta = {"per_run_s": r["budget"]["per_run_s"],
            "accs": [x["acl"] for x in r["runs"]]}
    return {"embedding": r["embedding"] or None, "wall": wall,
            "winner": winner, "meta": meta,
            "err": "" if r["success"] else "bestofk: all runs failed"}


def _mode_bestofk_par(src, g, budget, base_seed):
    """(c): K independent FULL-budget stock-MM runs, concurrently on K worker
    processes; lowest raw ACL among valid results. Same derived seeds as (b)."""
    _PAR["source"] = src
    _PAR["edges"] = g["edges"]
    t0 = time.perf_counter()
    ctx = multiprocessing.get_context("fork")
    results = []
    with ProcessPoolExecutor(max_workers=K, mp_context=ctx) as pool:
        futs = [pool.submit(_par_mm_run,
                            {"run": i, "seed": _arm_seed(base_seed, i),
                             "timeout": budget})
                for i in range(K)]
        for f in futs:
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"run": -1, "seed": -1, "embedding": {},
                                "used": 0.0,
                                "err": f"worker: {type(e).__name__}: {e}"})
    wall = time.perf_counter() - t0
    best_emb, best_acl, best_run = None, float("inf"), None
    accs = []
    for r in results:
        emb = r["embedding"]
        if emb and is_valid_embedding(emb, src, g["target"], adj=g["adj"]):
            a = acl(emb)
            accs.append(round(a, 4))
            if a < best_acl:
                best_emb, best_acl, best_run = emb, a, r["run"]
        else:
            accs.append(None)
    winner = f"mm[run{best_run}]" if best_emb is not None else ""
    meta = {"per_run_s": budget, "accs": accs,
            "used_s": [round(r["used"], 1) for r in results]}
    return {"embedding": best_emb, "wall": wall, "winner": winner,
            "meta": meta,
            "err": "" if best_emb is not None else "par-bestofk: all runs failed"}


def run_combo(task):
    """Run the requested modes of one (cell, inst, base) combo, strictly
    sequentially, and return one CSV row per mode."""
    topo, n, p, inst_seed, base_seed, budget, modes = task
    src = make_instance(n, p, inst_seed)
    g = _G[topo]
    rows = []
    for mode in MODE_ORDER:
        if mode not in modes:
            continue
        row = {"topo": topo, "n": n, "p": p, "inst_seed": inst_seed,
               "base_seed": base_seed, "mode": mode, "status": "", "success": 0,
               "acl": "", "acl_spur": "", "max_chain": "", "qubits": "",
               "wall": "", "winner": "", "n_edges": src.number_of_edges(),
               "err": "", "arm_meta": ""}
        try:
            if mode == "race8-seq":
                res = _mode_race(src, g, budget, base_seed, 1)
            elif mode == "bestof8-seq":
                res = _mode_bestofk_seq(src, g, budget, base_seed)
            elif mode == "bestof8-par":
                res = _mode_bestofk_par(src, g, budget, base_seed)
            else:  # race8-par
                res = _mode_race(src, g, budget, base_seed, K)
        except Exception as e:
            row["status"] = "CRASH"
            row["err"] = clean_err(f"{type(e).__name__}: {e}")
            rows.append(row)
            continue
        row["wall"] = round(res["wall"], 4)
        row["winner"] = res["winner"]
        row["arm_meta"] = _compact(res["meta"])
        row["err"] = clean_err(res["err"])
        emb = res["embedding"]
        if emb and is_valid_embedding(emb, src, g["target"], adj=g["adj"]):
            m = embedding_metrics(emb, g["target"])
            row.update(status="SUCCESS", success=1, acl=round(m["acl"], 4),
                       max_chain=m["max_chain"], qubits=m["qubits"])
            pol = terminal_polish(emb, src, g["target"],
                                  deadline_s=POLISH_DEADLINE_S, adj=g["adj"])
            row["acl_spur"] = round(acl(pol), 4)
        else:
            row["status"] = "FAILURE"
        rows.append(row)
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Summary — the two pre-registered paired reads
# ──────────────────────────────────────────────────────────────────────────────

def _paired_read(cell_rows, mode_a, mode_b):
    """Both-succeed (inst, base) pairs: (acl_spur[a], acl_spur[b])."""
    vals = {}
    for r in cell_rows:
        if r["success"] == "1" and r["acl_spur"]:
            vals[(r["mode"], r["inst_seed"], r["base_seed"])] = float(r["acl_spur"])
    pairs = []
    for (m, i, s), va in vals.items():
        if m != mode_a:
            continue
        vb = vals.get((mode_b, i, s))
        if vb is not None:
            pairs.append((va, vb))
    return pairs


def _fmt_read(tag, pairs):
    if not pairs:
        return f"  {tag}: no both-succeed pairs"
    deltas = [a - b for a, b in pairs]
    le = sum(1 for d in deltas if d <= 1e-9)
    win = sum(1 for d in deltas if d < -1e-9)
    loss = sum(1 for d in deltas if d > 1e-9)
    med = statistics.median(deltas)
    ref = statistics.median(b for _a, b in pairs)
    pct = 100.0 * med / ref if ref else float("nan")
    return (f"  {tag}: n={len(pairs):2d}  med d {med:+7.3f} ({pct:+6.2f}%)  "
            f"W/L/T {win}/{loss}/{len(deltas) - win - loss}  "
            f"pct(a<=b) {100.0 * le / len(deltas):5.1f}%")


def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    out("=" * 100)
    out("M3 racer summary — column: acl_spur (rule 3); pairs on (inst_seed, "
        "base_seed), both-succeed only.")
    out("PRE-REGISTERED reads: [seq] race8-seq vs bestof8-seq (1 core) and "
        "[par] race8-par vs bestof8-par (8 cores).")
    out("Bar (portfolio.md): race <= baseline on >=70% of pairs AND median "
        "paired dACL_spur <= -2%.")
    out("=" * 100)
    cells = sorted({(r["topo"], float(r["p"]), int(r["n"])) for r in rows},
                   key=lambda c: (c[0], -c[1], c[2]))
    pooled = {"seq": [], "par": []}
    for topo, p, n in cells:
        cell = [r for r in rows
                if r["topo"] == topo and float(r["p"]) == p and int(r["n"]) == n]
        out("")
        out(f"-- {topo}  n={n}  p={p:g}")
        for mode in MODE_ORDER:
            mrows = [r for r in cell if r["mode"] == mode]
            n_ok = sum(1 for r in mrows if r["success"] == "1")
            accs = [float(r["acl_spur"]) for r in mrows
                    if r["success"] == "1" and r["acl_spur"]]
            walls = sorted(float(r["wall"]) for r in mrows if r["wall"])
            wins = {}
            for r in mrows:
                if r["success"] == "1" and r["winner"]:
                    k = r["winner"].split("[")[0]
                    wins[k] = wins.get(k, 0) + 1
            line = f"  {mode:12s} success {n_ok}/{len(mrows)}  "
            line += (f"acl_spur med {statistics.median(accs):7.3f}  "
                     if accs else "acl_spur med     n/a  ")
            line += (f"wall med {statistics.median(walls):6.1f}s  "
                     if walls else "wall med    n/a  ")
            out(line + f"winners {wins}")
        p_seq = _paired_read(cell, "race8-seq", "bestof8-seq")
        p_par = _paired_read(cell, "race8-par", "bestof8-par")
        out(_fmt_read("[seq] race8-seq vs bestof8-seq", p_seq))
        out(_fmt_read("[par] race8-par vs bestof8-par", p_par))
        pooled["seq"] += p_seq
        pooled["par"] += p_par
    out("")
    out("POOLED across cells:")
    out(_fmt_read("[seq] race8-seq vs bestof8-seq", pooled["seq"]))
    out(_fmt_read("[par] race8-par vs bestof8-par", pooled["par"]))
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="M3 racer vs rule-2 baselines (see module docstring)")
    ap.add_argument("--outer-workers", type=int, default=1,
                    help="combos in flight; each uses <= 8 inner workers "
                         "(default 1 => total <= 8+1 procs)")
    ap.add_argument("--smoke", action="store_true",
                    help="local check: 1 combo, 12 s budget, all 4 modes")
    ap.add_argument("--resume", action="store_true",
                    help="skip (cell,inst,base,mode) keys already in the CSV")
    ap.add_argument("--topo", choices=("P16", "Z12", "both"), default="both")
    return ap.parse_args()


def main():
    args = parse_args()
    from ember_qc.algorithms.minorminer_forked import _find_so
    if _find_so() is None:
        sys.exit("fork .so missing — p3-race8's cuthill arm would be silently "
                 "skipped (roster integrity); build it first")

    if args.smoke:
        cells = [("P16", 100, 0.2)]
        inst_seeds, base_seeds, budget = (101,), (0,), SMOKE_BUDGET
        csv_path = CSV_PATH.replace(".csv", "_smoke.csv")
        summary_path = SUMMARY_PATH.replace(".txt", "_smoke.txt")
    else:
        topos = ("P16", "Z12") if args.topo == "both" else (args.topo,)
        cells = [c for c in CELLS if c[0] in topos]
        inst_seeds, base_seeds, budget = INST_SEEDS, BASE_SEEDS, BUDGET
        csv_path, summary_path = CSV_PATH, SUMMARY_PATH
    topos = tuple(sorted({c[0] for c in cells}))

    # Prelude: warm busclique disk caches (race's template slot uses them).
    from minorminer.busclique import busgraph_cache
    for t in topos:
        t0 = time.perf_counter()
        m = len(busgraph_cache(build_target(t)).largest_clique())
        print(f"prelude: {t} max clique = {m}  [{time.perf_counter() - t0:.1f}s]")

    done = load_done_keys(csv_path, KEY_FIELDS) if args.resume else set()
    combos = []
    for topo, n, p in cells:
        for i in inst_seeds:
            for b in base_seeds:
                modes = tuple(
                    m for m in MODE_ORDER
                    if stringify_key(topo, n, p, i, b, m) not in done)
                if modes:
                    combos.append((topo, n, p, i, b, budget, modes))
    n_modes = sum(len(c[6]) for c in combos)
    print(f"cells={len(cells)}  combos={len(combos)}  mode-runs={n_modes}  "
          f"budget={budget:g}s  outer-workers={args.outer_workers}  "
          f"(each combo: <= {K} inner workers)")

    t0 = time.time()
    if combos:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.outer_workers,
                                 mp_context=ctx, initializer=_init_worker,
                                 initargs=(topos,)) as ex:
            futures = {ex.submit(run_combo, c): c for c in combos}
            ndone = 0
            for fut in as_completed(futures):
                topo, n, p, i, b, _bud, modes = futures[fut]
                try:
                    rows = fut.result()
                except Exception as exc:
                    rows = []
                    for m in modes:
                        row = dict.fromkeys(FIELDS, "")
                        row.update(topo=topo, n=n, p=p, inst_seed=i,
                                   base_seed=b, mode=m, status="CRASH",
                                   success=0, err=clean_err(f"runner: {exc!r}"))
                        rows.append(row)
                for row in rows:
                    ndone += 1
                    append_row(csv_path, FIELDS, row)
                    a = (f"acl={row['acl']}/{row['acl_spur']}"
                         if row["success"] else "")
                    print(f"[{ndone}/{n_modes} {time.time() - t0:6.0f}s] "
                          f"{row['topo']} n{row['n']} p{row['p']:g} "
                          f"i{row['inst_seed']} b{row['base_seed']} "
                          f"{row['mode']}: {row['status']} {a} "
                          f"wall={row['wall']}s win={row['winner']}",
                          flush=True)
    print(f"\nall combos done in {time.time() - t0:.0f}s; csv: {csv_path}\n")

    text = summarize(csv_path)
    print(text)
    with open(summary_path, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {summary_path}")


if __name__ == "__main__":
    main()
