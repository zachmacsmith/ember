# Experiment 009: independent results review

Date: 2026-09-07 local time (manifest creation 2026-09-08 01:25:23 UTC).
Reviewed all 45 finalized results in
[`results/codex/009-first-development-screen`](../../../results/codex/009-first-development-screen),
its worker records, immutable tasks, frozen source, and graph records. The
[pre-launch note](009_first_development_screen.md) was left unchanged.

## Outcome

Every fixed candidate configuration returned a timely, structurally valid
embedding on all nine development inputs. MM returned eight timely valid
embeddings and one valid embedding after its deadline. On the eight timely
MM-comparable inputs, Search has lower ACL twice and higher ACL six times. Each
packed configuration has lower ACL once and higher ACL seven times. The present
screen therefore does not show an algorithm that beats MM across these inputs,
let alone across Ember's graph families.

All configurations use solver seed 0. These are nine generated development
instances from eight graph types, not the full Ember manifest or a held-out
sample. The two complete graphs have different sizes. A single result is the
mean of its chains; it does not establish expected ACL or variability across
repeated solver runs.

Search uses the inherited geometric order optimizer with at most 1,000 proposals
and no MM legalization or contact polish. Packed uses one random shared order
and two packing passes. Packed B1/B4 apply the same packed construction followed
by contact reconstruction with beam width one/four, at most two passes and 48
groups. MM uses stock defaults apart from seed 0 and the 30-second timeout.

## Per-input ACL and status

All numeric entries below are independently rechecked SUCCESS records; the
nonnumeric entry is excluded from timely-success quality comparisons. ACL is
qubits divided by source vertices. The tables preserve separate configurations;
there is no row-wise winner selection or portfolio output.

| Graph (vertices, edges) | MM | Search | Packed | Packed B1 | Packed B4 |
|---|---:|---:|---:|---:|---:|
| complete_40 (40, 780) | 4.200000 | 3.900000 | 3.900000 | 3.875000 | 3.875000 |
| complete_100 (100, 4950) | TIMEOUT | 7.260000 | 7.260000 | 7.260000 | 7.260000 |
| bipartite_30_30 (60, 900) | 3.166667 | 2.516667 | 4.700000 | 4.666667 | 4.666667 |
| random_er_80_d8 (80, 296) | 2.925000 | 3.412500 | 4.962500 | 4.862500 | 4.825000 |
| regular_80_d3 (80, 120) | 1.112500 | 1.812500 | 3.412500 | 3.000000 | 3.000000 |
| watts_strogatz_80 (80, 160) | 1.387500 | 1.912500 | 4.137500 | 3.725000 | 3.712500 |
| grid_8x8 (64, 112) | 1.109375 | 1.390625 | 3.265625 | 2.921875 | 2.921875 |
| honeycomb_5x5 (70, 94) | 1.000000 | 1.257143 | 3.100000 | 2.628571 | 2.614286 |
| king_8x8 (64, 210) | 1.578125 | 1.906250 | 4.171875 | 3.859375 | 3.890625 |

MM on K100 returned a valid 1,022-qubit embedding with diagnostic ACL 10.22, but
its solver wall time was 31.225618 seconds against a 30-second deadline. It is
correctly classified TIMEOUT; its ACL is not credited as a timely comparison.
All four candidate configurations on K100 used 726 qubits. That establishes the
observed difference in deadline compliance on this trial, not a statistically
supported family-level success advantage.

Honeycomb's MM ACL of 1 is the absolute lower bound for any nonempty embedding.
Strict improvement on that particular result is impossible; a future candidate
can tie it. The candidate's remaining quality gaps on these small structured
inputs are substantial.

## Solver and whole-process timing

Each cell is **solver seconds / process seconds**, rounded to three decimals.
Solver timing begins after loading inputs and importing the implementation and
ends when its call returns. Process timing includes startup, imports, input
loading, independent validation, serialization, and controller observation.
First-call JIT work inside the solver is charged to solver time.

