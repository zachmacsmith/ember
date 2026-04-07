"""
Results storage and summarization for QEBench.

Handles:
- Timestamped batch directories created in runs_unfinished/
- Per-run CSV (metrics only) and JSON (with embeddings)
- Summary CSV with grouped averages ± std dev
- Batch config recording
- Move-to-output on successful completion, with symlink to latest
"""

import json
import platform
import shutil
import sys
import subprocess as _subprocess
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _next_batch_name(base_dir: Path) -> str:
    """Generate a unique batch directory name with timestamp.

    Format: batch_YYYY-MM-DD_HH-MM-SS
    If that already exists (multiple runs in same second), appends _2, _3, etc.
    """
    now = datetime.now(timezone.utc)
    base = f"batch_{now.strftime('%Y-%m-%d_%H-%M-%S')}"
    candidate = base
    counter = 2
    while (base_dir / candidate).exists():
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


class ResultsManager:
    """Handles all results persistence and summarization.

    Batch directories are created in runs_unfinished/ and moved to results_dir
    only after successful compilation. Anything in results_dir is guaranteed
    to be a complete, compiled run.

    Usage:
        mgr = ResultsManager("./results")
        batch_dir = mgr.create_batch(config)        # → runs_unfinished/batch_.../
        ...run trials...
        output_dir = mgr.move_to_output(batch_dir)  # → results/batch_.../
        mgr.save_results(results, output_dir)
    """

    def __init__(self, results_dir: str = "./results",
                 unfinished_dir: Optional[str] = None):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True, parents=True)

        if unfinished_dir is None:
            self.unfinished_dir = self.results_dir.parent / "runs_unfinished"
        else:
            self.unfinished_dir = Path(unfinished_dir)
        self.unfinished_dir.mkdir(exist_ok=True, parents=True)

    def create_batch(self, config: Optional[dict] = None,
                     batch_note: str = "") -> Path:
        """Create a new timestamped batch directory in runs_unfinished/.

        Args:
            config: Optional dict of run configuration to save as config.json.
            batch_note: Human-readable note describing this run.

        Returns:
            Path to the new batch directory (inside runs_unfinished/).
        """
        batch_name = _next_batch_name(self.unfinished_dir)
        batch_dir = self.unfinished_dir / batch_name
        batch_dir.mkdir()

        if config:
            config['batch_name'] = batch_name
            config['timestamp'] = datetime.now(timezone.utc).isoformat()
            if batch_note:
                config['batch_note'] = batch_note
            try:
                deps = _subprocess.check_output(
                    [sys.executable, "-m", "pip", "freeze"],
                    stderr=_subprocess.DEVNULL
                ).decode()
            except Exception:
                deps = ""
            try:
                from ember_qc import __version__ as _ember_version
            except Exception:
                _ember_version = "unknown"
            try:
                from ember_qc.registry import ALGORITHM_REGISTRY
                _algo_versions = {
                    name: ALGORITHM_REGISTRY[name].version
                    for name in config.get('algorithms', [])
                    if name in ALGORITHM_REGISTRY
                }
            except Exception:
                _algo_versions = {}
            config['provenance'] = {
                'python_version': sys.version,
                'platform': platform.platform(),
                'processor': platform.processor(),
                'dependencies': deps,
                'ember_version': _ember_version,
                'algorithm_versions': _algo_versions,
            }
            with open(batch_dir / "config.json", 'w') as f:
                json.dump(config, f, indent=2)

        return batch_dir

    def move_to_output(self, batch_dir: Path,
                       output_dir: Optional[Path] = None) -> Path:
        """Move a completed batch from runs_unfinished/ to the output directory.

        Called after compile_batch() succeeds. The batch_dir argument must be
        inside runs_unfinished/. After this call the batch is in results_dir
        (or output_dir if specified) and the results/latest symlink is updated.

        Args:
            batch_dir: Path to the batch directory in runs_unfinished/.
            output_dir: Override output directory. Defaults to self.results_dir.

        Returns:
            Path to the batch in its final output location.
        """
        dest_root = Path(output_dir) if output_dir else self.results_dir
        dest_root.mkdir(exist_ok=True, parents=True)
        dest = dest_root / batch_dir.name

        # Remove any stale dest from a previous failed run so shutil.move cannot
        # nest batch_dir inside it instead of renaming to it.
        if dest.exists():
            shutil.rmtree(str(dest))

        try:
            # Try atomic rename first (same filesystem).
            batch_dir.rename(dest)
        except OSError:
            # Cross-filesystem: copy then remove source explicitly so we control
            # error handling at each step and never lose data silently.
            try:
                shutil.copytree(str(batch_dir), str(dest))
            except Exception as copy_err:
                # Copy failed — clean up any partial destination and leave the
                # source intact so the run can be recovered with ember resume.
                if dest.exists():
                    shutil.rmtree(str(dest), ignore_errors=True)
                raise RuntimeError(
                    f"Failed to copy batch '{batch_dir.name}' to '{dest_root}': {copy_err}. "
                    f"The run data is still in runs_unfinished/ and can be resumed."
                ) from copy_err
            # Copy succeeded — now remove the source.
            shutil.rmtree(str(batch_dir))

        if not dest.is_dir():
            raise RuntimeError(
                f"move_to_output: expected batch at '{dest}' after move but it does not "
                f"exist. Check filesystem permissions and disk space."
            )

        self._update_latest_symlink(dest, dest_root)
        return dest

    def save_results(self, results: list, batch_dir: Path,
                     config: Optional[dict] = None):
        """Save summary.csv and README.md for a completed batch.

        runs.csv and results.db are written by compile_batch() before this is
        called — this method only handles the human-readable artefacts.

        Args:
            results: List of EmbeddingResult objects.
            batch_dir: Path to the batch directory (already in output location).
            config: Run config dict (used for README generation).
        """
        if not results:
            return

        batch_dir = Path(batch_dir)
        batch_dir.mkdir(parents=True, exist_ok=True)

        self._save_summary(results, batch_dir)
        self._save_readme(results, batch_dir, config)

        print(f"\nResults saved to {batch_dir}/")
        print(f"   ├── README.md    (human-readable summary)")
        print(f"   ├── config.json  (machine-readable settings)")
        print(f"   ├── results.db   (SQLite — runs, embeddings, graphs, batches)")
        print(f"   ├── runs.csv     ({len(results)} rows, exported from SQLite)")
        print(f"   ├── workers/     (per-process JSONL source files)")
        print(f"   └── summary.csv  (grouped averages ± std dev)")

    def _save_summary(self, results: list, batch_dir: Path):
        """Save grouped averages and std devs."""
        rows = []
        for r in results:
            d = r.to_dict()
            d.pop('embedding', None)
            d.pop('chain_lengths', None)
            rows.append(d)

        df = pd.DataFrame(rows)
        group_cols = ['algorithm', 'problem_name', 'topology_name']

        summary_rows = []
        for group_key, group_df in df.groupby(group_cols):
            algo, problem, topo = group_key
            n = len(group_df)
            successful = group_df[group_df['success'] == True]
            n_success = len(successful)

            row = {
                'algorithm': algo,
                'problem_name': problem,
                'topology_name': topo,
                'n_trials': n,
                'n_success': n_success,
                'success_rate': n_success / n if n > 0 else 0,
            }

            if n_success > 0:
                for metric in ['wall_time', 'avg_chain_length', 'max_chain_length',
                               'total_qubits_used', 'total_couplers_used']:
                    vals = successful[metric].astype(float)
                    row[f'{metric}_mean'] = float(vals.mean())
                    row[f'{metric}_std'] = float(vals.std()) if n_success > 1 else 0.0
                    row[f'{metric}_median'] = float(vals.median())

                row['valid_rate'] = float(successful['is_valid'].mean())
            else:
                for metric in ['wall_time', 'avg_chain_length', 'max_chain_length',
                               'total_qubits_used', 'total_couplers_used']:
                    row[f'{metric}_mean'] = None
                    row[f'{metric}_std'] = None
                    row[f'{metric}_median'] = None
                row['valid_rate'] = 0.0

            row['problem_nodes'] = int(group_df['problem_nodes'].iloc[0])
            row['problem_edges'] = int(group_df['problem_edges'].iloc[0])
            row['problem_density'] = float(group_df['problem_density'].iloc[0])

            summary_rows.append(row)

        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(batch_dir / "summary.csv", index=False)

    def _save_readme(self, results: list, batch_dir: Path,
                     config: Optional[dict] = None):
        """Generate a human-readable README.md for this batch."""
        batch_name = batch_dir.name
        timestamp = config.get('timestamp', '') if config else ''
        batch_note = config.get('batch_note', '') if config else ''

        n_total = len(results)
        n_success = sum(1 for r in results if r.success)
        n_valid = sum(1 for r in results if r.is_valid)
        algorithms = sorted(set(r.algorithm for r in results))
        problems = sorted(set(r.problem_name for r in results))
        topologies = sorted(set(r.topology_name for r in results if r.topology_name))

        lines = [f"# {batch_name}\n"]

        if batch_note:
            lines.append(f"> {batch_note}\n")

        lines.append("## Settings\n")
        if config:
            lines.append("| Setting | Value |")
            lines.append("|---------|-------|")
            lines.append(f"| Timestamp | {timestamp} |")
            lines.append(f"| Algorithms | {', '.join(algorithms)} |")
            lines.append(f"| Graph selection | {config.get('graph_selection', 'custom')} |")
            lines.append(f"| Topology | {', '.join(topologies) or 'not specified'} |")
            lines.append(f"| Trials per (algo, graph) | {config.get('n_trials', '?')} |")
            lines.append(f"| Warm-up trials | {config.get('warmup_trials', 0)} |")
            lines.append(f"| Timeout | {config.get('timeout', '?')}s |")
            lines.append(f"| Problems | {len(problems)} |")
            lines.append(f"| Total measured runs | {n_total} |")
            lines.append("")

        lines.append("## Results Summary\n")
        lines.append(f"- **{n_success}/{n_total}** runs succeeded ({100*n_success/n_total:.0f}%)")
        lines.append(f"- **{n_valid}/{n_success}** successful embeddings validated" if n_success else "")

        if n_success > 0:
            times = [r.wall_time for r in results if r.success]
            chains = [r.avg_chain_length for r in results if r.success]
            qubits = [r.total_qubits_used for r in results if r.success]
            lines.append(f"- Embedding time: **{np.mean(times):.4f}s** mean ± {np.std(times):.4f}s")
            lines.append(f"- Avg chain length: **{np.mean(chains):.2f}** mean")
            lines.append(f"- Qubits used: **{np.mean(qubits):.1f}** mean")

        lines.append("")
        lines.append("## Files\n")
        lines.append("| File | Contents |")
        lines.append("|------|----------|")
        lines.append("| `results.db` | SQLite — runs, embeddings, graphs, batches |")
        lines.append("| `runs.csv` | Every trial as a row (exported from SQLite) |")
        lines.append("| `summary.csv` | Grouped averages ± std dev |")
        lines.append("| `config.json` | Machine-readable settings |")
        lines.append("| `workers/` | Per-process JSONL source files |")
        lines.append("")

        with open(batch_dir / "README.md", 'w') as f:
            f.write('\n'.join(lines))

    def _update_latest_symlink(self, batch_dir: Path, root: Path):
        """Point <root>/latest → newest batch directory."""
        link = root / "latest"
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(batch_dir.name)
        except OSError:
            pass
