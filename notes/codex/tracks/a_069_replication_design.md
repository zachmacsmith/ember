# A069 revised proposal: replicate the shared construction mechanism

2026-09-10 UTC. **Design only; no code, inputs, readers, checks or execution.**
[v1](a_069_replication_design_v1.md) preserves the superseded individual-Q veto.
Failed A068 policies remain rejected; A061 remains retained.

**Hypothesis and choice.** Replicate before buying more asks. Both A068 variants
improved A061 on eight shared canonical structures, including grid, honeycomb,
WS and SBM: complete support for their shared active-arm/corner/pricing change.
But full footprint lost 24 qubits on BA100 and 16 on the BA96 relabel; booking
lost 7 there. Test whether paired-mean compactness gains repeat while preserving
these deficits. Late improving bookmarks at 1000 asks establish an active limit,
not that more asks repair a regression. Saturation remains a separate question.

**One screen.** Existing ideal-Z12 g0013 grid128, g0014 honeycomb190, g0102 BA100,
g0302 BA96, g0309 its relabel, g0304 WS96 and g0011 SBM160: seven encodings,
six structures, five ordinary families. New solver seeds 1/2; unchanged full,
booking, A061 and MM: **56 complete cold calls on hyde06**. Every fixed arm is
evaluated across the entire panel; no per-input output selection.

```text
freeze methods, inputs and explicit seeds [1,2]
run each frozen graph/seed/method task once; preserve every outcome and cost
after all 56 terminate, reuse original-minor audit and compare paired means
report each arm, each seed sign, BA parent/relabel and prior seed 0 separately
```

**Seed-list adapter required.** No existing initializer/auditor switch selects
only 1/2: `pilot.initialize`, `freeze_mechanism_screen` and `analyze_multiseed`
enumerate `range(seeds)`. The unchanged worker already uses each task's actual
seed and checks task/result identity. Propose local adapters, with shared files
untouched: declare `seed_values:[1,2]`, `seeds:2`, validate distinct nonnegative
ordinary integers/count, and forbid supplement/corpus-selection paths. Adapt
only the initializer's task-loop iterable to `args.seed_values`; make the local
freezer verify tasks from that same list. Adapt the auditor's single
`seeds=tuple(range(screen['seeds']))` assignment to
`tuple(screen['seed_values'])`, with the same precheck. Bind parent hashes,
adapter identities and exact AST deltas; reversing the deltas must reproduce
all remaining logic. No seed 0 task is generated or run. Worker/controller,
isolation, source/input hashes, time accounting and minor validation remain
unchanged. These proposed adapters require review before implementation/use;
none exists yet, and adapted initialization/audit must be labeled honestly.

**Allocation.** Keep 1000 asks only as controlled replication exposure, not a
quality ceiling. Both new arms retain `D−min(10 seconds, remaining/2)` for
geometry under the 60-second outer limit; later stages receive surviving time.
A068 geometry took 4.101–13.344 seconds and complete downstream work at most
6.959 seconds, supporting the 10-second reserve with measured margin. Preserve
all ask/deadline/group/work stops and reserve excess. No instruction to spend 60
seconds everywhere, per-family allocation, extra ask arm or MM multiplier.

**Distinguishing observations.** Repeated gains with opposite booking policies
support their shared representation change. BA parent/relabel sign reversals
expose seeded placement sensitivity. Smaller core Q followed by worse full
handoff challenges compactness as a guide to refinement/lifting; unreduced
BA96 excludes lifting as its sole cause. Existing scores, endpoints and
handoffs locate reversals but cannot separate move reach, surrogate quality
and acceptance alone. Clock stops identify cost constraints; ask stops do not
prove more useful search exists. No new exact or saved-map campaign.

**Falsifier/self-critique.** The BA100/parent/relabel blocks directly challenge
generality within this complete screen. Two new seeds yield uncertain means
and weak variance estimates; count-matched exposure can hide unequal work.
This cannot answer whether more asks help. Complete all 56 calls, without
adaptive replacement or automatic budget extension after a negative result.

**Mechanism continuation.** For one fixed arm, require timely validity on all 14
calls; nonpositive paired-mean Q difference versus A061 on each canonical
structure **and separately on the BA relabel**; and one-third closure of a
positive paired-mean A061-to-MM gap on qualifying structures from two ordinary
families. Require improvement at both new seeds on at least two canonical
structures as additional consistency evidence. An individual Q loss is **not**
a veto: retain its magnitude/sign, paired mean and BA parent/relabel comparison.
Family mean ACL retains per-structure support; dense gains cannot hide a mean
regression. Show all seed 0 losses and descriptive three-seed means alongside
the new cohort; new means never erase A068's rejection. Report within-chain
variance, across-seed sample variance and complete costs separately.

If neither arm meets these criteria, stop this replication rationale rather
than automatically adding asks or local repairs. Opposing signs and near-zero
means remain uncertain, not a universal veto of support mechanisms. This is
only exploratory continuation; any later work needs a specific completed
explanation and a separate root decision after the other tracks' results.
