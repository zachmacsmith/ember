# Instrument one initial placement prefix, then stop

Planning only. No source edits, solver calls or screen execution occurred while
writing this specification. It implements only the proposed future mechanism
screen in [the termination design](certified_termination_design.md), contingent
on separate review. Experiment 037 is unchanged.

The [readiness audit](experiments/certified_termination_readiness.md) establishes
that all 34 fixed inputs pass the degree gates. Their existing final results do
not reveal whether the initial placement can attain the bound. The screen must
answer that question without running placement search or contact refinement.

## Capture the actual native prefix

Use the frozen native entry point for graph relabeling, grid setup and spectral
initialization. Do not duplicate those stages in a diagnostic constructor.
In a disposable worker process, compile an **in-memory copy** of `plane.arrange`
with one additional statement immediately after its first top-level assignment
to `best`, currently lines 371–372:

```text
best = (e_cur, copied_positions, books, misses, copied_axis_orders)  # unchanged
__capture_initial(best, info, rng, src_adj, grid, initial_orders, deadline)
```

The hook records the capture time, keeps the required objects alive, and raises
a dedicated `PrefixCaptured(BaseException)`. The diagnostic driver catches only
that type. Its deliberate base class bypasses native's `except Exception` at
lines 245–246, which otherwise turns the intended capture into an error return.
Do not catch all `BaseException`: interrupts and termination remain effective.
Restore patched function references in `finally`, including on ordinary errors.

At this point the original function has already seeded the scheduler at line
341, completed the readouts in the exact order `(1,0,1)` at lines 365–369, and
computed the initial proxy. It has not called `units`, consumed scheduler draws
for a proposal, or entered the search loop at line 376. Capture must assert
`asks=accepts=passes=0`, `readouts=3`, and exactly those three axis values.
The capture payload includes the full initial orders, spectral diagnostics,
positions/books/orders, proxy, misses, grid, integer source adjacency, exact
deadline and scheduler RNG state.

Install forbidden-call sentinels for `units` and `align_reinsert` in the copied
function's globals. No contact-refinement function may be called. Count packing
and physical-stage calls separately; a worker reaching a proposal is an
instrumentation failure, not a successful prefix observation. All 34 current
sources have at least 46 vertices and the target uses the typed grid, so the
trivial return at lines 345–352 is not expected. If it occurs, record a contract
failure instead of reconstructing an alternative prefix.

The AST transform must locate exactly one **top-level** `best` assignment and
leave the later nested assignment untouched. Removing the injected expression
from the transformed AST must reproduce the original AST, ignoring location
attributes. Retain both AST digests, the hook descriptor and transformed source
in the frozen diagnostic artifact. Compile from a namespace copied from the
frozen plane module; install timer wrappers/sentinels in that namespace before
compilation so the copied function actually uses them.

