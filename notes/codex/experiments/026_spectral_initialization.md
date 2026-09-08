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
