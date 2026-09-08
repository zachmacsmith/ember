"""Lazy incident endpoint scores for one frozen-outside group reconstruction.

This is a score collector, not an embedding validator or proposal generator.
The caller validates the entry and keeps every unselected chain unchanged.
Only completed scores may authorize an equal-size move. Scans use the common
absolute deadline; their counters are separate from routing expansions.
"""
from __future__ import annotations

import time


class ScoreDeadline(Exception):
    """A partial score must be discarded; an earlier valid incumbent survives."""


def score_diagnostics():
    return dict(attempted=0, completed=0, invalid=0, interrupted=0, cache_hits=0,
                owner_setup_attempts=0, owner_entries=0, source_adjacency_entries=0,
                incident_source_edges=0,
                overlay_sites=0, selected_qubits=0, target_adjacency_entries=0,
                endpoints_inserted=0, histogram_entries=0, comparison_entries=0,
                comparisons=0, comparison_interrupted=0,
                setup_wall=0.0, score_wall=0.0, comparison_wall=0.0,
                interrupted_stage=None)


def diagnostics():
    return dict(objective='qubits_endpoint_support', score=score_diagnostics(),
                validation_wall=0.0, best_qubit_updates=0, best_equal_updates=0,
                histogram_delta={}, histogram_complete=True,
                known_histogram_delta={}, known_contact_redundancy_gain=0,
                unknown_moves=0)


def histogram_difference(before, after):
    """Signed sparse difference; unaffected directed edges cancel exactly."""
    return {k: after.get(k, 0) - before.get(k, 0)
            for k in before.keys() | after.keys()
            if after.get(k, 0) != before.get(k, 0)}


class EndpointScorer:
    def __init__(self, entry, ctx, group, deadline=None):
        self.entry, self.ctx, self.deadline = entry, ctx, deadline
        self.group = tuple(sorted(group, key=lambda v: (type(v).__name__, repr(v))))
        self.selected = frozenset(self.group)
        self.info = score_diagnostics()
        self._owner = self._keys = None
        self._stage = None

    def check(self, stage):
        self._stage = stage
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise ScoreDeadline(stage)

    def _setup(self):
        if self._owner is not None:
            return True
        started = time.perf_counter()
        self.info['owner_setup_attempts'] += 1
        owner, keys, seen = {}, [], set()
        try:
            for v, chain in self.entry.items():
                for q in chain:
                    self.check('owner')
                    self.info['owner_entries'] += 1
                    if q not in self.ctx.adj or q in owner:
                        return False
                    owner[q] = v
            for u in self.group:
                for v in self.ctx.src_adj[u]:
                    self.check('source_edges')
                    self.info['source_adjacency_entries'] += 1
                    edge = frozenset((u, v))
                    if edge not in seen:
                        seen.add(edge)
                        self.info['incident_source_edges'] += 1
                        keys.extend(((u, v), (v, u)))
            self.check('owner_complete')
            self._owner, self._keys = owner, tuple(keys)
            return True
        finally:
            self.info['setup_wall'] += time.perf_counter() - started

    def score(self, embedding):
        """Return incident histogram/R or None for bad ownership/contact coverage.

        Every outside chain must be the unchanged entry chain. Connectivity is
        deliberately left to the caller's full original-graph validator. The
        owner map is published only after complete setup, and the returned score
        only after every scan and the final deadline check finish.
        """
        started = time.perf_counter()
        setup_before = self.info['setup_wall']
        self.info['attempted'] += 1
        try:
            self.check('start')
            result = self._score(embedding)
            self.check('score_complete')
            self.info['invalid' if result is None else 'completed'] += 1
            return result
        except ScoreDeadline:
            self.info['interrupted'] += 1
            self.info['interrupted_stage'] = self._stage
            raise
        finally:
            self.info['score_wall'] += max(
                0.0, time.perf_counter() - started -
                (self.info['setup_wall'] - setup_before))

    def _score(self, embedding):
        if not self._setup():
            return None
        proposed = {}
        absent = object()
        for v in self.group:
            self.check('overlay')
            if v not in embedding or not embedding[v]:
                return None
            for q in embedding[v]:
                self.check('overlay')
                self.info['overlay_sites'] += 1
                owner = self._owner.get(q, absent)
                if (q not in self.ctx.adj or q in proposed
                        or (owner is not absent and owner not in self.selected)):
                    return None
                proposed[q] = v

        support = {}
        for key in self._keys:
            self.check('support_sets')
            support[key] = set()
        couplers = 0
        for u in self.group:
            for q in embedding[u]:
                self.check('qubits')
                self.info['selected_qubits'] += 1
                for p in self.ctx.adj[q]:
                    self.check('adjacency')
                    self.info['target_adjacency_entries'] += 1
                    v = proposed.get(p, absent)
                    if v is absent:
                        v = self._owner.get(p, absent)
                        if v in self.selected:
                            v = absent  # Released old site, not a stale owner.
                    if (u, v) not in support:
                        continue
                    if v in self.selected and self.ctx.rank[q] > self.ctx.rank[p]:
                        continue  # Count a selected-selected coupler once.
                    couplers += 1
                    for key, endpoint in (((u, v), q), ((v, u), p)):
                        if endpoint not in support[key]:
                            support[key].add(endpoint)
                            self.info['endpoints_inserted'] += 1
        histogram = {}
        for endpoints in support.values():
            self.check('histogram')
            self.info['histogram_entries'] += 1
            if not endpoints:
                return None
            size = len(endpoints)
            histogram[size] = histogram.get(size, 0) + 1
        return dict(histogram=histogram, redundancy=couplers - len(self._keys) // 2)

    def improves(self, before, after):
        started = time.perf_counter()
        self.info['comparisons'] += 1
        first = change = None
        try:
            for k in before['histogram'].keys() | after['histogram'].keys():
                self.check('comparison')
                self.info['comparison_entries'] += 1
                delta = after['histogram'].get(k, 0) - before['histogram'].get(k, 0)
                if delta and (first is None or k < first):
                    first, change = k, delta
            self.check('comparison_complete')
            return change is not None and change < 0
        except ScoreDeadline:
            self.info['comparison_interrupted'] += 1
            self.info['interrupted_stage'] = self._stage
            raise
        finally:
            self.info['comparison_wall'] += time.perf_counter() - started
