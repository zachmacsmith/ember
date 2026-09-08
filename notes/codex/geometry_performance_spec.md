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
