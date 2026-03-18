"""
compute_graph_properties.py
===========================
Scan all (or a selection of) graphs in test_graphs/, compute missing
structural properties, and write them back into each JSON file in-place.

Usage (as a function):
    from compute_graph_properties import compute_graph_properties
    compute_graph_properties(
        properties=['algebraic_connectivity', 'diameter'],
        graph_selection="1-60",
        overwrite=False,
    )

Usage (as a script):
    python compute_graph_properties.py
    python compute_graph_properties.py --properties algebraic_connectivity diameter
    python compute_graph_properties.py --selection "1-60" --overwrite

After running, regenerate the manifest:
    from qebench import generate_manifest; generate_manifest()
"""

import argparse
import itertools
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

import networkx as nx
import numpy as np
from networkx.algorithms.approximation import treewidth_min_degree

from qebench.graphs import TEST_GRAPHS_DIR, parse_graph_selection, load_graph


# ---------------------------------------------------------------------------
# All computable properties, in display order
# ---------------------------------------------------------------------------

ALL_PROPERTIES: List[str] = [
    'n_vertices',
    'n_edges',
    'density',
    'avg_degree',
    'max_degree',
    'min_degree',
    'degree_std',
    'avg_clustering',
    'global_clustering',
    'n_triangles',
    'algebraic_connectivity',
    'avg_shortest_path_length',
    'diameter',
    'girth',
    'is_planar',
    'is_bipartite',
    'is_connected',
    'is_regular',
    'n_connected_components',
    'largest_component_fraction',
    'degree_assortativity',
    'degeneracy',
    'treewidth_upper',
    'clique_number',
    'clique_lower_bound',
    # 'source_problem' is manual-only — not auto-computed
]

# Properties that require a connected graph
_REQUIRES_CONNECTED = {'algebraic_connectivity', 'avg_shortest_path_length', 'diameter'}

# Properties that are skipped for large dense graphs (intractable)
_CLIQUE_EXACT_MAX_N = 50
_CLIQUE_EXACT_MAX_DENSITY = 0.3

# Max cliques to enumerate for the lower-bound approximation
_CLIQUE_LOWER_BOUND_LIMIT = 2000


# ---------------------------------------------------------------------------
# Per-property computation
# ---------------------------------------------------------------------------

