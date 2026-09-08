# Fixed spectral initialization in the independent pipeline

Protocol and integration critique recorded before any end-to-end spectral run.
The source-only design and its five-part self-critique are in
`../spectral_initialization_spec.md`. It uses a conventional bounded Laplacian
calculation; novelty and embedding quality remain unproved.

## Hypothesis and fixed comparison

The present constructor starts from two independent random vertex rankings.
Source-adjacency structure may provide a better initial placement, reducing
chain length after the same geometric search and contact reconstruction. Replace
those two rankings with the two orders returned by one spectral calculation.
There is no competition with random initialization within a solver call, no
restart or fallback, and no family-dependent parameter choice.

Compare the fixed contact-rearrangement pipeline with random initialization
against that identical pipeline with spectral initialization on all 34 exact
readiness inputs from 017, seed 0, ideal Z12 and 60 seconds per call. This is
68 trials, sequentially on hyde03 after 025 is complete. Both arms use 1000
placement evaluations, four refinement passes, 512 total groups, 500000 shared
refinement work units, 16 boundary sites, round-robin groups of sizes 1–4,
greedy contact trees, outer width one and the qubit/contact-redundancy objective.
The spectral policy uses its fixed 64 iterations, residual tolerance 1e-5 and
shared 50000000 numerical work limit on every input. The initializer's elapsed
time, including its lazy dependency import, is charged to the original solver
deadline. Finite approximate orders are used and explicitly labeled approximate.
No orders after numerical, work-limit or dependency failure means an explicit
initialization failure, never substitution of another initializer.

The choice to test this change does not depend on favorable 025 family results.
Keep every 017 input, duplicate-family mapping and missing Sudoku record. These
remain development inputs. Results from 019 MM are a historical quality reference
only; this experiment supplies no contemporaneous MM runtime comparison. Preserve
each fixed arm separately and every failure. Do not choose an arm per graph.

## Integration critique and correctness gates

1. The geometric engine consumes ranks, whereas the spectral API returns vertex
   orders. Invert both permutations explicitly; reject missing, duplicate or
   unknown vertices. An order/rank mixup can remain a valid embedding and therefore
   needs a direct semantic test beyond final embedding validity.
2. Preserve the independently seeded placement scheduler. Replaying the existing
   random initialization as explicit orders must give the same positions, physical
   construction and proposal trajectory at fixed work. New initialization must
   not accidentally change both initialization and scheduler randomness.
3. Near-degenerate eigenspaces and iteration limits can make the spectral plane
   a weak or arbitrary guide. Record residuals and cutoff uncertainty. Even valid,
   repeatable source-only output is not evidence of better embedding quality.
4. Source relabeling through the existing adapter, edge insertion order and graph
   metadata must not introduce an input-family selector. Include mixed labels and
   isolates in native correctness checks and keep arbitrary node-order sensitivity
   explicit rather than claiming isomorphism invariance.
5. Failed initialization must stop the single pipeline before placement. A common
   deadline must cover initialization, placement and repair; a late valid output
   is diagnostic only. An equal-work comparison can still have different runtime,
   so report both work and elapsed time at the fixed overall allowance.

Before freezing a cluster run: inspect the independent numerical review, run the
source-only tests, test explicit-order equivalence and invalid-order rejection,
check native failure/deadline forwarding, and perform a small isolated-environment
correctness smoke with forbidden embedding imports guarded. Only then save the
source snapshot and stage the declared full input comparison.

## Integration verification

Independent module review found no numerical or independence blocker and retained
the conventional-method attribution and approximation limits. A second review
checked the actual plane/native/pilot changes: order inversion, independent
scheduler, common deadline, fixed configuration and no fallback are preserved.
The default random branch remains unchanged. The native adapter now records
`initialization` and, for spectral calls, the full numerical diagnosis.

The combined focused suite passed 160 tests in 28.93 seconds. An additional
approximate-output boundary test was added after review: finite approximate
orders must pass through exactly one placement call and retain their numerical
status. The complete integration test file then passed 14 tests. These checks
establish implementation behavior, not a benchmark quality improvement.

The isolated correctness smoke uses the existing fixed development inputs
`complete_40`, `regular_80_d3`, and `grid_8x8`, one spectral candidate call each,
with the same 60-second end-to-end allowance and normal worker import guards.
All three inputs are retained regardless of outcome. These calls exercise dense,
sparse random and sparse geometric construction paths; they are not an
MM comparison or a family-level performance estimate.

All three smoke calls completed with independently valid embeddings and no
forbidden import attempts or loaded embedding libraries. MM is absent from the
candidate environment. The ordinary artifact analyzer passed all three records.

| Smoke source | Qubits / ACL | Solver / process seconds | Initialization seconds |
| --- | ---: | ---: | ---: |
| complete_40 | 151 / 3.775 | 3.652 / 4.867 | 0.168 |
| regular_80_d3 | 107 / 1.3375 | 3.841 / 4.632 | 0.131 |
| grid_8x8 | 72 / 1.125 | 3.099 / 3.891 | 0.128 |

These are local cold-process observations, including first-call JIT cost. They
are not pooled with cluster timings. Each call's two layout vectors met the
residual tolerance; complete_40 correctly reports an unresolved subspace cutoff.
Raw smoke artifacts are at `results/codex/026-spectral-native-smoke`.

## Frozen full comparison

Code revision: `f93f889f428baa26d1722382c77de385d4b4822f`.
Source snapshot: `91824466fdd3880940df0cc6d3569a461a617c3d1ae883e50425ee368952a765`.
Verified transport: `481ae432e47dc5b0c9f3951d38080ee21e9de0d9e52833bafd15985322c9608c`.
The 68 tasks are frozen in `results/codex/026-corpus-spectral-initialization`
and staged at `/home/dabh/ember-codex/runs/026-corpus-spectral-initialization`
on hyde03. They preserve selection 017 and its sidecars.

## Actual launch and fresh live verification

The benchmark auditor started this exact run after verifying that 025 had
completed all 68 trials, released its lock, stopped its tmux supervisor, and
returned supervisor exit 0, and after retrieving 025 with all 429 archive files
hash-verified. No 025 outcome changed the already frozen 026 protocol.

026's supervisor started at `2026-09-08T02:51:44.531316Z` under tmux session
`ember-codex-ef2a0cc9c971540d0411`; maximum lifetime is 6420 seconds. A fresh
SSH observation confirmed running controller PID 122275, active worker PID
122287, held inherited worker lock, and live tmux supervisor. A subsequent
fresh observation showed 4/68 finalized SUCCESS records and active worker
122416 under the same controller. These are launch/progress observations,
not completed quality evidence. No restart or active-run fetch was performed.

The full launch record is in `026_launch_status.md`, with raw responses saved
at `results/codex/026-launch/`. Retrieve the completed run only after verified
quiescence. Keep candidate timing comparisons within 026; MM019 remains
historical quality evidence only.
