# Codex research plan

2026-09-09 completed-cycle decision: [Transfer001 results](notes/codex/transfer_cycle_001_decision.md)
retain A061 and preserve all 198 outcomes. A063 supports a bounded scheduling
follow-up but is too costly for promotion; B027/C012 fixed policies are rejected.
Future independent tracks target A's measured root-search allocation, B's routing
cost, and a coherent replacement for C's failed frontier geometry. The decision
includes two self-critiques and retains all-class, variance, runtime and untouched
confirmation requirements.

2026-09-09 execution checkpoint: [Transfer001](notes/codex/transfer_cycle_001_launch.md)
implements the reviewed strategy with three independent complete-constructor
screens, fresh structures/sizes/relabelings and evaluator-hidden witnesses.
The [bounded B027 amendment](notes/codex/transfer_cycle_001_b027_amendment.md)
addresses measured exact neutral-state recurrence; B026 and its outcomes remain
preserved. All-class promotion and a separate untouched confirmation set remain
later requirements. A061 remains retained until complete results justify change.

2026-09-09 strategic-review amendment: the [current research decision](notes/codex/strategic_review_20260909.md)
supersedes the exploratory sequencing below. Previously running B025/C011 are
complete and preserved. Keep A061 as the whole retained policy; prioritize
physical contact mobility and coordinated construction, audit limits using
measured computation, remove the universal3× gate from future decisions, and
test fresh structures/relabelings/hidden witnesses early. Three independent
tracks continue; a coherent redesign may coordinate complementary operators
within one state. Historical frozen policies and every regression remain intact.
The amendment includes candidate critiques and two plan self-critique rounds.

2026-09-08 workflow amendment: run three independent research tracks concurrently
(inherited prototype, demand-aware connected-tree construction, multilevel region
splitting), with hypotheses and cheap falsification screens before implementation.
Reuse audited infrastructure and reserve exhaustive testing for promising changes.
See [the current workflow](notes/codex/tracks/workflow.md); this user-authorized
amendment supersedes earlier exploratory audit sequencing, while preserving all
algorithm, generality, Z12, runtime and eventual confirmation requirements.

Status: approved in user prompt 6; implementation may proceed. The user additionally
requires a general, principled heuristic with no graph- or family-specific fitting.
Prepared after two self-critique rounds and two further checks of the runtime-focused
revision requested in user prompt 4.
Research branch: `codex`, starting at `81074562`. Critiques and resulting revisions:
[`notes/codex/plan_self_critique.md`](notes/codex/plan_self_critique.md).
The original planning checkpoint contained no new algorithm implementation. A
subsequent automated continuation prematurely began uncommitted validation fixes,
an independent constructor, a local reconstruction prototype and a pilot harness.
Those changes were preserved during review and are now being checked under the
approved plan; they are not established research results.
No algorithm is claimed to outperform MM.

## 1. Independent brainstorm, before the repository audit

The following candidates were formulated before reading the prior handoff, drafts,
or algorithm source. Mechanisms are hypotheses, not established new algorithms.
Each has a pre-implementation critique and a falsifying experiment in
[`notes/codex/candidates.md`](notes/codex/candidates.md).

1. Capacity-priced Steiner routing.
2. Negotiated congestion with joint chain updates.
3. Multilevel embedding.
4. Separator-based embedding.
5. Zephyr-aware chain templates with local departures from those templates.
6. Connected-region optimization.
7. Edge-demand placement and routing.
8. Local exact repair.
9. Adaptive large-neighborhood search.
10. Tree-decomposition-guided embedding.
11. Replica-exchange search over embeddings.
12. Feature-guided algorithm portfolio — **excluded by the user's clarification**.

Candidates are independent research alternatives, not methods to combine by taking
the best output. The intended result is one non-portfolio algorithm with one
construction/refinement process and a single evolving embedding state. The
replica-exchange idea is deferred; it is unnecessary for the first implementation
and risks obscuring this distinction.

## 2. Objective and scope

