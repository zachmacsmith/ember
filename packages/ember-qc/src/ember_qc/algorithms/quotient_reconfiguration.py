"""Experimental connected target contraction and global quotient reconfiguration."""
from collections import Counter
import hashlib
import math
from pathlib import Path
import random
import time
import types

_path = Path(__file__).with_name('multilevel_regions.py')
_raw = _path.read_bytes()
if hashlib.sha256(_raw).hexdigest() != '1f8d947b232ef458e4d908f138bce8d5d1a9b00d5cb4b983929f7feb5759d973':
    raise ImportError('Unexpected structural helper source')
_helpers = types.ModuleType('_quotient_structural_helpers')
exec(compile(_raw, str(_path), 'exec'), _helpers.__dict__)
for _name in ('_Expired', '_Failed', '_Meter', '_adjacency', '_bfs', '_connected', '_articulations', '_valid', '_trim'):
    globals()[_name] = getattr(_helpers, _name)


def _coarsen(adj, n, rng, meter, diag):
    remaining, largest = set(range(len(adj))), set()
    while remaining:
        component = set(_bfs(remaining, adj, [min(remaining)], meter))
        remaining -= component
        if len(component) > len(largest):
            largest = component
    if len(largest) < n:
        raise _Failed('largest target component too small')
    regions = {q:{q} for q in largest}
    owner = list(range(len(adj)))
    next_id = len(adj)
    while len(regions) > n:
        meter.check()
        links = {u:Counter() for u in regions}
        for q in largest:
            for p in adj[q]:
                meter.tick('coarsen_target_adjacency')
                u,v = owner[q],owner[p]
                if q < p and u != v:
                    links[u][v] += 1
                    links[v][u] += 1
        order = sorted(regions)
        rng.shuffle(order)
        rank = {u:i for i,u in enumerate(order)}
        order.sort(key=lambda u:(len(regions[u]),rank[u]))
        unused = set(regions)
        selected = []
        needed = len(regions)-n
        for u in order:
            meter.tick('coarsen_region_candidates')
            if u not in unused:
                continue
            unused.remove(u)
            candidates = [v for v in links[u] if v in unused]
            if not candidates:
                continue
            v = min(candidates,key=lambda v:(len(regions[v]),links[u][v],rank[v]))
            unused.remove(v)
            selected.append((u,v))
            if len(selected) == needed:
                break
        if not selected:
            raise _Failed('no adjacent target contractions')
        for u,v in selected:
            group = regions.pop(u) | regions.pop(v)
            regions[next_id] = group
            for q in group:
                owner[q] = next_id
            meter.tick('coarsen_owner_updates',len(group))
            next_id += 1
        diag['coarsening_levels'] += 1
        diag['target_contractions'] += len(selected)
    return [regions[v] for v in sorted(regions)]


