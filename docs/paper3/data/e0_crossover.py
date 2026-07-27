"""
docs/paper3/data/e0_crossover.py
=================================
E0: the density-resolved crossover map (notes.md thesis; protocol.md rules).
Seven arms per (topology, n, p, instance) cell, paired by literal
(inst_seed, algo_seed) through the script route (protocol rule 1):

  minorminer      stock minorminer 0.2.22 via benchmark_one (the control)
  mmfork-cuthill  the C++ fork guided by Cuthill-McKee, fallback=False
  clmm            Zbinden-style CLMM: right-sized busclique chains as
                  initial_chains, then stock MM (source passed as a GRAPH
                  OBJECT — the isolated-vertex bug, see algorithms/minorminer.py)
  template        the §3.26 recipe: busclique K_n chains, identity assignment,
                  spur-pruned against the actual source edges (deterministic)
  clique          raw busclique on the source via the registry (may fail; data)
  pssa            registry pssa
  attraction      registry attraction

Candidate arms (clmm/template/clique/pssa/attraction) run under a subprocess
watchdog with hard kill at timeout+30 s; MM-family arms are exempt (protocol,
route choice). Every successful embedding from every arm gets the same
deadline-bounded terminal spur-prune; the CSV records both `acl` (raw) and
`acl_spur` (protocol rule 3 — polish parity).

Grid: see GRID below. p=1.0 rows are K_n and instance-seed-independent, so they
run one instance (seed 101) instead of three (duplicate (instance, algo_seed)
runs would be pure waste + pseudo-replication). The Z12 K_n ladder is built
adaptively at runtime from Z12's busclique max clique M (frontier rungs
M-5/M/M+5; 180 included iff 180 <= M+10).

Writes one flushed row per run to e0_crossover.csv next to this file (resume
with --resume) and prints + writes a paired per-cell summary to
e0_crossover_summary.txt.

Run:
  .venv/bin/python docs/paper3/data/e0_crossover.py --workers 48        # full (hyde06)
  .venv/bin/python docs/paper3/data/e0_crossover.py --smoke --workers 4 # local smoke
  .venv/bin/python docs/paper3/data/e0_crossover.py --quick --workers 8
Flags: --workers N | --smoke | --quick | --resume | --topo P16|Z12|both
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import csv
import multiprocessing
import random
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _runner_common import (  # noqa: E402
    acl, append_row, build_target, clean_err, embedding_metrics,
    load_done_keys, make_instance, run_arm_watchdogged, stringify_key,
    terminal_polish,
)

from ember_qc.benchmark import benchmark_one  # noqa: E402
from ember_qc.registry import ALGORITHM_REGISTRY  # noqa: E402
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.factored.polish import spur_prune  # noqa: E402

CSV_PATH = os.path.join(HERE, "e0_crossover.csv")
SUMMARY_PATH = os.path.join(HERE, "e0_crossover_summary.txt")

TIMEOUT = 60.0                 # s per attempt (protocol rule 5)
WATCHDOG_GRACE = 30.0          # hard kill at timeout + grace (protocol)
POLISH_DEADLINE_S = 5.0        # terminal spur-prune budget (acl_spur)
INST_SEEDS = (101, 102, 103)   # DEV registry (protocol rule 4; E0 slice)
ALGO_SEEDS = (0, 1, 2, 3, 4)   # DEV algorithm seeds
DET_SEED = -1                  # recorded algo_seed for deterministic arms

# n-ladders per density. p=1.0 is the P16 ladder; Z12's K_n ladder is built at
# runtime from its max clique M (see z12_clique_ladder()).
GRID = {
    1.0:  [60, 100, 140, 180],
    0.9:  [40, 60, 80, 100, 140, 180],
    0.7:  [40, 60, 80, 100, 140, 180, 220],
    0.5:  [60, 80, 100, 140, 180, 240],
    0.3:  [60, 100, 140, 180, 240, 300],
    0.2:  [60, 100, 140, 200, 260, 340],
    0.12: [60, 100, 160, 220, 300, 400],
    0.08: [80, 120, 180, 260, 360, 480],
    0.05: [100, 160, 240, 340, 460, 600],
}

ARMS = ("minorminer", "mmfork-cuthill", "clmm", "template", "clique",
        "pssa", "attraction")
SEEDED_ARMS = {"minorminer", "mmfork-cuthill", "clmm", "pssa", "attraction"}
MM_FAMILY = {"minorminer", "mmfork-cuthill"}   # watchdog-exempt (cooperative)

SMOKE_CELLS = [(100, 0.5), (60, 1.0), (160, 0.12)]   # P16 only
SMOKE_TIMEOUT = 20.0
QUICK_ARMS = ("minorminer", "mmfork-cuthill", "template", "clique")

FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed", "status",
          "success", "acl", "acl_spur", "acl_pre", "max_chain", "qubits",
          "time", "n_edges", "err"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed"]


# ──────────────────────────────────────────────────────────────────────────────
# Worker state — built once per worker process (never pickled through queues)
# ──────────────────────────────────────────────────────────────────────────────

_G = {}   # topo -> {"target", "adj", "cache", "maxclique"}


def _init_worker(topo_names):
    from minorminer.busclique import busgraph_cache
    for t in topo_names:
        tgt = build_target(t)
        cache = busgraph_cache(tgt)   # disk cache warmed by the parent prelude
        _G[t] = {"target": tgt, "adj": build_adjacency(tgt), "cache": cache,
                 "maxclique": len(cache.largest_clique())}


# ──────────────────────────────────────────────────────────────────────────────
# Arms — each returns a plain result dict:
#   {success, status, acl, max_chain, qubits, time, embedding, err[, acl_pre]}
# ──────────────────────────────────────────────────────────────────────────────

def _from_benchmark(r):
    ok = bool(r.success and r.is_valid and r.embedding)
    return {"success": ok, "status": r.status,
            "acl": r.avg_chain_length if ok else None,
            "max_chain": r.max_chain_length if ok else None,
            "qubits": r.total_qubits_used if ok else None,
            "time": r.wall_time,
            "embedding": r.embedding if ok else None,
            "err": r.error or ""}


def _arm_registry(arm, src, topo, algo_seed, timeout):
    """Any registered algorithm through benchmark_one (protocol rule 1)."""
    kwargs = {"seed": int(algo_seed) if algo_seed >= 0 else 0}
    if arm.startswith("mmfork"):
        kwargs["fallback"] = False     # pure arm, never silently stock (protocol)
    r = benchmark_one(src, _G[topo]["target"], arm, timeout=timeout, **kwargs)
    return _from_benchmark(r)


def _arm_clmm(src, topo, p, algo_seed, timeout):
    """CLMM (Zbinden et al. 2020): k right-sized busclique chains as
    initial_chains for stock MM. k = min(n, max clique); vertex choice when
    n > k: p >= 0.3 -> k random vertices (rng from algo seed), p < 0.3 -> k
    lowest-degree vertices. One wall-clock budget across both stages."""
    import minorminer as _mm
    g = _G[topo]
    t0 = time.perf_counter()
    deadline = t0 + timeout
    n = src.number_of_nodes()
    k = min(n, g["maxclique"])
    raw = g["cache"].find_clique_embedding(k)
    chain_list = [[int(q) for q in raw[key]] for key in sorted(raw)]
    nodes = sorted(int(v) for v in src.nodes())
    if n <= k:
        chosen = nodes
    elif p >= 0.3:
        rng = random.Random(int(algo_seed))
        chosen = sorted(rng.sample(nodes, k))
    else:
        degs = dict(src.degree())
        chosen = sorted(sorted(nodes, key=lambda v: (degs[v], v))[:k])
    initial = {v: chain_list[i] for i, v in enumerate(chosen)}
    remaining = max(1.0, deadline - time.perf_counter())
    # Source passed as the GRAPH OBJECT (edge-list form drops isolated vertices).
    emb = _mm.find_embedding(src, list(g["target"].edges()),
                             initial_chains=initial, timeout=remaining,
                             random_seed=int(algo_seed))
    elapsed = time.perf_counter() - t0
    if not emb:
        return {"success": False, "status": "FAILURE", "time": elapsed,
                "embedding": None, "err": "clmm: MM stage returned empty"}
    emb = {int(v): [int(q) for q in c] for v, c in emb.items()}
    if not is_valid_embedding(emb, src, g["target"], adj=g["adj"]):
        return {"success": False, "status": "INVALID_OUTPUT", "time": elapsed,
                "embedding": None, "err": "clmm: invalid embedding"}
    m = embedding_metrics(emb, g["target"])
    return {"success": True, "status": "SUCCESS", "acl": m["acl"],
            "max_chain": m["max_chain"], "qubits": m["qubits"],
            "time": elapsed, "embedding": emb, "err": ""}


def _arm_template(src, topo, timeout):
    """The §3.26 recipe: busclique K_n chains, vertex i -> chain i (identity
    over sorted vertices; valid for ANY subgraph of K_n by construction), then
    spur-prune against the actual source edges. Deterministic."""
    g = _G[topo]
    t0 = time.perf_counter()
    n = src.number_of_nodes()
    if n > g["maxclique"]:
        return {"success": False, "status": "INFEASIBLE",
                "time": time.perf_counter() - t0, "embedding": None,
                "err": f"n={n} > max clique {g['maxclique']}"}
    raw = g["cache"].find_clique_embedding(n)
    chain_list = [[int(q) for q in raw[key]] for key in sorted(raw)]
    nodes = sorted(int(v) for v in src.nodes())
    emb = {v: chain_list[i] for i, v in enumerate(nodes)}
    acl_pre = acl(emb)
    src_adj = {v: sorted(int(u) for u in src.neighbors(v)) for v in nodes}
    pruned = spur_prune(emb, src_adj, g["adj"], deadline=t0 + timeout)
    elapsed = time.perf_counter() - t0
    if not is_valid_embedding(pruned, src, g["target"], adj=g["adj"]):
        return {"success": False, "status": "INVALID_OUTPUT", "time": elapsed,
                "embedding": None, "acl_pre": acl_pre,
                "err": "template: pruned embedding invalid"}
    m = embedding_metrics(pruned, g["target"])
    return {"success": True, "status": "SUCCESS", "acl": m["acl"],
            "max_chain": m["max_chain"], "qubits": m["qubits"],
            "time": elapsed, "embedding": pruned, "acl_pre": acl_pre,
            "err": ""}


# ──────────────────────────────────────────────────────────────────────────────
# Task runner (executes inside a pool worker)
# ──────────────────────────────────────────────────────────────────────────────

def run_task(task):
    topo, n, p, inst_seed, arm, algo_seed, timeout = task
    src = make_instance(n, p, inst_seed)
    g = _G[topo]
    row = {"topo": topo, "n": n, "p": p, "inst_seed": inst_seed, "arm": arm,
           "algo_seed": algo_seed, "status": "", "success": 0, "acl": "",
           "acl_spur": "", "acl_pre": "", "max_chain": "", "qubits": "",
           "time": "", "n_edges": src.number_of_edges(), "err": ""}

    if arm in MM_FAMILY:
        if arm.startswith("mmfork"):
            ok, msg = ALGORITHM_REGISTRY[arm].is_available()
            if not ok:
                row.update(status="UNAVAILABLE", err=clean_err(msg))
                return row
        wstatus, res, werr = "OK", _arm_registry(arm, src, topo, algo_seed,
                                                 timeout), ""
    elif arm == "clmm":
        wstatus, res, werr = run_arm_watchdogged(
            _arm_clmm, timeout, grace_s=WATCHDOG_GRACE,
            args=(src, topo, p, algo_seed, timeout))
    elif arm == "template":
        wstatus, res, werr = run_arm_watchdogged(
            _arm_template, timeout, grace_s=WATCHDOG_GRACE,
            args=(src, topo, timeout))
    else:   # clique / pssa / attraction — registry arms, still watchdogged
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
    if res.get("acl_pre") is not None:
        row["acl_pre"] = round(res["acl_pre"], 4)
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
# Cell / task construction
# ──────────────────────────────────────────────────────────────────────────────

def z12_clique_ladder(max_clique):
    """Adaptive Z12 K_n ladder: 60/100/140, 180 iff <= M+10, plus frontier
    rungs M-5, M, M+5 (deduped, sorted)."""
    ladder = [60, 100, 140]
    if 180 <= max_clique + 10:
        ladder.append(180)
    ladder += [max_clique - 5, max_clique, max_clique + 5]
    return sorted(set(ladder))


def build_cells(mode, topos, z12_max_clique):
    """Ordered list of (topo, n, p) cells for the given mode."""
    if mode == "smoke":
        return [("P16", n, p) for n, p in SMOKE_CELLS]
    cells = []
    for topo in topos:
        for p in sorted(GRID, reverse=True):    # dense first
            ladder = GRID[p]
            if topo == "Z12" and p == 1.0:
                ladder = z12_clique_ladder(z12_max_clique)
            if mode == "quick":
                idx = sorted({1, 3, len(ladder) - 1} & set(range(len(ladder))))
                ladder = [ladder[i] for i in idx]
            for n in ladder:
                cells.append((topo, n, p))
    return cells


def inst_seeds_for(p, inst_seeds):
    """K_n cells are instance-seed-independent: run one instance, not three."""
    return (inst_seeds[0],) if p >= 1.0 else tuple(inst_seeds)


def build_tasks(cells, arms, inst_seeds, algo_seeds, timeout):
    tasks = []
    for topo, n, p in cells:
        for inst_seed in inst_seeds_for(p, inst_seeds):
            for arm in arms:
                seeds = algo_seeds if arm in SEEDED_ARMS else (DET_SEED,)
                for s in seeds:
                    tasks.append((topo, n, p, inst_seed, arm, s, timeout))
    return tasks


# ──────────────────────────────────────────────────────────────────────────────
# Summary (paired, per protocol rules 1/3/4)
# ──────────────────────────────────────────────────────────────────────────────

def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    out("=" * 100)
    out("E0 crossover summary — ACL column: acl_spur (spur-pruned, ALL arms; "
        "protocol rule 3)")
    out("dACL = arm - minorminer on both-succeed (inst_seed, algo_seed) pairs; "
        "deterministic arms pair")
    out("against every minorminer seed run on the same instance. "
        "Success rates are unpaired.")
    out("=" * 100)

    cells = sorted({(r["topo"], float(r["p"]), int(r["n"])) for r in rows},
                   key=lambda c: (c[0], -c[1], c[2]))
    arm_order = {a: i for i, a in enumerate(ARMS)}
    for topo, p, n in cells:
        cell = [r for r in rows
                if r["topo"] == topo and float(r["p"]) == p and int(r["n"]) == n]
        mm = [r for r in cell if r["arm"] == "minorminer"]
        mm_ok = {(r["inst_seed"], r["algo_seed"]): float(r["acl_spur"])
                 for r in mm if r["success"] == "1" and r["acl_spur"]}
        frontier = " [FRONTIER: minorminer 0/%d]" % len(mm) if mm and not mm_ok \
            else ("" if mm else " [no minorminer rows]")
        out("")
        out(f"-- {topo}  n={n}  p={p:g}{frontier}")
        arms_here = sorted({r["arm"] for r in cell},
                           key=lambda a: arm_order.get(a, 99))
        for arm in arms_here:
            arows = [r for r in cell if r["arm"] == arm]
            n_ok = sum(1 for r in arows if r["success"] == "1")
            times = sorted(float(r["time"]) for r in arows if r["time"])
            med_t = statistics.median(times) if times else float("nan")
            base = (f"  {arm:15s} success {n_ok}/{len(arows)}   "
                    f"med time {med_t:7.2f}s")
            if arm == "minorminer":
                accs = [float(r["acl_spur"]) for r in arows
                        if r["success"] == "1" and r["acl_spur"]]
                if accs:
                    base += (f"   acl_spur mean {statistics.mean(accs):.3f} "
                             f"median {statistics.median(accs):.3f}")
                out(base)
                continue
            # paired deltas vs minorminer
            pairs = []
            for r in arows:
                if r["success"] != "1" or not r["acl_spur"]:
                    continue
                a_val = float(r["acl_spur"])
                if r["algo_seed"] == str(DET_SEED):
                    pairs += [(a_val, v) for (i, _s), v in mm_ok.items()
                              if i == r["inst_seed"]]
                else:
                    key = (r["inst_seed"], r["algo_seed"])
                    if key in mm_ok:
                        pairs.append((a_val, mm_ok[key]))
            if pairs:
                deltas = [a - m for a, m in pairs]
                win = sum(1 for d in deltas if d < 0)
                loss = sum(1 for d in deltas if d > 0)
                tie = len(deltas) - win - loss
                base += (f"   pairs {len(deltas):3d}  dACL_spur mean "
                         f"{statistics.mean(deltas):+7.3f} median "
                         f"{statistics.median(deltas):+7.3f}  W/L/T "
                         f"{win}/{loss}/{tie}")
            elif n_ok and not mm_ok:
                accs = [float(r["acl_spur"]) for r in arows
                        if r["success"] == "1" and r["acl_spur"]]
                base += (f"   [unpairable: mm 0 successes]  acl_spur mean "
                         f"{statistics.mean(accs):.3f}")
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
                    help="tiny local check: P16, 3 cells, all arms, 20 s")
    ap.add_argument("--quick", action="store_true",
                    help="P16, rungs 2/4/top, 4 arms, 1 inst, 2 seeds")
    ap.add_argument("--resume", action="store_true",
                    help="skip (topo,n,p,inst,arm,seed) keys already in the CSV")
    ap.add_argument("--topo", choices=("P16", "Z12", "both"), default="both")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.smoke and args.quick:
        sys.exit("--smoke and --quick are mutually exclusive")
    mode = "smoke" if args.smoke else ("quick" if args.quick else "full")

    topos = ("P16", "Z12") if args.topo == "both" else (args.topo,)
    if mode in ("smoke", "quick"):
        topos = ("P16",)
    timeout = SMOKE_TIMEOUT if mode == "smoke" else TIMEOUT
    algo_seeds = (0, 1) if mode in ("smoke", "quick") else ALGO_SEEDS
    inst_seeds = (101,) if mode in ("smoke", "quick") else INST_SEEDS
    arms = QUICK_ARMS if mode == "quick" else ARMS

    # ── PRELUDE: build targets + busclique caches in the parent, report M ────
    from minorminer.busclique import busgraph_cache
    max_cliques = {}
    for t in topos:
        t0 = time.perf_counter()
        tgt = build_target(t)
        cache = busgraph_cache(tgt)
        m = len(cache.largest_clique())
        max_cliques[t] = m
        print(f"prelude: {t} built ({tgt.number_of_nodes()} qubits), "
              f"max clique = {m}  [{time.perf_counter() - t0:.1f}s]")
        if t == "P16" and m != 180:
            print(f"WARNING: P16 max clique = {m}, expected 180 — "
                  f"busclique cache anomaly; continuing")
        if t == "Z12":
            print(f"Z12 max clique = {m}")
        del cache, tgt   # workers build their own; keep no handles across fork

    cells = build_cells(mode, topos, max_cliques.get("Z12", 0))
    tasks = build_tasks(cells, arms, inst_seeds, algo_seeds, timeout)
    total_planned = len(tasks)
    if args.resume:
        done = load_done_keys(CSV_PATH, KEY_FIELDS)
        tasks = [t for t in tasks
                 if stringify_key(*t[:6]) not in done]
        print(f"resume: {total_planned - len(tasks)} of {total_planned} tasks "
              f"already in {os.path.basename(CSV_PATH)}")
    print(f"mode={mode}  topos={topos}  cells={len(cells)}  arms={len(arms)}  "
          f"tasks to run={len(tasks)}  timeout={timeout:g}s  "
          f"workers={args.workers}")

    t0 = time.time()
    if tasks:
        # ProcessPoolExecutor, not multiprocessing.Pool: Pool workers are
        # daemonic and cannot spawn the per-run watchdog child. Executor
        # workers are non-daemonic (Python >= 3.9) with the same
        # initializer/initargs semantics.
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
                    row = {"topo": topo, "n": n, "p": p,
                           "inst_seed": inst_seed, "arm": arm,
                           "algo_seed": algo_seed, "status": "CRASH",
                           "success": 0, "acl": "", "acl_spur": "",
                           "acl_pre": "", "max_chain": "", "qubits": "",
                           "time": "", "n_edges": "",
                           "err": clean_err(f"runner: {exc!r}")}
                append_row(CSV_PATH, FIELDS, row)
                a = f"acl={row['acl']}/{row['acl_spur']}" if row["success"] else ""
                print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                      f"{row['topo']} n{row['n']} p{row['p']:g} "
                      f"i{row['inst_seed']} {row['arm']} s{row['algo_seed']}: "
                      f"{row['status']} {a} {row['time']}s", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; "
          f"rows appended to {CSV_PATH}\n")

    text = summarize(CSV_PATH)
    print(text)
    with open(SUMMARY_PATH, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
