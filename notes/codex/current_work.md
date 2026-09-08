# Current research checkpoint

Updated 2026-09-08 UTC. Branch `codex`; full research goal remains active and
unmet. Preserve the original scope: one general non-portfolio algorithm, no MM
or busclique inside it, ideal Z12, quality and success retained, roughly MM's
runtime range. The pending user question about optimal ACL-1 ties has no answer;
do not interpret silence as a change in the success criterion.

**Latest completed diagnostic:** 040 on hyde03, controller 143531, ran from
07:37:00.001 to 07:57:57.603 UTC. All 34 inputs and 68 phases finished with
zero exits and no phase overruns. Fresh observation verified no matching run
process, free lock, stopped tmux and supervisor exit zero. Retrieval verified
all 2,654 files, digest
`13d0e1782fa2679efe4943d7d8b846816b5a7694a5e868c83041eec4b21ac3e1`.
Never restart the completed run. The independent results audit passes, and
root's repeat reproduces all nine JSON and two CSV outputs byte for byte.
Execution manifest is
`3f6155277ba866f376427b105371bb7b8a8abc70cefe961542f5a139534e096d`;
transport is `9dfba5ece5e210c9ca932c5b4fa277e807ceafb3b67d083239c61590fdbe8865`.
See `experiments/040_launch_record.md`. The accepted results review finds
1,122 complete valid raw states and 1,088 updates: incremental conversion
24.8823 seconds versus full conversion 34.6920 seconds, but captured adopted
transitions total only 10.7990 seconds. Its predeclared per-proposal cost gate
fails on every input. All original-graph validity, provenance and accounting
checks pass; this is not final ACL or end-to-end timing evidence. Report
`experiments/040_results_review.md` has SHA256
`e3cddb1ffe4cdb29345626b03a4a4b8389807b824ffd6f0e0a7b237a414d59d5`.
Root verified its 43 review files and four references against manifest
`f3870a7dae599e70c3c02ac55d8e30453fc3678e578dbae0043bb88cc5a93bef`.

**Current implementation:** root accepted the endpoint-support specification
`03cd87e074c8632c1361b7320e2d7942e5482d00505b138909b57d510501b8eb`.
The algorithm agent implements one experimental objective while preserving
legacy behavior, with no corpus launch yet. Its proxy counterexample and prior
art limits remain explicit. The benchmark agent prepares the independent
endpoint implementation review; the algorithm agent owns its integration.

The separate read-only deletion audit is complete and root-repeated: all 34
frozen 039 control outputs are valid, and 43 individual deletions on 43 chains
are safe across 13 inputs; 21 inputs have none. Every site was checked against
the unchanged embedding; these are not 43 composed savings. Root read the full
report/code and reproduced every non-time per-input check and summary. It
verified all 43 manifest-bound artifacts. The report is
`final_deletion_audit_results.md`, SHA256
`857fb5e59c420450a4a79e1c257d33952eb54e334df6e62a72cb3eb08288454b`.
The independently reviewed deletion-closure design now has bounded isolated
module/test implementation authorized to the literature agent. It does not
change native or the endpoint comparison; integration and a full-pipeline
experiment remain separate review steps.

**Latest completed candidate comparison:** 039 on hyde03, controller 139008, finished at
06:24:51.479 UTC with all 68 records finalized SUCCESS. Root verified the
controller and last worker absent, no matching run process, free lock, stopped
tmux and supervisor exit zero. The 433-file retrieved archive has digest
`9ad6f638f60242f51f79eb4002696c7222032bb76f8ff9406198a5ec40de4ed6`.
Do not restart it. The full independent original-graph and connected-accounting
audit passes. Root repeated it with all ten JSON tables identical, then reviewed
two metadata-only corrections. The final result is 1 lower ACL, 3 higher, 28
unresolved ties and 2 optimal ties, Q 15059 to 15063 and macro ACL 3.335135306 to
3.337318882. Two local qubit savings accompany six fewer ordinary savings.
The connected policy is rejected. The lead remains the fixed spectral/contact
control. The complete report is `experiments/039_results_review.md`, SHA256
`8b7c1e662971fd3699a47b8aff32fd6aa0d97a6bc0d771dc44b6be1d8826e860`.
Root checked all 121 final review artifacts and four input references against
manifest `70eee899eadcaab8e38ab94faab9cec7897b851dac5e7a01b2e7babb3cd4e703`.

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

## Latest completed experiment: 037

