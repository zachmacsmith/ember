# A064: broader owner coverage improves complete embeddings; ranking dominates cost

2026-09-09 UTC. **Exploratory result: the frozen criterion for one broader
complete-constructor screen is met. Do not promote A064 over retained A061.**
Changing only the A063 owner/root schedule improves final Q on all nine inputs,
including both fresh structures. Eight MM quality deficits remain, and eight
paired solver-time ratios exceed 10. The next decision is broader transfer of
the frozen mechanism, before another refinement or a new allocation policy.

## Evidence and complete outcomes

Root supplied the terminal 36/36 archive from hyde06: supervisor exit 0, tmux
absent, lock free, 306 verified files, archive digest
`2d99f6b4bddf3184717ef8f12ed879d96d313d11c95f6a662f5a7513851b2f5c`.
The original [shared audit](../../../results/codex/transfer-cycle-002/audit-a001/output/summary.json)
is the sole authority for final credit and all-method comparisons. The prepared
[passive reader](../../../results/codex/a064-transfer-analysis/mechanism.py), SHA
`7eb048745a0de74911bea657c690ed3802b1c5e64affb9770fd845fcfc9d0f28`,
ran once in [attempt001](../../../results/codex/a064-transfer-analysis/attempt001/status.json):
PASS, exit 0, empty stderr, 0.169s process wall. Its
[rows](../../../results/codex/a064-transfer-analysis/attempt001/output/rows.json)
retain per-epoch and admission details. No constructor, validator, MM-map read
or physical move replay occurred in this analysis. A later ad hoc table read
mistook the legacy query count for a list; that analysis-only failure is saved
in `results/codex/a064-transfer-analysis/table-preparation-error001.json`.
The mechanism reader was not rerun.

All four methods succeed on all nine seed-0 inputs under separate 60s
allocations, paired on the same host. All 36 attempts have known solver/CPU/
process times; there are no failed, invalid, late or uncredited calls. Candidate
dependency isolation and original-graph validation are inherited from the
unchanged audited harness. Timely returned incumbents coexist with nine added-
operator deadline stops; these are not failed complete calls.

For every input, A064's inherited base Q equals both fresh A061 Q and A063's
inherited base Q. Consequently the observed stage contribution is Q −110;
A063 contributes −18, so the paired A064 improvement is −92. These are sums of
observed chain sizes, not a class-weighted objective or a portfolio result.

| Input | A061 Q → A063 Q → A064 Q | MM Q | A064 / MM ACL | Q gap to MM | A064 / MM solver seconds | Solver ratio |
|---|---:|---:|---:|---:|---:|---:|
| ER80, g0001 | 261 → 260 → 252 | 248 | 3.1500 / 3.1000 | +4 | 59.010 / 3.011 | 19.60× |
| SBM80, g0005 | 153 → 151 → 142 | 131 | 1.7750 / 1.6375 | +11 | 59.011 / 0.929 | 63.54× |
| BA160, g0008 | 633 → 631 → 614 | 597 | 3.8375 / 3.7313 | +17 | 59.026 / 13.537 | 4.36× |
| Watts–Strogatz80, g0004 | 163 → 163 → 161 | 136 | 2.0125 / 1.7000 | +25 | 59.013 / 0.490 | 120.51× |
| Planar160, g0012 | 284 → 284 → 280 | 276 | 1.7500 / 1.7250 | +4 | 59.330 / 1.941 | 30.57× |
| Hidden singleton control80, g0017 | 201 → 201 → 199 | 181 | 2.4875 / 2.2625 | +18 | 59.016 / 1.816 | 32.50× |
| Grid128, g0013 | 168 → 164 → 162 | 133 | 1.2656 / 1.0391 | +29 | 59.012 / 0.615 | 95.99× |
| Fresh ER100, g0101 | 344 → 344 → 332 | 350 | 3.3200 / 3.5000 | −18 | 59.017 / 2.540 | 23.24× |
| Fresh BA100, g0102 | 282 → 273 → 237 | 199 | 2.3700 / 1.9900 | +38 | 59.009 / 4.727 | 12.48× |

