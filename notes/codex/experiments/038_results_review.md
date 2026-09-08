# Initial-prefix certificate screen: negative result

2026-09-08. **No timely certificate was found. Reject this fixed initial
checkpoint policy, including its prescribed overload gate.** The independent
audit passed all 68 observations with zero audit errors. Root independently
repeated the complete auditor and obtained byte-identical outputs.

The [frozen protocol](038_initial_prefix_certificates.md) examines only the
initial native prefix after its three packing readouts, before any search
proposal. It allows one physical evaluation only when initial overload is zero.
This review did not invoke a prefix, embedding algorithm, MM, or another solver.
It analyzed the completed immutable records after root verified quiescence.

## All outcomes are retained

Each of the 34 source structures had one cold and one second invocation, using
the same worker, seed zero, and common 60-second invocation allowance. Outcomes
were identical between the two invocations:

| Outcome | Cold | Second | Total |
|---|---:|---:|---:|
| Positive overload; physical evaluation skipped | 21 | 21 | 42 |
| Valid physical embedding, Q strictly above L | 13 | 13 | 26 |
| Timely Q=L certificate | 0 | 0 | 0 |
| Timeout, invalid final output, initialization failure, error, or missing observation | 0 | 0 | 0 |

Every input passed the source/target degree-capacity gates. Every capture had
zero recorded misses, including all 21 inputs with positive overload. Neither
fact establishes a valid embedding or attainment of the qubit bound. All
positive-overload cases followed the frozen skip policy; no conversion,
projection, alternative initialization, or later checkpoint was tried for them.
In particular, cycle and path were skipped, with overloads 5 and 17 respectively.

Positive overload is a cost gate, not an infeasibility certificate. These
observations do not establish that the skipped source graphs are unembeddable,
that their captured geometry could never yield a useful embedding, or that a
different prespecified stopping position could not work. The present result
does not authorize selecting another position or changing this gate after
examining these outcomes.

For the 13 physically evaluated structures, converted, completed and constructed
chain maps were exactly equal; all were independently valid. Pruning retained
validity and reduced their total Q from 13,271 to 12,576 in each invocation,
saving 695 qubits. None attained its bound. The nearest case was star 2229:
Q=136, L=133, gap 3. The remaining positive gaps are shown below. A gap above a
lower bound does not prove that the bound itself is attainable.

## Original inputs, target and validity

The 34 distinct original 017 readiness structures carry 35 family memberships.
The king/frustrated-square structure is one input, with one pair of observations;
its two memberships are not independent evidence. Original Sudoku remains
absent. No corrected Sudoku supplement was substituted. All these inherited
inputs are development data, with one selected size and one solver seed per
structure; this is not a holdout or a population estimate for each family.

All 170 manifest-listed files and the manifest itself remained byte-identical.
Production code is the exact 47-file 037 snapshot from commit
`13876c22b0576c3d41d54bffe5ec429e37f5d08c`. The complete source/input and
instrumentation preflight is recorded in [the independent preflight review](038_preflight_review.md).
The result auditor rechecked all frozen bytes, all original/normalized label
maps, source vertices and edges, selection membership, and the exact target.

The ideal Z12 target has 4,800 vertices, 45,864 edges, and maximum degree 20.
For a source vertex of degree d, a connected chain of k physical vertices has
at most `18*k+2` outgoing couplers. Thus

```text
ell[v] = max(1, ceil((d[v]-2)/18))
L = sum(ell[v])
```

The auditor recomputed these integer bounds and every necessary degree gate
from the original graph structure. It independently checked exact source-key
coverage including isolates, nonempty chains, target membership, disjointness,
chain connectivity, and every original source edge against the original target
couplers. For each valid chain it also verified actual internal-edge and
boundary-coupler counts against the connected-chain degree inequality.
Every physical-stage map was retained and checked. No low geometric score,
self-reported Q, or partial chain map was accepted as a certificate.

## Capture and replay checks

