"""Fixed, bounded group selection for the ownership reach/cost diagnostic.

The caller supplies one independently valid minor on stable simple undirected
graphs. This helper checks scalar/container/label/coverage/occupancy structure;
it does not repeat full minor or unused-target-edge validation. No method-specific
context, embedding algorithm, graph metadata or result comparison is used.
"""
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import math
import time


class _Invalid(Exception):
    pass


class _Expired(Exception):
    pass


class _Clock:
    def __init__(self):
        self.start = self.mark = time.perf_counter()
        self.deadline = None
        self.stage = 'administration'
        self.last_event = None
        self.failed_stage = None
        self.events = Counter()
        self.walls = Counter()

    def check(self):
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise _Expired

    def event(self, name, count=1):
        self.last_event = name
        self.check()
        self.events[name] += count

    def switch(self, stage):
        now = time.perf_counter()
        self.walls[self.stage] += now - self.mark
        self.mark, self.stage = now, stage

    @contextmanager
    def phase(self, stage):
        before = self.stage
        self.switch(stage)
        try:
            yield
        except (_Invalid, _Expired):
            if self.failed_stage is None:
                self.failed_stage = self.stage
            raise
        finally:
            self.switch(before)

    def ordered(self, values, *, key=None):
        # Counts are typed events, not CPU instructions or sort comparisons.
        # The complete builtin sort remains in wall time and is checked on both
        # sides; an interrupted/late sort cannot publish a partial sequence.
        self.event('sort_calls')
        self.events['sort_items'] += len(values)
        result = sorted(values, key=key)
        self.check()
        return result

    def finish(self):
        self.switch('administration')
        ended = time.perf_counter()
        self.walls[self.stage] += ended - self.mark
        return ended, dict(events=dict(self.events), stage_wall=dict(self.walls),
                           wall=ended-self.start,
                           deadline_overrun=max(0., ended-self.deadline)
                           if self.deadline is not None else 0.)


def _row(value):
    if type(value) not in (list, tuple):
        raise _Invalid('adjacency rows must be ordinary lists or tuples')
    return value


