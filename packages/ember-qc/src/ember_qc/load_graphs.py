"""
ember_qc/load_graphs.py
=======================
Graph library loader and selection system.

Graphs are stored as JSON in the bundled data directory:
  ember_qc/graphs/library/<category>/<id>_<name>.json

The authoritative graph list is described by:
  ember_qc/graphs/manifest.json

Three-layer lookup (load_graph):
  Layer 1 — local user cache (~/.local/share/ember-qc/graphs/)
  Layer 2 — bundled files (shipped with the package)
  Layer 3 — remote download (NotImplementedError stub; Phase 2)

Selection — by ID string or preset name:
    "1-100"           → IDs 1 through 100
    "1-10, 30-50"     → IDs 1-10 and 30-50
    "51, 52, 53"      → just those three IDs
    "1-100, !50"      → IDs 1-100 except 50
    "1-100 & !41-50"  → IDs 1-100 except 41-50
    "*"               → all graphs
    "quick"           → preset (defined in graphs/presets.csv)
    "diverse"         → preset

Public API:
    load_graph(graph_id)                              -> nx.Graph
    load_test_graphs(selection, max_nodes, min_nodes) -> List[(name, graph)]
    list_test_graphs()                                -> List[Dict]
    parse_graph_selection(spec)                       -> Set[int]
    load_presets()                                    -> Dict[str, str]
    list_presets()                                    -> Dict[str, str]
    load_manifest()                                   -> Dict
    generate_manifest(graph_dir, manifest_path)       -> Path  [authoring tool]
"""

import hashlib
import json
import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_GRAPHS_PKG_DIR  = Path(__file__).parent / "graphs"
GRAPHS_DIR       = _GRAPHS_PKG_DIR / "library"
PRESETS_FILE     = _GRAPHS_PKG_DIR / "presets.csv"
MANIFEST_PATH    = _GRAPHS_PKG_DIR / "manifest.json"

# Legacy hash-only manifest kept for backward compatibility
_LEGACY_MANIFEST = _GRAPHS_PKG_DIR / "manifest.sha256"


# ==============================================================================
# MANIFEST
# ==============================================================================

def load_manifest() -> Dict:
    """Load and return the bundled manifest.json.

    Returns a dict with keys:
        version (str)
        graphs  (list of dicts: id, type, parameters, nodes, edges,
                 difficulty, hash, url, size_bytes)

    Raises:
        FileNotFoundError: if manifest.json is not found in the package.
    """
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Graph manifest not found: {MANIFEST_PATH}\n"
            "Re-install the package to restore the bundled manifest."
        )
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _manifest_by_id() -> Dict[int, Dict]:
    """Return manifest entries keyed by graph ID."""
    manifest = load_manifest()
    return {entry["id"]: entry for entry in manifest.get("graphs", [])}


def verify_manifest(files: Optional[List[Tuple[int, Path]]] = None,
                    graph_dir: Path = GRAPHS_DIR) -> None:
    """Verify graph files match their SHA-256 hashes recorded in manifest.json.

    Args:
        files:     List of (graph_id, Path) pairs to check. If None, every
                   graph file in graph_dir is checked.
        graph_dir: Directory to scan when files is None.

    Raises:
        FileNotFoundError: if manifest.json does not exist.
        RuntimeError:      if any checked file is missing or its hash does not
                           match — indicates a corrupt install.
    """
    manifest = _manifest_by_id()

    if files is None:
        targets: List[Tuple[int, Path]] = []
        for json_file in sorted(graph_dir.rglob("*.json")):
            prefix = json_file.stem.split("_", 1)[0]
            try:
                targets.append((int(prefix), json_file))
            except ValueError:
                continue
    else:
        targets = files

    for gid, target in targets:
        if gid not in manifest:
            continue  # new graph not yet in manifest — silently skip
        if not target.exists():
            raise RuntimeError(f"Graph file missing: {target}")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != manifest[gid]["hash"]:
            raise RuntimeError(
                f"Graph integrity check failed: {target.name} (id={gid})\n"
                f"  expected: {manifest[gid]['hash']}\n"
                f"  actual:   {actual}\n"
                "The file has been modified. Re-install the package to restore it."
            )


# ==============================================================================
# LOCAL INDEX (user cache)
# ==============================================================================

