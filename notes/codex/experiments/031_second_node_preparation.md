# Experiment 031: second-node preparation status

Updated after independent environment readback at 2026-09-08 03:30 UTC. Scope: prepare isolated project native/MM
environments on hyde04 and inspect existing supervisor availability. No embedding,
service modification, global package installation, or SSH-master change is
authorized by this preparation task.

**Current result: hyde04 is reachable from the root execution context, and the
parent has prepared isolated environments using verified system Python 3.12.3.**
The original pip-23 bootstrap failed; its replacement using pip 24 completed with
exit code zero in root exec session `37071`, without duplicate preparation from
this subagent. The successful environment identity is `1111b11934b4524b`.
The second probe confirms `Linger=no` and no tmux, so neither existing launcher
supervisor route is currently available. No detached controller has been launched.
The successful evidence is detailed below; earlier failed attempts remain preserved.

## Initial connection failures

The subagent's fresh read-only SSH retry returned exit code 255 before reaching hyde04:

```text
ssh: Could not resolve hostname hyde01.dabh.io: nodename nor servname provided, or not known
Connection closed by UNKNOWN port 65535
```

The parent successfully reached the same jump host in its own execution context
at approximately 03:15–03:21 UTC. Therefore this failure is evidence about the
subagent's current connection attempt, not evidence that the cluster is generally
unreachable. The earlier 03:03 UTC probe failed the same way. A subsequent
escalation request was aborted and did not produce a remote result; it is not a
live preparation process. After the parent instructed a fresh ordinary retry,
the retry at approximately 03:23 UTC reproduced the DNS error. No preparation
handle or remotely created environment identity is available.

The probe uses the existing `cluster.SSH('hyde04')` helper, including a fresh
short configuration namespace, strict known-host verification, no inherited SSH
master, and the hyde01 jump host. Its intended remote actions are read-only:
machine/interpreter inventory, supervisor executable discovery, user-systemd
queries, linger status, and logind `KillUserProcesses`. None returned a result.

Raw evidence is under
[031-second-node-preparation](../../../results/codex/031-second-node-preparation):
`read_only_probe.py`, `read_only_probe.stderr`, the empty
`read_only_probe.stdout`, and `retry_status.json`. The status record includes
the probe hash, command, failure timestamp, and explicit absence of remote
execution or environment preparation.

The old [010 inventory](010_cluster_preparation.md) reported Python 3.12.3 on
hyde04, no standard Python 3.10 executable, and no tmux. Those historical facts
are not a fresh interpreter or supervisor verification. This task has not
silently selected the shared environment, changed interpreter versions inside
a frozen experiment, or inferred user-systemd persistence merely from
`systemctl` being installed.

At that point the next required action was the same probe from a working context.
The parent performed it successfully as recorded below. No detach fallback was
added or executed in response to the connection failure.

## Successful root-side inventory

The parent executed the same fresh-SSH probe successfully at
`2026-09-08T03:24:19.379516+00:00`. Raw evidence is in
[031-second-node-root-retry](../../../results/codex/031-second-node-root-retry),
separate from the preserved failed-attempt artifacts.

| Property | Observed hyde04 value |
| --- | --- |
| CPU | Intel Xeon w5-3435X, 32 logical CPUs, affinity CPUs 0–31 |
| Kernel / architecture | Linux 6.17.0-1032-oem, x86_64 |
| User | `dabh`, UID 1006 |
| Physical memory | 65,053,028 kB total; 27,269,732 kB available |
| Load, 1/5/15 minutes | 16.078 / 14.969 / 14.599 |
| Home-filesystem free bytes | 5,658,599,424 |
| Available system interpreters checked | `/usr/bin/python3`, `/usr/bin/python3.12`; both 3.12.3 |
| Existing shared environment | `/data/max/ember/.venv/bin/python`, not writable; untouched |
| Project root before preparation | `/home/dabh/ember-codex` absent |
| User-systemd query | `systemctl --user is-system-running`: return 0, `running` |
| Systemd version | 255.4-1ubuntu8.17 |
| User-manager cgroup | `/user.slice/user-1006.slice/user@1006.service` |
| SSH session cgroup | `/user.slice/user-1006.slice/session-594.scope` |
| logind policy | `KillUserProcesses`: return 0, `b false` |

`systemctl`, `systemd-run`, `loginctl`, `busctl`, `rsync`, `timeout`, `setsid`,
`nohup`, and `start-stop-daemon` were found. `tmux`, `screen`, `dtach`, `at`,
`batch`, `sbatch`, `srun`, and `daemon` were not found through the checked PATH.
This is an availability snapshot, not an installation or runtime-persistence test.