Develop a publishable, independently implemented graph minor-embedding algorithm
with lower mean average chain length (ACL) than stock MinorMiner across Ember graph
families on ideal Zephyr Z12 (`zephyr_graph(12, 4)`). Quality has priority, but the
user requires runtime roughly within MM's order of magnitude. Use approximately
10x MM's measured end-to-end time as a provisional upper target, reported per family
and size regime; do not hide much slower cases behind a pooled mean. An IP-led
constructor is excluded. Tiny exact solves are diagnostic tools or, only if justified
by measured cost, tightly bounded local subroutines. Variance, maximum chain length, success rate,
memory, and runtime remain reported. Defective hardware, other Zephyr sizes,
Pegasus, and Chimera are deferred by the user's latest instruction.

Candidate execution must never invoke MM, forks of MM, busclique, MM layout helpers,
or embeddings cached from those programs. This applies to construction, completion,
initialization, fallback, repair and polishing. MM is used solely as an isolated
experimental comparator. Reimplementing established MM or clique heuristics is not
sufficient evidence of novelty. No graph-ID lookup, family-specific winner
selection, or parallel/sequential independent-method portfolio is eligible.

For nonempty source graph G, ACL = sum_v |C_v| / |V(G)|. Every source vertex,
including isolated vertices, must have a nonempty connected chain. Final chains
must be vertex-disjoint subsets of the original target and realize every source
edge. These invariants precede any quality metric.

Strict improvement is mathematically impossible where MM already achieves the
lower bound ACL=1. A finite benchmark cannot establish superiority on every possible
graph. The scientific target is demonstrated per-family improvement on a declared
evaluation distribution, with optimal ties and capacity-infeasible cases reported
explicitly. Do not silently relabel ties as wins or missing coverage as success.

Use an explicit outcome table: supported improvement; certified optimal ties on
identified instances; unresolved eligible family; proved infeasible original
instances; supplemental-only family coverage. An optimal tie on some instances
does not exempt the entire family. A tie above a proved lower bound remains
unresolved. Separate claims about the original Ember corpus from claims about a
documented extended corpus. The broad research goal remains open while eligible
families are unresolved; do not declare victory by changing these labels.

## 3. What the initial audit changes

Treat every previous result as provisional until source, raw embedding, target,
configuration, and metrics can be independently checked.

- The current `attract_embed(tail="none")` can still call MM in legalization and
  fallback. Default `tail="mm"` also polishes with MM. `mm_skipped` does not prove
  that an entire invocation was independent. Existing PSSA uses busclique.
- Existing dense/ER results motivate preserving useful structure, but the reported
  pure-engine board loses on random regular, Watts–Strogatz, grid, honeycomb, and
  king graphs. The board contains ten chosen instances, not all Ember families.
- The packed manifest contains 31,149 entries across 36 categories, with substantial
  family imbalance. Graph names, metadata duplicates, and actual graph identity are
  different concepts. Existing grouping and topology handling require audit.
- Z12 has 4,800 qubits. The two manifest Sudoku instances exceed this vertex count;
  that category has no size-eligible original instance. Preserve this limitation.
  Raw metadata has 949 entries violating vertex or edge-count necessary bounds;
  the other 30,200 entries are not thereby proved embeddable.
- Some validation paths accept extra source keys or foreign target qubits, and the
  benchmark can use an algorithm-supplied replacement target. Repair trust boundaries
  before accepting performance evidence.
- The order-based engine optimizes a restricted geometric quantity. Establish its
  relation to realized qubit count rather than accepting claims of exactness.
- The current multi-chain repair reconstructs chains greedily in sequence. A true
  simultaneous contact/assignment optimization may address a different limitation,
  but must be distinguished from published exact embedding and routing methods.

Evidence and reproduction details live in `notes/codex/algorithm_audit.md`,
`benchmark_audit.md`, and `literature_review.md`. Historical failed experiments are
leads for reproduction, not universal impossibility results or design rules.

## 4. Research shortlist

Implement no more than three or four research variants at a time. Each variant is
a complete, independently evaluated single algorithm. Promote one fixed design;
do not dispatch among variants by graph class or choose their best outputs.

### A. Geometry-guided contact search with bounded joint reconstruction

Use one inexpensive geometric construction and a fast heuristic that revises
interacting chains together. Physical qubit assignments and actual coupler contacts
are authoritative. Geometry proposes locations; it does not constrain final chains
to one cross shape. Retain a small beam of alternative local reconstructions so a
later blocked chain can cause an earlier choice to be reconsidered.

