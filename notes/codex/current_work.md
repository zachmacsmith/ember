# Current research checkpoint

Updated 2026-09-09 02:43 UTC. Branch `codex`; goal active and unmet.
Single general heuristic, no MM/busclique, no portfolio, ideal Z12. Success,
mean ACL, variability and roughly MM-scale runtime remain separate requirements;
optimal ACL-one ties are acceptable. Candidate dependencies and the independent
original validator remain isolated from MM.

The [latest 79-call milestone](mechanism_cycle_062_b024_c010.md) is complete:
all three runs are terminal, retrieved once and analyzed once, with zero
validation errors. Root reviewed source and focused checks before launch and
verified final evidence: A06248 bindings, B02421, C01023. None passes its fixed
continuation gate. No old remote job remains live.

- A062 ready ordering recovers two lifting failures but loses planted seed0,
  regresses wheel/grid means and adds22.136s of scheduler wall. Retire its fixed
  priority; retain the unchanged measured A061 branch control. The reviewed
  [guarded-connector diagnostic](guarded_connector_diagnostic_proposal.md) is
  being implemented on exactly three saved blocked states. It tests fixed-owner
  connectors of at most three sites with all future-port guards and 5s/2M
  per-state limits. Root code review precedes its one run; no constructor replay.
- B024 reduces both initialization proxies on all seven noncliques but finishes
  only4/9 versus control6/9 and MM8/9. Retire it. [B025's reviewed acceptance
  discriminator](tracks/b_025_acceptance_discriminator.md) is implemented:
  unchanged B023 generators/prices/schedule, accept selected winners only when
  current-price energy does not increase. [27 calls are launched on02](tracks/b_025_launch_record.md),
  20s,seed0,treatment/control/MM. Root verified41 author/input bindings and
  reviewed the four new-risk groups and source diff before freezing it.
- C010 finishes2/8 versus MM6/8, with optimal path/tree ties. Six failures stop
  at charged work after0.318–0.653s, leaving most of15s unused. Retire the fixed
  policy. [C011's reviewed computation-allocation ablation](tracks/c_010_wall_budget_diagnostic_proposal.md)
  is implemented with unchanged placement/splitting and wall deadline,
  retaining work counts but disabling search/final work denial. [24 calls are
  launched on03](tracks/c_011_launch_record.md),15s,seed0,fixed C010/treatment/MM.
  Root verified23 author bindings and reviewed three new-risk groups plus the
  source diff before freezing it. Extra complete outputs and the separate
  continuation gate decide it; no partial-score justification or cap sweep.

The [replicated gap analysis](mm_gap_current_replications.md) and
[72 class/size rows](mm_gap_current_tables.md) preserve all36 class labels,
paired mean/sample-variance comparisons and failure-inclusive times. Eighteen
memberships repeat positive mean ACL gaps. The [prior136-call milestone](mechanism_cycle_061_b023_c009.md)
retains A061's modest branch gains and B023/C009 failures. Different constructor
versions, seed sets and hosts are never pooled. All current data are exposed
development inputs; no held-out or all-class improvement claim exists.

The [workflow](tracks/workflow.md) requires a causal diagnosis, distinguishing
observation, hypothesis, pseudocode, self-critique and cheap falsifier before
implementation. Exact neighborhood solves remain optional local diagnostics,
never global constructors. Root owns runtime freeze and transport; observation
failure never authorizes another launch. Only candidate registry entries were
added to shared pilot logic. Protected `.verified.json` and `.claude/` remain
untouched. No alternate architecture, paper or novelty claim is warranted yet.