037 is complete and independently audited. The fixed singleton-center matching
revision has 6 lower-ACL, 4 higher-ACL and 24 tied outputs against its own control.
All 68 calls are timely and independently valid. Total Q is 15059 to 15052;
mean per-input ACL is 3.335135306 to 3.333413590 (about -0.052%). Twenty-five
committed star moves save 38 Q, but ordinary savings fall 617 to 586. Net saving
is seven Q, all equaled by the kagome improvement; the other 33 inputs sum to
zero Q change. Do not remove any outcomes or claim a general advantage.

The original source is commit `13876c22b0576c3d41d54bffe5ec429e37f5d08c`, snapshot
`5dfc63cfb5bb2a674cb3e556e13d2b4d18a1857c7a8f296ba27cc2dd5075abc9`.
Transport `55064e25db44189b2ddd0f77d0285f17ae4de3292656b7b55e624ceffd24e2e9`.
Controller 134553 finished at 2026-09-08 05:00:08.650611 UTC; independent fresh
status verified lock free, stopped tmux and supervisor exit zero. Do not restart.
The quiescent archive is `results/codex/retrieved/hyde03/037-induced-star-pipeline`,
432 files, retrieval digest
`84aac4c4a530e3c07f78366eb35407e139d5f85fde5bcdf6b697f26d94379a25`.

Root independently reran the complete auditor. Summary, pairs, details,
initializations and historical replay are byte-identical; summary SHA256
`7199873aa92ae9c9057fa593c9e925fb586cf749d290222c8082dc68c36146df`.
All contact/cache/shared-work trace checks pass. Unsaved intermediate physical
states remain unverified; final embeddings are checked against original graphs.
Within each of all 34 pairs, saved initialization/layout/constructed/pruned
summaries match. The historical local-036 replay is cross-platform only:
33 Q ties and one lower Q, 28 exact embeddings. No historical timing ratio.

Same-run solver time ratio median is 1.000984, mean 1.031677, range
0.564246--1.698551. These broad variations include unchanged upstream work;
no speedup is established. Auxiliary search disables on 23 inputs, including
21 auxiliary-limit and two refresh-limit cases. There are 1,034 root queries,
25 certified/committed proposals, 930 exhausted no-match queries and 56 query
limits. The full report preserves every selection and scheduling outcome.
Single-seed development data do not establish across-seed or unseen-input gains.
Keep the non-star spectral/legacy-singleton configuration as the current lead;
the singleton-center operation remains an experimental mechanism, not a promoted
class-wide improvement.

## Current work and ownership

The 038 diagnostic controller completed locally at 05:46:49.789 UTC after its
05:42:33 UTC start. Root verified controller PID `60678` absent, all 34 workers
reaped, 68 atomic observations, free inherited lock and empty controller stderr.
The terminal controller SHA is
`5895509a4cd90091c25f0a342e957852f770dc12565a900de24db2b65c6255ae`;
the evidence is `results/codex/038-initial-prefix-certificates/root-terminal-observation.json`.
Do not restart this run. Both independent results analysis and root's repeats
are complete with no errors and byte-identical deterministic tables. Root read
the complete negative report and verified all 41 final review-artifact hashes.
Report SHA `a697b5aa8b918acdb4e67cde881ef28aaf16e07cd4265e06c811ec887ad1a8b5`;
review manifest `92f571a0fdce33ee65ee79c7eae583ff79b1b8d382e459a80a6a7f4599baaedc`.
039 has also terminated and been retrieved. No embedding benchmark controller
is running. The goal remains active and unmet.

Hyde02 environment preparation completed normally at approximately 05:29:58 UTC
(exec session `43604`, started 05:26:55 UTC, exit zero). The pinned preparation
used verified `/usr/bin/python3.10`. Logs are
`results/codex/cluster-readiness-20260908-0524/prepare.{stdout,stderr}`.
Independent remote readback verifies all five environment records, pinned
versions and native/MM separation. Full environment fingerprint is
`4e1fb892db12754ee8e3ea68781af5cc7d2aa62d74f20e8914eb6de8f5fd81c3`.
A single 20-second detached persistence probe completed after its launch SSH
connection closed. It used a 35-second timeout and five-second kill grace under
`/home/dabh/ember-codex/readiness/20260908-hyde02` at 05:35:08 UTC. Fresh SSH
readback found PID 167120's completion record, elapsed 20.020704 seconds, exit
zero, empty stderr and stopped tmux. This checks normal disconnect/reconnect,
not an actual Wi-Fi network switch. Do not relaunch that identity. No benchmark
is staged on hyde02.
Fresh inventory/routing evidence is
in `notes/codex/cluster_readiness_refresh.md`; only cluster host routing changed
in commit `75860aea`, with all six effective SSH routes checked.