**Why prioritize it:** combines candidates 5, 6, 7 and 9 as one evolving search.
It can accept a net improvement where one chain grows by one qubit and a neighbor
shrinks by three. This tests whether coupled contacts overcome the sparse deficits
without sacrificing useful dense structure. General connected-tree proposals are
implemented independently; neither MM nor busclique is called.

**One construction/refinement process (conceptual pseudocode):**

```text
read and hash G and the original Z12 adjacency
make one reproducible geometry-guided placement at a bounded work cost
derive connected disjoint chains; record missing vertices/contacts explicitly
while the declared work and time budgets remain:
    select 2-4 interacting chains from missing contacts, long chains or blockers
    release their complete chains provisionally into a bounded free region
    retain 4-8 alternative joint reconstruction prefixes in a small beam
    grow contact-covering trees using actual added qubits and current occupancy
    backtrack within the beam when a later chain blocks an earlier choice
    check the complete local replacement against every affected obligation
    in construction, prefer fewer missing vertices/contacts then fewer qubits
    in refinement, accept valid net qubit reductions; keep a valid incumbent
    roll back failed proposals atomically; enforce all routing-work limits
independently validate the complete embedding; return it or explicit failure
```

These widths/group sizes are pilot ranges, not final tuned constants. Compare
beam width 1, 4 and 8 with identical routing primitives and equal overall budgets.
Alternative prefixes are local moves on one embedding, not independent embedding
algorithms whose outputs are selected. B/C/D remain research revisions, never
runtime fallback algorithms.

Frozen neighboring chains offer sets of possible contact qubits, not fixed
terminals. Use compact occupancy/contact data, bounded BFS or tree growth, reversible
changes and cached geometric distances; cached feasible paths must be rechecked
after occupancy changes. Cap region size, beam expansions, routing work and global
elapsed time. Do not perform an exact solve at every insertion or replacement.

**Self-critique before implementation:** beam search is generic and CMR already
includes weighted routing and some path transfer. The contribution must be a
specific efficient coupled-contact mechanism with measurable gains over the existing
greedy group rebuild and a matched single-chain ablation. Small beams can discard
the necessary coordinated move; cheap placement can lose dense quality; repeated
per-neighbor BFS and broad regions can exceed the time budget. Construction must
prove competitive early, not rely on an expensive optimizer to rescue poor starts.
No performance or novelty claim is established yet.

The concrete heuristic and its scaling pilot are specified in
[`notes/codex/contact_search_spec.md`](notes/codex/contact_search_spec.md).
The earlier exact formulation in `joint_region_spec.md` is retained as a diagnostic
oracle specification; its IP-led construction is superseded by this section.

### B. Contact-flexible extension of the existing order-based construction

Retain independently audited order/packing logic as an internal construction
primitive. Permit single-qubit and single-direction chains, end-to-end contacts,
and verified Zephyr couplers omitted by the present cross-shaped representation.
Evaluate accepted refinements on actual branch sets.

**Why investigate:** reported dense strengths may be useful; sparse losses may be
partly representational. This develops candidates 5 and 7.

**Self-critique:** adding contact choices may invalidate tractable packing or its
correctness proof. It might merely be another template method. First distinguish
optimization failure from the best attainable quality inside the old template.
Do not equate removal of an MM call with a novel contribution.

### C. Multilevel regions within the same optimizer

Use logical structure to organize large coordinated moves and physical region
allocation, with exact fine-level chains retained or reconstructable. Apply the
same region operation during expansion and refinement.

**Self-critique:** coarse feasible solutions may not expand; clusters can hide
coupler demand. This is conditional on A's local operation being useful. Reject
if coarse optimization savings do not repay expansion cost or damage success.

### D. Independently constructed congestion-based joint routing

If the bounded heuristic cannot construct useful embeddings, investigate a single
joint-routing process using approximate connected-tree proposals and conflict
prices. Compare against an independently coded simple one-chain baseline.

**Self-critique:** this is closest to CMR/MM and risks becoming a clone. It needs
a materially different coupled update, not a new schedule or wrapper. Treat it as
an alternative research line, never a hidden fallback in the chosen algorithm.

