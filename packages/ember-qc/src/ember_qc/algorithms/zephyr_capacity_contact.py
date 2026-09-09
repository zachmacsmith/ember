"""C014: connected contact-tree growth with actual remaining-contact capacity.

One partial minor, one coordinated retraction trajectory. Reuse C013's graph,
geometry, domain, routing and validation helpers; never call its constructor.
"""
import importlib.util
import math
from pathlib import Path
import time

_path = Path(__file__).with_name('zephyr_contact_domain.py')
_spec = importlib.util.spec_from_file_location('_c014_contact_support', _path)
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)
_Budget, _Deadline, _InputError = _c._Budget, _c._Deadline, _c._InputError
_State, _Engine, _bits = _c._State, _c._Engine, _c._bits


def _capacities(state):
    result = {}
    for u in state.I:
        state.e.b.tick('capacity_owners')
        result[u] = ((state.boundaries[u] & state.free).bit_count(), len(state.e.G[u]-state.I))
    return result


def _violations(state):
    return {u:r-cap for u,(cap,r) in _capacities(state).items() if cap < r}


def _certify(state):
    state.certify()
    if _violations(state): raise RuntimeError('published state has insufficient contact capacity')
    state.e.b.check()


def _spanning_tree(state, sites):
    e = state.e
    root = min(sites,key=e.trank.__getitem__)
    seen, queue = {root}, [root]
    links = {q:set() for q in sites}
    for q in queue:
        for p in e.adj[q]:
            e.b.tick('recovered_tree_edges')
            if p in sites and p not in seen:
                seen.add(p);queue.append(p);links[q].add(p);links[p].add(q)
    if seen != set(sites): raise RuntimeError('contact sites do not induce a connected graph')
    return links


def _replace(state, v, sites):
    state.e.b.tick('growth_state_copy_records', len(state.owner)+state.Q+len(state.contacts))
    chains = state.chains.copy();chains[v] = frozenset(sites)
    return _State(state.e,chains)


def _boundary_owners(state,v):
    return {state.owner[q] for q in _bits(state.boundaries[v] & ~state.free)
            if state.owner[q] in state.I and state.owner[q] != v}


def _capacity_tree(entry,v,contact_sites,receipt):
    """One greedy capacity extension; all trials private, no positive-gain gate."""
    e = entry.e
    state = entry.add(v,contact_sites)
    links = _spanning_tree(state,contact_sites)
    receipt.update(contact_sites=sorted(contact_sites,key=e.trank.__getitem__), growth=[], pruning=[],
                   blockers=[], status='started')
    blockers = set()
    def fail(reason):
        blockers.update(_boundary_owners(state,v))
        receipt.update(status=reason,blockers=sorted(blockers),final_Q=state.Q,
                       capacities=_capacities(state),attempted_sites=sorted(state.chains[v],key=e.trank.__getitem__))
        return None
    old_violations = {u:d for u,d in _violations(state).items() if u in entry.I}
    if old_violations:
        blockers.update(old_violations)
        receipt['old_violations'] = old_violations
        return fail('old_capacity_violated_by_contact_tree')
    while True:
        e.b.check()
        cap = _capacities(state)
        current, required = cap[v]
        if current >= required: break
        boundary = state.boundaries[v] & state.free
        candidates = e.ordered(boundary)
        best, best_key, chosen, chosen_cap = None,None,None,None
        trial = dict(capacity_before=current,remaining=required,sites_considered=len(candidates),denied=[])
        receipt['growth'].append(trial)
        for q in candidates:
            e.b.tick('growth_site_trials')
            denied = {u for u in entry.I if state.boundaries[u] & (1 << q) and cap[u][0]-1 < cap[u][1]}
            if denied:
                blockers.update(denied);trial['denied'].append(dict(site=q,owners=sorted(denied)));continue
            after_mask = (boundary & ~(1 << q)) | (e.hm[q] & state.free & ~(1 << q))
            after = after_mask.bit_count()
            candidate = _replace(state,v,state.chains[v] | {q})
            observed = (candidate.boundaries[v] & candidate.free).bit_count()
            if observed != after: raise RuntimeError('signed capacity change disagrees with occupancy')
            if _violations(candidate).keys()-{v}: raise RuntimeError('growth damaged an older owner capacity')
            key = (-after,candidate.score(),e.trank[q])
            if best_key is None or key < best_key:
                best,best_key,chosen,chosen_cap = candidate,key,q,after
        if best is None: return fail('no_admissible_capacity_growth')
        anchor = min(state.e.H[chosen] & state.chains[v],key=e.trank.__getitem__)
        links[chosen] = {anchor};links[anchor].add(chosen)
        state = best
        trial.update(claimed=chosen,anchor=anchor,capacity_after=chosen_cap,delta=chosen_cap-current)
    # Recovered tree and subsequent attachment edges persist. A root can be
    # pruned, but capacity support cannot be removed as contact-only redundancy.
    while len(state.chains[v]) > 1:
        removed = False
        for q in sorted(state.chains[v],key=e.trank.__getitem__):
            e.b.tick('capacity_prune_visits')
            if len(links[q]) > 1: continue
            sites = state.chains[v]-{q}
            mask = sum(1 << p for p in sites)
            if any(not state.boundaries[u] & mask for u in e.G[v] & entry.I): continue
            candidate = _replace(state,v,sites)
            if _violations(candidate): continue
            for p in links[q]:links[p].remove(q)
            del links[q];state=candidate;receipt['pruning'].append(q);removed=True;break
        if not removed: break
    if _violations(state): raise RuntimeError('completed birth lacks capacity')
    receipt.update(status='capacity_safe',blockers=sorted(blockers),final_Q=state.Q,
                   capacities=_capacities(state),final_sites=sorted(state.chains[v],key=e.trank.__getitem__))
    return state


