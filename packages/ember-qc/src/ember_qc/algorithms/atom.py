"""
ember_qc/algorithms/atom.py
============================
ATOM — Adaptive Topology Minor-embedding.

Grows its own Chimera topology dynamically via compiled C++ binary.
Binary discovery order:
  1. EMBER_ATOM_BINARY env var
  2. get_user_binary_dir() / "atom" / "main"
"""

import logging
import math
import os
import subprocess
import tempfile
from pathlib import Path

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

logger = logging.getLogger(__name__)


def _resolve_atom_binary() -> Path:
    env = os.environ.get("EMBER_ATOM_BINARY")
    if env:
        return Path(env)
    from ember_qc._paths import get_user_binary_dir
    return get_user_binary_dir() / "atom" / "main"


@register_algorithm("atom")
class AtomAlgorithm(EmbeddingAlgorithm):
    """ATOM — grows its own Chimera topology dynamically."""

    _uses_subprocess = True
    supported_topologies = ['chimera']
    _binary = staticmethod(_resolve_atom_binary)
    _install_instruction = "Run: ember install-binary atom"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        atom_exe = _resolve_atom_binary()
        atom_dir = atom_exe.parent
        start_time = __import__('time').time()

        if not atom_exe.exists():
            logger.warning("ATOM binary not found at %s. Run: ember install-binary atom", atom_exe)
            return {'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE'}

        atom_exe = atom_exe.resolve()
        source_file = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                n = source_graph.number_of_nodes()
                f.write(f"{n}\n")
                for node in range(n):
                    f.write(f"{node}\n")
                for u, v in source_graph.edges():
                    f.write(f"{u} {v}\n")
                source_file = f.name

            try:
                result = subprocess.run(
                    [str(atom_exe), '-pfile', source_file, '-test', '0'],
                    capture_output=True, text=True,
                    timeout=timeout, cwd=atom_dir,
                )
                elapsed = __import__('time').time() - start_time
            except subprocess.TimeoutExpired:
                return {'embedding': {}, 'time': __import__('time').time() - start_time,
                        'success': False, 'status': 'TIMEOUT'}
            finally:
                if source_file and os.path.exists(source_file):
                    os.unlink(source_file)
                results_txt = atom_dir / "Results.txt"
                if results_txt.exists():
                    os.unlink(results_txt)

            # Parse ATOM stdout: "x y k color" per qubit
            embedding = {}
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('Embedding') or line.startswith('Requires'):
                    continue
                parts = line.split()
                if len(parts) == 4:
                    try:
                        x, y, k, color = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                        embedding.setdefault(color, []).append((x, y, k))
                    except ValueError:
                        continue

            if result.returncode != 0:
                stderr_snippet = (result.stderr or '').strip()[:300]
                logger.error(
                    "ATOM binary exited with code %d. stderr: %s",
                    result.returncode, stderr_snippet or '<empty>',
                )
                return {
                    'embedding': {}, 'time': elapsed,
                    'success': False, 'status': 'CRASH',
                    'error': f"ATOM binary exit code {result.returncode}: {stderr_snippet}",
                }

            if not embedding:
                return {'embedding': {}, 'time': elapsed, 'success': False, 'status': 'FAILURE'}

            # Convert (x, y, k) Chimera coords → linear qubit indices using target dimensions.
            # Must use target graph dimensions, NOT infer from ATOM output (off-by-one due to
            # expanding_border() final pass).
            n_cols = target_graph.graph.get('columns', None)
            n_rows = target_graph.graph.get('rows', None)
            if n_cols is None:
                n_cols = max(1, int(round(math.sqrt(target_graph.number_of_nodes() / 8))))
                n_rows = n_cols

            if n_rows is not None:
                all_positions = [p for ps in embedding.values() for p in ps]
                atom_max_row = max(p[0] for p in all_positions)
                atom_max_col = max(p[1] for p in all_positions)
                if atom_max_row >= n_rows or atom_max_col >= n_cols:
                    return {
                        'embedding': {}, 'time': elapsed,
                        'success': False, 'status': 'FAILURE',
                        'error': (
                            f"ATOM's embedding requires a "
                            f"{atom_max_row + 1}×{atom_max_col + 1} Chimera "
                            f"but target is {n_rows}×{n_cols}"
                        ),
                    }

            linear_embedding = {
                color: [x * n_cols * 8 + y * 8 + k for x, y, k in positions]
                for color, positions in embedding.items()
            }
            return {'embedding': linear_embedding, 'time': elapsed, 'method': 'ATOM'}

        except Exception as e:
            logger.error("ATOM error: %s", e)
            return {'embedding': {}, 'time': __import__('time').time() - start_time,
                    'success': False, 'status': 'FAILURE'}
