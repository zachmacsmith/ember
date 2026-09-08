This specifies the smallest diagnostic adapter for the unchanged ordinary contact proposer. It is a read-only design review, not implementation, a selected corpus protocol, or a pipeline change. No proposer, constructor, corpus input or remote process was executed. Root separately chooses the immutable input set, group-selection rule and numerical allowances described in the [ownership diagnostic design](ownership_exchange_diagnostic_design.md).

Use one immutable, independently valid entry embedding E, the exact original source/target and one frozen finite ordered group list L for both methods. The ordinary arm should construct one `_Context`, validate E once, and call unchanged `_repair(E, ctx, group, ...)` on successive groups. Stop at the first **timely returned, independently valid strict-Q contraction**. Never feed a returned proposal into another group. Exchange already provides these shared-entry batch semantics through `ownership_exchange(E, source_adj, target_adj, L, budget=..., deadline=...)`. No independent arm outputs are combined into an embedding algorithm.

**Why these APIs.** Public [`repair_group`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:519) constructs `_Context` and validates the whole entry for every call. Repeating that wrapper across L would artificially repeat setup that [`contact_polish`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:671) normally shares. Conversely, calling `contact_polish` would generate groups from an evolving incumbent and accept equal-Q rearrangements, answering a different question. The proposed adapter removes only repeated wrapper setup; it does not replace the reconstruction search.

[`_Context`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:32) stores source order, target rank, sorted original adjacency, original source edges, maximum target degree and the individual-chain degree lower bound. These records are read-only during `_repair` and can be reused across all groups of one arm. Retain `_ordered` exactly: it sorts by `(type name, repr(label))`, so integer 10 precedes integer 2. Changing it to numeric order would change ordinary search choices. Preserve the source graph's edge iteration order and every entry chain's list order. Exchange's own numeric normalization stays unchanged; a shared input does not require making the algorithms' internal traversals identical.

**Valid input contract and fixed options.** The diagnostic preflight requires stable simple undirected loopless source/target graphs with ordinary integer labels, nonempty list chains, exact source coverage including isolates and a finite ordinary list/tuple of groups. Each group has 1–4 distinct known source vertices. Duplicate group *occurrences* are preserved in order; duplicates *within* a group are rejected rather than silently removed by the public wrapper's `dict.fromkeys`. Groups of size 5–8 would require a separately declared unsupported-control comparison; do not quietly call private `_repair` beyond its public supported group domain. Neither an ownership-ineligible disconnected/oversized patch nor a zero-excess group may be removed retrospectively from the shared list.

For comparison with the existing ordinary control, pass every effective reconstruction option explicitly:

| Option | Existing control value | Preserve because |
|---|---:|---|
| `beam_width` | 1 | The public wrapper default is 4; using that default would change the control. |
| `alternatives` | 3 | Includes the existing old-choice retention, root-attempt order and duplicate handling. |
| `halo` | 2 | Retains the existing region BFS. |
| `max_region` | 512 | Do not replace this with exchange's 64 occupied-site cap. The two methods have different move domains. |
| per-group `max_expansions` | `min(50000, ordinary_work_remaining)` | Exactly the existing per-group cap and global remainder rule. |
| `max_orders` | 2 | Preserve supplied order, reverse order and existing bounded order enumeration. |
| `boundary_sites` | 16 | Retain free boundary-site augmentation and its charged scans. |
| `objective` | `qubits_contacts` | Equal-Q local alternatives remain part of the unchanged ordinary search. |
| `tree_policy` | `greedy` | No distance-tree, singleton, star or endpoint-support substitution. |

These values follow the [frozen 042 control configuration](../../results/codex/042-final-deletion-pipeline/source/scripts/codex/pilot.py:286), [native forwarding](../../packages/ember-qc/src/ember_qc/algorithms/factored/native.py:348) and [contact defaults](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:606). The historical total ordinary cap is 500,000 routing expansions; root must bind the diagnostic's total cap explicitly. Changing a numerical allowance for a declared diagnostic is possible, but is not an exact replay of that historical cap. Pass count, evolving scheduling and the historical 512-group ceiling are not secretly inherited: the caller's frozen finite list defines the diagnostic group occurrences. No second pass or list regeneration is allowed.

