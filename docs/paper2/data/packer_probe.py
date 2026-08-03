"""
docs/paper2/data/packer_probe.py
=================================
The exact-packer round (notes s3.59): the greedy nearest-line packer is
replaced in place by the exact order-preserving DP (`pack_lines`) with
integer per-line sub-lane pools shared with claim_overload (one
accounting), and the boundary rule moved from a grid.cap mutation to
packer-side data. Oversubscription (the d729 class, s3.56) is now
structurally impossible — unit-tested via post-pack claim_overload == 0;
this probe measures what that buys on the board.

Arms (3 seeds x 60 s, paired): att = zero-kwarg default (now DP-packed),
mm = stock minorminer. Control comparison: the s3.58 consolidation2
board (same box, same protocol): att 8.74 / 11.41 / 4.76 / 7.90 / 12.47,
off-template 2.89 / 3.01 / 3.81 / 6.69; mm 10.28 / 17.90(2/3) / 4.97 /
12.01 / 18.09, off-template 3.36 / 3.08 / 3.78 / 7.31.

PRE-REGISTERED BARS:
- MECHANISM (unit-tested, probe-corroborated): exact gates keep firing
  s1 d0 e0 on K100/K140/turan; no deficit regressions elsewhere.
- MINIMUM: turan <= 7.5 with s1 d0 (the s3.56 prediction: when packing
  respects depth 8, 7.19-negotiated and 7.90-constructed should meet);
  guards hold: K100 <= 8.9, K140 <= 11.6, spin_glass <= 12.7,
  ER <= 4.95; off-template neutral-or-better vs the s3.58 values.
- STRETCH: turan <= 7.2 (meet the retired negotiated record).
- SCORING RULE (shared box): scorable only if paired mm replicates its
  recorded values; a bar miss with an inflated mm control = contention,
  rerun on a quieter window.
- No further flips ride on this probe (the DP is the default path by
  construction; a failed bar reopens the round).

Run:  nohup .venv/bin/python docs/paper2/data/packer_probe.py \
        > docs/paper2/data/packer_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "packer_probe.csv")
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
S358 = {"K100": 8.74, "K140": 11.41, "ER100_d10": 4.76,
        "turan_n162": 7.90, "spin_glass_n163": 12.47,
        "regular_n316": 2.89, "ws_n486": 3.01,
        "wsc_c8xK32": 3.81, "wsc_c3xK64": 6.69}


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
    if arm == "att":
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
        emb = r.get("embedding") or {}
        d = r.get("diag", {})
        skips, deficit, ext = (d.get("mm_skips"), d.get("deficit_edges"),
                               d.get("extensions"))
    else:
        import minorminer
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
        skips = deficit = ext = None
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                skips=skips, deficit=deficit, ext=ext,
                time=round(time.perf_counter() - t0, 1))


def main():
    print("load at start:", os.getloadavg(), flush=True)
    jobs = [(c, g, arm, s) for c, g in CELLS
            for arm in ("att", "mm") for s in SEEDS]
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
    print("\nsummary (ACL mean over legal seeds (n); s3.58 = pre-DP att):")
    for cell, _ in CELLS:
        parts = [f"{cell:16s}"]
        for arm in ("att", "mm"):
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
        parts.append(f"s358={S358[cell]}")
        parts.append(f"tmpl={TEMPLATE.get(cell, '-')}")
        print("  ".join(parts))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-packer-probe", flush=True)


if __name__ == "__main__":
    main()
