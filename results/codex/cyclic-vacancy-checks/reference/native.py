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


def _final_deletion_cleanup(chains, source, target, src_adj, adjacency, *,
                            deadline, polish_passes, info):
    """Enabled-only wrapper; the original-graph final validator stays outside."""
    started = time.perf_counter()
    try:
        info['before_qubits'] = sum(map(len, chains.values()))
        info['after_qubits'] = info['before_qubits']
        info['qubits_saved'] = 0
        info['status'] = 'skipped'
        if not polish_passes:
            info['reason'] = 'polish_disabled'
            return chains, None
        if not info['contact_invoked']:
            info['reason'] = 'deadline_before_refinement'
            return chains, None
        if info['contact_invalid_input']:
            info.update(status='error', reason='invalid_contact_input')
            return chains, 'INVALID_OUTPUT'
        if deadline is not None and time.perf_counter() >= deadline:
            info['reason'] = 'deadline_before_cleanup'
            return chains, None
        checking = time.perf_counter()
        try:
            info['entry_validated'] = is_valid_embedding(chains, source, target)
        finally:
            info['entry_validation_wall'] = time.perf_counter() - checking
        if not info['entry_validated']:
            info.update(status='error', reason='invalid_cleanup_entry')
            return chains, 'INVALID_OUTPUT'
        if deadline is not None and time.perf_counter() >= deadline:
            info['reason'] = 'deadline_after_entry_validation'
            return chains, None
        from ember_qc.algorithms.factored.deletion_closure import deletion_closure
        info['module_calls'] += 1
        calling = time.perf_counter()
        try:
            chains, module_info = deletion_closure(
                chains, src_adj, adjacency, deadline=deadline)
        finally:
            info['module_call_wall'] = time.perf_counter() - calling
        info['module_returned'] = True
        info['module'] = module_info
        info['after_qubits'] = sum(map(len, chains.values()))
        info['qubits_saved'] = info['before_qubits'] - info['after_qubits']
        info['status'] = 'completed' if module_info['closure_complete'] else 'interrupted'
        info['reason'] = module_info['stopped_reason']
        return chains, None
    except Exception:
        info.update(status='error', reason='exception')
        raise
    finally:
        info['wall'] = time.perf_counter() - started


class _VacancyBudget:
    """One stage's relocation-proposal allowance; other costs consume wall time."""
    def __init__(self, deadline):
        self.limit = 50000
        self.expansions = 0
        self.deadline = deadline

    def pop(self):
        if self.expansions >= self.limit or time.perf_counter() >= self.deadline:
            return False
        self.expansions += 1
        return True


