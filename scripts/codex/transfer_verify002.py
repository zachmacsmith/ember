"""Check Transfer002 identities with existing graph/oracle tools, no embedders."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'results/codex/transfer-cycle-002'
PRIVATE=ROOT.parent/'ember-evaluator-private/transfer-cycle-002'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    import networkx as nx
    assert nx.__version__=='3.4.2'
    out=BASE/'input_review001';out.mkdir(exist_ok=False)
    began=time.perf_counter();bindings={};rows=[]
    def bound(path):
        bindings[str(path)]=sha(path);return read(path)
    panel=bound(BASE/'panel.json');assert panel['realized_inputs']==9
    ledger=bound(BASE/'attempt_ledger.json');assert len(ledger)==2 and all(r['status']=='READY' for r in ledger)
    original_panel=bound(ROOT/'results/codex/transfer-cycle-001/panel.json')
    original_entries={r['graph']:r for r in original_panel['inputs']}
    oraclepath=ROOT/'results/codex/042-results-review/pre-execution/ember_embedding_oracle.py'
    assert sha(oraclepath)=='e4718c2ec09f3ec80e035ef89648f81b45413f52c7580123ef129419b25612d9'
    bindings[str(oraclepath)]=sha(oraclepath)
    spec=importlib.util.spec_from_file_location('_unchanged_oracle002',oraclepath)
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    target_record=bound(ROOT/'results/codex/retrieved/hyde06/061-branched-path-breadth/target.json')
    target=oracle.adjacency(target_record)
    old_review=bound(ROOT/'results/codex/transfer-cycle-001/input_review001/summary.json')
    exposed={Path(p):h for p,h in old_review['exposed_index_files'].items()}
    exposed.update({ROOT/'results/codex/transfer-cycle-001/graphs'/(r['graph']+'.json'):r['graph_sha256'] for r in original_panel['inputs']})
    index=[]
    for path,want in exposed.items():
        path=path.resolve();assert sha(path)==want;rec=bound(path);adj,_=oracle.adjacency(rec)
        index.append((path,(len(adj),len(rec['edges']),sorted(map(len,adj.values())))))
    for entry in panel['inputs']:
        key=entry['graph'];path=BASE/'graphs'/(key+'.json');rec=bound(path);private=bound(PRIVATE/(key+'.json'))
        assert sha(path)==entry['graph_sha256'] and digest(rec)==entry['source_hash']==private['source_hash']
        assert sha(PRIVATE/(key+'.json'))==entry['private_record_sha256']
        assert rec['nodes']==list(range(entry['nodes'])) and rec['metadata']=={}
        assert all(row[-1]=={} for row in rec['node_attributes']+rec['edge_attributes'])
        original=private['original'];mapping={int(k):v for k,v in private['original_to_solver'].items()}
        assert set(mapping)==set(original['nodes']) and sorted(mapping.values())==rec['nodes']
        assert {tuple(sorted((mapping[a],mapping[b]))) for a,b in original['edges']}=={tuple(e) for e in rec['edges']}
        witness=private.get('witness_original');control=None
        if witness is not None:
            ok,why,control=oracle.embedding_quality(witness,*oracle.adjacency(original),*target);assert ok,why
            ok,why,quality=oracle.embedding_quality(private['witness_solver'],*oracle.adjacency(rec),*target);assert ok and quality==control,why
        if entry['kind']=='reused_development':
            prior=original_entries[key]
            assert entry['source_hash']==prior['source_hash'] and entry['private_record_sha256']==prior['private_record_sha256']
        matches=[];unknown=[]
        if entry['kind']=='fresh':
            adj,_=oracle.adjacency(rec);signature=(len(adj),len(rec['edges']),sorted(map(len,adj.values())))
            for candidate,sig in index:
                if sig!=signature:continue
                try:
                    p=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--isomorphic',str(path),str(candidate)],capture_output=True,text=True,timeout=5)
                    if p.returncode!=0:unknown.append(dict(path=str(candidate),returncode=p.returncode,stderr=p.stderr))
                    elif p.stdout.strip()=='true':matches.append(str(candidate))
                    else:assert p.stdout.strip()=='false'
                except subprocess.TimeoutExpired:unknown.append(dict(path=str(candidate),timeout=True))
        rows.append(dict(graph=key,kind=entry['kind'],nodes=entry['nodes'],edges=entry['edges'],witness_quality=control,
                         exposed_matches=matches,unresolved_comparisons=unknown))
    result=dict(status='PASS',rows=rows,constructor_calls=0,panel_sha256=sha(BASE/'panel.json'),
                exposed_files=len(index),scope='Bijections and bounded exposed-index identity; no global novelty claim',
                wall=time.perf_counter()-began,script_sha256=sha(Path(__file__)),files=bindings)
    (out/'summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('status','rows','constructor_calls','exposed_files','wall')}))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--isomorphic':
        import networkx as nx
        def graph(path):
            rec=read(Path(path));g=nx.Graph();g.add_nodes_from(rec['nodes']);g.add_edges_from(rec['edges']);return g
        print(json.dumps(nx.is_isomorphic(graph(sys.argv[2]),graph(sys.argv[3]))))
    else:main()
