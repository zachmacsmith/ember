"""
ember_qc/algorithms/factored/loop.py
======================================
The embedding loop: minorminer's outer search with the three factored choices
injected — vertex **order** (``search_orders.ORDERINGS`` + ``"random"``),
chain **tree** construction (``trees.TREES``), and qubit **cost**
(``costs.COSTS``). Design rationale in ``docs/paper2/notes.md``.

Structure (identical in shape to minorminer's):

    for each pass (up to max_passes, deadline-checked):
        for each source vertex, in the configured order:
            release its old chain, rebuild it cheapest-first under the current
            prices (overlaps allowed — they are priced, not forbidden), claim it
        if no qubit is contested and the embedding is valid: done
        else apply the cost's history update and go again

Vertices whose neighbours are all unplaced (the first vertex; component roots)
are seeded on a single free qubit far from the occupied region. The backend
legalizer (``resolve_overlaps``) runs only as a last resort when the pass
budget or deadline expires while contention remains.

Determinism: every ingredient (orders, tree assembly, seeding, the legalizer's
seeded RNG) is deterministic per ``seed``, so identical calls give identical
embeddings.
"""

from __future__ import annotations

import collections
import logging
import random
import time
from dataclasses import dataclass, fields, replace
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx

from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    is_valid_embedding,
    resolve_overlaps,
)
from ember_qc.algorithms.search_orders import ORDERINGS, bfs_maxdeg_order
from ember_qc.algorithms.factored.costs import COSTS, estimate_diameter
from ember_qc.algorithms.factored.trees import TREES
from ember_qc.algorithms.factored.polish import polish as polish_embedding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouterConfig:
    """One point in the algorithm family.

    The minorminer corner is ``RouterConfig(order="random", tree="union",
    alpha=0.0)``; the paper-2 default is below. Any field can be overridden
    per-call via keyword arguments to :func:`embed_factored`.
    """
    order: str = "cuthill"        # key of ORDERINGS, or "random"
    tree: str = "sph"             # key of trees.TREES
    cost: str = "negotiated"      # key of costs.COSTS
    alpha: float = 1.0            # history step size; 0 = memoryless (MM)
    beta: Optional[float] = None  # exponential base; None = estimated diam(G)
    beta_ramp_passes: int = 0     # >0: ramp effective base 1 -> beta (ME-style)
    max_passes: int = 64
    polish: bool = False          # post-legality cleanup (spur-prune + shorten)
    # minorminer-faithful randomization channels (verified against their source,
    # notes.md §3.8). Off by default: flags-off is the deterministic router.
    order_per_pass: bool = False  # recompute/reshuffle the vertex order each pass
    random_ties: bool = False     # uniform root choice among exact tie set +
                                  # random first-seed qubit (MM's choice noise)


def _vertex_order(source: nx.Graph, name: str, rng: random.Random) -> List[int]:
    """Placement order for the source vertices; must be a permutation."""
    nodes = sorted(source.nodes())
    if name == "random":
        order = list(nodes)
        rng.shuffle(order)
        return order
    fn = ORDERINGS.get(name)
    order = list(fn(source)) if fn is not None else []
    if len(order) != len(nodes) or set(order) != set(nodes):
        return bfs_maxdeg_order(source)
    return order


def _seed_qubit(qubits: Sequence[int], adj: Adjacency, occ: Dict[int, int],
                rng: Optional[random.Random] = None) -> int:
    """A single qubit for a vertex with no placed neighbour.

    With an rng: a uniform random free qubit (minorminer-faithful). This
    matters under randomized vertex orders, where several pass-0 vertices have
    no placed neighbour yet — the deterministic farthest-from-occupied rule
    below would scatter those seeds to mutually opposite corners of the fabric,
    whose connecting chains then become cross-fabric walls (measured: 0/3
    legalization on instances the same loop solves under Cuthill–McKee).

    Deterministic (rng=None, the flags-off router): lowest-id free qubit for
    the first placement; farthest-in-hops from everything occupied for later
    isolated placements, so disconnected source components spread out.
    """
    free = [q for q in qubits if occ[q] == 0]
    if rng is not None:
        pool = sorted(free) if free else sorted(qubits)
        return pool[rng.randrange(len(pool))]
    occupied = [q for q in qubits if occ[q] > 0]
    if not occupied:
        return min(free or list(qubits))
    dist: Dict[int, int] = {q: 0 for q in occupied}
    dq = collections.deque(occupied)
    while dq:
        x = dq.popleft()
        dx = dist[x]
        for w in adj[x]:
            if w not in dist:
                dist[w] = dx + 1
                dq.append(w)
    cand = free or list(qubits)
    unreached = 1 << 30
    return max(cand, key=lambda q: (dist.get(q, unreached), -q))


