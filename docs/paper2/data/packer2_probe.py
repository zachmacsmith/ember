"""
docs/paper2/data/packer2_probe.py
==================================
The claim-plan round (notes s3.61). Diagnosis (recorded before build):
turan's s3.59 d15 was NEITHER boundary parity NOR lane abutment — it was
one arm (v160) stranded by the insertion composite's y-permutation
creating a 9-on-8 row the DP never certified (counts are permutation-
invariant, interval depths are not; lam only PRICED the violation).
The un-avoided boundary arm measured d328 (all boundary class) — the
avoid rule's justification, now quantified. Built: (1) hard structural
veto — composite permutations may not increase claim_overload; (2)
boundary lines at HALF pool (4) instead of zeroed; (3) parity-preferring
lane choice in the coloring. avoid_boundary deleted.

Single-seed sanity on record: K100 7.92 s1 d0 (BELOW the 8.00 template);
turan 7.00 routed (best in program history) with the gate broken (d152 —
boundary arms' perpendicular partners uncovered; the router repaired
them profitably).

Arms (3 seeds x 60 s, paired): att = zero-kwarg default; att_noB = same
with boundary pools zeroed via monkeypatch (the attribution arm: is the
turan gate recoverable at the old capacity?); mm = stock minorminer.

PRE-REGISTERED BARS (from the approved plan):
- MECHANISM: K100/K140 gates keep firing s1 d0 e0; turan gate-valid at
  full depth WITH boundary lanes in use.
- MINIMUM: turan <= 7.5 gate-valid; records hold: K100 <= 8.3,
  K140 <= 11.2, spin_glass <= 12.7, ER <= 4.95; off-template >= s3.59.
- STRETCH: turan <= 7.0.
- Scoring rule: shared box; mm controls must replicate (10.28 /
  18.00-18.27 / 4.97 / 12.01 / ~18 / 3.36 / 3.08 / 3.78 / 7.31).
- Failure rule: turan gate not firing -> report + discuss (the sanity
  run predicts exactly this split: number passes, letter fails).

Run:  nohup .venv/bin/python docs/paper2/data/packer2_probe.py \
        > docs/paper2/data/packer2_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "packer2_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = [
    ("K100", None), ("K140", None), ("ER100_d10", None),
    ("turan_n162", 2647), ("spin_glass_n163", 37309),
    ("regular_n316", 13096), ("ws_n486", 17188),
    ("wsc_c8xK32", 33640), ("wsc_c3xK64", 33574),
]
TEMPLATE = {"K100": "8.00", "K140": "11.00", "turan_n162": "6.00",
            "spin_glass_n163": "11.64"}
S359 = {"K100": 8.12, "K140": 10.91, "ER100_d10": 4.76,
        "turan_n162": 9.06, "spin_glass_n163": 12.88,
        "regular_n316": 2.86, "ws_n486": 3.12,
        "wsc_c8xK32": 3.89, "wsc_c3xK64": 6.37}


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
    cell, gid, arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    skips = deficit = ext = None
    if arm == "mm":
        import minorminer
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
    else:
        import ember_qc.algorithms.factored.field as F
        # workers are REUSED across jobs: always reset the function to
        # the arm's variant (the first run of this probe was invalidated
        # by patch leakage between arms — recorded in s3.61)
        real = getattr(F, "_orig_line_pools", None) or F.line_pools
        F._orig_line_pools = real
        if arm == "att_noB":

            def zero_boundary(grid):
                base = dict(real(grid))
                if grid.stride > 1:
                    for o, nl in ((1, grid.H), (0, grid.W)):
                        base[(o, 0)] = 0
                        base[(o, nl - 1)] = 0
                return base

            F.line_pools = zero_boundary
        else:
            F.line_pools = real
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
        emb = r.get("embedding") or {}
        d = r.get("diag", {})
        skips, deficit, ext = (d.get("mm_skips"), d.get("deficit_edges"),
                               d.get("extensions"))
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                skips=skips, deficit=deficit, ext=ext,
                time=round(time.perf_counter() - t0, 1))


def main():
    print("load at start:", os.getloadavg(), flush=True)
    jobs = [(c, g, arm, s) for c, g in CELLS
            for arm in ("att", "att_noB", "mm") for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} s={row['skips']} d={row['deficit']} "
                  f"e={row['ext']} ({row['time']}s)", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nsummary (ACL mean over legal seeds (n); s359 = pre-round att):")
    for cell, _ in CELLS:
        parts = [f"{cell:16s}"]
        for arm in ("att", "att_noB", "mm"):
            sel = [r for r in rows if r["cell"] == cell
                   and r["arm"] == arm and r["final_acl"]]
            if sel:
                acl = f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                extra = ""
                for key, tag in (("skips", "s"), ("deficit", "d"),
                                 ("ext", "e")):
                    vals = [r[key] for r in sel if r[key] is not None]
                    if vals:
                        extra += f" {tag}{sum(vals)/len(vals):.0f}"
                parts.append(f"{arm}={acl}({len(sel)}){extra}")
            else:
                parts.append(f"{arm}=FAIL(0)")
        parts.append(f"s359={S359[cell]}")
        parts.append(f"tmpl={TEMPLATE.get(cell, '-')}")
        print("  ".join(parts))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-packer2-probe", flush=True)


if __name__ == "__main__":
    main()
