"""Shared-entry ordinary proposal diagnostic; no constructor or corpus loader.

The caller freezes groups and original graphs. Group generation is external but
belongs inside its overall arm deadline. Both proposal arms can use final_gate.
Only the hash-bound contact module is loaded here; its package is never imported.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
import time
from types import MappingProxyType
import uuid


CONTACT_SHA256 = 'c6f9a5555b010d5e877b568c1ee760e72d170f1f7e0c186179de16b53630da85'
OPTIONS = MappingProxyType(dict(beam_width=1, alternatives=3, halo=2,
                               max_region=512, max_orders=2, boundary_sites=16,
                               objective='qubits_contacts', tree_policy='greedy'))
GROUP_EXPANSIONS = 50000


def load_contact_repair(path):
    """Load the reviewed standalone module without importing ember_qc.__init__."""
    path = Path(path).absolute()
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONTACT_SHA256:
        raise ValueError('Contact source differs from the reviewed ordinary proposer')
    name = '_codex_ordinary_contact_' + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses needs the module during definition
    try:
        # Compile precisely the bytes checked above, without a pycache lookup.
        exec(compile(raw, str(path), 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    module.diagnostic_source_sha256 = CONTACT_SHA256
    return module


class _Late(Exception):
    pass


def _deadline(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('deadline must be a finite absolute timestamp')


def _timely(deadline, clock):
    if clock() >= deadline:
        raise _Late()


def _graph_value(graph):
    """Exact structural and iteration-order snapshot, excluding attributes."""
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError('Graphs must be simple undirected graphs')
    rows = []
    for v in graph:
        if type(v) is not int or v in graph[v]:
            raise ValueError('Graph labels must be integers and loops absent')
        neighbors = tuple(graph[v])
        if any(type(u) is not int or u not in graph or v not in graph[u]
               for u in neighbors):
            raise ValueError('Malformed undirected adjacency')
        rows.append((v, neighbors))
    return tuple(rows), tuple(graph.edges())


def _context_value(ctx):
    return (tuple(ctx.nodes), tuple(ctx.rank.items()), tuple(ctx.adj.items()),
            tuple(ctx.src_adj.items()), tuple(ctx.edges), ctx.max_degree)


def _groups_value(groups):
    """Snapshot ordinary groups without consuming or cloning malformed iterators."""
    def label(v):
        return ('int', v) if type(v) is int else ('unsupported', type(v), id(v))
    return (type(groups), tuple((type(g), tuple(label(v) for v in g))
                               if type(g) in (list, tuple) else ('unsupported', type(g), id(g))
                               for g in groups))


def _entry_copy(embedding):
    if not isinstance(embedding, Mapping):
        raise ValueError('Entry must be a mapping')
    copied = {}
    for v, chain in embedding.items():
        if type(v) is not int or type(chain) is not list or not chain:
            raise ValueError('Entry needs integer keys and nonempty list chains')
        if any(type(q) is not int for q in chain):
            raise ValueError('Entry qubits must be integers')
        copied[v] = list(chain)
    return copied


def _result_evidence(result, entry):
    """Lossless relative mapping, with original key/list order, for normal output.

    Malformed objects retain a deepcopy for diagnostic use; the final gate never
    accepts them. This materialization consumes wall, not routing expansions.
    """
    if isinstance(result, Mapping):
        return dict(kind='entry_delta', key_order=list(result),
                    removed_keys=[v for v in entry if v not in result],
                    changed={v: deepcopy(c) for v, c in result.items()
                             if v not in entry or c != entry[v]})
    return dict(kind='malformed', value=deepcopy(result))


def _validated_private(candidate, source, target, deadline, clock):
    """Original-edge predicate shared by evaluator checks and the final gate."""
    source_value, target_value = _graph_value(source), _graph_value(target)
    _timely(deadline, clock)
    nodes = {v for v, _ in source_value[0]}
    target_adj = {q: set() for q, _ in target_value[0]}
    for q, p in target_value[1]:
        _timely(deadline, clock)
        target_adj[q].add(p)
        target_adj[p].add(q)
    if not isinstance(candidate, Mapping) or set(candidate) != nodes:
        raise ValueError('candidate source-key coverage')
    owners, private = {}, {}
    for v, chain in candidate.items():
        _timely(deadline, clock)
        if type(v) is not int or type(chain) is not list or not chain:
            raise ValueError('candidate key/chain type or emptiness')
        members = set()
        copied = []
        for q in chain:
            _timely(deadline, clock)
            if type(q) is not int or q not in target_adj or q in owners:
                raise ValueError('candidate target membership or overlapping ownership')
            owners[q] = v
            members.add(q)
            copied.append(q)
        reached, stack = {chain[0]}, [chain[0]]
        while stack:
            _timely(deadline, clock)
            for q in target_adj[stack.pop()]:
                _timely(deadline, clock)
                if q in members and q not in reached:
                    reached.add(q)
                    stack.append(q)
        if reached != members:
            raise ValueError('disconnected candidate chain')
        private[v] = copied
    contacts = set()
    for q, p in target_value[1]:
        _timely(deadline, clock)
        if q in owners and p in owners and owners[q] != owners[p]:
            contacts.add(frozenset((owners[q], owners[p])))
    for u, v in source_value[1]:
        _timely(deadline, clock)
        if frozenset((u, v)) not in contacts:
            raise ValueError('missing original source edge')
    return private, len(owners), nodes


def validate_embedding(embedding, source, target, *, deadline=None, clock=None):
    """Pure evaluator check: returns valid/reason/Q/ACL; no candidate search.

    Omit deadline only for the evaluator's explicitly untimed input checks.
    """
    if deadline is not None:
        _deadline(deadline)
    clock = clock or time.perf_counter
    limit = float('inf') if deadline is None else deadline
    try:
        _timely(limit, clock)
        private, q, nodes = _validated_private(embedding, source, target, limit, clock)
        _timely(limit, clock)
        return dict(valid=True, reason=None, qubits=q,
                    acl=q / len(nodes) if nodes else None,
                    max_chain=max(map(len, private.values()), default=0))
    except _Late:
        return dict(valid=False, reason='deadline', qubits=None, acl=None, max_chain=None)
    except (ValueError, TypeError, KeyError) as exc:
        return dict(valid=False, reason=str(exc), qubits=None, acl=None, max_chain=None)


def final_gate(candidate, entry, source, target, *, deadline,
               allowed_changed=None, expected_drop=None, clock=None):
    """Independent original-edge validity, strict Q, private output and deadline.

    Reusable by exchange: supply its final selected owners as allowed_changed and
    expected_drop=1. The caller retains raw proposal evidence even if this gate
    interrupts. Wall includes full graph scanning, validation and list copying.
    Validation derives adjacency from original target edges, never ctx.adj.
    """
    _deadline(deadline)
    if expected_drop is not None and (type(expected_drop) is not int or expected_drop < 1):
        raise ValueError('expected_drop must be a positive integer or None')
    clock = clock or time.perf_counter
    start = clock()
    info = dict(valid=False, strict_q=False, outside_unchanged=None,
                private_copy_complete=False, credited=False, reason=None,
                q_entry=None, q_candidate=None, qubits_saved=None)
    private = None
    try:
        _timely(deadline, clock)
        if set(entry) != set(source):
            raise ValueError('entry source-key coverage')
        info['q_entry'] = sum(len(c) for c in entry.values())
        private, q, nodes = _validated_private(candidate, source, target, deadline, clock)
        info['valid'] = True
        info['q_candidate'] = q
        info['qubits_saved'] = info['q_entry'] - q
        info['strict_q'] = info['qubits_saved'] > 0
        if not info['strict_q']:
            raise ValueError('candidate is not a strict-Q contraction')
        if expected_drop is not None and info['qubits_saved'] != expected_drop:
            raise ValueError('candidate has incorrect Q reduction')
        if allowed_changed is not None:
            allowed = set(allowed_changed)
            if not allowed <= nodes:
                raise ValueError('unknown allowed changed owner')
            info['outside_unchanged'] = all(private[v] == entry[v] for v in nodes - allowed)
            if not info['outside_unchanged']:
                raise ValueError('outside chain changed')
        info['private_copy_complete'] = True
        _timely(deadline, clock)
        info['credited'] = True
        info['reason'] = 'accepted'
    except _Late:
        private = None
        info['reason'] = 'deadline'
    except (ValueError, TypeError, KeyError) as exc:
        private = None
        info['reason'] = 'invalid_output'
        info['error'] = str(exc)
    ended = clock()
    info['wall'] = ended - start
    info['deadline_overrun'] = max(0.0, ended - deadline)
    if ended >= deadline:
        private = None
        info['credited'] = False
        info['reason'] = 'deadline'
    # Include result bookkeeping, not only the earlier validation endpoint.
    observed = clock()
    info.update(wall=observed-start, deadline_overrun=max(0.0, observed-deadline))
    if observed >= deadline:
        private = None
        info.update(credited=False, reason='deadline')
    return private, info


def ordinary_first_contraction(embedding, source, target, groups, *, deadline,
                               max_expansions, contact_module, clock=None,
                               cpu_clock=None):
    """First timely returned contraction from unchanged E, with shared setup.

    contact_module should come from load_contact_repair; explicit injection is
    available for focused tests and is visible through the source identity field.
    The caller must reject unbound modules in an actual diagnostic worker.
    No group generation, constructor, competitor, cache reuse or retry occurs.
    """
    _deadline(deadline)
    if type(max_expansions) is not int or max_expansions < 0:
        raise ValueError('max_expansions must be a nonnegative integer')
    if type(groups) not in (list, tuple):
        raise ValueError('groups must be an ordinary finite list or tuple')
    clock, cpu_clock = clock or time.perf_counter, cpu_clock or time.process_time
    started, cpu_started = clock(), cpu_clock()
    info = dict(schema='ordinary-first-contraction-v1', options=dict(OPTIONS),
                contact_source_sha256=getattr(contact_module, 'diagnostic_source_sha256', None),
                group_count=len(groups), groups=[], groups_called=0,
                uninspected_groups=len(groups), max_expansions=max_expansions,
                group_expansions=GROUP_EXPANSIONS, expansions=0,
                expansions_basis='known trustworthy returned-record prefix',
                routing_accounting_complete=True, unaccounted_group_indices=[],
                setup_completed=False, entry_validated=False, entry_q=None,
                inputs_unchanged=None, context_unchanged=None,
                returned_contraction=False, credited_contraction=False,
                returning_group_index=None, stopped_by=None, error=None,
                stage_wall=dict(setup=0., entry_validation=0., proposal_calls=0.,
                                final_gate=0.), final_gate=None)
    candidate = None
    entry = ctx = context_value = input_value = group_value = None
    try:
        _timely(deadline, clock)
        cr = contact_module
        cr._parameters(OPTIONS['beam_width'], OPTIONS['alternatives'], OPTIONS['halo'],
                       OPTIONS['max_region'], max_expansions, OPTIONS['max_orders'],
                       OPTIONS['boundary_sites'])
        if not groups:
            info['stopped_by'] = 'no_groups'
        else:
            setup_start = clock()
            try:
                input_value = (_graph_value(source), _graph_value(target))
                entry = _entry_copy(embedding)
                group_value = _groups_value(groups)
                ctx = cr._Context(source, target)
                context_value = _context_value(ctx)
            finally:
                info['stage_wall']['setup'] = clock() - setup_start
            info['setup_completed'] = True
            _timely(deadline, clock)
            validation_start = clock()
            try:
                valid = ctx.valid(entry)
            finally:
                info['stage_wall']['entry_validation'] = clock() - validation_start
            if not valid:
                raise ValueError('invalid entry embedding')
            info['entry_validated'] = True
            info['entry_q'] = sum(map(len, entry.values()))
            _timely(deadline, clock)
            for index in range(len(groups)):
                _timely(deadline, clock)
                remaining = max_expansions - info['expansions']
                if remaining <= 0:
                    info['stopped_by'] = 'work_limit'
                    break
                group = groups[index]
                record = dict(index=index, group=deepcopy(group), called=False,
                              raw=None, result=None, gate=None)
                info['groups'].append(record)
                if (type(group) not in (list, tuple) or not 1 <= len(group) <= 4
                        or any(type(v) is not int or v not in entry for v in group)
                        or len(set(group)) != len(group)):
                    raise ValueError('malformed reached group')
                allowance = min(GROUP_EXPANSIONS, remaining)
                call_start, call_cpu = clock(), cpu_clock()
                record.update(called=True, allowance=allowance)
                info['groups_called'] += 1
                try:
                    result, raw = cr._repair(entry, ctx, tuple(group), **OPTIONS,
                                             max_expansions=allowance, deadline=deadline)
                except Exception as exc:
                    record['call_error'] = type(exc).__name__ + ': ' + str(exc)
                    record['routing_accounting_complete'] = False
                    info['routing_accounting_complete'] = False
                    info['unaccounted_group_indices'].append(index)
                    raise
                finally:
                    returned, returned_cpu = clock(), cpu_clock()
                    record.update(call_wall=returned-call_start, call_cpu=returned_cpu-call_cpu,
                                  return_elapsed=returned-started, raw_return_timely=returned < deadline)
                    info['stage_wall']['proposal_calls'] += returned-call_start
                record['raw'] = deepcopy(raw)
                spent = raw.get('expansions') if isinstance(raw, dict) else None
                trustworthy_work = type(spent) is int and 0 <= spent <= allowance
                record['routing_accounting_complete'] = trustworthy_work
                if trustworthy_work:
                    info['expansions'] += spent
                else:
                    info['routing_accounting_complete'] = False
                    info['unaccounted_group_indices'].append(index)
                # Preserve raw evidence before raising any accounting/validity error.
                if isinstance(result, Mapping) and all(v in result for v in group):
                    record['result'] = dict(kind='selected_delta',
                                            changed={v: deepcopy(result[v]) for v in group},
                                            outside='unchanged by reviewed proposer contract; gate checks positive output')
                else:
                    record['result'] = _result_evidence(result, embedding)
                if not trustworthy_work:
                    raise RuntimeError('invalid ordinary routing-work record')
                if not isinstance(result, Mapping) or any(v not in result for v in group):
                    raise RuntimeError('ordinary proposer returned malformed selected coverage')
                if any(type(result[v]) is not list or not result[v]
                       or any(type(q) is not int for q in result[v]) for v in group):
                    record['result'] = _result_evidence(result, embedding)
                    raise RuntimeError('ordinary proposer returned malformed selected chains')
                # Outside chains are unchanged by the exact reviewed _repair body.
                # Avoid an added whole-incumbent scan on every nonpositive group.
                q = (info['entry_q'] - sum(len(embedding[v]) for v in group)
                     + sum(len(result[v]) for v in group))
                record['q_basis'] = 'entry plus selected-size delta; positive output receives whole-map gate'
                record['q_returned'] = q
                if q > info['entry_q']:
                    record['result'] = _result_evidence(result, embedding)
                    raise RuntimeError('ordinary proposer increased Q')
                if q < info['entry_q']:
                    record['result'] = _result_evidence(result, embedding)
                    info['returned_contraction'] = True
                    info['returning_group_index'] = index
                _timely(deadline, clock)
                if q < info['entry_q']:
                    gate_start = clock()
                    try:
                        candidate, gate = final_gate(result, embedding, source, target,
                                                     deadline=deadline, allowed_changed=group,
                                                     clock=clock)
                    finally:
                        info['stage_wall']['final_gate'] += clock() - gate_start
                    record['gate'] = info['final_gate'] = gate
                    info['credited_contraction'] = candidate is not None
                    info['stopped_by'] = ('candidate_returned' if candidate is not None else
                                          'deadline' if gate['reason'] == 'deadline' else 'invalid_output')
                    break
            if info['stopped_by'] is None:
                info['stopped_by'] = 'groups_exhausted'
    except _Late:
        candidate = None
        info['credited_contraction'] = False
        info['stopped_by'] = 'deadline'
    except ValueError as exc:
        candidate = None
        info.update(credited_contraction=False, stopped_by='invalid_input', error=str(exc))
    except Exception as exc:
        candidate = None
        info.update(credited_contraction=False, stopped_by='error',
                    error=type(exc).__name__ + ': ' + str(exc))
    # These immutable-value checks and result bookkeeping stay in observed wall.
    try:
        if input_value is not None:
            info['inputs_unchanged'] = (input_value == (_graph_value(source), _graph_value(target))
                                       and (entry is None or entry == embedding)
                                       and (group_value is None or _groups_value(groups) == group_value))
            info['context_unchanged'] = ctx is None or _context_value(ctx) == context_value
            if not info['inputs_unchanged'] or not info['context_unchanged']:
                candidate = None
                info.update(credited_contraction=False, stopped_by='error',
                            error='input/context mutation detected')
    except Exception as exc:
        candidate = None
        info.update(credited_contraction=False, stopped_by='error',
                    error='mutation check: ' + str(exc))
    info['uninspected_groups'] = info['group_count'] - len(info['groups'])
    info['expansions_exact'] = info['expansions'] if info['routing_accounting_complete'] else None
    ended, cpu_ended = clock(), cpu_clock()
    info.update(wall=ended-started, cpu=cpu_ended-cpu_started,
                deadline=deadline, deadline_overrun=max(0., ended-deadline))
    if ended >= deadline:
        candidate = None
        info['credited_contraction'] = False
        if info['stopped_by'] not in ('error', 'invalid_input', 'invalid_output'):
            info['stopped_by'] = 'deadline'
    info['stage_wall']['diagnostics_and_administration'] = (
        info['wall'] - sum(info['stage_wall'].values()))
    observed = clock()
    info.update(wall=observed-started, deadline_overrun=max(0., observed-deadline),
                deadline_exceeded=observed >= deadline)
    info['stage_wall']['diagnostics_and_administration'] += observed-ended
    if observed >= deadline:
        candidate = None
        info['credited_contraction'] = False
        if info['stopped_by'] not in ('error', 'invalid_input', 'invalid_output'):
            info['stopped_by'] = 'deadline'
    return candidate, info


# Stable short integration name; identical implementation and contract.
ordinary_batch = ordinary_first_contraction
