"""C013: contact domains and joint retraction on one partial minor.

Only graph normalization/Zephyr parsing/budget and the existing final validator
are reused. No previous constructor is called. Counters never deny work.
"""
from collections import Counter, deque
import heapq
import importlib.util
import math
from pathlib import Path
import random
import time


def _support(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_front = _support('_c013_geometry_support', Path(__file__).with_name('zephyr_frontier.py'))
_backend = _support('_c013_validation_support', Path(__file__).parents[1]/'embedding_backend.py')
_Budget, _Deadline, _InputError = _front._Budget, _front._Deadline, _front._InputError
_graph, _geometry = _front._graph, _front._geometry
_validator = _backend._is_valid_embedding


def _bits(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length()-1
        mask ^= bit


class _Engine:
    def __init__(self, source, target, coords, m, seed, budget):
        self.G, self.H, self.b = source, target, budget
        self.n, self.h = len(source), len(target)
        sr, tr = list(range(self.n)), list(range(self.h))
        rng = random.Random(seed)
        rng.shuffle(sr); rng.shuffle(tr)
        self.sorder, self.torder = sr, tr
        self.srank = {u:i for i,u in enumerate(sr)}
        self.trank = {q:i for i,q in enumerate(tr)}
        self.adj, self.hm, self.center = [], [], []
        for q, ns in enumerate(target):
            budget.tick('target_index', len(ns)+1)
            self.adj.append(sorted(ns, key=self.trank.__getitem__))
            self.hm.append(sum(1 << p for p in ns))
            u,w,k,j,z = coords[q]
            x,y = (w,2*z+j) if u == 0 else (2*z+j,w)
            self.center.append(abs(x-m)+abs(y-m))
        self.all = (1 << self.h)-1
        self.complete = None
        self.complete_score = None
        self.complete_from = None
        self.placements = []
        self.rebuilds = []

    def ordered(self, mask):
        values = list(_bits(mask))
        self.b.tick('ordered_sites', len(values))
        result = sorted(values, key=self.trank.__getitem__)
        self.b.check()
        return result

    def boundary(self, sites):
        mask = 0
        for q in sites:
            self.b.tick('boundary_sites')
            mask |= self.hm[q]
        return mask

    def next(self, state, choices=None):
        eligible = set(state.domains) if choices is None else set(choices)
        self.b.tick('source_order', len(eligible))
        def key(u):
            k = len(self.G[u] & state.I)
            return (not k, state.domains[u].bit_count() if k else 0,
                    -k, -len(self.G[u]), self.srank[u])
        result = min(eligible, key=key)
        self.b.check()
        return result


class _State:
    def __init__(self, engine, chains=None):
        self.e = engine
        self.chains = {u:frozenset(c) for u,c in (chains or {}).items()}
        self.I = set(self.chains)
        self.owner = [-1]*engine.h
        self.masks, self.boundaries, self.keys = {}, {}, {}
        self.Q, self.geom = 0, 0
        for u,c in self.chains.items():
            engine.b.tick('state_memberships', len(c))
            for q in c:
                if not 0 <= q < engine.h or self.owner[q] != -1:
                    raise RuntimeError('foreign site or overlap')
                self.owner[q] = u
            self.masks[u] = sum(1 << q for q in c)
            self.boundaries[u] = engine.boundary(c)
            self.keys[u] = tuple(sorted(engine.trank[q] for q in c))
            self.Q += len(c); self.geom += sum(engine.center[q] for q in c)
        self.free = engine.all
        for mask in self.masks.values(): self.free &= ~mask
        self.contacts = self.recount()
        self.domains = self.domain_map()

    def E(self, v):
        mask = self.e.all
        for u in self.e.G[v] & self.I:
            self.e.b.tick('domain_intersections')
            mask &= self.boundaries[u]
        return mask

    def domain_map(self):
        result = {}
        for v in self.e.sorder:
            self.e.b.tick('domain_vertices')
            if v not in self.I:
                result[v] = self.E(v) & self.free
        return result

    def score(self):
        self.e.b.tick('score_records', len(self.domains)+self.Q+len(self.I))
        ds = [self.domains[v].bit_count() for v in self.e.sorder if v in self.domains]
        z = ds.count(0)
        key = tuple((self.e.srank[v], self.keys[v]) for v in self.e.sorder if v in self.I)
        result = (self.Q+len(ds)+z, z, -math.fsum(math.log1p(d) for d in ds), self.geom, key)
        self.e.b.check()
        return result

    def add(self, v, sites):
        e = self.e
        if v in self.I or not sites:
            raise RuntimeError('non-new or empty birth')
        mask = sum(1 << q for q in sites)
        if mask & ~self.free:
            raise RuntimeError('birth overlaps existing state')
        e.b.tick('proposal_copies', len(self.owner)+len(self.I)+len(self.contacts))
        new = object.__new__(_State)
        new.__dict__ = self.__dict__.copy()
        new.chains = self.chains.copy(); new.chains[v] = frozenset(sites)
        new.I = self.I | {v}
        new.owner = self.owner.copy()
        for q in sites: new.owner[q] = v
        new.masks = self.masks.copy(); new.masks[v] = mask
        new.boundaries = self.boundaries.copy(); new.boundaries[v] = e.boundary(sites)
        new.keys = self.keys.copy(); new.keys[v] = tuple(sorted(e.trank[q] for q in sites))
        new.Q = self.Q+len(sites); new.geom = self.geom+sum(e.center[q] for q in sites)
        new.free = self.free & ~mask
        new.contacts = self.contacts.copy()
        for u in e.G[v] & self.I:
            e.b.tick('new_contact_counts', len(sites))
            count = sum((e.hm[q] & self.masks[u]).bit_count() for q in sites)
            if not count: raise RuntimeError('birth lost a required contact')
            new.contacts[tuple(sorted((u,v)))] = count
        new.domains = new.domain_map()
        return new

    def recount(self):
        result = Counter()
        for u in self.I:
            for v in self.e.G[u] & self.I:
                self.e.b.tick('contact_recount_pairs')
                if u < v:
                    result[u,v] = sum((self.e.hm[q] & self.masks[v]).bit_count() for q in self.chains[u])
                    self.e.b.tick('contact_recount_sites', len(self.chains[u]))
        return +result

    def certify(self):
        used = set()
        for u,c in self.chains.items():
            if not c or used & c: raise RuntimeError('empty or overlapping chain')
            used.update(c)
            start = min(c, key=self.e.trank.__getitem__)
            seen, queue = {start}, [start]
            for q in queue:
                for p in self.e.adj[q]:
                    self.e.b.tick('certificate_edges')
                    if p in c and p not in seen: seen.add(p); queue.append(p)
            if seen != c: raise RuntimeError('disconnected chain')
        actual = self.recount()
        if actual != self.contacts: raise RuntimeError('contact counter mismatch')
        if any(not actual[tuple(sorted((u,v)))] for u in self.I for v in self.e.G[u] & self.I):
            raise RuntimeError('missing induced-source contact')
        if self.Q != len(used) or set(self.chains) != self.I:
            raise RuntimeError('state coverage/count mismatch')
        self.e.b.check()

    def snapshot(self):
        return dict(introduced=sorted(self.I), qubits=self.Q,
                    chains={u:sorted(c, key=self.e.trank.__getitem__) for u,c in self.chains.items()},
                    domain_sizes={u:d.bit_count() for u,d in self.domains.items()})


def _roots(state, v, passable):
    e = state.e; required = e.G[v] & state.I
    singleton = state.E(v) & passable
    if singleton:
        return e.ordered(singleton), True
    if not required:
        return e.ordered(passable), True
    # Component qualification is exhaustive for a single chain with others fixed.
    qualifying, remaining = 0, passable
    while remaining:
        start = (remaining & -remaining).bit_length()-1
        component, todo = 1 << start, [start]
        remaining &= ~(1 << start)
        for q in todo:
            e.b.tick('component_edges', len(e.H[q]))
            new = e.hm[q] & remaining
            remaining &= ~new; component |= new; todo.extend(_bits(new))
        if all(component & state.boundaries[u] for u in required):
            qualifying |= component
    pivot = min(required, key=lambda u: ((state.boundaries[u] & passable).bit_count(), e.srank[u]))
    roots = list(_bits(state.boundaries[pivot] & qualifying))
    e.b.tick('root_order', len(roots))
    roots.sort(key=lambda q: (-sum(bool((1 << q) & state.boundaries[u]) for u in required),
                             e.center[q], e.trank[q]))
    e.b.check()
    return roots, False


def _tree(state, v, root, passable, outside=None):
    """One nearest-contact shared tree. Outside sites are guide-only occupancy."""
    e = state.e; required = e.G[v] & state.I
    tree, parents = {root}, {root:None}
    missing = {u for u in required if not (state.boundaries[u] & (1 << root))}
    while missing:
        e.b.tick('contact_extensions')
        goals = {}
        for u in sorted(missing, key=e.srank.__getitem__):
            for q in _bits(state.boundaries[u] & passable):
                e.b.tick('goal_sites')
                goals.setdefault(q, u)
        pred = {q:None for q in tree}
        if outside is None:
            queue = deque(sorted(tree, key=e.trank.__getitem__))
            dist = {q:0 for q in tree}; hits = []; best = None
            while queue:
                q = queue.popleft(); e.b.tick('bfs_sites')
                if best is not None and dist[q] > best: break
                if q in goals:
                    best = dist[q]; hits.append(q); continue
                for p in e.adj[q]:
                    e.b.tick('bfs_edges')
                    if passable & (1 << p) and p not in pred:
                        pred[p] = q; dist[p] = dist[q]+1; queue.append(p)
        else:
            dist = {q:(0,0) for q in tree}
            heap = [(0,0,e.trank[q],q) for q in tree]; heapq.heapify(heap)
            hits, best = [], None
            while heap:
                a,d,_,q = heapq.heappop(heap); e.b.tick('guide_sites')
                if dist.get(q) != (a,d): continue
                if best is not None and (a,d) > best: break
                if q in goals:
                    best = (a,d); hits.append(q); continue
                for p in e.adj[q]:
                    e.b.tick('guide_edges')
                    if not passable & (1 << p): continue
                    cost = (a+int(state.owner[p] in outside), d+1)
                    if cost < dist.get(p, (math.inf,math.inf)):
                        dist[p] = cost; pred[p] = q
                        heapq.heappush(heap, (*cost,e.trank[p],p))
        if not hits: return None
        goal = min(hits, key=lambda q: (e.srank[goals[q]],e.trank[q]))
        path, q = [], goal
        while q not in tree:
            e.b.tick('path_records'); path.append(q); q = pred[q]
        for p in reversed(path): parents[p] = q; tree.add(p); q = p
        mask = sum(1 << q for q in tree)
        missing = {u for u in missing if not state.boundaries[u] & mask}
    # A root may be removed like any other unneeded tree leaf.
    links = {q:set() for q in tree}
    for q,p in parents.items():
        if p is not None: links[q].add(p); links[p].add(q)
    while len(tree) > 1:
        removed = False
        for q in sorted(tree, key=e.trank.__getitem__):
            e.b.tick('pruning_visits')
            if len(links[q]) > 1: continue
            rest = sum(1 << p for p in tree if p != q)
            if all(state.boundaries[u] & rest for u in required):
                for p in links[q]: links[p].remove(q)
                del links[q]; tree.remove(q); removed = True; break
        if not removed: break
    return frozenset(tree)


def _place(state, v, *, outside=None, context='ordinary'):
    e = state.e; guide = outside is not None
    row = dict(kind='guide' if guide else 'place', context=context, source=v,
               introduced=len(state.I), Q_before=state.Q, roots_generated=0,
               roots_completed=0, exhaustive=False, best_score=None)
    e.placements.append(row)
    started, cpu = e.b.clock(), time.process_time()
    best, best_score = None, None
    try:
        passable = state.free
        if guide:
            for u in outside: passable |= state.masks[u]
        roots, singleton = _roots(state, v, passable)
        row.update(roots_generated=len(roots), singleton=singleton)
        for root in roots:
            e.b.tick('root_attempts')
            chain = frozenset((root,)) if singleton else _tree(state,v,root,passable,outside)
            if chain is None: raise RuntimeError('qualified component did not yield a tree')
            if guide:
                score = (sum(state.owner[q] in outside for q in chain), len(chain),
                         sum(e.center[q] for q in chain), tuple(sorted(e.trank[q] for q in chain)))
                proposal = chain
            else:
                proposal = state.add(v,chain)
                score = proposal.score()
            row['roots_completed'] += 1
            if best_score is None or score < best_score:
                if not guide and len(proposal.I) == e.n:
                    proposal.certify(); e.b.check()
                    if e.complete_score is None or score < e.complete_score:
                        e.complete, e.complete_score, e.complete_from = proposal,score,row
                best, best_score = proposal,score
                row['best_score'] = score
        row.update(exhaustive=True, status='success' if best is not None else 'failure')
        if guide and best is not None:
            row['guide_sites'] = sorted(best, key=e.trank.__getitem__)
            row['outside_owners'] = sorted({state.owner[q] for q in best if state.owner[q] in outside})
        if not guide and best is not None:
            row['Q_after'] = best.Q
            row['newly_empty'] = _lost(state,best)
        return best
    except _Deadline:
        row.update(status='interrupted', exhaustive=False)
        raise
    except Exception as exc:
        row.update(status='error', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        row.update(wall=e.b.clock()-started, cpu=time.process_time()-cpu)


def _lost(before, after):
    return sorted((u for u in after.domains if before.domains.get(u,0) and not after.domains[u]),
                  key=before.e.srank.__getitem__)


def _transaction(entry, v, ordinary, row):
    e = entry.e
    lost = _lost(entry,ordinary) if ordinary is not None else []
    if ordinary is not None:
        w = min(lost, key=lambda u: (entry.domains[u].bit_count(),e.srank[u]))
        K = (e.G[v] | e.G[w]) & entry.I
        K |= {entry.owner[q] for q in _bits(ordinary.E(w)) if entry.owner[q] in entry.I}
        row['threatened'] = w
    else:
        K = e.G[v] & entry.I
        K |= {entry.owner[q] for q in _bits(entry.E(v)) if entry.owner[q] in entry.I}
    row.update(initial_K=sorted(K), attempts=[])
    while True:
        e.b.check()
        attempt = dict(K=sorted(K), reintroduced=[], status='started')
        row['attempts'].append(attempt)
        private = _State(e,{u:c for u,c in entry.chains.items() if u not in K})
        private.certify()
        todo, x = K | {v}, v
        while todo:
            candidate = _place(private,x,context='rebuild')
            if candidate is None: break
            private = candidate; todo.remove(x); attempt['reintroduced'].append(x)
            if todo: x = e.next(private,todo)
        if not todo:
            private.certify()
            if private.I != entry.I | {v}: raise RuntimeError('rebuild changed introduced set')
            attempt.update(status='complete', Q=private.Q, score=private.score())
            chosen = private if ordinary is None or private.score() < ordinary.score() else ordinary
            row.update(status='rebuilt' if chosen is private else 'ordinary_preferred',
                       rebuilt_score=private.score())
            return chosen
        attempt.update(status='placement_failed', failed_source=x)
        outside = entry.I-K
        if not outside:
            row['status'] = 'rebuild_failed_no_outside'
            return ordinary
        # _place returned None, so its scan completed exhaustively. Interruption
        # raises before this point and must never invoke/interpret a guide.
        guide = _place(private,x,outside=outside,context='obstruction')
        if guide is None:
            row['status'] = 'rebuild_failed_no_guide'
            return ordinary
        added = {private.owner[q] for q in guide if private.owner[q] in outside}
        if not added:
            raise RuntimeError('zero-owner guide after exhaustive PLACE failure')
        attempt.update(expanded_by=sorted(added), guide_sites=sorted(guide,key=e.trank.__getitem__))
        if added & K: raise RuntimeError('obstruction set did not strictly grow')
        K |= added


def _run(state, diag):
    e = state.e
    while len(state.I) < e.n:
        e.b.check(); v = e.next(state)
        row = dict(source=v, introduced_before=len(state.I), Q_before=state.Q,
                   domains_before={u:d.bit_count() for u,d in state.domains.items()}, status='started')
        diag['publications'].append(row)
        with e.b.stage('ordinary'):
            ordinary = _place(state,v)
        row['ordinary_score'] = ordinary.score() if ordinary is not None else None
        row['newly_empty'] = _lost(state,ordinary) if ordinary is not None else []
        if ordinary is not None and not row['newly_empty']:
            chosen = ordinary; row['status'] = 'ordinary'
        else:
            transaction = dict(source=v, status='started')
            e.rebuilds.append(transaction)
            try:
                with e.b.stage('retraction'):
                    chosen = _transaction(state,v,ordinary,transaction)
            except _Deadline:
                transaction['status'] = 'interrupted'; raise
            row['status'] = transaction['status']
        if chosen is None:
            return state,'construction_obstructed'
        with e.b.stage('publication_certificate'):
            chosen.certify()
            publication_score = chosen.score()
            publication_domains = {u:d.bit_count() for u,d in chosen.domains.items()}
            e.b.check()
        if chosen.I != state.I | {v}: raise RuntimeError('publication is not net one source vertex')
        # Move the root-visible current pointer only after complete certification.
        state = chosen; e.published = state
        row.update(published=True, introduced_after=len(state.I), Q_after=state.Q,
                   score=publication_score, domains_after=publication_domains)
    return state,'complete_introduced_source'


def _final(state, source, target, sl, tl, response):
    e = state.e
    mapping = {}
    for u in e.sorder:
        e.b.tick('final_output_records', len(state.chains.get(u,()))+1)
        if u in state.I: mapping[sl[u]] = [tl[q] for q in sorted(state.chains[u],key=e.trank.__getitem__)]
    response['diagnostic_embedding'] = mapping
    response['diag']['state'] = state.snapshot()
    state.certify(); e.b.check()
    valid = _validator(mapping,source,target.adj)
    e.b.check()
    response['diag']['final'] = dict(valid=valid, introduced=len(state.I), qubits=state.Q)
    if valid and not response.get('error') and not response['diag']['fatal_error']:
        response.update(embedding=mapping,status='SUCCESS')


def contact_domain_embed(source, target, *, seed=0, timeout=60., deadline=None):
    started,cpu = time.perf_counter(),time.process_time()
    response = dict(status='FAILURE', embedding={}, diag=dict(algorithm='contact_domain',policy='C013',
        publications=[], fatal_error=False, work_limit=None,
        restrictions=['singleton_first','one_greedy_tree_per_root','greedy_private_rebuild']))
    e, state, b, absolute = None,None,None,None
    try:
        if type(seed) is not int or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout <= 0:
            raise _InputError('integer seed and positive finite timeout required')
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise _InputError('finite deadline required')
        absolute = min(started+timeout,deadline) if deadline is not None else started+timeout
        reserve = min(.5,timeout/10)
        b = _Budget(absolute-reserve)
        response['diag'].update(deadline=absolute,search_deadline=b.deadline,final_reserve=reserve)
        with b.stage('input_geometry'):
            sl,src = _graph(source,b); tl,adj = _graph(target,b)
            if len(src) > len(adj): raise _InputError('source vertex count exceeds target count')
            m,coords = _geometry(target,tl,adj,b)
            e = _Engine(src,adj,coords,m,seed,b); state = _State(e); e.published = state
            response['diag'].update(source_ranks=e.srank,target_ranks=e.trank,initial=state.snapshot())
        _,response['diag']['stop_reason'] = _run(state,response['diag'])
    except _Deadline as exc:
        response['diag'].update(stop_reason='search_deadline',interrupted_stage=str(exc))
    except Exception as exc:
        expected = isinstance(exc,_InputError)
        response.update(status='FAILURE' if expected else 'ERROR',error=f'{type(exc).__name__}: {exc}')
        response['diag'].update(fatal_error=not expected,exception=dict(type=type(exc).__name__,message=str(exc)))
    if b is not None:
        b.deadline = absolute
        if e is not None and state is not None:
            state = e.published
            if e.complete is not None and not response.get('error'):
                state = e.complete
                response['diag']['complete_private_scan_censored'] = not e.complete_from['exhaustive']
            response['diag'].update(placements=e.placements,rebuilds=e.rebuilds,
                                    published_state=e.published.snapshot())
            try:
                with b.stage('final_validation_output'):
                    _final(state,source,target,sl,tl,response)
            except _Deadline:
                response['embedding'] = {}; response['diag']['final_stop'] = 'deadline'
            except Exception as exc:
                response.update(status='ERROR',embedding={},error=f'{type(exc).__name__}: {exc}')
                response['diag']['fatal_error'] = True
        response['diag'].update(work=dict(b.work),total_work=sum(b.work.values()),
                                stage_wall=dict(b.stage_wall),stage_cpu=dict(b.stage_cpu))
    finished = time.perf_counter()
    response['time'] = finished-started
    response['diag'].update(wall=finished-started,cpu=time.process_time()-cpu,finished=finished)
    if absolute is not None and finished >= absolute:
        response['embedding'] = {}
        if not response['diag']['fatal_error']: response['status'] = 'TIMEOUT'
    return response
