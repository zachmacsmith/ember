# Cluster inventory and execution design

Read-only checks on 2026-09-07 at approximately 19:20–19:21 UTC. User authorized
SSH as `dabh` on all nodes and use of available CPU/memory. This inventory is a
snapshot, not a performance calibration or a claim of exclusive resources.

| Host | Logical CPUs | RAM MiB | Available RAM MiB | 1-minute load | Observed execution tools |
|---|---:|---:|---:|---:|---|
| hyde01 | 128 | 515751 | 233409 | 131.56 | tmux, python3, rsync, systemctl |
| hyde02 | 32 | 128554 | 86847 | 33.16 | tmux, python3, rsync, systemctl |
| hyde03 | 32 | 63528 | 35667 | 14.64 | tmux, python3, rsync, sbatch, systemctl |
| hyde04 | 32 | 63528 | 37610 | 14.68 | python3, rsync, systemctl |
| hyde05 | 32 | 96243 | 39170 | 32.03 | python3, systemctl |
| hyde06 | 128 | 515312 | 68132 | 110.58 | tmux, python3, rsync, systemctl |

All six hosts authenticated successfully. Nodes 02–06 were reached through
`dabh@hyde01.dabh.io` using `ProxyJump`. `command -v` did not find tmux on nodes
04/05, rsync on node05, or sbatch outside node03. This does not establish that a
Slurm cluster is usable or that these tools cannot be installed. No experiments,
remote directories, environments, or worker processes were created in this phase.

The first hyde05 attempt encountered an unknown host key with batch-mode checking.
The authorized connection succeeded using `StrictHostKeyChecking=accept-new`, which
enrolled the new key while retaining rejection of changed keys. SSH added this
public key to the user's known_hosts. No host-key checking was disabled.

## Session behavior

Existing SSH configuration uses automatic multiplexing, an eight-hour persistent
master, and keepalives at 300 seconds. Jump connections emitted warnings about an
existing control socket. Do not remove or kill the user's existing shared masters.
The research runner should use a project-specific SSH configuration, including
settings for the jump host itself, rather than inheriting stale shared sockets.

An SSH connection cannot be assumed to survive a network change. The required
property is that jobs continue on the server and can be rediscovered afterward.
Keepalive settings only detect loss; they do not provide persistence.

## Planned robust execution

1. Freeze source, dependency lock, target hash, graph hashes, seeds, algorithm
   parameters and machine metadata into an immutable run manifest. Deploy to a new
   versioned remote directory; never run a mutable working tree.
2. Prefer an available scheduler after checking its configuration; otherwise use a
   remotely detached supervisor with all streams redirected and its PID/start time
   recorded. tmux is a convenience, not a required dependency. Verify persistence
   by deliberately disconnecting and reconnecting during a small pilot.
3. Give every task a stable ID derived from the manifest. Use atomic claims and
   terminal records, worker heartbeats, and a lease recovery policy that verifies
   the former worker is dead before retrying. A dropped SSH connection is not a
   reason to submit a second copy of a still-running job.
4. Save raw embeddings, statuses, diagnostics and timing per task with atomic
   replacement. Save RNG/state checkpoints for the candidate at bounded intervals.
   Preserve crash logs and attempt IDs; never count retry copies as new samples.
5. Use reconnectable SSH through hyde01 with short connection timeouts and
   keepalives. Download artifacts with resumable verified transfers; on node05,
   use available SSH/SFTP-based transfer or install rsync in the execution phase.
   Validate source/destination hashes before marking retrieval complete.
6. Pair candidate and MM runs sequentially on the same host and CPU allocation,
   randomizing order and blocking by time. Log actual CPU model, governor/frequency
   where available, affinity, thread environment, memory peak, CPU time, wall time,
   background load, and software versions. Do not pool raw times across hosts.
7. Parallelize different benchmark instances, seeds, and research variants.
   A candidate invocation remains one non-portfolio algorithm. Start with one
   worker per lightly loaded node and increase after measuring memory/CPU demand;
   user authorization for all resources does not remove timing confounding.
8. Separate JIT compilation/setup and steady-state experiments, and also report
   full end-to-end costs. Enforce external process limits and checkpoint valid
   incumbents. Distinguish timeout, OOM, crash, invalid output, and proven
   capacity-infeasibility. A hung implementation must not block the task queue.

Reproduce the inventory with SSH options `BatchMode=yes`, `ConnectTimeout=12`,
`ConnectionAttempts=1`, `ControlMaster=no`, `ControlPath=none`, `ForwardAgent=no`,
and `-J dabh@hyde01.dabh.io` for the other nodes. The inspected commands were
`hostname`, `uname -srmo`, `getconf _NPROCESSORS_ONLN`, `free -m`, `uptime`, and
`command -v` for the tools listed above.
