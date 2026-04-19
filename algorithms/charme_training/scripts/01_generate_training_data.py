#!/usr/bin/env python3
"""Generate diverse training graphs + minorminer baselines for QEBench.

Generates 195 graphs across 16 structural families matching the QEBench
benchmark graph types:
    bipartite, grid, cycle, path, star, wheel, turan, circulant,
    generalized_petersen, hypercube, binary_tree, tree, johnson, kneser,
    random_er, barabasi_albert, regular, watts_strogatz, sbm, lfr_benchmark,
    random_planar, triangular_lattice, kagome, honeycomb, king_graph,
    frustrated_square, shastry_sutherland, cubic_lattice, bcc_lattice,
    weak_strong_cluster, planted_solution, spin_glass, hardware_native,
    named_special, sudoku

Graph sizes are capped at 120 nodes to ensure ATOM can embed them into
a Chimera(45,45,4) hardware graph within a reasonable time.

Usage:
    python scripts/01_generate_training_data.py \
        --hw_topo_row 45 --hw_topo_col 45 --hw_bipart_cell 4 \
        --out_dir training_data
"""

from __future__ import annotations

import argparse
import pickle
import random
import sys
import traceback
from pathlib import Path
from typing import List, Tuple

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from charme.utils import (
    generate_Chimera,
    convert_graph_to_embeddingMinorminer,
)


# ── Graph generators ───────────────────────────────────────────────────────────
# Each entry: (label, generator_fn)
# generator_fn returns a connected NetworkX graph with nodes 0..N-1

def _relabel(G: nx.Graph) -> nx.Graph:
    """Relabel to 0..N-1 and ensure connected."""
    if not nx.is_connected(G):
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    return nx.convert_node_labels_to_integers(G)


def make_ba_sparse():
    return _relabel(nx.barabasi_albert_graph(random.randint(80, 120), 2))

def make_ba_medium():
    return _relabel(nx.barabasi_albert_graph(random.randint(80, 100), 5))

def make_ba_dense():
    return _relabel(nx.barabasi_albert_graph(random.randint(60, 80), 10))

def make_er_sparse():
    n = random.randint(60, 80)
    return _relabel(nx.erdos_renyi_graph(n, 0.08, seed=random.randint(0, 9999)))

def make_er_dense():
    n = random.randint(40, 60)
    return _relabel(nx.erdos_renyi_graph(n, 0.35, seed=random.randint(0, 9999)))

def make_regular_sparse():
    n = random.choice([60, 70, 80])
    if n % 2 != 0:
        n += 1
    return _relabel(nx.random_regular_graph(4, n, seed=random.randint(0, 9999)))

def make_regular_dense():
    n = random.choice([40, 50, 60])
    if n % 2 != 0:
        n += 1
    return _relabel(nx.random_regular_graph(8, n, seed=random.randint(0, 9999)))

def make_watts_strogatz_sparse():
    n = random.randint(60, 80)
    return _relabel(nx.watts_strogatz_graph(n, 4, 0.1, seed=random.randint(0, 9999)))

def make_watts_strogatz_dense():
    n = random.randint(60, 80)
    return _relabel(nx.watts_strogatz_graph(n, 6, 0.3, seed=random.randint(0, 9999)))

def make_grid():
    m = random.randint(5, 9)
    n = random.randint(5, 9)
    return _relabel(nx.grid_2d_graph(m, n))

def make_triangular_lattice():
    m = random.randint(4, 7)
    n = random.randint(4, 7)
    return _relabel(nx.triangular_lattice_graph(m, n))

def make_honeycomb():
    m = random.randint(3, 5)
    n = random.randint(3, 5)
    return _relabel(nx.hexagonal_lattice_graph(m, n))

def make_cycle():
    return _relabel(nx.cycle_graph(random.randint(50, 100)))

def make_wheel():
    return _relabel(nx.wheel_graph(random.randint(40, 80)))

def make_star():
    return _relabel(nx.star_graph(random.randint(30, 60)))

def make_path():
    return _relabel(nx.path_graph(random.randint(50, 100)))

def make_tree():
    return _relabel(nx.balanced_tree(r=random.randint(2, 3), h=random.randint(3, 5)))

