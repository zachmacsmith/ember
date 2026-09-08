"""Tiny original-graph and exhaustive-operation oracles; no constructors."""
from collections import Counter
from copy import deepcopy
from itertools import combinations, product
import importlib.util
from pathlib import Path
import sys

import pytest


PATH = (Path(__file__).resolve().parents[2] / 'packages/ember-qc/src/ember_qc/'
        'algorithms/factored/ownership_exchange.py')
SPEC = importlib.util.spec_from_file_location('isolated_ownership_exchange_author', PATH)
oe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = oe
SPEC.loader.exec_module(oe)
EVIDENCE = {}


class Budget:
    def __init__(self, limit=200000, initial=0, deadline=None, clock=None, expire_at=None):
        self.limit, self.expansions, self.deadline = limit, initial, deadline
        self.clock, self.expire_at = clock, expire_at

    def pop(self):
        if self.expansions >= self.limit:
            return False
        self.expansions += 1
        if self.clock is not None and self.expansions == self.expire_at:
            self.clock[0] = 2.
        return True


def adj(nodes, edges):
    out = {v: set() for v in nodes}
    for u, v in edges:
        out[u].add(v); out[v].add(u)
    return out


def connected(chain, target):
    chain = set(chain)
    if not chain:
        return False
    reached = {next(iter(chain))}
    while True:
        new = reached | {p for q in reached for p in target[q] if p in chain}
        if new == reached:
            return reached == chain
        reached = new


def valid(embedding, source, target):
    if set(embedding) != set(source):
        return False
    used = set()
    for chain in embedding.values():
        members = set(chain)
        if (len(members) != len(chain) or not members <= target.keys()
                or used & members or not connected(members, target)):
            return False
        used |= members
    return all(any(p in target[q] for q in embedding[u] for p in embedding[v])
               for u in source for v in source[u])


def missing(chains, source, target, selected):
    return sorted({tuple(sorted((u, v))) for u in selected for v in source[u]
                   if not any(p in target[q] for q in chains[u] for p in chains[v])})


def cycle():
    source = adj(range(6), zip(range(5), range(1, 6)))
    # q,a,l,b,c,d,r = 10,11,12,13,14,15,16.
    target = adj(range(10, 17), [(12,11),(11,10),(10,13),(13,14),
                                (14,15),(15,16),(11,15),(15,13),(14,16)])
    return {0:[12],1:[11,10],2:[13],3:[14],4:[15],5:[16]}, source, target


def remote_swap():
    target = adj(range(10, 19), [(11,10),(10,12),(12,13),(13,14),(14,15),
                                (15,16),(16,17),(17,18),(18,11)])
    source = adj(range(4), [(0,1),(0,2),(2,3)])
    return {0:[11,10],1:[12,13,14],2:[16,17,18],3:[15]},source,target


def free_escape():
    source = adj(range(3), [(0,1),(1,2)])
    target = adj(range(6), [(0,1),(1,2),(2,3),(3,4),(0,5),(5,4)])
    return {0:[0],1:[1,2,3],2:[4]},source,target


def run(fixture, groups, budget=None, **kwargs):
    entry, source, target = fixture
    original = deepcopy(fixture)
    budget = budget or Budget()
    start = budget.expansions
    result, info = oe.ownership_exchange(entry, source, target, groups,
                                         budget=budget, **kwargs)
    assert fixture == original
    assert info['work_total'] == budget.expansions-start == sum(info['work'].values())
    assert all(t >= 0 for t in info['stage_wall'].values())
    assert sum(info['stage_wall'].values()) == pytest.approx(info['wall'])
    if result is not None:
        assert valid(result, source, target)
        assert sum(map(len, result.values())) == sum(map(len, entry.values()))-1
        assert result is not entry and all(result[v] is not entry[v] for v in entry)
        assert info['candidate_returned'] and info['certificate_complete'] == 1
    else:
        assert not info['candidate_returned']
    return result, info


