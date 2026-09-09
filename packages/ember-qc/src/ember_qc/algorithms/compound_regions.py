"""Atomic growth plus one bounded private transfer/reconnect/compensate move."""
from collections import Counter, deque
import hashlib
import math
from pathlib import Path
import time
import types

_path = Path(__file__).with_name('atomic_regions.py')
_raw = _path.read_bytes()
_ATOMIC_SHA = '6d5cf638408dd8c698b1931e7295328d46f1c2212d4da7d0e81b5435e4608737'
if hashlib.sha256(_raw).hexdigest() != _ATOMIC_SHA:
    raise ImportError('Unexpected atomic region source')
_atomic = types.ModuleType('_compound_atomic_template')
_atomic.__file__ = str(_path)
exec(compile(_raw, str(_path), 'exec'), _atomic.__dict__)
_Expired = _atomic._elementary._Expired


class _Limit(Exception):
    pass


class _Budget:
    def __init__(self, meter, row):
        self.meter, self.row = meter, row
        self.started = time.perf_counter()
        self.deadline = min(self.started + .05, meter.deadline)
        self.work = 0
        self.finished = None
        row.update(started=self.started, deadline=self.deadline, work={}, screened=[], stage='screening')

    def check(self):
        self.meter.check()
        if time.perf_counter() >= self.deadline:
            raise _Limit('local_time')

    def tick(self, key, count=1):
        if count > 25000-self.work:
            self.row['unperformed_bulk_request'] = dict(key=key, count=count)
            raise _Limit('local_work')
        old = self.work
        self.work += count
        self.row['work'][key] = self.row['work'].get(key, 0) + count
        self.meter.tick('compound_' + key, count)
        if old // 128 != self.work // 128:
            self.check()

    def finish(self):
        if self.finished is None:
            self.finished = time.perf_counter()
            self.row.update(examined_records=self.work, wall=self.finished-self.started,
                            private_finished=self.finished)


def _pair(a, b):
    return (a, b) if a < b else (b, a)


def _components(sites, adj, budget):
    budget.tick('component_sites', len(sites))
    left = set(sites)
    groups = []
    while left:
        root = min(left)
        group = {root}
        left.remove(root)
        queue = deque([root])
        while queue:
            q = queue.popleft()
            for p in adj[q]:
                budget.tick('component_adjacency')
                if p in left:
                    left.remove(p)
                    group.add(p)
                    queue.append(p)
        groups.append(group)
    budget.check()
    return groups


class _Proposal:
    pass


