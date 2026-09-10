# A065: exact array acceleration of interleaved root ranking

2026-09-09. **Before-code proposal for root review. No implementation or launch
is authorized by this note.** A061 remains the retained algorithm. This is a
bounded computational-cost experiment on the promising A064 mechanism.

A064's [broader screen](064_broader_transfer_results.md) has 22/22 independently
valid outputs, 21 Q improvements and one tie against A061. All 12 generated
inputs improve, across six families. Nevertheless it loses Q to MM on 16/21
common successes, including both nested relabelings in that denominator, and
all 22 added stages expire before closing their current epoch. Root ranking
uses 875.655/1074.385 added-stage seconds (81.50%). Sparse planar80 and grid128
instead spend 35.628/32.877 seconds reconstructing trees and 17.894/16.321 seconds
ranking. K100 spends 43.772 seconds ranking and completes just 12 rankings.
These are exposed development observations, not class-level confirmation.

## Hypothesis and distinguishing observations

**Hypothesis:** the existing all-root, all-owner neighborhood is useful but too
expensive to examine. Exact compiled BFS over compact arrays will buy enough
additional complete search to reduce several persistent ACL deficits after
paying for cold startup and conversion.

| Explanation | Observation that distinguishes it |
|---|---|
| Computational cost | Identical fixed-query roots cost less including adaptation; complete constructors reach useful later roots/owners and improve final Q. |
| Restricted neighborhood or representation | Much more of the unchanged search completes without further Q improvement; exhaustion would concern only this fixed witness/donor-tree/shared-path neighborhood. |
| Strict-Q acceptance | Completed reconstructions often preserve Q but cannot be committed; this is suggestive only. This experiment does not test whether a neutral move would enable a later gain. |
| Packing/compilation cost | Kernel savings are consumed by import, JIT, allocation, conversion or deadline overrun, especially on sparse inputs. |

Faster intermediate searches alone do not justify another local repair. A064
still fixes other-neighbor contact witnesses and donor trees and accepts only
strict Q improvements. A065 neither resolves nor conceals those limitations.

## Exact mechanism and pseudocode

Create a new compiled helper, a small operator entry point and a copied wrapper.
Subclass A063 `_Context` and override **only `roots`**. Reuse A064 `_Search`
unchanged. Copy its operator lifecycle with the new context and version metadata;
copy the A064 wrapper with only the operator/name/version changed. The sole
complete construction remains one unchanged A061 call followed by coordinated
operators on its evolving state. No monkeypatching old modules, registry edits
by this agent, changed old sources, independent solution selection, MM/busclique
input or dependency, source-family rules, hardware templates, or exact solver.

A063 `roots` runs one multi-source BFS per reduced neighbor in the induced free
subgraph. Each neighbor's seeds are its boundary sites at distance zero. It
accumulates distance sum, maximum and reach count, then sorts every eligible
free site by `(sum, maximum, seeded_target_rank)`. It retains no predecessor
paths. Preserve source/target normalization, seeded rank namespaces, boundary
sets, donor trimming, old-root reach assertion and final Python sort exactly.
An exact per-neighbor distance implies exact aggregate scores; the final seeded
rank is a permutation, so the entire ordered root list is then unique.

```text
on first root query in this context, under the existing stage clock:
    lazily import the installed NumPy/Numba helper
    pack ctx.target, in its existing order, once into CSR offsets/neighbors
for each root query:
    pack free sites into a Boolean mask
    invert boundary memberships into one seed list per reduced neighbor
    sort each seed list by the existing seeded target rank
    allocate zero sum/maximum/reach arrays; one distance and queue workspace
    for each reduced neighbor in the existing reduced order:
        initialize distance=-1 and queue with its zero-distance seeds
        while its queue is nonempty:
            compiled BFS advances at most 256 popped vertices
            update sum/maximum/reach exactly once per popped vertex
            retain the queue and distance arrays between dispatches
            publish aggregate completed work, then check the existing deadline
    check every old focus-chain site reaches every reduced neighbor
    collect every free site whose reach count equals the neighbor count
    sort by the unchanged Python key; check clock before publishing the list
continue the unchanged A064 one-root visit / strict-Q certificate / epoch logic
```

