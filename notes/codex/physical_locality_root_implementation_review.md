# Root review of 040 instrumentation

2026-09-08. Root accepts the corrected implementation for one diagnostic,
subject to its target-environment synthetic checks and final remote preflight.
Production source and the prepared 153-file input copy remain unchanged.
The accepted protocol is [the physical-locality design](physical_locality_diagnostic_review.md).

Root read `instrumentation.py`, `common.py`, the complete geometry wrapper and
the relevant frozen `plane.arrange` body. The two hooks occur after the initial
best-state assignment and after the complete feasible adoption/bookmark block.
Removing those hooks restores the original AST. The original function returns
the selected orders and carried y-rank in its info record, so final-order
comparison does not depend on reconstructing order from packed coordinates.
The raw reference stops immediately before empty-chain seeding; removing its
terminal callback restores the full wire function AST.

The unit wrapper consumes the underlying generator only when its caller asks
for another value. Proposal wrappers record the actual changing arguments and
returned orders without extra RNG draws. These full values are encoded into
length-framed hash streams, but only stream digests and counts are retained.
Thus later audits can compare recorded digests under the reviewed wrapper;
they cannot independently reconstruct every proposal-stream hash from saved
elements. Final returned orders, captured states and their full books are
retained separately. This bounded retention is intentional and must remain an
explicit limit in the results report.

Tagged JSON preserves dictionary/list/tuple order, scalar float hex values,
array dtype/shape and element values. The relevant coordinate/bar arrays use
ordinary finite numeric values; runtime memory addresses and strides are not
converter inputs. Signed zero is covered by the author's focused fixture.
This is a transparent codec, not an executable serialized object format.

Root found a material reporting gap: offline completion alone did not require
matching, timely, nonbinding reference/capture geometry. Therefore timing
conclusions could incorrectly survive recording interference. Root requested
an explicit eligibility gate and a focused report fixture, with zero aggregate
transition denominators left undefined. The independent lifecycle reviewer
also required clean timely phase outcomes and adherence to copied ledger order.
The offline reviewer found that captured wire coordinates needed independent
binding to the original target, and that diagnostic book reconstruction belonged
outside the deployable update subtotal. These are being corrected before freeze.

Root's read-only hyde03 readiness check passed. The intended 040 run path is
absent; the pinned native environment contains neither MM nor busclique; tmux
and timeout are present and logout does not kill user processes. Readiness
artifacts are under `results/codex/040-launch/`. Root prepared fixed-run remote
operations using the existing isolated SSH route through hyde01, but has not
staged or launched the diagnostic. Observation failures must never trigger a
restart. One full focused suite will run in a separate synthetic-check directory
on hyde03 before any corpus start; its pass, unchanged code and environment are
required by the remote start operation.

## Final accepted review

Root read the complete final [geometry/lifecycle review](physical_locality_geometry_review.md)
and [offline review](physical_locality_offline_review.md), the implementation
note and the last narrow interruption-handling changes. All reported findings
are resolved. Root independently checked all 1,085 retained geometry-review
artifact hashes, the exact ten diagnostic files, author check records, final
offline check identities and the reviewed remote helper hash. The local final
review preflight also passes, including all prepared bytes and exact ledger
order. No additional corpus or solver run occurred during this acceptance.

The final diagnostic digest is
`0c68ab814eb76aea5876ec79386d1cbabd59f8a37197c688e1d12d447c412733`.
Author readiness record:
`37bc23e84bf7fb76ebeff27dd2f5b1b7188f1580af8dd6fb05b2de93c1dd1025`.
Independent geometry review manifest:
`b4d459b0a8d79ff0d567511b8b9c6f540a27296dbcf497e1944d3f3d131d44c9`.
Final independent offline summary:
`7218d03a2f84e05a42839f16af0757dda9a815e4dbe78b708da623386ca95f7c`.
Root's hash check and local review preflight are saved under
`results/codex/040-launch/`. The independent phase suite passes eight checks;
the final independent offline suite passes ten, including 36 tiny converter/cache
pairs. The author passed 21 full checks before the final failure-only change
and four focused checks afterward. The current complete suite has 23 checks
for the target-environment run. Do not describe the earlier 21-check execution
as an execution of every final byte.
