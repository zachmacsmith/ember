"""Experimental B018 joint-contact primitive; not an embedding constructor.

The private state may overlap, but has connected trees and an actual physical
coupler for every source edge. Only zero-overlap states are minor embeddings.
No third-party imports, initialization, sweeps, or adaptive prices occur here.
"""
from collections import Counter, deque
from heapq import heappop, heappush
from itertools import product
from math import isfinite
from random import Random
from time import perf_counter


class _Stop(Exception):
    pass


class _Meter:
    def __init__(self, deadline, limit):
        self.deadline = deadline
        self.limit = limit
        self.work = 0
        self.stage = "setup"
        self.counts = Counter()

    def step(self):
        if perf_counter() >= self.deadline:
            raise _Stop("deadline")
        if self.work == self.limit:
            raise _Stop("work_limit")
        self.work += 1
        self.counts[self.stage] += 1

    def walk(self, values):
        for value in values:
            self.step()
            yield value


def _adjacency(raw, meter):
    if not isinstance(raw, dict):
        raise ValueError("adjacency must be an ordinary dict")
    answer = {}
    for u, ns in raw.items():
        meter.step()
        if type(u) is not int or not isinstance(ns, (tuple, list, set, frozenset)):
            raise ValueError("integer vertices and finite neighbor containers required")
        row = set()
        for v in ns:
            meter.step()
            if type(v) is not int or v == u or v in row:
                raise ValueError("simple loopless integer graph required")
            row.add(v)
        answer[u] = row
    for u, ns in answer.items():
        for v in ns:
            meter.step()
            if v not in answer or u not in answer[v]:
                raise ValueError("symmetric complete adjacency required")
    return answer


def _tree(sites, adjacency, rank, meter):
    if not sites:
        raise ValueError("empty owner chain")
    root = min(meter.walk(sites), key=rank.__getitem__)
    result = {root: set()}
    queue = deque([root])
    while queue:
        q = queue.popleft()
        meter.step()
        for p in adjacency[q]:
            meter.step()
            if p in sites and p not in result:
                result[p] = {q}
                result[q].add(p)
                queue.append(p)
    if len(result) != len(sites):
        raise ValueError("disconnected owner chain")
    return result


def _copy_tree(tree, meter):
    result = {}
    for q, ns in tree.items():
        meter.step()
        result[q] = set()
        for p in ns:
            meter.step()
            result[q].add(p)
    return result


def _trim(tree, required, rank, meter):
    """Private minimal subtree of the supplied tree spanning required sites."""
    if not required:
        return {}
    result = _copy_tree(tree, meter)
    leaves = []
    for q in result:
        meter.step()
        if len(result[q]) <= 1 and q not in required:
            heappush(leaves, (rank[q], q))
    while leaves:
        _, q = heappop(leaves)
        meter.step()
        if q not in result or q in required or len(result[q]) > 1:
            continue
        for p in result[q]:
            meter.step()
            result[p].remove(q)
            if len(result[p]) <= 1 and p not in required:
                heappush(leaves, (rank[p], p))
        del result[q]
    if not required <= result.keys():
        raise ValueError("required terminal absent from tree")
    return result


def _owners(chains, meter):
    result = {}
    for u, chain in chains.items():
        for q in chain:
            meter.step()
            result.setdefault(q, set()).add(u)
    return result


def _score(chains, meter):
    occupancy = _owners(chains, meter)
    qubits = overlap = 0
    for owners in occupancy.values():
        meter.step()
        qubits += len(owners)
        overlap += max(0, len(owners) - 1)
    return {"qubits": qubits, "overlap": overlap, "energy": qubits + overlap}


def _increment(q, own, owner, occupancy):
    if q in own:
        return 0
    others = occupancy.get(q, ())
    return 1 + int(len(others) > int(owner in others))


def _distances(tree, owner, occupancy, adjacency, rank, meter, target=None):
    if not tree:
        distance = {}
        for q in adjacency:
            meter.step()
            distance[q] = _increment(q, tree, owner, occupancy)
        return distance, {}
    distance = {}
    parent = {}
    heap = []
    for q in tree:
        meter.step()
        distance[q] = 0
        parent[q] = None
        heappush(heap, (0, rank[q], q))
    while heap:
        d, _, q = heappop(heap)
        meter.step()
        if d != distance[q]:
            continue
        if q == target:
            break
        for p in adjacency[q]:
            meter.step()
            cost = d + _increment(p, tree, owner, occupancy)
            if p not in distance or cost < distance[p]:
                distance[p] = cost
                parent[p] = q
                heappush(heap, (cost, rank[p], p))
    return distance, parent


