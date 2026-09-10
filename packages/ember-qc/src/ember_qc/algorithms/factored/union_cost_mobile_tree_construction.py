"""B029: local root descent using the actual constructed owner-chain cost.

See notes/codex/tracks/b_029_union_construction_plan.md. Compilation is charged. Counters measure work;
the caller deadline is the only search allowance.  No competitor is imported.
"""
from collections import Counter, deque
from contextlib import contextmanager
from heapq import heappop, heappush
from math import isfinite
from random import Random
from time import perf_counter


class _Stop(Exception):
    pass


class _Meter:
    def __init__(self, deadline):
        self.deadline = deadline
        self.units, self.seconds, self.kinds = Counter(), Counter(), Counter()
        self.total = self.pending = 0
        self.stage, self.last = 'setup', perf_counter()

    def clock(self):
        now = perf_counter()
        if now >= self.deadline:
            raise _Stop(self.stage)
        return now

    def step(self, kind='site', amount=1):
        self.total += amount
        self.pending += amount
        self.units[self.stage] += amount
        self.kinds[kind] += amount
        if self.pending >= 256:
            self.pending = 0
            self.clock()

    def switch(self, stage):
        now = perf_counter()
        self.seconds[self.stage] += now - self.last
        self.stage, self.last = stage, now

    @contextmanager
    def phase(self, stage):
        previous = self.stage
        self.switch(stage)
        try:
            self.clock()
            yield
        finally:
            self.switch(previous)

    def ordered(self, values, key=None):
        self.clock()
        values = list(values)
        self.step('sort_item', len(values))
        values.sort(key=key)
        self.clock()
        return values

    def copy(self, values):
        self.clock()
        result = dict(values)
        self.step('map_copy_item', len(result))
        self.clock()
        return result


def _edge(u, v):
    return (u, v) if u < v else (v, u)


def _adjacency(graph, meter):
    if not isinstance(graph, dict):
        if graph.is_directed() or graph.is_multigraph():
            raise ValueError('simple undirected graph required')
        copied = {}
        for u in graph:
            meter.step('graph_copy_item')
            row = []
            for v in graph[u]:
                meter.step('graph_copy_item'); row.append(v)
            copied[u] = tuple(row)
        graph = copied
        meter.clock()
    answer = {}
    for u, neighbors in graph.items():
        meter.step('source_or_target_node')
        if type(u) is not int or not isinstance(neighbors, (tuple, list, set, frozenset)):
            raise ValueError('integer nodes and finite adjacency containers required')
        row = set()
        for v in neighbors:
            meter.step('normalization_adjacency')
            if type(v) is not int or v == u or v in row:
                raise ValueError('simple loopless graph required')
            row.add(v)
        answer[u] = frozenset(row)
    for u, neighbors in answer.items():
        for v in neighbors:
            meter.step('normalization_adjacency')
            if v not in answer or u not in answer[v]:
                raise ValueError('complete symmetric adjacency required')
    return answer


class _State:
    def __init__(self, chains=None, trees=None, owners=None, witnesses=None, Q=0, O=0):
        self.chains = {} if chains is None else chains
        self.trees = {} if trees is None else trees
        self.owners = {} if owners is None else owners
        self.witnesses = {} if witnesses is None else witnesses
        self.Q, self.O = Q, O

    def score(self):
        return dict(placed=len(self.chains), qubits=self.Q, overlap=self.O,
                    represented_contacts=len(self.witnesses))


