"""
docs/paper/data/solution_quality_large.py
=========================================
Extension of the solution-quality validation to the DEPLOYMENT chain-length
regime. The main experiment (solution_quality.py) is capped at n<=18 by the
exact ground-state computation, which keeps ACL <= 2.8; the paper's methods
differ most at ACL 3.5-5.5. Here we drop the exact reference -- sources are
ER n in {24,32,40}, d=0.5 into clean Pegasus P6 (ACL ~2.6-4.5) -- and score
each (problem, embedding, chain-strength) SA run against the BEST energy found
across all runs of that problem ("best-known"):

  p_best = fraction of reads reaching best-known
  resid  = (mean E - E_best) / |E_best|

SA only (500 reads, dwave.samplers); chain strength swept over {0.75, 1, 1.5}.
Writes raw_solution_quality_large.csv; the fixed-effects analysis lives in
analyze_quality.py.

Usage:  python solution_quality_large.py [n_workers]
"""
from __future__ import annotations

import csv
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import networkx as nx  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NS = [24, 32, 40]
DENSITY = 0.5
GRAPH_SEEDS = [0, 1, 2, 3]
PROBLEMS_PER_GRAPH = 2
EMBED_SEEDS = [0, 1]
METHODS = ["minorminer", "minorminer-layout", "reweave", "reweave-thorough",
           "mmfork-cuthill", "mmfork-portfolio"]
CHAIN_REL = [0.75, 1.0, 1.5]
NUM_READS = 500
ISING_SEED0 = 77000

_TARGET = None


def _init():
    global _TARGET
    import dwave_networkx as dnx
    _TARGET = dnx.pegasus_graph(6)


def build_problems():
    from ember_qc.anneal import random_ising
    problems, pid = [], 0
    for n in NS:
        for gs in GRAPH_SEEDS:
            G = nx.convert_node_labels_to_integers(
                nx.gnp_random_graph(n, DENSITY, seed=ISING_SEED0 + gs))
            gkey = f"ER_n{n}_d{DENSITY}_g{gs}"
            for k in range(PROBLEMS_PER_GRAPH):
                h, J = random_ising(G, seed=ISING_SEED0 + pid, kind="pm1")
                problems.append(dict(pid=pid, gkey=gkey, n=n, G=G, h=h, J=J))
                pid += 1
    return problems


def build_embeddings(problems):
    from ember_qc.benchmark import benchmark_one
    import dwave_networkx as dnx
    P = dnx.pegasus_graph(6)
    graphs = {}
    for p in problems:
        graphs.setdefault(p["gkey"], p["G"])
    embs = {}
    for gkey, G in graphs.items():
        recs = []
        for method in METHODS:
            for es in EMBED_SEEDS:
                r = benchmark_one(G, P, method, timeout=30, seed=es,
                                  graph_name=gkey, topology_name="pegasus_6")
                if r.success and r.is_valid:
                    recs.append(dict(gkey=gkey, method=method, eseed=es,
                                     acl=float(r.avg_chain_length),
                                     maxchain=int(r.max_chain_length),
                                     embedding={int(k): [int(q) for q in v]
                                                for k, v in r.embedding.items()}))
        embs[gkey] = recs
    return embs


def _run(task):
    import dimod
    from dwave.embedding import embed_ising, unembed_sampleset, chain_break_frequency
    from dwave.embedding.chain_breaks import majority_vote
    from dwave.samplers import SimulatedAnnealingSampler
    p, e, rel = task
    h, J = p["h"], p["J"]
    c = rel * max(abs(w) for w in J.values())
    bqm = dimod.BinaryQuadraticModel.from_ising(h, J)
    th, tJ = embed_ising(h, J, e["embedding"], _TARGET, chain_strength=c)
    sa = SimulatedAnnealingSampler().sample_ising(th, tJ, num_reads=NUM_READS, seed=p["pid"])
    un = unembed_sampleset(sa, e["embedding"], bqm, chain_break_method=majority_vote)
    energies = np.asarray(un.record.energy, dtype=float)
    cbf = float(np.mean(list(chain_break_frequency(sa, e["embedding"]).values())))
    return {"pid": p["pid"], "gkey": p["gkey"], "n": p["n"],
            "method": e["method"], "eseed": e["eseed"], "acl": e["acl"],
            "maxchain": e["maxchain"], "chain_rel": rel,
            "mean_e": float(energies.mean()), "best_e": float(energies.min()),
            "chainbreak": round(cbf, 4)}, energies


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 2)
    t0 = time.perf_counter()
    problems = build_problems()
    print(f"{len(problems)} problems (n up to {max(NS)}); building embeddings...", flush=True)
    embs = build_embeddings(problems)
    n_emb = sum(len(v) for v in embs.values())
    tasks = [(p, e, rel) for p in problems for e in embs[p["gkey"]] for rel in CHAIN_REL]
    print(f"{n_emb} embeddings; {len(tasks)} SA runs; workers={n_workers}", flush=True)

    rows, evecs = [], []
    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init) as ex:
        for i, (row, en) in enumerate(ex.map(_run, tasks, chunksize=1)):
            rows.append(row); evecs.append(en)
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(tasks)} ({time.perf_counter()-t0:.0f}s)", flush=True)

    # global best-known energy per problem, then per-row scores
    best = {}
    for row in rows:
        best[row["pid"]] = min(best.get(row["pid"], float("inf")), row["best_e"])
    for row, en in zip(rows, evecs):
        eb = best[row["pid"]]
        row["gs"] = round(eb, 3)   # best-known reference (column name matches main CSV)
        row["p_gs"] = round(float(np.mean(en <= eb + 1e-6)), 4)
        row["resid"] = round((row["mean_e"] - eb) / abs(eb) if abs(eb) > 1e-9 else 0.0, 4)
        row["mean_e"] = round(row["mean_e"], 3); row["best_e"] = round(row["best_e"], 3)

    out = os.path.join(HERE, "raw_solution_quality_large.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)\nTOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
