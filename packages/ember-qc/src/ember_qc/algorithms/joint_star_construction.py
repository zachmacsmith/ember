"""C019: joint center/leaf placement in one connected disjoint construction state.

Original contacts may be missing before first validity. No earlier constructor,
embedding library, saved map, global optimization or independent restart is used.
"""
from collections import Counter
from contextlib import contextmanager
import hashlib
import importlib.util
import math
from pathlib import Path
import random
import time


class _Deadline(Exception):
    pass


class _InputRejected(Exception):
    pass


class _Budget:
    def __init__(self, deadline):
        self.deadline = deadline; self.work = Counter()
        self.stage_wall = Counter(); self.stage_cpu = Counter()
        self.phase = 'bookkeeping'; self.last = time.perf_counter(); self.last_cpu = time.process_time()

    def check(self):
        if time.perf_counter() >= self.deadline:
            raise _Deadline(self.phase)

    def tick(self, key, count=1):
        self.work[key] += int(count); self.check()

    def _switch(self, phase):
        now, cpu = time.perf_counter(), time.process_time()
        self.stage_wall[self.phase] += now-self.last
        self.stage_cpu[self.phase] += cpu-self.last_cpu
        self.last, self.last_cpu, self.phase = now, cpu, phase

    @contextmanager
    def stage(self, phase):
        previous = self.phase; self._switch(phase)
        try:
            self.check(); yield; self.check()
        finally:
            self._switch(previous)


def _load(name, path, expected=None):
    if expected is not None and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ImportError('C019 initialization helper hash mismatch')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _support():
    here = Path(__file__).parent
    old = _load('_c019_initialization', here/'variable_regions.py',
                '696ab4a6882bf33fa48db733facd0517aba2fffbcc0a3445fc389d96df6dfa68')
    kernels = _load('_c019_kernels', here/'joint_star_kernels.py')
    return old, kernels


class _Published:
    """Published arrays are immutable by convention; replacement is one pointer."""
    def __init__(self, chains, owner, counts, gaps, versions):
        self.chains = tuple(chains); self.owner = owner; self.counts = counts
        self.gaps = gaps; self.versions = versions
        self.Q = sum(map(len, chains)); self.missing = int((counts == 0).sum())
        self.R = sum(map(int, counts)) - len(counts)


