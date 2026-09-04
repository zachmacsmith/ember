"""
docs/paper2/data/basin_persistence.py
=====================================
Does the legalization basin survive the shortening grind? (notes §3.15 gate)

Per (cell, seed): (a) legal-only run (chainlength_patience=0) -> legal ACL and
embedding; (b) warm-started polish of exactly that embedding (initial_chains +
skip_initialization, stock patience) -> polished ACL. If legal ACL predicts
polished ACL across seeds, best-of-N cheap legalizations -> polish-the-winner
is a strict improvement built from stock parameters; if the grind washes the
basin out, the idea dies cheaply here.

Also, for a few seeds, a plain full run as a fidelity check that
legalize+warm-polish reproduces the standard pipeline's quality.

Cells: Pegasus-16, ER avg degree 10, n in {100, 140, 180}, instance seed 12345.
Run:  .venv/bin/python docs/paper2/data/basin_persistence.py
"""

import csv
import os
import random
import time

import networkx as nx
import dwave_networkx as dnx
import minorminer

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "basin_persistence.csv")

INSTANCE_SEED = 12345
SEEDS = range(16)
FULL_SEEDS = range(4)
NS = (100, 140, 180)
T16 = list(dnx.pegasus_graph(16).edges())

acl = lambda e: sum(len(c) for c in e.values()) / len(e)


def main():
    rows = []
    t0 = time.time()
    for n in NS:
        d = 10.0 / (n - 1)
        src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, d, seed=INSTANCE_SEED))
        S = list(src.edges())
        for seed in SEEDS:
            t = time.perf_counter()
            legal = minorminer.find_embedding(S, T16, random_seed=seed, timeout=300,
                                              chainlength_patience=0)
            t_legal = time.perf_counter() - t
            if not legal:
                rows.append(dict(n=n, seed=seed, legal_acl=None, pol_acl=None,
                                 t_legal=round(t_legal, 2), t_pol=None))
                continue
            t = time.perf_counter()
            pol = minorminer.find_embedding(S, T16, random_seed=seed, timeout=300,
                                            initial_chains=legal,
                                            skip_initialization=True)
            t_pol = time.perf_counter() - t
            rows.append(dict(n=n, seed=seed,
                             legal_acl=round(acl(legal), 4),
                             pol_acl=round(acl(pol), 4) if pol else None,
                             t_legal=round(t_legal, 2), t_pol=round(t_pol, 2)))
        for seed in FULL_SEEDS:
            t = time.perf_counter()
            full = minorminer.find_embedding(S, T16, random_seed=seed, timeout=300)
            rows.append(dict(n=n, seed=f"full-{seed}",
                             legal_acl=None,
                             pol_acl=round(acl(full), 4) if full else None,
                             t_legal=None, t_pol=round(time.perf_counter() - t, 2)))
        print(f"[{time.time()-t0:5.0f}s] n={n} done", flush=True)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}\n")

    # ── analysis ──────────────────────────────────────────────────────────────
    from scipy import stats

    print("cell  pairs  pearson  spearman   mean legal->pol")
    pooled_l, pooled_p = [], []
    per_cell = {}
    for n in NS:
        pairs = [(r["legal_acl"], r["pol_acl"]) for r in rows
                 if r["n"] == n and isinstance(r["seed"], int)
                 and r["legal_acl"] and r["pol_acl"]]
        if len(pairs) < 3:
            continue
        L, P = zip(*pairs)
        per_cell[n] = pairs
        pr = stats.pearsonr(L, P)
        sr = stats.spearmanr(L, P)
        print(f"n={n}  {len(pairs):4d}  {pr.statistic:+.3f} (p={pr.pvalue:.3f})  "
              f"{sr.statistic:+.3f} (p={sr.pvalue:.3f})   "
              f"{sum(L)/len(L):.2f} -> {sum(P)/len(P):.2f}")
        mL, mP = sum(L)/len(L), sum(P)/len(P)
        pooled_l += [x - mL for x in L]
        pooled_p += [x - mP for x in P]
    if pooled_l:
        pr = stats.pearsonr(pooled_l, pooled_p)
        sr = stats.spearmanr(pooled_l, pooled_p)
        print(f"pooled (cell-centered): pearson {pr.statistic:+.3f} (p={pr.pvalue:.4f}), "
              f"spearman {sr.statistic:+.3f} (p={sr.pvalue:.4f})")

    # best-of-N preview: E[polished | pick best legal of N] via bootstrap
    rng = random.Random(0)
    print("\nbest-of-N preview (bootstrap, per cell): E[polished ACL]")
    for n, pairs in per_cell.items():
        line = [f"n={n}:"]
        for N in (1, 2, 4, 8):
            est = []
            for _ in range(2000):
                draw = [pairs[rng.randrange(len(pairs))] for _ in range(N)]
                est.append(min(draw)[1])  # polished ACL of the best-legal draw
            line.append(f"N={N}: {sum(est)/len(est):.3f}")
        print("  " + "  ".join(line))

    # fidelity: warm pipeline vs plain full runs
    print("\nfidelity check (plain full runs, same instance):")
    for n in NS:
        fulls = [r["pol_acl"] for r in rows
                 if r["n"] == n and str(r["seed"]).startswith("full") and r["pol_acl"]]
        if fulls:
            print(f"  n={n}: full-run ACLs {fulls}")


if __name__ == "__main__":
    main()
