"""
docs/paper2/data/pipeline_z12_probe.py
=======================================
The s3.47 experiment (Max: "I'm out of ideas, so it's probably experiment
time"): the EXISTING attraction pipeline (L-representation: corners +
derived arms + arrange + wire seeds, Zephyr adapter, derived kappa) run
with the full routed protocol on the four Z12 cells — the measurement the
contact rounds never made. Decides the reunification question:

- pipeline ER <= ~4.9 (contact got 4.65/4.72; mm 4.97/mm2 4.86): the
  corners-only state was right all along; seats are a Zephyr theorem;
  contact-land was the proof of why. Fold back and simplify.
- pipeline loses ER to contact: per-edge freedom buys something real on
  liquid graphs that derived arms cannot express — a third idea needed.

Arm: registered attraction default, 3 seeds x 60 s. mm/mm2 baselines
from contract_probe_routed.csv; contact numbers quoted from
contact_probe2.log (s3.46).

Run:  nohup .venv/bin/python docs/paper2/data/pipeline_z12_probe.py \
        > docs/paper2/data/pipeline_z12_probe.log 2>&1 &
"""
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "contract_probe_routed.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "ER100_d10": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}
CONTACT = {"K100": "15.50(3)", "ER100_d10": "4.72(3)",
           "turan_n162": "15.53(2)", "spin_glass_n163": "FAIL(0)"}


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, gid, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(cell, gid)
    target = dnx.zephyr_graph(12, 4)
    t0 = time.perf_counter()
    r = attract_embed(src, target, timeout=TIMEOUT, seed=seed)
    emb = r.get("embedding") or {}
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    return dict(cell=cell, seed=seed, final_acl=acl,
                time=round(time.perf_counter() - t0, 1),
                diag=str(r.get("diag", "")))


def main():
    jobs = [(c, g, s) for c, g in CELLS.items() for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} seed {row['seed']}: {row['final_acl']} "
                  f"({row['time']}s) {row['diag']}", flush=True)
            rows.append(row)

    base = {}
    if os.path.exists(BASE):
        with open(BASE) as fh:
            for r in csv.DictReader(fh):
                if r["target"] == "Z12" and r["cell"] in CELLS \
                        and r["arm"] in ("mm", "mm2"):
                    base.setdefault((r["cell"], r["arm"]), []).append(
                        float(r["final_acl"]) if r["final_acl"] else None)

    print("\nsummary (pipeline = registered attraction default on Z12):")
    for cell in CELLS:
        vals = [r["final_acl"] for r in rows
                if r["cell"] == cell and r["final_acl"]]
        parts = [f"{cell:16s}",
                 f"pipeline={sum(vals)/len(vals):.2f}({len(vals)})"
                 if vals else "pipeline=FAIL(0)",
                 f"contact={CONTACT[cell]}"]
        for arm in ("mm", "mm2"):
            bv = [x for x in base.get((cell, arm), []) if x is not None]
            parts.append(f"{arm}={sum(bv)/len(bv):.2f}({len(bv)})"
                         if bv else f"{arm}=?")
        print("  ".join(parts))
    print("done-pipeline-z12", flush=True)


if __name__ == "__main__":
    main()