def state_context(fixture, group, q):
    entry, source, target = fixture
    info = dict(setup_started=0, setup_completed=0, generated_feasible=0)
    meter = oe._Meter(Budget(2000000), None)
    ctx = oe._Context(source, target, meter, info)
    ctx.setup(entry)
    chains = {v:set(entry[v])-{q} for v in group}
    patch = set().union(*(set(entry[v]) for v in group))
    state = oe._State(q, chains, patch, ctx.owners_for(chains), [], 0, [])
    state.missing = ctx.missing(state)
    seed = Counter()
    seed.update(admissions=[], generations=[])
    return ctx, state, seed


def direct_children(entry, source, target, selected, q, current):
    """Enumerate every occupied transfer/swap, not the candidate boundary walk."""
    occupied = set().union(*(set(c) for c in entry.values()))
    owners = {p:v for v,c in current.items() for p in c}
    before_owner = {p:v for v,c in entry.items() for p in c}
    chosen = missing(current, source, target, selected)[0]
    results = {}
    for a, b in (chosen, chosen[::-1]):
        if a not in selected:
            continue
        for x in sorted(occupied-{q}):
            d = owners[x]
            if d == a or not any(p in target[x] for p in current[b]):
                continue
            extended = selected | {d}
            patch = set().union(*(set(entry[v]) for v in extended))
            if len(extended)>8 or len(patch)>64 or not connected(patch, target):
                continue
            for y in [None]+sorted(current[a]):
                key = (0,x,a) if y is None else (1,min(x,y),max(x,y))
                child = {v:set(c) for v,c in current.items()}
                child[d].remove(x); child[a].add(x)
                if y is not None:
                    child[a].remove(y); child[d].add(y)
                if not connected(child[d],target) or not connected(child[a],target):
                    continue
                deficit = missing(child,source,target,extended)
                if chosen in deficit:
                    continue
                changed = sum(before_owner[p]!=v for v in extended for p in child[v])
                rank = (len(deficit), changed, *key)
                results[key] = (rank, {v:sorted(child[v]) for v in extended})
    return sorted(results.values(), key=lambda x:x[0])


def test_two_swap_cycle_full_certificate_and_sorted_seed():
    result, info = run(cycle(), [[2,1]])
    assert result == {0:[12],1:[11],2:[15],3:[13],4:[14],5:[16]}
    p = info['proposal']
    assert p['deleted'] == 10 and p['depth'] == 2
    assert [x['operation'] for x in p['trace']] == ['swap','swap']
    assert [x['admitted_owner'] for x in p['trace']] == [4,3]
    assert info['groups'][0]['normalized'] == [1,2]
    seed = info['groups'][0]['seeds'][0]
    assert seed['generations'][0]['complete_children'] == 4
    assert seed['entered'] == 3
    entry, source, target = cycle()
    EVIDENCE['cycle'] = dict(entry=entry, source={v:sorted(ns) for v,ns in source.items()},
                             target={q:sorted(ns) for q,ns in target.items()},
                             groups=[[2,1]], candidate=result, info=info)


def test_batch_once_setup_repeated_occurrences_and_uninspected_suffix():
    result, info = run(cycle(), [[0], [0], [0,4], [1,2], ['bad']])
    assert result is not None and info['setup_started'] == info['setup_completed'] == 1
    assert info['group_accesses'] == 4 and info['uninspected_groups'] == 1
    assert [r['reason'] for r in info['groups']] == [
        'seeds_exhausted','seeds_exhausted','disconnected_original_patch','candidate_returned']
    assert [r['seeds'][0]['deleted'] for r in info['groups'][:2]] == [12,12]
    _, one = run(cycle(), [[1,2]])
    assert info['stage_wall']['setup'] >= 0
    setup = {k:v for k,v in one['work'].items() if k.startswith('setup_')}
    assert setup == {k:v for k,v in info['work'].items() if k.startswith('setup_')}


def test_same_q_different_group_restarts_from_entry_and_changes_reach():
    result, info = run(remote_swap(), [[0], [0,1]])
    assert result is not None
    assert info['groups'][0]['reason'] == 'seeds_exhausted'
    assert info['proposal']['group_index'] == 1 and info['proposal']['deleted'] == 10
    first = info['groups'][0]['seeds'][0]
    second = info['groups'][1]['seeds'][0]
    assert first['deleted'] == second['deleted'] and first['entered'] >= 1
    assert second['entered'] >= 1
    assert any(a['reason']=='disconnected_original_patch' for a in first['admissions'])