class _Local:
    def __init__(self, state, u, d, budget):
        self.state, self.u, self.d, self.budget = state, u, d, budget
        budget.tick('private_chain_copy', len(state.regions[u])+len(state.regions[d]))
        self.regions = {v: set(state.regions[v]) for v in (u, d)}
        self.owner_changes, self.changes = {}, Counter()

    def owner(self, q):
        return self.owner_changes.get(q, self.state.owner[q])

    def count(self, edge):
        a, b = edge
        return self.state.count[a][b] + self.changes[edge]

    def delta(self, q, new):
        old, change = self.owner(q), Counter()
        for p in self.state.adj[q]:
            self.budget.tick('local_delta_adjacency')
            v = self.owner(p)
            if v >= 0:
                if old >= 0 and old != v:
                    change[_pair(old, v)] -= 1
                if new >= 0 and new != v:
                    change[_pair(new, v)] += 1
        for edge, amount in change.items():
            self.budget.tick('local_delta_contacts')
            assert self.count(edge) + amount >= 0
        return change

    def apply(self, q, new, change):
        old = self.owner(q)
        self.budget.tick('private_change_records', len(change)+3)
        if old >= 0:
            self.regions[old].remove(q)
        if new >= 0:
            self.regions[new].add(q)
        self.owner_changes[q] = new
        self.changes.update(change)

    def source_delta(self):
        delta = 0
        for edge, amount in self.changes.items():
            self.budget.tick('source_delta_contacts')
            if edge in self.state.edges:
                a, b = edge
                delta += int(self.state.count[a][b]+amount == 0)-int(self.state.count[a][b] == 0)
        return delta

    def bridge(self, parts, row):
        frontiers = []
        for component in parts:
            frontier = set()
            for q in sorted(component):
                for p in self.state.adj[q]:
                    self.budget.tick('bridge_frontier_adjacency')
                    if self.owner(p) == -1:
                        frontier.add(p)
            frontiers.append(frontier)
        roots = sorted(frontiers[0])
        self.budget.tick('bridge_roots', len(roots))
        parent = {q: None for q in roots}
        queue = deque(roots)
        row['stage'] = 'bridge'
        while queue:
            q = queue.popleft()
            self.budget.tick('bridge_vertices')
            if q in frontiers[1]:
                path = []
                while q is not None:
                    self.budget.tick('bridge_path_records')
                    path.append(q)
                    q = parent[q]
                path.reverse()
                row['path'] = path
                for q in path:
                    self.apply(q, self.d, self.delta(q, self.d))
                self.budget.check()
                return True
            for p in self.state.adj[q]:
                self.budget.tick('bridge_adjacency')
                if self.owner(p) == -1 and p not in parent:
                    parent[p] = q
                    queue.append(p)
        self.budget.check()
        row.update(status='no_bridge', path=None)
        return False

    def compensate(self, row):
        required = set()
        for v in (self.u, self.d):
            for w in self.state.src[v]:
                self.budget.tick('required_source_edges')
                edge = _pair(v, w)
                if self.count(edge) > 0:
                    required.add(edge)
        entry = sum(len(self.state.regions[v]) for v in (self.u, self.d))
        sites = []
        for v in sorted((self.u, self.d)):
            self.budget.tick('deletion_order_sites', len(self.regions[v]))
            sites.extend((v, q) for q in sorted(self.regions[v]))
        row.update(stage='compensation', deletions=[])
        for v, q in sites[:64]:
            if sum(map(len, self.regions.values())) <= entry:
                break
            self.budget.check()
            attempt = dict(owner=v, site=q, status='started', deleted=False)
            row['deletions'].append(attempt)
            self.budget.tick('deletion_visits')
            remaining = self.regions[v]-{q}
            if not remaining:
                attempt['status'] = 'singleton'
                continue
            if len(_components(remaining, self.state.adj, self.budget)) != 1:
                attempt['status'] = 'disconnected'
                continue
            change = self.delta(q, -1)
            lost = [edge for edge, amount in change.items() if edge in required and self.count(edge)+amount == 0]
            self.budget.tick('deletion_contact_checks', len(change))
            if lost:
                attempt['status'] = 'contact_loss'
                continue
            self.apply(q, -1, change)
            attempt.update(status='deleted', deleted=True)
        final = sum(map(len, self.regions.values()))
        row.update(added_sites=len(row['path']), removed_sites=sum(r['deleted'] for r in row['deletions']),
                   delta_qubits=final-entry, deletion_prefix_truncated=final>entry and len(sites)>64)
        if final > entry:
            row['status'] = 'inflated'
            return None
        return required

    def certify(self, selected_edge, required, row):
        row['stage'] = 'certificate'
        for v in (self.u, self.d):
            assert len(_components(self.regions[v], self.state.adj, self.budget)) == 1
            for q in self.regions[v]:
                self.budget.tick('certificate_owner_records')
                assert self.owner(q) == v
        assert not (self.regions[self.u] & self.regions[self.d])
        updates = {q: v for q, v in self.owner_changes.items() if v != self.state.owner[q]}
        self.budget.tick('certificate_update_records', len(self.owner_changes))
        # Independent physical-delta recount visits each affected target edge once.
        seen, checked = set(), Counter()
        for q in sorted(updates):
            for p in self.state.adj[q]:
                self.budget.tick('certificate_adjacency')
                physical = _pair(q, p)
                if physical in seen:
                    continue
                seen.add(physical)
                a, b = self.state.owner[q], self.state.owner[p]
                x, y = self.owner(q), self.owner(p)
                if a >= 0 and b >= 0 and a != b:
                    checked[_pair(a, b)] -= 1
                if x >= 0 and y >= 0 and x != y:
                    checked[_pair(x, y)] += 1
        changes = {edge: value for edge, value in self.changes.items() if value}
        assert changes == {edge: value for edge, value in checked.items() if value}
        for edge, amount in changes.items():
            self.budget.tick('certificate_contacts')
            a, b = edge
            assert self.state.count[a][b]+amount >= 0
            if edge in self.state.edges and self.state.count[a][b] > 0:
                assert self.count(edge) > 0
        for edge in required:
            self.budget.tick('certificate_required_contacts')
            assert self.count(edge) > 0
        assert self.count(selected_edge) > 0
        dm = self.source_delta()
        dq = sum(len(self.regions[v])-len(self.state.regions[v]) for v in (self.u, self.d))
        assert dm < 0 and dq <= 0
        proposal = _Proposal()
        proposal.u, proposal.d = self.u, self.d
        proposal.regions, proposal.updates, proposal.changes = self.regions, updates, changes
        proposal.versions = {v: self.state.version[v] for v in (self.u, self.d)}
        proposal.before = {q: self.state.owner[q] for q in updates}
        proposal.dm, proposal.dq, proposal.row = dm, dq, row
        row.update(delta_missing=dm, delta_qubits=dq,
                   final_regions={str(v): sorted(self.regions[v]) for v in (self.u, self.d)})
        self.budget.tick('certificate_evidence_records', sum(map(len, self.regions.values()))+len(updates)+len(changes))
        row['certificate_checks_passed'] = True
        self.budget.check()
        row.update(status='certified', certified=True)
        return proposal


