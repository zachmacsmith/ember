# Prospective clarification of variance and the research objective

2026-09-09 22:12 UTC, before reading Transfer002 outcome maps or Q comparisons.
Root requested a read-only check against the user's stated objective and the
saved plan. It found an unintended stronger gate in recent notes.

The user makes mean ACL primary and explicitly allows a mean-ACL result to be
sufficient for a paper. PLAN_CODEX.md already states that neither run-to-run ACL
variance nor within-embedding chain-length variance is a hidden acceptance
rule. A064 and the Transfer002 protocol instead say variance regressions block
promotion; C014's blanket wording is also too broad. A single-seed screen's
within-chain variance is particularly inappropriate as a substitute for
run-to-run ACL variability.

Mean ACL across source classes remains the primary quality endpoint, with
preserved success and roughly-MM-order runtime. Across-run ACL variance and
within-embedding chain-length variance are distinct secondary outcomes that
must be reported. An increase in either is not by itself an automatic promotion
or publication veto. Preserve every regression and disclose the tradeoff.
Class-level mean-ACL or success losses cannot be hidden by aggregate gains.
Optimal ACL1 ties remain allowed. No universal3× runtime gate is introduced.

This clarification supersedes the recent blanket variance-veto wording
prospectively. Frozen input/method/source identities, allocations, exploratory
criteria and their verdicts remain unchanged. No prior rejected policy is
revived. A061 remains retained; A063 still lacks an all-class quality/runtime
result, independently of its reported within-chain variance increases.
New promotion work must follow the user's objective and estimate the actual
run-to-run statistic on repeated seeds rather than reinterpret a different
variance measure.
