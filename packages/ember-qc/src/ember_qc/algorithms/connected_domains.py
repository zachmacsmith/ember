"""C009: bounded simultaneous coordination of connected-chain alternatives.

Standalone exploratory constructor. No embedder, shared constructor or optimizer
is imported. Soft support is diagnostic; only the original-edge gate credits a map.
"""
from collections import Counter, defaultdict
from contextlib import contextmanager
import heapq
import math
import random
import time


class _Stop(Exception):
    pass


class _Budget:
    def __init__(self, deadline, *, limit=20_000_000, clock=None):
        self.deadline = deadline
        self.limit = limit
        self.clock = clock or time.perf_counter
        self.units = 0
        self.work = Counter()
        self.denied = None
        self.next_check = 0
        self.stage_wall = Counter()

    def check(self):
        if self.clock() >= self.deadline:
            raise _Stop('deadline')
        if self.units > self.limit:
            raise _Stop('work')

    def tick(self, name, amount=1):
        if self.units + amount > self.limit:
            self.denied = dict(name=name, units=amount)
            raise _Stop('work')
        if self.units >= self.next_check:
            self.check()
            self.next_check = self.units + 256
        self.units += amount
        self.work[name] += amount

    @contextmanager
    def stage(self, name):
        started = self.clock()
        try:
            self.check()
            yield
            self.check()
        finally:
            self.stage_wall[name] += self.clock() - started


def _graph(graph, budget):
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError('simple undirected graphs required')
    labels = list(graph.nodes)
    budget.tick('input_nodes', len(labels))
    index = {q: i for i, q in enumerate(labels)}
    adj = [set() for _ in labels]
    for u, v in graph.edges:
        budget.tick('input_edges')
        a, b = index[u], index[v]
        if a == b:
            raise ValueError('self-loops are unsupported')
        adj[a].add(b)
        adj[b].add(a)
    return labels, tuple(tuple(sorted(row)) for row in adj)


def _boundary(chain, adj, budget):
    out = set()
    for q in chain:
        budget.tick('boundary_sites')
        for p in adj[q]:
            budget.tick('boundary_adjacency')
            out.add(p)
    return frozenset(out)


def _contact(chain, boundary, budget):
    for q in chain:
        budget.tick('contact_memberships')
        if q in boundary:
            return True
    return False


def _connected(chain, adj, budget):
    if not chain:
        return False
    allowed = set(chain)
    budget.tick('connectivity_sites', len(chain))
    seen, queue = {min(chain)}, [min(chain)]
    for q in queue:
        for p in adj[q]:
            budget.tick('connectivity_adjacency')
            if p in allowed and p not in seen:
                seen.add(p)
                queue.append(p)
    return len(seen) == len(allowed) == len(chain)


