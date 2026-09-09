"""A063: valid-state whole-chain reconstruction with mobile contact stems.

One incumbent, original adjacency only, wall-bounded search. Work counters are
observations, never denial predicates. See 063_mobile_boundary_policy.md.
"""
from collections import Counter, deque
from collections.abc import Mapping, Sequence
from heapq import heappop, heappush
import math
import random
import time


class _Stop(Exception):
    pass


class _Meter:
    def __init__(self, deadline):
        self.deadline = deadline
        self.started = self.last = time.perf_counter()
        self.cpu_started = self.cpu_last = time.process_time()
        self.phase = 'setup'
        self.work = self.next_check = 0
        self.counts, self.units = Counter(), Counter()
        self.walls, self.cpus = Counter(), Counter()

    def check(self):
        if time.perf_counter() >= self.deadline:
            raise _Stop('deadline')

    def tick(self, name='item', amount=1):
        self.work += amount
        self.counts[name] += amount
        self.units[self.phase] += amount
        if self.work >= self.next_check:
            self.check()
            self.next_check = self.work + 256

    def phase_to(self, name):
        now, cpu = time.perf_counter(), time.process_time()
        self.walls[self.phase] += now-self.last
        self.cpus[self.phase] += cpu-self.cpu_last
        self.phase, self.last, self.cpu_last = name, now, cpu
        self.check()

    def ordered(self, values, key=None):
        self.check()
        self.tick('sort_items', len(values))
        answer = sorted(values, key=key)
        self.check()
        return answer

    def finish(self):
        now, cpu = time.perf_counter(), time.process_time()
        self.walls[self.phase] += now-self.last
        self.cpus[self.phase] += cpu-self.cpu_last
        self.last, self.cpu_last = now, cpu
        return dict(work=self.work, work_limit=None, counts=dict(self.counts),
                    work_by_stage=dict(self.units), wall_by_stage=dict(self.walls),
                    cpu_by_stage=dict(self.cpus), wall=now-self.started,
                    cpu=cpu-self.cpu_started, ended=now,
                    deadline=self.deadline, deadline_overrun=max(0., now-self.deadline))


class _ReadSequence(Sequence):
    def __init__(self, values, meter):
        self.values, self.meter = values, meter

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        self.meter.tick('validation_item')
        return self.values[key]

    def __iter__(self):
        for value in self.values:
            self.meter.tick('validation_item')
            yield value


class _ReadMap(Mapping):
    def __init__(self, values, meter):
        self.values, self.meter = values, meter

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        for key in self.values:
            self.meter.tick('validation_key')
            yield key

    def __getitem__(self, key):
        self.meter.tick('validation_lookup')
        return _ReadSequence(self.values[key], self.meter)


class _ReadSource:
    def __init__(self, adjacency, ranks, meter):
        self.adjacency, self.ranks, self.meter = adjacency, ranks, meter

    def __iter__(self):
        for key in self.adjacency:
            self.meter.tick('validation_key')
            yield key

    def edges(self):
        for u, ns in self.adjacency.items():
            for v in ns:
                self.meter.tick('validation_edge')
                if self.ranks[u] < self.ranks[v]:
                    yield u, v


class _Bundle:
    def __init__(self, chains, owners, witnesses, qubits, external):
        self.chains, self.owners, self.witnesses = chains, owners, witnesses
        self.qubits, self.external = qubits, external


def _graph(adjacency, meter):
    labels, ranks = [], {}
    for v in adjacency:
        meter.tick('input_vertex')
        ranks[v] = len(labels)
        labels.append(v)
    rows = []
    for v in labels:
        ns = set()
        for w in adjacency[v]:
            meter.tick('input_incidence')
            if w not in ranks or w == v or ranks[w] in ns:
                raise ValueError('simple adjacency required')
            ns.add(ranks[w])
        rows.append(frozenset(ns))
    for u, ns in enumerate(rows):
        for v in ns:
            meter.tick('input_symmetry')
            if u not in rows[v]:
                raise ValueError('undirected adjacency required')
    return labels, ranks, rows


