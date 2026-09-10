"""Thin generation adapter for the declared Transfer003 development inputs."""
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT/'scripts/codex/transfer_panel.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '85056d607d540ff788b305b7d6abb94e990cca1797ecb6fabb2eb644f1001e24'
spec = importlib.util.spec_from_file_location('_frozen_transfer_helpers', HELPER)
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
OLD_PUBLIC, OLD_PRIVATE = h.PUBLIC, h.PRIVATE
h.PUBLIC = ROOT/'results/codex/transfer-cycle-003'
h.PRIVATE = ROOT.parent/'ember-evaluator-private/transfer-cycle-003'
PROTOCOL = ROOT/'notes/codex/transfer_cycle_003_inputs.md'
COPIES = [f'g{i:04d}' for i in range(1,23)] + ['g0101','g0102']


def seed(namespace, case):
    return int.from_bytes(hashlib.sha256(f'ember-codex-transfer003/{namespace}/{case}'.encode()).digest()[:8], 'big')


h.seed = seed


def attempt(case):
    folder = h.PRIVATE/case['case']; folder.mkdir()
    argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker',
            json.dumps(case,sort_keys=True), str(folder/'generated.json')]
    h.save(folder/'invocation.json',dict(argv=argv,script_sha256=h.sha(__file__)))
    began = time.perf_counter()
    with (folder/'stdout').open('x') as stdout, (folder/'stderr').open('x') as stderr:
        try:
            result = subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=case['generation_timeout'])
            status = dict(returncode=result.returncode,timed_out=False)
        except subprocess.TimeoutExpired:
            status = dict(returncode=None,timed_out=True)
    status['process_wall'] = time.perf_counter()-began
    h.save(folder/'status.json',status)
    if status['returncode'] != 0 or not (folder/'generated.json').exists():
        return dict(case=case,status='GENERATION_TIMEOUT' if status['timed_out'] else 'GENERATION_ERROR',**status)
    return dict(case=case,**status,**json.loads((folder/'generated.json').read_text()))


def main():
    assert h.sha(h.GENERATOR) == 'f5528a0a2b9f82f8af501c1d253dc7bd34b77da52af58eac02117a6baf1b43b2'
    assert h.sha(h.ORACLE) == 'e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
    assert h.sha(h.ARCHIVE/'target.json') == 'c683ae784e2ee9a1d14f0760368deaa5cfeee2c47a6c2eade683e5412e61177c'
    h.PUBLIC.mkdir(exist_ok=False); (h.PUBLIC/'graphs').mkdir()
    h.PRIVATE.mkdir(exist_ok=False)
    cases = [dict(case='watts_strogatz-100-k6-b02',family='watts_strogatz',kind='fresh',params=dict(n=100,k=6,beta=.2),generation_timeout=30),
             dict(case='sbm-100-c4-p020-p002',family='sbm',kind='fresh',params=dict(n=100,n_communities=4,p_in=.20,p_out=.02),generation_timeout=30),
             dict(case='random_planar-100',family='random_planar',kind='fresh',params=dict(n=100),generation_timeout=300)]
    plan = dict(cases=cases,copied_graphs=COPIES,script_sha256=h.sha(__file__),helper_sha256=h.sha(HELPER),
                protocol_sha256=h.sha(PROTOCOL),old_panel_sha256=h.sha(OLD_PUBLIC/'panel.json'),
                second_panel_sha256=h.sha(ROOT/'results/codex/transfer-cycle-002/panel.json'),
                generator_sha256=h.sha(h.GENERATOR),oracle_sha256=h.sha(h.ORACLE),python=platform.python_version(),
                purpose='Development mechanism screens only; no constructor calls')
    h.save(h.PUBLIC/'generation_plan.json',plan)
    panels = {'transfer001': (OLD_PUBLIC,OLD_PRIVATE),
              'transfer002': (ROOT/'results/codex/transfer-cycle-002',ROOT.parent/'ember-evaluator-private/transfer-cycle-002')}
    entries = {}
    for panel_name,(public,private) in panels.items():
        for row in json.loads((public/'panel.json').read_text())['inputs']:
            if row['graph'] in COPIES and row['graph'] not in entries:
                entries[row['graph']] = (row,panel_name,public,private)
    rows=[]
    for key in COPIES:
        prior,panel_name,public,private=entries[key];row=dict(prior)
        assert h.sha(public/'graphs'/(key+'.json')) == row['graph_sha256']
        assert h.sha(private/(key+'.json')) == row['private_record_sha256']
        shutil.copy2(public/'graphs'/(key+'.json'), h.PUBLIC/'graphs'/(key+'.json'))
        shutil.copy2(private/(key+'.json'), h.PRIVATE/(key+'.json'))
        row.update(prior_panel=panel_name,prior_kind=row['kind'],kind='reused_development')
        rows.append(row)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        values=list(pool.map(attempt,cases))
    ledger=[]
    for i,value in enumerate(values,201):
        ledger.append({k:v for k,v in value.items() if k not in ('original','witness','witness_quality')})
        if value['status']=='READY':rows.append(h.publish(value,f'g{i:04d}',value['case']['case']))
    h.save(h.PUBLIC/'attempt_ledger.json',ledger)
    h.save(h.PUBLIC/'panel.json',dict(inputs=rows,realized_inputs=len(rows),intended_structures=25,
        intended_relabelings=2,private_witnesses_shipped=False,generation_plan_sha256=h.sha(h.PUBLIC/'generation_plan.json')))
    print(json.dumps(dict(status='PANEL_FROZEN',inputs=len(rows),generation_failures=sum(v['status']!='READY' for v in values))))


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':h.worker(json.loads(sys.argv[2]),Path(sys.argv[3]))
    else:main()
