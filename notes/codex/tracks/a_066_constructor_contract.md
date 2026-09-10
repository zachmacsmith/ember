# A066 proposal: exact obstruction pruning with coordinated singleton replacement

2026-09-10. **Before implementation; root approved the isolated implementation and focused checks.**
This is one evolving A061-initialized A065 construction state, not independent
complete algorithms or output selection. The new operator uses source adjacency,
chain membership and actual Zephyr couplers only. The existing constructor,
compiled ranking, reconstruction and validation remain the defaults elsewhere.

**Hypothesis.** A two-site focus with no removable donors sometimes has no
one-site embedding against its fixed neighbors. Ranking and reconstructing
thousands of roots cannot improve that query. At the same point, replacing an
adjacent (two-site, singleton) pair by two singletons can open contacts and save
one qubit. Exact obstruction detection and a coordinated replacement jointly
address computational waste and the demonstrated contact-mobility limitation.
The [six-map diagnostic](a_066_pair_diagnostic_results.md) found neutral-first
witnesses on grid/WS and joint-release-only witnesses on grid; four other input
structures were negative and remain explicit limitations.

**Integration correction.** A065 does not currently close a two-site owner at
its preparation bound. `1 + retained >= old_local` closes only a singleton with
zero donor savings. Add the exact obstruction test immediately after the existing
preparation and before compiled root ranking; do not wait for root exhaustion
or the global deadline.

```text
prepare focus u using the unchanged donor trees and contact witnesses
if |C(u)|=2 and no donor site was removed:
    D = free sites contacting every retained neighbor chain
    if D is empty:
        for singleton source neighbor v in the existing seeded neighbor order:
            release u and v privately; keep all outside chains fixed
            intersect available sites with each owner's outside contact boundaries
            find the first physical edge p--q between those domains
                in deterministic order derived from the existing target tie ranks
            if found:
                propose C(u)={p}, C(v)={q}; all other chains unchanged
                certify the complete minor, rebuild its ownership/contact bundle
                verify exact Q−1 and publish atomically before the existing deadline
                invalidate all cached queries and closed-owner marks as on an A065 commit
                advance to the next owner slot in the existing round
                return
        close u for this epoch: its original strict-Q query is provably impossible
        return
continue unchanged A065 preparation/ranking/reconstruction and admission
```

The preparation already produces free sites and a per-site set of contacted
retained neighbors; complete contact coverage gives the direct singleton domain.
The proof also uses the old reconstruction contract: `reconstruct` reads the
prepared donor map, grows and trims only the new focus tree, and returns only
that tree. `_Search.commit` then installs every prepared donor chain unchanged.
With zero removed sites, verify that each prepared donor site set equals its
current site set; failure is an error, never permission to prune. Therefore
`Q_after = Q_before - 2 + |new_focus|`. Strict improvement requires exactly one
focus site, and the prepared free/contact map is its exact feasibility domain.
The implementation must retain this assertion next to the pruning condition.
This argument concerns the unchanged query, even if donor list order differs.
An isolated owner always has a nonempty singleton domain and must not be closed
because its boundary dictionary is empty. When donors are unchanged, an empty
intersection is a proof for that query, not a heuristic score. Any better focus
would need one site. Pair domains must be recomputed against current chains and
include the two released owners' sites while excluding every outside occupied
site. No cached diagnostic witnesses or source labels enter production.

Publish both chains together even when a valid neutral intermediate exists.
There is no neutral walk, temporary public overlap, uphill acceptance or global
IP. All available couplers are eligible until the first certified strict
improvement; there is no top-k, pair-count or root cap. The first-improvement
order is a general scheduling choice, not a claim that the first witness is best.
An interrupted search stays unknown and leaves the last certified map intact.

**Scheduling, accounting and new correctness risks.** Keep the A065 owner order,
one-root visits for unaffected queries, and global epoch invalidation. A pair
publication can occur during query preparation, before an ordinary query cache
exists. Its receipt must therefore explicitly identify the pair operator rather
than pretend that compiled ranking occurred. Reuse the existing certificate and
bundle routines and the existing atomic-publication sequence, in an isolated new
module; do not mutate imported globals or shared A064/A065 code. All preexisting
cached owners are invalidated after any pair move, including queries whose owner
was not moved, because free space changed. Exact-negative closure is invalidated
by the same epoch transition. Preserve round/slot progression and the complete
changed-chain receipt. Certificate, bundle, receipt preparation and deadline
check must complete before publication; interruption at any earlier point cannot
change the incumbent. Keep original donor-trimming counters distinct from the
new donor-relocation count.

Use the unchanged full-call deadline and A065 final reserve
`min(1 second, 0.05 * timeout)`. Charge domain construction, searches, compilation,
validation, discarded work, output and failures. Record attempts, exhausted
obstructions, examined pair/coupler counts, successful pair moves, invalidated
queries and phase times as observations. No counter terminates search.

Focused checks before screening: compare the integrated domain operator to the
already checked exact primitive on nontrivially relabeled tiny graphs; exercise
successful pair publication with populated caches and prior closed owners;
interrupt domain search, certificate, bundle/receipt preparation and immediately
before publication, checking unchanged entry or complete valid admission; verify
empty-neighbor handling and the pruning-only ablation. Reuse the existing oracle
and guard. No fresh exhaustive routing infrastructure is needed.

**Cheap complete-constructor falsifier.** Propose nine development encodings:
the original six diagnostic inputs, the paired grid relabel g0021, BA100 g0102,
and fresh planar100 g0203. Freeze their actual manifest before execution. Run
A066, an otherwise identical exact-pruning-only ablation, unchanged A065, retained
A061 and pinned MM separately, seed 0 and 60 seconds, on one cluster host: 45 cold
calls. The ablation disables only the coordinated pair search after the exact
obstruction proof; it still closes that provably futile query. No outputs are
combined. Preserve every failure, Q regression, within-chain variance change and
time ratio by input; classify relabels separately from independent structures.
These are development inputs; across-seed effects and untouched confirmation
remain unmeasured.

If pair moves occur but A066 never improves final Q over pruning alone, the local
witnesses have not justified this integration: stop the fixed mechanism. If
pruning alone saves time or creates gains while pair moves do not, retain that
causal distinction. Further constructor work requires preserved success, no
hidden Q regression, and final Q gains attributable to the pair operator on at
least two distinct structures. Relabel/new-input results must be shown even if
negative. A failure or regression rejects the frozen policy; any bounded
follow-up needs a specific explanation supported by these completed results.
This is continuation evidence, not promotion or proof of the class-level goal.
There is no unexplained universal timing-ratio gate.

**Self-critique.** The measured witnesses save only one qubit and may compete for
sites; they cannot be added arithmetically. Changing contacts can destroy later
A065 improvements despite strict local admission. The no-donor, length-two
restriction leaves most ER/control deficits untouched. Exact pruning may help
more than the coordinated move, which is why the ablation matters. Atomic pair
publication introduces a correctness risk before a cache exists; explicit
interruption/invalidation checks are necessary. The mechanism is a principled
local heuristic, not yet a novelty claim or a promising complete constructor.
