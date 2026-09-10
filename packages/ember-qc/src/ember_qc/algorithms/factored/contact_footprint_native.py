"""Isolated native footprint variant; no alternate complete constructor."""
import math
import time
import networkx as nx
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
from ember_qc.algorithms.factored import contact_footprint_layout as layout
from ember_qc.algorithms.factored.contact_footprint_conversion import wire_seeds
from ember_qc.algorithms.factored.field import TileGrid, complete_seeds
from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.algorithms.factored.native import _final_deletion_cleanup, _bounded_vacancy_refinement

def footprint_native_embed(source_graph, target_graph, *, timeout=60.0, seed=0,
                 construction="search", order_strategy="random", packing_passes=2,
                 max_asks=10000, sched_seed=None, polish_passes=0,
                 beam_width=4, max_groups=64, polish_group_sizes=(2, 3, 4),
                 polish_expansions=500000, polish_boundary_sites=0,
                 polish_group_policy="legacy", polish_objective='qubits',
                 polish_tree_policy='greedy', initialization='random',
                 polish_singleton_policy='legacy', polish_star_policy='off',
                 final_cleanup='off', vacancy_refinement='off',
                 inactive_booking=False, deadline=None):
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
    ``'cyclic'`` retains these limits while continuing after the last accepted
    deletion seed in a fixed entry-owner priority and current-site order.
    """
    started = time.perf_counter()
    if type(inactive_booking) is not bool:
        raise ValueError('inactive_booking must be a constant boolean')
    if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('finite absolute deadline required')
    relative_end = started + timeout if timeout is not None and timeout > 0 else None
    deadline = min(deadline, relative_end) if deadline is not None and relative_end is not None else relative_end
    remaining = None if deadline is None else max(0., deadline-started)
    reserve = 0. if remaining is None else min(10., remaining/2.)
    geometry_deadline = None if deadline is None else deadline-reserve
    diag = {"construction": construction, "order_strategy": order_strategy,
            "polish_passes": polish_passes, "beam_width": beam_width,
            "polish_group_sizes": list(polish_group_sizes),
            "polish_expansions": polish_expansions,
            "polish_boundary_sites": polish_boundary_sites,
            "polish_group_policy": polish_group_policy,
            'polish_objective': polish_objective,
            'polish_tree_policy': polish_tree_policy,
            'initialization': initialization,
            'footprint_policy': 'contact_supported', 'inactive_booking': inactive_booking,
            'deadline': deadline, 'native_started': started,
            'allocation': dict(exposure='controlled_1000_asks_not_saturation_or_default',
                               max_asks=max_asks, reserve_seconds=reserve,
                               remaining_at_entry=remaining, geometry_deadline=geometry_deadline,
                               geometry_stop=None, remaining_after_layout=None,
                               layout_returned_at=None, downstream_wall=None,
                               reserve_overrun=None, original_deadline_overrun=None),
            'conversion_wall': None, 'completion_wall': None,
            'initial_validation_wall': None, 'initial_native_valid_at': None,
            'first_valid_scope': 'filled core only; full source remains subject to lifting'}
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
    if vacancy_refinement in ('bounded', 'cyclic'):
        diag['vacancy_refinement_policy'] = vacancy_refinement
        vacancy_info = {'status': 'not_reached', 'reason': 'pipeline_not_reached',
                        'pipeline_status': None, 'wall': None, 'calls': [],
                        'before_qubits': None, 'after_qubits': None,
                        'qubits_saved': None, 'query_calls': 0, 'accepted': 0}
        diag['vacancy_refinement'] = vacancy_info

    def result(embedding, status, **extra):
        elapsed = time.perf_counter() - started
        if deadline is not None and time.perf_counter() > deadline:
            diag["deadline_overrun"] = max(0.0, time.perf_counter() - deadline)
            status = "TIMEOUT"
        layout_returned = diag['allocation']['layout_returned_at']
        if layout_returned is not None:
            downstream = time.perf_counter()-layout_returned
            diag['allocation'].update(downstream_wall=downstream,
                reserve_overrun=max(0., downstream-reserve),
                original_deadline_overrun=max(0., time.perf_counter()-deadline) if deadline is not None else 0.)
        if final_cleanup == 'deletion':
            cleanup_info['pipeline_status'] = status
            if cleanup_info['status'] == 'not_reached':
                cleanup_info['status'] = 'skipped'
        if vacancy_refinement in ('bounded', 'cyclic'):
            vacancy_info['pipeline_status'] = status
            if vacancy_info['status'] == 'not_reached':
                vacancy_info['status'] = 'skipped'
        return {"embedding": embedding, "success": status == "SUCCESS",
                "status": status, "time": elapsed, "diag": diag, **extra}

    if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
        return result({}, "ERROR", error="timeout must be finite and positive, or None")
    if final_cleanup not in ('off', 'deletion'):
        return result({}, 'ERROR', error='unknown final cleanup policy')
    if vacancy_refinement not in ('off', 'bounded', 'cyclic'):
        return result({}, 'ERROR', error='unknown vacancy refinement policy')
    if vacancy_refinement in ('bounded', 'cyclic') and final_cleanup != 'deletion':
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
    if construction != "search":
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
        if vacancy_refinement in ('bounded', 'cyclic'):
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
                    src_adj, seed=seed, deadline=geometry_deadline)
                diag['initialization_info'] = initialization_info
                if initial_orders is None:
                    diag['allocation']['geometry_stop'] = 'initialization_'+initialization_info['status']
                    diag['layout_wall'] = time.perf_counter() - layout_started
                    status = ('TIMEOUT' if initialization_info['status'] == 'deadline'
                              else 'INITIALIZATION_FAILED')
                    return result({}, status)
                initialization_args['initial_orders'] = initial_orders
                if deadline is not None and time.perf_counter() >= deadline:
                    diag['layout_wall'] = time.perf_counter() - layout_started
                    return result({}, 'TIMEOUT')
            points, state, layout_info = layout.arrange(
                src_adj, grid, seed=seed, max_asks=max_asks, deadline=geometry_deadline,
                snap=True, sched_seed=seed if sched_seed is None else sched_seed,
                inactive_booking=inactive_booking, **initialization_args)
        diag["layout_wall"] = time.perf_counter() - layout_started
        diag["layout"] = layout_info
        diag['allocation'].update(geometry_stop=layout_info.get('stopped_by'),
                                  layout_returned_at=time.perf_counter(),
                                  remaining_after_layout=None if deadline is None else deadline-time.perf_counter())
        if deadline is not None and time.perf_counter() >= deadline:
            return result({}, "TIMEOUT")
        if final_cleanup == 'deletion':
            cleanup_info['pipeline_stage'] = 'conversion'
        phase_started = time.perf_counter()
        try:
            chains, conversion = wire_seeds(grid, points, state)
        finally:
            diag['conversion_wall'] = time.perf_counter()-phase_started
        diag['conversion'] = conversion
        if deadline is not None and time.perf_counter() >= deadline:
            return result({}, 'TIMEOUT', partial_embedding={labels[v]:list(c) for v,c in chains.items()})
        phase_started = time.perf_counter()
        try:
            chains, completion = complete_seeds(grid, chains, src_adj, adjacency)
        finally:
            diag['completion_wall'] = time.perf_counter()-phase_started
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
        if deadline is not None and time.perf_counter() >= deadline:
            return result({}, 'TIMEOUT', partial_embedding={labels[v]:list(c) for v,c in chains.items()})
        phase_started = time.perf_counter()
        try:
            initial_valid = is_valid_embedding(chains, source, target_graph)
        finally:
            diag['initial_validation_wall'] = time.perf_counter()-phase_started
        if initial_valid:
            diag['initial_native_valid_at'] = time.perf_counter()-started
        if not initial_valid:
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
        if vacancy_refinement in ('bounded', 'cyclic'):
            chains, vacancy_error = _bounded_vacancy_refinement(
                chains, source, target_graph, src_adj, adjacency,
                started=started, deadline=deadline, cleanup_info=cleanup_info, info=vacancy_info,
                policy=vacancy_refinement)
            if vacancy_error:
                return result({}, vacancy_error, error=vacancy_info.get('error', vacancy_info['reason']),
                              partial_embedding={labels[v]: list(c) for v, c in chains.items()})
        embedding = {labels[v]: list(c) for v, c in chains.items()}
        if not is_valid_embedding(embedding, source_graph, target_graph):
            return result({}, "INVALID_OUTPUT")
        return result(embedding, "SUCCESS")
    except layout.LayoutDeadline as exc:
        diag['layout_wall'] = time.perf_counter()-layout_started
        diag['layout'] = exc.info
        diag['allocation']['geometry_stop'] = exc.info.get('stopped_by')
        diag['allocation']['remaining_after_layout'] = None if deadline is None else deadline-time.perf_counter()
        return result({}, 'TIMEOUT', error=str(exc))
    except Exception as exc:
        return result({}, "ERROR", error=f"{type(exc).__name__}: {exc}")

