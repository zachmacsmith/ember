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


def _make_timed_oct_class(algo_name: str, desc: str, chunk_repeats: int = 5):
    """Factory producing a *time-budgeted* OctVariant.

    Unlike `_make_oct_class`, which hands the timeout to `subprocess.run`
    and lets the C++ binary run a fixed ``-r 100`` repeats, this factory
    drives the outer loop from Python. It repeatedly invokes the binary
    with ``-r chunk_repeats`` and a fresh seed each call, keeps the best
    embedding found (shortest max chain length), and stops when any of:

      (a) the wall-clock ``timeout`` budget is nearly exhausted,
      (b) ``tries`` total subprocess calls have been made,
      (c) the best max-chain-length has not improved for ``patience``
          consecutive successful attempts (diminishing-returns exit).

    This mirrors the adaptive stopping criteria used by ``minorminer``:

      ===================================  =============================
      minorminer parameter                 OCT-timed equivalent
      ===================================  =============================
      ``timeout``                          ``timeout`` (same semantics)
      ``tries``                            ``tries`` (hard cap on calls)
      ``max_no_improvement``               ``patience`` (stall counter)
      ``chainlength_patience``             ``patience`` (same — OCT's
                                           only quality metric exposed
                                           here is chain length)
      ``random_seed``                      ``seed`` (used as base; each
                                           subprocess gets seed+i)
      ===================================  =============================
    """

    class TimedOctVariant(EmbeddingAlgorithm):
        __doc__ = desc
        _uses_subprocess = True
        _supports_seed = True
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

            # Reserve a small margin for final parsing/cleanup
            SAFETY_MARGIN = 1.5
            MIN_CALL_BUDGET = 0.5  # don't start a call with less than this

            base_seed = kwargs.get('seed')
            if base_seed is None:
                base_seed = 42

            # How many iterations per inner call. User may override.
            repeats_per_call = int(kwargs.get('chunk_repeats', chunk_repeats))
            if repeats_per_call < 1:
                repeats_per_call = 1

            # Diminishing-returns: exit if no improvement for this many
            # consecutive successful attempts. Set to 0 to disable early exit.
            patience = int(kwargs.get('patience', 20))

            # Hard cap on total subprocess calls (analogue of minorminer.tries).
            # Default effectively unbounded — time/patience dominate.
            tries = int(kwargs.get('tries', 10**9))
            if tries < 1:
                tries = 1

            best_embedding: dict = {}
            best_max_chain = float('inf')
            best_attempt_idx = -1
            attempts_made = 0
            successful_attempts = 0
            stalled_streak = 0
            last_error = None
            source_file = None
            early_exit = False

            try:
                # Write the source graph once — reused across all attempts
                with tempfile.NamedTemporaryFile(mode='w', suffix='.graph',
                                                 dir=str(oct_dir), delete=False) as f:
                    n = source_graph.number_of_nodes()
                    f.write(f"{n}\n")
                    for node in range(n):
                        f.write(f"{node}\n")
                    for u, v in source_graph.edges():
                        f.write(f"{u} {v}\n")
                    source_file = f.name

                attempt = 0
                tries_exhausted = False
                timeout_exit = False
                while True:
                    if attempts_made >= tries:
                        tries_exhausted = True
                        break
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed - SAFETY_MARGIN
                    if remaining < MIN_CALL_BUDGET:
                        timeout_exit = True
                        break

                    out_base = None
                    try:
                        with tempfile.NamedTemporaryFile(mode='w', dir=str(oct_dir),
                                                         prefix="oct_out_", delete=False) as f:
                            out_base = f.name

                        seed = (int(base_seed) + attempt) & 0x7FFFFFFF
                        flags = ['-s', str(seed), '-r', str(repeats_per_call)]

                        cmd = [str(oct_exe), '-a', algo_name,
                               '-pfile', source_file,
                               '-c', str(c_t), '-m', str(c_m), '-n', str(c_n),
                               '-o', out_base] + flags

                        # Cap this subprocess at what's actually remaining
                        call_timeout = min(remaining + SAFETY_MARGIN,
                                           timeout - (time.time() - start_time))
                        if call_timeout < MIN_CALL_BUDGET:
                            break

                        try:
                            proc = subprocess.run(cmd, capture_output=True, text=True,
                                                  timeout=call_timeout, cwd=str(oct_dir))
                        except subprocess.TimeoutExpired:
                            # Budget exhausted mid-call — return best we have
                            timeout_exit = True
                            break

                        attempts_made += 1

                        if proc.returncode != 0:
                            last_error = (f"exit {proc.returncode}: "
                                          f"{(proc.stderr or '').strip()[:200]}")
                            attempt += 1
                            continue

                        emb_file = out_base + ".embedding"
                        embedding: dict = {}
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

                        if embedding:
                            successful_attempts += 1
                            max_chain = max(len(c) for c in embedding.values())
                            if max_chain < best_max_chain:
                                best_max_chain = max_chain
                                best_embedding = embedding
                                best_attempt_idx = attempt
                                stalled_streak = 0
                            else:
                                stalled_streak += 1

                            # Diminishing-returns exit: only triggers once
                            # we already have *some* embedding in hand.
                            if patience > 0 and stalled_streak >= patience:
                                early_exit = True

                        attempt += 1
                        if early_exit:
                            break

                    finally:
                        # Clean up this attempt's output files
                        if out_base is not None:
                            for p in (out_base,
                                      out_base + ".embedding",
                                      out_base + ".timing"):
                                if os.path.exists(p):
                                    try:
                                        os.unlink(p)
                                    except OSError:
                                        pass

                elapsed = time.time() - start_time
                if not best_embedding:
                    return {
                        'embedding': {}, 'time': elapsed, 'success': False,
                        'status': 'FAILURE',
                        'error': last_error or
                                 f"No successful embedding after {attempts_made} attempts",
                        'n_attempts': attempts_made,
                    }

                if early_exit:
                    exit_reason = 'diminishing_returns'
                elif tries_exhausted:
                    exit_reason = 'tries_exhausted'
                elif timeout_exit:
                    exit_reason = 'timeout'
                else:
                    exit_reason = 'completed'

                return {
                    'embedding': best_embedding, 'time': elapsed,
                    'chimera_dims': dims, 'chimera_graph': chimera_graph,
                    'algorithm': algo_name,
                    'n_attempts': attempts_made,
                    'n_successful_attempts': successful_attempts,
                    'best_attempt_idx': best_attempt_idx,
                    'exit_reason': exit_reason,
                    'stalled_streak': stalled_streak,
                }

            except Exception as e:
                logger.error("Timed OCT-%s error: %s", algo_name, e)
                return {'embedding': {}, 'time': time.time() - start_time,
                        'success': False, 'status': 'FAILURE'}
            finally:
                if source_file and os.path.exists(source_file):
                    try:
                        os.unlink(source_file)
                    except OSError:
                        pass

    TimedOctVariant.__name__ = f"OctTimed_{algo_name.replace('-', '_')}"
    TimedOctVariant.__qualname__ = TimedOctVariant.__name__
    return TimedOctVariant


