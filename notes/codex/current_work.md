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

`032-solver-seed-replication` is complete on hyde03. All 272 calls finalized:
258 SUCCESS and 14 TIMEOUT. The benchmark auditor verified controller 125964
complete, lock free, stopped tmux and supervisor exit zero, then retrieved the
quiescent archive. All 1,450 archived file hashes pass; retrieval digest
`1cb5179aba2218de69c5f1babebe99241f1e8fe52e7bad5a3c779fdb719468a4`.
Archive: `results/codex/retrieved/hyde03/032-solver-seed-replication`.
Source `89a3e77bf1df22a7eea436e42f0bc04c81055e098d7baf78c632a76224046994`;
transport `f02da9b1a88d747f8ba37e5e834395194cc084bd79ae3b47df73d09e13d83618`.
It contains no direct singleton relocation or physical checkpoint policy.
Do not restart the completed run.

Both full analyzers pass. Root reviewed the full report and independently reran
all 272 records; the resulting report is byte-identical (SHA256
`ebbe63b6ce53e75083e863a93e8a2d80f6699466f403dce094638e86f0e65feb`). The candidate has 136/136 timely valid results; MM has
122/136 with 14 timeouts. On the 28 inputs with all four seeds timely for both,
mean ACL wins/losses/ties are 7/19/2; macro mean is 2.261286 versus MM 2.222562.
Candidate across-seed sample variance is lower on 18, higher on 8, equal on 2.
Common-seed comparisons including partially successful MM inputs give a different
macro direction; retain both populations. Fifty of 122 timely paired solver
ratios exceed 10, maximum 28.413. All 34 candidate seed-zero embeddings exactly
replay 026. These are solver replications on development inputs, not new graph
instances or proof of generalization.

036 is **complete and independently audited**. Its34 tasks use only the
fixed spectral/legacy-singleton candidate with the corrected converter. Commit
`18ab7590e1267c6281e4c8c4443fa00b73887228`, source
`56338bafc7038d75001fe9fd36b067f246dc13ab796a2fdd29ded59b3226f243`.
Root and independent preflight confirm only field.py differs from033's frozen
source, with identical target and34 source graph bytes. Preflight passed all46
source hashes per run,37 input files,34 task configurations and package absence.
Root verified completion at04:10:39UTC: controller38178 and finalworker39628
absent, session16497 exited zero, all34results finalized SUCCESS. The controller
finished at1788840602.8600562. Independent original-graph audit passed and root
reran it successfully in `036-independent-review/root_repeat`. Do not restart.
Raw launch/completion evidence is under `results/codex/036-launch`.
Run path: `results/codex/036-converter-correction-pipeline`.

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

036:9wins,17ties,8losses versus033control; total Q remains15060, while mean
per-input ACL worsens3.334421to3.335319. All34new and34old controls independently
valid/timely. All stored non-time upstream diagnostics match, but only3final
chain sets match. Constructed18509to18506, pruned15675to15680, final15060to15060;
intermediate counts are recorded diagnostics, final embeddings are validated.
Every converter/completion deficit counter is zero. Keep corrected recurrence
globally for capacity correctness, not quality or speed claims. Timing remains
across-run and materially affected even in the unchanged layout stage.

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

## Current implementation and ownership

The induced-star core, optional scheduler, native adapter and pilot arm are
implemented and independently reviewed. The disabled policy preserves the
original behavior; direct singleton relocation remains disabled globally.
Core source SHA256 is
`785a1ab9f88d8ec6454029fe648b5d62213063f17d4933bdadbef336602c965a`.
Root passed 85 focused core tests, repeated the standalone 96-case / 89,280-
assignment oracle and its 4,494 interruption checks, and verified 12 exact
pre-integration off-path replays. Root's final integration/native/contact/pilot
regression passed 110 tests, with no forbidden import attempts. This includes
27 new integration tests and one prespecified small native correctness smoke.
These are correctness checks, not evidence of benchmark improvement.

- `benchmark_audit`: 032 is complete, retrieved and fully audited; root repeated
  its independent report exactly. The 037 protocol review found no blocker.
  Await root's committed source/run freeze, then perform independent preflight
  for hyde03. No 037 task has run yet.
- `algorithm_audit`: core and scheduler reviews are complete, with no source
  changes requested. The connected multi-qubit center specification is stable
  and reviewed, but remains design only. Update the final integration-test hash
  in the review note before root commits it; no further tests are needed.
- `literature`: isolated core, 85 new core tests and 27 integration tests are
  complete and stable. No source or test edits remain assigned. The separate
  hyde04 environment is prepared, but its supervisor remains deferred.

Root owns launch, monitoring coordination, current work and session notes.
Preserve unrelated `.claude/` and graph-library `.verified.json` files. Do not
restart any completed controller or fetch a run before verified quiescence.

## Next actions

1. Freeze the tested source and initialize 037 using its saved full-pipeline
   protocol: all 34 original readiness inputs, seed zero, 60 seconds, one fixed
   control and one matching treatment. Independent preflight precedes launch.
   Use hyde03 and its existing isolated native environment. No MM outputs are
   candidate inputs and no per-input selection occurs.
2. Independently audit all 68 final records, original embeddings, Q/R, limits,
   query/cache/ordinary work and all failures. Compare within-run upstream
   diagnostics. The historical local-036 replay is a cross-platform quality
   check; exact replay is not required and no timing is pooled with it.
3. Keep 033's negative result and legacy singleton policy. A matching move's
   local savings do not establish cumulative benefit. Retain all zero-gain,
   truncated and regressing inputs. The matching reduction has conventional
   LAD prior art; novelty and generalization remain unproved.
4. Review the connected-center extension only after this bounded diagnostic.
   Continue general revisions from failure mechanisms; no family dispatcher,
   seed selection, hidden fallback or broad superiority claim is justified.

The backend goal was checked at 04:24:25 UTC and reports `active`; the user was
told `/goal resume` is currently unnecessary. No UI internals or goal scheduler
state were modified. The full research objective remains unmet.
