"""
docs/paper2/data/history_2x2.py
===============================
The history 2x2 inside real minorminer (notes.md §3.13): {alpha=0, alpha=1} x
{stock order, Cuthill-McKee}, every arm a pure run of the forked minorminer
(fallback=False), so the alpha=0/stock-order corner IS stock minorminer 0.2.22.

Grid A (continuity with §3.9/§3.11): ER n in {20,30,40} x d in {0.3,0.5,0.7},
instance seed 12345, into clean Pegasus-6. Grid B (congestion): n in
{30,35,40,45} x d in {0.4,0.5} into clean Pegasus-4. Algorithm seeds 0..9.
Dose response alpha in {0.25, 4} on the four most congested cells, stock order.

Writes raw rows to history_2x2.csv next to this file and prints the paired
summary (paired by (cell, seed) with both alpha arms legal — never compare
unpaired means, §3.11).

Run:  .venv/bin/python docs/paper2/data/history_2x2.py
"""

import csv
import itertools
import os
import time

import networkx as nx
import dwave_networkx as dnx

from ember_qc.benchmark import benchmark_one

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "history_2x2.csv")

INSTANCE_SEED = 12345
SEEDS = range(10)
TIMEOUT = 60.0

GRID_A = [("P6", n, d) for n in (20, 30, 40) for d in (0.3, 0.5, 0.7)]
GRID_B = [("P4", n, d) for n in (30, 35, 40, 45) for d in (0.4, 0.5)]
DOSE_CELLS = [("P4", 40, 0.4), ("P4", 40, 0.5), ("P4", 45, 0.4), ("P4", 45, 0.5)]
DOSE_ALPHAS = (0.25, 4.0)

ARMS = [  # (label, algorithm, order_family, alpha)
    ("stock/a0", "mmfork", "stock", 0.0),
    ("stock/a1", "mmfork", "stock", 1.0),
    ("cuthill/a0", "mmfork-cuthill", "cuthill", 0.0),
    ("cuthill/a1", "mmfork-cuthill", "cuthill", 1.0),
]


def targets():
    return {"P6": dnx.pegasus_graph(6), "P4": dnx.pegasus_graph(4)}


def instance(n, d):
    return nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(n, d, seed=INSTANCE_SEED))


def run_one(src, tgt, algo, alpha, seed):
    kwargs = {"fallback": False}
    if alpha:
        kwargs["history_alpha"] = alpha
    r = benchmark_one(src, tgt, algo, timeout=TIMEOUT, seed=seed, **kwargs)
    ok = bool(r.is_valid and r.embedding)
    return {
        "success": ok,
        "acl": r.avg_chain_length if ok else None,
        "max_chain": r.max_chain_length if ok else None,
        "qubits": r.total_qubits_used if ok else None,
        "time": r.wall_time,
        "embedding": r.embedding if ok else None,
    }