# Register time-budgeted variant for the randomized fast-oct-reduce.
# The underlying C++ algorithm name ('fast-oct-reduce') is reused — only
# the Python driving loop changes. Existing 'oct-fast-oct-reduce' etc. are
# untouched and continue to use the fixed ``-r 100`` behaviour.
_timed_cls = _make_timed_oct_class(
    'fast-oct-reduce',
    'Time-budgeted Reduced Fast-OCT — minorminer-style adaptive loop '
    '(tries + patience + wall-clock timeout)',
    chunk_repeats=5,
)
register_algorithm('oct-fast-oct-reduce-timed')(_timed_cls)

# Additional non-adaptive variants: same fixed-iteration behaviour as
# oct-fast-oct-reduce, but cranked up. Subject to the usual subprocess-
# level timeout — long-running graphs will still be killed if the
# iterations exceed the wall-clock budget.
_cls_1k = _make_oct_class(
    'fast-oct-reduce',
    ['-s', '42', '-r', '1000'],
    'Reduced Fast-OCT with 1,000 internal repeats (non-adaptive; '
    'subject to subprocess timeout)',
    supports_seed=True,
)
register_algorithm('oct-fast-oct-reduce-1k')(_cls_1k)

_cls_10k = _make_oct_class(
    'fast-oct-reduce',
    ['-s', '42', '-r', '10000'],
    'Reduced Fast-OCT with 10,000 internal repeats (non-adaptive; '
    'subject to subprocess timeout)',
    supports_seed=True,
)
register_algorithm('oct-fast-oct-reduce-10k')(_cls_10k)

# "oct_based" alias for oct-triad (the most reliable default)
ALGORITHM_REGISTRY["oct_based"] = ALGORITHM_REGISTRY["oct-triad"]