def _place(state,v,context='ordinary'):
    e = state.e
    row = dict(kind='capacity_place',context=context,source=v,introduced=len(state.I),
               Q_before=state.Q,roots_generated=0,roots_completed=0,exhaustive=False,
               root_receipts=[],capacity_obstructions=[],best_score=None)
    e.placements.append(row)
    started,cpu = e.b.clock(),time.process_time()
    best,best_score,obstructions = None,None,set()
    try:
        roots,singleton = _c._roots(state,v,state.free)
        row.update(roots_generated=len(roots),singleton_start=singleton)
        if not roots:
            row.update(status='failure',failure_reason='contact_unreachable',exhaustive=True)
            return None
        for root in roots:
            e.b.tick('root_attempts')
            rr=dict(root=root,status='started');row['root_receipts'].append(rr)
            sites = frozenset((root,)) if singleton else _c._tree(state,v,root,state.free)
            if sites is None: raise RuntimeError('qualified contact component did not yield a tree')
            proposal = _capacity_tree(state,v,sites,rr)
            row['roots_completed'] += 1
            if proposal is None:
                obstructions.update(rr['blockers']);continue
            score = proposal.score()
            if best_score is None or score < best_score:
                if len(proposal.I) == e.n:
                    _certify(proposal)
                    if e.complete_score is None or score < e.complete_score:
                        e.complete,e.complete_score,e.complete_from = proposal,score,row
                best,best_score = proposal,score;row['best_score'] = score
        row.update(exhaustive=True,status='success' if best is not None else 'failure',
                   capacity_obstructions=sorted(obstructions))
        if best is None:row['failure_reason']='capacity_exhausted'
        else:row.update(Q_after=best.Q,newly_empty=_c._lost(state,best))
        return best
    except _Deadline:
        row.update(status='interrupted',exhaustive=False,capacity_obstructions=sorted(obstructions));raise
    except Exception as exc:
        row.update(status='error',error=f'{type(exc).__name__}: {exc}');raise
    finally:
        row.update(wall=e.b.clock()-started,cpu=time.process_time()-cpu)


def _retract(entry,K,receipt):
    e = entry.e
    before = _capacities(entry)
    state = _State(e,{u:cc for u,cc in entry.chains.items() if u not in K})
    after = _capacities(state)
    changes = {}
    for u,(new_cap,new_r) in after.items():
        e.b.tick('retraction_capacity_owners')
        removed_neighbors = len(e.G[u] & K)
        if new_r-before[u][1] != removed_neighbors or new_cap-before[u][0] < removed_neighbors:
            raise RuntimeError('retraction incidence/capacity accounting mismatch')
        changes[u] = dict(capacity_before=before[u][0],capacity_after=new_cap,
                          remaining_before=before[u][1],remaining_after=new_r,
                          removed_original_neighbors=removed_neighbors)
    _certify(state)
    receipt['retained_capacity_changes'] = changes
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


def capacity_contact_embed(source,target,*,seed=0,timeout=60.,deadline=None):
    started,cpu=time.perf_counter(),time.process_time()
    response=dict(status='FAILURE',embedding={},diag=dict(algorithm='capacity_contact_domain',policy='C014',
        publications=[],fatal_error=False,work_limit=None,
        restrictions=['individual_fixed_chain_capacity','greedy_capacity_growth','one_greedy_tree_per_root','greedy_private_rebuild']))
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
            state=_State(e);e.published=state
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
                state=e.complete;response['diag']['complete_private_scan_censored']=not e.complete_from['exhaustive']
            response['diag'].update(placements=e.placements,rebuilds=e.rebuilds,published_state=e.published.snapshot())
            try:
                with b.stage('final_validation_output'):
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
