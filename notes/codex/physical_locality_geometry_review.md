# Independent 040 geometry and lifecycle implementation review

2026-09-08. The reviewed geometry/controller behavior is consistent with the
[accepted diagnostic protocol](physical_locality_diagnostic_review.md) after
the corrections below. This is bounded implementation clearance, not evidence
of a useful physical objective, an execution manifest, or a performance result.
Root owns remote preflight and the single launch; the separate offline review
owns reconstruction and cache correctness.

I read the complete geometry/controller/supervision/watchdog code and the
report's eligibility logic. I also read root's fixed-run remote controller
without executing it. The independent checks performed here contain no graph
embedding, prefix, MM, corpus, SSH, or cluster lifecycle calls.

## Findings resolved before execution

1. **Input order.** The first controller sorted filenames, conflicting with the
   protocol's copied ledger order. `controller.py:23` now takes the exact
   `identity.solver_inputs` sequence and verifies that it contains the 34 unique
   normalized graph keys. This ordering is distinct from 039's randomized task
   order. Within each graph, `common.py:122` inserts the normalized record's nodes
   before edges, and `geometry.py:250` loads the normalized input. All 34 saved
   node vectors are exactly `0..n-1`. Original-label JSON is an evaluator input;
   feeding it to the solver could change insertion order, particularly for
   `ember_37761`.

2. **Timing conclusions after interference.** Offline completion formerly did
   not require an accepted reference/capture comparison. `report.py:67` now
   requires complete, timely geometry, matching final state/initial orders/wire
   data/source adjacency/proposal digests/RNG, and an accepted comparison.
   Missing or mismatched geometry preserves observations but prevents complete
   input and all-input timing conclusions.

3. **A publication is not a successful process exit.** The report now reads
   both phase summaries and requires zero exit, reaping, no external timeout,
   no kernel alarm, no phase overrun and no missing invocation. Publication
   verification must also succeed. A worker that publishes and is then killed
   cannot contribute accepted timing evidence. Missing/skipped phase summaries
   are explicitly ineligible; detailed skip reasons remain in controller state.

4. **Externally late zero-exit workers.** `controller.py:68` now records the
   actual monotonic finish, elapsed time from the absolute phase origin,
   overrun and lateness. A successful `wait()` or zero return code does not by
   itself prove compliance with the phase deadline. Two independent mocked
   clocks verify both a late geometry phase and a timely offline phase with its
   separate origin. Cleanup is charged conservatively in this elapsed time.

5. **Undefined transition costs.** The report leaves cost falsifiers undefined
   when there are no adopted transitions or the relevant denominator is zero.
   Partial observations retain their costs, but incomplete coverage cannot
   become an all-input cheapness conclusion.

6. **Retrieving a failed controller.** Root's remote inventory originally
   required a `COMPLETE`/`ERROR` controller record, preventing retrieval after
   an outer timeout or fatal controller exit left stale `RUNNING` state. The
   reviewed correction retains the original controller bytes and classifies
   quiescent archives as `COMPLETE`, `ERROR`, `INTERRUPTED`, or
   `NO_CONTROLLER_RECORD`. It still requires a free inherited lock, absent
   tmux session, no matching run processes and a supervisor exit record.

## Clock, state and process contracts

The geometry worker arms one default-fatal absolute 150-second alarm before
heavy imports. It performs reference then capture, each with a common
60-second deadline, and does not reset the process allowance. Graph copies,
input/state hashes and capture work are inside the common invocation clock.
Hook preparation and post-return encoding/publication are separately visible
inside the process allowance. The reference is atomically published before the
second call. A fatal capture termination can lose unflushed RAM snapshots;
those states are unavailable, rather than recoverable partial observations.

The offline worker is a separate process with a fresh absolute 60-second alarm.
Both phases receive the same inherited lock descriptor, exclusive logs and
process-group supervision with five-second cleanup grace. No observation may
replace an existing publication. Controller status alone uses replacement.
Direct children are reaped; same-group descendants are signaled. Deliberate
process-group escape and reaping orphan zombies are outside the documented
supervisor guarantee. The controller cannot resume an existing attempt.

The remote start checks frozen bytes, the native interpreter, absence of prior
lifecycle outputs, and process/lock/session state. An atomic no-clobber
`launch.json` is published before tmux is invoked, so concurrent or interrupted
launch attempts cannot automatically retry. The outer bound is 7,780 seconds
for 34 inputs, with a further five-second hard-kill interval. Remote inventory
hashes preserved artifacts only after quiescence checks and excludes cache
files. This review did not execute the remote wrapper or verify a live host.

