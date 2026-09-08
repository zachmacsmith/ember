# C007: atomic versus elementary growth on the fixed C8 panel

**Frozen comparison proposal, prepared before panel outcomes.** Use all eight previously exposed C inputs, unchanged ideal Z12, seed 0 and fifteen seconds for each of three independent arms: `atomic-regions`, the exact `variable-regions` elementary control, and fresh stock `mm`. This is 24 full-constructor calls on hyde04, with one sequential worker at a time. The elementary control's failed tiny growth gate remains reported. No candidate reads another arm's embedding or resumes a supplied partial state.

| Graph ID | Development family | n | m |
|---|---|---:|---:|
| 2030 | path | 141 | 140 |
| 5058 | tree | 121 | 120 |
| 1584 | grid | 128 | 232 |
| 31536 | planar | 152 | 450 |
| 6450 | Erdős–Rényi | 133 | 870 |
| 14334 | regular | 140 | 2800 |
| 1041 | complete | 127 | 8001 |
| 30736 | stochastic block | 120 | 625 |

The graph order is the table order. For each graph, the existing pilot shuffles `['mm','variable-regions','atomic-regions']` using `Random(f'{graph}:0')`; the prepared plan records the resulting order. Configurations are `{}` for each method. MM keeps its stock `find_embedding` settings except seed/timeout. Native and MM use their separate prepared hyde04 environments. Include graph-copy/construction/cleanup work in solver time; report process startup/import time separately. Do not pool historical timings or the tiny gate timings.

**Hypothesis and decisions.** Atomic growth should preserve the singleton representation's low initial Q while making preparatory contact routes available as complete proposals. Compare valid coverage on all eight inputs first, then Q/ACL only on timely valid pairs; retain failures and late-valid diagnostics separately. Optimal ACL1 ties count as acceptable outcomes. Reject the fixed candidate if it loses a C006 sparse success, or obtains neither a new harder completion nor lower Q on at least three of the four previous sparse successes (C006 Q313/207/367/457). This historical Q rule is a development decision, not a timing comparison. Also report the contemporaneous elementary/atomic/MM table without merging methods or selecting a winner per graph.

Save initial/final Q and missing contacts, visit/eligibility counts, selected ΔE and acceptance outcomes, atomic route lengths/failures, distance/BFS work, stage costs and stop reasons. For candidate pairs, compare actual initial state and prefix through the first differing addition; later different state/RNG trajectories are a limitation. Many no-free-path visits implicate access/neighborhood, uphill rejections implicate acceptance, growth undone by deletions implicates scheduling interaction, and deadline-dominated work implicates cost. These observations guide the next hypothesis without proving a unique cause.

Root owns registry, source freeze, transport and remote lifecycle. Before launch, require standalone registration, unchanged tested source hashes, passive retention of `diagnostic_embedding` in the pilot, exact original-label/source/target inputs, and 24 new task identities. Every finalized output must pass the original-graph oracle; incomplete assignments may be valid only for their realized-contact subgraph. The prepared ledger keeps missing families, including Sudoku, outside this eight-input scope. This is development data, one instance and one solver seed per family; no family means, solver variance or generalization claim follows.
