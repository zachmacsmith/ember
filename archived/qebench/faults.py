"""
qebench/faults.py
=================
Fault simulation for hardware topology graphs.

Standalone module — no dependency on the benchmark runner.
"""

import random
from typing import Collection, List, Optional, Tuple

import networkx as nx


def simulate_faults(
    topology: nx.Graph,
    fault_rate: float = 0.0,
    fault_seed: Optional[int] = None,
    faulty_nodes: Optional[Collection[int]] = None,
    faulty_couplers: Optional[Collection[Tuple[int, int]]] = None,
) -> nx.Graph:
    """Simulate hardware faults by removing qubits and/or couplers from a topology.

    Mode is inferred from arguments:
    - **Random**:   ``fault_rate > 0`` — removes ``int(N * fault_rate)`` randomly
                    selected nodes and all their incident edges.
    - **Explicit**: ``faulty_nodes`` or ``faulty_couplers`` non-empty — removes
                    exactly those nodes/couplers. Isolated nodes left behind by
                    coupler removal are automatically cleaned up.
    - **No faults**: all defaults — returns a copy of the topology unchanged.

    Args:
        topology:       Hardware graph to fault.
        fault_rate:     Fraction of nodes to remove randomly. Must be in [0, 1].
        fault_seed:     Seed for random node selection (random mode only).
        faulty_nodes:   Explicit node IDs to remove.
        faulty_couplers: Explicit (u, v) edge pairs to remove.

    Returns:
        New ``nx.Graph`` with faults applied (copy, not a view).

    Raises:
        ValueError: On conflicting modes, out-of-range fault_rate, or
                    nodes/couplers that do not exist in the topology.
    """
    faulty_nodes = list(faulty_nodes) if faulty_nodes else []
    faulty_couplers = [tuple(e) for e in faulty_couplers] if faulty_couplers else []

    # ── Validation ──────────────────────────────────────────────────────────
    if fault_rate < 0.0 or fault_rate > 1.0:
        raise ValueError(
            f"fault_rate must be in [0.0, 1.0], got {fault_rate}"
        )

    if fault_rate > 0 and (faulty_nodes or faulty_couplers):
        raise ValueError(
            "Cannot combine fault_rate with faulty_nodes/faulty_couplers. "
            "Use one mode at a time."
        )

    if faulty_nodes:
        unknown = [n for n in faulty_nodes if n not in topology]
        if unknown:
            raise ValueError(
                f"faulty_nodes contains nodes not in topology: {unknown}"
            )

    if faulty_couplers:
        bad_nodes = [(u, v) for u, v in faulty_couplers
                     if u not in topology or v not in topology]
        if bad_nodes:
            raise ValueError(
                f"faulty_couplers references nodes not in topology: {bad_nodes}"
            )
        bad_edges = [(u, v) for u, v in faulty_couplers
                     if not topology.has_edge(u, v)]
        if bad_edges:
            raise ValueError(
                f"faulty_couplers references edges not in topology: {bad_edges}"
            )

    # ── Random mode ─────────────────────────────────────────────────────────
    if fault_rate > 0:
        rng = random.Random(fault_seed)
        n_faults = int(len(topology) * fault_rate)
        faulty = set(rng.sample(list(topology.nodes()), n_faults))
        return topology.subgraph(
            [n for n in topology.nodes() if n not in faulty]
        ).copy()

    # ── Explicit mode ────────────────────────────────────────────────────────
    if faulty_nodes or faulty_couplers:
        working = topology.copy()
        if faulty_nodes:
            working.remove_nodes_from(faulty_nodes)
        if faulty_couplers:
            working.remove_edges_from(faulty_couplers)
            # Remove isolated nodes created by coupler removal
            isolated = [n for n, deg in working.degree() if deg == 0]
            working.remove_nodes_from(isolated)
        return working

    # ── No faults ────────────────────────────────────────────────────────────
    return topology.copy()
