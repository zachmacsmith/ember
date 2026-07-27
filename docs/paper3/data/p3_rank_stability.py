"""
docs/paper3/data/p3_rank_stability.py
======================================
P3/P4 shared gate probe (proposals/portfolio.md, "Gate first"): does ACL early
in minorminer's polish predict final ACL across seeds of the same instance?
Legal-stage selection is DEAD (paper2 notes 3.16, r ~ -0.01); this asks whether
EARLY-POLISH selection works instead.

Per (instance, algo_seed), total probe budget 64 s: one legal-only run
(chainlength_patience=0, timeout 8 s = the budget remainder), then 8
warm-restart polish quanta of 7 s each, using exactly the plumbing verified in
docs/paper2/data/basin_persistence.py (notes 3.16, fidelity confirmed there):

    find_embedding(src_graph, target_edges,
                   initial_chains=<current embedding>,
                   skip_initialization=True,
                   timeout=QUANTUM_S,
                   random_seed=algo_seed*1000+q,
                   chainlength_patience=<large>)   # never trips; quanta end
                                                   # on timeout, fixed-size

ACL is recorded after every quantum, raw AND monotone best-so-far. The gate:
Spearman rho(acl_best@q, acl_best@q8) across the 16 algo seeds of an instance,
per q -- rho >= 0.5 at the halfway quantum (q4) unlocks the P3 racer. The mean
ACL-vs-cumulative-time curve and the per-quantum share of total improvement
are P4's patience / diminishing-returns readout.

One extra "spur" row per trajectory (a deviation from the minimal stage set,
kept deliberately): the terminal spur-prune (protocol rule 3) of the
best-so-far embedding, OUTSIDE the 64 s budget; the summary also reports
rho(acl_best@q, spur ACL) so the gate can be read on the reported-metric
(acl_spur) scale that paper3 tables use.

Cells: target dnx.pegasus_graph(16); ER (n, p) in {(100, 0.1), (140, 0.2),
(100, 0.5)} x instance seeds {101, 102, 103} (DEV registry, protocol rule 4);
algo seeds 0-15. 144 tasks x ~60-64 s -> ~20 min at --workers 8. MM-family
only, so no watchdog (protocol route choice). One flushed row block per
completed task -> p3_rank_stability.csv; --resume skips completed
(n, p, inst_seed, algo_seed); summary printed and written to
p3_rank_stability_summary.txt. --smoke (1 instance x 3 seeds x 3 quanta of
3 s) writes to separate *_smoke files, never mixed with the full run.

The live per-task line prints `ovl` = mean per-variable Jaccard overlap
between the legal chains and the q1 chains (not a CSV column). Calibration:
chains migrate heavily during a quantum of grind, so warm polish shows
ovl ~ 0.1-0.2 (smoke: 0.13-0.14) -- but a re-initialization would place
chains afresh on P16's 5760 qubits, giving ovl ~ 0.001. ovl at the re-init
level, or raw q1 ACL > legal ACL, means skip_initialization misbehaved and
the probe must not be trusted (the summary's warm-start check flags the
latter automatically).

Run:
  .venv/bin/python docs/paper3/data/p3_rank_stability.py --workers 8          # full
  .venv/bin/python docs/paper3/data/p3_rank_stability.py --smoke --workers 3  # ~1 min
Flags: --workers N | --smoke | --resume
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import csv
import math
import multiprocessing
import re
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _runner_common import (  # noqa: E402
    acl, build_target, clean_err, load_done_keys, make_instance,
    stringify_key, terminal_polish,
)

import minorminer  # noqa: E402
from ember_qc.embedding_backend import build_adjacency  # noqa: E402

# ── design constants ─────────────────────────────────────────────────────────
CELLS = ((100, 0.1), (140, 0.2), (100, 0.5))    # (n, p) ER cells on P16
INST_SEEDS = (101, 102, 103)                    # DEV registry (protocol rule 4)
ALGO_SEEDS = tuple(range(16))
TOTAL_BUDGET_S = 64.0                           # per (instance, algo_seed)
N_QUANTA = 8
QUANTUM_S = 7.0
LEGALIZE_TIMEOUT_S = TOTAL_BUDGET_S - N_QUANTA * QUANTUM_S   # = 8.0 s
CHAINLENGTH_PATIENCE_LARGE = 10**6   # polish quanta end on timeout, not patience
SPUR_DEADLINE_S = 5.0                # protocol rule 3 pass, outside the 64 s

SMOKE_CELLS = ((100, 0.1),)
SMOKE_INST_SEEDS = (101,)
SMOKE_ALGO_SEEDS = (0, 1, 2)
SMOKE_N_QUANTA = 3
SMOKE_QUANTUM_S = 3.0

CSV_PATH = os.path.join(HERE, "p3_rank_stability.csv")
SUMMARY_PATH = os.path.join(HERE, "p3_rank_stability_summary.txt")
SMOKE_CSV_PATH = os.path.join(HERE, "p3_rank_stability_smoke.csv")
SMOKE_SUMMARY_PATH = os.path.join(HERE, "p3_rank_stability_smoke_summary.txt")

FIELDS = ["cell", "n", "p", "inst_seed", "algo_seed", "stage", "acl",
          "acl_best", "time_cum"]
KEY_FIELDS = ["n", "p", "inst_seed", "algo_seed"]   # a task appears atomically


# ──────────────────────────────────────────────────────────────────────────────
# Worker
# ──────────────────────────────────────────────────────────────────────────────

_G = {}   # per-worker: target graph, its edge list, its adjacency


def _init_worker():
    tgt = build_target("P16")
    _G["target"] = tgt
    _G["edges"] = list(tgt.edges())
    _G["adj"] = build_adjacency(tgt)


def _chain_overlap(e1, e2):
    """Mean per-variable Jaccard overlap between two embeddings' chains."""
    vs = set(e1) & set(e2)
    if not vs:
        return 0.0
    j = 0.0
    for v in vs:
        a, b = set(e1[v]), set(e2[v])
        j += len(a & b) / len(a | b)
    return j / len(vs)


