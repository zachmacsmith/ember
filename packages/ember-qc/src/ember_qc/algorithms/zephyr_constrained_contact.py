"""C015: first-admissible contact routing under distinct-site capacity budgets.

One evolving partial minor. C014 supplies state/certification/retraction helpers;
its constructor is never called. No external embedding solver is used.
"""
from collections import Counter
from fractions import Fraction
import heapq
import importlib.util
import math
from pathlib import Path
import time

_path = Path(__file__).with_name('zephyr_capacity_contact.py')
_spec = importlib.util.spec_from_file_location('_c015_capacity_support', _path)
_c14 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_c14)
_c = _c14._c
_Budget, _Deadline, _InputError = _c14._Budget, _c14._Deadline, _c14._InputError
_State, _Engine, _bits = _c14._State, _c14._Engine, _c14._bits
_capacities, _certify = _c14._capacities, _c14._certify


def _qualified(entry, mask, required):
    e = entry.e
    remaining, qualifying = mask, 0
    while remaining:
        start = (remaining & -remaining).bit_length()-1
        members, todo = 1 << start, [start]
        remaining &= ~members
        for q in todo:
            e.b.tick('quota_component_vertices')
            new = e.hm[q] & remaining
            remaining &= ~new; members |= new; todo.extend(_bits(new))
        if all(members & entry.boundaries[u] for u in required):
            qualifying |= members
    return qualifying


def _placement_data(entry, v):
    e = entry.e
    required = e.G[v] & entry.I
    boundaries, allowance = {}, {}
    for u in entry.I:
        e.b.tick('quota_owner_allowances')
        boundaries[u] = entry.boundaries[u] & entry.free
        allowance[u] = boundaries[u].bit_count()-len(e.G[u]-(entry.I | {v}))
        if allowance[u] < 0: raise RuntimeError('placement entry violates an old capacity')
    return dict(required=required, boundaries=boundaries, allowance=allowance,
                new_required=len(e.G[v]-entry.I), permitted=entry.free)


def _roots(entry, v, data, obstructions):
    e = entry.e
    raw = _qualified(entry, entry.free, data['required'])
    if not raw: return [], 'contact_unreachable'
    zero = {u for u, b in data['allowance'].items() if b == 0}
    forbidden = 0
    for u in zero:
        e.b.tick('zero_allowance_boundaries')
        forbidden |= data['boundaries'][u]
    data['permitted'] = entry.free & ~forbidden
    data['zero_owners'] = zero
    allowed = _qualified(entry, data['permitted'], data['required']) if forbidden else raw
    if not allowed:
        obstructions.update(u for u in zero if data['boundaries'][u] & raw)
        return [], 'capacity_exhausted'
    required = data['required']
    if required:
        pivot = min(required, key=lambda u: ((entry.boundaries[u] & allowed).bit_count(), e.srank[u]))
        root_mask = entry.boundaries[pivot] & allowed
    else:
        root_mask = allowed
    roots = []
    for q in _bits(root_mask):
        e.b.tick('constrained_root_order')
        supplied = sum(bool(entry.boundaries[u] & (1 << q)) for u in required)
        deficit = max(0, data['new_required']-(e.hm[q] & entry.free).bit_count())
        roots.append(((-supplied, deficit, e.center[q], e.trank[q]), q))
    roots.sort(); e.b.check()
    return [q for _, q in roots], None


def _score_sites(entry, v, mask, boundary):
    """The unchanged C013 score, evaluated without constructing a trial State."""
    e = entry.e
    free = entry.free & ~mask
    sizes = []
    for u in e.sorder:
        e.b.tick('hypothetical_domain_scores')
        if u not in entry.domains or u == v: continue
        domain = entry.domains[u] & free
        if u in e.G[v]: domain &= boundary
        sizes.append(domain.bit_count())
    zero = sizes.count(0)
    sites = tuple(_bits(mask))
    key = tuple((e.srank[u], tuple(sorted(e.trank[q] for q in sites)) if u == v else entry.keys[u])
                for u in e.sorder if u in entry.I or u == v)
    return (entry.Q+len(sites)+len(sizes)+zero, zero,
            -math.fsum(math.log1p(n) for n in sizes),
            entry.geom+sum(e.center[q] for q in sites), key)