- `algorithm_audit` completed 038 instrumentation, independent connected-core
  review and connected native/contact/pilot integration. Integration is committed
  and frozen. The agent now owns a design-only review of separate ordinary and
  auxiliary work allocation, including conditional replay and counterexamples.
  That review is accepted and committed. Its physical-line locality design is
  independently reviewed and accepted. The isolated 040 implementation and
  synthetic checks are frozen. It now owns a separate design-only critique of
  distinct endpoint support as an equal-Q refinement potential; no algorithm
  implementation or solver run belongs to that task.
- `literature` completed the connected core and its focused witnesses, integration
  critique and independent 039 local/remote preflight. Both preflight records
  pass and its final report is accepted. Its 039 connected-diagnostics helper
  is frozen and used in the completed audit. It independently verified all 153
  prepared 040 files and input mappings. Its offline line-cache review is
  complete. It now checks prior art for endpoint support/contact flexibility,
  without solver calls or implementation changes.
- `benchmark_audit` completed 037's report, the connected implementation-policy
  review and final 038 preflight. It now owns 038's complete independent results
  audit, which passes and has been root-repeated. Its report and artifact
  manifest are frozen. The independent 039 results auditor, narrative and final
  121-file review manifest are also complete, root-reviewed and frozen. Its 040
  geometry/lifecycle review is accepted. It now prepares the independent saved-
  data 040 results auditor, waiting for root's quiescent verified archive.
- Root owns protocol decisions, current work/session notes, source commits,
  connected implementation specification and any future launches/integration.

038 is specified in `notes/codex/experiments/038_initial_prefix_certificates.md`.
It freezes the 037 production bytes and all 34 inputs, seed zero. Each fresh
worker takes exactly the actual initial native prefix, before any search
proposal, then one eligible physical evaluation. One cold and one second
invocation share that worker's cache; no result selection, later checkpoint or
contact refinement occurs. Every invocation has a common 60-second deadline;
the worker watchdog is 150 seconds plus at most five seconds of kill grace.
The final diagnostic freeze passed independent source/input/environment/AST
review, seven instrumentation checks, two analyzer groups and root repeats of
eight supervision and three kernel-alarm groups. Root read the completed review
and final implementation and accepts one launch of this exact diagnostic.
Manifest `09bd7718cec3456ef5861c79f86065a582694902692c068b47240a7996f3aa3c`,
diagnostic `ec34d4e18e0fb72870e473b92669959f968288cec95bf62e2deb28bce85e9d78`.
The final prelaunch observation found all five output directories empty and no
controller attempt. Root's `results/codex/038-initial-prefix-certificates/launch.py`
started the frozen controller once at 05:42:32 UTC and recorded PID 60678;
controller startup was 05:42:33 UTC and all workers finished at 05:46:49 UTC.
Root's frozen analyzer completed with zero audit errors or nonbinding replay
mismatches: 26 VALID_NONATTAINING observations and 42 SKIPPED_OVERLOAD, zero
timely certificates. All 34 cold/second captures are comparable and agree in
saved geometry, RNG, orders and structural-state hashes; physical chain maps
exist for only the 13 eligible pairs. The independent complete audit confirms
these outcomes with zero errors and independently reconstructs four graph/
adjacency hash categories from frozen inputs. Root repeated that second auditor:
all six deterministic JSON tables are byte-identical. Root accepted the final
report and verified its artifact manifest.
The fixed initial-checkpoint policy
including its overload throttle is rejected; do not tune later checkpoint
indices or infer that skipped initial states are physically infeasible. The
termination design records this negative lesson.

The prerequisite read-only certificate audit is complete and root-repeated:
all 170 saved candidate outputs validate. Only path/cycle attain the degree
bound (two outputs in 036, eight in 032). Every degree gate passes all 34 inputs;
3,680 maximum-degree target sites make these particular relaxations vacuous
when L<=1,440. This supplies no evidence of early attainment or saved runtime.

