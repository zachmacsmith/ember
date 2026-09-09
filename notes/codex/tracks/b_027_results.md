# B027: exact recurrence removes the observed C4 quality cycle

The bounded comparison supports replacing B026's repeated quality computation with exact recurrence termination. It establishes a computation saving on this fixed cycle, **not better construction reach or fresh-input quality**. B026 source and its original four outcomes remain unchanged; no panel call has run.

The isolated [B027 source](/Users/dabh/ember/packages/ember-qc/src/ember_qc/algorithms/factored/recurrence_mobile_tree_construction.py) adds only two recurrence helpers, completed-quality-boundary hooks, and method/receipt fields. Removing those additions reproduces the frozen B026 source byte-for-byte. Full canonical state tuples—not reporting digests—decide recurrence. Keys include chains, shared witnesses, cached trees, ownership, Q and O. Key creation/comparison and private seen-table copying are charged; an interrupted key cannot publish a recurrence decision or change the incumbent.

Four focused groups passed: equal-Q but different chain/witness/cache states remain distinct; an exact repeat matches; interruptions during construction/private storage retain the old state/table; and the inherited-source projection is exact. Then exactly four seed0/5s full calls ran under the same passive visit wrapper. That wrapper copies each completed state inside the common deadline, with no observation cap. Independent original-edge validation accepted all four outputs, and the dependency guard observed no forbidden imports.

| Case / method | Valid Q | Stop | Completed visits | Work | Caller wall |
|---|---:|---|---:|---:|---:|
| Triangle→C4, B027 | 4 | Exact recurrence | 9 | 1,682 | 0.001992s |
| Triangle→C4, B026 | 4 | Search deadline | 34,792 | 5,613,088 | 4.750074s |
| P3→P5, B027 | 3 | Singleton lower bound | 3 | 308 | 0.000500s |
| P3→P5, B026 | 3 | Singleton lower bound | 3 | 308 | 0.000431s |

On C4, quality boundary2 exactly equals boundary0: period2, two distinct keys, three comparisons. All **nine completed visits through recurrence** agree with B026 in actor, decision and full state including frozen prices; the control prefix was not censored. B027 made four neutral quality changes and no Q improvement. Recurrence work was297 units and0.000107s. Both methods found Q4 during initialization, so the new result does not demonstrate overlap resolution. The path control's three complete visits also match exactly, and its existing ACL1 exit requires no recurrence check.

Passive copy time was0.000073s for B027/C4 and0.233117s for B026/C4, fully included in their caller times and never subtracted. Gzip trace encoding followed each constructor call and is separately recorded; it is not solver time. The original uninstrumented B026 result remains a separate observation. These tiny timings are neither an MM comparison nor a general speed claim.

The recurrence argument applies to the unchanged deterministic quality transition under nonbinding deadlines. Additional key overhead could censor another input earlier, and distinct-state history may consume memory; both remain visible costs. Repeated exact state excludes later Q improvement on this same trajectory because every quality commit is Q-nonincreasing. It says nothing about better roots, alternative neighborhoods or globally optimal embeddings. The result resolves the identified neutral-cycle waste without adding patience, a work cap or a changed move. Root review precedes the fresh complete screen.

[Full summary](/Users/dabh/ember/results/codex/track-b027-recurrence/gates001/summary.json), [exact source comparison](/Users/dabh/ember/results/codex/track-b027-recurrence/gates001/source_comparison.json), [invocation](/Users/dabh/ember/results/codex/track-b027-recurrence/gates001-invocation.json), and [manifest](/Users/dabh/ember/results/codex/track-b027-recurrence/manifest.json) retain every call, trace, cost and source identity. All authorized calls completed without an analysis or test failure; no source/policy adjustment followed the observations.