def _stats(chains, src, adj, budget):
    """Full recount, independent of compatibility matrices and probabilities."""
    if len(chains) != len(src):
        raise ValueError('one chain per original source vertex required')
    owners = Counter()
    boundaries = []
    structure = True
    for chain in chains:
        budget.tick('validation_chain')
        budget.tick('validation_membership_records', len(chain))
        if any(type(q) is not int or not 0 <= q < len(adj) for q in chain):
            raise ValueError('invalid target member')
        structure &= _connected(chain, adj, budget)
        for q in chain:
            budget.tick('validation_sites')
            owners[q] += 1
        boundaries.append(_boundary(chain, adj, budget))
    missing = []
    for u, neighbors in enumerate(src):
        for v in neighbors:
            if u < v:
                budget.tick('validation_source_edges')
                if not _contact(chains[v], boundaries[u], budget):
                    missing.append([u, v])
    overlap = sum(max(0, count - 1) for count in owners.values())
    pairs = sum(count * (count - 1) // 2 for count in owners.values())
    budget.tick('validation_owner_totals', len(owners))
    budget.check()
    return dict(valid=structure and not overlap and not missing,
                connected_nonempty=structure, qubits=sum(map(len, chains)),
                missing=len(missing), missing_edges=missing,
                overlap_excess=overlap, overlap_pairs=pairs)


def _signature(chain, ranks):
    return tuple(sorted(ranks[q] for q in chain))


def _probabilities(prob):
    for row in prob:
        if not row or any(not math.isfinite(x) or x < 0 for x in row):
            raise ValueError('invalid probabilities')
        if abs(math.fsum(row) - 1.) > 1e-12:
            raise ValueError('probability row not normalized')


class _Model:
    def __init__(self, domains, src, adj, budget):
        self.domains = tuple(tuple(tuple(sorted(c)) for c in row) for row in domains)
        self.src, self.adj, self.budget = src, adj, budget
        self.bounds, self.unions = [], []
        for row in self.domains:
            if not 1 <= len(row) <= 8 or len(set(row)) != len(row):
                raise ValueError('distinct bounded nonempty domain list required')
            bs = []
            union = set()
            for c in row:
                budget.tick('domain_records', len(c))
                if any(type(q) is not int or not 0 <= q < len(adj) for q in c):
                    raise ValueError('invalid domain target member')
                if not _connected(c, adj, budget):
                    raise ValueError('domain is not a nonempty connected chain')
                b = _boundary(c, adj, budget)
                bs.append(b)
                budget.tick('domain_union_records', len(b))
                union.update(b)
            self.bounds.append(tuple(bs))
            self.unions.append(frozenset(union))
        self.compatibility = {}
        for u, neighbors in enumerate(src):
            for v in neighbors:
                if u >= v:
                    continue
                matrix = []
                for b in self.bounds[u]:
                    row = []
                    for c in self.domains[v]:
                        budget.tick('pair_compatibility')
                        row.append(_contact(c, b, budget))
                    matrix.append(tuple(row))
                self.compatibility[u, v] = tuple(matrix)
                self.compatibility[v, u] = tuple(zip(*matrix))
        budget.check()

    def fields(self, prob):
        if len(prob) != len(self.domains) or any(len(p) != len(d) for p, d in zip(prob, self.domains)):
            raise ValueError('probability/domain shape mismatch')
        _probabilities(prob)
        own, contact, total = [], [], defaultdict(float)
        for v, row in enumerate(self.domains):
            a, b = defaultdict(float), defaultdict(float)
            for i, c in enumerate(row):
                for q in c:
                    self.budget.tick('probability_occupancy')
                    a[q] += prob[v][i]
                for q in self.bounds[v][i]:
                    self.budget.tick('probability_boundary')
                    b[q] += prob[v][i]
            for q, x in a.items():
                self.budget.tick('probability_total')
                total[q] += x
            own.append(dict(a))
            contact.append(dict(b))
        return own, contact, dict(total)

    def costs(self, prob, penalty, fields):
        own, _, total = fields
        costs = []
        for v, row in enumerate(self.domains):
            values = []
            for i, c in enumerate(row):
                missing = 0.
                for u in self.src[v]:
                    compat = self.compatibility[v, u][i]
                    for j, p in enumerate(prob[u]):
                        self.budget.tick('probability_contact')
                        if not compat[j]:
                            missing += p
                overlap = 0.
                for q in c:
                    self.budget.tick('probability_overlap')
                    overlap += max(0., total.get(q, 0.) - own[v].get(q, 0.))
                self.budget.tick('probability_cost')
                values.append(len(c) + penalty * (missing + overlap))
            costs.append(values)
        return costs

    def update(self, prob, penalty):
        costs = self.costs(prob, penalty, self.fields(prob))
        result = []
        for old, row in zip(prob, costs):
            base = min(row)
            exps = []
            for value in row:
                self.budget.tick('probability_exponential')
                exps.append(math.exp(-(value - base)))
            z = math.fsum(exps)
            mixed = [.5 * a + .5 * b / z for a, b in zip(old, exps)]
            norm = math.fsum(mixed)
            self.budget.tick('probability_normalization', len(mixed))
            result.append([x / norm for x in mixed])
        _probabilities(result)
        self.budget.check()
        return result

    def expected(self, prob, fields):
        own, _, total = fields
        q = math.fsum(prob[v][i] * len(c)
                      for v, row in enumerate(self.domains) for i, c in enumerate(row))
        missing = 0.
        for (u, v), matrix in self.compatibility.items():
            if u >= v:
                continue
            for i, row in enumerate(matrix):
                for j, exists in enumerate(row):
                    self.budget.tick('expected_contact')
                    if not exists:
                        missing += prob[u][i] * prob[v][j]
        squares = defaultdict(float)
        for row in own:
            for site, p in row.items():
                self.budget.tick('expected_occupancy')
                squares[site] += p * p
        pairs = math.fsum(max(0., x*x - squares[site]) / 2 for site, x in total.items())
        self.budget.tick('expected_totals', len(total) + sum(map(len, self.domains)))
        unsupported_edges = sum(not any(any(r) for r in m)
                                for (u, v), m in self.compatibility.items() if u < v)
        return dict(qubits=q, missing=missing, overlap_pairs=pairs,
                    edges_without_any_pairwise_support=unsupported_edges)

    def select(self, prob, ranks):
        out = []
        for v, row in enumerate(self.domains):
            self.budget.tick('selection_records', sum(map(len, row)))
            i = min(range(len(row)), key=lambda j: (
                -prob[v][j], len(row[j]), _signature(row[j], ranks[v])))
            out.append(row[i])
        self.budget.check()
        return tuple(out)


def _candidate_score(v, chain, model, prob, penalty, fields):
    own, _, total = fields
    boundary = _boundary(chain, model.adj, model.budget)
    missing, unsupported = 0., []
    for u in model.src[v]:
        supported = False
        for i, c in enumerate(model.domains[u]):
            model.budget.tick('generation_compatibility')
            yes = _contact(c, boundary, model.budget)
            supported |= yes
            if not yes:
                missing += prob[u][i]
        if not supported:
            unsupported.append(u)
    overlap = 0.
    for q in chain:
        model.budget.tick('generation_overlap')
        overlap += max(0., total.get(q, 0.) - own[v].get(q, 0.))
    return len(chain) + penalty * (missing + overlap), unsupported


def _route(chain, goals, adj, ranks, occupancy, budget):
    dist, parent, heap = {}, {}, []
    for q in sorted(chain, key=ranks.__getitem__):
        budget.tick('route_roots')
        dist[q], parent[q] = 0., None
        heapq.heappush(heap, (0., ranks[q], q))
    settled = set()
    while heap:
        budget.tick('route_queue')
        cost, _, q = heapq.heappop(heap)
        if q in settled:
            continue
        settled.add(q)
        if q in goals:
            path = []
            while q is not None:
                budget.tick('route_path')
                path.append(q)
                q = parent[q]
            budget.check()
            return tuple(reversed(path))
        budget.tick('route_neighbor_order', len(adj[q]))
        for p in sorted(adj[q], key=ranks.__getitem__):
            budget.tick('route_adjacency')
            if p in settled:
                continue
            candidate = cost + (0. if p in chain else 1. + occupancy.get(p, 0.))
            if candidate < dist.get(p, math.inf):
                dist[p], parent[p] = candidate, q
                heapq.heappush(heap, (candidate, ranks[p], p))
    budget.check()
    return None


def _regenerate(model, prob, ranks, penalty, incumbent, records):
    fields = model.fields(prob)
    own, contact, total = fields
    result = []
    for v, old in enumerate(model.domains):
        row = dict(owner=v, roots=[], completed=False)
        records.append(row)
        scores = defaultdict(float)
        for u in model.src[v]:
            for q, p in contact[u].items():
                model.budget.tick('root_contact_records')
                scores[q] += p
        occupancy = {}
        for q, x in total.items():
            model.budget.tick('root_occupancy_records')
            occupancy[q] = max(0., x - own[v].get(q, 0.))
        model.budget.tick('root_sort_records', len(model.adj))
        roots = sorted(range(len(model.adj)), key=lambda q: (
            -(scores.get(q, 0.) - occupancy.get(q, 0.)), ranks[v][q]))[:4]
        proposals = []
        for root in roots:
            receipt = dict(root=root, status='started', paths=0)
            row['roots'].append(receipt)
            chain = frozenset((root,))
            value, unsupported = _candidate_score(v, chain, model, prob, penalty, fields)
            key = len(unsupported), value, len(chain), _signature(chain, ranks[v])
            best = chain
            while unsupported:
                u = unsupported[0]
                receipt.update(status='routing', target_owner=u)
                path = _route(chain, model.unions[u], model.adj, ranks[v], occupancy, model.budget)
                if path is None:
                    receipt['status'] = 'no_route'
                    break
                model.budget.tick('generation_union', len(chain) + len(path))
                child = chain.union(path)
                child_value, child_unsupported = _candidate_score(v, child, model, prob, penalty, fields)
                if len(child_unsupported) >= len(unsupported):
                    raise AssertionError('growth failed to add pairwise support')
                child_key = (len(child_unsupported), child_value, len(child),
                             _signature(child, ranks[v]))
                if child_key < key:
                    key, best = child_key, child
                chain, unsupported = child, child_unsupported
                receipt['paths'] += 1
            else:
                receipt['status'] = 'all_neighbor_labels_supported'
            proposals.append(tuple(sorted(best)))
            receipt.update(emitted_Q=len(best), emitted_unsupported=key[0])
        candidates = set(old).union(proposals)
        if incumbent is not None:
            candidates.add(incumbent[v])
        scored = []
        for c in candidates:
            model.budget.tick('domain_dedup_records', len(c))
            value, _ = _candidate_score(v, c, model, prob, penalty, fields)
            scored.append((value, len(c), _signature(c, ranks[v]), c))
        scored.sort()
        kept = [incumbent[v]] if incumbent is not None else []
        for _, _, _, c in scored:
            if c not in kept:
                kept.append(c)
            if len(kept) == 8:
                break
        row.update(completed=True, unique_candidates=len(candidates), kept=len(kept),
                   proposed=len(proposals), duplicate_proposals=len(old)+len(proposals)-len(set(old).union(proposals)))
        result.append(tuple(kept))
    model.budget.check()
    return tuple(result)


def _cleanup(chains, src, adj, ranks, budget, records):
    current = tuple(chains)
    for v, original in enumerate(chains):
        budget.tick('cleanup_order_records', len(original))
        for q in sorted(original, key=ranks[v].__getitem__):
            budget.tick('cleanup_visits')
            if len(current[v]) <= 1:
                continue
            budget.tick('cleanup_chain_copy', len(current) + len(current[v]))
            candidate = list(current)
            candidate[v] = tuple(p for p in current[v] if p != q)
            candidate = tuple(candidate)
            record = dict(owner=v, site=q, committed=False)
            records.append(record)
            # Full gate includes all original edges; no matrix can certify deletion.
            if _stats(candidate, src, adj, budget)['valid']:
                budget.check()
                current = candidate
                record['committed'] = True
                yield current


def _materialize(chains, source_labels, target_labels, budget):
    result = {}
    for u, c in enumerate(chains):
        budget.tick('output_records', len(c)+1)
        result[source_labels[u]] = [target_labels[q] for q in c]
    budget.check()
    return result


def _record_exception(response, exc, *, input_complete):
    expected_input = isinstance(exc, ValueError) and not input_complete
    response.update(status='FAILURE' if expected_input else 'ERROR', embedding={},
                    error=type(exc).__name__+': '+str(exc))
    response['diag']['exception'] = dict(type=type(exc).__name__, message=str(exc),
                                       expected_input=expected_input)
    if not expected_input:
        response['diag']['fatal_error'] = True


def _finish(response, chains, source_labels, target_labels, src, adj, budget, absolute):
    """One reusable final credit gate, including post-copy clock observation."""
    response['diag']['final_chains'] = chains
    stats = _stats(chains, src, adj, budget)
    response['diag']['final'] = stats
    raw = _materialize(chains, source_labels, target_labels, budget)
    response['diagnostic_embedding'] = raw
    observed = budget.clock()
    if (stats['valid'] and observed < absolute and response['status'] != 'ERROR'
            and not response['diag'].get('fatal_error', False)):
        budget.tick('credited_output_records', sum(len(c)+1 for c in raw.values()))
        response.update(status='SUCCESS', embedding={u: list(c) for u, c in raw.items()})
        response.pop('error', None)
    else:
        response['embedding'] = {}
    if budget.clock() >= absolute:
        response.update(status='TIMEOUT', embedding={}, error='late final gate')
    return stats


def domain_embed(source, target, *, seed=0, timeout=15.0, deadline=None):
    """One six-epoch domain search; failures retain diagnostic maps only."""
    started = time.perf_counter()
    diag = dict(algorithm='connected_domains_v1', seed=seed, epochs=[], regeneration=[],
                cleanup=[], source_label_order='supplied nodes; diagnostics use integer ranks',
                domain_cap=8, epoch_cap=6, updates_per_epoch=8, work_cap=20_000_000,
                search_work_cap=19_000_000, penalties=[4, 8, 16, 32, 64, 128])
    response = dict(embedding={}, status='FAILURE', diag=diag)
    budget = model = incumbent = selected = None
    src = adj = source_labels = target_labels = ranks = ()
    absolute = None
    input_complete = False
    try:
        if type(seed) is not int or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('integer seed and finite positive timeout required')
        if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
            raise ValueError('finite absolute deadline required')
        absolute = min(started+timeout, deadline) if deadline is not None else started+timeout
        reserve = min(.5, max(0., absolute-started))
        search_deadline = absolute-reserve
        diag.update(deadline=absolute, search_deadline=search_deadline, validation_reserve=reserve)
        budget = _Budget(search_deadline, limit=19_000_000)
        with budget.stage('input'):
            source_labels, src = _graph(source, budget)
            target_labels, adj = _graph(target, budget)
            diag.update(source_nodes=len(src), target_nodes=len(adj),
                        source_edges=sum(map(len, src))//2, target_edges=sum(map(len, adj))//2)
            if len(src) > len(adj) or sum(map(len, src)) > sum(map(len, adj)):
                raise ValueError('necessary source/target count bound')
        input_complete = True
        with budget.stage('initial_domains'):
            rng, domains, ranks = random.Random(seed), [], []
            for _ in src:
                order = list(range(len(adj)))
                budget.tick('initial_permutation_records', len(order))
                rng.shuffle(order)
                rank = [0]*len(order)
                for i, q in enumerate(order):
                    budget.tick('initial_rank_records')
                    rank[q] = i
                ranks.append(tuple(rank))
                domains.append(tuple((q,) for q in order[:8]))
            model = _Model(domains, src, adj, budget)
            prob = [[1./len(row)]*len(row) for row in model.domains]
            diag['initial_domains'] = model.domains
            diag.update(last_complete_domains=model.domains, last_probabilities=prob)
            if not src:
                incumbent = ()
        for epoch, penalty in enumerate(diag['penalties']):
            record = dict(epoch=epoch, penalty=penalty, completed_updates=0, completed=False)
            diag['epochs'].append(record)
            with budget.stage('coordination'):
                for _ in range(8):
                    prob = model.update(prob, penalty)
                    record['completed_updates'] += 1
                    diag['last_probabilities'] = prob
                fields = model.fields(prob)
                record['expected'] = model.expected(prob, fields)
            with budget.stage('selection_validation'):
                selected = model.select(prob, ranks)
                record['selected'] = _stats(selected, src, adj, budget)
                response['diagnostic_embedding'] = _materialize(selected, source_labels, target_labels, budget)
                if record['selected']['valid'] and (incumbent is None or sum(map(len, selected)) < sum(map(len, incumbent))):
                    incumbent = selected
                    diag.setdefault('first_feasible_Q', sum(map(len, incumbent)))
                    diag['incumbent_Q'] = sum(map(len, incumbent))
                    diag['incumbent_chains'] = incumbent
                record['completed'] = True
            diag.update(last_complete_domains=model.domains, last_probabilities=prob)
            if epoch < 5:
                regen = dict(after_epoch=epoch, owners=[], committed=False)
                diag['regeneration'].append(regen)
                with budget.stage('domain_generation'):
                    new_domains = _regenerate(model, prob, ranks, penalty, incumbent, regen['owners'])
                    new_model = _Model(new_domains, src, adj, budget)
                    new_prob = [[1./len(row)]*len(row) for row in new_domains]
                    budget.check()
                    model, prob = new_model, new_prob
                    regen['committed'] = True
                    diag.update(last_complete_domains=model.domains, last_probabilities=prob)
        diag['search_stop'] = 'epoch_cap'
        if incumbent is None:
            response['error'] = 'no valid complete selection after six epochs'
    except _Stop as exc:
        diag['search_stop'] = str(exc)
        response.update(status='TIMEOUT' if str(exc)=='deadline' else 'FAILURE', error='search '+str(exc))
    except Exception as exc:
        _record_exception(response, exc, input_complete=input_complete)
    if budget is not None:
        budget.limit = 20_000_000
        try:
            if incumbent is not None:
                budget.deadline = absolute-diag['validation_reserve']/2
                try:
                    with budget.stage('cleanup'):
                        for revised in _cleanup(incumbent, src, adj, ranks, budget, diag['cleanup']):
                            incumbent = revised
                            diag['incumbent_chains'] = incumbent
                    diag['cleanup_stop'] = 'one_pass'
                except _Stop as exc:
                    diag['cleanup_stop'] = str(exc)
            budget.deadline = absolute
            chains = incumbent if incumbent is not None else selected
            if chains is not None:
                with budget.stage('final_validation'):
                    _finish(response, chains, source_labels, target_labels, src, adj, budget, absolute)
        except _Stop as exc:
            response.update(status='TIMEOUT' if str(exc)=='deadline' else 'FAILURE', embedding={}, error='final '+str(exc))
        except Exception as exc:
            _record_exception(response, exc, input_complete=True)
        diag.update(work=dict(budget.work), units=budget.units, denied_work=budget.denied,
                    stage_wall=dict(budget.stage_wall))
    observed = time.perf_counter()
    diag.update(wall=observed-started, deadline_overrun=max(0., observed-absolute) if absolute is not None else 0.)
    if absolute is not None and observed >= absolute:
        response.update(status='TIMEOUT', embedding={}, error='final bookkeeping exceeded deadline')
    if response['status'] != 'SUCCESS':
        response['embedding'] = {}
    return response
