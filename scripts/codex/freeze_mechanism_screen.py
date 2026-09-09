"""Input-only, specification-driven initializer for the unchanged audited pilot."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import types

ROOT=Path(__file__).resolve().parents[2]
PILOT=ROOT/'scripts/codex/pilot.py'
ALLOWED_NEW={'native-interleaved-boundary','compiled-mobile-tree','contact-domain'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def registry_proof():
    old=ast.parse(subprocess.check_output(['git','show','05eb4046:scripts/codex/pilot.py'],cwd=ROOT,text=True))
    new=ast.parse(PILOT.read_text())
    def registry(tree):
        return next(x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONSTRUCTORS' for t in x.targets))
    before=ast.literal_eval(registry(old).value);after=ast.literal_eval(registry(new).value)
    additions=set(after)-set(before)
    assert additions<=ALLOWED_NEW and {k:v for k,v in after.items() if k not in additions}==before
    registry(new).value=registry(old).value
    assert ast.dump(new,include_attributes=False)==ast.dump(old,include_attributes=False)
    return dict(previous_entries=len(before),added_entries=sorted(additions),all_other_ast_unchanged=True)


def main(spec_path):
    screen=read(spec_path);base=ROOT/screen['panel_directory'];panel=read(base/'panel.json')
    review=read(base/'input_review001/summary.json')
    assert review['status']=='PASS' and review['panel_sha256']==sha(base/'panel.json')
    keys=screen['graphs'];methods=screen['methods'];candidate=methods[0]
    assert len(set(keys))==len(keys) and len(set(methods))==len(methods)
    assert 'mm' in methods and 'native-branched-path' in methods and candidate in ALLOWED_NEW
    proof=registry_proof();out=ROOT/screen['freeze_directory'];out.mkdir(exist_ok=False)
    run=ROOT/'results/codex'/screen['run_name']
    entries={r['graph']:r for r in panel['inputs']};records={}
    for key in keys:
        entry=entries[key];path=base/'graphs'/(key+'.json');rec=read(path)
        assert sha(path)==entry['graph_sha256'] and digest(rec)==entry['source_hash']
        assert rec['metadata']=={} and all(row[-1]=={} for row in rec['node_attributes']+rec['edge_attributes'])
        records[key]=rec
    refs={}
    for name,want in screen['references'].items():
        path=ROOT/name;assert sha(path)==want,name;refs[name]=want
    spec=importlib.util.spec_from_file_location('_mechanism_pilot',PILOT)
    pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
    assert all(m=='mm' or m in pilot.CONSTRUCTORS for m in methods)
    method_path,function=pilot.CONSTRUCTORS[candidate]
    args=types.SimpleNamespace(run=str(run),graphs=','.join(keys),methods=','.join(methods),seeds=screen['seeds'],
        timeout=screen['timeout'],corpus_selection=None,input_supplement=None,
        candidate_python=screen['candidate_python'],mm_python=screen['mm_python'])
    authority=dict(args=vars(args),host=screen['host'],screen_spec_sha256=sha(spec_path),
        panel_sha256=sha(base/'panel.json'),adapter_sha256=sha(Path(__file__)),pilot_sha256=sha(PILOT),
        method_path=method_path,method_sha256=sha(ROOT/method_path),function=function,registry_proof=proof,references=refs)
    (out/'before_freeze.json').write_text(json.dumps(authority,indent=2,sort_keys=True)+'\n')
    pilot.make_graphs=lambda:{name:pilot.graph_from_record(r) for name,r in records.items()}
    pilot.initialize(args)
    manifest=read(run/'manifest.json');expected=[]
    # Other isolated tracks may be editing while the audited initializer copies
    # the repository. Refuse an incoherent snapshot before any remote execution.
    assert digest(manifest['source_files'])==manifest['source_snapshot']
    for name,want in manifest['source_files'].items():
        assert sha(run/'source'/name)==want,name
    assert manifest['source_files'][method_path]==authority['method_sha256']
    assert manifest['source_files']['scripts/codex/pilot.py']==authority['pilot_sha256']
    for name,want in refs.items():
        if name in manifest['source_files']:
            assert manifest['source_files'][name]==want,name
    assert sha(run/'target.json')=='c683ae784e2ee9a1d14f0760368deaa5cfeee2c47a6c2eade683e5412e61177c'
    for name,record in records.items():
        assert (run/'graphs'/(name+'.json')).read_bytes()==(base/'graphs'/(name+'.json')).read_bytes()
        for seed in range(args.seeds):
            order=list(methods);random.Random(f'{name}:{seed}').shuffle(order)
            for method in order:
                task=dict(graph=name,source_hash=digest(record),target_hash=manifest['target_hash'],
                    source_snapshot=manifest['source_snapshot'],seed=seed,method=method,config={},timeout=args.timeout)
                task['task_id']=digest(task)[:24]
                assert read(run/'tasks'/(task['task_id']+'.json'))==task
                expected.append(task['task_id'])
    assert expected==manifest['tasks'] and len(set(expected))==len(keys)*len(methods)*args.seeds
    manifest['research_input_identity']={k:authority[k] for k in ('panel_sha256','screen_spec_sha256','adapter_sha256')}
    pilot.write_json(run/'manifest.json',manifest)
    for path in run.rglob('*'):
        assert not path.is_symlink() and 'ember-evaluator-private' not in str(path)
        assert path.name not in ('transfer_panel.py','transfer_panel002.py','transfer_verify002.py')
    result=dict(status='FROZEN',run=str(run),tasks=len(expected),source_snapshot=manifest['source_snapshot'],
                manifest_sha256=sha(run/'manifest.json'),ordered_tasks_sha256=digest(expected),**authority)
    (out/'freeze_result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('status','run','host','tasks','source_snapshot','manifest_sha256')}))


if __name__=='__main__':main(Path(sys.argv[1]).resolve())
