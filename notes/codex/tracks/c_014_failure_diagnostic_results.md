# C014 saved-prefix diagnostic results

2026-09-09. **All three private prefixes reconstruct correctly, but none of the 140 saved alternative combinations resolves the failure.** The zero-allowance component test proves infeasibility on none of them. This rejects the narrow remedy of substituting the immediately previous saved placement while keeping a recorded failed tree; it leaves untested connected routes and earlier coordinated movement as distinct explanations. C014 remains rejected.

Root approved the exact frozen script after reading it, verifying all 19 preparation bindings and receiving an independent B-track static review. Approval is additive at `results/codex/c014-failure-diagnostic/root_approval001.json`. The single [recorded execution](../../../results/codex/c014-failure-diagnostic/attempt001/status.json) passed with exit 0 and empty stderr. It used the unchanged original oracle under `-I -S -B`, without a constructor, new routing query, exact solve, MM map or hidden witness.

| Input | Independently valid private owners / Q | Rejected trees checked | Saved safe previous placements | Pairs examined | Valid minor but quota failure | Overlap | Admissible witnesses | Case wall / CPU seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| g0001, ER80 | 20 / 34 | 1 | 8 | 8 | 8 | 0 | 0 | 0.1561 / 0.1479 |
| g0101, fresh ER100 | 16 / 20 | 12 | 1 | 12 | 12 | 0 | 0 | 0.1485 / 0.1440 |
| g0102, fresh BA100 | 10 / 16 | 12 | 10 | 120 | 102 | 18 | 0 | 1.0527 / 0.6975 |

Every decoded prefix passes induced-source contact, disjointness and connectivity checks, has safe individual capacities, and matches the saved owner count, Q and reintroduction chronology. All 19 saved previous-placement proposals also pass those checks independently. The 25 recorded rejected trees reproduce every recorded capacity pair and old-owner deficit exactly. All subsequent pair failures are preserved in [the diagnostic details](../../../results/codex/c014-failure-diagnostic/attempt001/output/details.json). Duplicate proposals and selected-chain controls were retained: their pair counts are respectively 3, 12 and 12. These are finite recorded choices, not independent embeddings or extra development instances.

For ER80, all eight valid-contact combinations leave owner 49 short by one boundary site. ER100 has one safe previous placement, so its twelve pair checks are controls: four leave owners 28, 61 and 93 short by one each; two leave owners 28 and 93 short by two each; six leave those two short by one each. For BA100, all 102 valid-contact pairs leave owner 73 short by one. The remaining 18 pairs satisfy individual quota counts but overlap; they are invalid and provide no constructive evidence. Improving quota counts alone would have misclassified them.

## What the component test does and does not show

| Input | Old owners with zero allowed consumption | Excluded free boundary sites | Remaining component size | Required old neighbors touched |
|---|---|---:|---:|---:|
| ER80 | 49, 56 | 14 | 4,752 | 5 / 5 |
| ER100 | 28, 93 | 11 | 4,769 | 2 / 2 |
| BA100 | 73 | 13 | 4,771 | 2 / 2 |

Each remaining target graph has one component, and it touches every chain that the next source vertex must contact. Thus the cheap sufficient certificate of fixed-prefix quota infeasibility does **not** apply. Component survival is explicitly inconclusive: a connected route can consume more than another owner's positive allowance or leave the new owner with too little remaining capacity. This is not evidence that a quota-safe route exists, and it does not justify relaxing quotas.

Total internal diagnostic wall/CPU were 1.3988/1.0258s; separately recorded process wall was 1.4699s. Case times include independent validation of successful and failed proposals. Prefix extraction and synthetic check costs remain separately recorded in [the preparation note](c_014_failure_diagnostic_preparation.md). No additional constructor runtime or quality result was produced.

## Next bounded decision

The justified unresolved question is now whether constructing a different contact tree while excluding forbidden boundary sites can satisfy **all** individual capacities with these exact old chains fixed. The completed experiment supports one short routing instrument on each of the three prefixes, with the previously proposed allowance of at most five seconds per prefix, full independent validation and all failure/time accounting. This would require root authorization and a frozen before-code specification; no such routing code or execution has occurred.

A valid route in ER and BA would identify a general interaction missing from C014: capacity constraints must inform contact routing before a greedy tree is built and rejected. That mechanism should then move promptly into a small complete-constructor screen, rather than accumulating local repairs. If bounded routing fails without a rigorous certificate, the result remains censored or inconclusive; deeper search is not automatically warranted. Earlier coordinated placement changes remain an alternative mechanism, and the recorded last-birth failures give no reason to repeat that exact substitution search. The original five constructor failures and the SBM/WS quality regressions remain unchanged.