def _attach(tree, q, owner, occupancy, adjacency, rank, meter):
    meter.step()
    if q in tree:
        return True
    if not tree:
        tree[q] = set()
        return True
    dist, parent = _distances(tree, owner, occupancy, adjacency, rank, meter, q)
    if q not in dist:
        return False
    path = []
    p = q
    while parent[p] is not None:
        meter.step()
        path.append((p, parent[p]))
        p = parent[p]
    for a, b in path:
        meter.step()
        tree.setdefault(a, set()).add(b)
        tree.setdefault(b, set()).add(a)
    return True


def _certificate(chains, witnesses, adjacency, rank, meter):
    for chain in chains.values():
        _tree(set(meter.walk(chain)), adjacency, rank, meter)
    for (u, v), (q, r) in witnesses.items():
        meter.step()
        if q not in chains[u] or r not in chains[v] or r not in adjacency[q]:
            raise ValueError("original-edge witness not preserved")


def _terminal_lists(vertices, witnesses, meter, excluded=()):
    lists = {u: [] for u in meter.walk(vertices)}
    for edge in sorted(witnesses):
        meter.step()
        if edge in excluded:
            continue
        u, v = edge
        q, r = witnesses[edge]
        lists[u].append(q)
        lists[v].append(r)
    return lists


