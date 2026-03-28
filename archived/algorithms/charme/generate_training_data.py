#!/usr/bin/env python3
"""
generate_training_data.py

Generates a set of logical graphs (edge lists) and a baseline embedding list
(using minorminer) on a Chimera hardware graph, then pickles the results.

Usage example:
  python generate_training_data.py \
    --hw_topo_row 10 --hw_topo_column 10 --hw_bipart_cell 4 \
    --lg_num_nodes 50 --lg_degree 5 \
    --n_graphs 10 \
    --out_dir training_data \
    --minorminer_filename minorminer_results.pth \
"""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Optional

import networkx as nx

# Assumes your project has these functions in utils.py
from charme.utils import (
    generate_Chimera,
    init_logical_graph,
    convert_graph_to_embeddingMinorminer,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate training graphs + minorminer baselines.")
    # Hardware (Chimera) hyperparameters
    p.add_argument("--hw_topo_row", type=int, default=10)
    p.add_argument("--hw_topo_column", type=int, default=10)
    p.add_argument("--hw_bipart_cell", type=int, default=4)

    # Logical graph hyperparameters
    p.add_argument("--lg_num_nodes", type=int, default=50)
    p.add_argument("--lg_degree", type=int, default=5)

    # Dataset size / paths
    p.add_argument("--n_graphs", type=int, default=10, help="Number of graphs to generate.")
    p.add_argument("--out_dir", type=str, default="training_data", help="Output directory.")
    p.add_argument(
        "--graph_prefix",
        type=str,
        default="graph_",
        help="Prefix for each edgelist file (graph_i.txt).",
    )
    p.add_argument(
        "--graph_ext",
        type=str,
        default=".txt",
        help="Extension for each graph file.",
    )
    p.add_argument(
        "--minorminer_filename",
        type=str,
        default="minorminer_results.pth",
        help="Pickle filename to store the list of embeddings.",
    )

    return p.parse_args()


def maybe_seed_for_index(seed: Optional[int], i: int) -> Optional[int]:
    return None if seed is None else (seed + i)


def main() -> None:
    args = parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build Chimera hardware graph
    original_chimera_graph = generate_Chimera(
        topo_row=args.hw_topo_row,
        topo_column=args.hw_topo_column,
        bipart_cell=args.hw_bipart_cell,
    )

    # Generate graphs + baseline embeddings
    minorminer_list = []
    for i in range(args.n_graphs):
        graph_path = out_dir / f"{args.graph_prefix}{i}{args.graph_ext}"

        # If your init_logical_graph does NOT accept seed, remove the seed=... argument.
        graph = init_logical_graph(
            args.lg_num_nodes,
            args.lg_degree
        )

        minorminer = convert_graph_to_embeddingMinorminer(graph, original_chimera_graph)
        minorminer_list.append(minorminer)

        # Save graph edge list
        nx.write_edgelist(graph, graph_path.as_posix(), data=False)

        print(f"[{i+1:>3}/{args.n_graphs}] wrote {graph_path}")

    # Pickle baseline results
    minorminer_path = out_dir / args.minorminer_filename
    with minorminer_path.open("wb") as f:
        pickle.dump(minorminer_list, f)

    print(f"\nSaved minorminer results to: {minorminer_path}")


if __name__ == "__main__":
    main()