A064 beats A063 and A061 on every input, but its only MM win, ER100, was already
an A061 win. The equal-input mean ACL remains worse than MM: 2.440903 versus
2.298368. No new MM-winning input or class is established. The hidden control
still misses its known Q=80 lower bound by 119 sites; the witness was hidden
from candidates, and MM also misses this optimum. These selected single-seed
observations are not estimates of whole-family means.

The seven reused inputs plus two new intermediate-size structures support
transfer across several source structures and sizes. Both new graphs improve:
ER100 saves 12 Q over both predecessors; BA100 saves 36 over A063 and 45 over
A061. There are no new relabelings, repeated seeds or untouched confirmation
inputs here. Wheel's previously recorded late-root gain and variance regression
remain preserved, untested risks. The broader panel must include them.

## Variability and total cost remain explicit

These are **within-embedding chain-length variances**. Run-to-run ACL variance
is unmeasured. A064 worsens this statistic against A063 on six inputs and
against A061 on five; the complete values remain in the audit.

| Input | A061 variance | A063 variance | A064 variance | MM variance |
|---|---:|---:|---:|---:|
| ER80 | 1.568594 | 1.512500 | 1.552500 | 1.640000 |
| SBM80 | 0.779844 | 0.674844 | 0.574375 | 0.406094 |
| BA160 | 5.391836 | 6.928086 | 5.161094 | 5.871523 |
| Watts–Strogatz80 | 0.861094 | 0.861094 | 0.887344 | 0.435000 |
| Planar160 | 1.024375 | 1.024375 | 1.025000 | 0.836875 |
| Singleton control80 | 0.774844 | 0.774844 | 0.799844 | 0.918594 |
| Grid128 | 0.324219 | 0.202148 | 0.195068 | 0.037537 |
| ER100 | 2.066400 | 2.066400 | 2.137600 | 2.130000 |
| BA100 | 3.287600 | 3.257100 | 3.773100 | 1.769900 |

BA160's previous maximum-chain regression improves from A063 18 to A064 11
(A061/MM 12). BA100 retains maximum chain 12 versus A061 9 and MM 6. The
[prospective objective clarification](../variance_objective_clarification.md)
was saved before these outcomes were read: variance increases are reported
secondary tradeoffs, not automatic publication vetoes. The frozen exploratory
criterion is unchanged, and no mean-ACL, success or runtime deficit is waived.

| Method | All-attempt solver wall, s | Solver CPU, s | Process wall, s |
|---|---:|---:|---:|
| A061 | 85.751 | 85.510 | 104.056 |
| A063 | 531.159 | 531.058 | 549.193 |
| A064 | 531.445 | 531.414 | 551.005 |
| MM | 29.604 | 29.596 | 34.638 |

The added A064 stage costs 455.944s; its inherited base costs 74.688s. Inherited
and separately run A061 times differ despite equal Q. A064 is not an end-to-end
speed improvement over A063 at this frozen allocation. Its 4.36–120.51× paired
MM solver ratios expose an unresolved cost problem, without introducing a
universal ratio gate. Process peak RSS is 317.30–332.21 MiB for A064 versus
307.04–311.69 MiB for A063, using the existing process-level measurement.

## Mechanism and computation

| Input | A064 owners queried / n | Owners with a completed root | A063 query count | A064 roots examined | Commits | First / last admission from wrapper start, s |
|---|---:|---:|---:|---:|---:|---:|
| ER80 | 80/80 | 73 | 2 | 136 | 6 | 8.613 / 56.504 |
| SBM80 | 80/80 | 58 | 2 | 6,772 | 10 | 5.644 / 29.987 |
| BA160 | 142/160 | 140 | 3 | 140 | 11 | 40.681 / 58.689 |
| Watts–Strogatz80 | 80/80 | 62 | 1 | 5,994 | 2 | 20.234 / 35.694 |
| Planar160 | 160/160 | 96 | 1 | 341 | 4 | 14.576 / 54.287 |
| Singleton control80 | 80/80 | 74 | 1 | 89 | 2 | 15.299 / 20.049 |
| Grid128 | 128/128 | 54 | 3 | 19,567 | 4 | 6.365 / 13.575 |
| ER100 | 100/100 | 93 | 1 | 188 | 9 | 19.886 / 42.307 |
| BA100 | 100/100 | 77 | 4 | 279 | 24 | 11.389 / 54.723 |