Separator and tree-decomposition methods remain deferred structural ideas; they
must earn inclusion through measured benefit inside a selected algorithm.

## 5. Work sequence and decision points

### Phase 0 — trustworthy experimental foundation

1. Save every user prompt verbatim in `PROMPTS_CODEX.md`, append decisions and
   artifacts under `notes/codex/`, and preserve the starting commit and old results.
2. Establish a fresh, pinned environment and inventory candidate/comparator call
   graphs and build dependencies. Do not overwrite other worktrees or remote jobs.
3. Add an unconditional independent validator at result ingestion and before
   candidate return. Check exact source key set, nonempty chains, duplicate chain
   entries, membership in the original target, connectivity, disjointness, and all
   source edges. Compute metrics from validated data with denominator |V(G)|.
4. Remove trust in algorithm-supplied target replacements, success flags, times,
   or certificates. Recompute validation and measure elapsed/CPU time externally.
5. Repair benchmark grouping to use immutable graph identity and complete target
   identity, replicate/run IDs and configuration hashes. Preserve embeddings and
   full-precision raw counts rather than rounded summaries alone.
6. Run meaningful regression tests for the demonstrated validation failures,
   target substitution, isolates, timeout behavior, and aggregation collisions.
7. Freeze a development manifest and define an untouched confirmatory split by
   graph identity, family, size, density and generator parameters. Isomorphic copies
   must not cross splits. Treat the **entire inherited corpus** as development,
   because previous work included full-library experiments. Confirm on newly
   generated graph structures checked against that corpus; new algorithm seeds or
   vertex relabelings are not new graph instances. For deterministic families with
   no unseen structure available, report descriptive corpus evidence and its limits.
8. Create an explicit full-corpus capacity/coverage ledger. For a family with no
   eligible original instances, inspect its definition and generator for legitimate
   smaller Z12-scale examples (for example, a smaller Sudoku encoding). Such examples
   form a separately labeled supplemental corpus with generation code and provenance;
   retain the oversized originals and state the resulting change in claim scope.

**Exit condition:** invalid outputs are rejected, metrics and IDs are unambiguous,
and reproducible candidate/comparator tasks run independently on the original Z12.

### Phase 1 — isolate and diagnose the existing independent construction

Create an explicitly MM-free entry point that fails honestly when independent
construction fails. Remove runtime dependencies from its process; block MM and
busclique imports/entrypoints, including aliases, forks and native extensions.
Exercise both successful and failing construction paths. The existing tailed method
remains an ineligible historical reference.

Run candidates in a pinned environment physically lacking MM, forks, busclique and
cached outputs; import interception supplements a source/dependency/native-load
audit. Ember currently declares MM as a dependency, so separate candidate runtime
dependencies from the comparator/controller environment explicitly. Exchange only
serialized source/target graphs, configurations, and independently produced results.
The candidate must have no access to comparator embeddings as inputs or hints.

Reproduce the small dense/sparse development cases, saving raw embeddings. Run
successive work budgets to distinguish incomplete optimization from a representation
limit. Compare proxy objective, actual total qubits, missing edges, and locality of
MM-independent repair opportunities. Use small exact examples to establish whether
the restricted representation itself prevents improvement.

**Exit condition:** a trustworthy per-family deficit table and a mechanistic
diagnosis; no historical claim is carried forward without eligibility and validation.

### Phase 2 — minimal falsifying prototypes

Implement A's bounded heuristic with exhaustive tiny cases as a correctness oracle.
Demonstrate a valid simultaneous change that improves an independently constructed
embedding where deletion-only, one-chain, and the existing greedy group repair
stall under their declared move sets. Test construction and refinement using the
same heuristic. Small exact solves may diagnose missed improvements offline; they
are not the production constructor or routine runtime repair.

Develop B only if it addresses a measured representation limitation. Test C or D
only after reviewing the previous line's failure note. Compare actual qubit count,
feasibility, memory, and total time across dense and sparse development cases;
avoid optimizing only the easiest or most dramatic example.

