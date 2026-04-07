"""
ember_qc/checkpoint.py
======================
Checkpoint reading, writing, and discovery for benchmark resume.

A checkpoint.json present in a batch directory means the run was cancelled
cleanly and is resumable. Absent means either still running or crashed.
Complete runs are moved out of runs_unfinished/ entirely — so anything
remaining in runs_unfinished/ is by definition incomplete.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def write_checkpoint(
    batch_dir: Path,
    unfinished_tasks: List[Tuple[str, int, str, str, str, int, int]],
    total_tasks: int,
    completed_count: int,
    resume_count: int = 0,
) -> Path:
    """Write checkpoint.json to batch_dir.

    Args:
        batch_dir: The batch directory (in runs_unfinished/).
        unfinished_tasks: Task tuples (source_graph, target_graph, algo_name,
            graph_id, graph_name, topo_name, trial, trial_seed).
        total_tasks: Total number of measured tasks in the full run.
        completed_count: Number of tasks completed before cancellation.
        resume_count: How many times this run has been resumed (0 on first cancel).

    Returns:
        Path to the written checkpoint file.
    """
    checkpoint = {
        'unfinished_tasks': [
            {
                'algo_name': t[2],
                'graph_id':  t[3],
                'graph_name': t[4],
                'topo_name': t[5],
                'trial':     t[6],
                'trial_seed': t[7],
            }
            for t in unfinished_tasks
        ],
        'total_tasks': total_tasks,
        'completed_count': completed_count,
        'cancelled_at': datetime.now(timezone.utc).isoformat(),
        'resume_count': resume_count,
    }
    cp_path = batch_dir / 'checkpoint.json'
    with open(cp_path, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    return cp_path


def read_checkpoint(batch_dir: Path) -> Optional[dict]:
    """Read checkpoint.json from batch_dir. Returns None if not present."""
    cp_path = batch_dir / 'checkpoint.json'
    if not cp_path.exists():
        return None
    with open(cp_path) as f:
        return json.load(f)


def delete_checkpoint(batch_dir: Path) -> None:
    """Remove checkpoint.json after successful compile and move."""
    cp_path = batch_dir / 'checkpoint.json'
    if cp_path.exists():
        cp_path.unlink()


def completed_seeds_from_jsonl(batch_dir: Path) -> Set[Tuple[str, int, str, int]]:
    """Collect completed (algo, graph_id, topo, seed) tuples from worker JSONL files.

    Used for crashed-run recovery when no checkpoint.json exists. Strips
    potentially truncated final lines (incomplete writes at crash time).

    Returns:
        Set of (algorithm, graph_id, topology_name, seed) tuples.
    """
    completed: Set[Tuple[str, int, str, int]] = set()
    workers_dir = batch_dir / 'workers'
    if not workers_dir.exists():
        return completed

    for jf in workers_dir.glob('worker_*.jsonl'):
        try:
            with open(jf) as f:
                raw_lines = f.readlines()
        except OSError:
            continue

        # Strip potentially truncated last line (incomplete write at crash time)
        if raw_lines:
            try:
                json.loads(raw_lines[-1])
            except json.JSONDecodeError:
                raw_lines = raw_lines[:-1]

        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                completed.add((
                    rec.get('algorithm', ''),
                    rec.get('graph_id', 0),
                    rec.get('topology_name', ''),
                    rec.get('seed', -1),
                ))
            except json.JSONDecodeError:
                pass

    return completed


def scan_incomplete_runs(unfinished_dir: Path) -> List[Dict]:
    """Scan unfinished_dir for incomplete or crashed benchmark runs.

    Every batch directory in runs_unfinished/ is by definition incomplete —
    complete runs are moved to the output directory. Within incomplete runs,
    checkpoint.json present means cleanly cancelled; absent means crashed or
    still running.

    Returns:
        List of dicts, each containing:
            batch_dir (Path), batch_id (str),
            checkpoint (dict | None), config (dict),
            jsonl_lines (int), has_checkpoint (bool)
        Sorted most-recent-first.
    """
    incomplete = []
    if not unfinished_dir.exists():
        return incomplete

    for batch_dir in sorted(unfinished_dir.glob('batch_*'), reverse=True):
        if not batch_dir.is_dir():
            continue

        config_path = batch_dir / 'config.json'
        if not config_path.exists():
            continue  # not a valid batch directory

        config: dict = {}
        try:
            with open(config_path) as f:
                config = json.load(f)
        except Exception:
            pass

        cp_path = batch_dir / 'checkpoint.json'
        has_checkpoint = cp_path.exists()
        checkpoint: Optional[dict] = None
        if has_checkpoint:
            try:
                with open(cp_path) as f:
                    checkpoint = json.load(f)
            except Exception:
                pass

        # Count JSONL lines as a rough progress indicator for crashed runs
        jsonl_lines = 0
        workers_dir = batch_dir / 'workers'
        if workers_dir.exists():
            for jf in workers_dir.glob('worker_*.jsonl'):
                try:
                    with open(jf) as fh:
                        jsonl_lines += sum(1 for _ in fh)
                except OSError:
                    pass

        incomplete.append({
            'batch_dir': batch_dir,
            'batch_id': batch_dir.name,
            'checkpoint': checkpoint,
            'config': config,
            'jsonl_lines': jsonl_lines,
            'has_checkpoint': has_checkpoint,
        })

    return incomplete
