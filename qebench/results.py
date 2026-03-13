"""
Results storage and summarization for QEBench.

Handles:
- Timestamped batch directories
- Per-run CSV (metrics only) and JSON (with embeddings)
- Summary CSV with grouped averages ± std dev
- Batch config recording
- Symlink to latest batch
"""

import json
import os
import platform
import sys
import subprocess as _subprocess
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _next_batch_name(results_dir: Path) -> str:
    """Generate a unique batch directory name with timestamp.
    
    Format: batch_YYYY-MM-DD_HH-MM-SS
    If that already exists (multiple runs in same second), appends _2, _3, etc.
    """
    now = datetime.now()
    base = f"batch_{now.strftime('%Y-%m-%d_%H-%M-%S')}"
    candidate = base
    counter = 2
    while (results_dir / candidate).exists():
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


class ResultsManager:
    """Handles all results persistence and summarization.
    
    Usage:
        mgr = ResultsManager("./results")
        batch_dir = mgr.create_batch(config)
        mgr.save_results(results, batch_dir)
    """
    
    def __init__(self, results_dir: str = "./results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True, parents=True)
    
    def create_batch(self, config: Optional[dict] = None, 
                     batch_note: str = "") -> Path:
        """Create a new timestamped batch directory.
        
        Args:
            config: Optional dict of run configuration to save as config.json.
            batch_note: Human-readable note describing this run.
            
        Returns:
            Path to the new batch directory.
        """
        batch_name = _next_batch_name(self.results_dir)
        batch_dir = self.results_dir / batch_name
        batch_dir.mkdir()
        
        # Save config if provided
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
                from qebench import __version__ as _qebench_version
            except Exception:
                _qebench_version = "unknown"
            config['provenance'] = {
                'python_version': sys.version,
                'platform': platform.platform(),
                'processor': platform.processor(),
                'dependencies': deps,
                'qebench_version': _qebench_version,
            }
            with open(batch_dir / "config.json", 'w') as f:
                json.dump(config, f, indent=2)
        
        self._update_latest_symlink(batch_dir)
        return batch_dir
    
    def save_results(self, results: list, batch_dir: Path, 
                     config: Optional[dict] = None):
        """Save all results to runs.csv, runs.json, summary.csv, and README.md.
        
        Args:
            results: List of EmbeddingResult objects.
            batch_dir: Path to the batch directory (from create_batch).
            config: Run config dict (used for README generation).
        """
        if not results:
            return
        
        self._save_runs_csv(results, batch_dir)
        self._save_runs_json(results, batch_dir)
        self._save_summary(results, batch_dir)
        self._save_readme(results, batch_dir, config)
        
        print(f"\n📁 Results saved to {batch_dir}/")
        print(f"   ├── README.md    (human-readable summary)")
        print(f"   ├── config.json  (machine-readable settings)")
        print(f"   ├── runs.csv     ({len(results)} rows, no embeddings)")
        print(f"   ├── runs.json    ({len(results)} entries with embeddings)")
        print(f"   └── summary.csv  (grouped averages ± std dev)")
    
    def _save_runs_csv(self, results: list, batch_dir: Path):
        """Save per-run CSV without embeddings (lightweight)."""
        rows = []
        for r in results:
            d = r.to_dict()
            d.pop('embedding', None)  # exclude embeddings from CSV
            d.pop('chain_lengths', None)  # list doesn't CSV well
            rows.append(d)
        
        df = pd.DataFrame(rows)
        csv_path = batch_dir / "runs.csv"
        df.to_csv(csv_path, index=False)
    
    def _save_runs_json(self, results: list, batch_dir: Path):
        """Save per-run JSON with embeddings (full archive)."""
        json_path = batch_dir / "runs.json"
        data = [r.to_dict() for r in results]
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_summary(self, results: list, batch_dir: Path):
        """Save grouped averages and std devs.
        
        Groups by (algorithm, problem_name, topology_name) and computes
        mean, std, median for timing and quality metrics.
        """
        rows = []
        for r in results:
            d = r.to_dict()
            d.pop('embedding', None)
            d.pop('chain_lengths', None)
            rows.append(d)
        
        df = pd.DataFrame(rows)
        group_cols = ['algorithm', 'problem_name', 'topology_name']
        
        # Only aggregate numeric/boolean columns
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
                for metric in ['embedding_time', 'avg_chain_length', 'max_chain_length',
                               'total_qubits_used', 'total_couplers_used']:
                    vals = successful[metric].astype(float)
                    row[f'{metric}_mean'] = float(vals.mean())
                    row[f'{metric}_std'] = float(vals.std()) if n_success > 1 else 0.0
                    row[f'{metric}_median'] = float(vals.median())
                
                row['valid_rate'] = float(successful['is_valid'].mean())
            else:
                for metric in ['embedding_time', 'avg_chain_length', 'max_chain_length',
                               'total_qubits_used', 'total_couplers_used']:
                    row[f'{metric}_mean'] = None
                    row[f'{metric}_std'] = None
                    row[f'{metric}_median'] = None
                row['valid_rate'] = 0.0
            
            # Problem metadata (same for all rows in group)
            row['problem_nodes'] = int(group_df['problem_nodes'].iloc[0])
            row['problem_edges'] = int(group_df['problem_edges'].iloc[0])
            row['problem_density'] = float(group_df['problem_density'].iloc[0])
            
            summary_rows.append(row)
        
        summary_df = pd.DataFrame(summary_rows)
        csv_path = batch_dir / "summary.csv"
        summary_df.to_csv(csv_path, index=False)
    
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
            lines.append(f"| Setting | Value |")
            lines.append(f"|---------|-------|")
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
            import numpy as np
            times = [r.embedding_time for r in results if r.success]
            chains = [r.avg_chain_length for r in results if r.success]
            qubits = [r.total_qubits_used for r in results if r.success]
            lines.append(f"- Embedding time: **{np.mean(times):.4f}s** mean ± {np.std(times):.4f}s")
            lines.append(f"- Avg chain length: **{np.mean(chains):.2f}** mean")
            lines.append(f"- Qubits used: **{np.mean(qubits):.1f}** mean")
        
        lines.append("")
        lines.append("## Files\n")
        lines.append("| File | Contents |")
        lines.append("|------|----------|")
        lines.append("| `runs.csv` | Every trial as a row (no embeddings) |")
        lines.append("| `runs.json` | Every trial with actual embeddings |")
        lines.append("| `summary.csv` | Grouped averages ± std dev |")
        lines.append("| `config.json` | Machine-readable settings |")
        lines.append("")
        
        with open(batch_dir / "README.md", 'w') as f:
            f.write('\n'.join(lines))
    
    def _update_latest_symlink(self, batch_dir: Path):
        """Point results/latest → newest batch directory."""
        link = self.results_dir / "latest"
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
            # Use relative path so the symlink works if the project moves
            link.symlink_to(batch_dir.name)
        except OSError:
            pass  # symlinks may not work on all filesystems
