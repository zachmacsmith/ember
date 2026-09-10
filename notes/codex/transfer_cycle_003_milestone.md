# Mechanism decisions before the next complete screens

2026-09-09. The goal remains unmet. **A061 is still the single retained
algorithm**; its [full class record](mm_gap_retained_a061.md) has 34/34 valid
attempts versus MM 29/34, with eight lower-ACL results, seventeen losses and
four optimal ACL1 ties on common successes. Earlier failures and unmeasured
Sudoku remain explicit. These one-seed observations do not estimate across-run
variance or class populations. No independent outputs are combined.

The capability we understand better is construction that considers a whole
chain's contacts together. The [pinned MM review](stock_mm_capabilities_review.md)
identified all-neighbor reconstruction and movable contacts. The new experiments
separate three reasons our searches fail to use that capability effectively:

| Track | Resolved observation | Complete-constructor evidence | Next decision |
|---|---|---|---|
| A, inherited construction | Owner interleaving exposes useful existing moves; root ranking now consumes 81.50% of the added search stage. | A064 preserves all 22 A061 successes, improves 21 Q values and ties K100. It still loses 16/21 common MM comparisons and costs 2.03–156.02 times MM on them. | Test exact compiled root ranking, then a diverse complete screen if its cost is repaid. A064 is promising, not promoted. |
| B, movable overlapping trees | The minimum distance-sum root misses lower actual shared-site cost on all four saved failed states. Lower priced cost can also worsen overlap. | B028 remains rejected at 2/6 successes versus A061/MM 6/6. The diagnostic supplies no new valid embedding. | Design cheaper evaluation of constructed site unions; test complete feasibility and ACL, not the surrogate alone. |
| C, disjoint contact construction | Capacity-aware routing finds valid insertions for all three blocked prefixes with every older chain fixed and all quota rules satisfied. | C014 remains rejected at 4/9 versus A061/MM 9/9, including its preserved quality regressions. Local route witnesses are not new constructor successes. | Implement C015 with constrained contact routes, capacity-safe growth and first-admissible placement; test eight complete inputs promptly. |

The common general mechanism is to evaluate the sites used by a connected
contact tree while constructing it. A's successful neighborhood can change
several contacts together. B shows that summing separate path distances can
misrank the resulting union. C shows that constructing a tree first and only
then rejecting its boundary consumption misses feasible insertions. These are
complementary findings across separate tracks, not a combined algorithm or a
proof that one mechanism will win across classes.

A's [broader per-input and family results](experiments/064_broader_transfer_results.md)
preserve the sparse grid/honeycomb/wheel, WS, SBM, planar and control deficits;
ER80 and BA160 losses remain visible despite favorable mixed-size family means.
Every timing and within-chain variance is reported. Across-seed variability,
full class coverage for the successors and roughly-MM-order runtime remain
unresolved. No dense-graph aggregate substitutes for those requirements.

Stop bulk root enumeration as B's default diagnostic allocation: it used the
entire budget before any contact retargeting was tested. Retargeting is therefore
untested, not refuted. Also stop the C last-birth substitution search: all 140
saved combinations failed, while a changed contact route supplied a witness
immediately. Do not continue C routing diagnostics after the three positive
witnesses. Preserve every rejected fixed policy and the fresh ER100 example
where lower priced cost increased overlap.

The [fresh input panel](transfer_cycle_003_input_results.md) adds WS100, SBM100
and planar100 without reseeding or replacement, retaining old encodings and
nested relabelings separately. Independent identity/exposure checks pass.
These are development inputs; no untouched confirmation set has been created.
Each complete screen will freeze its source, subset and allocation independently,
use isolated dependencies and the existing original-minor validator, and charge
all failures with paired timing on one host.

Detailed diagnostics: [B's score/cost inversion](tracks/b_028_failure_diagnostic_results.md),
[C's saved-choice failures](tracks/c_014_failure_diagnostic_results.md), and
[C's valid constrained routes](tracks/c_014_routing_diagnostic_results.md).
