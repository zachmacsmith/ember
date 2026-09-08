# Track B003: bounded congestion cost in the joint constructor

2026-09-08. Saved before code. B002 improves all five B001-common sparse outputs and completes ER, but all dense cases spend20million scans before completion. They have no recorded frontier rejection and retain valid partials. Its109–253 weighted path queries consume that entire scan allowance. This suggests that a compulsory contact site's large remaining-demand price can make the search inspect much of the otherwise cheap free target before reaching it. These aggregate counters motivate the hypothesis; they do not prove that price is the sole bottleneck.

**Only search-metric change:** keep B002's insertion, roots, domain lookahead, frontier checks, endpoint cuts and local pruning. Replace cost(q)=1+p(q) with cost(q)=1+p(q)/(1+p(q)), where p is the same nonnegative sum of remaining-demand/free-boundary ratios. No cap increases, new restart, extra method or family rule.

```text
p(q) = sum(remaining logical demand / free boundary size over owners touching q)
cost(q) = 1 + p(q)/(1+p(q))
run the unchanged B002 joint insertion constructor with this fixed cost
```

For one fixed shortest-path query with fixed occupied sites, terminals and costs, every newly occupied site costs between1 and2. Consequently its minimum-weight returned path uses at most twice the number of new sites in a minimum-new-site path, when such a path exists. This is a per-query statement only: it is not a bound on the complete embedding, cut choices, four-root selection, runtime or eventual feasibility. Individual site-price order is preserved; sums along paths intentionally change.

Self-critique: saturation can route repeatedly through a scarce boundary that the unbounded metric would avoid. Hard frontier checks protect only one remaining extension site, not enough room or future contact feasibility. The previous search may instead be dominated by repeated validation, pricing scans or root alternatives, so this change could save little. A shorter local path can produce a worse complete layout. The formula is conventional cost normalization, not a novelty claim or a standalone new algorithm.

Freeze the same nine source/target bytes, seed0,60seconds,20million scans, four branches and fresh isolated candidate/MM pairs on hyde02. Method `frontier-tree-bounded` is globally fixed. A useful result completes more dense inputs or sharply reduces work while preserving the sparse quality gains; preserve all regressions. Do not choose B002 or B003 separately per input, and do not promote based on an incomplete or late MM comparator.

## Implementation and freeze

Separate module `packages/ember-qc/src/ember_qc/algorithms/factored/frontier_bounded_construction.py`, SHA-256 `b94ff1e9d9a2384cbdb2fcccd7250af770c3758e579849569861932a6483062c`. The saved diff `results/codex/track-b003-checks/source_delta.diff` confirms that the only changes from B002 are the cost formula and document/diagnostic identifiers. Seven guarded targeted checks pass at `results/codex/track-b003-checks/attempt001`; the additional check directly verifies pressure3 gives cost1.75 and all inspected free-site costs lie in[1,2). No candidate implementation or validity proof is inferred merely from that scalar bound.

Shared pilot registry is `frontier-tree-bounded`; pilot SHA-256 `888c9bcc1b6d40fee1035f210b1b78148e962bd26b91194b92cda73960450d1a`. The registry owner ran the newly affected synthetic worker test separately. The actual candidate has no dependency on another constructor at runtime.

Frozen run `results/codex/track-b-bounded-003`: manifest `2a2c9fc35a1b45600f6f6a877ade8a9e37fd249b3a2528749d0b33653e3eec4c`, source snapshot `bfc42e79032d332cc32ff75753602204f75a79beb1c9f941afe6480483e887a1`. All nine graph bytes and target bytes match B001/B002 exactly. Freeze evidence and ordered18tasks are in `results/codex/track-b003-checks/freeze.json`, saved before outcomes. New source/settings require a new identity; the detached run is never restarted after an SSH interruption.


## Completed development screen

All 18 tasks finalized with supervisor exit 0; the controller, detached session and lock were inactive before retrieval. Retrieved archive `results/codex/retrieved/hyde02/track-b-bounded-003` has digest `a153dde2a01a720eccbecb3bc51c7ff031b41247454724b9b8489d36ad8e3106` and 165 hash-checked files. The small saved-data screen reuses the frozen pilot's original-graph validator and task checker. It performs no constructor or MM calls. Seven candidate outputs and both retained partial minors independently validate; no prohibited embedding imports were reported.