Keep `_parameters` and objective/tree-policy checks once per batch. Validate each reached group against the stated contract, preserving occurrence order and recording malformed input as an error. A preflight may validate the whole immutable ledger for both arms, but an unvisited suffix remains *uninspected by the proposer*. No candidate-dependent look-ahead or lazy generator is allowed. An empty list can return `NO_GROUPS` without context construction; record that setup and entry validation were not performed by that arm.

**Proposed control flow, with no production changes.**

```text
start arm wall/CPU clocks; receive one fixed absolute deadline D
check fixed scalar options; retain immutable E and L
if L is empty: return NO_GROUPS
build ctx = _Context(original_source, original_target)
check ctx.valid(E); invalid entry is an error, not a failed search
Q_entry = actual total chain lengths in E
spent = 0
for each reached group occurrence g in the frozen order:
    stop if deadline reached or ordinary total allowance exhausted
    validate g without reordering it
    result, raw = unchanged _repair(
        E, ctx, g, explicit_options,
        max_expansions=min(50000, total_allowance-spent), deadline=D)
    spent += raw.expansions
    retain the whole raw record and this occurrence's measured wall/CPU
    if result is a strict-Q contraction of E:
        independently verify full result and unchanged chains outside g
        materialize the complete private output; apply final deadline gate
        if valid and timely: return this one candidate
        if invalid: stop with audit/internal error
        if late: retain diagnostic result; return no credited candidate
    otherwise retain unchanged/equal-Q output as diagnostics; keep E
return no candidate with the exact stopping reason and uninspected suffix
```

The group-local `_repair` keeps a `best` and can improve it more than once while searching that group. Its region and each complete trial are still formed from E; the best affects size bounds and comparison. Preserve that behavior. Do not interrupt the function at its first internal update, restart after equal-Q output, switch to `objective='qubits'`, or scan all group outputs and select the minimum. The adapter's endpoint is the **first group call that returns a qualifying contraction**, not the earliest internal discovery. Ordinary can save more than one qubit in that returned proposal; exchange returns exactly Q−1. Report both saved Q and group/seed location without truncating ordinary output to a one-qubit change. Sources: [`_repair` entry/best](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:324), [proposal enumeration](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:397), [legacy validation/update](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:465).

An equal-Q ordinary return may have `accepted=1` and positive contact redundancy. That is an internal proposer diagnostic, not a contraction and not an accepted diagnostic state transition. Preserve it, then call the next group on the original E. All Q deltas are measured against E. Ordinary output outside g aliases E's lists, whereas exchange returns private lists throughout. The diagnostic must never mutate either result; its common output materialization makes all returned lists private and charges that cost. Input/adjacency/context value hashes before and after the arm provide a mutation check, not a substitute for structural validation.

**Shared setup and fair accounting.** Common artifact parsing, exact source/target validation, saved-entry provenance and frozen group-list construction may be prepared once and reported as evaluator preparation. Both arms receive equivalent value-identical inputs. Keep method-specific setup inside each arm's measured wall and original deadline: ordinary `_Context` construction and entry validation once; exchange's charged entry copy, owner map and certificate once. Do not use an ordinary context to bypass exchange setup, or vice versa. `_Context` scans the whole target; exchange checks the occupied portion. That real cost difference must remain visible.

Do not cache ordinary regions, owner maps, contact scores, `_alternatives` or beam choices between group calls. Their present scans and validation calls are part of the unchanged proposer. All failed groups, equal-Q outputs and unsuccessful root attempts consume their actual existing work. Sum `raw.expansions` across groups and enforce the global remainder; preserve every individual raw diagnostic. [`_Budget`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py:79) counts popped region/routing vertices and boundary scans, not every adjacency examination or validation operation. Exchange counts elementary records, copies and comparisons as well. Equal numeric caps are **not equal work**. Separate finite caps and common wall allowances must be fixed from the accepted small-fixture cost evidence before any corpus observations.

