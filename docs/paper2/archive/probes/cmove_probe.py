"""
docs/paper2/data/cmove_probe.py
================================
The s3.70 cluster-moves round: coarsen the MOVES, not the state.
Clusters (aggregation-fixpoint groups) are member sets gathered as one
E-gated composite inside arrange — real bars through the real gates,
nothing summarized, no sizes guessed. The s3.69 adjoint arm rides along
as the reference showing gated vs unconditional transport.

PRE-REGISTERED BARS (from the approved plan, before any run):
- BAR1 (REQUIRED): board parity INCLUDING the s3.69 failure cells
  (regular_n316, ws_n486; sbm_288/ws_404 extra) — cmove within
  max(0.3, 5%) of stock. This is the design's whole point.
- BAR2 (REQUIRED): turan/Z12 <= 6.5 under cmove (unconditional transport
  reached the 6.00 optimum; the gated move must recover most of it).
- BAR3 (dividend): lattice block moves toward the adjoint arm.
- BAR4 (watch, NOT a bar): P16 cells — first mechanism riding ordinary
  gates on every fabric; dense-Pegasus movement is upside to observe.
Decision rule: BAR1+BAR2 pass => candidate default; any BAR1 fail =>
parked with verdict.
Pre-registered diagnostic: if cmove turan lands above 6.0x, suspect the
fixed y-multiset at proposal time (the in-composite repack should mostly
cure it); attribute via cluster_accepts/reverts + E trajectory.

Run:  nohup .venv/bin/python docs/paper2/data/cmove_probe.py \
        > docs/paper2/data/cmove_probe.log 2>&1 &
Smoke: add `smoke` argv. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cmove_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
ARMS = ("stock", "cmove", "adjoint")

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
]
EXTRA = [("triangular_lattice", 150, "Z12"), ("triangular_lattice", 400, "Z12"),
         ("grid", 200, "Z12"), ("honeycomb", 200, "Z12"),
         ("king_graph", 196, "Z12"),
         ("sbm", 288, "Z12"), ("watts_strogatz", 404, "Z12"),
         ("sbm", 288, "P16"), ("triangular_lattice", 400, "P16")]


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
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    kw = {}
    if arm == "cmove":
        kw = {"cluster_moves": True}
    elif arm == "adjoint":
        kw = {"vcycle_agg": True, "vcycle_transport": True}
    t0 = time.perf_counter()
    from ember_qc.algorithms.factored import attract_embed
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None) if emb else None
    d = r.get("diag", {})
    return dict(cell=cell, fabric=fabric, gid=gid, arm=arm, seed=seed,
                final_acl=acl, max_chain=mx,
                cl_acc=d.get("cluster_accepts"),
                cl_rev=d.get("cluster_reverts"),
                stair_E=r.get("stair_E"),
                time=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD) + _resolve_extra()
    if smoke:
        cells = [c for c in cells
                 if c[0] in ("turan_n162", "regular_n316") and c[1] == "Z12"]
    seeds = SEEDS[:1] if smoke else SEEDS
    print(f"{len(cells)} cells x {len(ARMS)} arms x {len(seeds)} seeds; "
          f"load {os.getloadavg()}", flush=True)
    jobs = [(c, f, g, arm, s) for c, f, g in cells
            for arm in ARMS for s in seeds]
    rows = []
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['arm']:<8} "
                  f"seed {row['seed']}: {row['final_acl']} "
                  f"mx={row['max_chain']} acc/rev={row['cl_acc']}/"
                  f"{row['cl_rev']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    fail_cells = {("regular_n316", "Z12"), ("ws_n486", "Z12")}
    print("\nsummary (mean ACL; d = cmove - stock; a = adjoint - stock):")
    bar1_ok, bar2_ok = True, None
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
                      sum(1 for r in sel if r["final_acl"]))
        line = [f"{fabric} {cell:<18}"]
        for arm in ARMS:
            line.append(f"{arm}={m[arm][0]:.2f}({m[arm][1]})"
                        if m[arm][0] else f"{arm}=FAIL(0)")
        s, c, a = m["stock"], m["cmove"], m["adjoint"]
        if s[0] and c[0]:
            d = c[0] - s[0]
            tol = max(0.3, 0.05 * s[0])
            board = (cell, fabric) in [(x, f) for x, f, _ in BOARD]
            tag = "ok" if d <= tol else ("REGRESS" if board else "regress")
            if board and (d > tol or c[1] < s[1]):
                bar1_ok = False
            line.append(f"d={d:+.2f}[{tag}]")
        if a[0] and s[0]:
            line.append(f"a={a[0]-s[0]:+.2f}")
        if cell == "turan_n162" and fabric == "Z12" and c[0]:
            bar2_ok = c[0] <= 6.5
        print("  ".join(line))
    print(f"\nBAR1 (board parity incl. s3.69 failure cells): "
          f"{'PASS' if bar1_ok else 'FAIL'}")
    print(f"BAR2 (turan/Z12 cmove <= 6.5): "
          f"{'PASS' if bar2_ok else 'FAIL' if bar2_ok is not None else 'N/A'}")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