class _Scratch:
    def __init__(self, entry, v, root, data):
        self.entry, self.v, self.data = entry, v, data
        self.sites, self.mask, self.boundary = {root}, 1 << root, entry.e.hm[root]
        self.used = {u: int(bool(b & self.mask)) for u, b in data['boundaries'].items()}
        if any(self.used[u] > data['allowance'][u] for u in self.used):
            raise RuntimeError('ordered root violates an old allowance')
        self.links = {root: set()}

    def frontier(self):
        return self.boundary & self.entry.free & ~self.mask

    def denied(self, q):
        bit = 1 << q
        return {u for u, b in self.data['boundaries'].items()
                if b & bit and self.used[u]+1 > self.data['allowance'][u]}

    def add(self, q):
        e = self.entry.e
        e.b.tick('scratch_site_additions')
        if not self.frontier() & (1 << q) or self.denied(q):
            raise RuntimeError('inadmissible scratch extension')
        anchor = min(e.H[q] & self.sites, key=e.trank.__getitem__)
        self.links[q] = {anchor}; self.links[anchor].add(q)
        self.sites.add(q); self.mask |= 1 << q; self.boundary |= e.hm[q]
        for u, b in self.data['boundaries'].items():
            self.used[u] += int(bool(b & (1 << q)))

    def recover_tree(self):
        e = self.entry.e
        root = min(self.sites, key=e.trank.__getitem__)
        seen, todo = {root}, [root]
        links = {q: set() for q in self.sites}
        for q in todo:
            for p in e.adj[q]:
                e.b.tick('scratch_tree_edges')
                if p in self.sites and p not in seen:
                    seen.add(p); todo.append(p); links[q].add(p); links[p].add(q)
        if seen != self.sites: raise RuntimeError('scratch contact tree disconnected')
        self.links = links


def _path_to_contact(scratch, missing, obstructions, counts):
    e, data = scratch.entry.e, scratch.data
    owners = sorted(data['allowance'])
    remaining = {u: data['allowance'][u]-scratch.used[u] for u in owners}
    goals = 0
    for u in missing: goals |= data['boundaries'][u]
    goals &= data['permitted']
    labels, heap = {}, []
    for q in sorted(scratch.sites, key=e.trank.__getitem__):
        e.b.tick('path_initial_labels')
        cost = (0, Fraction(0), ())
        labels[q] = (cost, (), (0,)*len(owners))
        heapq.heappush(heap, (cost, e.trank[q], q))
    while heap:
        e.b.tick('path_label_pops')
        cost, _, q = heapq.heappop(heap)
        if labels[q][0] != cost:
            counts['stale_labels'] += 1; continue
        _, sites, consumed = labels[q]
        if goals & (1 << q): return sites
        for p in e.adj[q]:
            e.b.tick('path_edge_visits'); counts['path_edges'] += 1
            bit = 1 << p
            if not scratch.entry.free & bit or p in scratch.sites or p in sites: continue
            denied = {u for i, u in enumerate(owners)
                      if consumed[i]+int(bool(data['boundaries'][u] & bit)) > remaining[u]}
            if denied:
                obstructions.update(denied); counts['quota_denials'] += 1; continue
            uses = tuple(consumed[i]+int(bool(data['boundaries'][u] & bit)) for i, u in enumerate(owners))
            path = sites+(p,)
            pressure = sum((Fraction(uses[i], remaining[u]) for i, u in enumerate(owners)
                            if remaining[u] > 0), Fraction(0))
            key = (len(path), pressure, tuple(e.trank[t] for t in path))
            if p in labels and labels[p][0] <= key:
                counts['single_label_discards'] += 1; continue
            labels[p] = (key, path, uses)
            heapq.heappush(heap, (key, e.trank[p], p)); counts['accepted_path_labels'] += 1
    return None