class _Engine:
    def __init__(self, src, adj, chains, seed, budget, helper, kernels, rng=None,
                 started=None, cardinality_only=False):
        self.src, self.adj, self.b, self.helper, self.k = src, adj, budget, helper, kernels
        self.np = kernels.np; np = self.np
        self.n, self.h = len(src), len(adj); self.cardinality_only = cardinality_only
        self.started = time.perf_counter() if started is None else started
        self.search_seconds = max(0., budget.deadline-self.started)
        self.rng = random.Random(seed) if rng is None else rng
        so, to = list(range(self.n)), list(range(self.h))
        self.rng.shuffle(so); self.rng.shuffle(to)
        self.srank = {u:i for i,u in enumerate(so)}
        self.trank = np.empty(self.h, dtype=np.int64)
        for i,q in enumerate(to): self.trank[q] = i
        self.starts = np.zeros(self.h+1, dtype=np.int64); flat = []
        for q, row in enumerate(adj):
            flat.extend(sorted(row, key=lambda p:self.trank[p])); self.starts[q+1] = len(flat)
            self.b.tick('packed_target_rows')
        self.flat = np.asarray(flat, dtype=np.int64)
        self.degrees = np.diff(self.starts); self.maximum_degree = max(map(int, self.degrees), default=0)
        self.edges = [(u,v) for u,row in enumerate(src) for v in row if u<v]
        edge_index = {e:i for i,e in enumerate(self.edges)}
        self.neighbors, self.incident = [], []
        for u,row in enumerate(src):
            neighbors = sorted(row, key=lambda v:self.srank[v])
            self.neighbors.append(np.asarray(neighbors, dtype=np.int64))
            self.incident.append(np.asarray([edge_index[tuple(sorted((u,v)))] for v in neighbors],dtype=np.int64))
        owner = np.full(self.h, -1, dtype=np.int64)
        arrays = tuple(np.asarray(sorted(c),dtype=np.int64) for c in chains)
        for u,chain in enumerate(arrays):
            if not len(chain) or bool(np.any(owner[chain] >= 0)):
                raise ValueError('nonempty disjoint initial territories required')
            owner[chain] = u
        self.weights = np.full(len(self.edges), 2, dtype=np.int64)
        self.cache = np.full((self.n,self.h), -1, dtype=np.int64)
        self.cache_versions = np.full(self.n,-1,dtype=np.int64)
        self.state = _Published(arrays,owner,np.zeros(len(self.edges),dtype=np.int64),
                                np.zeros(len(self.edges),dtype=np.int64),np.zeros(self.n,dtype=np.int64))
        self.incumbent = None; self.events = []; self.visits = []; self.sweeps = []
        self.first_valid_snapshot = None; self.latest_certified = None; self.publication_id = 0
        for v in range(self.n):
            if len(src[v]): self.distance(v)
        counts, gaps = self.state.counts.copy(), self.state.gaps.copy()
        for u in range(self.n):
            nn = self.neighbors[u]; ix = self.incident[u]
            idx = self.neighbor_index(u)
            counts[ix] = self.counts(arrays[u],idx,len(nn))
            for j,v in enumerate(nn): gaps[ix[j]] = max(0,int(self.cache[v,arrays[u]].min())-1)
        if not np.array_equal(counts > 0,gaps == 0): raise RuntimeError('initial contact/distance mismatch')
        self.state = _Published(arrays,owner,counts,gaps,self.state.versions)
        self.b.check()

    def neighbor_index(self, u):
        idx = self.np.full(self.n,-1,dtype=self.np.int64)
        for j,v in enumerate(self.neighbors[u]): idx[v] = j
        return idx

    def bfs(self, roots, available):
        np = self.np
        distance = np.full(self.h,-1,dtype=np.int64); parent = np.full(self.h,-2,dtype=np.int64)
        queue = np.empty(self.h,dtype=np.int64)
        roots = sorted(roots,key=lambda q:self.trank[q]); head, tail = 0,len(roots)
        for i,q in enumerate(roots):
            if not available[q]: raise RuntimeError('BFS root not available')
            distance[q] = 0; parent[q] = -1; queue[i] = q
        work = np.zeros(2,dtype=np.int64)
        try:
            while head < tail:
                self.b.check()
                head,tail = self.k.bfs_batch(self.starts,self.flat,available,distance,parent,queue,head,tail,work)
                self.b.check()
        finally:
            self.b.work['bfs_vertices'] += int(work[0]); self.b.work['bfs_adjacency'] += int(work[1])
        return distance,parent,queue[:tail]

    def distance(self, v):
        version = int(self.state.versions[v])
        if self.cache_versions[v] == version:
            self.b.tick('distance_cache_hits'); return self.cache[v]
        with self.b.stage('distance_refresh'):
            distance,_,_ = self.bfs(self.state.chains[v],self.np.ones(self.h,dtype=self.np.bool_))
            if bool(self.np.any(distance < 0)): raise ValueError('C019 requires a connected target')
            self.b.check()
            self.cache[v,:] = distance; self.cache_versions[v] = version
            self.b.tick('distance_cache_refreshes')
        return self.cache[v]

    def counts(self, chain, index, degree, owner=None):
        work = self.np.zeros(2,dtype=self.np.int64)
        try:
            self.b.check()
            result = self.k.contact_counts(self.starts,self.flat,self.state.owner if owner is None else owner,chain,index,degree,work)
            self.b.check(); return result
        finally: self.b.work['contact_adjacency'] += int(work[1])

    def snapshot(self, state=None):
        s = self.state if state is None else state
        return dict(chains={str(u):list(map(int,c)) for u,c in enumerate(s.chains)},
                    qubits=s.Q,R=s.R,missing_edges=s.missing,
                    contacts=[int(v) for v in s.counts],gaps=[int(v) for v in s.gaps],
                    versions=[int(v) for v in s.versions])


    def ordered(self, sites):
        values = self.np.asarray(list(sites), dtype=self.np.int64)
        return values[self.np.argsort(self.trank[values], kind='stable')]


class _NoProposal(Exception):
    """A completed obstruction in this query, never global infeasibility."""


