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

Experiment009 completed all45 trials. Every returned embedding passed independent
structural revalidation;44 were timely, and the K100 MM result was valid but late.
Native candidates made no forbidden import attempts and loaded no external embedding
libraries. On the eight common timely comparisons, native search won ACL on two
inputs and lost on six. This is development evidence, not a class-level conclusion.
Width-four refinement of packed construction showed only small gains over width
one while using more work. See the dedicated results review for exact metrics.

Next decision: retain one globally fixed native-search constructor and compare
singleton reconstruction with narrow/wider joint reconstruction. Expose existing
contact group-size/work bounds through the native adapter; add no family dispatcher.
The prespecified011 ablation uses the same nine development inputs, two seeds and
60-second allowances, with exact frozen source and separate candidate/MM processes.
Partial-construction design is saved but deferred until the valid-Z12 quality
question is resolved. The novelty review identifies close prior art; no publication
claim is justified by the present implementation or data.

Append every new user prompt/answer verbatim to `PROMPTS_CODEX.md`. Record each
experiment's question, pre-run prediction, revision hash, config, graph/target hashes,
seeds, machine, environment, wall/CPU/memory budgets, raw artifacts, validation, result,
interpretation, and next decision under `notes/codex/experiments/`. Preserve failures
and negative results. Record agent instructions and reports here or in linked notes.
