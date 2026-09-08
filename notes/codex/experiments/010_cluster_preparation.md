# Hyde cluster preparation

Date: 2026-09-08 UTC (2026-09-07 in the user's America/Chicago timezone).
Scope: inspect hosts, prepare separate project environments, transfer immutable
pilot inputs, and supervise processes across SSH disconnection. No embedding
benchmark was launched as part of this preparation.

## Read-only inventory

Inventory was collected at approximately 01:23:49–01:23:57 UTC through
`dabh@hyde01.dabh.io` using fresh SSH configuration. Paths checked were limited
to the known embedding project locations and system tools. No shared environment
or unrelated process was modified.

| Property | hyde03 | hyde04 |
| --- | --- | --- |
| CPU | Intel Xeon w5-3435X, 32 logical CPUs | Intel Xeon w5-3435X, 32 logical CPUs |
| Process CPU affinity | 32 CPUs | 32 CPUs |
| Load averages, 1/5/15 minutes | 15.965 / 14.940 / 14.603 | 15.934 / 14.931 / 14.643 |
| RAM | approximately 62 GiB | approximately 62 GiB |
| Available memory | 26,631,064 kB | 28,757,920 kB |
| Free space on home filesystem | approximately 40.2 GiB | approximately 5.3 GiB |
| Default Python | `/usr/bin/python3`, 3.12.3 | `/usr/bin/python3`, 3.12.3 |
| Additional Python | `/usr/bin/python3.10`, 3.10.12 | no Python 3.10 found in standard executable locations |
| Detached execution tools | tmux, systemd user manager | systemd user manager; no tmux found |
| Transfer tool | rsync | rsync |
| Scheduler | Slurm clients present, but no working controller configuration | no Slurm clients found |

Both `sinfo` and the user-specific `squeue -u dabh` query failed on hyde03
because Slurm configuration/controller discovery was unavailable. Do not treat
these hosts as reserved compute allocations. Their observed loads were similar;
hyde03 was selected for its disk headroom, Python 3.10, and tmux availability.
Load and contention must still be recorded during trials. Timing comparisons
remain paired on the same host, and cannot establish isolated-machine speed.

Known project paths: `/home/dabh/ember` exists on hyde03 and is writable, but no
standard `.venv` was found there. `/data/dabh/ember` and `/data/max/ember` were
absent on hyde03. On hyde04, `/data/max/ember/.venv/bin/python` exists and reports
Python 3.12.3; it is a shared, non-writable environment and was left untouched.
`/home/dabh/ember` was absent on hyde04.

## Separate environments on hyde03

All new remote files are below `/home/dabh/ember-codex`. The prepared environments
are:

```text
/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python
/home/dabh/ember-codex/envs/4e1fb892db12754e/mm/bin/python
```

Both report Python 3.10.12. The native environment contains the exact pins from
`scripts/codex/requirements-native.txt`; `find_spec('minorminer')` is false. The
comparator environment has the same pins plus `minorminer==0.2.22`,
`dwave-graphs==1.0.0`, `fasteners==0.20`, and `homebase==1.0.1`.
Every pinned installed version was checked, and imports of NetworkX, NumPy,
SciPy, Numba, and dwave-networkx succeeded in both environments. No embedding
algorithm was called by these probes. The native pilot also retains its own
runtime prohibition on MM/busclique imports.

The environment root contains `native-requirements.txt`, `mm-requirements.txt`,
`native-environment.json`, `mm-environment.json`, and `environment-spec.json`.
The JSON records include distribution inventories, executable/prefix identity,
and interpreter version. They were read back successfully through a separate
SSH connection. The directory identity hashes the Python path/version/machine,
both requirement texts, and the bootstrap wheel hash. This is dependency-version
pinning, not a wheel-content-locked dependency supply chain; the worker records
its actual runtime versions too.

The system Python 3.10 installation lacks `ensurepip`, so normal `venv` creation
initially failed. The successful preparation uses `venv --without-pip`, verifies
and installs the local Python installation's bundled `pip-23.0.1` wheel, and then
installs the pinned dependencies into each project environment. The wheel and
pip cache remain under the project root. No system package installation, shared
environment modification, or shell profile change was made. The initial failed
attempt left an incomplete isolated directory at
`/home/dabh/ember-codex/envs/c58f3440a65c4f98/native`; it is not used by any run.

Preparation is repeatable with:

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 prepare
```

Local Python is 3.10.19 whereas the prepared remote version is 3.10.12; record
this difference instead of pooling elapsed times from different machines or
interpreters. On hyde04 the default preparation command intentionally fails
without the required Python 3.10 executable. Do not silently move to its shared
environment or change Python versions inside a frozen experiment.

## Transfer and execution commands

`scripts/codex/cluster.py` accepts only hyde03/04 and fixed project operations.
Each invocation creates a short, private SSH configuration/control-path
namespace, applies it to destination and jump-host connections, disables agent
forwarding, and preserves strict known-host verification. It does not inherit a
possibly stale user SSH master. The short `/tmp/ember-codex-ssh-*` path also avoids
macOS's Unix-socket path limit, which an initial longer temporary path exceeded.

The root agent must initialize a fresh version-2 pilot using the two remote
interpreter paths above **before freezing its manifest**. Changing interpreter
paths inside an existing frozen run is not a transfer step. For a concrete name
such as `011-development-zephyr12`, the commands are:

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 stage results/codex/011-development-zephyr12
.venv/bin/python scripts/codex/cluster.py --host hyde03 start 011-development-zephyr12
.venv/bin/python scripts/codex/cluster.py --host hyde03 status 011-development-zephyr12
.venv/bin/python scripts/codex/cluster.py --host hyde03 fetch 011-development-zephyr12 results/codex/retrieved/hyde03/011-development-zephyr12
```

These are command templates; this preparation did not stage or start that run.
Remote runs occupy `/home/dabh/ember-codex/runs/<name>`. Transfer first copies to
`/home/dabh/ember-codex/incoming/<name>-<input-digest-prefix>`, verifies every
transported input hash, and renames the verified directory into place. A
different input digest cannot reuse an existing run name. A matching staged run
is reusable without overwriting its results. Rsync can resume a partial transfer
after a network change using another fresh connection.

Only validated source files, source/target graph records, tasks, and the
manifest enter the input bundle. Source snapshot, target, graph, and task
identities are checked; symlinks in input paths are rejected; copied bytes are
the same bytes that were validated. A local run with any claim, worker result,
or terminal result cannot be staged as a fresh experiment. Mutable result,
claim, log, and JIT cache directories are created remotely. Transport adds its
own manifest and launcher source hash without changing the pilot's source
snapshot or any task input.

## Disconnection, restart, and retrieval

The hyde03 user manager reported `Linger=no`, so a persistent user-systemd
service could not be assumed. The host's logind manager reported
`KillUserProcesses=false`. Under those observed conditions the launcher uses a
project-specific tmux socket (`ember-codex`) with no user tmux configuration,
and a deterministic per-run session name. It refuses a launch without either
verified linger-enabled user-systemd or tmux/timeout with that logind policy.
It does not change logind settings.

The detached command runs the frozen controller with isolated Python startup,
`PYTHONNOUSERSITE=1`, and an overall GNU `timeout` bound of
`300 + sum(task timeout + 30)` seconds, followed by a five-second termination
grace. This outer bound is not the solver's credited time budget. The pilot
separately charges construction/repair time, uses per-task watchdogs and kernel
alarms, executes methods sequentially, and marks late outcomes as timeouts.
The controller and workers already use the inherited OS lock and pre-spawn
claims to prevent a disconnect/restart from silently rerunning an attempted
trial. Repeating `start` while a supervisor, tmux session, or worker lock remains
active returns its status; a finished run is not launched again.

The supervisor writes `supervision.json`, `supervisor.log`, and (for tmux)
`supervisor-exit.txt`. `status` checks actual supervisor/lock state and counts
only task-matching, controller-finalized terminal records. A stale `active.json`
alone is diagnostic, not proof of a running process. A computer reboot, storage
failure, or administrative process termination can still interrupt a run;
reconnecting cannot promise immunity to those events. Such attempts must remain
explicit interruptions rather than extra invisible trials.

The harmless persistence probe started at 01:34:04 UTC under the separate socket
`ember-codex-probe`. The initial SSH connection returned before a four-second
marker process finished. A new SSH connection found its valid JSON marker at:

```text
/home/dabh/ember-codex/probes/disconnect-20260908T013404Z/completed.json
```

The process completed at Unix time `1788831248.0892687`; its tmux session had
exited. This checks SSH-disconnection survival on the selected host without
running an embedding algorithm. It is not a test of a full network outage or
host reboot.

`fetch` accepts only a quiescent run, hashes all retained artifacts remotely,
transfers them, and checks every returned hash locally. Python/Numba caches are
omitted. It retains failed/interrupted outcomes and logs, and writes a local
`retrieval.json` with artifact identity and observed state. It refuses to merge
a different run into a destination that already has another transport manifest.
Do not concurrently restart a run during retrieval; any changing transferred
file causes verification failure and should be fetched again after quiescence.

## Verification and remaining limits

`tests/test_codex_cluster.py`: 14 tests passed. The checks cover immutable bundle
round trips, modified source/target/graph/task rejection, rejection of attempted
runs, symlinked ancestor rejection, helper JSON output, remote hash verification,
terminal result identity/finalization, and independent short SSH namespaces.
These tests do not execute a solver or contact remote hosts. The remote import
probes, JSON readback, and detached marker test are described separately above.

The first actual staged pilot still needs its launch, status, and retrieved
artifacts checked. Host CPU load is shared and variable. This launcher provides
provenance and interruption handling for development screens; it does not turn
a small screen into a confirmatory all-family result or supply a cluster resource
reservation. A separate plan is needed before any parallel CPU-heavy runs.
