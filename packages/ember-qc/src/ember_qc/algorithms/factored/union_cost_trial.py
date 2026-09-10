"""B029 private owner-chain evaluation and one-coupler root descent.

No embedding constructor is called here. A trial changes only scratch arrays;
all residual chains, prices, finalized route arrays and witnesses are read-only.
Dense degree-by-target contact endpoints impose no 64-neighbor mask limit.
"""
from time import perf_counter

import numpy as np
from numba import njit


WORK_NAMES = ('union_attachment_site', 'union_parent_step', 'union_contact_probe',
              'union_trim_arc', 'union_keep_site')


@njit(cache=False, boundscheck=True)
def _attach_neighbor(j, root, sites, length, members, contacts, settled, mask,
                     parents, work):
    for i in range(length):
        work[0] += 1
        if contacts[j, sites[i]] >= 0:
            return length, 1, 0
    found = False
    chosen = -1
    value = 0
    for i in range(length):
        q = sites[i]
        work[0] += 1
        if mask[j, q] and (not found or settled[j, q] < value
                          or settled[j, q] == value and q < chosen):
            found = True
            chosen, value = q, settled[j, q]
    if not found:
        raise ValueError('no finalized attachment entry')
    shared = int(chosen != root)
    q, added, steps = chosen, 0, 0
    while q != -1:
        # A simple positive-weight parent path cannot contain more than n sites.
        # This checks malformed input; it is not a research work allowance.
        if q < 0 or q >= len(members) or not mask[j, q] or steps >= len(members):
            raise ValueError('invalid finalized attachment parent path')
        work[1] += 1
        steps += 1
        if not members[q]:
            members[q] = True
            sites[length] = q
            length += 1
            added += 1
        q = parents[j, q]
    return length, shared, added


@njit(cache=False, boundscheck=True)
def _contacts_trim(members, length, contacts, starts, adjacency, occupied,
                   costs, work):
    n, degree = len(members), contacts.shape[0]
    owner_endpoint = np.full(degree, -1, dtype=np.int64)
    neighbor_endpoint = np.full(degree, -1, dtype=np.int64)
    terminals = np.zeros(n, dtype=np.bool_)
    found = 0
    # Target index is the fixed target rank. This is the original contact order.
    for q in range(n):
        if not members[q]:
            continue
        for j in range(degree):
            work[2] += 1
            if owner_endpoint[j] < 0 and contacts[j, q] >= 0:
                owner_endpoint[j], neighbor_endpoint[j] = q, contacts[j, q]
                terminals[q] = True
                found += 1
        if found == degree:
            break
    if found != degree:
        raise ValueError('missing actual source contact in trial')
    root = -1
    for q in range(n):
        if terminals[q]:
            root = q
            break
    if root < 0:
        raise ValueError('nonisolated trial has no terminal')
    tree = np.full(n, -2, dtype=np.int64)
    queue = np.empty(n, dtype=np.int64)
    tree[root], queue[0] = -1, root
    head, tail = 0, 1
    while head < tail:
        q = queue[head]
        head += 1
        for i in range(starts[q], starts[q + 1]):
            p = adjacency[i]
            work[3] += 1
            if members[p] and tree[p] == -2:
                tree[p] = q
                queue[tail] = p
                tail += 1
    if tail != length:
        raise ValueError('disconnected attached trial chain')
    keep = np.zeros(n, dtype=np.bool_)
    keep[root] = True
    for terminal in range(n):
        if not terminals[terminal]:
            continue
        q = terminal
        steps = 0
        while not keep[q]:
            if q < 0 or steps >= n or tree[q] == -2:
                raise ValueError('invalid witnessed trim path')
            keep[q] = True
            work[4] += 1
            steps += 1
            q = tree[q]
    Q = O = Phi = 0
    for q in range(n):
        if keep[q]:
            if costs[q] < 1:
                raise ValueError('trial uses forbidden residual site')
            Q += 1
            O += int(occupied[q] > 0)
            Phi += costs[q]
    return Q, O, Phi, keep, tree, owner_endpoint, neighbor_endpoint


def _score_key(scores, quality):
    return (scores['Q'],) if quality else (scores['O'], scores['Phi'], scores['Q'])


