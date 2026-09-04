"""
docs/paper2/data/analyze_fullember3.py
=======================================
Analysis of the third full-Ember sweep (s3.67): attraction vs stock
minorminer vs the busclique template arm (`clique`), multiple batch dirs
(phase x topology cells), unioned and keyed by (topology, graph_id,
algorithm). Per topology: the paired att-vs-mm table in the
analyze_fullember.py format, then a clique/template section on the
triple-success set. Emits fullember3_summary.csv next to this script.

Run:  .venv/bin/python docs/paper2/data/analyze_fullember3.py <batch_dir>...
"""

import csv
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from ember_qc.load_graphs import _manifest_by_id

BANDS = [(0, 30, "n<=30"), (31, 100, "31-100"), (101, 300, "101-300"),
         (301, 1000, "301-1000"), (1001, 10**9, "n>1000")]


def band(n):
    for lo, hi, name in BANDS:
        if lo <= n <= hi:
            return name


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else float("nan")


def load(batch_dirs):
    """runs[(topo, gid)][algo] = (success, acl, wall, n, density)"""
    runs = defaultdict(dict)
    for bd in batch_dirs:
        db_path = Path(bd) / "results.db"
        if not db_path.exists():
            print(f"WARNING: no results.db in {bd} — skipped", file=sys.stderr)
            continue
        db = sqlite3.connect(db_path)
        for gid, topo, algo, succ, acl, wt, n, d in db.execute(
                "SELECT graph_id, topology_name, algorithm, success, "
                "avg_chain_length, wall_time, problem_nodes, problem_density "
                "FROM runs"):
            runs[(topo, gid)][algo] = (succ, acl, wt, n, d)
        db.close()
    return runs


def paired_table(runs, topo, cats):
    G = defaultdict(lambda: dict(n=0, both=0, only_mm=0, only_att=0, neither=0,
                                 dacl=[], win=0, loss=0, tie=0,
                                 t_att=[], t_mm=[]))
    for (t, gid), algs in runs.items():
        if t != topo or "attraction" not in algs or "minorminer" not in algs:
            continue
        sa, aa, ta, n, dens = algs["attraction"]
        sm, am, tm, _, _ = algs["minorminer"]
        g = G[(cats.get(gid, "?"), band(n))]
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

    print(f"\n{'='*100}\nTOPOLOGY {topo} — attraction vs minorminer (paired)\n{'='*100}")
    print(f"{'category':<18}{'size':<10}{'graphs':>7}{'both':>6}{'onlyMM':>7}"
          f"{'onlyATT':>8}{'fail':>6}{'dACL':>8}{'win/loss/tie':>14}"
          f"{'medT att/mm':>13}")
    order = sorted(G, key=lambda k: (k[0], [b[2] for b in BANDS].index(k[1])))
    rows_csv = []
    for key in order:
        g = G[key]
        cat, bd = key
        dm = sum(g["dacl"]) / len(g["dacl"]) if g["dacl"] else float("nan")
        print(f"{cat:<18}{bd:<10}{g['n']:>7}{g['both']:>6}{g['only_mm']:>7}"
              f"{g['only_att']:>8}{g['neither']:>6}{dm:>8.3f}"
              f"{'%d/%d/%d' % (g['win'], g['loss'], g['tie']):>14}"
              f"{med(g['t_att']):>6.1f}/{med(g['t_mm']):<5.1f}")
        rows_csv.append(dict(topology=topo, category=cat, size_band=bd,
                             graphs=g["n"], both=g["both"],
                             only_mm=g["only_mm"], only_att=g["only_att"],
                             neither=g["neither"],
                             mean_dacl=round(dm, 4) if g["dacl"] else "",
                             win=g["win"], loss=g["loss"], tie=g["tie"]))

    allg = dict(n=0, both=0, only_mm=0, only_att=0, neither=0, dacl=[],
                win=0, loss=0, tie=0)
    for g in G.values():
        for k in ("n", "both", "only_mm", "only_att", "neither", "win",
                  "loss", "tie"):
            allg[k] += g[k]
        allg["dacl"] += g["dacl"]
    dm = (sum(allg["dacl"]) / len(allg["dacl"])) if allg["dacl"] else float("nan")
    print(f"\n{topo} OVERALL: {allg['n']} paired graphs | both {allg['both']} | "
          f"only-mm {allg['only_mm']} | only-att {allg['only_att']} | "
          f"neither {allg['neither']}")
    print(f"paired dACL (att-mm) {dm:+.3f} | win/loss/tie "
          f"{allg['win']}/{allg['loss']}/{allg['tie']}")
    return rows_csv


