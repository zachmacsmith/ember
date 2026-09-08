# 040 locality instrumentation implementation

Implementation of the reviewed
[all-input locality design](physical_locality_diagnostic_review.md), with its
self-critique and independent clarifications saved first. No production file,
prepared input, 039 artifact or algorithm configuration was edited. Corpus
execution remains unauthorized pending root review; the controller cannot run
without a later explicit reviewed execution manifest.

The new code is confined to
[`results/codex/040-physical-locality/diagnostic`](../../results/codex/040-physical-locality/diagnostic).
`common.py` provides input checks, isolated imports and transparent tagged JSON;
`instrumentation.py` verifies and compiles the two capture hooks and terminal
raw-wire reference; `geometry.py` performs reference/capture; `offline.py`
reconstructs and compares per-line replay; `controller.py` supervises phases;
`report.py` accounts for every input and refuses complete-corpus timing totals
when records are missing or incomplete. None is a new embedding algorithm.

## Exact observation contract

The reference uses the original frozen `arrange` function body. Both calls use
the same wrappers for `units`, actual align invocations/results, readout timing
and spectral deadline clamping, with existing `trace=True`. The capture function
adds only a hook after initial `best` creation and after the complete adoption/
bookmark block. AST removal restores the original exactly. There are no added
search expiration checks or changes to acceptance, ordering or RNG draws.

The worker feeds only the frozen canonical `expected_normalized` graph to native.
Original label maps and graph JSON remain offline evaluator inputs. This matters
for `ember_37761`, where original JSON node insertion order differs from the
canonical solver order. Hashes independently verify original-to-canonical
topology before original-edge physical validation.

Each call receives spectral seed/scheduler seed 0, `snap=True`, 1,000 asks and
60 seconds including its copies, input hashes and observation work. Both searches
run to the original stop; copying ends after initial plus 32 adoptions. The
complete `arrange` result is recorded before a dedicated `BaseException` stops
native ahead of all physical work. Conversion, completion, pruning and contact
entry points have counted rejecting sentinels. Final projection remains part of
the unchanged search return, never an extra adopted-state observation.

The actual unit/proposal streams are length-framed SHA256 streams. Full changing
align inputs and returned orders/failures are encoded; fixed source adjacency
is recorded once. Both calls compare final non-time geometry/books/orders,
layout trace/counters, initial orders, static wires and final scheduler RNG.
Replay equality is asserted only for complete, timely, matching pairs. The
reference is an instrumented reference environment, not an uninstrumented timing
control. The second call is a same-worker second invocation; no blanket warm-JIT
claim follows from its position.

Snapshots are deep copies of ordered positions, full books, carried orders and
event metadata. JSON uses explicit dict/list/tuple/set/array tags, hex floats,
array dtype/shape and values. It preserves dictionary/list ordering, array value
bits and signed zero; it rejects nonfinite values and duplicate decoded keys.
It is not pickle and does not execute decoded objects. Source arrays here are
small contiguous coordinate/bar arrays; runtime-only memory addresses or strides
are not inputs to the converter. Geometry copies remain inside the common
deadline; tagged encoding/publication after each return stays inside the outer
worker allowance and is timed separately.

## Pure-wire reference and cache

The independent scalar book reconstruction uses source adjacency and carried
y-rank, clipped/unbounded bar rules, half-to-even rounding, `snap=True` widening
and minimum occupancy span. It checks the captured books before independently
deriving complete per-line inputs. It does not trust a signature from a live
callback. Full sorted `(a,b,v)` and complete crossing targets retain fallback and
tie behavior.

The frozen corrected035 converter is unchanged. The full reference adds a
terminal callback immediately before `_ensure_seeds`; removing it restores the
original wire function AST. Read-only per-line timers preserve actual arguments,
return values and ordering. The result contains every source key, including
empty chains, all actual ordered fragments, claimed qubits and both counters.