def _bounded_vacancy_refinement(chains, source, target, src_adj, adjacency, *,
                                started, deadline, cleanup_info, info):
    """Evolve one valid incumbent; unsuccessful queries never replace it."""
    stage_start = time.perf_counter()
    elapsed = max(0.0, stage_start - started)
    allowance = min(1.0, 0.2 * elapsed)
    stage_deadline = stage_start + allowance
    if deadline is not None:
        stage_deadline = min(deadline, stage_deadline)
    budget = _VacancyBudget(stage_deadline)
    info.update(status='skipped', reason=None, elapsed_before_stage=elapsed,
                allowance=allowance, deadline=stage_deadline,
                original_deadline=deadline, before_qubits=sum(map(len, chains.values())),
                after_qubits=sum(map(len, chains.values())), qubits_saved=0,
                accepted=0, query_calls=0, proposal_limit=budget.limit,
                successful_call_limit=20, proposals_used=0, calls=[],
                module_call_wall=0.0, validation_wall=0.0)
    try:
        if cleanup_info['status'] != 'completed':
            info['reason'] = 'cleanup_not_completed'
            return chains, None
        if time.perf_counter() >= stage_deadline:
            info['reason'] = 'deadline_before_vacancy'
            return chains, None
        from ember_qc.algorithms.factored.vacancy_repair import vacancy_repair
        info['status'] = 'completed'
        for index in range(1, 21):
            if time.perf_counter() >= stage_deadline:
                info.update(status='interrupted', reason='deadline')
                break
            if budget.expansions >= budget.limit:
                info.update(status='interrupted', reason='work')
                break
            call = dict(index=index, before_qubits=info['after_qubits'],
                        after_qubits=info['after_qubits'], committed=False,
                        commit_rejection=None, budget_start=budget.expansions,
                        budget_end=None, module_call_wall=None, validation_wall=None,
                        candidate_validated=None, core=None)
            info['calls'].append(call)
            info['query_calls'] += 1
            calling = time.perf_counter()
            try:
                candidate, core_info = vacancy_repair(
                    chains, src_adj, adjacency, (), budget=budget, deadline=stage_deadline)
                call['core'] = core_info
            finally:
                call['module_call_wall'] = time.perf_counter() - calling
                call['budget_end'] = budget.expansions
                info['module_call_wall'] += call['module_call_wall']
            if (core_info.get('error') is not None
                    or core_info.get('stopped_reason') in ('invalid_input', 'internal_error')):
                call['commit_rejection'] = 'core_error'
                info.update(status='error', reason='core_error', error=core_info.get('error'))
                return chains, 'ERROR'
            if candidate is None:
                info['reason'] = core_info.get('stopped_reason', 'no_proposal')
                if info['reason'] in ('deadline', 'work'):
                    info['status'] = 'interrupted'
                break
            if (not core_info.get('candidate_returned')
                    or not core_info.get('certificate_complete')
                    or sum(map(len, candidate.values())) != call['before_qubits'] - 1):
                call['commit_rejection'] = 'invalid_candidate_contract'
                info.update(status='error', reason='invalid_candidate_contract')
                return chains, 'INVALID_OUTPUT'
            if time.perf_counter() >= stage_deadline:
                call['commit_rejection'] = 'deadline'
                info.update(status='interrupted', reason='deadline')
                break
            checking = time.perf_counter()
            try:
                call['candidate_validated'] = is_valid_embedding(candidate, source, target)
            finally:
                call['validation_wall'] = time.perf_counter() - checking
                info['validation_wall'] += call['validation_wall']
            if not call['candidate_validated']:
                call['commit_rejection'] = 'invalid_candidate'
                info.update(status='error', reason='invalid_candidate')
                return chains, 'INVALID_OUTPUT'
            # The full candidate and its accounting exist before the admission gate.
            if time.perf_counter() >= stage_deadline:
                call['commit_rejection'] = 'deadline'
                info.update(status='interrupted', reason='deadline')
                break
            chains = candidate
            call['committed'] = True
            call['after_qubits'] -= 1
            info['accepted'] += 1
            info['after_qubits'] -= 1
            info['qubits_saved'] += 1
        else:
            info['reason'] = 'successful_call_limit'
        return chains, None
    except Exception as exc:
        info.update(status='error', reason='exception', error=f'{type(exc).__name__}: {exc}')
        if info['calls'] and not info['calls'][-1]['committed']:
            info['calls'][-1]['commit_rejection'] = 'exception'
        return chains, 'ERROR'
    finally:
        ended = time.perf_counter()
        info['proposals_used'] = budget.expansions
        info['wall'] = ended - stage_start
        info['deadline_overrun'] = max(0.0, ended - stage_deadline)
        if ended >= stage_deadline and info['status'] == 'completed':
            info.update(status='interrupted', reason='deadline')


