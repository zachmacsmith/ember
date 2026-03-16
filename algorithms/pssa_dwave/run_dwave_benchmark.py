"""
experiments/run_dwave_benchmark.py
====================================
Run PSSA across D-Wave topologies and compare against minorminer.

Usage examples:
    # Quick smoke test (no D-Wave install needed — uses manual HW graph)
    python experiments/run_dwave_benchmark.py --mode smoke

    # Full benchmark on chimera(4)
    python experiments/run_dwave_benchmark.py --topology chimera --size 4

    # All topologies
    python experiments/run_dwave_benchmark.py --topology all
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import networkx as nx
from pssa_dwave.benchmark import run_benchmark
from pssa_dwave.improved_pssa import ImprovedPSSA, is_valid_embedding
from pssa_dwave.core import _path_partition_guiding, DWaveSchedule


def smoke_test():
    """No dwave-networkx needed — uses a 6x6 grid as surrogate HW."""
    print("=" * 60)
    print("SMOKE TEST  (6x6 grid surrogate hardware)")
    print("=" * 60)

    H = nx.convert_node_labels_to_integers(nx.grid_2d_graph(6, 6))

    test_cases = [
        ("path_4",    nx.path_graph(4)),
        ("cycle_6",   nx.cycle_graph(6)),
        ("cubic_8",   nx.random_regular_graph(3, 8, seed=0)),
        ("K4",        nx.complete_graph(4)),
    ]

    for name, I in test_cases:
        algo = ImprovedPSSA(
            hardware_graph = H,
            tmax           = 30_000,
            seed           = 42,
            verbose        = False,
        )
        r = algo.run(I)
        status = "✓" if r.success else f"✗ ({r.coverage:.0%})"
        print(f"  {name:15s}  n={I.number_of_nodes():3d}  m={I.number_of_edges():3d}  "
              f"→  {status}  chain={sum(len(v) for v in r.phi.values())/len(r.phi):.2f}  "
              f"t={r.wall_time:.2f}s")


def compare_topologies():
    """Requires dwave-networkx. Compare PSSA vs minorminer on each topology."""
    configs = [
        ("chimera", 4),
        ("pegasus", 2),
        ("zephyr",  2),
    ]
    for topo, sz in configs:
        try:
            run_benchmark(
                topology    = topo,
                size        = sz,
                algorithms  = ["pssa", "pssa-weighted", "minorminer"],
                graph_types = ["cubic", "erdos_renyi"],
                n_input     = 8,
                n_trials    = 3,
                verbose     = True,
            )
        except ImportError as e:
            print(f"Skipping {topo}({sz}): {e}")


def parameter_sensitivity():
    """Show effect of key parameters on embedding quality."""
    print("\n" + "=" * 60)
    print("PARAMETER SENSITIVITY — tmax vs coverage")
    print("=" * 60)

    H = nx.convert_node_labels_to_integers(nx.grid_2d_graph(8, 8))
    I = nx.random_regular_graph(3, 12, seed=0)
    print(f"Hardware: 8x8 grid  ({H.number_of_nodes()} nodes)")
    print(f"Input:    cubic-3, n=12  ({I.number_of_edges()} edges)\n")

    for tmax in [5_000, 20_000, 100_000, 500_000]:
        results = []
        for seed in range(5):
            r = ImprovedPSSA(hardware_graph=H, tmax=tmax, seed=seed).run(I)
            results.append(r.coverage)
        avg = sum(results) / len(results)
        bar = "█" * int(avg * 20)
        print(f"  tmax={tmax:>8,}  avg_coverage={avg:.3f}  {bar}")

    print("\n" + "=" * 60)
    print("PARAMETER SENSITIVITY — topology defaults (T0, beta)")
    print("=" * 60)
    for topo in ["chimera", "pegasus", "zephyr"]:
        s = DWaveSchedule(tmax=100_000, topology=topo)
        print(f"  {topo:10s}  T0={s.T0:.1f}  Thalf={s.Thalf:.1f}  "
              f"beta={s.beta}  pa_end={s.pa_end}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["smoke", "full", "sensitivity", "all"],
                        default="smoke")
    parser.add_argument("--topology", default="chimera",
                        choices=["chimera", "pegasus", "zephyr", "all"])
    parser.add_argument("--size", type=int, default=4)
    args = parser.parse_args()

    if args.mode == "smoke" or args.mode == "all":
        smoke_test()
    if args.mode == "sensitivity" or args.mode == "all":
        parameter_sensitivity()
    if args.mode == "full" or args.mode == "all":
        compare_topologies()