def _matching(e, cost, allowed, weighted):
    """Exact maximum-cardinality assignment; soft cost is optional, score is not."""
    np = e.np; k, real = cost.shape
    if k == 0:
        return np.empty(0, dtype=np.int64), 0, 0
    if cost.shape != allowed.shape or bool(np.any(cost[allowed] < 0)):
        raise RuntimeError('invalid assignment matrix')
    largest = max(map(int, cost[allowed]), default=0) if weighted else 0
    penalty = 1 + k * largest
    if 8 * (k + 1) * (penalty + largest + 1) >= e.k.INF:
        raise OverflowError('assignment potential bound exceeds exact integer range')
    columns = real + k
    u = np.zeros(k + 1, dtype=np.int64); v = np.zeros(columns + 1, dtype=np.int64)
    p = np.zeros(columns + 1, dtype=np.int64); way = np.zeros(columns + 1, dtype=np.int64)
    work = np.zeros(1, dtype=np.int64)
    e.b.tick('assignment_queries')
    try:
        for row in range(1, k + 1):
            e.b.check(); p[0] = row; column = 0
            minimum = np.full(columns + 1, e.k.INF, dtype=np.int64)
            used = np.zeros(columns + 1, dtype=np.bool_)
            while True:
                e.b.check()
                column = int(e.k.hungarian_step(cost, allowed, weighted, penalty,
                             u, v, p, way, minimum, used, column, work))
                e.b.check()
                if p[column] == 0:
                    break
            while column:
                previous = int(way[column]); p[column] = p[previous]; column = previous
                e.b.tick('assignment_path_records')
    finally:
        e.b.work['assignment_column_scans'] += int(work[0])
    assigned = np.full(k, -1, dtype=np.int64); actual_cost = 0; cardinality = 0
    for j in range(1, real + 1):
        if p[j]:
            row = int(p[j]) - 1
            if not allowed[row, j - 1] or assigned[row] >= 0:
                raise RuntimeError('assignment extraction violates ownership')
            assigned[row] = j - 1; actual_cost += int(cost[row, j - 1]); cardinality += 1
        e.b.tick('assignment_extraction_columns')
    e.b.tick('completed_assignments')
    return assigned, cardinality, actual_cost