class _Engine:
    def __init__(self, source, target, meter, seed=0):
        self.m = meter
        with meter.phase('normalization'):
            self.G = _adjacency(source, meter)
            self.H = _adjacency(target, meter)
            self.vertices = meter.ordered(self.G)
            self.sorder = list(self.vertices)
            self.qorder = meter.ordered(self.H)
            Random(seed).shuffle(self.sorder)
            Random(seed).shuffle(self.qorder)
            meter.step('shuffle_item', len(self.sorder) + len(self.qorder))
            self.srank = {u: i for i, u in enumerate(self.sorder)}
            self.rank = {q: i for i, q in enumerate(self.qorder)}
            self.adj = {q: tuple(meter.ordered(self.H[q], self.rank.__getitem__)) for q in self.qorder}
            self.edges = []
            for u in self.vertices:
                for v in meter.ordered(self.G[u]):
                    meter.step('source_adjacency')
                    if u < v:
                        self.edges.append((u, v))
            if len(self.G) > len(self.H):
                raise ValueError('more source vertices than target sites')
        self.state = _State()
        self.prices = {}
        self.quality = False
        self.stats = Counter()
        self.visits = []
        self.visit_count = 0
        self.last_visit = None
        self.initial = self.first_valid = None
        self.progress = []
        self.initialization_order = []
        self.began = perf_counter()

    def trim(self, sites, terminals):
        """Protect complete shared witness endpoints, never contact estimates."""
        m = self.m
        if not sites or not terminals.issubset(sites):
            raise ValueError('empty chain or absent protected terminal')
        root = min(terminals or sites, key=self.rank.__getitem__)
        m.step('terminal_or_anchor', len(terminals or sites))
        if not terminals:
            return frozenset((root,)), {root: None}
        parent, queue = {root: None}, deque((root,))
        while queue:
            q = queue.popleft(); m.step('tree_site')
            for p in self.adj[q]:
                m.step('tree_adjacency')
                if p in sites and p not in parent:
                    parent[p] = q; queue.append(p)
        if len(parent) != len(sites):
            raise ValueError('disconnected chain')
        keep = {root}
        for q in m.ordered(terminals, self.rank.__getitem__):
            while q not in keep:
                m.step('tree_path_site'); keep.add(q); q = parent[q]
        return frozenset(keep), {q: parent[q] for q in keep}

    def owner_patch(self, changes):
        patch = {}
        for u, new in changes.items():
            old = self.state.chains.get(u, frozenset())
            for q in old | new:
                self.m.step('owner_site')
                if q not in patch:
                    patch[q] = set(self.state.owners.get(q, ()))
                    self.m.step('owner_copy', len(patch[q]))
                if q in old:
                    patch[q].discard(u)
                if q in new:
                    patch[q].add(u)
        return {q: frozenset(owners) for q, owners in patch.items()}

    def contacts(self, u, sites, chains, witnesses):
        """Fill u-incident witnesses using actual edges, including shared supports."""
        wanted = {v for v in self.G[u] if v in chains}
        self.m.step('source_adjacency', len(self.G[u]))
        neighbor_order = self.m.ordered(wanted, self.srank.__getitem__)
        for q in self.m.ordered(sites, self.rank.__getitem__):
            for p in self.adj[q]:
                self.m.step('contact_adjacency')
                for v in neighbor_order:
                    self.m.step('contact_owner')
                    if v in wanted and p in chains[v]:
                        e = _edge(u, v)
                        witnesses[e] = (q, p) if u < v else (p, q)
                        wanted.remove(v)
                if not wanted:
                    break
            if not wanted:
                break
        if wanted:
            raise ValueError('missing represented contact')

    def joint_root(self, neighbors, chains, occupancy, quality):
        if not neighbors:
            return self._python_joint_root(neighbors, chains, occupancy, quality)
        # The public constructor is standalone: importing this sibling by path
        # avoids package __init__ files and their unrelated registered methods.
        if not hasattr(self, '_b029_kernel'):
            with self.m.phase('routing_import'):
                import importlib.util
                from pathlib import Path
                import sys
                path = Path(__file__).with_name('union_cost_joint_root.py')
                name = __name__ + '_kernel'
                if name not in sys.modules:
                    spec = importlib.util.spec_from_file_location(name, path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[name] = module
                    try:
                        spec.loader.exec_module(module)
                    except BaseException:
                        sys.modules.pop(name, None)
                        raise
                self._b029_kernel = sys.modules[name]
        return self._b029_kernel.joint_root(self, neighbors, chains, occupancy, quality)

    def _python_joint_root(self, neighbors, chains, occupancy, quality):
        """Exact declared sum-distance root, stopping only beyond best J."""
        m = self.m
        costs = {}

        def cost(q):
            if q not in costs:
                m.step('node_cost')
                k = len(occupancy.get(q, self.state.owners.get(q, ())))
                costs[q] = None if quality and k else 1 + (0 if quality else self.prices.get(q, 1) * k)
            return costs[q]

        if not neighbors:
            allowed = []
            for q in self.qorder:
                m.step('root_site')
                if cost(q) is not None:
                    allowed.append(q)
            if not allowed:
                return None
            root = min(allowed, key=lambda q: (cost(q), -len(self.H[q]), self.rank[q]))
            m.step('root_site', len(allowed))
            return root, {}, {}, dict(root_score=cost(root), labels=0, pushes=0, pops=0,
                                      early_stopped=False, boundary_sites=0)
        distances, parents, settled = {}, {}, {}
        queue = []
        boundary_count = pushes = pops = labels = 0
        for v in neighbors:
            if self.last_visit is not None:
                self.last_visit['current_neighbor'] = v
            distance, parent = {}, {}
            for p in m.ordered(chains[v], self.rank.__getitem__):
                for q in self.adj[p]:
                    m.step('boundary_adjacency')
                    weight = cost(q)
                    if weight is not None and q not in distance:
                        distance[q] = weight; parent[q] = None
                        heappush(queue, (weight, self.srank[v], self.rank[q], v, q))
                        m.step('heap_push'); pushes += 1
            boundary_count += len(distance)
            distances[v], parents[v], settled[v] = distance, parent, {}
            if not distance:
                return None
        sums, counts = {}, Counter()
        best = root = None
        early = False
        while queue:
            m.clock()
            distance, _, _, v, q = heappop(queue)
            if self.last_visit is not None:
                self.last_visit['current_neighbor'] = v
            m.step('heap_pop'); pops += 1
            if q in settled[v] or distances[v].get(q) != distance:
                continue
            if best is not None and distance > best:
                early = True; break
            settled[v][q] = distance
            m.step('settled_label'); labels += 1
            sums[q] = sums.get(q, 0) + distance; counts[q] += 1
            if counts[q] == len(neighbors):
                score = sums[q] - (len(neighbors) - 1) * cost(q)
                if root is None or (score, self.rank[q]) < (best, self.rank[root]):
                    best, root = score, q
                    if self.last_visit is not None:
                        self.last_visit['best_root_so_far'] = root
            for p in self.adj[q]:
                m.step('routing_adjacency')
                weight = cost(p)
                if weight is None or p in settled[v]:
                    continue
                candidate = distance + weight
                if candidate < distances[v].get(p, float('inf')):
                    distances[v][p] = candidate; parents[v][p] = q
                    heappush(queue, (candidate, self.srank[v], self.rank[p], v, p))
                    m.step('heap_push'); pushes += 1
        if root is None:
            return None
        return root, settled, parents, dict(root_score=best, labels=labels, pushes=pushes, pops=pops,
                                           early_stopped=early, boundary_sites=boundary_count)

    def attach(self, root, neighbors, chains, distances, parents):
        sites = {root}
        shared = added = 0
        for v in neighbors:
            if self.last_visit is not None:
                self.last_visit['current_neighbor'] = v
            contact = False
            for q in sites:
                self.m.step('attachment_site')
                for p in self.adj[q]:
                    self.m.step('attachment_adjacency')
                    if p in chains[v]:
                        contact = True; break
                if contact:
                    break
            if contact:
                shared += 1; continue
            candidates = []
            for q in sites:
                self.m.step('attachment_site')
                if q in distances[v]:
                    candidates.append(q)
            q = min(candidates, key=lambda p: (distances[v][p], self.rank[p]))
            self.m.step('attachment_site', len(candidates))
            if q != root:
                shared += 1
            while q is not None:
                self.m.step('attachment_path')
                if q not in sites:
                    added += 1; sites.add(q)
                q = parents[v][q]
        return frozenset(sites), shared, added

    def validate(self, state, selected=None, full=False):
        m = self.m
        if full and set(state.chains) != set(self.G):
            raise ValueError('incomplete source coverage')
        selected = set(state.chains) if selected is None else set(selected)
        checked = set()
        for u in selected:
            m.step('certificate_owner')
            sites = state.chains[u]
            if not sites or not sites.issubset(self.H):
                raise ValueError('empty or foreign chain')
            reached, queue = {next(iter(sites))}, deque((next(iter(sites)),))
            while queue:
                q = queue.popleft(); m.step('certificate_site')
                for p in self.adj[q]:
                    m.step('certificate_adjacency')
                    if p in sites and p not in reached:
                        reached.add(p); queue.append(p)
            if reached != set(sites):
                raise ValueError('disconnected chain')
            for v in self.G[u]:
                m.step('certificate_source_edge')
                if v not in state.chains:
                    continue
                e = _edge(u, v)
                if e in checked:
                    continue
                checked.add(e)
                a, b = e
                pair = state.witnesses.get(e)
                if pair is None or pair[0] not in state.chains[a] or pair[1] not in state.chains[b] or pair[1] not in self.H[pair[0]]:
                    raise ValueError('invalid original-edge witness')
        if full:
            owners = {}
            Q = 0
            for u, sites in state.chains.items():
                for q in sites:
                    m.step('certificate_owner_site'); Q += 1
                    owners.setdefault(q, set()).add(u)
            O = sum(max(0, len(v) - 1) for v in owners.values())
            m.step('certificate_occupied_site', len(owners))
            if Q != state.Q or O != state.O or owners != state.owners:
                raise ValueError('incorrect ownership totals')
            if O:
                raise ValueError('overlapping chains')
        m.clock()

    def _isolated_legacy_proposal(self, u, row):
        m = self.m
        old = self.state
        neighbors = m.ordered((v for v in self.G[u] if v in old.chains), self.srank.__getitem__)
        m.step('source_adjacency', len(self.G[u]))
        changes, trees = {u: frozenset()}, {}
        with m.phase('trim'):
            for v in neighbors:
                row['current_neighbor'] = v
                protected = set()
                for w in self.G[v]:
                    m.step('protected_source_edge')
                    if w != u and w in old.chains:
                        pair = old.witnesses[_edge(v, w)]
                        protected.add(pair[0 if v < w else 1])
                changes[v], trees[v] = self.trim(old.chains[v], protected)
            occupancy = self.owner_patch(changes)
        row['neighbor_sites_released'] = sum(len(old.chains[v]) - len(changes[v]) for v in neighbors)
        with m.phase('routing'):
            routed = self.joint_root(neighbors, changes, occupancy, self.quality)
            if routed is None:
                row['no_joint_root'] = True
                return None
            root, distances, parents, routing = routed
            row.update(routing, root=root)
            changes[u], shared, added = self.attach(root, neighbors, changes, distances, parents)
            row.update(shared_attachments=shared, path_sites_added=added)
        with m.phase('certificate'):
            chains = m.copy(old.chains); chains.update(changes)
            witnesses = m.copy(old.witnesses)
            self.contacts(u, changes[u], chains, witnesses)
            terminals = set()
            for v in neighbors:
                m.step('new_terminal')
                terminals.add(witnesses[_edge(u, v)][0 if u < v else 1])
            changes[u], trees[u] = self.trim(changes[u], terminals)
            chains[u] = changes[u]
            patch = self.owner_patch(changes)
            owners = m.copy(old.owners)
            O = old.O
            for q, new_owners in patch.items():
                m.step('occupancy_delta')
                O += max(0, len(new_owners) - 1) - max(0, len(old.owners.get(q, ())) - 1)
                if new_owners:
                    owners[q] = new_owners
                else:
                    owners.pop(q, None)
            Q = old.Q + sum(len(sites) - len(old.chains.get(v, ())) for v, sites in changes.items())
            m.step('chain_size_delta', len(changes))
            new_trees = m.copy(old.trees); new_trees.update(trees)
            candidate = _State(chains, new_trees, owners, witnesses, Q, O)
            self.validate(candidate, selected=changes)
            if self.quality and O:
                raise ValueError('quality proposal overlaps')
            transfers = 0
            for q in changes[u]:
                m.step('transfer_site')
                transfers += sum(v in old.owners.get(q, ()) and q not in changes[v] for v in neighbors)
                m.step('transfer_owner', len(neighbors))
            row.update(proposal=candidate.score(), cross_owner_transfers=transfers,
                       proposal_complete=True)
            return candidate

    def proposal(self, u, row):
        m, old = self.m, self.state
        neighbors = m.ordered((v for v in self.G[u] if v in old.chains), self.srank.__getitem__)
        m.step('source_adjacency', len(self.G[u]))
        if not neighbors:
            return self._isolated_legacy_proposal(u, row)
        changes, trees = {u: frozenset()}, {}
        with m.phase('trim'):
            for v in neighbors:
                row['current_neighbor'] = v
                protected = set()
                for w in self.G[v]:
                    m.step('protected_source_edge')
                    if w != u and w in old.chains:
                        pair = old.witnesses[_edge(v, w)]
                        protected.add(pair[0 if v < w else 1])
                changes[v], trees[v] = self.trim(old.chains[v], protected)
            occupancy = self.owner_patch(changes)
        row['neighbor_sites_released'] = sum(len(old.chains[v]) - len(changes[v]) for v in neighbors)
        with m.phase('routing'):
            route = self.joint_root(neighbors, changes, occupancy, self.quality)
            if route is None:
                row['no_joint_root'] = True
                return None
            row.update(route['stats'], root=self.qorder[route['anchor']])
        if not hasattr(self, '_b029_trial'):
            with m.phase('union_import'):
                import importlib.util
                from pathlib import Path
                import sys
                path = Path(__file__).with_name('union_cost_trial.py')
                name = __name__ + '_trial'
                if name not in sys.modules:
                    spec = importlib.util.spec_from_file_location(name, path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[name] = module
                    try:
                        spec.loader.exec_module(module)
                    except BaseException:
                        sys.modules.pop(name, None)
                        raise
                self._b029_trial = sys.modules[name]
        local = row['union'] = {}
        evaluator = self._b029_trial.Evaluator(self, u, changes, occupancy, route, local)
        selected = evaluator.descend(getattr(self, 'refine_roots', True))
        changes[u], trees[u] = selected['chain'], selected['cached_tree']
        selected_rank = self.rank[local['selected_root']]
        selected_J = sum(int(route['settled'][j, selected_rank]) for j in range(len(neighbors))) - (len(neighbors) - 1) * int(route['costs'][selected_rank])
        m.step('union_selected_J_label', len(neighbors))
        row.update(root=local['selected_root'], anchor_root_score=route['stats']['root_score'],
                   root_score=selected_J, shared_attachments=selected['shared'], path_sites_added=selected['added'])
        with m.phase('certificate'):
            chains = m.copy(old.chains); chains.update(changes)
            witnesses = m.copy(old.witnesses); witnesses.update(selected['witnesses'])
            patch = self.owner_patch(changes)
            owners = m.copy(old.owners)
            O = old.O
            for q, new_owners in patch.items():
                m.step('occupancy_delta')
                O += max(0, len(new_owners) - 1) - max(0, len(old.owners.get(q, ())) - 1)
                if new_owners:
                    owners[q] = new_owners
                else:
                    owners.pop(q, None)
            Q = old.Q + sum(len(sites) - len(old.chains.get(v, ())) for v, sites in changes.items())
            m.step('chain_size_delta', len(changes))
            Phi = Q
            for q, values in owners.items():
                k = len(values)
                Phi += self.prices.get(q, 1) * k * (k - 1) // 2
                m.step('union_selected_phi_site')
            if dict(Q=Q, O=O, Phi=Phi) != selected['scores']:
                raise RuntimeError('selected local scores differ from materialized full state')
            new_trees = m.copy(old.trees); new_trees.update(trees)
            candidate = _State(chains, new_trees, owners, witnesses, Q, O)
            # Verify the selected chain through the unchanged Python attachment,
            # contact and trim routines. Views avoid unpacking all route maps.
            distances = {v: self._b029_trial.FinalizedRow(self, route, j) for j, v in enumerate(neighbors)}
            parents = {v: self._b029_trial.FinalizedRow(self, route, j, parent=True) for j, v in enumerate(neighbors)}
            attached, expected_shared, expected_added = self.attach(local['selected_root'], neighbors, changes, distances, parents)
            expected_witnesses = {}
            self.contacts(u, attached, chains, expected_witnesses)
            terminals = {pair[0 if u < v else 1] for v in neighbors
                         for pair in (expected_witnesses[_edge(u, v)],)}
            expected_chain, expected_tree = self.trim(attached, terminals)
            if (expected_chain != selected['chain'] or expected_tree != selected['cached_tree']
                    or expected_witnesses != selected['witnesses']
                    or expected_shared != selected['shared'] or expected_added != selected['added']):
                raise RuntimeError('selected compact construction differs from original pipeline')
            self.validate(candidate, selected=changes)
            if self.quality and O:
                raise ValueError('quality proposal overlaps')
            transfers = 0
            for q in changes[u]:
                m.step('transfer_site')
                transfers += sum(v in old.owners.get(q, ()) and q not in changes[v] for v in neighbors)
                m.step('transfer_owner', len(neighbors))
            row.update(proposal=candidate.score(), cross_owner_transfers=transfers,
                       proposal_complete=True)
            return candidate

    def visit(self, u):
        m = self.m
        began, work = perf_counter(), m.total
        labels_before = m.kinds['settled_label']
        pushes_before, pops_before = m.kinds['heap_push'], m.kinds['heap_pop']
        row = dict(index=self.visit_count, owner=u, quality=self.quality,
                   initialization=u not in self.state.chains,
                   before=self.state.score(), complete=False, accepted=False)
        self.visit_count += 1
        self.last_visit = row
        if len(self.visits) < 16:
            self.visits.append(row)
        try:
            candidate = self.proposal(u, row)
            with m.phase('publication'):
                eligible = candidate is not None and (not self.quality or candidate.Q <= self.state.Q)
                chain_changed = candidate is not None and candidate.chains != self.state.chains
                witness_changed = candidate is not None and candidate.witnesses != self.state.witnesses
                changed = chain_changed or witness_changed
                m.step('publication_compare_item', len(self.state.chains) + len(self.state.witnesses))
                row.update(eligible=eligible, changed=changed, chain_changed=chain_changed,
                           witness_changed=witness_changed)
                m.clock()
                row['complete'] = True
                self.stats['complete_visits'] += 1
                if candidate is None:
                    self.stats['no_joint_root'] += 1
                    return 'no_joint_root'
                self.stats['certified_proposals'] += 1
                if not eligible:
                    row['rejected'] = 'larger_Q'
                    self.stats['quality_rejections'] += 1
                    return 'rejected'
                old = self.state
                self.state = candidate
                row['accepted'] = True
                self.stats['accepted_visits'] += 1
                self.stats['changed_commits'] += int(changed)
                self.stats['neighbor_sites_released'] += row['neighbor_sites_released']
                self.stats['cross_owner_transfers'] += row['cross_owner_transfers']
                self.stats['shared_attachments'] += row['shared_attachments']
                if self.quality:
                    self.stats['quality_strict_Q'] += int(candidate.Q < old.Q)
                    self.stats['quality_neutral_changes'] += int(changed and candidate.Q == old.Q)
                    if candidate.Q < old.Q:
                        self.progress.append(dict(wall=perf_counter() - self.began, work=m.total, qubits=candidate.Q))
                else:
                    self.stats['feasibility_Q_increases'] += int(candidate.Q > old.Q)
                    self.stats['feasibility_O_increases'] += int(candidate.O > old.O)
                    if not row['initialization']:
                        self.stats['reconstruction_Q_increases'] += int(candidate.Q > old.Q)
                        self.stats['reconstruction_O_increases'] += int(candidate.O > old.O)
                return 'changed' if changed else 'unchanged'
        except _Stop as exc:
            row.update(interrupted=True, interrupted_stage=str(exc))
            self.stats['interrupted_visits'] += 1
            if not row['accepted']:
                self.stats['discarded_complete_proposals'] += int(row.get('proposal_complete', False))
            raise
        finally:
            row.update(wall=perf_counter() - began, work=m.total - work,
                       labels_settled=m.kinds['settled_label'] - labels_before,
                       heap_pushes=m.kinds['heap_push'] - pushes_before,
                       heap_pops=m.kinds['heap_pop'] - pops_before)

    def price_update(self):
        with self.m.phase('prices'):
            new = self.m.copy(self.prices)
            changed = 0
            for q, owners in self.state.owners.items():
                self.m.step('price_occupied_site')
                if len(owners) > 1:
                    new[q] = new.get(q, 1) + len(owners) - 1
                    changed += 1
            self.m.clock()
            self.prices = new
            self.stats['price_updates'] += 1
            self.stats['site_price_increments'] += changed

    def snapshot(self):
        with self.m.phase('recording'):
            chains = {str(u): self.m.ordered(self.state.chains[u], self.rank.__getitem__)
                      for u in self.vertices if u in self.state.chains}
            self.m.step('record_edge', len(self.state.witnesses))
            witnesses = [[u, v, p, q] for (u, v), (p, q) in sorted(self.state.witnesses.items())]
            return dict(**self.state.score(), chains=chains, witnesses=witnesses,
                        prices=[[q, self.prices[q]] for q in self.qorder if q in self.prices])

    def enter_quality(self):
        if self.quality or len(self.state.chains) != len(self.G) or self.state.O:
            return
        with self.m.phase('first_valid_validation'):
            self.validate(self.state, full=True)
            self.first_valid = dict(wall=perf_counter() - self.began, work=self.m.total,
                                    **self.state.score())
            self.quality = True

    def quality_key(self):
        """Complete canonical equality key; digests never determine recurrence."""
        m, state = self.m, self.state
        chains, trees, witnesses, owners = [], [], [], []
        entries = 2
        for u in self.vertices:
            m.step('recurrence_owner')
            sites = tuple(m.ordered(state.chains[u], self.rank.__getitem__))
            m.step('recurrence_site', len(sites))
            chains.append((u, sites)); entries += 1 + len(sites)
            parent_pairs = []
            for q in m.ordered(state.trees[u], self.rank.__getitem__):
                m.step('recurrence_tree_site')
                parent_pairs.append((q, state.trees[u][q])); entries += 2
            trees.append((u, tuple(parent_pairs)))
        for (u, v), (p, q) in m.ordered(state.witnesses.items(), key=lambda x: x[0]):
            m.step('recurrence_edge')
            witnesses.append((u, v, p, q)); entries += 4
        for q in m.ordered(state.owners, self.rank.__getitem__):
            values = tuple(m.ordered(state.owners[q]))
            m.step('recurrence_owner_site', len(values))
            owners.append((q, values)); entries += 1 + len(values)
        return (tuple(chains), tuple(trees), tuple(witnesses), tuple(owners), state.Q, state.O), entries

    def check_recurrence(self, seen, boundary):
        began, work = perf_counter(), self.m.total
        row = dict(boundary=boundary, complete=False, repeated=False)
        self.recurrence_info = row
        try:
            with self.m.phase('recurrence'):
                key, entries = self.quality_key()
                previous = seen.get(key)
                self.m.step('recurrence_comparison_item', entries)
                next_seen = seen
                if previous is None:
                    next_seen = self.m.copy(seen)
                    next_seen[key] = boundary
                    self.m.step('recurrence_storage_item', entries)
                row.update(first_seen=previous, repeated=previous is not None,
                           period=None if previous is None else boundary - previous,
                           qubits=self.state.Q, distinct_keys=len(next_seen), key_items=entries)
                self.m.clock()
                row['complete'] = True
                self.stats['recurrence_keys_examined'] += 1
                self.stats['recurrence_distinct_keys'] = len(next_seen)
                self.stats['recurrence_stops'] += int(previous is not None)
                return next_seen, previous is not None
        except _Stop:
            row.update(interrupted=True, repeated=False)
            raise
        finally:
            row.update(wall=perf_counter() - began, work=self.m.total - work)

    def run(self, began):
        self.began = began
        quality_seen, quality_registered = {}, False
        with self.m.phase('initialization'):
            remaining = set(self.G)
            while remaining:
                keys = {}
                for u in remaining:
                    self.m.step('initial_source_owner')
                    attached = 0
                    for v in self.G[u]:
                        self.m.step('initial_source_adjacency')
                        attached += v in self.state.chains
                    keys[u] = (-attached, -len(self.G[u]), self.srank[u])
                u = min(remaining, key=keys.__getitem__)
                self.m.step('initial_owner_choice', len(remaining))
                if self.visit(u) == 'no_joint_root':
                    return 'initialization_no_joint_root'
                remaining.remove(u); self.initialization_order.append(u)
            self.initial = self.snapshot()
        self.enter_quality()
        if not self.quality:
            self.price_update()
        while True:
            self.m.clock()
            if self.quality and self.state.Q == len(self.G):
                return 'singleton_lower_bound'
            if self.quality and not quality_registered:
                quality_seen, repeated = self.check_recurrence(quality_seen, 0)
                quality_registered = True
            with self.m.phase('schedule'):
                quality_at_entry = self.quality
                keys = {}
                for u, sites in self.state.chains.items():
                    excess = 0
                    for q in sites:
                        self.m.step('schedule_owner_site')
                        excess += len(self.state.owners[q]) - 1
                    keys[u] = ((-len(sites), self.srank[u]) if self.quality else
                               (-excess, -len(sites), self.srank[u]))
                order = self.m.ordered(self.state.chains, keys.__getitem__)
            changed = False
            for u in order:
                changed |= self.visit(u) == 'changed'
                self.enter_quality()
                if self.quality and not quality_at_entry:
                    break
                if self.quality and self.state.Q == len(self.G):
                    return 'singleton_lower_bound'
            if self.quality and not quality_at_entry:
                continue
            self.stats['quality_sweeps' if self.quality else 'feasibility_sweeps'] += 1
            if self.quality:
                if not changed:
                    return 'quality_fixed_point'
                quality_seen, repeated = self.check_recurrence(quality_seen, self.stats['quality_sweeps'])
                if repeated:
                    return 'quality_state_recurrence'
            else:
                self.price_update()


def contact_embed(source, target, *, timeout=60.0, deadline=None, seed=0, refine_roots=True):
    """Fresh constructor; return only a timely independently recertified minor."""
    began = perf_counter()
    info = dict(algorithm='union-cost-mobile-tree-construction', version='B029', seed=seed,
                error=None, stopped_by=None, trace_limit=16, work_limit=None,
                pass_limit=None, query_limit=None, clock_poll_units=256)
    absolute = began
    engine = meter = None
    output, status = {}, 'FAILURE'
    try:
        if type(timeout) not in (int, float) or not isfinite(timeout) or timeout <= 0 or type(seed) is not int or type(refine_roots) is not bool:
            raise ValueError('positive finite timeout and integer seed required')
        absolute = began + timeout
        if deadline is not None:
            if type(deadline) not in (int, float) or not isfinite(deadline):
                raise ValueError('finite caller deadline required')
            absolute = min(absolute, deadline)
        reserve = min(1.0, 0.05 * max(0.0, absolute - began))
        meter = _Meter(absolute - reserve)
        info.update(started=began, deadline=absolute, search_deadline=meter.deadline,
                    final_reserve_seconds=reserve)
        engine = _Engine(source, target, meter, seed)
        engine.refine_roots = refine_roots
        info['refine_roots'] = refine_roots
        info['stopped_by'] = engine.run(began)
    except _Stop as exc:
        info.update(stopped_by='search_deadline', interrupted_stage=str(exc))
    except Exception as exc:
        info.update(stopped_by='error', error=repr(exc))
    if meter is not None:
        meter.deadline = absolute
        final_start, final_work = perf_counter(), meter.total
        try:
            with meter.phase('finalization'):
                if engine is not None:
                    info.update(initial=engine.initial, first_valid=engine.first_valid,
                                final=engine.snapshot(), initialization_order=engine.initialization_order,
                                stats=dict(engine.stats), visits=engine.visits, last_visit=engine.last_visit,
                                visit_count=engine.visit_count, detailed_visits_omitted=max(0, engine.visit_count - 16),
                                quality_progress=engine.progress,
                                recurrence=getattr(engine, 'recurrence_info', None),
                                acceleration=getattr(engine, 'acceleration', None),
                                union_stats=getattr(engine, 'union_stats', None))
                    if info['error'] is None and len(engine.state.chains) == len(engine.G) and engine.state.O == 0:
                        engine.validate(engine.state, full=True)
                        output = {u: meter.ordered(engine.state.chains[u], engine.rank.__getitem__) for u in engine.vertices}
                        meter.clock(); status = 'SUCCESS'
            meter.clock()
        except _Stop as exc:
            info['finalization_stop'] = str(exc); output = {}; status = 'FAILURE'
        except Exception as exc:
            info['finalization_error'] = repr(exc); output = {}; status = 'FAILURE'
        meter.switch('administration')
        info.update(finalization_wall=perf_counter() - final_start, finalization_work=meter.total - final_work,
                    work=meter.total, stage_units=dict(meter.units), stage_wall=dict(meter.seconds),
                    operation_counts=dict(meter.kinds))
    returned = perf_counter()
    if returned >= absolute:
        status, output = 'TIMEOUT', {}
    if info['error'] is not None:
        output = {}; status = 'FAILURE' if returned < absolute else 'TIMEOUT'
    info.update(returned=returned, wall=returned - began, deadline=absolute,
                deadline_overrun=max(0.0, returned - absolute))
    return dict(status=status, embedding=output if status == 'SUCCESS' else {}, diag=info)
