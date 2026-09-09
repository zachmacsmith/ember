"""Record one existing cluster CLI action; observation failure never retries it."""
from pathlib import Path
import argparse
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('host', choices=['hyde02', 'hyde03', 'hyde06'])
    parser.add_argument('action', choices=['stage', 'start', 'status', 'fetch'])
    parser.add_argument('arguments', nargs='+')
    args = parser.parse_args()
    out = args.evidence.resolve(); out.mkdir(parents=True, exist_ok=False)
    argv = [str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/codex/cluster.py'),
            '--host', args.host, args.action, *args.arguments]
    start = time.time()
    (out/'invocation.json').write_text(json.dumps(dict(argv=argv, started=start), indent=2)+'\n')
    with (out/'stdout').open('x') as stdout, (out/'stderr').open('x') as stderr:
        try:
            result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr,
                                    timeout=55 if args.action == 'status' else None)
            status = dict(exit_code=result.returncode, observation_timeout=False)
        except subprocess.TimeoutExpired:
            status = dict(exit_code=None, observation_timeout=True)
    status.update(ended=time.time(), elapsed=time.time()-start)
    (out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps(dict(evidence=str(out), **status)))
    raise SystemExit(status['exit_code'] if status['exit_code'] is not None else 124)


if __name__ == '__main__':
    main()
