"""A066: exact futile-query pruning and atomic adjacent singleton replacement.

One A065 incumbent. No independent construction, witness input, work cap or
neutral public-state move. The optional constant ablation disables only pairs.
"""
import math
import time

from ember_qc.algorithms.factored.compiled_boundary_reconstruction import _Context
from ember_qc.algorithms.factored.mobile_boundary_reconstruction import _Meter, _Stop
from ember_qc.algorithms.factored.interleaved_boundary_reconstruction import (
    _Query, _Search as _OldSearch, _PAYLOAD,
)


class _Search(_OldSearch):
    def __init__(self, ctx, current, info, *, enable_pairs):
        super().__init__(ctx, current, info)
        if type(enable_pairs) is not bool:
            raise ValueError('constant boolean pair policy required')
        self.enable_pairs = enable_pairs
        info.update(pair_policy=enable_pairs, exact_obstructions=0, pair_commits=0,
                    pair_attempts=0)

    def direct_domain_nonempty(self, u, reduced, removed, free, boundary):
        """Exact proof for a length-two focus with unchanged prepared donors.

        A063 reconstruct returns only a new focus tree; A064 commit installs all
        prepared donors unchanged. With no donor removed, strict Q requires one
        focus site. Its domain is free sites contacting every retained neighbor.
        This assertion guards that proof against a changed preparation contract.
        """
        self.m.phase_to('exact_obstruction')
        if len(self.current.chains[u]) != 2 or any(removed.values()):
            raise RuntimeError('ineligible exact singleton obstruction proof')
        if set(reduced) != set(self.ctx.source[u]):
            raise RuntimeError('prepared neighbor coverage changed')
        for v, sites in reduced.items():
            self.m.tick('unchanged_donor_proof', len(sites)+len(self.current.chains[v]))
            if len(sites) != len(self.current.chains[v]) or set(sites) != set(self.current.chains[v]):
                raise RuntimeError('zero-removal donor set changed')
        if not reduced:
            self.m.check()
            return bool(free)
        required = set(reduced)
        for q, contacts in boundary.items():
            self.m.tick('exact_contact_coverage', len(contacts)+1)
            if q not in free or not set(contacts) <= required:
                raise RuntimeError('prepared boundary contract changed')
            if len(contacts) == len(required):
                return True
        self.m.check()
        return False

    def find_pair(self, u, free, record):
        """First exact physical coupler in two released singleton domains."""
        self.m.phase_to('pair_domains')
        details = record['pair_obstruction']
        current, ctx = self.current, self.ctx
        boundary_cache = {}

        def contact(owner):
            if owner not in boundary_cache:
                sites = set()
                for q in current.chains[owner]:
                    self.m.tick('pair_contact_site')
                    for p in ctx.target[q]:
                        self.m.tick('pair_contact_incidence'); sites.add(p)
                boundary_cache[owner] = sites
            return boundary_cache[owner]

        def domain(owner, other, available):
            self.m.tick('pair_available_copy', len(available))
            sites = set(available)
            for w in ctx.source[owner]:
                self.m.tick('pair_outside_neighbor')
                if w != other:
                    sites.intersection_update(contact(w))
                    self.m.check()
            return sites

        for v in ctx.source[u]:
            self.m.tick('pair_neighbor')
            if len(current.chains[v]) != 1:
                continue
            self.info['pair_attempts'] += 1
            attempt = dict(neighbor=v, status='running', domain_u=None,
                           domain_v=None, sites_examined=0, couplers_examined=0)
            details['attempts'].append(attempt)
            self.m.tick('pair_release_copy', len(free)+1)
            available = set(free); available.add(current.chains[v][0])
            du, dv = domain(u, v, available), domain(v, u, available)
            attempt.update(domain_u=len(du), domain_v=len(dv))
            for p in self.m.ordered(du, key=ctx.qtie.__getitem__):
                self.m.tick('pair_domain_site'); attempt['sites_examined'] += 1
                for q in ctx.target[p]:
                    self.m.tick('pair_physical_coupler'); attempt['couplers_examined'] += 1
                    if q in dv and q != p:
                        neutral = (q not in current.chains[u] and q != current.chains[v][0]
                                   and q in contact(u))
                        attempt.update(status='found', focus_site=p, neighbor_site=q,
                                       neutral_first=neutral)
                        return v, p, q, neutral
            attempt['status'] = 'exhausted'
        return None

    def prepare(self, u, record):
        reduced, removed, free, boundary = self.ctx.prepare(self.current, u, record)
        old_local = len(self.current.chains[u])+sum(len(self.current.chains[v]) for v in reduced)
        retained = sum(map(len, reduced.values()))
        if len(self.current.chains[u]) == 2 and not any(removed.values()):
            began, cpu = time.perf_counter(), time.process_time()
            details = dict(status='running', direct_domain=None, attempts=[],
                           pairs_enabled=self.enable_pairs, wall=None, cpu=None)
            record['pair_obstruction'] = details
            try:
                direct = self.direct_domain_nonempty(u, reduced, removed, free, boundary)
                details['direct_domain'] = 'nonempty' if direct else 'empty'
                if not direct:
                    self.info['exact_obstructions'] += 1
                    if self.enable_pairs:
                        pair = self.find_pair(u, free, record)
                        if pair is not None:
                            self.commit_pair(u, *pair, record)
                            details['status'] = 'committed'
                            return None
                    self.m.check()
                    self.closed.add(u)
                    record.update(status='exact_two_site_obstruction', closed_epoch=self.epoch)
                    details['status'] = 'exhausted' if self.enable_pairs else 'pruning_only'
                    return None
                details['status'] = 'ordinary_query_retained'
            finally:
                details.update(wall=time.perf_counter()-began, cpu=time.process_time()-cpu)
        del removed
        # The remaining preparation is A064's original code, without alteration.
        if 1+retained >= old_local:
            self.closed.add(u)
            record.update(status='no_strict_gain_bound', closed_epoch=self.epoch)
            return None
        began, cpu = time.perf_counter(), time.process_time()
        try:
            roots = self.ctx.roots(self.current, u, reduced, free, boundary, record)
        finally:
            record.update(root_generation_wall=time.perf_counter()-began,
                          root_generation_cpu=time.process_time()-cpu)
        self.m.phase_to('cache_accounting')
        q = _Query(self.epoch, u, reduced, free, boundary, roots, old_local, retained, record)
        self.m.tick('cache_boundary_count', len(boundary))
        self.payload_change(q.payload, 1)
        self.cache[u] = q
        record['prepared_payload'] = dict(q.payload)
        return q

    def commit_pair(self, u, v, p, q, neutral, record):
        """Original admission sequence, with an explicit uncached pair receipt."""
        current = self.current
        if u == v or v not in self.ctx.source[u] or len(current.chains[u]) != 2 or len(current.chains[v]) != 1:
            raise RuntimeError('invalid pair owner contract')
        self.m.phase_to('pair_candidate_copy')
        self.m.tick('pair_candidate_owner_copy', len(current.chains))
        updated = list(current.chains); updated[u] = (p,); updated[v] = (q,)
        chains = tuple(updated)
        record['certificates'] += 1
        self.ctx.certify(chains)
        candidate = self.ctx.bundle(chains)
        if candidate.qubits != current.qubits-1:
            raise RuntimeError('pair total-Q admission mismatch')
        self.m.phase_to('pair_bookkeeping')
        changed = []
        for owner, (old, new) in enumerate(zip(current.chains, candidate.chains)):
            self.m.tick('pair_frozen_owner_check')
            if old != new:
                if owner not in (u, v):
                    raise RuntimeError('outside pair owner changed')
                self.m.tick('pair_receipt_sites', len(old)+len(new))
                changed.append(dict(owner=owner, before=list(old), after=list(new)))
        if {c['owner'] for c in changed} != {u, v}:
            raise RuntimeError('pair did not relocate both owners')
        ri, slot = record['last_round'], record['last_slot']
        receipt = dict(index=len(self.info['commits']), epoch=self.epoch,
                       round=ri, slot=slot, query=record['index'], owner=u,
                       kind='paired_singletons', neighbor=v, root=p, root_rank=None,
                       neighbor_site=q, neutral_first=neutral,
                       before_qubits=current.qubits, after_qubits=candidate.qubits,
                       qubits_saved=1, donors_changed=0, stem_sites=0,
                       relocated_donors=1, changed_owners=changed, deadline=self.m.deadline)
        closing = []
        for owner, other in self.cache.items():
            self.m.tick('pair_epoch_close_context')
            if other.epoch != self.epoch or owner == u:
                raise RuntimeError('stale or unexpectedly cached pair query')
            closing.append(dict(owner=owner, query=other.record['index'], outcome='invalidated',
                                roots_completed=other.record['trees_completed'],
                                roots_unexamined=other.payload['unexamined_roots']))
        event = dict(epoch=self.epoch, next_epoch=self.epoch+1, reason='pair_commit',
                     round=ri, next_slot=slot+1, queries=closing,
                     prepared_pair_query=record['index'], prior_closed_owners=len(self.closed),
                     discarded_payload=dict(self.live))
        self.m.tick('pair_receipt_list_copy', len(self.info['commits']))
        receipts = self.info['commits']+[receipt]
        self.m.tick('pair_event_list_copy', len(self.info['epochs']))
        events = self.info['epochs']+[event]
        empty_cache, empty_closed, empty_live = {}, set(), dict.fromkeys(_PAYLOAD, 0)
        self.m.tick('pair_publication_prepare')
        self.m.check()
        admitted = time.perf_counter()
        if admitted >= self.m.deadline:
            raise _Stop('deadline')
        receipt['admitted'] = event['admitted'] = admitted
        old_cache = self.cache
        (self.current, self.epoch, self.cache, self.closed, self.live,
         self.info['commits'], self.info['epochs'], self.info['cache_payload_current']) = (
            candidate, self.epoch+1, empty_cache, empty_closed, empty_live,
            receipts, events, empty_live)
        self.info['accepted'] += 1
        self.info['pair_commits'] += 1
        record.update(status='committed', committed=True, after_qubits=candidate.qubits)
        record['pair_obstruction']['status'] = 'committed'
        self.dispose(old_cache)