class FinalizedRow:
    """Read-only original-label lookups for one selected-proposal comparison."""

    def __init__(self, engine, route, neighbor_index, parent=False):
        self.engine, self.route = engine, route
        self.j, self.parent = neighbor_index, parent

    def __contains__(self, q):
        rank = self.engine.rank.get(q)
        return rank is not None and bool(self.route['settled_mask'][self.j, rank])

    def __getitem__(self, q):
        if q not in self:
            raise KeyError(q)
        rank = self.engine.rank[q]
        if not self.parent:
            return int(self.route['settled'][self.j, rank])
        p = int(self.route['parent'][self.j, rank])
        if p < -1:
            raise ValueError('finalized site has an unknown parent')
        return None if p == -1 else self.engine.qorder[p]


class Evaluator:
    """A fixed residual state and a reusable packed route, scoped to one visit."""

    def __init__(self, engine, owner, changes, occupancy, route, record, observer=None):
        self.e, self.u, self.route, self.record = engine, owner, route, record
        self.observer = observer
        self.neighbors = route['neighbors']
        self.n = len(engine.qorder)
        self.work = np.zeros(len(WORK_NAMES), dtype=np.int64)
        self.previous_work = [0] * len(WORK_NAMES)
        record.update(status='PREPARING', roots=[], neighborhoods=[], cached_hits=0,
            moves=[], overlap_definition='excess memberships: sum(max(k-1,0))',
            materialized=False, native_safe=route['native_safe'])
        if not hasattr(engine, 'union_stats'):
            engine.union_stats = dict(trial_attempts=0, completed_trials=0,
                local_moves=0, excluded_neighbors=0, dispatches=0,
                compilation_attempts=0, compile_dispatches=0, compile_dispatch_wall=0.0,
                dispatch_wall=0.0, materialization_wall=0.0, maximum_dispatch_wall=0.0,
                fallback_dispatches=0, trace_scope='first sixteen visits and last visit; counters cover all')
        self.stats = engine.union_stats
        old, m = engine.state, engine.m
        with m.phase('union_residual_pack'):
            old_phi = old.Q
            for q, owners in old.owners.items():
                k = len(owners)
                old_phi += engine.prices.get(q, 1) * k * (k - 1) // 2
                m.step('union_residual_owner')
            Q = old.Q + sum(len(c) - len(old.chains.get(v, ())) for v, c in changes.items())
            O, Phi = old.O, old_phi + Q - old.Q
            for q, owners in occupancy.items():
                before, after = len(old.owners.get(q, ())), len(owners)
                O += max(after - 1, 0) - max(before - 1, 0)
                Phi += engine.prices.get(q, 1) * (after * (after - 1) - before * (before - 1)) // 2
                m.step('union_residual_delta')
            self.base = dict(Q=Q, O=O, Phi=Phi)
            record.update(entry_scores=dict(Q=old.Q, O=old.O, Phi=old_phi), residual_scores=self.base)
            self.occupied = np.asarray([len(occupancy.get(q, old.owners.get(q, ())))
                                        for q in engine.qorder], dtype=np.int64)
            m.step('union_occupancy_pack', self.n)
            # contacts[j,q] is the first target-rank endpoint in neighbor j
            # adjacent to q. Dense endpoints support arbitrary source degree.
            self.contacts = np.full((len(self.neighbors), self.n), -1, dtype=np.int64)
            m.step('union_contact_allocation', len(self.neighbors) * self.n)
            for j, v in enumerate(self.neighbors):
                for p in changes[v]:
                    r = engine.rank[p]
                    for q in engine.adj[p]:
                        k = engine.rank[q]
                        if self.contacts[j, k] < 0 or r < self.contacts[j, k]:
                            self.contacts[j, k] = r
                        m.step('union_contact_pack_arc')
                m.clock()
            self.contacts.flags.writeable = False
            self.occupied.flags.writeable = False
            for name in ('costs', 'settled', 'settled_mask', 'parent'):
                if route[name].flags.writeable:
                    raise ValueError('mutable route array supplied to evaluator')
            if route['settled'].shape != (len(self.neighbors), self.n):
                raise ValueError('wrong settled array shape')
            if route['parent'].shape != route['settled'].shape or route['settled_mask'].shape != route['settled'].shape:
                raise ValueError('wrong parent/mask array shape')
            if len(route['costs']) != self.n:
                raise ValueError('wrong site-cost array shape')
            m.clock()
        record['status'] = 'READY'

    def _dispatch(self, function, args, row):
        m = self.e.m
        m.clock()
        native = self.route['native_safe']
        signatures = len(function.signatures) if native else 0
        began = perf_counter()
        failure = None
        try:
            return (function if native else function.py_func)(*args)
        except BaseException as exc:
            failure = exc
            row['dispatch_error'] = repr(exc)
            raise
        finally:
            elapsed = perf_counter() - began
            compiled = native and len(function.signatures) > signatures
            attempted = native and (compiled or signatures == 0)
            units = 0
            for i, name in enumerate(WORK_NAMES):
                value = int(self.work[i])
                delta = value - self.previous_work[i]
                if delta < 0:
                    raise RuntimeError('trial work counter moved backwards')
                self.previous_work[i] = value
                m.kinds[name] += delta
                units += delta
            m.total += units; m.pending += units; m.units[m.stage] += units
            row['dispatches'] += 1
            row['dispatch_wall'] += elapsed
            row['compilation_attempts'] += int(attempted)
            row['compile_dispatches'] += int(compiled)
            row['compile_dispatch_wall'] += elapsed if attempted else 0.0
            self.stats['dispatches'] += 1
            self.stats['dispatch_wall'] += elapsed
            self.stats['compilation_attempts'] += int(attempted)
            self.stats['compile_dispatches'] += int(compiled)
            self.stats['compile_dispatch_wall'] += elapsed if attempted else 0.0
            self.stats['fallback_dispatches'] += int(not native)
            self.stats['maximum_dispatch_wall'] = max(self.stats['maximum_dispatch_wall'], elapsed)
            # One neighbor attachment or one bounded target-chain trim per
            # observation; cold compilation remains included and can overrun.
            if failure is None:
                m.clock()

    def trial(self, root, kind='root_trial'):
        e, route = self.e, self.route
        row = dict(root=e.qorder[root] if 0 <= root < self.n else None,
            root_rank=root, kind=kind, status='STARTED',
            started=perf_counter() - e.began, dispatches=0, dispatch_wall=0.0,
            compilation_attempts=0, compile_dispatches=0, compile_dispatch_wall=0.0)
        self.record['roots'].append(row)
        self.stats['trial_attempts'] += 1
        began = perf_counter()
        try:
            if self.observer is not None:
                self.observer('trial_started', row)
            e.m.clock()
            if root < 0 or root >= self.n or not all(route['settled_mask'][:, root]):
                raise ValueError('root lacks finalized labels')
            with e.m.phase('union_trial_allocation'):
                members = np.zeros(self.n, dtype=np.bool_)
                sites = np.empty(self.n, dtype=np.int64)
                members[root], sites[0] = True, root
                length, shared, added = 1, 0, 0
                e.m.step('union_scratch_item', 2 * self.n)
            with e.m.phase('union_attachment'):
                for j in range(len(self.neighbors)):
                    length, current_shared, current_added = self._dispatch(_attach_neighbor,
                        (j, root, sites, length, members, self.contacts, route['settled'],
                         route['settled_mask'], route['parent'], self.work), row)
                    shared += current_shared; added += current_added
            with e.m.phase('union_contacts_trim'):
                result = self._dispatch(_contacts_trim, (members, length, self.contacts,
                    route['starts'], route['adjacency'], self.occupied, route['costs'], self.work), row)
            Q, O, Phi, keep, tree, endpoints, neighbor_endpoints = result
            scores = {k: self.base[k] + int(v) for k, v in zip(('Q', 'O', 'Phi'), (Q, O, Phi))}
            row.update(status='COMPLETE', scores=scores, local_memberships=int(Q),
                shared_attachments=int(shared), path_sites_added=int(added))
            e.m.clock()
            self.stats['completed_trials'] += 1
            return dict(scores=scores, keep=keep, tree=tree, endpoints=endpoints,
                        neighbor_endpoints=neighbor_endpoints, shared=int(shared), added=int(added))
        except Exception as exc:
            row.update(status='INTERRUPTED' if type(exc).__name__ == '_Stop' else 'ERROR', error=repr(exc))
            raise
        finally:
            row['wall'] = perf_counter() - began
            if self.observer is not None:
                self.observer('trial_finished', row)

    def descend(self, refine=True):
        e, record = self.e, self.record
        root = self.route['anchor']
        record.update(status='STARTED', anchor=e.qorder[root], refine_roots=refine)
        scores = {}
        try:
            scores[root] = self.trial(root)['scores']
            record['anchor_scores'] = scores[root]
            while refine:
                e.m.clock()
                neighborhood = dict(root=e.qorder[root], status='STARTED', eligible=[], excluded=[])
                record['neighborhoods'].append(neighborhood)
                choices = []
                for physical in e.adj[e.qorder[root]]:
                    q = e.rank[physical]
                    missing = [v for j, v in enumerate(self.neighbors) if not self.route['settled_mask'][j, q]]
                    e.m.step('union_domain_label', len(self.neighbors))
                    if missing:
                        neighborhood['excluded'].append(dict(root=physical, missing_neighbors=missing))
                        self.stats['excluded_neighbors'] += 1
                        continue
                    neighborhood['eligible'].append(physical)
                    if q not in scores:
                        scores[q] = self.trial(q)['scores']
                    else:
                        record['cached_hits'] += 1
                    if _score_key(scores[q], e.quality) < _score_key(scores[root], e.quality):
                        choices.append(q)
                neighborhood['status'] = 'COMPLETE'
                if not choices:
                    record['stop_reason'] = ('captured_domain_local_optimum' if neighborhood['excluded']
                                             else 'geometric_local_optimum')
                    break
                next_root = min(choices, key=lambda q: (_score_key(scores[q], e.quality), q))
                record['moves'].append(dict(before=e.qorder[root], after=e.qorder[next_root],
                    before_scores=scores[root], after_scores=scores[next_root]))
                self.stats['local_moves'] += 1
                root = next_root
            if not refine:
                record['stop_reason'] = 'fixed_anchor_ablation'
            record.update(selected_root=e.qorder[root], selected_scores=scores[root])
            began = perf_counter()
            try:
                selected = self.trial(root, kind='selected_materialization')
                if selected['scores'] != scores[root]:
                    raise RuntimeError('cached root score differs during materialization')
                with e.m.phase('union_materialization'):
                    chain, tree = set(), {}
                    for q in range(self.n):
                        if selected['keep'][q]:
                            actual = e.qorder[q]; chain.add(actual)
                            p = int(selected['tree'][q])
                            tree[actual] = None if p == -1 else e.qorder[p]
                        e.m.step('union_materialize_site')
                    witnesses = {}
                    for j, v in enumerate(self.neighbors):
                        q = e.qorder[int(selected['endpoints'][j])]
                        p = e.qorder[int(selected['neighbor_endpoints'][j])]
                        witnesses[(self.u, v) if self.u < v else (v, self.u)] = (q, p) if self.u < v else (p, q)
                        e.m.step('union_materialize_witness')
                    selected.update(chain=frozenset(chain), cached_tree=tree, witnesses=witnesses)
                    e.m.clock()
            finally:
                elapsed = perf_counter() - began
                record['materialization_wall'] = elapsed
                self.stats['materialization_wall'] += elapsed
            record.update(status='COMPLETE', materialized=True,
                delta_from_anchor={k: selected['scores'][k] - record['anchor_scores'][k] for k in ('Q','O','Phi')},
                delta_from_entry={k: selected['scores'][k] - record['entry_scores'][k] for k in ('Q','O','Phi')})
            return selected
        except Exception as exc:
            record.update(status='INTERRUPTED' if type(exc).__name__ == '_Stop' else 'ERROR', error=repr(exc))
            if record['neighborhoods'] and record['neighborhoods'][-1]['status'] == 'STARTED':
                record['neighborhoods'][-1].update(status='INCOMPLETE', error=repr(exc))
            raise
