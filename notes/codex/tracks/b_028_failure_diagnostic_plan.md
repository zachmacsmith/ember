# B028: fixed-state failure diagnostic, before implementation

**For root review; no new diagnostic, routing or constructor calls have run.** B027/B028 remain rejected. This tests mechanisms, not a new constructor.

## Available state and missing information

Read-only inspection confirms that all four audited failures retain **complete connected chains, every valid original-edge witness, and prices** in `diag.final`. Recounted Q/O match. Graph/target bytes and seed0 are bound by the audit. Nonzero overlap prevents minor validity.

| Input | Final Q / O | Saved witnesses | Explicit prices / largest price | Pending owner / degree | Diagnostic owner / degree |
|---|---:|---:|---:|---:|---:|
| ER80 g0001 | 249 / 42 | 323 | 80 / 7 | 76 / 8 | 71 / 10 |
| Singleton80 g0017 | 189 / 77 | 488 | 29 / 7 | 37 / 19 | 41 / 16 |
| Fresh ER100 g0101 | 334 / 60 | 378 | 97 / 9 | 80 / 9 | 44 / 14 |
| Fresh BA100 g0102 | 248 / 19 | 291 | 97 / 6 | 75 / 30 | 10 / 12 |

Prices are unique integral target-site entries; unspecified prices default to 1. Owners derive from chains; ranks derive from sorted labels, seed and pinned shuffle. **Cached trees, full scheduling/history and interrupted Dijkstra arrays are missing.**

Load a **reconstructed fixed state**, without trajectory/recurrence/scheduler replay. Cached trees may be deterministic representatives: `proposal` only copies unaffected trees, while `trim` builds its own BFS tree. Neither routing nor local certification reads those caches. Freeze reconstructed inputs before querying; verify entry chains/witnesses/prices remain unchanged.

Use the saved pending owner and one owner selected by greatest overlap incidence, then longest chain, then source rank. Pending owners have zero incidence on ER80/BA100. All four failures are included; no MM state or hidden witness enters.

## Hypothesis and precisely bounded alternatives

**Hypothesis:** summing independent neighbor distances can rank completed shared trees poorly. Alternatives are a priced objective that prefers more reported overlap, or stored witnesses that prevent neighbor shortening. Cost remains unresolved after only zero to three feasibility sweeps and interrupted terminal proposals.

For one frozen owner query, remove its chain and perform the unchanged neighbor trim. Let k(q) be resulting occupancy and p(q) the saved price. The actual routing weight is

```text
w(q) = 1 + p(q) k(q)
J(r) = sum_v distance_v(r) - (degree(u)-1) w(r).
```

J discounts the root but can recount other shared segments. Its weight is the marginal increment of

```text
Phi(state) = Q(state) + sum_q p(q) occupancy(q)(occupancy(q)-1)/2.
```

Phi counts priced co-owner pairs; O sums `max(occupancy-1,0)`. With neighbor trims fixed, Phi changes by distinct-site weights plus the common removal/trim constant. Record **J and final Phi/Q/O** independently after attachment and trimming. Compare lexicographic `(Phi,O,Q,rank)` and `(O,Q,Phi,rank)` so price ties cannot fabricate a preference conflict.

Use two explicit proposal spaces for each congested owner:

1. **Current interfaces.** Retain finalized route dictionaries from one unchanged B028 proposal. R is the intersection of all neighbors' settled-distance keys. Substitute each r∈R, then use unchanged attachment, contact assignment, final trim and certification. Verify original-root substitution reproduces the original proposal. This enumerates one finite root/parent-map space; early stopping may omit roots. Report `|R|/4800`; do not claim all-path search.
2. **One contact retargeted.** Enumerate alternative physical couplers already joining saved chains on edges (v,w), with v neighboring u and w≠u. Change one witness, keeping chains/other witnesses/prices fixed. Recompute affected neighbor trims, deduplicate identical results, and select minimum residual O, then Q, then canonical ranks. Run the same route/root enumeration once for that variant. If none differs, record this and skip its query. This probes one chosen witness change, not combinations.