def _screen(state, u, w, q, budget, record):
    d = state.owner[q]
    candidate = dict(site=q, donor=d, status='started')
    record['screened'].append(candidate)
    local = _Local(state, u, d, budget)
    change = local.delta(q, u)
    lost = [edge for edge, amount in change.items() if edge in state.edges and local.count(edge)>0 and local.count(edge)+amount == 0]
    selected = _pair(u, w)
    budget.tick('eligibility_contact_checks', len(change)+1)
    if lost:
        candidate.update(status='lost_contact', lost=sorted(lost))
        return None
    if local.count(selected)+change[selected] <= 0:
        candidate['status'] = 'no_selected_edge_gain'
        return None
    local.apply(q, u, change)
    parts = _components(local.regions[d], state.adj, budget)
    candidate['donor_components'] = len(parts)
    if len(parts) != 2:
        candidate['status'] = 'component_count'
        return None
    candidate['status'] = 'eligible'
    record.update(eligible=True, site=q, donor=d, recipient=u, destination=w,
                  transfer_delta_missing=local.source_delta(), stage='transfer')
    budget.check()
    return local, parts


class _State(_atomic._State):
    def __init__(self, regions, src, adj, meter):
        super().__init__(regions, src, adj, meter)
        self.compound = dict(attempt_limit=128, per_attempt_records=25000, per_attempt_seconds=.05,
                             per_visit_attempts=1, deletion_visit_limit=64, attempts=[], counts=Counter())
        meter.diag['compound'] = self.compound

    def transfer(self, q, v, change):
        if not isinstance(change, _Proposal):
            return super().transfer(q, v, change)
        proposal = change
        assert v == proposal.u
        for u, version in proposal.versions.items():
            assert self.version[u] == version
        for site, owner in proposal.before.items():
            assert self.owner[site] == owner
        self.meter.tick('compound_publication_preconditions', len(proposal.before)+2)
        self.meter.check()
        # Bounded publication has no cooperative interruption halfway through.
        for u, region in proposal.regions.items():
            self.regions[u] = region
            self.version[u] += 1
        for site, owner in proposal.updates.items():
            self.owner[site] = owner
        for (a, b), amount in sorted(proposal.changes.items()):
            self.count[a][b] += amount
            self.count[b][a] += amount
            if (a, b) in self.edges:
                self._update_missing((a, b))
        self.q += proposal.dq
        proposal.row['committed'] = True
        self.compound['counts']['committed'] += 1
        cost = len(proposal.updates)+len(proposal.changes)+5
        self.meter.work['compound_publication_records'] += cost
        self.meter.units += cost


