# Fresh cluster readiness and additional host routing

Read-only observations at 2026-09-08 approximately 05:24 UTC. All four requested
connections succeeded with fresh configuration, strict known-host checking,
no agent forwarding and no reused SSH master. Hosts02,05,06 were reached through
hyde01; no candidate/MM import, benchmark, environment preparation or remote
write occurred during these probes.

| Host | Logical CPUs | CPU model | System Python | 1-minute load | Available RAM GiB | Home free GiB | tmux found |
| --- | ---: | --- | --- | ---: | ---: | ---: | --- |
| hyde01 | 128 | AMD EPYC 75F3 32-Core Processor | 3.13.5 | 148.53 | 250.22 | 139.05 | yes |
| hyde02 | 32 | Intel(R) Xeon(R) Silver 4215R CPU @ 3.20GHz | 3.10.12 | 33.19 | 63.54 | 218.55 | yes |
| hyde05 | 32 | 13th Gen Intel(R) Core(TM) i9-13900KS | 3.13.5 | 32.01 | 31.82 | 6925.53 | no |
| hyde06 | 128 | AMD EPYC 9575F 64-Core Processor | 3.11.2 | 167.96 | 52.81 | 94.16 | yes |

All four report `Linger=no` and no existing `/home/dabh/ember-codex` environment.
Hyde05 also lacks rsync through the checked PATH. The observed loads are near
or above their logical CPU counts; this is not a claim of idle or exclusive
resources. Host clocks are not assumed synchronized: hyde05's recorded Unix
time is about27seconds behind the local observation interval. Use local
monotonic elapsed time for measurements and keep paired arms on the same host.

Hyde02 is the simplest additional environment target: its verified
`/usr/bin/python3.10` is3.10.12, and tmux, GNUtimeout and rsync are present.
The existing pinned native/MM preparation procedure can be used there without
changing candidate dependencies or the Python major/minor version. Preparation
is an infrastructure step, not an embedding run or a timing calibration.
Hyde03's already prepared environments and hyde04's separately documented
Python3.12 environments remain untouched.

The existing `scripts/codex/cluster.py` CLI previously accepted only hyde03/04.
Root extended its explicit choices to the six user-authorized nodes and applied
the same hyde01 jump rule to02through06. Effective OpenSSH configuration was
checked with `ssh -G` for every node: correct `dabh` identity, strict host keys,
no agent forwarding or inherited multiplexing, direct01and jump02through06.
These are configuration checks, not embedding tests or proof of persistence on
a newly prepared host. The default host remains hyde03.

Raw per-host scripts, stdout/stderr, inventories and status records are in
`results/codex/cluster-readiness-20260908-0524/`; the probe SHA256 is
`c5cef2b7f00aea3704925044d7280dd013ec579f507eceaa1bb89ad37df814e7`.
`ssh_route_checks.json` records all six effective routes. No existing benchmark
source freeze changes, including the exact037bytes used by038.

Next authorized infrastructure action: prepare isolated pinned native/MM
environments on hyde02 under `/home/dabh/ember-codex` using the verified
interpreter. Root will retain raw logs, the exact helper/requirement identities,
completed environment records and import separation. No benchmark is staged or
started by this preparation. Its completion and a bounded disconnect probe are
still required before using the host for a future frozen experiment.
