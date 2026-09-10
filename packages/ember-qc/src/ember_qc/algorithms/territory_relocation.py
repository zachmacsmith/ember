"""C018: one disjoint territory state, full-owner relocation and tree regrowth.

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
        raise ImportError('C018 initialization helper hash mismatch')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _support():
    here = Path(__file__).parent
    old = _load('_c018_initialization', here/'variable_regions.py',
                '696ab4a6882bf33fa48db733facd0517aba2fffbcc0a3445fc389d96df6dfa68')
    kernels = _load('_c018_kernels', here/'territory_relocation_kernels.py')
    return old, kernels


class _Published:
    """Published arrays are immutable by convention; replacement is one pointer."""
    def __init__(self, chains, owner, counts, gaps, versions):
        self.chains = tuple(chains); self.owner = owner; self.counts = counts
        self.gaps = gaps; self.versions = versions
        self.Q = sum(map(len, chains)); self.missing = int((counts == 0).sum())


class _Engine:
    def __init__(self, src, adj, chains, seed, budget, helper, kernels, rng=None,
                 started=None, old_roots=False):
        self.src, self.adj, self.b, self.helper, self.k = src, adj, budget, helper, kernels
        self.np = kernels.np; np = self.np
        self.n, self.h = len(src), len(adj); self.old_roots = old_roots
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
        self.weights = np.full(len(self.edges), 2., dtype=np.float64)
        self.cache = np.full((self.n,self.h), -1, dtype=np.int64)
        self.cache_versions = np.full(self.n,-1,dtype=np.int64)
        self.state = _Published(arrays,owner,np.zeros(len(self.edges),dtype=np.int64),
                                np.zeros(len(self.edges),dtype=np.int64),np.zeros(self.n,dtype=np.int64))
        self.incumbent = None; self.events = []; self.visits = []; self.sweeps = []
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
            if bool(self.np.any(distance < 0)): raise ValueError('C018 requires a connected target')
            self.b.check()
            self.cache[v,:] = distance; self.cache_versions[v] = version
            self.b.tick('distance_cache_refreshes')
        return self.cache[v]

    def counts(self, chain, index, degree):
        work = self.np.zeros(2,dtype=self.np.int64)
        try:
            self.b.check()
            result = self.k.contact_counts(self.starts,self.flat,self.state.owner,chain,index,degree,work)
            self.b.check(); return result
        finally: self.b.work['contact_adjacency'] += int(work[1])

    def snapshot(self, state=None):
        s = self.state if state is None else state
        return dict(chains={str(u):list(map(int,c)) for u,c in enumerate(s.chains)},
                    qubits=s.Q,missing_edges=s.missing,
                    contacts=[int(v) for v in s.counts],gaps=[int(v) for v in s.gaps],
                    versions=[int(v) for v in s.versions])


def _root(e,u,available,quality,row):
    np=e.np; nn=e.neighbors[u]; weights=e.weights[e.incident[u]]
    sites=np.flatnonzero(available)
    if e.old_roots: sites=e.state.chains[u].copy()
    sites=sites[np.argsort(e.trank[sites],kind='stable')]
    scores=e.k.root_scores(e.cache,nn,weights,sites)
    e.b.tick('root_scores',len(sites)*max(1,len(nn)))
    if not len(sites) or not bool(np.all(np.isfinite(scores))):raise RuntimeError('invalid root domain/score')
    if quality:
        selected=int(np.argmin(scores)); draw=None
    else:
        scale=(float(np.median(e.weights)) if len(e.weights) else 2.)*max(1,len(nn))
        mass=np.exp(-(scores-float(scores.min()))/scale)
        cumulative=np.cumsum(mass);draw=e.rng.random()
        selected=min(int(np.searchsorted(cumulative,draw*float(cumulative[-1]),side='right')),len(sites)-1)
    root=int(sites[selected])
    row.update(root=root,root_domain=len(sites),root_score=float(scores[selected]),
               minimum_singleton_score=float(scores.min()),root_draw=draw,
               root_outside_old=bool(root not in e.state.chains[u]))
    e.b.check();return root


def _regrow(e,u,root,available,row):
    np=e.np;nn=e.neighbors[u];weights=e.weights[e.incident[u]];index=e.neighbor_index(u)
    tree=np.zeros(e.h,dtype=np.bool_);tree[root]=True
    near=np.asarray([e.cache[v,root] for v in nn],dtype=np.int64)
    row.update(extensions=[],paths_scored=0,no_free_endpoint=0,growth_rounds=0)
    while bool(np.any(near>1)):
        e.b.check();row['growth_rounds']+=1
        _,parent,order=e.bfs(np.flatnonzero(tree),available)
        work=np.zeros(2,dtype=np.int64)
        try:
            goals=e.k.endpoints(e.starts,e.flat,e.state.owner,order,index,near,work);e.b.check()
        finally:e.b.work['endpoint_adjacency']+=int(work[1])
        best=None
        for j,v in enumerate(nn):
            if near[j]<=1:continue
            e.b.check();q=int(goals[j])
            if q<0:row['no_free_endpoint']+=1;continue
            path=[]
            while parent[q]>=0:
                path.append(q);q=int(parent[q]);e.b.tick('path_recovery_sites')
            path=np.asarray(path[::-1],dtype=np.int64)
            if not len(path) or bool(np.any(tree[path])):raise RuntimeError('invalid canonical extension')
            delta,updated=e.k.extension_score(e.cache,nn,weights,near,path)
            e.b.tick('path_score_terms',len(path)*max(1,len(nn)));row['paths_scored']+=1
            key=(float(delta),len(path),e.srank[int(v)])
            if delta<0 and (best is None or key<best[0]):best=key,path,updated,int(v)
        if best is None:break
        key,path,updated,v=best
        e.b.check();tree[path]=True
        row['extensions'].append(dict(destination=v,length=len(path),delta_energy=key[0],
                                      newly_met=int(((near>1)&(updated==1)).sum())))
        near=updated
    e.b.check();return np.flatnonzero(tree),near,index


def _propose(e,u,quality,row):
    np=e.np;s=e.state;nn=e.neighbors[u];ix=e.incident[u]
    for v in nn:e.distance(int(v))
    with e.b.stage('root_scoring'):
        available=(s.owner<0)|(s.owner==u)
        root=_root(e,u,available,quality,row)
    with e.b.stage('regrowth'):
        chain,near,index=_regrow(e,u,root,available,row)
    with e.b.stage('proposal_bookkeeping'):
        new_counts=e.counts(chain,index,len(nn));new_gaps=np.maximum(near-1,0)
        if not np.array_equal(new_counts>0,new_gaps==0):raise RuntimeError('proposal contact/distance mismatch')
        delta_q=len(chain)-len(s.chains[u])
        delta_e=float(delta_q+np.dot(e.weights[ix],new_gaps-s.gaps[ix]))
        chains=list(s.chains);chains[u]=chain
        owner=s.owner.copy();owner[s.chains[u]]=-1;owner[chain]=u
        counts,gaps,versions=s.counts.copy(),s.gaps.copy(),s.versions.copy()
        changed=not np.array_equal(chain,s.chains[u])
        counts[ix]=new_counts;gaps[ix]=new_gaps;versions[u]+=int(changed)
        proposed=_Published(chains,owner,counts,gaps,versions)
        row.update(delta_Q=delta_q,delta_energy=delta_e,Q_proposed=proposed.Q,missing_proposed=proposed.missing,
                   contacts_broken=int(((s.counts[ix]>0)&(new_counts==0)).sum()),
                   contacts_gained=int(((s.counts[ix]==0)&(new_counts>0)).sum()),
                   proposed_length=len(chain),geometry_changed=changed,proposal_complete=True)
        e.b.check();return proposed,delta_e


def _accept(delta,temperature,quality,old,proposed,rng,row):
    draw=None
    if quality:accepted=proposed.missing==0 and proposed.Q<old.Q
    elif delta<=0:accepted=True
    elif temperature>0:
        draw=rng.random();accepted=draw<math.exp(-delta/temperature)
    else:accepted=False
    row.update(acceptance_uniform=draw,temperature=temperature,accepted=accepted)
    return accepted


def _publish(e,proposed,row):
    e.b.check()
    e.state=proposed
    row.update(committed=True,status='committed',Q_after=proposed.Q,missing_after=proposed.missing)
    e.b.check()


def _certify(e):
    if e.state.missing:return False
    if e.incumbent is not None and e.state.Q>=e.incumbent.Q:return False
    previous,count=e.incumbent,len(e.events)
    try:
        with e.b.stage('incumbent_validation'):
            chains={u:set(map(int,c)) for u,c in enumerate(e.state.chains)}
            if not e.helper._valid(chains,e.src,e.adj,e.b):raise RuntimeError('complete state failed existing validator')
            e.b.check()
            event=dict(wall=time.perf_counter()-e.started,Q=e.state.Q,acl=e.state.Q/e.n if e.n else None,
                       kind='first_valid' if e.incumbent is None else 'strict_Q',missing=0)
            e.b.check();e.incumbent=e.state;e.events.append(event)
    except _Deadline:
        e.incumbent=previous;del e.events[count:];raise
    return True


def _run(e):
    np=e.np;_certify(e)
    while True:
        e.b.check();quality=e.incumbent is not None
        pressure=np.zeros(e.n,dtype=np.float64)
        for i,(u,v) in enumerate(e.edges):
            amount=e.weights[i]*e.state.gaps[i];pressure[u]+=amount;pressure[v]+=amount
        order=sorted(range(e.n),key=lambda u:(-pressure[u],e.srank[u]))
        sweep=dict(index=len(e.sweeps),quality=quality,status='running',Q_before=e.state.Q,missing_before=e.state.missing,
                   visits_completed=0,commits=0)
        e.sweeps.append(sweep);transition=False
        try:
            for u in order:
                e.b.check();began,cpu=time.perf_counter(),time.process_time()
                row=dict(owner=u,sweep=sweep['index'],quality=e.incumbent is not None,status='running',
                         Q_before=e.state.Q,missing_before=e.state.missing,proposal_complete=False,committed=False)
                e.visits.append(row)
                try:
                    proposed,delta=_propose(e,u,row['quality'],row)
                    median=float(np.median(e.weights)) if len(e.weights) else 2.
                    fraction=max(0.,1.-(time.perf_counter()-e.started)/max(e.search_seconds,1e-300))
                    temperature=median*fraction*fraction
                    if _accept(delta,temperature,row['quality'],e.state,proposed,e.rng,row):
                        _publish(e,proposed,row);sweep['commits']+=1
                        was_valid=e.incumbent is not None;_certify(e)
                        if not was_valid and e.incumbent is not None:transition=True
                    else:row['status']='rejected'
                    e.b.check();sweep['visits_completed']+=1
                except _Deadline:
                    row['interrupted']=True
                    if not row['committed']:row['status']='interrupted'
                    raise
                finally:row.update(wall=time.perf_counter()-began,cpu=time.process_time()-cpu,
                                   elapsed=time.perf_counter()-e.started)
                if transition:break
            if transition:sweep['status']='first_valid_transition';continue
            if quality and not sweep['commits']:
                sweep['status']='policy_exhausted';return 'valid_policy_exhausted'
            if not quality:
                missing=np.flatnonzero(e.state.counts==0)
                e.weights[missing]+=1.
                if not bool(np.all(np.isfinite(e.weights))):raise RuntimeError('nonfinite edge weights')
                sweep['raised_weights']=[int(i) for i in missing]
            sweep['status']='complete';e.b.check()
        except _Deadline:
            if sweep['status']=='running':sweep['status']='interrupted'
            raise


def _embed(source,target,seed,timeout,deadline,old_roots):
    started,cpu=time.perf_counter(),time.process_time()
    diag=dict(algorithm='territory_relocation',policy='C018',old_territory_roots=old_roots,
              work_limit=None,fatal_error=False,first_valid=None,incumbent_events=[],visits=[],sweeps=[])
    response=dict(status='FAILURE',embedding={},diag=diag);e=b=helper=None;absolute=None
    sl=tl=[]
    try:
        if type(seed) is not int or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
            raise ValueError('integer seed and positive finite timeout required')
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise ValueError('finite deadline required')
        absolute=min(started+timeout,deadline) if deadline is not None else started+timeout
        reserve=min(.5,timeout/10);b=_Budget(absolute-reserve)
        diag.update(started=started,deadline=absolute,search_deadline=b.deadline,final_reserve=reserve)
        with b.stage('support_imports'):helper,kernels=_support()
        with b.stage('input'):
            sl,src=helper._adjacency(source,b);tl,adj=helper._adjacency(target,b)
            if len(src)>len(adj):raise helper._Failed('more source owners than target sites')
        rng=random.Random(seed)
        with b.stage('initialization'):
            chains,_=helper._initialize(src,adj,rng,b,diag) if src else ([],0)
        with b.stage('state_setup'):
            e=_Engine(src,adj,chains,seed,b,helper,kernels,rng,started,old_roots)
            diag['initial']=e.snapshot()
        diag['stop_reason']=_run(e)
    except _Deadline as exc:
        response['status']='TIMEOUT';diag.update(stop_reason='search_deadline',interrupted_stage=str(exc))
    except Exception as exc:
        if helper is not None and isinstance(exc,helper._Expired):
            response['status']='TIMEOUT';diag.update(stop_reason='search_deadline',interrupted_stage=str(exc))
        else:
            expected=isinstance(exc,ValueError) or (helper is not None and isinstance(exc,helper._Failed))
            response.update(status='FAILURE' if expected else 'ERROR',error=type(exc).__name__+': '+str(exc))
            diag.update(fatal_error=not expected,stop_reason='input_rejected' if expected else 'exception')
    if b is not None:
        b.deadline=absolute
        if e is not None:
            diag.update(visits=e.visits,sweeps=e.sweeps,incumbent_events=e.events,
                        first_valid=e.events[0] if e.events else None)
            try:
                with b.stage('final_validation_output'):
                    diag['terminal']=e.snapshot();diag['weights']=[float(w) for w in e.weights];b.check()
                    if e.incumbent is not None and not response.get('error'):
                        chains={u:set(map(int,c)) for u,c in enumerate(e.incumbent.chains)}
                        if not e.helper._valid(chains,e.src,e.adj,b):raise RuntimeError('incumbent failed final validation')
                        mapping={sl[u]:[tl[int(q)] for q in c] for u,c in enumerate(e.incumbent.chains)}
                        b.check();response.update(status='SUCCESS',embedding=mapping)
                        diag['final_Q']=e.incumbent.Q
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


def territory_relocation_embed(source,target,*,seed=0,timeout=60.,deadline=None):
    return _embed(source,target,seed,timeout,deadline,False)


def territory_old_roots_embed(source,target,*,seed=0,timeout=60.,deadline=None):
    return _embed(source,target,seed,timeout,deadline,True)
