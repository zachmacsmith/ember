# C014 early-failure reconstruction review

2026-09-09. **The three terminal private prefixes are recoverable without replaying the constructor.** This is a bounded source and saved-field review, not a diagnostic result. No constructor, passive reader, validator, routing query, exact solver, MM embedding or witness was executed or inspected. C014 remains rejected.

Reviewed C014 source SHA256 `3b452c6167707bb8a351aa34028fd821586d4f7f253504bd81489ace593a2a64`, C013 support `113d5b006abf5a87010b477d8107bb7460fcabdfe0954f2832356180c0377786`, and [existing passive details](../../../results/codex/c014-transfer-analysis/attempt001/output/details.json), SHA256 `7ee260db7d969e03b429b149144aa2e7cd5b4330e9199adbdba643c8082eabc7`. Only the three early-failure candidate terminal records were additionally read from `results/codex/retrieved/hyde03/track-c-capacity-contact-014/results/`.

## What is actually saved

C013 `_State.score()` stores a fifth component containing **every introduced chain**, encoded as `(source_rank, sorted_target_ranks)`. C014 `_place()` saves this complete score whenever its best proposal changes. An exhaustive successful call returns exactly that proposal; `_transaction()` assigns it to the private state before the next birth. Thus the successful placement immediately preceding each terminal failed birth gives that birth's exact entry map, even though the failed call itself has `best_score = null`.

| Input | Terminal candidate task | Previous / failed placement indices, zero based | Private owners / Q | Failed source index | Roots completed | Old owners whose quotas reject the contact trees |
|---|---|---:|---:|---:|---:|---|
| g0001 | c1ecf8e24384155c3a0ba652 | 117 / 118 | 20 / 34 | 58 | 1 | 49 |
| g0101 | 7f6245adcb67310b0c602e3f | 198 / 199 | 16 / 20 | 38 | 12 | 28, 61, 93 |
| g0102 | 62740391de10d01061809627 | 51 / 52 | 10 / 16 | 92 | 12 | 73 |

The preceding scores have respectively 20, 16 and 10 chain records, and their `Q_after` equals the failed call's `Q_before`. The records contain source rank dictionaries of size 80, 100 and 100 and target rank dictionaries of size 4,800. These are **index-to-rank** mappings; inversion recovers internal indices. Root receipts already use internal indices and must not be rank-decoded again. Frozen `graph_from_record()` inserts nodes in saved node-list order, and `_graph()` enumerates that order: index-to-solver-label conversion therefore uses the frozen source/target `nodes` lists.

All 25 failed root receipts have status `old_capacity_violated_by_contact_tree`, with saved `contact_sites`, identical `attempted_sites`, capacity pairs and explicit deficit owners. None reaches the growth loop. g0001's rejected proposal is a singleton; the other two have routed contact trees. This further localizes these particular failures: changing capacity-growth tie breaking cannot alter their immediate rejection.

The passive projection omits the rank dictionaries, individual root chains and full published maps. The raw candidate records retain them. Accordingly, the existing reader's blanket limitation “Historical chain maps are unsaved” is too broad: completed selected placement states are saved losslessly in scores. Preserve the frozen reader and its verdict; this note supplies the narrower interpretation. Unrecorded rejected growth-trial states, intermediate BFS queues, and counterfactual search trajectories remain unavailable. No independent geometric reconstruction check was performed in this review.

## Proposed cheap diagnostic, before code

**Hypothesis.** Hard quota rejection of these particular greedy trees does not necessarily require relaxing capacity. A quota-safe alternative tree or a different previously available private placement may avoid the conflict. The competing explanation is that the fixed prefix leaves no quota-admissible contact route, requiring coordinated movement or temporary capacity debt. Merely expanding the outside movable set cannot address the recorded internal blockers.

For a reconstructed prefix with free sites F and next owner x, define the old owner's consumption allowance

`b(u) = |N(chain(u)) intersect F| - |G(u) minus (I union {x})|`.

