"""Bounded contact-tree proposals prioritized by an optimistic distance bound.

The search extends one connected physical set. It uses only supplied adjacency,
contact masks, and the caller's work/deadline budget. A bounded frontier and
shortest witness selection make this a heuristic, not an exact Steiner solver.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass


_popcount = getattr(int, 'bit_count', lambda value: bin(value).count('1'))


def _bits(mask):
    while mask:
        bit = mask & -mask
        yield bit
        mask ^= bit


@dataclass(frozen=True)
class _State:
    tree: frozenset
    covered: int
    bound: int
    paths: tuple
    priority: tuple


def _prepare(tree, covered, available, masks, required, ctx, budget, size_cap,
             witnesses_per_contact, reverse, stats):
    """Bounded BFS: exact missing-contact distances and shortest witnesses."""
    stats['states_prepared'] += 1
    if not budget.check():
        return None
    missing = required & ~covered
    slack = size_cap - len(tree)
    order = sorted(tree, key=ctx.rank.__getitem__, reverse=reverse)
    queue = deque(order)
    parent = {q: None for q in tree}
    distance = {q: 0 for q in tree}
    first_distance = {}
    bit_paths = {}
    paths = set()
    last_distance = None
    truncated = False
    while queue:
        q = queue[0]
        depth = distance[q]
        if last_distance is not None and depth > last_distance:
            break
        if not budget.pop():
            return None
        queue.popleft()
        hits = masks.get(q, 0) & missing
        if hits:
            extension = None
            for bit in _bits(hits):
                if bit not in first_distance:
                    first_distance[bit] = depth
                    bit_paths[bit] = set()
                if depth != first_distance[bit] or len(bit_paths[bit]) >= witnesses_per_contact:
                    continue
                if extension is None:
                    route = []
                    node = q
                    while node not in tree:
                        route.append(node)
                        node = parent[node]
                    extension = frozenset(route)
                if extension:
                    bit_paths[bit].add(extension)
                    paths.add(extension)
            if len(first_distance) == _popcount(missing):
                last_distance = depth
        if last_distance is not None and depth >= last_distance:
            continue
        neighbors = reversed(ctx.adj[q]) if reverse else ctx.adj[q]
        for neighbor in neighbors:
            if neighbor not in available or neighbor in parent:
                continue
            if depth >= slack:
                truncated = True
                continue
            parent[neighbor] = q
            distance[neighbor] = depth + 1
            queue.append(neighbor)
    if len(first_distance) != _popcount(missing):
        stats['distance_pruned' if truncated else 'unreachable_pruned'] += 1
        return None
    bound = max(first_distance.values(), default=0)
    if len(tree) + bound > size_cap:
        stats['distance_pruned'] += 1
        return None
    ranked_paths = tuple(sorted(paths, key=lambda path: (
        len(path), tuple(sorted(ctx.rank[q] for q in path)))))
    priority = (len(tree) + bound, _popcount(missing), len(tree),
                tuple(sorted(ctx.rank[q] for q in tree)))
    return _State(tree, covered, bound, ranked_paths, priority)


def _trim(frontier, width, stats):
    """Prefer different covered masks, then fill with other ranked locations."""
    ordered = sorted(frontier, key=lambda state: state.priority)
    selected = []
    masks = set()
    for state in ordered:
        if state.covered not in masks:
            selected.append(state)
            masks.add(state.covered)
            if len(selected) == width:
                break
    if len(selected) < width:
        trees = {state.tree for state in selected}
        for state in ordered:
            if state.tree not in trees:
                selected.append(state)
                trees.add(state.tree)
                if len(selected) == width:
                    break
    stats['frontier_pruned'] += len(frontier) - len(selected)
    stats['frontier_peak'] = max(stats['frontier_peak'], len(selected))
    stats['coverage_peak'] = max(stats['coverage_peak'], len({s.covered for s in selected}))
    return sorted(selected, key=lambda state: state.priority)


def grow_contact_tree(root, available, masks, required, ctx, budget, size_cap,
                      reverse=False, *, frontier_width=4,
                      witnesses_per_contact=2, diagnostics=None):
    """Return one complete rooted contact tree, or ``None`` on failure.

    The core arguments match ``contact_repair._grow``. ``budget`` is the same
    caller-owned object: each BFS vertex processed here calls ``budget.pop()``.
    ``ctx`` needs only actual ``adj`` and stable ``rank`` mappings. Available
    nodes and masks are read-only. A completed tree found before exhaustion is
    retained; unfinished trees are never returned.

    Search priority is tree size plus the largest shortest distance to a missing
    contact set. This lower-bounds the size of any extension of that tree. The
    frontier truncation and limited shortest witnesses still sacrifice search
    completeness. Optional diagnostics accumulate counters across calls.
    """
    for name, value in (('frontier_width', frontier_width),
                        ('witnesses_per_contact', witnesses_per_contact)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f'{name} must be an integer >= 1')
    if not isinstance(required, int) or isinstance(required, bool) or required < 0:
        raise ValueError('required must be a nonnegative integer bit mask')
    if not isinstance(size_cap, int) or isinstance(size_cap, bool):
        raise ValueError('size_cap must be an integer')
    stats = diagnostics if diagnostics is not None else {}
    for key in ('states_prepared', 'states_expanded', 'completed_trees',
                'distance_pruned', 'unreachable_pruned', 'incumbent_pruned',
                'frontier_pruned', 'frontier_peak', 'coverage_peak', 'bfs_expansions'):
        stats.setdefault(key, 0)
    started_work = budget.expansions
    best = None

    def finish():
        stats['bfs_expansions'] += budget.expansions - started_work
        return best

    if root not in available or size_cap < 1 or not budget.check():
        return finish()
    tree = frozenset((root,))
    covered = masks.get(root, 0) & required
    if covered == required:
        best = tree
        stats['completed_trees'] += 1
        return finish()
    first = _prepare(tree, covered, available, masks, required, ctx, budget,
                     size_cap, witnesses_per_contact, reverse, stats)
    if first is None:
        return finish()
    stats['initial_bound'] = first.bound
    frontier = _trim([first], frontier_width, stats)
    seen = {tree}
    while frontier and budget.check():
        state = frontier.pop(0)
        if best is not None and state.priority[0] >= len(best):
            stats['incumbent_pruned'] += 1
            continue
        stats['states_expanded'] += 1
        pending = []
        for path in state.paths:
            if not budget.check():
                return finish()
            child = state.tree | path
            if child in seen or len(child) > size_cap:
                continue
            seen.add(child)
            child_covered = state.covered
            for q in path:
                child_covered |= masks.get(q, 0) & required
            if child_covered == required:
                stats['completed_trees'] += 1
                if best is None or len(child) < len(best):
                    best = child
            else:
                pending.append((child, child_covered))
        if best is not None and len(best) == first.priority[0]:
            # The rooted initial lower bound has been attained.
            return finish()
        for child, child_covered in pending:
            if not budget.check():
                return finish()
            cap = min(size_cap, len(best) - 1) if best is not None else size_cap
            if len(child) >= cap:
                stats['incumbent_pruned'] += 1
                continue
            prepared = _prepare(child, child_covered, available, masks, required,
                                ctx, budget, cap, witnesses_per_contact, reverse, stats)
            if prepared is not None:
                frontier = _trim([*frontier, prepared], frontier_width, stats)
    return finish()
