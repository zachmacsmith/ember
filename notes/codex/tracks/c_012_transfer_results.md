# C012 transfer screen: retire the fixed frontier policy

C012 completed **5/22 encodings, or 4/20 primary structures**, against A061's 22/22 and MM's 21/22. Its two fresh successes both have worse Q than both comparators; all four evaluator-hidden witness controls failed. The fixed policy is rejected. A061 remains retained. The wheel's Q204 versus A061 Q206 is preserved, but MM achieves Q144 on that same encoding. C012 has no observed Q win against MM.

This is exploratory evidence from one seed, ideal Z12, a common 60-second allowance and sequential paired calls on hyde03. The [frozen screen](../transfer_cycle_001_screen.md) contains 12 fresh structures from six families at two sizes, three exposed sparse anchors, K100, four diagnostic controls and two nested relabelings. It is neither a class-mean estimate nor confirmation. Across-seed ACL variance is undefined. Within-embedding chain-length variance is worse than both comparators on four of the five C012 successes and lower on the wheel; these are different statistics.

The [root original-label audit](../../../results/codex/transfer-cycle-001/audit-c001/output/summary.json) passed on its first execution, with 66 accounted calls, no unknown timing fields and no audit errors. The separately reviewed [receipt reader](../../../results/codex/c012-transfer-analysis/attempt001/output/summary.json) also passed once and checked all 22 C012 ledgers. Both invocation/status/log records remain beside their outputs. This note reads those saved outputs only: no candidate, MM, routing, witness inspection or analyzer rerun. The six pre-execution file/reference bindings still match, including C012 source `d51efebe…df096` and receipt reader `68b1a163…87bd5f`.

Every outcome is retained below. Numeric triples are **C012 / A061 / MM**. Q counts occupied sites; ACL is Q/n. F means failure, T means timeout, and neither receives a finite quality score. C012 stop codes are S = complete source, P = `no_carry_with_port`, R = `no_reachable_carry`, L = `lost_live_port`; the fraction is introduced source vertices, not success credit. Grid, honeycomb and wheel correspond to g0013–15. g0021 is a relabeling of g0013; g0022 relabels g0002 and adds no new structure.