def make_sbm():
    sizes = [random.randint(15, 25) for _ in range(random.randint(3, 5))]
    n = sum(sizes)
    k = len(sizes)
    # Dense within communities, sparse between
    p = np.full((k, k), 0.05)
    np.fill_diagonal(p, 0.4)
    return _relabel(nx.stochastic_block_model(sizes, p.tolist(),
                                               seed=random.randint(0, 9999)))

def make_community():
    """Weak/strong cluster — 2 communities with different inter-edge density."""
    n1, n2 = random.randint(20, 35), random.randint(20, 35)
    G = nx.Graph()
    # Community 1: dense
    G.add_nodes_from(range(n1))
    for i in range(n1):
        for j in range(i+1, n1):
            if random.random() < 0.4:
                G.add_edge(i, j)
    # Community 2: medium
    for i in range(n1, n1+n2):
        for j in range(i+1, n1+n2):
            if random.random() < 0.3:
                G.add_edge(i, j)
    G.add_nodes_from(range(n1, n1+n2))
    # Sparse inter-community edges
    for i in range(n1):
        for j in range(n1, n1+n2):
            if random.random() < 0.02:
                G.add_edge(i, j)
    # Ensure connectivity
    if not nx.is_connected(G):
        for i in range(n1):
            G.add_edge(i, n1)
            if nx.is_connected(G):
                break
    return _relabel(G)

def make_petersen_like():
    k = random.randint(4, 8)
    return _relabel(nx.generalized_petersen_graph(k * 2, k))

