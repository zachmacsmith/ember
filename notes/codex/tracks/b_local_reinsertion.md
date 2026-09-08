# Track B004: local removal and reinsertion during construction

2026-09-08. Hypothesis saved before implementation. B003 completes seven of nine development inputs but loses all seven timely MM comparisons. K40 blocks at 32 inserted vertices before its work limit. All retained partial chains are valid and retain an extension site, so that invariant does not solve placement conflicts. B003 can extend old chains but does not freely relocate their existing qubits.

Keep one evolving B003 construction state. A local repair releases at most two old chains together with the new vertex, and rebuilds them through the same connected-tree insertion primitive. Outside chains are frozen during this query. The released logical vertices are reinserted in a fixed order; no alternate constructor, restart, embedding library, family rule or output portfolio is involved.

```text
For next vertex v in the unchanged construction order:
    compute ordinary private insertion P from current partial minor E
    if P fails, or Q(P)-Q(E) > connected_degree_bound(v):
        select at most two old chains as one connected neighborhood of v
        privately release them from E; insert v first
        reinsert removed vertices by most already present neighbors, degree, seeded rank
        freeze every outside chain throughout this query
        if every insertion completes, independently validate the resulting partial minor
        use repair only if P failed or repair has strictly smaller Q than P
    atomically commit a complete insertion of exactly E's vertices plus v
    if neither insertion completed, preserve E and report failure
```

The degree bound is max(1, ceil((degree(v)-2)/(Delta-2))) for target maximum degree Delta>2; use 1 otherwise. It is a necessary final chain-size bound, not a bound on extra sites forced into other chains. Its use here is only a general expensive-insertion trigger.

Select the first removed vertex from v's already placed logical neighbors, preferring larger chains, then larger remaining-demand/free-boundary ratio, then seeded rank. The second comes from placed logical neighbors of v or logical/physical neighbors of the first removed chain, with the same ranking. Deduplicate and exclude v. This connects the selected block in the graph of logical and existing physical contacts; it does not enumerate all useful blockers. Zero-excess chains remain eligible because their position can obstruct another insertion. If no old neighbor exists, no repair is attempted.

Use the unchanged total limit of 20 million adjacency scans and common 60-second deadline. A local query has at most one million additional scans, and all local queries together at most five million, charged inside the same global limit. Query setup, failed reconstructions and final validity scans count toward these bounds; bitset operations and Python administration remain charged to the absolute deadline, not falsely represented as adjacency scans. Local exhaustion discards the private repair and retains the provisional ordinary result, if present. Deadline/global exhaustion preserves the last committed valid prefix and never produces a late success. A complete repair finishing exactly at its local scan cap may publish after its final timely check; no extra scan is granted. These fixed bounds are hypotheses, not tuned per graph.

To freeze outside chains, urgent preparation may not extend them; if required to protect their remaining frontier, the private query fails. A path to a frozen neighbor assigns all new path sites to the inserted chain. Local pruning is restricted to the newly inserted and already reinserted selected chains. Thus a completed block changes at most its three selected chains. Source coverage, disjointness, connectedness, every contact among currently inserted vertices, and the extension-frontier invariant must all hold at commit. Outside lists/sets must compare equal to entry. Removing chains preserves the induced partial minor, but restoration of all their old obligations must be checked before publication.

Self-critique: rip-up and reroute is conventional and close to established minor-embedding local repair; this is a construction hypothesis, not a novelty claim. A greedy v-first reconstruction can consume the only site required to reinsert a removed chain even when the block has a feasible assignment. The selected neighborhood can miss a remote blocker or require more than two removals. Equal-Q reorganizations are rejected when ordinary insertion works, so beneficial longer trajectories may be missed. Repair can spend its allowance early and displace later ordinary search; additional reach does not imply lower final ACL. Freezing outside chains intentionally prevents the broader existing-chain growth available to ordinary insertion. No feasibility or approximation guarantee is claimed.

Before the unchanged nine-input screen, require one tiny original-graph witness in which ordinary insertion fails or has higher Q and this exact release/reinsert operation succeeds with outside unchanged. Independently validate its complete minor and exercise local work/deadline interruption and rollback. If that cheap witness fails under the declared selection/order, stop and document it rather than launching merely to test larger caps. If it passes, freeze seed 0, the same nine source/target bytes, and fresh candidate/MM pairs on hyde02. Falsifier: no added completed inputs or lower Q on the panel, or gains outweighed by failures/work displacement. Preserve every regression and late comparator. A positive toy witness proves only that local mechanism's reach.


