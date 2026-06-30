"""
dirtyset_verify.py — quick-verify the reweave-dirtyset variant (S4).

Checks, on a few small (cell, seed) pairs:
  1. contract: module import registers "reweave-dirtyset"; embed() returns a
     dict with a valid embedding.
  2. determinism: same seed -> identical embedding.
  3. ACL parity: dirty-set ACL is not worse than baseline (per cell/seed).
  4. work reduction: count of _try_shorten calls, dirty-set vs baseline router,
     on the SAME seeded warm-start state (isolates the schedule change).

Run: .venv/bin/python docs/candidate-algorithms/data/dirtyset_verify.py
"""
from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

import ember_qc.algorithms.rw_dirtyset  # noqa: E402  (registers the variant)
from ember_qc.algorithms import reweave as pf  # noqa: E402
from ember_qc.algorithms.rw_dirtyset import DirtySetRouter  # noqa: E402
from ember_qc.registry import ALGORITHM_REGISTRY  # noqa: E402
from ember_qc.benchmark import benchmark_one  # noqa: E402
from ember_qc.embedding_backend import is_valid_embedding  # noqa: E402

assert "reweave-dirtyset" in ALGORITHM_REGISTRY, "variant not registered!"
print("contract: 'reweave-dirtyset' registered OK")

targets = make_targets()
CELLS = [
    ("ER", 20, 0.5, "pegasus_6"),
    ("ER", 30, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6"),
]
SEEDS = [0, 1, 2]

# ---- instrument _try_shorten to count calls (wraps the shared base method) ----
_orig_try_shorten = pf.ReweaveRouter._try_shorten
_calls = {"n": 0}


def _counting_try_shorten(self, v, best_total):
    _calls["n"] += 1
    return _orig_try_shorten(self, v, best_total)


pf.ReweaveRouter._try_shorten = _counting_try_shorten


def run_router(router_cls, src, tgt, seed):
    """One seed->improve attempt; returns (embedding, n_try_shorten_calls)."""
    _calls["n"] = 0
    router = router_cls(src, tgt, seed=seed, base_method="minorminer")
    emb = router.run(deadline=None, base_timeout=30.0)
    return emb, _calls["n"]


print(f"\n{'cell':16s} {'seed':>4s} {'base_ACL':>8s} {'dirty_ACL':>9s} "
      f"{'base_calls':>10s} {'dirty_calls':>11s} {'call_ratio':>10s} valid")
print("-" * 84)
all_ok = True
for (fam, n, p, tname) in CELLS:
    src = make_source(fam, n, p)
    tgt = targets[tname]
    cell = f"{fam}_n{n}_d{p}"
    for s in SEEDS:
        emb_b, calls_b = run_router(pf.ReweaveRouter, src, tgt, s)
        emb_d, calls_d = run_router(DirtySetRouter, src, tgt, s)
        # determinism: re-run dirty-set, must be identical
        emb_d2, _ = run_router(DirtySetRouter, src, tgt, s)
        det = emb_d == emb_d2

        valid_b = bool(emb_b) and is_valid_embedding(emb_b, src, tgt)
        valid_d = bool(emb_d) and is_valid_embedding(emb_d, src, tgt)
        acl_b = (sum(len(c) for c in emb_b.values()) / len(emb_b)) if emb_b else float("nan")
        acl_d = (sum(len(c) for c in emb_d.values()) / len(emb_d)) if emb_d else float("nan")
        ratio = (calls_d / calls_b) if calls_b else float("nan")
        ok = valid_d and det and (acl_d <= acl_b + 1e-9)
        all_ok &= ok
        flag = "" if ok else "  <-- CHECK"
        det_flag = "" if det else " NONDET!"
        print(f"{cell:16s} {s:>4d} {acl_b:>8.3f} {acl_d:>9.3f} "
              f"{calls_b:>10d} {calls_d:>11d} {ratio:>9.2f}x "
              f"{int(valid_d)}{det_flag}{flag}")

# restore
pf.ReweaveRouter._try_shorten = _orig_try_shorten

print("\nALL CHECKS PASS" if all_ok else "\nSOME CHECKS FAILED")
sys.exit(0 if all_ok else 1)