def test_free_site_exclusion_and_safe_deletion_skip():
    fixture = free_escape()
    replacement = {0:[0],1:[5],2:[4]}
    assert valid(replacement, fixture[1], fixture[2])
    result, info = run(fixture, [[1],[1]])
    assert result is None and info['groups_completed'] == 2
    assert info['groups'][0]['seeds'][0]['entered'] > 0
    assert info['groups'][0]['seeds'][0]['entered'] == info['groups'][1]['seeds'][0]['entered']
    source = adj([0], [])
    target = adj([0,1], [(0,1)])
    _, info = run(({0:[0,1]}, source, target), [[0]])
    assert [s['reason'] for s in info['groups'][0]['seeds']] == ['safe_deletion']*2


def test_arbitrary_integer_labels_zero_owner_and_zero_deleted_site():
    e,s,t = cycle()
    labels = {0:-10,1:0,2:5,3:22,4:97,5:1000}
    qubits = {q:q-10 for q in t}
    fixture = ({labels[v]:[qubits[q] for q in c] for v,c in e.items()},
               {labels[v]:{labels[u] for u in ns} for v,ns in s.items()},
               {qubits[q]:{qubits[p] for p in ns} for q,ns in t.items()})
    result, info = run(fixture, [[0,5]])
    assert result is not None and info['proposal']['deleted']==0
    assert info['proposal']['trace'][0]['receiver']==5


@pytest.mark.parametrize('groups', [None, iter([[1,2]]), [()], [[1,1]], [[True]], [[999]]])
def test_malformed_encountered_groups(groups):
    result, info = run(cycle(), groups)
    assert result is None and info['stopped_reason']=='invalid_input'


def test_empty_groups_do_not_validate_entry_or_consume_setup():
    result, info = oe.ownership_exchange(None,None,None,[],budget=Budget())
    assert result is None and info['stopped_reason']=='no_groups'
    assert not info['entry_validated'] and info['setup_started']==0
    assert info['work_total']==1


@pytest.mark.parametrize('kind', ['missing_source','extra_source','unknown_target','duplicate',
                                 'disconnected','missing_edge','bool_source','bool_target'])
def test_entry_validation_trust_boundary(kind):
    e,s,t = deepcopy(cycle())
    if kind=='missing_source': del e[0]
    if kind=='extra_source': e[99]=[100];t[100]=set()
    if kind=='unknown_target': e[0]=[100]
    if kind=='duplicate': e[0]=[12,12]
    if kind=='disconnected': t[10].remove(11);t[11].remove(10)
    if kind=='missing_edge': t[12].remove(11);t[11].remove(12)
    if kind=='bool_source': s[False]=s.pop(0);e[False]=e.pop(0)
    if kind=='bool_target': e[0]=[True];t[True]=set()
    result, info = run((e,s,t), [[1,2]])
    assert result is None and info['stopped_reason']=='invalid_input'
    assert not info['entry_validated']


@pytest.mark.parametrize('value', [-1, float('inf'), float('nan'), True, 'soon'])
def test_invalid_deadlines_raise(value):
    with pytest.raises(ValueError):
        oe.ownership_exchange(*cycle(), [[1,2]], budget=Budget(), deadline=value
                              if value!=-1 else float('-inf'))


def test_all_work_prefixes_leave_entry_untouched_and_exact_cap_returns():
    _, full = run(cycle(), [[1,2]])
    cost = full['work_total']
    for allowance in range(cost):
        result, info = run(cycle(), [[1,2]], Budget(allowance))
        assert result is None and info['stopped_reason']=='work'
        assert info['work_total']==allowance
    result, exact = run(cycle(), [[1,2]], Budget(cost))
    assert result is not None and exact['budget_end']==cost
    result, shared = run(cycle(), [[1,2]], Budget(cost+23, initial=23))
    assert result is not None and shared['work_total']==cost
    EVIDENCE['work_prefixes'] = dict(all_interrupted_prefixes=cost, exact_cap=cost,
                                    shared_initial_work=23)


