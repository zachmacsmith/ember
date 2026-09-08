# Experiment 022: independent redundancy review and validation-order probe

Reviewed 2026-09-08 UTC. This review reads raw results and frozen source independently of `analyze_refinement.py`. It does not change candidate code or rerun the 022 benchmark. A separately requested, two-case instrumented probe uses frozen revision 024 and is documented below.

Equal-size contact rearrangement saves 25 more physical qubits than strict revision-016 `both` across these 18 development incumbents, but regresses on two trials. Its original implementation spends almost three times as long in refinement. Much of that overhead comes from fully validating complete proposals that cannot improve the secondary objective. Revision 024 safely rejects those proposals earlier; the two K100 probes directly confirm that 983 of 993 proposal validations are avoided while preserving outputs and work trajectories. Neither experiment establishes an across-class result or an MM performance claim.

## Protocol and provenance

The [design and critique](../contact_redundancy_revision_022.md) were recorded before implementation. All arms start independently from the same 18 saved `native-search` incumbents from 011, covering nine graphs and two construction seeds on ideal Zephyr Z12. No MM embedding is an input. The three globally fixed arms are legacy strict refinement, strict `both` (16 boundary sites and round-robin groups), and `both_redundancy`, which changes the objective to `(qubits, -contact redundancy)` and permits generated equal-size alternatives. No result is selected per graph.

Every arm uses four passes, 512 group attempts, beam width one, group sizes 1–4, three chain alternatives, two group orders, halo two, region size at most 512, 500000 total charged expansions, 50000 per group, and a 60-second refinement allowance. Source, target, and saved incumbent validation occur before refinement; final validation and independent global coupler counting occur outside its measured time. The 18 legacy replays form the initial gate. The 18 strict `both` results are also checked against their saved revision-016 counterparts before interpreting effects.

Raw artifacts: [022-contact-redundancy](../../../results/codex/022-contact-redundancy). Every output, trajectory, configuration, input identity, guard, and timing remains in its original result file.

| Provenance | SHA-256 |
| --- | --- |
| Frozen 022 source map | `544a8a671b51ad53f0cafe57b23edf88089b72b13b9b22f081f6245202f57a3f` |
| 022 manifest bytes | `b178bf3c6baa6d516f7b09dbe357b9932c0ab934e6842065a7f4fcf58506aaa6` |
| Frozen 022 `contact_repair.py` bytes | `d3fe2b09de3b8086bc3e325282099b74dba14520a89723fc1f796c9cd7eb7f9d` |
| Frozen 022 refinement runner bytes | `a74b4cf1dbdcd9e84e6d52281ffe7519220a9c159db40da75494b1e65f4c7abb` |
| Canonical map of 54 result filenames to byte hashes | `c14b4a8a77adb88a867ec49360fe67859f9dc21e57e48aafb263638e9ff37466` |
| Original 011 input source map | `73cca55965158b69bdbf94340cd36d701acd8fa426be191f457c4945284baeae` |
| Ideal Z12 target record | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |

The manifest records parent revision `14eac906ca88cd87876dfabad16da34cd179d61a`, plus individual graph and file hashes. The target contains 4800 vertices and 45864 undirected edges. The frozen source is authoritative; later plane reuse and contact changes are not retroactively part of 022. Refinement never calls the plane constructor.

## Independent validity and objective audit

The audit passed all 43 source hashes, 46 copied input hashes, 54 task/configuration/result identities, and 54 final embeddings. Structural checking covered exact source coverage, nonempty connected chains, target membership, no duplicated or shared qubits, and every logical contact. ACL, total qubits, maximum chain, and within-chain variance match recomputation. All 54 results are timely `SUCCESS`, return code zero, with MM absent from installed metadata and no prohibited import attempt or loaded module. All 18 legacy embeddings exactly match the saved Joint1 references, and all 18 strict `both` embeddings exactly match 016, including chain-list order.

For a valid embedding, direct enumeration of target edges counted the couplers between each pair of chains joined by a source edge. Edges within one chain and edges between logically nonadjacent chains were excluded. Every required source pair has at least one coupler. The global score is

`R = sum over source edges {u,v} of (number of target couplers between C[u] and C[v] − 1)`.

The frozen `_contact_redundancy` helper agrees with independently enumerated counts on **6053 comparisons** using the 18 initial and 54 final embeddings, empty/all-vertex selections, individual source vertices, and selected groups taken from recorded trajectories.

The helper's arithmetic is correct for these simple undirected graphs. When both endpoints are selected, it encounters each physical coupler and logical edge twice, then halves both counts. With one selected endpoint, it counts each once. Thus it returns exactly the excess couplers on source edges incident to the selected group. Source edges wholly outside the group remain unchanged by reconstruction, so the incident-score difference equals the global difference.