**Exit condition:** at least one coherent MM-free algorithm improves the diagnosed
deficit on diverse development instances with acceptable success and resource use.
Require representative end-to-end runtime approximately within 10x MM, with
family/size distributions and startup costs visible. If gains require large beams,
whole-chip search or repeated exact solves, reject that version before scaling.
If none does, record negative results, revise the mechanism, and continue research.

### Phase 3 — iterative class coverage

Expand from tiny oracles to a balanced stratified Z12 development set covering every
eligible family and multiple size/density regimes. Use at least five stochastic
seeds in screening and more for unstable near-capacity cases. Parallelize independent
experiments across the cluster. Every revision gets an explicit prediction and
falsifier, one-factor ablations where informative, and a failure diagnosis.

Maintain a family-by-family table of mean ACL, run-to-run ACL variance, within-chain
length variance, success rate, maximum chain, wall/CPU time, and peak memory. A gain
in one family cannot cancel a loss in another. Retain failed code by immutable Git
revision and linked notes; keep inactive experiments out of the chosen runtime.

### Phase 4 — freeze and confirm

Freeze a single algorithm version/configuration before opening the final holdout.
Use adequate graph-level replication and seed counts determined from pilot variance
and power analysis. Default target: at least 30 distinct graphs per sufficiently
large family and 10 runs per graph, with sparse-family counts reported explicitly.
Enumerate small finite families where appropriate; repeated seeds are not new graphs.

