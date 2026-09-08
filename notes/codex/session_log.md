# Codex research session log

## 2026-09-07 — planning phase

- User requests a skeptical research plan first (`/plan`), followed by sustained
  algorithm research. Active goal records the broader objective; no success claimed.
- Formulated and communicated 12 candidate mechanisms, each with a critique, before
  reading handoff notes, paper drafts, or algorithm source. Saved in `candidates.md`.
- Starting commit: `81074562`, branch `factored`. Created requested `codex` branch.
  Sandbox initially blocked Git metadata writes; escalated branch creation succeeded.
- Pre-existing untracked paths: `.claude/` and
  `packages/ember-qc/src/ember_qc/graphs/library/.verified.json`. Existing worktrees
  under `.claude/worktrees/` are not ours and must be preserved.
- No `AGENTS.md` found in workspace or checked ancestor directories. Read `CLAUDE.md`.
  Its algorithm preferences and claimed fingerprint results are material to audit,
  not evidence of correctness; explicit user instructions take precedence.
- Three independent task briefs dispatched: (1) primary-source embedding literature
  and novelty limitations, output `literature_review.md`; (2) algorithm/call-graph and
  draft audit, output `algorithm_audit.md`; (3) benchmark/data/metric and statistical
  audit, output `benchmark_audit.md`. All are bounded read-only investigations except
  writing their assigned note. No algorithm implementations authorized by these briefs.
- Asked optional user clarification about permitted runtime tradeoff and cluster
  username/resource limits; continue planning and local inspection while pending.
- Planning edits only so far; no new algorithm or remote experiments launched.
- User prompt 2: quality first; slower candidates acceptable; SSH username `dabh`
  on all six nodes; CPU/memory available without a user-specified limit. Single
  non-portfolio algorithm required. Candidate 12 excluded and all agents informed.
  Independent-method winner selection is excluded in parallel or sequential form.
- User prompt 3 fixes initial hardware scope to ideal Zephyr Z12. Faulted hardware,
  other Zephyr sizes, Pegasus, and Chimera are deferred. Oversized library instances
  must be reported as capacity-infeasible, not hidden or scored as solver failures.
- Read-only SSH inventory used authorized username `dabh`. hyde01 reachable after
  sandbox network escalation; five remaining nodes queried through hyde01. No
  remote jobs or files created. hyde05 initial connection failed host-key checking;
  retain checking and investigate trusted existing configuration, not disable it.
- All six hosts ultimately authenticated. hyde05 had an unknown key; an authorized
  retry using `StrictHostKeyChecking=accept-new` enrolled it without allowing changed
  keys. Inventory saved in `cluster.md`; no cluster benchmarks launched.
- Local package metadata checked: Python 3.10.19, MM 0.2.22, numpy 2.2.6,
  numba 0.65.1, networkx 3.4.2, dwave-networkx 0.8.19, scipy 1.15.3,
  OR-Tools 9.15.6755. `highspy` and `pyscipopt` not found. No dependencies installed.
- Audit agents finished their assigned notes. Small existing tests reported 57
  passes; targeted in-memory probes reproduced MM fallback reachability, incomplete
  validator checks, target substitution and grouping collisions. Passing tests do
  not cover all reproduced defects. No source-code edits were made.
- Drafted plan v0; performed self-critique round 1; revised to v1. Requested bounded
  v1 reviews from algorithm and benchmark audit agents: four implementation gaps
  and five scientific validity gaps, without edits or experiments. Their challenges
  informed primary self-critique round 2. Revisions are in `plan_self_critique.md`.
- Added `joint_region_spec.md` with an exact mathematical model and self-critique.
  It was a proposed design, never an implemented or measured algorithm.
- User prompt 4 rejects IP-led construction and requires roughly MM-order runtime.
  Logged verbatim. Lead design revised to a fast bounded heuristic, provisionally
  targeting within about 10x MM end-to-end time, reported by family and scale.
  Exact model reclassified as tiny diagnostic oracle; no routine IP runtime plan.
- Requested bounded follow-up critiques from algorithm/literature agents: propose
  efficient coupled reconstruction beyond the existing greedy rebuild, preserve one
  state and constructor, critique novelty/scalability, no code or tests. Incorporated
  their findings in `contact_search_spec.md` and two additional plan checks.
