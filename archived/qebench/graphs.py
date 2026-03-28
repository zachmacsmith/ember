"""
Test Graph Generator, Loader, and Selection System

Pre-generates a standard library of test graphs with numeric IDs.
Graphs are stored as JSON in test_graphs/<category>/<name>.json.

ID Scheme (clean category boundaries):
    001-010  Complete graphs (K4, K5, K6, ..., K15)
    011-020  Bipartite graphs (K_{m,n})
    021-030  Grid graphs (2×2 through 5×5)
    031-040  Cycle graphs (C5, C8, ..., C30)
    041-050  Tree graphs (balanced trees)
    051-060  Special graphs (Petersen, dodecahedral, icosahedral)
    061-099  Reserved for future structured types
    100-199  Random / Erdős–Rényi graphs

Selection — by ID string or preset name:
    "1-100"           → IDs 1 through 100
    "1-10, 30-50"     → IDs 1-10 and 30-50
    "51, 52, 53"      → just those three IDs
    "1-100, !50"      → IDs 1-100 except 50
    "1-100 & !41-50"  → IDs 1-100 except 41-50
    "*"               → all graphs
    "quick"           → preset (defined in test_graphs/presets.csv)
    "diverse"         → preset

Usage:
    python generate_test_graphs.py          # generate standard library
    python generate_test_graphs.py --list   # list all graphs with IDs

    from qebench.graphs import load_test_graphs, parse_graph_selection
    problems = load_test_graphs("quick")           # use a preset
    problems = load_test_graphs("1-10, 51-60")     # complete + special
    problems = load_test_graphs("*")               # everything
"""

import hashlib
import json
import networkx as nx
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

TEST_GRAPHS_DIR = Path(__file__).parent.parent / "test_graphs"
PRESETS_FILE = TEST_GRAPHS_DIR / "presets.csv"


# ==============================================================================
# SELECTION PARSER
# ==============================================================================

def load_presets() -> Dict[str, str]:
    """Load named presets from test_graphs/presets.csv.
    
    Format: first comma separates name from selection string.
    Everything after the first comma is the selection (commas included).
    
    Returns:
        Dict mapping preset name → selection string.
    """
    presets = {}
    if PRESETS_FILE.exists():
        with open(PRESETS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('name'):  # skip header/empty
                    continue
                name, selection = line.split(',', 1)  # split on FIRST comma only
                presets[name.strip()] = selection.strip()
    return presets


def list_presets() -> Dict[str, str]:
    """Return dict of preset_name → selection_string."""
    return load_presets()


def parse_graph_selection(spec: str) -> Set[int]:
    """Parse a graph selection string or preset name into a set of integer IDs.
    
    Syntax:
        "5"          → {5}
        "1-10"       → {1, 2, ..., 10}
        "1-10, 20"   → {1, 2, ..., 10, 20}
        "!5"         → exclude 5 (applied after includes)
        "!5-10"      → exclude 5 through 10
        "*"          → all available IDs (resolved at load time)
        "quick"      → resolved from test_graphs/presets.csv
        
    Separators: comma ',' and ampersand '&' both work.
    Exclusions (prefixed with '!') are applied after all includes.
    If spec matches a preset name, the preset's selection string is used.
    
    Returns:
        Set of selected graph IDs. Returns {-1} for wildcard "*".
    """
    spec = spec.strip()
    
    # Check if it's a preset name
    presets = load_presets()
    if spec in presets:
        spec = presets[spec]
    
    if spec == "*":
        return {-1}  # sentinel for "all"
    
    # Split on commas and ampersands
    tokens = []
    for part in spec.replace('&', ',').split(','):
        part = part.strip()
        if part:
            tokens.append(part)
    
    includes = set()
    excludes = set()
    
    for token in tokens:
        is_exclude = token.startswith('!')
        if is_exclude:
            token = token[1:].strip()
        
        if '-' in token:
            parts = token.split('-', 1)
            try:
                start, end = int(parts[0].strip()), int(parts[1].strip())
                id_set = set(range(start, end + 1))
            except ValueError:
                raise ValueError(f"Invalid range: '{token}'")
        else:
            try:
                id_set = {int(token)}
            except ValueError:
                raise ValueError(f"Invalid ID or unknown preset: '{token}'")
        
        if is_exclude:
            excludes.update(id_set)
        else:
            includes.update(id_set)
    
    return includes - excludes


# ==============================================================================
# SAVE / LOAD
# ==============================================================================

def save_graph(graph: nx.Graph, graph_id: int, name: str, category: str,
               metadata: Optional[Dict] = None):
    """Save a graph to test_graphs/<category>/<name>.json with a numeric ID."""
    category_dir = TEST_GRAPHS_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)

    n = graph.number_of_nodes()
    # Normalize edge key to 'edges' regardless of NetworkX version.
    # NetworkX < 3.3 uses 'links'; >= 3.3 uses 'edges'. Storing as 'edges'
    # ensures load_graph() can always detect the correct key.
    graph_data = nx.node_link_data(graph)
    if 'links' in graph_data:
        graph_data['edges'] = graph_data.pop('links')
    data = {
        'id': graph_id,
        'name': name,
        'category': category,
        'num_nodes': n,
        'num_edges': graph.number_of_edges(),
        'density': round(2 * graph.number_of_edges() / (n * (n - 1)) if n > 1 else 0, 4),
        'metadata': metadata or {},
        'graph': graph_data
    }
    
    filepath = category_dir / f"{graph_id:03d}_{name}.json"
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

    return filepath


