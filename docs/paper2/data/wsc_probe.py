"""
docs/paper2/data/wsc_probe.py
==============================
Multi-dense-patch behavior of the consolidated pipeline (Max, 2026-07-29):
weak_strong_cluster cells — c disjoint K32/K64 cliques joined by ONE
inter-edge per cluster pair. Every clique member is a participant (deg >=
31 > kappa), and the inter-cluster edges are participant-participant, so
they ARE visible to the insertion proxy — this family tests whether the
arrangement keeps the patches as separate blocks and where the routing
economics land, on the terrain busclique cannot touch at all (not a
clique) and where s3.23 recorded the old pipeline losing +0.3-0.5.

Arms: default (1shot, the new default), rounds (the pre-consolidation
protocol — ws_n486 suggested rounds may still help when sparse coupling
matters), mm (stock). 3 seeds, 60 s, P16, 8 niced workers (machine carries
a 60-core batch; ~68 cores free at launch).

Run:  nohup .venv/bin/python docs/paper2/data/wsc_probe.py \
        > docs/paper2/data/wsc_probe.log 2>&1 &
"""

import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "wsc_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

CELLS = {                      # name -> graph id
    "wsc_c3_sz32_n96": 33571,
    "wsc_c5_sz32_n160": 33601,
    "wsc_c8_sz32_n256": 33640,
    "wsc_c3_sz64_n192": 33574,
}

ARMS = [
    ("default", {}),
    ("rounds", {"max_rounds": 10, "round_frac": 0.4}),
    ("mm", None),
]


def _run(job):
    cell, gid, arm, kw, seed = job
    os.nice(10)
    import networkx as nx
    import dwave_networkx as dnx
    from ember_qc.load_graphs import load_graph
    src = nx.convert_node_labels_to_integers(load_graph(gid))
    target = dnx.pegasus_graph(16)
    t0 = time.perf_counter()
    if kw is None:
        import minorminer
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
        r = {}
    else:
        from ember_qc.algorithms.factored import attract_embed
        r = attract_embed(src, target, timeout=TIMEOUT, seed=seed, **kw)
        emb = r.get("embedding") or {}
    return dict(cell=cell, arm=arm, seed=seed,
                final_acl=round(sum(len(c) for c in emb.values()) / len(emb),
                                3) if emb else None,
                rounds=r.get("rounds"),
                time=round(time.perf_counter() - t0, 1),
                diag=str(r.get("diag", "")))


def main():
    jobs = [(cell, gid, arm, kw, s) for cell, gid in CELLS.items()
            for s in SEEDS for arm, kw in ARMS]
    rows = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} ({row['time']}s) {row['diag']}",
                  flush=True)
            rows.append(row)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    print("\nsummary (mean over legal seeds; n legal in parens):")
    for cell in CELLS:
        parts = [f"{cell:18s}"]
        for arm, _ in ARMS:
            vals = [r["final_acl"] for r in rows
                    if r["cell"] == cell and r["arm"] == arm
                    and r["final_acl"]]
            parts.append(f"{arm}={sum(vals)/len(vals):.2f}({len(vals)})"
                         if vals else f"{arm}=FAIL(0)")
        print("  ".join(parts))
    print("done-wsc", flush=True)


if __name__ == "__main__":
    main()
