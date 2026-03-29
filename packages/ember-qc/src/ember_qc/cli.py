"""
ember_qc/cli.py
===============
Command-line interface for ember-qc.

Entry point: `ember-qc` (configured in pyproject.toml).

Subcommand groups:
  ember run          — run a benchmark (from YAML or flags)
  ember resume       — resume an unfinished benchmark
  ember graphs       — list test graphs and presets
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
# YAML helpers (PyYAML is not a declared dependency — degrade gracefully)
# ---------------------------------------------------------------------------

import yaml


def _load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _resolved_yaml_name(yaml_path: Optional[Path]) -> str:
    """Return the filename for the resolved YAML."""
    if yaml_path is None:
        return "experiment_resolved.yaml"
    stem = yaml_path.stem
    return f"{stem}_resolved.yaml"


def _build_resolved_params(args: argparse.Namespace, yaml_params: dict) -> dict:
    """
    Merge YAML params with CLI flag overrides into a clean reproducible dict.
    CLI flags that were not explicitly set (still at their argparse default)
    do not override YAML values.
    """
    # Start from YAML (or empty if no YAML)
    p = dict(yaml_params)

    # Apply CLI overrides only when explicitly provided
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
    }
    for key, val in cli_overrides.items():
        if val is not None:
            p[key] = val

    # Normalise algorithms to a list
    if "algorithms" in p and isinstance(p["algorithms"], str):
        p["algorithms"] = [a.strip() for a in p["algorithms"].split(",")]

    # Normalise topologies to a list
    if "topologies" in p and isinstance(p["topologies"], str):
        p["topologies"] = [t.strip() for t in p["topologies"].split(",")]

    # Fill in fallbacks: user config (stored/env) then package defaults.
    # config.get() already implements the env-var → stored → default chain.
    from ember_qc.config import get as _cfg
    p.setdefault("algorithms",      None)    # None → all registered
    p.setdefault("graphs",          _cfg("default_graphs") or "*")
    p.setdefault("topologies",      _cfg("default_topology"))
    p.setdefault("n_trials",        _cfg("default_n_trials"))
    p.setdefault("warmup_trials",   _cfg("default_warmup_trials"))
    p.setdefault("timeout",         _cfg("default_timeout"))
    p.setdefault("seed",            _cfg("default_seed"))
    p.setdefault("n_workers",       _cfg("default_workers"))
    p.setdefault("fault_rate",      _cfg("default_fault_rate"))
    p.setdefault("fault_seed",      None)
    p.setdefault("faulty_nodes",    None)
    p.setdefault("faulty_couplers", None)
    p.setdefault("note",            "")
    p.setdefault("output_dir",      _cfg("output_dir"))
    p.setdefault("analyze",         False)

    # default_topology from config is a single string; normalise to list
    if "topologies" in p and isinstance(p["topologies"], str):
        p["topologies"] = [t.strip() for t in p["topologies"].split(",")]

    return p


def _write_resolved_yaml(params: dict, final_dir: Path, yaml_path: Optional[Path],
                         actual_warmup: Optional[int] = None) -> None:
    """
    Write the resolved experiment YAML to final_dir.

    actual_warmup: if run_full_benchmark zeroed warmup_trials (n_workers > 1),
                   pass the actual value used so the YAML is accurate.
    """
    resolved = {k: v for k, v in params.items()
                if k not in ("output_dir",)}   # output_dir is bookkeeping, not an input

    if actual_warmup is not None:
        resolved["warmup_trials"] = actual_warmup

    out_name = _resolved_yaml_name(yaml_path)
    _write_yaml(resolved, final_dir / out_name)


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

    # Resolve topologies → list of (label, graph, name)
    topo_names = params["topologies"] or list_topologies()
    topo_list = []
    for name in topo_names:
        try:
            g = get_topology(name)
            topo_list.append((name, g, name))
        except KeyError:
            print(f"error: unknown topology '{name}'. Run: ember topologies list")
            sys.exit(1)

    # Use first topology's graph as the target_graph for EmbeddingBenchmark.
    # run_full_benchmark handles the full topo_list internally.
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
    )

    if final_dir is None:
        # Cancelled — batch is in runs_unfinished/, no output dir yet
        return

    # Copy original YAML verbatim
    if yaml_path is not None:
        shutil.copy2(yaml_path, final_dir / yaml_path.name)

    # warmup may have been zeroed by run_full_benchmark when n_workers > 1
    actual_warmup = 0 if (n_workers > 1 and warmup_trials > 0) else warmup_trials
    _write_resolved_yaml(params, final_dir, yaml_path, actual_warmup=actual_warmup)

    print(f"Results: {final_dir}")


# ---------------------------------------------------------------------------
# ember resume
# ---------------------------------------------------------------------------

def cmd_resume(args: argparse.Namespace) -> None:
    from ember_qc.benchmark import load_benchmark, delete_benchmark
    from ember_qc._paths import get_user_unfinished_dir
    from ember_qc.checkpoint import scan_incomplete_runs

    if args.delete_all:
        unfinished_dir = get_user_unfinished_dir()
        runs = scan_incomplete_runs(unfinished_dir)
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
            delete_benchmark(batch_id=r["batch_id"], force=True)
        return

    if args.delete:
        delete_benchmark(batch_id=args.batch_id or None)
        return

    load_benchmark(
        batch_id=args.batch_id or None,
        n_workers=args.workers or None,
        output_dir=args.output_dir or None,
    )


# ---------------------------------------------------------------------------
# ember graphs
# ---------------------------------------------------------------------------

def cmd_graphs_list(args: argparse.Namespace) -> None:
    from ember_qc.load_graphs import list_test_graphs, parse_graph_selection

    graphs = list_test_graphs()
    if not graphs:
        print("No test graphs found. Check your test_graphs/ directory.")
        return

    if args.filter:
        try:
            ids = parse_graph_selection(args.filter)
            graphs = [g for g in graphs if g["id"] in ids]
        except Exception as e:
            print(f"error parsing filter '{args.filter}': {e}")
            sys.exit(1)

    print(f"{'ID':>6}  {'Name':<40}  {'Nodes':>6}  {'Edges':>7}")
    print("-" * 65)
    for g in graphs:
        print(f"{g['id']:>6}  {g['name']:<40}  {g.get('nodes', '?'):>6}  {g.get('edges', '?'):>7}")
    print(f"\n{len(graphs)} graph(s)")


def cmd_graphs_presets(args: argparse.Namespace) -> None:
    from ember_qc.load_graphs import list_presets
    presets = list_presets()
    if not presets:
        print("No presets found.")
        return
    print(f"{'Preset':<20}  Selection")
    print("-" * 60)
    for name, spec in sorted(presets.items()):
        print(f"{name:<20}  {spec}")


def cmd_graphs_status(_: argparse.Namespace) -> None:
    print("ember graphs status: not yet implemented")


def cmd_graphs_fetch(_: argparse.Namespace) -> None:
    print("ember graphs fetch: not yet implemented")


def cmd_graphs_cache_list(_: argparse.Namespace) -> None:
    print("ember graphs cache list: not yet implemented")


def cmd_graphs_cache_size(_: argparse.Namespace) -> None:
    print("ember graphs cache size: not yet implemented")


def cmd_graphs_cache_clear(_: argparse.Namespace) -> None:
    print("ember graphs cache clear: not yet implemented")


def cmd_graphs_cache_verify(_: argparse.Namespace) -> None:
    print("ember graphs cache verify: not yet implemented")


# ---------------------------------------------------------------------------
# ember topologies
# ---------------------------------------------------------------------------

def cmd_topologies_list(args: argparse.Namespace) -> None:
    from ember_qc.topologies import list_topologies, get_topology_config

    names = list_topologies(family=args.family or None)
    if not names:
        msg = f"No topologies found" + (f" for family '{args.family}'" if args.family else "")
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
            algos = ", ".join(cfg.get("algorithms", []))[:28]
            trials = cfg.get("total_measured_runs", "?")
        else:
            algos = "?"
            trials = "?"
        print(f"{b.name:<35}  {algos:<30}  {str(trials):>7}")

    print(f"\n{len(batches)} batch(es) in {results_dir.resolve()}")


def cmd_results_show(args: argparse.Namespace) -> None:
    results_dir = _find_results_dir(args)
    batch_dir = results_dir / args.batch_id
    if not batch_dir.exists():
        print(f"error: batch not found: {batch_dir}")
        sys.exit(1)

    summary = batch_dir / "summary.csv"
    config_path = batch_dir / "config.json"

    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        print("=== Config ===")
        for k, v in cfg.items():
            if k not in ("custom_problems",):   # skip large serialised graphs
                print(f"  {k}: {v}")
        print()

    if summary.exists():
        print("=== Summary ===")
        print(summary.read_text())
    else:
        print("No summary.csv found.")


def cmd_results_delete(args: argparse.Namespace) -> None:
    results_dir = _find_results_dir(args)
    batch_dir = results_dir / args.batch_id
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
        is_custom = getattr(algo, "_is_custom", False)

        if args.available and not ok:
            continue
        if args.custom and not is_custom:
            continue

        tag = "[custom]" if is_custom else ""
        status = "available" if ok else f"unavailable — {reason}"
        ver = algo.version if hasattr(algo, "version") else "?"
        print(f"  {name:<30}  {ver:<8}  {status}  {tag}")

    print(f"\n({len(ALGORITHM_REGISTRY)} registered)")


def cmd_algos_add(args: argparse.Namespace) -> None:
    print("ember algos add: not yet implemented (custom algorithm registration pending).")
    print("See: TODO_userConfig.md §3")


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

Contract:
  - Subclass EmbeddingAlgorithm and implement embed().
  - Return {'embedding': {node: [qubits], ...}} on success.
  - Return {'embedding': {}, 'status': 'FAILURE'} on failure.
  - Never return None.
  - Register with @register_algorithm("your-algo-name").
"""
from ember_qc.registry import EmbeddingAlgorithm, register_algorithm


