"""
docs/paper3/data/_runner_common.py
===================================
Shared helpers for paper3 script-route experiments (protocol.md, route choice
section). Every e*_*.py runner in this directory imports from here so the
measurement conventions are implemented exactly once:

* ``terminal_polish``      — the polish-parity pass (protocol rule 3): a
                             deadline-bounded spur-prune applied to EVERY arm's
                             successful embedding, producing the ``acl_spur``
                             column.
* ``acl`` / ``embedding_metrics`` — mean chain length and the cheap size
                             metrics (max chain, qubits, intra-chain couplers),
                             delegating to ``ember_qc.benchmark``'s reference
                             implementation.
* ``run_arm_watchdogged``  — candidate (non-MM-family) arms run in a separate
                             process with a hard kill at timeout+grace
                             (protocol route-choice rule: the harness has no
                             watchdog; a hang stalls a whole batch). MM-family
                             arms are exempt (known cooperative).
* CSV append/resume        — one flushed row per completed run;
                             ``load_done_keys`` supports ``--resume``.
* ``build_target`` / ``make_instance`` — the E0 topology and ER-instance
                             constructors, so every script generates
                             byte-identical graphs from the same params.

Not runnable on its own; no state, no side effects at import beyond pinning
BLAS/OMP threads to 1 (protocol hyde06 rule — must happen before numpy loads).
"""

import os

# Pin BLAS/OMP to one thread per process (protocol.md, hyde06 section). Must be
# set before numpy is first imported anywhere in the process.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import csv
import multiprocessing
import queue as _queue
import time
import traceback
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import networkx as nx
import dwave_networkx as dnx

from ember_qc.benchmark import compute_embedding_metrics
from ember_qc.embedding_backend import build_adjacency
from ember_qc.algorithms.factored.polish import spur_prune

Embedding = Dict[int, List[int]]


# ──────────────────────────────────────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────────────────────────────────────

def acl(embedding: Embedding) -> float:
    """Mean chain length of an embedding (the paper's headline metric)."""
    return sum(len(c) for c in embedding.values()) / len(embedding)