| Input | Q | ACL | Solver seconds | Process seconds | C012 stop / introduced |
|---|---:|---:|---:|---:|---|
| g0001 random_er-80 | F / 261 / 248 | — / 3.263 / 3.100 | 2.067 / 7.219 / 2.911 | 2.577 / 9.617 / 3.534 | P 54/80 |
| g0002 barabasi_albert-80 | F / 216 / 257 | — / 2.700 / 3.212 | 2.065 / 6.956 / 1.629 | 2.679 / 9.167 / 2.276 | R 48/80 |
| g0003 regular-80 | F / 268 / 279 | — / 3.350 / 3.487 | 1.369 / 6.860 / 1.398 | 2.026 / 10.018 / 2.130 | R 53/80 |
| g0004 watts_strogatz-80 | 262 / 163 / 136 | 3.275 / 2.038 / 1.700 | 0.906 / 6.261 / 0.552 | 1.524 / 8.810 / 1.123 | S 80/80 |
| g0005 sbm-80 | F / 153 / 131 | — / 1.913 / 1.637 | 0.488 / 6.734 / 0.636 | 1.021 / 9.417 / 1.070 | L 72/80 |
| g0006 random_planar-80 | 239 / 127 / 118 | 2.987 / 1.587 / 1.475 | 1.297 / 6.075 / 0.480 | 1.823 / 8.467 / 0.921 | S 80/80 |
| g0007 random_er-160 | F / 1289 / 1684 | — / 8.056 / 10.525 | 5.129 / 11.168 / 25.083 | 5.743 / 13.189 / 25.663 | R 52/160 |
| g0008 barabasi_albert-160 | F / 633 / 597 | — / 3.956 / 3.731 | 6.122 / 11.106 / 12.357 | 6.851 / 13.744 / 12.794 | P 73/160 |
| g0009 regular-160 | F / 925 / 1018 | — / 5.781 / 6.362 | 3.653 / 10.834 / 6.595 | 4.336 / 13.034 / 7.207 | L 81/160 |
| g0010 watts_strogatz-160 | F / 476 / 368 | — / 2.975 / 2.300 | 1.171 / 9.424 / 2.081 | 1.774 / 12.232 / 2.580 | P 115/160 |
| g0011 sbm-160 | F / 894 / 833 | — / 5.588 / 5.206 | 5.855 / 10.864 / 10.399 | 6.497 / 12.684 / 10.931 | R 83/160 |
| g0012 random_planar-160 | F / 284 / 276 | — / 1.775 / 1.725 | 1.382 / 9.728 / 1.667 | 1.926 / 11.919 / 2.331 | R 125/160 |
| g0013 ember_1584 | 253 / 168 / 133 | 1.977 / 1.312 / 1.039 | 0.481 / 6.610 / 0.477 | 1.072 / 9.064 / 1.072 | S 128/128 |
| g0014 ember_32367 | F / 240 / 202 | — / 1.263 / 1.063 | 0.635 / 10.086 / 0.513 | 1.324 / 12.684 / 1.123 | P 181/190 |
| g0015 ember_2429 | 204 / 206 / 144 | 1.606 / 1.622 / 1.134 | 0.862 / 6.086 / 6.240 | 1.421 / 8.161 / 6.857 | S 127/127 |
| g0016 complete-100 | F / 726 / T | — / 7.260 / — | 25.839 / 11.771 / 63.027 | 26.944 / 13.585 / 63.818 | R 65/100 |
| g0017 singleton_control-80 | F / 201 / 181 | — / 2.513 / 2.263 | 2.714 / 6.917 / 1.750 | 3.438 / 10.028 / 2.433 | P 61/80 |
| g0018 singleton_control-160 | F / 566 / 505 | — / 3.538 / 3.156 | 10.708 / 12.057 / 2.948 | 11.980 / 14.074 / 3.586 | P 99/160 |
| g0019 branch_control-80 | F / 158 / 150 | — / 1.975 / 1.875 | 0.934 / 6.906 / 0.789 | 1.676 / 10.020 / 1.373 | R 70/80 |
| g0020 branch_control-160 | F / 345 / 307 | — / 2.156 / 1.919 | 2.753 / 11.524 / 2.488 | 3.536 / 14.495 / 3.186 | P 112/160 |
| g0021 grid relabel | 294 / 163 / 133 | 2.297 / 1.273 / 1.039 | 0.535 / 7.803 / 0.370 | 1.070 / 10.625 / 0.920 | S 128/128 |
| g0022 BA-80 relabel | F / 220 / 233 | — / 2.750 / 2.913 | 2.667 / 7.214 / 1.696 | 3.434 / 10.171 / 2.177 | P 50/80 |

C012's 22 attempts cost **79.631 solver / 79.624 CPU / 94.671 process seconds**, including **75.551 solver seconds in failures**. A061 totals are 190.202 / 190.169 / 245.207 seconds; MM totals are 146.088 / 146.078 / 159.107, including its K100 timeout. These different success sets cannot support an aggregate speedup claim. Full precision, per-call CPU, within-chain variance, status and validation reasons remain in the [root rows](../../../results/codex/transfer-cycle-001/audit-c001/output/rows.json).

The fresh WS and planar n80 successes fail to transfer to their n160 counterparts. All four controls fail despite independently certified available embeddings; the singleton controls have certified optimum Q=n, while branch witnesses provide upper bounds only. This establishes missed feasible solutions, not their cause. Relabeling the grid increases C012 Q by 41, A061 decreases by 5, and MM remains at Q133. Both BA encodings fail for C012. These two pairs expose encoding sensitivity without estimating its distribution or selecting a favorable encoding.

The publication ledgers distinguish birth cost from carrying:

| Complete C012 output | Birth additions | Restoration additions | Suffix releases | Carry additions | Final Q |
|---|---:|---:|---:|---:|---:|
| WS-80 | 235 | 0 | 0 | 27 | 262 |
| Planar-80 | 208 | 0 | 0 | 31 | 239 |
| Grid | 243 | 0 | 0 | 10 | 253 |
| Wheel | 179 | 1 | 2 | 26 | 204 |
| Grid relabel | 294 | 0 | 0 | 0 | 294 |

Final Q = birth + restoration − release + carry. This is signed event accounting, not a partition of surviving sites by permanent provenance. Grid's Q253 already contains 243 birth sites, versus complete A061 Q168 and MM Q133; its relabel uses Q294 with **zero carrying**. Reducing carrying alone cannot explain away these gaps. This does not predict the counterfactual result of deleting the carry operator, which changes later construction.

