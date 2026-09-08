"""Transfer, supervise and retrieve frozen Ember pilot runs on hyde03/04.

No benchmark starts during prepare or stage. Explicit start uses a uniquely named
persistent supervisor, so an SSH disconnect does not own the controller lifetime.
All remote writes stay below /home/dabh/ember-codex. Existing project environments,
SSH masters and unrelated services are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


REMOTE_ROOT = '/home/dabh/ember-codex'
HERE = Path(__file__).absolute().parent


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def safe_name(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,90}', value):
        raise ValueError('run names must be 1–91 simple filename characters')
    return value


def relative_path(value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Unsafe relative path: {value}')
    return path


# Only these fixed project operations execute remotely; arbitrary commands are
# not accepted from the CLI. Paths, actions and arguments arrive as JSON.
REMOTE_HELPER = r'''
import fcntl,hashlib,json,math,os,pathlib,platform,shlex,shutil,subprocess,sys,time
a=json.loads(sys.argv[1]); base=pathlib.Path('/home/dabh/ember-codex')
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def output(v):print(json.dumps(v,sort_keys=True),flush=True)
def checked(argv,**kw):
 kw.setdefault('stdout',sys.stderr);kw.setdefault('stderr',sys.stderr)
 return subprocess.run(argv,check=True,**kw)
def save(path,value):
 tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
 tmp.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');os.replace(tmp,path)
def verify(root):
 t=json.loads((root/'transport.json').read_text())
 if digest(t['files'])!=t['input_digest']:raise RuntimeError('Transport identity mismatch')
 for rel,expected in t['files'].items():
  p=pathlib.Path(rel)
  if p.is_absolute() or '..' in p.parts:raise RuntimeError('Unsafe transport path')
  if hashlib.sha256((root/p).read_bytes()).hexdigest()!=expected:raise RuntimeError('Input changed: '+rel)
 return t
def lock_busy(run):
 p=run/'controller.lock'
 if not p.exists():return False
 with p.open('r') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return True
 return False
def unit_for(run):return 'ember-codex-'+digest(str(run))[:20]+'.service'
def session_for(run):return 'ember-codex-'+digest(str(run))[:20]
def state(run):
 unit=unit_for(run)
 p=subprocess.run(['systemctl','--user','show',unit,'--property=ActiveState,SubState,Result,MainPID'],text=True,capture_output=True)
 service=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
 m=json.loads((run/'manifest.json').read_text())
 statuses={}
 for task_id in m['tasks']:
  path=run/'results'/(task_id+'.json')
  if path.exists():
   r=json.loads(path.read_text());task=json.loads((run/'tasks'/(task_id+'.json')).read_text())
   if not r.get('controller_finalized') or not r.get('status') or any(r.get(k)!=v for k,v in task.items()):
    raise RuntimeError('Invalid terminal result: '+task_id)
   s=r['status'];statuses[s]=statuses.get(s,0)+1
 tmux=bool(shutil.which('tmux')) and subprocess.run(['tmux','-L','ember-codex','has-session','-t',session_for(run)],capture_output=True).returncode==0
 return {'host':platform.node(),'run':str(run),'unit':unit,'service':service,'tmux_running':tmux,'lock_busy':lock_busy(run),
         'planned':len(m['tasks']),'finalized':sum(statuses.values()),'statuses':statuses,
         'controller':json.loads((run/'controller.json').read_text()) if (run/'controller.json').exists() else None,
         'active_record':json.loads((run/'active.json').read_text()) if (run/'active.json').exists() else None,
         'supervision':json.loads((run/'supervision.json').read_text()) if (run/'supervision.json').exists() else None,
         'supervisor_exit':(run/'supervisor-exit.txt').read_text().strip() if (run/'supervisor-exit.txt').exists() else None,
         'load':os.getloadavg()}
action=a['action']
if action=='bootstrap':
 directory=base/'bootstrap';directory.mkdir(parents=True,exist_ok=True)
 output({'path':str(directory/a['filename'])})
elif action=='prepare':
 python=a['python']
 if not python.startswith('/usr/bin/python3'):raise RuntimeError('Use an explicit system Python executable')
 version=subprocess.check_output([python,'-I','-c','import platform;print(platform.python_version())'],text=True).strip()
 wheel=base/'bootstrap'/a['bootstrap_filename']
 if hashlib.sha256(wheel.read_bytes()).hexdigest()!=a['bootstrap_sha256']:raise RuntimeError('Bootstrap wheel mismatch')
 spec={'python':python,'version':version,'machine':platform.machine(),'native':a['native'],'mm':a['mm'],
       'bootstrap_sha256':a['bootstrap_sha256']}
 envroot=base/'envs'/digest(spec)[:16];envroot.mkdir(parents=True,exist_ok=True)
 with (envroot/'prepare.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for label in ('native','mm'):
   req=envroot/(label+'-requirements.txt');req.write_text(spec[label])
   env=envroot/label; exe=env/'bin/python'
   if not exe.exists():checked([python,'-m','venv','--without-pip',str(env)])
   if subprocess.run([str(exe),'-I','-c','import pip'],capture_output=True).returncode:
    bootstrap="import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('pip',run_name='__main__')"
    checked([str(exe),'-I','-c',bootstrap,str(wheel),'--isolated','install','--no-index',str(wheel)])
   checked([str(exe),'-m','pip','--isolated','install','--disable-pip-version-check','--no-input',
            '--cache-dir',str(base/'cache/pip'),'-r',str(req)],stdout=sys.stderr,stderr=sys.stderr)
   probe="import importlib.metadata as m,importlib.util,json,sys;import networkx,numpy,scipy,numba,dwave_networkx;print(json.dumps({'executable':sys.executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix,'python':sys.version,'versions':{d.metadata['Name']:d.version for d in m.distributions()},'minorminer_present':importlib.util.find_spec('minorminer') is not None}))"
   record=json.loads(subprocess.check_output([str(exe),'-I','-c',probe],text=True))
   if record['minorminer_present']!=(label=='mm'):raise RuntimeError('Environment separation failed')
   for line in spec[label].splitlines():
    if line and not line.startswith('#'):
     name,want=line.split('==');actual=subprocess.check_output([str(exe),'-I','-c','import importlib.metadata,sys;print(importlib.metadata.version(sys.argv[1]))',name],text=True).strip()
     if actual!=want:raise RuntimeError('Pinned package mismatch: '+name)
   save(envroot/(label+'-environment.json'),record)
  save(envroot/'environment-spec.json',spec)
 output({'environment_root':str(envroot),'candidate_python':str(envroot/'native/bin/python'),
         'mm_python':str(envroot/'mm/bin/python'),'python_version':version})
elif action=='stage_prepare':
 run=base/'runs'/a['name'];incoming=base/'incoming'/(a['name']+'-'+a['input_digest'][:16])
 if run.exists():
  t=verify(run)
  if t['input_digest']!=a['input_digest']:raise RuntimeError('Run name already contains different immutable inputs')
  output({'already_staged':True,'run':str(run)})
 else:
  incoming.mkdir(parents=True,exist_ok=True);output({'already_staged':False,'incoming':str(incoming)})
elif action=='stage_finish':
 incoming=base/'incoming'/(a['name']+'-'+a['input_digest'][:16]);run=base/'runs'/a['name'];t=verify(incoming)
 if t['input_digest']!=a['input_digest']:raise RuntimeError('Unexpected incoming bundle')
 m=json.loads((incoming/'manifest.json').read_text())
 for key in ('candidate_python','mm_python'):
  p=pathlib.Path(m[key])
  if not p.is_relative_to(base/'envs') or not p.is_file():raise RuntimeError('Prepare and freeze a project environment first: '+str(p))
 for name in ('results','worker_results','claims','logs','jit_cache'):(incoming/name).mkdir(exist_ok=True)
 run.parent.mkdir(parents=True,exist_ok=True)
 if run.exists():
  if verify(run)['input_digest']!=t['input_digest']:raise RuntimeError('Run name collision')
 else:incoming.rename(run)
 output({'run':str(run),'input_digest':t['input_digest']})
elif action in ('start','status','inventory'):
 run=base/'runs'/a['name'];verify(run);s=state(run)
 if action=='status':output(s)
 elif action=='start':
  if s['service'].get('ActiveState') in ('active','activating','deactivating') or s['tmux_running'] or s['lock_busy']:
   output(dict(s,launch='already_running'))
  elif s['finalized']==s['planned']:
   output(dict(s,launch='already_finished'))
  else:
   m=json.loads((run/'manifest.json').read_text())
   lifetime=300+sum(json.loads((run/'tasks'/(tid+'.json')).read_text())['timeout']+30 for tid in m['tasks'])
   unit=s['unit'];log=str(run/'supervisor.log')
   controller=[m['candidate_python'],'-I',str(run/'source/scripts/codex/pilot.py'),'run',str(run)]
   linger=subprocess.run(['loginctl','show-user','dabh','--property=Linger','--value'],text=True,capture_output=True).stdout.strip()
   if linger=='yes':
    mode='user-systemd'
    cmd=['systemd-run','--user','--collect','--unit='+unit,'--description=Ember Codex '+a['name'],
         '--property=WorkingDirectory='+str(run),'--property=StandardOutput=append:'+log,
         '--property=StandardError=append:'+log,'--property=KillMode=control-group',
         '--property=RuntimeMaxSec='+str(math.ceil(lifetime)),'--property=TimeoutStopSec=5',
         '--setenv=PYTHONNOUSERSITE=1']+controller
   else:
    kill_policy=subprocess.run(['busctl','get-property','org.freedesktop.login1','/org/freedesktop/login1',
                                'org.freedesktop.login1.Manager','KillUserProcesses'],text=True,capture_output=True).stdout.strip()
    if not shutil.which('tmux') or not shutil.which('timeout') or kill_policy!='b false':
     raise RuntimeError('No verified logout-persistent supervisor: require linger or tmux with KillUserProcesses=false')
    mode='tmux-with-timeout'
    bounded=['env','PYTHONNOUSERSITE=1','timeout','--signal=TERM','--kill-after=5s',str(math.ceil(lifetime))]+controller
    shell='cd '+shlex.quote(str(run))+' && '+shlex.join(bounded)+' >> '+shlex.quote(log)+' 2>&1; ember_exit=$?; printf "%s\\n" "$ember_exit" > '+shlex.quote(str(run/'supervisor-exit.txt'))+'; exit "$ember_exit"'
    cmd=['tmux','-L','ember-codex','-f','/dev/null','new-session','-d','-s',session_for(run),shlex.join(['bash','-c',shell])]
   save(run/'supervision.json',{'mode':mode,'command':cmd,'host':platform.node(),'started':time.time(),
                               'maximum_seconds':math.ceil(lifetime)})
   checked(cmd,stdout=sys.stderr,stderr=sys.stderr)
   output(dict(state(run),launch='started',supervisor=mode,maximum_service_seconds=math.ceil(lifetime)))
 else:
  if s['lock_busy'] or s['tmux_running'] or s['service'].get('ActiveState') in ('active','activating','deactivating'):
   raise RuntimeError('Retrieval waits for a quiescent run; use status while it is active')
  files={}
  for p in run.rglob('*'):
   if p.is_symlink():raise RuntimeError('Unexpected symlink in run: '+str(p))
   if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.nbc','.nbi'):
    files[str(p.relative_to(run))]=hashlib.sha256(p.read_bytes()).hexdigest()
  output({'run':str(run),'files':files,'artifact_digest':digest(files),'state':s})
else:raise RuntimeError('Unknown action')
'''


class SSH:
    def __init__(self, host):
        self.host = host + '.dabh.io'
        # macOS's default per-user temporary path exceeds its 104-byte Unix
        # socket limit after OpenSSH expands %C. Keep this private namespace short.
        self.temp = tempfile.TemporaryDirectory(prefix='ember-codex-ssh-', dir='/tmp')
        self.config = Path(self.temp.name) / 'config'
        # A fresh config and control-path namespace apply to the jump connection
        # as well as the destination. No user's multiplexing settings are inherited.
        self.config.write_text(
            'Host *\n  User dabh\n  BatchMode yes\n  ConnectTimeout 12\n'
            '  ConnectionAttempts 1\n  ServerAliveInterval 15\n  ServerAliveCountMax 2\n'
            '  ForwardAgent no\n  StrictHostKeyChecking yes\n  ControlMaster no\n'
            f'  ControlPath {self.temp.name}/%C\n'
            'Host hyde03.dabh.io hyde04.dabh.io\n  ProxyJump dabh@hyde01.dabh.io\n'
        )
        self.command = ['ssh', '-F', str(self.config)]

    def remote(self, action, **kwargs):
        command = shlex.join(['python3', '-c', REMOTE_HELPER, json.dumps(dict(action=action, **kwargs))])
        result = subprocess.run(self.command + [self.host, command], text=True, stdout=subprocess.PIPE)
        if result.returncode:
            raise RuntimeError(f'Remote {action} failed on {self.host} (exit {result.returncode}); see remote stderr')
        return json.loads(result.stdout)

    def transfer(self, source, destination):
        subprocess.run(['rsync', '-a', '--checksum', '--partial', '--exclude=__pycache__/',
                        '--exclude=*.nbc', '--exclude=*.nbi', '-e', shlex.join(self.command),
                        source, destination], check=True)


def build_bundle(run, destination):
    inputs = {}

    def read_input(relative):
        if relative not in inputs:
            parts = relative_path(relative).parts
            if any(run.joinpath(*parts[:index]).is_symlink() for index in range(1, len(parts) + 1)):
                raise ValueError('Symlinks are not immutable run inputs: ' + relative)
            inputs[relative] = (run / relative).read_bytes()
        return inputs[relative]

    manifest = json.loads(read_input('manifest.json'))
    if manifest.get('format_version') != 2:
        raise ValueError('Only frozen version-2 pilot runs can be transferred')
    if len(manifest['tasks']) != len(set(manifest['tasks'])):
        raise ValueError('Duplicate task IDs')
    if digest(manifest['source_files']) != manifest['source_snapshot']:
        raise ValueError('Source snapshot identity mismatch')
    if any((run / name).exists() and any((run / name).iterdir())
           for name in ('results', 'worker_results', 'claims')):
        raise ValueError('Stage a fresh run; do not silently repeat an already attempted local experiment')
    for relative, expected in manifest['source_files'].items():
        path = Path('source') / relative_path(relative)
        if hashlib.sha256(read_input(str(path))).hexdigest() != expected:
            raise ValueError(f'Source changed: {relative}')
    target = json.loads(read_input('target.json'))
    if digest(target) != manifest['target_hash']:
        raise ValueError('Target changed')
    for task_id in manifest['tasks']:
        safe_name(task_id)
        path = 'tasks/' + task_id + '.json'
        task = json.loads(read_input(path))
        if task.get('task_id') != task_id or digest({k: v for k, v in task.items() if k != 'task_id'})[:24] != task_id:
            raise ValueError('Task identity mismatch: ' + task_id)
        if task['source_snapshot'] != manifest['source_snapshot'] or task['target_hash'] != manifest['target_hash']:
            raise ValueError('Task provenance mismatch: ' + task_id)
        graph = 'graphs/' + safe_name(task['graph']) + '.json'
        if digest(json.loads(read_input(graph))) != task['source_hash']:
            raise ValueError('Graph changed: ' + task['graph'])
    hashes = {}
    for relative, data in sorted(inputs.items()):
        target_path = destination / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    transport = {'files': hashes, 'input_digest': digest(hashes), 'local_run_name': run.name,
                 'launcher_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (destination / 'transport.json').write_text(json.dumps(transport, sort_keys=True, indent=2) + '\n')
    return transport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=('hyde03', 'hyde04'), default='hyde03')
    sub = parser.add_subparsers(dest='action', required=True)
    prep = sub.add_parser('prepare', help='create isolated, pinned native/MM environments; no benchmark')
    prep.add_argument('--python', default='/usr/bin/python3.10')
    stage = sub.add_parser('stage', help='transfer fresh frozen inputs; no benchmark')
    stage.add_argument('run', type=Path)
    for name in ('start', 'status'):
        command = sub.add_parser(name)
        command.add_argument('name', type=safe_name)
    fetch = sub.add_parser('fetch', help='retrieve and hash-verify a quiescent run, including failed runs')
    fetch.add_argument('name', type=safe_name)
    fetch.add_argument('destination', type=Path)
    args = parser.parse_args()
    ssh = SSH(args.host)
    if args.action == 'prepare':
        import ensurepip

        native = (HERE / 'requirements-native.txt').read_text()
        mm = native.rstrip() + '\nminorminer==0.2.22\ndwave-graphs==1.0.0\nfasteners==0.20\nhomebase==1.0.1\n'
        wheel = next(iter(sorted((Path(ensurepip.__file__).parent / '_bundled').glob('pip-*.whl'))), None)
        if wheel is None:
            raise RuntimeError('This interpreter must supply an ensurepip bundled pip wheel for isolated bootstrap')
        target = ssh.remote('bootstrap', filename=wheel.name)
        ssh.transfer(str(wheel), ssh.host + ':' + target['path'])
        result = ssh.remote('prepare', python=args.python, native=native, mm=mm,
                            bootstrap_filename=wheel.name,
                            bootstrap_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest())
    elif args.action == 'stage':
        run = args.run.resolve()
        name = safe_name(run.name)
        with tempfile.TemporaryDirectory(prefix='ember-codex-bundle-') as temporary:
            bundle = Path(temporary)
            transport = build_bundle(run, bundle)
            result = ssh.remote('stage_prepare', name=name, input_digest=transport['input_digest'])
            if not result['already_staged']:
                ssh.transfer(str(bundle) + '/', ssh.host + ':' + result['incoming'] + '/')
                result = ssh.remote('stage_finish', name=name, input_digest=transport['input_digest'])
    elif args.action in ('start', 'status'):
        result = ssh.remote(args.action, name=args.name)
    else:
        index = ssh.remote('inventory', name=args.name)
        destination = args.destination.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        existing = destination / 'transport.json'
        if existing.exists():
            if hashlib.sha256(existing.read_bytes()).hexdigest() != index['files']['transport.json']:
                raise ValueError('Retrieval destination already contains a different run')
        ssh.transfer(ssh.host + ':' + index['run'] + '/', str(destination) + '/')
        for relative, expected in index['files'].items():
            if hashlib.sha256((destination / relative_path(relative)).read_bytes()).hexdigest() != expected:
                raise RuntimeError('Retrieved artifact mismatch: ' + relative)
        (destination / 'retrieval.json').write_text(json.dumps(index, sort_keys=True, indent=2) + '\n')
        result = {'destination': str(destination), 'verified_files': len(index['files']),
                  'artifact_digest': index['artifact_digest'], 'state': index['state']}
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError) as exc:
        raise SystemExit(str(exc)) from None