def native_embed(source_graph, target_graph, *, timeout=60.0, seed=0,
                 construction="search", order_strategy="random", packing_passes=2,
                 max_asks=10000, sched_seed=None, polish_passes=0,
                 beam_width=4, max_groups=64, polish_group_sizes=(2, 3, 4),
                 polish_expansions=500000, polish_boundary_sites=0,
                 polish_group_policy="legacy", polish_objective='qubits',
                 polish_tree_policy='greedy', initialization='random',
                 polish_singleton_policy='legacy', polish_star_policy='off',
                 final_cleanup='off', vacancy_refinement='off'):
    """Return a validated independent result or an explicit construction failure.

    Deadline overruns are reported and never counted as timely success. Conversion
    currently has no internal cancellation points; the experiment worker also uses
    an external watchdog. This limitation is recorded rather than hidden.
    Direct singleton relocation is an optional proposal rule inside the one
    contact-refinement call and shares that call's work and deadline limits.
    Matching-star or connected-center relocation selects one experimental
    proposal policy in that same call; either requires the legacy singleton policy.
    ``final_cleanup='deletion'`` optionally closes safe single deletions after
    legacy contact refinement, within the original deadline and before final
    validation. It is currently supported only with greedy contact scoring,
    legacy singletons and stars off; disabled refinement causes a recorded skip.
    ``vacancy_refinement='bounded'`` adds at most 20 Q-minus-one contractions
    after completed deletion cleanup, sharing 50,000 relocation proposals and
    at most one second or 20% of the preceding pipeline time, whichever is less.
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
    if polish_star_policy != 'off':
        diag['polish_star_policy'] = polish_star_policy
    if final_cleanup == 'deletion':
        diag['final_cleanup_policy'] = final_cleanup
        cleanup_info = {
            'status': 'not_reached', 'reason': 'pipeline_not_reached',
            'pipeline_stage': 'parameters', 'pipeline_status': None,
            'contact_invoked': False, 'contact_returned': False,
            'contact_invalid_input': None, 'entry_validated': None,
            'before_qubits': None, 'after_qubits': None, 'qubits_saved': None,
            'wall': None, 'prerequisite_wall': None, 'entry_validation_wall': None,
            'module_call_wall': None, 'module_calls': 0, 'module_returned': False,
        }
        diag['final_cleanup'] = cleanup_info
    if vacancy_refinement == 'bounded':
        diag['vacancy_refinement_policy'] = vacancy_refinement
        vacancy_info = {'status': 'not_reached', 'reason': 'pipeline_not_reached',
                        'pipeline_status': None, 'wall': None, 'calls': [],
                        'before_qubits': None, 'after_qubits': None,
                        'qubits_saved': None, 'query_calls': 0, 'accepted': 0}
        diag['vacancy_refinement'] = vacancy_info

    def result(embedding, status, **extra):
        elapsed = time.perf_counter() - started
        if deadline is not None and time.perf_counter() > deadline:
            diag["deadline_overrun"] = max(0.0, elapsed - timeout)
            status = "TIMEOUT"
        if final_cleanup == 'deletion':
            cleanup_info['pipeline_status'] = status
            if cleanup_info['status'] == 'not_reached':
                cleanup_info['status'] = 'skipped'
        if vacancy_refinement == 'bounded':
            vacancy_info['pipeline_status'] = status
            if vacancy_info['status'] == 'not_reached':
                vacancy_info['status'] = 'skipped'
        return {"embedding": embedding, "success": status == "SUCCESS",
                "status": status, "time": elapsed, "diag": diag, **extra}

    if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
        return result({}, "ERROR", error="timeout must be finite and positive, or None")
    if final_cleanup not in ('off', 'deletion'):
        return result({}, 'ERROR', error='unknown final cleanup policy')
    if vacancy_refinement not in ('off', 'bounded'):
        return result({}, 'ERROR', error='unknown vacancy refinement policy')
    if vacancy_refinement == 'bounded' and final_cleanup != 'deletion':
        return result({}, 'ERROR', error='bounded vacancy refinement requires final deletion cleanup')
    if final_cleanup == 'deletion':
        if (polish_objective != 'qubits_contacts' or polish_tree_policy != 'greedy'
                or polish_singleton_policy != 'legacy' or polish_star_policy != 'off'):
            return result({}, 'ERROR', error='final deletion requires greedy contact scoring, legacy singletons and stars off')
        checking = time.perf_counter()
        prerequisite_error = None
        try:
            for graph in (source_graph, target_graph):
                if graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph):
                    prerequisite_error = 'final deletion requires simple undirected loopless graphs'
                    break
            if prerequisite_error is None and any(type(q) is not int for q in target_graph):
                prerequisite_error = 'final deletion requires ordinary integer target labels'
        finally:
            cleanup_info['prerequisite_wall'] = time.perf_counter() - checking
        if prerequisite_error:
            return result({}, 'ERROR', error=prerequisite_error)
    if construction not in ("search", "packed"):
        return result({}, "ERROR", error="unknown construction")
    if initialization not in ('random', 'spectral'):
        return result({}, 'ERROR', error='unknown initialization')
    if initialization == 'spectral' and construction != 'search':
        return result({}, 'ERROR', error='spectral initialization requires search construction')
    if polish_singleton_policy not in ('legacy', 'direct'):
        return result({}, 'ERROR', error='unknown singleton policy')
    if polish_star_policy not in ('off', 'matching', 'connected'):
        return result({}, 'ERROR', error='unknown star policy')
    if polish_objective == 'qubits_endpoint_support':
        if (polish_tree_policy != 'greedy' or polish_singleton_policy != 'legacy'
                or polish_star_policy != 'off'):
            return result({}, 'ERROR', error='endpoint support requires greedy trees, legacy singletons and stars off')
        for graph in (source_graph, target_graph):
            if graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph):
                return result({}, 'ERROR', error='endpoint support requires simple undirected loopless graphs')
    if polish_star_policy != 'off' and polish_singleton_policy != 'legacy':
        return result({}, 'ERROR', error=f'{polish_star_policy} star and direct singleton policies are mutually exclusive')
    if polish_singleton_policy == 'direct' and (
            target_graph.is_directed() or target_graph.is_multigraph()
            or nx.number_of_selfloops(target_graph)):
        return result({}, 'ERROR', error='direct singleton target must be simple and undirected')
    if polish_star_policy != 'off' and (
            target_graph.is_directed() or target_graph.is_multigraph()
            or nx.number_of_selfloops(target_graph)):
        return result({}, 'ERROR', error=f'{polish_star_policy} star target must be simple and undirected')
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
        if final_cleanup == 'deletion':
            skipping = time.perf_counter()
            cleanup_info.update(status='skipped', reason='empty_source',
                                before_qubits=0, after_qubits=0, qubits_saved=0)
            cleanup_info['wall'] = time.perf_counter() - skipping
        if vacancy_refinement == 'bounded':
            vacancy_info.update(status='skipped', reason='empty_source',
                                before_qubits=0, after_qubits=0, qubits_saved=0)
        return result({}, "SUCCESS")

    # Existing geometric primitives require integer source labels. Keep an explicit
    # inverse map so mixed/tuple labels and isolated vertices survive the adapter.
    labels = list(source_graph)
    mapping = {v: i for i, v in enumerate(labels)}
    source = nx.relabel_nodes(source_graph, mapping, copy=True)
    src_adj = {v: sorted(source[v]) for v in source}
    adjacency = build_adjacency(target_graph)
    try:
        if final_cleanup == 'deletion':
            cleanup_info['pipeline_stage'] = 'layout'
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
        if final_cleanup == 'deletion':
            cleanup_info['pipeline_stage'] = 'conversion'
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
        if final_cleanup == 'deletion':
            cleanup_info['pipeline_stage'] = 'initial_pruning'
        chains = spur_prune(chains, src_adj, adjacency, deadline=deadline)
        diag["pruned_qubits"] = sum(map(len, chains.values()))
        if polish_passes and (deadline is None or time.perf_counter() < deadline):
            from ember_qc.algorithms.factored.contact_repair import contact_polish
            singleton_options = ({'singleton_policy': polish_singleton_policy}
                                 if polish_singleton_policy != 'legacy' else {})
            star_options = ({'star_policy': polish_star_policy}
                            if polish_star_policy != 'off' else {})
            if final_cleanup == 'deletion':
                cleanup_info['pipeline_stage'] = 'contact_refinement'
                cleanup_info['contact_invoked'] = True
            chains, polish_info = contact_polish(
                chains, source, target_graph, deadline=deadline,
                max_passes=polish_passes, beam_width=beam_width, max_groups=max_groups,
                group_sizes=polish_group_sizes, max_expansions=polish_expansions,
                boundary_sites=polish_boundary_sites, group_policy=polish_group_policy,
                objective=polish_objective, tree_policy=polish_tree_policy,
                **singleton_options, **star_options)
            diag["contact_repair"] = polish_info
            if final_cleanup == 'deletion':
                cleanup_info['contact_returned'] = True
                cleanup_info['contact_invalid_input'] = bool(polish_info.get('invalid_input'))
        if final_cleanup == 'deletion':
            cleanup_info['pipeline_stage'] = 'final_cleanup'
            chains, cleanup_error = _final_deletion_cleanup(
                chains, source, target_graph, src_adj, adjacency,
                deadline=deadline, polish_passes=polish_passes, info=cleanup_info)
            if cleanup_error:
                return result({}, cleanup_error)
            cleanup_info['pipeline_stage'] = 'final_validation'
        if vacancy_refinement == 'bounded':
            chains, vacancy_error = _bounded_vacancy_refinement(
                chains, source, target_graph, src_adj, adjacency,
                started=started, deadline=deadline, cleanup_info=cleanup_info, info=vacancy_info)
            if vacancy_error:
                return result({}, vacancy_error, error=vacancy_info.get('error', vacancy_info['reason']),
                              partial_embedding={labels[v]: list(c) for v, c in chains.items()})
        embedding = {labels[v]: list(c) for v, c in chains.items()}
        if not is_valid_embedding(embedding, source_graph, target_graph):
            return result({}, "INVALID_OUTPUT")
        return result(embedding, "SUCCESS")
    except Exception as exc:
        return result({}, "ERROR", error=f"{type(exc).__name__}: {exc}")
