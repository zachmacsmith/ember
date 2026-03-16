"""
pssa_dwave/benchmark.py
========================
Benchmark PSSA against minorminer across Chimera, Pegasus, Zephyr.

Usage:
    python -m pssa_dwave.benchmark --topology chimera --size 4 --trials 5
    python -m pssa_dwave.benchmark --topology all
"""

import argparse
import time
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import networkx as nx

from pssa_dwave.improved_pssa import ImprovedPSSA, is_valid_embedding
from pssa_dwave.core import build_hardware_graph, eemb, invert


# ── Input graph generators ─────────────────────────────────────────────────

def random_cubic(n: int, seed: int) -> nx.Graph:
    """Random 3-regular graph. n must be even."""
    n = n if n % 2 == 0 else n + 1
    return nx.random_regular_graph(3, n, seed=seed)


def erdos_renyi(n: int, p: float, seed: int) -> nx.Graph:
    return nx.erdos_renyi_graph(n, p, seed=seed)


def barabasi_albert(n: int, m: int, seed: int) -> nx.Graph:
    return nx.barabasi_albert_graph(n, m, seed=seed)


def complete_graph(n: int) -> nx.Graph:
    return nx.complete_graph(n)


# ── Result dataclass ───────────────────────────────────────────────────────

@dataclass
class TrialResult:
    algorithm:    str
    graph_type:   str
    n_input:      int
    topology:     str
    size:         int
    trial:        int
    success:      bool
    coverage:     float
    chain_length: float      # mean chain length across super vertices
    wall_time:    float
    eemb:         int
    m_I:          int


@dataclass
class BenchmarkSummary:
    algorithm:        str
    topology:         str
    size:             int
    graph_type:       str
    n_trials:         int
    success_rate:     float
    mean_coverage:    float
    mean_chain_len:   float
    mean_time:        float
    results:          List[TrialResult] = field(repr=False, default_factory=list)

    def __str__(self):
        return (
            f"{self.algorithm:25s} | {self.topology}({self.size}) | "
            f"{self.graph_type:15s} | "
            f"success={self.success_rate:.0%}  "
            f"coverage={self.mean_coverage:.3f}  "
            f"chain={self.mean_chain_len:.2f}  "
            f"time={self.mean_time:.2f}s"
        )


# ── Mean chain length helper ───────────────────────────────────────────────

def mean_chain_length(phi: dict) -> float:
    if not phi:
        return 0.0
    return sum(len(v) for v in phi.values()) / len(phi)


# ── Single trial runner ────────────────────────────────────────────────────

def run_trial(
    algorithm:  str,
    I:          nx.Graph,
    H:          nx.Graph,
    topology:   str,
    size:       int,
    graph_type: str,
    trial:      int,
    tmax:       Optional[int]  = None,
    weighted:   bool           = False,
    seed:       Optional[int]  = None,
) -> TrialResult:

    if algorithm.startswith("pssa"):
        _weighted = "weighted" in algorithm
        _tmax = tmax
        if "fast" in algorithm:
            _tmax = 50_000
        elif "thorough" in algorithm:
            _tmax = 2_000_000
        elif tmax is None:
            _tmax = None  # auto

        algo   = ImprovedPSSA(
            topology       = topology,
            size           = size,
            tmax           = _tmax,
            weighted       = _weighted,
            hardware_graph = H,
            seed           = seed,
        )
        result = algo.run(I)
        phi    = result.phi
        success = result.success
        coverage = result.coverage
        t = result.wall_time

    elif algorithm == "minorminer":
        try:
            import minorminer
            t0  = time.time()
            phi = minorminer.find_embedding(I, H, random_seed=seed or 0)
            t   = time.time() - t0
            if phi:
                inv      = invert(phi)
                e        = eemb(phi, I, H, inv)
                success  = (e == I.number_of_edges()) and is_valid_embedding(phi, I, H)
                coverage = e / max(I.number_of_edges(), 1)
            else:
                success  = False
                coverage = 0.0
        except ImportError:
            print("minorminer not installed — skipping")
            return None

    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    return TrialResult(
        algorithm    = algorithm,
        graph_type   = graph_type,
        n_input      = I.number_of_nodes(),
        topology     = topology,
        size         = size,
        trial        = trial,
        success      = success,
        coverage     = coverage,
        chain_length = mean_chain_length(phi) if phi else 0.0,
        wall_time    = t,
        eemb         = result.eemb if algorithm.startswith("pssa") else int(coverage * I.number_of_edges()),
        m_I          = I.number_of_edges(),
    )