The connected-center core is implemented, frozen and independently reviewed.
Core SHA `d58b16bdee4024e5f40d066165c17fec1e7a5193c97d31a63fa871d0b80d9473`,
test SHA `67763d5a9822c5f6d3bcd61cebae35a647602a7c0ae32bb2f65d42a5bb6f28a8`.
Root independently repeated all 43 focused tests with prohibited imports blocked;
they passed in 1.14 seconds and both hashes were unchanged. The initial root
harness failed before test collection because pytest's timeout plugin had been
disabled; its raw logs remain, and only the harness was corrected. Four separate
native-environment witnesses include actual ideal Z12, degree-22 source center,
Q 25 to 24 and center length 3 to 2 using 1,808 total units. A saved alternative
valid embedding accompanies the known one-root failure. These are mechanism
checks, not corpus quality or speed evidence. The independent oracle review
passed: 32,404 matching comparisons, 419 connected footprints, 121 strict-Q
certificates and 2,315 query/shared/cache interruption checks. Root read the
complete review and reran its verifier; summary matches except audit wall and
six deterministic JSON files match byte-for-byte. The accepted review SHA is
`18abd36b638fcb376058132a3252e6366600298df48aec7d8106fd6f1930e33d`.
Integration is now complete and root-reviewed. The author's new 36-test suite
and combined 160-test regression suite pass. Root independently repeated all
36 integration tests; hashes were unchanged and prohibited imports absent.
Eight historical off/matching replays agree exactly apart from wall fields.
The experimental mode retains one search object, the existing failed-visit
schedule, shared budgets, signed R and actual committed member-growth counts.
No default changed. The accepted review is
`notes/codex/connected_star_integration_review.md`.

The draft 039 complete-pipeline protocol compares only the global control with
the connected policy under the same work/deadline limits. Its input order is
predeclared in `results/codex/039-protocol/graph_order.json`, SHA
`8be5feff3102f38801ab32abf4efc17c9967aa22cc11b63e3969b955d01151fc`.
Evaluator-only originals, label maps, expected normalized inputs and target are
copied/hash-verified from 038: 103 files, manifest SHA
`dc7632dd7d50cb72e81360f495d5b1a98c3a2ce68121c0ba4191dbfe9fa6c145`.
The final 039 source is commit `c61c474ca7bdd2f6e455cfa67f34af72b8d537cf`,
snapshot `63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473`.
All independent local/remote gates passed and root launched once; current run
details and identities are in `experiments/039_launch_record.md`.

040 preparation history: root copied the exact 039 source (48 files), audited
evaluator inputs (103 files), and both selection ledgers into
`results/codex/040-physical-locality/prepared/`. Its 153-file map digest is
`a5ddbd44613f37ebfa63c2e4232920573775fd3727e647dedce0b968b945bdcf`.
The proposed new diagnostic observes the initial packed state and first 32
adopted layouts on every development input with spectral initialization, seed
zero. Physical line conversion is replayed offline, keeping its cost out of the
live capture trajectory. The design and independent input review are accepted.
Workers consume the canonical expected-normalized graph, preserving Ember's
source order; original JSON insertion order differs on ember_37761. Geometry
and offline phases have separate absolute 150/60-second process allowances.
Focused synthetic/tiny Z2 checks preceded the corpus run. Root
accepted the final independent geometry/offline reviews and verified all review
hashes. Diagnostic digest is
`0c68ab814eb76aea5876ec79386d1cbabd59f8a37197c688e1d12d447c412733`.
The target-environment 23-check suite and final remote preflight passed. Root
launched once on hyde03; current identities and lifecycle are recorded above.

The reviewed theory
allows several center qubits and exact singleton-leaf assignment at a fixed
footprint. The proposed implementation groups exactly identical leaf obligations
into demand classes, uses charged compact speculative-state copies and fixed
one-root/four-successor/BFS growth, and shares the existing auxiliary/visit
allowances without the singleton core's 2,048-unit per-query cap. Root's
implementation specification passed independent review, which root read in full.
The reviewed policy hash is
`41e7b0bc31d7fa44a8c2f326d0a143315b6e5f178a5e7164cc530a32919f1e99`. It includes the
known root failure, nonmonotone matching, distinct-site boundary bound and
owned-site Hall-counting caveat; none is a novelty or superiority claim.

## Next actions

1. Preserve 037's narrow, concentrated gain and four regressions. Its complete
   report and all-input table are reviewed and committed as `a658ce00`.
2. Preserve 038's independently verified negative report and frozen artifacts.
   The controller and all workers have terminated; never restart them.
3. Preserve 039's independently verified negative full-pipeline outcome and all
   unsuccessful work. Local improvements did not imply a final quality gain.
4. Preserve the accepted 040 outcome: exact saved-cache agreement, but update
   cost fails the per-proposal criterion on all inputs. Review the experimental
   endpoint implementation and isolated deletion closure before new screens.
5. Continue one general constructor/refinement pipeline. No MM or busclique
   dependency, cached competitor input, hidden fallback, per-family dispatch,
   selected seed or best-of result is allowed. Broader replication and fresh
   source instances remain necessary for any publication claim.

The backend has repeatedly reported `active`; automated continuations are
working. The user was told `/goal resume` is unnecessary. No UI internals or
goal scheduler state were modified. Preserve unrelated `.claude/` and
`packages/ember-qc/src/ember_qc/graphs/library/.verified.json`. Do not restart
completed controllers or retrieve an archive before verified quiescence.
