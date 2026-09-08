# Experimental endpoint-support objective

2026-09-08. Implements the accepted
[bounded specification](endpoint_support_implementation_spec.md), SHA256
`03cd87e074c8632c1361b7320e2d7942e5482d00505b138909b57d510501b8eb`.
No change to frozen experiments, final pruning, construction/search rules,
auxiliary proposal policies or work allocation. No corpus or cluster launch.
The new choice remains experimental; these checks establish local correctness
and compatibility, not ACL, runtime or novelty superiority.

## Implemented contract

`factored/endpoint_support.py` supplies `EndpointScorer(entry, ctx, group,
deadline=None)`. Construction performs no ownership/contact scan. Its `score`
method lazily builds the entry owner map once, applies selected ownership through
a temporary overlay, and returns a completed incident histogram plus raw
redundancy. Old selected sites absent from the overlay become free. The caller
must keep outside chains unchanged and validate connectivity independently.
No helper here calls a constructor, routing algorithm or external solver.

The scan records both endpoints of every actual coupler representing an incident
source edge. Selected-selected couplers are counted once; endpoints are
deduplicated separately for each direction. `source_adjacency_entries` records
every examined source-neighbor entry, including selected-selected duplicates;
`incident_source_edges` separately records each distinct edge admitted during
setup. The latter was added after independent static review identified that the
former alone did not supply the specified quantity. This was a new-diagnostic
correction only, with no search/acceptance change.

`ScoreDeadline` means a partial result cannot authorize acceptance. Setup is
published only when complete; partial score sets are local and discarded. The
scorer does not consume or extend `_Budget.expansions`. Owner/overlay/adjacency/
endpoint/histogram/comparison counters include performed partial work; setup,
score and comparison times are separate subtotals under the common deadline.
Comparison interruption is counted separately from interrupted score calls.

`repair_group` and `contact_polish` accept the new
`objective='qubits_endpoint_support'`. The existing complete-proposal loop and
size bounds are reused. At equal Q, a complete incident support histogram must
strictly improve relative to the current within-group best, followed by full
original-graph validation and a final deadline check. R is never its tie-breaker.
Valid strict-Q proposals pass validation and the final deadline check without a
secondary score. A later interrupted comparison retains an earlier certified
improvement. A validation that finishes late cannot authorize a new commit.

The feature rejects non-simple/directed/looped graphs and combinations with
direct singleton proposals, either star policy, or distance trees. Contact and
native perform these checks even on disabled/empty paths. Initial support scope
is ordinary reconstruction with greedy trees; no unsupported combination is
silently run under a different objective.

Native already forwarded `polish_objective` through its one common-deadline
contact call; its new code adds the early feature constraints. The new pilot arm
`native-search-joint1-endpoint-support-spectral` is exactly the unchanged
contacts-spectral configuration with this one objective option. All historical
configuration dictionaries remain equal to the frozen pre-edit versions.

There is no normalized-R path. Existing `qubits` and `qubits_contacts` preserve
their eager scoring/validation behavior and numeric diagnostic schema. As the
specification states, future control/treatment timing and finite-deadline results
compare complete scoring policies, not an isolated mathematical objective under
artificially identical computation.

## Nullable signed evidence

The new objective alone adds an `endpoint_support` record to moves and aggregate
diagnostics. When entry and returned-best secondary scores are both available,
the net R change and sparse histogram change are exact and signed. Equal-Q moves
can have **negative** R; a focused valid fixture demonstrates R delta −1 with a
strictly better endpoint histogram. It is an injected acceptance witness, not a
claim of proposer reachability or better final Q.

A strict-Q move can have `contact_redundancy_gain: null` and
`histogram_delta: null`, with `histogram_complete: false`. Missing is never 0.
The aggregate remains null if any accepted net move is unknown, while
`known_contact_redundancy_gain`, `known_histogram_delta` and `unknown_moves`
preserve explicitly partial evidence. An intermediate comparison baseline is
never substituted for the group's original entry. No finish-time scan is added
merely to eliminate a null. Histogram integer keys become strings in JSON.

Trajectory records label the objective, signed/null histogram change and
secondary completeness, alongside unchanged Q/member-growth meanings. Internal
best-update counts distinguish strict-Q and equal-Q updates; the outer accepted
count remains one per committed group result. Native's final original-graph
validator and overall timeout status remain unchanged.

