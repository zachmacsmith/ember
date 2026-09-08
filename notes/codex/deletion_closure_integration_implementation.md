# Final deletion closure: native integration evidence

2026-09-08. Implemented the accepted
[integration specification](deletion_closure_integration_spec.md), after root
accepted the core and independent review and froze 041. No corpus, saved-output
cleanup, remote action or benchmark call was made. No 041 observations were
read. The closure core, its accepted design/specification and prior evidence
remain unchanged.

## Implemented behavior

Native adds `final_cleanup='off'|'deletion'`. The enabled option is restricted to
legacy singletons, stars off, greedy trees and raw-contact scoring. This is the
experiment's supported API boundary, not mathematical incompatibility. Source
and target must be simple undirected loopless graphs; actual target labels must
be ordinary integers. Native retains its canonical source adapter and inverse
label restoration.

Initial pruning and contact refinement are unchanged. The enabled wrapper runs
only after a normal contact return, independently validates its entry, calls the
frozen closure at most once with the exact native absolute deadline, and then
retains native's original-graph final validation and existing timeout handling.
No time is renewed. No cleanup imports, extra graph scans or cleanup diagnostic
keys appear on the off path. The pilot adds exactly
`native-search-joint1-contacts-spectral-final-deletion`, equal to the control's
configuration with only `final_cleanup='deletion'` added. Every older config
remains equal to its pre-integration value.

Empty source, disabled contact refinement and expiry before refinement/cleanup
or during the entry check have distinct recorded skip reasons. Invalid contact
input or independently invalid entry cannot reach the closure. Exceptions
preserve known wrapper/check/call costs in the existing ERROR envelope. An
expired pre-copy alias remains explicitly an unvalidated-by-core, incomplete
module result; the independent native entry check is separate. A private valid
prefix survives interruption. Final validation can still reject either, and a
valid completed closure can still finish as a native TIMEOUT.

`diag.final_cleanup` retains full nested core info and every accepted deletion,
canonical source keys, before/after Q, actual module calls/return, contact
invocation/return, independent entry validity, skip/stop reason, and final native
stage/status. Unavailable fields are null or absent; no skipped module receives
fabricated work. Wrapper wall contains the module-call and entry-validation
intervals. Initial graph-prerequisite wall is separate. All are inside native
solver time; nested walls must not be added again. Final relabeling/validation
lies outside wrapper wall but remains inside native time.

## Checks and preserved attempts

The new suite passes **34 checks**. Inert construction/pruning/contact adapters
isolate native wiring on hand-constructed valid minors; the real closure and
independent original-graph validators exercise actual deletion decisions.
These fixtures do not pretend to be a geometric construction experiment. They
verify exact default/explicit-off envelopes against preserved pre-integration
source, call order, one common deadline, no import on skipped paths, all API and
graph guards, source labels/isolate preservation, Q arithmetic and full trace
reversal to recover every cleanup chain set. Controlled clocks test all skip
stages, actual-core pre-copy aliasing, a private prefix retaining an earlier
deletion, late final validation and caught failure costs. Inputs remain intact.

One real tiny spectral native call on ideal Z3 uses a seven-vertex path plus an
isolate, mixed source labels, 16 asks, four groups and 2,000 contact expansions.
It verifies actual wiring, original validity, unchanged graphs, deadline sharing
and nested timer/Q arithmetic. It makes no expected-gain assertion.

The broader guarded regression passes **189 checks**: the new integration
suite, frozen closure core tests, existing native tests, and endpoint, singleton
star and connected-star integration suites. MinorMiner/busclique imports were
blocked and no attempt occurred. Python was 3.10.19 in `.venv`; each test attempt
used a new private JIT cache. This is correctness-suite timing, not embedding
performance evidence. `git diff --check` also passed.

All attempts are retained under
`results/codex/deletion-closure-integration-checks`:

* `attempt001`: 32 passed and two test failures. A test wrapper captured a local
  function variable later rebound to the validator. The wrapper, not production
  behavior, was corrected; the native source hash is identical across attempts.
* `attempt002`: all 34 focused checks passed.
* `attempt003-broad`: all 189 checks passed; all bound source hashes remained
  unchanged during execution.

Exact successful broad command:

```sh
.venv/bin/python -B results/codex/deletion-closure-integration-checks/run_checks.py results/codex/deletion-closure-integration-checks/attempt003-broad --broad
```

The harness rejects an existing attempt directory; an independent repeat must
use a fresh path. The reference subdirectory contains the exact prior native
and pilot source needed for the regression assertions. These small reference
files must accompany the test/evidence bundle when reproduced elsewhere.

Root explicitly authorized one existing endpoint-test compatibility change:
its old whole-config equality assertion now accounts for this one exact new
arm while still checking every preexisting config and the endpoint arm. It
does not permit arbitrary unverified extra configs. `integration.diff` preserves
that change and the two production diffs; frozen endpoint source/evidence is
unchanged.

## Stable review revision and limitations

Native SHA-256:
`49a2175874b4b0c65f2ddccde519e8905ae7fc3836e15e2a7c478b37f91e5c57`.
Pilot SHA-256:
`fedbdf4dc60c78bb357c93c465eda50e5eb403c888dc4e70f6255bf90666f5b9`.
New integration-test SHA-256:
`3ff1e3da2185e718d4999a3590a5e89d6b0064ca6f4cc6c31478c7793ec15cfb`.
Core SHA-256 remains
`66a2bc21af6c035ca0b03f9065e2ce780ca0503b9be1af95487eb19e6be67d8b`.

The added graph and entry checks can cost time without reducing Q. Their
underlying validator/scans are cooperative, and the final validator still has
no internal cancellation. Enabled prerequisites can change binding search
prefixes. Native's original result-time boundary is retained, not replaced by
a hard real-time guarantee. Completed deletion closure proves neither minimum
Q nor timely native completion. No 042 result, mean-ACL improvement or speed
benefit is established here. Independent integration review must precede freeze
and root launch under the accepted 042 protocol.