- Finalized `PLAN_CODEX.md` with all four user prompts incorporated. Twelve initial
  candidates remain recorded, portfolio excluded; four research directions are
  shortlisted with individual critiques. The broader algorithm goal is unachieved.
  This phase saved plans, pseudocode and evidence, without new algorithm code.

## Logging convention for continued work

## User prompt 5 — implementation paused for plan review

An automated goal continuation began implementation after the planning checkpoint:
validation/backend fixes, an explicit native constructor, bounded contact-repair
code, regression tests and a development pilot harness. These implementation
changes remain uncommitted. The previous planning turn constituted progress, but
moving into implementation before presenting the plan for user review was premature.

The user clarified that the plan must be presented for approval or editing first.
All three implementation agents were interrupted. The local pilot controller
(PID 98936) had already completed and no longer existed; its last worker (98982)
was also checked. The pilot log reports errors rather than usable performance
results. No cluster benchmark jobs had been launched. Preserve the existing
worktree and artifacts; do not resume implementation or experiments until the
user approves or revises the plan.

The current plan is presented in the assistant response and linked in
`PLAN_CODEX.md`. This user-requested review pause supersedes autonomous continuation
of the research objective.

## Logging convention for continued work (continued)

## User prompts 6–7 — approved continuation

The user approved the presented plan and emphasized generality: the algorithm must
be a principled heuristic, not fitted to specific graphs or families. Implementation
agents resumed their bounded tasks. General graph structure and current search
state may guide moves; graph names, family labels, instance IDs and cached answers
may not choose a runtime algorithm or supply embeddings. Development comparisons
will use multiple scales and varied structures, plus separate confirmation data.

The user asked why the goal UI still showed paused. `get_goal` confirmed the actual
goal record had status `paused`. The current approved conversational work is active,
but automatic goal continuation requires the user's Resume action or `/goal resume`.
Available goal tools cannot change paused/active status; no internal UI state was
edited. OpenAI Docs skill consulted for this product question.

The failed local pilot was traced to resolving virtual-environment Python symlinks
to their base interpreter; every worker then lacked NetworkX. The harness now
preserves the executable's absolute symlink path. Original failed artifacts remain
in `results/codex/003-native-screen` and are not embedding-performance evidence.

## Logging convention for continued work (current)

After the UI question, another authoritative `get_goal` read returned `active`.
The user-facing status was corrected: no further resume command is needed. The
assistant did not change the paused/active state itself.

The second harness smoke (005) preserved virtual-environment paths but exposed
another input bug: graph serialization dropped node attributes while preserving
Zephyr `data=True` metadata. Native layout then lacked `zephyr_index`. The harness
now round-trips node/edge attributes, with a regression comparing reconstructed
Zephyr topology and coordinates. This failure is a harness error, not evidence of
algorithm success or failure. Its raw artifacts remain preserved.

Agent follow-ups: the algorithm auditor checks label/metadata/insertion-order
generality without changing the algorithm; the benchmark auditor reviews the
isolated pilot harness; the literature agent repairs remaining plot identity
grouping after completing the statistics/summary fixes.

Validation and analysis repairs were committed as `efc49090` after a combined
205-test focused suite passed. This includes strict original-target validation,
late-result accounting, graph/target/batch identity, absent-trial handling, and a
confirmed Pareto-direction correction. Existing unrelated legacy fixture failures
are documented in the respective experiment notes; no whole-suite pass is claimed.

Experiment 009 completed all 45 trials. Every returned embedding passed independent
structural revalidation; 44 were timely, and the K100 MM result was valid but late.
Native candidates made no forbidden import attempts and loaded no external embedding
libraries. On the eight common timely comparisons, native search won ACL on two
inputs and lost on six. This is development evidence, not a class-level conclusion.
Width-four refinement of packed construction showed only small gains over width
one while using more work. See the dedicated results review for exact metrics.

Next decision: retain one globally fixed native-search constructor and compare
singleton reconstruction with narrow/wider joint reconstruction. Expose existing
contact group-size/work bounds through the native adapter; add no family dispatcher.
The prespecified 011 ablation uses the same nine development inputs, two seeds and
60-second allowances, with exact frozen source and separate candidate/MM processes.
Partial-construction design is saved but deferred until the valid-Z12 quality
question is resolved. The novelty review identifies close prior art; no publication
claim is justified by the present implementation or data.