## Checks, preserved failures and scope

The source before editing is copied under
`results/codex/endpoint-support-checks/reference`, with a manifest for contact,
native and pilot bytes. Tests import the frozen contact source under a separate
module name. Thirty-two paired replays span both historical objectives, both
group policies, ordinary/direct/matching/connected paths, and two tiny quotient
fixtures. They match embeddings and every non-time diagnostic exactly.

The additive detailed replay result is
`results/codex/endpoint-support-checks/replay002.json`, SHA256
`9f2eb3f90f82a5cf4d07ff91935c054f8da0f5f16e3c3a0362b8cf0fd2d59602`.
All 32 canonical output hashes match. Full leaf-difference lists retain the only
observed differences: `wall`, `proposal_wall`, `query_wall`, and `setup_wall`.
No ordinary trajectory guarantee is claimed for binding wall limits.

The first attempt, `focused001`, failed before test/algorithm imports because
the separate native environment does not contain pytest; its setup failure is
preserved. Tests use the project environment with an explicit import guard, as
the earlier connected integration checks did. The native-only environment is
not changed by this work.

`focused002` recorded 46 passes and eight replay-test failures. Its comparator
had removed only `wall`, leaving the existing star timing subtotals in a claimed
non-time comparison. The separate leaf-difference audit confirmed this exact
cause. Only the test comparator changed; no algorithm output was corrected or
excluded. The subsequent 54-check `focused003` passed. All failed artifacts
remain intact.

The final regression run `regression001` passed **191 tests in 4.47 seconds**
(runner wall 4.915 seconds), with stable production hashes and no prohibited
embedding import attempts or loaded modules. It includes 55 focused endpoint/API
checks and relevant existing contact/native/star/singleton/spectral suites.
One additional directed test then checked that released sites of a selected
neighbor cannot remain phantom contact support; it changes no production code.
The final `focused004` rerun passed **56 tests in 2.37 seconds** (runner wall
2.877 seconds) on unchanged production hashes, with no prohibited imports. Final
hashes are recorded in the additive review manifest beside these logs. These
durations are test-run costs, not embedding
runtime measurements or benchmark speed evidence.

Independent whole-target-edge enumeration covers 64 scored states across eight
tiny quotient targets, mixed labels, groups of one through four, frozen
multi-qubit chains, owner transfers, free sites and non-source physical edges.
The actual ideal-Z12 hand-specified A/B witness is checked separately against its
physical graph, with no constructor call. Its nonminimal-start and subset-only
deletion interpretation remain explicit in the design; it does not establish
the current proposer reaches either state.

Focused acceptance checks include support/R disagreement, exact ties, comparison
against an already improved best, no score on strict-Q acceptance, retaining a
prior gain after later score interruption, known negative and unknown aggregate
R, and validation crossing the deadline. Every score-check prefix is interrupted
on a small fixture, preserving the incumbent and uncommitted setup. A completed
proposal using the last routing expansion can still be scored, with its separate
scan count proving expansions were neither redefined nor extended.

A single new small native Z3/path-plus-isolate smoke checks one initializer,
one placement and one real contact call with the same deadline, label coverage,
input immutability and full physical validity. Other native calls belong to the
existing bounded regression suites. No all-34 source or new MM input is used.

## Additive reproduction and remaining gate

From the repo root, use fresh output paths:

```sh
.venv/bin/python results/codex/endpoint-support-checks/run_checks.py results/codex/endpoint-support-checks/root_focused
.venv/bin/python results/codex/endpoint-support-checks/run_checks.py results/codex/endpoint-support-checks/root_regression --regression
.venv/bin/python results/codex/endpoint-support-checks/replay_check.py results/codex/endpoint-support-checks/root_replay.json
```

The runners refuse existing outputs; test invocation records include exact
arguments, environment package versions, source/test hashes, runner hash and
guard outcomes. The review manifest binds the final code, reference, tests and
notes. Root owns independent acceptance and any separately frozen experiment.
The heuristic can still prefer articulations or dispersed sole obligations,
spend time on secondary plateaus, and displace useful groups. Correct scores and
old-path replay do not resolve those quality and runtime risks.
