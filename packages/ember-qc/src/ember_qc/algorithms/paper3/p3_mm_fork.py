"""
ember_qc/algorithms/paper3/p3_mm_fork.py
========================================
CLI-usable arms for the paper3 fork switches (P4 shortener economics + P6
anatomy; specs in ``docs/paper3/proposals/{shortener,anatomy}.md``). Each arm
is exactly one switch flipped on the forked minorminer
(``ember_qc.algorithms.minorminer_forked.forked_find_embedding``); the control
arm for every one of them is plain ``mmfork`` (== stock minorminer 0.2.22).

Registered sparingly, per the specs:

  p3-mm-audit   short_audit=2, audit_budget=3 — budgeted audition in
                ``find_short_chain`` (P4)
  p3-mm-dirty   dirty_skip=1 — negative-result cache in the chainlength
                phase (P4)
  p3-mm-union   chain_tree=1 — the revived union-of-paths constructor, the
                build the 2014 CMR paper describes (P6)

Everything else (``short_audit=1``, ``chain_tree=2``, ``root_boltzmann``,
``max_beta``, combinations) stays kwargs-only through
``forked_find_embedding`` for the script route.

Per ``docs/paper3/protocol.md``, internal fallback-to-stock-MM is OFF by
default for p3 arms (a fallback variant would need an explicit ``-fb`` name);
override per call with ``fallback=True`` if ever needed.
"""
from __future__ import annotations

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.algorithms.minorminer_forked import (
    _FORK_DIR,
    _find_so,
    forked_find_embedding,
)


class _P3ForkArm(EmbeddingAlgorithm):
    """One fork switch engaged; everything else stock. Pure arm (no fallback)."""

    _kwargs: dict = {}
    _install_instruction = "build the fork: bash scripts/build_mm_fork.sh"

    @classmethod
    def is_available(cls) -> tuple:
        if _find_so() is None:
            return (False, f"forked _minorminer not built ({_FORK_DIR})\n"
                           f"  {cls._install_instruction}")
        return (True, "")

    @property
    def version(self) -> str:
        return "0.2.22+ember-p3"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        seed = kwargs.get("seed", 0) or 0
        fallback = bool(kwargs.get("fallback", False))
        return forked_find_embedding(source_graph, target_graph, seed=int(seed),
                                     timeout=timeout, fallback=fallback,
                                     **self._kwargs)


@register_algorithm("p3-mm-audit")
class P3MMAudit(_P3ForkArm):
    """mmfork + short_audit=2 (audit_budget=3): audition meeting points in
    estimated-cost order, stop at the first strict improvement or after 3
    constructions, instead of stock's construct-at-every-meeting-point."""
    _kwargs = dict(short_audit=2, audit_budget=3)


@register_algorithm("p3-mm-dirty")
class P3MMDirty(_P3ForkArm):
    """mmfork + dirty_skip=1: skip re-auditing a variable in the chainlength
    phase while no chain in its closed neighborhood has changed since its last
    failed audition (fingerprint-tracked; conservative)."""
    _kwargs = dict(dirty_skip=1)


@register_algorithm("p3-mm-union")
class P3MMUnion(_P3ForkArm):
    """mmfork + chain_tree=1: chains built by the revived ``construct_chain``
    (union of independent shortest paths — exactly the 2014 paper's build)
    instead of the shipped nearest-attach Steiner constructor."""
    _kwargs = dict(chain_tree=1)
