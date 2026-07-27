"""
docs/paper3/data/p6_probes.py
==============================
P6 fork-anatomy probes (proposals/anatomy.md, three drafted blocks in ONE
interleaved queue/CSV; report-only anatomy — the DELTA vs stock is the
deliverable, no kill bar):

  P6a tree ablation      chain_tree=1 (2014 paper's union-of-paths) and
                         chain_tree=2 (pure SPH, attach filter dropped)
                         vs stock nearest-attach Steiner.
  P6b Boltzmann root     root_boltzmann in {0.5, 2.0, 8.0} vs stock
                         uniform-among-minima (the paper's unshipped proposal).
  P6c finite max_beta    max_beta in {2.0, 16.0, dhat} vs the shipped
                         effectively-infinite lexicographic-overlap pricing.

Arms are all forked_find_embedding(fallback=False) — MM-family, cooperative,
no watchdog (protocol route choice).

Cells (pegasus_16): ER deg-10 ladder n in {60, 100, 140, 180} with
p = 10.0/(n-1) (paper2 house convention, e.g. basin_persistence.py) + dense
cells ER(100, 0.3) and ER(140, 0.3). P6c additionally runs one near-cliff
cell, ER(140, 0.2): the anatomy.md draft asked for "largest n with MM 4/5 at
p=0.2" from E0's cliff table — E0 §4.1 output 4 puts MM's 60 s cliff at
n=140 for every p in {0.2..1.0} (the next p=0.2 rung, n=200, has MM 0/15),
so (140, 0.2) IS that cell; the task sheet's tentative ER(260, 0.2) does not
exist in E0's feasible set and is SUBSTITUTED by (140, 0.2), documented here.
The near-cliff cell runs stock + the beta family only (P6c's registration);
tree/root arms run on the six shared cells.

dhat (the paper's D-hat graph-diameter estimate): exact nx.diameter of the
source's LARGEST connected component (n <= 180 here, so exact BFS-per-node is
trivial); components of size <= 2 give 1; guarded by a size cap (> 2000
nodes -> double-BFS eccentricity lower bound, never triggered at these
sizes); floored at 2.0 so max_beta stays a meaningful base (diameter-2 dense
instances make dhat coincide with the 2.0 rung — that is data, both rows are
kept under their own switch labels). The realized value is recorded per row
in `switch_val`.

Instance seeds 101-105, algo seeds 0-4, 60 s; both `acl` and `acl_spur`
(rule 3); paired summaries per probe family vs stock on the same
(cell, inst_seed, algo_seed).

Run:
  .venv/bin/python docs/paper3/data/p6_probes.py --workers 48       # hyde06
  .venv/bin/python docs/paper3/data/p6_probes.py --smoke --workers 4
Flags: --workers N | --smoke | --resume
--smoke writes to p6_probes_smoke.csv (smoke shares cells with the full grid
at a shorter budget and must never enter the full CSV's resume keys).
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

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _runner_common import (  # noqa: E402
    acl, append_row, build_target, clean_err, embedding_metrics,
    load_done_keys, make_instance, stringify_key, terminal_polish,
)

from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.minorminer_forked import forked_find_embedding, _find_so  # noqa: E402

CSV_PATH = os.path.join(HERE, "p6_probes.csv")
SUMMARY_PATH = os.path.join(HERE, "p6_probes_summary.txt")

TOPO = "P16"
TIMEOUT = 60.0
POLISH_DEADLINE_S = 5.0
INST_SEEDS = (101, 102, 103, 104, 105)
ALGO_SEEDS = (0, 1, 2, 3, 4)

DEG10_NS = (60, 100, 140, 180)
CELLS_MAIN = [(n, 10.0 / (n - 1)) for n in DEG10_NS] + [(100, 0.3), (140, 0.3)]
CELL_CLIFF = (140, 0.2)     # P6c only (substitution documented in docstring)

_DHAT_EXACT_CAP = 2000      # above this, double-BFS estimate (never at n<=180)
DHAT = "dhat"               # sentinel: per-instance diameter estimate

# switch name -> (family, forked_find_embedding kwargs)
SWITCHES = {
    "stock":      ("stock", {}),
    "tree-union": ("tree",  {"chain_tree": 1}),
    "tree-sph":   ("tree",  {"chain_tree": 2}),
    "boltz-0.5":  ("root",  {"root_boltzmann": 0.5}),
    "boltz-2.0":  ("root",  {"root_boltzmann": 2.0}),
    "boltz-8.0":  ("root",  {"root_boltzmann": 8.0}),
    "beta-2.0":   ("beta",  {"max_beta": 2.0}),
    "beta-16.0":  ("beta",  {"max_beta": 16.0}),
    "beta-dhat":  ("beta",  {"max_beta": DHAT}),
}
SWITCH_ORDER = ("stock", "tree-union", "tree-sph", "boltz-0.5", "boltz-2.0",
                "boltz-8.0", "beta-2.0", "beta-16.0", "beta-dhat")
CLIFF_SWITCHES = ("stock", "beta-2.0", "beta-16.0", "beta-dhat")

SMOKE_CELLS = [(60, 10.0 / 59), (100, 0.3)]
SMOKE_SWITCHES = ("stock", "tree-union", "tree-sph", "boltz-2.0", "beta-2.0",
                  "beta-dhat")
SMOKE_TIMEOUT = 8.0

FIELDS = ["topo", "n", "p", "inst_seed", "arm", "family", "algo_seed",
          "switch_val", "status", "success", "acl", "acl_spur", "max_chain",
          "qubits", "wall", "n_edges", "err"]
KEY_FIELDS = ["topo", "n", "p", "inst_seed", "arm", "algo_seed"]


# ──────────────────────────────────────────────────────────────────────────────
# dhat — the D-hat source-diameter estimate (documented in the docstring)
# ──────────────────────────────────────────────────────────────────────────────

def dhat_of(src: nx.Graph) -> float:
    if src.number_of_nodes() == 0:
        return 2.0
    comp = max(nx.connected_components(src), key=len)
    sub = src.subgraph(comp)
    if sub.number_of_nodes() <= 2:
        d = 1
    elif sub.number_of_nodes() > _DHAT_EXACT_CAP:
        # double-BFS eccentricity lower bound (cost cap; never at n<=180)
        v0 = min(sub.nodes())
        d1 = nx.single_source_shortest_path_length(sub, v0)
        far = max(d1, key=lambda v: (d1[v], v))
        d2 = nx.single_source_shortest_path_length(sub, far)
        d = max(d2.values())
    else:
        d = nx.diameter(sub)
    return float(max(2.0, d))


# ──────────────────────────────────────────────────────────────────────────────
# Worker
# ──────────────────────────────────────────────────────────────────────────────

_G = {}
_DHAT_CACHE = {}   # (n, p, inst_seed) -> float


def _init_worker(_unused=None):
    tgt = build_target(TOPO)
    _G[TOPO] = {"target": tgt, "adj": build_adjacency(tgt)}


def run_task(task):
    n, p, inst_seed, arm, algo_seed, timeout = task
    src = make_instance(n, p, inst_seed)
    g = _G[TOPO]
    family, kwargs = SWITCHES[arm]
    kwargs = dict(kwargs)
    sval = ""
    if kwargs.get("max_beta") == DHAT:
        key = (n, p, inst_seed)
        if key not in _DHAT_CACHE:
            _DHAT_CACHE[key] = dhat_of(src)
        kwargs["max_beta"] = _DHAT_CACHE[key]
    for v in kwargs.values():   # record the one engaged switch's value
        if isinstance(v, (int, float)):
            sval = v
            break
    row = {"topo": TOPO, "n": n, "p": p, "inst_seed": inst_seed, "arm": arm,
           "family": family, "algo_seed": algo_seed, "switch_val": sval,
           "status": "", "success": 0, "acl": "", "acl_spur": "",
           "max_chain": "", "qubits": "", "wall": "",
           "n_edges": src.number_of_edges(), "err": ""}
    t0 = time.perf_counter()
    try:
        r = forked_find_embedding(src, g["target"], seed=int(algo_seed),
                                  timeout=float(timeout), fallback=False,
                                  **kwargs)
    except Exception as e:  # belt: forked_find_embedding never raises
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
        row["status"] = ("TIMEOUT" if wall >= timeout - 0.05
                         else r.get("status", "FAILURE"))
        row["err"] = clean_err(r.get("error", "") or
                               ("invalid embedding" if emb else ""))
    return row


# ──────────────────────────────────────────────────────────────────────────────
# Summary — paired vs stock per probe family
# ──────────────────────────────────────────────────────────────────────────────

def summarize(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    lines = []
    out = lines.append
    out("=" * 100)
    out("P6 fork-anatomy probes — column: acl_spur (rule 3); dACL vs stock on "
        "both-succeed (inst_seed, algo_seed) pairs;")
    out("success rates separate/unpaired (rule 4). Report-only anatomy: any "
        "arm beating stock by median < -1% escalates")
    out("to a 15-seed confirm before a paper claim (anatomy.md decision tree).")
    out("=" * 100)

    order = {a: i for i, a in enumerate(SWITCH_ORDER)}
    cells = sorted({(int(r["n"]), float(r["p"])) for r in rows})
    for n, p in cells:
        cell = [r for r in rows if int(r["n"]) == n and float(r["p"]) == p]
        stock_ok = {(r["inst_seed"], r["algo_seed"]): float(r["acl_spur"])
                    for r in cell if r["arm"] == "stock"
                    and r["success"] == "1" and r["acl_spur"]}
        stock_rows = [r for r in cell if r["arm"] == "stock"]
        deg = p * (n - 1)
        stock_accs = sorted(stock_ok.values())
        out("")
        out(f"-- ER({n}, p={p:.4g})  [avg deg {deg:.1f}]   stock: success "
            f"{len(stock_ok)}/{len(stock_rows)}"
            + (f"  acl_spur med {statistics.median(stock_accs):7.3f}"
               if stock_accs else ""))
        for arm in sorted({r["arm"] for r in cell}, key=lambda a: order.get(a, 99)):
            if arm == "stock":
                continue
            arows = [r for r in cell if r["arm"] == arm]
            n_ok = sum(1 for r in arows if r["success"] == "1")
            walls = sorted(float(r["wall"]) for r in arows if r["wall"])
            svals = sorted({r["switch_val"] for r in arows if r["switch_val"]})
            fam = arows[0]["family"]
            base = (f"  [{fam:5s}] {arm:10s} success {n_ok}/{len(arows)}  "
                    f"wall med {statistics.median(walls):6.1f}s"
                    if walls else
                    f"  [{fam:5s}] {arm:10s} success {n_ok}/{len(arows)}")
            if arm == "beta-dhat" and svals:
                base += f"  dhat={svals}"
            pairs = [(float(r["acl_spur"]),
                      stock_ok[(r["inst_seed"], r["algo_seed"])])
                     for r in arows if r["success"] == "1" and r["acl_spur"]
                     and (r["inst_seed"], r["algo_seed"]) in stock_ok]
            if pairs:
                deltas = [a - s for a, s in pairs]
                med = statistics.median(deltas)
                ref = statistics.median(s for _a, s in pairs)
                pct = 100.0 * med / ref if ref else float("nan")
                win = sum(1 for d in deltas if d < 0)
                loss = sum(1 for d in deltas if d > 0)
                base += (f"   pairs {len(pairs):2d}  med d {med:+7.3f} "
                         f"({pct:+6.2f}%)  W/L/T {win}/{loss}/"
                         f"{len(deltas) - win - loss}")
                if pct < -1.0:
                    base += "   [SURPRISE: beats stock — 15-seed confirm]"
            else:
                base += "   [no both-succeed pairs]"
            out(base)
    out("")
    out(f"rows: {len(rows)}   csv: {csv_path}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    ap = argparse.ArgumentParser(
        description="P6 fork-anatomy probes (tree/root/beta; see docstring)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--confirm", action="store_true",
                    help="§4.8b 15-seed surprise confirm: deg-10 n in {100,140,"
                         "180} x {stock,tree-sph,boltz-2.0,boltz-8.0,beta-16.0,"
                         "beta-dhat} x algo seeds 0-14; separate CSV")
    ap.add_argument("--smoke", action="store_true",
                    help="local check: 2 cells, 6 switches, 1 inst, 1 seed, 8 s")
    ap.add_argument("--resume", action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()
    if _find_so() is None:
        sys.exit("fork .so not built (scripts/build_mm_fork.sh) — every P6 "
                 "arm needs it")

    if args.smoke:
        plan = [(n, p, SMOKE_SWITCHES) for n, p in SMOKE_CELLS]
        inst_seeds, algo_seeds, timeout = (101,), (0,), SMOKE_TIMEOUT
        csv_path = CSV_PATH.replace(".csv", "_smoke.csv")
        summary_path = SUMMARY_PATH.replace(".txt", "_smoke.txt")
    elif args.confirm:
        confirm_switches = ("stock", "tree-sph", "boltz-2.0", "boltz-8.0",
                            "beta-16.0", "beta-dhat")
        plan = [(n, 10.0 / (n - 1), confirm_switches) for n in (100, 140, 180)]
        inst_seeds, algo_seeds, timeout = INST_SEEDS, tuple(range(15)), TIMEOUT
        csv_path = CSV_PATH.replace(".csv", "_confirm.csv")
        summary_path = SUMMARY_PATH.replace(".txt", "_confirm.txt")
    else:
        plan = [(n, p, SWITCH_ORDER) for n, p in CELLS_MAIN]
        plan.append((CELL_CLIFF[0], CELL_CLIFF[1], CLIFF_SWITCHES))
        inst_seeds, algo_seeds, timeout = INST_SEEDS, ALGO_SEEDS, TIMEOUT
        csv_path, summary_path = CSV_PATH, SUMMARY_PATH

    tasks = []
    for n, p, switches in plan:
        for i in inst_seeds:
            for s in algo_seeds:
                for arm in switches:    # arms innermost: one interleaved queue
                    tasks.append((n, p, i, arm, s, timeout))
    total_planned = len(tasks)
    if args.resume:
        done = load_done_keys(csv_path, KEY_FIELDS)
        tasks = [t for t in tasks
                 if stringify_key(TOPO, t[0], t[1], t[2], t[3], t[4])
                 not in done]
        print(f"resume: {total_planned - len(tasks)} of {total_planned} "
              f"already in {os.path.basename(csv_path)}")
    print(f"cells={len(plan)}  tasks={len(tasks)}  timeout={timeout:g}s  "
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
                    n, p, inst_seed, arm, algo_seed, _t = futures[fut]
                    row = dict.fromkeys(FIELDS, "")
                    row.update(topo=TOPO, n=n, p=p, inst_seed=inst_seed,
                               arm=arm, family=SWITCHES[arm][0],
                               algo_seed=algo_seed, status="CRASH", success=0,
                               err=clean_err(f"runner: {exc!r}"))
                append_row(csv_path, FIELDS, row)
                a = f"acl={row['acl']}/{row['acl_spur']}" if row["success"] else ""
                print(f"[{i}/{len(tasks)} {time.time() - t0:6.0f}s] "
                      f"n{row['n']} p{float(row['p']):.4g} i{row['inst_seed']} "
                      f"{row['arm']} s{row['algo_seed']}: {row['status']} {a} "
                      f"{row['wall']}s", flush=True)
    print(f"\nall tasks done in {time.time() - t0:.0f}s; csv: {csv_path}\n")

    text = summarize(csv_path)
    print(text)
    with open(summary_path, "w") as fh:
        fh.write(text + "\n")
    print(f"\nsummary -> {summary_path}")


if __name__ == "__main__":
    main()