class _Query:
    def __init__(self, e, center, row):
        self.e, self.u, self.row = e, center, row; np = e.np
        candidates = [v for v in e.src[center]
                      if len(e.state.chains[v]) == 1 and len(e.src[v]) <= e.maximum_degree]
        candidates.sort(key=lambda v: (len(e.src[v]), e.srank[v]))
        blocked = set(); self.leaves = []
        for v in candidates:
            if v not in blocked:
                self.leaves.append(v); blocked.update(e.src[v])
            e.b.tick('leaf_selection_records')
        self.selected = [center] + self.leaves; selected = set(self.selected); self.k = len(self.leaves)
        self.demands = np.asarray([len(e.src[v]) for v in self.leaves], dtype=np.int64)
        self.required = np.sort(self.demands)
        row.update(selected=self.selected,leaves=self.k,eligible_singletons=len(candidates),
            long_neighbor_exclusions=sum(len(e.state.chains[v]) != 1 for v in e.src[center]),
            degree_neighbor_exclusions=sum(len(e.src[v]) > e.maximum_degree for v in e.src[center]),
            independence_exclusions=len(candidates)-self.k,
            old_selected_Q=sum(len(e.state.chains[v]) for v in self.selected),
            assignment_calls=0,assignment_completions=0,growth_trials=0,growth_retained=0,
            precoverage_growth=0,postcoverage_growth=0,maximum_proxy_gap=0,covering_footprints=0)
        self.available = e.state.owner < 0
        for v in self.selected:
            self.available[e.state.chains[v]] = True
        self.outside = {}; self.outside_weights = {}; total_weight = 0
        for v in self.selected:
            pairs = [(int(w),int(e.weights[ix])) for w,ix in zip(e.neighbors[v],e.incident[v]) if w not in selected]
            self.outside[v] = np.asarray([w for w,_ in pairs], dtype=np.int64)
            self.outside_weights[v] = np.asarray([weight for _,weight in pairs], dtype=np.int64)
            total_weight += sum(weight for _,weight in pairs)
        if 16 * (self.k + 1)**2 * (e.h + self.k + max(1,e.h)*total_weight + 1) >= e.k.INF:
            raise OverflowError('query cost bound exceeds exact integer range')
        for w in sorted({int(w) for nn in self.outside.values() for w in nn}):
            e.distance(w)
        self.costs = np.empty((self.k,e.h),dtype=np.int64)
        self.center_cost = np.empty(e.h,dtype=np.int64)
        with e.b.stage('cost_vectors'):
            work = np.zeros(1,dtype=np.int64)
            try:
                for i,v in enumerate(self.selected):
                    output = self.center_cost if i == 0 else self.costs[i-1]
                    for begin in range(0,e.h,256):
                        e.b.check()
                        e.k.cost_batch(e.cache,self.outside[v],self.outside_weights[v],output,
                                       begin,min(e.h,begin+256),work)
                        e.b.check()
            finally:e.b.work['cost_vector_terms'] += int(work[0])
        self.baseline = np.empty(self.k,dtype=np.int64)
        for i,demand in enumerate(self.demands):
            domain = self.available & (e.degrees >= demand)
            if not bool(np.any(domain)):
                raise _NoProposal('leaf_degree_domain_empty')
            self.baseline[i] = self.costs[i,domain].min();e.b.tick('leaf_baselines')
        self.baseline_sum = sum(map(int,self.baseline))

    def root(self):
        e=self.e;np=e.np
        sites=e.ordered(np.flatnonzero(self.available))
        if self.k:
            sizes=np.zeros(e.h,dtype=np.int64);remaining=self.available.copy()
            with e.b.stage('component_bound'):
                for r in sites:
                    if not remaining[r]:continue
                    _,_,component=e.bfs([int(r)],self.available)
                    sizes[component]=len(component);remaining[component]=False;e.b.check()
            sites=sites[sizes[sites]>=self.k+1]
        self.row['root_domain']=len(sites)
        if not len(sites):raise _NoProposal('component_size_bound')
        best=None;work=np.zeros(2,dtype=np.int64)
        with e.b.stage('root_scoring'):
            try:
                for begin in range(0,len(sites),32):
                    e.b.check();end=min(len(sites),begin+32)
                    deficits,scores=e.k.root_batch(e.starts,e.flat,self.available,e.degrees,e.maximum_degree,
                        self.demands,self.required,self.costs,self.baseline,self.center_cost,sites,begin,end,work)
                    e.b.check()
                    for i,r in enumerate(sites[begin:end]):
                        key=(int(deficits[i]),int(scores[i]),int(e.trank[r]))
                        if best is None or key<best[0]:best=key,int(r)
            finally:
                e.b.work['root_adjacency']+=int(work[0]);e.b.work['root_leaf_terms']+=int(work[1])
        key,r=best
        self.row.update(root=r,root_proxy=list(key[:2]),root_outside_old=bool(r not in e.state.chains[self.u]))
        tree=np.zeros(e.h,dtype=np.bool_);tree[r]=True
        boundary=np.zeros(e.h,dtype=np.bool_)
        for q in e.adj[r]:
            if self.available[q]:boundary[q]=True
        near=np.asarray([e.cache[w,r] for w in self.outside[self.u]],dtype=np.int64)
        return self.footprint(tree,boundary,near,key[:2])

    def footprint(self,tree,boundary,near,proxy):
        e=self.e;np=e.np;sites=e.ordered(np.flatnonzero(boundary));size=int(tree.sum())
        cost=self.costs[:,sites]-self.baseline[:,None]
        allowed=e.degrees[sites][None,:]>=self.demands[:,None]
        self.row['assignment_calls']+=1
        with e.b.stage('assignment'):
            assignment,matched,actual_cost=_matching(e,cost,allowed,not e.cardinality_only)
        self.row['assignment_completions']+=1
        center_value=sum(int(w)*max(0,int(d)-1) for w,d in zip(self.outside_weights[self.u],near))
        score=(self.k-matched,size+self.k+center_value+self.baseline_sum+actual_cost)
        if score[0]!=proxy[0] or score[1]<proxy[1]:
            raise RuntimeError('proxy/cardinality disagrees with completed assignment')
        self.row['maximum_proxy_gap']=max(self.row['maximum_proxy_gap'],score[1]-proxy[1])
        if matched==self.k:self.row['covering_footprints']+=1
        return dict(tree=tree,boundary=boundary,sites=sites,near=near,size=size,
                    assignment=assignment,score=score,proxy=proxy)

    def extension(self,footprint):
        e=self.e;np=e.np;f=footprint;sites=f['sites']
        if not len(sites):return None
        work=np.zeros(2,dtype=np.int64)
        with e.b.stage('growth_scoring'):
            best=None
            try:
                summary=e.k.boundary_summary(sites,e.degrees,e.maximum_degree,self.demands,
                                            self.costs,self.baseline,work);e.b.check()
                for begin in range(0,len(sites),32):
                    e.b.check();end=min(len(sites),begin+32)
                    deficits,scores=e.k.growth_batch(e.starts,e.flat,self.available,f['tree'],f['boundary'],
                        e.degrees,self.demands,self.required,self.costs,self.baseline,e.cache,
                        self.outside[self.u],self.outside_weights[self.u],f['near'],f['size'],
                        *summary,sites,begin,end,work)
                    e.b.check()
                    for i,q in enumerate(sites[begin:end]):
                        key=(int(deficits[i]),int(scores[i]),int(e.trank[q]))
                        if best is None or key<best[0]:best=key,int(q)
            finally:
                e.b.work['growth_adjacency_or_summary_terms']+=int(work[0])
                e.b.work['growth_leaf_or_center_terms']+=int(work[1])
        key,q=best
        tree=f['tree'].copy();tree[q]=True;boundary=f['boundary'].copy();boundary[q]=False
        for p in e.adj[q]:
            if self.available[p] and not tree[p]:boundary[p]=True
        near=np.minimum(f['near'],e.cache[self.outside[self.u],q])
        self.row['growth_trials']+=1
        proposed=self.footprint(tree,boundary,near,key[:2])
        self.row['last_extension']=dict(site=q,proxy=list(key[:2]),actual=list(proposed['score']),
                                        center_size=proposed['size'])
        return proposed

    def grow(self):
        e=self.e;current=self.root()
        while True:
            e.b.check();covered=current['score'][0]==0
            if covered and 'first_covering' not in self.row:
                self.row['first_covering']=dict(center_size=current['size'],score=current['score'][1])
            proposed=self.extension(current)
            if proposed is None:
                if not covered:raise _NoProposal('available_boundary_exhausted_before_coverage')
                self.row['growth_stop']='available_boundary_exhausted';break
            if covered and (proposed['score'][0]!=0 or proposed['score'][1]>=current['score'][1]):
                self.row['growth_stop']=('selected_extension_loses_coverage' if proposed['score'][0]
                                         else 'selected_extension_nonimproving');break
            self.row['growth_retained']+=1
            self.row['postcoverage_growth' if covered else 'precoverage_growth']+=1
            current=proposed
        e.b.check();self.row['final_center_size']=current['size']
        replacements={self.u:e.np.flatnonzero(current['tree'])}
        for i,v in enumerate(self.leaves):
            j=int(current['assignment'][i])
            if j<0:raise RuntimeError('unassigned leaf in completed block')
            replacements[v]=e.np.asarray([current['sites'][j]],dtype=e.np.int64)
        return replacements,current['score'][1]


