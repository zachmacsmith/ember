"""C016: publish admissible births; rebuild only after ordinary placement fails.

One evolving partial minor. C015 supplies unchanged placement, capacity and
retraction helpers; its constructor is never called. No external embedding
solver, proactive reconstruction, or additional work limit is used.
"""
import importlib.util
import math
from pathlib import Path
import time

_path = Path(__file__).with_name('zephyr_constrained_contact.py')
_spec = importlib.util.spec_from_file_location('_c016_constrained_support', _path)
_c15 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_c15)
_c, _c14 = _c15._c, _c15._c14
_Budget, _Deadline, _InputError = _c15._Budget, _c15._Deadline, _c15._InputError
_State, _Engine = _c15._State, _c15._Engine
_capacities, _certify = _c15._capacities, _c15._certify
_place, _transaction = _c15._place, _c15._transaction


def _run(state,diag):
    e=state.e
    while len(state.I)<e.n:
        e.b.check();v=e.next(state)
        row=dict(source=v,introduced_before=len(state.I),Q_before=state.Q,status='started',
                 domains_before={u:d.bit_count() for u,d in state.domains.items()},capacities_before=_capacities(state))
        diag['publications'].append(row)
        with e.b.stage('ordinary'):
            ordinary=_place(state,v)
        failure=e.placements[-1] if ordinary is None else None
        row.update(ordinary_score=ordinary.score() if ordinary is not None else None,
                   newly_empty=_c._lost(state,ordinary) if ordinary is not None else [])
        if ordinary is not None:
            chosen=ordinary;row['status']='ordinary'
        else:
            transaction=dict(source=v,status='started');e.rebuilds.append(transaction)
            try:
                with e.b.stage('retraction'):
                    chosen=_transaction(state,v,ordinary,transaction,failure)
            except _Deadline:transaction['status']='interrupted';raise
            row['status']=transaction['status']
        if chosen is None:return state,'construction_obstructed'
        with e.b.stage('publication_certificate'):
            _certify(chosen);score=chosen.score()
            domains={u:d.bit_count() for u,d in chosen.domains.items()};caps=_capacities(chosen);e.b.check()
        if chosen.I != state.I | {v}:raise RuntimeError('publication is not net one source vertex')
        state=chosen;e.published=state
        row.update(published=True,introduced_after=len(state.I),Q_after=state.Q,score=score,
                   domains_after=domains,capacities_after=caps)
    return state,'complete_introduced_source'


def admissible_contact_embed(source,target,*,seed=0,timeout=60.,deadline=None):
    started,cpu=time.perf_counter(),time.process_time()
    response=dict(status='FAILURE',embedding={},diag=dict(algorithm='admissible_contact_domain',policy='C016',
        publications=[],fatal_error=False,work_limit=None,
        restrictions=['individual_fixed_chain_capacity','first_admissible_root','single_path_label','greedy_capacity_growth','greedy_private_rebuild']))
    e,state,b,absolute=None,None,None,None
    try:
        if type(seed) is not int or type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0:
            raise _InputError('integer seed and positive finite timeout required')
        if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
            raise _InputError('finite deadline required')
        absolute=min(started+timeout,deadline) if deadline is not None else started+timeout
        reserve=min(.5,timeout/10);b=_Budget(absolute-reserve)
        response['diag'].update(deadline=absolute,search_deadline=b.deadline,final_reserve=reserve)
        with b.stage('input_geometry'):
            sl,src=_c._graph(source,b);tl,adj=_c._graph(target,b)
            if len(src)>len(adj):raise _InputError('source vertex count exceeds target count')
            m,coords=_c._geometry(target,tl,adj,b);e=_Engine(src,adj,coords,m,seed,b)
            state=_State(e);e.published=state;e.active_entry=state;e.active_source=None
            response['diag'].update(source_ranks=e.srank,target_ranks=e.trank,initial=state.snapshot())
        _,response['diag']['stop_reason']=_run(state,response['diag'])
    except _Deadline as exc:
        response['diag'].update(stop_reason='search_deadline',interrupted_stage=str(exc))
    except Exception as exc:
        expected=isinstance(exc,_InputError)
        response.update(status='FAILURE' if expected else 'ERROR',error=f'{type(exc).__name__}: {exc}')
        response['diag'].update(fatal_error=not expected,exception=dict(type=type(exc).__name__,message=str(exc)))
    if b is not None:
        b.deadline=absolute
        if e is not None and state is not None:
            state=e.published
            if e.complete is not None and not response.get('error'):
                state=e.complete;response['diag']['complete_private_first_admissible']=True
            response['diag'].update(placements=e.placements,rebuilds=e.rebuilds,published_state=e.published.snapshot())
            try:
                with b.stage('final_validation_output'):
                    b.tick('terminal_prefix_records',e.active_entry.Q+len(e.active_entry.I))
                    response['diag']['terminal_private_entry']=e.active_entry.snapshot()
                    response['diag']['terminal_private_source']=e.active_source
                    _certify(state);_c._final(state,source,target,sl,tl,response)
            except _Deadline:
                response['embedding']={};response['diag']['final_stop']='deadline'
            except Exception as exc:
                response.update(status='ERROR',embedding={},error=f'{type(exc).__name__}: {exc}')
                response['diag']['fatal_error']=True
        response['diag'].update(work=dict(b.work),total_work=sum(b.work.values()),
                                stage_wall=dict(b.stage_wall),stage_cpu=dict(b.stage_cpu))
    finished=time.perf_counter();response['time']=finished-started
    response['diag'].update(wall=finished-started,cpu=time.process_time()-cpu,finished=finished)
    if absolute is not None and finished>=absolute:
        response['embedding']={}
        if not response['diag']['fatal_error']:response['status']='TIMEOUT'
    return response
