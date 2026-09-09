# A063 before-execution censoring clarification

2026-09-09 UTC. C's static review found a diagnostic classification defect in
the unexecuted reader: a TIMEOUT returned by A061 was grouped under constructor
failure and marked uncensored; a completed mobile search followed by final
validation or publication timeout could likewise be marked uncensored. No
outcomes were read and no candidate or analyzer ran before this correction.

The preserved original script/preparation/note are under
`results/codex/a063-transfer-analysis/before-censoring-clarification/`.
The narrow reader delta adds separate base, operator and final scope records,
each retaining entered state, a True/False/null censoring flag, and its evidence.
Base TIMEOUT is named constructor timeout. A final gate or actual output deadline
is independent of whether the mobile operator completed its last pass. Missing,
unentered and error-ambiguous scopes remain distinct from observed completed
timely scopes. A top-level timeout without a located stage is still an observed
output timeout; it does not invent a base/operator/final cause.

Raw reported/finalized, inherited base, operator and wrapper stage statuses remain
visible. Overall censoring is True if any scope or the output reports a deadline;
it is False only when all applicable public scopes completed, and otherwise null.
This projection concerns those public scopes: it does not infer whether every
internal A061 search exhausted its alternatives or resolve generic constructor
failures into work, geometry or acceptance causes.

Receipt Q/counters, authority hashes, physical validation delegation and timings
are unchanged. C reviews only this delta. No broad tests, outcome reads or
execution are added. The additive `preparation002.json` binds this revision and
the superseded bytes; the original preparation is retained unchanged.