| Graph | MM | Search | Packed | Packed B1 | Packed B4 |
|---|---:|---:|---:|---:|---:|
| complete_40 | 2.780 / 3.160 | 2.528 / 3.980 | 1.346 / 2.215 | 1.472 / 2.329 | 1.576 / 2.475 |
| complete_100 | 31.226 / 31.634 | 8.476 / 9.504 | 1.506 / 2.438 | 1.819 / 2.740 | 2.430 / 3.352 |
| bipartite_30_30 | 0.995 / 1.370 | 2.659 / 3.556 | 1.423 / 2.312 | 1.487 / 2.438 | 1.649 / 2.542 |
| random_er_80_d8 | 1.019 / 1.316 | 4.162 / 5.232 | 1.375 / 2.259 | 1.708 / 2.639 | 2.125 / 3.029 |
| regular_80_d3 | 0.217 / 0.510 | 3.784 / 4.668 | 1.342 / 2.222 | 1.497 / 2.370 | 1.805 / 2.704 |
| watts_strogatz_80 | 0.232 / 0.607 | 3.884 / 4.759 | 1.327 / 2.171 | 1.524 / 2.391 | 1.777 / 2.656 |
| grid_8x8 | 0.169 / 0.444 | 3.034 / 3.875 | 1.449 / 2.329 | 1.479 / 2.334 | 1.747 / 2.636 |
| honeycomb_5x5 | 0.159 / 0.455 | 3.362 / 4.221 | 1.341 / 2.206 | 1.496 / 2.426 | 1.741 / 2.588 |
| king_8x8 | 0.259 / 0.566 | 3.179 / 4.047 | 1.328 / 2.218 | 1.570 / 2.454 | 1.602 / 2.600 |

The frozen harness creates a new, previously nonexistent Numba cache directory
per task and runs methods sequentially in randomized order on `dabhmbp`, Darwin
arm64. It fixes `PYTHONHASHSEED=0` and four numerical-runtime thread limits to one.
These are cold calls, not measurements of a persistent warm service. All recorded
process times exceed solver times; neither timing column should be substituted
for the other depending on which comparison looks better.

The machine's one-minute load average at worker start ranged from 18.762 to
46.801. CPU affinity was unavailable. Randomized sequential comparison on one
machine avoids pooling different hardware speeds, but does not remove changing
background load. One observation cannot establish timing variability.

On the eight timely paired inputs, the median per-input Search/MM ratio is
14.502 for solver wall and 7.499 for process wall. Search solver ratios on grid,
honeycomb, regular, Watts–Strogatz, and king are approximately 18.0, 21.1, 17.4,
16.7, and 12.3 respectively. Its current internal solver cost therefore exceeds
10 times MM on those five inputs, even though cold whole-process ratios are
below ten. The corresponding median process ratios for Packed, Packed B1, and
Packed B4 are 3.749, 4.139, and 4.487. These descriptive numbers are not precise
speed estimates under controlled load.

## Conditional comparison coverage

| Fixed candidate | Timely successes | Timely MM pairs | ACL wins / ties / losses | Mean paired ACL | Mean per-graph ACL ratio to MM |
|---|---:|---:|---:|---:|---:|
| Search | 9/9 | 8/9 | 2 / 0 / 6 | 2.263523 | 1.202019 |
| Packed | 9/9 | 8/9 | 1 / 0 / 7 | 3.956250 | 2.355748 |
| Packed B1 | 9/9 | 8/9 | 1 / 0 / 7 | 3.692374 | 2.143491 |
| Packed B4 | 9/9 | 8/9 | 1 / 0 / 7 | 3.688244 | 2.141452 |

The MM mean ACL over those same eight inputs is 2.059896. Each mean above gives
equal weight to an input; the final column separately averages the individual
candidate/MM ACL ratios. A mean of ratios is not the ratio of the means. These
aggregates are illustrative for this deliberately small screen, not population
estimates, significance tests, or family-balanced Ember results.

K100 is explicitly absent from this conditional quality comparison. Excluding it
must not hide that all candidates succeeded 9/9 and MM succeeded within budget
8/9. Conversely, the existence of a diagnostic late MM embedding must not turn
this into nine timely quality pairs.

