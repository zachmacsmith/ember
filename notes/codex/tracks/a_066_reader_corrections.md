# A066 passive reader: pre-execution censoring corrections

2026-09-10. Root and B-track static review found two reader defects before any
constructor outcome analysis. Candidate sources, the running screen and original
shared readers remain unchanged.

First, an operator dictionary can exist when a deadline stops context creation,
entry reading, certification or bundle creation before `_Search` initializes its
A066 fields. The corrected projection accepts only wholly absent search fields,
empty diagnostic sequences, zero initial state counters, absent cache state and
a terminal deadline/error. It reports `operator_initialized=False` with unknown
pair policy/counters; it does not invent zero pair work. Mixed fields, populated
sequences, nonzero counters, existing caches or a nonterminal state are errors.
The ordinary receipt and censoring interpreter still runs before this projection.

Second, the inherited interpreter marks a fully exhausted search as uncensored
and recomputes total cost censoring from its inner scopes. That can erase a
separate observed process/output timeout. A common post-interpret step now
preserves `late=True`, `TIMEOUT` and `WATCHDOG_TIMEOUT` as positive outer-censoring
evidence for both A066 arms and A065. It leaves inner scopes unchanged, preserves
unknown status in the absence of positive evidence, and never changes audit
credit. This is an inherited annotation issue; no earlier-cohort impact is claimed
here without a separate audit.

The original prepared reader/preparation are preserved under
`results/codex/a066-constructor/superseded_mechanism001/`. The intermediate
pre-Search-corrected reader and its first passing check freeze are preserved under
`superseded_mechanism002/`. There was no full reader execution at either version.
Two initial synthetic check groups passed once in 0.091167 seconds process wall.
After the second correction, three synthetic reader-only groups passed once in
0.088397 seconds process wall. Tests cover both policies, initialized-zero versus
uninitialized-unknown counters, 17 malformed-state variants, and eight outer-time
truth cases for A066, pruning-only and A065. There were no failed checks, candidate
imports/calls, constructor outcome reads or full reader-main invocations.

The generated A066 interpreter remains unchanged. Exact source diffs are
`mechanism_presearch_fix.diff` and `mechanism_outer_censoring_fix.diff`; corrected
source/check bindings and passing output are frozen in `mechanism_preparation002.json`.
Root reviews this version before any actual mechanism analysis.
