"""
docs/paper3/data/p1_kg2.py
===========================
P1 KG2 — the assignment honesty gate (proposals/ate.md, kill gate KG2).
Does the template arm's 2-swap assignment optimizer earn its complexity, or
do the seed orders (or ANY assignment) already capture everything?

On the 6 dev cells where the template wins (P16/Z12: (100, 0.3), (140, 0.2),
(140, 1.0)=K140), for each instance (seeds 101-105; K_n cells once), compute
the template's spur-pruned ACL under:

  identity     vertex i -> chain i (E0's `template` arm assignment)
  cuthill      slots from cuthill_mckee_order(G)
  spectral     slots from spectral_order(G)
  shipped      the as-built pipeline: best-of-3 seed orders scored by the
               span simulator, then deterministic 2-swap refinement
               (_template_core.assign_slots, refine=True)
  rand-00..31  32 random slot permutations, rng seeded 0..31 (deterministic)

Everything is template-side (busclique K_n template -> assignment ->
restrict_template == exact spur_prune against the source edges): NO
minorminer anywhere, no algorithm seeds, fully deterministic — protocol
rule 2's "internal best-of-N inside one MM budget" note applies with room to
spare (the whole gate costs seconds per instance).

Measurement note (rule 3): the evaluation pipeline is prune-only — the
shipped arm's optional 50 ms shorten_chains stage is OMITTED for every
assignment uniformly, so the column isolates the ASSIGNMENT signal exactly as
KG2's drafted bar specifies ("32 random assignments + prune"). The pruned
output IS spur-pruned, so the recorded `acl_spur` is the rule-3 column;
`acl_pre` (pre-prune template ACL) is assignment-invariant and recorded once
per row as a sanity anchor. On K_n cells the source is complete, so the
pruned ACL is assignment-INVARIANT by symmetry (assign_slots' complete_skip
fast path); the K140 cells are kept as a degenerate control demonstrating
exactly that.

Pre-registered kill reads (ate.md KG2), per cell on the acl_spur column:
  READ1  if best-of-32-random gain over identity < 2% (median over
         instances) -> the 2-swap optimizer DIES (there is nothing to
         optimize; seeds-only, refine=False default).
  READ2  if the three seed orders capture >= 80% of the identity->best-of-32
         spread (median capture fraction) -> keep seeds-only.
  Also reported: shipped vs best-of-32 vs best seed (does the 2-swap reach
  the random oracle?).

Run:
  .venv/bin/python docs/paper3/data/p1_kg2.py --workers 8
  .venv/bin/python docs/paper3/data/p1_kg2.py --smoke
Flags: --workers N | --smoke | --resume | --n-random N (default 32)
--smoke writes to p1_kg2_smoke.csv (kg2 rows are deterministic, but the smoke
uses fewer random draws — keeping it out of the full CSV avoids a resume run
silently inheriting the truncated random set).
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import csv
import json
import multiprocessing
import random
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _runner_common import (  # noqa: E402
    append_row, build_target, clean_err, load_done_keys, make_instance,
    stringify_key,
)

from ember_qc.embedding_backend import is_valid_embedding  # noqa: E402
from ember_qc.algorithms.search_orders import (  # noqa: E402
    cuthill_mckee_order, spectral_order,
)
from ember_qc.algorithms.paper3._template_core import (  # noqa: E402
    get_target_state, ordered_template, assign_slots, restrict_template,
    simulate_objective,
)

CSV_PATH = os.path.join(HERE, "p1_kg2.csv")
SUMMARY_PATH = os.path.join(HERE, "p1_kg2_summary.txt")

CELLS = [(topo, n, p)
         for topo in ("P16", "Z12")
         for n, p in ((100, 0.3), (140, 0.2), (140, 1.0))]
INST_SEEDS = (101, 102, 103, 104, 105)
N_RANDOM = 32
PRUNE_CAP_S = 60.0     # per-assignment restrict_template deadline (generous;
                       # measured ~0.5-2 s at n=100-140 — never binds)

SMOKE_CELLS = [("P16", 100, 0.3)]
SMOKE_N_RANDOM = 4

FIELDS = ["topo", "n", "p", "inst_seed", "assignment", "status", "acl_pre",
          "acl_spur", "obj_sim", "qubits", "time", "detail", "err"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "assignment"]


# ──────────────────────────────────────────────────────────────────────────────
# The thin local shim: slots from an arbitrary order / permutation.
# assign_slots() only exposes the pipeline (best seed + 2-swap); it does not
# accept an arbitrary permutation, so we build the slots vector directly and
# feed restrict_template — the module is used as-is, never edited.
# ──────────────────────────────────────────────────────────────────────────────

def _slots_from_order(order, vidx):
    """slots[i] = template chain of vertex i, from a vertex ORDER (order[k]
    is the vertex assigned to chain k) — the seed-order convention of
    _template_core._seed_orders/assign_slots."""
    n = len(vidx)
    if len(order) != n:
        raise ValueError(f"order length {len(order)} != n {n}")
    slots = [0] * n
    for k, v in enumerate(order):
        slots[vidx[v]] = k
    return slots


def _slots_from_perm(perm):
    """slots directly from a permutation of range(n) (random assignments)."""
    return list(perm)


# ──────────────────────────────────────────────────────────────────────────────
# Worker: one instance -> all assignment rows
# ──────────────────────────────────────────────────────────────────────────────

_G = {}   # topo -> TargetState (via get_target_state, busclique-cached)


def _init_worker(topo_names):
    for t in topo_names:
        tgt = build_target(t)
        state = get_target_state(tgt)
        _G[t] = {"target": tgt, "state": state}


def run_instance(task):
    """All requested assignments for one (cell, instance). Deterministic."""
    topo, n, p, inst_seed, assignments = task
    src = make_instance(n, p, inst_seed)
    g = _G[topo]
    state = g["state"]
    rows = []

    def blank(name):
        return {"topo": topo, "n": n, "p": p, "inst_seed": inst_seed,
                "assignment": name, "status": "", "acl_pre": "",
                "acl_spur": "", "obj_sim": "", "qubits": "", "time": "",
                "detail": "", "err": ""}

    if state is None or n > state.kmax:
        for name in assignments:
            row = blank(name)
            row.update(status="INFEASIBLE",
                       err=f"n={n} > K_max or busclique unavailable")
            rows.append(row)
        return rows
    tpl = ordered_template(state, n)
    if tpl is None:
        for name in assignments:
            row = blank(name)
            row.update(status="FAILURE", err="ordered_template returned None")
            rows.append(row)
        return rows
    chains, pos = tpl
    verts = sorted(src.nodes())
    vidx = {v: i for i, v in enumerate(verts)}
    nbr_idx = [[vidx[u] for u in src.neighbors(v) if u != v] for v in verts]
    acl_pre = sum(len(c) for c in chains) / n          # assignment-invariant
    src_idx = nx.relabel_nodes(src, vidx)              # for validity checks

    for name in assignments:
        row = blank(name)
        row["acl_pre"] = round(acl_pre, 4)
        t0 = time.perf_counter()
        try:
            detail = {}
            if name == "identity":
                slots = list(range(n))
            elif name == "cuthill":
                slots = _slots_from_order(list(cuthill_mckee_order(src)), vidx)
            elif name == "spectral":
                slots = _slots_from_order(list(spectral_order(src)), vidx)
            elif name == "shipped":
                slots, info = assign_slots(src, verts, pos, refine=True)
                detail = {"seed_order": info.get("seed_order"),
                          "obj_seed": info.get("obj_seed"),
                          "obj_final": info.get("obj_final"),
                          "complete_skip": info.get("complete_skip")}
            elif name.startswith("rand-"):
                r = int(name.split("-", 1)[1])
                rng = random.Random(r)
                perm = list(range(n))
                rng.shuffle(perm)
                slots = _slots_from_perm(perm)
            else:
                raise ValueError(f"unknown assignment {name!r}")
            row["obj_sim"] = simulate_objective(slots, nbr_idx, pos)
            emb_idx = restrict_template(
                src, verts, slots, chains, state.adj,
                deadline=time.perf_counter() + PRUNE_CAP_S)
            row["time"] = round(time.perf_counter() - t0, 4)
            if not is_valid_embedding(emb_idx, src_idx, g["target"],
                                      adj=state.adj):
                row.update(status="INVALID_OUTPUT",
                           err="pruned embedding failed validation")
                rows.append(row)
                continue
            row["status"] = "SUCCESS"
            row["acl_spur"] = round(
                sum(len(c) for c in emb_idx.values()) / n, 4)
            row["qubits"] = sum(len(c) for c in emb_idx.values())
            if detail:
                row["detail"] = json.dumps(detail, separators=(",", ":"),
                                           default=str)[:200]
        except Exception as e:
            row["time"] = round(time.perf_counter() - t0, 4)
            row.update(status="CRASH", err=clean_err(f"{type(e).__name__}: {e}"))
        rows.append(row)
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Summary — the KG2 kill reads
# ──────────────────────────────────────────────────────────────────────────────

def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    out("=" * 100)
    out("P1 KG2 assignment honesty gate — column: acl_spur (prune-only "
        "template evaluation; see docstring).")
    out("READ1: median best-of-random gain over identity < 2% -> 2-swap DIES "
        "(seeds-only). READ2: seeds capture")
    out(">= 80% of the identity->best-of-random spread -> keep seeds-only. "
        "Deterministic; no MM anywhere.")
    out("=" * 100)

    cells = sorted({(r["topo"], float(r["p"]), int(r["n"])) for r in rows},
                   key=lambda c: (c[0], -c[1], c[2]))
    for topo, p, n in cells:
        cell = [r for r in rows
                if r["topo"] == topo and float(r["p"]) == p and int(r["n"]) == n]
        insts = sorted({r["inst_seed"] for r in cell})
        per_inst = []
        out("")
        out(f"-- {topo}  n={n}  p={p:g}" + ("  [K_n: assignment-invariant "
            "control]" if p >= 1.0 else ""))
        for i in insts:
            vals = {r["assignment"]: float(r["acl_spur"]) for r in cell
                    if r["inst_seed"] == i and r["status"] == "SUCCESS"
                    and r["acl_spur"]}
            rand = [v for k, v in vals.items() if k.startswith("rand-")]
            need = {"identity", "cuthill", "spectral", "shipped"}
            if not (need <= set(vals)) or not rand:
                out(f"   i{i}: incomplete ({sorted(set(vals))[:6]}...)")
                continue
            a_id, a_cu, a_sp, a_sh = (vals["identity"], vals["cuthill"],
                                      vals["spectral"], vals["shipped"])
            best_seed = min(a_id, a_cu, a_sp)
            best_r, med_r, worst_r = min(rand), statistics.median(rand), max(rand)
            gain32 = 100.0 * (a_id - best_r) / a_id if a_id else 0.0
            gainseed = 100.0 * (a_id - best_seed) / a_id if a_id else 0.0
            gainship = 100.0 * (a_id - a_sh) / a_id if a_id else 0.0
            spread = a_id - best_r
            capture = ((a_id - best_seed) / spread if spread > 1e-9 else 1.0)
            per_inst.append((gain32, gainseed, gainship, capture,
                             a_sh - best_r))
            out(f"   i{i}: id {a_id:7.3f}  cu {a_cu:7.3f}  sp {a_sp:7.3f}  "
                f"ship {a_sh:7.3f}  rand[min/med/max] {best_r:7.3f}/"
                f"{med_r:7.3f}/{worst_r:7.3f}  gain32 {gain32:+5.2f}%  "
                f"gainship {gainship:+5.2f}%  capture {capture:5.2f}")
        if not per_inst:
            out("   [no complete instances]")
            continue
        med = [statistics.median(x[j] for x in per_inst) for j in range(5)]
        out(f"   CELL medians: gain32 {med[0]:+5.2f}%  gainseed "
            f"{med[1]:+5.2f}%  gainship {med[2]:+5.2f}%  capture {med[3]:5.2f}"
            f"  shipped-minus-best32 {med[4]:+7.3f}")
        read1 = med[0] < 2.0
        read2 = med[3] >= 0.80
        out(f"   READ1 (oracle gain < 2%): {'FIRES — 2-swap dies (seeds-only)' if read1 else 'no'}"
            f"   READ2 (seeds capture >= 80%): {'FIRES — seeds-only' if read2 else 'no'}")
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="P1 KG2 assignment honesty gate (see docstring)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--smoke", action="store_true",
                    help="local check: P16 (100,0.3), 1 inst, 4 randoms")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--n-random", type=int, default=N_RANDOM)
    return ap.parse_args()


def main():
    args = parse_args()
    if args.smoke:
        cells, inst_seeds, n_random = SMOKE_CELLS, (101,), SMOKE_N_RANDOM
        csv_path = CSV_PATH.replace(".csv", "_smoke.csv")
        summary_path = SUMMARY_PATH.replace(".txt", "_smoke.txt")
    else:
        cells, inst_seeds, n_random = CELLS, INST_SEEDS, args.n_random
        csv_path, summary_path = CSV_PATH, SUMMARY_PATH
    topos = tuple(sorted({c[0] for c in cells}))

    names = (["identity", "cuthill", "spectral", "shipped"]
             + [f"rand-{r:02d}" for r in range(n_random)])

    from minorminer.busclique import busgraph_cache
    for t in topos:
        t0 = time.perf_counter()
        m = len(busgraph_cache(build_target(t)).largest_clique())
        print(f"prelude: {t} max clique = {m}  [{time.perf_counter() - t0:.1f}s]")

    done = load_done_keys(csv_path, KEY_FIELDS) if args.resume else set()
    tasks = []
    for topo, n, p in cells:
        seeds = (inst_seeds[0],) if p >= 1.0 else inst_seeds   # K_n once
        for i in seeds:
            todo = tuple(nm for nm in names
                         if stringify_key(topo, n, p, i, nm) not in done)
            if todo:
                tasks.append((topo, n, p, i, todo))
    n_rows = sum(len(t[4]) for t in tasks)
    print(f"cells={len(cells)}  instance-tasks={len(tasks)}  "
          f"assignment-rows={n_rows}  workers={args.workers}  "
          f"(deterministic, no MM, no algo seeds)")

    t0 = time.time()
    if tasks:
        ctx = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=_init_worker,
                                 initargs=(topos,)) as ex:
            futures = {ex.submit(run_instance, t): t for t in tasks}
            ndone = 0
            for fut in as_completed(futures):
                topo, n, p, i, todo = futures[fut]
                try:
                    rows = fut.result()
                except Exception as exc:
                    rows = []
                    for nm in todo:
                        row = dict.fromkeys(FIELDS, "")
                        row.update(topo=topo, n=n, p=p, inst_seed=i,
                                   assignment=nm, status="CRASH",
                                   err=clean_err(f"runner: {exc!r}"))
                        rows.append(row)
                for row in rows:
                    ndone += 1
                    append_row(csv_path, FIELDS, row)
                print(f"[{ndone}/{n_rows} {time.time() - t0:5.0f}s] "
                      f"{topo} n{n} p{p:g} i{i}: {len(rows)} assignments "
                      f"done", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; csv: {csv_path}\n")

    text = summarize(csv_path)
    print(text)
    with open(summary_path, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {summary_path}")


if __name__ == "__main__":
    main()