| Input | B003 Q / ACL | MM Q / ACL | B003 seconds | MM seconds |
|---|---:|---:|---:|---:|
| complete 40 | failure | 194 / 4.850 | 15.025 | 9.996 |
| complete 100 | failure | 1113 / 11.130, **late** | 22.364 | 66.070 |
| bipartite 30+30 | 330 / 5.500 | 180 / 3.000 | 15.116 | 5.333 |
| ER 80, degree 8 | 298 / 3.725 | 211 / 2.638 | 10.411 | 3.716 |
| regular 80, degree 3 | 114 / 1.425 | 90 / 1.125 | 3.094 | 1.258 |
| Watts–Strogatz 80 | 112 / 1.400 | 94 / 1.175 | 2.987 | 1.240 |
| grid 8×8 | 73 / 1.141 | 70 / 1.094 | 1.560 | 0.563 |
| honeycomb 5×5 | 83 / 1.186 | 71 / 1.014 | 2.347 | 0.381 |
| king 8×8 | 108 / 1.688 | 90 / 1.406 | 2.635 | 0.710 |

There are seven timely common pairs: zero wins, zero ties, seven losses on Q/ACL. The late K100 MM embedding is retained as raw evidence and receives no timely credit. The candidate completes seven inputs versus B002's six. Its new bipartite success is still 150 qubits worse than MM. Relative to B002, ER saves three qubits, regular/Watts–Strogatz/grid/honeycomb retain the same Q, and king loses three qubits. Those six jointly successful outputs therefore have unchanged summed Q. This is one seed on an exposed development panel, with no claim about variance, complete classes or novelty.

The cost hypothesis has partial support: K40 advances from 19 to 32 placed vertices, K100 from 14 to 35, and bipartite finishes in 13,399,495 scans instead of hitting 20 million at 30 vertices. ER scans decrease from 10,217,358 to 8,057,298. Four sparse inputs have almost unchanged scan counts and exactly unchanged Q; their lower across-run wall times therefore do **not** establish an algorithmic speed gain from this cost change. Contemporary candidate/MM ratios range from 2.41 to 6.15 on the seven valid pairs. Host load is approximately 33–34 on 32 logical CPUs; candidate CPU/wall ratios are 0.99846–0.99993, indicating little direct descheduling but not ruling out cache, frequency or other contention effects. These are host-specific observations.

K40 stops through `construction_blocked` after 11,201,262 scans, 132 root branches and 932 path queries. Its retained 32-chain partial occupies 267 sites, remains valid, and satisfies the stated one-free-port condition for every unfinished chain. Thirteen chains nevertheless have fewer free boundary sites than remaining neighbors (minimum difference −6). K100 hits the unchanged 20-million work limit at 35 chains / 315 sites after 1,002 path queries; 26 chains have that stronger deficit (minimum −64), again with no violation of the one-free-port condition. Such deficits are not proofs of infeasibility: later growth may expose additional sites. They demonstrate why that invariant cannot certify enough capacity for future contacts. The counters do not distinguish a globally blocked geometry from an omitted root, cut or path alternative.

The saturation change improves progress but does not make the constructor competitive. Do not promote it or select B002/B003 per input. The next substantive hypothesis, if pursued, should revisit existing ownership or placement decisions under blocked contact obligations; another scalar cost adjustment or larger cap would leave the observed limitation largely intact. That would need its own pre-code specification and test of added reach, runtime and sparse quality. No such follow-on algorithm is implemented by this note.

Reproduce the saved-data screen into a new output directory:

```sh
.venv/codex-native/bin/python -B results/codex/track-b003-analysis/analyze.py results/codex/retrieved/hyde02/track-b-bounded-003 results/codex/track-b003-analysis/analysis002
```

Full rows, pairs and retained failures are in `results/codex/track-b003-analysis/analysis001`; `mechanism_summary.json` contains the bounded counter comparison with B002. Source, tests and frozen run are unchanged after outcomes.
