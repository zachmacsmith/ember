"""
docs/paper/data/solution_quality.py
===================================
Validation experiment (#1): does a shorter / lower-variance embedding actually
yield BETTER annealing solutions? We never claimed it directly in the paper; here
we test the proxy link ACL -> solution quality on a simulator.

Pipeline, per (random Ising problem H, embedding phi, chain strength c):
  embed_ising(H, phi, target, chain_strength=c)   [dwave.embedding reference]
    -> SimulatedAnnealingSampler  (num_reads)      [dwave.samplers reference]
    -> majority-vote unembed                       [dwave.embedding reference]
    -> metrics vs the EXACT ground state (dimod.ExactSolver):
         P(ground state), residual-energy ratio, chain-break fraction.
A spin-vector Monte Carlo (SVMC) cross-check (ember_qc.anneal, semiclassical QA
proxy) is run at the reference chain strength.

Problems are kept small (n<=18) so the exact ground state is tractable; the target
is Pegasus P3 (clean and broken) -- small enough that dense sources need real,
breakable chains, so chain length visibly matters.

Outputs raw_solution_quality.csv (one row per problem x embedding x chain-strength,
SA + SVMC) and embeddings_solution_quality.csv (per-embedding ACL/max-chain). The
ACL<->quality correlation, paired tests, and figures live in analyze_quality.py.

Usage:  python solution_quality.py [n_workers] [num_reads]
"""
from __future__ import annotations

import csv
import itertools
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import networkx as nx  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# --- experiment grid ---------------------------------------------------------
FAMILIES = [
    ("ER", [10, 12, 14, 16, 18], [0.4, 0.6, 0.8]),
    ("REG", [12, 16], [4, 6]),                       # d here is the regular degree
]
GRAPH_SEEDS = [0, 1]            # independent source graphs per cell
PROBLEMS_PER_GRAPH = 3         # random Ising instances per graph
EMBED_SEEDS = [0, 1]
METHODS = ["minorminer", "minorminer-layout", "reweave", "reweave-thorough",
           "mmfork-cuthill", "mmfork-portfolio"]
CHAIN_REL = [0.5, 0.75, 1.0, 1.5, 2.0]   # chain strength / max|J|; 1.0 = reference
REF_REL = 1.0
PEGASUS_M = 3
FAULT_RATE, FAULT_SEED = 0.05, 7
ISING_SEED0 = 9000
SVMC_READS, SVMC_SWEEPS, SVMC_BETA = 64, 500, 6.0


def _gen_graph(fam, n, d, seed):
    if fam == "ER":
        g = nx.gnp_random_graph(n, d, seed=seed)
    else:
        g = nx.random_regular_graph(int(d), n, seed=seed)
    return nx.convert_node_labels_to_integers(g)


def build_problems():
    """Returns list of dicts: graph key + (h, J) + exact ground energy."""
    import dimod
    from ember_qc.anneal import random_ising
    problems = []
    pid = 0
    for fam, ns, ds in FAMILIES:
        for n in ns:
            for d in ds:
                for gseed in GRAPH_SEEDS:
                    G = _gen_graph(fam, n, d, gseed)
                    gkey = f"{fam}_n{n}_d{d}_g{gseed}"
                    for k in range(PROBLEMS_PER_GRAPH):
                        h, J = random_ising(G, seed=ISING_SEED0 + pid, kind="pm1")
                        bqm = dimod.BinaryQuadraticModel.from_ising(h, J)
                        gs = float(dimod.ExactSolver().sample(bqm).first.energy)
                        problems.append(dict(pid=pid, gkey=gkey, fam=fam, n=n, d=d,
                                             gseed=gseed, G=G, h=h, J=J, gs=gs))
                        pid += 1
    return problems


def build_embeddings(problems):
    """One embedding per (graph, target, method, embed-seed). Returns dict
    gkey -> list of embedding records (shared by all problems on that graph)."""
    from ember_qc.benchmark import benchmark_one
    import dwave_networkx as dnx
    from ember_qc.faults import simulate_faults
    P = dnx.pegasus_graph(PEGASUS_M)
    targets = {"pegasus_3": P,
               "pegasus_3_broken5": simulate_faults(P, fault_rate=FAULT_RATE, fault_seed=FAULT_SEED)}
    # unique graphs
    graphs = {}
    for p in problems:
        graphs.setdefault(p["gkey"], p["G"])
    embs: dict = {}
    for gkey, G in graphs.items():
        recs = []
        for tname, T in targets.items():
            for method in METHODS:
                for eseed in EMBED_SEEDS:
                    r = benchmark_one(G, T, method, timeout=30, seed=eseed,
                                      graph_name=gkey, topology_name=tname)
                    if not (r.success and r.is_valid):
                        continue
                    recs.append(dict(gkey=gkey, target=tname, method=method, eseed=eseed,
                                     acl=float(r.avg_chain_length),
                                     maxchain=int(r.max_chain_length),
                                     qubits=int(r.total_qubits_used),
                                     embedding={int(k): [int(q) for q in v]
                                                for k, v in r.embedding.items()}))
        embs[gkey] = recs
    return embs, targets


# --- worker ------------------------------------------------------------------
_TARGETS: dict = {}
_NUM_READS = 500


