"""Compact quotient construction guided by current distinct adjacency loss."""
from collections import Counter, deque
import hashlib
import math
from pathlib import Path
import random
import time
import types

_path = Path(__file__).with_name('quotient_compact.py')
_raw = _path.read_bytes()
if hashlib.sha256(_raw).hexdigest() != 'ebc65f36d6e0700e28398de1e1f65921e437667d952587f63902855e1891dc91':
    raise ImportError('Unexpected quotient utility source')
_helpers = types.ModuleType('_compact_quotient_helpers')
_helpers.__file__ = str(_path)
exec(compile(_raw,str(_path),'exec'),_helpers.__dict__)
for _name in ('_Expired','_Failed','_Meter','_adjacency','_bfs','_valid','_trim','_coarsen','_assign','_State','_subset','_search'):
    globals()[_name] = getattr(_helpers,_name)


def _loss(links,u,v,meter):
    if len(links[u])>len(links[v]):u,v=v,u
    common=0
    for w in links[u]:
        meter.tick('distinct_loss_neighbor_tests')
        common+=w in links[v]
    return 1+common


def _contract(regions,links,owner,u,v,new_id,meter):
    loss=_loss(links,u,v,meter)
    raw=links[u][v]
    meter.check()
    merged=Counter(links[u]);merged.update(links[v])
    del merged[u];del merged[v]
    group=regions[u]|regions[v]
    cost=len(links[u])+len(links[v])+3*len(merged)+len(group)
    for w in merged:
        links[w].pop(u,None);links[w].pop(v,None)
        links[w][new_id]=merged[w]
    del links[u];del links[v];links[new_id]=merged
    del regions[u];del regions[v];regions[new_id]=group
    for q in group:owner[q]=new_id
    # Finish bookkeeping atomically; the caller records this committed merge
    # before its next cooperative deadline check.
    meter.work['distinct_contraction_records']+=cost;meter.units+=cost
    return loss,raw


def _coarsen(adj,n,rng,meter,diag):
    regions={q:{q} for q in range(len(adj))};owner=list(range(len(adj)))
    links={q:Counter({v:1 for v in neighbors}) for q,neighbors in enumerate(adj)}
    meter.tick('coarsen_initial_adjacency',sum(map(len,adj)))
    next_id=len(adj)
    diag['coarsening_trace']=[]
    edges=sum(map(len,links.values()))//2
    while len(regions)>n:
        meter.check()
        order=sorted(regions);rng.shuffle(order)
        rank={u:i for i,u in enumerate(order)}
        order.sort(key=lambda u:(len(regions[u]),rank[u]))
        unused=set(regions);needed=len(regions)-n
        row=dict(regions_before=len(regions),quotient_edges_before=edges,
                 merges=0,distinct_loss=0,raw_internal_couplers=0,status='running')
        diag['coarsening_trace'].append(row)
        try:
            for u in order:
                meter.tick('coarsen_region_candidates')
                if u not in unused:continue
                unused.remove(u)
                candidates=[v for v in links[u] if v in unused]
                if not candidates:continue
                def score(v):
                    return len(regions[v]),_loss(links,u,v,meter),rank[v]
                v=min(candidates,key=score)
                loss,raw=_contract(regions,links,owner,u,v,next_id,meter)
                unused.remove(v);next_id+=1
                row['merges']+=1;row['distinct_loss']+=loss;row['raw_internal_couplers']+=raw
                edges-=loss;diag['target_contractions']+=1
                if row['merges']==needed:break
            if not row['merges']:raise _Failed('no adjacent target contractions')
            row['status']='complete';diag['coarsening_levels']+=1
        finally:
            row.update(regions_after=len(regions),quotient_edges_after=edges)
            if row['status']=='running':row['status']='interrupted'
    diag['coarsened_quotient_edges']=sum(map(len,links.values()))//2
    assert diag['coarsened_quotient_edges']==edges
    return [regions[v] for v in sorted(regions)]


def distinct_embed(source,target,*,seed=0,timeout=30.0,deadline=None):
    started = time.perf_counter()
    diag = dict(algorithm='distinct_neighbor_quotient_v1', seed=seed, stage='parameters',stage_wall={},
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
                diag['initial_regions_target_ranks']={str(v):sorted(selected[q] for q in region) for v,region in enumerate(regions)}
                diag['initial_quotient_degrees']=[sum(c>0 for c in row) for row in state.count]
                diag['initial_quotient_edges']=sum(diag['initial_quotient_degrees'])//2
                meter.tick('initial_quotient_diagnostic_records',sum(map(len,regions))+len(src)**2)
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
