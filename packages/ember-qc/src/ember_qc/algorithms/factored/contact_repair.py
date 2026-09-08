"""Bounded contact search on small groups of physical branch sets.

This module operates on a valid incumbent. It preserves frozen chains and
reconstructs selected chains in a small beam of alternative local assignments.
Contacts with frozen neighbors can move, and one selected chain may grow when
the whole group shrinks. Routing uses only bounded breadth-first searches in
the supplied target. No external embedding algorithm or optimization solver is
used. Partial-construction support is deliberately not part of this first API.

The incumbent is kept independently from the beam: an interrupted or exhausted
search cannot destroy it. Beam prefixes contain only group assignments and
occupancy deltas, never copies of the entire target or incumbent embedding.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
import time
from typing import Optional


_popcount = getattr(int, "bit_count", lambda value: bin(value).count("1"))


def _ordered(nodes):
    # Stable for mixed ordinary NetworkX labels; no coercion of labels to ints.
    return sorted(nodes, key=lambda q: (type(q).__name__, repr(q)))


class _Context:
    def __init__(self, source, target):
        self.nodes = _ordered(source)
        self.rank = {q: i for i, q in enumerate(_ordered(target))}
        self.adj = {q: tuple(sorted(target[q], key=self.rank.__getitem__))
                    for q in self.rank}
        self.src_adj = {v: tuple(_ordered(source[v])) for v in self.nodes}
        self.edges = tuple(source.edges())
        self.max_degree = max(map(len, self.adj.values()), default=0)

    def valid(self, embedding):
        if set(embedding) != set(self.nodes):
            return False
        owner = {}
        for v, chain in embedding.items():
            if not chain:
                return False
            for q in chain:
                if q not in self.adj or q in owner:
                    return False
                owner[q] = v
            todo = [chain[0]]
            reached = {chain[0]}
            chain_set = set(chain)
            while todo:
                for q in self.adj[todo.pop()]:
                    if q in chain_set and q not in reached:
                        reached.add(q)
                        todo.append(q)
            if reached != chain_set:
                return False
        for v, w in self.edges:
            if not any(owner.get(q) == w for p in embedding[v]
                       for q in self.adj[p]):
                return False
        return True

    def lower_bound(self, v):
        # A connected L-qubit set has at most (Delta-2)*L+2 boundary
        # edges, so it cannot contact more distinct source neighbors.
        if self.max_degree <= 2:
            return 1
        return max(1, math.ceil((len(self.src_adj[v]) - 2)
                               / (self.max_degree - 2)))


@dataclass
class _Budget:
    limit: int
    deadline: Optional[float]
    expansions: int = 0
    stopped_by: Optional[str] = None

    def check(self):
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            self.stopped_by = "deadline"
            return False
        if self.expansions >= self.limit:
            self.stopped_by = "work_limit"
            return False
        return True

    def pop(self):
        if not self.check():
            return False
        self.expansions += 1
        return True


def _region(ctx, embedding, selected, halo, max_region, budget):
    old = {q for v in selected for q in embedding[v]}
    if len(old) > max_region:
        return None
    frozen = {q for v, c in embedding.items() if v not in selected for q in c}
    region = set(old)
    frontier = sorted(old, key=ctx.rank.__getitem__)
    for _ in range(halo):
        nxt = []
        for q in frontier:
            if not budget.pop():
                return region
            for r in ctx.adj[q]:
                if r not in frozen and r not in region:
                    if len(region) >= max_region:
                        return region
                    region.add(r)
                    nxt.append(r)
        frontier = nxt
        if not frontier:
            break
    return region


def _add_boundary_sites(ctx, embedding, selected, region, max_region,
                        site_limit, budget, info):
    """Add bounded singleton sites satisfying each vertex's frozen contacts.

    Keep the original region intact. These sites may still need contacts to
    selected neighbors; the normal reconstruction and validity checks enforce
    those obligations. Scanned physical vertices consume the same work budget
    as routing expansions. No coordinates or graph-family metadata are used.
    """
    if not site_limit or len(region) >= max_region:
        return region
    frozen = {q for v, chain in embedding.items() if v not in selected for q in chain}
    selected_owner = {q: v for v in selected for q in embedding[v]}
    pools = []
    for v in _ordered(selected):
        known = [w for w in ctx.src_adj[v] if w not in selected]
        if not known:
            continue
        sites = None
        for w in known:
            boundary = set()
            for q in embedding[w]:
                if not budget.pop():
                    return region
                info['boundary_expansions'] += 1
                boundary.update(r for r in ctx.adj[q] if r not in frozen)
            sites = boundary if sites is None else sites & boundary
            if not sites:
                break
        pending = selected.intersection(ctx.src_adj[v])
        ranked = []
        for q in sites or ():
            if q in region:
                continue
            if not budget.pop():
                return region
            info['boundary_expansions'] += 1
            old_contacts = {selected_owner[r] for r in ctx.adj[q]
                            if r in selected_owner and selected_owner[r] in pending}
            free_degree = sum(r not in frozen for r in ctx.adj[q])
            ranked.append((-len(old_contacts), -free_degree, ctx.rank[q], q))
        pools.append(iter(item[-1] for item in sorted(ranked)[:site_limit]))
    added = 0
    while pools and added < site_limit and len(region) < max_region:
        active = []
        for pool in pools:
            if not budget.check():
                return region
            q = next(pool, None)
            if q is None:
                continue
            active.append(pool)
            if q not in region:
                region.add(q)
                added += 1
                info['boundary_sites_added'] += 1
            if added >= site_limit or len(region) >= max_region:
                break
        pools = active
    return region


def _grow(root, available, masks, required, ctx, budget, size_cap,
          reverse=False):
    """Connect a root to contact sets by shortest free paths to the tree."""
    tree = {root}
    covered = masks.get(root, 0)
    while covered != required:
        missing = required & ~covered
        queue = deque(sorted(tree, key=ctx.rank.__getitem__, reverse=reverse))
        parent = {q: None for q in tree}
        hit = None
        while queue:
            if not budget.pop():
                return None
            q = queue.popleft()
            neighbors = reversed(ctx.adj[q]) if reverse else ctx.adj[q]
            for r in neighbors:
                if r not in available or r in parent:
                    continue
                parent[r] = q
                if masks.get(r, 0) & missing:
                    hit = r
                    break
                queue.append(r)
            if hit is not None:
                break
        if hit is None:
            return None
        path = []
        while hit not in tree:
            path.append(hit)
            hit = parent[hit]
        if len(tree) + len(path) > size_cap:
            return None
        for q in path:
            tree.add(q)
            covered |= masks.get(q, 0)
    return frozenset(tree)


def _alternatives(v, prefix, occupied, selected, region, embedding, ctx,
                  alternatives, size_cap, budget, info):
    available = region - occupied
    if not available or size_cap < ctx.lower_bound(v) or not budget.check():
        return []
    masks = {}
    soft = {}
    count = 0
    for w in ctx.src_adj[v]:
        if not budget.check():
            return []
        known = w not in selected or w in prefix
        chain = prefix[w] if w in prefix else embedding[w]
        boundary = {r for q in chain for r in ctx.adj[q] if r in available}
        if known:
            if not boundary:
                info["unreachable_contacts"] += 1
                return []
            bit = 1 << count
            count += 1
            for q in boundary:
                masks[q] = masks.get(q, 0) | bit
        else:
            # Pending contacts guide root selection but are not constraints
            # tied to the old position of a chain that will be rebuilt.
            for q in boundary:
                soft[q] = soft.get(q, 0) + 1
    required = (1 << count) - 1
    old = frozenset(embedding[v])
    roots = sorted(available, key=lambda q: (
        -_popcount(masks.get(q, 0)), -soft.get(q, 0),
        q not in old, ctx.rank[q]))
    found = []
    seen = set()

    def add(chain):
        if chain is not None and chain not in seen:
            seen.add(chain)
            found.append(chain)

    # A feasible old choice is retained even when no generated route finds it.
    if old <= available and len(old) <= size_cap:
        covered = 0
        for q in old:
            covered |= masks.get(q, 0)
        if covered == required:
            add(old)
    # Bounded root attempts; duplicates do not consume the alternative quota.
    generated = 0
    for attempt, root in enumerate(roots[:max(1, 3 * alternatives)]):
        if generated >= alternatives or not budget.check():
            break
        info["tree_attempts"] += 1
        chain = _grow(root, available, masks, required, ctx, budget,
                      size_cap, reverse=bool(attempt % 2))
        if chain is not None and chain not in seen:
            add(chain)
            generated += 1
    return sorted(found, key=lambda c: (len(c), tuple(sorted(ctx.rank[q] for q in c))))


def _diagnostics():
    return {"accepted": 0, "qubits_saved": 0, "member_growth": 0,
            "expansions": 0, "region_size": 0, "tree_attempts": 0,
            "beam_expansions": 0, "beam_pruned": 0,
            "unreachable_contacts": 0, "complete_proposals": 0,
            "orders_tried": 0, "boundary_sites_added": 0,
            "boundary_expansions": 0, "stopped_by": None}


def _repair(embedding, ctx, group, *, beam_width, alternatives, halo,
            max_region, max_expansions, max_orders, deadline, boundary_sites=0):
    start = time.perf_counter()
    info = _diagnostics()
    selected = set(group)
    old_size = sum(len(embedding[v]) for v in group)
    budget = _Budget(max_expansions, deadline)
    best = embedding
    best_size = old_size

    def finish(reason):
        ended = time.perf_counter()
        info["expansions"] = budget.expansions
        info["stopped_by"] = budget.stopped_by or reason
        if deadline is not None:
            info['deadline_overrun'] = max(0.0, ended - deadline)
            if ended >= deadline:
                info['stopped_by'] = 'deadline'
        info["wall"] = ended - start
        if best is not embedding:
            info["accepted"] = 1
            info["qubits_saved"] = old_size - best_size
            info["member_growth"] = sum(
                len(best[v]) > len(embedding[v]) for v in group)
        return best, info

    if not budget.check():
        return finish("work_limit")
    if old_size <= sum(ctx.lower_bound(v) for v in group):
        return finish("size_bound")
    region = _region(ctx, embedding, selected, halo, max_region, budget)
    if region is None:
        return finish("region_limit")
    region = _add_boundary_sites(ctx, embedding, selected, region, max_region,
                                 boundary_sites, budget, info)
    info["region_size"] = len(region)
    # Both pair orders; bounded cyclic/reversed orders for larger groups.
    orders = []
    for candidate in (tuple(group), tuple(reversed(group))):
        if candidate not in orders:
            orders.append(candidate)
    for offset in range(1, len(group)):
        candidate = tuple(group[offset:]) + tuple(group[:offset])
        if candidate not in orders:
            orders.append(candidate)
    for order in orders[:max_orders]:
        if not budget.check():
            break
        info["orders_tried"] += 1
        beam = [({}, frozenset(), 0)]
        for index, v in enumerate(order):
            if not budget.check():
                break
            successors = []
            remaining_bound = sum(ctx.lower_bound(w) for w in order[index + 1:])
            for prefix, occupied, size in beam:
                size_cap = best_size - 1 - size - remaining_bound
                choices = _alternatives(
                    v, prefix, occupied, selected, region, embedding, ctx,
                    alternatives, size_cap, budget, info)
                for chain in choices:
                    candidate = dict(prefix)
                    candidate[v] = chain
                    successors.append((candidate, occupied | chain,
                                       size + len(chain)))
                    info["beam_expansions"] += 1
                if not budget.check():
                    break
            successors.sort(key=lambda state: (
                state[2], tuple(tuple(sorted(ctx.rank[q] for q in state[0][w]))
                                for w in order[:index + 1])))
            info["beam_pruned"] += max(0, len(successors) - beam_width)
            beam = successors[:beam_width]
            if not beam:
                break
        for prefix, _occupied, size in beam:
            if len(prefix) != len(group) or size >= best_size:
                continue
            info["complete_proposals"] += 1
            trial = dict(embedding)
            for v, chain in prefix.items():
                trial[v] = sorted(chain, key=ctx.rank.__getitem__)
            # Validate against all original graph obligations before commit.
            if ctx.valid(trial):
                best, best_size = trial, size
    return finish("searched")


def _parameters(beam_width, alternatives, halo, max_region,
                max_expansions, max_orders, boundary_sites=0):
    values = {"beam_width": beam_width, "alternatives": alternatives,
              "halo": halo, "max_region": max_region,
              "max_expansions": max_expansions, "max_orders": max_orders,
              "boundary_sites": boundary_sites}
    for name, value in values.items():
        minimum = 0 if name in ("halo", "max_expansions", "boundary_sites") else 1
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")


def repair_group(embedding, source_graph, target_graph, group, *,
                 beam_width=4, alternatives=3, halo=2, max_region=512,
                 max_expansions=50000, max_orders=2, deadline=None, boundary_sites=0):
    """Try a strictly shorter replacement of 1–4 selected chains.

    ``deadline`` is an absolute ``time.perf_counter()`` timestamp.
    ``max_expansions`` bounds popped vertices across region BFS and routing.
    A one-chain group is supported for the controlled local-move ablation.
    No input graph, chain list, or embedding mapping is mutated. Invalid input
    returns unchanged with ``invalid_input=True``. A timeout may return a valid
    improvement already found; otherwise the original embedding is returned.
    """
    start = time.perf_counter()
    _parameters(beam_width, alternatives, halo, max_region, max_expansions, max_orders,
                boundary_sites)
    group = tuple(dict.fromkeys(group))
    if not 1 <= len(group) <= 4:
        raise ValueError("group must contain 1–4 distinct source vertices")
    ctx = _Context(source_graph, target_graph)
    if not set(group) <= set(ctx.nodes):
        raise ValueError("group contains an unknown source vertex")
    if not ctx.valid(embedding):
        return embedding, {**_diagnostics(), "invalid_input": True,
                           "stopped_by": "invalid_input",
                           "wall": time.perf_counter() - start}
    result, info = _repair(
        embedding, ctx, group, beam_width=beam_width, alternatives=alternatives,
        halo=halo, max_region=max_region, max_expansions=max_expansions,
        max_orders=max_orders, deadline=deadline, boundary_sites=boundary_sites)
    ended = time.perf_counter()
    info["wall"] = ended - start
    if deadline is not None:
        info['deadline_overrun'] = max(0.0, ended - deadline)
        if ended >= deadline:
            info['stopped_by'] = 'deadline'
    return result, info


def _groups(embedding, ctx, group_sizes, limit):
    if limit <= 0:
        return []
    owner = {q: v for v, c in embedding.items() for q in c}
    excess = {v: len(embedding[v]) - ctx.lower_bound(v) for v in ctx.nodes}
    rank = {v: i for i, v in enumerate(ctx.nodes)}
    centers = sorted(ctx.nodes, key=lambda v: (-excess[v], -len(embedding[v]), rank[v]))
    seen = set()
    out = []
    for v in centers:
        neighbors = set(ctx.src_adj[v])
        # Adjacent occupied chains can block relocation even without a source edge.
        neighbors.update(owner[q] for p in embedding[v] for q in ctx.adj[p]
                         if q in owner and owner[q] != v)
        neighbors = sorted(neighbors, key=lambda w: (-excess[w], -len(embedding[w]), rank[w]))
        for size in group_sizes:
            if len(neighbors) + 1 < size:
                continue
            group = (v, *neighbors[:size - 1])
            key = frozenset(group)
            if key in seen or sum(excess[w] for w in group) <= 0:
                continue
            seen.add(key)
            out.append(group)
            if len(out) >= limit:
                return out
    return out


def contact_polish(embedding, source_graph, target_graph, *, timeout=None,
                   deadline=None, max_passes=2, max_groups=128,
                   group_sizes=(2, 3, 4), beam_width=4, alternatives=3, halo=2,
                   max_region=512, max_expansions=500000,
                   group_expansions=50000, max_orders=2, boundary_sites=0,
                   group_policy="legacy"):
    """Apply bounded group reconstruction to one valid evolving incumbent.

    Global work limits include every attempted group. ``max_groups`` is total,
    not per pass. The fixed source/target adjacency is built once. Groups are
    generated from chain costs, source contacts, and physical blockers; graph
    family names are never used. Outside chains remain fixed for each move.
    """
    start = time.perf_counter()
    _parameters(beam_width, alternatives, halo, max_region, max_expansions, max_orders,
                boundary_sites)
    if group_policy not in ('legacy', 'round_robin'):
        raise ValueError('unknown group policy')
    for name, value in (("max_passes", max_passes), ("max_groups", max_groups),
                        ("group_expansions", group_expansions)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be an integer >= 0")
    group_sizes = tuple(dict.fromkeys(group_sizes))
    if not group_sizes or any(not isinstance(s, int) or isinstance(s, bool)
                              or s not in (1, 2, 3, 4) for s in group_sizes):
        raise ValueError("group_sizes must contain sizes from 1 through 4")
    if timeout is not None:
        if timeout < 0:
            raise ValueError("timeout must be >= 0")
        own_deadline = start + timeout
        deadline = own_deadline if deadline is None else min(deadline, own_deadline)
    ctx = _Context(source_graph, target_graph)
    info = {**_diagnostics(), "groups_tried": 0, "passes": 0,
            "trajectory": [], "max_region_size": 0}
    work = embedding

    def finish(reason):
        ended = time.perf_counter()
        if deadline is not None:
            info['deadline_overrun'] = max(0.0, ended - deadline)
            if ended >= deadline and reason != 'invalid_input':
                reason = 'deadline'
        info["stopped_by"] = reason
        info["wall"] = ended - start
        return work, info

    if not ctx.valid(work):
        info["invalid_input"] = True
        return finish("invalid_input")
    if max_groups == 0:
        return finish("group_limit")
    if max_expansions == 0:
        return finish("work_limit")
    for _ in range(max_passes):
        if deadline is not None and time.perf_counter() >= deadline:
            return finish("deadline")
        if info["groups_tried"] >= max_groups:
            return finish("group_limit")
        if info["expansions"] >= max_expansions:
            return finish("work_limit")
        info["passes"] += 1
        changed = False
        if group_policy == 'round_robin':
            from ember_qc.algorithms.factored.contact_groups import round_robin_groups
            groups = round_robin_groups(work, ctx, group_sizes, max_groups - info['groups_tried'])
        else:
            groups = _groups(work, ctx, group_sizes, max_groups - info["groups_tried"])
        for group in groups:
            if deadline is not None and time.perf_counter() >= deadline:
                return finish("deadline")
            if info["groups_tried"] >= max_groups:
                return finish("group_limit")
            remaining = max_expansions - info["expansions"]
            if remaining <= 0:
                return finish("work_limit")
            result, move = _repair(
                work, ctx, group, beam_width=beam_width, alternatives=alternatives,
                halo=halo, max_region=max_region,
                max_expansions=min(group_expansions, remaining),
                max_orders=max_orders, deadline=deadline, boundary_sites=boundary_sites)
            info["groups_tried"] += 1
            for key in ("accepted", "qubits_saved", "member_growth", "expansions",
                        "tree_attempts", "beam_expansions", "beam_pruned",
                        "unreachable_contacts", "complete_proposals", "orders_tried",
                        "boundary_sites_added", "boundary_expansions"):
                info[key] += move[key]
            info["max_region_size"] = max(info["max_region_size"], move["region_size"])
            if move["accepted"]:
                work = result
                changed = True
                info["trajectory"].append({
                    "group": list(group), "qubits_saved": move["qubits_saved"],
                    "member_growth": move["member_growth"],
                    "total_qubits": sum(map(len, work.values())),
                    "expansions": info["expansions"]})
        if info['groups_tried'] >= max_groups:
            return finish('group_limit')
        if info['expansions'] >= max_expansions:
            return finish('work_limit')
        if not changed:
            return finish("no_improvement")
    return finish("pass_limit")