## Implemented mechanism and targeted checks

New standalone module `packages/ember-qc/src/ember_qc/algorithms/factored/frontier_reinsertion_construction.py`, SHA-256 `f29cdef92e5e0d6ce51594c7a13dfe2b234c3dfa15e25e4b5b0022d92c5f678d`. It copies the B003 primitive and adds the declared optional frozen-outside argument and one bounded repair query. It never imports or invokes B003. The accepted repair counter is updated only after the main commit's final deadline check; returned complete proposals are separately recorded and may be rejected on Q.

The tiny witness uses source edges (0,2),(1,2),(3,4),(3,5), target edges (0,2),(2,4),(0,1),(4,5),(2,6),(2,8),(6,7),(3,7),(3,8), and partial chains 0:[0],1:[4],3:[2,6],4:[7],5:[8]. Source vertex 2 is pending. Ordinary insertion fails. The fixed selector removes logical vertices [1,3]; reinsertion returns 0:[0],1:[4],2:[2],3:[3],4:[7],5:[8]. All original logical contacts validate, outside chains are unchanged, and six source vertices now use six sites. Neither site of the old chain 3 can individually be deleted while preserving its original contacts. This witness takes 150 repair scans. It establishes the declared move's reach on one supplied valid partial minor, not constructor reach on the benchmark or novelty.

Ten targeted guarded checks pass in `results/codex/track-b004-checks/attempt002`: the witness, local-cap rollback, exact-last-unit completion, deadline rollback, frozen urgent-growth rejection, small complete constructors, metadata/order controls and inherited path/frontier checks. Attempt001 is preserved: two tests passed set-valued chains into the reused validator, which expects indexable chain lists. Only the fixtures were corrected to sorted lists; candidate source was unchanged. Test source SHA-256 `00f1cba17396c2997bed9e3bd1f1fbd7f665b3b4dd12dd4fa23a716817529501`.

Reproduce targeted checks in a new additive directory:

```sh
.venv/codex-native/bin/python -B results/codex/track-b004-checks/run_checks.py results/codex/track-b004-checks/repeat001
```


## Frozen paired screen

`results/codex/track-b-reinsert-004` contains the unchanged nine development graph bytes and ideal-Z12 target bytes, seed 0, 60-second common deadline, 18 fresh candidate/MM tasks on hyde02. Pilot method `frontier-tree-reinsert` has empty configuration and loads only the exact standalone source file. Manifest SHA-256 `e485d8a3ddae44d020f5548275d4821d18eb12a3c690c7473a6ec7b44ed42d04`; source snapshot `fcda1fc047d21f02f36017120dd07ae1cbd992c6c4c21dc7cd53dd24e08e2973`; pilot `375b686eab25298b8bfabbf41e44cc4c37d056541938c743c58023d1c6a4e6b3`. Pre-outcome checks are in `results/codex/track-b004-checks/freeze.json`.

Remote input digest is `d1ef4ce6324ccb592a708e4c67a2b369b6945d1d55f035f218fc3d91aa35acb9`. A sandbox DNS failure before staging is retained as `stage-attempt001.json`; retrying the same immutable stage succeeded before any experiment invocation. Detached launch occurred once at epoch 1788890131.5118525, with session `ember-codex-60d260ef2cc823032725` and the existing 1,920-second outer supervisor. No restart is performed after connection loss.


## Results and decision

The controller finished all 18 records at epoch 1788890392.7755227; the supervisor exited 0 and the lock/session were inactive before retrieval. Archive `results/codex/retrieved/hyde02/track-b-reinsert-004` has digest `3b7f4e472c56913781c584f6dc4c206a38f3a4327f86bd24d24fccec86fe1e09` and 167 verified files. The reused saved-data validator confirms all seven candidate successes and both retained partial minors on the supplied original graphs. No prohibited embedding imports were recorded. No new solver calls occur in analysis.