Report stock MM under pinned defaults plus a reproducible budget policy, and a
separately declared stronger MM quality-budget comparison. Primary discovery is
quality-first; also report equal-time/compute quality curves. Include all construction,
repair, preprocessing, unsuccessful search, and internal optimization costs.
Calibrate discovery budgets against measured MM times on development instances,
using roughly 1x, 3x and 10x work/time allowances and explicit absolute caps for
timeouts. Choose a size-based budget rule before confirmation, not from a test
instance's MM output. Investigative runs beyond this envelope may explain a failure
but cannot qualify the algorithm. Choose confirmatory budgets before exposing the
holdout. MM's `tries` and `chainlength_patience`, not only `timeout`, affect effort;
the stronger configuration must be fixed globally, with every option reported.
Consult the pinned implementation and [official API documentation](https://docs.dwavequantum.com/en/latest/ocean/api_ref_system/generated/minorminer.find_embedding.html).

The discovery budget ladder is not a confirmatory dispatch rule. Before confirmation
freeze a single global budget or explicit input-size-only budget function, baseline
options, thread allocation, warmup policy, time boundaries, stopping conditions and
machine blocks. Name the primary comparison precisely: quality-first candidate at
its declared budget versus stock MM defaults at a declared cap/natural stopping;
also publish equal-time and stronger-MM results separately. A quality-only win must
state its extra compute cost. At any deadline, credit only an independently valid
incumbent made available by then. A watchdog grace period may allow cleanup/output
but cannot earn extra optimization credit. Record actual runtime overruns.

### Phase 5 — publication only if warranted

If the frozen method demonstrates the required class-wide quality and reliability,
prepare an ACM TQC draft: exact problem and algorithm, relationship to prior work,
invariants/proofs, complexity and empirical scaling, full protocol, per-family
results, ablations, limitations, raw artifacts and reproduction instructions.
No hardware generalization or quantum-solution-quality claim follows solely from
shorter chains on ideal Z12. Revisit other targets later as the user requested.

## 6. Evaluation rules

- Primary quality contrast: paired ACL differences on identical graph/trial sets
  where both methods return valid embeddings, summarized within graph and then
  with equal graph weights within family. Report the pair-coverage denominator and
  missingness, plus each method's own success-conditioned means as descriptive
  statistics. Never let the very large Watts–Strogatz category determine the answer
  for the other families. No unconditional quality claim follows from successful
  pairs alone.
- Report success on all scheduled trials and joint-success ACL separately; invalid,
  failed, crashed and timed-out runs cannot disappear from denominators. A quality
  result is insufficient if it is bought by selectively failing hard instances.
  Add the fraction of all trials achieving ACL <= a versus a and versus time;
  failure never meets an ACL threshold. Require no observed per-family success
  regression and a one-sided confidence bound on candidate excess failure below
  one percentage point, with confirmation error allocation included. This is an
  uncertainty criterion, not permission to deliberately sacrifice success for ACL.
  Sample size must support that bound; a small pilot with zero failures cannot
  automatically satisfy it. Exact equality of underlying success probabilities
  cannot be established from finite observations.
- Show both-success, candidate-only success, MM-only success and neither-success
  counts by graph and size/density stratum. Equal marginal success does not make
  common-success ACL unconditional. Claim unqualified mean-ACL improvement only
  with complete common coverage of the declared comparison set; otherwise label
  the result conditional and preserve unresolved cases. The all-trial success-quality
  curve is a separate endpoint, not a disguised mean ACL or a fabricated failure cost.
- Separate run-to-run variance of ACL from within-embedding variance of individual
  chain lengths. Mean ACL is primary; neither variance is a hidden acceptance rule.
- Preserve original graph-category membership but group exact/isomorphic copies for
  splitting and statistical dependence. Count capacity-impossible instances and
  no-eligible-instance families in coverage tables.
- Pair algorithm runs by graph, seed index and physical machine. Matching seed
  integers does not couple the algorithms' random trajectories. Randomize execution
  order. Do not compare unadjusted seconds from different CPU types or loads.
- Use graph-level paired intervals or a hierarchical analysis with seeds nested
  within graphs; predeclare the treatment of cross-family duplicates, missing
  pairs and multiplicity. A global average is not the all-family claim.
- Do not repeatedly inspect the confirmatory holdout while tuning. Record every
  look and retire an exposed holdout to development before further design decisions.
  Allocate confirmation attempt k an error budget alpha_k=0.05/[k(k+1)], k>=1,
  across successive frozen versions. Within an attempt, predeclare the familywise
  procedure (for example Holm-adjusted one-sided tests for separately advertised
  family claims), dependence handling and reliability tests. The total error budget
  across unlimited attempts is at most 0.05 if the individual procedures are valid.
  Distinguish the single conjunction claim from separate family discoveries. Follow
  a successful frozen attempt with independent replication without changing the
  algorithm. Fresh holdouts alone do not correct repeated-until-significant testing.
- ACL=1 ties are optimal, not wins. For oversized originals, a timeout does not
  establish infeasibility; use certified necessary conditions when available.

## 7. Cluster and persistent execution

All six authorized hosts were reachable as `dabh`; nodes 02–06 via hyde01. Machines
have 32 or 128 logical CPUs and different memory/loads. Detailed inventory and
execution design: [`notes/codex/cluster.md`](notes/codex/cluster.md).

Use immutable remote run directories, remotely detached or scheduler-owned workers,
atomic task claims and results, deterministic task IDs, checkpointed state/RNG,
heartbeats, and reconnectable artifact transfer. Verify survival of a deliberate
disconnect on a pilot. An SSH reconnect must discover running work rather than
submit duplicates. Limit and record threads, wall/CPU time and peak memory.
Use lightly loaded nodes for initial paired pilots and calibrate before scaling.

## 8. Research records and continuing decisions

Each experiment records: question, candidate critique, hypothesis, falsifier, code
revision, source/target hashes, graph split, parameters, seeds, environment, node,
resource limits, raw embeddings, measured outcomes, uncertainty, lessons, and the
next decision. A failed approach gets an explanation tied to evidence, not a vague
label. Revisit it only when a specific assumption or mechanism changes.

Persist toward the research objective, but do not promise that a universally better
algorithm exists or declare success without evidence. Ask the user for decisions
that change scope or scientific claims; continue already authorized independent work.
The planning phase produces reviewable notes and a finalized plan, not a claimed
algorithmic breakthrough.

## 2026-09-09 mechanism-cycle continuation

The strategic review and completed Transfer001 results remain authoritative.
Follow [Transfer002's frozen protocol](notes/codex/transfer_cycle_002_protocol.md):
A064 tests allocation of unchanged reconstruction queries in a complete36-call
screen; B028 first measures exact-route acceleration including cold compilation;
C013's complete tiny star failure rejects singleton-first construction and permits
one separately specified capacity-aware design hypothesis. Each decision uses
complete outcomes and the identified representation, neighborhood, acceptance or
cost explanation. Preserve earlier regressions and track the retained A061 class
table; none of these development screens replaces confirmation or the full goal.