def _load_local_index() -> Dict[str, Dict]:
    """Load local_index.json from the user graphs cache dir.

    Returns {} if the file does not exist or is malformed.
    Keys are string graph IDs (JSON object keys are always strings).
    """
    try:
        from ember_qc._paths import get_user_graphs_dir
        index_path = get_user_graphs_dir() / "local_index.json"
        if not index_path.exists():
            return {}
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_local_index(index: Dict[str, Dict]) -> None:
    """Write index back to local_index.json."""
    from ember_qc._paths import get_user_graphs_dir
    index_path = get_user_graphs_dir() / "local_index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


# ==============================================================================
# CORE LOADER
# ==============================================================================

def _load_graph_file(filepath: Path) -> Tuple[int, str, nx.Graph, Dict]:
    """Load a single graph JSON file. Returns (id, name, graph, metadata)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph_data = data["graph"]
    edges_key  = "edges" if "edges" in graph_data else "links"
    graph      = nx.node_link_graph(graph_data, edges=edges_key)
    return data.get("id", 0), data["name"], graph, data.get("metadata", {})


def load_graph(graph_id: int) -> nx.Graph:
    """Load a graph by its integer ID using a three-layer lookup.

    Layer 1 — Local cache
        Check ~/.local/share/ember-qc/graphs/ for a cached copy.
        If found, verify SHA-256 against local_index.json.
        On hash mismatch the entry is invalidated and lookup continues.

    Layer 2 — Bundled files
        Search the package library directory for a file whose numeric
        prefix matches graph_id. If found, return the graph.

    Layer 3 — Remote download (stub)
        Not yet implemented. Raises NotImplementedError with instructions.

    Args:
        graph_id: Integer graph ID as recorded in manifest.json.

    Returns:
        A NetworkX Graph object.

    Raises:
        KeyError:            if graph_id is not in the manifest.
        NotImplementedError: if the graph is not bundled and no cache exists
                             (remote download not yet implemented).
        RuntimeError:        if a bundled file is missing or corrupt.
    """
    manifest = _manifest_by_id()

    if graph_id not in manifest:
        raise KeyError(
            f"Graph ID {graph_id} not found in manifest. "
            f"Available IDs: run 'ember graphs list' to see all graphs."
        )

    entry = manifest[graph_id]
    expected_hash = entry["hash"]

    # ------------------------------------------------------------------
    # Layer 1: local user cache
    # ------------------------------------------------------------------
    try:
        from ember_qc._paths import get_user_graphs_dir
        cache_dir  = get_user_graphs_dir()
        cache_file = cache_dir / f"{graph_id:03d}.json"

        if cache_file.exists():
            index = _load_local_index()
            idx_entry = index.get(str(graph_id))

            actual_hash = hashlib.sha256(cache_file.read_bytes()).hexdigest()

            if idx_entry and actual_hash == idx_entry.get("hash"):
                _, _, graph, _ = _load_graph_file(cache_file)
                return graph
            else:
                # Hash mismatch or not in index — invalidate and fall through
                if str(graph_id) in index:
                    del index[str(graph_id)]
                    _save_local_index(index)
    except Exception:
        pass  # Cache unavailable — continue to bundled layer

    # ------------------------------------------------------------------
    # Layer 2: bundled files
    # ------------------------------------------------------------------
    if GRAPHS_DIR.exists():
        for candidate in sorted(GRAPHS_DIR.rglob("*.json")):
            prefix = candidate.stem.split("_", 1)[0]
            try:
                if int(prefix) == graph_id:
                    actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
                    if actual_hash != expected_hash:
                        raise RuntimeError(
                            f"Bundled graph {candidate.name} (id={graph_id}) "
                            f"failed integrity check.\n"
                            f"  expected: {expected_hash}\n"
                            f"  actual:   {actual_hash}\n"
                            "The package installation may be corrupt. "
                            "Try: pip install --force-reinstall ember-qc"
                        )
                    _, _, graph, _ = _load_graph_file(candidate)
                    return graph
            except ValueError:
                continue

    # ------------------------------------------------------------------
    # Layer 3: remote download (stub)
    # ------------------------------------------------------------------
    raise NotImplementedError(
        f"Graph {graph_id} is not available locally and remote download "
        "is not yet implemented.\n"
        "This will be resolved in a future version of ember-qc.\n"
        f"  Remote URL recorded in manifest: {entry.get('url')}"
    )


# ==============================================================================
# PRESETS
# ==============================================================================

def load_presets() -> Dict[str, str]:
    """Load named presets from graphs/presets.csv.

    Format: first comma separates name from selection string.

    Returns:
        Dict mapping preset name → selection string.
    """
    presets = {}
    if PRESETS_FILE.exists():
        with open(PRESETS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("name"):
                    continue
                name, selection = line.split(",", 1)
                presets[name.strip()] = selection.strip()
    return presets


def list_presets() -> Dict[str, str]:
    """Return dict of preset_name → selection_string."""
    return load_presets()


# ==============================================================================
# SELECTION PARSER
# ==============================================================================

def parse_graph_selection(spec: str) -> Set[int]:
    """Parse a graph selection string or preset name into a set of integer IDs.

    Syntax:
        "5"          → {5}
        "1-10"       → {1, 2, ..., 10}
        "1-10, 20"   → {1, 2, ..., 10, 20}
        "!5"         → exclude 5 (applied after includes)
        "!5-10"      → exclude 5 through 10
        "*"          → all available IDs (sentinel {-1})
        "quick"      → resolved from graphs/presets.csv

    Returns:
        Set of selected graph IDs. Returns {-1} for wildcard "*".
    """
    spec = spec.strip()

    presets = load_presets()
    if spec in presets:
        spec = presets[spec]

    if spec == "*":
        return {-1}

    tokens = []
    for part in spec.replace("&", ",").split(","):
        part = part.strip()
        if part:
            tokens.append(part)

    includes: Set[int] = set()
    excludes: Set[int] = set()

    for token in tokens:
        is_exclude = token.startswith("!")
        if is_exclude:
            token = token[1:].strip()

        if "-" in token:
            parts = token.split("-", 1)
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
# BULK LOAD (used by benchmark runner)
# ==============================================================================

def load_test_graphs(selection: str = "*",
                     max_nodes: Optional[int] = None,
                     min_nodes: Optional[int] = None) -> List[Tuple[str, nx.Graph]]:
    """Load bundled test graphs by selection string.

    Args:
        selection: Graph selection string (e.g., "1-10", "1-60, !35", "*").
        max_nodes: Only include graphs with at most this many nodes.
        min_nodes: Only include graphs with at least this many nodes.

    Returns:
        List of (name, graph) tuples sorted by ID.
    """
    if not GRAPHS_DIR.exists():
        print("No test graphs found in package data directory.")
        return []

    selected_ids = parse_graph_selection(selection)
    is_wildcard  = -1 in selected_ids

    results    = []
    loaded_files: List[Tuple[int, Path]] = []

    for json_file in sorted(GRAPHS_DIR.rglob("*.json")):
        if json_file.name.startswith("REGISTRY"):
            continue

        prefix = json_file.stem.split("_", 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            continue

        if not is_wildcard and gid not in selected_ids:
            continue

        gid, name, graph, _ = _load_graph_file(json_file)

        n = graph.number_of_nodes()
        if max_nodes and n > max_nodes:
            continue
        if min_nodes and n < min_nodes:
            continue

        results.append((gid, name, graph))
        loaded_files.append((gid, json_file))

    if loaded_files and MANIFEST_PATH.exists():
        verify_manifest(files=loaded_files)

    results.sort(key=lambda x: x[0])
    return [(name, graph) for _, name, graph in results]


def list_test_graphs() -> List[Dict]:
    """List all available test graphs with their IDs and metadata."""
    catalog = []

    if not GRAPHS_DIR.exists():
        return catalog

    for json_file in sorted(GRAPHS_DIR.rglob("*.json")):
        if json_file.name.startswith("REGISTRY"):
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            prefix = json_file.stem.split("_", 1)[0]
            try:
                int(prefix)
            except ValueError:
                continue
            catalog.append({
                "id":       data.get("id", 0),
                "name":     data["name"],
                "category": data["category"],
                "nodes":    data["num_nodes"],
                "edges":    data["num_edges"],
                "density":  round(data["density"], 3),
            })
        except Exception:
            pass

    catalog.sort(key=lambda x: x["id"])
    return catalog


