"""
ember_qc_analysis/cli.py
=========================
Command-line interface for ember-qc-analysis.

Entry points: `ember-analysis` and `ember-a` (both call main()).

Subcommands:
  ember-analysis stage <batch_dir>       — set active batch context
  ember-analysis unstage                 — clear active batch context
  ember-analysis report                  — run full analysis pipeline
  ember-analysis plots [GROUP...]        — run plot generation
  ember-analysis tables                  — run summary table generation
  ember-analysis stats                   — run statistical analysis
  ember-analysis batches list            — list batches in input_dir
  ember-analysis batches show <batch_id> — show batch summary
  ember-analysis config show/get/set/reset/path
  ember-analysis version
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ember_qc_analysis._config import (
    DEFAULTS, ENV_VARS, load_config, set_config, get_config, reset_config,
    resolve, resolve_input_dir, get_output_dir,
    is_valid_batch, validate_batch,
)
from ember_qc_analysis._paths import get_user_config_path


# ---------------------------------------------------------------------------
# Plot groups
# ---------------------------------------------------------------------------

PLOT_GROUPS = {
    "distributions": "Embedding metric distributions",
    "scaling":       "Performance scaling with graph size",
    "pairwise":      "Algorithm pairwise comparisons",
    "success":       "Success rate analysis",
    "graph-indexed": "Metrics indexed by graph ID",
    "topology":      "Performance by hardware topology",
}


# ---------------------------------------------------------------------------
# Batch resolution helpers
# ---------------------------------------------------------------------------

def _resolve_active_batch(input_dir_explicit: Optional[str] = None) -> Path:
    """
    Resolve the active batch, with fallback logic per spec §4.3.

    Priority:
      1. active_batch from config
      2. If input_dir is set and contains exactly one batch → use it
      3. If input_dir is set and contains multiple batches → error with list
      4. If input_dir is not set → ember-qc discovery prompt, then error
    """
    # 1. Staged batch
    active = resolve("active_batch")
    if active:
        p = Path(active)
        if not p.exists():
            print(f"Warning: staged batch no longer exists: {p}")
            print("Run: ember-analysis stage <path>")
            sys.exit(1)
        return p

    # 2+3+4. Fall back to input_dir
    input_dir = resolve_input_dir(explicit=input_dir_explicit, prompt=True)
    batches = [d for d in sorted(input_dir.iterdir()) if is_valid_batch(d)]

    if not batches:
        print(f"No valid batches found in: {input_dir}")
        print("Run: ember-analysis stage <batch_path>")
        sys.exit(1)

    if len(batches) == 1:
        print(f"Using batch: {batches[0].name}")
        return batches[0]

    # Multiple batches — require explicit staging
    print(f"Multiple batches found in {input_dir}. Stage one first:")
    for b in batches:
        print(f"  {b.name}")
    print("\nRun: ember-analysis stage <batch_path>")
    sys.exit(1)


def _read_batch_config(batch_dir: Path) -> dict:
    cfg_path = batch_dir / "config.json"
    if cfg_path.exists():
        try:
            with open(cfg_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _batch_status(batch_dir: Path) -> str:
    """Return 'complete' or 'incomplete' based on presence of results.db/runs.csv."""
    if (batch_dir / "results.db").exists() or (batch_dir / "runs.csv").exists():
        return "complete"
    return "incomplete"


# ---------------------------------------------------------------------------
# ember-analysis stage
# ---------------------------------------------------------------------------

def cmd_stage(args: argparse.Namespace) -> None:
    path = Path(args.batch_dir).resolve()
    try:
        validate_batch(path)
    except ValueError as e:
        print(f"error: {e}")
        sys.exit(1)

    set_config("active_batch", str(path))

    cfg = _read_batch_config(path)
    algos = ", ".join(cfg.get("algorithms", [])) or "unknown"
    graphs = cfg.get("total_measured_runs", "?")
    note = cfg.get("batch_note", "")

    print(f"Staged: {path.name}")
    print(f"  Algorithms: {algos}")
    print(f"  Trials:     {graphs}")
    if note:
        print(f"  Note:       {note}")
    print(f"  Status:     {_batch_status(path)}")


# ---------------------------------------------------------------------------
# ember-analysis unstage
# ---------------------------------------------------------------------------

def cmd_unstage(args: argparse.Namespace) -> None:
    active = resolve("active_batch")
    if active is None:
        print("No batch is currently staged.")
        return
    set_config("active_batch", None)
    print("Unstaged.")


# ---------------------------------------------------------------------------
# ember-analysis report
# ---------------------------------------------------------------------------

def cmd_report(args: argparse.Namespace) -> None:
    from ember_qc_analysis import BenchmarkAnalysis

    batch_dir = _resolve_active_batch()
    output_root = get_output_dir(batch_dir, explicit=getattr(args, "output_dir", None))
    fmt = getattr(args, "format", None) or resolve("fig_format")
    overwrite = getattr(args, "overwrite", False)

    print(f"Batch:  {batch_dir.name}")
    print(f"Output: {output_root}")

    an = BenchmarkAnalysis(str(batch_dir), output_root=str(output_root))

    if overwrite:
        an.generate_report(fmt=fmt)
    else:
        _generate_with_skip(an, fmt=fmt, groups=None, output_root=output_root)


# ---------------------------------------------------------------------------
# ember-analysis plots
# ---------------------------------------------------------------------------

def cmd_plots(args: argparse.Namespace) -> None:
    from ember_qc_analysis import BenchmarkAnalysis

    if args.list:
        print(f"{'Group':<15}  Description")
        print("-" * 55)
        for name, desc in PLOT_GROUPS.items():
            print(f"  {name:<13}  {desc}")
        return

    groups = args.groups or list(PLOT_GROUPS.keys())
    unknown = [g for g in groups if g not in PLOT_GROUPS]
    if unknown:
        print(f"error: unknown plot group(s): {', '.join(unknown)}")
        print(f"Valid groups: {', '.join(PLOT_GROUPS)}")
        sys.exit(1)

    batch_dir = _resolve_active_batch()
    output_root = get_output_dir(batch_dir, explicit=getattr(args, "output_dir", None))
    fmt = getattr(args, "format", None) or resolve("fig_format")
    overwrite = getattr(args, "overwrite", False)

    an = BenchmarkAnalysis(str(batch_dir), output_root=str(output_root))
    _generate_with_skip(an, fmt=fmt, groups=groups, output_root=output_root, overwrite=overwrite)


# ---------------------------------------------------------------------------
# ember-analysis tables
# ---------------------------------------------------------------------------

def cmd_tables(args: argparse.Namespace) -> None:
    from ember_qc_analysis import BenchmarkAnalysis

    batch_dir = _resolve_active_batch()
    output_root = get_output_dir(batch_dir, explicit=getattr(args, "output_dir", None))
    overwrite = getattr(args, "overwrite", False)

    an = BenchmarkAnalysis(str(batch_dir), output_root=str(output_root))
    summary_dir = an.summary_dir
    summary_dir.mkdir(parents=True, exist_ok=True)

    generated = skipped = 0
    try:
        tables = {
            "overall_summary": (an.overall_summary(), "Algorithm performance summary", "tab:overall_summary"),
            "rank_table_chain": (an.rank_table("avg_chain_length"), "Algorithm rank by average chain length", "tab:rank_chain"),
            "rank_table_time": (an.rank_table("wall_time"), "Algorithm rank by embedding time", "tab:rank_time"),
            "summary_by_category_chain": (an.summary_by_category("avg_chain_length"), "Mean avg chain length by graph category", "tab:category_chain"),
            "summary_by_category_time": (an.summary_by_category("wall_time"), "Mean embedding time by graph category", "tab:category_time"),
            "pairwise_comparison": (an.win_rate_matrix("avg_chain_length"), "Win rate matrix (avg chain length)", "tab:win_rate_chain"),
        }
        from ember_qc_analysis.export import df_to_latex, export_tables
        for name, (df, caption, label) in tables.items():
            csv_path = summary_dir / f"{name}.csv"
            tex_path = summary_dir / f"{name}.tex"
            if not overwrite and csv_path.exists() and tex_path.exists():
                skipped += 2
                continue
            df.to_csv(csv_path, index=True)
            tex = df_to_latex(df, caption=caption, label=label)
            tex_path.write_text(tex, encoding="utf-8")
            generated += 2
    except Exception as e:
        print(f"Tables failed: {e}")
        sys.exit(1)

    _print_summary(generated, skipped, output_root)


# ---------------------------------------------------------------------------
# ember-analysis stats
# ---------------------------------------------------------------------------

def cmd_stats(args: argparse.Namespace) -> None:
    from ember_qc_analysis import BenchmarkAnalysis

    batch_dir = _resolve_active_batch()
    output_root = get_output_dir(batch_dir, explicit=getattr(args, "output_dir", None))
    overwrite = getattr(args, "overwrite", False)

    an = BenchmarkAnalysis(str(batch_dir), output_root=str(output_root))
    stats_dir = an.statistics_dir
    stats_dir.mkdir(parents=True, exist_ok=True)

    generated = skipped = 0

    def _csv(name: str, df_fn, index=True):
        nonlocal generated, skipped
        out = stats_dir / f"{name}.csv"
        if not overwrite and out.exists():
            skipped += 1
            return
        try:
            df_fn().to_csv(out, index=index)
            generated += 1
        except Exception as e:
            print(f"  [stats] {name}: {e}")

    def _txt(name: str, fn):
        nonlocal generated, skipped
        out = stats_dir / f"{name}.txt"
        if not overwrite and out.exists():
            skipped += 1
            return
        try:
            result = fn()
            out.write_text('\n'.join(f'{k}: {v}' for k, v in result.items()) + '\n', encoding="utf-8")
            generated += 1
        except Exception as e:
            print(f"  [stats] {name}: {e}")

    _csv("significance_tests",  an.significance_tests)
    _csv("correlation_matrix",  an.correlation_matrix)
    _csv("win_rate_matrix",     lambda: an.win_rate_matrix())
    _txt("friedman_test",       an.friedman_test)

    _print_summary(generated, skipped, output_root)


# ---------------------------------------------------------------------------
# Skip-aware report generation
# ---------------------------------------------------------------------------

def _generate_with_skip(
    an,
    fmt: str,
    groups: Optional[list],
    output_root: Path,
    overwrite: bool = False,
) -> None:
    """
    Run generate_report() or a subset of plots, respecting the overwrite flag.

    For full report (groups=None), delegates to generate_report() when overwrite
    is True. When overwrite is False, we call generate_report() and let existing
    files be overwritten — generate_report() always writes. This is acceptable
    for v0.0.1; a per-file skip layer can be added when plots support it natively.
    """
    # For now, generate_report() always overwrites. We warn if --overwrite is
    # not set and the output dir already exists, so the user is informed.
    if not overwrite and output_root.exists() and any(output_root.iterdir()):
        print("Note: output directory already exists. Use --overwrite to skip this warning.")

    if groups is None:
        an.generate_report(fmt=fmt)
    else:
        # Run only the requested plot groups
        import itertools
        from ember_qc_analysis.plots import (
            build_algo_palette,
            plot_chain_distribution, plot_max_chain_distribution,
            plot_distributions, plot_heatmap, plot_consistency,
            plot_scaling, plot_density_hardness,
            plot_win_rate_matrix, plot_head_to_head, plot_intersection_comparison,
            plot_success_heatmap, plot_success_by_nodes, plot_success_by_density,
            plot_graph_indexed_chain, plot_graph_indexed_time, plot_graph_indexed_success,
            plot_topology_comparison, plot_pareto,
        )
        df = an.df
        algos = sorted(df["algorithm"].unique())
        palette = build_algo_palette(algos)
        generated = 0

        def _run(label, fn):
            nonlocal generated
            try:
                fn()
                generated += 1
            except Exception as e:
                print(f"  [{label}]: {e}")

        for group in groups:
            if group == "distributions":
                an.output_dir.mkdir(parents=True, exist_ok=True)
                (an.figures_dir / "distributions").mkdir(parents=True, exist_ok=True)
                _run("chain_length_kde",     lambda: plot_chain_distribution(df, algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("max_chain_length_kde", lambda: plot_max_chain_distribution(df, algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("chain_length_violin",  lambda: plot_distributions(df, "avg_chain_length", algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("embedding_time_violin",lambda: plot_distributions(df, "wall_time", algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("chain_length_heatmap", lambda: plot_heatmap(df, "avg_chain_length", algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("consistency_cv",       lambda: plot_consistency(df, algo_palette=palette, output_dir=an.output_dir, save=True))

            elif group == "scaling":
                (an.figures_dir / "scaling").mkdir(parents=True, exist_ok=True)
                _run("chain_length_vs_nodes", lambda: plot_scaling(df, "avg_chain_length", "problem_nodes", algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("time_vs_nodes",         lambda: plot_scaling(df, "wall_time", "problem_nodes", algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("density_hardness",      lambda: plot_density_hardness(df, algo_palette=palette, output_dir=an.output_dir, save=True))

            elif group == "pairwise":
                (an.figures_dir / "pairwise").mkdir(parents=True, exist_ok=True)
                _run("win_rate_matrix", lambda: plot_win_rate_matrix(df, output_dir=an.output_dir, save=True))
                for a, b in itertools.combinations(algos, 2):
                    _run(f"scatter_{a}_vs_{b}",      lambda a=a, b=b: plot_head_to_head(df, a, b, output_dir=an.output_dir, save=True))
                    _run(f"intersection_{a}_vs_{b}", lambda a=a, b=b: plot_intersection_comparison(df, a, b, algo_palette=palette, output_dir=an.output_dir, save=True))

            elif group == "success":
                (an.figures_dir / "success").mkdir(parents=True, exist_ok=True)
                _run("success_rate_heatmap",    lambda: plot_success_heatmap(df, output_dir=an.output_dir, save=True))
                _run("success_rate_by_nodes",   lambda: plot_success_by_nodes(df, algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("success_rate_by_density", lambda: plot_success_by_density(df, algo_palette=palette, output_dir=an.output_dir, save=True))

            elif group == "graph-indexed":
                for x_mode in ("by_graph_id", "by_n_nodes", "by_density"):
                    (an.figures_dir / "graph_indexed" / x_mode).mkdir(parents=True, exist_ok=True)
                    _run(f"graph_indexed/{x_mode}/chain_length",    lambda xm=x_mode: plot_graph_indexed_chain(df, xm, algo_palette=palette, output_dir=an.output_dir, save=True))
                    _run(f"graph_indexed/{x_mode}/max_chain_length", lambda xm=x_mode: plot_graph_indexed_chain(df, xm, algo_palette=palette, metric="max_chain_length", output_dir=an.output_dir, save=True))
                    _run(f"graph_indexed/{x_mode}/embedding_time",  lambda xm=x_mode: plot_graph_indexed_time(df, xm, algo_palette=palette, output_dir=an.output_dir, save=True))
                    _run(f"graph_indexed/{x_mode}/success",         lambda xm=x_mode: plot_graph_indexed_success(df, xm, output_dir=an.output_dir, save=True))

            elif group == "topology":
                (an.figures_dir / "topology").mkdir(parents=True, exist_ok=True)
                _run("topology_comparison", lambda: plot_topology_comparison(df, algo_palette=palette, output_dir=an.output_dir, save=True))
                _run("pareto_frontier",     lambda: plot_pareto(df, algo_palette=palette, output_dir=an.output_dir, save=True))

        print(f"\nGenerated: {generated} plots")
        print(f"Output:    {output_root.resolve()}")


def _print_summary(generated: int, skipped: int, output_dir: Path) -> None:
    print(f"\nGenerated: {generated} files")
    if skipped:
        print(f"Skipped:   {skipped} files (already exist — use --overwrite to regenerate)")
    print(f"Output:    {output_dir.resolve()}")


# ---------------------------------------------------------------------------
# ember-analysis batches
# ---------------------------------------------------------------------------

def cmd_batches_list(args: argparse.Namespace) -> None:
    input_dir = resolve_input_dir(
        explicit=getattr(args, "input_dir", None),
        prompt=True,
    )
    batches = sorted(
        [d for d in input_dir.iterdir() if is_valid_batch(d)],
        reverse=True,
    )
    if not batches:
        print(f"No valid batches found in: {input_dir}")
        return

    active = resolve("active_batch")

    print(f"\n{'Batch':<35}  {'Algorithms':<30}  {'Trials':>7}  Status")
    print("-" * 85)
    for b in batches:
        cfg = _read_batch_config(b)
        algos = ", ".join(cfg.get("algorithms", []))[:28] or "?"
        trials = str(cfg.get("total_measured_runs", "?"))
        status = _batch_status(b)
        marker = " *" if active and Path(active) == b else ""
        print(f"  {b.name:<33}  {algos:<30}  {trials:>7}  {status}{marker}")

    print(f"\n{len(batches)} batch(es) in {input_dir.resolve()}")
    if active:
        active_name = Path(active).name
        print(f"Active batch: {active_name}  (* marked above)")


def cmd_batches_show(args: argparse.Namespace) -> None:
    # Try to locate the batch: absolute path, or look in input_dir
    path = Path(args.batch_id)
    if not path.exists():
        input_dir = resolve_input_dir(prompt=True)
        path = input_dir / args.batch_id
    if not path.exists():
        print(f"error: batch not found: {args.batch_id}")
        sys.exit(1)
    try:
        validate_batch(path)
    except ValueError as e:
        print(f"error: {e}")
        sys.exit(1)

    cfg = _read_batch_config(path)
    print(f"=== {path.name} ===")
    print(f"  Status:     {_batch_status(path)}")
    for k in ("algorithms", "topologies", "n_trials", "timeout", "seed", "batch_note", "total_measured_runs"):
        if k in cfg:
            print(f"  {k:<25} {cfg[k]}")


# ---------------------------------------------------------------------------
# ember-analysis config
# ---------------------------------------------------------------------------

def cmd_config_show(args: argparse.Namespace) -> None:
    path = get_user_config_path()
    print(f"Config file: {path}\n")
    stored = load_config()

    print(f"{'Key':<15}  {'Value':<35}  Source")
    print("─" * 65)

    env_active = []
    for key in DEFAULTS:
        env_var = ENV_VARS.get(key)
        env_val = __import__("os").environ.get(env_var) if env_var else None

        if env_val is not None:
            value = env_val
            source = "environment variable"
            env_active.append(env_var)
        elif stored.get(key) is not None:
            value = str(stored[key])
            source = "config file"
        else:
            value = "—"
            source = f"default ({DEFAULTS[key]!r})" if DEFAULTS[key] is not None else "default (batch/analysis/)" if key == "output_dir" else "default (null)"

        print(f"  {key:<13}  {value:<35}  {source}")

    if env_active:
        print(f"\nEnvironment overrides active: {', '.join(env_active)}")


def cmd_config_get(args: argparse.Namespace) -> None:
    try:
        val = get_config(args.key)
        print(val if val is not None else "null")
    except ValueError as e:
        print(f"error: {e}")
        sys.exit(1)


def cmd_config_set(args: argparse.Namespace) -> None:
    key = args.key
    raw = args.value

    if key not in DEFAULTS:
        valid = ", ".join(sorted(DEFAULTS))
        print(f"error: unknown key '{key}'. Valid keys: {valid}")
        sys.exit(1)

    # Coerce string input to appropriate type
    value: any
    if raw.lower() in ("null", "none", ""):
        value = None
    else:
        value = raw

    try:
        set_config(key, value)
        print(f"{key} = {value}")
    except (ValueError, TypeError) as e:
        print(f"error: {e}")
        sys.exit(1)


def cmd_config_reset(args: argparse.Namespace) -> None:
    path = get_user_config_path()
    if not path.exists():
        print("Nothing to reset (no config file exists).")
        return
    try:
        ans = input(f"Delete {path}? This resets all keys to defaults. [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return
    if ans not in ("y", "yes"):
        print("Aborted.")
        return
    reset_config()
    print("Config reset.")


def cmd_config_path(args: argparse.Namespace) -> None:
    print(get_user_config_path())


# ---------------------------------------------------------------------------
# ember-analysis version
# ---------------------------------------------------------------------------

def cmd_version(args: argparse.Namespace) -> None:
    try:
        from importlib.metadata import version
        ver = version("ember-qc-analysis")
    except Exception:
        ver = "unknown"
    print(f"ember-qc-analysis {ver}")


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ember-analysis",
        description="ember-qc-analysis — post-benchmark analysis for ember-qc",
    )
    parser.set_defaults(func=lambda _: parser.print_help())
    sub = parser.add_subparsers(dest="command")

    # -- version -------------------------------------------------------------
    p_ver = sub.add_parser("version", help="print package version")
    p_ver.set_defaults(func=cmd_version)

    # -- stage ---------------------------------------------------------------
    p_stage = sub.add_parser("stage", help="set active batch context")
    p_stage.add_argument("batch_dir", metavar="BATCH_DIR")
    p_stage.set_defaults(func=cmd_stage)

    # -- unstage -------------------------------------------------------------
    p_unstage = sub.add_parser("unstage", help="clear active batch context")
    p_unstage.set_defaults(func=cmd_unstage)

    # -- report --------------------------------------------------------------
    p_report = sub.add_parser("report", help="run full analysis pipeline")
    p_report.add_argument("-o", "--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_report.add_argument("-f", "--format",     metavar="FMT",  default=None, dest="format",
                          choices=["png", "pdf", "svg"])
    p_report.add_argument("--overwrite", action="store_true", default=False)
    p_report.set_defaults(func=cmd_report)

    # -- plots ---------------------------------------------------------------
    p_plots = sub.add_parser("plots", help="run plot generation")
    p_plots.add_argument("groups", nargs="*", metavar="GROUP",
                         help=f"plot groups: {', '.join(PLOT_GROUPS)}")
    p_plots.add_argument("-o", "--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_plots.add_argument("-f", "--format",     metavar="FMT",  default=None, dest="format",
                         choices=["png", "pdf", "svg"])
    p_plots.add_argument("--list",     action="store_true", default=False,
                         help="list available plot groups")
    p_plots.add_argument("--overwrite", action="store_true", default=False)
    p_plots.set_defaults(func=cmd_plots)

    # -- tables --------------------------------------------------------------
    p_tables = sub.add_parser("tables", help="run summary table generation")
    p_tables.add_argument("-o", "--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_tables.add_argument("--overwrite", action="store_true", default=False)
    p_tables.set_defaults(func=cmd_tables)

    # -- stats ---------------------------------------------------------------
    p_stats = sub.add_parser("stats", help="run statistical analysis")
    p_stats.add_argument("-o", "--output-dir", metavar="PATH", default=None, dest="output_dir")
    p_stats.add_argument("--overwrite", action="store_true", default=False)
    p_stats.set_defaults(func=cmd_stats)

    # -- batches -------------------------------------------------------------
    p_batches = sub.add_parser("batches", help="list and inspect batches")
    bs = p_batches.add_subparsers(dest="batches_cmd")
    p_batches.set_defaults(func=lambda _: p_batches.print_help())

    p_bl = bs.add_parser("list", help="list batches in input_dir")
    p_bl.add_argument("-i", "--input-dir", metavar="PATH", default=None, dest="input_dir")
    p_bl.set_defaults(func=cmd_batches_list)

    p_bs = bs.add_parser("show", help="show batch summary")
    p_bs.add_argument("batch_id", metavar="BATCH_ID")
    p_bs.set_defaults(func=cmd_batches_show)

    # -- config --------------------------------------------------------------
    p_config = sub.add_parser("config", help="manage persistent configuration")
    cs = p_config.add_subparsers(dest="config_cmd")
    p_config.set_defaults(func=lambda _: p_config.print_help())

    p_cshow = cs.add_parser("show",  help="show all config keys and sources")
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