The comma-separated `loginctl --property=Linger,State,RuntimePath,Sessions`
query returned exit code zero with **empty output**. It does not establish any
of those property values. In particular, a running user manager and
`KillUserProcesses=false` do not supply the existing launcher's required
`Linger=yes` evidence for its user-systemd route. The absence of tmux prevents
its current alternate route until a supported supervisor is available.

Machine record SHA-256:
`4b7a7b1a63aaf27c7120637ed9d3a913ec16f6f6b274a8da8111ecc395b36bef`.

## Preparation and next read-only checks

The parent started the existing preparation command with the explicitly verified
interpreter, rather than the helper's unavailable Python 3.10 default:

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde04 prepare --python /usr/bin/python3.12
```

Root exec session `53998` owned that first operation. Its stdout/stderr are saved in the
root-retry artifact directory. The expected writes stay below
`/home/dabh/ember-codex`, using separate pinned native and MM environments. Final
environment paths, installed versions, and separation must come from the
completed preparation/readback, not from guessing its directory hash. Python
3.12.3 differs from hyde03's Python 3.10.12 and must be recorded in later run
manifests; timings must not be pooled across hosts/interpreters.

A second small read-only probe is prepared for the parent to execute:

```sh
.venv/bin/python results/codex/031-second-node-root-retry/supervisor_details_probe.py
```

It queries `Linger`, `State`, `RuntimePath`, and `Sessions` separately, rechecks
user-systemd and logind policy, and inspects tmux's local apt-cache candidate and
package metadata, `dpkg-deb`, installed libevent/ncurses packages, and compiler/
make/pkg-config availability. It does not refresh package indexes, download or
install packages, modify services, or start a detached process. Its syntax was
checked locally, and the parent executed it successfully at 03:26:25 UTC. Probe source
SHA-256: `6bb7397a257255afc249ded0b942c93c2e2893d4ee0ccc596ca49837b698268a`.

The results establish the limitations and a possible project-local approach
below. No such installation or fallback has been performed by this subagent.

## Python bootstrap failure and isolated retry

The first preparation exited 1 while bootstrapping pip, before installing the
pinned native requirements. Local `.venv/bin/python` supplied `pip-23.0.1`, whose
vendored code attempted to use `pkgutil.ImpImporter` under remote Python 3.12.
The raw `prepare.stderr` records the resulting `AttributeError` and failed
subprocess. The partial directory
`/home/dabh/ember-codex/envs/ed8c55fda26153d2/native` is preserved and unused.
It is not a prepared environment and must not appear in an experiment manifest.

The parent verified a local Python 3.12.4 interpreter at
`/opt/homebrew/anaconda3/bin/python3` with bundled pip 24.0, then reran the unchanged
preparation script under that interpreter:

```sh
/opt/homebrew/anaconda3/bin/python3 scripts/codex/cluster.py --host hyde04 prepare --python /usr/bin/python3.12
```

This does not change the remote system interpreter, package pins, existing
environment, or launcher source. The bootstrap wheel hash contributes to the
environment fingerprint, so the retry receives its own identity. Root exec
session `37071` completed this attempt with exit code zero; logs are
`prepare_pip24.stdout` and `prepare_pip24.stderr`. Its completion identity and
separate record readback are described below.

## Supervisor findings and project-local prerequisites

The individual-property probe completed at
`2026-09-08T03:26:25.059788+00:00`. Its raw record is
`031-second-node-root-retry/supervisor_details.json`.

| Query | Observed result |
| --- | --- |
| `loginctl show-user dabh --property=Linger --value` | `no` |
| `--property=State --value` | `active` |
| `--property=RuntimePath --value` | `/run/user/1006` |
| User-systemd | `running`, return 0 |
| `KillUserProcesses` | `b false`, return 0 |
| tmux | Not installed and not on PATH |
| dpkg-deb | `/usr/bin/dpkg-deb`, version 1.22.6 |
| C compiler / make | `/usr/bin/cc` reports GCC 13.3.0; `/usr/bin/make` present |
| pkg-config | Present, but neither libevent nor ncursesw development metadata found |

The active sessions do not establish survival after the last session disappears.
With `Linger=no`, the existing launcher's user-systemd condition is unmet.
With tmux absent, its existing tmux/timeout condition is also unmet. The logind
policy is compatible with investigating that latter route, but no harmless
disconnect probe has yet verified it on hyde04.

The local apt cache offers Ubuntu amd64 `tmux=3.4-1ubuntu0.1`, size 479838 bytes,
SHA-256 `2913e17aa61879d1f905aab6f374f153f1ece63aefba1b996e387325d1d5338d`.
Its declared runtime dependencies include libc6, libevent-core-2.1-7t64,
libsystemd0, libtinfo6, and libutempter0. The query found installed
`libevent-2.1-7t64=2.1.12-stable-9ubuntu2.1` and
`libncurses6`, `libncursesw6`, and `libtinfo6=6.4+20240113-1ubuntu2.2`.
It found **no installed libevent-core-2.1-7t64**, and libevent/ncurses development
packages were absent. The unsplit libevent package is not evidence that the
specifically required core shared library is available. libc6, libsystemd0, and
libutempter0 installation/linkage were not checked by this probe.

One bounded proposal is to download the matching distribution tmux package and
any missing runtime libraries, verify their package hashes, and extract them
with `dpkg-deb` into an immutable project directory below
`/home/dabh/ember-codex`. This would avoid package installation scripts, global
library paths, and system services. Before adopting it, complete the dependency
checks, verify executable linkage and version, add an explicitly reviewed way
for the launcher to find that project executable, and test a harmless bounded
marker across disconnect/reconnect using an isolated socket. Source compilation
would require obtaining missing development headers as well; the present
compiler alone is insufficient. These are proposals, not completed work.

Supervisor record SHA-256:
`7317e00d559acc6064fd38e1f9df37c5362e00d1ca23df03ca5df5cc740618ca`.

## Completed isolated environments

The successful preparation emits these exact paths:

```text
/home/dabh/ember-codex/envs/1111b11934b4524b/native/bin/python
/home/dabh/ember-codex/envs/1111b11934b4524b/mm/bin/python
```

Both use remote Python 3.12.3. The helper emits its final JSON only after checking
the declared package versions, required numerical imports, and MM availability
in the comparator environment and absence from the native environment. The
native package pins are unchanged from `scripts/codex/requirements-native.txt`;
the comparator adds `minorminer==0.2.22`, `dwave-graphs==1.0.0`,
`fasteners==0.20`, and `homebase==1.0.1`. No embedding was executed by these
import/version checks. The prepared environment's identity includes the
verified pip-24 bootstrap wheel hash, Python path/version, machine architecture,
and both requirement texts.

The successful completion stdout has SHA-256
`30f4b42c7250f7b58c6a7efdf3cee3c76b145b866fbc6c782b267543751621db`.
The failed `ed8c55fda26153d2` directory remains separate and unused.

The parent can retrieve the five exact environment records with the prepared
read-only helper:

```sh
.venv/bin/python results/codex/031-second-node-root-retry/retrieve_environment_records.py
```

It reads `environment-spec.json`, `native-environment.json`,
`mm-environment.json`, `native-requirements.txt`, and `mm-requirements.txt` from
the successful environment root. It verifies remote/local byte hashes,
recomputes the directory fingerprint, checks every declared installed pin,
confirms the exact interpreter/prefix identities and native/MM separation, and
preserves the records plus a `retrieval.json` verification report under
`031-second-node-root-retry/environment_records/`. Raw readback stdout/stderr
are preserved separately. The parent executed this retrieval successfully at
`2026-09-08T03:30:54.196547+00:00`.

An independent local pass over the five saved files verified every byte hash,
recomputed the full environment fingerprint, and compared installed distributions
against all 15 native and 19 comparator pins. Both inventories record pip 24.0,
Python 3.12.3, the exact project executable and prefix shown above, and base
prefix `/usr`. Native records `minorminer_present=false`; MM records true and
installed `minorminer==0.2.22`. No numeric pin or environment-separation mismatch
was found.

| Identity | SHA-256 |
| --- | --- |
| Full environment fingerprint | `1111b11934b4524bf59814019e56cac6613d99f8798e83685f6673e391152435` |
| pip-24 bootstrap wheel | `ba0d021a166865d2265246961bec0152ff124de910c5cc39f1156ce3fa7c69dc` |
| Environment specification bytes | `9138c2e0a9bc22c1fd4faa4aa4a70b9f2d9624f2fb6ab306b499efb7a4a31edc` |
| Native inventory bytes | `3212085b489a47e55f38e54702f97fc9e09ab509eef666ba7c73d2ae3327be30` |
| MM inventory bytes | `5d2cc2864b31e210369c9cafcafb8ee97e63aad5b118016c0fcfbe42bdf70fac` |

The retrieved requirement-file hashes are recorded in `environment_records/retrieval.json`.
Dependency versions are pinned, but the downloaded dependency wheels are not a
complete content-locked supply chain; only the bootstrap wheel has the explicit
content hash above. Future workers still record their installed versions.

Environment preparation and its independent readback are complete. Persistent
benchmark execution on hyde04 remains unavailable through the current launcher
until the separate supervisor work is reviewed and tested. Project-local tmux
implementation is deferred; no benchmark, service change, global installation,
linger change, or new detach fallback was performed in this task.
