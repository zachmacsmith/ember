# C017 diagnostic proposal: alternatives inside the private conflict set

2026-09-10 UTC. **Plan only: no implementation, solver installation, model construction or execution.** C016 remains rejected. This is a bounded diagnostic of its three completed zero-root obstructions, not a new constructor or revival of that policy. Root will review the contract before any implementation.

## Hypothesis and distinguishing evidence

The central assumption is that reconsidering the failing owner together with its already reintroduced quota blockers can admit that owner under the existing hard quotas, without increasing any participating owner's reference chain-length bound. A valid alternative would expose a missing joint neighborhood in C016. Conversely, exact infeasibility in that explicitly limited neighborhood would disprove this assumption there. It would not prove global embedding infeasibility or invalidate all capacity-based construction.

Compare the same finite connected-chain model with and without the quota inequalities. This distinguishes a missing search neighborhood from exclusions caused by enforcing fixed-chain capacity at every private step. If neither model resolves within its allowance, the instrument's computational cost remains the explanation for absent evidence. A quota-free partial minor is not evidence that its fixed chains permit completion; future movement may be necessary.

## Fixed inputs and smallest changed owner set

Use only the three C016 terminal-private states already independently validated by the existing reader. Let `I` be the saved private introduced set, `x` its failed source owner, and `B` the recorded terminal quota blockers. Every member of `B` is already reintroduced inside the transaction's movable set. Release exactly `B`, add `x`, and fix **every other private chain**, including other owners in that movable set. The final induced source is `I ∪ {x}`. This local net-one result need not complete the interrupted outer reconstruction, much less the full source graph.

| Development input | Failed internal owner x | Blockers B | Per-owner chain-length upper bounds |
|---|---:|---|---|
| g0001 ER80 | 48 | {77} | x: 6; blocker: 3 |
| g0101 ER100 | 87 | {79, 93} | x: 7; blockers: 2, 2 |
| g0102 BA100 | 39 | {43, 75} | x: 3; blockers: 2, 2 |

These identifiers select offline diagnostic records only; they are not production decisions. Each blocker's bound is its actual terminal-private length. Each `x` bound is its length in the last published state before the failed transaction, where it already existed. Only that scalar length defines the domain; no old chain is restored, supplied as a solver start or used as a template. The bounds ask whether changing positions and contacts within already observed lengths is enough. They define the tested neighborhood, **not a claimed global optimum or a production work cap**. Their total local limits are 9, 11 and 7 sites. No radius, preferred hardware patch or top-K domain is introduced.

The physical available set is every currently free Z12 site plus all released `B` sites. For each changed owner, candidates are all nonempty connected subsets of this set within its length bound and touching every fixed outside source-neighbor chain. Sound distance pruning is allowed: each candidate site must lie within `L−1` available-graph steps of every required outside contact boundary. This condition is necessary for a connected chain of at most `L` sites; it cannot remove an eligible chain. Owners without outside contacts retain the whole available domain. Internal source contacts and disjointness among changed chains remain exact constraints.

## One bounded exact instrument

Use a local mixed-integer feasibility model for these **two or three changed owners only**, with site-ownership variables, connectedness flow constraints, pairwise disjointness, required source contacts and the stated length bounds. It is neither a global embedding model nor the constructor proposed for production. Select one open-source solver and pin its version and all relevant settings in implementation preparation before execution; do not mix solvers or choose among their answers.

Hard-quota mode requires, for every introduced owner in `I ∪ {x}`,

```text
number of distinct finally free physical sites adjacent to its chain
    >= number of its source neighbors outside I ∪ {x}
```

Outside chains have fixed boundaries; changed chains need exact boundary-union indicators. Count sites once even when several chain sites touch them, and exclude every finally occupied site. Quota-relaxed mode removes only these inequalities. It retains exactly the same owner set, available-site domains, length bounds, connectivity, disjointness and source-contact constraints. No route heuristic or different ranking is substituted between modes. Feasibility, rather than minimum Q, is the model's objective.

```text
verify frozen private state, source/target order and recorded blockers
S := B ∪ {x}; freeze chains of I \ B
derive identical length-bounded physical domains for the two modes
build exact connected-chain feasibility model on S
if hard-quota mode: include all final capacity inequalities
solve until a feasible assignment, proven infeasibility or global deadline
if feasible:
    extract the full induced partial minor with frozen outside chains
    validate independently; recount every quota and changed-owner membership
save model status, certificate/witness, bounds, timing and censoring
```