The 90-trial 011 ablation is running on hyde03 under a detached tmux supervisor.
Fresh SSH inspection confirmed 10 finalized successes and a live controller
(PID 113328). Candidate records use the isolated environment and frozen source,
with clean dependency guards. See experiment 011 for exact paths, manifest hashes,
status/retrieval commands and launch details. Follow through to quiescence, verified
retrieval, independent revalidation, and comparison before changing the algorithm
based on this experiment. The overall goal record is active; it is not achieved.

Append every new user prompt/answer verbatim to `PROMPTS_CODEX.md`. Record each
experiment's question, pre-run prediction, revision hash, config, graph/target hashes,
seeds, machine, environment, wall/CPU/memory budgets, raw artifacts, validation, result,
interpretation, and next decision under `notes/codex/experiments/`. Preserve failures
and negative results. Record agent instructions and reports here or in linked notes.

## Completed ablation and revision 016

Experiment 011 is now complete, quiescent, retrieved, and independently audited.
The 90 observations contain 88 timely successes and two late MM K100 results.
All returned embeddings are valid. Width-one joint reconstruction is the globally
fixed reference; increasing beam width worsened aggregate quality and increased
repair work. The reference still loses to MM on the six sparse inputs. Detailed
evidence is in `experiments/011_results_review.md` and the retrieved run's analysis.

Experiments 012–014 produced an outcome-independent Ember corpus selection,
bounded contact-search diagnostics, and a cold/warm runtime profile. The diagnostics
identify omitted neighboring groups and complete boundary-contact sites outside
the current free-space halo. Revision 016 records both proposed changes and their
self-critiques before implementation. New defaults preserve the old search;
separate explicit configurations test each change and their combination.
The 48 focused algorithm tests pass, including independent validity checks for
relocation beyond the old region, work/cap rollback, and omitted group coverage.

Delegated next work: literature agent runs the frozen 72-case refinement ablation
from all 18 independent native-search incumbents (requiring old-reference replay
first); algorithm auditor independently reviews revision 016; benchmark auditor
specifies an honest generalization protocol after inspecting actual generators.
Root integrates the predetermined 017 readiness selection into the pilot.
The adapter keeps all family provenance in sidecars, provides only unweighted
integer graph structure to solvers, shares tasks for exact duplicates, and checks
input/selection identity before execution and analysis. Its focused harness and
corpus suite passes 39 tests. No actual 017 corpus comparison has run yet.

A fresh goal-status read confirms `active`. The UI pause report was answered from
that backend observation; no resume command is currently needed, and no UI or
goal scheduler internals were edited. The research objective remains incomplete.

Revision 016 completed all 72 refinement calls with valid, timely outputs.
Legacy exactly reproduces all 18 prior Joint1 chain assignments. Sites alone
change no output. Round-robin groups save 19 additional qubits; both changes
save 21 (nine improvements, eight ties, one regression versus the reference).
Both changes give the lowest fixed candidate mean; the additional site benefit
is only one case, and no broad superiority follows. Preserve the honeycomb
regression. Final deadline diagnostics were then corrected without changing
search decisions; the frozen ablation predates those diagnostic-only edits.

The source/harness checkpoint is committed as `d270f2bb`; the earlier completed
diagnostics/corpus notes are committed as `af339c19`. A combined focused suite
passed 95 tests, followed by all 10 finalized independent revision-review tests
after adding helper-level deadline coverage. The local corpus adapter smoke
produced two valid outputs but a clear candidate loss on the path input.

The outcome-independent 019 screen is now running on hyde03: 34 exact solver
inputs, three globally fixed arms (MM, prior width-one joint candidate, both
revision changes), seed 0, 60 seconds each, 102 trials. Source and corpus hashes,
launch/status/retrieval commands and interpretation limits are saved in
`experiments/019_ember_readiness_screen.md`. A fresh SSH check verified controller
115997, worker 116011, busy inherited lock and one finalized success. Continue
monitoring this exact run, then retrieve after quiescence and independently
analyze every result. No current evidence satisfies the full research objective.

## Continued algorithm work after checkpoint 14eac906

The previous turn made concrete progress: revision 016 was implemented and
tested, its modest gains and regression documented, and the broader 019 screen
launched. This turn began by verifying that exact controller remained live,
with no restart. The latest automated continuation is appended verbatim to
`PROMPTS_CODEX.md`. The goal remains active and incomplete.

