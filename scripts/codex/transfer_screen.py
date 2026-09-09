"""Input-only adapter to freeze the declared transfer001 screens in the audited pilot."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import types

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / 'results/codex/transfer-cycle-001'
PROTOCOL = ROOT / 'notes/codex/transfer_cycle_001_screen.md'
PILOT = ROOT / 'scripts/codex/pilot.py'
TARGET = ROOT / 'results/codex/retrieved/hyde06/061-branched-path-breadth/target.json'
TRACKS = {
    'a': ('063-mobile-boundary-transfer', 'hyde06', '3c7aa36653394e61', 'native-mobile-boundary'),
    'b': ('track-b-mobile-tree-027', 'hyde02', '4e1fb892db12754e', 'mobile-tree-recurrence'),
    'c': ('track-c-012-zephyr-frontier', 'hyde03', '4e1fb892db12754e', 'zephyr-frontier'),
}
NEW = {'native-mobile-boundary', 'mobile-tree', 'mobile-tree-recurrence', 'zephyr-frontier'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def registry_only():
    old = ast.parse(subprocess.check_output(['git', 'show', '4030f0e4:scripts/codex/pilot.py'], cwd=ROOT, text=True))
    new = ast.parse(PILOT.read_text())
    def registry(tree):
        return next(x for x in tree.body if isinstance(x, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'CONSTRUCTORS' for t in x.targets))
    before = ast.literal_eval(registry(old).value); after = ast.literal_eval(registry(new).value)
    assert set(after) - set(before) == NEW
    assert {k: v for k, v in after.items() if k not in NEW} == before
    registry(new).value = registry(old).value
    assert ast.dump(new, include_attributes=False) == ast.dump(old, include_attributes=False)
    return dict(previous_entries=len(before), new_entries=sorted(NEW), all_other_ast_unchanged=True)


def freeze(track):
    name, host, env, candidate = TRACKS[track]
    out = PANEL / ('freeze-' + track); out.mkdir(exist_ok=False)
    run = ROOT / 'results/codex' / name
    panel = json.loads((PANEL/'panel.json').read_text())
    review = json.loads((PANEL/'input_review001/summary.json').read_text())
    assert review['status'] == 'PASS' and review['panel_sha256'] == sha(PANEL/'panel.json')
    assert panel['realized_inputs'] == 22 and len(panel['inputs']) == 22
    proof = registry_only()
    spec = importlib.util.spec_from_file_location('_transfer_pilot', PILOT)
    pilot = importlib.util.module_from_spec(spec); spec.loader.exec_module(pilot)
    method_path, function = pilot.CONSTRUCTORS[candidate]
    assert (ROOT/method_path).is_file()
    records = {}
    for entry in panel['inputs']:
        path=PANEL/'graphs'/(entry['graph']+'.json'); raw=path.read_bytes(); record=json.loads(raw)
        assert sha(path) == entry['graph_sha256'] and digest(record) == entry['source_hash']
        assert record['metadata'] == {} and all(x[-1] == {} for x in record['node_attributes'] + record['edge_attributes'])
        records[entry['graph']] = record
    methods = [candidate, 'native-branched-path', 'mm']
    args = types.SimpleNamespace(run=str(run), graphs=','.join(records), methods=','.join(methods),
        seeds=1, timeout=60.0, corpus_selection=None, input_supplement=None,
        candidate_python=f'/home/dabh/ember-codex/envs/{env}/native/bin/python',
        mm_python=f'/home/dabh/ember-codex/envs/{env}/mm/bin/python')
    authority = dict(track=track, host=host, args=vars(args), adapter_sha256=sha(__file__),
        protocol_sha256=sha(PROTOCOL), panel_sha256=sha(PANEL/'panel.json'),
        pilot_sha256=sha(PILOT), method_path=method_path, method_sha256=sha(ROOT/method_path),
        function=function, registry_proof=proof)
    if track == 'b':
        authority['amendment_sha256'] = sha(ROOT / 'notes/codex/transfer_cycle_001_b027_amendment.md')
    (out/'before_freeze.json').write_text(json.dumps(authority, indent=2, sort_keys=True)+'\n')
    # Only the initializer's provider is replaced in this local process. The
    # frozen worker, supervision, timing and original-minor validators are byte copies.
    pilot.make_graphs = lambda: {name: pilot.graph_from_record(r) for name, r in records.items()}
    pilot.initialize(args)
    manifest = json.loads((run/'manifest.json').read_text())
    assert sha(run/'target.json') == sha(TARGET)
    expected=[]
    for name,record in records.items():
        assert (run/'graphs'/(name+'.json')).read_bytes() == (PANEL/'graphs'/(name+'.json')).read_bytes()
        order=list(methods);random.Random(f'{name}:0').shuffle(order)
        for method in order:
            task=dict(graph=name, source_hash=digest(record), target_hash=manifest['target_hash'],
                source_snapshot=manifest['source_snapshot'], seed=0, method=method, config={}, timeout=60.0)
            task['task_id']=digest(task)[:24]
            assert json.loads((run/'tasks'/(task['task_id']+'.json')).read_text()) == task
            expected.append(task['task_id'])
    assert expected == manifest['tasks'] and len(set(expected)) == 66
    # Only nonrevealing hashes are shipped. No private original, label map,
    # generator provenance, feasibility witness or family annotation is copied.
    manifest['research_input_identity'] = dict(panel_sha256=authority['panel_sha256'],
        adapter_sha256=authority['adapter_sha256'], protocol_sha256=authority['protocol_sha256'],
        purpose='fresh and exposed development with nested relabelings and hidden diagnostic controls')
    if 'amendment_sha256' in authority:
        manifest['research_input_identity']['amendment_sha256'] = authority['amendment_sha256']
    pilot.write_json(run/'manifest.json',manifest)
    for path in run.rglob('*'):
        assert not path.is_symlink()
        assert 'ember-evaluator-private' not in str(path) and path.name != 'transfer_panel.py'
    result=dict(status='FROZEN',run=str(run),tasks=len(expected),
                source_snapshot=manifest['source_snapshot'],manifest_sha256=sha(run/'manifest.json'),
                ordered_tasks_sha256=digest(expected),private_files_shipped=False,**authority)
    (out/'freeze_result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('status','host','run','tasks','source_snapshot','manifest_sha256')}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('track',choices=TRACKS)
    freeze(parser.parse_args().track)
