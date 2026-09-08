# Experiment 033: cumulative direct-singleton ablation

This is a preimplementation development protocol. The detailed operator and its
self-critique belong in `../singleton_relocation_spec.md`; that specification,
the implementation and correctness checks must be complete before the run is
frozen or any 033 embedding call begins.

Use all 34 distinct source structures in readiness selection 017, ideal Z12,
solver seed zero and 60 seconds per call. Compare two fixed configurations in
the same frozen source: the spectral/contact control from 026/032 and that same
pipeline with `polish_singleton_policy='direct'`. Run 68 full native calls, with
one construction and one evolving refinement state per call. No source ID,
family, coordinates, MM embedding or previously saved candidate embedding enters
the solver. The proposed method is a refinement operator inside one algorithm.

Keep the control's 1000 placement-evaluation ceiling, four refinement passes,
512 total group visits, group sizes 1–4, width one, 500000 total refinement work
units, 50000 per group, 16 extra boundary sites for ordinary reconstruction and
512-qubit ordinary region cap. The direct operator's scans and cache maintenance
consume the declared shared allowance. Its exact subsidiary cap and scheduling
must be recorded in the operator specification before freezing source. No extra
budget is granted simply because direct mode is enabled.

Correctness checks must cover complete common-boundary enumeration against a
small independent exhaustive oracle; strict qubit and equal-qubit contact
acceptance; occupied-site exclusion; stale-cache prevention after every type of
accepted move; degree-ineligible and all-singleton-neighbor skips; mixed labels,
isolates, binding work limits and expired deadlines. The legacy policy must
preserve the existing default behavior. A failure to find a singleton must
retain ordinary reconstruction's opportunity to shorten a longer chain. The
current incumbent survives any incomplete scan or failed proposal.

Measure final qubits/ACL, full solver/process times, construction and pruned
counts, all move/work/stop diagnostics, successes, failures and deadline
overruns. Report all wins, ties and regressions by input and mapped family;
count the shared king/frustrated-square graph once in aggregates. Compare the
control's physical chain sets with the existing seed-zero spectral result as
a separate quality replay check. Use same-run pairs for runtime, and label any
MM quality references from other experiments as historical. No across-run or
cross-host timing pooling is allowed.

Both arms start from their own complete pipeline. A promising move on a saved
final embedding cannot establish the cumulative result: extra work or visits
can displace useful joint reconstruction, while early accepted moves can change
subsequent opportunities. The end-to-end comparison must preserve such losses.
These remain inherited development inputs at one solver seed, providing neither
family mean estimates nor a clean generalization test. Do not tune the direct
budget, interleaving interval or method choice by observed family outcomes.

Use a node only after its isolated environment and logout-persistent supervisor
are verified. The current four-seed experiment on hyde03 owns that node's
sequential benchmark slot. Record the actual 033 host and frozen source/transport
identities before launch; do not overlap benchmark jobs on a node merely to
shorten elapsed development time.