def _init(num_reads):
    global _TARGETS, _NUM_READS
    import dwave_networkx as dnx
    from ember_qc.faults import simulate_faults
    P = dnx.pegasus_graph(PEGASUS_M)
    _TARGETS = {"pegasus_3": P,
                "pegasus_3_broken5": simulate_faults(P, fault_rate=FAULT_RATE, fault_seed=FAULT_SEED)}
    _NUM_READS = num_reads


def _score(logical_energies, gs, tol=1e-6):
    e = np.asarray(logical_energies, dtype=float)
    p_gs = float(np.mean(e <= gs + tol))
    mean_e = float(np.mean(e))
    best_e = float(np.min(e))
    # residual ratio: 0 = reached GS on average; 1 = no better than a random spin
    # config (whose expected Ising energy is 0 for zero-field-mean +/-1 couplings).
    denom = abs(gs) if abs(gs) > 1e-9 else 1.0
    resid = (mean_e - gs) / denom
    return p_gs, resid, mean_e, best_e


def _run(task):
    import dimod
    from dwave.embedding import embed_ising, unembed_sampleset, chain_break_frequency
    from dwave.embedding.chain_breaks import majority_vote
    from dwave.samplers import SimulatedAnnealingSampler
    from ember_qc.anneal import svmc_sample, ising_energy

    p, e, rel = task
    h, J, gs = p["h"], p["J"], p["gs"]
    emb = e["embedding"]
    T = _TARGETS[e["target"]]
    maxabsJ = max((abs(w) for w in J.values()), default=1.0)
    c = rel * maxabsJ
    bqm = dimod.BinaryQuadraticModel.from_ising(h, J)

    th, tJ = embed_ising(h, J, emb, T, chain_strength=c)
    sa = SimulatedAnnealingSampler().sample_ising(th, tJ, num_reads=_NUM_READS, seed=p["pid"])
    un = unembed_sampleset(sa, emb, bqm, chain_break_method=majority_vote)
    p_gs, resid, mean_e, best_e = _score(un.record.energy, gs)
    cbf = float(np.mean(list(chain_break_frequency(sa, emb).values()))) if emb else 0.0

    row = dict(pid=p["pid"], gkey=p["gkey"], fam=p["fam"], n=p["n"], d=p["d"],
               target=e["target"], method=e["method"], eseed=e["eseed"],
               acl=e["acl"], maxchain=e["maxchain"], chain_rel=rel,
               sampler="SA", p_gs=round(p_gs, 4), resid=round(resid, 4),
               mean_e=round(mean_e, 3), best_e=round(best_e, 3),
               gs=round(gs, 3), chainbreak=round(cbf, 4))

    # SVMC cross-check at the reference chain strength only
    svmc_row = None
    if abs(rel - REF_REL) < 1e-9:
        samples = svmc_sample(th, tJ, num_reads=SVMC_READS, num_sweeps=SVMC_SWEEPS,
                              beta=SVMC_BETA, seed=p["pid"])
        # majority-vote unembed each SVMC sample -> logical energy
        log_es = []
        for s in samples:
            logical = {}
            for v, chain in emb.items():
                votes = sum(s[q] for q in chain)
                logical[v] = 1 if votes >= 0 else -1
            log_es.append(ising_energy(h, J, logical))
        sp_gs, sresid, smean, sbest = _score(log_es, gs)
        svmc_row = dict(row, sampler="SVMC", p_gs=round(sp_gs, 4), resid=round(sresid, 4),
                        mean_e=round(smean, 3), best_e=round(sbest, 3), chainbreak="")
    return row, svmc_row


def main():
    n_workers = int(sys.argv[1]) if len(sys.argv) > 1 else max(1, (os.cpu_count() or 4) - 2)
    num_reads = int(sys.argv[2]) if len(sys.argv) > 2 else 500

    t0 = time.perf_counter()
    print("building problems (+ exact ground states)...", flush=True)
    problems = build_problems()
    print(f"  {len(problems)} problems in {time.perf_counter()-t0:.0f}s", flush=True)

    print("building embeddings...", flush=True)
    embs, _ = build_embeddings(problems)
    n_emb = sum(len(v) for v in embs.values())
    print(f"  {n_emb} embeddings in {time.perf_counter()-t0:.0f}s", flush=True)

    # write per-embedding table
    with open(os.path.join(HERE, "embeddings_solution_quality.csv"), "w", newline="") as f:
        recs = [dict(gkey=r["gkey"], target=r["target"], method=r["method"], eseed=r["eseed"],
                     acl=r["acl"], maxchain=r["maxchain"], qubits=r["qubits"])
                for v in embs.values() for r in v]
        w = csv.DictWriter(f, fieldnames=list(recs[0].keys())); w.writeheader(); w.writerows(recs)

    tasks = [(p, e, rel) for p in problems for e in embs[p["gkey"]] for rel in CHAIN_REL]
    print(f"{len(tasks)} SA trials (+{sum(1 for _,_,r in tasks if abs(r-REF_REL)<1e-9)} SVMC); "
          f"workers={n_workers}, num_reads={num_reads}", flush=True)

    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init, initargs=(num_reads,)) as ex:
        for sa_row, svmc_row in ex.map(_run, tasks, chunksize=1):
            rows.append(sa_row)
            if svmc_row is not None:
                rows.append(svmc_row)
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(tasks)}  ({time.perf_counter()-t0:.0f}s)", flush=True)

    raw = os.path.join(HERE, "raw_solution_quality.csv")
    with open(raw, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"wrote {raw} ({len(rows)} rows)\nTOTAL_WALL={time.perf_counter()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