def run_task(task):
    """One (instance, algo_seed): legalize, then n_quanta warm polish quanta,
    then the rule-3 spur pass. Returns the row block for this task."""
    n, p, inst_seed, algo_seed, n_quanta, quantum_s = task
    src = make_instance(n, p, inst_seed)
    base = {"cell": f"P16:{n}:{p:g}", "n": n, "p": p,
            "inst_seed": inst_seed, "algo_seed": algo_seed}
    rows = []
    t_cum = 0.0

    # -- legalize: chainlength_patience=0 -> first valid embedding, no grind
    t = time.perf_counter()
    legal = minorminer.find_embedding(
        src, _G["edges"], random_seed=algo_seed,
        timeout=LEGALIZE_TIMEOUT_S, chainlength_patience=0)
    t_cum += time.perf_counter() - t
    if not legal:
        rows.append({**base, "stage": "q0legal", "acl": "", "acl_best": "",
                     "time_cum": round(t_cum, 2)})
        return rows
    a0 = acl(legal)
    best_a, best_emb = a0, legal
    rows.append({**base, "stage": "q0legal", "acl": round(a0, 4),
                 "acl_best": round(best_a, 4), "time_cum": round(t_cum, 2)})

    # -- polish quanta: warm restart of the CURRENT embedding each time
    #    (basin_persistence.py kwargs: initial_chains + skip_initialization;
    #    large chainlength_patience so each quantum runs its full timeout)
    cur = legal
    for q in range(1, n_quanta + 1):
        t = time.perf_counter()
        pol = minorminer.find_embedding(
            src, _G["edges"],
            initial_chains=cur,
            skip_initialization=True,
            timeout=quantum_s,
            random_seed=algo_seed * 1000 + q,
            chainlength_patience=CHAINLENGTH_PATIENCE_LARGE)
        t_cum += time.perf_counter() - t
        row = {**base, "stage": f"q{q}", "acl": "",
               "acl_best": round(best_a, 4), "time_cum": round(t_cum, 2)}
        if pol:
            a = acl(pol)
            if a < best_a:
                best_a, best_emb = a, pol
            row["acl"] = round(a, 4)
            row["acl_best"] = round(best_a, 4)
            if q == 1:
                row["_ovl"] = round(_chain_overlap(legal, pol), 3)
            cur = pol   # chain-forward the raw result, best or not
        rows.append(row)

    # -- protocol rule 3: terminal spur-prune of the best-so-far embedding
    #    (outside the 64 s probe budget; _ovl and this row are the only
    #    things beyond the specified stage set)
    t = time.perf_counter()
    spur = terminal_polish(best_emb, src, _G["target"],
                           deadline_s=SPUR_DEADLINE_S, adj=_G["adj"])
    t_cum += time.perf_counter() - t
    a_spur = acl(spur) if spur else best_a
    rows.append({**base, "stage": "spur", "acl": round(a_spur, 4),
                 "acl_best": round(min(best_a, a_spur), 4),
                 "time_cum": round(t_cum, 2)})
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# CSV (per-task atomic append; extras like _ovl are print-only, never written)
# ──────────────────────────────────────────────────────────────────────────────