Preserve ordinary `accepted`, `qubits_saved`, `member_growth`, `expansions`, `region_size`, `tree_attempts`, `beam_expansions`, `beam_pruned`, `unreachable_contacts`, `complete_proposals`, `orders_tried`, `boundary_sites_added`, `boundary_expansions`, `equal_size_moves`, `contact_redundancy_gain`, `tree_search`, `stopped_by`, `wall` and any deadline fields. `region_size` is per group; use its maximum for a summary, not a summed region size. Raw `_repair.wall` excludes shared context/entry setup, unlike public `repair_group.wall`; label the distinction explicitly. A sum of raw accepted moves or saved-Q fields across uncommitted groups is not cumulative embedding improvement. Save separate `returned_contraction`, `credited_contraction`, `groups_called`, `uninspected_groups`, total routing work, setup/entry-validation/publication costs and arm wall/CPU. Nested stage measurements must not be added twice.

**Deadlines and independent checking.** Each arm gets the same declared duration from its own start, and one absolute D carried across setup, all groups and final output handling. Never grant a new wall allowance per group or let the second arm inherit the first arm's remaining time. Pair order/host isolation belong to root's overall protocol. Record raw proposer return time separately from complete diagnostic acceptance time. Include the same independent result gate and output-copy overhead in each arm's final credited deadline; report that common diagnostic overhead separately from method-specific cost.

The legacy ordinary branch performs `ctx.valid(trial)` without an interruptible deadline check inside it and may return an earlier or newly found valid improvement after D. Even `stopped_by='deadline'` does not establish when its retained best was discovered. Preserve the raw return, but credit no contraction that is first available after D or whose final gate crosses D. A later saved-data audit must validate original source keys including isolates, every target membership and edge, nonempty connected disjoint chains, actual Q and the method's outside-chain constraint. Exchange's claimed complete certificate is also checked independently; rejected/late certificate evidence is not a returned candidate. No watchdog grace earns proposal work. Cooperative unmetered ordinary scans require an external process backstop, with interrupted/missing outputs retained rather than retried.

**Self-critique and required implementation checks.** This adapter compares restricted proposal reach from a deliberately fixed state, not evolving contact-polish effectiveness or full-pipeline speed. Sharing setup avoids a needless ordinary disadvantage but does not make its routing counter comparable to exchange's meter. Ordinary's within-group completion can make its first-return latency longer than its first internal discovery; instrumenting that event would be a different reviewed diagnostic. An exchange-ineligible initial patch can still permit ordinary free-space contraction, while exchange may admit additional owners beyond the supplied group. Keep both facts in the report; do not force their domains to match retrospectively. Existing round-robin grouping omits zero-excess groups and prioritizes singleton opportunities; neither omission nor a failed search proves lack of contraction after donor admission. Root must fix the group rule independently of outcomes.

Before use, focused synthetic checks should compare the adapter's per-group `_repair` results with public `repair_group` on the same E and explicit options, excluding only documented wall fields. Cover an equal-Q group followed by a contraction while every call sees identical E; unchanged and duplicate group occurrences; exhausted global remainder; deadline crossing during final validity/materialization; invalid output injection; source/target/chain-order preservation; shared setup exactly once; and empty/malformed input. Use a separately implemented original-edge oracle. No new broad or corpus execution is authorized here.

Reviewed source identities: contact_repair.py `c6f9a5555b010d5e877b568c1ee760e72d170f1f7e0c186179de16b53630da85`; contact_groups.py `43574f6f13eb33d790de535e4e614533d0f1df7f50d129932301b7832e1301bd`; ownership_exchange.py `015781019833ee5a3f49dcec5a189161104003224b1327b44cedda6e084532bb`; accepted ownership specification `8d870c3a2e16615574ad018eec266258200bd7740b7cbd2450d47a47d299f82f`. Any source change requires a narrow review before adapting these private APIs.