## Packed beam comparison

Packed B1 and Packed B4 have identical declared construction settings and seed.
For every graph, both report the same pre-repair qubit count as the unrefined
Packed result. Both attempted 48 groups per graph, with the same two-pass upper
bound. B1 is still **coupled group reconstruction**, with one retained beam
prefix; it is not a singleton-chain control.

| Graph | Saved qubits B1 / B4 | Accepted moves B1 / B4 | Growing members B1 / B4 | BFS expansions B1 / B4 | Repair seconds B1 / B4 |
|---|---:|---:|---:|---:|---:|
| complete_40 | 1 / 1 | 1 / 1 | 0 / 0 | 14,311 / 34,013 | 0.113 / 0.265 |
| complete_100 | 0 / 0 | 0 / 0 | 0 / 0 | 44,056 / 138,570 | 0.316 / 0.876 |
| bipartite_30_30 | 2 / 2 | 2 / 2 | 0 / 0 | 21,417 / 52,275 | 0.135 / 0.309 |
| random_er_80_d8 | 8 / 11 | 7 / 10 | 0 / 0 | 166,246 / 377,649 | 0.352 / 0.749 |
| regular_80_d3 | 33 / 33 | 17 / 17 | 0 / 0 | 76,166 / 235,810 | 0.169 / 0.478 |
| watts_strogatz_80 | 33 / 34 | 16 / 17 | 2 / 3 | 67,340 / 211,334 | 0.161 / 0.447 |
| grid_8x8 | 22 / 22 | 15 / 15 | 0 / 0 | 59,016 / 191,174 | 0.147 / 0.418 |
| honeycomb_5x5 | 33 / 34 | 17 / 17 | 1 / 1 | 63,223 / 210,206 | 0.139 / 0.408 |
| king_8x8 | 20 / 18 | 15 / 12 | 1 / 0 | 37,991 / 80,907 | 0.173 / 0.270 |

Across the nine inputs:

- B1 saves 152 qubits in 90 accepted moves; B4 saves 155 in 91 accepted moves.
- B4 improves on B1 on ER by three qubits, honeycomb by one, and Watts–Strogatz by
  one. It ties on five inputs and is worse on king by two qubits.
- B1 uses 549,766 counted BFS expansions and 1.705894 seconds of repair time.
  B4 uses 1,531,938 expansions and 4.219836 seconds: 2.787 times the work count
  and 2.474 times repair wall for three additional net saved qubits.
- Both record four growing-member occurrences across three accepted moves.
  B1's growth-bearing moves occur on honeycomb, king, and Watts–Strogatz; B4's
  occur on honeycomb and twice on Watts–Strogatz. A move with two growing members
  contributes two to the member count.

The reported move trajectories sum consistently to the final savings and final
qubit totals. For example, the shared Watts–Strogatz group `[34,17,18,20]` has two
members grow while saving five qubits in both B1 and B4. This is evidence that
coordinated growth occurs in useful accepted moves, but not evidence that width
four is needed to realize it. The trajectories do not store every intermediate
embedding or each member's exact size delta, so growth counts here are checked
for internal consistency, not independently reconstructed member by member.

The beam comparison is not equal-work: equal group limits permit wider beams to
inspect more routes. Different accepted local choices also change subsequent
search states, so a larger beam need not produce a smaller final embedding. The
king result demonstrates that limitation. The small aggregate difference does
not yet justify the additional width on efficiency grounds. A controlled
singleton-group comparison and equal-work/equal-time curves are still needed to
attribute a gain to the proposed mechanism.

All repair diagnostics say `stopped_by=no_improvement`, but they also report
48 attempted groups and two passes. That status is not evidence of a local
optimum: the total group allowance has been consumed. The next empty pass in
the examined implementation can produce that label. Treat the explicit work
counts as the actual evidence about search extent.

## Search construction versus packed construction

Search without contact repair has lower ACL than unrefined Packed on seven
inputs and ties on both cliques. Against either fixed packed-plus-repair variant,
it is lower on seven inputs, tied on K100, and one qubit worse on K40. Thus the
construction choice explains far more of the present quality gap than widening
packed refinement: the seven Search-versus-B4 improvements range from 95 to
144 qubits per input.

