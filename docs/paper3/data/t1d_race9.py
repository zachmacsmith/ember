"""
docs/paper3/data/t1d_race9.py
==============================
T1d — racer v1.2 A/B: p3-race9 vs p3-race8, PAIRED at the same master seeds
(pre-registered notes.md §4.15, T1d; bars quoted verbatim in the summary).

race9 = race8's roster + the §4.8b beta-dhat arm appended at index 8 + one
terminal anytime_polish pass on the winner (improvement-notes #4-5). Arms 0-7
derive byte-identical per-arm seeds from the master seed in both rosters
(race.py's _arm_seed; unit-tested in tests/algorithms/test_p3_race.py), so a
(cell, inst_seed, base_seed) pair differs ONLY by the two race9 flips — a
clean paired A/B, not a rule-2 baseline read (m3_race.py covers that frame).

Four modes per (cell, inst_seed, base_seed), run BACK-TO-BACK on one outer
worker (same host, same load window — rule 5 within-batch comparability):

  race8-seq   race(..., RACE8_SPEC, n_workers=1)                  1 core
  race9-seq   race(..., RACE9_SPEC, n_workers=1, terminal_polish) 1 core
  race8-par   race(..., RACE8_SPEC, n_workers=8)                  8 cores
  race9-par   race(..., RACE9_SPEC, n_workers=8, terminal_polish) 8 cores

Both par modes get the SAME 8 workers (equal-core fairness frame): race8-par
runs its 7 racing arms on 8 workers, race9-par its 8 on 8 — the roster
difference is the treatment, the cores are controlled.

Cells (Z12 only, the §4.15 dev registry): (160, 0.05) — the sparse cell the
bar is stated on — and (100, 0.2) as the mid-density context cell. Instance
seeds 101-105, base (master) seeds 0-4, 60 s per mode. Both `acl` and
`acl_spur` recorded (rule 3); the paired reads use `acl_spur`.

PRE-REGISTERED BARS (notes.md §4.15, printed as verdicts by the summary):
  race9 vs race8, paired at the same master seeds: median < -0.5% AND >=60%W
  on (160,0.05) in >=1 fairness read (seq or par) with the other read
  non-regressing (median <= 0). Diagnostic: race9 worse on >40% of pairs in
  ANY read -> roster-interference investigation before shipping.

Run:
  .venv/bin/python docs/paper3/data/t1d_race9.py --outer-workers 5   # hyde06
  .venv/bin/python docs/paper3/data/t1d_race9.py --smoke             # local
Flags: --outer-workers N | --smoke | --resume
--smoke writes to t1d_race9_smoke.csv (1 combo, 12 s budget; smoke keys must
never enter the full CSV's resume keys). The mm fork .so must be built (or
EMBER_MM_FORK_DIR exported) BEFORE launch: without it race9's mm-beta arm and
both rosters' cuthill arm are silently skipped (roster integrity).
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
    race, RACE8_SPEC, RACE9_SPEC,
)

CSV_PATH = os.path.join(HERE, "t1d_race9.csv")
SUMMARY_PATH = os.path.join(HERE, "t1d_race9_summary.txt")

TOPO = "Z12"
BUDGET = 60.0                  # s per mode (protocol rule 5)
SMOKE_BUDGET = 12.0
POLISH_DEADLINE_S = 5.0        # rule-3 parity spur-prune (acl_spur)
N_PAR = 8                      # workers for BOTH par modes (equal cores)
INST_SEEDS = (101, 102, 103, 104, 105)
BASE_SEEDS = (0, 1, 2, 3, 4)

CELLS = [(160, 0.05), (100, 0.2)]      # (160,0.05) carries the bar
BAR_CELL = (160, 0.05)

MODE_ORDER = ("race8-seq", "race9-seq", "race8-par", "race9-par")
#: mode -> (arms_spec, n_workers, terminal_polish)
MODES = {
    "race8-seq": (RACE8_SPEC, 1, False),
    "race9-seq": (RACE9_SPEC, 1, True),
    "race8-par": (RACE8_SPEC, N_PAR, False),
    "race9-par": (RACE9_SPEC, N_PAR, True),
}
READS = (("seq", "race9-seq", "race8-seq"), ("par", "race9-par", "race8-par"))

FIELDS = ["topo", "n", "p", "inst_seed", "base_seed", "mode", "status",
          "success", "acl", "acl_spur", "max_chain", "qubits", "wall",
          "winner", "n_edges", "err", "arm_meta"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "base_seed", "mode"]


# ──────────────────────────────────────────────────────────────────────────────
# Outer worker
# ──────────────────────────────────────────────────────────────────────────────

_G = {}      # topo -> {"target", "adj"}


def _init_worker(_unused=None):
    tgt = build_target(TOPO)
    _G[TOPO] = {"target": tgt, "adj": build_adjacency(tgt)}


def _compact(md, limit=600):
    try:
        return json.dumps(md, separators=(",", ":"), default=str)[:limit]
    except Exception:
        return ""


def _mode_race(src, g, budget, base_seed, mode):
    spec, n_workers, tpol = MODES[mode]
    t0 = time.perf_counter()
    r = race(src, g["target"], budget, base_seed, spec, n_workers=n_workers,
             terminal_polish=tpol)
    wall = time.perf_counter() - t0
    w = r.get("winner")
    winner = f"{w['kind']}[{w['index']}]@{w['stage']}" if w else ""
    meta = {"final_survivor": r.get("final_survivor"),
            "elapsed_s": r.get("elapsed_s"),
            "terminal_polish_s": r.get("budget", {}).get("terminal_polish_s"),
            "arms": {str(a["index"]): [a["kind"], a["status"], a["acl_best"]]
                     for a in r.get("arms", [])}}
    return {"embedding": r["embedding"] or None, "wall": wall,
            "winner": winner, "meta": meta,
            "err": "" if r["success"] else "race: no valid embedding"}


def run_combo(task):
    """Run the requested modes of one (cell, inst, base) combo, strictly
    sequentially, and return one CSV row per mode."""
    n, p, inst_seed, base_seed, budget, modes = task
    src = make_instance(n, p, inst_seed)
    g = _G[TOPO]
    rows = []
    for mode in MODE_ORDER:
        if mode not in modes:
            continue
        row = {"topo": TOPO, "n": n, "p": p, "inst_seed": inst_seed,
               "base_seed": base_seed, "mode": mode, "status": "", "success": 0,
               "acl": "", "acl_spur": "", "max_chain": "", "qubits": "",
               "wall": "", "winner": "", "n_edges": src.number_of_edges(),
               "err": "", "arm_meta": ""}
        try:
            res = _mode_race(src, g, budget, base_seed, mode)
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
# Summary — the pre-registered paired reads + the §4.15 verdicts
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


def _read_stats(pairs):
    """n, med delta, pct-of-baseline median, win/loss/tie counts + rates."""
    if not pairs:
        return None
    deltas = [a - b for a, b in pairs]
    win = sum(1 for d in deltas if d < -1e-9)
    loss = sum(1 for d in deltas if d > 1e-9)
    med = statistics.median(deltas)
    ref = statistics.median(b for _a, b in pairs)
    pct = 100.0 * med / ref if ref else float("nan")
    n = len(deltas)
    return {"n": n, "med": med, "pct": pct, "win": win, "loss": loss,
            "tie": n - win - loss, "win_rate": 100.0 * win / n,
            "loss_rate": 100.0 * loss / n}


def _fmt_read(tag, st):
    if st is None:
        return f"  {tag}: no both-succeed pairs"
    return (f"  {tag}: n={st['n']:2d}  med d {st['med']:+7.3f} "
            f"({st['pct']:+6.2f}%)  W/L/T {st['win']}/{st['loss']}/{st['tie']}"
            f"  win {st['win_rate']:5.1f}%")


def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    out("=" * 100)
    out("T1d racer v1.2 summary — race9 vs race8, PAIRED at the same master "
        "seeds; column: acl_spur (rule 3);")
    out("pairs on (inst_seed, base_seed), both-succeed only. Reads: [seq] "
        "race9-seq vs race8-seq, [par] race9-par vs race8-par.")
    out("PRE-REGISTERED BAR (notes.md 4.15): median < -0.5% AND >=60%W on "
        "(160,0.05) in >=1 read, other read non-regressing (median <= 0).")
    out("DIAGNOSTIC: race9 worse on >40% of pairs in ANY read -> "
        "roster-interference investigation before shipping.")
    out("=" * 100)
    cells = sorted({(int(r["n"]), float(r["p"])) for r in rows},
                   key=lambda c: c[1])
    stats = {}          # (cell, read_tag) -> stats dict
    for n, p in cells:
        cell = [r for r in rows if int(r["n"]) == n and float(r["p"]) == p]
        out("")
        out(f"-- {TOPO}  n={n}  p={p:g}")
        for mode in MODE_ORDER:
            mrows = [r for r in cell if r["mode"] == mode]
            n_ok = sum(1 for r in mrows if r["success"] == "1")
            accs = [float(r["acl_spur"]) for r in mrows
                    if r["success"] == "1" and r["acl_spur"]]
            walls = sorted(float(r["wall"]) for r in mrows if r["wall"])
            wins = {}
            tps = []
            for r in mrows:
                if r["success"] == "1" and r["winner"]:
                    k = r["winner"].split("[")[0]
                    wins[k] = wins.get(k, 0) + 1
                if r["arm_meta"]:
                    try:
                        tp = json.loads(r["arm_meta"]).get("terminal_polish_s")
                        if tp is not None:
                            tps.append(float(tp))
                    except Exception:
                        pass
            line = f"  {mode:10s} success {n_ok}/{len(mrows)}  "
            line += (f"acl_spur med {statistics.median(accs):7.3f}  "
                     if accs else "acl_spur med     n/a  ")
            line += (f"wall med {statistics.median(walls):6.1f}s  "
                     if walls else "wall med    n/a  ")
            if tps:
                line += f"tpol med {statistics.median(tps):4.1f}s  "
            out(line + f"winners {wins}")
        for tag, mode_a, mode_b in READS:
            st = _read_stats(_paired_read(cell, mode_a, mode_b))
            stats[((n, p), tag)] = st
            out(_fmt_read(f"[{tag}] {mode_a} vs {mode_b}", st))

    # ── §4.15 verdicts ────────────────────────────────────────────────────────
    out("")
    out("VERDICTS (notes.md 4.15, race9-vs-race8 bar):")
    bar = {tag: stats.get((BAR_CELL, tag)) for tag, _a, _b in READS}
    if any(v is None for v in bar.values()):
        out(f"  BAR CELL {BAR_CELL}: INCOMPLETE — a read has no "
            f"both-succeed pairs; no verdict.")
    else:
        seq, par = bar["seq"], bar["par"]
        passes = {t: (s["pct"] < -0.5 and s["win_rate"] >= 60.0)
                  for t, s in bar.items()}
        nonreg = {t: (s["pct"] <= 0.0) for t, s in bar.items()}
        ok = ((passes["seq"] and nonreg["par"])
              or (passes["par"] and nonreg["seq"]))
        for t in ("seq", "par"):
            s = bar[t]
            out(f"  {BAR_CELL} [{t}]: med {s['pct']:+.2f}% "
                f"win {s['win_rate']:.0f}%  -> "
                f"{'meets win-bar' if passes[t] else 'no win-bar'}"
                f"{'' if nonreg[t] else ', REGRESSING (median > 0)'}")
        out(f"  BAR: {'PASS' if ok else 'FAIL'} — needs >=1 read with "
            f"median < -0.5% AND >=60%W, other read median <= 0.")
    flagged = [(c, t) for (c, t), s in sorted(stats.items())
               if s is not None and s["loss_rate"] > 40.0]
    if flagged:
        for c, t in flagged:
            s = stats[(c, t)]
            out(f"  DIAGNOSTIC TRIPPED: {c} [{t}] race9 worse on "
                f"{s['loss_rate']:.0f}% of pairs (> 40%) -> "
                f"roster-interference investigation before shipping.")
    else:
        out("  diagnostic clean: no read has race9 worse on > 40% of pairs.")
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="T1d race9-vs-race8 paired A/B (see module docstring)")
    ap.add_argument("--outer-workers", type=int, default=1,
                    help="combos in flight; par modes use <= 8 inner workers "
                         "each (default 1 => total <= 8+1 procs)")
    ap.add_argument("--smoke", action="store_true",
                    help="local check: 1 combo, 12 s budget, all 4 modes")
    ap.add_argument("--resume", action="store_true",
                    help="skip (cell,inst,base,mode) keys already in the CSV")
    return ap.parse_args()


def main():
    args = parse_args()
    from ember_qc.algorithms.minorminer_forked import _find_so
    if _find_so() is None:
        sys.exit("fork .so missing — race9's mm-beta arm (and both rosters' "
                 "cuthill arm) would be silently skipped (roster integrity); "
                 "build it or export EMBER_MM_FORK_DIR first")

    if args.smoke:
        cells = [CELLS[0]]
        inst_seeds, base_seeds, budget = (101,), (0,), SMOKE_BUDGET
        csv_path = CSV_PATH.replace(".csv", "_smoke.csv")
        summary_path = SUMMARY_PATH.replace(".txt", "_smoke.txt")
    else:
        cells = CELLS
        inst_seeds, base_seeds, budget = INST_SEEDS, BASE_SEEDS, BUDGET
        csv_path, summary_path = CSV_PATH, SUMMARY_PATH

    # Prelude: warm the busclique disk cache (race's template slot uses it).
    from minorminer.busclique import busgraph_cache
    t0 = time.perf_counter()
    m = len(busgraph_cache(build_target(TOPO)).largest_clique())
    print(f"prelude: {TOPO} max clique = {m}  [{time.perf_counter() - t0:.1f}s]")

    done = load_done_keys(csv_path, KEY_FIELDS) if args.resume else set()
    combos = []
    for n, p in cells:
        for i in inst_seeds:
            for b in base_seeds:
                modes = tuple(
                    m for m in MODE_ORDER
                    if stringify_key(TOPO, n, p, i, b, m) not in done)
                if modes:
                    combos.append((n, p, i, b, budget, modes))
    n_modes = sum(len(c[5]) for c in combos)
    print(f"cells={len(cells)}  combos={len(combos)}  mode-runs={n_modes}  "
          f"budget={budget:g}s  outer-workers={args.outer_workers}  "
          f"(par modes: {N_PAR} inner workers)")

    t0 = time.time()
    if combos:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.outer_workers,
                                 mp_context=ctx, initializer=_init_worker,
                                 initargs=(None,)) as ex:
            futures = {ex.submit(run_combo, c): c for c in combos}
            ndone = 0
            for fut in as_completed(futures):
                n, p, i, b, _bud, modes = futures[fut]
                try:
                    rows = fut.result()
                except Exception as exc:
                    rows = []
                    for m in modes:
                        row = dict.fromkeys(FIELDS, "")
                        row.update(topo=TOPO, n=n, p=p, inst_seed=i,
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
