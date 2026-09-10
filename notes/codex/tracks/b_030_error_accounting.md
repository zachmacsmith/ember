# B030 unexpected-error accounting correction

2026-09-10, before the complete screen. Root and C's independent source review
identified that a runtime or finalization exception could be recorded only in
diagnostics while the wrapper reported an ordinary FAILURE/TIMEOUT. The first
implementation and three-case check remain preserved in check001 and git
`997bc7d1`. No search policy changed.

Unexpected exceptions now set `diag.fatal`, return ERROR with top-level `error`,
and suppress the embedding even when a previous incumbent exists or the clock
is late. Explicit parameter/graph input errors use a separate `_InputError`;
declared input failures, normal search failure and deadline censoring remain
distinct. Reporting an observed incumbent is inside the finalization exception
boundary. The original pilot may still give an outer late call TIMEOUT, but it
preserves the wrapper's `reported_status` and top-level `error`; passive analysis
must show both. The original audit already excludes top-level errors from credit.

The single authorized focused check replaced `_Engine.run` with the fixed public
rail fixture, certified its Q3 incumbent through the unchanged production
validator, and independently verified that minor through the original oracle.
It then raised one runtime ValueError. A synthetic late wrapper clock tested
error precedence without sleeping or running a search. The wrapper returned
ERROR, retained its first-valid observation and error, and returned an empty
embedding rejected by the original oracle. This tests runtime error accounting;
it is not a constructor performance measurement or exhaustive exception test.

**First execution PASS**, one case, no retries, errors, import violations or
source changes. Process wall 0.933701 s; program wall/CPU 0.823684/0.678427 s.
The synthetic 30.658327 s overrun is explicitly artificial and is not useful
computation. No original three-case rerun or development constructor occurred.

Evidence: `results/codex/b030-constructor/check002/`, including source snapshots,
exact `accounting.diff`, manifest, invocation/completion receipts, stdout/stderr
and summary. Manifest SHA256
`0682e32bc357e4b4eb97d0f18f24936f0cfd79ffc56af7e5069ab81bc9289036`;
corrected main source SHA256
`17ce44c13a14099824a269ccfde48b98877f29b87f46e975adaa7bf173656c59`;
new check source SHA256
`a219fda01175861eb3ddf98008990c914e8d7a322efdef5cf7198b052ca92a0b`.
Arrays and algorithm contract are unchanged. The snapshot uses the then-current
pilot SHA `69e9459e21909fdb2666479fee1bd25a68944f18e5a410f3d33115388fb0eb5b`;
its root-owned registry update occurred after check001 and was not edited here.