def _propose(state, kind, rng, meter, row, weight):
    if kind != 'transfer':
        return _atomic._propose(state, kind, rng, meter, row, weight)
    u, w = state.missing[rng.randrange(len(state.missing))]
    if rng.randrange(2):
        u, w = w, u
    row.update(source=u, destination=w, eligibility_checks=0, ineligible=0, scored=[])
    frontier = set()
    for q in sorted(state.regions[u]):
        for p in state.adj[q]:
            meter.tick('frontier_adjacency')
            if state.owner[p] not in (-1, u):
                frontier.add(p)
    candidates = sorted(frontier)
    distance = state.distance(w) if candidates else {}
    row['enumerated'] = len(candidates)
    rng.shuffle(candidates)
    rank = {q: i for i, q in enumerate(candidates)}
    meter.tick('candidate_order_records', len(candidates))
    candidates.sort(key=lambda q: (distance.get(q, math.inf), rank[q]))
    meter.check()
    best, budget, record, closed = None, None, None, False
    try:
        for q in candidates:
            row['eligibility_checks'] += 1
            meter.tick('proposal_eligibility_checks')
            proposal = None
            if not state.removable(q):
                row['ineligible'] += 1
                if closed or len(state.regions[state.owner[q]]) <= 1:
                    continue
                if budget is None:
                    if len(state.compound['attempts']) >= 128:
                        state.compound['counts']['global_cap_visits'] += 1
                        closed = True
                        continue
                    record = dict(visit=row.get('visit'), eligible=False, certified=False, selected=False,
                                  committed=False, status='screening')
                    row['compound'] = record
                    state.compound['attempts'].append(record)
                    budget = _Budget(meter, record)
                try:
                    budget.check()
                    found = _screen(state, u, w, q, budget, record)
                    if found is None:
                        continue
                    closed = True
                    local, parts = found
                    if not local.bridge(parts, record):
                        budget.finish()
                        continue
                    required = local.compensate(record)
                    if required is None:
                        budget.finish()
                        continue
                    proposal = local.certify(_pair(u, w), required, record)
                    budget.finish()
                    if budget.finished >= budget.deadline:
                        raise _Limit('local_time')
                    dm, dq, change = proposal.dm, proposal.dq, proposal
                except _Limit as exc:
                    record.update(status=str(exc), certified=False)
                    budget.finish()
                    closed = True
                    continue
            else:
                dm, change = state.transfer_delta(q, u)
                dq = 0
            de = dm + dq * weight
            score = dict(site_or_owner=q, delta_missing=dm, delta_qubits=dq, delta_energy=de,
                         distance=distance.get(q), seeded_rank=rank[q])
            if proposal is not None:
                score['compound'] = True
            row['scored'].append(score)
            key = de, distance.get(q, math.inf), rank[q]
            if best is None or key < best[0]:
                best = key, q, change, score
            if len(row['scored']) == 16:
                break
        meter.check()
        row['proposal_prefix_complete'] = True
        if record is not None:
            if record['status'] == 'screening':
                record['status'] = 'no_eligible_site'
            record['selected'] = best is not None and isinstance(best[2], _Proposal)
        return best
    except _Expired:
        if record is not None:
            record.update(status='global_deadline', candidate_returned=False)
        raise
    finally:
        if budget is not None:
            budget.finish()
            state.compound['counts'][record['status']] += 1
            state.compound['counts']['selected'] += record['selected']


_atomic._elementary._State = _State
_atomic._elementary._propose = _propose


def compound_embed(source, target, *, seed=0, timeout=30., deadline=None):
    started = time.perf_counter()
    valid_timeout = type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
    valid_deadline = deadline is None or (type(deadline) in (int, float) and math.isfinite(deadline))
    absolute = min(started+timeout, deadline) if valid_timeout and deadline is not None and valid_deadline else started+timeout if valid_timeout and valid_deadline else None
    result = _atomic._elementary.variable_embed(source, target, seed=seed, timeout=timeout,
                                                 deadline=absolute if absolute is not None else deadline)
    result['diag'].update(algorithm='variable_connected_regions_compound_transfer_v1', atomic_template_sha256=_ATOMIC_SHA)
    observed = time.perf_counter()
    result['diag']['wall'] = observed-started
    if absolute is not None:
        result['diag']['deadline_overrun'] = max(0., observed-absolute)
        if observed >= absolute:
            result.update(status='TIMEOUT', embedding={}, error='compound wrapper exceeded common deadline')
    return result
