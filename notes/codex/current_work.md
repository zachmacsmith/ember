# Current research checkpoint

Updated 2026-09-08 UTC. Branch `codex`; full research goal remains active and
unmet. Preserve the original scope: one general non-portfolio algorithm, no MM
or busclique inside it, ideal Z12, quality and success retained, roughly MM's
runtime range. The pending user question about optimal ACL-1 ties has no answer;
do not interpret silence as a change in the success criterion.

## Latest cluster experiment

`026-corpus-spectral-initialization` completed on hyde03 and was retrieved and
independently audited. All 68 results are timely and valid. Its frozen source is
`91824466fdd3880940df0cc6d3569a461a617c3d1ae883e50425ee368952a765`.
The already frozen `029-sudoku-development-comparison` then completed all six
calls; fresh supervisor status reports complete, lock free and exit zero. Its
independent audit passes. Neither completed controller should restart.

`032-solver-seed-replication` is running on hyde03: all 34 original
readiness sources, MM and fixed spectral candidate, seeds 0–3, 272 calls and
60 seconds per call. Independent preflight passed before the 03:21:46 UTC launch;
fresh SSH status verified controller 125964, worker 125975, held lock and live
tmux. The benchmark auditor monitors this exact supervisor. Source
`89a3e77bf1df22a7eea436e42f0bc04c81055e098d7baf78c632a76224046994`;
transport `f02da9b1a88d747f8ba37e5e834395194cc084bd79ae3b47df73d09e13d83618`.
It contains no direct singleton relocation and no physical checkpoint policy.

`033-singleton-relocation-ablation` completed locally in the isolated native
environment. At 03:51:01 UTC root verified complete controller status, absent
controller33003/final worker34600, launch session94745 exit zero, and all68
finalized records reporting SUCCESS. Independent original-embedding and metric
audit passed, and root reran both ordinary and independent analyzers.
Start time was 2026-09-08 03:40:02.619 UTC. Do not restart this run. It contains all
34 readiness sources and two fixed spectral arms, differing only by direct
singleton relocation, seed zero and 60 seconds. Frozen commit
`684a95d5f00c4b36ffaab1e23983aca5d58ee0c3`, source
`e0ba48c4636082140e4a8d7040ecb22165712a1ef0672d0dee518948ef40853b`.
The 152-file local input-bundle check has digest
`e71d3c4b255301ad641703777aaef0e11b16b4acfe1359aecd48dfd4a5fc3ca8`.
Local preflight confirms the target/all source bytes match 026, the exact trial
matrix, and absence of MM/busclique in the native interpreter. No timing is
pooled between 032 and 033.

## Most recent complete evidence

033: all68outputs independently valid/timely. Direct singleton relocation has
7wins,22ties,5losses versus its contemporaneous control, and net+1Q
(15060to15061). Mean per-input ACL3.334421to3.334938; no cumulative benefit.
Retain legacy singleton policy globally. The new operator saves143Q, while
ordinary reconstruction saves471Q versus control615Q; operator-specific savings
do not establish an advantage. Group coverage and equal-size trajectories change.
Runtime median ratio1.00884 is small relative to local load variation.
Within-run layouts/constructed/pruned counts agree for all34pairs. Cross-host
026controls reproduce28/34finalchainsets and32/34Qcounts; numerical differences
are a plausible but unproved cause. No cross-host timing comparison.

019: both candidates have 34 timely valid results; MM has 31 plus three timeouts.
On the common 31 inputs, candidates win eight and lose 23 on ACL. The lower
aggregate mean hides broad sparse quality deficits and runtime problems.

025: all 68 results timely and valid. Contact rearrangements save 65 qubits versus
the fixed strict candidate, with 17 improvements, 10 regressions, seven ties.
The strict arm reproduces all 34 strict-019 embeddings exactly. Contact policy
still wins eight and loses 23 against historical MM quality. Ordinary and
independent artifact checks pass; no new MM timing comparison is available.

026: spectral improves 23 inputs, regresses on nine and ties two against its
random-initialized control, saving 644 qubits and lowering mean ACL 4.146%.
Against historical MM quality it has eight wins, 21 losses and two optimal ties
(cycle and path) on 31 common timely successes. The other three MM timeouts
remain separate. All controls exactly replay 025 chain sets. Root reran ordinary
analysis; the independent audit checks every original embedding and numerical
diagnostic consistency. No vectors/orders were retained to recompute residuals.
Carry the spectral configuration forward globally as the development candidate;
do not select initialization by input or family. One graph/seed per family is
not evidence about family means or generalization.