def _grow_prune(scratch, obstructions, counts):
    e = scratch.entry.e
    scratch.recover_tree()
    while scratch.frontier().bit_count() < scratch.data['new_required']:
        e.b.check()
        best, chosen = None, None
        for q in _bits(scratch.frontier()):
            e.b.tick('growth_site_trials'); counts['growth_site_trials'] += 1
            denied = scratch.denied(q)
            if denied:
                obstructions.update(denied); counts['growth_quota_denials'] += 1; continue
            mask, boundary = scratch.mask | (1 << q), scratch.boundary | e.hm[q]
            after = (boundary & scratch.entry.free & ~mask).bit_count()
            if best is not None and -after > best[0]: continue
            score = _score_sites(scratch.entry, scratch.v, mask, boundary)
            key = (-after, score, e.trank[q])
            if best is None or key < best: best, chosen = key, q
        if chosen is None:
            occupied = scratch.boundary & ~scratch.entry.free
            obstructions.update(scratch.entry.owner[q] for q in _bits(occupied)
                                if scratch.entry.owner[q] in scratch.entry.I)
            return False
        before = scratch.frontier().bit_count()
        scratch.add(chosen)
        counts['growth_claims'] += 1
        if scratch.frontier().bit_count() <= before: counts['nonpositive_growth_claims'] += 1
    while len(scratch.sites) > 1:
        removed = False
        for q in sorted(scratch.sites, key=e.trank.__getitem__):
            e.b.tick('scratch_prune_visits')
            if len(scratch.links[q]) > 1: continue
            mask = scratch.mask & ~(1 << q)
            if any(not mask & scratch.entry.boundaries[u] for u in scratch.data['required']): continue
            boundary = 0
            for p in _bits(mask):
                e.b.tick('pruned_boundary_sites'); boundary |= e.hm[p]
            if (boundary & scratch.entry.free & ~mask).bit_count() < scratch.data['new_required']: continue
            for p in scratch.links[q]: scratch.links[p].remove(q)
            del scratch.links[q]; scratch.sites.remove(q); scratch.mask = mask; scratch.boundary = boundary
            for u, b in scratch.data['boundaries'].items(): scratch.used[u] -= int(bool(b & (1 << q)))
            counts['pruned_sites'] += 1; removed = True; break
        if not removed: break
    return True


def _materialize(scratch):
    entry, e = scratch.entry, scratch.entry.e
    e.b.tick('completed_root_states')
    result = entry.add(scratch.v, scratch.sites)
    _certify(result)
    observed = _capacities(result)
    for u, boundary in scratch.data['boundaries'].items():
        if observed[u] != (boundary.bit_count()-scratch.used[u], len(e.G[u]-result.I)):
            raise RuntimeError('scratch old capacity mismatch')
    if observed[scratch.v] != (scratch.frontier().bit_count(), scratch.data['new_required']):
        raise RuntimeError('scratch new capacity mismatch')
    score = result.score()
    if score != _score_sites(entry, scratch.v, scratch.mask, scratch.boundary):
        raise RuntimeError('hypothetical score differs from materialized state')
    e.b.check()
    return result, score


def _place(entry, v, context='ordinary'):
    e = entry.e
    e.active_entry, e.active_source = entry, v
    row = dict(kind='constrained_place', context=context, source=v, introduced=len(entry.I),
               Q_before=entry.Q, roots_generated=0, roots_completed=0, roots_started=0,
               exhaustive=False, status='started', counts=Counter(), root_statuses=Counter(),
               capacity_obstructions=[])
    e.placements.append(row)
    started, cpu = e.b.clock(), time.process_time()
    obstructions = set()
    try:
        data = _placement_data(entry, v)
        roots, failure = _roots(entry, v, data, obstructions)
        row['roots_generated'] = len(roots)
        if failure:
            row.update(status='failure', failure_reason=failure, exhaustive=True)
            return None
        for root in roots:
            e.b.tick('constrained_root_attempts'); row['roots_started'] += 1
            scratch = _Scratch(entry, v, root, data)
            while True:
                e.b.check()
                missing = {u for u in data['required'] if not scratch.mask & entry.boundaries[u]}
                if not missing: break
                extension = _path_to_contact(scratch, missing, obstructions, row['counts'])
                if extension is None: break
                for q in extension: scratch.add(q)
            if missing:
                row['root_statuses']['path_policy_exhausted'] += 1
                row['roots_completed'] += 1; continue
            if not _grow_prune(scratch, obstructions, row['counts']):
                row['root_statuses']['new_capacity_unreached'] += 1
                row['roots_completed'] += 1; continue
            proposal, score = _materialize(scratch)
            row['roots_completed'] += 1; row['root_statuses']['admissible'] += 1
            row.update(status='success', accepted_root=root,
                       accepted_sites=sorted(scratch.sites, key=e.trank.__getitem__),
                       Q_after=proposal.Q, score_prefix=score[:4],
                       newly_empty=_c._lost(entry, proposal), first_admissible=True)
            if len(proposal.I) == e.n:
                if e.complete_score is None or score < e.complete_score:
                    e.complete, e.complete_score, e.complete_from = proposal, score, row
            return proposal
        row.update(status='failure', failure_reason='capacity_exhausted', exhaustive=True)
        return None
    except _Deadline:
        row.update(status='interrupted', exhaustive=False); raise
    except Exception as exc:
        row.update(status='error', error=f'{type(exc).__name__}: {exc}'); raise
    finally:
        row.update(capacity_obstructions=sorted(obstructions),
                   wall=e.b.clock()-started, cpu=time.process_time()-cpu)


