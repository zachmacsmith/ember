# 044: does the work cap hide useful exchange reach?

Specified before preparation/execution, 2026-09-08. Track A exploratory
allocation experiment; no search implementation change and no full-pipeline
or MM claim.

**Hypothesis.** 043's 1.25-million-unit cap prevents ownership exchange from
using its available time: 29/32 nonempty cases hit that cap, and the maximum
common runtime was 0.901 seconds under a five-second deadline. A larger finite
cap may expose useful contractions without increasing the allowed wall time.

```text
for each of the same 34 fixed development entries, in the same frozen order:
    run ordinary reconstruction in a fresh process, with unchanged settings
    run ownership exchange in a fresh process, with 10,000,000 work units
    each arm independently builds the same groups and shares its original
        absolute five-second deadline across preparation, search and validation
    preserve first returned contraction, every limit/failure and full time
```

The two arm orders remain the per-graph orders fixed in 043. Both are freshly
run on hyde03. All 34 inputs, 35 memberships, group rules, search depth/state/
child/patch limits, ordinary routing allowance and process supervision remain
unchanged. Use a new run identity and immutable snapshot; never rerun 043.
Only exchange's work cap changes from 1.25M to 10M. The cap is a generous
finite bound; the common deadline remains authoritative. Late proposals and
interrupted searches receive no success credit. No output combination.

**Self-critique.** More work can explore the same unproductive early groups
without improving coverage. Eight times the measured maximum work-cap runtime
can exceed five seconds; this is deliberately a deadline-limited test, not a
guaranteed completion allowance. Deep search may need a different allocation
across seeds. Even new first contractions would not establish cumulative
quality, novelty, or affordable full-pipeline improvement.

**Cheap falsifier.** Reuse the existing caller and independent original-label
validator for 68 calls. If exchange still finds no contraction absent from
ordinary, reject a simple larger work allowance as the next improvement and
use recorded group/seed/depth costs to design a different allocation. If it
does, inspect those few traces and evaluate a fixed pipeline integration or
bounded scheduling change. Do not enlarge the cap again under this identity.