027: Sudoku q2/q3 records are frozen separately, with new IDs 1000002/1000003,
16/81 vertices and 56/810 edges. Root reran all 34 tests and verified the bundle.
Original entries remain unchanged; q4/q5 are reserved and ungenerated. Their
frozen input provenance says feasibility unproved. The separate 029 results
must establish any subsequent feasibility claim without rewriting those inputs.

030: 150 checkpoint conversions are valid and preserve the unchanged placement
trajectory. Choosing the smallest evaluated physical state saves seven qubits
on complete-40 before contact repair and none on the two sparse cases. Repeated
conversion adds substantial cost. Root reran the independent artifact analysis;
do not promote this 64-evaluation policy or tune its cap on these three inputs.

029: all six outputs are independently valid and timely. At Sudoku box order 2,
MM and spectral use 25 qubits, while contacts uses 24; spectral's tie is therefore
nonoptimal. At box order 3, MM uses 408, contacts 405 and spectral 394. Spectral
solver/MM ratios are 10.85 and 1.43 respectively. These are two source structures
at seed zero, kept separate from the readiness corpus. Root reran both artifact
analyzers successfully. The result archive supplies valid feasibility witnesses
without changing the frozen input sidecars.

## Parallel work and ownership

- `benchmark_audit`: 026 and 029 reviews are complete and reviewed. 032 preflight
  and launch are verified; now monitor its exact supervisor, then retrieve and
  independently audit all272 observations after quiescence. Latest03:50 update:
  121 finalized,111SUCCESS/10TIMEOUT, same controller125964/heldlock/livetmux.
- `algorithm_audit`: 028 performance change is complete and independently reviewed;
  55 proposal tests plus 38 root integration tests pass. All 12 outputs and
  trajectories match exactly, with small observed speed gains and timing caveats.
  The singleton implementation is complete and committed, with independent
  review and 172 root-run focused tests passing. A separate exhaustive oracle
  checks 240 proposer cases across 24 small minors. The physical cost model is
  complete. Now own the narrowly specified035converter correction, field.py,
  converter tests and tiny diagnostic artifacts. Root read the saved specification
  and critique before implementation review. No other pipeline change or full
  solver call is part of035.
- `literature`: 029 adapter is complete; root reviewed it, reran 103 tests and
  committed `4cad1d67`. The six-trial run completed on hyde03.
  031 is complete to environment preparation/readback: Python3.12.3, pinned
  native/MM environments under `/home/dabh/ember-codex/envs/1111b11934b4524b`.
  All five records and versions were independently verified. Linger=no and no
  tmux: supervisor work remains deferred, so no benchmark runs on hyde04.
  The independent singleton core review found no blocker. The034capacity audit
  is complete and root reran its saved-hash/physical-witness verifier successfully.
  The033independent review is complete and root reran its analyzer successfully.
  Now own the bounded induced-star relocation review: tiny exhaustively checked
  witness and targeted primary-source prior art. Root saved the new specification
  and self-critique before this task. No source edits or full embedding calls.

Review agent-owned edits before committing. The current cluster run uses its
frozen source and is unaffected by these working-tree edits. Root owns README,
session log and this checkpoint; avoid touching files while their agent edits.
Preserve unrelated `.claude/` and graph-library `.verified.json` files.

## Next actions

1. Keep033's negative cumulative result and unchanged legacy singleton policy.
   Review the induced-star joint relocation hypothesis before implementation.
   Matching decides a restricted all-singleton block problem; usefulness and
   novelty remain unproved, and scheduling/budgets are not yet implemented.
2. Review035's converter correction against the exhaustive class-assignment and
   actual-seating oracles, plus measured state growth. Root reviewed034 and the
   physical-cost model: feasible assignments are missed by the old DP while
   physical seating remains disjoint; no full-pipeline effect is established.
   A later full-pipeline correction ablation requires its own frozen specification.
   Root saved036's34call local fixed-candidate protocol, contingent on035review.
   Its quality reference is033control; across-run timing is explicitly limited.
   Keep028; no physical-checkpoint production callback is promoted.
3. Follow 032 through repeated-seed quality and timing analysis, preserving all
   failures and the distinction between solver seeds and source instances.
   Review the second-node preparation before using it for later experiments.
4. Continue general revisions from observed failure mechanisms. No source-family
   dispatcher, per-input best-of result, hidden fallback, broad superiority claim,
   or paper-success claim is justified by present evidence.

The user was told the backend goal reports `active`; `/goal resume` is currently
unnecessary. No UI internals or goal scheduler state were modified.