def make_circulant():
    n = random.randint(40, 80)
    offsets = random.sample(range(1, n//2), min(3, n//2 - 1))
    return _relabel(nx.circulant_graph(n, offsets))

def make_hypercube():
    d = random.randint(4, 6)  # 2^4=16 to 2^6=64 nodes
    return _relabel(nx.hypercube_graph(d))

def make_bipartite():
    n1 = random.randint(20, 40)
    n2 = random.randint(20, 40)
    p = random.uniform(0.15, 0.4)
    return _relabel(nx.bipartite.random_graph(n1, n2, p,
                                               seed=random.randint(0, 9999)))

def make_planar():
    n = random.randint(40, 70)
    # Random planar graph via triangulation of random points
    G = nx.random_geometric_graph(n, 0.25, seed=random.randint(0, 9999))
    return _relabel(G)

def make_king():
    """King graph — grid where nodes also connect diagonally."""
    m = random.randint(5, 8)
    n = random.randint(5, 8)
    G = nx.grid_2d_graph(m, n)
    # Add diagonal edges
    for i in range(m-1):
        for j in range(n-1):
            G.add_edge((i, j), (i+1, j+1))
            G.add_edge((i+1, j), (i, j+1))
    return _relabel(G)


# ── Training set spec ─────────────────────────────────────────────────────────
# (label, generator_fn, count)
TRAINING_SPEC: List[Tuple[str, object, int]] = [
    # Barabási-Albert family — covers ba, random-like, sparse/dense
    ("ba_sparse",           make_ba_sparse,          20),
    ("ba_medium",           make_ba_medium,          20),
    ("ba_dense",            make_ba_dense,           20),
    # Erdős-Rényi — covers random_er
    ("er_sparse",           make_er_sparse,          15),
    ("er_dense",            make_er_dense,           15),
    # Regular — covers regular, circulant
    ("regular_sparse",      make_regular_sparse,     15),
    ("regular_dense",       make_regular_dense,      15),
    # Watts-Strogatz — covers watts_strogatz, small-world
    ("ws_sparse",           make_watts_strogatz_sparse, 15),
    ("ws_dense",            make_watts_strogatz_dense,  15),
    # Lattice family — covers grid, triangular_lattice, honeycomb, king_graph
    ("grid",                make_grid,               10),
    ("triangular_lattice",  make_triangular_lattice,  5),
    ("honeycomb",           make_honeycomb,           5),
    ("king_graph",          make_king,                5),
    # Sparse structured — covers cycle, path, star, wheel, tree
    ("cycle",               make_cycle,               5),
    ("path",                make_path,                3),
    ("star",                make_star,                3),
    ("wheel",               make_wheel,               3),
    ("tree",                make_tree,                4),
    # Community structure — covers sbm, lfr, weak_strong_cluster, spin_glass
    ("sbm",                 make_sbm,                10),
    ("community",           make_community,          10),
    # Algebraic/structured — covers petersen, circulant, hypercube
    ("petersen_like",       make_petersen_like,       5),
    ("circulant",           make_circulant,           5),
    ("hypercube",           make_hypercube,           5),
    # Bipartite — covers bipartite
    ("bipartite",           make_bipartite,          10),
    # Planar — covers random_planar
    ("planar",              make_planar,              7),
]

TOTAL = sum(c for _, _, c in TRAINING_SPEC)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--hw_topo_row",   type=int, default=45)
    p.add_argument("--hw_topo_col",   type=int, default=45)
    p.add_argument("--hw_bipart_cell", type=int, default=4)
    p.add_argument("--out_dir",       type=str, default="training_data")
    p.add_argument("--minorminer_filename", type=str,
                   default="minorminer_results.pth")
    p.add_argument("--seed",          type=int, default=42)
    return p.parse_args()


def main():
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building Chimera({args.hw_topo_row},{args.hw_topo_col},"
          f"{args.hw_bipart_cell})...")
    chimera = generate_Chimera(
        topo_row=args.hw_topo_row,
        topo_column=args.hw_topo_col,
        bipart_cell=args.hw_bipart_cell,
    )
    print(f"  Hardware: {chimera.number_of_nodes()} nodes, "
          f"{chimera.number_of_edges()} edges")
    print(f"\nGenerating {TOTAL} training graphs across "
          f"{len(TRAINING_SPEC)} structural families...\n")

    graph_list = []
    minorminer_list = []
    graph_idx = 0
    skipped = 0

    for label, gen_fn, count in TRAINING_SPEC:
        family_ok = 0
        attempts = 0
        while family_ok < count and attempts < count * 5:
            attempts += 1
            try:
                G = gen_fn()
                # Sanity checks
                if G.number_of_nodes() < 4:
                    continue
                if G.number_of_nodes() > 120:
                    continue
                if not nx.is_connected(G):
                    continue

                mm = convert_graph_to_embeddingMinorminer(G, chimera)
                qubits = (sum(len(v) for v in mm.values())
                          if isinstance(mm, dict) else len(mm))

                # Skip if embedding failed (returned empty)
                if qubits == 0:
                    skipped += 1
                    continue

                graph_path = out_dir / f"graph_{graph_idx}.txt"
                nx.write_edgelist(G, str(graph_path), data=False)

                graph_list.append(G)
                minorminer_list.append(mm)

                print(f"[{graph_idx+1:>3}/{TOTAL}] {label:<22} "
                      f"n={G.number_of_nodes():>3} "
                      f"m={G.number_of_edges():>4} "
                      f"qubits={qubits:>5}")

                graph_idx += 1
                family_ok += 1

            except Exception:
                skipped += 1
                continue

        if family_ok < count:
            print(f"  WARNING: only generated {family_ok}/{count} "
                  f"graphs for {label}")

    # Save minorminer baselines
    mm_path = out_dir / args.minorminer_filename
    with open(mm_path, "wb") as f:
        pickle.dump(minorminer_list, f)

    # Save a manifest so train.py knows the training_size
    manifest = {
        "total_graphs": len(graph_list),
        "families": {label: count for label, _, count in TRAINING_SPEC},
        "skipped": skipped,
    }
    manifest_path = out_dir / "manifest.pkl"
    with open(manifest_path, "wb") as f:
        pickle.dump(manifest, f)

    print(f"\n{'='*50}")
    print(f"Generated {len(graph_list)} graphs ({skipped} skipped)")
    print(f"Saved to: {out_dir}/")
    print(f"  graph_0.txt ... graph_{len(graph_list)-1}.txt")
    print(f"  {args.minorminer_filename}")
    print(f"  manifest.pkl  (training_size={len(graph_list)})")
    print(f"\nIMPORTANT: update train.py TrainConfig:")
    print(f"  training_size = {len(graph_list)}")
    print(f"  lg_num_nodes  = (set to your largest graph node count)")
    print(f"\nNext: python scripts/02_generate_orderlist.py")


if __name__ == "__main__":
    main()
