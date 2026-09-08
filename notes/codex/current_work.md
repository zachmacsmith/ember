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

`032-solver-seed-replication` is frozen and staged on hyde03: all 34 original
readiness sources, MM and fixed spectral candidate, seeds 0–3, 272 calls and
60 seconds per call. The benchmark auditor owns preflight/launch and records
actual liveness in its protocol. Source
`89a3e77bf1df22a7eea436e42f0bc04c81055e098d7baf78c632a76224046994`;
transport `f02da9b1a88d747f8ba37e5e834395194cc084bd79ae3b47df73d09e13d83618`.
It contains no direct singleton relocation and no physical checkpoint policy.

## Most recent complete evidence

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

- `benchmark_audit`: 026 and 029 reviews are complete and reviewed. Now
  independently preflight and launch 032, then monitor its exact supervisor.
- `algorithm_audit`: 028 performance change is complete and independently reviewed;
  55 proposal tests plus 38 root integration tests pass. All 12 outputs and
  trajectories match exactly, with small observed speed gains and timing caveats.
  030 is complete and reviewed. Now specify direct singleton relocation using
  common neighbor-chain boundaries, including zero-excess chains under the same
  qubit/contact objective. Own `singleton_relocation_spec.md`; critique before
  implementation and explicitly account for shared work and scheduling costs.
- `literature`: 029 adapter is complete; root reviewed it, reran 103 tests and
  committed `4cad1d67`. The six-trial run completed on hyde03. Now prepare the
  pinned environments on hyde04 and inspect supervisor availability, with evidence
  under `031-second-node-preparation`. No benchmark, global package/service
  change or new supervisor fallback is authorized in that bounded task.

Review agent-owned edits before committing. The current cluster run uses its
frozen source and is unaffected by these working-tree edits. Root owns README,
session log and this checkpoint; avoid touching files while their agent edits.
Preserve unrelated `.claude/` and graph-library `.verified.json` files.

## Next actions

1. Preserve complete 026/030 evidence and develop a fixed direct singleton
   relocation experiment after reviewing its design, failure cases and budgets.
2. Keep the 028 semantics-preserving speed change. No physical-checkpoint
   production callback is justified by the completed 030 diagnostic.
3. Follow 032 through repeated-seed quality and timing analysis, preserving all
   failures and the distinction between solver seeds and source instances.
   Review the second-node preparation before using it for later experiments.
4. Continue general revisions from observed failure mechanisms. No source-family
   dispatcher, per-input best-of result, hidden fallback, broad superiority claim,
   or paper-success claim is justified by present evidence.

The user was told the backend goal reports `active`; `/goal resume` is currently
unnecessary. No UI internals or goal scheduler state were modified.
