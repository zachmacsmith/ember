# Experiment 032: repeated solver seeds for the fixed spectral candidate

This development experiment compares the single spectral/contact candidate with
MM on all 34 original readiness structures from 017. It fixes solver seeds
`0, 1, 2, 3`, ideal Z12 and a 60-second solver deadline: 272 calls. Seed zero
provides a quality replay check after the semantics-preserving 028 optimization;
the three additional seeds expose initialization/search variability. There is
no selection of the best seed, embedding, initializer or algorithm within a
candidate call. Every trial and failure stays in the analysis.

The candidate is `native-search-joint1-contacts-spectral` with the same explicit
configuration as 026: spectral initialization, 1000 placement evaluations,
four contact passes, 512 total groups, group sizes 1–4, width one, 16 extra
boundary sites, round-robin coverage and the qubit/contact-redundancy objective.
Default shared contact work is 500000, with 50000 per group and a 512-qubit
region cap. The source includes the 028 removal of unused neighbor preparation.
It does not include the proposed direct singleton relocation or physical
checkpoint selection. MM is an isolated comparator with one call per task.

The run uses the existing isolated native and MM environments on hyde03 and the
existing disconnect-resistant tmux supervisor. Calls are sequential on this
shared host, in the runner's frozen order. Each has a fresh process and JIT
cache. Full solver wall includes first-call compilation; process wall is reported
separately. Stage the immutable source, target, inputs and trial plan before
launch. Start only after the completed 029 controller is quiescent and its archive
has been retrieved and checked. Later source edits cannot affect this snapshot.

Report per-source attempted/timely-valid counts, ACL means and sample variance
across timely successful solver seeds, all paired seed differences, and solver
and process times. Also report the count and values of failed/late/invalid trials.
An ACL mean conditioned on success is not an unconditional success-adjusted
measure. If either method fails, show the complete-case comparison separately
from each method's success-only summary. Never silently substitute a late valid
embedding. Compare seed-zero physical chain sets with 026 as a separate quality
replay check; no old timing observation enters the new paired timing analysis.

Count the shared king/frustrated-square input once in aggregates and retain its
two family memberships in the ledger. These inherited inputs remain development
data. Repeating solver seeds does not supply new source structures or independent
family samples. Sudoku stays in its separately identified supplementary study.
Four solver seeds give only a preliminary variance estimate and cannot establish
family-wide mean superiority, statistical equivalence or a stable runtime ratio.
This experiment does not consume a protected final set or alter the success
criterion for optimal ACL-one ties, which remains awaiting user clarification.

The purpose is to test repeatability and obtain contemporaneous MM timing while
the next general refinement is developed independently. No result from 032 will
trigger per-family settings or a seed-selection policy.

```sh
.venv/bin/python scripts/codex/pilot.py init results/codex/032-solver-seed-replication \
  --corpus-selection results/codex/017-corpus-readiness/selection.json \
  --methods mm,native-search-joint1-contacts-spectral --seeds 4 --timeout 60 \
  --candidate-python /home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python \
  --mm-python /home/dabh/ember-codex/envs/4e1fb892db12754e/mm/bin/python
.venv/bin/python scripts/codex/cluster.py --host hyde03 stage results/codex/032-solver-seed-replication
```

This note freezes the protocol before any 032 solver outcome. Record actual
source/transport identities and verified launch in an additive section.

## Verified preflight and launch

The independent preflight passed before launch. It recomputed all 355 immutable
input-file hashes, including 45 source files, and checked the exact Cartesian
product of 34 inputs, two methods and seeds 0–3. Every task has the specified
configuration and a 60-second solver budget. The 34 graph files, target and both
corpus selection sidecars are byte-identical to 026. The only source-map change
from 029 is omission of `scripts/codex/sudoku_supplement.py`; all remaining source
bytes match. This run contains no supplementary Sudoku inputs.

| Identity | Frozen value |
|---|---|
| Commit | `9c01447dbc8ef2249664123d1b511504b8803222` |
| Source snapshot | `89a3e77bf1df22a7eea436e42f0bc04c81055e098d7baf78c632a76224046994` |
| Transport input digest | `f02da9b1a88d747f8ba37e5e834395194cc084bd79ae3b47df73d09e13d83618` |
| Target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Readiness selection | `06c02356f8df5503b57f280ba4939c298cc05834c563a3da8a71f96fe245db98` |

A fresh SSH connection confirmed the preceding 029 run was complete with six
finalized successes, no held controller lock, stopped tmux supervision and exit
code zero. All 95 files in its retrieved archive were rechecked against retrieval
digest `eb27661c6f97ff253e30a15f77e00eb070969bb8ea83b4fe5b00b4e1111f17a9`.
A separate fresh check confirmed 032 was staged and unstarted, with no claims or
results. The launch command was:

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 start 032-solver-seed-replication
.venv/bin/python scripts/codex/cluster.py --host hyde03 status 032-solver-seed-replication
```

The exact run `/home/dabh/ember-codex/runs/032-solver-seed-replication` started at
`2026-09-08T03:21:46.368074Z` (Unix `1788837706.368074`). A subsequent connection
confirmed controller PID `125964` running and worker PID `125975` executing task
`66f17800e7dd9e7e8282aa3d`. The inherited lock was busy and tmux was running. This
first status had zero of 272 trials finalized; it establishes liveness, without
an outcome claim. The detached supervisor has a 24780-second outer limit and
executes the frozen runner under the native isolated interpreter. The inactive
systemd service fields are expected because supervision uses tmux.

Raw launch and live-status responses, plus the independently executable local
preflight and its report, are saved outside the frozen run in
`results/codex/032-launch/`. Monitor this exact supervisor without restarting;
retrieve its full archive only after verified quiescence.