Search's layout diagnostics reach the configured 1,000-proposal limit on seven
inputs; K40 and bipartite stop with the internal `fixpoint` label after 515 and
584 proposals. No candidate reaches the 30-second solver deadline. Extra search
could change quality, but this screen does not establish its marginal benefit
or runtime cost, and `fixpoint` is not a certificate of optimality.

This supports the next planned experiment with one fixed Search-plus-contact
configuration. It does not authorize combining Search and Packed outputs per
instance. Search still loses to MM on six of the eight timely pairs and has a
significant internal runtime cost. All four candidates succeeded here, contrary
to the pre-launch possibility of native conversion failure; this screen supplies
no observed partial-construction failure for assessing the proposed partial
repair extension.

## Provenance and independence checks

The independent review recomputed SHA-256 using the frozen harness's canonical
JSON convention (sorted keys and compact separators) for structured records,
and raw bytes for source files. It found no discrepancy:

- All 42 frozen source files match their manifest hashes, and their hash-map
  digest matches `source_snapshot`.
- All 45 task IDs match their payload digests; tasks match the source snapshot
  and target hash; every result agrees with every task identity/config field.
- All nine serialized source graphs and the complete target record match their
  declared hashes, including attributes. The target has 4,800 vertices and
  45,864 edges, with Zephyr Z12 metadata and coordinates.
- All 45 worker-result payloads agree with their finalized records. Every final
  record has `controller_finalized=true` and return code zero; there are no
  missing tasks or duplicate task IDs.
- A separate plain adjacency check revalidated all 45 stored embeddings:
  exact source keys, nonempty connected chains, target membership, no repeated
  qubits, disjointness, and every source contact. Qubit totals, ACL, maximum
  chain length, and within-embedding chain variance also recompute correctly
  for all 45, using diagnostic quality for the late MM result.

Snapshot: `9ef616aeeab4a15691ee2fbe991ca9ade6af707eeb4be6edb33810437474f8db`.
Target: `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`.
Repository HEAD recorded by the manifest is
`580d20447a78f92cafa2343bd63794fcb6a87c82`; the snapshot hashes identify the
uncommitted experimental code more precisely than that commit alone.

For all 36 candidate records, the interpreter is `.venv/codex-native/bin/python`,
MM package metadata is absent, forbidden import attempts are empty, loaded
prohibited embedding modules are empty, and the recorded native implementation
path is within frozen source. The worker checks for installed `minorminer`,
`_minorminer`, and `busclique` before importing the candidate, then rejects
matching top-level imports. The examined native entry point does not receive a
baseline embedding or select between independent constructors at runtime.

The MM records use `.venv/bin/python` and identify MM 0.2.22. Both environments
report Python 3.10.19, NetworkX 3.4.2, NumPy 2.2.6, Numba 0.65.1,
`dwave-networkx` 0.8.19, and SciPy 1.15.3. Candidate use of D-Wave's topology/layout
utility is distinct from invoking an embedding algorithm.

These checks support independence of the recorded candidate execution paths.
They are not a formal proof against disguised native code or an exhaustive
external dependency audit. The broad source snapshot contains unused historical
MM wrappers; including a file in that snapshot does not mean it was called.
Baseline package versions are recorded, but installed dependency binary hashes
are not part of this source snapshot.

## Why this cannot estimate across-run ACL variance

For a fixed source graph, the run-level ACL is the mean chain size from one
embedding. There is only one solver-seed observation per configuration and graph,
so an unbiased sample variance of run-level ACL is undefined, not zero. The raw
`within_chain_variance` describes differences between chains inside that one
embedding; it is a different quantity. Dispersion across these heterogeneous
nine graphs would measure changing inputs, not repeated-run stability.

Repeated independently chosen solver seeds on each fixed input, and multiple
instances per graph class, are needed to separate run variation from instance
variation. This screen provides neither confidence intervals for expected ACL
nor evidence that one method has lower across-run variance. All nine inputs
remain development data after this review.