def append_rows(csv_path, fieldnames, rows):
    need_header = (not os.path.exists(csv_path)
                   or os.path.getsize(csv_path) == 0)
    with open(csv_path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fieldnames),
                           extrasaction="ignore")
        if need_header:
            w.writeheader()
        w.writerows(rows)
        fh.flush()
        os.fsync(fh.fileno())


def _task_line(rows):
    r0 = rows[0]
    head = f"n{r0['n']} p{r0['p']:g} i{r0['inst_seed']} s{r0['algo_seed']}"
    if r0["acl"] == "":
        return f"{head}: LEGALIZE-FAIL ({r0['time_cum']}s)"
    qrows = [r for r in rows if re.fullmatch(r"q\d+", r["stage"])]
    traj = " ".join(f"{r['acl']:.2f}" if r["acl"] != "" else "--"
                    for r in qrows)
    best = qrows[-1]["acl_best"] if qrows else r0["acl_best"]
    s = f"{head}: legal {r0['acl']:.2f} -> {traj} | best {best:.2f}"
    spur_r = next((r for r in rows if r["stage"] == "spur"), None)
    if spur_r is not None:
        s += f" spur {spur_r['acl']:.2f}"
    ovl = next((r["_ovl"] for r in rows if "_ovl" in r), None)
    if ovl is not None:
        s += f" ovl {ovl:.2f}"
    return s + f" | {rows[-1]['time_cum']:.1f}s"


# ──────────────────────────────────────────────────────────────────────────────
# Summary / analysis
# ──────────────────────────────────────────────────────────────────────────────