**Mechanism diagnosis.** All 17 failures are explicit port/carry failures: eight P, seven R, two L. They stop after 0.488–25.839 seconds; none is deadline-censored or denied by a work counter. Sixteen fail by cut 1. The final published states leave 4,170–4,673 target sites unused, and every live owner still has some unused full-target boundary. These counts do not prove simultaneous usable routes; they show that total target exhaustion is not the observed stopping condition. A three-strip birth domain, irreversible strip expiration, fixed roots, closed-owner immobility and one sequential carry order restrict the admissible continuation. An individual current or next port is not a capacity certificate: several failures retain next ports for every live owner at the last published state, yet the private carry transaction cannot preserve them jointly.

Representation and neighborhood remain confounded here. A complete successful extension outside the strip with all old chains fixed would implicate the window; an extension requiring prior owners to move would implicate immobility or coordinated moves. Neither was tested by the saved-output reader. The hard live-port guard rejected tested private placements; no measured alternative proves that relaxing it would complete the source. C012 has no energy-based acceptance rule, so these failures do not justify another annealing adjustment.

Cost is measured separately: joint suffix births consume **48.357 stage-wall seconds**, ordinary births 19.834 and carrying 3.551 across all attempts. Only **21 of 19,331 joint attempts publish**, and only one of those publications belongs to a completed output. Dense K100 alone spends 18.535 seconds in joint births and still stops with 65/100 vertices introduced. Failed attempts and recorded private paths remain in [the detailed receipts](../../../results/codex/c012-transfer-analysis/attempt001/output/details.json). Stage and event timers overlap and must not be added. Historical intermediate maps are unsaved, so this reader reconciles receipts and final occupancy rather than independently replaying every rollback. Extra wall time under the same stopping rule would not resume these terminal calls; the evidence supports retiring the rule, not raising an unexplained limit or optimizing its repeated failed suffix attempts.

**One redesign direction, not an implementation authorization:** reversible construction guided by physical contact domains. The hypothesis is that anticipating shared contact sites, and retracting the placements that destroy them, can address both inflated birth trees and early loss of continuation. Use Zephyr's orientations, coordinates and actual couplers to prioritize locations across the full target. Keep one evolving partial embedding; no monotone cut, compulsory carrying, permanent owner root or independent complete-output selection. This is distinct from the earlier independent single-site addition/deletion constructor and C012's proper-suffix fallback: the central operation reconsiders mutually constraining placement decisions together.

```text
Maintain one partial original minor and each unplaced vertex's free physical
sites adjacent to all of its already placed neighbors (its singleton domain).
Use these domains and actual target connectivity to rank constrained vertices;
rank positions by shared future contacts and Zephyr geometry, not source labels.
Try a singleton or a shared contact tree; measure how that placement changes
the remaining domains before committing it to the current trajectory.
When placement destroys short contact options, trace the obstructing prior
owners, retract that connected conflict set, and jointly place it with the
blocked vertex. Previously closed owners may move. Preserve outside contacts.
Treat empty singleton domains as pressure to reconsider or grow a tree, never
as proof that a minor embedding is impossible. Validate complete output.
```

Self-critique: singleton domains may be too restrictive as a predictor when short branched trees are the right answer. Domain propagation, conflict extraction and repeated retraction can consume the wall budget or cycle; Zephyr proximity does not certify routes. The current results motivate testing this mechanism but do not establish that it works or is novel. A subsequent before-code policy must specify growth, retraction, acceptance and stopping without smuggling in another unmeasured patch cap.

Cheap falsifier for that subsequent experiment: a small complete-constructor screen spanning a fresh local source, community source, hub source and hidden singleton control, using the audited validator and same-host A061/MM. Record birth Q, destroyed/recovered domains, successful joint retractions, repeated states and stage time. Failure to produce complete improvements on at least two structurally different fresh inputs, or domain recovery without end-to-end progress, rejects the central assumption. Widespread empty domains despite modest successful MM chains would question the representation; admissible joint retractions absent from generated moves would question the neighborhood; generated useful retractions rejected would question acceptance; useful construction censored while domain updates dominate would question cost. Preserve every regression, and keep promotion dependent on the unchanged per-class objective and later independent confirmation. No further C012 refinement or call follows from this proposal.