def _recount(e,selected,replacements,row):
    """Private multi-owner transaction; all old ownership is removed first."""
    np=e.np;old=e.state;selected=set(selected);owner=old.owner.copy();chains=list(old.chains)
    for v in selected:owner[old.chains[v]]=-1
    changed=[]
    for v in sorted(selected):
        chain=np.asarray(sorted(map(int,replacements[v])),dtype=np.int64)
        if not len(chain) or len(np.unique(chain))!=len(chain) or bool(np.any(chain<0)) or bool(np.any(chain>=e.h)):
            raise RuntimeError('invalid selected chain members')
        if bool(np.any(owner[chain]>=0)):raise RuntimeError('selected ownership collision')
        member=set(map(int,chain));seen={int(chain[0])};stack=[int(chain[0])]
        while stack:
            q=stack.pop()
            for p in e.adj[q]:
                if p in member and p not in seen:seen.add(p);stack.append(p)
            e.b.tick('selected_connectivity_sites')
        if len(seen)!=len(chain):raise RuntimeError('disconnected selected chain')
        owner[chain]=v;chains[v]=chain
        if not np.array_equal(chain,old.chains[v]):changed.append(v)
    counts,gaps,versions=old.counts.copy(),old.gaps.copy(),old.versions.copy()
    touched=sorted({int(ix) for v in selected for ix in e.incident[v]})
    recounted={}
    for v in sorted(selected):
        new_counts=e.counts(chains[v],e.neighbor_index(v),len(e.neighbors[v]),owner)
        for w,ix,count in zip(e.neighbors[v],e.incident[v],new_counts):
            ix=int(ix);count=int(count)
            if ix in recounted and recounted[ix]!=count:raise RuntimeError('asymmetric incident count')
            recounted[ix]=count;counts[ix]=count
            if w in selected:
                if count<=0:raise RuntimeError('constructed internal star contact absent')
                gaps[ix]=0
            else:
                gaps[ix]=max(0,int(e.distance(int(w))[chains[v]].min())-1)
            if (count>0)!=(gaps[ix]==0):raise RuntimeError('incident contact/gap mismatch')
            e.b.tick('selected_incident_edges')
    for v in changed:versions[v]+=1
    proposal=_Published(chains,owner,counts,gaps,versions)
    delta_q=proposal.Q-old.Q
    delta_e=delta_q+sum(int(e.weights[ix])*(int(gaps[ix])-int(old.gaps[ix])) for ix in touched)
    row.update(proposal_complete=True,geometry_changed=bool(changed),changed_owners=changed,
        Q_proposed=proposal.Q,R_proposed=proposal.R,missing_proposed=proposal.missing,
        delta_Q=delta_q,delta_R=proposal.R-old.R,delta_M=proposal.missing-old.missing,delta_energy=delta_e,
        contacts_broken=sum(old.counts[ix]>0 and counts[ix]==0 for ix in touched),
        contacts_gained=sum(old.counts[ix]==0 and counts[ix]>0 for ix in touched))
    row['contacts_broken']=int(row['contacts_broken']);row['contacts_gained']=int(row['contacts_gained'])
    e.b.check();return proposal,delta_e


