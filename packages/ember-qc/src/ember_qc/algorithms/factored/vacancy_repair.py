"""Exploratory contact-directed free-site relocation from one valid minor.

No constructor or external embedding library is imported. The caller owns the
final independent validation and the common deadline. Inputs use integer labels.
"""
import time

DEPTH = 8
BEAM = 16
PER_SEED = 256
OWNERS = 8
SITES = 64


class _Stop(Exception):
    def __init__(self, reason):
        self.reason = reason


def vacancy_repair(embedding, source, target, _seed_groups, *, budget, deadline=None):
    """Return at most one private Q-minus-one proposal and complete accounting.

    The supplied group vector is retained by the diagnostic caller for its
    ordinary control. This method searches all eligible deletion seeds instead.
    Budget units count attempted relocation proposals, not adjacency scans.
    """
    started = time.perf_counter()
    deadlines = [x for x in (deadline, getattr(budget, 'deadline', None)) if x is not None]
    deadline = min(deadlines) if deadlines else float('inf')
    initial = budget.expansions
    info = dict(algorithm='contact_directed_vacancy', stopped_reason=None, error=None,
                proposal=None, seed_attempts=0, seeds=[], candidate_returned=False,
                generated_feasible=0, certificate_complete=0, entry_validated=False,
                work_unit='attempted relocation proposal', limits=dict(depth=DEPTH,
                    beam=BEAM, proposals_per_seed=PER_SEED, owners=OWNERS, original_sites=SITES),
                seed_order=[], groups_inspected=0, setup_completed=False)
    answer = None

    def check():
        if time.perf_counter() >= deadline:
            raise _Stop('deadline')

    def connected(chain):
        if not chain:
            return False
        todo = [next(iter(chain))]
        seen = set(todo)
        while todo:
            check()
            for q in target[todo.pop()]:
                if q in chain and q not in seen:
                    seen.add(q)
                    if len(seen) == len(chain):
                        return True
                    todo.append(q)
        return len(seen) == len(chain)

    def contacts(v, chain, owner):
        seen = set()
        for q in chain:
            check()
            for p in target[q]:
                w = owner.get(p)
                if w in source[v]:
                    seen.add(w)
        return seen

    def missing_for(v, chain, owner):
        present = contacts(v, chain, owner)
        return {(min(v, w), max(v, w)) for w in source[v] if w not in present}

    def certify(chains, owner, changed, trace, seed, removed):
        nonlocal answer
        check()
        if set(chains) != set(source) or sum(map(len, chains.values())) != entry_q-1:
            raise ValueError('proposal coverage or cardinality')
        rebuilt = {}
        for v, chain in chains.items():
            check()
            if not connected(chain):
                raise ValueError('proposal disconnected chain')
            for q in chain:
                if q not in target or q in rebuilt:
                    raise ValueError('proposal membership or overlap')
                rebuilt[q] = v
        if owner != rebuilt:
            raise ValueError('proposal ownership bookkeeping')
        for v, chain in chains.items():
            if missing_for(v, chain, rebuilt):
                raise ValueError('proposal missing original contact')
        candidate = {v: sorted(chain) if v in changed else list(embedding[v])
                     for v, chain in chains.items()}
        check()
        info['proposal'] = dict(selected=sorted(changed), deleted=removed,
                                seed_owner=seed, depth=len(trace), trace=trace,
                                q_before=entry_q, q_after=entry_q-1)
        info['certificate_complete'] += 1
        answer = candidate

    try:
        check()
        if set(embedding) != set(source):
            raise ValueError('entry source coverage')
        entry = {v: frozenset(chain) for v, chain in embedding.items()}
        owner0 = {}
        for v, chain in entry.items():
            check()
            if len(chain) != len(embedding[v]) or not connected(chain):
                raise ValueError('entry duplicate or disconnected chain')
            for q in chain:
                if q not in target or q in owner0:
                    raise ValueError('entry overlap or missing site')
                owner0[q] = v
        for v, chain in entry.items():
            if missing_for(v, chain, owner0):
                raise ValueError('entry missing original contact')
        entry_q = sum(map(len, entry.values()))
        info.update(entry_validated=True, setup_completed=True, q_before=entry_q)
        order = sorted((v for v in entry if 1 < len(entry[v]) <= SITES),
                       key=lambda v: (-len(entry[v]), -len(source[v]), v))
        info['seed_order'] = order
        for v in order:
            for removed in sorted(entry[v]):
                check()
                row = dict(owner=v, removed=removed, proposals=0, entered=0,
                           reason=None, depth_peak=0)
                info['seeds'].append(row)
                info['seed_attempts'] += 1
                remainder = entry[v]-{removed}
                if not connected(remainder):
                    row['reason'] = 'disconnected_remainder'
                    continue
                chains = dict(entry); chains[v] = remainder
                owner = dict(owner0); del owner[removed]
                missing = missing_for(v, remainder, owner)
                if not missing:
                    info['generated_feasible'] += 1
                    certify(chains, owner, {v}, [], v, removed)
                    row['reason'] = 'candidate_returned'
                    break
                # (chains, ownership, missing edges, changed owners, trace)
                beam = [(chains, owner, missing, frozenset([v]), [])]
                visited = set()
                capped = False
                for depth in range(DEPTH):
                    children = []
                    for chains, owner, missing, changed, trace in beam:
                        check()
                        row['entered'] += 1
                        edge = min(missing)
                        for a, b in (edge, edge[::-1]):
                            selected = changed | {a}
                            if len(selected) > OWNERS or sum(len(entry[w]) for w in selected) > SITES:
                                continue
                            free = set()
                            for site in chains[b]:
                                check()
                                free.update(q for q in target[site] if q not in owner)
                            for q in sorted(free):
                                for p in sorted(chains[a]):
                                    check()
                                    if row['proposals'] >= PER_SEED:
                                        capped = True
                                        break
                                    if not budget.pop():
                                        raise _Stop('work')
                                    row['proposals'] += 1
                                    replacement = (chains[a]-{p}) | {q}
                                    if not connected(replacement):
                                        continue
                                    new_owner = dict(owner); del new_owner[p]; new_owner[q] = a
                                    new_missing = {e for e in missing if a not in e}
                                    new_missing.update(missing_for(a, replacement, new_owner))
                                    if edge in new_missing:
                                        continue
                                    new_chains = dict(chains); new_chains[a] = frozenset(replacement)
                                    new_trace = trace + [(a, p, q)]
                                    row['depth_peak'] = max(row['depth_peak'], len(new_trace))
                                    if not new_missing:
                                        info['generated_feasible'] += 1
                                        certify(new_chains, new_owner, selected, new_trace, v, removed)
                                        row['reason'] = 'candidate_returned'
                                        break
                                    key = tuple((w, tuple(sorted(new_chains[w]))) for w in sorted(selected))
                                    if key in visited:
                                        continue
                                    visited.add(key)
                                    changed_sites = sum(len(new_chains[w] ^ entry[w]) for w in selected)
                                    rank = (len(new_missing), len(selected), changed_sites, tuple(new_trace))
                                    children.append((rank, (new_chains, new_owner, new_missing, selected, new_trace)))
                                if answer is not None or capped:
                                    break
                            if answer is not None or capped:
                                break
                        if answer is not None or capped:
                            break
                    if answer is not None or capped or not children:
                        break
                    check()
                    children.sort(key=lambda x: x[0])
                    beam = [state for _, state in children[:BEAM]]
                if answer is not None:
                    break
                row['reason'] = 'seed_proposal_cap' if capped else 'bounded_search_exhausted'
            if answer is not None:
                break
        info['stopped_reason'] = 'candidate_returned' if answer is not None else 'seeds_exhausted'
    except _Stop as exc:
        info['stopped_reason'] = exc.reason
        if info['seeds'] and info['seeds'][-1]['reason'] is None:
            info['seeds'][-1]['reason'] = exc.reason
    except Exception as exc:
        answer = None
        info.update(stopped_reason='invalid_input' if not info['entry_validated'] else 'internal_error',
                    error=repr(exc))
    used = budget.expansions-initial
    info.update(candidate_returned=answer is not None, work_total=used,
                work={'relocation_proposals': used}, budget_start=initial,
                budget_end=budget.expansions)
    ended = time.perf_counter()
    info.update(wall=ended-started, deadline_overrun=max(0., ended-deadline))
    if ended >= deadline:
        answer = None
        info.update(stopped_reason='deadline', candidate_returned=False)
    return answer, info
