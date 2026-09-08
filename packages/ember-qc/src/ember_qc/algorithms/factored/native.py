"""Explicitly independent Zephyr construction for audited research experiments.

This entry point calls only the geometric constructor, its native conversion and
completion, pruning, and optional bounded contact reconstruction. Failed native
construction is returned as a failure, with its incomplete chains in diagnostics.
There is no external embedding fallback or cached embedding input.

``construction='search'`` reproduces the inherited order optimizer without its
legalizer. ``construction='packed'`` is a separate fixed research configuration:
one shared structural order and a bounded number of packing passes. A run never
competes between these configurations or chooses their best result.
"""
from __future__ import annotations

import math
import time

import networkx as nx
import numpy as np

from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
from ember_qc.algorithms.factored import plane
from ember_qc.algorithms.factored.field import (
    TileGrid, complete_seeds, wire_seeds_exact,
)
from ember_qc.algorithms.factored.polish import spur_prune


def _shared_order(source, seed, strategy):
    """An explicit configuration, not a graph-family dispatcher."""
    rng = np.random.default_rng(seed)
    nodes = list(source)
    if strategy == "random":
        return [nodes[int(i)] for i in rng.permutation(len(nodes))]
    if strategy == "degree":
        priority = {v: float(rng.random()) for v in nodes}
        return sorted(nodes, key=lambda v: (-source.degree(v), priority[v]))
    if strategy == "bfs":
        priority = {v: float(rng.random()) for v in nodes}
        remaining = set(nodes)
        order = []
        while remaining:
            root = max(remaining, key=lambda v: (source.degree(v), priority[v]))
            queue = [root]
            remaining.remove(root)
            for v in queue:
                order.append(v)
                neighbors = sorted((w for w in source[v] if w in remaining),
                                   key=lambda w: (-source.degree(w), priority[w]))
                for w in neighbors:
                    remaining.remove(w)
                    queue.append(w)
        return order
    raise ValueError(f"unknown order strategy: {strategy}")


def _packed_layout(src_adj, grid, order, *, passes, deadline):
    positions = {v: np.array([float(i), float(i)]) for i, v in enumerate(order)}
    orders = {0: list(order), 1: list(order)}
    state = None
    readouts = 0
    misses = 0
    for _ in range(passes):
        for axis in (1, 0, 1):
            if state is not None and deadline is not None and time.perf_counter() >= deadline:
                break
            positions, state, misses = plane.readout(
                axis, orders, positions, src_adj, grid, snap=True, bk=state)
            readouts += 1
    penalty, objective = plane.judge(state, positions, src_adj, grid,
                                     bar=float(plane.stride(grid)))
    if penalty > 0:
        for axis in (0, 1, 0):
            if deadline is not None and time.perf_counter() >= deadline:
                break
            positions, state, misses = plane.readout(
                axis, orders, positions, src_adj, grid, snap=True, bounded=True)
            readouts += 1
    return positions, state, {
        "asks": 0, "readouts": readouts, "misses": misses,
        "pen": int(penalty), "stair": float(objective),
        "stopped_by": "deadline" if deadline is not None and time.perf_counter() >= deadline
        else "packing_passes",
    }


