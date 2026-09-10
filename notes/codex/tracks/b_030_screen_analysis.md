# B030 passive complete-screen analysis

2026-09-10. Prepared without reading complete-screen outcomes or executing the
reader. Root owns the 48-call lifecycle, terminal archive verification, original
audit and reader invocation. No candidate, route, validator or private witness
is imported by this reader. This plan does not alter the frozen constructor.

The screen is B030 `disconnected-ownership`, its `connected-ownership` ablation,
retained A061 `native-branched-path`, and pinned `mm`, each separately on hyde02.
Inputs g0013/g0301/g0302/g0305/g0308/g0309 and seeds 0/1 give 48 cold 60 s calls.
These are five structures with one BA relabel, not six independent structures.
Screen SHA `817902d8a7d9c50e3583fbe1c06b8f00f9d62fc7e0f8086af60a4a8ee15adbde`;
source snapshot `1b123236393082641750d6f8e28fa83a182c4de96f64f840e1d8a837b652aa6e`;
manifest `d1da691dba4de9720de34167fc8e9624021055ecfc1b3b72c9da4076b310add9`.

Reuse the isolated shared multi-seed adapter
`results/codex/three-track-20260910/analyze_multiseed.py`, SHA
`a4c16e83ff90210d5ac9454010723ce0f6301c05fd4fef3eaa92c276855f7540`.
Its original oracle, success/quality/clock/error credit are unchanged. It alone
supplies all 48 final rows. B's `results/codex/b030-constructor/mechanism.py`
then binds the approved audit, frozen identities and each raw result hash;
it only projects scalar receipts and descriptive comparisons. Reader identity
is external to the already frozen screen. No second validator is added.

The compact report and accompanying JSON preserve:

- Every graph/seed/method status, credited Q/ACL, within-chain variance, recorded
  solver wall/CPU and process wall, including failures. Missing times stay
  unknown. Outer TIMEOUT and a wrapper's fatal ERROR/error are both retained.
- Per-encoding two-seed mean ACL and sample variance with credited denominators;
  both individual seeds and every lost success/Q regression. Failed seeds have
  no invented ACL. Relabel results stay visible without a second structure vote.
- Native first-valid time, every valid-incumbent Q admission and retrospective
  time after the last admission. A final working state may be fragmented even
  with a credited earlier incumbent. Failed-call incumbents receive no credit.
- Initial/final and all recorded scalar slot Q/M/D/P/component changes; scored,
  accepted, rejected, interrupted and no-proposal outcomes by operator/subtype;
  real merge costs and Q jumps; counter coverage, cache/phase and slot costs.
  E comparisons use one slot's unchanged prices. Sweep price changes are saved
  separately; decreasing an isolated proxy is not constructor progress.

**Decision interpretation, agreed before launch.** Count a structure's Q gain
using lower mean Q on two credited seeds for *each* compared method. Show
all-seed strict-gain counts separately. The candidate must still be timely valid
on all twelve calls, beat the ablation on two distinct structures including a
fresh input, and beat A061 on two structures. A new hidden branch control is
identified separately from ordinary fresh inputs. No failures are averaged away.
The pre-launch clarification is saved in `criterion_seed_interpretation.json`,
SHA `59db9676f2386f9845d398b7c47ccb63264f6413154e788201a50ac165f0bc1d`.
Numerical criterion evidence is not automatic promotion: preserve each seed
regression, MM gap and generalization limit. The all-class objective is unchanged.

**Mechanism question.** Does movable contact-bearing ownership reach complete
low-Q minors promptly? Contact gains with growing/persistent fragments or large
actual merge Q costs support the expensive-fragment explanation. Repeated
fully scored useful proposals that are rejected support a specific acceptance
question; they do not establish a better counterfactual trajectory. Few completed
proposals with recount/distance/merge deadline interruptions instead expose
computational cost and leave reach unresolved. The connected ablation tests this
fixed policy: state, proposal geometry and prices diverge after its first rejection,
so a final difference cannot be attributed to one isolated patch or to temporary
fragmentation in every possible algorithm. No refinement follows automatically.

**Reader self-critique and scope.** Native incumbent events are production
certificates reported by the constructor, not independent saved-map revalidation.
Scalar slot receipts cover every recorded attempt; a started slot can lack a row
if interrupted before row creation, and that discrepancy is exposed. Detailed
changed-site traces contain only the first sixteen plus last. Observation counts
are not exact time spent fragmented. Hardware-distance/MST debt ignores blocked
corridors and may overcount shared branches. Phase wall is exclusive within the
meter; slot costs overlap phases and cannot be added to them. Phase CPU and
process CPU were not measured. Retrospective flat intervals include finalization,
and do not prove an early-stop policy would preserve quality. Two development
seeds do not establish population variability, class-level generalization or
publication readiness. Keep this analysis bounded; add no new correctness suite.

Invocation after root's original-audit PASS:

```
python -I -B results/codex/b030-constructor/mechanism.py ARCHIVE AUDIT NEW_OUTPUT \
  --identity IDENTITY_JSON --identity-sha256 SHA --archive-digest ROOT_DIGEST
```

The identity binds reader/shared-audit/oracle hashes, frozen manifest/source/task
order/screen, methods/graphs/seeds/timeout/host and source references. Each analysis
attempt writes to a new directory and retains failures. Root reviews this source
before invoking it; no analysis execution has occurred during preparation.