class _Context:
    def __init__(self, source, target, seed, validator, meter):
        self.m, self.validator = meter, validator
        self.vlabels, self.vindex, self.src_sets = _graph(source, meter)
        self.qlabels, self.qindex, target_sets = _graph(target, meter)
        vp, qp = list(range(len(self.vlabels))), list(range(len(self.qlabels)))
        meter.tick('permutation_items', len(vp)+len(qp))
        random.Random('A063:source:'+str(seed)).shuffle(vp)
        random.Random('A063:target:'+str(seed)).shuffle(qp)
        meter.check()
        self.vtie, self.qtie = [0]*len(vp), [0]*len(qp)
        for i, v in enumerate(vp):
            meter.tick('rank_item'); self.vtie[v] = i
        for i, q in enumerate(qp):
            meter.tick('rank_item'); self.qtie[q] = i
        self.source = tuple(tuple(meter.ordered(ns, key=self.vtie.__getitem__))
                            for ns in self.src_sets)
        self.target = tuple(tuple(meter.ordered(ns, key=self.qtie.__getitem__))
                            for ns in target_sets)
        self.src_map = dict(enumerate(self.source))
        self.tgt_map = dict(enumerate(self.target))
        self.ranks = dict(enumerate(range(len(vp))))

    def read_entry(self, embedding):
        self.m.tick('entry_keys', len(embedding))
        if not isinstance(embedding, Mapping) or set(embedding) != set(self.vlabels):
            raise ValueError('complete source ownership required')
        chains = []
        for v in self.vlabels:
            chain = []
            if isinstance(embedding[v], (str, bytes, Mapping)):
                raise ValueError('chain must be a site collection')
            for q in embedding[v]:
                self.m.tick('entry_copy_site')
                if q not in self.qindex:
                    raise ValueError('unknown target site')
                chain.append(self.qindex[q])
            chains.append(tuple(chain))
        return tuple(chains)

    def externalize(self, chains):
        external = {}
        for u, chain in enumerate(chains):
            values = []
            for q in chain:
                self.m.tick('output_site'); values.append(self.qlabels[q])
            external[self.vlabels[u]] = values
        self.m.check()
        return external

    def certify(self, chains):
        """Authoritative validator; its whole cost belongs to certificate time."""
        self.m.phase_to('validation')
        self.m.tick('validation_mapping', len(chains))
        valid = self.validator(_ReadMap(dict(enumerate(chains)), self.m),
                               _ReadSource(self.src_map, self.ranks, self.m),
                               _ReadMap(self.tgt_map, self.m))
        self.m.check()
        if not valid:
            raise RuntimeError('original-graph certificate failed')

    def bundle(self, chains):
        """Linear occupied-edge witness accumulation, including reciprocal pairs."""
        self.m.phase_to('index_refresh')
        owners = [-1]*len(self.target)
        self.m.tick('owner_array_items', len(owners))
        qubits = 0
        for u, chain in enumerate(chains):
            self.m.tick('index_owner')
            if not chain:
                raise RuntimeError('empty chain')
            for q in chain:
                self.m.tick('index_site')
                if not 0 <= q < len(owners) or owners[q] != -1:
                    raise RuntimeError('ownership partition violated')
                owners[q] = u
                qubits += 1
        witnesses = {}
        for q, u in enumerate(owners):
            self.m.tick('index_target_site')
            if u < 0:
                continue
            for p in self.target[q]:
                self.m.tick('index_target_edge')
                v = owners[p]
                if u < v and v in self.src_sets[u]:
                    e, pair = (u, v), (q, p)
                    if e not in witnesses or pair < witnesses[e]:
                        witnesses[e] = pair
        for u, ns in enumerate(self.source):
            for v in ns:
                self.m.tick('index_source_edge')
                if u < v and (u, v) not in witnesses:
                    raise RuntimeError('missing original contact')
        external = self.externalize(chains)
        return _Bundle(chains, tuple(owners), witnesses, qubits, external)

    def spanning_tree(self, sites, root):
        allowed = set(sites)
        self.m.tick('tree_membership', len(sites))
        tree, queue = {root: set()}, deque([root])
        while queue:
            self.m.check()
            q = queue.popleft()
            self.m.tick('tree_pop')
            for p in self.target[q]:
                self.m.tick('tree_edge')
                if p in allowed and p not in tree:
                    tree[p] = {q}; tree[q].add(p); queue.append(p)
        if len(tree) != len(allowed):
            raise RuntimeError('disconnected chain during tree construction')
        return tree

    def trim(self, tree, terminals):
        heap = []
        for q, ns in tree.items():
            self.m.tick('leaf_setup')
            if len(ns) <= 1 and q not in terminals:
                heappush(heap, q)
        while heap:
            self.m.check()
            q = heappop(heap); self.m.tick('leaf_pop')
            if q not in tree or q in terminals or len(tree[q]) > 1:
                continue
            for p in tree[q]:
                self.m.tick('leaf_edge')
                tree[p].remove(q)
                if len(tree[p]) <= 1 and p not in terminals:
                    heappush(heap, p)
            del tree[q]
        if not tree or not terminals <= tree.keys():
            raise RuntimeError('terminal/nonempty invariant failed')
        return tuple(self.m.ordered(tree))

    def prepare(self, current, u, record):
        self.m.phase_to('stem_selection')
        reduced, removed = {}, {}
        for v in self.source[u]:
            terminals = set()
            for w in self.source[v]:
                self.m.tick('protected_edge')
                if w == u:
                    continue
                a, b = (v, w) if v < w else (w, v)
                pair = current.witnesses[(a, b)]
                terminals.add(pair[0 if v == a else 1])
            if not terminals:
                terminals.add(min(current.chains[v]))
                self.m.tick('anchor_scan', len(current.chains[v]))
            tree = self.spanning_tree(current.chains[v], min(terminals))
            reduced[v] = self.trim(tree, terminals)
            keep = set(reduced[v]); self.m.tick('retained_set', len(keep))
            removed[v] = []
            for q in current.chains[v]:
                self.m.tick('stem_site')
                if q not in keep:
                    removed[v].append(q)
        free = set()
        for q, owner in enumerate(current.owners):
            self.m.tick('free_site')
            if owner < 0 or owner == u:
                free.add(q)
        for values in removed.values():
            for q in values:
                self.m.tick('free_stem'); free.add(q)
        boundary = {}
        for v, sites in reduced.items():
            for q in sites:
                self.m.tick('boundary_site')
                for p in self.target[q]:
                    self.m.tick('boundary_edge')
                    if p in free:
                        boundary.setdefault(p, set()).add(v)
        record.update(neighbors=len(reduced), stem_sites=sum(map(len, removed.values())),
                      donors_changed=sum(bool(x) for x in removed.values()))
        return reduced, removed, free, boundary

    def roots(self, current, u, reduced, free, boundary, record):
        self.m.phase_to('root_search')
        n = len(self.target)
        sums, maxima, reached = [0]*n, [0]*n, [0]*n
        self.m.tick('root_array_items', 3*n)
        for v in reduced:
            distance = [-1]*n
            self.m.tick('distance_array_items', n)
            seeds = []
            for q, ns in boundary.items():
                self.m.tick('boundary_root')
                if v in ns:
                    seeds.append(q)
            queue = deque(self.m.ordered(seeds, key=self.qtie.__getitem__))
            for q in queue:
                distance[q] = 0
            while queue:
                self.m.check()
                q = queue.popleft(); d = distance[q]
                self.m.tick('root_bfs_pop')
                sums[q] += d; maxima[q] = max(maxima[q], d); reached[q] += 1
                for p in self.target[q]:
                    self.m.tick('root_bfs_edge')
                    if p in free and distance[p] < 0:
                        distance[p] = d+1; queue.append(p)
        eligible = []
        for q in free:
            self.m.tick('root_candidate')
            if reached[q] == len(reduced):
                eligible.append(q)
        for q in current.chains[u]:
            self.m.tick('old_root_check')
            if reached[q] != len(reduced):
                raise RuntimeError('old-root contact reach invariant failed')
        eligible = self.m.ordered(eligible, key=lambda q: (sums[q], maxima[q], self.qtie[q]))
        record.update(ranking_complete=True, eligible_roots=len(eligible))
        return eligible

    def reconstruct(self, root, reduced, free, boundary, u):
        self.m.phase_to('reconstruction')
        tree = {root: set()}
        missing = set(reduced)
        self.m.tick('unmet_neighbors', len(missing))
        while True:
            for q in tree:
                self.m.tick('tree_contact_site')
                for v in boundary.get(q, ()):
                    self.m.tick('tree_contact'); missing.discard(v)
            if not missing:
                break
            start = self.m.ordered(tree, key=self.qtie.__getitem__)
            pred = {q: None for q in start}
            level = start
            chosen = None
            self.m.tick('tree_bfs_sources', len(start))
            while level and chosen is None:
                following, hits = [], []
                for q in level:
                    self.m.check(); self.m.tick('tree_bfs_pop')
                    for v in boundary.get(q, ()):
                        self.m.tick('tree_bfs_contact')
                        if v in missing:
                            hits.append((self.vtie[v], self.qtie[q], q))
                    for p in self.target[q]:
                        self.m.tick('tree_bfs_edge')
                        if p in free and p not in pred:
                            pred[p] = q; following.append(p)
                if hits:
                    chosen = min(hits)[2]
                    self.m.tick('hit_selection', len(hits))
                level = following
            if chosen is None:
                raise RuntimeError('ranked root lost shared-path reach')
            path, q = [], chosen
            while q not in tree:
                self.m.tick('extension_site'); path.append(q); q = pred[q]
            self.m.tick('shared_tree_junction')
            for p in reversed(path):
                self.m.tick('extension_publish')
                tree[p] = {q}; tree[q].add(p); q = p
        witnesses, retained_owner = {}, {}
        for v, sites in reduced.items():
            for q in sites:
                self.m.tick('retained_witness_site'); retained_owner[q] = v
        for q in tree:
            self.m.tick('new_contact_site')
            for p in self.target[q]:
                self.m.tick('new_contact_edge')
                if p in retained_owner:
                    v = retained_owner[p]
                    pair = (q, p) if u < v else (p, q)
                    if v not in witnesses or pair < witnesses[v]:
                        witnesses[v] = pair
        terminals = {pair[0 if u < v else 1] for v, pair in witnesses.items()} if reduced else {min(tree)}
        if len(witnesses) != len(reduced):
            raise RuntimeError('constructed tree lacks required terminal')
        return self.trim(tree, terminals)