A proposed new chain S must consume at most `b(u)` distinct free boundary sites of each fixed old owner. The original-source adjacency to x is already accounted for in this formula; using the pre-birth remaining count would reject legal contacts. Also check x's own remaining capacity after insertion.

**Pseudocode.**

```text
For each of the three frozen terminal failures:
    Decode the preceding successful best_score[4] using saved inverse ranks.
    Check membership/Q continuity and transaction/reintroduction chronology.
    Independently validate the induced partial minor using the existing oracle.
    Recompute capacities; check every saved rejected contact tree and deficit.

    Delete from F every boundary site belonging to an old owner with b(u) = 0.
    Find connected components of the remaining target graph.
    If no component touches every required neighbor chain of x:
        record a fixed-prefix hard-quota infeasibility certificate.
    Otherwise:
        record that this necessary test is inconclusive.

    For each saved capacity-safe root proposal of the immediately previous birth:
        substitute its saved final_sites into the prefix, keeping other chains fixed;
        combine it with each saved failed contact tree for x;
        independently check disjointness, connectivity, original contacts and ALL quotas.
        record every valid witness and every rejection; do not choose a constructor output.

    For unresolved cases only, allow one <=5-second contact-routing probe
    on the fixed prefix with zero-allowance sites excluded.
    Use existing contact-tree support as a diagnostic helper, followed by all-quota
    checks and independent validation; no whole-constructor call or quota relaxation.
```

**Distinguishing observations.** A different tree valid under unchanged chains and quotas identifies the connected-tree neighborhood as insufficient. A saved alternative prior placement plus a saved contact tree that passes all checks demonstrates a limitation of irreversible greedy placement selection, without changing either quota policy or the recorded tree generators. A zero-allowance component cut proves that *no* connected insertion can obey the old quotas with that prefix fixed; the already saved contact trees show that contact-only insertion remains possible. This last result implicates hard enforcement **conditional on fixed earlier placements**, not capacity reservation in every possible embedding. It motivates coordinated movement, not an automatic decision to abandon capacity. Failed bounded probes without a cut certificate remain inconclusive.

**Cost scope.** Exactly three prefixes and their 25 failed root receipts; no graph generation, complete constructor or MM call. The immediately previous births have 8, 1 and 10 saved safe proposals, yielding at most **140 recorded proposal pairs**, including duplicates and controls. Exhausting this finite saved set answers a specific choice question; it is not a new algorithmic root cap. Component checks cover ideal Z12 once per prefix. Optional routing is at most 15 solver seconds total, with cold imports, input parsing, validation, all failures and censoring reported separately. Reading the three terminal JSON files covers 172,982,512 bytes; avoid copying or reserializing their full receipts. No exact solve is needed initially; a later bounded neighborhood solve would require its own explicit region, question and accounting.

**Self-critique and falsifier.** These exposed prefixes can diagnose a mechanism, not establish graph-class performance. The last-birth alternatives may miss the relevant earlier decision; g0101 has only one safe proposal at that birth. A component cut is sufficient for fixed-prefix infeasibility, while component survival does not establish capacity feasibility because positive consumption budgets and x's own capacity still matter. If all three have certified cuts and no recorded replacement witness, the cheap evidence rejects the claim that rerouting x alone fixes these stops; a routing-only refinement should stop. Conversely, one quota-safe witness disproves necessity of weakening quotas for that prefix, but cannot revive C014. Any mechanism retained from this diagnosis must promptly enter a small complete-constructor screen on diverse development instances and retain all existing failures.

## Staging authorized before implementation

Root authorized preparation of the exact prefix reconstruction, unchanged-oracle partial validation, capacity/allowance checks, component certificates and all 140 saved proposal combinations. Implement these in a separate stdlib-only diagnostic with isolated candidate-only inputs. Add focused checks for rank inversion, allowance/cut semantics and preservation of changed-owner contacts. Freeze the script, checks, oracle and input hashes for root review **before running the three development cases**. Input extraction and tiny synthetic correctness checks are authorized; the development diagnostic is not yet authorized. Defer all new routing and exact-solver implementation or execution until the cheap stages reveal an unresolved question. No C014 refinement or policy revival follows from this authorization.