The second space moves **contact endpoints within existing chains**, adding no neighbor sites or movable owners. No IP/exact solver is needed. Negative findings cannot establish wider-neighborhood impossibility.

## Pseudocode and accounting

```text
for each of the four frozen failed candidate states, in a fresh native worker:
    restore chains, witnesses, prices and deterministic ranks; verify structure
    complete the pending-owner proposal privately; record Q/O/Phi and charged cost
    restore the same entry state
    select the congested owner by the fixed rule above
    for current interfaces and the one declared contact-retarget variant:
        run the unchanged proposal once, capturing the completed route dictionaries
        verify original-root substitution reproduces its complete proposal
        enumerate remaining complete roots by (J, target rank), without publication
        record every complete proposal's J/Phi/Q/O and certification outcome
        preserve interruption, unvisited roots and all costs
    return observations only; never an embedding selected for a benchmark arm
```

At most **12 genuine joint-root queries**, plus counted private proposal reconstructions; zero constructor calls. Use isolated native hyde02, the pinned B028 code and existing dependency guard. Root reviews code/input bundle before execution; candidate and shared harness remain unchanged.

Allocate **60 s measured wall per state**, charging import/JIT/copying/reconstruction/validation/output under existing supervision. Evidence: the six-query packet cost 14.887 s cold; its full 36-neighbor query cost 1.300 s compiled/6.950 s Python; complete-screen compiling dispatches reached 9.940 s plus import/allocation. Here degrees≤30, but root-enumeration cost remains unmeasured. No root-count cap applies. Deadline censoring means unresolved, not mechanism rejection; changed allocations require a subsequent experiment. Report cold total and disjoint costs without excluded warmups.

The original oracle rejects overlap immediately. Keep it unchanged; add one diagnostic-only check using its graph/traversal logic to verify connected chains, actual source contacts and Q/O/Phi with overlap permitted. Reuse the oracle when O=0. Focused checks cover this allowance, map immutability, original-root equivalence, price arithmetic and witness retargeting. Preserve all failures/unprocessed work without quality credit. Root reviews the new checker before launch.

## Observations that decide the mechanism

- **Sum-distance surrogate mismatch:** a completed same-interface proposal has lower actual Phi than the selected-root proposal despite higher J (or equal J with an unfavorable rank tie). This is a concrete counterexample in the declared pool; cheaper actual shared trees were available to the same attachment procedure.
- **Priced objective versus reported overlap:** a lower-O proposal exists, but minimizing actual Phi over the same completed pool prefers higher O. Preserve Q and price tradeoffs; this proves a local preference conflict, not that greedily minimizing O will construct good minors.
- **Stored-interface limitation:** after complete enumeration, the retargeted pool contains a lower-O proposal than every current-interface proposal. This demonstrates an added contact-endpoint capability within these pools; it does not prove that unrestricted current-interface trees lack an equally good solution.
- **Terminal cost censoring:** completing the pending-owner proposal yields useful O reduction from the saved terminal state. This establishes a missed local counterfactual at that state, not that extending the full run would succeed. If original-root reproduction or structural checks fail, stop interpretation and classify a reconstruction/correctness problem.

Feasibility acceptance admits every complete proposal, so rejection of generated proposals does not explain these failures. Whether accepting overlap increases helps requires separate trajectory evidence.

**Cheap falsifier/self-critique.** If selected roots minimize Phi and O/Q in every fully enumerated pool and retargeting adds nothing, stop this reranking/retargeting hypothesis. One owner, early-stopped root fields, one witness probe and failure-selected states limit negative conclusions and generalization. Extra root evaluations may cost too much. Positive counterexamples must recur across structures with acceptable cost before informing a separately screened constructor. Nothing here promotes B028 or removes regressions.

Authority: [B028 completed result note](b_028_constructor_results.md), archive digest `fa4fc35a0734ff329cddc97ba4b8da33ad989fb1b595f2f6130051b984d30e7b`; wrapper `16ec9260a0971acd81a79cb4d8577fbbaf34653d784f6d21ddd488ab724775fe`, kernel `c729ccd815262ec9ebf18eaa24f33544719c53ca610ecd7d823fbc63456564c8`. No MM implementation or output was required for this plan.
