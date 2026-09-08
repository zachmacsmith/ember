"""Bounded repair of one blocked partial-minor insertion, preserving all guards."""
import hashlib
import itertools
from pathlib import Path
import time
import types

_PATH=Path(__file__).with_name('frontier_reinsertion_construction.py')
_SHA='f29cdef92e5e0d6ce51594c7a13dfe2b234c3dfa15e25e4b5b0022d92c5f678d'
_raw=_PATH.read_bytes()
if hashlib.sha256(_raw).hexdigest()!=_SHA:
    raise ImportError('Unexpected frozen-aware frontier primitive source')
_helpers=types.ModuleType('_blocked_reinsertion_primitives')
_helpers.__file__=str(_PATH)
exec(compile(_raw,str(_PATH),'exec'),_helpers.__dict__)
Builder=_helpers._Builder
Stop=_helpers._Stop
QUERY_SCANS=1_000_000
TOTAL_SCANS=5_000_000


def blocked_reinsert(engine,v,entry,created_fill=()):
    """Use the live engine/R/budget; return at most one certified private mapping.

    The engine must use the pinned frozen-aware Builder primitives. No core or
    ordinary constructor is called. `entry` and its chain sets remain untouched.
    Certification here is not the caller's final joint graph/chain commitment.
    """
    info=engine.info
    used=info.setdefault('blocked_repair_scans',0)
    start=time.perf_counter();began=engine.scans
    limit=min(QUERY_SCANS,TOTAL_SCANS-used,_helpers.SCANS-engine.scans)
    record=dict(vertex=v,status='started',scan_start=began,scan_end=began,scans=0,
                total_start=used,total_end=used,limit=max(0,limit),blocks=[],pool=[],
                competitors=[],required_neighbors=[],certified=False,returned=False,committed=False,
                qubits_before=sum(map(len,entry.values())),qubits_after=None,wall=0.)
    record['limit_sources']=[name for name,value in (('query',QUERY_SCANS),
        ('repair_total',TOTAL_SCANS-used),('global',_helpers.SCANS-engine.scans)) if value==limit]
    info['blocked_repair_queries']=info.get('blocked_repair_queries',0)+1
    if limit<=0:
        record.update(status='repair_budget_exhausted',wall=time.perf_counter()-start)
        info.setdefault('blocked_repair_records',[]).append(record)
        return None,record
    old_end=getattr(engine,'repair_end',None)
    if old_end is not None:
        raise RuntimeError('recursive/nested blocked repair is not supported')
    engine.repair_end=engine.scans+limit
    answer=None
    current=None
    try:
        engine.check()
        if v in entry:raise ValueError('new source vertex already placed')
        _,_,bounds,free=engine.state(entry)
        required=[w for w in engine.source[v] if w in entry]
        if len(required)>3:raise ValueError('at most three required neighbors expected')
        record['required_neighbors']=sorted(required)
        union=0
        for w in required:
            engine.scan();union|=bounds[w]&free
        competitors=[]
        for w in entry:
            engine.scan()
            if w in required or not engine.future(w,entry):continue
            port=bounds[w]&free
            if port.bit_count()!=1 or not port&union:continue
            support=0
            for u in required:
                engine.scan();support+=bool(bounds[u]&port)
            competitors.append((-support,len(entry[w]),engine.vrank[w],w,port))
        competitors.sort()
        competitors=competitors[:2]
        critical=[x[3] for x in competitors]
        record['competitors']=[dict(owner=w,required_support=-negative,chain_size=size,
                                    free_site=next(q for q in engine.target if engine.bit[q]&port))
                               for negative,size,rank,w,port in competitors]
        pool=critical+sorted(required,key=lambda w:(len(entry[w]),engine.vrank[w]))
        pool_rank={w:i for i,w in enumerate(pool)}
        record['pool']=pool
        blocks=[]
        for size in (1,2):
            for chosen in itertools.combinations(pool,size):
                engine.scan();blocks.append(chosen)
        blocks.sort(key=lambda k:(sum(len(entry[w]) for w in k),len(k),
                                  tuple(sorted(pool_rank[w] for w in k))))
        record['selection_scans']=engine.scans-began
        for chosen in blocks:
            engine.check()
            block_start=engine.scans;wall_start=time.perf_counter()
            current=dict(selected=list(chosen),released_sites=sum(len(entry[w]) for w in chosen),
                         order=[],status='started',scan_start=block_start,scans=0,wall=0.,
                         frozen_equal=None,valid=None,frontier_preserved=None,qubits=None)
            record['blocks'].append(current)
            frozen=set(entry)-set(chosen)
            trial={w:set(c) for w,c in entry.items() if w in frozen}
            todo=set(chosen);u=v
            try:
                while True:
                    current['order'].append(u)
                    trial=engine.insert(u,trial,frozen)
                    if trial is None:
                        current['status']='reconstruction_blocked';break
                    if not todo:break
                    u=max(todo,key=lambda z:(sum(w in trial for w in engine.source[z]),
                                              len(engine.source[z]),-engine.vrank[z]))
                    todo.remove(u)
                if trial is None:continue
                movable_fill={w for edge in created_fill for w in edge if w in chosen}
                before_prune=sum(map(len,trial.values()))
                if movable_fill:trial=engine.prune(trial,movable_fill)
                current['released_fill_qubits_pruned']=before_prune-sum(map(len,trial.values()))
                equal=True
                for w in frozen:
                    engine.scan()
                    if trial.get(w)!=entry[w]:equal=False;break
                current['frozen_equal']=equal
                if set(trial)!=set(entry)|{v} or not equal:
                    raise RuntimeError('rebuilt block changed frozen ownership or coverage')
                current['valid']=engine.valid(trial,complete=False)
                if not current['valid']:raise RuntimeError('invalid rebuilt partial minor')
                _,_,new_bounds,new_free=engine.state(trial)
                current['frontier_preserved']=engine.frontier_ok(trial,new_bounds,new_free)
                if not current['frontier_preserved']:raise RuntimeError('rebuilt block lost future frontier')
                engine.check()
                q=sum(map(len,trial.values()))
                current.update(status='complete',qubits=q)
                record.update(status='certified',certified=True,qubits_after=q,selected=list(chosen),
                              released_fill_qubits_pruned=current['released_fill_qubits_pruned'])
                answer=trial
                break
            finally:
                current.update(scans=engine.scans-block_start,wall=time.perf_counter()-wall_start)
        if answer is None:record['status']='all_blocks_failed'
    except _helpers._RepairLimit:
        record['status']='local_work_limit'
        if current is not None and current['status']=='started':current['status']='local_work_limit'
    except Stop:
        record['status']=info.get('stopped_by') or 'interrupted'
        if current is not None and current['status']=='started':current['status']=record['status']
        raise
    except Exception as exc:
        record.update(status='error',error=repr(exc))
        if current is not None and current['status']=='started':current['status']='error'
        raise
    finally:
        engine.repair_end=old_end
        record.update(scan_end=engine.scans,scans=engine.scans-began,
                      total_end=used+engine.scans-began,wall=time.perf_counter()-start)
        info['blocked_repair_scans']=record['total_end']
        info.setdefault('blocked_repair_records',[]).append(record)
    ended=time.perf_counter()
    record['wall']=ended-start
    if ended>=engine.deadline:
        info['stopped_by']='deadline'
        record.update(status='deadline',returned=False)
        raise Stop
    record['returned']=answer is not None
    return answer,record