Parallel tasks: the benchmark auditor monitors 019 and independently reviews its
full results after quiescent retrieval; the algorithm auditor designed and tested
bounded distance-guided contact trees; the profiling agent implemented local
reuse of fixed-order contact assignments and checked exact trajectory equality.
Root developed equal-size contact rearrangements with a strict lexicographic
objective (qubits first, then actual logical-edge coupler redundancy), with its
self-critique recorded before implementation.

Revision 021 preserves all 24 before/after embeddings and proposal traces. Warm
time was 1.59% lower and cold time 1.23% higher in its small shared-host sample, so
no reliable overall speedup is claimed. The implementation removes repeated
contact computation without caching across changing orders or source graphs.

Revision 022 saved 25 additional qubits over the fixed sites/groups reference on
18 saved native incumbents: nine improvements, seven ties, two regressions.
It initially tripled measured refinement time. Revision 024 moves exact score
rejection ahead of full validation while still validating every potential
acceptance. All 54 embeddings and non-time diagnostics reproduce 022 exactly;
the redundancy arm's measured total falls 48.36→17.93 seconds, against 16.05 seconds
for its contemporaneous strict control. Independent validation-count probes
confirm the avoided work; see the detailed experiment notes and artifacts.

Revision 020's distance-guided tree builder has real local mechanism witnesses,
including a missed king-graph shortening, but cumulative 023 rejects promotion:
zero improvements, 12 ties, six regressions and 24 more qubits than its fixed control.
Thirteen of 18 calls exhaust the work allowance, versus two controls. Its code
and failure evidence are preserved. The next candidate retains greedy trees.

The 109-test focused suite passes after integrating the experimental tree API,
score-rejection optimization, native objective forwarding, and corpus runner.
Checkpoint `cdd89085` saved the initial contact-rearrangement implementation and
contact-reuse optimization; later changes and results have separate provenance.

Protocol 025 is fixed before outcomes: rerun the strict sites/groups control and
the contact-redundancy candidate on all 34 readiness inputs, same host, one seed,
60 seconds per call, after 019 finishes. MM 019 results will be a historical quality
comparison only; no new contemporaneous MM timing ratio will be claimed.

A user clarification is pending: when MM reaches the lower bound ACL 1, should
an explicitly reported optimal tie count as acceptable, or require a speed
advantage? Experiments continue independently; no answer or altered objective
is inferred from silence. The algorithm auditor is separately specifying a
general spectral initializer from source adjacency, with self-critique before
any implementation and no end-to-end experiment yet.

## Completed broad screen and next independent initialization hypothesis

Screen 019 is complete and independently checked: 102 finalized trials, 99 timely
valid successes and three MM timeouts. Each native arm succeeds on all 34 inputs;
MM succeeds in time on 31. On those 31 common timely inputs, each candidate has
eight ACL wins and 23 losses against MM. The revised candidate's common-input
mean ACL is 2.85991 versus MM's 2.96154, but that aggregate hides substantial
sparse-graph deficits and does not satisfy the across-family objective. The
revision saves 202 qubits over the previous candidate across 34 inputs, with
22 improvements, seven ties and five regressions. Runtime remains a concern;
the independent review retains both solver and process measurements and their
denominators, rather than pooling hosts or excluding inconvenient outcomes.

After verified quiescence of 019, root started the frozen 025 comparison. Fresh
SSH status verifies controller 120218 and worker 120414 are live, with 17 of 68
outputs finalized successfully. The benchmark auditor monitors this exact run.
The algorithm auditor has separately specified and implemented one bounded
source-Laplacian initializer; source-only tests are encouraging about its cost,
but no embedding-quality result exists. Root and a second agent review its
numerical behavior and integration contract before any end-to-end experiment.

A fresh goal read still reports `active`. The user was told `/goal resume` is
currently unnecessary; no claim was made to fix the UI display or its internals.
The original user question was already saved verbatim in `PROMPTS_CODEX.md`.

Spectral integration is committed as `f93f889f`, following the source-only design
checkpoint `d8385017`. Independent review found no integration blocker. Tests
verify order-to-rank semantics through complete old-trajectory replay, failure
boundaries, scheduler independence and a shared deadline. The focused suite passed
160 tests; after adding the reviewer-requested finite-approximation boundary,
the complete integration file passed 14 tests. The isolated native smoke then
passed on all three predeclared development inputs with no MM installed or
imported. No spectral superiority claim follows from those correctness checks.

