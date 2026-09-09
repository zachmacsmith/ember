"""A064: one-root visits to unchanged A063 queries on one incumbent epoch."""
import math
import time

from ember_qc.algorithms.factored.mobile_boundary_reconstruction import (
    _Context, _Meter, _Stop,
)


_PAYLOAD = ('contexts', 'stored_roots', 'unexamined_roots', 'free_sites',
            'reduced_sites', 'boundary_keys', 'boundary_memberships')


class _Query:
    def __init__(self, epoch, owner, reduced, free, boundary, roots,
                 old_local, retained, record):
        self.epoch, self.owner = epoch, owner
        self.reduced, self.free, self.boundary, self.roots = reduced, free, boundary, roots
        self.old_local, self.retained, self.record = old_local, retained, record
        self.cursor = 0
        self.payload = dict(contexts=1, stored_roots=len(roots), unexamined_roots=len(roots),
                            free_sites=len(free), reduced_sites=retained,
                            boundary_keys=len(boundary),
                            boundary_memberships=sum(map(len, boundary.values())))


class _Search:
    def __init__(self, ctx, current, info):
        self.ctx, self.m, self.current, self.info = ctx, ctx.m, current, info
        self.epoch, self.cache, self.closed = 0, {}, set()
        self.live = dict.fromkeys(_PAYLOAD, 0)
        self.peak = dict(self.live)
        info.update(cache_payload_current=self.live, cache_payload_peak=self.peak)

    def payload_change(self, payload, sign):
        self.m.phase_to('cache_accounting')
        live = {k: self.live[k]+sign*payload[k] for k in _PAYLOAD}
        if any(v < 0 for v in live.values()):
            raise RuntimeError('negative live cache payload')
        peak = {k: max(self.peak[k], live[k]) for k in _PAYLOAD}
        self.m.tick('cache_payload_fields', len(_PAYLOAD))
        self.live, self.peak = live, peak
        self.info.update(cache_payload_current=live, cache_payload_peak=peak)

    def dispose(self, cache):
        """Release storage even if the phase boundary notices the deadline."""
        stopped = None
        try:
            self.m.phase_to('cache_disposal')
        except _Stop as exc:
            stopped = exc
        count = len(cache)
        cache.clear()
        try:
            self.m.tick('cache_context_release', count)
            self.m.check()
        except _Stop as exc:
            stopped = exc
        if stopped is not None:
            raise stopped

    def close(self, u, q, status):
        # The fixed-size counter update can stop before any cache mutation.
        self.payload_change(q.payload, -1)
        old = {u: self.cache.pop(u)}
        self.closed.add(u)
        q.record.update(status=status, closed_epoch=self.epoch)
        self.dispose(old)

    def cleanup(self):
        self.info.update(epoch=self.epoch, closed_owners_current=len(self.closed),
                         cache_payload_at_stop=dict(self.live))
        if self.cache:
            old, self.cache = self.cache, {}
            self.live = dict.fromkeys(_PAYLOAD, 0)
            self.info['cache_payload_current'] = self.live
            self.dispose(old)

    def new_record(self, u, round_index, slot):
        record = dict(index=len(self.info['queries']), epoch=self.epoch, owner=u,
                      first_round=round_index, last_round=round_index, last_slot=slot,
                      before_qubits=self.current.qubits, status='running',
                      ranking_complete=False, eligible_roots=None, roots_examined=0,
                      trees_completed=0, next_root=0, q_rejections=0, certificates=0,
                      committed=False, best_completed_qubits=None, visits=0,
                      wall=0., cpu=0., work=0, first_started=None, last_ended=None,
                      root_generation_wall=None, root_generation_cpu=None,
                      reconstruction_wall={}, reconstruction_cpu={})
        self.info['queries'].append(record)
        return record

    def prepare(self, u, record):
        reduced, removed, free, boundary = self.ctx.prepare(self.current, u, record)
        old_local = len(self.current.chains[u])+sum(len(self.current.chains[v]) for v in reduced)
        retained = sum(map(len, reduced.values()))
        del removed
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
        # No clock checks split publication of this complete prepared cache.
        self.cache[u] = q
        record['prepared_payload'] = dict(q.payload)
        return q

    def commit(self, u, q, tree, proposed, root, root_rank, round_index, slot):
        current, record = self.current, q.record
        self.m.phase_to('candidate_copy')
        self.m.tick('candidate_owner_copy', len(current.chains))
        updated = list(current.chains)
        updated[u] = tree
        for v, sites in q.reduced.items():
            self.m.tick('candidate_neighbor'); updated[v] = sites
        chains = tuple(updated)
        record['certificates'] += 1
        self.ctx.certify(chains)
        candidate = self.ctx.bundle(chains)
        if candidate.qubits != proposed or candidate.qubits >= current.qubits:
            raise RuntimeError('actual total-Q admission mismatch')
        self.m.phase_to('bookkeeping')
        changed_owners = []
        for v, (old, new) in enumerate(zip(current.chains, candidate.chains)):
            self.m.tick('frozen_owner_check')
            if old != new:
                if v != u and v not in q.reduced:
                    raise RuntimeError('frozen owner changed')
                self.m.tick('receipt_sites', len(old)+len(new))
                changed_owners.append(dict(owner=v, before=list(old), after=list(new)))
        receipt = dict(index=len(self.info['commits']), epoch=self.epoch,
                       round=round_index, slot=slot, query=record['index'], owner=u,
                       root=root, root_rank=root_rank, before_qubits=current.qubits,
                       after_qubits=candidate.qubits, qubits_saved=current.qubits-candidate.qubits,
                       donors_changed=record['donors_changed'], stem_sites=record['stem_sites'],
                       changed_owners=changed_owners, deadline=self.m.deadline)
        closing = []
        for v, other in self.cache.items():
            self.m.tick('epoch_close_context')
            if other.epoch != self.epoch:
                raise RuntimeError('stale epoch during publication')
            closing.append(dict(owner=v, query=other.record['index'],
                                outcome='committed' if v == u else 'invalidated',
                                roots_completed=other.record['trees_completed'],
                                roots_unexamined=other.payload['unexamined_roots']))
        event = dict(epoch=self.epoch, next_epoch=self.epoch+1, reason='commit',
                     round=round_index, next_slot=slot+1, queries=closing,
                     prior_closed_owners=len(self.closed), discarded_payload=dict(self.live))
        self.m.tick('receipt_list_copy', len(self.info['commits']))
        receipts = self.info['commits']+[receipt]
        self.m.tick('epoch_event_list_copy', len(self.info['epochs']))
        events = self.info['epochs']+[event]
        empty_cache, empty_closed, empty_live = {}, set(), dict.fromkeys(_PAYLOAD, 0)
        self.m.tick('epoch_publication_prepare')
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
        record.update(status='committed', committed=True, after_qubits=candidate.qubits)
        self.dispose(old_cache)

    def visit(self, u, round_index, slot):
        self.m.check()
        if u in self.closed:
            self.m.tick('closed_owner_slot')
            return
        q = self.cache.get(u)
        if q is not None and q.epoch != self.epoch:
            raise RuntimeError('stale query epoch on resumption')
        record = q.record if q is not None else self.new_record(u, round_index, slot)
        began, cpu, work = time.perf_counter(), time.process_time(), self.m.work
        record.update(status='running', last_round=round_index, last_slot=slot)
        record['visits'] += 1
        if record['first_started'] is None:
            record['first_started'] = began
        try:
            self.m.tick('query_visit')
            if q is None:
                q = self.prepare(u, record)
                if q is None:
                    return
            if q.cursor >= len(q.roots):
                self.close(u, q, 'roots_exhausted')
                return
            root, root_rank = q.roots[q.cursor], q.cursor+1
            self.m.phase_to('schedule')
            self.m.tick('root_cursor')
            record['roots_examined'] += 1
            q.payload['unexamined_roots'] -= 1
            self.live['unexamined_roots'] -= 1
            started, tree_cpu = time.perf_counter(), time.process_time()
            outcome = 'interrupted_or_error'
            try:
                tree = self.ctx.reconstruct(root, q.reduced, q.free, q.boundary, u)
                record['trees_completed'] += 1
                q.cursor += 1
                record['next_root'] = q.cursor
                proposed = self.current.qubits-q.old_local+q.retained+len(tree)
                outcome = 'nonimproving' if proposed >= self.current.qubits else 'smaller_Q'
            finally:
                record['reconstruction_wall'][outcome] = record['reconstruction_wall'].get(outcome, 0.)+time.perf_counter()-started
                record['reconstruction_cpu'][outcome] = record['reconstruction_cpu'].get(outcome, 0.)+time.process_time()-tree_cpu
            best = record['best_completed_qubits']
            record['best_completed_qubits'] = proposed if best is None else min(best, proposed)
            if proposed < self.current.qubits:
                self.commit(u, q, tree, proposed, root, root_rank, round_index, slot)
            else:
                record['q_rejections'] += 1
                if q.cursor == len(q.roots):
                    self.close(u, q, 'roots_exhausted')
                else:
                    record['status'] = 'parked'
        finally:
            ended = time.perf_counter()
            record.update(wall=record['wall']+ended-began,
                          cpu=record['cpu']+time.process_time()-cpu,
                          work=record['work']+self.m.work-work, last_ended=ended)
            if record['status'] == 'running':
                record.update(status='interrupted_or_error', stopped_phase=self.m.phase)

    def run(self):
        n = len(self.ctx.source)
        while len(self.closed) < n:
            self.m.phase_to('schedule')
            order = self.m.ordered(list(range(n)),
                                   key=lambda u: (-len(self.current.chains[u]), self.ctx.vtie[u]))
            ri = len(self.info['rounds'])
            round_record = dict(index=ri, start_epoch=self.epoch, end_epoch=self.epoch,
                                owner_order=order, next_slot=0, completed=False, mixed_epoch=False)
            self.info['rounds'].append(round_record)
            self.info['rounds_started'] += 1
            try:
                for slot, u in enumerate(order):
                    self.m.phase_to('schedule')
                    round_record['next_slot'] = slot+1
                    self.visit(u, ri, slot)
                    if len(self.closed) == n:
                        break
                if round_record['next_slot'] == n:
                    round_record['completed'] = True
                    self.info['rounds_completed'] += 1
            finally:
                round_record.update(end_epoch=self.epoch,
                                    mixed_epoch=round_record['start_epoch'] != self.epoch)
        self.info['status'] = 'epoch_exhausted'


def interleaved_boundary_reconstruction(embedding, source_adj, target_adj, *, seed=0,
                                       deadline, validator):
    """Return one last certified incumbent; fatal errors have no credited map."""
    if type(seed) is not int or not isinstance(deadline, (int, float)) or not math.isfinite(deadline):
        raise ValueError('integer seed and finite absolute deadline required')
    m = _Meter(deadline)
    info = dict(algorithm='interleaved_boundary_reconstruction', version='A064',
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
        search = _Search(ctx, current, info)
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