class _State:
    def __init__(self, regions, src, adj, meter):
        self.regions = regions
        self.src, self.adj, self.meter = src,adj,meter
        self.n = len(src)
        self.edges = {tuple(sorted((u,v))) for u,neighbors in enumerate(src) for v in neighbors}
        self.owner = [-1]*len(adj)
        for u,region in enumerate(regions):
            for q in region:
                self.owner[q] = u
        self.count = [[0]*self.n for _ in src]
        for q,u in enumerate(self.owner):
            if u < 0:
                continue
            for p in adj[q]:
                meter.tick('initial_count_adjacency')
                v = self.owner[p]
                if p>q and v>=0 and u!=v:
                    self.count[u][v] += 1
                    self.count[v][u] += 1
        self.version = [0]*self.n
        self.cut_cache, self.distance_cache = {},{}
        self.missing, self.position = [],{}
        for edge in sorted(self.edges):
            self._update_missing(edge)

    def _update_missing(self, edge):
        a,b = edge
        absent = self.count[a][b] == 0
        exists = edge in self.position
        if absent and not exists:
            self.position[edge] = len(self.missing)
            self.missing.append(edge)
        elif not absent and exists:
            index = self.position.pop(edge)
            last = self.missing.pop()
            if index < len(self.missing):
                self.missing[index] = last
                self.position[last] = index

    def affected_source(self,u,v):
        return {tuple(sorted((a,b))) for a in (u,v) for b in self.src[a]}

    def swap_delta(self,u,v):
        affected = self.affected_source(u,v)
        def old_owner(w):
            return v if w==u else u if w==v else w
        delta = 0
        for a,b in affected:
            self.meter.tick('swap_score_source_edges')
            delta += int(self.count[old_owner(a)][old_owner(b)]==0)-int(self.count[a][b]==0)
        return delta,affected

    def swap(self,u,v,affected):
        self.meter.check()
        self.regions[u],self.regions[v] = self.regions[v],self.regions[u]
        for w in (u,v):
            for q in self.regions[w]:
                self.owner[q] = w
            self.version[w] += 1
        self.count[u],self.count[v] = self.count[v],self.count[u]
        for row in self.count:
            row[u],row[v] = row[v],row[u]
        for edge in sorted(affected):
            self._update_missing(edge)
        # Finish accounting before the caller's post-commit deadline check.
        # An interruption must not hide an already committed move.
        cost = self.n+len(self.regions[u])+len(self.regions[v])+len(affected)
        self.meter.work['swap_commit_records'] += cost
        self.meter.units += cost

    def movable(self,q,v,lower):
        u = self.owner[q]
        if u < 0 or u==v or len(self.regions[u]) <= lower[u]:
            return False
        if not any(self.owner[p]==v for p in self.adj[q]):
            return False
        cached = self.cut_cache.get(u)
        if cached is None or cached[0] != self.version[u]:
            cached = self.version[u],_articulations(self.regions[u],self.adj,self.meter)
            self.cut_cache[u] = cached
        return q not in cached[1]

    def transfer_delta(self,q,v):
        u = self.owner[q]
        change = Counter()
        for p in self.adj[q]:
            self.meter.tick('transfer_score_adjacency')
            w = self.owner[p]
            if w < 0:
                continue
            if w!=u:
                change[tuple(sorted((u,w)))] -= 1
            if w!=v:
                change[tuple(sorted((v,w)))] += 1
        change = {edge:d for edge,d in change.items() if d}
        delta = 0
        for (a,b),d in change.items():
            assert self.count[a][b]+d >= 0
            if (a,b) in self.edges:
                delta += int(self.count[a][b]+d==0)-int(self.count[a][b]==0)
        return delta,change

    def transfer(self,q,v,change):
        self.meter.check()
        u = self.owner[q]
        self.regions[u].remove(q)
        self.regions[v].add(q)
        self.owner[q] = v
        for (a,b),d in change.items():
            self.count[a][b] += d
            self.count[b][a] += d
        for edge in sorted(change):
            if edge in self.edges:
                self._update_missing(edge)
        self.version[u] += 1
        self.version[v] += 1
        self.meter.work['transfer_commit_records'] += len(change)+3
        self.meter.units += len(change)+3

    def distance(self,w):
        cached = self.distance_cache.get(w)
        if cached is None or cached[0] != self.version[w]:
            occupied = {q for q,u in enumerate(self.owner) if u>=0}
            self.meter.tick('distance_region_records',len(self.owner))
            cached = self.version[w],_bfs(occupied,self.adj,sorted(self.regions[w]),self.meter)
            self.distance_cache[w] = cached
        return cached[1]


def _assign(regions,src,adj,lower,rng,meter):
    # This temporary quotient uses region IDs only; no candidate embedding call.
    empty = [tuple() for _ in src]
    quotient = _State(regions,empty,adj,meter)
    available = set(range(len(src)))
    assignment = {}
    source_rank = list(range(len(src)))
    rng.shuffle(source_rank)
    rank = {u:i for i,u in enumerate(source_rank)}
    while available:
        u = min((u for u in range(len(src)) if u not in assignment),
                key=lambda u:(-sum(v in assignment for v in src[u]),-len(src[u]),rank[u]))
        candidates = [a for a in available if len(regions[a])>=lower[u]]
        if not candidates:
            raise _Failed('initial regions do not meet source degree capacities')
        order = sorted(candidates)
        rng.shuffle(order)
        local_rank = {a:i for i,a in enumerate(order)}
        def score(a):
            meter.tick('assignment_candidates')
            represented = sum(quotient.count[a][assignment[v]]>0 for v in src[u] if v in assignment)
            future = sum(quotient.count[a][b]>0 for b in available if b!=a)
            return (-represented,-future,local_rank[a])
        a = min(candidates,key=score)
        assignment[u] = a
        available.remove(a)
    return [regions[assignment[u]] for u in range(len(src))]