The cache is scoped to one immutable wire map/stride, whose physical partition
is verified. Each dirty line starts with **empty local claims**, releasing its
previous assignment, and reruns the existing converter over every current arm
on that line. New and removed lines are explicit. Global merge uses orientation
`(1,0)`, then ascending line, preserving local emitted list order. A no-op update
reuses the existing entry without a converter call. A changed fallback endpoint
invalidates a signature even when required crossing targets are unchanged.

For every captured state, one full and one cache replay are compared. Their order
alternates by state index after full-first initial evaluation. A candidate cache
is published only after timely, complete ordered-output/counter equality and
independent physical checks finish. Physical invalidity is retained as an
observation rather than rescued; structural cache disagreement is an error.
Any exception or deadline before that gate terminates the incremental sequence
and retains the previous complete cache. There is no count-only approximation,
new DP state cap, seeding, completion, pruning or contact polishing.

## Timing, process bounds and failure recording

The copied `supervision.py` and `watchdog.py` are byte-identical to the reviewed
038 versions; `reused_provenance.json` records exact source paths/hashes. Geometry
has one absolute 150-second fatal alarm armed before heavy imports. It never
resets between its two common 60-second invocations. Reference publication occurs
before capture starts. A killed capture's unflushed RAM snapshots are unavailable,
not falsely described as saved partial observations.

Offline analysis is a new process with its own absolute 60-second alarm armed
before heavy imports/input decoding. Each phase also has external process-group
supervision, five-second cleanup grace, inherited advisory run lock, exclusive
logs and atomic no-clobber observations. There are no automatic retries or
replacement writes to observations. Mutable controller status is separate. Direct
children are reaped; same-group descendants are signaled. Process-group escape
and reaping orphan zombies are outside the supervisor's guarantees.

Per-state records separate diagnostic book reconstruction, signature construction,
dirty conversion, merge/cache bookkeeping, full reference, equality and
original-graph validation. The update subtotal includes construction of line
signatures from the verified existing books, dirty conversion, merge and commit;
it excludes diagnostic book verification/reference/equality/validation cost. All remain in
offline phase wall time. Initial cache construction is reported separately and
in amortized totals. Raw full/cached outputs and per-line timing/counters remain
available for independent review.

Captured adopted-transition time starts at the actual align wrapper and ends
at the post-adoption copy hook, before copying. Proposal recording time is
separate. Specifically, `timers.wrapper_wall` measures stream serialization/hash
work; it does not separately attribute every wrapper counter update, timer call
or list append. Those costs remain in common/transition/phase wall. The stream
hashes and counts are retained, not every raw unit/proposal event, so later audit
can compare stream identities but cannot inspect unsaved event elements. No
recording, copy or JIT overhead is subtracted to extend a deadline.
The all-input report preserves every missing/error/late record and applies the
predeclared cost falsifiers only with complete coverage. These are diagnostic
cost comparisons for early adopted proposals, not timing or quality claims
about a proposed production objective.

## Focused evidence and preserved failures

`checks/attempt-001` preserves an import-guard bootstrap failure before any
algorithm call: matching the entire module name incorrectly rejected Ember's
lazy registration wrapper. The guard now uses the reviewed038 rule blocking
external embedding-package roots; the native environment lacks those packages.

`checks/attempt-002` preserves two test/instrumentation failures. A class-stored
reference callable was accidentally bound as a method; it is now a staticmethod.
The mutation check compared `Graph.copy()`'s neighbor iteration with its original
graph, although NetworkX can reorder neighbors while making the copy. The
correct check records copied arguments immediately before native and compares
those same arguments afterwards, while separately checking caller inputs.
No source algorithm was changed to satisfy either check.

The first passing run, `checks/attempt-003`, has 14 checks. Its sole unmodified
native fixture is a six-vertex path on ideal Z2: reference and capture both
naturally stop after 40 asks and three adoptions; all four captured states replay
exactly through offline conversion/cache reconstruction. This validates the
declared mechanism only and supplies no Zephyr12 performance observation.

`checks/attempt-004` adds a synthetic proposal stream forcing 40 feasible no-op
adoptions, proving that copying stops at 33 while all 40 proposals continue,
and a common deadline exhausted before native begins. All 16 checks pass. The
remaining checks exercise fallback/boundary/tie behavior, empty keys and ordered
fragments, missing/new lines, no-op reuse, staged interruption/rollback, failed
equality, independent physical-edge validation, inherited lock contention,
reference survival after killed capture and distinct fatal phase alarms.

