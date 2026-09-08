# Skip unused neighbor preparation during horizontal reinsertion

Design, dependency review, and self-critique saved before implementation,
2026-09-08 UTC. This is a performance change to the existing geometric search;
it changes no proposal family, objective, contact ownership, or acceptance rule.

## Evidence and limited opportunity

Experiment [014](experiments/014_native_profile.md) measured layout search as
85.76% of aggregate warm native time on its nine small development cases. Its
warm ER-80/300-evaluation profile attributes 0.74439 seconds to `align_reinsert`
out of 1.50474 seconds of layout; its two `_arm` calls account for 0.47802 seconds
within that total. These cumulative times overlap and must not be added. The
already compiled packing DP accounts for only 0.00815 seconds. Contact reuse from
[021](experiments/021_contact_reuse.md) has already removed a different repeated
calculation and is retained.

`field.align_reinsert` constructs directed adjacency arrays and partitions/sorts
every source vertex's neighbors into the two carried subsequences for **both**
axes. The horizontal move (`axis=0`) uses frozen horizontal contact sets instead.
It never consumes these source-neighbor arrays during pricing. Thus it can skip
their construction without replacing arithmetic or introducing a compiled kernel.

The saved 014 profile has exactly 48,300 `argsort` calls from 300 reinsertion
requests on 80 vertices: `2*n+1` per request. There are 145 horizontal requests
and 155 vertical requests, so the change removes 23,345 of those sorts in that
trajectory. That operation count is not a speedup measurement.

A bounded current-code diagnostic used the same ER-80 input and Z12 target,
random initialization, seed zero, 300 evaluations, and no conversion/refinement.
It made one cold geometry call, one warm call, and one warm call with two timers
inserted in memory around the existing neighbor-preparation block. No optimized
implementation was run. The two timers enclose `heads` through `maxQf` in
`align_reinsert`; the rest of the function is unchanged.

| Existing-code call | Layout wall (s) | Evaluations | Readouts |
|---|---:|---:|---:|
| first call, empty JIT cache | 2.30999 | 300 | 403 |
| warm original | 1.00385 | 300 | 403 |
| warm with block timers | 0.99593 | 300 | 403 |

The timed block consumed 0.053742 seconds over 145 horizontal requests and
0.072156 seconds over 155 vertical requests. The removable horizontal part is
**5.40% of warm layout time** in this one case. Removing all of it, with zero
replacement cost, would yield only about **1.057 times** the layout throughput.
That is a ceiling calculation for this sample, not an observed optimization gain.
It cannot resolve 019's factors-of-ten runtime deficits. It remains a concrete
small improvement that adds no JIT compilation cost.

All three calls returned identical positions, complete geometry, accepted trace,
and non-time diagnostics. Their canonical JSON SHA256 was
`3789ce2ce7ff2d9a02bd742ffaa207bdf9e5597082423e5a463f555e276fd9bc`.
The diagnostic does not independently hash every declined proposal. The cold/warm
difference includes first-use costs and is not a precise attribution to JIT alone.
Graph reading and target-grid setup were outside these layout times. The
temporary JIT cache was empty before the first call and reused thereafter.
The experiment used the isolated `.venv/codex-native/bin/python`, and only graph
records from 014; neither MM results nor saved embeddings were inputs.

Provenance: `field.py` SHA256
`1778a3af4670c34a8acdc51ec7be000195bb208f0213399203e4982c498bb18c`
(also the exact 014 field source); current `plane.py` SHA256
`5459df9e949df9b0b2e855f100361770b054523542a67c06ece50cbfa1b9b1e8`.
The source/target record hashes and old profile artifact are recorded in 014.
The performance specification was finalized against repository commit
`d735d157eb764b02d1d139c55b8e3123238364b6`; the authoritative code identities
for the diagnostic are the file hashes above.

## Dependency review and proposed code change

No public API changes. Keep `align_reinsert(...)` and all return conventions.
In its current source around lines 1615–1651, restrict the directed-neighbor
construction to `axis == 1`:

```text
retain S, R, slot_of, inS, rpos, qpos, r_slots, q_slots and scaled slot gaps
if axis == 1:
    build heads/tails, ha/ta, ta_s and bnd
    build sorted nRi/nQi and aligned xRn/xQn
    derive minRv, minQf, maxQf
if axis == 0:
    construct net_stats from the supplied frozen contacts, unchanged
retain existing vertical suffix preparation under axis == 1
inside each forward/reverse _arm:
    if axis == 1:
        derive minQv and define/use the oriented Q-neighbor views
    retain transition construction, rectangles, prefix sums, recurrence,
        backtracking, identity-path scoring and final comparisons unchanged
```

