# Feature Specification: Graph Library Management

## Minimal Architecture Required Before Paper Release

The following must be implemented before the paper deadline. Everything else in this document is post-submission.

**Must implement now:**

1. `load_graph(graph_id)` with the three-layer lookup (local cache → bundled files → download). The download layer can raise `NotImplementedError` for now — it will never fire while graphs are bundled. The interface must be correct from day one because everything in the codebase calls it.
    
2. The manifest file (`manifest.json`) must be created and bundled with the package, even though it isn't used by any lookup layer yet. It must accurately describe every graph currently in the library. Doing this now means the manifest stays in sync with the actual library rather than being retrofitted later.
    
3. The local index file structure must be defined, even if it is never written to during the paper phase. When bundled files are the only source, the local index is always empty and that is fine.
    
4. The bundled graph files must be correctly declared as package data in `pyproject.toml` and accessible via `importlib.resources`. This is the most likely failure point — graphs that install correctly on the developer's machine but are absent from the wheel.
    

**Leave as stubs now:**

- Download layer inside `load_graph` — raise `NotImplementedError` with a message explaining that remote download is not yet implemented
- All `ember graphs fetch` CLI commands — register the command group so `ember graphs --help` shows it exists, but each subcommand prints "not yet implemented"
- All `ember graphs cache` CLI commands — same pattern
- `ember graphs status` — same pattern
- Named release sets / graph collections — post-submission design decision
- Manifest remote versioning — post-submission

---

## 1. Purpose

The graph library is the core data asset of EMBER. It contains the benchmark instances — NetworkX graphs in JSON format — that algorithms are evaluated against. The library management system is responsible for three things: storing graphs in a way that survives package updates, providing a single consistent interface for all code that needs to load a graph, and giving users control over what is cached locally and what is fetched on demand.

The design must accommodate two phases of the library's lifecycle:

**Phase 1 (current):** The library is small enough to bundle entirely inside the PyPI wheel. All graphs are available immediately after `pip install ember-qc` with no network access required.

**Phase 2 (future):** The library has grown beyond the bundling threshold (~50MB). Graphs are hosted remotely and cached locally on demand. The transition from Phase 1 to Phase 2 must be invisible to any code that calls `load_graph`.

---

## 2. Directory Structure

### 2.1 Bundled files (inside the package, ships with pip install)

```
src/ember_qc/graphs/
├── __init__.py
├── generators.py
├── presets.csv
├── manifest.json          # describes all graphs in the library
└── library/               # graph JSON files (Phase 1 only)
    ├── 001.json
    ├── 002.json
    └── ...
```

In Phase 2, the `library/` directory is empty or absent. The manifest remains bundled because it is small and must be available offline.

### 2.2 User data directory (outside the package, persists across upgrades)

```
~/.local/share/ember-qc/graphs/
├── local_index.json       # tracks what is cached, file hashes, download dates
├── 001.json               # cached graph files
├── 002.json
└── ...
```

The user graph directory is managed entirely by EMBER. Users should not need to interact with it directly except through CLI commands.

---

## 3. The Manifest

### 3.1 Purpose

The manifest is the authoritative description of the graph library. It is a single JSON file that lists every graph available in the library, with enough metadata to locate, validate, and describe each one. It ships inside the package and is versioned with the package.

### 3.2 Contents

For each graph, the manifest must record:

|Field|Description|
|---|---|
|`id`|Integer graph ID — unique, stable across versions|
|`type`|Graph family (er, ba, grid, kagome, etc.)|
|`parameters`|Dict of generation parameters used to produce this graph|
|`nodes`|Node count|
|`edges`|Edge count|
|`difficulty`|Difficulty band (trivial / easy / medium / hard / near_threshold) per topology|
|`hash`|SHA-256 hash of the JSON file for integrity verification|
|`url`|Remote URL for download (null in Phase 1, populated in Phase 2)|
|`size_bytes`|File size, used to report download size before fetching|

### 3.3 Versioning

The manifest version is tied to the package version. Adding new graphs to the library requires a package release that updates the manifest. This is a deliberate constraint — it ensures that a given package version fully describes the graph library it expects, making benchmark results unambiguously reproducible.

### 3.4 Manifest must not track local state

The manifest describes what exists in the library, not what is installed locally. Local installation state is tracked separately in the local index. The manifest is read-only from the user's perspective — it is never written to after install.

---

## 4. The Local Index

### 4.1 Purpose

The local index tracks which graphs are currently cached in the user data directory. It is separate from the manifest because its contents change as graphs are fetched and deleted, while the manifest is fixed for a given package version.

### 4.2 Contents

For each locally cached graph, the local index records:

|Field|Description|
|---|---|
|`id`|Graph ID|
|`cached_at`|Timestamp of when the graph was downloaded|
|`hash`|Hash of the cached file, used to detect corruption|
|`source`|Where the graph came from: `bundled`, `downloaded`, `user_provided`|

### 4.3 Consistency

The local index must stay consistent with the actual files in the user graph directory. If a file is present but not in the index, it is treated as uncached and re-fetched if needed. If an entry is in the index but the file is missing or the hash does not match, the entry is invalidated and the graph is treated as uncached.

---

## 5. `load_graph(graph_id)` — The Core Interface

### 5.1 Purpose

`load_graph` is the single function through which all code in EMBER accesses graph data. No other part of the codebase should construct graph file paths, read graph files, or interact with the manifest or local index directly. All of that complexity is encapsulated here.

### 5.2 Lookup order

The function must attempt to load the graph from three sources in strict priority order:

