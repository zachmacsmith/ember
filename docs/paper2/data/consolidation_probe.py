"""
docs/paper2/data/consolidation_probe.py
========================================
Phase C of the 2026-07-29 consolidation: confirm the single-pipeline
`attraction` defaults (stair + arrange + insertion + wire seeds,
insert_sweeps=8) against stock minorminer, and close the harness->pipeline
gap (the champion dense numbers were produced by the emergence_check.py
probe harness; the in-pipeline stair arms had never run with insertion).

Pre-registered bars (set before the run; plan file + attraction.md entry):
- MINIMUM (consolidation valid): beat stock mm on all four dense cells
  (mm baselines ~13.44 / 20.70 / 25.37-with-failures / 8.26); K140 3/3
  legal; guards within ~0.2 of standing (regular_n316 ~3.5, ws_n486 ~3.4);
  ER within noise of mm.
- TARGET (gap closed): K100 <= ~12.6, K140 <= ~17.6, spin_glass <= ~18,
  turan <= ~8.5.
- Protocol decision rule: default = rounds unless 1shot wins >= 3 of the 4
  dense cells.

Arms: default (rounds), 1shot (max_rounds=1, round_frac=0.5), mm (stock).
3 seeds, 60 s, P16. Parallel workers (machine is shared: niced, bounded).

Run:  nohup .venv/bin/python docs/paper2/data/consolidation_probe.py \
        > docs/paper2/data/consolidation_probe.log 2>&1 &
"""

import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "consolidation_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

CELLS = ("K100", "K140", "turan_n162", "spin_glass_n163",
         "regular_n316", "ws_n486", "ER100_d10")

ARMS = [
    ("default", {}),
    ("1shot", {"max_rounds": 1, "round_frac": 0.5}),
    ("mm", None),
]


def _load_cell(name):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    ids = {"turan_n162": 2647, "spin_glass_n163": 37309,
           "regular_n316": 13096, "ws_n486": 17188}
    if name in ids:
        from ember_qc.load_graphs import load_graph
        return nx.convert_node_labels_to_integers(load_graph(ids[name]))
    raise ValueError(name)


def _run(job):
    cell, arm, kw, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    src = _load_cell(cell)
    target = dnx.pegasus_graph(16)
    t0 = time.perf_counter()
    if kw is None:  # stock minorminer
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
                legal_acl=r.get("legal_acl"),
                time=round(time.perf_counter() - t0, 1),
                diag=str(r.get("diag", "")))


def main():
    jobs = [(cell, arm, kw, s) for cell in CELLS for s in SEEDS
            for arm, kw in ARMS]
    rows = []
    # first run (consolidation_probe_w24.log) used 24 workers and hit machine
    # contention (load ~70 on the shared box): wall-clock timeouts starved the
    # rounds budget, spin_glass failed 0/3 for ALL arms incl. mm 1/3, while a
    # direct sequential run legalized in 2 rounds at legal_acl 17.76. Scoring
    # run: 8 workers.
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
        parts = [f"{cell:15s}"]
        for arm, _ in ARMS:
            vals = [r["final_acl"] for r in rows
                    if r["cell"] == cell and r["arm"] == arm
                    and r["final_acl"]]
            parts.append(f"{arm}={sum(vals)/len(vals):.2f}({len(vals)})"
                         if vals else f"{arm}=FAIL(0)")
        print("  ".join(parts))
    print("done-consolidation", flush=True)


if __name__ == "__main__":
    main()
