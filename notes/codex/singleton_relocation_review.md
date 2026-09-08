# Independent review of singleton relocation

Recommendation: proceed to the predeclared fixed 033 ablation after the independent
site oracle and final native/runner integration checks pass. I found no blocking
validity, cache, or charged-work defect in the core reviewed below. This is a
source review, not evidence of better final ACL or runtime. No algorithm code was
edited, no embedding benchmark was launched, and no external algorithm was used
for this review.

The review covers the stable implementation, its semantic tests, and the
[specification](singleton_relocation_spec.md), including the amendment allowing
the first scheduled extra visit to initialize the cache. Native and pilot
integration are separately owned and are not certified by this core review.

| Reviewed file | SHA256 |
| --- | --- |
| `factored/singleton_relocation.py` | `bd3b6f7b32490c00a3843dd400c4998a96dd0f4fef5a02cebe06d8a94f90b424` |
| `factored/contact_repair.py` | `804edfaaf9cdefe33249ffea9db1d752cd79c0e0b8a2a0d2bcd9478e0c483c57` |
| `notes/codex/singleton_relocation_spec.md` | `76dfc2e7d3ae831152194b47802afe22d304d02e3ff8e402939bcdd70279a852` |
| `tests/algorithms/test_singleton_relocation.py` | `ec022ec1ae28a172a81e04f79a13e3d6e3404bd3a5d1217057d9e226e94bb7e4` |

## Validity and objective

`contact_polish(singleton_policy='direct')` explicitly rejects directed graphs,
multigraphs, and self loops for both source and target, then validates the whole
incumbent with `_Context.valid`. That validator checks exact source keys, nonempty
chains, target membership, duplicate/disjoint occupancy, connectivity, and all
logical edges. The lower-level proposer and cache functions rely on this caller
contract; they are not independent public validators.

For a selected source vertex `v`, the proposer permits only a free target vertex
or one currently owned by `v`. It checks that the target vertex has a physical
neighbor owned by every logical neighbor of `v`. Replacing only `C[v]` with this
singleton therefore preserves disjointness, connectivity, and every required
edge. Freed vertices from the old chain do not affect other chains' connectivity.
The argument relies on the exact current owner map, not the cache's volume
heuristic or the old reconstruction region.

The score counts actual target couplers to required logical-neighbor chains,
subtracting `degree_G(v)` once. Because the other chains remain fixed, the change
equals the global logical-edge redundancy change. Long-chain shortening may lose
redundancy and still strictly improve the declared lexicographic objective.
An equal-size singleton move requires strictly greater redundancy. Nonlogical
contacts and contacts to the removed chain itself are excluded. The degree bound
and all-singleton-neighbor shortcut are sound for the enforced simple graphs.
The admissible upper bound `Delta - degree_G(v)` permits early termination; it
does not require the old long chain's redundancy to lie below that bound.

Every feasible singleton lies on the boundary of the chosen logical-neighbor
chain. An untruncated enumeration consequently covers the feasible sites, except
when an exact shortcut or the maximum possible score has already resolved the
choice. First-discovery ties are retained. Budget truncation can miss feasible or
better sites, but a returned site has already passed its complete contact check.
The isolated-vertex case chooses the lowest-ranked old vertex and is also valid.

## Cache validity

The cache is local to one polishing call and records the incumbent mapping's
object identity. The context's source and target adjacencies are frozen for that
call. The integration creates a new mapping for accepted proposals and does not
mutate old chain lists; thus identity is an adequate version token on this path.
Identity alone would not detect an external caller mutating a chain in place.
The internal functions should retain their documented immutable-incumbent
contract; they are not safe general-purpose caches for arbitrary external edits.

Refresh marks the cache invalid before changes, removes all selected old owners,
and only then inserts selected new owners. This ordering correctly handles a
qubit transferred between two selected chains. Unselected ownership and volume
remain unchanged. Selected volumes and sorted physical chain order are rebuilt,
and the new mapping identity is installed only after complete maintenance.

Failed or interrupted setup produces no reusable cache. Failed maintenance
discards it and disables direct search for the rest of the call, while retaining
the already accepted valid embedding. The next visit cannot use partial owner
state. Accepted ordinary group reconstructions take the same refresh path as
accepted singleton moves. There is no cross-call cache or source-identity lookup.