def _retract(entry, K, receipt):
    temporary = {}
    state = _c14._retract(entry, K, temporary)
    changes = temporary['retained_capacity_changes']
    receipt['retained_capacity_check'] = dict(owners=len(changes),
        removed_neighbor_incidences=sum(c['removed_original_neighbors'] for c in changes.values()),
        released_boundary_sites=sum(c['capacity_after']-c['capacity_before'] for c in changes.values()))
    return state


def _transaction(entry,v,ordinary,row,ordinary_failure=None):
    e = entry.e
    if ordinary is not None:
        lost = _c._lost(entry,ordinary)
        w = min(lost,key=lambda u:(entry.domains[u].bit_count(),e.srank[u]))
        K = (e.G[v] | e.G[w]) & entry.I
        K |= {entry.owner[q] for q in _bits(ordinary.E(w)) if entry.owner[q] in entry.I}
        row['threatened'] = w
    else:
        K = e.G[v] & entry.I
        K |= {entry.owner[q] for q in _bits(entry.E(v)) if entry.owner[q] in entry.I}
        K |= set((ordinary_failure or {}).get('capacity_obstructions',())) & entry.I
    row.update(initial_K=sorted(K),attempts=[])
    while True:
        e.b.check();attempt=dict(K=sorted(K),reintroduced=[],status='started');row['attempts'].append(attempt)
        private = _retract(entry,K,attempt)
        todo,x = K | {v},v
        while todo:
            candidate = _place(private,x,'rebuild')
            if candidate is None:break
            private=candidate;todo.remove(x);attempt['reintroduced'].append(x)
            if todo:x=e.next(private,todo)
        if not todo:
            _certify(private)
            if private.I != entry.I | {v}:raise RuntimeError('rebuild introduced-set mismatch')
            score = private.score()
            chosen = private if ordinary is None or score < ordinary.score() else ordinary
            attempt.update(status='complete',Q=private.Q,score=score)
            row.update(status='rebuilt' if chosen is private else 'ordinary_preferred',rebuilt_score=score)
            return chosen
        failure = e.placements[-1]
        if not failure['exhaustive']:raise RuntimeError('censored PLACE treated as failure')
        reason = failure['failure_reason'];outside=entry.I-K
        attempt.update(status='placement_failed',failed_source=x,failure_reason=reason)
        if reason == 'capacity_exhausted':
            added = set(failure['capacity_obstructions']) & outside
            if not added:
                row['status']='rebuild_failed_capacity_no_outside';return ordinary
            attempt['expansion_reason']='recorded_capacity_obstruction'
        elif reason == 'contact_unreachable':
            if not outside:
                row['status']='rebuild_failed_contact_no_outside';return ordinary
            guide = _c._place(private,x,outside=outside,context='contact_obstruction_only')
            if guide is None:
                row['status']='rebuild_failed_no_contact_guide';return ordinary
            added = {private.owner[q] for q in guide if private.owner[q] in outside}
            if not added:raise RuntimeError('zero-owner guide after exhaustive contact-unreachable failure')
            attempt.update(expansion_reason='contact_guide',guide_sites=sorted(guide,key=e.trank.__getitem__))
        else:raise RuntimeError('unknown PLACE failure')
        if added & K or not added:raise RuntimeError('obstruction set did not grow')
        attempt['expanded_by']=sorted(added);K |= added


