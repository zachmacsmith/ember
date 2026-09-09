# A064 focused-check outcome

2026-09-09 UTC. All four declared new-risk groups passed on the first execution,
with zero failures/errors, no changed preparation bindings and no prohibited
import attempt. The suite took 1.226s; the complete check process took 1.471s,
exit 0, with empty stderr. The native environment reported MM, its extension
and busclique absent. This is correctness evidence on supplied tiny states,
not complete-constructor quality or runtime evidence.

Evidence is under `results/codex/interleaved-boundary-checks/attempt001/`:
invocation, stdout, stderr, outer status, preexecution bindings, checks log and
summary. Preparation SHA is
`2dd503b96405d79e1527b5e8b5e819058bab60c13a9b684441de9fe32a48dd2d`.
The corrected before-code policy SHA is
`355fd8f93f8826ee99b42203ab7dfa5c87ec8002633a54eb05cb8ecc61c09822`;
its first draft is preserved separately. No test failed and no rerun occurred.

The four groups verify:

- Every owner gets later roots across rounds; three full rounds are needed in
  the controlled no-gain fixture, with no repeated completed owner/root pair.
  Same-epoch exhaustion and bound-closed/empty-source cases stop correctly.
- An actual P3-in-P5 donor transfer reduces independently valid Q5 to Q3 while
  invalidating an earlier cached owner. A last-slot variant checks that the
  completed round stays intact and the next round uses updated lengths.
- Expiry during cache preparation/resumption, epoch-event preparation, before
  publication and after publication's cache disposal preserves the appropriate
  certified incumbent. A forced stale-epoch lookup is fatal with no creditable
  map. Live payload counters return to zero after cleanup.
- Active query costs exclude deliberately inserted parked time; peak retained
  context/root/free-site counts reconcile. Diagnostics retain no bulky query
  domains. The wrapper function AST matches A063 apart from its name and metadata,
  dispatches A061 once in stubbed executions, and preserves base failure/late
  outer-return behavior. Its real isolated import uses the unchanged helpers.

Only tiny supplied-state operator calls and three stubbed wrapper executions
occurred. A061 was not executed, and there were no corpus, MM, new-panel or
full-constructor calls. No existing shared source, default, harness or validator
changed. The next step is root source review and the frozen nine-input,
36-call complete-constructor screen; wheel remains outside this small screen.

## Root-review diagnostic correction

Root subsequently found that the final `ended >= deadline` branch still
overrode the first recorded deadline phase after cleanup. The earlier safeguard
inside `finally` was insufficient. This changed diagnostic classification, not
search, admission, current embedding or deadline behavior. The originally
passing source/checks/preparation/manifest and this initial outcome note are
preserved under `before-stop-phase-fix/`; attempt001 is unchanged.

The final guard now leaves an existing `deadline` status and its first
`stopped_phase` intact; cleanup expiry remains separate in `cleanup_deadline`.
Only the deadline-focused group was strengthened and rerun in attempt002 under
`preparation002.json`. It passed: one group, zero failures/errors, 0.702s suite,
0.926s outer process, exit0. It explicitly checks that schedule/bookkeeping
stops survive expired cache cleanup, as well as pre/postpublication incumbents.
The other three groups were not rerun, and no constructor/panel call occurred.

Final scheduler SHA: `0d6f442ddb8473b5225b119f304e8db9aff10c74e71a0753fc920bc5ebfaf2e4`.
The policy and wrapper are unchanged. Current-file bindings are in
`results/codex/interleaved-boundary-checks/manifest002.json`; the first manifest
remains a historical record of its original passing snapshot.