| Data | Actual consumer | Treatment |
|---|---|---|
| S/R, carried slots and side ranks | both axes and backtracking | preserve |
| neighbor R/Q arrays and minima | vertical transition costs and crossing rectangles | build only for axis 1 |
| `minQv` inside `_arm` | vertical activity and crossing tests | move under the same axis guard |
| frozen `net_stats` | horizontal crossing rectangles | preserve exactly |
| transition matrices and merge recurrence | both axes | preserve exactly |
| source/target geometry and contact assignments | downstream packing/conversion | no change |

The currently unconditional `minQv` assignment is the one eager read of the
otherwise unused neighbor minima inside a horizontal arm. Guarding only the
outer construction would therefore raise an error; it must be guarded too.
`_qview` reads the same arrays, but is called only in the vertical transition
branch. Keeping its definition in that branch makes this dependency explicit.

For `n` vertices and source degrees `d_v`, the skipped preparation costs
`O(n + sum d_v + sum d_v log d_v)` per horizontal request, including many small
arrays and Python list/dictionary operations. It uses `O(n + sum d_v)` temporary
storage. Frozen contact-net processing and the `O(|R|*|S|)` transition/recurrence
work remain. No source-family condition or cross-proposal cache is introduced.

## Self-critique before implementation

1. **The measured opportunity is small.** The 5.4% fraction is one warm geometry
   case after contact reuse, not an Ember-wide gain. Total native savings are
   smaller, and source density/group sizes change the fraction. Preserve all
   predeclared cases, including any noisy or negative timing differences.
2. **Dead data can have an eager consumer.** `minQv` is such a consumer. Audit both
   orientation arms, singleton slot-cost mode, and early declines before removing
   preparation. Source mappings with side-effectful `.get` methods are not a
   supported semantic contract; ordinary source adjacency must remain unmodified.
3. **Do not use this cleanup to change arithmetic.** Replacing the recurrence,
   rectangle update order, sorting policy, floating operations, or tie tolerances
   would create a different and harder equivalence question. All remain literal
   existing operations in this bounded change.
4. **A faster deadline-limited run can change output.** Exact trajectory equality
   is required at equal evaluation counts with an ample deadline, not when one
   version fits more work before a deadline. Numerical comparisons must include
   both axes, both block orientations, and singleton slot-cost vectors, not only
   final ACL or successful embeddings.
5. **Cold costs remain.** This change adds no new JIT function, but existing
   packing compilation still dominates some short calls. Warm gains cannot be
   presented as equal cold gains or evidence that the MM runtime gap is closed.

## Approved implementation and verification protocol

After saving this specification, implement only the conditional preparation in
`field.py` and a new `tests/algorithms/test_reinsert_preparation.py`. Keep
`plane.py`, `native.py`, the pilot, and the frozen 026 source unchanged. Save a
pre-edit reference before touching `field.py`.

Use the existing brute-force reinsertion tests as mathematical checks. Add exact
differential proposal checks against frozen pre-edit source for both axes,
forward/reversed groups, singleton slot costs, tied coordinates, and early
declines. Confirm complete non-time trajectories against the frozen reference;
also record actual proposal sequence hashes and full physical embeddings in the
bounded native timing diagnostic.

Predeclared timing inputs are **all three** serialized 014 sources: complete-40,
ER-80, and grid-64, each at **1,000 evaluations**, seed zero, ideal Z12, random
initialization, no contact refinement. Each source/version gets a fresh process
and empty JIT cache, followed by one cold and one warm call: twelve calls in six
workers, with every case retained. Freeze before source, create after by replacing
only `field.py`, and use identical instrumentation. Keep a 30-second native
allowance and 105-second worker watchdog. Interleave and record before/after
worker order; record graph, source, proposal, trace, and embedding hashes.
Preserve source/target validation and forbidden-embedder import guards.

Store scripts, snapshots, timing data, exact reproduction commands and summary
under `results/codex/028-reinsert-preparation`, then append measured outcomes here.
This protocol authorizes performance evaluation; it makes no algorithm-quality
or novelty claim.

## Implemented change and verification

Only the directed-neighbor preparation, its minima, and the `_arm` neighbor-view
setup are now guarded by `axis == 1`. The vertical branch performs the same
operations in the same order. Horizontal frozen-net construction, both arm
orientations, transition costs, prefix sums, comparisons, and backtracking remain
unchanged. No compiled function, cache, API, constructor, or stopping rule was
added. `plane.py`, `native.py`, and the pilot were not edited in this task.

The new `tests/algorithms/test_reinsert_preparation.py` contains 24 exact proposal
regressions, eight exact singleton cost-vector regressions, four direct checks
that only vertical pricing reads source-neighbor views, and eight early-decline
checks. The proposal examples include accepted forward and reversed blocks,
rejections, half-integral coordinates and ties, and bar costs zero/eight. Their
expected values were generated from the frozen pre-edit source, before editing.
They reside directly in the test module, so the tests do not require ignored
result artifacts or a git subprocess. They are regression data, not embeddings
or tables used by the algorithm. Input and contact mutation are also checked.