# ── Full benchmark ─────────────────────────────────────────────────────────

def run_benchmark(
    topology:    str   = "chimera",
    size:        int   = 4,
    algorithms:  List[str] = None,
    graph_types: List[str] = None,
    n_input:     int   = 10,
    n_trials:    int   = 5,
    seed_base:   int   = 42,
    verbose:     bool  = True,
) -> List[BenchmarkSummary]:

    if algorithms is None:
        algorithms = ["pssa", "pssa-weighted", "minorminer"]
    if graph_types is None:
        graph_types = ["cubic", "erdos_renyi", "barabasi_albert"]

    H = build_hardware_graph(topology, size)

    if verbose:
        print(f"\n{'='*70}")
        print(f"Topology: {topology}({size})  |  HW nodes: {H.number_of_nodes()}")
        print(f"Input graphs: n={n_input}, types={graph_types}")
        print(f"Algorithms: {algorithms}")
        print(f"Trials per config: {n_trials}")
        print(f"{'='*70}\n")

    summaries: List[BenchmarkSummary] = []

    for gtype in graph_types:
        for algo in algorithms:
            trials: List[TrialResult] = []
            for t in range(n_trials):
                seed = seed_base + t * 100
                # Build input graph
                if gtype == "cubic":
                    I = random_cubic(n_input, seed=seed)
                elif gtype == "erdos_renyi":
                    I = erdos_renyi(n_input, p=0.3, seed=seed)
                elif gtype == "barabasi_albert":
                    I = barabasi_albert(n_input, m=2, seed=seed)
                elif gtype == "complete":
                    I = complete_graph(n_input)
                else:
                    continue

                r = run_trial(
                    algorithm  = algo,
                    I          = I,
                    H          = H,
                    topology   = topology,
                    size       = size,
                    graph_type = gtype,
                    trial      = t,
                    seed       = seed,
                )
                if r is not None:
                    trials.append(r)
                    if verbose:
                        status = "✓" if r.success else "✗"
                        print(f"  [{status}] {algo:20s}  {gtype:15s}  trial {t}  "
                              f"cov={r.coverage:.3f}  chain={r.chain_length:.2f}  "
                              f"t={r.wall_time:.2f}s")

            if trials:
                summary = BenchmarkSummary(
                    algorithm       = algo,
                    topology        = topology,
                    size            = size,
                    graph_type      = gtype,
                    n_trials        = len(trials),
                    success_rate    = sum(r.success for r in trials) / len(trials),
                    mean_coverage   = sum(r.coverage for r in trials) / len(trials),
                    mean_chain_len  = sum(r.chain_length for r in trials) / len(trials),
                    mean_time       = sum(r.wall_time for r in trials) / len(trials),
                    results         = trials,
                )
                summaries.append(summary)

    if verbose:
        print(f"\n{'─'*70}")
        print("SUMMARY")
        print(f"{'─'*70}")
        for s in summaries:
            print(s)

    return summaries


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark PSSA on D-Wave hardware")
    parser.add_argument("--topology", default="chimera",
                        choices=["chimera", "pegasus", "zephyr", "all"])
    parser.add_argument("--size",     type=int, default=4)
    parser.add_argument("--n-input",  type=int, default=10)
    parser.add_argument("--trials",   type=int, default=5)
    parser.add_argument("--algorithms", nargs="+",
                        default=["pssa", "pssa-weighted", "minorminer"])
    args = parser.parse_args()

    topologies = (
        [("chimera", 4), ("pegasus", 2), ("zephyr", 2)]
        if args.topology == "all"
        else [(args.topology, args.size)]
    )

    for topo, sz in topologies:
        run_benchmark(
            topology    = topo,
            size        = sz,
            algorithms  = args.algorithms,
            n_input     = args.n_input,
            n_trials    = args.trials,
            verbose     = True,
        )