This differs from 030's callback at both `best` assignments
([diagnostic.py:219](../../results/codex/030-physical-checkpoint-diagnostic/diagnostic.py#L219)):
there is one terminal capture, no subsequent record, no reserved final slot and
no best-physical-output comparison. Simply passing `moves=False` is unsuitable:
`arrange` still performs its final bounded projection for an overloaded initial
state. The proposed screen must observe and skip that state before projection.

## One physical evaluation, or an explicit skip

After capture, the native stack is not resumed. The driver uses the captured
grid and adjacency produced by native, and copies the captured geometry/books
for the physical evaluation. It must not rebuild a grid or recompute contacts.
A transparent timer around native's `build_adjacency` retains its returned
adjacency; timers around spectral initialization and each packing readout retain
their diagnostics without changing return values or consuming random draws.

```text
if the degree-capacity gates fail: record skipped_capacity_gate
else run the native prefix to the single capture
if initialization fails or deadline expires: record that failure; stop
if initial overload > 0: record skipped_overload; stop
copy the captured positions and books
wire_seeds_exact(grid, positions, books[1], src_adj, books)   # once
complete_seeds(grid, chains, src_adj, captured_target_adj)   # once
fill missing isolates using native's original target iteration order
validate the constructed embedding using the existing physical validator
if invalid or late: retain failure and partial chains; stop
spur_prune(chains, src_adj, target_adj, deadline=common_deadline)  # once
invert native's source relabeling; validate against the original caller graph
record actual Q, L, validity and whether Q==L; stop
```

Positive overload is the prespecified cost throttle, not proof that an optimum
is impossible. Zero overload and zero misses do not replace physical validation.
Do not add a separate misses-based eligibility rule. Pruning is attempted once
only after valid construction; it may stop before a fixpoint at the deadline.
There is no completion fallback, alternative initialization, later checkpoint or
contact polishing. A valid but nonattaining output is retained as diagnostic
evidence only; it is not compared with the saved 036 result or selected for use.

Native's `labels=list(source_graph)` and the relabeling at lines 168–171 must be
preserved. Retain the actual caller graphs and their node iteration order; verify
the captured integer adjacency against that mapping before conversion. The
independent analyzer must invert the corpus normalization too, as the readiness
verifier does, and check all original source edges and isolates.

## Cold, second-invocation and deadline accounting

A proposed fixed screen contains all 34 inputs, seed zero, with the existing
spectral settings and nominal 1000-ask configuration; actual asks must be zero.
Use one fresh isolated worker and initially empty per-input JIT-cache directory
for each input. Perform a cold prefix followed by one second invocation in the
same worker/cache, giving at most 68 prefix observations and at most one physical
evaluation per observation. Record both outputs independently; do not select
between them. There is no unrecorded warm-up or full-search reference run.
This second invocation is called warm only with the explicit qualification that
the first invocation may have exercised only part of the code before a skip or
failure. A hard worker failure leaves the second invocation explicitly missing;
it does not authorize a fresh-process retry labeled warm.

Reload no saved placement. Both invocations recreate native's input copies and
grid and reset the same seed. Where both complete without a binding deadline,
their initial orders, complete captured state, scheduler RNG state and resulting
chain sets must agree exactly. Any difference is preserved and investigated;
warmth is not permission to choose a different initializer.

Use the native-only interpreter, fixed single-thread environment and MM/busclique
availability check plus import blocker. Freeze current implementation bytes and
all original input/target identities before any execution. Import the candidate
and compile the AST hook before the measured solver interval, matching the pilot
convention for implementation imports; process wall still includes those costs.
Lazy imports during spectral initialization and first-call JIT stay inside the
measured prefix. Graph loading and AST/hash preparation are separate recorded
setup costs, not silently omitted from process wall.

Each measured invocation receives a fresh 60-second common deadline beginning
before degree checks and input copies. Pass only the remaining timeout into
native. The transparent spectral and arrange wrappers clamp their received
deadline to that exact common timestamp, avoiding a new allowance at either
stage. After capture, every deadline-aware operation receives the same timestamp.
Check it before and after each physical stage and after final validation.
The scalar timeout argument and native's internally computed deadline can differ
by call overhead; record both, with the earlier common timestamp authoritative.
Deadline-sensitive failures are retained; exact prefix replay is claimed only
for completed, nonbinding arithmetic/RNG execution.

Record these nonoverlapping stage intervals plus the full elapsed invocation:

* degree checks and input copies; native setup (relabeling, adjacency, target
  layout and `TileGrid`), with component timers nested and not added twice;
* spectral initialization and its full diagnostics; the three packing readouts;
  remaining initial proxy/bookkeeping work;
* hook/copy/provenance overhead; conversion; completion and isolate handling;
  constructed validation; pruning; final validation.

Keep raw elapsed timestamps and separately measured solver CPU time. Serialization
after the terminal observation is recorded outside solver wall and inside process
wall; any diagnostic hashing performed before that observation consumes the
common elapsed budget and is not subtracted to manufacture timely success.
Report cold and second-invocation costs separately. A cold/warm difference here
includes lazy imports and other caching as well as compilation; it is not a
pure JIT estimate or an MM speed comparison.

Conversion/completion still have no internal deadline checks, and initial
packing is not preemptible inside a readout. A one-call quota is not a hard work
cap. Freeze an external worker-watchdog policy before launch and preserve timeout
records. Do not claim a timely certificate after either the common deadline or
the watchdog boundary. This screen does not estimate layout time saved; only a
later full-pipeline paired experiment could measure that.

## Source identities reviewed

These are the current bytes inspected for this plan, not permission to use newer
bytes without recording a new freeze. No code was imported to obtain them.

| File | Relevant entry / lines | SHA-256 |
|---|---|---|
| `factored/plane.py` | `arrange` 302; scheduler 341; initial packing 365; capture after 372 | `5459df9e949df9b0b2e855f100361770b054523542a67c06ece50cbfa1b9b1e8` |
| `factored/native.py` | setup 168–176; spectral 184; arrange 196; physical stages 208–225; final validation 241–243 | `4fd880391e9c5bf2f3ed4e6f238ce987070108a7fc5eb36cac6aa95d69b7cbc9` |
| `factored/field.py` | `TileGrid` 136; `wire_seeds_exact` 801; `complete_seeds` 960 | `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690` |
| `factored/spectral_order.py` | `spectral_orders` 102 | `02dd5ad22567f3b0e0d1b5836e1f55b975377de3f275a28823a3e518e5425b56` |
| `factored/polish.py` | `spur_prune` 43 | `d80ea929168eab6e08250b57c14eeca652f8174140dfd7c98d1aefb5f98340d3` |
| `embedding_backend.py` | `is_valid_embedding` 425 | `8816182c7faf1f37f287ea084e21856166500cd9467bdb61bb76997aca02daa5` |
| 030 `diagnostic.py` | two-hook transform 219–234; cold full-search reference 268 | `9cae70d71e81b5bd2aca5b98cec6589858655378ae41a12086b79fdc0926aee9` |

The first six paths are under `packages/ember-qc/src/ember_qc/`; 030's path is
`results/codex/030-physical-checkpoint-diagnostic/diagnostic.py`. Retain source
files and whole-file hashes as well as the exact transformed function source.

## Self-critique and review gate

The exception hook avoids duplicating initialization, but it is easy to swallow
the capture or accidentally invoke a copied function with stale global wrappers.
Exact AST identity, one hook count, explicit function provenance and forbidden
proposal calls are therefore required. Capturing RNG state must only read it.
Hash the original captured state before and after physical evaluation to detect
mutation; the geometric workspace is copied, and grid/source/target data used by
conversion must remain read-only. Preserve these checks even if they add measured
diagnostic overhead.

This first-prefix policy can miss every useful stopping point. The zero-overload
throttle can skip an initial state that projection would rescue; that limitation
is deliberate and must be visible. If no timely initial certificate appears,
retain that negative finding and stop the hypothesis at this schedule, rather
than selecting later checkpoints from these observations. Even a positive result
does not authorize deployment or imply net speed improvement across the corpus.

Status: ready for review only. No worker, frozen screen or implementation of
this instrumentation has been created or executed.