All 68 captures used exactly three initial readouts on axes `(1,0,1)`, with zero
asks, accepts and search passes. The degree check, input copy, target-adjacency
construction, grid construction and spectral initializer each ran once per
invocation. Each of the 26 eligible observations called conversion, completion,
isolate handling, constructed validation, pruning and final validation exactly
once, in that order. The 42 skipped observations called none of those physical
stages. Proposal/refinement sentinels and prohibited import records were clear.

Every invocation used the manifest-bound native-only interpreter and frozen
module paths. MM, its checked variants, and busclique were absent; no forbidden
import attempt or loaded module was recorded. Each input had a fresh process
and initially empty dedicated JIT cache, followed by its one second invocation
in that process/cache. There was no replacement worker or unrecorded warm-up.

All 34 cold/second pairs agreed exactly in the saved geometry representation,
initial vertex orders, full scheduler RNG state, typed structural-state hashes,
and serialized final embedding (including the shared absence of an embedding
for skips). Initialization arithmetic and call counts also matched. Each RNG
state equals the recorded seed-zero state before proposal draws. Every capture's
before/after geometry, RNG and structural hashes agreed.

Four structural-hash categories were independently reconstructed from frozen
records without importing the candidate or NetworkX: caller source graph,
caller target graph, native source adjacency and captured target adjacency.
The reconstruction preserves node/neighbor iteration and attribute order.
The fifth category—the full grid, including its arrays and caches—is saved only
as a typed hash. Its before/after and cold/second hashes agree, but unsaved grid
arrays and caches cannot be independently reconstructed from those hashes.
This distinction is retained in every observation's audit record.

Spectral initialization reported 32 residual-tolerance results and two
approximate results per invocation; the latter were cycle and path. Per
invocation it recorded 3,691,205 work units, 3,145 operator columns, no dense
base-case work, eight warning messages in four observations, and 15 uncertain
cutoff components. The maximum used residual was approximately 0.001078850619.
The independent initializer auditor reconciled component structure, work,
residual/tolerance classification and the saved numerical diagnostics.
Eigenvectors were not saved, so it does not independently recompute residuals.

## Deadlines, supervision and measured costs

Root launched once at 05:42:32.741 UTC. Controller 60678 ran from
05:42:33.097 to 05:46:49.789 UTC. All 34 workers returned zero, were reaped,
and ran sequentially. No worker timeout, kernel alarm, TERM/KILL cleanup, or
surviving descendant was recorded. Each raw supervisor log contains the matching
start and finish records. Root's terminal observation confirms the controller
absent and inherited lock free; the auditor binds that observation to the
unchanged controller record.

All invocation deadlines were nonbinding. Maximum charged solver wall was
5.291 seconds cold and 3.673 seconds second, leaving minimum margins of 54.709
and 56.327 seconds respectively. The original native deadline differed from
the authoritative common deadline by at most 27.625 microseconds cold and
6.417 microseconds second; wrappers clamped to the common timestamp. No extra
allowance was created by entering a later physical stage. Both observations
in each worker retained the same absolute 150-second kernel-alarm deadline.

The following are **totals across 34 observations per column**, not family
means or estimates of production runtime. Skipped physical stages contribute
zero measured function time. Nested native-prefix timing is shown separately
and is not added again to the partition.

| Measured quantity | Cold total (s) | Second total (s) |
|---|---:|---:|
| Charged solver wall | 131.034 | 82.896 |
| Solver CPU | 122.329 | 79.303 |
| Raw timed function stages | 54.671 | 8.269 |
| Full structural hashing inside solver wall | 73.421 | 71.635 |
| Remaining diagnostics and uninstrumented work | 2.941 | 2.991 |
| Native prefix, nested within the above | 50.123 | 3.862 |
| Three readout functions, nested | 40.900 | 0.230 |
| Spectral initializer, nested | 5.838 | 0.288 |
| Physical functions, nested; 13 evaluations | 2.902 | 2.805 |
| AST preparation outside solver wall | 1.349 | 1.705 |