def mobile_boundary_reconstruction(embedding, source_adj, target_adj, *, seed=0,
                                   deadline, validator):
    """Return the last certified minor after a normal stop; return {} on error."""
    if type(seed) is not int or not isinstance(deadline, (int, float)) or not math.isfinite(deadline):
        raise ValueError('integer seed and finite absolute deadline required')
    m = _Meter(deadline)
    info = dict(algorithm='mobile_boundary_reconstruction', version='A063', status='started',
                error=None, input_copy_complete=False, input_validated=False,
                passes_started=0, passes_completed=0, queries=[], commits=[],
                accepted=0, before_qubits=None, after_qubits=None,
                last_complete_query=None, stopped_phase=None, diagnostic_embedding=None)
    current, result = None, embedding
    try:
        m.check()
        ctx = _Context(source_adj, target_adj, seed, validator, m)
        chains = ctx.read_entry(embedding)
        result = ctx.externalize(chains)
        info['input_copy_complete'] = True
        ctx.certify(chains)
        current = ctx.bundle(chains)
        result = current.external
        info.update(input_validated=True, before_qubits=current.qubits)
        while True:
            m.phase_to('schedule')
            order = m.ordered(list(range(len(ctx.source))),
                              key=lambda u: (-len(current.chains[u]), ctx.vtie[u]))
            info['passes_started'] += 1
            changed = False
            for u in order:
                m.check()
                started, cpu, work = time.perf_counter(), time.process_time(), m.work
                record = dict(pass_index=info['passes_started']-1, owner=u,
                              before_qubits=current.qubits, status='started',
                              ranking_complete=False, eligible_roots=None,
                              roots_examined=0, trees_completed=0, best_completed_qubits=None,
                              q_rejections=0, certificates=0, committed=False,
                              root_generation_wall=None, root_generation_cpu=None,
                              reconstruction_wall={}, reconstruction_cpu={})
                info['queries'].append(record)
                try:
                    reduced, removed, free, boundary = ctx.prepare(current, u, record)
                    old_local = len(current.chains[u])+sum(len(current.chains[v]) for v in reduced)
                    retained = sum(map(len, reduced.values()))
                    if 1+retained >= old_local:
                        record['status'] = 'no_strict_gain_bound'
                        continue
                    root_start, root_cpu = time.perf_counter(), time.process_time()
                    try:
                        roots = ctx.roots(current, u, reduced, free, boundary, record)
                    finally:
                        record.update(root_generation_wall=time.perf_counter()-root_start,
                                      root_generation_cpu=time.process_time()-root_cpu)
                    for root in roots:
                        m.check(); record['roots_examined'] += 1
                        tree_start, tree_cpu = time.perf_counter(), time.process_time()
                        outcome = 'interrupted_or_error'
                        try:
                            tree = ctx.reconstruct(root, reduced, free, boundary, u)
                            record['trees_completed'] += 1
                            proposed = current.qubits-old_local+retained+len(tree)
                            outcome = 'nonimproving' if proposed >= current.qubits else 'smaller_Q'
                        finally:
                            record['reconstruction_wall'][outcome] = record['reconstruction_wall'].get(outcome, 0.)+time.perf_counter()-tree_start
                            record['reconstruction_cpu'][outcome] = record['reconstruction_cpu'].get(outcome, 0.)+time.process_time()-tree_cpu
                        previous = record['best_completed_qubits']
                        record['best_completed_qubits'] = proposed if previous is None else min(previous, proposed)
                        if proposed >= current.qubits:
                            record['q_rejections'] += 1
                            continue
                        m.phase_to('candidate_copy')
                        m.tick('candidate_owner_copy', len(current.chains))
                        updated = list(current.chains)
                        updated[u] = tree
                        for v, sites in reduced.items():
                            m.tick('candidate_neighbor'); updated[v] = sites
                        chains = tuple(updated)
                        record['certificates'] += 1
                        ctx.certify(chains)
                        candidate = ctx.bundle(chains)
                        if candidate.qubits != proposed or candidate.qubits >= current.qubits:
                            raise RuntimeError('actual total-Q admission mismatch')
                        m.phase_to('bookkeeping')
                        changed_owners = []
                        for v, (old, new) in enumerate(zip(current.chains, candidate.chains)):
                            m.tick('frozen_owner_check')
                            if old != new:
                                if v != u and v not in reduced:
                                    raise RuntimeError('frozen owner changed')
                                m.tick('receipt_sites', len(old)+len(new))
                                changed_owners.append(dict(owner=v, before=list(old), after=list(new)))
                        receipt = dict(index=len(info['commits']), owner=u, root=root,
                                       before_qubits=current.qubits, after_qubits=candidate.qubits,
                                       qubits_saved=current.qubits-candidate.qubits,
                                       donors_changed=record['donors_changed'], stem_sites=record['stem_sites'],
                                       changed_owners=changed_owners, deadline=deadline)
                        m.tick('receipt_list_copy', len(info['commits']))
                        new_receipts = info['commits']+[receipt]
                        m.check()
                        admitted = time.perf_counter()
                        if admitted >= deadline:
                            raise _Stop('deadline')
                        receipt['admitted'] = admitted
                        # All fallible preparation/certification precedes this publication.
                        current, result, info['commits'] = candidate, candidate.external, new_receipts
                        info['accepted'] += 1
                        changed = True
                        record.update(status='committed', committed=True, after_qubits=current.qubits)
                        break
                    if not record['committed']:
                        record['status'] = 'no_gain'
                finally:
                    record.update(wall=time.perf_counter()-started, cpu=time.process_time()-cpu,
                                  work=m.work-work)
                    if record['status'] == 'started':
                        record.update(status='interrupted_or_error', stopped_phase=m.phase)
                    else:
                        info['last_complete_query'] = len(info['queries'])-1
            info['passes_completed'] += 1
            if not changed:
                info['status'] = 'no_improvement_pass'
                break
    except _Stop:
        info.update(status='deadline', stopped_phase=m.phase)
    except Exception as exc:
        info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_phase=m.phase,
                    diagnostic_embedding=current.external if current is not None else embedding)
        result = {}
    info['after_qubits'] = current.qubits if current is not None else None
    info.update(m.finish())
    if info['ended'] >= deadline and info['status'] != 'error':
        info.update(status='deadline', stopped_phase=m.phase)
    return result, info
