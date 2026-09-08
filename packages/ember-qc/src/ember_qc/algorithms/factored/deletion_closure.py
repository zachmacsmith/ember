"""Experimental deletion-only closure, preserving legacy global sweep order.

This module does not construct an embedding. The caller supplies a valid minor
on stable simple undirected adjacency maps. No native integration is performed.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import math
import time


class _Expired(Exception):
    def __init__(self, stage):
        super().__init__(stage)
        self.stage = stage


class _Meter:
    def __init__(self, deadline):
        self.deadline = deadline
        self.started = time.perf_counter()
        self.phase_started = self.started
        self.phase_name = 'copy'
        self.work = Counter()
        self.phase_wall = Counter()

    def checkpoint(self, stage):
        if self.deadline is not None:
            self.work['deadline_checks'] += 1
            if time.perf_counter() >= self.deadline:
                raise _Expired(stage)

    def charge(self, counter, stage):
        self.checkpoint(stage)
        self.work[counter] += 1

    def phase(self, name):
        now = time.perf_counter()
        self.phase_wall[self.phase_name] += now - self.phase_started
        self.phase_name, self.phase_started = name, now

    def finish(self):
        now = time.perf_counter()
        self.phase_wall[self.phase_name] += now - self.phase_started
        return {'wall': now - self.started, 'phase_wall': dict(self.phase_wall),
                'work': dict(self.work),
                'deadline_overrun': max(0., now-self.deadline) if self.deadline is not None else 0.}


def _connected(members, adj, meter, prefix, stage):
    if not members:
        return False
    # The set and start choice affect traversal work, never acceptance order.
    start = next(iter(members))
    reached, pending = {start}, [start]
    while pending:
        meter.charge(prefix + '_vertices', stage)
        q = pending.pop()
        for p in adj[q]:
            meter.charge(prefix + '_adjacency_entries', stage)
            if p in members and p not in reached:
                reached.add(p)
                pending.append(p)
    return len(reached) == len(members)


def _covers(remainder, neighbors, chain_sets, adj, meter, prefix, stage):
    for v in neighbors:
        meter.charge(prefix + '_logical_neighbors', stage)
        found = False
        for q in remainder:
            meter.charge(prefix + '_qubits', stage)
            for p in adj[q]:
                meter.charge(prefix + '_adjacency_entries', stage)
                if p in chain_sets[v]:
                    found = True
                    break
            if found:
                break
        if not found:
            return False
    return True


def deletion_closure(chains, src_adj, adj, *, deadline=None):
    """Return ``(embedding, info)`` after deterministic safe single deletions.

    Source/target labels must be Python integers, with arbitrary source keys;
    chains must be nonempty lists. Adjacency maps must remain stable, simple,
    undirected and loopless. The supplied entry is required to be a valid minor.
    Initial checks certify the occupied portion and all source contacts, not
    every unused target edge. Detected invalid inputs raise ``ValueError``.

    ``deadline`` is an absolute ``time.perf_counter()`` timestamp. Expiry before
    a complete private copy returns the unchanged input mapping (possibly an
    alias); otherwise the complete private state is returned. No partial copy
    or uncertified deletion is returned. ``input_validated=False`` on an early
    interruption is not a validity claim about an arbitrary supplied input.

    Nonbinding runs preserve ``spur_prune``'s sorted-chain/sorted-site accepted
    deletion sequence. Only chains changed by their own preceding completed
    sweep are revisited. A complete closure is not a minimum-qubit embedding.
    Container primitives and sorting are cooperative interruption boundaries.
    """
    if deadline is not None and (type(deadline) not in (int, float)
                                 or not math.isfinite(deadline)):
        raise ValueError('deadline must be a finite absolute timestamp or None')
    if not all(isinstance(value, Mapping) for value in (chains, src_adj, adj)):
        raise ValueError('chains and adjacency arguments must be mappings')
    meter = _Meter(deadline)
    info = {'private_copy_complete': False, 'input_validated': False,
            'closure_complete': False, 'stopped_reason': None, 'stopped_stage': None,
            'rounds_started': 0, 'rounds_completed': 0, 'chain_sweeps_started': 0,
            'chain_sweeps_completed': 0, 'attempted_deletions': 0,
            'accepted_deletions': 0, 'accepted_sequence': [],
            'returned_input_alias': True}
    result = chains
    try:
        meter.checkpoint('copy')
        copied, chain_sets, occupied = {}, {}, set()
        for v, chain in chains.items():
            meter.charge('copy_chains', 'copy')
            if type(v) is not int or type(chain) is not list or not chain:
                raise ValueError('integer source labels and nonempty list chains required')
            row, members = [], set()
            for q in chain:
                meter.charge('copy_qubits', 'copy')
                if type(q) is not int or q not in adj or q in occupied:
                    raise ValueError('unknown, noninteger or multiply owned qubit')
                row.append(q)
                members.add(q)
                occupied.add(q)
            copied[v], chain_sets[v] = row, members
        meter.checkpoint('copy_complete')
        result = copied
        info['private_copy_complete'] = True
        info['returned_input_alias'] = False
        meter.phase('setup')
        source = {}
        for v, neighbors in src_adj.items():
            meter.charge('setup_source_vertices', 'source_setup')
            if type(v) is not int or v not in copied:
                raise ValueError('source coverage or integer label mismatch')
            seen = set()
            for u in neighbors:
                meter.charge('setup_source_adjacency_entries', 'source_setup')
                if type(u) is not int or u == v or u not in copied or u in seen:
                    raise ValueError('source must be simple, loopless and fully placed')
                seen.add(u)
            source[v] = seen
        if len(source) != len(copied):
            raise ValueError('source coverage mismatch')
        for v, neighbors in source.items():
            for u in neighbors:
                meter.charge('setup_source_symmetry_tests', 'source_setup')
                if v not in source[u]:
                    raise ValueError('source must be undirected')
        meter.checkpoint('source_order')
        ordered = sorted(copied)
        neighbors = {}
        for v in ordered:
            meter.charge('setup_sorted_neighbor_lists', 'source_order')
            neighbors[v] = sorted(source[v])
        meter.checkpoint('source_order')
        meter.phase('initial_validation')
        for v in ordered:
            meter.charge('initial_chains', 'initial_validation')
            if not _connected(chain_sets[v], adj, meter, 'initial_connectivity', 'initial_connectivity'):
                raise ValueError('entry contains a disconnected chain')
            if not _covers(chain_sets[v], neighbors[v], chain_sets, adj, meter,
                           'initial_contacts', 'initial_contacts'):
                raise ValueError('entry omits a logical contact')
        meter.checkpoint('initial_validation_complete')
        info['input_validated'] = True
        meter.phase('search')
        active = ordered
        while active:
            meter.checkpoint('round_start')
            info['rounds_started'] += 1
            round_number = info['rounds_started']
            next_active = []
            meter.work['unchanged_chain_sweeps_skipped'] += len(ordered)-len(active)
            for v in active:
                meter.checkpoint('chain_start')
                info['chain_sweeps_started'] += 1
                changed = False
                if len(result[v]) > 1:
                    meter.checkpoint('site_order')
                    sites = sorted(result[v])
                    meter.work['sorted_site_entries'] += len(sites)
                    meter.checkpoint('site_order')
                    for q in sites:
                        if len(result[v]) <= 1:
                            break
                        meter.checkpoint('candidate')
                        info['attempted_deletions'] += 1
                        remainder = set()
                        for p in result[v]:
                            meter.charge('remainder_qubits', 'remainder')
                            if p != q:
                                remainder.add(p)
                        if not _connected(remainder, adj, meter, 'deletion_connectivity', 'connectivity'):
                            meter.work['disconnected_rejections'] += 1
                            continue
                        if not _covers(remainder, neighbors[v], chain_sets, adj, meter,
                                       'deletion_contacts', 'contacts'):
                            meter.work['contact_rejections'] += 1
                            continue
                        replacement = []
                        for p in result[v]:
                            meter.charge('replacement_qubits', 'replacement')
                            if p != q:
                                replacement.append(p)
                        meter.checkpoint('commit_record')
                        record = {'round':round_number, 'source_vertex':v, 'qubit':q,
                                  'old_chain_size':len(result[v]), 'new_chain_size':len(replacement)}
                        meter.checkpoint('commit')
                        # All expensive preparation is complete. No cancellable
                        # checkpoint separates these consistent state updates.
                        result[v] = replacement
                        chain_sets[v] = remainder
                        info['accepted_sequence'].append(record)
                        info['accepted_deletions'] += 1
                        changed = True
                info['chain_sweeps_completed'] += 1
                if changed:
                    next_active.append(v)
            meter.checkpoint('round_end')
            info['rounds_completed'] += 1
            active = next_active
        meter.checkpoint('complete')
        info['closure_complete'] = True
        info['stopped_reason'] = 'closed'
    except _Expired as stopped:
        info['stopped_reason'] = 'deadline'
        info['stopped_stage'] = stopped.stage
    info.update(meter.finish())
    return result, info