## Work limits and deadlines

Every auxiliary `pop` first charges the active `_Budget` and then exactly one of
setup, refresh, queue, or scan work. The active visit starts with the smaller of
remaining global work and the original group allowance. Ordinary `_repair` gets
only the remaining visit allowance, and its reported expansions are added once.
The final visit total is then added once to global expansions. These relations
also hold for an extra slot that fails to find an eligible queued vertex.

The auxiliary allowance `max_expansions // 20` and extra-slot limit
`max_groups // 16` persist across passes. Setup and refresh share the auxiliary,
group, global, and deadline limits; they do not borrow from another visit.
Queue inspection plus proposal scanning share the extra visit's 256 scan units.
An accepted reconstruction can exhaust the group allowance and force cache
discard with zero further maintenance work. Exhausting only the 256 scan units
does not stop the whole call or restore those units for reconstruction.

The direct path checks the common deadline again before committing a certified
site. A failed or late direct proposal on a longer old chain still reaches the
old `_repair` path with its remaining allowance and original deadline. That
existing path and its cooperative timeout behavior are unchanged. Context setup,
full validation, group generation, sorting, dictionary copying, and processing
one target adjacency are not hard real-time operations. Reported elapsed time
and overrun remain necessary; charged work is not a wall-time guarantee.

## Scheduling coverage and remaining risks

The ordinary group order is retained within each generated pass. One extra slot
can follow each block of 15 ordinary visits, or a nonempty partial block at pass
end. Actual extra visits count against the original group cap. Empty/skipped
slots consume their charged work and slot allowance without claiming a group
reconstruction. No extra sweep runs when the ordinary group list is empty.

The amended rule allows an extra slot to build the cache even when all ordinary
singleton chains exceed the target degree bound. This fixes the specified hub
counterexample while retaining the same limits. It can also spend setup work
and discover an empty queue, which is correctly visible as unused extra capacity.

The queue reflects the embedding **when the lazy cache is built**, which may be
after earlier ordinary moves; it does not necessarily describe call-entry state.
No later vertices are appended. Each queued vertex is consumed at most once and
its eligibility is checked again. Therefore newly useful singleton moves can be
missed, and an unsuccessful pass can stop while queued opportunities remain.
This is the specified bounded heuristic, not exhaustive coordinate descent.

The main empirical risks are setup/refresh cost, loss of ordinary group coverage,
and locally useful redundancy moves occupying sites needed later. More accepted
moves or greater redundancy need not improve final qubits. `ordinary_groups_displaced`
counts the unvisited suffix of the current generated list at the shared group
cap; it is not the number of improvements a control run would have made.
Unchanged group generation or proposal code does not imply identical direct-arm
trajectories after its incumbent or budget changes.

## Verification evidence and scope

I compared source against pre-edit commit
`6d5168a72df4c287f147a0a2f2ec89a40859500a`. The entire implementation preceding
`contact_polish` and the complete legacy traversal body are byte-identical.
The default policy does not import/build the new search or add its diagnostics.
The new path retains ordinary longer-chain reconstruction when a singleton
proposal fails, including degree-ineligible chains. It does not guarantee that
the same reconstruction succeeds after auxiliary work spends part of its budget.

I read the focused tests, including independent whole-embedding and coupler
checks, owner transfers, partial refresh, stale identity, a three-to-two fallback,
deadline rollback, exact caps, the high-degree-only lazy-setup witness, and a
frozen non-time legacy regression. The implementing agent reports 35 focused
tests passing on the hashes above, after the final diagnostic split. I did not
repeat those tests or run benchmarks in this review. Root's separately owned
exhaustive-site oracle and final integration checks remain additional evidence
before experiment 033.

The implementation uses source adjacency, target adjacency, and one current
embedding. The new module imports only `dataclasses`; its caller uses existing
local reconstruction. No MM, busclique, optimizer, graph-family lookup, restart,
or independent-output selection is introduced. Common-boundary enumeration and
local relocation are conventional mechanisms; this review establishes no
novelty or MM superiority. Preserve every regression in the fixed full-pipeline
comparison rather than selecting a proposal policy by input.
