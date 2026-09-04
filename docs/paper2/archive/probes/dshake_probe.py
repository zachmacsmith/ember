"""
docs/paper2/data/dshake_probe.py
=================================
The discrete-shake round (s3.53; Max: "test the discrete shaking and the
order inversion — I'd really like a sense of whether either is helpful").
Two mechanisms vs the s3.52 champion config:

- order_shake: coarse-to-fine order moves (segment reversals + block
  relocations at decaying scale L = n/2..2) chained before insertion in
  the same true-E-gated composite. The discrete shake — annealing in
  order space, scale playing the role of temperature.
- shake_invert: reshake cycles use radial RANK REVERSAL about the
  centroid instead of dilation (dilation preserves radial order — the
  measured reason s3.52's reshakes explored nothing; inversion makes
  the core earn its place).

Arms (all courses=True; paired by (cell, seed); 3 seeds x 60 s):
- base   : shake_cycles=1                    — s3.52 champion control
           (reference values: turan 7.70 / K100 10.02 / K140 14.17 /
           spin_glass 14.21 / ER 4.70)
- invert : shake_cycles=2, shake_invert     — cycle 0 == base's run;
           cycle 1 = exactly ONE inversion+resettle under keep-best
- dshake : shake_cycles=1, order_shake=1
- both   : shake_cycles=2, shake_invert, order_shake=1 (additivity only:
           the mechanisms act at different cycles)

PRE-REGISTERED READING (sense-probe; written before any run):
- A mechanism is HELPFUL if it improves >= 2 cells paired vs base beyond
  noise without regressing any other beyond noise. Watch: turan < 7.70
  (toward template 6.00) and the K140 zone (14.17; shake_pool holds
  12.16).
- KNOWN CONFOUND, recorded not fixed: order search (insert_sweeps /
  order_shake) runs only at cycle 0, so the invert arms' post-inversion
  resettle has NO order repair (_mono + packing only). If invert reads
  null, the verdict is "inversion without post-inversion order search is
  null"; all-cycles order search is the NEXT flip, not this probe.
- FAILURE RULE: both mechanisms inert -> record and stop; no further
  mechanism without discussion. No default flips from this probe.

Protocol notes: 12 workers nice 10 (box idle ~125 cores; Max approved —
finishing faster also dodges the other user's bursts). Launch only on a
quiet box; sanity-check base against the s3.52 shake1 values before
scoring.

Run:  nohup .venv/bin/python docs/paper2/data/dshake_probe.py \
        > docs/paper2/data/dshake_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "dshake_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "K140": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
ARMS = [("base", {"courses": True, "shake_cycles": 1}),
        ("invert", {"courses": True, "shake_cycles": 2,
                    "shake_invert": True}),
        ("dshake", {"courses": True, "shake_cycles": 1, "order_shake": 1}),
        ("both", {"courses": True, "shake_cycles": 2, "shake_invert": True,
                  "order_shake": 1})]
TEMPLATE = {"K100": "8.00", "K140": "11.00", "ER100_d10": "-",
            "turan_n162": "6.00", "spin_glass_n163": "11.64"}


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
    cell, gid, arm, kw, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    e0 = r.get("round_E") or [None]
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                geo_E=e0[0], time=round(time.perf_counter() - t0, 1))


def main():
    jobs = [(c, g, arm, kw, s) for c, g in CELLS.items()
            for arm, kw in ARMS for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=12) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} E={row['geo_E']} "
                  f"({row['time']}s)", flush=True)
            rows.append(row)

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print("\nsummary (ACL mean over legal seeds (n) | geometry E):")
    for cell in CELLS:
        parts = [f"{cell:16s}"]
        for arm, _ in ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["arm"] == arm and r["final_acl"]]
            es = [r["geo_E"] for r in rows if r["cell"] == cell
                  and r["arm"] == arm and r["geo_E"] is not None]
            acl = (f"{sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                   f"({len(sel)})" if sel else "FAIL(0)")
            emean = f"E{sum(es)/len(es):.0f}" if es else "E?"
            parts.append(f"{arm}={acl} {emean}")
        parts.append(f"tmpl={TEMPLATE[cell]}")
        print("  ".join(parts))
    print("done-dshake-probe", flush=True)


if __name__ == "__main__":
    main()