def paired_boundary_reconstruction(embedding, source_adj, target_adj, *, seed=0,
                                   deadline, validator, enable_pairs=True):
    """Return one last certified incumbent; fatal errors have no credited map."""
    if type(seed) is not int or not isinstance(deadline, (int, float)) or not math.isfinite(deadline):
        raise ValueError('integer seed and finite absolute deadline required')
    m = _Meter(deadline)
    info = dict(algorithm='paired_boundary_reconstruction', version='A066',
                status='started', error=None, input_copy_complete=False, input_validated=False,
                rounds_started=0, rounds_completed=0, rounds=[], queries=[], commits=[], epochs=[],
                epoch=0, accepted=0, before_qubits=None, after_qubits=None,
                stopped_phase=None, diagnostic_embedding=None)
    current, search, result = None, None, embedding
    try:
        m.check()
        ctx = _Context(source_adj, target_adj, seed, validator, m)
        chains = ctx.read_entry(embedding)
        result = ctx.externalize(chains)
        info['input_copy_complete'] = True
        ctx.certify(chains)
        current = ctx.bundle(chains)
        result = current.external
        info.update(input_validated=True, before_qubits=current.qubits)
        search = _Search(ctx, current, info, enable_pairs=enable_pairs)
        search.run()
    except _Stop:
        info.update(status='deadline', stopped_phase=m.phase)
    except Exception as exc:
        info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_phase=m.phase)
    finally:
        if search is not None:
            current = search.current
            result = current.external
            try:
                search.cleanup()
            except _Stop:
                info['cleanup_deadline'] = True
                if info['status'] not in ('error', 'deadline'):
                    info.update(status='deadline', stopped_phase=m.phase)
            except Exception as exc:
                info.update(status='error', error=type(exc).__name__+': '+str(exc), stopped_phase=m.phase)
    if info['error'] is not None:
        info['diagnostic_embedding'] = current.external if current is not None else embedding
        result = {}
    info['after_qubits'] = current.qubits if current is not None else None
    info.update(m.finish())
    if info['ended'] >= deadline and info['status'] not in ('error', 'deadline'):
        info.update(status='deadline', stopped_phase=m.phase)
    return result, info