All **805 recorded accepted steps** satisfy their declared qubit arithmetic and cumulative work bounds. The redundancy arm contains 463 accepted group moves: 203 reduce qubits and 260 preserve size while strictly increasing recorded redundancy. Starting with independently measured global `R`, every recorded step strictly improves `(Q,-R)`, and accumulated changes end at the independently counted final global score. Equal-size steps add 444 redundancy units; qubit-shortening steps lose 271, for a net increase of 173. A shrinking move is allowed to reduce redundancy because qubit count has priority.

Intermediate chain contents are not serialized. Consequently, individual recorded score increments are checked through strict lexicographic arithmetic, endpoint consistency, source inspection, and independent helper comparisons; they are not reconstructed from per-step embeddings. This distinction matters when describing the strength of the audit.

For strict arms, `diag.contact_redundancy_gain` remains zero because that secondary score is disabled. It does **not** mean their actual global redundancy stayed constant. Use the separately enumerated initial/final score fields for those arms.

## Quality and work

Qubit pairs below are seeds 0 and 1, in that order. Means average only those same two saved incumbents.

| Source | Strict Both qubits | Redundancy qubits | Strict mean ACL | Redundancy mean ACL |
| --- | --- | --- | ---: | ---: |
| Bipartite 30+30 | 148, 148 | 148, 148 | 2.466667 | 2.466667 |
| Complete 100 | 726, 726 | 726, 726 | 7.260000 | 7.260000 |
| Complete 40 | 155, 152 | 155, 153 | 3.837500 | 3.850000 |
| Grid 8×8 | 84, 86 | 82, 85 | 1.328125 | 1.304688 |
| Honeycomb 5×5 | 79, 82 | 75, 82 | 1.150000 | 1.121429 |
| King 8×8 | 112, 115 | 110, 110 | 1.773438 | 1.718750 |
| ER 80 | 263, 240 | 260, 234 | 3.143750 | 3.087500 |
| Regular 80, degree 3 | 122, 110 | 124, 110 | 1.450000 | 1.462500 |
| Watts–Strogatz 80 | 132, 119 | 130, 116 | 1.568750 | 1.537500 |

Against strict `both`, the redundancy arm wins nine trials, ties seven, and loses two. Improvements sum to 28 qubits, offset by a one-qubit K40 seed-1 regression and a two-qubit regular seed-0 regression. Across the same nine source means, its mean ACL is 2.645448 versus 2.664248 for strict `both`; total final qubits are 3574 versus 3599. Five source means improve, two tie, and two worsen. These are development observations, not graph-family estimates.

Sample ACL variance does not uniformly improve. With two samples and denominator one, grid variance rises from 0.0004883 to 0.0010986; honeycomb rises from 0.0009184 to 0.0050000; ER rises from 0.0413281 to 0.0528125. King's two final ACLs agree, giving sample variance zero, while its strict variance was 0.0010986. Two samples provide one degree of freedom and cannot establish a variance advantage.

| Aggregate over 18 calls | Legacy | Strict Both | Both with redundancy |
| --- | ---: | ---: | ---: |
| Qubits saved from Search incumbents | 170 | 191 | 216 |
| Accepted group moves | 160 | 182 | 463 |
| Equal-size accepted moves | 0 | 0 | 260 |
| Group attempts | 7913 | 8981 | 8927 |
| Charged expansions | 3869129 | 4142004 | 4411954 |
| Complete proposals | 160 | 182 | 13598 |
| Tree construction attempts | 250043 | 298533 | 305854 |
| Refinement wall, seconds | 14.3110 | 16.1826 | 48.3616 |
| Refinement CPU, seconds | 14.3038 | 16.1773 | 48.3481 |

Strict Both and the redundancy arm each stop 16 times at the group cap and twice at the work cap. Neither exhausts an unbounded neighborhood or reaches a deadline. Group generation still omits groups without excess over the individual size lower bounds, and the width-one prefix beam ranks size and deterministic physical order rather than the final redundancy objective. These limitations prevent any completeness interpretation of the secondary-objective search.

The 022 redundancy arm uses 2.989× aggregate refinement wall, despite only about 6.5% more charged expansions. Its median paired wall ratio is 1.682. Charged BFS/boundary work does not count full-graph validation or redundancy scoring, so that counter alone substantially understates the extra computation.

K100 contributes 71.1% of the added wall: its two redundancy calls use 27.379 seconds versus 4.506 seconds for strict Both. They accept ten equal-size moves in total, increase redundancy from 768 to 786 in each case, and save **no** qubits. More redundant couplers therefore do not by themselves establish useful shortening. The remaining quality gains justify investigation, but this original timing result does not justify promoting the arm as a general improvement.

## Validation-order reasoning