Use ordinary integer arithmetic, one `@njit(cache=False, boundscheck=True)`
advance kernel, no parallel reduction or fast-math setting. CSR and scratch
arrays belong only to this context; reuse the distance/queue workspace between
neighbors, not across simultaneous cached queries. Query scratch is discarded
when ranking finishes or stops; A064 caches only its usual completed roots and
domains. A degree-zero query must preserve the old all-free-sites behavior.
Validate array indices/shapes and Python-integer bounds before fixed-width
conversion, including `degree * max(0, target_size - 1)` and work-counter bounds.
Z12 has 4800 sites and 91728 directed target arcs; this does not require a
source-family assumption. No arithmetic fallback to another constructor.

The 256-pop value is a **clock-observation interval**, not a query/owner/root
limit. No queue entries or eligible roots are dropped at a dispatch boundary.
Record maximum cold and noncompiling dispatch duration; compilation is not
cooperatively interruptible. A late dispatch may publish diagnostics but never
a completed query or embedding after the existing admission check. Keep the
unchanged outer deadline, final-validation reserve and late-return accounting.

## Cost accounting and focused risks

Keep the existing `root_search` phase and A064 query/root-generation timing so
old passive accounting remains usable. Add nested import, one-time target pack,
query pack, allocation, compilation-bearing dispatch, later kernel, root export/
sort and residual wall/CPU. Never add these nested fields to the enclosing total.
Compilation-bearing dispatch includes its executed kernel work; do not subtract
an estimated compiler cost from the headline. Cold process time remains primary.

Accumulate BFS pops and scanned arcs in native integer counters. Scanned arcs
can add `offset[q+1]-offset[q]` once per popped vertex; do not call a Python meter
per edge. Publish all completed counter deltas together before checking time,
so interruption cannot lose already executed work. Label new packing and
membership counts separately: inverting boundary memberships deliberately
removes the old degree-times-boundary scan. Work counters are diagnostics only.
Keep actual allocated-array bytes/payload counts, not a false interpretation of
the historical worker `ru_maxrss` field as candidate-specific memory.

Reuse the old independent validator, import guard and A064 correctness tests;
add only these new-risk checks before the packet:

1. Compare complete roots with the pinned Python method and scores with a tiny
   independent unweighted-BFS specification. Include equal sums/different maxima,
   final rank ties, disconnected free components, shared boundary seeds, empty
   neighbor sets and source/target relabeling. Retain old-root invariant errors.
2. Force chunk boundaries at 1, 2 and 256 pops in tiny fixtures; compare every
   final root and completed BFS count. Deadline injection after a dispatch and
   before root publication must retain the previous certified incumbent. Test
   safe integer bounds and rejected malformed array indices before native code.
3. Use the existing tiny valid A064 fixture to compare the entire finite commit
   sequence and final embedding with clocks that do not truncate either run.
   This checks subclass integration, one A061 call, unchanged epoch invalidation
   and no extra imports. Do not rerun the exhaustive old correctness suite.

Available pattern: B028 `compiled_joint_root.py` uses lazy imports, uncached
Numba kernels, checked arrays, bounded dispatch and batch counter publication.
It is a design reference, not a dependency of A065. Its constructor's measured
packing/conversion regressions warn against recreating Python arrays or counters
per edge. Existing cluster records pin NumPy 2.2.6, Numba 0.65.1 and llvmlite
0.47.0; no installation or warm-up run is proposed.

## Cheap paired query falsifier, then complete constructors