def diagnostic_groups(embedding, source_adj, target_adj, *, limit=512, deadline=None):
    """Return ``(complete_groups, info)`` or ``(None, incomplete_info)``.

    All mappings must be ordinary dicts, chains ordinary nonempty lists and
    adjacency rows ordinary lists/tuples with ordinary integer labels. The valid
    minor/simple-undirected-graph premise is checked separately by the caller.
    Only completed selection returns a list, including an empty list. ``limit=0``
    still completes input preparation and pool sorting. Typed event counts are
    diagnostic counts; complete elapsed cost, including builtin sorting/hash
    work and finalization, is reported in wall time. The deadline is cooperative.
    """
    clock = _Clock()
    pools = {k: [] for k in (1, 2, 3, 4)}
    pool_info = {str(k): dict(raw=0, duplicates=0, over_site_cap=0, no_seed=0,
                              eligible=None, selected=None) for k in pools}
    info = dict(status=None, complete=False, generation_complete=False,
                selection_materialized=False, limit=None, deadline=None,
                returned_groups=None, vector_sha256=None,
                vector_encoding='UTF-8 compact JSON arrays; no trailing newline',
                source_vertices=None, target_vertices=None, occupied_qubits=None,
                maximum_target_degree=None, quotient_edges=None,
                pool_counts=pool_info, stopped_stage=None, stopped_event=None,
                error=None, validation_scope='structure and occupancy only; valid minor and simple stable graphs are caller preconditions')
    candidate = None
    vector_hash = None
    try:
        with clock.phase('input'):
            clock.event('scalar_checks')
            if type(limit) is not int or limit < 0:
                raise _Invalid('limit must be an ordinary nonnegative integer')
            info['limit'] = limit
            if deadline is not None:
                try:
                    finite = type(deadline) in (int, float) and math.isfinite(deadline)
                except OverflowError:
                    finite = False
                if not finite:
                    raise _Invalid('deadline must be a finite absolute timestamp')
            clock.deadline = deadline
            info['deadline'] = deadline
            clock.check()
            for value in (embedding, source_adj, target_adj):
                clock.event('mapping_checks')
                if type(value) is not dict:
                    raise _Invalid('embedding and adjacency mappings must be ordinary dicts')
            info['source_vertices'] = len(source_adj)
            info['target_vertices'] = len(target_adj)
            maximum_degree = 0
            for q, neighbors in target_adj.items():
                clock.event('target_header_records')
                if type(q) is not int:
                    raise _Invalid('target keys must be ordinary integers')
                maximum_degree = max(maximum_degree, len(_row(neighbors)))
            info['maximum_target_degree'] = maximum_degree
            degrees = {}
            for v, neighbors in source_adj.items():
                clock.event('source_records')
                if type(v) is not int:
                    raise _Invalid('source keys must be ordinary integers')
                seen_neighbors = set()
                for w in _row(neighbors):
                    clock.event('source_adjacency_entries')
                    if type(w) is not int or w not in source_adj or w == v or w in seen_neighbors:
                        raise _Invalid('malformed source adjacency row')
                    seen_neighbors.add(w)
                degrees[v] = len(neighbors)
            lengths, owners = {}, {}
            if len(embedding) != len(source_adj):
                raise _Invalid('embedding/source coverage differs')
            for v, chain in embedding.items():
                clock.event('chain_records')
                if type(v) is not int or v not in source_adj or type(chain) is not list or not chain:
                    raise _Invalid('source coverage and nonempty ordinary list chains required')
                lengths[v] = len(chain)
                for q in chain:
                    clock.event('occupied_sites')
                    if type(q) is not int or q not in target_adj or q in owners:
                        raise _Invalid('unknown, noninteger or multiply owned target site')
                    owners[q] = v
            info['occupied_qubits'] = len(owners)

        with clock.phase('quotient'):
            adjacent = {}
            for v in source_adj:
                clock.event('quotient_vertex_records')
                adjacent[v] = set()
            for q, v in owners.items():
                clock.event('quotient_owned_sites')
                seen_neighbors = set()
                for p in target_adj[q]:
                    clock.event('occupied_target_adjacency_entries')
                    if type(p) is not int or p not in target_adj or p == q or p in seen_neighbors:
                        raise _Invalid('malformed occupied target adjacency row')
                    seen_neighbors.add(p)
                    if p in owners and owners[p] != v:
                        w = owners[p]
                        clock.event('quotient_relation_entries')
                        if w in adjacent[v]:
                            clock.events['quotient_relation_duplicates'] += 1
                        else:
                            adjacent[v].add(w)
                            adjacent[w].add(v)
                            clock.events['quotient_edge_insertions'] += 1
            info['quotient_edges'] = clock.events['quotient_edge_insertions']

        with clock.phase('ranking'):
            nodes = []
            for v in source_adj:
                clock.event('rank_node_records')
                nodes.append(v)
            ranks = {}
            textual = {}
            for v in nodes:
                clock.event('label_repr_records')
                try:
                    textual[v] = repr(v)
                except ValueError as exc:
                    raise _Invalid('source integer label cannot be represented') from exc
            for i, v in enumerate(clock.ordered(nodes, key=textual.__getitem__)):
                clock.event('rank_records')
                ranks[v] = i
            priorities = {}
            for v in nodes:
                clock.event('priority_records')
                bound = (max(1, math.ceil((degrees[v]-2)/(maximum_degree-2)))
                         if maximum_degree > 2 else 1)
                priorities[v] = (-(lengths[v]-bound), -lengths[v], ranks[v])
            centers = clock.ordered(nodes, key=priorities.__getitem__)
            neighbors = {}
            for v in centers:
                clock.event('neighbor_list_records')
                neighbors[v] = clock.ordered(adjacent[v], key=priorities.__getitem__)

        with clock.phase('windows'):
            for v in centers:
                clock.event('singleton_candidates')
                row = pool_info['1']; row['raw'] += 1
                if lengths[v] > 64:
                    row['over_site_cap'] += 1
                elif lengths[v] == 1:
                    row['no_seed'] += 1
                else:
                    clock.event('pool_records')
                    pools[1].append((lengths[v], (v,), (v,)))
            seen = {k: set() for k in (2, 3, 4)}
            active = []
            for v in centers:
                clock.event('active_center_records')
                if neighbors[v]:
                    active.append(v)
            depth = 0
            while active:
                for k in (2, 3, 4):
                    width = k-1
                    for v in active:
                        clock.event('window_center_visits')
                        if depth+width > len(neighbors[v]):
                            continue
                        row = pool_info[str(k)]; row['raw'] += 1
                        payload = [v]
                        for w in neighbors[v][depth:depth+width]:
                            clock.event('window_member_records')
                            payload.append(w)
                        key = tuple(clock.ordered(payload))
                        clock.event('window_dedup_checks')
                        if key in seen[k]:
                            row['duplicates'] += 1
                            continue
                        footprint, has_seed = 0, False
                        for w in payload:
                            clock.event('window_size_records')
                            footprint += lengths[w]
                            has_seed = has_seed or lengths[w] >= 2
                        if footprint > 64:
                            row['over_site_cap'] += 1
                        elif not has_seed:
                            row['no_seed'] += 1
                        else:
                            clock.event('pool_records')
                            seen[k].add(key)
                            pools[k].append((footprint, key, tuple(payload)))
                depth += 1
                next_active = []
                for v in active:
                    clock.event('active_center_records')
                    if len(neighbors[v]) > depth:
                        next_active.append(v)
                active = next_active

        with clock.phase('pool_sorting'):
            for k in (1, 2, 3, 4):
                clock.event('pool_sort_records')
                pools[k] = clock.ordered(pools[k], key=lambda row: (row[0], row[1]))
                pool_info[str(k)]['eligible'] = len(pools[k])
            clock.check()
            info['generation_complete'] = True

        with clock.phase('selection'):
            offsets = {k: 0 for k in pools}
            selected = []
            while len(selected) < limit:
                advanced = False
                for k in (1, 2, 3, 4):
                    clock.event('interleave_stream_visits')
                    if offsets[k] >= len(pools[k]) or len(selected) >= limit:
                        continue
                    payload = []
                    for v in pools[k][offsets[k]][2]:
                        clock.event('output_member_records')
                        payload.append(v)
                    clock.event('output_group_records')
                    selected.append(tuple(payload))
                    offsets[k] += 1
                    advanced = True
                if not advanced:
                    break
            for k in pools:
                clock.event('selected_size_records')
                pool_info[str(k)]['selected'] = offsets[k]
            clock.check()
            info['selection_materialized'] = True

        with clock.phase('encoding'):
            clock.event('vector_encodings')
            encoded = json.dumps(selected, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
            clock.check()
            clock.events['encoded_bytes'] += len(encoded)
            vector_hash = hashlib.sha256(encoded).hexdigest()
            clock.check()
            candidate = selected
            info['status'] = 'complete'
    except _Invalid as exc:
        info['status'], info['error'] = 'invalid_input', str(exc)
    except _Expired:
        info['status'] = 'deadline'
    # No vector has been published yet. Finalization itself remains in wall time;
    # crossing here invalidates a completely generated/hashed private selection.
    info['stopped_stage'] = clock.failed_stage or clock.stage
    info['stopped_event'] = clock.last_event
    ended, cost = clock.finish()
    info.update(cost)
    if info['status'] != 'invalid_input' and clock.deadline is not None and ended >= clock.deadline:
        if info['status'] == 'complete':
            info['stopped_stage'] = 'finalization'
        info['status'] = 'deadline'
        candidate = None
    if info['status'] == 'complete':
        info['complete'] = True
        info['returned_groups'] = len(candidate)
        info['vector_sha256'] = vector_hash
        info['stopped_stage'] = None
        info['stopped_event'] = None
    else:
        candidate = None
    return candidate, info
