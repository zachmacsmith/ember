"""
ember_qc/cli.py
===============
Command-line interface for ember-qc.

Entry point: `ember-qc` (configured in pyproject.toml).

Subcommand groups:
  ember run          — run a benchmark (from YAML or flags)
  ember resume       — resume an unfinished benchmark
  ember graphs       — browse and manage the graph library
  ember topologies   — list registered hardware topologies
  ember results      — list, inspect, and delete completed batches
  ember algos        — manage algorithms (list, add, remove, validate, template)
  ember config       — manage persistent user configuration
  ember install-binary — build and install C++ algorithm binaries
  ember version      — print package version
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

import yaml


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _resolved_yaml_name(yaml_path: Optional[Path]) -> str:
    if yaml_path is None:
        return "experiment_resolved.yaml"
    return f"{yaml_path.stem}_resolved.yaml"


def _build_resolved_params(args: argparse.Namespace, yaml_params: dict) -> dict:
    p = dict(yaml_params)
    cli_overrides = {
        "algorithms":     args.algorithms,
        "graphs":         args.graphs,
        "topologies":     args.topologies,
        "n_trials":       args.trials,
        "warmup_trials":  args.warmup,
        "timeout":        args.timeout,
        "seed":           args.seed,
        "n_workers":      args.workers,
        "fault_rate":     args.fault_rate,
        "fault_seed":     args.fault_seed,
        "note":           args.note,
        "output_dir":     args.output_dir,
        "analyze":        args.analyze,
        "verbose":        args.verbose,
    }
    for key, val in cli_overrides.items():
        if val is not None:
            p[key] = val
    if "algorithms" in p and isinstance(p["algorithms"], str):
        p["algorithms"] = [a.strip() for a in p["algorithms"].split(",")]
    if "topologies" in p and isinstance(p["topologies"], str):
        p["topologies"] = [t.strip() for t in p["topologies"].split(",")]
    from ember_qc.config import get as _cfg
    p.setdefault("algorithms",      None)
    p.setdefault("graphs",          _cfg("default_graphs") or "*")
    p.setdefault("topologies",      _cfg("default_topology"))
    p.setdefault("n_trials",        _cfg("default_n_trials"))
    p.setdefault("warmup_trials",   _cfg("default_warmup_trials"))
    p.setdefault("timeout",         _cfg("default_timeout"))
    p.setdefault("seed",            _cfg("default_seed"))
    p.setdefault("n_workers",       _cfg("default_workers"))
    p.setdefault("fault_rate",      _cfg("default_fault_rate"))
    p.setdefault("fault_seed",      None)
    p.setdefault("verbose",         _cfg("default_verbose"))
    p.setdefault("faulty_nodes",    None)
    p.setdefault("faulty_couplers", None)
    p.setdefault("note",            "")
    p.setdefault("output_dir",      _cfg("output_dir"))
    p.setdefault("analyze",         False)
    if "topologies" in p and isinstance(p["topologies"], str):
        p["topologies"] = [t.strip() for t in p["topologies"].split(",")]
    return p


def _write_resolved_yaml(params: dict, final_dir: Path, yaml_path: Optional[Path],
                         actual_warmup: Optional[int] = None) -> None:
    resolved = {k: v for k, v in params.items() if k not in ("output_dir",)}
    if actual_warmup is not None:
        resolved["warmup_trials"] = actual_warmup
    _write_yaml(resolved, final_dir / _resolved_yaml_name(yaml_path))


# ---------------------------------------------------------------------------
# ember run
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> None:
    from ember_qc.benchmark import EmbeddingBenchmark
    from ember_qc.topologies import get_topology, list_topologies

    yaml_path: Optional[Path] = None
    yaml_params: dict = {}

    if args.experiment:
        yaml_path = Path(args.experiment)
        if not yaml_path.exists():
            print(f"error: experiment file not found: {yaml_path}")
            sys.exit(1)
        yaml_params = _load_yaml(yaml_path)

    params = _build_resolved_params(args, yaml_params)
    topo_names = params["topologies"] or list_topologies()
    topo_list = []
    for name in topo_names:
        try:
            g = get_topology(name)
            topo_list.append((name, g, name))
        except KeyError:
            print(f"error: unknown topology '{name}'. Run: ember topologies list")
            sys.exit(1)

    target_graph = topo_list[0][1]
    bench = EmbeddingBenchmark(target_graph)
    n_workers = params["n_workers"]
    warmup_trials = params["warmup_trials"]

    final_dir = bench.run_full_benchmark(
        graph_selection=params["graphs"],
        methods=params["algorithms"],
        topologies=params["topologies"] or list_topologies(),
        n_trials=params["n_trials"],
        warmup_trials=warmup_trials,
        timeout=params["timeout"],
        seed=params["seed"],
        n_workers=n_workers,
        batch_note=params["note"],
        output_dir=params["output_dir"],
        fault_rate=params["fault_rate"],
        fault_seed=params["fault_seed"],
        faulty_nodes=params["faulty_nodes"],
        faulty_couplers=params["faulty_couplers"],
        analyze=params["analyze"],
        verbose=params["verbose"],
    )

    if final_dir is None:
        return

    if yaml_path is not None:
        shutil.copy2(yaml_path, final_dir / yaml_path.name)

    actual_warmup = 0 if (n_workers > 1 and warmup_trials > 0) else warmup_trials
    _write_resolved_yaml(params, final_dir, yaml_path, actual_warmup=actual_warmup)
    print(f"Results: {final_dir}")


# ---------------------------------------------------------------------------
# ember resume
# ---------------------------------------------------------------------------

def cmd_resume(args: argparse.Namespace) -> None:
    from ember_qc.benchmark import load_benchmark, delete_benchmark
    from ember_qc.checkpoint import scan_incomplete_runs
    from ember_qc.config import get as _cfg, resolve_unfinished_dir as _resolve_ud

    _out_dir   = args.output_dir or _cfg("output_dir")
    _ud_setting = _cfg("unfinished_dir")
    _unfinished = _resolve_ud(_ud_setting, output_dir=_out_dir)

    if args.delete_all:
        runs = scan_incomplete_runs(_unfinished)
        if not runs:
            print("No unfinished runs found.")
            return
        print("Unfinished runs to delete:")
        for r in runs:
            print(f"  {r['batch_id']}")
        try:
            ans = input(f"\nDelete all {len(runs)} run(s)? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if ans not in ("y", "yes"):
            print("Aborted.")
            return
        for r in runs:
            delete_benchmark(batch_id=r["batch_id"], unfinished_dir=str(_unfinished), force=True)
        return

    if args.delete:
        delete_benchmark(batch_id=args.batch_id or None,
                         unfinished_dir=str(_unfinished))
        return

    load_benchmark(
        batch_id=args.batch_id or None,
        n_workers=args.workers or None,
        output_dir=_out_dir,
        unfinished_dir=_ud_setting,
        verbose=args.verbose,
        analyze=args.analyze,
    )


# ---------------------------------------------------------------------------
# ember graphs
# ---------------------------------------------------------------------------

def _fmt_bytes(n: int) -> str:
    """Human-readable byte size."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def cmd_graphs_list(args: argparse.Namespace) -> None:
    """ember graphs list [TYPE] [-a]

    Without TYPE: overview table of all graph types with ID ranges and counts.
    With TYPE:    all graphs of that type with per-graph node/edge counts.
    -a flag:      restrict to installed graphs / types only.
    """
    from ember_qc.load_graphs import list_graph_types, list_graphs_of_type

    category = getattr(args, "category", None)
    installed_only = getattr(args, "installed", False)

    if category:
        graphs = list_graphs_of_type(category, installed_only=installed_only)
        if not graphs:
            suffix = " (installed only)" if installed_only else ""
            print(f"No graphs found for type '{category}'{suffix}.")
            return
        print(f"\n  {'ID':>6}  {'Name':<45}  {'Nodes':>6}  {'Edges':>7}  Inst")
        print("  " + "-" * 74)
        for g in graphs:
            inst = "✓" if g["installed"] else " "
            print(f"  {g['id']:>6}  {g['name']:<45}  "
                  f"{g['nodes']:>6}  {g['edges']:>7}  {inst}")
        print(f"\n  {len(graphs)} graph(s) in '{category}'")
    else:
        types = list_graph_types(installed_only=installed_only)
        if not types:
            print("No graph types found in manifest.")
            return
        total     = sum(t["total"]     for t in types)
        installed = sum(t["installed"] for t in types)
        print(f"\n  {'Type':<25}  {'ID Range':<14}  {'Total':>7}  {'Installed':>9}")
        print("  " + "-" * 62)
        for t in types:
            id_range = f"{t['id_start']}–{t['id_end']}"
            print(f"  {t['category']:<25}  {id_range:<14}  "
                  f"{t['total']:>7}  {t['installed']:>9}")
        print(f"\n  {len(types)} types · {total:,} total · {installed:,} installed")