The complete 026 random-versus-spectral comparison is frozen and staged on hyde03
with the same 34 readiness inputs, two fixed arms and 60 seconds each. It will
start after 025 is quiescent and retrieved. The spectral policy changes only the
single pipeline's initialization and never selects between embedding results.
Two independent bounded tasks proceed meanwhile: prepare the explicitly planned
Sudoku development supplement at box orders 2 and 3, preserving original IDs and
reserved larger orders; and specify one semantics-preserving geometric-search
speed improvement from the saved profiling evidence, before implementing it.

Experiment 025 has now completed all 68 calls with timely valid embeddings. Its
independent review finds 17 improvements, 10 regressions and seven ties for contact
rearrangements versus the fixed strict control, saving 65 total qubits. The strict
control exactly reproduces all 34 corresponding 019 embeddings. Against historical
MM quality, the candidate still has eight wins and 23 losses on 31 common timely
inputs. Root independently reran the ordinary analyzer successfully. This remains
a modest general improvement, not the requested all-class result.

After 025 quiescence and hash-verified retrieval, the benchmark auditor started
the exact staged 026 run. Fresh status confirms controller 122275, worker 122287,
the held inherited lock and live tmux supervisor. Source and protocol remain the
already frozen `f93f889f` snapshot. Later working-tree edits cannot change this run.

The Sudoku input task is complete: separate IDs 1000002 and 1000003 contain the
correct 16-vertex and 81-vertex development cell-conflict graphs. Root reran all
34 focused tests and verified the frozen bundle with the isolated interpreter.
Original manifest entries are unchanged; reserved box orders 4 and 5 remain
ungenerated. Embeddability remains unproved because no solver has run on these
supplementary inputs. Their later pilot adapter and six-trial comparison protocol
are being prepared separately, with no replacement of prior corpus records.

The geometric performance diagnosis identifies horizontal neighbor preparation
that is never used in horizontal scoring. Its measured removal ceiling is only
about 5.4% of warm layout time in the diagnostic case, so it cannot explain away
the large MM runtime gap. The algorithm auditor saved a self-critique, then began
the restricted code change and full-trajectory differential checks against a
frozen pre-edit reference. No search objective or arithmetic changes are intended.

## Third automatic continuation

The preceding goal turn made progress: spectral initialization was implemented,
reviewed, tested and launched; the complete 025 evidence was independently checked;
and corrected Sudoku development records were frozen separately. The next prompt
is appended verbatim to `PROMPTS_CODEX.md`. A fresh SSH check confirms the same
026 controller is live, with 19 of 68 results finalized successfully at that
observation. No run was restarted and the original objective remains unmet.

The bounded 028 speed change is complete. Only unused horizontal-neighbor
preparation was removed; before/after sources differ only in `field.py`.
All 12 calls are valid, timely and exactly equal in their embeddings, actual
proposal hashes and complete non-time diagnostics. The measured total solver
reductions are 7.77% warm and 3.39% cold across the three fixed sources. These
single local pairs happened to execute after-before in every pair, so drift is
not balanced; no broad speed claim follows. Root reviewed the source diff,
reran the artifact audit successfully and passed 38 additional native/spectral
integration checks after the agent's 55 proposal/brute-force tests.

The next bounded quality investigation tests the mismatch between geometric
placement score and actual physical qubit count. Its specification and critique
must precede diagnostics. It considers conversion/pruning at new proxy incumbents
within one unchanged trajectory, with one final contact repair, not multiple
initializers or selection among embedding algorithms. No production checkpoint
callback has been implemented yet. The Sudoku runner adapter is independently
under review before any supplementary embedding call.

The complete 026 comparison is retrieved and independently audited: all 68
embeddings are timely and valid. Spectral initialization saves 644 qubits versus
the fixed random control, with 23 improvements, nine regressions and two ties.
Against historical MM it still has eight wins, 21 losses and two optimal ties
on 31 common timely successes. Root reran ordinary analysis successfully and
reviewed the complete family ledger. Spectral is the single initialization for
the next development revision; every regression remains part of the evidence.
The numerical audit verifies recorded diagnostics, not residuals recomputed from
unsaved eigenvectors. No all-family or generalization claim follows.

