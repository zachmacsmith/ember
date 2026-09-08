"""One bounded connected target allocation, followed by quotient reconfiguration."""
from collections import deque
import hashlib
import math
from pathlib import Path
import random
import time
import types

_path = Path(__file__).with_name('quotient_reconfiguration.py')
_raw = _path.read_bytes()
if hashlib.sha256(_raw).hexdigest() != '4fc12515fb088be951e8270dad0bc06d64b49a1b9db86037d4592776c507fec1':
    raise ImportError('Unexpected quotient utility source')
_helpers = types.ModuleType('_compact_quotient_helpers')
_helpers.__file__ = str(_path)
exec(compile(_raw,str(_path),'exec'),_helpers.__dict__)
for _name in ('_Expired','_Failed','_Meter','_adjacency','_bfs','_valid','_trim','_coarsen','_assign','_State','_search'):
    globals()[_name] = getattr(_helpers,_name)


def _subset(adj,n,lower,rng,meter,diag):
    remaining,largest = set(range(len(adj))),set()
    while remaining:
        component = set(_bfs(remaining,adj,[min(remaining)],meter))
        remaining -= component
        if len(component)>len(largest):
            largest = component
    if len(largest)<n:
        raise _Failed('largest target component too small')
    budget = min(len(largest),4*sum(lower))
    first = _bfs(largest,adj,[min(largest)],meter)
    a = max(first,key=lambda q:(first[q],-q))
    second = _bfs(largest,adj,[a],meter)
    b = max(second,key=lambda q:(second[q],-q))
    center = b
    for _ in range(second[b]//2):
        meter.tick('center_path_vertices')
        center = min(p for p in adj[center] if p in second and second[p]==second[center]-1)
    selected,seen,queue = [center],{center},deque([center])
    while len(selected)<budget:
        meter.check()
        q = queue.popleft()
        neighbors = [p for p in adj[q] if p in largest and p not in seen]
        rng.shuffle(neighbors)
        meter.tick('subset_adjacency',len(adj[q]))
        for p in neighbors:
            if p in seen:
                continue
            selected.append(p);seen.add(p);queue.append(p)
            if len(selected)==budget:
                break
    selected.sort()
    rank = {q:i for i,q in enumerate(selected)}
    restricted = []
    for q in selected:
        restricted.append(tuple(sorted(rank[p] for p in adj[q] if p in rank)))
        meter.tick('induced_target_adjacency',len(adj[q]))
    diag.update(active_target_nodes=len(selected),target_budget=budget,target_center_rank=center,
                active_target_ranks=selected,largest_target_component=len(largest))
    return selected,restricted


def compact_embed(source,target,*,seed=0,timeout=30.0,deadline=None):
    started = time.perf_counter()
    diag = dict(algorithm='compact_target_quotient_v1', seed=seed, stage='parameters',stage_wall={},
                coarsening_levels=0,target_contractions=0,improvements=[],search_visits=0,
                trimming=[],trim_deletions=0,source_label_order='supplied node iteration; diagnostic IDs are ranks')
    response = {'embedding':{},'status':'FAILURE','diag':diag}
    meter,state = None,None
    source_labels,target_labels,chains = [],[],{}
    selected,full_adj = [],[]
    try:
        if type(seed) is not int or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
            raise ValueError('ordinary integer seed and finite positive timeout required')
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise ValueError('finite absolute deadline required')
        deadline = min(deadline,started+timeout) if deadline is not None else started+timeout
        reserve = min(.5,timeout*.1)
        diag.update(deadline=deadline,validation_reserve=reserve)
        meter = _Meter(deadline-reserve,diag)
        rng = random.Random(seed)
        with meter.stage('input'):
            source_labels,src = _adjacency(source,meter)
            full_target_labels,full_adj = _adjacency(target,meter)
            adj = full_adj
            delta = max(map(len,adj),default=0)
            lower = [max(1,(len(row)+delta-5)//(delta-2)) if delta>2 else 1 for row in src]
            if sum(lower)>len(adj):
                raise _Failed('necessary source degree/vertex capacity bound')
            diag.update(source_nodes=len(src),target_nodes=len(adj),degree_lower_bound=sum(lower))
        if src:
            with meter.stage('target_allocation'):
                selected,adj = _subset(full_adj,len(src),lower,rng,meter,diag)
                target_labels = [full_target_labels[q] for q in selected]
            with meter.stage('target_coarsening'):
                regions = _coarsen(adj,len(src),rng,meter,diag)
            with meter.stage('source_assignment'):
                regions = _assign(regions,src,adj,lower,rng,meter)
                state = _State(regions,src,adj,meter)
            with meter.stage('global_reconfiguration'):
                _search(state,lower,rng,meter,diag)
            chains = dict(enumerate(state.regions))
            with meter.stage('entry_validation'):
                original_chains = {v:{selected[q] for q in chain} for v,chain in chains.items()}
                if not _valid(original_chains,src,full_adj,meter):
                    raise AssertionError('quotient missing-edge bookkeeping disagrees with original minor')
                diag['entry_qubits'] = sum(map(len,chains.values()))
            try:
                with meter.stage('trimming'):
                    _trim(chains,src,adj,meter,diag)
                diag['trimming_stop'] = 'complete'
            except _Expired:
                diag['trimming_stop'] = 'validation_reserve'
        meter.deadline = deadline
        with meter.stage('final_validation'):
            original_chains = {v:{selected[q] for q in chain} for v,chain in chains.items()}
            if not _valid(original_chains,src,full_adj,meter):
                raise AssertionError('invalid final minor')
            response['embedding'] = {source_labels[v]:[target_labels[q] for q in sorted(chains[v])] for v in range(len(src))}
            meter.check()
        response['status'] = 'SUCCESS'
    except _Expired:
        response['status'] = 'TIMEOUT'
        response['error'] = 'construction or final-validation allowance exhausted'
    except _Failed as exc:
        response['error'] = str(exc)
    except Exception as exc:
        response['status'] = 'ERROR'
        response['error'] = type(exc).__name__+': '+str(exc)
    if state is not None:
        diag['last_missing_edges'] = len(state.missing)
        if response['status']!='SUCCESS':
            response['partial_embedding'] = {str(source_labels[v]):[target_labels[q] for q in sorted(state.regions[v])] for v in range(state.n)}
    diag['work'] = dict(meter.work) if meter else {}
    diag['wall'] = time.perf_counter()-started
    diag['deadline_overrun'] = max(0.,time.perf_counter()-deadline) if meter else 0.
    if meter and time.perf_counter()>=deadline:
        response['status'] = 'TIMEOUT'
    return response
