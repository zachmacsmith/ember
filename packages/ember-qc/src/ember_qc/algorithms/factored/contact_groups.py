"""Bounded group coverage for one evolving contact-reconstruction state.

Groups use only current chain sizes, logical neighbors, and physically adjacent
occupied chains. Neighbor windows broaden coverage without enumerating all
subsets. This module neither constructs embeddings nor evaluates graph families.
"""


def round_robin_groups(embedding, ctx, group_sizes, limit):
    """Return at most ``limit`` distinct groups from a valid incumbent.

    ``ctx`` supplies ``nodes``, ``src_adj``, ``adj``, and ``lower_bound(v)`` as
    in the contact-reconstruction context. Callers validate the incumbent and
    group sizes (1 through 4). The embedding and context are never modified.

    Enabled singletons are emitted first. At each subsequent neighbor depth,
    every eligible center is visited for one configured size before the next
    size. A size-k group contains its center and the contiguous k-1 neighboring
    entries starting at that depth; windows do not wrap. Configured size order
    is preserved, except that singletons always precede larger groups.

    Group sets are deduplicated, and groups with no positive total excess over
    the individual degree bounds are omitted. A returned group is an opportunity
    to search, not a claim that its chains can be shortened.
    """
    if limit <= 0:
        return []

    sizes = tuple(dict.fromkeys(group_sizes))
    rank = {v: i for i, v in enumerate(ctx.nodes)}
    excess = {v: len(embedding[v]) - ctx.lower_bound(v) for v in ctx.nodes}

    def priority(v):
        return -excess[v], -len(embedding[v]), rank[v]

    centers = sorted(ctx.nodes, key=priority)
    seen = set()
    groups = []

    def offer(group):
        key = frozenset(group)
        if key in seen or sum(excess[v] for v in group) <= 0:
            return False
        seen.add(key)
        groups.append(group)
        return len(groups) >= limit

    if 1 in sizes:
        for v in centers:
            if offer((v,)):
                return groups

    larger_sizes = tuple(size for size in sizes if size >= 2)
    if not larger_sizes or not any(value > 0 for value in excess.values()):
        return groups

    owner = {q: v for v, chain in embedding.items() for q in chain}
    neighbors = {}
    for v in centers:
        adjacent = set(ctx.src_adj[v])
        adjacent.update(owner[q] for p in embedding[v] for q in ctx.adj[p]
                        if q in owner and owner[q] != v)
        adjacent.discard(v)
        neighbors[v] = sorted(adjacent, key=priority)

    minimum_width = min(larger_sizes) - 1
    active = [v for v in centers if len(neighbors[v]) >= minimum_width]
    depth = 0
    while active:
        for size in larger_sizes:
            width = size - 1
            for v in active:
                if depth + width <= len(neighbors[v]):
                    group = (v, *neighbors[v][depth:depth + width])
                    if offer(group):
                        return groups
        depth += 1
        active = [v for v in active
                  if len(neighbors[v]) >= depth + minimum_width]
    return groups