The 030 checkpoint diagnostic preserves exact search trajectories and validates
all 150 evaluated physical states. It finds seven pre-refinement qubits of gain
on complete-40 but none on ER-80 or grid-64, at substantial conversion cost. Root
reran its independent analyzer successfully. The 64-evaluation policy is not
promoted. A new preimplementation critique instead examines direct singleton
relocation through exact common neighbor-chain boundaries and its shared-budget
cost, including length-one chains excluded by current group generation.

After 026 quiescence and retrieval, the six-trial 029 Sudoku comparison completed
on hyde03. Its independent supplementary-input audit is ongoing. Pinned
environment preparation and supervisor inspection on hyde04 proceed separately;
no global package or service change is authorized in that preparation task.

The 029 independent audit is complete; root read its full report and reran both
ordinary and independent analyses. All six outputs are timely and valid. The
spectral candidate ties MM at 25 qubits on Sudoku order 2, where the independent
contacts arm gives a better 24-qubit witness. At order 3 it uses 394 versus MM's
408. The corresponding solver-time ratios are 10.85 and 1.43. The small-input
runtime deficit and nonoptimal tie remain explicit. The resulting feasibility
witnesses do not rewrite the original supplementary input provenance.

Root prespecified and staged 032 at commit `9c01447d`: 34 original development
inputs, MM and the fixed spectral candidate, four solver seeds 0–3 and 60 seconds
per call, 272 total. The source includes the 028 speed change but neither proposed
singleton relocation nor physical checkpoint selection. The benchmark auditor
owns independent preflight and launch after the verified 029 completion/retrieval.
Repeated seeds measure preliminary stochastic variation and current same-run MM
timing; they do not create unseen source structures or support family-wide claims.

The direct singleton revision is now independently reviewed and committed as
`684a95d5`. Root ran 172 focused tests successfully, including an independent
exhaustive-site oracle over 240 vertex/objective cases across 24 small valid
minors. A pre-benchmark structural counterexample led to a documented correction:
lazy cache setup can also occur in the first scheduled extra visit when all
overlong chains exceed the target degree bound. The same budgets and fixed
constants remain. No general performance claim follows from these checks.

Root froze and launched033 locally, 68 complete pipeline calls on the original
34 readiness sources. The two globally fixed spectral arms differ only by the
direct singleton policy. Source identity is e0ba48c4636082140e4a8d7040ecb22165712a1ef0672d0dee518948ef40853b.
Controller33003 and an isolated native worker were verified live; root owns
session94745. The four-seed032 comparison remains separately active onhyde03.
Their timing populations are never pooled.

Hyde04's pinned Python3.12.3 environments are prepared and independently read
back under1111b11934b4524b. An initial pip23 bootstrap failed; the unchanged helper
succeeded using an existing local Python3.12 bundled pip24. The failed partial
environment is unused. Linger is disabled and tmux absent, so persistent
benchmark supervision there remains a separate unfinished prerequisite.

During physical-cost modeling, the algorithm auditor identified a possible
converter capacity-state error. An independent frozen-source diagnostic has now
reproduced infeasible DP assignments and a missed feasible assignment, including
an intact default-Z12 line. Physical seating still prevents overlap and reports
the miss. This is converter-only evidence: no upstream occurrence frequency or
full-pipeline ACL effect is yet established. The proposed correction and its
runtime/proof limitations are being documented before implementation;033's
frozen source remains unchanged.

At03:50UTC the backend again reported the research goal active. Root told the
user that `/goal resume` is unnecessary and that this session cannot alter the
UI's paused label. No scheduler or UI state was modified.

033completed at03:49:17UTC. Root verified controller/final-worker absence,
launch-session exit zero and68finalized SUCCESS records, then assigned the
complete independent audit. No comparison is promoted before that audit.
032remains active onhyde03; its latest121finalized records include10timeouts.

Root reviewed034and the physical cost model, and reran034's saved-artifact
verifier with an additive output filename. All source/runner hashes and the
explicit feasible nine-arm Z12 placement pass. The035correction specification
was saved and reviewed before source implementation review: a common monotone
frontier plus a complete closed-interval overlap check replaces unsafe expiration.
Its exactness claim is limited to class intervals, and state growth/runtime must
be measured against exhaustive tiny oracles before a full embedding ablation.

