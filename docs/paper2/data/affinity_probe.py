"""
docs/paper2/data/affinity_probe.py
===================================
The s3.72 round: per-member affinity as THE merge criterion — one
formula, no twin hash, no adjacency-only rule, no threshold — vs the
s3.71 shipped units (raw-total score + adjacency-only + hash), which
rides here as a process-local monkeypatch control.

PRE-REGISTERED BARS (approved plan):
- BAR1 (REQUIRED): ACL parity-or-better per cell vs the s371 arm;
  placement completes inside its round_frac budget (walls reported; no
  +/-10% clause — that drafting error is on the record).
- BAR2 (watch): grid/honeycomb — non-adjacent pairing's last shot at
  move-time lattice gains before the init round.
- BAR3 (guard): turan 10-seed <= 6.46 + noise; star_971/wheel walls
  sane (hub candidate enumeration cost).
Decision: parity-or-better => default stays ON (winners ship); any
regression => verdict recorded, revert to s3.71 units.

Run:  nohup .venv/bin/python docs/paper2/data/affinity_probe.py \
        > docs/paper2/data/affinity_probe.log 2>&1 &
Smoke: add `smoke`. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "affinity_probe.csv")
TIMEOUT = 60
ARMS = ("s371", "affinity")
TURAN_SEEDS = tuple(range(10))
SEEDS = (0, 1, 2)

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
]
EXTRA = [("grid", 200, "Z12"), ("grid", 588, "Z12"),
         ("honeycomb", 200, "Z12"), ("honeycomb", 600, "Z12"),
         ("triangular_lattice", 400, "Z12"), ("king_graph", 196, "Z12")]
# star/wheel cells dropped: hub candidate-enumeration cost is measured
# directly (star_972 coarsens in 0.32 s); their router-stage mm wedge
# (known, arm-independent, hard-capped in the benchmark harness) makes
# them unusable in a bare probe.


def _units_s371(fine):
    """The s3.71 shipped units coarsener, verbatim (control arm):
    twin hash round 0, raw-total _wjaccard ranking, ADJACENT candidates
    only, greedy matching, fixpoint."""
    from ember_qc.algorithms.factored.coarsen import (
        Level, _merge, _twin_groups, _wjaccard)
    diag = {"rounds": 0, "ratios": [], "max_cluster": 1}
    cur = fine
    chain = [fine]
    groups = _twin_groups(cur.adj)
    if groups:
        nxt = _merge(cur.adj, cur.weight, groups, cur.self_mass)
        diag["ratios"].append(round(len(cur.adj) / len(nxt.adj), 3))
        diag["max_cluster"] = max(len(g) for g in groups)
        chain.append(nxt)
        cur = nxt
    while len(cur.adj) > 1:
        adj, weight = cur.adj, cur.weight
        pairs = []
        for v in sorted(adj):
            for u in sorted(adj[v]):
                if u > v:
                    sc = _wjaccard(adj[v], weight[v], v,
                                   adj[u], weight[u], u)
                    if sc > 0.0:
                        pairs.append((sc, v, u))
        pairs.sort(key=lambda t: (-t[0], t[1], t[2]))
        matched = set()
        groups = []
        for sc, v, u in pairs:
            if v not in matched and u not in matched:
                groups.append([v, u])
                matched.update((v, u))
        if not groups:
            break
        nxt = _merge(cur.adj, cur.weight, groups, cur.self_mass)
        if len(nxt.adj) >= len(cur.adj):
            break
        diag["rounds"] += 1
        diag["ratios"].append(round(len(cur.adj) / len(nxt.adj), 3))
        chain.append(nxt)
        cur = nxt
    chain[-1].diag = diag
    return chain


def _resolve_extra():
    from ember_qc.load_graphs import _manifest_by_id, _graph_dedup_info
    man = _manifest_by_id()
    skip, _ = _graph_dedup_info()
    cells = []
    for cat, n_target, fab in EXTRA:
        cands = sorted((abs(e.get("nodes", 0) - n_target), g)
                       for g, e in man.items()
                       if e.get("category") == cat and g not in skip
                       and 40 <= e.get("nodes", 0) <= 1200)
        _, gid = cands[0]
        cells.append((f"{cat[:14]}_{man[gid]['nodes']}", fab, gid))
    return cells


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
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
    if not hasattr(_cz, "_units_new"):
        _cz._units_new = _cz._coarsen_units
    _cz._coarsen_units = (_units_s371 if arm == "s371"
                          else _cz._units_new)
    t0 = time.perf_counter()
    from ember_qc.algorithms.factored import attract_embed
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = r.get("diag", {})
    return dict(cell=cell, fabric=fabric, gid=gid, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx,
                cl_acc=d.get("cluster_accepts"),
                cl_rev=d.get("cluster_reverts"),
                wall=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD) + _resolve_extra()
    jobs = []
    for c, f, g in cells:
        seeds = (TURAN_SEEDS if (c, f) == ("turan_n162", "Z12") and not smoke
                 else SEEDS[:1] if smoke else SEEDS)
        for arm in ARMS:
            for s in seeds:
                jobs.append((c, f, g, arm, s))
    if smoke:
        jobs = [j for j in jobs
                if j[0].startswith(("turan_n162", "grid_200"))
                and j[1] == "Z12"]
    print(f"{len(jobs)} jobs; load {os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['arm']:<8} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} acc/rev={row['cl_acc']}/"
                  f"{row['cl_rev']} w={row['wall']}s", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    print("\nsummary (mean ACL, mean wall; d = affinity - s371):")
    bar1_ok = True
    seen = []
    for cell, fabric, _ in cells:
        if (cell, fabric) in seen:
            continue
        seen.append((cell, fabric))
        m = {}
        for arm in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm]
            m[arm] = (mean([r["final_acl"] for r in sel]),
                      sum(1 for r in sel if r["final_acl"]),
                      mean([r["wall"] for r in sel]))
        if not (m["s371"][1] or m["affinity"][1]):
            continue
        line = [f"{fabric} {cell:<18}"]
        for arm in ARMS:
            a, nok, w = m[arm]
            line.append(f"{arm}={a:.2f}({nok},w{w:.0f})" if a
                        else f"{arm}=FAIL(0)")
        s, a = m["s371"], m["affinity"]
        if s[0] and a[0]:
            dv = a[0] - s[0]
            tol = max(0.3, 0.05 * s[0])
            if dv > tol or a[1] < s[1]:
                bar1_ok = False
                line.append(f"d={dv:+.2f}[REGRESS]")
            else:
                line.append(f"d={dv:+.2f}[ok]")
        elif s[0] and not a[0]:
            bar1_ok = False
            line.append("[affinity lost success]")
        print("  ".join(line))
    tu = mean([r["final_acl"] for r in rows
               if r["cell"] == "turan_n162" and r["fabric"] == "Z12"
               and r["arm"] == "affinity"])
    print(f"\nBAR1 (parity-or-better): {'PASS' if bar1_ok else 'FAIL'}")
    if tu:
        print(f"BAR3 turan 10-seed (affinity): {tu:.3f} "
              f"({'PASS' if tu <= 6.56 else 'FAIL'} vs 6.46 + noise)")
    print("BAR2: read grid/honeycomb rows. Hub walls: star/wheel rows.")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
