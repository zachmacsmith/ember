# C014 constrained-routing diagnostic results

2026-09-09. **A different contact tree resolves all three saved terminal failures while every earlier chain remains fixed and every capacity inequality holds.** Each probe succeeds on its first examined root, well inside its five-second interval. This supports a complete-constructor test of contact routing that accounts for reserved boundary capacity. It does not revive C014 or establish an ACL improvement.

The [before-code contract](c_014_routing_diagnostic_contract.md) was hashed before implementation. Root authorized focused checks followed by exactly one frozen three-prefix execution. Four synthetic groups passed first attempt: simultaneous path consumption, previously consumed shared-tree resources, an explicit feasible longer route missed by the single-label heuristic, and rejection of a positive validation that finishes late. Check process wall was 0.041478s; internal wall/CPU were 0.000181/0.000181s. No development prefix was read by those checks.

The first and only [development execution](../../../results/codex/c014-routing-diagnostic/attempt001/status.json) passed with exit 0 and empty stderr. It ran under `-I -S -B` using stdlib, the previously checked prefix helpers and the unchanged original oracle. There were three probes, no constructor calls, no exact solves and no MM or hidden-witness inputs.

| Prefix | Earlier owners / Q | New chain sites | Required old contacts | New owner's remaining capacity / required | Roots generated / examined | Time to fully validated witness | Prefix wall / CPU seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| ER80, g0001 | 20 / 34 | 7 | 5 | 69 / 3 | 1 / 1 | 0.336159s | 0.336164 / 0.332571 |
| ER100, g0101 | 16 / 20 | 4 | 2 | 57 / 6 | 9 / 1 | 0.215431s | 0.215436 / 0.213931 |
| BA100, g0102 | 10 / 16 | 5 | 2 | 82 / 2 | 12 / 1 | 0.191525s | 0.191531 / 0.189204 |

Times include each prefix's input/decode, geometry setup, allowance/component construction, routing and independent validation. Every witness has disjoint connected chains, every original edge among introduced vertices is represented, and every old and new owner satisfies its capacity inequality. Earlier chain maps are unchanged. Capacity counts can decrease when sites are claimed; the inequality and its correct post-birth remaining-neighbor count are preserved, not relaxed.

No completed-root failure or late validation occurred in this execution. Rejected path extensions are still counted: 12, 40 and 115 extensions respectively exceeded an old owner's remaining allowance. Single-label discards, all path receipts and complete witness chains are retained in [the details](../../../results/codex/c014-routing-diagnostic/attempt001/output/details.json). Unexamined roots after a successful witness were intentionally not run, so these are feasibility-search timings rather than exhaustive root-scan costs.

## Mechanism resolved

ER80's old singleton contact domain contained one site that violated an unrelated old owner's zero allowance. The new seven-site tree starts at a root excluded by that old singleton-only rule. A non-singleton tree is therefore necessary to escape this recorded singleton proposal while respecting those unchanged old chains and quotas.

ER100 succeeds from a different pivot root than the recorded C014 roots. Its witness also contains an originally recorded root site, so the successful tree itself is expressible with the old root set; this experiment does not isolate the causal contribution of changing pivot choice. BA100 uses an originally recorded root and finds a different five-site route. Together, these observations identify inadequate contact-tree construction and root selection, rather than a representation requiring overlaps or unavoidable capacity debt.

All three witnesses refute fixed-prefix hard-quota infeasibility. They also show that revisiting an earlier private placement is unnecessary for these particular next insertions. They do not prove that earlier movement is unnecessary later in construction. The single-label path heuristic remains incomplete, as its synthetic counterexample demonstrates.

Total internal wall/CPU were 0.770541/0.762209s; separately recorded process wall was 0.815628s. Shared input/hash checks and module setup are included in total internal time outside the three prefix intervals. These local measurements are not paired MM timings and must not be extrapolated to full-constructor speed. In particular, C014's all-root proposal selection could multiply routing cost substantially.

## Complete-constructor decision

Proceed to the small complete-constructor screen specified in the contract after root source/outcome review. Implement one evolving partial minor whose contact routing respects old boundary consumption and can consider non-singleton routes when a singleton contact choice is capacity-inadmissible. Keep hard capacity inequalities and existing independent validation. The diagnostic maps and discovered chains must never initialize the new constructor. Its allocation is a global construction deadline; the diagnostic five-second interval does not become a per-owner limit.

The immediate screen should include the three ER/BA cases, WS, grid, the hidden singleton control and fresh SBM/planar development instances, with candidate/A061/MM evaluated separately on the same host. Preserve all previous C014 failures, its BA160/planar160 deadline stops and SBM/WS Q regressions as unresolved until measured for the successor. The three new chains contain 7, 4 and 5 sites; local feasibility can therefore carry a quality cost. Only complete-constructor success, per-class mean ACL and charged runtime can decide whether this mechanism is worth retaining. No further local routing diagnostic sequence is justified before that screen, and no constructor has yet been implemented.

Bindings: routing source SHA256 `0b3ae18f80edce63008b33dddb182f37b104d20ad53636ab80952636c4d21339`; checks `bcf0665313adee50c8dee2bf4c36bb5a366f0fbec564ec3ca68656737f62ec04`; 15-file pre-execution freeze `63e1c724d45fae51dcc03f2cda86ee0f0425cac14fccc7cbb4596b910fd6d169`. All source, checks, input and execution records remain under `results/codex/c014-routing-diagnostic/`; the candidate-only packet was reused without modification.