The raw function stages, structural hashing and residual partition reconcile
to the full solver wall. Full structural hashing alone accounts for 67.8% of
the combined charged solver wall. This diagnostic was deliberately intrusive;
those costs remain charged and visible. They were never subtracted to change a
deadline classification. The average physical-function time per actual
evaluation was 0.223 seconds cold and 0.216 seconds second; these nested timers
exclude intervening record-copying/publication overhead, which stays in the
residual and total wall.

Total external worker-process wall was 256.456 seconds, with mean 7.543,
median 7.282, and maximum 10.139 seconds for a complete two-invocation worker.
It reconciles as 213.929 seconds of solver wall, 26.991 seconds of shared
import/hash setup and graph loading counted **once per worker**, 3.053 seconds
of AST preparation, 0.639 seconds of finalized observation publication, and
11.844 seconds of remaining process work. Controller span was 256.693 seconds.

Execution was local on `dabhmbp`, Darwin arm64, with 10 reported logical CPUs
and the frozen single-thread numerical settings. Observed one-minute load
averages ranged from 18.345 to 49.627. "Cold" denotes a fresh worker and empty
per-input JIT cache; it does not mean an empty operating-system file cache.
Cold/second differences also include lazy imports, allocation and machine load,
so they are not a pure JIT estimate. No MM timing, another host's timing, or
saved complete-pipeline timing is used here. This diagnostic cannot establish
search time saved or a net complete-pipeline speed improvement.

## Complete input table

Status, overload, Q and gap are the same in both invocations. "Skipped" means
SKIPPED_OVERLOAD; every numeric final Q is VALID_NONATTAINING. Times are separate
charged invocation walls. Exact rational ACLs and the shared terminal status are
retained in `report-tables/all_inputs.csv`; the complete individual records are
in `final/observations.json`. This table does not average the two invocations
into independent quality samples.

