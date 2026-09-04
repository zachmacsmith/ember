"""
docs/paper2/data/aggregation_probe.py
======================================
The s3.68 aggregation round: replace {ONE greedy pairwise Jaccard matching
round + the no-fixpoint depth cap} with LEADER AGGREGATION ITERATED TO
FIXPOINT — one general clustering rule instead of three mechanisms. The
exact-twin hash stays at round 0 (fine level, unchanged semantics); its
absorption into the score is the separate extended-body dE/dd derivation
(future round, out of scope here). The unpack/spread/spectral code is
byte-identical — this probe monkeypatches ONLY `coarsen.coarsen`,
process-locally, because the s3.67 full sweep is running off this tree
and no algorithm file may be edited until it completes.

Design analysis on record (2026-08-05, conversation -> this docstring):
- The weighted score already refuses the turan-quotient collapse
  (S = 162/13122 ~ 0.012 << tau) that the hand-coded "no twin fixpoint"
  rule exists to prevent; the UNWEIGHTED twin hash is what over-collapses.
- Pairwise matching has a straggler pathology: an odd twin family merges
  {2,2,1} -> {4,1} and the leftover scores S ~ deg/(5deg+5) ~ 0.2 < tau —
  permanently unmergeable with its own class, an artifact of the pairing
  schedule, not of the score.
- Matching (vs clustering) is a partitioning-tradition inheritance whose
  justifying constraint (balanced coarse nodes) our AMG-shaped problem
  does not have; aggregation stars are radius-1 in the similarity graph,
  so twin classes collapse whole and chains cannot single-link.

PRE-REGISTERED BARS (before any run):
- BAR1 (parity, REQUIRED): no board cell regresses — per cell, agg's
  3-seed mean ACL within max(0.3, 5%) of att's, no success-count loss.
- BAR2 (emergent protection, REQUIRED): turan cells reach fixpoint with
  the block quotient intact (final coarse n >= 2) — the behavior the
  deleted no-fixpoint decree enforced must EMERGE from the weighted score.
- BAR3 (dividend, NOT required): any cell improving beyond seed noise,
  or deeper hierarchies on ws/cycle at parity.
Decision rule: BAR1+BAR2 pass => propose the default flip as a real
switch-guarded coarsen.py change AFTER the sweep completes; any BAR1
fail => verdict recorded, arm parked.

CONTENTION CAVEAT: runs niced alongside the s3.67 sweep (100 workers);
att-vs-agg pairing shares the contention (internally valid); comparisons
to historical BASE_REF absolute numbers carry this caveat.

Run:  nohup .venv/bin/python docs/paper2/data/aggregation_probe.py \
        > docs/paper2/data/aggregation_probe.log 2>&1 &
Smoke: add `smoke` argv (2 cells x 1 seed).
Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "aggregation_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
TAU = 0.34  # unchanged from stock

CELLS = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
    ("cycle_mid", "P16", "CYCLE"),  # structural-depth cell (ACL-inert)
]
BASE_REF = {"K100": 8.12, "K140": 10.91, "ER100_d10": 4.76,
            "turan_n162": 9.06, "spin_glass_n163": 12.88,
            "regular_n316": 2.86, "ws_n486": 3.12}

# Diagnostics of the LAST coarsen_v2 call in this process (probe-local).
V2_DIAG: dict = {}


def coarsen_v2(src_adj, *, threshold: float = TAU, min_nodes: int = 8):
    """Leader aggregation iterated to fixpoint. Round 0 = stock twin
    collapse (whole exact-twin groups, unchanged). Rounds 1..k: stars
    around invariant-ordered seeds under the UNCHANGED weighted score;
    iterate until a round produces no merge. Returns [fine, coarsest]
    with parent_of composed across rounds (the 2-level interface
    multilevel_init expects). Residual id-dependence: the last-resort
    tie-break in seed order and `_merge`'s min-id representative."""
    from ember_qc.algorithms.factored.coarsen import (
        Level, _merge, _twin_groups, _wjaccard)

    adj0 = {v: {u: 1.0 for u in nbrs} for v, nbrs in src_adj.items()}
    for v in src_adj:
        adj0.setdefault(v, {})
    fine = Level(adj0, {v: 1.0 for v in adj0})
    V2_DIAG.clear()
    V2_DIAG.update(rounds=0, ratios=[], n_fine=len(adj0), n_coarse=len(adj0),
                   max_cluster=1)
    if len(adj0) <= min_nodes:
        return [fine]

    # Round 0: stock exact-twin collapse (whole groups at once).
    cur = fine
    total_map = None  # fine node -> current-level node
    groups = _twin_groups(cur.adj)
    if groups:
        nxt = _merge(cur.adj, cur.weight, groups)
        total_map = dict(nxt.parent_of)
        V2_DIAG["ratios"].append(round(len(cur.adj) / len(nxt.adj), 3))
        cur = nxt

    # Rounds 1..k: leader aggregation to fixpoint.
    while True:
        adj, weight = cur.adj, cur.weight
        # Invariant seed order: heavy first, then high-degree; id last.
        order = sorted(adj, key=lambda v: (-weight[v], -len(adj[v]), v))
        assigned: dict = {}   # node -> seed
        seeds: list = []
        for v in order:
            if v in assigned:
                continue
            # candidates: distance <= 2 seeds (stock candidate radius)
            cand: set = set()
            for u in adj[v]:
                if u in assigned and assigned[u] == u:
                    cand.add(u)
                for w in adj.get(u, ()):
                    if w != v and w in assigned and assigned[w] == w:
                        cand.add(w)
            best, best_sc = None, threshold
            for s in sorted(cand):
                sc = _wjaccard(adj[v], weight[v], v, adj[s], weight[s], s)
                if sc > best_sc or (sc == best_sc and best is not None
                                    and s < best):
                    best, best_sc = s, sc
            if best is None:
                assigned[v] = v  # becomes a seed
                seeds.append(v)
            else:
                assigned[v] = best
        clusters: dict = {}
        for v, s in assigned.items():
            clusters.setdefault(s, []).append(v)
        groups = [g for g in clusters.values() if len(g) > 1]
        if not groups:
            break
        nxt = _merge(cur.adj, cur.weight, groups)
        if len(nxt.adj) >= len(cur.adj):
            break
        V2_DIAG["rounds"] += 1
        V2_DIAG["ratios"].append(round(len(cur.adj) / len(nxt.adj), 3))
        V2_DIAG["max_cluster"] = max(V2_DIAG["max_cluster"],
                                     max(len(g) for g in groups))
        if total_map is None:
            total_map = dict(nxt.parent_of)
        else:
            total_map = {f: nxt.parent_of[c] for f, c in total_map.items()}
        cur = nxt

    V2_DIAG["n_coarse"] = len(cur.adj)
    if total_map is None:
        return [fine]
    cur.parent_of = total_map
    return [fine, cur]


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    if gid == "CYCLE":
        from ember_qc.load_graphs import _manifest_by_id, load_graph
        man = _manifest_by_id()
        cands = sorted((abs(e.get("nodes", 0) - 500), g)
                       for g, e in man.items()
                       if e.get("category") == "cycle")
        return nx.convert_node_labels_to_integers(load_graph(cands[0][1]))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, fabric, gid, arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import coarsen as _cz
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    # Explicit per-job patch state (pool workers are reused across jobs).
    if not hasattr(_cz, "_stock_coarsen"):
        _cz._stock_coarsen = _cz.coarsen
    _cz.coarsen = coarsen_v2 if arm == "agg" else _cz._stock_coarsen
    t0 = time.perf_counter()
    from ember_qc.algorithms.factored import attract_embed
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = dict(V2_DIAG) if arm == "agg" else {}
    return dict(cell=cell, fabric=fabric, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx,
                rounds=d.get("rounds"), n_coarse=d.get("n_coarse"),
                ratios="|".join(str(x) for x in d.get("ratios", [])) or None,
                max_cluster=d.get("max_cluster"),
                time=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = CELLS[:1] + CELLS[3:4] if smoke else CELLS  # K100/Z12 + turan/Z12
    seeds = SEEDS[:1] if smoke else SEEDS
    print("load at start:", os.getloadavg(), "(s3.67 sweep co-resident; "
          "paired arms share contention)", flush=True)
    jobs = [(c, f, g, arm, s) for c, f, g in cells
            for arm in ("att", "agg") for s in seeds]
    rows = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']} {row['arm']} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} rounds={row['rounds']} "
                  f"nc={row['n_coarse']} clus<={row['max_cluster']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print("\nsummary (mean ACL over legal seeds (n)); BAR1 = agg within "
          "max(0.3, 5%) of att, no success loss:")
    bar1_ok = True
    for cell, fabric, _ in cells:
        line = [f"{fabric} {cell:16s}"]
        means = {}
        for arm in ("att", "agg"):
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm
                   and r["final_acl"]]
            means[arm] = (sum(r["final_acl"] for r in sel) / len(sel)
                          if sel else None)
            n_ok = len(sel)
            line.append(f"{arm}={means[arm]:.2f}({n_ok})"
                        if means[arm] else f"{arm}=FAIL(0)")
        ref = BASE_REF.get(cell)
        if ref:
            line.append(f"ref={ref}")
        att_n = sum(1 for r in rows if r["cell"] == cell
                    and r["fabric"] == fabric and r["arm"] == "att"
                    and r["final_acl"])
        agg_n = sum(1 for r in rows if r["cell"] == cell
                    and r["fabric"] == fabric and r["arm"] == "agg"
                    and r["final_acl"])
        if means["att"] and means["agg"]:
            delta = means["agg"] - means["att"]
            tol = max(0.3, 0.05 * means["att"])
            verdict = "ok" if delta <= tol else "REGRESS"
            if cell != "cycle_mid" and (delta > tol or agg_n < att_n):
                bar1_ok = False
            line.append(f"d={delta:+.2f} [{verdict}]")
        elif att_n and not agg_n and cell != "cycle_mid":
            bar1_ok = False
            line.append("[REGRESS: agg lost success]")
        print("  ".join(line))
    turan_nc = [r["n_coarse"] for r in rows
                if r["cell"] == "turan_n162" and r["arm"] == "agg"
                and r["n_coarse"] is not None]
    bar2_ok = bool(turan_nc) and all(nc >= 2 for nc in turan_nc)
    print(f"\nBAR1 (parity): {'PASS' if bar1_ok else 'FAIL'}")
    print(f"BAR2 (turan quotient emerges intact, n_coarse {turan_nc}): "
          f"{'PASS' if bar2_ok else 'FAIL' if turan_nc else 'N/A (smoke)'}")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
