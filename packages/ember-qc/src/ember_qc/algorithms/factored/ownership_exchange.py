"""Experimental occupied-site exchange; this is not an embedding constructor.

One immutable valid entry, one live work allowance, and at most one Q-1
proposal. The caller supplies stable simple undirected loopless adjacency.
Only standard-library modules are imported. No pipeline integration is implied.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import math
import time


MAX_CHAINS = 8
MAX_SITES = 64
MAX_DEPTH = 8
MAX_CHILDREN = 4
MAX_ENTERED = 256
_ABSENT = object()


class _Stop(Exception):
    def __init__(self, reason, stage, timestamp=None):
        self.reason, self.stage, self.timestamp = reason, stage, timestamp


class _Invalid(Exception):
    pass


class _Internal(Exception):
    pass


class _SeedCap(Exception):
    pass


class _Meter:
    def __init__(self, budget, deadline):
        for name in ('limit', 'expansions'):
            value = getattr(budget, name, None)
            if type(value) is not int or value < 0:
                raise ValueError('budget limit/expansions must be nonnegative integers')
        if budget.expansions > budget.limit or not callable(getattr(budget, 'pop', None)):
            raise ValueError('malformed live budget')
        dates = []
        for value in (deadline, getattr(budget, 'deadline', None)):
            if value is not None:
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('deadlines must be finite absolute timestamps')
                dates.append(value)
        self.deadline = min(dates) if dates else None
        self.budget, self.initial = budget, budget.expansions
        self.work = Counter()
        self.started = self.mark = time.perf_counter()
        self.current = 'administration'
        self.walls = Counter()
        self.last_kind = None

    def timely(self):
        if self.deadline is not None:
            now = time.perf_counter()
            if now >= self.deadline:
                raise _Stop('deadline', self.current + ':' + str(self.last_kind), now)

    def spend(self, kind):
        self.last_kind = kind
        self.timely()
        before = self.budget.expansions
        granted = self.budget.pop()
        if not granted:
            if self.budget.expansions != before:
                raise ValueError('failed budget reservation consumed work')
            self.timely()
            raise _Stop('work', self.current + ':' + kind)
        if self.budget.expansions != before + 1:
            raise ValueError('successful budget reservation must consume one unit')
        self.work[kind] += 1

    def _phase(self, name):
        now = time.perf_counter()
        self.walls[self.current] += now - self.mark
        self.mark, self.current = now, name

    @contextmanager
    def phase(self, name):
        old = self.current
        self._phase(name)
        try:
            yield
        finally:
            self._phase(old)

    def finish(self):
        self._phase('administration')
        end = time.perf_counter()
        self.walls[self.current] += end - self.mark
        delta = self.budget.expansions - self.initial
        if delta != sum(self.work.values()):
            raise ValueError('live budget changed outside this query')
        return dict(work=dict(self.work), work_total=delta,
                    budget_start=self.initial, budget_end=self.budget.expansions,
                    stage_wall=dict(self.walls), wall=end-self.started,
                    deadline=self.deadline,
                    deadline_overrun=max(0., end-self.deadline)
                    if self.deadline is not None else 0.)


def _compare(a, b, meter, kind='ordering_comparisons'):
    """Lexicographic comparison with each examined integer token charged."""
    for i in range(min(len(a), len(b))):
        meter.spend(kind)
        if a[i] != b[i]:
            return -1 if a[i] < b[i] else 1
    meter.spend(kind)
    return (len(a) > len(b)) - (len(a) < len(b))


def _ordered(values, meter, pairs=False):
    """Bottom-up merge sort: charge reads, comparisons and every item write."""
    data = []
    for value in values:
        meter.spend('ordering_reads')
        meter.spend('ordering_writes')
        data.append(value)
    width = 1
    while width < len(data):
        out = []
        for lo in range(0, len(data), 2*width):
            middle, end = min(lo+width, len(data)), min(lo+2*width, len(data))
            i, j = lo, middle
            while i < middle or j < end:
                left = j == end
                if i < middle and j < end:
                    if pairs:
                        left = _compare(data[i], data[j], meter) <= 0
                    else:
                        meter.spend('ordering_comparisons')
                        left = data[i] <= data[j]
                elif i == middle:
                    left = False
                meter.spend('ordering_writes')
                if left:
                    out.append(data[i]); i += 1
                else:
                    out.append(data[j]); j += 1
        data = out
        width *= 2
    return data


def _copy_sites(values, meter, kind):
    result = set()
    for q in values:
        meter.spend(kind)
        result.add(q)
    return result


def _connected(members, target, meter):
    if not members:
        return False
    meter.spend('connectivity_queue')
    start = next(iter(members))
    reached, pending = {start}, [start]
    while pending:
        meter.spend('connectivity_queue')
        q = pending.pop()
        for p in target[q]:
            meter.spend('connectivity_adjacency')
            if p in members and p not in reached:
                meter.spend('connectivity_queue')
                reached.add(p)
                pending.append(p)
    return len(reached) == len(members)


@dataclass
class _State:
    deleted: int
    chains: dict
    patch: set
    owners: dict
    missing: list
    depth: int
    trace: list
    rank: tuple = ()


class _Visited:
    """Hash buckets never substitute a digest for exact token equality."""
    def __init__(self, meter):
        self.meter, self.buckets = meter, {}

    def admit(self, signature, depth):
        h = 0
        for token in signature:
            self.meter.spend('signature_hash_tokens')
            h = ((h*1000003) ^ hash(token)) & ((1 << 64)-1)
        bucket = self.buckets.get(h)
        if bucket is not None:
            for record in bucket:
                if _compare(signature, record[0], self.meter,
                            'signature_equality_tokens') == 0:
                    if depth >= record[1]:
                        return False, False
                    self.meter.spend('signature_records')
                    record[1] = depth
                    return True, True
        self.meter.spend('signature_records')
        if bucket is None:
            bucket = []
            self.buckets[h] = bucket
        bucket.append([signature, depth])
        return True, False


class _Context:
    """One immutable entry; private child states never modify this ownership."""
    def __init__(self, source, target, meter, info):
        self.original_source, self.target = source, target
        self.m, self.info = meter, info
        self.source, self.entry, self.owner = {}, {}, {}
        self.vertices, self.q_entry = [], 0

    def setup(self, embedding):
        m = self.m
        if not all(isinstance(x, Mapping)
                   for x in (embedding, self.original_source, self.target)):
            raise _Invalid('embedding and adjacency must be mappings')
        self.info['setup_started'] += 1
        for v, neighbors in self.original_source.items():
            m.spend('setup_source_records')
            if type(v) is not int or isinstance(neighbors, Iterator):
                raise _Invalid('source labels must be integers; adjacency reiterable')
            row = set()
            for u in neighbors:
                m.spend('setup_source_adjacency')
                if type(u) is not int or u == v or u in row:
                    raise _Invalid('malformed source adjacency')
                row.add(u)
            self.source[v] = row
        for v, neighbors in self.source.items():
            m.spend('setup_source_records')
            for u in neighbors:
                m.spend('setup_source_symmetry')
                if u not in self.source or v not in self.source[u]:
                    raise _Invalid('source must be undirected with exact key coverage')
        for v, chain in embedding.items():
            m.spend('setup_chain_records')
            if type(v) is not int or v not in self.source or type(chain) is not list or not chain:
                raise _Invalid('source keys and nonempty list chains required')
            row = []
            for q in chain:
                m.spend('setup_qubit_copies')
                if type(q) is not int or q not in self.target or q in self.owner:
                    raise _Invalid('unknown, noninteger or multiply owned target site')
                row.append(q)
                self.owner[q] = v
                self.q_entry += 1
            self.entry[v] = row
        if len(self.entry) != len(self.source):
            raise _Invalid('source coverage mismatch')
        self.info['private_copy_complete'] = True
        # Check touched target rows, without scanning the unused target graph.
        for q in self.owner:
            m.spend('setup_target_records')
            row = self.target[q]
            if isinstance(row, Iterator):
                raise _Invalid('target adjacency must be reiterable')
            seen = set()
            for p in row:
                m.spend('setup_target_adjacency')
                if type(p) is not int or p == q or p not in self.target or p in seen:
                    raise _Invalid('malformed occupied target adjacency')
                seen.add(p)
        self.vertices = _ordered(self.entry, m)
        self.validate(self.entry)
        self.info['entry_validated'] = True
        self.info['setup_completed'] = 1
        self.info['q_before'] = self.q_entry

    def validate(self, embedding):
        """Whole-minor oracle, independent of incremental deficits/patch owners."""
        m, owners, total = self.m, {}, 0
        if len(embedding) != len(self.source):
            raise _Invalid('certificate source coverage mismatch')
        for v, chain in embedding.items():
            m.spend('validation_chain_records')
            if type(v) is not int or v not in self.source or type(chain) is not list or not chain:
                raise _Invalid('certificate source key or chain type')
            members = set()
            for q in chain:
                m.spend('validation_membership')
                if type(q) is not int or q not in self.target or q in owners:
                    raise _Invalid('certificate occupancy violation')
                owners[q] = v
                members.add(q)
                total += 1
            if not _connected(members, self.target, m):
                raise _Invalid('certificate disconnected chain')
        represented = set()
        for q, v in owners.items():
            m.spend('validation_owned_sites')
            for p in self.target[q]:
                m.spend('validation_target_adjacency')
                u = owners.get(p, _ABSENT)
                if u is not _ABSENT and u != v:
                    m.spend('validation_contact_updates')
                    represented.add((min(u, v), max(u, v)))
        for v, neighbors in self.source.items():
            m.spend('validation_source_records')
            for u in neighbors:
                m.spend('validation_source_edges')
                if (min(u, v), max(u, v)) not in represented:
                    raise _Invalid('certificate missing source contact')
        return owners, total

    def owners_for(self, chains):
        owners = {}
        for v, chain in chains.items():
            self.m.spend('patch_chain_records')
            for q in chain:
                self.m.spend('patch_owner_records')
                if q in owners:
                    raise _Internal('private patch multiply owned')
                owners[q] = v
        return owners

    def owner_at(self, state, q):
        if q == state.deleted:
            return _ABSENT
        return state.owners.get(q, self.owner.get(q, _ABSENT))

    def missing(self, state):
        needed, represented = set(), set()
        for v, chain in state.chains.items():
            self.m.spend('contact_chain_records')
            for u in self.source[v]:
                self.m.spend('contact_source_edges')
                needed.add((min(u, v), max(u, v)))
            for q in chain:
                self.m.spend('contact_qubits')
                for p in self.target[q]:
                    self.m.spend('contact_target_adjacency')
                    u = self.owner_at(state, p)
                    if u is not _ABSENT and u in self.source[v]:
                        self.m.spend('contact_updates')
                        represented.add((min(u, v), max(u, v)))
        absent = []
        for edge in needed:
            self.m.spend('contact_obligation_checks')
            if edge not in represented:
                self.m.spend('contact_updates')
                absent.append(edge)
        return _ordered(absent, self.m, pairs=True)

    def signature(self, state):
        result = []
        selected = _ordered(state.chains, self.m)
        self.m.spend('signature_tokens')
        result.append(len(selected))
        for v in selected:
            self.m.spend('signature_tokens'); result.append(v)
        self.m.spend('signature_tokens'); result.append(len(state.owners))
        for q in _ordered(state.owners, self.m):
            self.m.spend('signature_tokens'); result.append(q)
            self.m.spend('signature_tokens'); result.append(state.owners[q])
        return result

    def _record(self, rows, value):
        self.m.spend('diagnostic_records')
        rows.append(value)

    def _child(self, state, a, x, y, descriptor, seed):
        m = self.m
        d = self.owner_at(state, x)
        if d is _ABSENT or x == state.deleted or d == a:
            raise _Internal('illegal generated donor')
        admitted = d not in state.chains
        event = None
        if admitted:
            m.spend('admission_checks')
            event = dict(owner=d, descriptor=descriptor, chains_before=len(state.chains),
                         sites_before=len(state.patch), added_sites=len(self.entry[d]),
                         reason=None, staged=False, child_complete=False)
            self._record(seed['admissions'], event)
            if len(state.chains) + 1 > MAX_CHAINS:
                event['reason'] = 'chain_cap'; return None
            if len(state.patch) + len(self.entry[d]) > MAX_SITES:
                event['reason'] = 'site_cap'; return None
        patch = _copy_sites(state.patch, m, 'patch_copies')
        if admitted:
            for q in self.entry[d]:
                m.spend('admission_site_copies'); patch.add(q)
            if not _connected(patch, self.target, m):
                event['reason'] = 'disconnected_original_patch'; return None
            event['staged'] = True
        chains = {}
        for v, chain in state.chains.items():
            m.spend('child_chain_copies')
            chains[v] = _copy_sites(chain, m, 'child_qubit_copies')
        if admitted:
            m.spend('child_chain_copies')
            chains[d] = _copy_sites(self.entry[d], m, 'child_qubit_copies')
        m.spend('operation_updates'); chains[d].remove(x)
        m.spend('operation_updates'); chains[a].add(x)
        if y is not None:
            m.spend('operation_updates'); chains[a].remove(y)
            m.spend('operation_updates'); chains[d].add(y)
        if not _connected(chains[d], self.target, m) or not _connected(chains[a], self.target, m):
            if event is not None: event['reason'] = 'connectivity'
            return None
        trace = []
        for op in state.trace:
            m.spend('trace_copies'); trace.append(op)
        m.spend('trace_copies')
        trace.append((descriptor[0], x, y, a, d, d if admitted else None))
        child = _State(state.deleted, chains, patch, self.owners_for(chains),
                       [], state.depth+1, trace)
        child.missing = self.missing(child)
        # missing is small but its membership walk is still charged.
        for edge in child.missing:
            m.spend('chosen_contact_checks')
            if edge == state.missing[0]:
                if event is not None: event['reason'] = 'chosen_edge_missing'
                return None
        changed = 0
        for q, v in child.owners.items():
            m.spend('changed_site_checks')
            changed += v != self.owner[q]
        child.rank = (len(child.missing), changed, *descriptor)
        if event is not None:
            event['reason'] = 'complete_child'
            event['child_complete'] = True
        return child

    def generate(self, state, seed):
        """Complete declared successor generation, returning exactly its top four."""
        m, shortlist, descriptors = self.m, [], set()
        generation = dict(depth=state.depth, edge=state.missing[0], complete=False,
                          descriptors=0, complete_children=0, generated_feasible=0,
                          retained=None, prefix_retained=0, top_four_discarded=0,
                          work_start=m.budget.expansions, work=None,
                          interruption_stage=None)
        self._record(seed['generations'], generation)
        try:
            u, v = state.missing[0]
            for a, b in ((u, v), (v, u)):
                m.spend('generation_orientations')
                if a not in state.chains:
                    continue
                domain = set()
                chain = state.chains.get(b, self.entry[b])
                for q in chain:
                    m.spend('boundary_qubits')
                    for x in self.target[q]:
                        m.spend('boundary_adjacency')
                        donor = self.owner_at(state, x)
                        if donor is _ABSENT or donor == a:
                            continue
                        m.spend('boundary_domain_updates')
                        if x in domain:
                            seed['boundary_duplicates'] += 1
                        domain.add(x)
                receivers = _ordered(state.chains[a], m)
                for x in _ordered(domain, m):
                    # None means transfer; each actual site gives a simultaneous swap.
                    for index in range(-1, len(receivers)):
                        m.spend('generation_descriptors')
                        y = None if index == -1 else receivers[index]
                        key = (0, x, a) if y is None else (1, min(x, y), max(x, y))
                        generation['descriptors'] += 1
                        seed['generated'] += 1
                        if key in descriptors:
                            seed['descriptor_duplicates'] += 1
                            continue
                        m.spend('descriptor_records'); descriptors.add(key)
                        child = self._child(state, a, x, y, key, seed)
                        if child is None:
                            seed['rejected_descriptors'] += 1
                            continue
                        generation['complete_children'] += 1
                        seed['complete_children'] += 1
                        if not child.missing:
                            generation['generated_feasible'] += 1
                            seed['generated_feasible'] += 1
                            self.info['generated_feasible'] += 1
                        at = 0
                        while at < len(shortlist) and _compare(shortlist[at].rank, child.rank, m) <= 0:
                            at += 1
                        if at < MAX_CHILDREN:
                            m.spend('shortlist_writes'); shortlist.append(child)
                            j = len(shortlist)-1
                            while j > at:
                                m.spend('shortlist_writes'); shortlist[j] = shortlist[j-1]
                                j -= 1
                            m.spend('shortlist_writes'); shortlist[at] = child
                            if len(shortlist) > MAX_CHILDREN:
                                m.spend('shortlist_discards'); shortlist.pop()
                                generation['top_four_discarded'] += 1
                        else:
                            m.spend('shortlist_discards')
                            generation['top_four_discarded'] += 1
                        generation['prefix_retained'] = len(shortlist)
            generation['complete'] = True
            generation['retained'] = len(shortlist)
            seed['retained'] += len(shortlist)
            seed['top_four_discarded'] += generation['top_four_discarded']
            return shortlist
        except _Stop as exc:
            generation['interruption_stage'] = exc.stage
            seed['incomplete_generation'] = True
            seed['incomplete_generated_feasible'] += generation['generated_feasible']
            raise
        finally:
            generation['work'] = m.budget.expansions-generation['work_start']

    def certificate(self, state, group_index, seed):
        m = self.m
        original_patch = set()
        for v in state.chains:
            m.spend('certificate_original_chain_records')
            if v not in self.entry:
                raise _Internal('unknown selected owner')
            for q in self.entry[v]:
                m.spend('certificate_original_patch_checks')
                original_patch.add(q)
        if (len(state.chains) > MAX_CHAINS or len(original_patch) > MAX_SITES
                or len(original_patch) != len(state.patch)):
            raise _Internal('original patch/cap mismatch')
        for q in original_patch:
            m.spend('certificate_original_patch_checks')
            if q not in state.patch:
                raise _Internal('patch is not the whole entry-chain union')
        if state.deleted not in original_patch or not _connected(original_patch, self.target, m):
            raise _Internal('invalid original deletion patch')
        candidate = {}
        for v in self.vertices:
            m.spend('output_chain_records')
            if v in state.chains:
                candidate[v] = _ordered(state.chains[v], m)
            else:
                row = []
                for q in self.entry[v]:
                    m.spend('output_qubit_copies'); row.append(q)
                candidate[v] = row
        try:
            owners, total = self.validate(candidate)
        except _Invalid as exc:
            raise _Internal(str(exc)) from exc
        if total != self.q_entry-1 or state.deleted in owners:
            raise _Internal('Q/deleted-site certificate mismatch')
        selected_count = 0
        for v in self.vertices:
            m.spend('certificate_source_records')
            if v not in state.chains:
                if len(candidate[v]) != len(self.entry[v]):
                    raise _Internal('outside chain length changed')
                for i, q in enumerate(self.entry[v]):
                    m.spend('certificate_outside_checks')
                    if candidate[v][i] != q:
                        raise _Internal('outside chain changed')
            else:
                for q in candidate[v]:
                    m.spend('certificate_partition_checks')
                    selected_count += 1
                    if q not in state.patch or q == state.deleted:
                        raise _Internal('candidate left original patch')
        if selected_count != len(state.patch)-1:
            raise _Internal('incomplete surviving patch partition')
        for q in state.patch:
            m.spend('certificate_partition_checks')
            if q != state.deleted and owners.get(q, _ABSENT) not in state.chains:
                raise _Internal('patch site escaped selected owners')
        trace = []
        for kind, x, y, receiver, donor, admitted in state.trace:
            m.spend('output_trace_records')
            admitted_sites = None
            if admitted is not None:
                admitted_sites = _ordered(self.entry[admitted], m)
            trace.append(dict(operation='transfer' if kind == 0 else 'swap',
                              site=x, other_site=y, receiver=receiver, donor=donor,
                              admitted_owner=admitted, admitted_entry_sites=admitted_sites))
        selected = _ordered(state.chains, m)
        patch = _ordered(state.patch, m)
        selected_chains = {}
        for v in selected:
            m.spend('output_selected_records')
            row = []
            for q in candidate[v]:
                m.spend('output_qubit_copies'); row.append(q)
            selected_chains[v] = row
        metadata = dict(group_index=group_index, deleted=state.deleted,
                        selected=selected, original_patch=patch,
                        old_qubits=self.q_entry, new_qubits=total,
                        selected_chains=selected_chains, depth=state.depth,
                        trace=trace)
        self.info['certificate_complete'] += 1
        seed['certificate_complete'] += 1
        # All materialization and graph checking is over before publication.
        m.spend('publication')
        m.timely()  # Success at exactly budget.limit needs no spare unit.
        self.info['proposal'] = metadata
        self.info['candidate_returned'] = True
        self.info['q_after'] = total
        seed['reason'] = 'candidate_returned'
        return candidate

    def search(self, state, visited, group_index, seed):
        m = self.m
        m.spend('dfs_transitions')
        signature = self.signature(state)
        accepted, improved = visited.admit(signature, state.depth)
        if not accepted:
            seed['dominated_states'] += 1
            m.spend('dfs_transitions')
            return None
        seed['entered'] += 1
        seed['improved_depth_revisits'] += improved
        seed['depth_peak'] = max(seed['depth_peak'], state.depth)
        seed['selected_peak'] = max(seed['selected_peak'], len(state.chains))
        seed['patch_peak'] = max(seed['patch_peak'], len(state.patch))
        if not state.missing:
            with m.phase('certificate'):
                return self.certificate(state, group_index, seed)
        if seed['entered'] >= MAX_ENTERED:
            seed['state_cap'] = True
            raise _SeedCap
        if state.depth >= MAX_DEPTH:
            seed['depth_truncations'] += 1
        else:
            children = self.generate(state, seed)
            for child in children:
                m.spend('dfs_transitions')
                result = self.search(child, visited, group_index, seed)
                if result is not None:
                    return result
        m.spend('dfs_transitions')
        return None

    def group(self, supplied, index):
        m = self.m
        record = dict(index=index, normalized=None, inspected=False, complete=False,
                      reason=None, patch_sites=None, seeds=[], work_start=m.budget.expansions,
                      work=None)
        self._record(self.info['groups'], record)
        try:
            if type(supplied) not in (list, tuple) or not supplied:
                raise _Invalid('groups must be nonempty ordinary lists/tuples')
            members = set()
            for v in supplied:
                m.spend('group_validation')
                if type(v) is not int or v not in self.source or v in members:
                    raise _Invalid('group labels must be distinct existing source integers')
                members.add(v)
            ordered = _ordered(members, m)
            record['normalized'] = ordered
            record['inspected'] = True
            self.info['groups_inspected'] += 1
            if len(members) > MAX_CHAINS:
                record['reason'] = 'chain_cap'; record['complete'] = True
                return None
            patch, chains = set(), {}
            for v in ordered:
                m.spend('group_chain_records')
                chain = set()
                for q in self.entry[v]:
                    m.spend('group_qubit_copies')
                    chain.add(q); patch.add(q)
                chains[v] = chain
            record['patch_sites'] = len(patch)
            if len(patch) > MAX_SITES:
                record['reason'] = 'site_cap'; record['complete'] = True
                return None
            if not _connected(patch, self.target, m):
                record['reason'] = 'disconnected_original_patch'; record['complete'] = True
                return None
            for v in ordered:
                for q in _ordered(self.entry[v], m):
                    m.spend('seed_tests')
                    seed = dict(group_index=index, source_vertex=v, deleted=q,
                                reason=None, eligible=False, complete=False,
                                entered=0, generated=0, complete_children=0,
                                rejected_descriptors=0, descriptor_duplicates=0,
                                boundary_duplicates=0, retained=0, top_four_discarded=0,
                                dominated_states=0, improved_depth_revisits=0,
                                depth_peak=0, selected_peak=len(chains), patch_peak=len(patch),
                                depth_truncations=0, state_cap=False,
                                generated_feasible=0, certificate_complete=0,
                                incomplete_generation=False, incomplete_generated_feasible=0,
                                admissions=[], generations=[], work_start=m.budget.expansions,
                                work=None)
                    self._record(record['seeds'], seed)
                    self.info['seed_attempts'] += 1
                    try:
                        if len(self.entry[v]) < 2:
                            seed['reason'] = 'empty_remainder'; seed['complete'] = True
                            continue
                        selected = {}
                        for u, chain in chains.items():
                            m.spend('seed_chain_copies')
                            selected[u] = _copy_sites(chain, m, 'seed_qubit_copies')
                        m.spend('seed_removal'); selected[v].remove(q)
                        if not _connected(selected[v], self.target, m):
                            seed['reason'] = 'disconnected_remainder'; seed['complete'] = True
                            continue
                        root = _State(q, selected, _copy_sites(patch, m, 'patch_copies'),
                                      self.owners_for(selected), [], 0, [])
                        root.missing = self.missing(root)
                        if not root.missing:
                            seed['reason'] = 'safe_deletion'; seed['complete'] = True
                            continue
                        seed['eligible'] = True
                        try:
                            with m.phase('search'):
                                result = self.search(root, _Visited(m), index, seed)
                        except _SeedCap:
                            seed['reason'] = 'state_cap'
                            result = None
                        if result is not None:
                            record['reason'] = 'candidate_returned'
                            return result
                        if seed['reason'] is None:
                            seed['reason'] = 'retained_search_exhausted'
                        seed['complete'] = True
                    except _Stop as exc:
                        seed['reason'] = exc.reason
                        raise
                    finally:
                        seed['work'] = m.budget.expansions-seed['work_start']
            record['reason'] = 'seeds_exhausted'
            record['complete'] = True
            return None
        except _Invalid as exc:
            record['reason'] = 'invalid_input'
            record['error'] = str(exc)
            raise
        except _Stop as exc:
            record['reason'] = exc.reason
            raise
        finally:
            record['work'] = m.budget.expansions-record['work_start']


def ownership_exchange(embedding, source_adj, target_adj, seed_groups,
                       *, budget, deadline=None):
    """Return at most one fully certified occupied-site Q-1 proposal and info.

    Groups are finite ordinary lists/tuples, inspected lazily in supplied order.
    Source/target must be stable simple undirected loopless integer adjacency;
    chain values are nonempty lists and the entry must be valid. The occupied
    portion and all source edges are checked once, without traversing unused
    target vertices. No caller mapping or list is mutated, even on interruption.

    Malformed budget/deadline scalars raise ValueError. Detected input problems
    yield (None, info) with invalid_input; work/time interruptions yield no
    candidate. A returned private mapping is not automatically committed by any
    scheduler. All indices in the diagnostics are zero based. Work categories
    reconcile exactly to the caller's expansions delta; stage_wall is exclusive.
    """
    meter = _Meter(budget, deadline)
    info = dict(setup_started=0, setup_completed=0, private_copy_complete=False,
                entry_validated=False, group_count=None, group_accesses=0,
                groups_inspected=0, groups_completed=0, uninspected_groups=None,
                groups=[], seed_attempts=0, generated_feasible=0,
                certificate_complete=0, candidate_returned=False,
                proposal=None, q_before=None, q_after=None,
                stopped_reason=None, stopped_stage=None, error=None,
                limits=dict(chains=MAX_CHAINS, sites=MAX_SITES, depth=MAX_DEPTH,
                            children=MAX_CHILDREN, entered_per_seed=MAX_ENTERED))
    candidate = None
    try:
        meter.spend('group_sequence_header')
        if type(seed_groups) not in (list, tuple):
            raise _Invalid('seed_groups must be an ordinary finite list or tuple')
        info['group_count'] = len(seed_groups)
        if not seed_groups:
            info['stopped_reason'] = 'no_groups'
        else:
            ctx = _Context(source_adj, target_adj, meter, info)
            with meter.phase('setup'):
                ctx.setup(embedding)
            for index in range(len(seed_groups)):
                with meter.phase('groups'):
                    meter.spend('group_accesses')
                    info['group_accesses'] += 1
                    candidate = ctx.group(seed_groups[index], index)
                if candidate is not None:
                    info['stopped_reason'] = 'candidate_returned'
                    break
                info['groups_completed'] += 1
            if info['stopped_reason'] is None:
                info['stopped_reason'] = 'groups_exhausted'
    except _Stop as exc:
        info['stopped_reason'], info['stopped_stage'] = exc.reason, exc.stage
    except _Invalid as exc:
        info['stopped_reason'], info['error'] = 'invalid_input', str(exc)
    except _Internal as exc:
        info['stopped_reason'], info['error'] = 'internal_error', str(exc)
    if info['group_count'] is not None:
        info['uninspected_groups'] = info['group_count']-info['group_accesses']
    info.update(meter.finish())
    # Include unwinding and diagnostic finalization in timeliness. This check
    # requires no spare work and does not scan or copy any graph state.
    if candidate is not None:
        try:
            meter.timely()
        except _Stop as exc:
            candidate = None
            info['candidate_returned'] = False
            info['stopped_reason'], info['stopped_stage'] = exc.reason, 'final_return'
            info['q_after'] = None
            info['groups'][-1]['reason'] = 'deadline'
            info['groups'][-1]['seeds'][-1]['reason'] = 'deadline'
            late = max(0., exc.timestamp-meter.started-info['wall'])
            info['stage_wall']['administration'] += late
            info['wall'] += late
            info['deadline_overrun'] = max(0., exc.timestamp-meter.deadline)
    return candidate, info