def native_embed(source_graph, target_graph, *, timeout=60.0, seed=0,
                 construction="search", order_strategy="random", packing_passes=2,
                 max_asks=10000, sched_seed=None, polish_passes=0,
                 beam_width=4, max_groups=64, polish_group_sizes=(2, 3, 4),
                 polish_expansions=500000, polish_boundary_sites=0,
                 polish_group_policy="legacy", polish_objective='qubits',
                 polish_tree_policy='greedy', initialization='random',
                 polish_singleton_policy='legacy'):
    """Return a validated independent result or an explicit construction failure.

    Deadline overruns are reported and never counted as timely success. Conversion
    currently has no internal cancellation points; the experiment worker also uses
    an external watchdog. This limitation is recorded rather than hidden.
    Direct singleton relocation is an optional proposal rule inside the one
    contact-refinement call and shares that call's work and deadline limits.
    """
    started = time.perf_counter()
    deadline = started + timeout if timeout is not None and timeout > 0 else None
    diag = {"construction": construction, "order_strategy": order_strategy,
            "polish_passes": polish_passes, "beam_width": beam_width,
            "polish_group_sizes": list(polish_group_sizes),
            "polish_expansions": polish_expansions,
            "polish_boundary_sites": polish_boundary_sites,
            "polish_group_policy": polish_group_policy,
            'polish_objective': polish_objective,
            'polish_tree_policy': polish_tree_policy,
            'initialization': initialization}
    if polish_singleton_policy != 'legacy':
        diag['polish_singleton_policy'] = polish_singleton_policy

    def result(embedding, status, **extra):
        elapsed = time.perf_counter() - started
        if deadline is not None and time.perf_counter() > deadline:
            diag["deadline_overrun"] = max(0.0, elapsed - timeout)
            status = "TIMEOUT"
        return {"embedding": embedding, "success": status == "SUCCESS",
                "status": status, "time": elapsed, "diag": diag, **extra}

    if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
        return result({}, "ERROR", error="timeout must be finite and positive, or None")
    if construction not in ("search", "packed"):
        return result({}, "ERROR", error="unknown construction")
    if initialization not in ('random', 'spectral'):
        return result({}, 'ERROR', error='unknown initialization')
    if initialization == 'spectral' and construction != 'search':
        return result({}, 'ERROR', error='spectral initialization requires search construction')
    if polish_singleton_policy not in ('legacy', 'direct'):
        return result({}, 'ERROR', error='unknown singleton policy')
    if polish_singleton_policy == 'direct' and (
            target_graph.is_directed() or target_graph.is_multigraph()
            or nx.number_of_selfloops(target_graph)):
        return result({}, 'ERROR', error='direct singleton target must be simple and undirected')
    if packing_passes < 1 or max_asks < 1 or polish_passes < 0:
        return result({}, "ERROR", error="invalid work limit")
    if (source_graph.is_directed() or source_graph.is_multigraph()
            or nx.number_of_selfloops(source_graph)):
        return result({}, "ERROR", error="source must be simple and undirected")
    if target_graph.graph.get("family") != "zephyr":
        return result({}, "UNSUPPORTED", error="native research constructor requires Zephyr")
    if target_graph.graph.get("labels", "int") != "int":
        return result({}, "UNSUPPORTED", error="integer target labels required")
    if (len(source_graph) > len(target_graph)
            or source_graph.number_of_edges() > target_graph.number_of_edges()):
        return result({}, "INFEASIBLE_CAPACITY")
    if not source_graph:
        return result({}, "SUCCESS")

    # Existing geometric primitives require integer source labels. Keep an explicit
    # inverse map so mixed/tuple labels and isolated vertices survive the adapter.
    labels = list(source_graph)
    mapping = {v: i for i, v in enumerate(labels)}
    source = nx.relabel_nodes(source_graph, mapping, copy=True)
    src_adj = {v: sorted(source[v]) for v in source}
    adjacency = build_adjacency(target_graph)
    try:
        import dwave_networkx as dnx
        positions = dnx.zephyr_layout(target_graph)
        grid = TileGrid(target_graph, positions, courses=True)
        if grid.stride <= 1 or not grid.wire_map:
            return result({}, "UNSUPPORTED", error="course-resolved native wires unavailable")
        layout_started = time.perf_counter()
        if construction == "search":
            initialization_args = {}
            if initialization == 'spectral':
                from ember_qc.algorithms.factored.spectral_order import spectral_orders
                initial_orders, initialization_info = spectral_orders(
                    src_adj, seed=seed, deadline=deadline)
                diag['initialization_info'] = initialization_info
                if initial_orders is None:
                    diag['layout_wall'] = time.perf_counter() - layout_started
                    status = ('TIMEOUT' if initialization_info['status'] == 'deadline'
                              else 'INITIALIZATION_FAILED')
                    return result({}, status)
                initialization_args['initial_orders'] = initial_orders
                if deadline is not None and time.perf_counter() >= deadline:
                    diag['layout_wall'] = time.perf_counter() - layout_started
                    return result({}, 'TIMEOUT')
            points, state, layout_info = plane.arrange(
                src_adj, grid, seed=seed, max_asks=max_asks, deadline=deadline,
                snap=True, sched_seed=seed if sched_seed is None else sched_seed,
                **initialization_args)
        else:
            points, state, layout_info = _packed_layout(
                src_adj, grid, _shared_order(source, seed, order_strategy),
                passes=packing_passes, deadline=deadline)
        diag["layout_wall"] = time.perf_counter() - layout_started
        diag["layout"] = layout_info
        if deadline is not None and time.perf_counter() >= deadline:
            return result({}, "TIMEOUT")
        chains, conversion = wire_seeds_exact(grid, points, state[1], src_adj, state)
        chains, completion = complete_seeds(grid, chains, src_adj, adjacency)
        # Isolates impose no contacts and need just one unused physical vertex.
        used = {q for c in chains.values() for q in c}
        free = iter(q for q in target_graph if q not in used)
        for v in source:
            if not chains.get(v) and not src_adj[v]:
                q = next(free, None)
                if q is not None:
                    chains[v] = [q]
        diag["conversion"] = conversion
        diag["completion"] = completion
        if not is_valid_embedding(chains, source, target_graph):
            diag["partial_qubits"] = sum(len(c) for c in chains.values())
            return result({}, "CONSTRUCTION_FAILED",
                          partial_embedding={labels[v]: list(c) for v, c in chains.items()})
        diag["constructed_qubits"] = sum(map(len, chains.values()))
        chains = spur_prune(chains, src_adj, adjacency, deadline=deadline)
        diag["pruned_qubits"] = sum(map(len, chains.values()))
        if polish_passes and (deadline is None or time.perf_counter() < deadline):
            from ember_qc.algorithms.factored.contact_repair import contact_polish
            singleton_options = ({'singleton_policy': polish_singleton_policy}
                                 if polish_singleton_policy != 'legacy' else {})
            chains, polish_info = contact_polish(
                chains, source, target_graph, deadline=deadline,
                max_passes=polish_passes, beam_width=beam_width, max_groups=max_groups,
                group_sizes=polish_group_sizes, max_expansions=polish_expansions,
                boundary_sites=polish_boundary_sites, group_policy=polish_group_policy,
                objective=polish_objective, tree_policy=polish_tree_policy,
                **singleton_options)
            diag["contact_repair"] = polish_info
        embedding = {labels[v]: list(c) for v, c in chains.items()}
        if not is_valid_embedding(embedding, source_graph, target_graph):
            return result({}, "INVALID_OUTPUT")
        return result(embedding, "SUCCESS")
    except Exception as exc:
        return result({}, "ERROR", error=f"{type(exc).__name__}: {exc}")
