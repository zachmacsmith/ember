# Work caps, completed evidence and the retained A baseline

2026-09-09 UTC. Read-only strategic review of existing source and accepted saved
outcomes. No constructor, solver, connector diagnostic or new timing experiment
was run. B025's authorized saved analysis became available during the review
and is included as its own fresh cohort. The held guarded-connector draft
remains untested.

**The limits are not equally informative.** C010 was strongly work-censored,
but C011 has now tested the obvious extra-wall remedy and gained no completion.
B023/B024 sparse failures generally exhaust a fixed pass schedule, not their
work allowance. A has both useful complete-output evidence and early local
repair stops whose unvisited alternatives remain unknown. None establishes a
universal three-times-MM runtime requirement. That threshold was an exploratory
screen rule, not a user requirement; its historical verdicts remain unchanged.

| Active layer | Fixed limits / source location | What justifies the limit? |
|---|---|---|
| A053 inherited native core | 1,000 geometric asks; four contact passes, 512 total groups of 1–4 owners, beam 1, 16 boundary sites. Contact reconstruction also has 500k total/50k per-group expansions, region 512, two orders. [Core config, lines19–23](../../packages/ember-qc/src/ember_qc/algorithms/factored/site_transfer_construction.py#L19); [contact defaults,606–610](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L606). | Fixed bounded search choices with measured outputs; no cap sweep establishing saturation or runtime equivalence. The core's work is not included in the lifting 20M counter. |
| A053 lifting / blocked repair / transfer | 20M shared wrapper scans; 64 roots, four branches. Blocked repair 1M/query, 5M total. Transfer first 64 sites, 50k/query, 1M total, nested in 20M. [Wrapper 189–191](../../packages/ember-qc/src/ember_qc/algorithms/factored/site_transfer_construction.py#L189); [repair 18–38](../../packages/ember-qc/src/ember_qc/algorithms/factored/blocked_reinsertion.py#L18); [transfer 7–9,75](../../packages/ember-qc/src/ember_qc/algorithms/factored/site_transfer.py#L7). | Engineering bounds, not calibrated. Positive repair/transfer results establish usefulness at these settings, not adequacy of their caps. Local repair denial can stop the complete constructor while global work and wall remain. |
| A core vacancy refinement | Shared 50k **proposals**, at most 20 successful calls; stage time min(1s, 20% elapsed before stage), inside original deadline. Depth 8, beam 16, 256 proposals/seed, 8 owners/64 original occupied sites. [Native 141–170](../../packages/ember-qc/src/ember_qc/algorithms/factored/native.py#L141); [vacancy 8–12](../../packages/ember-qc/src/ember_qc/algorithms/factored/vacancy_repair.py#L8). | Measured finite neighborhood, not a calibrated CPU budget. Proposal count excludes other work from that counter; wall still charges it. |
| Retained A061 branch stage | Eight seeds, 128 owners/path, route 512, 32 attempts/path, 1M work; stage min(1s, 20% preceding wrapper elapsed). Independent final gate uses original deadline after the local stop. [Operator 11–15,31–41](../../packages/ember-qc/src/ember_qc/algorithms/factored/branched_path_reconstruction.py#L11); [wrapper 67–91](../../packages/ember-qc/src/ember_qc/algorithms/factored/branched_path_construction.py#L67). | Complete A059/060/061 comparisons support this stage's measured benefit. They do not calibrate the caps; stage entry validation alone can exhaust 1M. |
| Rejected A062 scheduler | Shares lifting 20M; each bigint operation charges ceil(target size / Python digit bits) units before operating; all ready keys must complete before selection. [Scheduler 19–50](../../packages/ember-qc/src/ember_qc/algorithms/factored/ready_lifting_schedule.py#L19). | Conservative accounting, deliberately not an O(1) fiction. It is not measured CPU work: its per-unit Python metering loop itself costs time. The failed complete-output screen does not isolate that overhead from ordering quality. |
| B023/B024/B025 construction | 19M search/20M total; fixed eight full edge passes; hard 20s maximum even if caller supplies more, with up to 1s reserved for finalization. B024 initial placement shares these limits. [B023 meter 19–43](../../packages/ember-qc/src/ember_qc/algorithms/factored/temporary_contact_construction.py#L19), [passes 405–420](../../packages/ember-qc/src/ember_qc/algorithms/factored/temporary_contact_construction.py#L405), [deadline 514–534](../../packages/ember-qc/src/ember_qc/algorithms/factored/temporary_contact_construction.py#L514); [B024 611–631](../../packages/ember-qc/src/ember_qc/algorithms/factored/joint_placement_construction.py#L611); [B025 533–553](../../packages/ember-qc/src/ember_qc/algorithms/factored/nonincreasing_contact_construction.py#L533). | Fixed exploratory choices, not empirical runtime calibration. A larger outer timeout alone cannot extend this implementation. Eight passes are a search restriction even when no operation or deadline is interrupted. |
| C010 / C011 construction | C010 19M search/20M total; D−0.5s search reserve. C011 removes both work denials while retaining charged counters. Both keep 32-site ranking prefixes and up to four local revision attempts, each releasing up to four old clones. [C010 21–46,187,238–256,518–550](../../packages/ember-qc/src/ember_qc/algorithms/adaptive_clones.py#L21); [C011 35–48,525–558](../../packages/ember-qc/src/ember_qc/algorithms/wall_adaptive_clones.py#L35). | C010's caps lacked calibration. C011 supplies an actual allocation experiment: the fixed policy's extra computation did not yield extra valid outputs on its panel. Local move limits remain untested separately. |

Work counters serve accounting and interruption, not cross-algorithm exchange
rates. A combines scans, routing expansions and a separate proposal counter;
B meters visited items; C reserves full bitset-word work and n·ceil(log2(n+1))
sorting units before native Python operations. C's word size is 64 bits, whereas
A062 uses Python's digit size. Dividing any of these counts by an MM count, or
calling equal 20M limits equal compute, is unjustified. CPU and outer solver wall
measure different things again; process wall additionally retains imports and
worker setup. Nested core/layout, expansion/validation and scheduler timers must
not be summed as disjoint costs.

| Saved cohort, kept separate | Stop / complete-output evidence | Interpretation |
|---|---|---|
| A056 original 34 × four seeds, hyde06, 60s | A053 134/136, MM 120/136. The two A053 seed 1 lifting failures stop at local 1M repair limits after 4.746s and 5.391s. | Actual failures under the policy; repair alternatives are censored well before the global wall. Neither valid partial state nor a larger unused deadline proves recoverability. [Accepted report](../../results/codex/056-results-review/RESULTS.md). |
| A057 additional 35 × two seeds, hyde03, 60s | A053 68/70, MM 64/70. Wheel seed 1 fails at 4.256s: 1M local repair used, 1.048M/5M repair total, 6.300M/20M wrapper total. Hypercube seed 1 fails at 9.440s after all 1,000 asks and unsuccessful conversion/completion. | Wheel's repair suffix is unvisited; hypercube reaches the declared geometric ask endpoint. Neither is a target-capacity proof. A complete-output shortening stage cannot act on either failure. [Exact stage diagnosis](experiments/057_failure_stage_diagnosis.md). |
| A061 original 34, seed 0, hyde06, 60s | A053/branch 34/34; branch saves 40Q across six inputs. Complete/spin-glass stage work stops occur at 0.597/0.610s of 1s; both retain independently valid unchanged bases. Spin-glass never completes its new entry certificate. | Useful full outputs coexist with no observation of those capped proposal neighborhoods. These two are not output loss or solver failure. [Full result](experiments/061_branched_path_results.md). |
| A062 six structures × two seeds, hyde06, 60s | Ready 10/12, unchanged branch 9/12, MM 12/12; new planted failure at 5.800s/local 1M repair, 2.759M/20M global. Scheduler spends 22.136s/31.744M aggregate charged units; all 924 selections complete. | New failure and wheel/grid regressions reject the policy; scheduler interruption did not cause the selected-row failures. Its total solver 127.037s versus 102.856s control includes changed trajectories and 22.136s scheduling, not just abstract word operations. [Full result](experiments/062_ready_lifting_results.md). |
| B023 and separate B024 paired cohort, B9, hyde02, 20s | B023 6/9 vs MM 8/9. In B024's fresh comparison, B024 4/9, B023 6/9, MM 8/9. Sparse B024 failures finish eight passes at 4.22–11.05s; no B023/B024 work-limit denial. K100 reaches the 19s search deadline; B024 spends 7.39s in unchanged initial assignment first. | Raising only 19M cannot address the observed sparse pass stops. More passes are an explicit allocation hypothesis, not proven futile or guaranteed helpful. All completed route/erase actions commit, including energy increases; a universal strict-energy rejection barrier is absent in these two versions. [B023](tracks/b_023_results.md), [B024](tracks/b_024_results.md). |
| B025 separate fresh B023/B025/MM cohort, B9, hyde02, 20s | B025 2/9 versus B023 6/9 and MM 8/9. All seven B025 failures stop at the search deadline after 19.019–19.088s, using 5.306–10.848M units; no work/pass stop. | A changed acceptance policy makes wall limiting, without exhausting work. It rejects 2,312 uphill actions and no selected zero-defect score. All nine recorded prefixes match through the first gate rejection. [Audited summary](../../results/codex/track-b025-analysis/analysis001/summary.json),[mechanism receipts](../../results/codex/track-b025-analysis/mechanism001/summary.json). |
| C011 fresh C010/wall/MM, C8, hyde03, 15s | Both candidates 2/8 vs MM 6/8. Six control work stops at 0.333–0.659s become six wall-arm search stops at 14.502–14.515s; all recorded prefixes and 19M crossing charges match. No extra completion. | Strong negative evidence for **unused wall alone** fixing this policy. Still no impossibility proof for adaptive clones. Wall arm 416–926M units/input is not 416–926M measured CPU instructions. [C011 report and receipts](tracks/c_011_results.md). |

C011's all-attempt solver/CPU totals are 87.915/87.911s versus control 3.359/3.358s;
86.585s belongs to placement/splitting, not initial setup. Its 16,065 revisions
yield 24 commits and 6,326 splits without a new completed minor. This is more
informative than the old partial placement counts alone. B024's improved initial
distance/contact proxies likewise cannot override four completed successes versus
six control successes. A's successful branch savings, unlike those proxies,
survive independent complete-output gates.

B025 further separates direct gate overhead from trajectory cost: its gate costs
0.258s/78,049 units, but total solver/CPU grows to 152.863/152.835s versus fresh
B023 82.278/82.086s. Routing costs 118.798s versus 57.283s. The fixed rejection
policy worsens complete coverage; this is not evidence that the comparison
operation itself is expensive, or that a larger work cap would fix the result.

In the earlier [A053 screen](experiments/053_results_screen.md), all 34 outputs
completed; 134 transfers were committed, and final quality improved 10 inputs,
regressed two and tied 22 versus fresh A050. Transfer caps never bound:
maximum query 19,906/50k, total 599,064/1M, inspected prefix 20/64. This is useful
nonbinding evidence for that primitive on that seed, not calibration for later
blocked-repair states or evidence that the chosen ceilings are optimal.

There is one narrow historical empirical calibration: [ownership-exchange cost
calibration](ownership_exchange_cost_calibration.md) measured 180 tiny local calls
and recommended 250k units/1s using a predeclared fourfold margin. Its largest
actual query was 7,254 units, source degree ≤2, target degree ≤4, on a different host.
Root extrapolated that to 1.25M/5s for a former operator. It does **not** justify
the current A/B/C 20M counters, Zephyr throughput or a universal margin. The present
local caps mostly have boundedness and successful-run precedent, not evidence
that their marginal search benefit has saturated.

The retained baseline is **A061's single fixed branch policy**, not a per-input
collection of outputs. Its [complete 35-membership projection](../../results/codex/strategic-allocation-review/a061_per_class.md)
and [exact CSV](../../results/codex/strategic-allocation-review/a061_per_class.csv)
use only A061 seed 0/hyde06. On 29 common successful structures it wins 8, loses 17,
ties 4 at optimal ACL 1; paired macroACL 2.463346 versus MM 2.649578 and total Q −874
coexist with those 17 losses. Five MM timeouts have no imputed Q. Examples of
remaining excess are cubic +71Q, hardware-native +61, frustrated-square/king +56,
honeycomb +45, Kneser +44, wheel +40, hypercube +30 and grid +29. The linked king membership
is not another independent input. All 17 losses remain in the table.

All-attempt solver totals branch/MM 333.695/442.332s include MM's five timeouts;
the common 29 totals are 243.955/120.287s. Twelve branch calls exceed 10× MM solver
time, five exceed 10× process time. In those 12 slow rows, the inherited base costs
95.980s, core 77.437s, known layout 62.266s on 11 rows, expansion 16.657s, branch 1.173s
and final gate 0.035s. These timers overlap hierarchically; unassigned core time
is not labeled JIT. Cost is predominantly upstream of the small branch stage.
A061 supplies no across-seed variance estimate; the separate A056 four-seed
results and A057 failures remain visible rather than being replaced by this
successful seed. The branch stage is retained within measured scope, not shown
to dominate MM across classes.

For future decisions, keep the old success/quality/≤3× verdicts as historical
facts while using **quality first, with runtime roughly in MM's order** as the
research objective. Report success, common-pair ACL/Q, optimal ties, seed variability,
all regressions, and all-attempt solver/CPU/process costs separately. A universal
median multiplier can hide both real quality gains and expensive easy-input
failures; it should not substitute for those measurements.

An explicit subsequent allocation experiment is legitimate when a binding cap
leaves a stated reach or quality question unresolved. Freeze the exact affected
limit, unchanged search/acceptance/order, a small diverse complete-constructor panel
and a finite common wall envelope before its outcomes; retain both complete arm
outputs without best-of selection. First distinguish local-query denial, total
work denial, pass completion, search-reserve stop and late publication. Merely
raising the outer timeout does not override B's hard 20s or A's local limits.
Do not repeat C011's rejected explanation without a different stated question.

Calibrate any future defensive work cap against **actual target-process**
wall/CPU costs, including setup, failed searches and certification; save distributions
by operation type and binding stage. Prefer wall as the resource boundary and
transparent counters as diagnostics unless a calibrated work backstop has a
specific purpose. Account for metering overhead rather than claiming abstract
charges are CPU. A later calibration or allocation revision must have its own
identity and complete-output comparison; it must not retroactively relabel old
failures, erase regressions, or silently tune an allowance until it succeeds.

Self-critique: saved scalar counters cannot reveal the success of an unvisited
alternative. The evidence distinguishes several stopping mechanisms, but it does
not attribute every quality gap to caps, representation, acceptance or routing.
Neither removing conservative caps nor retaining a useful local stage replaces
a construction mechanism that produces good complete minors across the difficult
classes. This review proposes no new run and leaves the connector held.