Combined with the existing brute-force reinsertion tests:

```sh
PYTHONPATH=packages/ember-qc/src .venv/bin/python -m pytest -q \
  tests/algorithms/test_reinsert_preparation.py \
  tests/algorithms/test_field.py::TestAlignReinsert
```

Result: **55 passed**, one existing dwave-networkx deprecation warning, 1.02 seconds.
`git diff --check` also passed for the owned change.

## Frozen twelve-call comparison

All artifacts are in
[`results/codex/028-reinsert-preparation`](../../results/codex/028-reinsert-preparation).
The before snapshot was saved before editing; after was copied from it, replacing
only `field.py`. The worker is a copied diagnostic harness from 021 with the
predeclared three inputs and 1,000-evaluation budget. Both versions have identical
proposal/contact-count/accepted-trace instrumentation, which adds some overhead.
Snapshot hashes, inputs, worker configurations, guards, and every output were
independently checked by `analyze.py`.

All **12 calls** are valid, timely, and free of attempted/loaded MM or busclique
dependencies. On each input, all four calls have exactly equal full embeddings,
actual proposal hashes, contact rebuild counts, accepted traces, layout orders,
and complete non-time diagnostics. Only `wall`, `bookmark_wall`, and `layout_wall`
are excluded from diagnostic equality. The independent validator checks every
original source and target adjacency. The full results and hash audit are saved
in `analysis.json`; no input or failed result was dropped.

| Input | Actual evaluations | Qubits, before = after | Cold solver before → after (s) | Warm solver before → after (s) | Warm layout before → after (s) |
|---|---:|---:|---:|---:|---:|
| complete-40 | 515 | 156 | 2.13403 → 1.99791 | 1.04109 → 0.93587 | 0.88475 → 0.77762 |
| ER-80 | 1,000 | 273 | 3.91688 → 3.90620 | 2.76529 → 2.57413 | 2.60625 → 2.41670 |
| grid-64 | 1,000 | 89 | 2.86744 → 2.71146 | 1.77792 → 1.64046 | 1.63721 → 1.49540 |
| total | — | unchanged | 8.91834 → 8.61557 | 5.58429 → 5.15046 | 5.12822 → 4.68972 |

Observed total solver reductions are **3.39% cold** and **7.77% warm**; warm layout
decreases **8.55%**. Warm solver reductions are 10.11%, 6.91%, and 7.73% for the
three rows respectively. Total solver CPU decreases 5.44% cold and 7.80% warm.
These are sums over the three declared calls, not averages over Ember classes.
The earlier 5.40% removal ceiling concerned ER at **300** evaluations; it was not
a ceiling for these different trajectories or budgets.

The local host was not reserved. Each version/input has only one fresh worker,
one cold call, and one warm call; the measurements do not estimate uncertainty.
Seed 28001 fixed the pair/within-pair shuffle before timing and happened to place
`after` then `before` in **all three pairs**. That order is preserved in
`execution_order.json`; possible time drift is not balanced away. The first ER
after cold call also spent about 0.171 seconds more wall than CPU time, versus
about 0.001 seconds in its before call. This limits conclusions from the tiny
ER cold-wall difference. No new JIT work was introduced, and all pre-existing
packing compilation remained inside the cold allowance.

This evidence supports keeping a small behavior-preserving optimization. It does
not close the MM runtime gap, estimate scaling to larger source graphs, establish
graph-class-wide timing improvements, or improve ACL. More substantial search
optimization may still be needed, with a separate specification and equivalence
review.

| Artifact | SHA256 |
|---|---|
| Before source map | `f40241742585d1f3212358d4882e5f72d0a9567b195d4bedf0a525a3287ece80` |
| After source map | `a41ac4895fdfa324dec85f27a4aa52323e52180aa8a15a59f77835a3afbcdc27` |
| Complete result-file hash map | `b005e2fce3352a0253bb5f4784ffcfbb8b44ae9ea8e83fa3fc6e8e322c4da8b1` |

Reproduction uses fresh output directories and the already frozen source, avoiding
new working-tree changes. The stored manifests preserve the interpreter's symlink
path; moving to another checkout/machine requires explicitly updating that path
and reporting the changed environment. Run from the repository root:

```sh
.venv/codex-native/bin/python results/codex/028-reinsert-preparation/reproduce.py \
  results/codex/028-reinsert-preparation-repeat
.venv/codex-native/bin/python results/codex/028-reinsert-preparation-repeat/run_pairs.py
.venv/codex-native/bin/python results/codex/028-reinsert-preparation-repeat/analyze.py
```

`run_pairs.py` refuses to overwrite results and creates an empty per-worker JIT
cache. Its environment sets `PYTHONHASHSEED=0` before process startup and numerical
thread limits to one. The 30-second native allowance and 105-second worker
watchdog remain in force. Re-running the original directory's `analyze.py` checks
the original results and rewrites only its derived `analysis.json` summary.