@register_algorithm("my-algorithm")
class MyAlgorithm(EmbeddingAlgorithm):
    """Short description of your algorithm."""

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, **kwargs):
        timeout = kwargs.get("timeout", 60.0)
        seed = kwargs.get("seed", 42)

        # Your embedding logic here.
        # source_graph: networkx.Graph — the logical problem graph
        # target_graph: networkx.Graph — the hardware topology graph
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
        val = str(info["value"]) if info["value"] is not None else "null"
        src = info["source"]
        env = info["env_var"]
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

    # Coerce the string value to the expected type
    expected = CONFIG_SCHEMA[key]["type"]
    try:
        if isinstance(expected, tuple) and type(None) in expected:
            if raw.lower() in ("null", "none", ""):
                coerced = None
            else:
                non_none = [t for t in expected if t is not type(None)]
                coerced = non_none[0](raw) if non_none else raw
        elif expected is bool:
            coerced = raw.lower() in ("true", "1", "yes")
        else:
            coerced = expected(raw)
    except (ValueError, TypeError):
        tn = expected.__name__ if not isinstance(expected, tuple) else " | ".join(t.__name__ for t in expected)
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
        # No binary name and no --list: show status table as a helpful default.
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
    p_run.add_argument("experiment", nargs="?", metavar="experiment.yaml",
                       help="YAML experiment file (optional)")
    p_run.add_argument("--graphs",      metavar="SPEC",    default=None)
    p_run.add_argument("--algorithms",  metavar="NAMES",   default=None,
                       help="comma-separated algorithm names")
    p_run.add_argument("--topologies",  metavar="NAMES",   default=None,
                       help="comma-separated topology names")
    p_run.add_argument("--trials",      type=int,          default=None)
    p_run.add_argument("--warmup",      type=int,          default=None)
    p_run.add_argument("--timeout",     type=float,        default=None)
    p_run.add_argument("--seed",        type=int,          default=None)
    p_run.add_argument("--workers",     type=int,          default=None)
    p_run.add_argument("--fault-rate",  type=float,        default=None, dest="fault_rate")
    p_run.add_argument("--fault-seed",  type=int,          default=None, dest="fault_seed")
    p_run.add_argument("--output-dir",  metavar="PATH",    default=None, dest="output_dir")
    p_run.add_argument("--note",        metavar="TEXT",    default=None)
    p_run.add_argument("--analyze",     action="store_true", default=False,
                       help="run ember-qc-analysis on the completed batch")
    p_run.set_defaults(func=cmd_run)

    # -- resume --------------------------------------------------------------
    p_res = sub.add_parser("resume", help="resume or manage unfinished benchmarks")
    p_res.add_argument("batch_id", nargs="?", metavar="BATCH_ID",
                       help="batch directory name; omit to select interactively")
    p_res.add_argument("--workers",    type=int, default=None)
    p_res.add_argument("--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_res.add_argument("--delete",     action="store_true", default=False,
                       help="delete an unfinished run instead of resuming it")
    p_res.add_argument("--delete-all", action="store_true", default=False,
                       dest="delete_all",
                       help="delete all unfinished runs (prompts for confirmation)")
    p_res.set_defaults(func=cmd_resume)

    # -- graphs --------------------------------------------------------------
    p_graphs = sub.add_parser("graphs", help="list test graphs and presets")
    gs = p_graphs.add_subparsers(dest="graphs_cmd")
    p_graphs.set_defaults(func=lambda _: p_graphs.print_help())

    p_gl = gs.add_parser("list", help="list available test graphs")
    p_gl.add_argument("--filter", metavar="SPEC", default=None,
                      help="selection string or preset name")
    p_gl.set_defaults(func=cmd_graphs_list)

    p_gp = gs.add_parser("presets", help="list named graph presets")
    p_gp.set_defaults(func=cmd_graphs_presets)

    p_gst = gs.add_parser("status", help="show graph library status [stub]")
    p_gst.set_defaults(func=cmd_graphs_status)

    p_gf = gs.add_parser("fetch", help="pre-download graphs to local cache [stub]")
    p_gf.add_argument("selection", nargs="?", metavar="SPEC", default=None)
    p_gf.add_argument("--preset", metavar="NAME", default=None)
    p_gf.add_argument("--type",   metavar="TYPE", default=None)
    p_gf.add_argument("--all",    action="store_true", default=False)
    p_gf.set_defaults(func=cmd_graphs_fetch)

    p_gc = gs.add_parser("cache", help="manage local graph cache [stub]")
    gcs  = p_gc.add_subparsers(dest="cache_cmd")
    p_gc.set_defaults(func=lambda _: p_gc.print_help())

    p_gcl = gcs.add_parser("list",   help="list cached graphs [stub]")
    p_gcl.set_defaults(func=cmd_graphs_cache_list)

    p_gcsz = gcs.add_parser("size",  help="show cache disk usage [stub]")
    p_gcsz.set_defaults(func=cmd_graphs_cache_size)

    p_gcc = gcs.add_parser("clear",  help="delete cached graphs [stub]")
    p_gcc.add_argument("selection", nargs="?", metavar="SPEC", default=None)
    p_gcc.set_defaults(func=cmd_graphs_cache_clear)

    p_gcv = gcs.add_parser("verify", help="verify cached graph hashes [stub]")
    p_gcv.set_defaults(func=cmd_graphs_cache_verify)

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
    p_al.add_argument("--available", action="store_true", help="available only")
    p_al.add_argument("--custom",    action="store_true", help="custom only")
    p_al.set_defaults(func=cmd_algos_list)

    p_aa = als.add_parser("add",      help="add a custom algorithm file")
    p_aa.add_argument("file")
    p_aa.set_defaults(func=cmd_algos_add)

    p_arm = als.add_parser("remove",  help="remove a custom algorithm")
    p_arm.add_argument("name")
    p_arm.set_defaults(func=cmd_algos_remove)

    p_av = als.add_parser("validate", help="validate a file against the algorithm contract")
    p_av.add_argument("file")
    p_av.set_defaults(func=cmd_algos_validate)

    p_at = als.add_parser("template", help="print an algorithm template to stdout")
    p_at.set_defaults(func=cmd_algos_template)

    p_ar = als.add_parser("reset",    help="remove all custom algorithms")
    p_ar.set_defaults(func=cmd_algos_reset)

    p_ad = als.add_parser("dir",      help="print custom algorithms directory")
    p_ad.set_defaults(func=cmd_algos_dir)

    # -- config --------------------------------------------------------------
    p_config = sub.add_parser("config", help="manage persistent configuration")
    cs = p_config.add_subparsers(dest="config_cmd")
    p_config.set_defaults(func=lambda _: p_config.print_help())

    p_cshow = cs.add_parser("show",  help="show all config keys and their sources")
    p_cshow.set_defaults(func=cmd_config_show)

    p_cget = cs.add_parser("get",    help="print the resolved value for a key")
    p_cget.add_argument("key")
    p_cget.set_defaults(func=cmd_config_get)

    p_cset = cs.add_parser("set",    help="set a config value")
    p_cset.add_argument("key")
    p_cset.add_argument("value")
    p_cset.set_defaults(func=cmd_config_set)

    p_creset = cs.add_parser("reset", help="delete config file, revert to defaults")
    p_creset.set_defaults(func=cmd_config_reset)

    p_cpath = cs.add_parser("path",  help="print path to config file")
    p_cpath.set_defaults(func=cmd_config_path)

    # -- install-binary ------------------------------------------------------
    p_ib = sub.add_parser("install-binary",
                          help="download and install pre-built C++ binaries")
    p_ib.add_argument("name", nargs="?", choices=["atom", "oct"],
                      help="binary to install (atom or oct)")
    p_ib.add_argument("--version", metavar="X.Y.Z", dest="binary_version",
                      default=None,
                      help="pin a specific release version (default: latest)")
    p_ib.add_argument("--force", action="store_true", default=False,
                      help="overwrite an already-installed binary")
    p_ib.add_argument("--list", action="store_true", dest="list_binaries",
                      help="show all binaries and their install status")
    p_ib.set_defaults(func=lambda args: cmd_install_binary_list(args)
                      if args.list_binaries else cmd_install_binary(args))

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
