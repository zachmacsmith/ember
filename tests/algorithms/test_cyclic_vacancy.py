"""Current-seed continuation checks, without constructors or corpus trials."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import networkx as nx
import pytest

from ember_qc.algorithms.factored import native, vacancy_repair as vr


ROOT=Path(__file__).resolve().parents[2]
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
fixtures=load(Path(__file__).with_name('test_deletion_closure_integration.py'),'_cyclic_fixtures')


@pytest.mark.parametrize('cursor,expected', [
    (None,[(20,2),(20,5),(10,1),(10,4)]),
    ((20,3),[(20,5),(10,1),(10,4),(20,2)]),  # disappeared cursor
    ((20,5),[(10,1),(10,4),(20,2),(20,5)]),
    ((10,100),[(20,2),(20,5),(10,1),(10,4)]),  # wrap from beyond last site
    ((30,9),[(20,2),(20,5),(10,1),(10,4)]),  # cursor owner now singleton
])
def test_complete_current_seed_set_rotates_once(cursor,expected):
    entry={10:frozenset([1,4]),20:frozenset([2,5]),30:frozenset([9])}
    before=deepcopy(entry)
    batches,info=vr._cyclic_seed_batches(entry,(20,10,30),cursor,lambda:None)
    flat=[(v,q) for v,sites in batches for q in sites]
    assert flat==expected==info['seed_schedule']
    assert len(set(flat))==len(flat)==info['seed_count']==4
    assert info['seed_schedule_complete'] and entry==before


def test_new_sites_are_enumerated_and_large_or_singleton_chains_are_ineligible():
    entry={20:frozenset([2,3,5]),10:frozenset([1,4]),30:frozenset(range(100,165)),40:frozenset([90])}
    batches,info=vr._cyclic_seed_batches(entry,(20,10,30,40),(20,2),lambda:None)
    assert info['seed_schedule']==[(20,3),(20,5),(10,1),(10,4),(20,2)]
    assert {v for v,sites in batches}=={10,20}


def test_schedule_interruption_has_no_partial_publication_or_mutation():
    entry={0:frozenset([10,11,12]),1:frozenset([20,21])};before=deepcopy(entry)
    calls=[]
    def check():
        calls.append(1)
        if len(calls)==7: raise vr._Stop('deadline')
    with pytest.raises(vr._Stop,match='deadline'):
        vr._cyclic_seed_batches(entry,(0,1),None,check)
    assert entry==before and len(calls)==7


def witness():
    source=nx.Graph([(0,1),(0,2),(3,4),(3,5)])
    target=nx.Graph([(10,11),(10,12),(11,13),(12,14),(13,14),
                     (20,21),(20,22),(21,23),(22,24),(23,24),(14,24)])
    entry={0:[11,10],1:[12],2:[13],3:[21,20],4:[22],5:[23]}
    return source,target,entry


def stage(source,target,entry,**options):
    info={}
    result,error=native._bounded_vacancy_refinement(
        entry,source,target,{v:set(source[v]) for v in source},{q:set(target[q]) for q in target},
        started=95.,deadline=160.,cleanup_info={'status':'completed'},info=info,policy='cyclic',**options)
    return result,error,info


def test_real_two_contractions_and_all_intermediate_minors(monkeypatch):
    monkeypatch.setattr(native.time,'perf_counter',fixtures.Clock())
    source,target,entry=witness();before=deepcopy(entry)
    # Neither center admits any initial safe single deletion.
    for v in (0,3):
        for q in entry[v]:
            trial=deepcopy(entry);trial[v].remove(q)
            assert not native.is_valid_embedding(trial,source,target)
    actual=vr.vacancy_repair;inputs=[];outputs=[]
    def query(current,*args,**kwargs):
        inputs.append(deepcopy(current));out,info=actual(current,*args,**kwargs)
        if out is not None: fixtures.verify(out,source,target);outputs.append(deepcopy(out))
        assert current==inputs[-1]
        return out,info
    monkeypatch.setattr(vr,'vacancy_repair',query)
    result,error,info=stage(source,target,entry)
    assert error is None and entry==before
    assert result=={0:[14],1:[12],2:[13],3:[24],4:[22],5:[23]}
    assert info['accepted']==info['qubits_saved']==2 and info['query_calls']==3
    assert info['owner_priority']==(0,3,1,2,4,5) and info['cursor']==(3,20)
    assert [c['cursor_before'] for c in info['calls']]==[None,(0,10),(3,20)]
    assert [c['cursor_after'] for c in info['calls']]==[(0,10),(3,20),(3,20)]
    assert inputs[1:]==outputs
    assert info['calls'][1]['core']['seed_schedule']==[(3,20),(3,21)]
    assert info['calls'][2]['core']['seed_schedule']==[] and info['reason']=='seeds_exhausted'
    assert info['proposals_used']==sum(c['budget_end']-c['budget_start'] for c in info['calls'])


def test_late_second_gate_keeps_first_cursor_and_valid_incumbent(monkeypatch):
    clock=fixtures.Clock();monkeypatch.setattr(native.time,'perf_counter',clock)
    source,target,entry=witness();validator=native.is_valid_embedding;checked=[]
    def validate(*args):
        result=validator(*args);checked.append(1)
        if len(checked)==2: clock.value=101.
        return result
    monkeypatch.setattr(native,'is_valid_embedding',validate)
    result,error,info=stage(source,target,entry)
    fixtures.verify(result,source,target)
    assert error is None and info['accepted']==1 and info['cursor']==(0,10)
    assert info['calls'][1]['cursor_after']==(0,10)
    assert info['calls'][1]['core']['proposal']['seed_owner']==3
    assert not info['calls'][1]['committed'] and info['calls'][1]['commit_rejection']=='deadline'


def test_frozen_priority_and_live_budget_survive_changed_lengths(monkeypatch):
    monkeypatch.setattr(native.time,'perf_counter',fixtures.Clock())
    source=nx.Graph([(10,0)]);target=nx.path_graph(5);entry={10:[0,1,2],0:[3,4]};seen=[]
    def query(current,*args,budget,deadline,owner_priority,cursor):
        seen.append((owner_priority,cursor,id(budget),deadline))
        if len(seen)==1:
            for _ in range(49999): assert budget.pop()
            return {10:[1,2],0:[3,4]},dict(candidate_returned=True,certificate_complete=1,
                       error=None,stopped_reason='candidate_returned',proposal={'seed_owner':10,'deleted':0})
        assert budget.pop() and not budget.pop()
        return None,dict(error=None,stopped_reason='work')
    monkeypatch.setattr(vr,'vacancy_repair',query)
    result,error,info=stage(source,target,entry)
    assert error is None and result=={10:[1,2],0:[3,4]}
    assert [x[:2] for x in seen]==[((10,0),None),((10,0),(10,0))]
    assert len({x[2] for x in seen})==1 and {x[3] for x in seen}=={101.}
    assert info['proposals_used']==50000 and info['reason']=='work' and info['accepted']==1


def test_default_core_matches_frozen_047_output_and_all_non_time_fields(monkeypatch):
    old=load(ROOT/'results/codex/cyclic-vacancy-checks/reference/vacancy_repair.py','_047_original_vacancy')
    monkeypatch.setattr(native.time,'perf_counter',fixtures.Clock())
    source,target,entry=witness()
    for budget_limit in (1,50000):
        results=[]
        for module in (old,vr):
            budget=native._VacancyBudget(160.);budget.limit=budget_limit
            results.append(module.vacancy_repair(entry,{v:set(source[v]) for v in source},
                {q:set(target[q]) for q in target},(),budget=budget,deadline=160.))
        assert results[0]==results[1]


def test_native_bounded_replay_and_cyclic_policy_wiring(monkeypatch):
    old=load(ROOT/'results/codex/cyclic-vacancy-checks/reference/native.py','_047_original_native')
    source,target,_,_,_=fixtures.pipeline(monkeypatch,old)
    expected=old.native_embed(source,target,**fixtures.OPTIONS,vacancy_refinement='bounded')
    source,target,_,_,_=fixtures.pipeline(monkeypatch)
    assert native.native_embed(source,target,**fixtures.OPTIONS,vacancy_refinement='bounded')==expected
    source,target,_,clock,_=fixtures.pipeline(monkeypatch)
    closing=native._final_deletion_cleanup
    def close(*args,**kwargs):
        result=closing(*args,**kwargs);clock.value+=1.;return result
    monkeypatch.setattr(native,'_final_deletion_cleanup',close)
    result=native.native_embed(source,target,**fixtures.OPTIONS,vacancy_refinement='cyclic')
    fixtures.verify(result['embedding'],source,target)
    assert result['status']=='SUCCESS' and result['diag']['vacancy_refinement_policy']=='cyclic'
    assert result['diag']['vacancy_refinement']['owner_priority']==(0,1,2)
    bad=native.native_embed(source,target,vacancy_refinement='cyclic')
    assert bad['status']=='ERROR' and 'deletion' in bad['error']


def test_pilot_cyclic_config_changes_exactly_one_policy():
    pilot=load(ROOT/'scripts/codex/pilot.py','_048_pilot_config')
    base=pilot.CONFIGS['native-search-joint1-contacts-spectral-vacancy']
    cyclic=pilot.CONFIGS['native-search-joint1-contacts-spectral-vacancy-cyclic']
    assert cyclic==dict(base,vacancy_refinement='cyclic') and cyclic is not base
