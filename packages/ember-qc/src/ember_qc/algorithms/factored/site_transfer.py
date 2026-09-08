"""One-site ownership transfer for a reverse insertion, using its live R/budget."""
from functools import cmp_to_key
import time

from ember_qc.algorithms.factored.blocked_reinsertion import _helpers

QUERY_SCANS = 50_000
TOTAL_SCANS = 1_000_000
SITE_LIMIT = 64


class TransferLimit(Exception):
    pass


def _copy(engine, entry):
    trial = {}
    for w, chain in entry.items():
        engine.scan()
        trial[w] = set()
        for q in chain:
            engine.scan()
            trial[w].add(q)
    return trial


def _gate(engine, trial, entry, v, donor, site):
    """Existing partial validator plus explicit partition/frontier certificate."""
    occupied = set()
    for w, chain in trial.items():
        engine.scan()
        for q in chain:
            engine.scan()
            occupied.add(q)
        # These owner/source loops in the inherited validator are not scans.
        for _ in engine.source[w]:
            engine.scan()
    old_occupied = set()
    for w, chain in entry.items():
        engine.scan()
        for q in chain:
            engine.scan()
            old_occupied.add(q)
        expected = chain - {site} if w == donor else chain
        if trial.get(w) != expected:
            raise RuntimeError('transfer changed another chain')
    if (set(trial) != set(entry) | {v} or trial[v] != {site} or
            occupied != old_occupied or sum(map(len, trial.values())) != len(old_occupied)):
        raise RuntimeError('transfer changed occupancy, coverage or Q')
    if not engine.valid(trial, complete=False):
        raise RuntimeError('local transfer disagrees with partial validator')
    # Charge inherited state/frontier traversals, including pending adjacency.
    for w, chain in trial.items():
        engine.scan()
        for _ in chain:
            engine.scan()
        for _ in engine.source[w]:
            engine.scan()
    _, _, bounds, free = engine.state(trial)
    if not engine.frontier_ok(trial, bounds, free):
        raise RuntimeError('local transfer disagrees with full future-port guard')
    engine.check()