def _search(state,lower,rng,meter,diag):
    step = 0
    diag['initial_missing_edges'] = len(state.missing)
    diag['best_missing_edges'] = len(state.missing)
    counters = Counter()
    diag['search_counts'] = counters
    while state.missing:
        meter.check()
        u,w = state.missing[rng.randrange(len(state.missing))]
        if rng.randrange(2):
            u,w = w,u
        if step%2 == 0:
            counters['swap_visits'] += 1
            candidates = [v for v in range(state.n) if v not in (u,w) and state.count[v][w]>0
                          and len(state.regions[v])>=lower[u] and len(state.regions[u])>=lower[v]]
            rng.shuffle(candidates)
            best = None
            for v in candidates[:8]:
                delta,affected = state.swap_delta(u,v)
                counters['swap_scored'] += 1
                if best is None or delta<best[0]:
                    best = delta,v,affected
            if best is not None:
                delta,v,affected = best
                if delta<=0 or rng.random()<math.exp(-delta/.5):
                    state.swap(u,v,affected)
                    counters['swap_commits'] += 1
                    counters['uphill_commits'] += delta>0
                else:
                    counters['swap_rejections'] += 1
        else:
            counters['transfer_visits'] += 1
            distance = state.distance(w)
            frontier = set()
            for q in state.regions[u]:
                for p in state.adj[q]:
                    meter.tick('frontier_adjacency')
                    if state.owner[p] not in (-1,u):
                        frontier.add(p)
            ordered = list(sorted(frontier))
            rng.shuffle(ordered)
            order = {q:i for i,q in enumerate(ordered)}
            ordered.sort(key=lambda q:(distance[q],order[q]))
            best,scored = None,0
            for q in ordered:
                counters['transfer_eligibility_checks'] += 1
                if not state.movable(q,u,lower):
                    continue
                delta,change = state.transfer_delta(q,u)
                counters['transfer_scored'] += 1
                key = delta,distance[q],order[q]
                if best is None or key<best[0]:
                    best = key,q,change
                scored += 1
                if scored==16:
                    break
            if best is not None:
                key,q,change = best
                delta = key[0]
                if delta<=0 or rng.random()<math.exp(-delta/.5):
                    state.transfer(q,u,change)
                    counters['transfer_commits'] += 1
                    counters['uphill_commits'] += delta>0
                else:
                    counters['transfer_rejections'] += 1
        step += 1
        diag['search_visits'] = step
        if len(state.missing)<diag['best_missing_edges']:
            diag['best_missing_edges'] = len(state.missing)
            diag['improvements'].append([step,len(state.missing)])
    return


def quotient_embed(source,target,*,seed=0,timeout=30.0,deadline=None):
    started = time.perf_counter()
    diag = dict(algorithm='target_quotient_reconfiguration_v1', seed=seed, stage='parameters',stage_wall={},
                coarsening_levels=0,target_contractions=0,improvements=[],search_visits=0,
                trimming=[],trim_deletions=0,source_label_order='supplied node iteration; diagnostic IDs are ranks')
    response = {'embedding':{},'status':'FAILURE','diag':diag}
    meter,state = None,None
    source_labels,target_labels,chains = [],[],{}
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
            target_labels,adj = _adjacency(target,meter)
            delta = max(map(len,adj),default=0)
            lower = [max(1,(len(row)+delta-5)//(delta-2)) if delta>2 else 1 for row in src]
            if sum(lower)>len(adj):
                raise _Failed('necessary source degree/vertex capacity bound')
            diag.update(source_nodes=len(src),target_nodes=len(adj),degree_lower_bound=sum(lower))
        if src:
            with meter.stage('target_coarsening'):
                regions = _coarsen(adj,len(src),rng,meter,diag)
            with meter.stage('source_assignment'):
                regions = _assign(regions,src,adj,lower,rng,meter)
                state = _State(regions,src,adj,meter)
            with meter.stage('global_reconfiguration'):
                _search(state,lower,rng,meter,diag)
            chains = dict(enumerate(state.regions))
            with meter.stage('entry_validation'):
                if not _valid(chains,src,adj,meter):
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
            if not _valid(chains,src,adj,meter):
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
