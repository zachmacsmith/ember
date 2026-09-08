"""Independent tiny whole-minor oracles for the isolated deletion closure."""
from copy import deepcopy
import json
from pathlib import Path
import random
import subprocess
import sys

import pytest

from ember_qc.algorithms.factored import deletion_closure as dc
from ember_qc.algorithms.factored.polish import spur_prune


def adjacency(nodes, edges):
    result = {v:set() for v in nodes}
    for a,b in edges:
        result[a].add(b); result[b].add(a)
    return result


def valid(chains, source, target):
    if set(chains) != set(source):
        return False
    used = set()
    for chain in chains.values():
        members = set(chain)
        if not members or len(members) != len(chain) or used & members or not members <= target.keys():
            return False
        seen = {chain[0]}
        while True:
            enlarged = seen | {p for q in seen for p in target[q] if p in members}
            if enlarged == seen:
                break
            seen = enlarged
        if seen != members:
            return False
        used.update(members)
    return all(any(p in target[q] for q in chains[v] for p in chains[u])
               for v in source for u in source[v])


def reference(chains, source, target, reverse=False):
    """Legacy round order, but certify each trial by the whole-graph oracle."""
    work = deepcopy(chains)
    records, round_number = [], 0
    while True:
        round_number += 1
        changes = False
        for v in sorted(work, reverse=reverse):
            for q in sorted(work[v]):
                proposal = deepcopy(work)
                proposal[v].remove(q)
                if valid(proposal,source,target):
                    work = proposal
                    records.append((round_number,v,q))
                    changes = True
        if not changes:
            return work, records


def sequence(info):
    return [(r['round'],r['source_vertex'],r['qubit']) for r in info['accepted_sequence']]


def articulation_fixture():
    source = adjacency([0,1],[(0,1)])
    target = adjacency([0,1,2,3],[(0,1),(0,2),(2,3)])
    return {0:[0,1,2],1:[3]},source,target


def random_fixture(seed):
    rng = random.Random(seed)
    vertices = [-9, 0, 4, 18, 101][:1+seed%5]
    source = adjacency(vertices,[(u,v) for i,u in enumerate(vertices)
        for v in vertices[i+1:] if rng.random()<.6])
    chains, next_q = {}, -30
    for v in reversed(vertices):
        chains[v] = list(range(next_q,next_q+1+rng.randrange(4)))
        next_q += len(chains[v])+1
        rng.shuffle(chains[v])
    target = adjacency(range(-30,next_q+2),[])
    for chain in chains.values():
        for a,b in zip(chain,chain[1:]):
            target[a].add(b); target[b].add(a)
    for u in source:
        for v in source[u]:
            a,b = rng.choice(chains[u]),rng.choice(chains[v])
            target[a].add(b);target[b].add(a)
    nodes=list(target)
    for i,a in enumerate(nodes):
        for b in nodes[i+1:]:
            if rng.random()<.1:
                target[a].add(b);target[b].add(a)
    assert valid(chains,source,target)
    return chains,source,target


@pytest.mark.parametrize('seed',range(40))
def test_nonbinding_output_and_sequence_match_legacy_and_whole_minor_oracle(seed):
    chains,source,target=random_fixture(seed)
    before=deepcopy((chains,source,target))
    expected,trace=reference(chains,source,target)
    old=spur_prune(chains,{v:sorted(nbrs) for v,nbrs in source.items()},target)
    result,info=dc.deletion_closure(chains,source,target)
    assert result==old==expected and sequence(info)==trace
    assert valid(result,source,target) and info['closure_complete'] and info['input_validated']
    assert info['accepted_deletions']==len(trace)==sum(map(len,chains.values()))-sum(map(len,result.values()))
    assert all(not valid({**result,v:[p for p in chain if p!=q]},source,target)
               for v,chain in result.items() for q in chain)
    assert (chains,source,target)==before and result is not chains
    assert all(result[v] is not chains[v] for v in chains)
    assert sum(info['phase_wall'].values())==pytest.approx(info['wall'])


def test_interfering_cross_chain_deletions_depend_on_order():
    source=adjacency([0,1],[(0,1)])
    target=adjacency(range(4),[(0,1),(2,3),(0,3),(1,2)])
    chains={0:[0,1],1:[2,3]}
    forward,trace=reference(chains,source,target)
    backwards,_=reference(chains,source,target,reverse=True)
    assert forward != backwards
    result,info=dc.deletion_closure(chains,source,target)
    assert result==forward=={0:[1],1:[2]} and sequence(info)==trace
    assert valid(result,source,target)


def test_earlier_articulation_revisited_only_after_self_deletion():
    chains,source,target=articulation_fixture()
    result,info=dc.deletion_closure(chains,source,target)
    assert sequence(info)==[(1,0,1),(2,0,0)]
    assert result=={0:[2],1:[3]}
    assert info['work']['unchanged_chain_sweeps_skipped']>=1
    assert info['rounds_started']==info['rounds_completed']==3


class Clock:
    value=0.
    def __call__(self):
        return self.value


@pytest.mark.parametrize('stage',['copy','copy_complete','source_setup','source_order',
    'initial_connectivity','initial_contacts','remainder','connectivity','contacts',
    'replacement','commit_record','commit','round_end','complete'])