def summarize(csv_path):
    import warnings
    from scipy import stats

    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    if not rows:
        out(f"no rows in {csv_path}")
        return "\n".join(lines)

    qnums = sorted({int(m.group(1)) for r in rows
                    for m in [re.fullmatch(r"q(\d+)", r["stage"])] if m})
    n_q = max(qnums)
    q_half = (n_q + 1) // 2
    has_spur = any(r["stage"] == "spur" for r in rows)

    trajs = {}
    for r in rows:
        key = (int(r["n"]), float(r["p"]), int(r["inst_seed"]),
               int(r["algo_seed"]))
        trajs.setdefault(key, {})[r["stage"]] = r

    def fv(st, stage, col):
        r = st.get(stage)
        if r is None:
            return None
        v = r.get(col, "")
        return float(v) if v not in ("", None) else None

    complete, legal_fail = {}, []
    for key, st in sorted(trajs.items()):
        if fv(st, "q0legal", "acl") is None:
            legal_fail.append(key)
            continue
        if all(fv(st, f"q{q}", "acl_best") is not None
               for q in range(1, n_q + 1)):
            complete[key] = st

    def spear(x, y):
        pairs = [(a, b) for a, b in zip(x, y)
                 if a is not None and b is not None]
        if len(pairs) < 3:
            return None, None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sr = stats.spearmanr([a for a, _ in pairs], [b for _, b in pairs])
        rho = float(sr.statistic)
        return (None, None) if math.isnan(rho) else (rho, float(sr.pvalue))

    def fmt(rho):
        return f"{rho:+.2f}" if rho is not None else "  na "

    out("=" * 100)
    out(f"p3_rank_stability summary -- {n_q} polish quanta; gate quantum "
        f"q{q_half} (proposals/portfolio.md)")
    out(f"trajectories: {len(complete)} complete, {len(legal_fail)} "
        f"legalize failures, {len(trajs) - len(complete) - len(legal_fail)} "
        f"partial")
    out("=" * 100)

    # -- warm-start check: the substantive test is raw q1 <= legal (acl_best
    #    is non-increasing by construction) plus how often the raw trajectory
    #    ticks up (small/rare is expected: MM improves the chain-size
    #    histogram, not ACL directly; q1 >> legal would mean re-init)
    ok_q1 = viol = upticks = n_steps = 0
    worst, max_up = None, 0.0
    for key, st in complete.items():
        lg, q1 = fv(st, "q0legal", "acl"), fv(st, "q1", "acl")
        if q1 is not None:
            if q1 <= lg + 1e-6:
                ok_q1 += 1
            else:
                viol += 1
                if worst is None or q1 - lg > worst[0]:
                    worst = (q1 - lg, key)
        prev = lg
        for q in range(1, n_q + 1):
            a = fv(st, f"q{q}", "acl")
            if a is not None and prev is not None:
                n_steps += 1
                if a > prev + 1e-6:
                    upticks += 1
                    max_up = max(max_up, a - prev)
            if a is not None:
                prev = a
    out("")
    out(f"warm-start check: {ok_q1}/{ok_q1 + viol} trajectories with raw q1 "
        f"ACL <= legal ACL"
        + (f"; WORST VIOLATION +{worst[0]:.3f} at {worst[1]}" if viol else ""))
    out(f"  raw upticks along trajectories: {upticks}/{n_steps} consecutive "
        f"steps increase (max +{max_up:.3f})")
    if viol:
        out("  WARNING: q1 > legal on some trajectories -- inspect the warm "
            "restart before trusting the probe")

    # -- P3 gate: per-instance and pooled rank stability
    out("")
    out(f"== P3 gate: Spearman rho(acl_best@q, acl_best@q{n_q}) across algo "
        f"seeds ==")
    insts = sorted({k[:3] for k in complete})
    out("instance                ok   "
        + " ".join(f"  q{q} " for q in range(1, n_q))
        + (f"  | rho(q{q_half}, spur)" if has_spur else ""))
    pooled_x = {q: [] for q in range(1, n_q)}
    pooled_y = []
    pooled_xs = {q: [] for q in range(1, n_q)}   # vs spur (own subset)
    pooled_ys = []
    inst_rho_half = []
    for (n, p, i) in insts:
        keys = [k for k in complete if k[:3] == (n, p, i)]
        finals = [fv(complete[k], f"q{n_q}", "acl_best") for k in keys]
        strip = []
        for q in range(1, n_q):
            xs = [fv(complete[k], f"q{q}", "acl_best") for k in keys]
            rho, _ = spear(xs, finals)
            strip.append(rho)
            if len(keys) >= 3:
                mx = statistics.mean(xs)
                pooled_x[q] += [x - mx for x in xs]
        if len(keys) >= 3:
            my = statistics.mean(finals)
            pooled_y += [y - my for y in finals]
        line = (f"n={n:3d} p={p:<4g} i={i}   {len(keys):2d}   "
                + " ".join(fmt(r) for r in strip))
        if has_spur:
            ks = [k for k in keys if fv(complete[k], "spur", "acl") is not None]
            ss = [fv(complete[k], "spur", "acl") for k in ks]
            rho_s, _ = spear([fv(complete[k], f"q{q_half}", "acl_best")
                              for k in ks], ss)
            line += f"  |  {fmt(rho_s)}"
            if len(ks) >= 3:
                ms = statistics.mean(ss)
                pooled_ys += [s - ms for s in ss]
                for q in range(1, n_q):
                    xs = [fv(complete[k], f"q{q}", "acl_best") for k in ks]
                    mx = statistics.mean(xs)
                    pooled_xs[q] += [x - mx for x in xs]
        out(line)
        inst_rho_half.append(strip[q_half - 1] if strip else None)
    pooled_strip = []
    for q in range(1, n_q):
        rho, _ = spear(pooled_x[q], pooled_y)
        pooled_strip.append(rho)
    out(f"pooled (instance-centered, N={len(pooled_y)})   "
        + " ".join(fmt(r) for r in pooled_strip))
    if has_spur and pooled_ys:
        out(f"pooled vs spur ACL   (N={len(pooled_ys)})    "
            + " ".join(fmt(spear(pooled_xs[q], pooled_ys)[0])
                       for q in range(1, n_q)))

    # -- gate verdict
    good = [r for r in inst_rho_half if r is not None]
    n_pass = sum(1 for r in good if r >= 0.5)
    rho_p, pv_p = spear(pooled_x[q_half], pooled_y) if n_q > 1 else (None, None)
    out("")
    out(f"GATE (portfolio.md: rho >= 0.5 at the halfway quantum q{q_half}; "
        f"rho < 0.5 -> no racer):")
    if good:
        out(f"  per-instance rho@q{q_half}: median "
            f"{statistics.median(good):+.3f}; {n_pass}/{len(good)} instances "
            f">= 0.5")
    if rho_p is not None:
        out(f"  pooled (instance-centered) rho@q{q_half} = {rho_p:+.3f} "
            f"(p={pv_p:.2g}, N={len(pooled_y)}) -> "
            f"{'PASS' if rho_p >= 0.5 else 'FAIL'}")

    # -- P4 patience curve: mean ACL vs cumulative time, per cell
    out("")
    out("== P4 patience curve: mean ACL vs cumulative time (complete "
        "trajectories) ==")
    stage_order = (["q0legal"] + [f"q{q}" for q in range(1, n_q + 1)]
                   + (["spur"] if has_spur else []))
    cells = sorted({(k[0], k[1]) for k in complete})
    for (n, p) in cells:
        keys = [k for k in complete if (k[0], k[1]) == (n, p)]
        out(f"-- n={n} p={p:g}  ({len(keys)} trajectories)")
        out("   stage      mean_t_cum   mean_acl   mean_acl_best")
        for stg in stage_order:
            ts = [fv(complete[k], stg, "time_cum") for k in keys]
            ar = [fv(complete[k], stg, "acl") for k in keys]
            ab = [fv(complete[k], stg, "acl_best") for k in keys]
            ts = [x for x in ts if x is not None]
            ar = [x for x in ar if x is not None]
            ab = [x for x in ab if x is not None]
            if not ts:
                continue
            out(f"   {stg:9s} {statistics.mean(ts):9.1f}s   "
                f"{statistics.mean(ar) if ar else float('nan'):8.3f}   "
                f"{statistics.mean(ab) if ab else float('nan'):8.3f}")

    # -- P4 diminishing returns: share of total acl_best improvement/quantum
    out("")
    out("== P4 diminishing returns: mean share of total acl_best improvement "
        "per quantum ==")
    for (n, p) in cells:
        keys = [k for k in complete if (k[0], k[1]) == (n, p)]
        fracs, totals, zero = [], [], 0
        for k in keys:
            st = complete[k]
            b = [fv(st, "q0legal", "acl_best")] + \
                [fv(st, f"q{q}", "acl_best") for q in range(1, n_q + 1)]
            total = b[0] - b[-1]
            if total <= 1e-9:
                zero += 1
                continue
            fracs.append([(b[q - 1] - b[q]) / total
                          for q in range(1, n_q + 1)])
            totals.append(total)
        if not fracs:
            out(f"-- n={n} p={p:g}: no improving trajectories "
                f"({zero} zero-improvement)")
            continue
        mean_f = [statistics.mean(f[q] for f in fracs) for q in range(n_q)]
        cum = []
        s = 0.0
        for m in mean_f:
            s += m
            cum.append(s)
        out(f"-- n={n} p={p:g}: "
            + "  ".join(f"q{q + 1} {100 * m:4.1f}%"
                        for q, m in enumerate(mean_f)))
        out(f"     cumulative: "
            + "  ".join(f"{100 * c:5.1f}%" for c in cum)
            + f"   (mean total drop {statistics.mean(totals):.3f} ACL; "
              f"{zero} zero-improvement trajs)")

    if legal_fail:
        out("")
        out(f"legalize failures ({len(legal_fail)}): "
            + ", ".join(f"n{n} p{p:g} i{i} s{s}"
                        for (n, p, i, s) in legal_fail))
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="P3/P4 gate probe: rank stability of ACL across "
                    "warm-restart polish quanta (proposals/portfolio.md)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true",
                    help="1 instance x 3 seeds x 3 quanta of 3 s; writes to "
                         "separate *_smoke files")
    ap.add_argument("--resume", action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.smoke:
        cells, inst_seeds, algo_seeds = (SMOKE_CELLS, SMOKE_INST_SEEDS,
                                         SMOKE_ALGO_SEEDS)
        n_quanta, quantum_s = SMOKE_N_QUANTA, SMOKE_QUANTUM_S
        csv_path, summary_path = SMOKE_CSV_PATH, SMOKE_SUMMARY_PATH
    else:
        cells, inst_seeds, algo_seeds = CELLS, INST_SEEDS, ALGO_SEEDS
        n_quanta, quantum_s = N_QUANTA, QUANTUM_S
        csv_path, summary_path = CSV_PATH, SUMMARY_PATH

    tasks = [(n, p, i, s, n_quanta, quantum_s)
             for (n, p) in cells for i in inst_seeds for s in algo_seeds]
    total_planned = len(tasks)
    if args.resume:
        done = load_done_keys(csv_path, KEY_FIELDS)
        tasks = [t for t in tasks
                 if stringify_key(t[0], t[1], t[2], t[3]) not in done]
        print(f"resume: {total_planned - len(tasks)} of {total_planned} "
              f"tasks already in {os.path.basename(csv_path)}")
    print(f"cells={list(cells)}  inst_seeds={list(inst_seeds)}  "
          f"algo_seeds={list(algo_seeds)}  tasks to run={len(tasks)}  "
          f"workers={args.workers}")
    print(f"budget/task: {LEGALIZE_TIMEOUT_S:g}s legalize + "
          f"{n_quanta}x{quantum_s:g}s polish quanta "
          f"(+ spur <= {SPUR_DEADLINE_S:g}s, outside the budget)  "
          f"csv={os.path.basename(csv_path)}")

    t0 = time.time()
    if tasks:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=_init_worker) as ex:
            futures = {ex.submit(run_task, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futures), 1):
                try:
                    rows = fut.result()
                except Exception as exc:
                    # append nothing -> --resume retries this task
                    n, p, ins, s, _, _ = futures[fut]
                    print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                          f"n{n} p{p:g} i{ins} s{s}: CRASH "
                          f"{clean_err(repr(exc))}", flush=True)
                    continue
                append_rows(csv_path, FIELDS, rows)
                print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                      f"{_task_line(rows)}", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; rows appended to "
          f"{csv_path}\n")

    text = summarize(csv_path)
    print(text)
    with open(summary_path, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {summary_path}")


if __name__ == "__main__":
    main()