The final remote helper also requires its own pre-launch synthetic check. It
reserves a fresh directory and cache, records the invocation and exclusive
stdout/stderr, and caps the direct test process at 45 seconds. Start requires
its saved zero-exit `PASS`, zero failures/errors/prohibited attempts, matching
diagnostic hashes and environment, and the saved summary hash. Result
publication follows the direct test process's reaping. A timeout or failed
test leaves its evidence and prevents start; it does not authorize a retry.
This direct-process test cap is distinct from the geometry/offline process-group
supervision. An unsuccessful test run still requires explicit process
observation before further action. Numba cache binaries are excluded from
retrieval inventory. I reviewed these additions without executing their tests.

The reference has the same read-only stream wrappers as capture. They consume
the original unit generator on demand, without extra RNG draws. Copying ends
after initial state plus 32 adoptions, while the original search continues to
its stop. Complete final orders remain saved separately. Proposal/unit stream
digests and counts are retained, but the complete stream elements are not;
later auditors cannot independently reconstruct those digests. Equality is
therefore a comparison of recorded digests under the reviewed wrapper.

`wrapper_wall` measures stream encoding and hashing, not every counter update,
timer call or list append. Those smaller operations remain in common,
transition and process wall time. No overhead is subtracted to extend a
deadline or claim an uninstrumented speedup. The second call is a same-process
second invocation; it is not a universal warm-JIT measurement. This screen
does not estimate final ACL, complete-pipeline runtime, MM performance, family
means or generalization.

## Independent evidence and identities

The [phase-only runner](../../results/codex/040-geometry-review/phase_checks.py)
passed **8 checks**, with zero failures/errors. It ran the six phase/report
fixtures and two independent mocked-clock checks, leaving `RUNTIME=None`.
No Ember, NumPy, NetworkX, Numba, MM or busclique module was loaded. It did not
invoke the author's complete suite or its tiny native fixtures. Results and
exact imported file hashes are in
[attempt001/summary.json](../../results/codex/040-geometry-review/attempt001/summary.json).
The 1.2285-second test-suite duration is not benchmark evidence.

```sh
.venv/codex-native/bin/python -B results/codex/040-geometry-review/phase_checks.py results/codex/040-geometry-review/root-repeat
```

The destination must not exist. A separate read-only metadata check verified
all 153 prepared file hashes, the file-map digest, all 34 canonical node vectors,
and the exact copied 038 supervision/watchdog bytes. At that observation, the
corpus observations, logs, worker summaries and cache directories contained no
files. The frozen prepared manifest is
`eca3cb626475eba348a5154d91c9ee993e04f58940b72fca2a9a0bc27d3a9230`;
source snapshot is
`63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473`.
The inventory and exact ledger vector are in
[static_review.json](../../results/codex/040-geometry-review/static_review.json).

| Reviewed file | SHA256 |
| --- | --- |
| `geometry.py` | `732af19c71c3928c189a125a4926d042c71a655df5465d962e6dc2bf7f1155d5` |
| `controller.py` | `9f990991233ad5fc75a850997181933af66cf4620d36f1594d21e742db6698aa` |
| `report.py` | `980ed11b601d6058b4a0043d6f5a43a8856e411aa9d4c12abf88038ae80668da` |
| `common.py` | `4c75d637a6f96a4375fa7a38b92e3464b83116b483df3be0939a0fb637b64a6c` |
| `supervision.py` | `f9699c6f41e2d850a9cc24b4de144c3a64074993eb08d21652152dc5b227be6a` |
| `watchdog.py` | `2cb1fc463d61ec605b23f1f6d1f8ded930f7a528daf1ccd6e749f5676a964a7b` |
| `040-launch/remote_control.py` | `4828e1426d4e09160a388b8c0e62aeb35f5036f82dbbc272fb1123c8a416d8d2` |
| Independent `phase_checks.py` | `7c4d6c019b3e1a1a5e6cc3318bba1e5516a4f14ac214ba636eacb9d9de03ff80` |
| Independent phase summary | `607d20ca72d0c6eaa7d352a9e3dccff12c81489b3d504410b8c331bbc8d3e419` |

The protocol hash is
`c5dd735cdc1713baab9b7f76dc6641949877ee366682d6cd280e537cec8e3750`.
After the phase-only run, the author added cooperative offline exception
evidence: current/completed lines, elapsed work and uncertified partial
chains/claims survive without a cache commit. The geometry capture functions
and all six implementation identities above remain unchanged. The final
`instrumentation.py` hash is
`72eba8d970c0ba43e82c9cb20a11fff1487d8665c82536666a4fbedc326db13b`,
`offline.py` is
`5d05f4428537d12e29fb5e6e47308ba14aa0d6f13752e85eba49f0fbaee720ed`,
and `checks.py` is
`5cf2004d5d7f597bd4ef429e47b23f077d84b01e4af2513a363c25fb21d1d7bb`.
Those additions belong to the separate offline review; this note does not
claim that those final revisions ran in `attempt001`.

The preceding note bytes and first review inventory are retained under
`040-geometry-review`; the final note incorporates the later remote synthetic
gate and final separately reviewed offline hashes. The current frozen review
inventory is `final_review_manifest.json` in that directory.