def load_graph(filepath: Path) -> Tuple[int, str, nx.Graph, Dict]:
    """Load a single graph from JSON. Returns (id, name, graph, metadata)."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    graph_data = data['graph']
    # NetworkX < 3.3 stores edges under 'links'; >= 3.3 uses 'edges'.
    # Detect the key present in the file rather than relying on the
    # version-dependent default, so saved files work across all versions.
    edges_key = 'edges' if 'edges' in graph_data else 'links'
    graph = nx.node_link_graph(graph_data, edges=edges_key)
    return data.get('id', 0), data['name'], graph, data.get('metadata', {})


def load_test_graphs(selection: str = "*",
                     max_nodes: Optional[int] = None,
                     min_nodes: Optional[int] = None) -> List[Tuple[str, nx.Graph]]:
    """Load pre-generated test graphs by selection string.
    
    Args:
        selection: Graph selection string (e.g., "1-10", "1-60, !35", "*").
        max_nodes: Only include graphs with at most this many nodes.
        min_nodes: Only include graphs with at least this many nodes.
    
    Returns:
        List of (name, graph) tuples sorted by ID, ready for run_full_benchmark().
    """
    if not TEST_GRAPHS_DIR.exists():
        print("⚠️  No test graphs found. Run: python generate_test_graphs.py")
        return []
    
    selected_ids = parse_graph_selection(selection)
    is_wildcard = -1 in selected_ids

    results = []
    loaded_files: List[Tuple[int, Path]] = []

    for json_file in sorted(TEST_GRAPHS_DIR.rglob("*.json")):
        # Skip non-graph files
        if json_file.name.startswith("REGISTRY"):
            continue

        # Extract graph ID from filename prefix (e.g. "001_K4.json" → 1).
        # Files that don't follow the {id}_{name}.json scheme are skipped so
        # that stray JSON files in the directory never cause a crash.
        stem = json_file.stem
        prefix = stem.split('_', 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            continue

        if not is_wildcard and gid not in selected_ids:
            continue  # skip without opening the file

        gid, name, graph, meta = load_graph(json_file)

        n = graph.number_of_nodes()
        if max_nodes and n > max_nodes:
            continue
        if min_nodes and n < min_nodes:
            continue

        results.append((gid, name, graph))
        loaded_files.append((gid, json_file))

    # Verify integrity of only the loaded graphs. Raises RuntimeError if any
    # file has been modified since the manifest was generated — propagates up
    # through run_full_benchmark() and cancels the run before any trials start.
    if loaded_files and MANIFEST_PATH.exists():
        verify_manifest(files=loaded_files)

    results.sort(key=lambda x: x[0])
    return [(name, graph) for _, name, graph in results]


def list_test_graphs() -> List[Dict]:
    """List all available test graphs with their IDs."""
    catalog = []
    
    if not TEST_GRAPHS_DIR.exists():
        return catalog
    
    for json_file in sorted(TEST_GRAPHS_DIR.rglob("*.json")):
        if json_file.name == "REGISTRY.md":
            continue
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            catalog.append({
                'id': data.get('id', 0),
                'name': data['name'],
                'category': data['category'],
                'nodes': data['num_nodes'],
                'edges': data['num_edges'],
                'density': round(data['density'], 3),
            })
        except Exception:
            pass
    
    catalog.sort(key=lambda x: x['id'])
    return catalog


# ==============================================================================
# GRAPH GENERATORS
# ==============================================================================

def generate_complete_graphs():
    """IDs 001-010: Complete graphs K_n."""
    configs = [(1, 4), (2, 5), (3, 6), (4, 8), (5, 10), (6, 12), (7, 15)]
    graphs = []
    for gid, n in configs:
        G = nx.complete_graph(n)
        name = f"K{n}"
        save_graph(G, gid, name, "complete", {'type': 'complete', 'n': n})
        graphs.append((name, G))
    return graphs


def generate_bipartite_graphs():
    """IDs 011-020: Complete bipartite graphs K_{m,n}."""
    configs = [(11, 2, 3), (12, 3, 3), (13, 3, 4), (14, 4, 4), (15, 4, 6), (16, 5, 5)]
    graphs = []
    for gid, m, n in configs:
        G = nx.complete_bipartite_graph(m, n)
        name = f"bipartite_K{m}_{n}"
        save_graph(G, gid, name, "bipartite", {'type': 'complete_bipartite', 'm': m, 'n': n})
        graphs.append((name, G))
    return graphs


def generate_grid_graphs():
    """IDs 021-030: 2D grid graphs."""
    configs = [(21, 2, 2), (22, 3, 3), (23, 3, 4), (24, 4, 4), (25, 4, 6), (26, 5, 5)]
    graphs = []
    for gid, m, n in configs:
        G = nx.convert_node_labels_to_integers(nx.grid_2d_graph(m, n))
        name = f"grid_{m}x{n}"
        save_graph(G, gid, name, "grid", {'type': 'grid', 'm': m, 'n': n})
        graphs.append((name, G))
    return graphs


def generate_cycle_graphs():
    """IDs 031-040: Cycle graphs."""
    configs = [(31, 5), (32, 8), (33, 10), (34, 15), (35, 20), (36, 30)]
    graphs = []
    for gid, n in configs:
        G = nx.cycle_graph(n)
        name = f"cycle_{n}"
        save_graph(G, gid, name, "cycle", {'type': 'cycle', 'n': n})
        graphs.append((name, G))
    return graphs


def generate_tree_graphs():
    """IDs 041-050: Balanced tree graphs."""
    configs = [(41, 2, 3), (42, 2, 4), (43, 2, 5), (44, 3, 3), (45, 3, 4)]
    graphs = []
    for gid, r, h in configs:
        G = nx.balanced_tree(r, h)
        name = f"tree_r{r}_d{h}"
        save_graph(G, gid, name, "tree", {'type': 'balanced_tree', 'branching': r, 'depth': h})
        graphs.append((name, G))
    return graphs


def generate_special_graphs():
    """IDs 051-060: Classic named graphs."""
    graphs = []
    
    G = nx.petersen_graph()
    save_graph(G, 51, "petersen", "special", {'type': 'petersen'})
    graphs.append(("petersen", G))
    
    G = nx.dodecahedral_graph()
    save_graph(G, 52, "dodecahedral", "special", {'type': 'dodecahedral'})
    graphs.append(("dodecahedral", G))
    
    G = nx.icosahedral_graph()
    save_graph(G, 53, "icosahedral", "special", {'type': 'icosahedral'})
    graphs.append(("icosahedral", G))
    
    return graphs


def generate_random_graphs(sizes=None, densities=None, instances=3):
    """IDs 100-199: Erdős–Rényi random graphs."""
    sizes = sizes or [6, 8, 10, 15, 20]
    densities = densities or [0.2, 0.3, 0.5, 0.7]
    
    graphs = []
    gid = 100
    
    for n in sizes:
        for d in densities:
            for i in range(instances):
                seed = n * 1000 + int(d * 100) + i
                G = nx.gnp_random_graph(n, d, seed=seed)
                if G.number_of_edges() == 0:
                    gid += 1
                    continue
                name = f"random_n{n}_d{d:.1f}_i{i}"
                save_graph(G, gid, name, "random", {
                    'type': 'erdos_renyi', 'n': n, 'density': d,
                    'instance': i, 'seed': seed
                })
                graphs.append((name, G))
                gid += 1
    
    return graphs


def _generate_registry_doc(catalog: List[Dict]):
    """Generate test_graphs/REGISTRY.md from the catalog."""
    lines = []
    lines.append("# Test Graph Registry\n")
    lines.append("## Selection Syntax\n")
    lines.append("Use a selection string to choose which graphs to benchmark:\n")
    lines.append("| Expression | Meaning |")
    lines.append("|------------|---------|")
    lines.append('| `"*"` | All graphs |')
    lines.append('| `"1-10"` | IDs 1 through 10 (complete graphs) |')
    lines.append('| `"1-10, 51-60"` | Complete + special graphs |')
    lines.append('| `"1-60"` | All structured graphs (no random) |')
    lines.append('| `"1-60, !5"` | All structured except graph 5 (K10) |')
    lines.append('| `"100-199"` | All random graphs |')
    lines.append('| `"1-199 & !100-199"` | Same as `"1-60"` — `&` and `,` are interchangeable |')
    lines.append('| `"51, 52"` | Just Petersen and dodecahedral |')
    lines.append("")
    lines.append("```python")
    lines.append('from qebench.graphs import load_test_graphs')
    lines.append('problems = load_test_graphs("1-10, 51-60")  # complete + special')
    lines.append("```\n")
    
    lines.append("## Graph Registry\n")
    
    current_cat = None
    cat_labels = {
        'complete': '001–010: Complete Graphs',
        'bipartite': '011–020: Bipartite Graphs',
        'grid': '021–030: Grid Graphs',
        'cycle': '031–040: Cycle Graphs',
        'tree': '041–050: Tree Graphs',
        'special': '051–060: Special Graphs',
        'random': '100–199: Random (Erdős–Rényi) Graphs',
    }
    
    for entry in catalog:
        cat = entry['category']
        if cat != current_cat:
            current_cat = cat
            label = cat_labels.get(cat, cat)
            lines.append(f"### {label}\n")
            lines.append("| ID | Name | Nodes | Edges | Density |")
            lines.append("|----|------|-------|-------|---------|")
        
        lines.append(f"| {entry['id']:3d} | {entry['name']} | {entry['nodes']} | {entry['edges']} | {entry['density']:.3f} |")
    
    lines.append("")
    
    doc_path = TEST_GRAPHS_DIR / "REGISTRY.md"
    with open(doc_path, 'w') as f:
        f.write('\n'.join(lines))
    
    return doc_path


# ==============================================================================
# MANIFEST
# ==============================================================================

MANIFEST_PATH = TEST_GRAPHS_DIR / "manifest.sha256"


def generate_manifest(graph_dir: Path = TEST_GRAPHS_DIR,
                      manifest_path: Path = MANIFEST_PATH) -> Path:
    """Compute SHA-256 hashes for every graph JSON and write manifest file.

    Format — graph ID (integer) followed by two spaces and the hash:
        1  a3f2b8c9...
        11  7b1c3d5e...

    Only files following the {id}_{name}.json naming scheme are included.
    The ID is parsed from the filename prefix so the manifest remains valid
    even if files are moved to a different subdirectory.

    Returns:
        Path to the written manifest file.
    """
    entries = []
    for json_file in sorted(graph_dir.rglob("*.json")):
        stem = json_file.stem
        prefix = stem.split('_', 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            continue
        digest = hashlib.sha256(json_file.read_bytes()).hexdigest()
        entries.append((gid, digest))

    entries.sort(key=lambda x: x[0])
    manifest_path.write_text(
        "\n".join(f"{gid}  {digest}" for gid, digest in entries) + "\n"
    )
    return manifest_path


def verify_manifest(graph_dir: Path = TEST_GRAPHS_DIR,
                    manifest_path: Path = MANIFEST_PATH,
                    files: Optional[List[Tuple[int, Path]]] = None) -> None:
    """Verify graph files match their recorded SHA-256 hashes.

    The manifest is keyed by integer graph ID, so files can be moved between
    subdirectories without triggering a false integrity failure.

    Args:
        graph_dir:     Root directory containing graph JSON files (used only
                       when files=None for a full scan).
        manifest_path: Path to the manifest file.
        files:         If provided, only verify these (graph_id, path) pairs.
                       Files whose ID is absent from the manifest are silently
                       skipped (new additions are allowed).
                       If None, verify all files found under graph_dir.

    Raises:
        FileNotFoundError: if manifest does not exist.
        RuntimeError: if any checked file is missing or its hash does not match.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Graph manifest not found: {manifest_path}\n"
            "Run: python -m qebench.graphs  (or generate_all()) to regenerate it."
        )

    # Parse manifest into {graph_id: hash}
    manifest: Dict[int, str] = {}
    with open(manifest_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("  ", 1)
            if len(parts) == 2:
                try:
                    manifest[int(parts[0])] = parts[1]
                except ValueError:
                    pass  # skip malformed lines

    # Determine which (gid, path) pairs to check
    if files is not None:
        targets: List[Tuple[int, Path]] = files
    else:
        # Full scan: extract IDs from filenames
        targets = []
        for json_file in sorted(graph_dir.rglob("*.json")):
            stem = json_file.stem
            prefix = stem.split('_', 1)[0]
            try:
                gid = int(prefix)
            except ValueError:
                continue
            targets.append((gid, json_file))

    for gid, target in targets:
        if not target.exists():
            raise RuntimeError(f"Graph file missing: {target}")
        if gid not in manifest:
            continue  # new graph not yet in manifest — allowed, skip check
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != manifest[gid]:
            raise RuntimeError(
                f"Graph integrity check failed: {target.name} (id={gid})\n"
                f"  expected: {manifest[gid]}\n"
                f"  actual:   {actual}\n"
                "The file has been modified. Re-run the graph generator to rebuild the manifest."
            )


def generate_all(sizes=None, densities=None, instances=3):
    """Generate the full standard test graph library and REGISTRY.md."""
    print("Generating test graph library...")
    
    all_graphs = []
    
    generators = [
        ("Complete graphs (001-010)", generate_complete_graphs),
        ("Bipartite graphs (011-020)", generate_bipartite_graphs),
        ("Grid graphs (021-030)", generate_grid_graphs),
        ("Cycle graphs (031-040)", generate_cycle_graphs),
        ("Tree graphs (041-050)", generate_tree_graphs),
        ("Special graphs (051-060)", generate_special_graphs),
    ]
    
    for label, gen_func in generators:
        print(f"  {label}...", end=" ")
        graphs = gen_func()
        print(f"{len(graphs)} graphs")
        all_graphs.extend(graphs)
    
    print("  Random graphs (100-199)...", end=" ")
    graphs = generate_random_graphs(sizes=sizes, densities=densities, instances=instances)
    print(f"{len(graphs)} graphs")
    all_graphs.extend(graphs)
    
    # Generate registry doc and manifest
    catalog = list_test_graphs()
    doc_path = _generate_registry_doc(catalog)
    manifest_path = generate_manifest()

    print(f"\n✓ Generated {len(all_graphs)} graphs in {TEST_GRAPHS_DIR}/")
    print(f"✓ Registry: {doc_path}")
    print(f"✓ Manifest: {manifest_path}")
    return all_graphs


# ==============================================================================
# CLI
# ==============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate test graph library')
    parser.add_argument('--sizes', nargs='+', type=int,
                       help='Node sizes for random graphs')
    parser.add_argument('--densities', nargs='+', type=float,
                       help='Densities for random graphs')
    parser.add_argument('--instances', type=int, default=3,
                       help='Random instances per config')
    parser.add_argument('--list', action='store_true',
                       help='List existing test graphs')
    
    args = parser.parse_args()
    
    if args.list:
        catalog = list_test_graphs()
        if not catalog:
            print("No test graphs found. Run without --list to generate.")
        else:
            current_cat = None
            total = 0
            for entry in catalog:
                if entry['category'] != current_cat:
                    current_cat = entry['category']
                    print(f"\n{current_cat}/")
                print(f"  [{entry['id']:3d}] {entry['name']:30s}  "
                      f"n={entry['nodes']:3d}  e={entry['edges']:3d}  d={entry['density']:.3f}")
                total += 1
            print(f"\nTotal: {total} graphs")
    else:
        generate_all(sizes=args.sizes, densities=args.densities,
                     instances=args.instances)