| Input | B003 Q | B004 Q / ACL | Fresh MM Q / ACL | B004 seconds | MM seconds |
|---|---:|---:|---:|---:|---:|
| complete 40 | failure | failure | 194 / 4.850 | 27.379 | 8.164 |
| complete 100 | failure | failure | 1052 / 10.520, **late** | 28.406 | 64.855 |
| bipartite 30+30 | 330 | 223 / 3.717 | 180 / 3.000 | 20.080 | 4.190 |
| ER 80, degree 8 | 298 | 312 / 3.900 | 211 / 2.638 | 23.903 | 4.622 |
| regular 80, degree 3 | 114 | 114 / 1.425 | 90 / 1.125 | 18.511 | 0.809 |
| Watts–Strogatz 80 | 112 | 111 / 1.388 | 94 / 1.175 | 9.933 | 1.201 |
| grid 8×8 | 73 | 77 / 1.203 | 70 / 1.094 | 3.367 | 0.549 |
| honeycomb 5×5 | 83 | 82 / 1.171 | 71 / 1.014 | 7.033 | 0.371 |
| king 8×8 | 108 | 113 / 1.766 | 90 / 1.406 | 13.533 | 1.721 |

B004 completes the same seven inputs as B003. All seven timely comparisons still lose to MM; the late K100 comparator receives no timely credit. Against B003, there are three improvements, one tie and three regressions. Summed Q decreases by 86, dominated by the 107-qubit bipartite reduction; ER, grid and king instead add 14, 4 and 5 qubits. This is one seed on nine exposed development inputs and does not estimate family performance or ACL variance.

There are 116 repair queries: 100 complete private proposals, 13 local work-limit stops, and three blocked reconstructions. Twenty proposals commit, including one on each subsequently failed complete-graph construction. All 37,765,876 recorded repair scans across the nine separate calls reconcile exactly with their query records. Every query stays within one million scans; every call stays within five million repair scans and twenty million total scans. Six inputs consume the entire repair allowance. Query administration and bitset work are included in wall time, so those scan counts are not a total operation count.

The negative cost evidence is substantial. Regular accepts no repair but spends its full five million scans, raising total scans from 2,612,530 to 7,612,530 with unchanged output Q. Its contemporary candidate/MM time ratio is 22.87; honeycomb's is 18.94 for a one-qubit improvement over B003. Other successful pair ratios range from 4.79 to 8.27. Candidate CPU/wall ratios are 0.99965–0.99991 while host load is approximately 33–34 on 32 logical CPUs. These are host-specific paired observations; cross-run B003/B004 wall differences also include uncontrolled host effects. No portable speed advantage is claimed.

K40 advances to 35 placed vertices, then blocks at 19,645,953 scans. K100 reaches only 32 before the global work limit, versus B003's 35. Both retained partials validate and preserve the one-free-port condition. Their five-million repair allowances have already been exhausted, so the final failures do not prove that a fresh repair query could not help. Conversely, larger allowances would consume further ordinary work and are not justified by this screen. The full failed records remain available.

The cheap witness was informative: the operator truly expands the available moves. The corpus screen shows the limit of that evidence. The same fixed local repair substantially improves one trajectory, yet local strict-Q choices produce worse final Q on three other inputs, and many completed proposals cost work without committing. Current records do not retain a separate ordinary-proposal Q baseline for each rejected query, so they do not estimate unrealized per-query savings; final outputs and commit counts are authoritative.

Do not promote this fixed schedule or select B003/B004 by input. Reject the present expensive-insertion scheduling policy as a broadly competitive constructor. Retain the lesson that relocatable ownership can materially improve an embedding, together with the failure of immediate-Q acceptance and exhaustive use of the auxiliary allowance to predict final benefit. A further construction revision should require a substantively different placement/feasibility hypothesis rather than another allowance or ranking adjustment. No next variant or extra run is launched here.

Reproduce the two small saved-data checks in a new directory:

```sh
.venv/codex-native/bin/python -B results/codex/track-b004-analysis/analyze.py results/codex/retrieved/hyde02/track-b-reinsert-004 results/codex/track-b004-analysis/analysis002
.venv/codex-native/bin/python -B results/codex/track-b004-analysis/summarize_repairs.py results/codex/track-b004-analysis/analysis002
```

Full pairs, failures, raw diagnostics and the scan reconciliation are under `results/codex/track-b004-analysis/analysis001`. Source and settings are unchanged from their pre-outcome freeze.
