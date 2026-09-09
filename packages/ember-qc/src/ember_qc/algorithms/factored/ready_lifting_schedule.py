"""Metered dependency-ready scheduling; no embedding proposal or graph imports."""
import sys
import time


def diagnostics():
    return dict(policy='fewest_direct_singletons_then_reverse_index',
                word_bits=sys.int_info.bits_per_digit, target_words=None,
                work=0, work_by_kind={}, bigint_operations_completed=0,
                wall=0., selections=[], processed_row_ids=[], first_departure=None,
                status='not_started', stopped_phase=None)


class ReadySchedule:
    def __init__(self, engine, journal, info):
        self.engine, self.journal, self.info = engine, journal, info
        self.processed = set()
        self.remaining = len(journal)
        self.words = max(1, (len(engine.target)+info['word_bits']-1)//info['word_bits'])
        info['target_words'] = self.words
        info['status'] = 'complete' if not self.remaining else 'between_insertions'
        self.current = None
        self.phase = 'readiness'

    def charge(self, kind, units=1):
        for _ in range(units):
            before = self.engine.scans
            try:
                self.engine.scan()
            finally:
                used = self.engine.scans-before
                self.info['work'] += used
                counts = self.info['work_by_kind']
                counts[kind] = counts.get(kind, 0)+used

    def word(self, op, a, b=0):
        self.charge('word_'+op, self.words)
        self.engine.check()
        if op == 'or':
            out = a | b
        elif op == 'xor':
            out = a ^ b
        elif op == 'and':
            out = a & b
        elif op == 'count':
            out = a.bit_count()
        else:
            raise RuntimeError('unknown scheduler word operation')
        self.info['bigint_operations_completed'] += 1
        self.engine.check()
        return out

    def choose(self, chains):
        started, began = time.perf_counter(), self.info['work']
        record = dict(insertion_index=len(self.info['processed_row_ids']),
                      ready_complete=False, keys_complete=False, ready_count=None,
                      keys=[], selected_row=None, selected_vertex=None,
                      direct_singletons=None, legacy_pending_index=None,
                      admission_prepared=False, committed=False, status='started',
                      stopped_phase=None, work=0, wall=0.)
        self.current = record
        self.info['selections'].append(record)
        self.info['status'] = 'selecting'
        self.phase = 'readiness'
        try:
            self.charge('record')
            ready, legacy = [], None
            for i, row in enumerate(self.journal):
                self.charge('row_visit')
                if i in self.processed:
                    continue
                legacy = i
                if row['vertex'] in chains:
                    raise RuntimeError('unprocessed row vertex already placed')
                eligible = True
                for v in row['neighbors']:
                    self.charge('dependency_visit')
                    if v not in chains:
                        eligible = False
                if eligible:
                    ready.append(i)
            self.engine.check()
            record.update(ready_complete=True, ready_count=len(ready), legacy_pending_index=legacy)
            if not ready:
                raise RuntimeError('nonempty journal has no dependency-ready row')
            if len(ready) == 1:
                chosen, count = ready[0], None
            else:
                self.phase = 'physical_masks'
                needed = set()
                for i in ready:
                    self.charge('ready_visit')
                    for v in self.journal[i]['neighbors']:
                        self.charge('dependency_visit')
                        needed.add(v)
                occupied, boundaries = 0, {}
                for v, chain in chains.items():
                    self.charge('owner_visit')
                    boundary = 0
                    for q in chain:
                        self.charge('site_visit')
                        occupied = self.word('or', occupied, self.engine.bit[q])
                        if v in needed:
                            boundary = self.word('or', boundary, self.engine.adj_bits[q])
                    if v in needed:
                        boundaries[v] = boundary
                free = self.word('xor', self.engine.all_bits, occupied)
                self.phase = 'keys'
                best = None
                for i in ready:
                    self.charge('ready_visit')
                    domain = free
                    for v in self.journal[i]['neighbors']:
                        self.charge('dependency_visit')
                        domain = self.word('and', domain, boundaries[v])
                    n = self.word('count', domain)
                    self.charge('record')
                    record['keys'].append(dict(journal_index=i, vertex=self.journal[i]['vertex'],
                                               direct_singletons=n))
                    key = (n, -i)
                    if best is None or key < best:
                        best, chosen, count = key, i, n
            # No selected row is exposed until every required key and this gate finish.
            self.phase = 'selection_publication'
            self.charge('record')
            self.engine.check()
            record.update(keys_complete=True, selected_row=chosen,
                          selected_vertex=self.journal[chosen]['vertex'],
                          direct_singletons=count, status='selected')
            self.info['status'] = 'insertion'
            if chosen != legacy and self.info['first_departure'] is None:
                self.info['first_departure'] = dict(insertion_index=record['insertion_index'],
                    selected_row=chosen, legacy_pending_index=legacy, direct_singletons=count)
            return chosen, record
        finally:
            ended = time.perf_counter()
            record.update(work=self.info['work']-began, wall=ended-started)
            self.info['wall'] += ended-started
            if record['status'] == 'started':
                record.update(status=self.engine.info.get('stopped_by') or 'error',
                              stopped_phase=self.phase)
                self.info.update(status=record['status'], stopped_phase=self.phase)

    def prepare_commit(self, i, record):
        started, began = time.perf_counter(), self.info['work']
        self.phase = 'retirement_preparation'
        try:
            if record is not self.current or record['selected_row'] != i or i in self.processed:
                raise RuntimeError('scheduler admission identity mismatch')
            # Charge the bounded bookkeeping before the final caller admission gate.
            self.charge('retirement', 3)
            self.engine.check()
            record['admission_prepared'] = True
        finally:
            self.info['wall'] += time.perf_counter()-started
            record['retirement_work'] = self.info['work']-began

    def commit(self, i, record):
        # No interruption point: caller has just checked its deadline, and publishes E/R too.
        self.processed.add(i)
        self.remaining -= 1
        self.info['processed_row_ids'].append(i)
        record.update(committed=True, status='committed')
        self.info['status'] = 'complete' if not self.remaining else 'between_insertions'

    def stop(self):
        # Constant-size receipt completion; output materialization stays in the caller timer.
        if self.current is not None and self.current['status'] == 'selected':
            self.current.update(status=self.engine.info.get('stopped_by') or 'error',
                                stopped_phase=self.phase if self.phase == 'retirement_preparation' else 'insertion')
            self.info.update(status=self.current['status'], stopped_phase=self.current['stopped_phase'])
