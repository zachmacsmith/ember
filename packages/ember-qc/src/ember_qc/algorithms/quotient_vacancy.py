"""Compact quotient reconfiguration with constant-size free-site exchanges."""
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
for _name in ('_Expired','_Failed','_Meter','_adjacency','_bfs','_valid','_trim','_coarsen','_assign','_State','_subset'):
    globals()[_name] = getattr(_helpers,_name)


_articulations = _helpers._helpers._articulations
_BaseState = _State


class _State(_BaseState):
    def free_safe(self,u,p,q):
        self.meter.tick('free_release_checks')
        if self.owner[p]!=-1 or self.owner[q]!=u or not any(self.owner[v]==u for v in self.adj[p]):
            return False
        if len(self.regions[u])==1:
            return True
        cached=self.cut_cache.get(u)
        if cached is None or cached[0]!=self.version[u]:
            cached=self.version[u],_articulations(self.regions[u],self.adj,self.meter)
            self.cut_cache[u]=cached
        return q not in cached[1] and any(v!=q and self.owner[v]==u for v in self.adj[p])

    def free_delta(self,u,p,q):
        change=Counter()
        for site,sign in ((q,-1),(p,1)):
            for v in self.adj[site]:
                self.meter.tick('free_score_adjacency')
                w=self.owner[v]
                if w>=0 and w!=u:
                    change[tuple(sorted((u,w)))]+=sign
        change={e:d for e,d in change.items() if d}
        delta=0
        for (a,b),d in change.items():
            assert self.count[a][b]+d>=0
            if (a,b) in self.edges:
                delta+=int(self.count[a][b]+d==0)-int(self.count[a][b]==0)
        return delta,change

    def free_commit(self,u,p,q,change):
        self.meter.check()
        self.regions[u].remove(q);self.regions[u].add(p)
        self.owner[q]=-1;self.owner[p]=u
        for (a,b),d in change.items():
            self.count[a][b]+=d;self.count[b][a]+=d
            if (a,b) in self.edges:self._update_missing((a,b))
        self.version[u]+=1
        cost=len(change)+4
        self.meter.work['free_commit_records']+=cost
        self.meter.units+=cost


def _nearest(state,w,candidates,limit,rng,meter):
    order=sorted(candidates);rng.shuffle(order)
    tie={q:i for i,q in enumerate(order)}
    wanted=set(order)
    if not wanted:return []
    limit=min(limit,len(wanted))
    roots=sorted(state.regions[w]);distance={q:0 for q in roots};queue=deque(roots)
    found=[];cutoff=None
    while queue:
        q=queue.popleft();d=distance[q]
        meter.tick('proposal_bfs_vertices')
        if cutoff is not None and d>cutoff:break
        if q in wanted:
            found.append(q)
            if len(found)>=limit:cutoff=d
        if cutoff is not None:continue
        for v in state.adj[q]:
            meter.tick('proposal_bfs_adjacency')
            if v not in distance:distance[v]=d+1;queue.append(v)
    return sorted(found,key=lambda q:(distance[q],tie[q]))[:limit]


def _frontier(state,u,meter):
    owned,free=set(),set()
    for q in state.regions[u]:
        for p in state.adj[q]:
            meter.tick('frontier_adjacency')
            if state.owner[p]==-1:free.add(p)
            elif state.owner[p]!=u:owned.add(p)
    return owned,free


def _search(state,lower,rng,meter,diag):
    step=0;initial=set(diag['active_target_ranks'])
    diag['initial_missing_edges']=diag['best_missing_edges']=len(state.missing)
    counters=Counter();diag['search_counts']=counters
    while state.missing:
        meter.check()
        u,w=state.missing[rng.randrange(len(state.missing))]
        if rng.randrange(2):u,w=w,u
        best=None
        kind=('swap','transfer','free_exchange')[step%3]
        counters[kind+'_visits']+=1
        if step%3==0:
            candidates=[v for v in range(state.n) if v not in (u,w) and state.count[v][w]>0
                        and len(state.regions[v])>=lower[u] and len(state.regions[u])>=lower[v]]
            rng.shuffle(candidates)
            for v in candidates[:8]:
                delta,affected=state.swap_delta(u,v);counters['swap_scored']+=1
                if best is None or delta<best[0]:best=delta,(v,affected)
        else:
            owned,free=_frontier(state,u,meter)
            if step%3==1:
                eligible=[]
                for q in sorted(owned):
                    counters['transfer_eligibility_checks']+=1
                    if state.movable(q,u,lower):eligible.append(q)
                for q in _nearest(state,w,eligible,16,rng,meter):
                    delta,change=state.transfer_delta(q,u);counters['transfer_scored']+=1
                    if best is None or delta<best[0]:best=delta,(q,change)
            else:
                # Eligibility precedes the distance query, so an unseatable
                # frontier site does not consume a nearest-candidate slot.
                releases={}
                for p in sorted(free):
                    safe=[q for q in sorted(state.regions[u]) if state.free_safe(u,p,q)]
                    if safe:releases[p]=safe
                for p in _nearest(state,w,releases,8,rng,meter):
                    old=releases[p][:];rng.shuffle(old)
                    for q in old[:8]:
                        delta,change=state.free_delta(u,p,q);counters['free_exchange_scored']+=1
                        if best is None or delta<best[0]:best=delta,(p,q,change)
        if best is not None:
            delta,args=best
            if delta<=0 or rng.random()<math.exp(-delta/.5):
                if kind=='swap':state.swap(u,*args)
                elif kind=='transfer':state.transfer(args[0],u,args[1])
                else:
                    state.free_commit(u,*args)
                    counters['free_exchange_entered_outside_initial']+=args[0] not in initial
                counters[kind+'_commits']+=1
                counters['uphill_commits']+=delta>0
            else:counters[kind+'_rejections']+=1
        step+=1;diag['search_visits']=step
        if len(state.missing)<diag['best_missing_edges']:
            diag['best_missing_edges']=len(state.missing)
            diag['improvements'].append([step,len(state.missing)])


def vacancy_embed(source,target,*,seed=0,timeout=30.0,deadline=None):
    started = time.perf_counter()
    diag = dict(algorithm='vacancy_target_quotient_v1', seed=seed, stage='parameters',stage_wall={},
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
                regions=[{selected[q] for q in region} for region in regions]
                adj=full_adj;target_labels=full_target_labels;selected=list(range(len(full_adj)))
                meter.tick('initial_global_region_mapping',sum(map(len,regions)))
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
