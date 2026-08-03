"""
ember_qc/algorithms/paper3/clmm.py
===================================
P2 — CLMM: clique-template-seeded minorminer (Zbinden, Bärtschi, Eidenbenz,
Djidjev 2020, ISC LNCS 12151) and the ++ core-seeded variant.

Two registered arms (spec: ``docs/paper3/proposals/clmm.md``):

``p3-clmm`` — the faithful reproduction (the mandatory literature control).
    k = min(n, busclique max clique) right-sized clique chains from
    ``busgraph_cache(target).find_clique_embedding(k)`` are handed to STOCK
    ``minorminer.find_embedding`` as ``initial_chains``; MM legalizes around
    them (``skip_initialization`` left at its default False). When k < n the
    chains go to k random vertices (edge density >= 0.3, rng from the kwargs
    seed) or k lowest-degree vertices (density < 0.3) — Zbinden's rule.
    Single shot, no restarts: CLMM is not a restart scheme. Semantics match
    the script-local ``clmm`` arm in ``docs/paper3/data/e0_crossover.py``
    (same k, same selection, same tie-breaks, same MM call, same >=1 s MM
    floor), with one necessary deviation: a registered arm cannot see the
    generator parameter p, so the density test uses ``nx.density(source)``.

``p3-clmm-core`` — the ++ variant. Instead of degree/random selection, seed
    the degeneracy core: peel the source by the degeneracy elimination order
    (``search_orders.degeneracy_order`` placement order = reverse
    elimination) until <= k vertices remain, and seed exactly those. Each
    seeded chain is SPUR-PRUNED (``factored.polish.spur_prune``) against the
    source's edges *among the seeded vertices* before it is handed to MM, so
    the seed pays only for adjacency the core actually needs. The periphery
    is left entirely to MM's search — the regime where MM excels.

Contract notes: never raises; returns plain int chain lists; cooperative
timeout (busclique stage is bounded, spur_prune takes a deadline, MM gets the
remaining wall-clock as its native ``timeout``); same seed -> same output; no
stdout. The source is passed to MM as the GRAPH OBJECT — the edge-list form
silently drops isolated vertices (see ``algorithms/minorminer.py``).

The busclique cache is memoized module-wide, keyed by
``busgraph_cache(g).topology_identifier()`` (a topology hash, so any graph
object of the same topology shares the entry): the entry stores the cache
object, the max-clique size, the frozen target adjacency, and each per-k
chain template — repeat calls never rebuild any of them.
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Dict, List, Optional

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm

logger = logging.getLogger(__name__)

# Zbinden's selection-rule density split (their Pegasus result: random
# selection wins at/above ~0.3, lowest-degree below).
_DENSITY_SPLIT = 0.3

# e0_crossover.py parity: the MM stage always gets at least this much of the
# wall clock, even if the template stage ate the budget (MM's timeout is
# cooperative; the contract grace period absorbs the floor).
_MM_FLOOR_S = 1.0

# p3-clmm-core only: spur_prune may use at most this fraction of the budget,
# so a slow prune can never starve the MM stage (truncated pruning is safe —
# spur_prune is validity-preserving move by move).
_PRUNE_BUDGET_FRAC = 0.5


# ---------------------------------------------------------------------------
# busclique template cache (module-level, per topology)
# ---------------------------------------------------------------------------

# topology_identifier() -> {"cache": busgraph_cache, "maxclique": int,
#                           "adj": Adjacency | None, "templates": {k: chains}}
_BUS_ENTRIES: Dict[str, Dict] = {}


def _bus_entry(target_graph: nx.Graph) -> Dict:
    """Memoized busclique state for a target topology.

    The ``busgraph_cache`` constructor is cheap (~70 ms on P16 with a warm
    disk cache) and raises for non-{chimera, pegasus, zephyr} targets — the
    caller catches. The first call per topology pays for ``largest_clique()``
    (disk-cached by busclique itself); everything else is a dict hit.
    """
    from minorminer.busclique import busgraph_cache

    cache = busgraph_cache(target_graph)
    key = cache.topology_identifier()
    entry = _BUS_ENTRIES.get(key)
    if entry is None:
        entry = {
            "cache": cache,
            "maxclique": len(cache.largest_clique()),
            "adj": None,          # built lazily (only the core variant needs it)
            "templates": {},
        }
        _BUS_ENTRIES[key] = entry
    return entry


def _template_chains(entry: Dict, k: int) -> Optional[List[List[int]]]:
    """The k-clique template as a list of k plain-int chains, index-ordered.

    Returns fresh per-call copies (the memoized lists must never be aliased
    into results or mutated by pruning). None if busclique has no K_k on this
    target (``find_clique_embedding`` returns {} when k exceeds the max
    clique — the caller's ``k = min(n, maxclique)`` should prevent this, but
    never trust it silently).
    """
    tpl = entry["templates"].get(k)
    if tpl is None:
        raw = entry["cache"].find_clique_embedding(k)
        if not raw or len(raw) < k:
            return None
        tpl = [[int(q) for q in raw[key]] for key in sorted(raw)]
        entry["templates"][k] = tpl
    return [list(c) for c in tpl]


def _target_adj(entry: Dict, target_graph: nx.Graph) -> Dict[int, tuple]:
    """Frozen target adjacency (built once per topology; core variant only)."""
    if entry["adj"] is None:
        from ember_qc.embedding_backend import build_adjacency
        entry["adj"] = build_adjacency(target_graph)
    return entry["adj"]


# ---------------------------------------------------------------------------
# seed-vertex selection
# ---------------------------------------------------------------------------

def _ssorted(vals) -> list:
    """Deterministic sort that survives mixed / non-comparable node labels."""
    try:
        return sorted(vals)
    except TypeError:
        return sorted(vals, key=str)


def _select_zbinden(source: nx.Graph, nodes: List, k: int, seed: int) -> List:
    """Zbinden's rule: k random vertices when dense, k lowest-degree when
    sparse (ties by node id). ``nodes`` is the sorted node list; the sample
    draws from it in order, so the choice is a pure function of the seed."""
    if len(nodes) <= k:
        return list(nodes)
    if nx.density(source) >= _DENSITY_SPLIT:
        rng = random.Random(int(seed))
        return _ssorted(rng.sample(nodes, k))
    degs = dict(source.degree())
    return _ssorted(sorted(nodes, key=lambda v: (degs[v], v))[:k])


def _select_core(source: nx.Graph, nodes: List, k: int) -> List:
    """Degeneracy core: peel by the degeneracy elimination order until <= k
    vertices remain — i.e. keep the first k of the reverse-elimination
    placement order (densest-core-first)."""
    if len(nodes) <= k:
        return list(nodes)
    from ember_qc.algorithms.search_orders import degeneracy_order
    return _ssorted(degeneracy_order(source)[:k])


# ---------------------------------------------------------------------------
# core-variant seed pruning
# ---------------------------------------------------------------------------

def _prune_seed_chains(source: nx.Graph, chosen: List,
                       initial: Dict, target_graph: nx.Graph, entry: Dict,
                       deadline: float) -> Dict:
    """Spur-prune the seeded chains against the source edges among the seeded
    vertices (the periphery is unplaced, so only core-internal adjacency can
    be required of a seed). Runs in index space so arbitrary source labels
    never reach spur_prune's int casts."""
    from ember_qc.algorithms.factored.polish import spur_prune

    idx = {v: i for i, v in enumerate(chosen)}
    idx_chains = {i: list(initial[v]) for v, i in idx.items()}
    idx_adj = {
        i: sorted(idx[u] for u in source.neighbors(v) if u in idx)
        for v, i in idx.items()
    }
    adj = _target_adj(entry, target_graph)
    pruned = spur_prune(idx_chains, idx_adj, adj, deadline=deadline)
    return {v: [int(q) for q in pruned[i]] for v, i in idx.items()}