A063's query count bounds its distinct-owner coverage; it can include revisits.
A064 queries include owners closed by its unchanged strict-gain bound without
constructing a root. Coverage is over the whole evolving run, not evidence that
all owners were tested against the same incumbent. No final epoch exhausts all
owners. Six stops occur in root ranking and three in reconstruction; BA160 does
not finish even its first owner round. No artificial work limit stops these runs.

There are 72 admitted strict-Q commits: 69 at root rank 1, two at rank 3
(SBM80 and planar160), and one at rank 2 (BA100). This preserves direct evidence
against a first-root-only restriction. Fifty commits change donor chains and
save 80 Q; the other 22 save 30 Q without donor changes. The existing mobile-
boundary neighborhood contains useful moves on all nine inputs, including
several previously stalled cases. Thus representation or acceptance cannot
explain the absence of *these particular* gains in A063; serial search
allocation prevented their discovery within the allowance. Remaining MM gaps
are not assigned a structural cause by this experiment alone.

The computation bottleneck moves substantially. A063 spends 441.075s in
reconstruction and 8.725s in root ranking. A064 spends **388.256s in root ranking
(85.2% of stage wall)** and 60.630s in reconstruction. Cache accounting and
disposal together cost only 0.242s. Ranking is therefore the measured cost
concern; cache bookkeeping is not an explanation for the remaining delay.

Of 1,943 queries, 1,063 noncommitting queries are invalidated by later commits.
They contain 272.481s of active time, including 269.134s of root generation.
There are 993 repeated-owner queries, containing 188.343s of observed root
generation. These overlapping quantities are nested in stage time and are
**not additive overhead or a proof of avoidable waste**: the embedding changed,
and some previous computation established that no immediate gain was found.
BA160, for example, has no repeated-owner query but invalidates 41.728s of
previously prepared work while progressing through its first round.

The reader saves these costs and discarded payloads by epoch. Componentwise
peak cache counts reach 94 contexts and 424,935 stored roots; final retained
payload is zero on all inputs. Per-epoch cache phase times were not recorded
and remain unknown; only whole-operator cache times are available. Some nested
root-generation fields are absent when ranking was not entered, or was not
completed. This does not remove any complete-call time from accounting.

Admission receipts show 69 of the 110 Q savings by wrapper time 30s and 93 by
50s; 17 further savings arrive afterward. These describe one saved trajectory,
not separately validated shorter-budget runs. Late useful work rules out
declaring a shorter universal allowance from early gains alone.

## Research decision

The frozen continuation test asks for additional complete-output Q gains on
at least two structures/families, including a stalled or fresh intermediate
case. All nine improve over A063, and both fresh cases improve, so it supports
**one broader complete screen of unchanged A064**. It does not establish the
all-class objective, reliable success across seeds, or acceptable runtime.
A061 remains the retained research baseline pending that evidence.

Stop extending A063's serial exhaustive-owner schedule as the default research
direction. Preserve its results and use it only when a controlled comparison
needs that schedule. Also stop treating owner coverage alone as progress: here
it earned continuation because complete outputs improved. Do not add another
local operator or acceptance repair before broader transfer. If transfer holds,
the measured follow-up target is root-ranking computation across changing
states; any proposed reduction must preserve correctness and distinguish
useful preparation from repeated work. No root-distance pruning, first-root
cap, new allocation, redesign or broader call is authorized by this note.