def cmd_graphs_info(args: argparse.Namespace) -> None:
    """ember graphs info <ID> — full metadata for one graph."""
    from ember_qc.load_graphs import graph_info, GRAPHS_DIR, _cache_path

    try:
        entry = graph_info(args.graph_id)
    except KeyError as e:
        print(f"error: {e}")
        sys.exit(1)

    nodes = entry.get("nodes", entry.get("num_nodes", "?"))
    edges = entry.get("edges", entry.get("num_edges", "?"))
    topos = ", ".join(entry.get("topologies", []) or ["unknown"])

    print(f"\n  ID:         {entry['id']}")
    print(f"  Name:       {entry['name']}")
    print(f"  Category:   {entry.get('category', '?')}")
    print(f"  Nodes:      {nodes}")
    print(f"  Edges:      {edges}")
    print(f"  Density:    {entry.get('density', '?')}")
    print(f"  Topologies: {topos}")

    # Try to find the file: cache first, then bundled
    json_path = None
    try:
        p = _cache_path(args.graph_id, entry["name"])
        if p.exists():
            json_path = p
    except Exception:
        pass
    if json_path is None and GRAPHS_DIR.exists():
        for candidate in GRAPHS_DIR.rglob("*.json"):
            prefix = candidate.stem.split("_", 1)[0]
            try:
                if int(prefix) == args.graph_id:
                    json_path = candidate
                    break
            except ValueError:
                continue

    if json_path is not None:
        with open(json_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        meta = {k: v for k, v in file_data.get("metadata", {}).items()
                if k != "topologies"}
        print(f"  Installed:  yes")
        if meta:
            print(f"  Parameters:")
            for k, v in meta.items():
                print(f"    {k}: {v}")
    else:
        print(f"  Installed:  no")


def cmd_graphs_install(args: argparse.Namespace) -> None:
    """ember graphs install <SPEC> [--dry-run] — download graphs to cache."""
    from ember_qc.load_graphs import install_graphs, parse_graph_selection, \
        _manifest_by_id, _cache_path

    selection = getattr(args, "selection", None)
    if not selection:
        print("error: provide a selection string, ID range, or preset name.")
        print("  Examples:  ember graphs install 1000-1099")
        print("             ember graphs install complete")
        print("             ember graphs install quick")
        sys.exit(1)

    manifest = _manifest_by_id()
    ids = parse_graph_selection(selection)
    if -1 in ids:
        ids = set(manifest.keys())

    if getattr(args, "dry_run", False):
        to_download = [
            gid for gid in sorted(ids)
            if (entry := manifest.get(gid))
            and not _cache_path(gid, entry["name"]).exists()
        ]
        already = len(ids & set(manifest.keys())) - len(to_download)
        est_bytes = sum(manifest[gid].get("size_bytes", 0) for gid in to_download)
        print(f"Would download {len(to_download):,} graph(s) "
              f"({_fmt_bytes(est_bytes)} estimated, {already:,} already cached).")
    else:
        # verbose=False suppresses the built-in summary; we print our own with size.
        # Progress lines ("Downloading…", "Cached to…") come from _download_graph()
        # directly and are unaffected by verbose.
        downloaded = install_graphs(selection, verbose=False)
        total_bytes = sum(
            _cache_path(gid, manifest[gid]["name"]).stat().st_size
            for gid in downloaded
            if manifest.get(gid) and _cache_path(gid, manifest[gid]["name"]).exists()
        )
        already = len(ids & set(manifest.keys())) - len(downloaded)
        print(f"Done. Downloaded: {len(downloaded):,} ({_fmt_bytes(total_bytes)}), "
              f"already available: {already:,}.")


def cmd_graphs_presets(args: argparse.Namespace) -> None:
    """ember graphs presets — list named selection presets with resolved counts."""
    from ember_qc.load_graphs import list_presets, _manifest_by_id, parse_graph_selection

    presets = list_presets()
    if not presets:
        print("No presets found.")
        return
    manifest = _manifest_by_id()
    print(f"\n  {'Preset':<20}  {'Graphs':>7}  Selection")
    print("  " + "-" * 65)
    for name, spec in sorted(presets.items()):
        try:
            ids = parse_graph_selection(spec)
            count = len(manifest) if -1 in ids else len(ids & set(manifest.keys()))
        except Exception:
            count = "?"
        print(f"  {name:<20}  {str(count):>7}  {spec}")


def cmd_graphs_cache(args: argparse.Namespace) -> None:
    """ember graphs cache — summary of the local graph cache."""
    from ember_qc.load_graphs import cache_summary

    s = cache_summary()
    print(f"\n  Installed: {s['total_installed']:,} graphs")
    print(f"  Size:      {_fmt_bytes(s['total_bytes'])}")
    if s["by_category"]:
        print(f"\n  {'Type':<25}  {'Count':>7}  Size")
        print("  " + "-" * 48)
        for cat, info in sorted(s["by_category"].items(),
                                 key=lambda x: x[1]["count"], reverse=True):
            print(f"  {cat:<25}  {info['count']:>7}  {_fmt_bytes(info['bytes'])}")


def cmd_graphs_cache_delete(args: argparse.Namespace) -> None:
    """ember graphs cache delete [SPEC] [--all] — remove graphs from cache."""
    from ember_qc.load_graphs import delete_from_cache, cache_summary, \
        _manifest_by_id, _cache_path, parse_graph_selection

    if getattr(args, "all", False):
        before = cache_summary()
        try:
            ans = input("Delete entire graph cache? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if ans not in ("y", "yes"):
            print("Aborted.")
            return
        deleted = delete_from_cache(delete_all=True)
        print(f"Deleted {deleted:,} graph(s), freed {_fmt_bytes(before['total_bytes'])}.")
    elif getattr(args, "selection", None):
        # Measure sizes before deletion
        manifest = _manifest_by_id()
        ids = parse_graph_selection(args.selection)
        if -1 in ids:
            ids = set(manifest.keys())
        freed_bytes = sum(
            _cache_path(gid, manifest[gid]["name"]).stat().st_size
            for gid in ids
            if manifest.get(gid) and _cache_path(gid, manifest[gid]["name"]).exists()
        )
        deleted = delete_from_cache(selection=args.selection)
        print(f"Deleted {deleted:,} graph(s), freed {_fmt_bytes(freed_bytes)}.")
    else:
        print("error: provide a selection string or --all.")
        sys.exit(1)


def cmd_graphs_verify(args: argparse.Namespace) -> None:
    """ember graphs verify [--fix] — check cached graphs against manifest hashes."""
    from ember_qc.load_graphs import verify_cache

    print("Verifying cached graphs...")
    result = verify_cache(fix=getattr(args, "fix", False))
    ok      = len(result["ok"])
    corrupt = len(result["corrupt"])

    print(f"  OK:      {ok:,}")
    print(f"  Corrupt: {corrupt:,}")
    if corrupt:
        for gid in result["corrupt"]:
            print(f"    ID {gid}")
        if not getattr(args, "fix", False):
            print("\n  Re-run with --fix to re-download corrupt files.")
    sys.exit(1 if corrupt > 0 else 0)


def cmd_graphs_search(args: argparse.Namespace) -> None:
    """ember graphs search — filter graphs by property (reads manifest only)."""
    from ember_qc.load_graphs import search_graphs

    results = search_graphs(
        category=getattr(args, "type", None),
        min_nodes=getattr(args, "min_nodes", None),
        max_nodes=getattr(args, "max_nodes", None),
        min_edges=getattr(args, "min_edges", None),
        max_edges=getattr(args, "max_edges", None),
        topology=getattr(args, "topology", None),
        installed_only=getattr(args, "installed", False),
    )
    if not results:
        print("No graphs match the given filters.")
        return
    print(f"\n  {'ID':>6}  {'Type':<20}  {'Name':<35}  {'Nodes':>6}  {'Edges':>7}  Inst")
    print("  " + "-" * 82)
    for g in results:
        inst = "✓" if g["installed"] else " "
        print(f"  {g['id']:>6}  {g['category']:<20}  {g['name']:<35}  "
              f"{g['nodes']:>6}  {g['edges']:>7}  {inst}")
    print(f"\n  {len(results):,} graph(s) matched")


# ---------------------------------------------------------------------------
# ember topologies
# ---------------------------------------------------------------------------

def cmd_topologies_list(args: argparse.Namespace) -> None:
    from ember_qc.topologies import list_topologies, get_topology_config

    names = list_topologies(family=args.family or None)
    if not names:
        msg = "No topologies found"
        if args.family:
            msg += f" for family '{args.family}'"
        print(msg)
        return
    print(f"{'Name':<30}  {'Family':<12}  Description")
    print("-" * 80)
    for name in names:
        cfg = get_topology_config(name)
        print(f"{name:<30}  {cfg.family:<12}  {cfg.description}")


def cmd_topologies_info(args: argparse.Namespace) -> None:
    from ember_qc.topologies import topology_info
    print(topology_info())


# ---------------------------------------------------------------------------
# ember results
# ---------------------------------------------------------------------------

def _find_results_dir(args: argparse.Namespace) -> Path:
    from ember_qc.config import resolve_output_dir
    explicit = getattr(args, "output_dir", None)
    resolved = resolve_output_dir(explicit)
    return resolved if resolved is not None else Path("results")


def cmd_results_list(args: argparse.Namespace) -> None:
    results_dir = _find_results_dir(args)
    if not results_dir.exists():
        print(f"No results directory found at: {results_dir.resolve()}")
        return
    batches = sorted(results_dir.glob("batch_*"), reverse=True)
    if not batches:
        print(f"No completed batches in: {results_dir.resolve()}")
        return
    print(f"{'Batch':<35}  {'Algorithms':<30}  {'Trials':>7}")
    print("-" * 78)
    for b in batches:
        cfg_path = b / "config.json"
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = json.load(f)
            algos  = ", ".join(cfg.get("algorithms", []))[:28]
            trials = cfg.get("total_measured_runs", "?")
        else:
            algos, trials = "?", "?"
        print(f"{b.name:<35}  {algos:<30}  {str(trials):>7}")
    print(f"\n{len(batches)} batch(es) in {results_dir.resolve()}")


def cmd_results_show(args: argparse.Namespace) -> None:
    results_dir = _find_results_dir(args)
    batch_dir   = results_dir / args.batch_id
    if not batch_dir.exists():
        print(f"error: batch not found: {batch_dir}")
        sys.exit(1)
    config_path = batch_dir / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        print("=== Config ===")
        for k, v in cfg.items():
            if k not in ("custom_problems",):
                print(f"  {k}: {v}")
        print()
    summary = batch_dir / "summary.csv"
    if summary.exists():
        print("=== Summary ===")
        print(summary.read_text())
    else:
        print("No summary.csv found.")


def cmd_results_delete(args: argparse.Namespace) -> None:
    results_dir = _find_results_dir(args)
    batch_dir   = results_dir / args.batch_id
    if not batch_dir.exists():
        print(f"error: batch not found: {batch_dir}")
        sys.exit(1)
    confirm = input(f"Delete {batch_dir.name}? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return
    shutil.rmtree(batch_dir)
    print(f"Deleted: {batch_dir.name}")


# ---------------------------------------------------------------------------
# ember algos
# ---------------------------------------------------------------------------

def cmd_algos_list(args: argparse.Namespace) -> None:
    from ember_qc.registry import ALGORITHM_REGISTRY
    for name, algo in sorted(ALGORITHM_REGISTRY.items()):
        ok, reason = algo.is_available()
        is_custom  = getattr(algo, "_is_custom", False)
        if args.available and not ok:
            continue
        if args.custom and not is_custom:
            continue
        tag    = "[custom]" if is_custom else ""
        status = "available" if ok else f"unavailable — {reason}"
        ver    = algo.version if hasattr(algo, "version") else "?"
        print(f"  {name:<30}  {ver:<8}  {status}  {tag}")
    print(f"\n({len(ALGORITHM_REGISTRY)} registered)")


def cmd_algos_add(args: argparse.Namespace) -> None:
    print("ember algos add: not yet implemented.")


def cmd_algos_remove(args: argparse.Namespace) -> None:
    print("ember algos remove: not yet implemented.")


def cmd_algos_validate(args: argparse.Namespace) -> None:
    print("ember algos validate: not yet implemented.")


def cmd_algos_template(args: argparse.Namespace) -> None:
    print(_ALGO_TEMPLATE)


def cmd_algos_reset(args: argparse.Namespace) -> None:
    print("ember algos reset: not yet implemented.")


def cmd_algos_dir(args: argparse.Namespace) -> None:
    from ember_qc._paths import get_user_algo_dir
    print(get_user_algo_dir())


_ALGO_TEMPLATE = '''\
"""
Custom embedding algorithm template for ember-qc.
"""
from ember_qc.registry import EmbeddingAlgorithm, register_algorithm


@register_algorithm("my-algorithm")
class MyAlgorithm(EmbeddingAlgorithm):
    """Short description of your algorithm."""

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        seed = kwargs.get("seed", 42)
        embedding = {}
        if not embedding:
            return {"embedding": {}, "status": "FAILURE"}
        return {"embedding": embedding}
'''


# ---------------------------------------------------------------------------
# ember config
# ---------------------------------------------------------------------------

def cmd_config_show(args: argparse.Namespace) -> None:
    from ember_qc.config import show
    state = show()
    print(f"{'Key':<20}  {'Value':<30}  {'Source':<10}  Env var")
    print("-" * 80)
    for key, info in state.items():
        val  = str(info["value"]) if info["value"] is not None else "null"
        src  = info["source"]
        env  = info["env_var"]
        flag = "  *" if src == "env" else ""
        print(f"  {key:<20}  {val:<30}  {src:<10}  {env}{flag}")
    print("\n* = environment variable override active")


def cmd_config_get(args: argparse.Namespace) -> None:
    from ember_qc.config import get
    try:
        val = get(args.key)
        print(val if val is not None else "null")
    except ValueError as e:
        print(f"error: {e}")
        sys.exit(1)


def cmd_config_set(args: argparse.Namespace) -> None:
    from ember_qc.config import set_value, CONFIG_SCHEMA
    key = args.key
    raw = args.value
    if key not in CONFIG_SCHEMA:
        valid = ", ".join(sorted(CONFIG_SCHEMA))
        print(f"error: unknown key '{key}'. Valid keys: {valid}")
        sys.exit(1)
    expected = CONFIG_SCHEMA[key]["type"]
    try:
        if isinstance(expected, tuple) and type(None) in expected:
            if raw.lower() in ("null", "none", ""):
                coerced = None
            else:
                non_none = [t for t in expected if t is not type(None)]
                coerced  = non_none[0](raw) if non_none else raw
        elif expected is bool:
            coerced = raw.lower() in ("true", "1", "yes")
        else:
            coerced = expected(raw)
    except (ValueError, TypeError):
        tn = (expected.__name__ if not isinstance(expected, tuple)
              else " | ".join(t.__name__ for t in expected))
        print(f"error: '{key}' expects {tn}, got: {raw!r}")
        sys.exit(1)
    set_value(key, coerced)
    print(f"{key} = {coerced}")


def cmd_config_reset(args: argparse.Namespace) -> None:
    from ember_qc.config import reset, get_config_path
    path = get_config_path()
    if not path.exists():
        print("Nothing to reset (no config file exists).")
        return
    confirm = input(f"Delete {path}? This resets all keys to defaults. [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return
    reset()
    print("Config reset.")


def cmd_config_path(args: argparse.Namespace) -> None:
    from ember_qc.config import get_config_path
    print(get_config_path())


# ---------------------------------------------------------------------------
# ember install-binary
# ---------------------------------------------------------------------------

def cmd_install_binary(args: argparse.Namespace) -> None:
    from ember_qc._install_binary import install_binary
    if args.name is None:
        from ember_qc._install_binary import list_binaries
        list_binaries()
        return
    install_binary(
        name=args.name,
        version=getattr(args, "binary_version", None),
        force=getattr(args, "force", False),
    )


def cmd_install_binary_list(args: argparse.Namespace) -> None:
    from ember_qc._install_binary import list_binaries
    list_binaries()


# ---------------------------------------------------------------------------
# ember doctor
# ---------------------------------------------------------------------------

def cmd_doctor(args: argparse.Namespace) -> None:
    """Diagnose binary algorithm availability and correctness on this machine."""
    import platform
    import shutil
    import subprocess
    import time
    from pathlib import Path

    import dwave_networkx as dnx
    import networkx as nx

    from ember_qc import __version__
    from ember_qc.registry import ALGORITHM_REGISTRY

    _OK  = "✓"
    _BAD = "✗"
    _sys = platform.system()
    _mach = platform.machine()

    print("ember doctor — system diagnostics")
    print("=" * 54)
    print(f"  Platform : {_sys} {_mach}")
    print(f"  Python   : {platform.python_version()}")
    print(f"  ember-qc : {__version__}")
    print()

    # Tiny smoke-test graphs: K4 embeds into any C(4,4,*) easily.
    _source = nx.complete_graph(4)
    _target = dnx.chimera_graph(4, 4, 4)

    # Track which binary paths we've already run the ldd/file checks on so
    # we don't repeat for every OCT variant.
    _checked_binaries: set = set()

    algo_filter = getattr(args, 'algo', None)
    any_printed = False

    for name, cls in sorted(ALGORITHM_REGISTRY.items()):
        if algo_filter and name != algo_filter:
            continue

        ok, reason = cls.is_available()
        uses_subprocess = getattr(cls, '_uses_subprocess', False)

        if not uses_subprocess:
            sym = _OK if ok else _BAD
            suffix = "" if ok else f": {reason}"
            print(f"  {name:<22} {sym} pure Python{suffix}")
            any_printed = True
            continue

        # --- subprocess-based binary algorithm ---
        any_printed = True
        print(f"\n  {name}")

        # Resolve binary path
        binary_fn = getattr(cls, '_binary', None)
        binary_path: Path | None = None
        if callable(binary_fn):
            binary_path = Path(binary_fn())
        elif binary_fn is not None:
            binary_path = Path(binary_fn)

        if binary_path is None:
            print(f"    binary      : unknown")
        else:
            print(f"    binary      : {binary_path}")

            if not binary_path.exists():
                print(f"    status      : {_BAD} binary not found")
                install_name = name.split('_')[0]
                print(f"    fix         : ember install-binary {install_name}")
                continue

            bp_str = str(binary_path)

            # Architecture + shared-library checks (once per unique binary)
            if bp_str not in _checked_binaries:
                _checked_binaries.add(bp_str)

                # `file` — architecture
                if shutil.which("file"):
                    r = subprocess.run(["file", bp_str],
                                       capture_output=True, text=True)
                    file_out = r.stdout.strip()
                    # Decide if the arch matches
                    arch_ok = True
                    lo = file_out.lower()
                    if _sys == "Linux":
                        if "x86-64" in file_out and _mach not in ("x86_64", "amd64"):
                            arch_ok = False
                        elif "aarch64" in lo and _mach not in ("arm64", "aarch64"):
                            arch_ok = False
                        elif "arm" in lo and "aarch64" not in lo and _mach == "x86_64":
                            arch_ok = False
                    elif _sys == "Darwin":
                        if "arm64" in lo and _mach != "arm64":
                            arch_ok = False
                        elif "x86_64" in lo and _mach not in ("x86_64", "i386"):
                            arch_ok = False
                    sym = _OK if arch_ok else _BAD
                    print(f"    architecture: {sym} {file_out}")
                    if not arch_ok:
                        print(f"    fix         : reinstall binary for {_sys} {_mach}")

                # Shared library check
                if _sys == "Linux" and shutil.which("ldd"):
                    r = subprocess.run(["ldd", bp_str],
                                       capture_output=True, text=True)
                    missing = [ln.strip() for ln in r.stdout.splitlines()
                               if "not found" in ln.lower()]
                    if missing:
                        print(f"    ldd         : {_BAD} missing shared libraries:")
                        for m in missing:
                            print(f"                  {m}")
                        if any("libgomp" in m for m in missing):
                            print(f"                  fix: sudo apt install libgomp1")
                        if any("libstdc++" in m for m in missing):
                            print(f"                  fix: sudo apt install libstdc++6")
                    else:
                        print(f"    ldd         : {_OK} all shared libraries found")
                elif _sys == "Darwin" and shutil.which("otool"):
                    r = subprocess.run(["otool", "-L", bp_str],
                                       capture_output=True, text=True)
                    lines = [ln.strip() for ln in r.stdout.splitlines()[1:]
                             if ln.strip()]
                    missing = [ln for ln in lines if "not found" in ln.lower()]
                    if missing:
                        print(f"    otool       : {_BAD} missing dylibs:")
                        for m in missing:
                            print(f"                  {m}")
                    else:
                        print(f"    otool -L    : {_OK} {len(lines)} dylib(s) found")

                # Writable working directory (OCT writes temp files there)
                work_dir = binary_path.parent.parent  # oct_dir convention
                can_write = os.access(str(work_dir), os.W_OK)
                sym = _OK if can_write else _BAD
                print(f"    work dir    : {sym} {'writable' if can_write else 'NOT writable'} ({work_dir})")

        # --- Smoke test: embed K4 into C(4,4,4) ---
        print(f"    smoke test  : ", end="", flush=True)
        try:
            t0 = time.monotonic()
            instance = cls()
            result = instance.embed(_source, _target, timeout=30.0)
            elapsed = time.monotonic() - t0
            emb = result.get('embedding') or {}
            status = result.get('status', 'FAILURE')
            error  = result.get('error', '')
            if emb:
                print(f"{_OK} embedded K4 → C(4,4,4) in {elapsed:.2f}s")
            else:
                detail = f": {error}" if error else ""
                print(f"{_BAD} {status}{detail}")
        except Exception as exc:
            print(f"{_BAD} exception: {exc}")

    if not any_printed:
        print(f"  (no algorithms match filter {algo_filter!r})")

    print()
    print("Done.")


# ---------------------------------------------------------------------------
# ember version
# ---------------------------------------------------------------------------

def cmd_version(args: argparse.Namespace) -> None:
    from ember_qc import __version__
    print(f"ember-qc {__version__}")


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ember",
        description="ember-qc — quantum minor-embedding benchmark suite",
    )
    parser.set_defaults(func=lambda _: parser.print_help())
    sub = parser.add_subparsers(dest="command")

    # -- version -------------------------------------------------------------
    p_ver = sub.add_parser("version", help="print package version")
    p_ver.set_defaults(func=cmd_version)

    # -- run -----------------------------------------------------------------
    p_run = sub.add_parser("run", help="run a benchmark")
    p_run.add_argument("experiment", nargs="?", metavar="experiment.yaml")
    p_run.add_argument("--graphs",      metavar="SPEC",  default=None)
    p_run.add_argument("--algorithms",  metavar="NAMES", default=None)
    p_run.add_argument("--topologies",  metavar="NAMES", default=None)
    p_run.add_argument("--trials",      type=int,        default=None)
    p_run.add_argument("--warmup",      type=int,        default=None)
    p_run.add_argument("--timeout",     type=float,      default=None)
    p_run.add_argument("--seed",        type=int,        default=None)
    p_run.add_argument("--workers",     type=int,        default=None)
    p_run.add_argument("--fault-rate",  type=float,      default=None, dest="fault_rate")
    p_run.add_argument("--fault-seed",  type=int,        default=None, dest="fault_seed")
    p_run.add_argument("--output-dir",  metavar="PATH",  default=None, dest="output_dir")
    p_run.add_argument("--note",        metavar="TEXT",  default=None)
    p_run.add_argument("--analyze",     action="store_true", default=False)
    vg = p_run.add_mutually_exclusive_group()
    vg.add_argument("--verbose",    dest="verbose", action="store_const", const=True,  default=None)
    vg.add_argument("--no-verbose", dest="verbose", action="store_const", const=False)
    p_run.set_defaults(func=cmd_run)

    # -- resume --------------------------------------------------------------
    p_res = sub.add_parser("resume", help="resume or manage unfinished benchmarks")
    p_res.add_argument("batch_id", nargs="?", metavar="BATCH_ID")
    p_res.add_argument("--workers",    type=int, default=None)
    p_res.add_argument("--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_res.add_argument("--analyze",    action="store_true", default=False)
    p_res.add_argument("--delete",     action="store_true", default=False)
    p_res.add_argument("--delete-all", action="store_true", default=False, dest="delete_all")
    rvg = p_res.add_mutually_exclusive_group()
    rvg.add_argument("--verbose",    dest="verbose", action="store_const", const=True,  default=None)
    rvg.add_argument("--no-verbose", dest="verbose", action="store_const", const=False)
    p_res.set_defaults(func=cmd_resume)

    # -- graphs --------------------------------------------------------------
    p_graphs = sub.add_parser("graphs", help="browse and manage the graph library")
    gs = p_graphs.add_subparsers(dest="graphs_cmd")
    p_graphs.set_defaults(func=lambda _: p_graphs.print_help())

    # list [TYPE] [-a]
    p_gl = gs.add_parser("list",
                         help="list graph types or graphs within a type")
    p_gl.add_argument("category", nargs="?", metavar="TYPE", default=None,
                      help="graph type to drill into (e.g. complete, random_er)")
    p_gl.add_argument("-a", "--installed", action="store_true", default=False,
                      help="show only installed graphs / types")
    p_gl.set_defaults(func=cmd_graphs_list)

    # info <ID>
    p_gi = gs.add_parser("info", help="full metadata for a single graph")
    p_gi.add_argument("graph_id", type=int, metavar="ID")
    p_gi.set_defaults(func=cmd_graphs_info)

    # install <SPEC> [--dry-run]
    p_ginstall = gs.add_parser("install", help="download graphs to local cache")
    p_ginstall.add_argument("selection", nargs="?", metavar="SPEC/PRESET",
                             help="ID range, selection string, or preset name")
    p_ginstall.add_argument("--dry-run", action="store_true", default=False,
                             dest="dry_run")
    p_ginstall.set_defaults(func=cmd_graphs_install)

    # presets
    p_gp = gs.add_parser("presets", help="list named graph presets")
    p_gp.set_defaults(func=cmd_graphs_presets)

    # verify [--fix]
    p_gv = gs.add_parser("verify",
                         help="verify cached graphs against manifest hashes")
    p_gv.add_argument("--fix", action="store_true", default=False,
                      help="re-download corrupt files automatically")
    p_gv.set_defaults(func=cmd_graphs_verify)

    # search
    p_gs = gs.add_parser("search",
                         help="filter graphs by property (manifest only, no download)")
    p_gs.add_argument("--type",      metavar="TYPE", default=None, dest="type")
    p_gs.add_argument("--topology",  metavar="TOPO", default=None)
    p_gs.add_argument("--min-nodes", metavar="N",    type=int, default=None, dest="min_nodes")
    p_gs.add_argument("--max-nodes", metavar="N",    type=int, default=None, dest="max_nodes")
    p_gs.add_argument("--min-edges", metavar="N",    type=int, default=None, dest="min_edges")
    p_gs.add_argument("--max-edges", metavar="N",    type=int, default=None, dest="max_edges")
    p_gs.add_argument("-a", "--installed", action="store_true", default=False)
    p_gs.set_defaults(func=cmd_graphs_search)

    # cache [delete]
    p_gc = gs.add_parser("cache", help="cache summary and management")
    gcs  = p_gc.add_subparsers(dest="cache_cmd")
    p_gc.set_defaults(func=cmd_graphs_cache)

    p_gcd = gcs.add_parser("delete", help="remove graphs from cache")
    p_gcd.add_argument("selection", nargs="?", metavar="SPEC")
    p_gcd.add_argument("--all", action="store_true", default=False)
    p_gcd.set_defaults(func=cmd_graphs_cache_delete)

    # -- topologies ----------------------------------------------------------
    p_topos = sub.add_parser("topologies", help="list hardware topologies")
    ts = p_topos.add_subparsers(dest="topos_cmd")
    p_topos.set_defaults(func=lambda _: p_topos.print_help())

    p_tl = ts.add_parser("list", help="list registered topologies")
    p_tl.add_argument("--family", metavar="FAMILY", default=None)
    p_tl.set_defaults(func=cmd_topologies_list)

    p_ti = ts.add_parser("info", help="full topology table")
    p_ti.set_defaults(func=cmd_topologies_info)

    # -- results -------------------------------------------------------------
    p_results = sub.add_parser("results", help="inspect completed batches")
    rs = p_results.add_subparsers(dest="results_cmd")
    p_results.set_defaults(func=lambda _: p_results.print_help())

    p_rl = rs.add_parser("list", help="list completed batches")
    p_rl.add_argument("--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_rl.set_defaults(func=cmd_results_list)

    p_rs = rs.add_parser("show", help="print summary for a batch")
    p_rs.add_argument("batch_id")
    p_rs.add_argument("--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_rs.set_defaults(func=cmd_results_show)

    p_rd = rs.add_parser("delete", help="delete a batch")
    p_rd.add_argument("batch_id")
    p_rd.add_argument("--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_rd.set_defaults(func=cmd_results_delete)

    # -- algos ---------------------------------------------------------------
    p_algos = sub.add_parser("algos", help="manage algorithms")
    als = p_algos.add_subparsers(dest="algos_cmd")
    p_algos.set_defaults(func=lambda _: p_algos.print_help())

    p_al = als.add_parser("list", help="list registered algorithms")
    p_al.add_argument("--available", action="store_true")
    p_al.add_argument("--custom",    action="store_true")
    p_al.set_defaults(func=cmd_algos_list)

    p_aa = als.add_parser("add",      help="add a custom algorithm file")
    p_aa.add_argument("file")
    p_aa.set_defaults(func=cmd_algos_add)

    p_arm = als.add_parser("remove",  help="remove a custom algorithm")
    p_arm.add_argument("name")
    p_arm.set_defaults(func=cmd_algos_remove)

    p_av = als.add_parser("validate", help="validate against the algorithm contract")
    p_av.add_argument("file")
    p_av.set_defaults(func=cmd_algos_validate)

    p_at = als.add_parser("template", help="print an algorithm template")
    p_at.set_defaults(func=cmd_algos_template)

    p_ar = als.add_parser("reset",    help="remove all custom algorithms")
    p_ar.set_defaults(func=cmd_algos_reset)

    p_ad = als.add_parser("dir",      help="print custom algorithms directory")
    p_ad.set_defaults(func=cmd_algos_dir)

    # -- config --------------------------------------------------------------
    p_config = sub.add_parser("config", help="manage persistent configuration")
    cs = p_config.add_subparsers(dest="config_cmd")
    p_config.set_defaults(func=lambda _: p_config.print_help())

    cs.add_parser("show",  help="show all config keys").set_defaults(func=cmd_config_show)

    p_cget = cs.add_parser("get", help="print value for a key")
    p_cget.add_argument("key")
    p_cget.set_defaults(func=cmd_config_get)

    p_cset = cs.add_parser("set", help="set a config value")
    p_cset.add_argument("key")
    p_cset.add_argument("value")
    p_cset.set_defaults(func=cmd_config_set)

    cs.add_parser("reset", help="reset all keys to defaults").set_defaults(func=cmd_config_reset)
    cs.add_parser("path",  help="print path to config file").set_defaults(func=cmd_config_path)

    # -- doctor --------------------------------------------------------------
    p_doc = sub.add_parser(
        "doctor",
        help="check binary algorithms are installed and working on this machine",
    )
    p_doc.add_argument(
        "--algo", metavar="NAME", default=None,
        help="restrict check to one algorithm (default: all)",
    )
    p_doc.set_defaults(func=cmd_doctor)

    # -- install-binary ------------------------------------------------------
    p_ib = sub.add_parser("install-binary",
                          help="download and install pre-built C++ binaries")
    p_ib.add_argument("name", nargs="?", choices=["atom", "oct"])
    p_ib.add_argument("--version", metavar="X.Y.Z", dest="binary_version", default=None)
    p_ib.add_argument("--force",   action="store_true", default=False)
    p_ib.add_argument("--list",    action="store_true", dest="list_binaries")
    p_ib.set_defaults(func=lambda args: cmd_install_binary_list(args)
                      if args.list_binaries else cmd_install_binary(args))

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