def propose_contacts(embedding, source_adj, target_adj, witnesses, changed_edges,
                     *, deadline=None, max_work=100_000):
    """Return (atomic proposal or None, diagnostics) for the frozen B018 rule.

    A proposal contains complete ``embedding`` and ``witnesses`` mappings. It
    need not be disjoint when its input already overlaps; consult ``overlap``.
    All work/deadline interruptions discard the query, including earlier bests.
    """
    started = perf_counter()
    info = dict(status="started", accepted=False, pools=[], combinations=[],
                seed=0, price=1, max_work=max_work, started=started)
    meter = None
    best = None
    best_key = None
    current = None
    absolute = started + 5.0
    try:
        if type(max_work) is not int or not 0 <= max_work <= 100_000:
            raise ValueError("max_work must be an integer in 0..100000")
        if deadline is not None:
            if type(deadline) not in (int, float) or not isfinite(deadline):
                raise ValueError("finite absolute deadline required")
            absolute = min(absolute, deadline)
        info["deadline"] = absolute
        meter = _Meter(absolute, max_work)
        source = _adjacency(source_adj, meter)
        hardware = _adjacency(target_adj, meter)
        qorder = sorted(meter.walk(hardware))
        Random(0).shuffle(qorder)
        rank = {q: i for i, q in enumerate(meter.walk(qorder))}
        adjacency = {q: tuple(sorted(meter.walk(hardware[q]), key=rank.__getitem__)) for q in meter.walk(qorder)}
        info["physical_order"] = qorder
        vertices = sorted(meter.walk(source))
        expected = set()
        for u in vertices:
            for v in source[u]:
                meter.step()
                if u < v:
                    expected.add((u, v))
        if (not isinstance(embedding, dict) or any(type(u) is not int for u in meter.walk(embedding))
                or set(embedding) != set(source)):
            raise ValueError("exact source chain coverage required")
        old_lists = {}
        chains = {}
        for u in vertices:
            if not isinstance(embedding[u], (list, tuple)):
                raise ValueError("finite ordered chain lists required")
            old_lists[u] = []
            chains[u] = set()
            for q in embedding[u]:
                meter.step()
                if type(q) is not int or q not in hardware or q in chains[u]:
                    raise ValueError("distinct existing integer target sites required")
                old_lists[u].append(q)
                chains[u].add(q)
        if not isinstance(witnesses, dict):
            raise ValueError("ordinary witness dict required")
        for edge in witnesses:
            meter.step()
            if not isinstance(edge, tuple) or len(edge) != 2 or any(type(u) is not int for u in edge):
                raise ValueError("canonical integer witness key required")
        if set(witnesses) != expected:
            raise ValueError("exact canonical source-edge witness coverage required")
        links = {}
        for edge in sorted(witnesses):
            meter.step()
            pair = witnesses[edge]
            if not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(type(q) is not int for q in pair):
                raise ValueError("integer witness pair required")
            links[edge] = tuple(pair)
        changed = []
        if not isinstance(changed_edges, (list, tuple)) or not 1 <= len(changed_edges) <= 2:
            raise ValueError("one or two finite changed edges required")
        for edge in changed_edges:
            meter.step()
            if not isinstance(edge, (list, tuple)) or len(edge) != 2 or any(type(u) is not int for u in edge):
                raise ValueError("canonical changed edge required")
            pair = tuple(edge)
            if pair not in expected or pair in changed:
                raise ValueError("distinct existing canonical changed edges required")
            changed.append(pair)
        changed.sort()
        if len(changed) == 2 and not set(changed[0]) & set(changed[1]):
            raise ValueError("changed edges must share an owner")
        selected = sorted({u for edge in changed for u in edge})
        _certificate(chains, links, adjacency, rank, meter)
        entry_score = _score(chains, meter)
        info.update(entry=entry_score, selected=selected, changed_edges=changed)
        terms = _terminal_lists(vertices, links, meter)
        remaining = _terminal_lists(vertices, links, meter, changed)
        info["terminal_counts"] = {u: dict(Counter(meter.walk(terms[u]))) for u in meter.walk(vertices)}
        retained = {}
        for u in selected:
            retained[u] = _trim(_tree(chains[u], adjacency, rank, meter),
                                set(meter.walk(remaining[u])), rank, meter)
        info["retained"] = {u: sorted(meter.walk(retained[u]), key=rank.__getitem__) for u in selected}
        base = {u: (retained[u] if u in retained else chains[u]) for u in meter.walk(vertices)}
        occupancy = _owners(base, meter)
        meter.stage = "pools"
        region = set()
        for u in selected:
            for q in chains[u]:
                meter.step()
                region.add(q)
                for p in adjacency[q]:
                    meter.step()
                    region.add(p)
        distances = {}
        for u in selected:
            distances[u], _ = _distances(retained[u], u, occupancy, adjacency, rank, meter)
        pools = []
        for edge in changed:
            u, v = edge
            alternatives = []
            for q in sorted(region, key=rank.__getitem__):
                meter.step()
                for r in adjacency[q]:
                    meter.step()
                    if r in region and (q, r) != links[edge] and q in distances[u] and r in distances[v]:
                        alternatives.append((distances[u][q] + distances[v][r], rank[q], rank[r], q, r))
            alternatives.sort()
            pool = [links[edge]] + [(row[3], row[4]) for row in alternatives[:3]]
            pools.append(pool)
            info["pools"].append(dict(edge=edge, old=links[edge], couplers=pool,
                                      ranked_alternatives=len(alternatives)))
        meter.stage = "combinations"
        for index, combination in enumerate(product(*pools)):
            meter.step()
            current = dict(index=index, couplers=combination, complete=False, eligible=False)
            info["combinations"].append(current)
            proposed_links = {}
            for edge, pair in links.items():
                meter.step()
                proposed_links[edge] = pair
            for edge, pair in zip(changed, combination):
                meter.step()
                proposed_links[edge] = pair
            required = _terminal_lists(vertices, proposed_links, meter)
            rebuilt = {}
            for u in selected:
                tree = _copy_tree(retained[u], meter)
                present = {v: (rebuilt[v] if v in rebuilt else retained[v] if v in retained else chains[v])
                           for v in meter.walk(vertices)}
                active_owners = _owners(present, meter)
                reachable = True
                for q in required[u]:
                    if not _attach(tree, q, u, active_owners, adjacency, rank, meter):
                        reachable = False
                        break
                if not reachable:
                    break
                rebuilt[u] = _trim(tree, set(meter.walk(required[u])), rank, meter)
            if len(rebuilt) != len(selected):
                current.update(complete=True, reason="unreachable_terminal")
                continue
            candidate = {}
            candidate_lists = {}
            for u in vertices:
                candidate[u] = set()
                candidate_lists[u] = []
                sites = sorted(rebuilt[u], key=rank.__getitem__) if u in rebuilt else old_lists[u]
                for q in sites:
                    meter.step()
                    candidate[u].add(q)
                    candidate_lists[u].append(q)
            _certificate(candidate, proposed_links, adjacency, rank, meter)
            score = _score(candidate, meter)
            eligible = ((score["overlap"] == 0 and score["qubits"] < entry_score["qubits"])
                        if entry_score["overlap"] == 0 else score["energy"] < entry_score["energy"])
            key = (score["energy"], score["overlap"], score["qubits"],
                   tuple((rank[q], rank[r]) for q, r in combination))
            current.update(complete=True, eligible=eligible, score=score, embedding=candidate_lists)
            if eligible and (best_key is None or key < best_key):
                best_key = key
                best = dict(embedding=candidate_lists, witnesses=proposed_links, **score)
                info["best_combination"] = index
        info["status"] = "accepted" if best is not None else "no_improvement"
    except _Stop as exc:
        info["status"] = str(exc)
        info["interrupted_stage"] = meter.stage
        if current is not None and not current["complete"]:
            current["interruption"] = str(exc)
        best = None
    except (ValueError, TypeError, KeyError) as exc:
        info.update(status="invalid_input" if meter is None or meter.stage == "setup" else "invalid_proposal", error=str(exc))
        best = None
    ended = perf_counter()
    info.update(wall=ended - started, returned=ended, deadline=absolute,
                deadline_overrun=max(0.0, ended - absolute),
                work=meter.work if meter else 0, stage_units=dict(meter.counts) if meter else {})
    if ended >= absolute:
        info["status"] = "deadline"
        best = None
    info["accepted"] = best is not None
    return best, info
