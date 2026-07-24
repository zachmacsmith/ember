"""
docs/paper2/data/analyze_fullember.py
======================================
Paired analysis of the first full-Ember sweep (notes §3.22-3.23):
attraction (hybrid v3) vs stock minorminer, batch_2026-07-17_20-34-03,
Pegasus-16, 60 s, shared seed, one trial. Pairs by graph_id; scores the
pre-registered predictions in attraction.md.

Run:  .venv/bin/python docs/paper2/data/analyze_fullember.py [batch_dir]
"""

import sqlite3
import sys
from collections import defaultdict

from ember_qc.load_graphs import _manifest_by_id

BATCH = sys.argv[1] if len(sys.argv) > 1 else \
    "results/batch_2026-07-17_20-34-03"

BANDS = [(0, 30, "n<=30"), (31, 100, "31-100"), (101, 300, "101-300"),
         (301, 1000, "301-1000"), (1001, 10**9, "n>1000")]


def band(n):
    for lo, hi, name in BANDS:
        if lo <= n <= hi:
            return name


def main():
    cats = {gid: e.get("category", "?") for gid, e in _manifest_by_id().items()}
    db = sqlite3.connect(f"{BATCH}/results.db")
    rows = db.execute(
        "SELECT graph_id, algorithm, success, avg_chain_length, wall_time, "
        "problem_nodes, problem_density FROM runs").fetchall()

    per_graph = defaultdict(dict)
    for gid, algo, succ, acl, wt, n, d in rows:
        per_graph[gid][algo] = (succ, acl, wt, n, d)

    # group[(category, band)] = stats
    G = defaultdict(lambda: dict(n=0, both=0, only_mm=0, only_att=0, neither=0,
                                 dacl=[], win=0, loss=0, tie=0,
                                 t_att=[], t_mm=[]))
    for gid, algs in per_graph.items():
        if "attraction" not in algs or "minorminer" not in algs:
            continue
        sa, aa, ta, n, dens = algs["attraction"]
        sm, am, tm, _, _ = algs["minorminer"]
        key = (cats.get(gid, "?"), band(n))
        g = G[key]
        g["n"] += 1
        g["t_att"].append(ta)
        g["t_mm"].append(tm)
        if sa and sm:
            g["both"] += 1
            delta = aa - am
            g["dacl"].append(delta)
            if delta < -1e-6:
                g["win"] += 1
            elif delta > 1e-6:
                g["loss"] += 1
            else:
                g["tie"] += 1
        elif sm:
            g["only_mm"] += 1
        elif sa:
            g["only_att"] += 1
        else:
            g["neither"] += 1

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else float("nan")

    print(f"{'category':<18}{'size':<10}{'graphs':>7}{'both':>6}{'onlyMM':>7}"
          f"{'onlyATT':>8}{'fail':>6}{'dACL':>8}{'win/loss/tie':>14}"
          f"{'medT att/mm':>13}")
    order = sorted(G, key=lambda k: (k[0], [b[2] for b in BANDS].index(k[1])))
    for key in order:
        g = G[key]
        cat, bd = key
        dm = sum(g["dacl"]) / len(g["dacl"]) if g["dacl"] else float("nan")
        print(f"{cat:<18}{bd:<10}{g['n']:>7}{g['both']:>6}{g['only_mm']:>7}"
              f"{g['only_att']:>8}{g['neither']:>6}{dm:>8.3f}"
              f"{'%d/%d/%d' % (g['win'], g['loss'], g['tie']):>14}"
              f"{med(g['t_att']):>6.1f}/{med(g['t_mm']):<5.1f}")

    # overall
    allg = dict(n=0, both=0, only_mm=0, only_att=0, neither=0, dacl=[],
                win=0, loss=0, tie=0)
    for g in G.values():
        for k in ("n", "both", "only_mm", "only_att", "neither", "win",
                  "loss", "tie"):
            allg[k] += g[k]
        allg["dacl"] += g["dacl"]
    dm = sum(allg["dacl"]) / len(allg["dacl"])
    print(f"\nOVERALL: {allg['n']} paired graphs | both {allg['both']} | "
          f"only-mm {allg['only_mm']} | only-att {allg['only_att']} | "
          f"neither {allg['neither']}")
    print(f"paired dACL (att-mm) {dm:+.3f} | win/loss/tie "
          f"{allg['win']}/{allg['loss']}/{allg['tie']}")


if __name__ == "__main__":
    main()
