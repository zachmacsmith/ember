"""
dirtyset_propagation_experiment.py
==================================
Decide the dirty-set propagation rule. Compares, against the baseline router:

  A) SOURCE-LOCAL (shipped): on accept, re-dirty the closed source-neighbourhood
     of the changed chains ({v} u displaced).
  B) OCCUPANCY-AWARE: (A) PLUS re-dirty owners of chains physically adjacent to
     the qubits whose occupancy changed (the "global occupancy leak" that a
     source-local rule misses) -- aims to match baseline's fixpoint exactly.

Reports per cell: baseline ACL, rule-A ACL/calls, rule-B ACL/calls. The point is
to see whether (B) closes the small ACL drift (A) shows on a couple of cells and
at what extra _try_shorten cost.

Run: .venv/bin/python docs/candidate-algorithms/data/dirtyset_propagation_experiment.py
"""
from __future__ import annotations

import os
import sys
import statistics as st
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

from ember_qc.algorithms import reweave as pf  # noqa: E402
from ember_qc.algorithms.rw_dirtyset import DirtySetRouter  # noqa: E402
from ember_qc.embedding_backend import is_valid_embedding  # noqa: E402

import time
from typing import Optional, Set


class OccAwareRouter(DirtySetRouter):
    """Dirty-set with the extra occupancy-leak propagation (rule B)."""

    def _lns_improve(self, deadline: Optional[float]):
        best = self._materialise()
        best_total = sum(len(c) for c in self.chains.values())
        dirty: Set[int] = set(self.chains)
        while dirty:
            if deadline is not None and time.perf_counter() > deadline:
                return best
            v = max(dirty, key=lambda u: (len(self.chains[u]), -u))
            dirty.discard(v)
            if len(self.chains[v]) <= 1:
                continue
            before = dict(self.chains)
            accepted = self._try_shorten(v, best_total)
            if not accepted:
                continue
            displaced = tuple(
                w for w, c in self.chains.items() if w != v and before.get(w) is not c
            )
            best = self._materialise()
            best_total = sum(len(c) for c in self.chains.values())
            changed = (v, *displaced)
            # (A) source-local
            for w in changed:
                dirty.add(w)
                dirty.update(self.src_adj[w])
            # (B) occupancy-leak: qubits whose occupancy changed this move
            q_delta: Set[int] = set()
            for w in changed:
                q_delta ^= set()  # noop to keep types
                q_delta |= set(before[w]) ^ set(self.chains[w])
            region: Set[int] = set(q_delta)
            for q in q_delta:
                region.update(self.adj.get(q, ()))
            owner = {q: vid for vid, ch in self.chains.items() for q in ch}
            for q in region:
                o = owner.get(q)
                if o is not None:
                    dirty.add(o)
        return best


# instrument call counts on the shared base method
_orig = pf.ReweaveRouter._try_shorten
_calls = {"n": 0}


def _counting(self, v, bt):
    _calls["n"] += 1
    return _orig(self, v, bt)


pf.ReweaveRouter._try_shorten = _counting


def run(router_cls, src, tgt, seed):
    _calls["n"] = 0
    r = router_cls(src, tgt, seed=seed, base_method="minorminer")
    t0 = time.perf_counter()
    emb = r.run(deadline=None, base_timeout=30.0)
    dt = time.perf_counter() - t0
    acl = sum(len(c) for c in emb.values()) / len(emb)
    return emb, acl, _calls["n"], dt, is_valid_embedding(emb, src, tgt)


GRID = [
    ("ER", 20, 0.5, "pegasus_6"), ("ER", 30, 0.5, "pegasus_6"),
    ("ER", 30, 0.7, "pegasus_6"), ("ER", 40, 0.5, "pegasus_6"),
    ("ER", 40, 0.7, "pegasus_6"), ("ER", 30, 0.5, "pegasus_6_broken5"),
    ("ER", 30, 0.5, "zephyr_4"),
]
SEEDS = [0, 1, 2]
targets = make_targets()

print(f"{'cell':16s} {'base_ACL':>8s} {'A_ACL':>7s} {'B_ACL':>7s} "
      f"{'baseC':>6s} {'A_C':>6s} {'B_C':>6s}   A_valid B_valid")
print("-" * 78)
da_list, db_list, ca_ratio, cb_ratio = [], [], [], []
for (fam, n, p, tname) in GRID:
    src = make_source(fam, n, p)
    tgt = targets[tname]
    cell = f"{fam}_n{n}_d{p}"
    for s in SEEDS:
        _, acl_base, c_base, _, _ = run(pf.ReweaveRouter, src, tgt, s)
        _, acl_a, c_a, _, val_a = run(DirtySetRouter, src, tgt, s)
        _, acl_b, c_b, _, val_b = run(OccAwareRouter, src, tgt, s)
        da_list.append(acl_a - acl_base)
        db_list.append(acl_b - acl_base)
        ca_ratio.append(c_a / c_base if c_base else 1.0)
        cb_ratio.append(c_b / c_base if c_base else 1.0)
        mark = "" if acl_a <= acl_base + 1e-9 and acl_b <= acl_base + 1e-9 else "  <-"
        print(f"{cell:16s} {acl_base:>8.3f} {acl_a:>7.3f} {acl_b:>7.3f} "
              f"{c_base:>6d} {c_a:>6d} {c_b:>6d}   {int(val_a):>7d} {int(val_b):>7d}{mark}")

print("-" * 78)
print(f"mean dACL  A vs base = {st.mean(da_list):+.4f}   B vs base = {st.mean(db_list):+.4f}")
print(f"mean callratio  A = {st.mean(ca_ratio):.3f}x   B = {st.mean(cb_ratio):.3f}x")
pf.ReweaveRouter._try_shorten = _orig