033's complete independent audit passed and root reran both analyzers. Direct
singleton relocation improves7inputs,ties22andregresses5, using one more qubit
overall (15060to15061). Retain the globally fixed legacy policy. The new operator
saves143qubits inside its trajectory, but ordinary reconstruction then saves471
versus615in the control; these local gains are not comparative gains. The report
preserves all changes in group coverage, equal-size moves and runtime, plus the
limits imposed by missing intermediate chain snapshots. No parameter retuning
or family selection follows.

Root's separate exhaustive converter review checked431901small interval cases
against direct occupancy enumeration, with zero assignment/cost/tie differences.
The final field source has the same whole-module AST as that frozen oracle
snapshot; only restored EOF whitespace differs. Root also passed109integration
tests and276subtests, including native, plane, spectral, contact and pilot paths.
The035physical/state/runtime audit remains required before036's newly saved
fixed-candidate full-pipeline protocol can launch.

A new design/critique considers replacing an induced star of logical vertices
with singleton chains together. For a fixed center site, bipartite matching can
assign independent leaves to distinct eligible neighboring qubits while
preserving all frozen outside contacts. The literature auditor is checking a
tiny counterexample to single-chain reductions and primary-source prior art.
No implementation, generalization or novelty claim has been made.

035's full evidence is reviewed and committed as18ab7590. Root reran its saved
artifact auditor without overwriting original measurements. Both independent
oracles and actual seating checks pass; the sixfold hard-line slowdown remains
documented. The recurrence's exact-cost claim is qualified by representability
of the existing floating-point accumulator; declared coordinate ranges satisfy
that condition, without claiming arbitrary huge-integer optimization.

036 is frozen and running locally after independent preflight. It has34calls
with the fixed spectral/legacy-singleton configuration, differing from033's
control only in corrected field.py. Root verified controller38178 and worker
38191 at04:05:48UTC; session16497 owns the launch. Source SHA is
56338bafc7038d75001fe9fd36b067f246dc13ab796a2fdd29ded59b3226f243.
The algorithm auditor prepares complete-results analysis while root monitors.
032 remains separately active onhyde03 (last report189/272 finalized).

The induced-star matching proposal overlaps directly with Solnon's local
AllDifferent subgraph filter. Its matching reduction is treated as conventional.
A tiny actual-Z12 witness confirms a joint8-to5-qubit improvement unavailable
to unilateral singleton reductions, but its group size3 does not establish
an advantage over the existing generic2–4-chain operation. The independent
review is checking that comparison on the same fixed witness without a full
embedding call or new operator implementation.

Automated goal continuation4 was appended verbatim to PROMPTS_CODEX.md. The
previous goal turn was progress: it committed the independently checked035
capacity correction, retained the negative033result and launched frozen036.
There is no repeated external blocker, and the broader goal remains unmet.

036 is complete. Root verified controller/final-worker absence and session
exit zero, then reran its full independent original-graph audit. All34new calls
succeed. Final Qties15060overall, with9wins,17ties,8losses and slightly worse
mean per-input ACL. Corrected conversion is retained globally for its proved
capacity correction, not a benchmark quality gain. All regressions and the
limits of across-run timing attribution remain in the full report.

Root reran the induced-star Z12witness exactly and independently checked the
existing generic proposer artifact:8to7Q,Rgain1,16five-qubit assignments at12
centers inside its actual final region. The corresponding matching optimum is
5Q; neither witness establishes general superiority. Root read Solnon's archived
Definition1 and accepted the prior-art overlap explicitly.

After the saved design and critiques, the literature agent was assigned only
the induced-star core and focused tests. Its fixed schedule attaches to failed
ordinary visits without added groups; the query ceiling is2048units and all
setup/maintenance/search share5% of the original global allowance. A separate
design task investigates connected multi-qubit centers, because all-singleton
blocks cannot address high-degree centers. No generalized implementation is
authorized yet.

Before any new benchmark outcome,037's unexecuted saved-incumbent draft was
superseded by a complete34-by-two native pipeline comparison using the existing
audited pilot. This avoids creating another controller and gives direct
cumulative pipeline evidence. The treatment policy/constants did not change.
Core correctness review still precedes scheduler integration, source freeze,
independent preflight and launch.