def transfer_site(engine, v, entry):
    """Return (private mapping or None, receipt); entry must be a valid minor.

    engine.source is the caller's already staged requirement graph after only
    this row's created fill was removed. The caller owns cleanup and joint
    R/mapping adoption. Every other chain is frozen in this raw proposal.
    """
    info = engine.info
    used = info.get('transfer_scans', 0)
    start, began = time.perf_counter(), engine.scans
    limit = max(0, min(QUERY_SCANS, TOTAL_SCANS-used, _helpers.SCANS-began))
    record = dict(vertex=v, status='started', required=[], pool_size=None,
                  pool_complete=False, inspected=[], rejections={}, certified=False,
                  returned=False, committed=False, donor=None, site=None,
                  query_limit=QUERY_SCANS, total_limit=TOTAL_SCANS, site_limit=SITE_LIMIT,
                  limit=limit, scan_start=began, scans=0, total_start=used,
                  total_end=used, wall=0., before_q=None, raw_q=None)
    info['transfer_queries'] = info.get('transfer_queries', 0)+1
    info.setdefault('transfer_records', []).append(record)
    answer = None
    if getattr(engine, 'transfer_end', None) is not None or getattr(engine, 'repair_end', None) is not None:
        raise RuntimeError('nested transfer query is unsupported')
    engine.transfer_end = began+limit

    def reject(reason):
        counts = record['rejections']
        counts[reason] = counts.get(reason, 0)+1

    try:
        engine.check()
        if engine.scans >= _helpers.SCANS:
            info['stopped_by'] = 'work_limit'
            raise _helpers._Stop
        if limit == 0:
            record['status'] = 'transfer_total_limit'
        else:
            if v in entry or v not in engine.source:
                raise ValueError('expected one unplaced source vertex')
            required = []
            for w in engine.source[v]:
                engine.scan()
                if w in entry:
                    required.append(w)
            if len(required) > 3:
                raise ValueError('at most three placed required neighbors expected')
            record['required'] = required
            pool = []
            for a in required:
                engine.scan()
                if len(entry[a]) < 2:
                    continue
                for q in entry[a]:
                    engine.scan()
                    pool.append((len(entry[a]), engine.vrank[a], engine.qrank[q], a, q))

            def compare(a, b):
                engine.scan()
                return (a[:3] > b[:3]) - (a[:3] < b[:3])

            pool.sort(key=cmp_to_key(compare))
            record.update(pool_size=len(pool), pool_complete=True)
            engine.check()
            if not pool:
                record['status'] = 'no_donor'
            else:
                owners = {}
                for w, chain in entry.items():
                    engine.scan()
                    for q in chain:
                        engine.scan()
                        owners[q] = w
                record['before_q'] = len(owners)
                pending, has_free = {}, {}
                for w in (*entry, v):
                    engine.scan()
                    pending[w] = False
                    for z in engine.source[w]:
                        engine.scan()
                        if z not in entry and z != v:
                            pending[w] = True
                for w, chain in entry.items():
                    engine.scan()
                    has_free[w] = False
                    for q in chain:
                        engine.scan()
                        for p in engine.target[q]:
                            engine.scan()
                            if p not in owners:
                                has_free[w] = True
                blocked = []
                for w in entry:
                    engine.scan()
                    if pending[w] and not has_free[w]:
                        blocked.append(w)
                if blocked:
                    record.update(status='existing_future_port_missing', blocked_owners=blocked)
                else:
                    for _, _, _, a, q in pool[:SITE_LIMIT]:
                        engine.check()
                        engine.scan()
                        record['inspected'].append([a, q])
                        touches, q_free = set(), False
                        for p in engine.target[q]:
                            engine.scan()
                            if p in owners:
                                touches.add(owners[p])
                            else:
                                q_free = True
                        missing = False
                        for w in required:
                            engine.scan()
                            if w not in touches:
                                missing = True
                        if missing:
                            reject('new_contacts'); continue
                        if pending[v] and not q_free:
                            reject('new_future_port'); continue
                        donor = set()
                        for p in entry[a]:
                            engine.scan()
                            if p != q:
                                donor.add(p)
                        first = next(iter(donor))
                        seen, stack, contacts = {first}, [first], set()
                        donor_free = False
                        while stack:
                            engine.check()
                            p = stack.pop()
                            for z in engine.target[p]:
                                engine.scan()
                                if z in donor and z not in seen:
                                    seen.add(z); stack.append(z)
                                if z not in owners:
                                    donor_free = True
                                elif z != q and owners[z] != a:
                                    contacts.add(owners[z])
                        if seen != donor:
                            reject('donor_disconnected'); continue
                        lost = False
                        for w in engine.source[a]:
                            engine.scan()
                            if w in entry and w not in contacts:
                                lost = True
                        if lost:
                            reject('donor_contacts'); continue
                        if pending[a] and not donor_free:
                            reject('donor_future_port'); continue
                        trial = _copy(engine, entry)
                        trial[a] = donor
                        engine.scan()
                        trial[v] = {q}
                        _gate(engine, trial, entry, v, a, q)
                        record.update(status='certified', certified=True, donor=a,
                                      site=q, raw_q=record['before_q'])
                        answer = trial
                        break
                    if answer is None:
                        record['status'] = 'site_limit' if len(pool) > SITE_LIMIT else 'no_transfer'
    except TransferLimit:
        record['status'] = 'local_work_limit'
        try:
            engine.check()
        except _helpers._Stop:
            record['status'] = info.get('stopped_by') or 'interrupted'
            raise
    except _helpers._Stop:
        record['status'] = info.get('stopped_by') or 'interrupted'
        raise
    except Exception as exc:
        record.update(status='error', error=repr(exc))
        raise
    finally:
        engine.transfer_end = None
        record.update(scans=engine.scans-began, scan_end=engine.scans,
                      total_end=used+engine.scans-began, wall=time.perf_counter()-start)
        info['transfer_scans'] = record['total_end']
    ended = time.perf_counter()
    record['wall'] = ended-start
    if ended >= engine.deadline:
        record['status'] = 'deadline'
        info['stopped_by'] = 'deadline'
        raise _helpers._Stop
    record['returned'] = answer is not None
    return answer, record
