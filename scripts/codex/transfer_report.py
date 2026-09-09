"""Project audited transfer001 results; no constructor or validation changes."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/codex/transfer-cycle-001'
OUT = BASE / 'milestone001'
METHODS = {'a':'native-mobile-boundary', 'b':'mobile-tree-recurrence', 'c':'zephyr-frontier'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=False)
    bindings = {}; projections = {}; text = [
        '# Transfer001 audited development tables', '',
        'All results are seed0 on ideal Z12. Each track has its own same-host A061/MM references.',
        'Twenty primary structures and two nested relabelings are shown separately. Failed calls have no ACL.',
        'Across-seed ACL variance is unmeasured. Within-embedding variance, CPU and process time remain in the linked audit CSVs.',
        'No aggregate mean establishes improvement across sizes or classes.', '']
    for track, candidate in METHODS.items():
        directory = BASE / ('audit-'+track+'001') / 'output'
        def read(name):
            path = directory/name; bindings[str(path)] = sha(path)
            return json.loads(path.read_text())
        authority, comparisons, relabels = read('summary.json'), read('comparisons.json'), read('relabels.json')
        assert authority['status'] == 'PASS' and authority['candidate'] == candidate
        assert authority['script_sha256'] == '545a244f64548daf399a82e5496e67b712704ce4737e2f8e0612778719e2cb1c'
        assert len(comparisons) == 22
        projection = dict(all_attempts=authority['totals'], continuation_signal=authority['continuation_signal'],
                          relabels=relabels, scopes={})
        for scope, rows in [('primary', [c for c in comparisons if c['parent'] is None]),
                            ('fresh', [c for c in comparisons if c['parent'] is None and c['kind']=='fresh'])]:
            metrics = {}
            for method in [candidate, 'native-branched-path', 'mm']:
                rs = [c[method] for c in rows]
                metrics[method] = dict(attempts=len(rs), successes=sum(r['credited'] for r in rs),
                    statuses=dict(Counter(r['status'] for r in rs)),
                    **{field:sum(r[field] for r in rs) for field in ('solver_wall','solver_cpu','process_wall')})
            for ref in ['retained','mm']:
                ds = [c['q_delta_'+ref] for c in rows if c['q_delta_'+ref] is not None]
                metrics['versus_'+ref] = dict(common=len(ds), wins=sum(d<0 for d in ds), ties=sum(d==0 for d in ds),
                    losses=sum(d>0 for d in ds), q_delta_sum=sum(ds),
                    lost_successes=[c['graph'] for c in rows if c['lost_success_'+ref]],
                    solver_over10=[c['graph'] for c in rows if c['solver_ratio_'+ref] is not None and c['solver_ratio_'+ref]>10],
                    process_over10=[c['graph'] for c in rows if c['process_ratio_'+ref] is not None and c['process_ratio_'+ref]>10])
            projection['scopes'][scope] = metrics
        projections[track] = projection
        text += [f'## Track {track.upper()}: {candidate}', '',
                 'Q / ACL and solver seconds are candidate, A061, MM in that order. `r` marks a nested relabel.', '',
                 '| Input | Q: candidate / A061 / MM | ACL: candidate / A061 / MM | Solver seconds: candidate / A061 / MM |',
                 '|---|---:|---:|---:|']
        for c in comparisons:
            rs = [c[m] for m in [candidate,'native-branched-path','mm']]
            q = ' / '.join(str(r['qubits']) if r['credited'] else r['status'] for r in rs)
            acl = ' / '.join(f"{r['acl']:.4f}" if r['credited'] else '—' for r in rs)
            wall = ' / '.join(f"{r['solver_wall']:.3f}" for r in rs)
            text.append(f"| {c['graph']} {c['case']}{' r' if c['parent'] else ''} | {q} | {acl} | {wall} |")
        text += ['', f"[All 66 audit rows, including chain variance and process/CPU costs](../audit-{track}001/output/rows.csv).", '']
    # This fixed retained policy's development expansion is deliberately separate
    # from its previous breadth cohort and other hosts' timings/outcomes.
    comps = json.loads((BASE/'audit-a001/output/comparisons.json').read_text())
    groups = defaultdict(list)
    for c in comps:
        if c['kind']=='fresh' and c['parent'] is None: groups[c['family']].append(c)
    class_rows = []
    text += ['## Retained A061: fresh development by class on hyde06', '',
             'Two structures per row, sizes80/160, one seed each. Means summarize this sample only;',
             'the split result counts and worst ACL gap preserve mixed-size regressions. Variance across seeds is unknown.', '',
             '| Class | Success A061 / MM | Mean ACL A061 / MM | Lower / tied / higher ACL inputs | Worst A061−MM ACL | Solver seconds A061 / MM |',
             '|---|---:|---:|---:|---:|---:|']
    for family, cs in sorted(groups.items()):
        a, b = ([c[method] for c in cs] for method in ['native-branched-path','mm'])
        assert all(r['credited'] for r in a+b)
        ds = [x['acl']-y['acl'] for x,y in zip(a,b)]
        row = dict(family=family,inputs=[c['graph'] for c in cs],successes=[len(a),len(b)],
                   mean_acl=[statistics.mean(r['acl'] for r in rs) for rs in [a,b]],
                   lower_tied_higher=[sum(d<0 for d in ds),sum(d==0 for d in ds),sum(d>0 for d in ds)],
                   worst_acl_gap=max(ds),solver_seconds=[sum(r['solver_wall'] for r in rs) for rs in [a,b]],
                   across_seed_acl_variance=None)
        class_rows.append(row)
        text.append(f"| {family} | 2/2 / 2/2 | {row['mean_acl'][0]:.4f} / {row['mean_acl'][1]:.4f} | {' / '.join(map(str,row['lower_tied_higher']))} | {row['worst_acl_gap']:+.4f} | {row['solver_seconds'][0]:.3f} / {row['solver_seconds'][1]:.3f} |")
    projections['retained_fresh_classes_hyde06'] = class_rows
    (OUT/'projection.json').write_text(json.dumps(projections,indent=2,sort_keys=True)+'\n')
    (OUT/'tables.md').write_text('\n'.join(text)+'\n')
    bindings[str(Path(__file__))] = sha(Path(__file__))
    for name in ['projection.json','tables.md']: bindings[str(OUT/name)] = sha(OUT/name)
    (OUT/'manifest.json').write_text(json.dumps(dict(status='PASS',constructor_calls=0,files=bindings),indent=2)+'\n')
    print(json.dumps(dict(output=str(OUT),status='PASS',bindings=len(bindings))))


if __name__ == '__main__':
    main()