def test_clock_prefixes_earlier_budget_deadline_and_publication(monkeypatch):
    _, full = run(cycle(), [[1,2]])
    for cut in [1,2,17,100, full['work_total']//2, full['work_total']-1, full['work_total']]:
        clock = [0.]
        monkeypatch.setattr(oe.time, 'perf_counter', lambda:clock[0])
        result, info = run(cycle(), [[1,2]], Budget(deadline=1., clock=clock, expire_at=cut), deadline=5.)
        assert result is None and info['stopped_reason']=='deadline'
        assert info['work_total']==cut
        assert info['deadline']==1.
        if cut==full['work_total']:
            assert info['certificate_complete']==1 and info['work']['publication']==1


def test_feasible_child_during_incomplete_generation_never_publishes(monkeypatch):
    real = oe._Context._child
    marks = []
    def observed(self, *args, **kwargs):
        child = real(self, *args, **kwargs)
        if child is not None and not child.missing:
            marks.append(self.m.budget.expansions)
        return child
    monkeypatch.setattr(oe._Context, '_child', observed)
    result, full = run(remote_swap(), [[0,1]])
    assert result is not None and marks
    first = marks[0]
    result, info = run(remote_swap(), [[0,1]], Budget(first))
    assert result is None and info['generated_feasible']>=1
    assert info['certificate_complete']==0
    seed = info['groups'][0]['seeds'][0]
    assert seed['incomplete_generation'] and seed['incomplete_generated_feasible']>=1
    assert not seed['generations'][-1]['complete']


def test_final_unwinding_deadline_cannot_escape_and_reports_elapsed(monkeypatch):
    clock = [0.]
    monkeypatch.setattr(oe.time, 'perf_counter', lambda:clock[0])
    real = oe._Meter.finish
    def expire_after_finalization(self):
        info = real(self)
        clock[0] = 2.
        return info
    monkeypatch.setattr(oe._Meter, 'finish', expire_after_finalization)
    result, info = run(cycle(), [[1,2]], deadline=1.)
    assert result is None and info['certificate_complete']==1
    assert info['stopped_stage']=='final_return'
    assert info['wall']==2. and info['deadline_overrun']==1.


def test_interrupted_group_normalization_never_accesses_suffix():
    _, reference = run(cycle(), [[1,2]])
    # Header and setup precede group work. Stop on the first group access,
    # before a malformed suffix could be visited or interpreted.
    first_group_work = reference['groups'][0]['work_start']
    result, info = run(cycle(), [[1,2], ['bad']], Budget(first_group_work+1))
    assert result is None and info['stopped_reason']=='work'
    assert info['group_accesses']==1 and info['uninspected_groups']==1
    assert not info['groups'][0]['inspected']


def test_independent_complete_generation_oracle():
    fixtures = [(cycle(), [1,2], 10), (remote_swap(), [0,1], 10)]
    edges = list(combinations(range(4),2))
    entry = {0:[0,1],1:[2],2:[3]}
    source = adj(range(3), [(0,1),(1,2)])
    for mask in product((0,1), repeat=len(edges)):
        target = adj(range(4), [e for e,b in zip(edges,mask) if b])
        if valid(entry,source,target):
            fixtures.append(((entry,source,target), [0,1,2], 0))
    compared = 0
    for fixture, group, q in fixtures:
        e,s,t = fixture
        current = {v:set(c)-{q} for v,c in e.items()}
        if not missing(current,s,t,group):
            continue
        ctx, state, seed = state_context(fixture,group,q)
        before = deepcopy(state)
        children = ctx.generate(state,seed)
        expected = direct_children(e,s,t,set(group),q,current)
        actual = [(c.rank,{v:sorted(chain) for v,chain in c.chains.items()}) for c in children]
        assert actual == expected[:4]
        assert seed['generations'][0]['complete_children']==len(expected)
        assert state==before and all(q not in c.owners for c in children)
        compared += 1
    # This predeclared path-source domain has four qualifying tiny targets,
    # plus the two larger fixed witnesses. Coverage is exact, not a quota.
    assert compared == 6
    EVIDENCE['generation_oracle'] = dict(complete_generations_compared=compared,
                                        entry_valid_fixtures=len(fixtures))


def test_admission_whole_chain_and_caps_are_inclusive():
    e,s,t = cycle()
    # One extra selected isolate holds a long connected chain; no logical
    # obligations are invented by its physical adjacency to the existing patch.
    extra = list(range(100,160))
    e[8]=extra;s[8]=set()
    for q in extra:t[q]=set()
    t[11].add(extra[0]);t[extra[0]].add(11)
    for a,b in zip(extra,extra[1:]):t[a].add(b);t[b].add(a)
    ctx,state,seed = state_context((e,s,t),[1,2,8],10)
    assert len(state.patch)==63
    children = ctx.generate(state,seed)
    assert any(len(c.patch)==64 for c in children)
    assert all(len(c.patch)<=64 for c in children)
    # A three-site donor cannot be admitted by taking only its contacting end.
    e[4] += [200,201];t[200]={15,201};t[201]={200};t[15].add(200)
    ctx,state,seed = state_context((e,s,t),[1,2,8],10)
    ctx.generate(state,seed)
    assert any(a['owner']==4 and a['added_sites']==3 and a['reason']=='site_cap'
               for a in seed['admissions'])
    assert all(4 not in c.chains for c in ctx.generate(state,Counter(admissions=[],generations=[])))


def test_chain_cap_rejects_ninth_owner_without_partial_admission():
    e,s,t = cycle()
    extras = list(range(20,26))
    for v in extras:
        e[v]=[100+v];s[v]=set();t[100+v]={11};t[11].add(100+v)
    ctx,state,seed = state_context((e,s,t),[1,2]+extras,10)
    before = deepcopy(state)
    ctx.generate(state,seed)
    assert len(state.chains)==8 and state==before
    assert seed['admissions'] and all(a['reason']=='chain_cap' for a in seed['admissions'])


def test_every_generation_prefix_preserves_parent_and_whole_admission():
    ctx,state,seed = state_context(cycle(),[1,2],10)
    start = ctx.m.budget.expansions
    ctx.generate(state,seed)
    complete_cost = ctx.m.budget.expansions-start
    staged_interruptions = 0
    for allowance in range(complete_cost):
        ctx,state,seed = state_context(cycle(),[1,2],10)
        parent, entry, owners = deepcopy(state), deepcopy(ctx.entry), deepcopy(ctx.owner)
        ctx.m.budget.limit = ctx.m.budget.expansions+allowance
        with pytest.raises(oe._Stop):
            ctx.generate(state,seed)
        assert state==parent and ctx.entry==entry and ctx.owner==owners
        staged_interruptions += any(a['staged'] for a in seed['admissions'])
        assert not seed['generations'] or not seed['generations'][-1]['complete']
    assert staged_interruptions>0
    EVIDENCE['generation_prefixes'] = dict(interrupted_prefixes=complete_cost,
                                          prefixes_with_staged_admissions=staged_interruptions)


def test_exact_signature_dominance_keeps_selected_set_and_smaller_depth():
    ctx,state,_ = state_context(cycle(),[1,2],10)
    signature = ctx.signature(state)
    visited = oe._Visited(ctx.m)
    assert visited.admit(signature,3)==(True,False)
    assert visited.admit(signature,3)==(False,False)
    assert visited.admit(signature,4)==(False,False)
    assert visited.admit(signature,2)==(True,True)
    extended = deepcopy(state)
    extended.chains[4]={15};extended.patch.add(15);extended.owners[15]=4
    assert visited.admit(ctx.signature(extended),3)==(True,False)


def test_signature_hash_collision_requires_exact_equality(monkeypatch):
    monkeypatch.setattr(oe, 'hash', lambda _:0, raising=False)
    meter = oe._Meter(Budget(), None)
    visited = oe._Visited(meter)
    assert visited.admit([2,0,1,2,10,0,11,1],3)==(True,False)
    assert visited.admit([2,0,1,2,10,1,11,0],3)==(True,False)
    assert visited.admit([2,0,1,2,10,0,11,1],2)==(True,True)
    assert meter.work['signature_equality_tokens']>0


def test_full_certificate_rejects_false_incremental_missing_set():
    ctx,state,seed = state_context(cycle(),[1,2],10)
    state.missing=[]
    with pytest.raises(oe._Internal, match='missing source contact'):
        ctx.certificate(state,0,seed)


def test_dependency_surface_is_standard_library_only():
    import ast
    tree = ast.parse(PATH.read_text())
    imports = {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    imports |= {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
    assert imports <= {'__future__','collections','contextlib','dataclasses','math','time'}