def _propose(e,u,row):
    try:
        with e.b.stage('block_selection'):query=_Query(e,u,row)
        replacements,block_score=query.grow()
        with e.b.stage('proposal_recount'):
            proposal,delta=_recount(e,query.selected,replacements,row)
            touched={int(ix) for v in query.selected for ix in e.incident[v]}
            new_cost=sum(len(proposal.chains[v]) for v in query.selected)+sum(
                int(e.weights[ix])*int(proposal.gaps[ix]) for ix in touched)
            old_cost=sum(len(e.state.chains[v]) for v in query.selected)+sum(
                int(e.weights[ix])*int(e.state.gaps[ix]) for ix in touched)
            if new_cost!=block_score or new_cost-old_cost!=delta:
                raise RuntimeError('conditional block cost omitted an original-edge term')
            row.update(old_block_cost=old_cost,new_block_cost=new_cost)
            return proposal,delta
    except _NoProposal as exc:
        row.update(status='completed_query_failure',query_stop=str(exc),query_complete=True)
        return None,None


def _accept(e,proposal,delta,row):
    draw=None;temperature=None;old=e.state
    if not row['geometry_changed']:accepted=False;reason='identical'
    elif e.incumbent is not None:
        accepted=proposal.missing==0 and (proposal.Q<old.Q or (proposal.Q==old.Q and proposal.R>old.R))
        reason='valid_Q_R'
    elif proposal.missing==0:accepted=True;reason='first_valid'
    else:
        median=float(e.np.median(e.weights)) if len(e.weights) else 2.
        fraction=max(0.,1.-(time.perf_counter()-e.started)/max(e.search_seconds,1e-300))
        temperature=median*fraction*fraction;draw=e.rng.random()
        accepted=delta<=0 or (temperature>0 and draw<math.exp(-delta/temperature))
        reason='construction_energy'
    row.update(accepted=bool(accepted),acceptance_rule=reason,acceptance_uniform=draw,temperature=temperature)
    return bool(accepted)


