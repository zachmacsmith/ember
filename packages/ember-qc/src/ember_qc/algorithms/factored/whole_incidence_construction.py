"""B022 standalone whole-incidence constructor; standard library only.

Jointly replaces two complete trees and every incident contact binding.
Uses B019 normalization/initialization/accounting in this standalone copy.
See b_022_whole_incidence_policy.md; no other constructor is imported or called.
"""
from collections import Counter, deque
from heapq import heappop, heappush
from itertools import product
from math import isfinite
from random import Random
from time import perf_counter


class _Stop(Exception):
    pass


class _Meter:
    def __init__(self, deadline, limit=19_000_000):
        self.deadline = deadline
        self.limit = limit
        self.work = 0
        self.stage = "setup"
        self.counts = Counter()
        self.query_start = None
        self.query_deadline = None
        self.query_limit = 100_000

    def clock(self):
        now = perf_counter()
        if now >= self.deadline:
            raise _Stop("search_deadline" if self.stage != "finalize" else "final_deadline")
        if self.query_deadline is not None and now >= self.query_deadline:
            raise _Stop("query_deadline")
        return now

    def step(self):
        self.clock()
        if self.work >= self.limit:
            raise _Stop("search_work_limit" if self.stage != "finalize" else "final_work_limit")
        if self.query_start is not None and self.work-self.query_start >= self.query_limit:
            raise _Stop("query_work_limit")
        self.work += 1
        self.counts[self.stage] += 1

    def walk(self, values):
        for value in values:
            self.step()
            yield value


def _adjacency(raw, meter):
    if not isinstance(raw, dict):
        if raw.is_directed() or raw.is_multigraph():
            raise ValueError("simple undirected graph required")
        raw = {u: tuple(meter.walk(raw[u])) for u in meter.walk(raw)}
    if not isinstance(raw, dict):
        raise ValueError("adjacency must be an ordinary dict")
    answer = {}
    for u, ns in raw.items():
        meter.step()
        if type(u) is not int or not isinstance(ns, (tuple, list, set, frozenset)):
            raise ValueError("integer vertices and finite neighbor containers required")
        row = set()
        for v in ns:
            meter.step()
            if type(v) is not int or v == u or v in row:
                raise ValueError("simple loopless integer graph required")
            row.add(v)
        answer[u] = row
    for u, ns in answer.items():
        for v in ns:
            meter.step()
            if v not in answer or u not in answer[v]:
                raise ValueError("symmetric complete adjacency required")
    return answer


def _tree(sites, adjacency, rank, meter):
    if not sites:
        raise ValueError("empty owner chain")
    root = min(meter.walk(sites), key=rank.__getitem__)
    result = {root: set()}
    queue = deque([root])
    while queue:
        q = queue.popleft()
        meter.step()
        for p in adjacency[q]:
            meter.step()
            if p in sites and p not in result:
                result[p] = {q}
                result[q].add(p)
                queue.append(p)
    if len(result) != len(sites):
        raise ValueError("disconnected owner chain")
    return result


def _copy_tree(tree, meter):
    result = {}
    for q, ns in tree.items():
        meter.step()
        result[q] = set()
        for p in ns:
            meter.step()
            result[q].add(p)
    return result


def _trim(tree, required, rank, meter):
    """Private minimal subtree of the supplied tree spanning required sites."""
    if not required:
        return {}
    result = _copy_tree(tree, meter)
    leaves = []
    for q in result:
        meter.step()
        if len(result[q]) <= 1 and q not in required:
            heappush(leaves, (rank[q], q))
    while leaves:
        _, q = heappop(leaves)
        meter.step()
        if q not in result or q in required or len(result[q]) > 1:
            continue
        for p in result[q]:
            meter.step()
            result[p].remove(q)
            if len(result[p]) <= 1 and p not in required:
                heappush(leaves, (rank[p], p))
        del result[q]
    if not required <= result.keys():
        raise ValueError("required terminal absent from tree")
    return result


def _owners(chains, meter):
    result = {}
    for u, chain in chains.items():
        for q in chain:
            meter.step()
            result.setdefault(q, set()).add(u)
    return result




def _increment(q, own, owner, occupancy, prices):
    if q in own:
        return 0
    return 1 + (prices.get(q, 1) if occupancy.has_other(q, owner) else 0)