def embedding_metrics(embedding: Embedding, target_graph: nx.Graph) -> Dict:
    """ACL plus the cheap size metrics, via the framework's reference code.

    Returns ``{"acl", "max_chain", "qubits", "couplers"}``.
    """
    m = compute_embedding_metrics(embedding, target_graph)
    return {
        "acl": m["avg_chain_length"],
        "max_chain": m["max_chain_length"],
        "qubits": m["total_qubits_used"],
        "couplers": m["total_couplers_used"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Polish parity (protocol rule 3)
# ──────────────────────────────────────────────────────────────────────────────

def terminal_polish(embedding: Embedding, source_graph: nx.Graph,
                    target_graph: nx.Graph, deadline_s: float = 5.0,
                    adj=None) -> Embedding:
    """Spur-prune ``embedding`` against the actual source edges, deadline-bounded.

    This is the ONE polish applied identically to every arm's successful
    embedding (protocol rule 3); its ACL is the ``acl_spur`` column. Pruning is
    validity-preserving move by move, so hitting the deadline is safe.

    ``adj`` — optional prebuilt ``build_adjacency(target_graph)`` (workers keep
    one per topology; rebuilding per call is correct but slower).
    """
    if not embedding:
        return embedding
    if adj is None:
        adj = build_adjacency(target_graph)
    src_adj = {int(v): sorted(int(u) for u in source_graph.neighbors(v))
               for v in source_graph.nodes()}
    deadline = time.perf_counter() + deadline_s
    return spur_prune(embedding, src_adj, adj, deadline=deadline)


# ──────────────────────────────────────────────────────────────────────────────
# Watchdog for candidate arms (protocol route-choice rule)
# ──────────────────────────────────────────────────────────────────────────────

def _watchdog_child(q: multiprocessing.Queue, fn: Callable,
                    args: tuple, kwargs: dict) -> None:
    try:
        result = fn(*args, **kwargs)
        q.put(("OK", result, ""))
    except Exception:
        q.put(("CRASH", None, traceback.format_exc(limit=8)))


def run_arm_watchdogged(fn: Callable, timeout_s: float, grace_s: float = 30.0,
                        args: tuple = (), kwargs: Optional[dict] = None,
                        ) -> Tuple[str, Optional[dict], str]:
    """Run ``fn(*args, **kwargs)`` in a separate process; hard-kill it if it has
    not returned by ``timeout_s + grace_s``.

    Returns ``(status, result_or_None, err_string)`` with status one of:

    * ``"OK"``     — fn returned; result is whatever it returned (a dict).
    * ``"KILLED"`` — hard-killed at timeout+grace (the arm hung past its own
                     cooperative timeout); result is None.
    * ``"CRASH"``  — fn raised, or the child died without reporting.

    Uses the ``fork`` start method explicitly (Linux-native; works on macOS for
    this pure-numeric stack) so the child inherits the worker's module globals
    (built targets, busclique caches) with zero pickling/rebuild cost.
    Candidate (non-MM-family) arms go through here; minorminer-family arms are
    exempt (protocol: known cooperative).
    """
    ctx = multiprocessing.get_context("fork")
    q = ctx.Queue()
    proc = ctx.Process(target=_watchdog_child, args=(q, fn, args, kwargs or {}),
                       daemon=True)
    proc.start()
    try:
        status, result, err = q.get(timeout=timeout_s + grace_s)
    except _queue.Empty:
        status, result, err = "KILLED", None, (
            f"watchdog hard-kill at {timeout_s:g}+{grace_s:g}s")
        if proc.is_alive():
            proc.kill()   # no grace beyond the grace: it already overstayed
    except Exception as exc:  # queue corrupted by a dying child
        status, result, err = "CRASH", None, f"watchdog queue error: {exc!r}"
    if proc.is_alive():
        proc.join(timeout=2.0)
    if proc.is_alive():
        proc.kill()
        proc.join(timeout=10.0)
    if status == "OK" and proc.exitcode not in (0, None) and result is None:
        status, err = "CRASH", f"child exitcode {proc.exitcode}"
    q.close()
    return status, result, err


# ──────────────────────────────────────────────────────────────────────────────
# CSV append / resume
# ──────────────────────────────────────────────────────────────────────────────

def append_row(csv_path: str, fieldnames: Sequence[str], row: Dict) -> None:
    """Append one row (writing the header iff the file is new/empty) and flush.

    Open-per-append keeps every completed run durable even if the parent is
    killed; row rates in these experiments are far too low for it to matter.
    """
    need_header = (not os.path.exists(csv_path)
                   or os.path.getsize(csv_path) == 0)
    with open(csv_path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fieldnames))
        if need_header:
            w.writeheader()
        w.writerow(row)
        fh.flush()
        os.fsync(fh.fileno())


def load_done_keys(csv_path: str, key_fields: Sequence[str]) -> Set[tuple]:
    """Return the set of key tuples already present in ``csv_path``.

    Keys are tuples of the RAW CSV strings of ``key_fields``; callers must
    stringify their task keys identically (see :func:`stringify_key`).
    Missing/empty file -> empty set (fresh run).
    """
    done: Set[tuple] = set()
    if not os.path.exists(csv_path):
        return done
    with open(csv_path, newline="") as fh:
        for rec in csv.DictReader(fh):
            try:
                done.add(tuple(rec[f] for f in key_fields))
            except KeyError:
                continue  # header mismatch — treat row as unknown
    return done


def stringify_key(*values) -> tuple:
    """Stringify a task key exactly as ``csv`` will render the row values.

    Floats must be passed as floats (so 1.0 -> "1.0", 0.12 -> "0.12"), ints as
    ints; this mirrors DictWriter's ``str()`` of each cell.
    """
    return tuple(str(v) for v in values)


def clean_err(err) -> str:
    """One-line, truncated error string safe for a CSV cell."""
    if not err:
        return ""
    return " | ".join(str(err).strip().splitlines())[:300]


# ──────────────────────────────────────────────────────────────────────────────
# E0 topology / instance constructors
# ──────────────────────────────────────────────────────────────────────────────

TOPOLOGIES = ("P16", "Z12")


def build_target(topo_name: str) -> nx.Graph:
    """The two E0 hardware graphs, by short name."""
    if topo_name == "P16":
        return dnx.pegasus_graph(16)
    if topo_name == "Z12":
        return dnx.zephyr_graph(12)
    raise ValueError(f"unknown topology {topo_name!r} (expected P16 or Z12)")


def make_instance(n: int, p: float, inst_seed: int) -> nx.Graph:
    """The E0 source instance for cell (n, p) and instance seed.

    p == 1.0 rows are the complete graph (instance-seed-independent by
    construction); otherwise G(n, p) with the given seed, relabeled 0..n-1.
    """
    if p >= 1.0:
        return nx.complete_graph(n)
    return nx.convert_node_labels_to_integers(
        nx.gnp_random_graph(n, p, seed=inst_seed))
