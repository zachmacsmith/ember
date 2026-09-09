"""Independently validate specification-driven transfer002 outputs against evaluator-only originals.

No constructors, generator imports, witness initialization or output selection.
The existing pure-stdlib original-minor oracle supplies all embedding checks.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import time

ROOT=Path(__file__).resolve().parents[2]
PANEL=ROOT/'results/codex/transfer-cycle-002'
PRIVATE=ROOT.parent/'ember-evaluator-private/transfer-cycle-002'
ORACLE=ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main(screen_path, archive, output):
    output.mkdir(exist_ok=False)
    began=time.perf_counter(); errors=[]; bindings={}; rows=[]
    def bound(path):
        value=read(path); bindings[str(path)]=sha(path); return value
    assert sha(ORACLE)=='e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
    bindings[str(ORACLE)]=sha(ORACLE)
    spec=importlib.util.spec_from_file_location('_transfer_original_oracle',ORACLE)
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    screen=bound(screen_path)
    assert screen['seeds']==1, 'This small screen analyzes seed0 only'
    frozen=bound(ROOT/screen['freeze_directory']/'freeze_result.json')
    assert sha(screen_path)==frozen['screen_spec_sha256']
    track=screen['track']
    review=bound(PANEL/'input_review001/summary.json')
    assert review['status']=='PASS' and review['panel_sha256']==sha(PANEL/'panel.json')
    panel=bound(PANEL/'panel.json');manifest=bound(archive/'manifest.json')
    assert sha(archive/'manifest.json')==frozen['manifest_sha256']
    assert sha(PANEL/'panel.json')==frozen['panel_sha256']
    assert digest(manifest['source_files'])==manifest['source_snapshot']==frozen['source_snapshot']
    for name,want in manifest['source_files'].items():
        path=archive/'source'/name;assert sha(path)==want,name;bindings[str(path)]=want
    assert digest(manifest['tasks'])==frozen['ordered_tasks_sha256'] and len(set(manifest['tasks']))==len(screen['graphs'])*len(screen['methods'])==frozen['tasks']
    target_record=bound(archive/'target.json')
    assert sha(archive/'target.json')=='c683ae784e2ee9a1d14f0760368deaa5cfeee2c47a6c2eade683e5412e61177c'
    target=oracle.adjacency(target_record)
    assert digest(target_record)==manifest['target_hash']
    entries={entry['graph']:entry for entry in panel['inputs'] if entry['graph'] in screen['graphs']}
    assert set(entries)==set(screen['graphs'])
    candidate=frozen['args']['methods'].split(',')[0]
    methods=screen['methods'];assert methods==frozen['args']['methods'].split(',')
    seen=set()
    for tid in manifest['tasks']:
        task=bound(archive/'tasks'/(tid+'.json'))
        assert digest({k:v for k,v in task.items() if k!='task_id'})[:24]==tid==task['task_id']
        assert task['source_snapshot']==manifest['source_snapshot'] and task['target_hash']==manifest['target_hash']
        assert task['seed']==0 and task['timeout']==screen['timeout'] and task['config']=={} and task['method'] in methods
        key=(task['graph'],task['method']);assert key not in seen;seen.add(key)
        entry=entries[task['graph']];source_path=archive/'graphs'/(task['graph']+'.json')
        record=bound(source_path);assert sha(source_path)==entry['graph_sha256']
        assert digest(record)==entry['source_hash']==task['source_hash']
        evaluator=bound(PRIVATE/(task['graph']+'.json'))
        assert sha(PRIVATE/(task['graph']+'.json'))==entry['private_record_sha256']
        assert evaluator['source_hash']==entry['source_hash']
        result_path=archive/'results'/(tid+'.json')
        row=dict(task_id=tid,graph=task['graph'],case=entry['case'],family=entry['family'],kind=entry['kind'],
                 prior_kind=entry.get('prior_kind'),
                 parent=entry['parent'],nodes=entry['nodes'],edges=entry['edges'],method=task['method'],seed=0,
                 credited=False,status='MISSING_RESULT',qubits=None,acl=None,max_chain=None,within_chain_variance=None,
                 solver_wall=None,solver_cpu=None,process_wall=None,diagnostic_valid=False)
        if not result_path.exists():
            errors.append(dict(task=tid,error='Missing terminal result'));rows.append(row);continue
        result=bound(result_path)
        assert all(result.get(k)==v for k,v in task.items()),tid
        assert result.get('controller_finalized') is True,tid
        assert result['host']==frozen['host'],(tid,result['host'])
        expected_python=frozen['args']['mm_python' if task['method']=='mm' else 'candidate_python']
        identity_ok=result.get('python_executable') is not None
        if identity_ok:
            assert result['python_executable']==expected_python
        elif result['status']=='SUCCESS':
            errors.append(dict(task=tid,error='Successful result lacks interpreter identity'))
        for field in ('solver_wall','solver_cpu','process_wall'):
            value=result.get(field)
            if value is not None: assert isinstance(value,(int,float)) and math.isfinite(value) and value>=0,(tid,field)
            row[field]=value
        row['unknown_time_fields']=[field for field in ('solver_wall','solver_cpu','process_wall') if row[field] is None]
        valid,reason,quality=oracle.embedding_quality(result.get('embedding'),*oracle.adjacency(record),*target)
        if valid:
            reverse={int(v):int(k) for k,v in evaluator['original_to_solver'].items()}
            original_map={str(reverse[int(v)]):chain for v,chain in result['embedding'].items()}
            ov,why,oq=oracle.embedding_quality(original_map,*oracle.adjacency(evaluator['original']),*target)
            assert ov and quality==oq,(tid,why)
            for field in ('qubits','max_chain'):
                if field in result: assert result[field]==quality[field],(tid,field)
            for field in ('acl','within_chain_variance'):
                if field in result: assert math.isclose(result[field],quality[field],rel_tol=1e-12,abs_tol=1e-12),(tid,field)
        row['peak_rss_bytes']=result.get('peak_rss_bytes')
        passive=result.get('diagnostic_embedding')
        passive_valid,passive_reason,passive_quality=oracle.embedding_quality(passive,*oracle.adjacency(record),*target)
        if passive_valid:
            reverse={int(v):int(k) for k,v in evaluator['original_to_solver'].items()}
            passive_original={str(reverse[int(v)]):chain for v,chain in passive.items()}
            pv,pr,pq=oracle.embedding_quality(passive_original,*oracle.adjacency(evaluator['original']),*target)
            assert pv and pq==passive_quality,(tid,pr)
        timely=row['solver_wall'] is not None and row['solver_wall']<=task['timeout']
        credit=(identity_ok and result['status']=='SUCCESS' and result.get('returncode')==0 and not result.get('error') and valid and timely)
        if result['status']=='SUCCESS' and not credit:
            errors.append(dict(task=tid,error='Reported success fails independent credit',valid=valid,reason=reason,timely=timely,
                               worker_error=result.get('error'),returncode=result.get('returncode')))
        row.update(status=result['status'],credited=credit,returned_embedding_valid=valid,
                   diagnostic_valid=passive_valid,diagnostic_present=passive is not None,
                   diagnostic_validation_reason=passive_reason,validation_reason=reason,
                   returncode=result.get('returncode'),error=result.get('error'),
                   late=None if row['solver_wall'] is None else not timely,
                   returned_embedding_qubits=quality['qubits'] if quality else None,
                   diagnostic_qubits=passive_quality['qubits'] if passive_quality else None)
        if credit: row.update(quality)
        rows.append(row)
    assert seen=={(name,method) for name in entries for method in methods}
    by_key={(r['graph'],r['method']):r for r in rows};comparisons=[]
    for name,entry in entries.items():
        comparison=dict(graph=name,case=entry['case'],family=entry['family'],kind=entry['kind'],
                        prior_kind=entry.get('prior_kind'),parent=entry['parent'])
        for method in methods:comparison[method]=by_key[name,method]
        references=[(m, 'retained' if m=='native-branched-path' else 'mm' if m=='mm' else 'predecessor') for m in methods[1:]]
        assert len({label for _,label in references})==len(references)
        for ref,label in references:
            a,b=by_key[name,candidate],by_key[name,ref]
            common=a['credited'] and b['credited']
            comparison['q_delta_'+label]=a['qubits']-b['qubits'] if common else None
            comparison['solver_ratio_'+label]=a['solver_wall']/b['solver_wall'] if common and b['solver_wall'] else None
            comparison['process_ratio_'+label]=(a['process_wall']/b['process_wall']
                if common and a['process_wall'] is not None and b['process_wall'] is not None and b['process_wall']>0 else None)
            comparison['lost_success_'+label]=b['credited'] and not a['credited']
            comparison['gained_success_'+label]=a['credited'] and not b['credited']
        comparisons.append(comparison)
    fresh=[c for c in comparisons if c['kind']=='fresh' and c['parent'] is None]
    gains=[c for c in fresh if c['q_delta_retained'] is not None and c['q_delta_retained']<0]
    families=sorted({c['family'] for c in gains})
    lost=[c['graph'] for c in comparisons if c['lost_success_retained']]
    worse=[c['graph'] for c in comparisons if c['q_delta_retained'] is not None and c['q_delta_retained']>0]
    # These are numerical observations, not automatic mechanism or promotion decisions.
    # Each fixed policy defines its separate continuation criterion before calls.
    totals={}
    for method in methods:
        subset=[r for r in rows if r['method']==method]
        totals[method]=dict(attempts=len(subset),credited=sum(r['credited'] for r in subset),
            statuses={s:sum(r['status']==s for r in subset) for s in sorted({r['status'] for r in subset})},
            **{field:dict(sum=sum(r[field] for r in subset if r[field] is not None),
                          observed=sum(r[field] is not None for r in subset))
               for field in ('solver_wall','solver_cpu','process_wall')})
    unknown_times=[dict(task=r['task_id'],fields=r.get('unknown_time_fields', ['solver_wall','solver_cpu','process_wall']))
                   for r in rows if r.get('unknown_time_fields', ['solver_wall','solver_cpu','process_wall'])]
    relabels=[]
    for name,entry in entries.items():
        if entry['parent'] is None: continue
        parent=entry['parent'];assert entries[parent]['original_topology_hash']==entry['original_topology_hash']
        for method in methods:
            a,b=by_key[parent,method],by_key[name,method]
            relabels.append(dict(parent=parent,relabeled=name,method=method,parent_status=a['status'],
                relabeled_status=b['status'],parent_credited=a['credited'],relabeled_credited=b['credited'],
                parent_qubits=a['qubits'],relabeled_qubits=b['qubits'],
                q_change=b['qubits']-a['qubits'] if a['credited'] and b['credited'] else None,
                parent_solver_wall=a['solver_wall'],relabeled_solver_wall=b['solver_wall'],
                parent_process_wall=a['process_wall'],relabeled_process_wall=b['process_wall']))
    summary=dict(status='PASS' if not errors else 'AUDIT_ERROR',errors=errors,track=track,candidate=candidate,
        totals=totals,mechanism_decision_required=True,screen_spec_sha256=sha(screen_path),
        unknown_time_rows=unknown_times, time_sum_scope='Observed costs only; missing times are unknown, never zero or inferred speedups',
        fresh_q_gain_graphs=[c['graph'] for c in gains],
        fresh_q_gain_families=families,lost_retained_successes=lost,retained_q_regressions=worse,
        variance_scope='Across-seed ACL variance undefined; within-embedding variance is a different metric',
        generalization_scope='Selected Transfer002 development inputs; exposure labels retained; no confirmation',
        analysis_wall=time.perf_counter()-began,script_sha256=sha(__file__),oracle_sha256=sha(ORACLE),
        constructor_calls=0,files=bindings)
    for name,value in [('summary.json',summary),('rows.json',rows),('comparisons.json',comparisons),('relabels.json',relabels)]:
        (output/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    with (output/'rows.csv').open('w') as f:
        fields=sorted(set().union(*(r.keys() for r in rows)));writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)
    print(json.dumps({k:summary[k] for k in ('status','track','fresh_q_gain_graphs','lost_retained_successes','retained_q_regressions','analysis_wall')}))
    if errors: raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screen',type=Path);parser.add_argument('archive',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();main(args.screen.resolve(),args.archive.resolve(),args.output.resolve())