In frozen 022, each counted complete proposal is assembled into `trial`, fully validated through `ctx.valid(trial)`, then scored for redundancy. All 13598 complete proposals in the redundancy arm therefore cause a full validity check, even when equal-size proposals cannot improve the current best score. Counts of final accepted groups alone do not identify exactly how many checks are avoidable: a group may examine multiple complete proposals, including invalid or intermediate improving candidates.

Moving the exact redundancy comparison ahead of validation is behavior-preserving for generated candidates under fixed work limits:

1. The size filter already rejects oversized proposals and rejects equal size under the strict objective.
2. For an equal-size redundancy proposal, `redundancy <= best_redundancy` is sufficient for rejection regardless of validity. The scorer and validator are pure; rejecting here cannot remove a candidate the old code would accept.
3. Every potentially improving proposal must still pass complete original-graph validation before `best`, `best_size`, or `best_redundancy` is changed. Smaller accepted candidates must retain their correct redundancy for subsequent equal-size comparisons, even when it is lower than the previous score.
4. Keep `complete_proposals` incremented before the new rejection, preserve proposal ordering and all work counters, and do not add random draws or modify prefix ranking.

The score is defined before validation for `_repair`'s generated candidates: the original incumbent is valid, selected chains are built from known target-region vertices, and full trial keys come from the incumbent plus selected assignments. This is not permission to score arbitrary malformed public inputs before establishing their type/key/membership preconditions. The optimization retains full validation for possible acceptance. Faster execution can change how much work fits under a wall deadline; it promises fixed-work behavior rather than identical timeout trajectories.

## Frozen 024 replay and direct validation-count probe

Revision 024 implements that reorder. Its frozen source map is `b9faba282725123074247e5fb97a617c538827030fcc245d65b558cc30243b37`, under [024-redundancy-validation-order](../../../results/codex/024-redundancy-validation-order). Independent comparison of all **54** 024 records against 022 finds identical embeddings, configurations, initial/final redundancy, and every non-time refinement diagnostic and trajectory. No plane behavior enters these refinement calls.

The raw 024 refinement totals are 13.9553 seconds for legacy, 16.0525 for strict Both, and 17.9276 for redundancy. The revised redundancy total is about 11.7% above its strict control rather than the original near-threefold total. These are uninstrumented recorded refinement timings; the validation-count probe below is kept separate.

The bounded probe loads only frozen 024 source and the two K100 native-search incumbents, wraps `_Context.valid` to count calls, runs the declared redundancy configuration once per seed, and independently validates each output. It requires exact equality with that seed's saved 024 embedding, objective endpoints, and all non-time diagnostics and trajectories. It uses the isolated native interpreter with MM/busclique guards. The script and its two JSON outputs are additive artifacts; no raw trial is overwritten:

- [Probe script](../../../results/codex/024-redundancy-validation-order/validation_count_probe.py)
- [Probe records](../../../results/codex/024-redundancy-validation-order/validation_count_probe)

| K100 seed | Complete proposals | Total `ctx.valid` calls | Initial validation | Proposal validations | Skipped proposal validations |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 451 | 6 | 1 | 5 | 446 |
| 1 | 542 | 6 | 1 | 5 | 537 |
| Total | 993 | 12 | 2 | 10 | 983 |

The formula is `skipped = complete_proposals − (ctx.valid calls − 1)` for each call, because `contact_polish` validates the initial incumbent once and all other counted calls are complete-proposal checks. External validation uses independent graph operations and does not enter the counter. Both probe outputs pass exact reference/work/trajectory matching and original graph validation. Their `instrumented_probe_wall` fields are explicitly diagnostic timings, not benchmark samples or extra replicates.

Probe record SHA-256 values:

- Seed 0: `915220356d0e9db94031c8489840bd16792efa38c2808c889d6c510c0f5e1052`
- Seed 1: `49cf093e5dfef2013300f5a408d9eb8288915437b8f682bcf9e5e80db0dad8c8`

This confirms the avoided validation work directly on the two expensive cases. It does not imply that the same fraction is avoided on every source or that validation should be weakened elsewhere.

## Limits

The runs use an unreserved `dabhmbp` arm64 host with Python 3.10.19 and the same dependency versions as 016. In 022 the worker-start one-minute load ranges from 14.63 to 36.07; the local plane timing diagnostic in 021 overlapped part of the run. Single refinement calls do not estimate timing distributions. The large measured validation-count reduction is direct mechanism evidence; wall-time ratios remain descriptive shared-host measurements.

All comparisons reuse development incumbents already examined while designing these mechanisms. No fresh constructor or MM benchmark was run here. The source-specific regressions, two-seed uncertainty, remaining MM quality gaps documented in earlier reviews, and lack of broader corpus confirmation preclude an across-board improvement claim. No novelty claim follows from a standard strict lexicographic secondary objective or its evaluation-order optimization.
