"""
ember_qc/algorithms/oct.py
============================
OCT-suite algorithm variants (TRIAD, Fast-OCT, Hybrid-OCT and their reduced forms).

All variants share one compiled binary (the "driver"). Binary discovery order:
  1. EMBER_OCT_BINARY env var
  2. get_user_binary_dir() / "oct_based" / "embedding" / "driver"
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

import dwave_networkx as dnx

from ember_qc.registry import ALGORITHM_REGISTRY, EmbeddingAlgorithm, register_algorithm

logger = logging.getLogger(__name__)


def _resolve_oct_binary() -> Path:
    env = os.environ.get("EMBER_OCT_BINARY")
    if env:
        return Path(env)
    from ember_qc._paths import get_user_binary_dir
    return get_user_binary_dir() / "oct_based" / "embedding" / "driver"


def _infer_chimera_dims(target_graph):
    """Try to infer Chimera dimensions (m, n, t) from a target graph."""
    try:
        gd = target_graph.graph
        if 'rows' in gd and 'columns' in gd and 'tile' in gd:
            return (gd['rows'], gd['columns'], gd['tile'])
        num_nodes = target_graph.number_of_nodes()
        for m in range(1, 20):
            for t in [4, 8]:
                if num_nodes == 2 * t * m * m:
                    candidate = dnx.chimera_graph(m, m, t)
                    if (candidate.number_of_nodes() == num_nodes and
                            candidate.number_of_edges() == target_graph.number_of_edges()):
                        return (m, m, t)
    except Exception:
        pass
    return None


def _make_oct_class(algo_name: str, extra_flags: list, desc: str, supports_seed: bool = False):
    """Factory producing one OctVariant class for the given OCT algorithm name."""

    class OctVariant(EmbeddingAlgorithm):
        __doc__ = desc
        _uses_subprocess = True
        _supports_seed = supports_seed
        supported_topologies = ['chimera']
        _binary = staticmethod(_resolve_oct_binary)
        _install_instruction = "Run: ember install-binary oct"

        def embed(self, source_graph, target_graph, timeout=60.0,
                  chimera_dims=None, **kwargs):
            import time
            oct_exe_path = _resolve_oct_binary()
            if os.environ.get("EMBER_OCT_BINARY"):
                oct_exe = oct_exe_path.resolve()
                oct_dir = oct_exe.parent.parent
            else:
                oct_dir = oct_exe_path.parent.parent.resolve()
                oct_exe = oct_exe_path.resolve()

            start_time = time.time()

            if not oct_exe.exists():
                logger.warning("OCT binary not found at %s. Run: ember install-binary oct", oct_exe)
                return {'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE'}

            dims = chimera_dims or _infer_chimera_dims(target_graph) or (4, 4, 4)
            c_m, c_n, c_t = dims
            chimera_graph = dnx.chimera_graph(c_m, c_n, c_t)

            flags = list(extra_flags)
            if self._supports_seed and kwargs.get('seed') is not None:
                seed_str = str(kwargs['seed'])
                if '-s' in flags:
                    flags[flags.index('-s') + 1] = seed_str
                else:
                    flags += ['-s', seed_str]

            source_file = out_base = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.graph',
                                                 dir=str(oct_dir), delete=False) as f:
                    n = source_graph.number_of_nodes()
                    f.write(f"{n}\n")
                    for node in range(n):
                        f.write(f"{node}\n")
                    for u, v in source_graph.edges():
                        f.write(f"{u} {v}\n")
                    source_file = f.name

                with tempfile.NamedTemporaryFile(mode='w', dir=str(oct_dir),
                                                 prefix="oct_out_", delete=False) as f:
                    out_base = f.name

                cmd = [str(oct_exe), '-a', algo_name,
                       '-pfile', source_file,
                       '-c', str(c_t), '-m', str(c_m), '-n', str(c_n),
                       '-o', out_base] + flags

                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True,
                                          timeout=timeout, cwd=str(oct_dir))
                    elapsed = time.time() - start_time
                except subprocess.TimeoutExpired:
                    return {'embedding': {}, 'time': time.time() - start_time,
                            'success': False, 'status': 'TIMEOUT'}

                if proc.returncode != 0:
                    stderr_snippet = (proc.stderr or '').strip()[:300]
                    logger.error(
                        "OCT binary exited with code %d. stderr: %s",
                        proc.returncode, stderr_snippet or '<empty>',
                    )
                    return {
                        'embedding': {}, 'time': elapsed,
                        'success': False, 'status': 'CRASH',
                        'error': f"OCT binary exit code {proc.returncode}: {stderr_snippet}",
                    }

                emb_file = out_base + ".embedding"
                embedding = {}
                if os.path.exists(emb_file) and os.path.getsize(emb_file) > 0:
                    with open(emb_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if ':' in line:
                                lp, pp = line.split(':', 1)
                                pp = pp.strip()
                                if pp:
                                    chain = ([int(x.strip()) for x in pp.split(',') if x.strip()]
                                             if ',' in pp else
                                             [int(x) for x in pp.split() if x])
                                    if chain:
                                        embedding[int(lp.strip())] = chain

                if not embedding:
                    return {'embedding': {}, 'time': elapsed, 'success': False, 'status': 'FAILURE'}

                return {'embedding': embedding, 'time': elapsed,
                        'chimera_dims': dims, 'chimera_graph': chimera_graph,
                        'algorithm': algo_name}

            except Exception as e:
                logger.error("OCT-%s error: %s", algo_name, e)
                return {'embedding': {}, 'time': __import__('time').time() - start_time,
                        'success': False, 'status': 'FAILURE'}
            finally:
                for p in [source_file, out_base,
                          (out_base + ".embedding") if out_base else None,
                          (out_base + ".timing") if out_base else None]:
                    if p and os.path.exists(p):
                        os.unlink(p)

    OctVariant.__name__ = f"Oct_{algo_name.replace('-', '_')}"
    OctVariant.__qualname__ = OctVariant.__name__
    return OctVariant


# Register all OCT variants
_OCT_CONFIGS = {
    'triad':             ([], False, 'TRIAD — deterministic, 2 qubits/node, handles dense graphs'),
    'triad-reduce':      ([], False, 'Reduced TRIAD — TRIAD with chain reduction'),
    'fast-oct':          (['-s', '42', '-r', '100'], True,  'Fast-OCT — randomized with seed/repeats'),
    'fast-oct-reduce':   (['-s', '42', '-r', '100'], True,  'Reduced Fast-OCT'),
    'hybrid-oct':        (['-s', '42', '-r', '100'], True,  'Hybrid-OCT — combined approach'),
    'hybrid-oct-reduce': (['-s', '42', '-r', '100'], True,  'Reduced Hybrid-OCT'),
}

for _name, (_flags, _seed, _desc) in _OCT_CONFIGS.items():
    _cls = _make_oct_class(_name, _flags, _desc, supports_seed=_seed)
    register_algorithm(f"oct-{_name}")(_cls)

# "oct_based" alias for oct-triad (the most reliable default)
ALGORITHM_REGISTRY["oct_based"] = ALGORITHM_REGISTRY["oct-triad"]