def _run(state,diag):
    e=state.e
    while len(state.I)<e.n:
        e.b.check();v=e.next(state)
        row=dict(source=v,introduced_before=len(state.I),Q_before=state.Q,status='started',
                 domains_before={u:d.bit_count() for u,d in state.domains.items()},capacities_before=_capacities(state))
        diag['publications'].append(row)
        with e.b.stage('ordinary'):
            ordinary=_place(state,v)
        failure=e.placements[-1] if ordinary is None else None
        row.update(ordinary_score=ordinary.score() if ordinary is not None else None,
                   newly_empty=_c._lost(state,ordinary) if ordinary is not None else [])
        if ordinary is not None and not row['newly_empty']:
            chosen=ordinary;row['status']='ordinary'
        else:
            transaction=dict(source=v,status='started');e.rebuilds.append(transaction)
            try:
                with e.b.stage('retraction'):
                    chosen=_transaction(state,v,ordinary,transaction,failure)
            except _Deadline:transaction['status']='interrupted';raise
            row['status']=transaction['status']
        if chosen is None:return state,'construction_obstructed'
        with e.b.stage('publication_certificate'):
            _certify(chosen);score=chosen.score()
            domains={u:d.bit_count() for u,d in chosen.domains.items()};caps=_capacities(chosen);e.b.check()
        if chosen.I != state.I | {v}:raise RuntimeError('publication is not net one source vertex')
        state=chosen;e.published=state
        row.update(published=True,introduced_after=len(state.I),Q_after=state.Q,score=score,
                   domains_after=domains,capacities_after=caps)
    return state,'complete_introduced_source'


def constrained_contact_embed(source,target,*,seed=0,timeout=60.,deadline=None):
    started,cpu=time.perf_counter(),time.process_time()
    response=dict(status='FAILURE',embedding={},diag=dict(algorithm='constrained_contact_domain',policy='C015',
        publications=[],fatal_error=False,work_limit=None,
        restrictions=['individual_fixed_chain_capacity','first_admissible_root','single_path_label','greedy_capacity_growth','greedy_private_rebuild']))
    e,state,b,absolute=None,None,None,None
    try:
        if type(seed) is not int or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
            raise _InputError('integer seed and positive finite timeout required')
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise _InputError('finite deadline required')
        absolute=min(started+timeout,deadline) if deadline is not None else started+timeout
        reserve=min(.5,timeout/10);b=_Budget(absolute-reserve)
        response['diag'].update(deadline=absolute,search_deadline=b.deadline,final_reserve=reserve)
        with b.stage('input_geometry'):
            sl,src=_c._graph(source,b);tl,adj=_c._graph(target,b)
            if len(src)>len(adj):raise _InputError('source vertex count exceeds target count')
            m,coords=_c._geometry(target,tl,adj,b);e=_Engine(src,adj,coords,m,seed,b)
            state=_State(e);e.published=state;e.active_entry=state;e.active_source=None
            response['diag'].update(source_ranks=e.srank,target_ranks=e.trank,initial=state.snapshot())
        _,response['diag']['stop_reason']=_run(state,response['diag'])
    except _Deadline as exc:
        response['diag'].update(stop_reason='search_deadline',interrupted_stage=str(exc))
    except Exception as exc:
        expected=isinstance(exc,_InputError)
        response.update(status='FAILURE' if expected else 'ERROR',error=f'{type(exc).__name__}: {exc}')
        response['diag'].update(fatal_error=not expected,exception=dict(type=type(exc).__name__,message=str(exc)))
    if b is not None:
        b.deadline=absolute
        if e is not None and state is not None:
            state=e.published
            if e.complete is not None and not response.get('error'):
                state=e.complete;response['diag']['complete_private_first_admissible']=True
            response['diag'].update(placements=e.placements,rebuilds=e.rebuilds,published_state=e.published.snapshot())
            try:
                with b.stage('final_validation_output'):
                    b.tick('terminal_prefix_records',e.active_entry.Q+len(e.active_entry.I))
                    response['diag']['terminal_private_entry']=e.active_entry.snapshot()
                    response['diag']['terminal_private_source']=e.active_source
                    _certify(state);_c._final(state,source,target,sl,tl,response)
            except _Deadline:
                response['embedding']={};response['diag']['final_stop']='deadline'
            except Exception as exc:
                response.update(status='ERROR',embedding={},error=f'{type(exc).__name__}: {exc}')
                response['diag']['fatal_error']=True
        response['diag'].update(work=dict(b.work),total_work=sum(b.work.values()),
                                stage_wall=dict(b.stage_wall),stage_cpu=dict(b.stage_cpu))
    finished=time.perf_counter();response['time']=finished-started
    response['diag'].update(wall=finished-started,cpu=time.process_time()-cpu,finished=finished)
    if absolute is not None and finished>=absolute:
        response['embedding']={}
        if not response['diag']['fatal_error']:response['status']='TIMEOUT'
    return response