Freeze six diagnostic workers: three states × two modes, each with **60 seconds total cold worker time**, including imports, domain/model construction, solve, validation and output. This uses the existing complete-call allowance to determine whether even a tiny exact instrument is affordable; it is not a constructor promotion threshold. A solver receives only the remaining allowance, with the existing small final-output reserve. Use the existing detached runner and outer supervision, one pinned diagnostic environment on a spare host, with the two modes for each state on the same host. Randomize and freeze their order before results. Do not impose extra node, root, solution-count or iteration limits; record any unavoidable engine limit. Threads and all solver settings must be fixed and logged. No worker restart, automatic budget increase or larger owner/length domain follows from censoring or failure.

Record model/domain sizes, preprocessing/model/solve/validation wall and CPU, process wall, solver termination reason and every failed or interrupted attempt. A time or resource limit is `UNKNOWN`, never infeasibility. A feasible solver assignment earns evidence only after independent original-oracle validation on the induced partial source and direct quota recount. Quota-relaxed witnesses must report every violation. Save the complete model and solver result for claimed infeasibility; an ambiguous engine status is insufficient. Neither mode supplies any future candidate's initialization, and their outputs are never combined into an embedding portfolio.

Before these six workers, add only checks specific to the new exact model: hand-enumerable connected/disjoint two- and three-owner fixtures, distinct-site quota counting, and hard-quota/relaxed monotonicity. Reuse the original oracle and dependency guard. No MM/busclique imports or outputs, witness embeddings, source-family rules or global exact solve are permitted.

## Frozen interpretation and next decision

| Hard-quota result | Quota-relaxed result | Permitted conclusion |
|---|---|---|
| Independently valid feasible witness | Any consistent result | A useful alternative exists under current quotas within the tested neighborhood; C016 missed it. |
| Proven infeasible | Valid feasible witness with quota violation | Quota enforcement excludes every alternative in this fixed owner/length neighborhood, although a valid partial minor exists there. This is a local constraint explanation, not global quota infeasibility. |
| Proven infeasible | Proven infeasible | This owner/length neighborhood does not repair the obstruction. Stop this primitive; do not automatically enlarge it. |
| Unknown | Feasible or unknown | Hard-quota feasibility is unresolved; do not blame quotas from the relaxed witness alone. |
| Unknown or infeasible | Unknown | Missing evidence is censored; report measured instrument cost and stop the packet. |

A hard-quota witness paired with a proved quota-relaxed infeasibility is a model/result inconsistency that rejects the instrument. No intermediate objective bound or number of explored states substitutes for a resolved outcome.

Positive local evidence warrants constructor work only if the same explanation appears in both an ER input and BA100. The relevant future mechanism is **conflict-directed local reembedding of already introduced owners**, with one evolving state. It must use a practical heuristic rather than invoking this exact model globally. A coherent design can apply the same local operator to a blocked birth and to shortening existing chains, rank admissible local changes by their total occupied-site cost, and revisit contact placements after the first complete embedding. This connects completion repair to C016's unresolved quality deficit. The diagnostic alone does not establish that such a heuristic will find the witness quickly or improve ACL.

After one before-code design and focused risk check, such a mechanism should move directly to a small complete-constructor screen with retained A061/MM, diverse source structures, a fresh size and a source relabeling. Its exact panel and allocation require a new freeze. It must retain success and improve final quality; local repair success or additional published owners cannot justify another repair sequence. If only quota-relaxed alternatives exist, a constructor would additionally need an explicit rule for revising earlier capacity reservations and resolving resulting deficits. That is a substantive redesign requiring separate critique, not permission to silently drop quotas from C016. No constructor implementation or diagnostic series is authorized by this contract.

Self-critique: two or three changed owners may be insufficient; the length bounds may exclude a useful temporary expansion; and local feasibility may merely move the next conflict to another owner. Exact modeling across the available hardware can still consume the entire allowance. The two-mode comparison separates quota exclusion only within its fixed domains, and neither valid partial witness establishes end-to-end quality or generalization. These limits are reasons to preserve negative or censored results and make one bounded decision, rather than repeatedly broadening the diagnostic until it succeeds.

Inputs derive from [C016 causal output](../../../results/codex/c016-constructor/causal001/output.json), SHA256 `689f2122f047dddc1b24f324250c9e378e6d32fa84a8d2f0603b8a57148bf583`, and the same frozen raw candidate records already bound by the original audit/reader. The [C016 rejection](c_016_results.md) and [causal decision](c_016_causal_decision.md) remain unchanged. Exact input, source, model and environment hashes must be frozen separately if implementation is approved.
