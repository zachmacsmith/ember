"""
docs/paper2/data/adjoint_probe.py
==================================
The s3.69 adjoint round: aggregation substrate (vcycle_agg) + measure-
transport junction (vcycle_transport) vs the shipped disc unpack.
Design: merge and unpack are adjoint — the merge score certifies which
sibling orders are free; decompression = coarse ORDERS expanded by wire
MASS (contiguous blocks, attachment rank within, fabric-linear scale),
walked LEVEL-BY-LEVEL down the fixpoint chain. Geometry constants
(COARSE_SPAN / 0.45 / 0.05 / V0 anchor) are not consulted on this path.

PRE-REGISTERED BARS:
- BAR1 (board parity, REQUIRED): consolidation-3 Z12 board + P16 spot —
  no cell regresses beyond max(0.3, 5%) vs the stock arm (paired seeds).
- BAR2 (the model test, REQUIRED): triangular cells (which coarsen AND
  are lost at library scale, s3.67 sweep) move toward mm under adjoint;
  grid/honeycomb move little (weak coarsening via boundary erosion only
  — near-null prediction; wholesale movement there means the model is
  mis-specified and we learn that).
- BAR3 (dividend, NOT required): sbm/planted/ws movement; Galerkin
  E_interp (junction handoff energy) shrinks vs stock on coarsenable
  cells (dev-scale evidence: triangular/Z6 155 -> 12).
Decision rule: BAR1+BAR2 pass => defaults-flip proposal (vcycle_agg +
vcycle_transport on) as its own commit; BAR2 fail => transport parked
with verdict, aggregation keeps s3.68 validation.

P16 cells measure the stride gate only (vcycle inert off-Zephyr —
placement.py:344): both arms byte-identical there; included as the
gate-integrity control.

Run:  nohup .venv/bin/python docs/paper2/data/adjoint_probe.py \
        > docs/paper2/data/adjoint_probe.log 2>&1 &
Smoke: add `smoke` argv. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "adjoint_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
ARMS = ("stock", "agg", "adjoint")

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
]
# (category, n_target, count) — gids resolved from the manifest at run
# time, deterministically (nearest-n unique picks, recorded in the CSV).
LATTICE = [("triangular_lattice", 150, 1), ("triangular_lattice", 400, 1),
           ("triangular_lattice", 800, 1),
           ("grid", 200, 1), ("grid", 600, 1),
           ("honeycomb", 200, 1), ("honeycomb", 600, 1),
           ("generalized_petersen", 200, 1), ("generalized_petersen", 500, 1),
           ("king_graph", 200, 1), ("king_graph", 500, 1)]
MIDDLES = [("sbm", 300, 1), ("sbm", 700, 1),
           ("planted_solution", 300, 1), ("planted_solution", 700, 1),
           ("watts_strogatz", 400, 1), ("watts_strogatz", 800, 1)]


def _resolve_extra_cells():
    from ember_qc.load_graphs import _manifest_by_id, _graph_dedup_info
    man = _manifest_by_id()
    skip, _ = _graph_dedup_info()
    cells = []
    for cat, n_target, count in LATTICE + MIDDLES:
        cands = sorted((abs(e.get("nodes", 0) - n_target), g)
                       for g, e in man.items()
                       if e.get("category") == cat and g not in skip
                       and 40 <= e.get("nodes", 0) <= 1200)
        for _, gid in cands[:count]:
            cells.append((f"{cat[:14]}_{man[gid]['nodes']}", "Z12", gid))
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
    if arm == "agg":
        kw = {"vcycle_agg": True}
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
                E_interp=d.get("E_interp"), E_contract=d.get("E_contract"),
                stair_E=r.get("stair_E"),
                time=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD) + _resolve_extra_cells()
    if smoke:
        cells = [c for c in cells if c[0] in ("K100", "turan_n162")
                 and c[1] == "Z12"] + cells[10:11]
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
                  f"mx={row['max_chain']} Ei={row['E_interp']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    print("\nsummary (mean ACL over legal seeds; dACL vs stock; "
          "Ei = mean E_interp):")
    bar1_ok = True
    seen = []
    for cell, fabric, _ in cells:
        if (cell, fabric) in seen:
            continue
        seen.append((cell, fabric))
        line = [f"{fabric} {cell:<18}"]
        m = {}
        for arm in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["arm"] == arm]
            a = mean([r["final_acl"] for r in sel])
            m[arm] = (a, sum(1 for r in sel if r["final_acl"]),
                      mean([r["E_interp"] for r in sel]))
            line.append(f"{arm}={a:.2f}({m[arm][1]})" if a
                        else f"{arm}=FAIL(0)")
        s, j = m["stock"], m["adjoint"]
        if s[0] and j[0]:
            delta = j[0] - s[0]
            tol = max(0.3, 0.05 * s[0])
            board = (cell, fabric) in [(c, f) for c, f, _ in BOARD]
            flag = "ok" if delta <= tol else (
                "REGRESS" if board else "regress")
            if board and (delta > tol or j[1] < s[1]):
                bar1_ok = False
            line.append(f"d={delta:+.2f}[{flag}]")
            if s[2] and j[2]:
                line.append(f"Ei {s[2]:.0f}->{j[2]:.0f}")
        elif s[0] and not j[0]:
            if (cell, fabric) in [(c, f) for c, f, _ in BOARD]:
                bar1_ok = False
            line.append("[adjoint lost success]")
        print("  ".join(line))
    print(f"\nBAR1 (board parity): {'PASS' if bar1_ok else 'FAIL'}")
    print("BAR2/BAR3: score from the lattice/middle rows above "
          "(triangular vs grid/honeycomb; Ei shifts).")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
