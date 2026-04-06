"""
ember_qc/load_graphs.py
=======================
Graph library loader and selection system.

Graphs are stored as JSON in the bundled data directory:
  ember_qc/graphs/library/{id}_{name}.json

The authoritative graph list is described by:
  ember_qc/graphs/manifest.json

Three-layer lookup (load_graph):
  Layer 1 — local user cache (~/.local/share/ember-qc/graphs/)
  Layer 2 — bundled files (shipped with the package)
  Layer 3 — remote download from HuggingFace (zachmacsmith/ember-graphs)

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
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_GRAPHS_PKG_DIR  = Path(__file__).parent / "graphs"
GRAPHS_DIR       = _GRAPHS_PKG_DIR / "library"
PRESETS_FILE     = _GRAPHS_PKG_DIR / "presets.csv"
MANIFEST_PATH    = _GRAPHS_PKG_DIR / "manifest.json"

_HF_REPO         = "zachmacsmith/ember-graphs"
_HF_BASE_URL     = f"https://huggingface.co/datasets/{_HF_REPO}/resolve/main"


def _hf_subdir(category: str, filename: str) -> str:
    """Return the HuggingFace subdirectory for a graph file.

    Most categories map directly (random_er -> random_er/).
    watts_strogatz is split by k to stay under HF's 10k file limit.
    The JSON 'category' field is unchanged — this is a storage detail only.
    """
    import re
    if category == "watts_strogatz":
        m = re.search('_k([0-9]+)_', filename)
        return f"watts_strogatz_k{m.group(1)}" if m else "watts_strogatz_other"
    return category


# ==============================================================================
# MANIFEST
# ==============================================================================

def load_manifest() -> Dict:
    """Load and return the bundled manifest.json.

    Returns a dict with keys:
        version (str)
        graphs  (list of dicts: id, name, type, parameters, nodes, edges,
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


def _normalize_entry(entry: dict) -> dict:
    """Normalize a manifest entry to full key names.

    The manifest uses abbreviated keys to keep file size down:
        type → category
        n    → nodes
        e    → edges
        d    → density
        h    → hash prefix (first 16 hex chars of SHA-256)
        sz   → size_bytes
        p    → parameters
        topo → topologies

    Full-key manifests (if ever generated) are passed through unchanged.
    """
    return {
        "id":         entry["id"],
        "name":       entry["name"],
        "category":   entry.get("type",  entry.get("category",  "")),
        "nodes":      entry.get("n",     entry.get("nodes",     entry.get("num_nodes",  0))),
        "edges":      entry.get("e",     entry.get("edges",     entry.get("num_edges",  0))),
        "density":    entry.get("d",     entry.get("density",   0)),
        "topologies": entry.get("topo",  entry.get("topologies", [])),
        "parameters": entry.get("p",     entry.get("parameters", {})),
        "size_bytes": entry.get("sz",    entry.get("size_bytes", 0)),
        # `h` is the first 16 hex chars of the SHA-256 (prefix fingerprint).
        # Stored as-is; callers use _hash_ok() to compare against the full digest.
        "hash":       entry.get("h",    entry.get("hash", "")),
        "url":        entry.get("url",  ""),
    }


def _hash_ok(actual_hex: str, expected: str) -> bool:
    """Return True if actual_hex matches expected.

    expected may be a full SHA-256 (64 chars) or the 16-char prefix stored
    in the manifest.  An empty expected string always passes (no hash on record).
    """
    if not expected:
        return True
    return actual_hex.startswith(expected) if len(expected) < 64 else actual_hex == expected


def _manifest_by_id() -> Dict[int, Dict]:
    """Return manifest entries keyed by graph ID, with keys normalised to full names."""
    manifest = load_manifest()
    return {entry["id"]: _normalize_entry(entry) for entry in manifest.get("graphs", [])}


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
        expected = manifest[gid].get("hash", "")
        if not expected:
            continue  # no hash on record — skip integrity check
        if not target.exists():
            raise RuntimeError(f"Graph file missing: {target}")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if not _hash_ok(actual, expected):
            raise RuntimeError(
                f"Graph integrity check failed: {target.name} (id={gid})\n"
                f"  expected: {expected}\n"
                f"  actual:   {actual}\n"
                "The file has been modified. Re-install the package to restore it."
            )


# ==============================================================================
# LOCAL CACHE
# ==============================================================================

def _get_cache_dir() -> Path:
    """Return the user graph cache directory (flat structure), creating it if needed."""
    from ember_qc._paths import get_user_graphs_dir
    d = get_user_graphs_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _bundled_id_set() -> Set[int]:
    """Return the set of graph IDs present in the bundled package library."""
    if not GRAPHS_DIR.exists():
        return set()
    result: Set[int] = set()
    for f in GRAPHS_DIR.rglob("*.json"):
        prefix = f.stem.split("_", 1)[0]
        try:
            result.add(int(prefix))
        except ValueError:
            pass
    return result


def _is_installed(graph_id: int, name: str, cache_dir: Optional[Path],
                  bundled: Optional[Set[int]] = None) -> bool:
    """Return True if graph_id is available locally (cache or bundled)."""
    if bundled is not None and graph_id in bundled:
        return True
    if cache_dir is not None and _cache_path(graph_id, name).exists():
        return True
    return False


def _cache_path(graph_id: int, name: str) -> Path:
    """Canonical path for a cached graph file: <cache_dir>/{id}_{name}.json.

    Filename is deterministic from the manifest — no index needed.
    """
    return _get_cache_dir() / f"{graph_id}_{name}.json"


# ==============================================================================
# CORE LOADER
# ==============================================================================

def _load_graph_file(filepath: Path) -> Tuple[int, str, nx.Graph, Dict]:
    """Load a single graph JSON file. Returns (id, name, graph, metadata)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    graph_data = data["graph"]
    # Handle both NX 2.x ("links") and NX 3.x ("edges") node-link format
    edges_key  = "edges" if "edges" in graph_data else "links"
    graph      = nx.node_link_graph(graph_data, edges=edges_key)
    return data.get("id", 0), data["name"], graph, data.get("metadata", {})


def _download_graph(graph_id: int, entry: Dict, cache_dir: Path) -> Path:
    """Download a graph from HuggingFace, verify its hash, and cache it.

    Args:
        graph_id:  Integer graph ID.
        entry:     Manifest entry dict (must contain 'name' and 'hash').
        cache_dir: Local directory to save the downloaded file.

    Returns:
        Path to the cached file.

    Raises:
        RuntimeError:  If the download fails or the hash does not match.
    """
    name     = entry["name"]
    category = entry.get("category", "")
    filename = f"{graph_id}_{name}.json"
    subdir   = _hf_subdir(category, filename)
    url      = entry.get("url") or f"{_HF_BASE_URL}/{subdir}/{filename}"

    print(f"  Downloading graph {graph_id} ({name}) from {_HF_REPO}...",
          file=sys.stderr)

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Failed to download graph {graph_id} ({name}): HTTP {e.code} — {url}\n"
            f"Check your network connection or that the dataset is public."
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Failed to download graph {graph_id} ({name}): {e.reason} — {url}\n"
            "Check your network connection."
        ) from e

    # Verify hash before writing to disk
    actual_hash = hashlib.sha256(raw).hexdigest()
    expected_hash = entry.get("hash", "")
    if not _hash_ok(actual_hash, expected_hash):
        raise RuntimeError(
            f"Hash mismatch for graph {graph_id} ({name}) after download.\n"
            f"  expected: {expected_hash}\n"
            f"  actual:   {actual_hash}\n"
            "The file may be corrupt or the manifest is stale. "
            "Try updating the ember-qc package."
        )

    # Write atomically: temp file + rename (never leaves a partial file)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = _cache_path(graph_id, name)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=cache_dir, suffix=".tmp")
    try:
        with open(tmp_fd, "wb") as f:
            f.write(raw)
        shutil.move(tmp_path, dest)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    print(f"  Cached to {dest}", file=sys.stderr)
    return dest


def load_graph(graph_id: int) -> nx.Graph:
    """Load a graph by its integer ID using a three-layer lookup.

    Layer 1 — Local cache
        Check ~/.local/share/ember-qc/graphs/ for a previously downloaded copy.
        Filename is deterministic ({id}_{name}.json) — no index needed.
        Verifies SHA-256 prefix against manifest before returning.
        On hash mismatch the stale file is deleted and lookup continues.

    Layer 2 — Bundled files
        Search the package library directory for a file whose numeric
        prefix matches graph_id. If found, return the graph.

    Layer 3 — Remote download
        Download from the HuggingFace dataset (zachmacsmith/ember-graphs),
        verify the hash, cache locally, and return the graph.
        Subsequent calls for the same graph will hit Layer 1.

    Args:
        graph_id: Integer graph ID as recorded in manifest.json.

    Returns:
        A NetworkX Graph object.

    Raises:
        KeyError:     if graph_id is not in the manifest.
        RuntimeError: if a file is corrupt or the download fails.
    """
    manifest = _manifest_by_id()

    if graph_id not in manifest:
        raise KeyError(
            f"Graph ID {graph_id} not found in manifest. "
            "Run 'ember graphs list' to see all available graphs."
        )

    entry = manifest[graph_id]
    expected_hash = entry.get("hash", "")

    # ------------------------------------------------------------------
    # Layer 1: local user cache
    # Filename is deterministic from the manifest — no index needed.
    # ------------------------------------------------------------------
    try:
        cached_file = _cache_path(graph_id, entry["name"])
        if cached_file.exists():
            actual_hash = hashlib.sha256(cached_file.read_bytes()).hexdigest()
            if _hash_ok(actual_hash, expected_hash):
                _, _, graph, _ = _load_graph_file(cached_file)
                return graph
            else:
                # Hash mismatch — delete stale file and fall through to re-download
                cached_file.unlink(missing_ok=True)
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
                    if expected_hash:
                        actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
                        if not _hash_ok(actual_hash, expected_hash):
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
    # Layer 3: remote download from HuggingFace
    # ------------------------------------------------------------------
    try:
        cached_file = _download_graph(graph_id, entry, _get_cache_dir())
        _, _, graph, _ = _load_graph_file(cached_file)
        return graph
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Failed to download graph {graph_id}: {e}"
        ) from e


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
    """Load test graphs by selection string.

    Graphs not bundled with the package are downloaded from HuggingFace
    and cached locally for subsequent calls.

    Args:
        selection: Graph selection string (e.g., "1-10", "1-60, !35", "*").
        max_nodes: Only include graphs with at most this many nodes.
        min_nodes: Only include graphs with at least this many nodes.

    Returns:
        List of (name, graph) tuples sorted by ID.
    """
    selected_ids = parse_graph_selection(selection)
    is_wildcard  = -1 in selected_ids

    # If wildcard, resolve all IDs from manifest
    if is_wildcard:
        manifest     = _manifest_by_id()
        selected_ids = set(manifest.keys())

    # Apply node filters from manifest to avoid downloading graphs we'll discard
    manifest = _manifest_by_id()
    if max_nodes or min_nodes:
        filtered = set()
        for gid in selected_ids:
            entry = manifest.get(gid, {})
            n = entry.get("nodes", 0)
            if max_nodes and n > max_nodes:
                continue
            if min_nodes and n < min_nodes:
                continue
            filtered.add(gid)
        selected_ids = filtered

    results: List[Tuple[int, str, nx.Graph]] = []
    loaded_files: List[Tuple[int, Path]] = []

    # First, satisfy from bundled files
    bundled_ids: Set[int] = set()
    if GRAPHS_DIR.exists():
        for json_file in sorted(GRAPHS_DIR.rglob("*.json")):
            if json_file.name.startswith("REGISTRY"):
                continue
            prefix = json_file.stem.split("_", 1)[0]
            try:
                gid = int(prefix)
            except ValueError:
                continue
            if gid not in selected_ids:
                continue

            gid, name, graph, _ = _load_graph_file(json_file)
            results.append((gid, name, graph))
            loaded_files.append((gid, json_file))
            bundled_ids.add(gid)

    # Download any remaining IDs not found in bundle
    remaining = selected_ids - bundled_ids
    if remaining:
        for gid in sorted(remaining):
            entry = manifest.get(gid)
            if not entry:
                continue
            try:
                graph = load_graph(gid)
                results.append((gid, entry["name"], graph))
            except Exception as e:
                print(f"  Warning: could not load graph {gid}: {e}", file=sys.stderr)

    if loaded_files and MANIFEST_PATH.exists():
        verify_manifest(files=loaded_files)

    results.sort(key=lambda x: x[0])
    return [(name, graph) for _, name, graph in results]


def list_test_graphs() -> List[Dict]:
    """List all available graphs with their IDs and metadata (from manifest)."""
    try:
        manifest = load_manifest()
        catalog = []
        for entry in manifest.get("graphs", []):
            catalog.append({
                "id":       entry.get("id", 0),
                "name":     entry.get("name", ""),
                "category": entry.get("category", entry.get("type", "")),
                "nodes":    entry.get("nodes", entry.get("num_nodes", 0)),
                "edges":    entry.get("edges", entry.get("num_edges", 0)),
                "density":  round(entry.get("density", 0), 3),
            })
        catalog.sort(key=lambda x: x["id"])
        return catalog
    except FileNotFoundError:
        pass

    # Fallback: scan bundled files directly
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


# ==============================================================================
# GRAPH TYPE OVERVIEW
# ==============================================================================

def list_graph_types(installed_only: bool = False) -> List[Dict]:
    """List all graph categories with ID range, total count, and installed count.

    Args:
        installed_only: If True, only return types that have at least one
                        graph installed in the local cache.

    Returns:
        List of dicts sorted by id_start, each containing:
            category, id_start, id_end, total, installed
    """
    manifest = _manifest_by_id()
    cache_dir = None
    try:
        cache_dir = _get_cache_dir()
    except Exception:
        pass
    bundled = _bundled_id_set()

    # Group manifest entries by category
    by_category: Dict[str, List[Dict]] = {}
    for entry in manifest.values():
        cat = entry.get("category", "unknown")
        by_category.setdefault(cat, []).append(entry)

    result = []
    for cat, entries in by_category.items():
        ids = [e["id"] for e in entries]
        installed = sum(
            1 for e in entries
            if _is_installed(e["id"], e["name"], cache_dir, bundled)
        )

        if installed_only and installed == 0:
            continue

        result.append({
            "category":  cat,
            "id_start":  min(ids),
            "id_end":    max(ids),
            "total":     len(entries),
            "installed": installed,
        })

    result.sort(key=lambda x: x["id_start"])
    return result


def list_graphs_of_type(category: str,
                        installed_only: bool = False) -> List[Dict]:
    """List all graphs of a given category from the manifest.

    Args:
        category:       Graph type name (e.g. 'complete', 'random_er').
        installed_only: If True, only return graphs present in the local cache.

    Returns:
        List of dicts sorted by ID, each containing:
            id, name, nodes, edges, density, installed
    """
    manifest = _manifest_by_id()
    cache_dir = None
    try:
        cache_dir = _get_cache_dir()
    except Exception:
        pass
    bundled = _bundled_id_set()

    result = []
    for entry in manifest.values():
        if entry.get("category") != category:
            continue
        installed = _is_installed(entry["id"], entry["name"], cache_dir, bundled)
        if installed_only and not installed:
            continue
        result.append({
            "id":        entry["id"],
            "name":      entry["name"],
            "nodes":     entry.get("nodes", entry.get("num_nodes", 0)),
            "edges":     entry.get("edges", entry.get("num_edges", 0)),
            "density":   round(entry.get("density", 0), 4),
            "installed": installed,
        })

    result.sort(key=lambda x: x["id"])
    return result


def graph_info(graph_id: int) -> Dict:
    """Return full manifest metadata for a single graph, plus installed status.

    Raises:
        KeyError: if graph_id is not in the manifest.
    """
    manifest = _manifest_by_id()
    if graph_id not in manifest:
        raise KeyError(f"Graph ID {graph_id} not found in manifest.")
    entry = dict(manifest[graph_id])
    try:
        cache_dir = _get_cache_dir()
    except Exception:
        cache_dir = None
    entry["installed"] = _is_installed(
        graph_id, entry["name"], cache_dir, _bundled_id_set()
    )
    return entry


# ==============================================================================
# INSTALL
# ==============================================================================

def install_graphs(selection: str, verbose: bool = True) -> List[int]:
    """Download and cache graphs matching a selection string or preset.

    Graphs already in the cache are skipped. Graphs bundled with the
    package are not re-downloaded but are counted as available.

    Args:
        selection: Graph selection string or preset name.
        verbose:   Print progress to stderr.

    Returns:
        List of graph IDs that were newly downloaded.
    """
    selected_ids = parse_graph_selection(selection)
    manifest = _manifest_by_id()

    if -1 in selected_ids:
        selected_ids = set(manifest.keys())

    downloaded = []
    skipped = 0
    missing = 0

    for gid in sorted(selected_ids):
        entry = manifest.get(gid)
        if not entry:
            missing += 1
            continue

        # Already cached?
        if _cache_path(gid, entry["name"]).exists():
            skipped += 1
            continue

        # Already bundled?
        if GRAPHS_DIR.exists():
            found = any(
                int(f.stem.split("_", 1)[0]) == gid
                for f in GRAPHS_DIR.rglob("*.json")
                if f.stem.split("_", 1)[0].isdigit()
            )
            if found:
                skipped += 1
                continue

        # Download
        try:
            _download_graph(gid, entry, _get_cache_dir())
            downloaded.append(gid)
        except Exception as e:
            print(f"  Warning: could not download graph {gid}: {e}",
                  file=sys.stderr)

    if verbose:
        print(
            f"Done. Downloaded: {len(downloaded)}, "
            f"already available: {skipped}"
            + (f", not in manifest: {missing}" if missing else ""),
            file=sys.stderr,
        )

    return downloaded


# ==============================================================================
# CACHE MANAGEMENT
# ==============================================================================

def cache_summary() -> Dict:
    """Return a summary of the local graph cache.

    Returns a dict with:
        total_installed  — number of cached graph files
        total_bytes      — total disk usage in bytes
        by_category      — dict of category → {count, bytes}
    """
    try:
        cache_dir = _get_cache_dir()
    except Exception:
        return {"total_installed": 0, "total_bytes": 0, "by_category": {}}

    manifest = _manifest_by_id()
    # Build a quick id→category lookup
    id_to_cat = {e["id"]: e.get("category", "unknown") for e in manifest.values()}

    total_bytes = 0
    total_installed = 0
    by_category: Dict[str, Dict] = {}

    for f in cache_dir.glob("*.json"):
        prefix = f.stem.split("_", 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            continue
        size = f.stat().st_size
        cat = id_to_cat.get(gid, "unknown")
        total_bytes += size
        total_installed += 1
        if cat not in by_category:
            by_category[cat] = {"count": 0, "bytes": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["bytes"] += size

    return {
        "total_installed": total_installed,
        "total_bytes":     total_bytes,
        "by_category":     by_category,
    }


def delete_from_cache(selection: Optional[str] = None,
                      delete_all: bool = False) -> int:
    """Remove graphs from the local cache.

    Args:
        selection:  Selection string or preset. Required unless delete_all.
        delete_all: If True, wipe the entire cache directory.

    Returns:
        Number of files deleted.
    """
    try:
        cache_dir = _get_cache_dir()
    except Exception:
        return 0

    if delete_all:
        count = sum(1 for f in cache_dir.glob("*.json"))
        for f in cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)
        return count

    if not selection:
        raise ValueError("Provide a selection string or pass delete_all=True.")

    selected_ids = parse_graph_selection(selection)
    manifest = _manifest_by_id()
    if -1 in selected_ids:
        selected_ids = set(manifest.keys())

    deleted = 0
    for gid in selected_ids:
        entry = manifest.get(gid)
        if not entry:
            continue
        path = _cache_path(gid, entry["name"])
        if path.exists():
            path.unlink()
            deleted += 1

    return deleted


def verify_cache(fix: bool = False) -> Dict:
    """Verify all cached graphs against manifest hashes.

    Args:
        fix: If True, re-download any corrupt or missing files.

    Returns:
        Dict with keys: ok (list of IDs), corrupt (list), missing (list).
    """
    try:
        cache_dir = _get_cache_dir()
    except Exception:
        return {"ok": [], "corrupt": [], "missing": []}

    manifest = _manifest_by_id()
    ok, corrupt, missing = [], [], []

    for f in sorted(cache_dir.glob("*.json")):
        prefix = f.stem.split("_", 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            continue

        entry = manifest.get(gid)
        if not entry:
            continue  # not in manifest — skip

        expected = entry.get("hash", "")
        if not expected:
            ok.append(gid)
            continue

        actual = hashlib.sha256(f.read_bytes()).hexdigest()
        if _hash_ok(actual, expected):
            ok.append(gid)
        else:
            corrupt.append(gid)
            if fix:
                f.unlink(missing_ok=True)
                try:
                    _download_graph(gid, entry, cache_dir)
                    ok.append(gid)
                    corrupt.remove(gid)
                except Exception as e:
                    print(f"  Failed to re-download {gid}: {e}", file=sys.stderr)

    return {"ok": ok, "corrupt": corrupt, "missing": missing}


def search_graphs(category: Optional[str] = None,
                  min_nodes: Optional[int] = None,
                  max_nodes: Optional[int] = None,
                  min_edges: Optional[int] = None,
                  max_edges: Optional[int] = None,
                  topology: Optional[str] = None,
                  installed_only: bool = False) -> List[Dict]:
    """Filter graphs from the manifest by property.

    All filters are ANDed. Reads only from the manifest — no files needed.

    Args:
        category:       Filter by graph type (e.g. 'random_er').
        min_nodes:      Minimum node count.
        max_nodes:      Maximum node count.
        min_edges:      Minimum edge count.
        max_edges:      Maximum edge count.
        topology:       Only include graphs feasible on this topology
                        ('chimera', 'pegasus', 'zephyr').
        installed_only: Only include graphs present in the local cache.

    Returns:
        List of matching manifest entry dicts, sorted by ID.
    """
    manifest = _manifest_by_id()
    cache_dir = None
    try:
        cache_dir = _get_cache_dir()
    except Exception:
        pass

    result = []
    for entry in manifest.values():
        n = entry.get("nodes", entry.get("num_nodes", 0))
        e = entry.get("edges", entry.get("num_edges", 0))
        cat = entry.get("category", "")
        topos = entry.get("topologies", [])

        if category and cat != category:
            continue
        if min_nodes is not None and n < min_nodes:
            continue
        if max_nodes is not None and n > max_nodes:
            continue
        if min_edges is not None and e < min_edges:
            continue
        if max_edges is not None and e > max_edges:
            continue
        if topology and topology not in topos:
            continue
        if installed_only:
            if not (cache_dir and _cache_path(entry["id"], entry["name"]).exists()):
                continue

        result.append({
            "id":        entry["id"],
            "name":      entry["name"],
            "category":  cat,
            "nodes":     n,
            "edges":     e,
            "density":   round(entry.get("density", 0), 4),
            "topologies": topos,
            "installed": cache_dir is not None and _cache_path(
                entry["id"], entry["name"]
            ).exists(),
        })

    result.sort(key=lambda x: x["id"])
    return result
