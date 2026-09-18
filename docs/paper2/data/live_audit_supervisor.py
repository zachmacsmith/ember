"""Detached one-worker live-reference audit; safe to restart after interruption."""
from pathlib import Path
import datetime
import fcntl
import json
import os
import signal
import subprocess
import tempfile

signal.signal(signal.SIGHUP, signal.SIG_IGN)
root = Path('/data/max/ember')
python = str(root / '.venv/bin/python')
bench = str(root / 'docs/paper2/data/live_bench.py')
steps = [('equivalence', 'all'), ('micro', 'baseline'), ('micro', 'full'),
         ('board', 'baseline'), ('board', 'loop'), ('board', 'full'),
         ('board', 'mm'), ('fingerprint', 'full')]
commands = [(f'{suite}-{policy}', [python, bench, '--suite', suite,
             '--policy', policy, '--cold-cache']) for suite, policy in steps]
commands.append(('summary', [python, str(root / 'docs/paper2/data/live_summary.py')]))
status = Path('/tmp/ember-live-audit.status.json')
state = dict(pid=os.getpid(), pgid=os.getpgrp(), commands=commands,
             log='/tmp/ember-live-audit.log',
             started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             phase='starting', completed=[])

def save():
    with tempfile.NamedTemporaryFile(mode='w', dir='/tmp', prefix='ember-live-status-', delete=False) as stream:
        json.dump(state, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    os.replace(temporary, status)

with open('/tmp/ember-live-audit.lock', 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    save()
    try:
        for name, command in commands:
            state['phase'] = name
            state['command'] = command
            save()
            print('starting-live-stage', name, flush=True)
            subprocess.run(command, cwd=root, stdin=subprocess.DEVNULL, check=True)
            state['completed'].append(name)
            save()
        state.update(phase='complete', exit_code=0)
    except BaseException as exc:
        state.update(phase='failed', error=repr(exc), exit_code=1)
        raise
    finally:
        state['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