# ---------------------------------------------------------------------------
# the shared CLMM pipeline
# ---------------------------------------------------------------------------

def _clmm_embed(source_graph: nx.Graph, target_graph: nx.Graph,
                timeout: float, seed: int, core_seeding: bool) -> Dict:
    """Template-seed selection + single-shot stock-MM legalization."""
    t0 = time.perf_counter()
    deadline = t0 + timeout

    def _fail(msg: str, status: str = "FAILURE") -> Dict:
        return {"embedding": {}, "time": time.perf_counter() - t0,
                "success": False, "status": status, "error": msg}

    try:
        import minorminer as _mm

        n = source_graph.number_of_nodes()
        if n == 0:
            return _fail("clmm: empty source graph")

        try:
            entry = _bus_entry(target_graph)
        except Exception as e:
            # Not a busclique-supported topology: the CLMM mechanism does not
            # exist here. No silent fallback to stock MM (protocol: fallback
            # variants are explicit, `-fb`).
            return _fail(f"clmm: busclique unavailable for this target ({e})")

        k = min(n, entry["maxclique"])
        chains = _template_chains(entry, k)
        if chains is None:
            return _fail(f"clmm: busclique returned no K_{k} template")

        nodes = _ssorted(source_graph.nodes())
        if core_seeding:
            chosen = _select_core(source_graph, nodes, k)
            selection = "core" if len(nodes) > k else "all"
        else:
            chosen = _select_zbinden(source_graph, nodes, k, seed)
            if len(nodes) <= k:
                selection = "all"
            else:
                selection = ("random" if nx.density(source_graph) >= _DENSITY_SPLIT
                             else "lowdeg")

        initial = {v: chains[i] for i, v in enumerate(chosen)}
        seed_qubits_pre = sum(len(c) for c in initial.values())

        if core_seeding:
            prune_deadline = min(deadline, t0 + _PRUNE_BUDGET_FRAC * timeout)
            initial = _prune_seed_chains(source_graph, chosen, initial,
                                         target_graph, entry, prune_deadline)
        seed_qubits = sum(len(c) for c in initial.values())

        remaining = max(_MM_FLOOR_S, deadline - time.perf_counter())
        # Source as the GRAPH OBJECT (edge-list form drops isolated vertices).
        emb = _mm.find_embedding(
            source_graph,
            list(target_graph.edges()),
            initial_chains=initial,
            timeout=remaining,
            random_seed=int(seed),
        )
        elapsed = time.perf_counter() - t0
        if not emb:
            status = ("TIMEOUT" if time.perf_counter() >= deadline
                      else "FAILURE")
            return _fail("clmm: MM stage returned empty", status)

        embedding = {v: [int(q) for q in c] for v, c in emb.items()}
        return {
            "embedding": embedding,
            "time": elapsed,
            "metadata": {
                "template_k": k,
                "n_seeded": len(initial),
                "selection": selection,
                "seed_qubits_pre_prune": seed_qubits_pre,
                "seed_qubits": seed_qubits,
                "maxclique": entry["maxclique"],
            },
        }
    except Exception as e:  # contract: never raise
        logger.error("p3-clmm%s error: %s",
                     "-core" if core_seeding else "", e)
        return _fail(f"clmm: {e}")