def _admit(e,proposal,row,initial=False):
    """Certification precedes the one publication; the latest valid state wins ties."""
    valid=proposal.missing==0;event=None;receipt=None;first_snapshot=None
    if valid:
        with e.b.stage('incumbent_validation'):
            mapping={u:set(map(int,chain)) for u,chain in enumerate(proposal.chains)}
            if not e.helper._valid(mapping,e.src,e.adj,e.b):raise RuntimeError('valid proposal failed original validator')
            receipt=dict(Q=proposal.Q,R=proposal.R,
                         publication=e.publication_id+(0 if initial else 1))
            if e.incumbent is None or proposal.Q<e.incumbent.Q:
                event=dict(receipt,acl=proposal.Q/e.n if e.n else None,missing=0,
                           kind='first_valid' if e.incumbent is None else 'strict_Q')
            if e.incumbent is None:first_snapshot=e.snapshot(proposal)
            e.b.check()
    e.b.check()
    if valid:
        receipt['wall']=time.perf_counter()-e.started
        if event is not None:event['wall']=receipt['wall']
    e.state=proposal
    if not initial:e.publication_id+=1
    if valid:
        e.incumbent=proposal;e.latest_certified=receipt
        if event is not None:e.events.append(event)
        if first_snapshot is not None:e.first_valid_snapshot=first_snapshot
    row.update(committed=True,status='committed',publication=e.publication_id,
               Q_after=proposal.Q,R_after=proposal.R,missing_after=proposal.missing,certified=valid,
               certification=receipt)
    e.b.check()


def _run(e):
    if e.state.missing==0:_admit(e,e.state,{},initial=True)
    while True:
        e.b.check();quality=e.incumbent is not None
        if quality and e.incumbent.Q==e.n:return 'optimal_Q_equals_n'
        pressure=[0]*e.n
        for ix,(u,v) in enumerate(e.edges):
            amount=int(e.weights[ix])*int(e.state.gaps[ix]);pressure[u]+=amount;pressure[v]+=amount
        order=sorted(range(e.n),key=lambda u:(-pressure[u],e.srank[u]))
        sweep=dict(index=len(e.sweeps),quality=quality,status='running',Q_before=e.state.Q,
                   missing_before=e.state.missing,visits_completed=0,commits=0)
        e.sweeps.append(sweep);transition=False
        try:
            for u in order:
                e.b.check();began,cpu=time.perf_counter(),time.process_time()
                row=dict(owner=u,sweep=sweep['index'],quality=e.incumbent is not None,status='running',
                    Q_before=e.state.Q,R_before=e.state.R,missing_before=e.state.missing,
                    proposal_complete=False,query_complete=False,committed=False)
                e.visits.append(row)
                try:
                    proposal,delta=_propose(e,u,row)
                    if proposal is not None:
                        row['query_complete']=True
                        if _accept(e,proposal,delta,row):
                            was_valid=e.incumbent is not None
                            _admit(e,proposal,row)
                            transition=not was_valid and e.incumbent is not None
                        else:row['status']='rejected'
                    e.b.check();sweep['visits_completed']+=1
                except _Deadline:
                    row['interrupted']=True
                    if not row['committed']:row['status']='interrupted'
                    raise
                finally:
                    sweep['commits']+=int(row['committed'])
                    row.update(wall=time.perf_counter()-began,cpu=time.process_time()-cpu,
                               elapsed=time.perf_counter()-e.started)
                if transition:break
            if transition:sweep['status']='first_valid_transition';continue
            if quality and not sweep['commits']:
                sweep['status']='policy_exhausted';return 'valid_policy_exhausted'
            if not quality:
                missing=e.np.flatnonzero(e.state.counts==0)
                if any(int(e.weights[ix])>=e.k.INF for ix in missing):raise OverflowError('contact price range')
                e.b.check();e.weights[missing]+=1
                sweep['raised_weight_count']=len(missing)
            sweep['status']='complete';e.b.check()
        except _Deadline:
            if sweep['status']=='running':sweep['status']='interrupted'
            raise