def clique_table(runs, topo, cats):
    """The template arm: coverage (clique succeeds only within busclique's
    template reach) and ACL on the triple-success set."""
    cov = defaultdict(lambda: dict(n=0, clq=0, triple=0,
                                   d_att=[], d_mm=[], best=defaultdict(int)))
    for (t, gid), algs in runs.items():
        if t != topo:
            continue
        sc, ac_ = (algs.get("clique") or (0, None, None, None, None))[:2]
        sa, aa = (algs.get("attraction") or (0, None, None, None, None))[:2]
        sm, am = (algs.get("minorminer") or (0, None, None, None, None))[:2]
        n = next((v[3] for v in algs.values() if v[3] is not None), 0)
        g = cov[(cats.get(gid, "?"), band(n or 0))]
        g["n"] += 1
        if sc:
            g["clq"] += 1
        if sc and sa and sm:
            g["triple"] += 1
            g["d_att"].append(aa - ac_)
            g["d_mm"].append(am - ac_)
            best = min(("attraction", aa), ("minorminer", am), ("clique", ac_),
                       key=lambda kv: kv[1])[0]
            g["best"][best] += 1

    print(f"\n---- {topo}: clique/busclique template arm ----")
    print(f"{'category':<18}{'size':<10}{'graphs':>7}{'clq-ok':>7}{'triple':>7}"
          f"{'d(att-clq)':>11}{'d(mm-clq)':>10}{'best a/m/c':>12}")
    order = sorted(cov, key=lambda k: (k[0], [b[2] for b in BANDS].index(k[1])))
    rows_csv = []
    for key in order:
        g = cov[key]
        if g["clq"] == 0:
            continue  # off-template: clique never succeeds — omit the noise
        cat, bd = key
        da = sum(g["d_att"]) / len(g["d_att"]) if g["d_att"] else float("nan")
        dm_ = sum(g["d_mm"]) / len(g["d_mm"]) if g["d_mm"] else float("nan")
        b = g["best"]
        print(f"{cat:<18}{bd:<10}{g['n']:>7}{g['clq']:>7}{g['triple']:>7}"
              f"{da:>11.3f}{dm_:>10.3f}"
              f"{'%d/%d/%d' % (b['attraction'], b['minorminer'], b['clique']):>12}")
        rows_csv.append(dict(topology=topo, category=cat, size_band=bd,
                             graphs=g["n"], clique_ok=g["clq"],
                             triple=g["triple"],
                             mean_d_att_clq=round(da, 4) if g["d_att"] else "",
                             mean_d_mm_clq=round(dm_, 4) if g["d_mm"] else "",
                             best_att=b["attraction"], best_mm=b["minorminer"],
                             best_clq=b["clique"]))
    tot = sum(g["clq"] for g in cov.values())
    trip = sum(g["triple"] for g in cov.values())
    print(f"{topo} clique coverage: {tot} successes, {trip} triple-success graphs")
    return rows_csv


def main():
    batch_dirs = sys.argv[1:]
    if not batch_dirs:
        print("usage: analyze_fullember3.py <batch_dir>...", file=sys.stderr)
        return 1
    cats = {gid: e.get("category", "?") for gid, e in _manifest_by_id().items()}
    runs = load(batch_dirs)
    topos = sorted({t for (t, _) in runs})
    print(f"Loaded {len(runs)} (topology, graph) cells from "
          f"{len(batch_dirs)} batch dir(s); topologies: {topos}")
    all_rows = []
    for topo in topos:
        all_rows += paired_table(runs, topo, cats)
        all_rows += clique_table(runs, topo, cats)
    out = Path(__file__).parent / "fullember3_summary.csv"
    if all_rows:
        keys = sorted({k for r in all_rows for k in r})
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(all_rows)
        print(f"\nCSV: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