def _materialise(chains: Embedding) -> Embedding:
    return {int(v): [int(q) for q in chain] for v, chain in chains.items()}


def embed_factored(
    source_graph: nx.Graph,
    target_graph: nx.Graph,
    *,
    timeout: float = 60.0,
    seed: int = 0,
    config: Optional[RouterConfig] = None,
    **overrides,
) -> dict:
    """Functional entry point; returns an ember-qc result dict (never raises).

    ``overrides`` matching :class:`RouterConfig` fields replace those fields;
    unknown keyword arguments are ignored (the harness passes extras through).
    """
    start = time.perf_counter()
    deadline = start + timeout if timeout else None

    counters = {
        "target_node_visits": 0,
        "cost_function_evaluations": 0,
        "embedding_state_mutations": 0,
        "overlap_qubit_iterations": 0,
    }

    def _failure(status: str = "FAILURE", **extra) -> dict:
        return {"embedding": {}, "time": time.perf_counter() - start,
                "success": False, "status": status, **counters, **extra}

    try:
        cfg = config if config is not None else RouterConfig()
        known = {f.name for f in fields(RouterConfig)}
        picked = {k: v for k, v in overrides.items() if k in known}
        if picked:
            cfg = replace(cfg, **picked)
        if cfg.tree not in TREES:
            return _failure(error=f"unknown tree strategy {cfg.tree!r}")
        if cfg.cost not in COSTS:
            return _failure(error=f"unknown cost model {cfg.cost!r}")

        adj = build_adjacency(target_graph)
        qubits: Tuple[int, ...] = tuple(adj.keys())
        nodes = sorted(source_graph.nodes())
        if not nodes or not qubits or len(nodes) > len(qubits):
            return _failure()
        src_adj = {v: sorted(source_graph.neighbors(v)) for v in nodes}

        rng = random.Random(seed)
        order = _vertex_order(source_graph, cfg.order, rng)
        beta = cfg.beta if cfg.beta is not None else float(estimate_diameter(adj))
        cost = COSTS[cfg.cost](
            qubits, beta=beta, alpha=cfg.alpha,
            beta_ramp_passes=cfg.beta_ramp_passes,
        )
        tree_fn = TREES[cfg.tree]

        visits = [0]
        chains: Embedding = {}
        legal: Optional[Embedding] = None
        out_of_time = False

        tie_rng = rng if cfg.random_ties else None
        for pass_idx in range(cfg.max_passes):
            if deadline is not None and time.perf_counter() > deadline:
                break
            if cfg.order_per_pass and pass_idx > 0:
                order = _vertex_order(source_graph, cfg.order, rng)
            cost.start_pass(pass_idx)
            for v in order:
                if deadline is not None and time.perf_counter() > deadline:
                    out_of_time = True
                    break
                old = chains.pop(v, None)
                if old is not None:
                    cost.release(old)
                    counters["embedding_state_mutations"] += len(old)
                placed = [u for u in src_adj[v] if u in chains]
                chain: Optional[List[int]] = None
                if placed:
                    counters["cost_function_evaluations"] += 1
                    chain = tree_fn(v, placed, chains, adj, cost.prices, visits,
                                    rng=tie_rng)
                if not chain:
                    chain = [_seed_qubit(qubits, adj, cost.occ, rng=tie_rng)]
                chains[v] = chain
                cost.claim(chain)
                counters["embedding_state_mutations"] += len(chain)
            if out_of_time:
                break
            contested = cost.contested()
            counters["overlap_qubit_iterations"] += len(contested)
            if not contested:
                emb = _materialise(chains)
                if is_valid_embedding(emb, source_graph, target_graph, adj=adj):
                    legal = emb
                    break
                # Disjoint but invalid (an unreachable neighbour got seeded):
                # keep passing — chains are state, so the configuration can
                # still evolve even though prices are momentarily conflict-free.
            else:
                cost.apply_history_update()

        if legal is None and chains:
            emb = _materialise(chains)
            if is_valid_embedding(emb, source_graph, target_graph, adj=adj):
                legal = emb
            else:
                legal = resolve_overlaps(
                    chains, source_graph, target_graph, seed=seed, adj=adj,
                )

        if legal is not None and cfg.polish:
            polished = polish_embedding(
                legal, src_adj, adj, deadline=deadline, visit_counter=visits,
            )
            # Paranoia guard: polish preserves validity by construction, but a
            # broken cleanup must never be able to corrupt a legal result.
            if is_valid_embedding(polished, source_graph, target_graph, adj=adj):
                legal = polished

        counters["target_node_visits"] = int(visits[0])

        if legal is None:
            return _failure()
        return {"embedding": legal,
                "time": time.perf_counter() - start, **counters}
    except Exception as exc:
        logger.error("factored embed error: %s", exc)
        return _failure(error=str(exc))