def main():
    tgts = targets()
    rows = []
    results = {}  # (tgt,n,d,family,alpha,seed) -> run dict
    cells = GRID_A + GRID_B
    total = len(cells) * len(SEEDS) * len(ARMS) + len(DOSE_CELLS) * len(SEEDS) * len(DOSE_ALPHAS)
    done = 0
    t0 = time.time()

    for tname, n, d in cells:
        src, tgt = instance(n, d), tgts[tname]
        for seed in SEEDS:
            for label, algo, family, alpha in ARMS:
                r = run_one(src, tgt, algo, alpha, seed)
                results[(tname, n, d, family, alpha, seed)] = r
                rows.append(dict(cell=f"{tname} n{n} d{d}", target=tname, n=n, d=d,
                                 arm=label, order=family, alpha=alpha, seed=seed,
                                 success=r["success"], acl=r["acl"],
                                 max_chain=r["max_chain"], qubits=r["qubits"],
                                 time=round(r["time"], 4)))
                done += 1
        print(f"[{time.time()-t0:6.0f}s] {tname} n{n} d{d}: {done}/{total} runs")

    for tname, n, d in DOSE_CELLS:
        src, tgt = instance(n, d), tgts[tname]
        for seed in SEEDS:
            for alpha in DOSE_ALPHAS:
                r = run_one(src, tgt, "mmfork", alpha, seed)
                results[(tname, n, d, "stock", alpha, seed)] = r
                rows.append(dict(cell=f"{tname} n{n} d{d}", target=tname, n=n, d=d,
                                 arm=f"stock/a{alpha}", order="stock", alpha=alpha,
                                 seed=seed, success=r["success"], acl=r["acl"],
                                 max_chain=r["max_chain"], qubits=r["qubits"],
                                 time=round(r["time"], 4)))
                done += 1
        print(f"[{time.time()-t0:6.0f}s] dose {tname} n{n} d{d}: {done}/{total} runs")

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {CSV_PATH}\n")

    # ── paired analysis ────────────────────────────────────────────────────────
    print("=" * 72)
    print("PAIRED (cell, seed): dACL = ACL(a1) - ACL(a0), same dynamics")
    print("=" * 72)
    pooled = []
    for family in ("stock", "cuthill"):
        for grid, cells_g in (("A/P6", GRID_A), ("B/P4", GRID_B)):
            deltas, act, ties = [], 0, 0
            for (tname, n, d), seed in itertools.product(cells_g, SEEDS):
                r0 = results[(tname, n, d, family, 0.0, seed)]
                r1 = results[(tname, n, d, family, 1.0, seed)]
                if not (r0["success"] and r1["success"]):
                    continue
                dl = r1["acl"] - r0["acl"]
                deltas.append(dl)
                if r1["embedding"] != r0["embedding"]:
                    act += 1
                if dl == 0:
                    ties += 1
            pooled += deltas
            if deltas:
                shorter = sum(1 for x in deltas if x < 0)
                longer = sum(1 for x in deltas if x > 0)
                print(f"{family:8s} grid {grid}: pairs={len(deltas):3d} "
                      f"mean dACL={sum(deltas)/len(deltas):+.3f}  "
                      f"shorter/longer/tie={shorter}/{longer}/{ties}  "
                      f"diverged={act}/{len(deltas)}")
    if pooled:
        sh = sum(1 for x in pooled if x < 0)
        lo = sum(1 for x in pooled if x > 0)
        print(f"{'POOLED':8s}          pairs={len(pooled):3d} "
              f"mean dACL={sum(pooled)/len(pooled):+.3f}  "
              f"shorter/longer/tie={sh}/{lo}/{len(pooled)-sh-lo}")

    print()
    print("=" * 72)
    print("SUCCESS RATES (per arm; unpaired — reported separately from ACL)")
    print("=" * 72)
    for grid, cells_g in (("A/P6", GRID_A), ("B/P4", GRID_B)):
        for family, alpha in (("stock", 0.0), ("stock", 1.0),
                              ("cuthill", 0.0), ("cuthill", 1.0)):
            ok = sum(results[(t, n, d, family, alpha, s)]["success"]
                     for (t, n, d), s in itertools.product(cells_g, SEEDS))
            tot = len(cells_g) * len(SEEDS)
            print(f"grid {grid} {family:8s} a={alpha}: {ok}/{tot}")

    print()
    print("=" * 72)
    print("DOSE RESPONSE (stock order, congested cells; paired vs a=0)")
    print("=" * 72)
    for alpha in (0.25, 1.0, 4.0):
        deltas = []
        for (tname, n, d), seed in itertools.product(DOSE_CELLS, SEEDS):
            r0 = results[(tname, n, d, "stock", 0.0, seed)]
            r1 = results.get((tname, n, d, "stock", alpha, seed))
            if r1 is None or not (r0["success"] and r1["success"]):
                continue
            deltas.append(r1["acl"] - r0["acl"])
        if deltas:
            print(f"alpha={alpha:4}: pairs={len(deltas):2d} "
                  f"mean dACL={sum(deltas)/len(deltas):+.3f}")

    print()
    print("=" * 72)
    print("WALL-CLOCK (mean s per run, successful runs)")
    print("=" * 72)
    for family, alpha in (("stock", 0.0), ("stock", 1.0),
                          ("cuthill", 0.0), ("cuthill", 1.0)):
        ts = [r["time"] for k, r in results.items()
              if k[3] == family and k[4] == alpha and r["success"]]
        if ts:
            print(f"{family:8s} a={alpha}: {sum(ts)/len(ts):.3f}s (n={len(ts)})")


if __name__ == "__main__":
    main()