**Layer 1 — Local cache** Check the user data directory for a cached copy of the graph. If found, verify the file hash against the local index. If the hash matches, return the graph. If the hash does not match, invalidate the cache entry and continue to the next layer.

**Layer 2 — Bundled files** Check the package's bundled library directory for the graph. If found, return the graph. In Phase 2 when graphs are no longer bundled, this layer is empty and always falls through.

**Layer 3 — Remote download** Consult the manifest for the graph's remote URL. Download the file, verify its hash against the manifest, save it to the local cache, update the local index, and return the graph. If the download fails, raise a clear error with instructions for manual pre-fetching.

### 5.3 Return value

The function always returns a NetworkX graph object regardless of which layer served it. The caller never needs to know which layer was used.

### 5.4 Failure behaviour

If the graph ID does not exist in the manifest, raise a clear error identifying the unknown ID.

If all three layers fail, raise a clear error that explains what was tried and suggests `ember graphs fetch <id>` as the manual resolution.

### 5.5 Hash verification

Hash verification must be performed for any graph loaded from the local cache. If a bundled file's hash does not match the manifest, raise a clear error — this indicates a corrupted install and the user should reinstall the package.

### 5.6 Transparency

The function must operate silently when loading from local cache or bundled files. When a download is triggered, it must print a single clear line indicating what is being fetched and why, so the user is not surprised by network activity.

---

## 6. Fetch and Cache CLI Commands

### 6.1 `ember graphs fetch`

Pre-downloads graphs to the local cache so they are available without network access during benchmark runs. Intended for use on HPC login nodes before submitting compute jobs.

**Behaviour:**

- Accepts the same graph selection syntax as `ember run` — ID ranges, preset names, type names
- Checks local cache first and skips any graph already present with a valid hash
- Reports download progress with a progress bar
- Reports total download size before starting
- Reports count of graphs skipped (already cached), downloaded, and failed at completion
- Failures during a batch fetch must not abort the entire operation — failed graphs are reported at the end

**Subcommands:**

```
ember graphs fetch <selection>        by ID range or individual IDs
ember graphs fetch --preset <name>    by named preset
ember graphs fetch --type <type>      all graphs of a given type
ember graphs fetch --all              entire library (warns about size first)
```

### 6.2 `ember graphs cache list`

Lists all graphs currently in the local cache with their ID, type, node count, edge count, and download date. Supports the same filtering flags as `ember graphs fetch` to show only a subset.

### 6.3 `ember graphs cache size`

Reports total disk usage of the local graph cache, and optionally a breakdown by graph type.

### 6.4 `ember graphs cache clear`

Deletes graphs from the local cache. Deleted graphs are not permanently removed — they will be re-downloaded if referenced by a future benchmark run.

**Behaviour:**

- Accepts the same selection syntax as `ember graphs fetch`
- Without a selection argument, clears the entire cache after confirmation
- With a selection, clears only matching graphs without requiring confirmation
- Updates the local index after deletion

### 6.5 `ember graphs cache verify`

Checks the hash of every cached graph against the manifest and reports any files that are corrupt or mismatched. Does not delete or repair — only reports. The user can then run `ember graphs cache clear` on the affected IDs and re-fetch.

### 6.6 `ember graphs status`

Prints a summary of the graph library state:

```
Graph library
─────────────────────────────────────────────
Manifest version:    0.5.0
Total in library:    847 graphs
Locally cached:      123 graphs (45.2 MB)
Bundled in package:  60 graphs

Run 'ember graphs fetch --preset default' to cache the default graph set.
```

---

## 7. Graph Listing CLI Commands

### 7.1 `ember graphs list`

Lists graphs available in the library with ID, type, node count, edge count, difficulty, and local availability (cached / bundled / remote).

**Flags:**

```
ember graphs list                     all graphs in manifest
ember graphs list --filter <spec>     preview a selection string
ember graphs list --preset <name>     graphs in a named preset
ember graphs list --type <type>       graphs of a given type
ember graphs list --cached            only locally available graphs
```

### 7.2 `ember graphs presets`

Lists all named presets with their name, selection string, and graph count.

---

## 8. Package Data Declaration

Graph JSON files and the manifest must be explicitly declared as package data in `pyproject.toml`. Without this declaration, they are silently omitted from the wheel. This is the single most common packaging mistake and must be verified explicitly during the pre-upload checklist by inspecting the wheel contents.

The manifest must always be declared as package data regardless of whether any graph JSON files are bundled. In Phase 2, the manifest is the only bundled graph-related file.

---

## 9. Cross-cutting Constraints

### 9.1 Offline operation

Any benchmark run that uses only locally cached or bundled graphs must work with no network access. The download layer must only be reached when a graph is not available locally. EMBER must never attempt a network connection during a run unless a required graph is genuinely absent.

### 9.2 HPC compatibility

The fetch commands must be usable on login nodes to pre-populate the cache before job submission. The benchmark runner must detect missing graphs before dispatching any workers, fail fast with a clear list of missing IDs, and suggest the exact fetch command to resolve the situation.

### 9.3 Reproducibility

A benchmark run's output folder records the manifest version alongside the package version. This means the exact graph library used for any published result is fully specified and recoverable.

### 9.4 Cache persistence across upgrades

The local graph cache must not be invalidated or deleted by `pip install --upgrade ember-qc`. Graphs cached from a previous version remain valid as long as their hash matches the current manifest's entry for that ID. If the manifest entry for a graph changes between versions — because the graph was regenerated — the hash check will fail and the graph will be re-fetched automatically.