def _compute_property(name: str, G: nx.Graph) -> object:
    """Compute a single property on graph G. Returns the value or None.

    Raises exceptions on genuine failures (e.g. scipy not installed).
    Returning None is the expected result for inapplicable properties
    (e.g. diameter on a disconnected graph), not a failure.
    """
    n = G.number_of_nodes()
    m = G.number_of_edges()
    degrees = [d for _, d in G.degree()]

    if name == 'n_vertices':
        return n

    if name == 'n_edges':
        return m

    if name == 'density':
        return round(nx.density(G), 6)

    if name == 'avg_degree':
        return round(sum(degrees) / n, 6) if n else 0.0

    if name == 'max_degree':
        return int(max(degrees)) if degrees else 0

    if name == 'min_degree':
        return int(min(degrees)) if degrees else 0

    if name == 'degree_std':
        return round(float(np.std(degrees)), 6) if degrees else 0.0

    if name == 'avg_clustering':
        return round(nx.average_clustering(G), 6)

    if name == 'global_clustering':
        return round(nx.transitivity(G), 6)

    if name == 'n_triangles':
        return int(sum(nx.triangles(G).values()) // 3)

    if name == 'algebraic_connectivity':
        if not nx.is_connected(G):
            return None
        return round(float(nx.algebraic_connectivity(G)), 6)

    if name == 'avg_shortest_path_length':
        if not nx.is_connected(G):
            return None
        return round(nx.average_shortest_path_length(G), 6)

    if name == 'diameter':
        if not nx.is_connected(G):
            return None
        return int(nx.diameter(G))

    if name == 'girth':
        g = nx.girth(G)
        return None if math.isinf(g) else int(g)

    if name == 'is_planar':
        return bool(nx.check_planarity(G)[0])

    if name == 'is_bipartite':
        return bool(nx.is_bipartite(G))

    if name == 'is_connected':
        return bool(nx.is_connected(G))

    if name == 'is_regular':
        return bool(len(set(degrees)) <= 1)

    if name == 'n_connected_components':
        return int(nx.number_connected_components(G))

    if name == 'largest_component_fraction':
        if n == 0:
            return 0.0
        largest = max(len(c) for c in nx.connected_components(G))
        return round(largest / n, 6)

    if name == 'degree_assortativity':
        if m < 2:
            return None
        val = nx.degree_assortativity_coefficient(G)
        if val is None or math.isnan(val):
            return None
        return round(float(val), 6)

    if name == 'degeneracy':
        core_numbers = nx.core_number(G)
        return int(max(core_numbers.values())) if core_numbers else 0

    if name == 'treewidth_upper':
        if n == 0:
            return 0
        tw, _ = treewidth_min_degree(G)
        return int(tw)

    if name == 'clique_number':
        density = (2 * m / (n * (n - 1))) if n > 1 else 0.0
        if n > _CLIQUE_EXACT_MAX_N and density >= _CLIQUE_EXACT_MAX_DENSITY:
            return None  # intractable — skip
        if n == 0 or m == 0:
            return 1 if n > 0 else 0
        return int(max(len(c) for c in nx.find_cliques(G)))

    if name == 'clique_lower_bound':
        if n == 0 or m == 0:
            return 1 if n > 0 else 0
        best = 1
        for clique in itertools.islice(nx.find_cliques(G), _CLIQUE_LOWER_BOUND_LIMIT):
            if len(clique) > best:
                best = len(clique)
        return int(best)

    raise ValueError(f"Unknown property: {name!r}")


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def compute_graph_properties(
    properties: Optional[List[str]] = None,
    graph_selection: str = "*",
    overwrite: bool = False,
) -> None:
    """Compute and write graph properties to test_graphs/ JSON files in-place.

    Args:
        properties: List of property names to compute. None means all
                    properties in ALL_PROPERTIES.
        graph_selection: Standard graph selection string (e.g. "1-60", "*").
        overwrite: If True, recompute properties even if already present.
                   Default False — existing values are preserved.
    """
    if properties is None:
        requested: List[str] = list(ALL_PROPERTIES)
    else:
        unknown = set(properties) - set(ALL_PROPERTIES)
        if unknown:
            raise ValueError(
                f"Unknown properties: {sorted(unknown)}\n"
                f"Available: {ALL_PROPERTIES}"
            )
        requested = list(properties)

    if not TEST_GRAPHS_DIR.exists():
        print(f"test_graphs/ not found at {TEST_GRAPHS_DIR}")
        return

    # Collect matching graph files
    selected_ids = parse_graph_selection(graph_selection)
    is_wildcard = -1 in selected_ids

    graph_files: List[Path] = []
    for json_file in sorted(TEST_GRAPHS_DIR.rglob("*.json")):
        if json_file.name.startswith("REGISTRY"):
            continue
        stem = json_file.stem
        prefix = stem.split('_', 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            continue
        if not is_wildcard and gid not in selected_ids:
            continue
        graph_files.append(json_file)

    total = len(graph_files)
    if total == 0:
        print(f"No graphs matched selection '{graph_selection}'.")
        return

    n_computed = 0
    n_skipped = 0
    failures: List[str] = []      # "graph_id / property: error message"
    _batch_start = time.perf_counter()
    computed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    for file_idx, json_file in enumerate(graph_files, 1):
        # Load raw JSON (preserve all existing keys)
        with open(json_file) as f:
            data = json.load(f)

        gid = data.get('id', 0)
        name = data.get('name', json_file.stem)
        existing_props: Dict = data.get('properties', {})

        # Determine which properties actually need computing
        to_compute = [
            p for p in requested
            if overwrite or p not in existing_props
        ]

        if not to_compute:
            n_skipped += 1
            print(f"[{file_idx:3d}/{total}]  graph_{gid:<4d}  {name:<35s}"
                  f"  (all requested properties already present, skipped)")
            continue

        # Load the NetworkX graph object (only if we have work to do)
        try:
            _, _, G, _ = load_graph(json_file)
        except Exception as e:
            failures.append(f"graph_{gid} / (load): {e}")
            print(f"[{file_idx:3d}/{total}]  graph_{gid:<4d}  {name:<35s}"
                  f"  ERROR loading graph: {e}")
            continue

        # Compute each property, catching failures individually
        new_values: Dict = {}
        prop_failures: List[str] = []
        for prop in to_compute:
            try:
                val = _compute_property(prop, G)
                new_values[prop] = val
            except Exception as e:
                prop_failures.append(f"graph_{gid} / {prop}: {e}")

        if prop_failures:
            # Do not write a partial result — skip the whole file
            failures.extend(prop_failures)
            for msg in prop_failures:
                print(f"  ✗ {msg}")
            print(f"[{file_idx:3d}/{total}]  graph_{gid:<4d}  {name:<35s}"
                  f"  ERROR — file not written (see above)")
            continue

        # Merge into existing properties, update timestamp
        existing_props.update(new_values)
        existing_props['computed_at'] = computed_at

        # Initialise source_problem to null if it has never been set
        if 'source_problem' not in existing_props:
            existing_props['source_problem'] = None

        data['properties'] = existing_props

        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)

        n_computed += 1

        # Build a compact display string for newly computed values
        display_parts = []
        for p, v in new_values.items():
            if isinstance(v, float):
                display_parts.append(f"{p}={v:.4g}")
            else:
                display_parts.append(f"{p}={v}")
        display = "  ".join(display_parts) if display_parts else ""
        print(f"[{file_idx:3d}/{total}]  graph_{gid:<4d}  {name:<35s}  {display}")

    # Final summary
    elapsed = time.perf_counter() - _batch_start
    m, s = divmod(int(elapsed), 60)
    h, m = divmod(m, 60)
    time_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s" if m else f"{s}s"

    print()
    if failures:
        print(f"Failures ({len(failures)}):")
        for msg in failures:
            print(f"  ✗ {msg}")
        print()

    print(f"Computed properties for {n_computed} / {total} graphs "
          f"({n_skipped} skipped — already present).")
    print(f"Total time: {time_str}")
    print()
    print("⚠️  REMEMBER TO UPDATE GRAPH HASH MANIFEST")
    print("   from qebench import generate_manifest; generate_manifest()")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute structural properties for test graphs."
    )
    parser.add_argument(
        "--properties", "-p",
        nargs="+",
        metavar="PROP",
        default=None,
        help=f"Properties to compute (default: all). Available: {', '.join(ALL_PROPERTIES)}",
    )
    parser.add_argument(
        "--selection", "-s",
        default="*",
        metavar="SELECTION",
        help='Graph selection string, e.g. "1-60" or "*" (default: "*").',
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Recompute properties even if already present in the file.",
    )
    args = parser.parse_args()
    compute_graph_properties(
        properties=args.properties,
        graph_selection=args.selection,
        overwrite=args.overwrite,
    )