| Family / representative ID | n | m | L | Overload | Q before → after pruning | Q−L | Cold wall (s) | Second wall (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| complete / 1041 | 127 | 8001 | 889 | 0 | 1624 → 1598 | 709 | 4.673 | 3.344 |
| barabasi_albert / 10662 | 122 | 472 | 129 | 2 | skipped | — | 3.547 | 2.245 |
| bipartite / 1363 | 126 | 3969 | 504 | 0 | 1554 → 1537 | 1033 | 4.182 | 2.758 |
| regular / 14334 | 140 | 2800 | 420 | 0 | 1788 → 1755 | 1335 | 4.279 | 2.951 |
| grid / 1584 | 128 | 232 | 128 | 5 | skipped | — | 3.581 | 2.657 |
| cycle / 1829 | 126 | 126 | 126 | 5 | skipped | — | 3.480 | 2.291 |
| path / 2030 | 141 | 140 | 141 | 17 | skipped | — | 3.385 | 2.161 |
| star / 2229 | 127 | 126 | 133 | 0 | 346 → 136 | 3 | 3.569 | 2.291 |
| watts_strogatz / 22972 | 174 | 1740 | 249 | 3 | skipped | — | 3.647 | 2.322 |
| wheel / 2429 | 127 | 252 | 133 | 0 | 358 → 287 | 154 | 4.126 | 2.789 |
| turan / 3060 | 90 | 2700 | 360 | 0 | 831 → 815 | 455 | 4.784 | 2.632 |
| sbm / 30736 | 120 | 625 | 121 | 0 | 868 → 844 | 723 | 3.998 | 2.353 |
| lfr_benchmark / 31357 | 100 | 204 | 100 | 1 | skipped | — | 3.530 | 2.269 |
| random_planar / 31536 | 152 | 450 | 152 | 12 | skipped | — | 3.556 | 2.302 |
| triangular_lattice / 31879 | 128 | 384 | 128 | 64 | skipped | — | 4.042 | 2.741 |
| kagome / 32122 | 131 | 236 | 131 | 29 | skipped | — | 4.501 | 2.193 |
| honeycomb / 32367 | 190 | 264 | 190 | 4 | skipped | — | 3.411 | 2.159 |
| frustrated_square / king_graph / 32616 | 121 | 420 | 121 | 5 | skipped | — | 3.414 | 2.105 |
| shastry_sutherland / 33018 | 121 | 270 | 121 | 46 | skipped | — | 3.721 | 2.294 |
| cubic_lattice / 33219 | 125 | 300 | 125 | 14 | skipped | — | 4.016 | 2.177 |
| bcc_lattice / 33402 | 91 | 216 | 91 | 11 | skipped | — | 3.622 | 2.161 |
| weak_strong_cluster / 33587 | 128 | 1988 | 256 | 0 | 526 → 513 | 257 | 3.800 | 2.385 |
| planted_solution / 34404 | 133 | 175 | 133 | 11 | skipped | — | 3.411 | 2.258 |
| circulant / 3499 | 134 | 402 | 134 | 9 | skipped | — | 3.390 | 2.254 |
| spin_glass / 37302 | 160 | 12720 | 1440 | 0 | 2505 → 2471 | 1031 | 5.291 | 3.673 |
| hardware_native / 37603 | 128 | 352 | 128 | 64 | skipped | — | 4.166 | 2.173 |
| named_special / 37761 | 46 | 69 | 46 | 0 | 97 → 67 | 21 | 3.891 | 2.244 |
| generalized_petersen / 4083 | 126 | 189 | 126 | 35 | skipped | — | 3.872 | 2.353 |
| hypercube / 4755 | 128 | 448 | 128 | 6 | skipped | — | 3.544 | 2.291 |
| binary_tree / 4905 | 127 | 126 | 127 | 1 | skipped | — | 3.451 | 2.155 |
| tree / 5058 | 121 | 120 | 121 | 0 | 326 → 172 | 51 | 3.657 | 2.323 |
| johnson / 5242 | 120 | 1680 | 240 | 0 | 1276 → 1239 | 999 | 3.882 | 2.665 |
| kneser / 5411 | 126 | 315 | 126 | 5 | skipped | — | 3.870 | 2.245 |
| random_er / 6450 | 133 | 870 | 135 | 0 | 1172 → 1142 | 1007 | 3.744 | 2.682 |

## Reproducibility and review

Artifacts are under `results/codex/038-results-review`. The main auditor and
its helpers use only the standard library and never call a solver:

```sh
.venv/bin/python -B results/codex/038-results-review/final/analyze.py results/codex/038-initial-prefix-certificates --output results/codex/038-results-review/fresh-repeat
```

Root repeated this auditor into `root-repeat`. Summary, observations,
comparisons, workers, inputs and raw-hash JSON files were all byte-identical
to the first successful independent audit. The comparison record is
`root-repeat-comparison.json`, SHA-256
`d8012df2a150fa5fc0d98e6af43b3d8c6ad2c9c5331b6f204e3d9879e326ef8b`.
Raw observations, stage maps, skips and all original source mappings remain
unchanged. No audit error required a source change or a solver rerun.

| Artifact | SHA-256 |
|---|---|
| Frozen experiment manifest | `09bd7718cec3456ef5861c79f86065a582694902692c068b47240a7996f3aa3c` |
| Production source snapshot | `5dfc63cfb5bb2a674cb3e556e13d2b4d18a1857c7a8f296ba27cc2dd5075abc9` |
| Diagnostic snapshot | `ec34d4e18e0fb72870e473b92669959f968288cec95bf62e2deb28bce85e9d78` |
| Exact ideal Z12 target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Independent auditor | `f04fd0308718d4e5fd123a52e1691b1140c224722dd45feed52d3037c51f0422` |
| Integer-bound/state helper | `f3ceb39ac425fb788611528852f8454c3c00ec21c9cd80a6f597e66a1824c48f` |
| Independently repeated summary | `3ea85ff61cb1536c529069a47390b9222e3f3c7fe04df0628eda7710b40563f8` |

The useful lesson is limited and concrete: these degree gates excluded no
inputs; zero misses did not imply zero overload; and the prescribed initial
physical evaluations produced no exact lower-bound witness. Keep the negative
result. The valid optimality theorem remains available for a separately justified
future design, but this experiment provides no basis for deploying this initial
checkpoint, changing its gate after the fact, or claiming an all-family win.
