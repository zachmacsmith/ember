# Reject nonimproving scores before full validation

This is a behavior-preserving optimization of revision 022, not a new search
policy. The complete proposal's incident coupler score is defined on generated
chains drawn from the known target region. If its qubit count equals the current
best and its redundancy does not improve, reject it before full embedding
validation. Both computations are pure, and that proposal could not be accepted
under the existing lexicographic objective. All potentially accepted proposals
still receive full validation before any incumbent update. Public input checks
remain unchanged. This ordering must not be used to accept malformed embeddings.

An independent review agreed with this reasoning. The regression constructs
nonimproving equal-size proposals, confirms unchanged valid output, and confirms
that full validation is needed only for the input. Replay all 54 cases of 022
with exactly its work limits, configurations, incumbents and method order, then
require every embedding to match the saved result. Fixed-work search decisions
should remain identical; reaching more work under an active wall deadline would
be a separate effect. No comparison here approaches its 60-second allowance.

The new run is `results/codex/024-redundancy-validation-order`. Compare outputs
against `022-contact-redundancy` and independently enumerate contact redundancy.
Retain all timings, including cold process overhead. This is a later run on the
same unreserved laptop, so elapsed-time ratios have temporal confounding; fewer
unnecessary validations are the directly established implementation change.

All 54 observations completed successfully; every final embedding exactly matches
022. Both new and old strict control outputs match too. The source snapshot is
`b9faba282725123074247e5fb97a617c538827030fcc245d65b558cc30243b37`.
The independent result analyzer checked original embeddings, final quality,
lexicographic trajectory arithmetic, source/input/configuration identity, caps,
dependency guards and the full endpoint redundancy delta.

The redundancy arm's total measured refinement wall fell from 48.3616 to 17.9276
seconds, with unchanged qubits, accepted trajectories and 4,411,954 expansions.
Its same-run strict sites/groups control took 16.0525 seconds, close to 022's
16.1826 seconds. The new median paired redundancy/control wall ratio is 1.1285.
Thus the equal-size mechanism retains its 25 additional qubits saved across the
18 inputs at a much smaller observed overhead. These remain descriptive local
timings, not an end-to-end MM comparison. Dedicated validation-count probes will
test the proposed explanation without overwriting any original trial.
