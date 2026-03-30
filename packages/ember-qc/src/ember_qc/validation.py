"""
ember_qc/validation.py
=====================
Independent validation of algorithm outputs before database storage.

The algorithm is treated as an untrusted black box. Validation runs on every
result immediately after embed() returns, before any metrics are computed or
anything is written to the database.

Implemented:
  Layer 2 — Type/Format: numpy int leakage, tuple chains, NaN/zero wall time,
             spurious/missing keys, chain values not in target graph,
             CPU time plausibility. Runs first on every result.
  Layer 1 — Structural: five mathematical checks on the embedding itself.
             Runs only if Layer 2 passed and algorithm claimed success.

Not yet implemented (TODO):
  Layer 3 — Consistency: field-level cross-checks (success ↔ embedding,
             counter types, valid status strings). Must run after Layers 1 & 2.
  Layer 4 — Statistical: batch-level sanity checks run once after all trials
             complete (seed reproducibility, timing outliers, universal failures).

Integration order:
  1. Layer 2 (type/format) — always, on every result
  2. Layer 1 (structural) — only if Layer 2 passed and algorithm claimed success
  3. Layer 3 (consistency) — always [TODO]

Import:
    from ember_qc.validation import validate_layer1, validate_layer2, ValidationResult
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Optional

import networkx as nx


@dataclass
class ValidationResult:
    """Result of a single validation call.

    Attributes:
        passed:     True if all checks passed.
        check_name: Short identifier for the failing check, e.g. ``"coverage"``.
                    None if passed.
        detail:     Human-readable description of the failure: which vertex was
                    missing, which qubit was duplicated, etc. None if passed.
    """
    passed: bool
    check_name: Optional[str] = None
    detail: Optional[str] = None

    def __bool__(self) -> bool:
        return self.passed


# ── Layer 1 — Structural validation ────────────────────────────────────────────

def validate_layer1(embedding: dict,
                    source_graph: nx.Graph,
                    target_graph: nx.Graph) -> ValidationResult:
    """Verify that the embedding is a mathematically correct minor embedding.

    Runs five checks in order, stopping at the first failure:

    1. **Coverage** — every source vertex has a key in the embedding.
    2. **Non-empty chains** — every chain contains at least one target node.
    3. **Connectivity** — every chain forms a connected subgraph of the target
       graph. Checked via BFS on the target graph's adjacency structure so no
       subgraph object is created. Chains of length 1 are trivially connected.
    4. **Disjointness** — no target qubit appears in more than one chain.
       Uses a reverse-map dict for O(1) collision detection.
    5. **Edge preservation** — for every source edge, at least one target edge
       exists between the two chains. Uses the O(e) approach: iterate qubits in
       one chain, check each neighbor against the other chain set.

    Args:
        embedding:    The raw embedding dict ``{source_node: [target_qubits]}``.
        source_graph: The problem graph being embedded.
        target_graph: The hardware topology graph.

    Returns:
        :class:`ValidationResult` — ``passed=True`` on success, or
        ``passed=False`` with ``check_name`` and ``detail`` on failure.

    Note:
        Layer 2 must run before Layer 1 in production. Layer 2 guarantees that
        keys are valid source-node IDs, chain values are valid target-node IDs,
        and all types are plain Python ``int`` — preconditions Layer 1 relies on.
    """
    # ── Check 1: Coverage ──────────────────────────────────────────────────────
    for node in source_graph.nodes():
        if node not in embedding:
            return ValidationResult(
                passed=False,
                check_name="coverage",
                detail=f"source vertex {node!r} has no chain in embedding",
            )

    # ── Check 2: Non-empty chains ──────────────────────────────────────────────
    for src, chain in embedding.items():
        if len(chain) == 0:
            return ValidationResult(
                passed=False,
                check_name="non_empty_chains",
                detail=f"chain for source vertex {src!r} is empty",
            )

    # ── Check 3: Connectivity ──────────────────────────────────────────────────
    # BFS on target graph restricted to chain nodes — no subgraph object created.
    for src, chain in embedding.items():
        if len(chain) == 1:
            continue  # trivially connected
        chain_set = set(chain)
        visited = {chain[0]}
        queue = [chain[0]]
        while queue:
            node = queue.pop()
            for nbr in target_graph.neighbors(node):
                if nbr in chain_set and nbr not in visited:
                    visited.add(nbr)
                    queue.append(nbr)
        if len(visited) != len(chain_set):
            disconnected = chain_set - visited
            return ValidationResult(
                passed=False,
                check_name="connectivity",
                detail=(
                    f"chain for source vertex {src!r} is not connected in "
                    f"target graph; unreachable target nodes: {sorted(disconnected)}"
                ),
            )

    # ── Check 4: Disjointness ──────────────────────────────────────────────────
    # Build reverse map as we go; fail immediately on first collision.
    qubit_to_src: dict = {}
    for src, chain in embedding.items():
        for qubit in chain:
            if qubit in qubit_to_src:
                return ValidationResult(
                    passed=False,
                    check_name="disjointness",
                    detail=(
                        f"target qubit {qubit!r} appears in chains for both "
                        f"source vertex {qubit_to_src[qubit]!r} and {src!r}"
                    ),
                )
            qubit_to_src[qubit] = src

    # ── Check 5: Edge preservation ─────────────────────────────────────────────
    # O(e_target) total: for each qubit in chain_u, check its target-graph
    # neighbors against chain_v_set (O(1) lookup). Each target edge is visited
    # at most twice across the full loop.
    for src_u, src_v in source_graph.edges():
        chain_v_set = set(embedding[src_v])
        found = False
        for qubit_u in embedding[src_u]:
            for nbr in target_graph.neighbors(qubit_u):
                if nbr in chain_v_set:
                    found = True
                    break
            if found:
                break
        if not found:
            return ValidationResult(
                passed=False,
                check_name="edge_preservation",
                detail=(
                    f"source edge ({src_u!r}, {src_v!r}) has no corresponding "
                    f"edge in target graph between the two chains"
                ),
            )

    return ValidationResult(passed=True)


# ── Layer 2 — Type and format validation ────────────────────────────────────────

def validate_layer2(result: dict,
                    source_graph: nx.Graph,
                    target_graph: nx.Graph) -> ValidationResult:
    """Catch serialization bugs and type errors before they reach Layer 1 or the DB.

    Runs on every result, even failures, before Layer 1. Type errors would cause
    Layer 1 to raise exceptions rather than return a clean INVALID_OUTPUT, so
    Layer 2 must act as the first line of defence.

    Six checks in order (stops at first failure):

    1. **Key validity** — all embedding keys are node IDs present in the source
       graph. No extra keys (spurious output), no missing keys (caught again by
       Layer 1 coverage, but here we catch the case with extras).
    2. **Chain format** — all chains are Python ``list`` objects. ``set``,
       ``tuple``, and ``numpy.ndarray`` are invalid even if their contents pass.
       Runs before value/type checks so those can iterate chains directly.
    3. **Value validity** — all qubit IDs in every chain exist in the target graph.
    4. **Type correctness** — all embedding keys and every qubit in every chain
       are plain Python ``int``. ``numpy.int64`` and other integer-like types are
       rejected — they break JSON serialization and database storage silently.
    5. **Wall time validity** — if the algorithm reports a wall time
       (``result['time']`` is present), it must be a positive, finite ``float``.
       Rejects NaN, infinity, zero, and negative values.
    6. **CPU time plausibility** — if ``result['cpu_time']`` is present, it must
       be a non-negative ``float`` and must not exceed
       ``wall_time × os.cpu_count()``. CPU time exceeding that bound is
       physically impossible and indicates a measurement bug.

    Args:
        result:       The raw dict returned by ``algo.embed()``.
        source_graph: The problem graph being embedded.
        target_graph: The hardware topology graph.

    Returns:
        :class:`ValidationResult` — ``passed=True`` on success, or
        ``passed=False`` with ``check_name`` and ``detail`` on failure.
    """
    embedding = result.get('embedding') or {}
    source_nodes = set(source_graph.nodes())
    target_nodes = set(target_graph.nodes())

    if embedding:
        embedding_keys = set(embedding.keys())

        # ── Check 1: Key validity ───────────────────────────────────────────────
        extra_keys = embedding_keys - source_nodes
        if extra_keys:
            return ValidationResult(
                passed=False,
                check_name="key_validity",
                detail=(
                    f"embedding contains {len(extra_keys)} key(s) not in source graph: "
                    f"{sorted(extra_keys)[:5]}{'...' if len(extra_keys) > 5 else ''}"
                ),
            )
        missing_keys = source_nodes - embedding_keys
        if missing_keys:
            return ValidationResult(
                passed=False,
                check_name="key_validity",
                detail=(
                    f"embedding missing {len(missing_keys)} source vertex key(s): "
                    f"{sorted(missing_keys)[:5]}{'...' if len(missing_keys) > 5 else ''}"
                ),
            )

        for src, chain in embedding.items():
            # ── Check 4: Chain format (moved first) ────────────────────────────
            # Must run before checks 2 & 3 so they can iterate chain directly
            # without a fallback. A numpy array or tuple would otherwise pass
            # checks 2 & 3 vacuously (via the old `else []` guard) and only
            # fail here — giving a misleading validation order.
            if not isinstance(chain, list):
                return ValidationResult(
                    passed=False,
                    check_name="chain_format",
                    detail=(
                        f"chain for source vertex {src!r} is {type(chain).__name__!r}, "
                        f"expected list (set, tuple, and numpy arrays are invalid)"
                    ),
                )

            # ── Check 2: Value validity ─────────────────────────────────────────
            for qubit in chain:
                if qubit not in target_nodes:
                    return ValidationResult(
                        passed=False,
                        check_name="value_validity",
                        detail=(
                            f"chain for source vertex {src!r} contains qubit {qubit!r} "
                            f"which does not exist in the target graph"
                        ),
                    )

            # ── Check 3: Type correctness ───────────────────────────────────────
            if type(src) is not int:
                return ValidationResult(
                    passed=False,
                    check_name="type_correctness",
                    detail=(
                        f"embedding key {src!r} is {type(src).__name__!r}, "
                        f"expected plain Python int (numpy.int64 and similar are invalid)"
                    ),
                )
            for qubit in chain:
                if type(qubit) is not int:
                    return ValidationResult(
                        passed=False,
                        check_name="type_correctness",
                        detail=(
                            f"qubit {qubit!r} in chain for source vertex {src!r} is "
                            f"{type(qubit).__name__!r}, expected plain Python int"
                        ),
                    )

    # ── Check 5: Wall time validity ─────────────────────────────────────────────
    if 'time' in result:
        wall = result['time']
        if not isinstance(wall, (int, float)) or not math.isfinite(wall) or wall <= 0:
            return ValidationResult(
                passed=False,
                check_name="wall_time_validity",
                detail=(
                    f"algorithm-reported wall time {wall!r} is invalid; "
                    f"must be a positive finite float (not NaN, inf, zero, or negative)"
                ),
            )

    # ── Check 6: CPU time plausibility ─────────────────────────────────────────
    if 'cpu_time' in result and 'time' in result:
        cpu = result['cpu_time']
        wall = result['time']
        if not isinstance(cpu, (int, float)) or cpu < 0:
            return ValidationResult(
                passed=False,
                check_name="cpu_time_plausibility",
                detail=(
                    f"cpu_time {cpu!r} is invalid; must be a non-negative float"
                ),
            )
        n_cores = os.cpu_count() or 1
        if isinstance(wall, (int, float)) and math.isfinite(wall) and wall > 0:
            if cpu > wall * n_cores:
                return ValidationResult(
                    passed=False,
                    check_name="cpu_time_plausibility",
                    detail=(
                        f"cpu_time {cpu:.3f}s exceeds wall_time {wall:.3f}s × "
                        f"{n_cores} cores = {wall * n_cores:.3f}s; "
                        f"physically impossible, indicates a measurement bug"
                    ),
                )

    return ValidationResult(passed=True)