# ---------------------------------------------------------------------------
# registered arms
# ---------------------------------------------------------------------------

_GUARD_MIN_DENSITY = 0.15          # §4.11 M5 guard (P16/Z12-class win regime)
_GUARD_MIN_DENSITY_CHIMERA = 0.35  # §4.11-C16: Chimera's crossover sits higher
_GUARD_CHIMERA_RATIO = 1.6         # chimera-class iff kmax < 1.6 * sqrt(|target|)


def _guard_threshold(target_graph: nx.Graph) -> float:
    """v1.2 architecture-aware gate threshold (improvement-notes #11).

    §4.11-C16 evidence: the flat 0.15 density gate, calibrated on P16/Z12,
    sits below Chimera's higher crossover — 8 mid-family mean-ACL bar trips on
    the C16 library sweep. The fix is keyed on the busclique max clique
    (``_bus_entry(target)["maxclique"]``; the topology_identifier is an opaque
    sha, so kmax is the fabric signal), normalized by target size so the class
    is size-invariant: chimera-class fabrics have kmax/sqrt(|V|) = sqrt(2)
    ~ 1.41 at every size (C16: 64/sqrt(2048); chimera_graph(4): 16/sqrt(128)),
    while pegasus/zephyr-class sit >= 1.7 (P16: 180/sqrt(5640) = 2.40, Z12:
    184/sqrt(4800) = 2.66; pegasus_graph(4): 36/sqrt(264) = 2.22,
    zephyr_graph(3): 40/sqrt(336) = 2.18). At the flagship sizes this is the
    C16 kmax ~ 64 vs P16 = 180 / Z12 = 184 split. Chimera-class targets gate
    at 0.35; pegasus/zephyr-class keep the measured 0.15 (P16/Z12 behavior
    unchanged by construction — the §5 frozen-arm requirement). Any failure
    (non-busclique target) -> 0.15, exactly the v1.1 behavior.
    """
    try:
        kmax = _bus_entry(target_graph)["maxclique"]
        if 0 < kmax < _GUARD_CHIMERA_RATIO * math.sqrt(
                max(1, target_graph.number_of_nodes())):
            return _GUARD_MIN_DENSITY_CHIMERA
    except Exception:
        pass
    return _GUARD_MIN_DENSITY