class _State:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def replace(self, **updates):
        fields = dict(self.__dict__)
        fields.update(updates)
        return _State(**fields)

    def score(self):
        return dict(qubits=self.Q, overlap=self.O, energy=self.E)


class _Overlay:
    """Global outside counts plus at most three private replacement trees."""
    def __init__(self, state, old_counts, replacements):
        self.state, self.old_counts, self.replacements = state, old_counts, replacements

    def has_other(self, q, owner):
        count = len(self.state.owners.get(q, ())) - self.old_counts.get(q, 0)
        # At most three constant-time memberships per inspected physical site.
        return count + sum(q in tree for u, tree in self.replacements.items() if u != owner) > 0


class _Context:
    def __init__(self, source, target, meter, seed):
        self.m = meter
        meter.stage = "normalization"
        self.G = _adjacency(source, meter)
        self.H = _adjacency(target, meter)
        self.vertices = sorted(meter.walk(self.G))
        self.qorder = sorted(meter.walk(self.H))
        Random(seed).shuffle(self.qorder)
        self.rank = {q: i for i, q in enumerate(meter.walk(self.qorder))}
        self.adj = {q: tuple(sorted(meter.walk(self.H[q]), key=self.rank.__getitem__))
                    for q in meter.walk(self.qorder)}
        if len(self.vertices) > len(self.qorder):
            raise ValueError("more source vertices than target sites")
        self.edges = []
        self.incident = {u: [] for u in meter.walk(self.vertices)}
        for u in self.vertices:
            for v in sorted(meter.walk(self.G[u])):
                if u < v:
                    edge = (u, v)
                    self.edges.append(edge)
                    self.incident[u].append(edge); self.incident[v].append(edge)
        for row in self.incident.values():
            row.sort()
        self.edge_order = list(meter.walk(self.edges))
        Random(seed).shuffle(self.edge_order)
        self.edge_rank = {e: i for i, e in enumerate(meter.walk(self.edge_order))}
        self.owner_order = list(meter.walk(self.vertices))
        Random(seed).shuffle(self.owner_order)
        self.owner_rank = {u: i for i, u in enumerate(meter.walk(self.owner_order))}
        self.isolates = [u for u in meter.walk(self.vertices) if not self.G[u]]

    def terms(self, owner, links, overrides=None, excluded=()):
        result = []
        for edge in self.incident[owner]:
            self.m.step()
            if edge not in excluded:
                pair = overrides[edge] if overrides and edge in overrides else links[edge]
                result.append(pair[0 if owner == edge[0] else 1])
        return result

    def check_tree(self, tree):
        if not tree:
            raise ValueError("empty tree")
        root = min(self.m.walk(tree), key=self.rank.__getitem__)
        reached = {root}; queue = [root]; directed = 0
        for q in queue:
            self.m.step()
            if q not in self.H:
                raise ValueError("tree outside target")
            for p in tree[q]:
                self.m.step(); directed += 1
                if p not in tree or p not in self.H[q] or q not in tree[p]:
                    raise ValueError("invalid physical tree edge")
                if p not in reached:
                    reached.add(p); queue.append(p)
        if len(reached) != len(tree) or directed != 2*(len(tree)-1):
            raise ValueError("owner structure is not a tree")

    def state(self, trees, links):
        """Once-validated entry, also used for supplied tiny equivalence checks."""
        if set(trees) != set(self.vertices) or set(links) != set(self.edges):
            raise ValueError("incomplete state")
        terms = {}
        for u in self.vertices:
            self.check_tree(trees[u])
            terms[u] = Counter(self.m.walk(self.terms(u, links)))
        for (u, v), (q, r) in links.items():
            self.m.step()
            if q not in trees[u] or r not in trees[v] or r not in self.H[q]:
                raise ValueError("missing original-edge witness")
        owners = _owners(trees, self.m)
        Q = O = 0
        for group in self.m.walk(owners.values()):
            Q += len(group); O += max(0, len(group)-1)
        h = {u: sum(len(owners[q])-1 for q in self.m.walk(trees[u])) for u in self.vertices}
        return _State(trees=trees, links=links, terms=terms, owners=owners,
                      h=h, Q=Q, O=O, E=Q+O, prices={})

    def initialize(self):
        m = self.m; m.stage = "initialization"
        source_order = []; seen = set()
        priority = sorted(m.walk(self.vertices), key=lambda u: (-len(self.G[u]), u))
        for root in priority:
            m.step()
            if root in seen:
                continue
            seen.add(root); queue = [root]
            for u in queue:
                m.step(); source_order.append(u)
                for v in sorted(m.walk(self.G[u]), key=lambda v: (-len(self.G[v]), v)):
                    if v not in seen:
                        seen.add(v); queue.append(v)
        if not self.qorder:
            return self.state({}, {}), dict(source_order=[], target_order=[], anchors={})
        root = min(m.walk(self.qorder), key=lambda q: (-len(self.H[q]), self.rank[q]))
        parent = {root: None}; depth = {root: 0}; target_order = [root]
        for q in target_order:
            m.step()
            for p in self.adj[q]:
                m.step()
                if p not in parent:
                    parent[p] = q; depth[p] = depth[q]+1; target_order.append(p)
        if len(parent) != len(self.H):
            raise ValueError("disconnected hardware unsupported")
        anchors = dict(zip(m.walk(source_order), target_order))
        trees = {u: {anchors[u]: set()} for u in m.walk(self.vertices)}
        links = {}
        for u, v in self.edges:
            m.step()
            a, b = anchors[u], anchors[v]; left = [a]; right = [b]
            while depth[a] > depth[b]:
                m.step(); a = parent[a]; left.append(a)
            while depth[b] > depth[a]:
                m.step(); b = parent[b]; right.append(b)
            while a != b:
                m.step(); a = parent[a]; b = parent[b]; left.append(a); right.append(b)
            path = list(m.walk(left)) + list(m.walk(reversed(right[:-1])))
            cut = (len(path)-2)//2
            links[(u, v)] = (path[cut], path[cut+1])
            for owner, half in ((u, path[:cut+1]), (v, path[cut+1:])):
                for q in half:
                    m.step(); trees[owner].setdefault(q, set())
                for q, p in zip(half, half[1:]):
                    m.step(); trees[owner][q].add(p); trees[owner][p].add(q)
        for u in self.vertices:
            required = set(m.walk(self.terms(u, links))) or {anchors[u]}
            trees[u] = _trim(trees[u], required, self.rank, m)
        return self.state(trees, links), dict(source_order=source_order, target_order=target_order, anchors=anchors)

    def partner(self, state, owner):
        m = self.m; m.stage = "schedule"
        conflicts = Counter()
        for q in m.walk(state.trees[owner]):
            for other in m.walk(state.owners[q]):
                if other != owner:
                    conflicts[other] += state.prices.get(q, 1)
        if conflicts:
            other = min(m.walk(conflicts), key=lambda v: (-conflicts[v], self.owner_rank[v]))
        elif self.G[owner]:
            other = min(m.walk(self.G[owner]), key=lambda v: (-len(state.trees[v]), self.owner_rank[v]))
        else:
            return None
        return sorted((owner, other), key=self.owner_rank.__getitem__)

    def delta(self, state, replacements):
        old_counts = Counter(); new_counts = Counter()
        for u, tree in replacements.items():
            old_counts.update(self.m.walk(state.trees[u]))
            new_counts.update(self.m.walk(tree))
        Q = state.Q + sum(new_counts.values()) - sum(old_counts.values())
        O, E = state.O, state.E + Q-state.Q
        for q in self.m.walk(old_counts.keys() | new_counts.keys()):
            old = len(state.owners.get(q, ()))
            new = old-old_counts.get(q, 0)+new_counts.get(q, 0)
            change = max(0, new-1)-max(0, old-1)
            O += change; E += state.prices.get(q, 1)*change
        return dict(qubits=Q, overlap=O, energy=E)

    def certify_patch(self, state, replacements, overrides):
        edges = set()
        for u, tree in replacements.items():
            self.check_tree(tree)
            edges.update(self.m.walk(self.incident[u]))
        for edge in self.m.walk(sorted(edges)):
            u, v = edge; q, r = overrides.get(edge, state.links[edge])
            if q not in replacements.get(u, state.trees[u]) or r not in replacements.get(v, state.trees[v]) or r not in self.H[q]:
                raise ValueError("changed tree lost an original contact")

    def prepare_commit(self, state, replacements, overrides, score):
        """Stage full shallow maps and changed values; caller swaps one pointer."""
        m = self.m
        trees = dict(m.walk(state.trees.items())); trees.update(replacements)
        links = dict(m.walk(state.links.items())); links.update(overrides)
        terms = dict(m.walk(state.terms.items()))
        owners = dict(m.walk(state.owners.items()))
        h = dict(m.walk(state.h.items()))
        affected = set()
        for u, tree in replacements.items():
            affected.update(m.walk(state.trees[u])); affected.update(m.walk(tree))
        copied_terms = set()
        for edge, pair in m.walk(overrides.items()):
            for u, old_site, new_site in m.walk(zip(edge, state.links[edge], pair)):
                if old_site == new_site:
                    continue
                if u not in copied_terms:
                    terms[u] = Counter(dict(m.walk(state.terms[u].items())))
                    copied_terms.add(u)
                terms[u][old_site] -= 1
                if not terms[u][old_site]:
                    del terms[u][old_site]
                terms[u][new_site] += 1
        for q in m.walk(affected):
            old = state.owners.get(q, set())
            new = {u for u in m.walk(old) if u not in replacements}
            new.update(u for u in m.walk(replacements) if q in replacements[u])
            for u in m.walk(old):
                h[u] -= len(old)-1
            for u in m.walk(new):
                h[u] += len(new)-1
            if new:
                owners[q] = new
            else:
                owners.pop(q, None)
        m.clock()
        return state.replace(trees=trees, links=links, terms=terms, owners=owners, h=h,
                             Q=score['qubits'], O=score['overlap'], E=score['energy'])

    def contacts(self, state, trees, edges):
        """Actual oriented couplers; outside trees fixed, no retained bindings."""
        m = self.m; selected = set(trees); links = {}
        for u in sorted(m.walk(trees), key=self.owner_rank.__getitem__):
            for q in m.walk(trees[u]):
                for r in m.walk(self.adj[q]):
                    others = [v for v in m.walk(state.owners.get(r, ())) if v not in selected]
                    others.extend(v for v in m.walk(selected) if v != u and r in trees[v])
                    for v in m.walk(others):
                        if v not in self.G[u]:
                            continue
                        edge = (min(u,v), max(u,v))
                        pair = (q,r) if u == edge[0] else (r,q)
                        old = links.get(edge)
                        if old is None or (self.rank[pair[0]],self.rank[pair[1]]) < (self.rank[old[0]],self.rank[old[1]]):
                            links[edge] = pair
        missing = [edge for edge in m.walk(edges) if edge not in links]
        return links, missing

    def signature(self, trees):
        return tuple(tuple(self.rank[q] for q in sorted(self.m.walk(trees[u]), key=self.rank.__getitem__))
                     for u in sorted(self.m.walk(trees), key=self.owner_rank.__getitem__))

    def routes(self, state, trees, old_counts, owner, goals, count, record, internal=False):
        m = self.m; began = perf_counter(); start = m.work
        receipt = dict(owner=owner, internal=internal, requested=count, goals=len(goals), complete=False, paths=[])
        record['routes'].append(receipt)
        overlay = _Overlay(state, old_counts, trees)
        own = trees[owner]; distance = {}; parent = {}; heap = []; paths = []
        try:
            for q in sorted(m.walk(own), key=self.rank.__getitem__):
                distance[q] = 0; parent[q] = None; heappush(heap,(0,self.rank[q],q))
            needed = min(count, len(goals))
            while heap and len(paths) < needed:
                cost, _, q = heappop(heap); m.step()
                if cost != distance[q]:
                    continue
                if q in goals:
                    path = [q]; p = q
                    while parent[p] is not None:
                        m.step(); p = parent[p]; path.append(p)
                    path.reverse(); paths.append(path)
                    receipt['paths'].append(dict(sites=list(m.walk(path)), cost=cost))
                    if internal or len(paths) == needed:
                        break
                for p in m.walk(self.adj[q]):
                    if p in own:
                        continue
                    if internal and p in goals:
                        increment = 0
                    else:
                        increment = _increment(p, own, owner, overlay, state.prices)
                    candidate = cost+increment
                    if p not in distance or candidate < distance[p]:
                        distance[p] = candidate; parent[p] = q
                        heappush(heap,(candidate,self.rank[p],p))
            receipt.update(complete=True, settled_paths=len(paths))
            return paths
        finally:
            receipt.update(work=m.work-start, wall=perf_counter()-began)

    def extend(self, tree, path):
        result = _copy_tree(tree, self.m)
        for q in self.m.walk(path):
            result.setdefault(q,set())
        for a,b in self.m.walk(zip(path,path[1:])):
            result[a].add(b); result[b].add(a)
        return result

    def query(self, state, selected):
        m = self.m; began = perf_counter(); start = m.work
        m.query_start = start; m.query_deadline = min(m.deadline,began+5)
        deadline = m.query_deadline
        record = dict(selected=list(selected), scope='all_incident_bindings', edges=[], entry=state.score(),
                      started=began, deadline=deadline, start_work=start, accepted=False,
                      root_pools=[], routes=[], layers=[], proposals=[], eligible_proposals=0,
                      discarded_eligible=0, completed_states=0, generated_states=0)
        prepared = best = best_key = None
        try:
            m.stage = 'query_preparation'
            selected = sorted(m.walk(selected), key=self.owner_rank.__getitem__)
            if len(selected)!=2 or selected[0]==selected[1]:
                raise ValueError('two distinct selected owners required')
            chosen = set(selected); edges = set(); old_counts = Counter()
            for u in m.walk(selected):
                edges.update(m.walk(self.incident[u])); old_counts.update(m.walk(state.trees[u]))
            edges = sorted(m.walk(edges)); record['edges'] = edges
            boundaries = {}
            for u in m.walk(selected):
                for w in sorted(m.walk(self.G[u])):
                    if w in chosen or w in boundaries:
                        continue
                    boundary = set()
                    for q in m.walk(state.trees[w]):
                        boundary.update(m.walk(self.adj[q]))
                    boundaries[w] = boundary
            m.stage = 'query_roots'; pools = []
            for u in selected:
                region = set(m.walk(state.trees[u]))
                for q in m.walk(state.trees[u]):
                    region.update(m.walk(self.adj[q]))
                for w in m.walk(self.G[u]):
                    if w not in chosen:
                        region.update(m.walk(boundaries[w]))
                ranked = []
                for q in m.walk(region):
                    contacted = set()
                    for r in m.walk(self.adj[q]):
                        for w in m.walk(state.owners.get(r,())):
                            if w not in chosen and w in self.G[u]:
                                contacted.add(w)
                    occupied = len(state.owners.get(q,()))-old_counts.get(q,0)>0
                    ranked.append((1+(state.prices.get(q,1) if occupied else 0),-len(contacted),self.rank[q],q))
                ranked.sort(); m.clock()
                pool = [item[3] for item in m.walk(ranked[:4])]; pools.append(pool)
                record['root_pools'].append(dict(owner=u,region=len(region),sites=pool))
            initial = []
            for a,b in product(*pools):
                m.step()
                if a!=b:
                    initial.append({selected[0]:{a:set()},selected[1]:{b:set()}})

            def inspect(trees, layer):
                nonlocal best,best_key
                m.stage = 'query_contacts'
                links, missing = self.contacts(state,trees,edges)
                score = self.delta(state,trees); signature = self.signature(trees)
                record['generated_states'] += 1
                if missing:
                    return (len(missing),score['energy'],score['overlap'],score['qubits'],signature),trees,missing
                record['completed_states'] += 1
                m.stage = 'query_certificate'
                rebuilt = {}
                for u in selected:
                    required = set()
                    for edge in m.walk(self.incident[u]):
                        required.add(links[edge][0 if edge[0]==u else 1])
                    if not required:
                        required = {min(m.walk(trees[u]),key=self.rank.__getitem__)}
                    rebuilt[u] = _trim(trees[u],required,self.rank,m)
                self.certify_patch(state,rebuilt,links)
                score = self.delta(state,rebuilt)
                eligible = (score['overlap']==0 and score['qubits']<state.Q) if state.O==0 else score['energy']<state.E
                entry = dict(layer=layer,score=score,eligible=eligible,complete=True)
                record['proposals'].append(entry)
                record['eligible_proposals'] += bool(eligible)
                key = (score['energy'],score['overlap'],score['qubits'],
                       tuple((self.rank[links[e][0]],self.rank[links[e][1]]) for e in m.walk(edges)),self.signature(rebuilt))
                if eligible and (best_key is None or key<best_key):
                    best = (rebuilt,links,score); best_key = key
                    record['best_proposal'] = len(record['proposals'])-1
                return None

            def layer_filter(children, layer):
                dedup = {}; seen = set(); complete_before = record['completed_states']; count = 0
                for trees in children:
                    m.step(); count += 1
                    signature = self.signature(trees)
                    if signature in seen:
                        continue
                    seen.add(signature)
                    item = inspect(trees,layer)
                    if item is not None:
                        dedup.setdefault(item[0][-1],item)
                ranked = sorted(m.walk(dedup.values()),key=lambda item:item[0]); m.clock()
                completed = record['completed_states']-complete_before
                record['layers'].append(dict(layer=layer,generated=count,distinct_partial=len(ranked),complete=completed,retained=0 if completed else min(4,len(ranked))))
                return [] if completed else ranked[:4]

            beam = layer_filter(initial,0)
            layer = 0
            while beam:
                layer += 1; children = []
                for _,trees,missing in beam:
                    m.stage = 'query_obligation'; m.step()
                    internal = [edge for edge in m.walk(missing) if edge[0] in chosen and edge[1] in chosen]
                    if internal:
                        edge = internal[0]; u,v = selected
                        if set(m.walk(trees[u])) & trees[v].keys():
                            raise ValueError('unsatisfied internal edge has overlapping trees')
                        m.stage = 'query_routes'
                        paths = self.routes(state,trees,old_counts,u,set(m.walk(trees[v])),1,record,internal=True)
                        for path in paths:
                            cuts = sorted({0,(len(path)-2)//2,len(path)-2})
                            for cut in m.walk(cuts):
                                children.append({u:self.extend(trees[u],path[:cut+1]),v:self.extend(trees[v],path[cut+1:])})
                    else:
                        def obligation_rank(edge):
                            w = edge[1] if edge[0] in chosen else edge[0]
                            return len(boundaries[w]),edge
                        edge = min(m.walk(missing),key=obligation_rank)
                        u = edge[0] if edge[0] in chosen else edge[1]; w = edge[1] if u==edge[0] else edge[0]
                        m.stage = 'query_routes'
                        paths = self.routes(state,trees,old_counts,u,boundaries[w],3,record)
                        for path in paths:
                            child = dict(trees); child[u] = self.extend(trees[u],path); children.append(child)
                beam = layer_filter(children,layer)
                if layer>len(edges):
                    raise ValueError('contact growth did not terminate')
            if best is not None:
                m.stage = 'query_commit'
                self.certify_patch(state,best[0],best[1])
                prepared = self.prepare_commit(state,*best)
                record['changed_witnesses'] = sum(state.links[e]!=prepared.links[e] for e in m.walk(edges))
                m.clock()
            record['status'] = 'proposal' if prepared is not None else 'no_improvement'
        except _Stop as exc:
            record.update(status=str(exc),interrupted_stage=m.stage); prepared = None
        except Exception as exc:
            record.update(status='query_error',error=repr(exc),interrupted_stage=m.stage); prepared = None
        ended = perf_counter()
        if ended>=deadline:
            record['status'] = 'search_deadline' if ended>=m.deadline else 'query_deadline'; prepared = None
        if prepared is None:
            record['discarded_eligible'] = record['eligible_proposals']
        record['certified_proposals'] = len(record['proposals'])
        record.update(returned=ended,wall=ended-began,work=m.work-start,end_work=m.work,deadline_overrun=max(0.0,ended-deadline))
        m.query_start = m.query_deadline = None
        return prepared,record

    def relocate_isolates(self, state, records):
        m = self.m; m.stage = "isolates"
        for u in self.isolates:
            m.step()
            old = next(iter(state.trees[u]))
            if len(state.owners[old]) <= 1:
                continue
            start = m.work; began = perf_counter(); site = None
            for q in self.qorder:
                m.step()
                if q not in state.owners:
                    site = q; break
            if site is None:
                records.append(dict(owner=u, accepted=False, reason='no_free_site', work=m.work-start))
                continue
            replacements = {u: {site: set()}}
            score = self.delta(state, replacements)
            proposed = self.prepare_commit(state, replacements, {}, score)
            m.clock()
            records.append(dict(owner=u, old=old, new=site, accepted=True,
                                entry=state.score(), final=score, work=m.work-start,
                                wall=perf_counter()-began))
            state = proposed
            yield state

    def raise_prices(self, state):
        m = self.m; m.stage = "prices"
        prices = dict(m.walk(state.prices.items()))
        energy = state.Q
        for q, owners in state.owners.items():
            m.step()
            excess = len(owners)-1
            if excess:
                prices[q] = prices.get(q,1)+excess
                energy += prices[q]*excess
        m.clock()
        return state.replace(prices=prices, E=energy)

    def full_minor(self, state):
        """Original-edge oracle at return, independent of witness assignments."""
        m = self.m
        if set(state.trees) != set(self.vertices):
            return 'source_coverage'
        owners = {}
        for u in self.vertices:
            tree = state.trees[u]
            if not tree:
                return 'empty_chain'
            for q in tree:
                m.step()
                if q not in self.H or q in owners:
                    return 'membership_or_overlap'
                owners[q] = u
            first = min(m.walk(tree), key=self.rank.__getitem__)
            seen = {first}; queue = [first]
            for q in queue:
                m.step()
                for p in self.adj[q]:
                    m.step()
                    if p in tree and p not in seen:
                        seen.add(p); queue.append(p)
            if len(seen) != len(tree):
                return 'disconnected_chain'
        contacts = set()
        for q, u in owners.items():
            m.step()
            for p in self.adj[q]:
                m.step()
                v = owners.get(p)
                if v is not None and v != u:
                    contacts.add((min(u,v), max(u,v)))
        for edge in self.edges:
            m.step()
            if edge not in contacts:
                return 'missing_logical_edge'
        return None

    def snapshot(self, state, output):
        """Retain a truthful partial snapshot if finalization is interrupted."""
        output.update(embedding={}, witnesses=[], prices={}, complete=False)
        for u in self.vertices:
            output['embedding'][u] = sorted(self.m.walk(state.trees[u]), key=self.rank.__getitem__)
        for edge in self.edges:
            self.m.step()
            output['witnesses'].append([list(edge), list(state.links[edge])])
        for q, price in self.m.walk(state.prices.items()):
            output['prices'][q] = price
        output['complete'] = True


def contact_embed(source, target, *, timeout=60.0, deadline=None, seed=0):
    """One bounded evolving contact/tree state, with explicit failed outputs."""
    began = perf_counter()
    info = dict(algorithm='whole-incidence-trees', version='B022', seed=seed,
                queries=[], isolates=[], sweeps=[], trajectory=[], error=None,
                stopped_by=None, limits=dict(global_work=20_000_000, search_work=19_000_000,
                                            query_work=100_000, query_seconds=5, sweeps=8, roots_per_owner=4, beam=4, routes=3))
    m = ctx = state = None
    embedding = {}; status = 'FAILURE'
    absolute = began
    try:
        if type(timeout) not in (int,float) or not isfinite(timeout) or timeout <= 0 or type(seed) is not int:
            raise ValueError('positive finite timeout and integer seed required')
        absolute = began+timeout
        if deadline is not None:
            if type(deadline) not in (int,float) or not isfinite(deadline):
                raise ValueError('finite absolute deadline required')
            absolute = min(absolute, deadline)
        reserve = min(1.0, .05*timeout)
        search_deadline = absolute-reserve
        info.update(started=began, deadline=absolute, search_deadline=search_deadline,
                    final_reserve_seconds=reserve)
        m = _Meter(search_deadline)
        ctx = _Context(source,target,m,seed)
        state, init_order = ctx.initialize()
        info.update(initial=state.score(), initialization_work=m.work,
                    initialization_wall=perf_counter()-began,
                    initialization_orders=init_order, initially_feasible=state.O==0)
        info['initial_state'] = {}
        try:
            ctx.snapshot(state, info['initial_state'])
        finally:
            info['initialization_work'] = m.work
            info['initialization_wall'] = perf_counter()-began
        for sweep in range(8):
            sweep_started = perf_counter(); sweep_work = m.work
            commits = 0; all_complete = True
            before_isolates = len(info['isolates'])
            for moved in ctx.relocate_isolates(state, info['isolates']):
                state = moved
            commits += sum(r['accepted'] for r in info['isolates'][before_isolates:])
            for owner in ctx.owner_order:
                m.clock()
                selected = ctx.partner(state, owner)
                if selected is None:
                    continue
                proposed, row = ctx.query(state, selected)
                row.update(sweep=sweep, primary_owner=owner)
                info['queries'].append(row)
                if row['status'] == 'query_error':
                    info['error'] = row['error']
                    raise _Stop('query_error')
                if proposed is not None and perf_counter() < row['deadline']:
                    old = state.score()
                    changed_witnesses = row['changed_witnesses']
                    state = proposed; row['accepted'] = True; commits += 1
                    info['trajectory'].append(dict(query=len(info['queries'])-1, before=old,
                                                    after=state.score(), changed_witnesses=changed_witnesses))
                elif proposed is not None:
                    row['status'] = 'outer_query_deadline'; row['discarded_eligible'] = row['eligible_proposals']; proposed = None
                if row['status'] not in ('proposal','no_improvement'):
                    all_complete = False
                if row['status'] in ('search_deadline','search_work_limit'):
                    raise _Stop(row['status'])
            summary = dict(sweep=sweep, commits=commits, all_queries_complete=all_complete,
                           final=state.score(), work=m.work-sweep_work,
                           wall=perf_counter()-sweep_started)
            info['sweeps'].append(summary)
            if state.O == 0 and all_complete and commits == 0:
                info['stopped_by'] = 'feasible_fixed_point'; break
            if state.O:
                state = ctx.raise_prices(state)
                summary['after_price_energy'] = state.E
        else:
            info['stopped_by'] = 'sweep_limit'
    except _Stop as exc:
        info['stopped_by'] = str(exc)
    except (ValueError, TypeError, KeyError) as exc:
        info.update(stopped_by='invalid_input_or_state', error=str(exc))
    except Exception as exc:
        info.update(stopped_by='error', error=repr(exc))
    if m is not None:
        # All prior work remains in this meter; only its reserved final limits change.
        m.query_start = m.query_deadline = None
        m.deadline = absolute; m.limit = 20_000_000; m.stage = 'finalize'
        final_start = m.work; final_began = perf_counter()
        try:
            if state is not None:
                info['final'] = state.score()
                info['resolved_initial_overlap'] = bool(info.get('initial',{}).get('overlap',0)>0 and state.O==0)
                if not info['error'] and state.O==0:
                    reason = ctx.full_minor(state)
                    info['final_validation'] = reason
                    if reason is None:
                        for u in ctx.vertices:
                            embedding[u] = sorted(m.walk(state.trees[u]), key=ctx.rank.__getitem__)
                        status = 'SUCCESS'
                else:
                    info['final_validation'] = 'overlap' if state.O else 'prior_error'
                info['final_state'] = {}
                ctx.snapshot(state, info['final_state'])
            m.clock()
        except _Stop as exc:
            info['finalization_stop'] = str(exc); embedding = {}; status = 'FAILURE'
        except Exception as exc:
            info['finalization_error'] = repr(exc); embedding = {}; status = 'FAILURE'
        info.update(finalization_work=m.work-final_start, finalization_wall=perf_counter()-final_began,
                    work=m.work, stage_units=dict(m.counts), query_work=sum(r['work'] for r in info['queries']),
                    query_wall=sum(r['wall'] for r in info['queries']),
                    eligible_proposals=sum(r['eligible_proposals'] for r in info['queries']),
                    discarded_eligible=sum(r['discarded_eligible'] for r in info['queries']))
    ended = perf_counter()
    if ended >= absolute:
        status = 'TIMEOUT'; embedding = {}
    info.update(wall=ended-began, returned=ended, deadline=absolute,
                deadline_overrun=max(0.0,ended-absolute))
    return dict(embedding=embedding if status=='SUCCESS' else {}, status=status, diag=info)