def _embed(source,target,seed,timeout,deadline,cardinality_only):
    started,cpu=time.perf_counter(),time.process_time()
    diag=dict(algorithm='joint_star_construction',policy='C019',cardinality_only=cardinality_only,
              work_limit=None,fatal_error=False,first_valid=None,incumbent_events=[],visits=[],sweeps=[])
    response=dict(status='FAILURE',embedding={},diag=diag);e=b=helper=None;absolute=None
    sl=tl=[]
    try:
        if type(seed) is not int or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
            raise _InputRejected('integer seed and positive finite timeout required')
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise _InputRejected('finite deadline required')
        absolute=min(started+timeout,deadline) if deadline is not None else started+timeout
        reserve=min(.5,timeout/10);b=_Budget(absolute-reserve)
        diag.update(started=started,deadline=absolute,search_deadline=b.deadline,final_reserve=reserve)
        with b.stage('support_imports'):helper,kernels=_support()
        with b.stage('input'):
            try:
                sl,src=helper._adjacency(source,b);tl,adj=helper._adjacency(target,b)
            except ValueError as exc:
                raise _InputRejected(str(exc)) from exc
            if len(src)>len(adj):raise helper._Failed('more source owners than target sites')
        rng=random.Random(seed)
        with b.stage('initialization'):
            chains,_=helper._initialize(src,adj,rng,b,diag) if src else ([],0)
        with b.stage('state_setup'):
            e=_Engine(src,adj,chains,seed,b,helper,kernels,rng,started,cardinality_only)
            diag['initial']=e.snapshot()
        diag['stop_reason']=_run(e)
    except _Deadline as exc:
        response['status']='TIMEOUT';diag.update(stop_reason='search_deadline',interrupted_stage=str(exc))
    except Exception as exc:
        if helper is not None and isinstance(exc,helper._Expired):
            response['status']='TIMEOUT';diag.update(stop_reason='search_deadline',interrupted_stage=str(exc))
        else:
            expected=isinstance(exc,_InputRejected) or (helper is not None and isinstance(exc,helper._Failed))
            response.update(status='FAILURE' if expected else 'ERROR',error=type(exc).__name__+': '+str(exc))
            diag.update(fatal_error=not expected,stop_reason='input_rejected' if expected else 'exception')
    if b is not None:
        b.deadline=absolute
        if e is not None:
            diag.update(visits=e.visits,sweeps=e.sweeps,incumbent_events=e.events,
                        first_valid=e.events[0] if e.events else None,latest_certified=e.latest_certified,
                        first_valid_geometry=e.first_valid_snapshot,publication_count=e.publication_id)
            try:
                with b.stage('final_validation_output'):
                    diag['terminal']=e.snapshot();diag['weights']=[int(w) for w in e.weights];b.check()
                    if e.incumbent is not None and not response.get('error'):
                        chains={u:set(map(int,c)) for u,c in enumerate(e.incumbent.chains)}
                        if not e.helper._valid(chains,e.src,e.adj,b):raise RuntimeError('incumbent failed final validation')
                        mapping={sl[u]:[tl[int(q)] for q in c] for u,c in enumerate(e.incumbent.chains)}
                        b.check();response.update(status='SUCCESS',embedding=mapping)
                        diag['final_Q']=e.incumbent.Q;diag['final_R']=e.incumbent.R
                        diag['returned_geometry']=e.snapshot(e.incumbent)
            except _Deadline:
                diag['final_stop']='deadline';response['embedding']={}
                if not diag['fatal_error']:response['status']='TIMEOUT'
            except Exception as exc:
                response.update(status='ERROR',embedding={},error=type(exc).__name__+': '+str(exc));diag['fatal_error']=True
        b._switch('bookkeeping')
        diag.update(work=dict(b.work),stage_wall=dict(b.stage_wall),stage_cpu=dict(b.stage_cpu))
    finished=time.perf_counter();response['time']=finished-started
    diag.update(finished=finished,wall=finished-started,cpu=time.process_time()-cpu)
    if absolute is not None and finished>=absolute:
        if response.get('embedding'):response['diagnostic_embedding']=response['embedding']
        response['embedding']={}
        if not diag['fatal_error']:response['status']='TIMEOUT'
    return response



def joint_star_construction_embed(source,target,*,seed=0,timeout=60.,deadline=None):
    return _embed(source,target,seed,timeout,deadline,False)


def cardinality_star_construction_embed(source,target,*,seed=0,timeout=60.,deadline=None):
    return _embed(source,target,seed,timeout,deadline,True)