Root freezes one query from each of six saved **candidate-only A061** states:
g0001 ER80, g0008 BA160, g0006 planar80, g0013 grid128, g0016 K100 and g0017
hidden singleton control80. Exclude the hidden witness; independently validate
these entry maps. Choose each state's first rankable owner in A064's initial
decreasing-chain-length/seeded-rank order, applying the unchanged strict-gain
bound. Record exclusions and input hashes before timing. These fixed states
are diagnostics, not replays of the original A064 trajectory.

Run two separately measured six-query packets on the same host (proposed hyde06),
one Python and one compiled, each in a fresh native process. Freeze query/arm
order before launch. Each query gets its corresponding context, so the packet
charges all six target packs; a constructor packs once per context. Lazy import,
JIT, conversion and output are charged. Record each query, cold packet and whole
process wall/CPU. Later-query timing is secondary; one packet's compiled module
reuse does **not** predict six cold constructors. No warm-up or file cache.
Use a 60-second packet allowance and existing detached supervision/retrieval;
retain every failure, interruption and unattempted query. This is a measurement
bound, not a candidate work limit. No expensive serialization framework is needed.

Require exact full ordered-root-list agreement on all six queries and unchanged
state fingerprints. A mismatch stops this revision. Report every case's full
adaptation cost, first compilation and later dispatches. If later adapted queries
do not improve in ranking-dominated cases, retire this cost-only mechanism.
Otherwise compare measured cold overhead and query savings with actual A064
query counts, explicitly as an uncertain repayment estimate. Plausible repayment
supports the immediate complete screen even with a first-query regression; keep
sparse-case regressions visible. No universal speed-ratio gate. Root may authorize
implementation, focused checks and this bounded packet together after review.

Suggested next frozen complete screen: the six diagnostic structures, two new
development structures at an intermediate size from different deficient families
(for example WS100 and SBM100), plus the existing grid relabeling as a nested
observation. Root owns generation, exclusion records and exact freeze. Run A065,
A064 and MM independently, seed0, 60 seconds, paired on one host: 27 calls.
Candidates start their own sole A061 construction; the diagnostic maps are
absent. No MM result or hidden witness enters a candidate. This is exploration,
not the untouched confirmation set or a change to historical experiment rules.

Report independent-valid success, Q/ACL, within-chain variance and all-attempt
solver/CPU/process time first, preserving every MM deficit. Compare base maps/Q
before attributing differences to ranking. Also report time to admitted Q,
complete rankings/reconstructions, owner coverage and final-epoch closure. More
search without better complete Q on any input contradicts the quality hypothesis
and stops acceleration-only refinements; earlier natural completion at unchanged
quality is a distinct speed result. Q gains on several structurally different
inputs including a fresh one support replicated breadth, provided no success
loss is concealed. All regressions require explanation, not aggregation away.
Across-seed variability, all Ember classes, fresh sizes, and untouched confirmation
remain required before promotion or a research-paper claim.

**Self-critique.** This optimizes a measured bottleneck but invents no new search
capability by itself. Large query throughput gains may expose fixed witnesses,
greedy shared paths or strict-Q acceptance as the actual quality barriers. Sparse
cases already spend most time elsewhere. Cold compilation can shorten useful
search or overrun finalization; denser arrays and more completed reconstructions
can shift cost into validation, packing or logging. Exact query equivalence
implies the same complete search sequence only from the same base state without
clock truncation. Wall-bounded fresh constructors may stop at different prefixes.
Do not describe a later prefix or a faster kernel as an all-class runtime win.

Pinned sources inspected before this proposal:

- A063 context: `217436640d2ae9e6266b58c8d20aa7fc0333acbe1ca2cc35140688e899876854`.
- A064 search/operator: `0d6f442ddb8473b5225b119f304e8db9aff10c74e71a0753fc920bc5ebfaf2e4`.
- A064 wrapper: `1b78eeecadb96aa67edddafdb64316f42b54ea02860d46826166c16fbd7f27d4`.
- B028 kernel reference: `c729ccd815262ec9ebf18eaa24f33544719c53ca610ecd7d823fbc63456564c8`.