def test_expiry_at_each_work_stage_returns_complete_valid_prefix(monkeypatch,stage):
    chains,source,target=articulation_fixture()
    before=deepcopy(chains)
    _,trace=reference(chains,source,target)
    clock=Clock()
    original=dc._Meter.checkpoint
    def expire(self,current):
        if current==stage:
            clock.value=1.
        return original(self,current)
    monkeypatch.setattr(dc.time,'perf_counter',clock)
    monkeypatch.setattr(dc._Meter,'checkpoint',expire)
    result,info=dc.deletion_closure(chains,source,target,deadline=1.)
    assert info['stopped_reason']=='deadline' and info['stopped_stage']==stage
    assert not info['closure_complete'] and valid(result,source,target) and chains==before
    assert sequence(info)==trace[:info['accepted_deletions']]
    assert info['returned_input_alias']==(result is chains)
    if stage in ('copy','copy_complete'):
        assert result is chains and not info['private_copy_complete'] and not info['input_validated']
    else:
        assert result is not chains and info['private_copy_complete']
    if stage=='commit':
        assert info['accepted_deletions']==0 and result==chains


def test_later_commit_deadline_retains_earlier_certified_deletion(monkeypatch):
    chains,source,target=articulation_fixture()
    clock=Clock();original=dc._Meter.checkpoint
    commits=0
    def expire(self,stage):
        nonlocal commits
        if stage=='commit':
            commits+=1
            if commits==2:clock.value=1.
        return original(self,stage)
    monkeypatch.setattr(dc.time,'perf_counter',clock)
    monkeypatch.setattr(dc._Meter,'checkpoint',expire)
    result,info=dc.deletion_closure(chains,source,target,deadline=1.)
    assert sequence(info)==[(1,0,1)] and result=={0:[0,2],1:[3]}
    assert valid(result,source,target) and info['stopped_stage']=='commit'


def test_every_clock_prefix_preserves_a_complete_valid_mapping(monkeypatch):
    chains,source,target=articulation_fixture()
    before=deepcopy(chains)
    expected,trace=reference(chains,source,target)
    class PrefixClock:
        def __init__(self,cutoff):self.calls,self.cutoff=0,cutoff
        def __call__(self):
            self.calls+=1
            return 1. if self.calls>=self.cutoff else 0.
    unlimited=PrefixClock(100000)
    monkeypatch.setattr(dc.time,'perf_counter',unlimited)
    result,info=dc.deletion_closure(chains,source,target,deadline=1.)
    assert result==expected and info['closure_complete']
    cases=unlimited.calls+1
    saw_partial_copy=False
    for cutoff in range(1,cases+1):
        clock=PrefixClock(cutoff)
        monkeypatch.setattr(dc.time,'perf_counter',clock)
        result,info=dc.deletion_closure(chains,source,target,deadline=1.)
        assert set(result)==set(chains) and valid(result,source,target) and chains==before
        assert sequence(info)==trace[:info['accepted_deletions']]
        assert sum(info['phase_wall'].values())==pytest.approx(info['wall'])
        if 0<info['work'].get('copy_qubits',0)<sum(map(len,chains.values())):
            saw_partial_copy=True
            assert result is chains and not info['private_copy_complete']
    assert saw_partial_copy


def test_empty_graph_and_expired_entry_alias():
    result,info=dc.deletion_closure({}, {}, {})
    assert result=={} and info['closure_complete'] and info['input_validated']
    chains,source,target=articulation_fixture()
    result,info=dc.deletion_closure(chains,source,target,deadline=-1.)
    assert result is chains and info['returned_input_alias'] and not info['input_validated']


@pytest.mark.parametrize('deadline',[float('nan'),float('inf'),float('-inf'),True,'soon'])
def test_malformed_deadlines_are_rejected(deadline):
    with pytest.raises(ValueError):dc.deletion_closure({}, {}, {},deadline=deadline)


@pytest.mark.parametrize('kind',['duplicate','missing','unknown','disconnected','uncovered','source_loop','source_asymmetry','source_bool'])
def test_detected_invalid_inputs_raise_without_mutation(kind):
    chains,source,target=articulation_fixture()
    if kind=='duplicate':chains[0].append(3)
    elif kind=='missing':del chains[1]
    elif kind=='unknown':chains[0].append(999)
    elif kind=='disconnected':chains[0]=[1,2]
    elif kind=='uncovered':chains[0]=[0,1]
    elif kind=='source_loop':source[0].add(0)
    elif kind=='source_asymmetry':source[1].clear()
    elif kind=='source_bool':source={False:{1},1:{False}}
    before=deepcopy((chains,source,target))
    with pytest.raises(ValueError):dc.deletion_closure(chains,source,target)
    assert (chains,source,target)==before


def test_isolated_module_import_and_tiny_call_block_external_embedders():
    path=Path(dc.__file__).resolve()
    program='''import importlib.abc,json,runpy,sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if any(s in fullname.lower() for s in ('minorminer','busclique')):
            raise AssertionError('prohibited import '+fullname)
sys.meta_path.insert(0,Block())
module=runpy.run_path(sys.argv[1])
result,info=module['deletion_closure']({0:[0,1]},{0:[]},{0:{1},1:{0}})
assert result=={0:[1]} and info['accepted_deletions']==1
assert not any(any(s in n.lower() for s in ('minorminer','busclique')) for n in sys.modules)
print(json.dumps({'valid':True,'closure_complete':info['closure_complete']}))
'''
    completed=subprocess.run([sys.executable,'-I','-B','-c',program,str(path)],
                             capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(completed.stdout)=={'valid':True,'closure_complete':True}