## Independent review corrections and final author evidence

The frozen target's coordinate records now independently determine expected
wire membership, physical positions, dimensions and linear qubit identity.
Merely preserving a partition is insufficient: swapped physical sites and altered
dimensions are rejected. Snapshot checks bind canonical adjacency key/list order,
copy counts, initial/adopted event sequence, asks, axes/units and final counters.
Published observations are checked against the geometry publication hashes when
available. A missing final publication receipt is labeled unattested partial
data, never complete corpus evidence.

Book verification and offline tagged encoding/JSON publication have explicit
timing fields outside the candidate update subtotal. Line statistics distinguish
old, new and union keys, actually reconverted lines and removed lines. The dirty
fraction uses the union denominator; the conversion fraction uses current lines.
This avoids a misleading fraction above one when an old line is replaced.

The controller follows the copied `solver_inputs` ledger order verbatim, verifies
34 unique names against the canonical file set, and records each phase's absolute
finish, elapsed time and overrun. The corpus report now requires verified
publications, complete matching timely geometry, and clean timely/reaped
geometry/offline worker exits before publishing all-input cost conclusions.
Killed or late workers can leave useful durable records, but those records are
explicitly incomplete. Zero-transition and zero-denominator comparisons are
undefined, rather than a manufactured `0 >= 0` rejection.

The final full author run before the cooperative-failure diagnostic addition,
[`checks/attempt-008`](../../results/codex/040-physical-locality/checks/attempt-008),
passes **21 checks in 2.974 seconds**. Its summary records every diagnostic source
hash and environment. Earlier attempts remain developmental evidence; this run
finished with its then-current code bytes unchanged. New tests cover target-coordinate
corruption, capture/publication corruption, actual fixed phase allowances, late
geometry, differing replay streams, a killed/late offline phase, preserved
partial results and undefined zero-transition ratios. No broad benchmark ran.

The literature agent's separate
[`independent-offline-review/attempt002`](../../results/codex/040-physical-locality/independent-offline-review/attempt002)
passes eight tests, including 36 tiny converter/cache pairs, independently
computed scalar books, no-op reuse, second-line rollback, same-Q ordered-chain
mismatch, target/snapshot corruption and a synthetic timing-separation check.
It imports neither Ember nor an embedding solver and observes no corpus input.

A final evidence-preservation review added current-line identity, completed-line
records and elapsed work to caught cache failures, and uncertified partial
chains/claims to caught raw-line failures. Failed rows retain those diagnostics;
they never publish a candidate cache. This does not recover RAM after fatal
termination or change successful conversion. The focused
[`checks/partial-interruption-002`](../../results/codex/040-physical-locality/checks/partial-interruption-002)
passes four checks in 0.033 seconds on the final bytes, including an exception
after a converter has written partial claims and an interruption during cache
merge after line work completed. It invokes no native constructor. The full
suite now contains 23 checks for root's final environment repeat.

The benchmark audit agent independently passed eight phase/report checks under
[`040-geometry-review/attempt001`](../../results/codex/040-geometry-review/attempt001),
without scientific or production-module imports. Geometry/controller/report
bytes were unchanged by the final cooperative-failure additions. The source
identities and latest preparation preflight are linked from the additive
[`author_ready_002.json`](../../results/codex/040-physical-locality/checks/author_ready_002.json),
which is a review record, not execution authorization.

Safe additive reproduction (choose fresh output and JIT paths each time):

```sh
env PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 \
  NUMBA_CACHE_DIR=/Users/dabh/ember/results/codex/040-physical-locality/checks/jit-root-repeat \
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1 \
  .venv/codex-native/bin/python results/codex/040-physical-locality/diagnostic/checks.py \
  results/codex/040-physical-locality/checks/root-repeat
```

Root owns final environment preflight, execution freeze and launch. No
`execution_manifest.json`, corpus controller run or corpus observation was
created by this implementation task.