def _guarded_embed(source_graph, target_graph, timeout, seed, core_seeding,
                   guard):
    """Density gate (v1.1; per-architecture threshold since v1.2): below the
    measured win regime (E0/M5: seeds hurt on sparse/structured sources), pass
    through to plain full-budget stock MM so the arm is exactly minorminer
    off-regime. ``guard=False`` (script-route kwargs) restores the unguarded
    faithful behavior for science runs."""
    if guard and nx.density(source_graph) < _guard_threshold(target_graph):
        t0 = time.perf_counter()
        try:
            import minorminer
            raw = minorminer.find_embedding(
                source_graph, list(target_graph.edges()),
                timeout=timeout, random_seed=seed, verbose=0)
            if not raw:
                return {"embedding": {}, "time": time.perf_counter() - t0,
                        "success": False, "status": "FAILURE"}
            emb = {int(w): [int(q) for q in c] for w, c in raw.items()}
            return {"embedding": emb, "time": time.perf_counter() - t0,
                    "metadata": {"selection": "guard_passthrough_mm",
                                 "guard_threshold": _guard_threshold(target_graph)}}
        except Exception as e:  # contract: never raise
            logger.error("p3-clmm guard passthrough error: %s", e)
            return {"embedding": {}, "time": time.perf_counter() - t0,
                    "success": False, "status": "FAILURE", "error": str(e)}
    return _clmm_embed(source_graph, target_graph, timeout, seed,
                       core_seeding=core_seeding)


@register_algorithm("p3-clmm")
class ClmmAlgorithm(EmbeddingAlgorithm):
    """CLMM (Zbinden et al. 2020): right-sized busclique clique chains as
    initial_chains for single-shot stock minorminer; degree/random seed-vertex
    selection at density 0.3. v1.1: density-gated (passthrough to stock MM
    below the gate — §4.11 M5 guard). v1.2: the gate is kmax-keyed per target
    architecture (improvement-notes #11, §4.11-C16): chimera-class fabrics
    (C16 kmax ~ 64) gate at 0.35, pegasus/zephyr-class (P16 = 180 / Z12 = 184)
    keep 0.15 — P16/Z12 behavior identical to v1.1. guard=False kwarg restores
    the faithful literature-control behavior."""

    _requires = ["minorminer"]
    supported_counters: List[str] = []

    @property
    def version(self) -> str:
        return "1.2.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        seed = kwargs.get("seed", None)
        if seed is None:
            seed = 42
        return _guarded_embed(source_graph, target_graph, float(timeout),
                              int(seed), core_seeding=False,
                              guard=kwargs.get("guard", True))


@register_algorithm("p3-clmm-core")
class ClmmCoreAlgorithm(EmbeddingAlgorithm):
    """CLMM++: seed the degeneracy core (peel by degeneracy order to <= k
    vertices) with spur-pruned busclique chains; periphery left entirely to
    stock minorminer's search. v1.1: density-gated like p3-clmm. v1.2:
    kmax-keyed per-architecture gate (0.35 chimera-class / 0.15
    pegasus-zephyr-class; P16/Z12-identical to v1.1)."""

    _requires = ["minorminer"]
    supported_counters: List[str] = []

    @property
    def version(self) -> str:
        return "1.2.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        seed = kwargs.get("seed", None)
        if seed is None:
            seed = 42
        return _guarded_embed(source_graph, target_graph, float(timeout),
                              int(seed), core_seeding=True,
                              guard=kwargs.get("guard", True))
