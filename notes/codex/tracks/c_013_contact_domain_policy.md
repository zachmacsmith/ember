# C013: reversible construction using contact domains

**Before-code decision contract; no implementation or calls authorized.** [C012](c_012_transfer_results.md) failed before its deadline on 17/22 encodings and inflated grid birth Q even without carrying. Test one coherent replacement: full-target placement guided by remaining contact opportunities, with joint reconsideration of the placements defining an obstructed contact. There is one evolving partial embedding. No expired strips, fixed owner roots, closed-owner immobility, independent constructor outputs, MM, busclique, global IP or exhaustive source-assignment solver.

**Hypothesis.** Avoiding the destruction of short future contacts, then moving their obstructing owners together when needed, can improve both completion and Q across local, community and hub inputs. C012's results motivate this hypothesis; they do not separate geometric exclusion from insufficient coordinated movement.

## State, order and placement

Maintain introduced vertices I, disjoint nonempty connected chains realizing **every original edge induced by I**, and exact original-contact counts. Other original edges remain pending. A single seeded RNG shuffles source and target ranks once; no later random draws. Original adjacency determines every choice; source labels, family metadata and evaluator maps supply no features.

For pending vertex v, let E(v) be the intersection of actual target-neighbor sets of its introduced neighbor chains; an empty intersection of constraints means all target sites. Its **singleton domain** is D(v)=E(v)∩Free. Domains are bitsets updated from actual occupancy/contact changes. Empty D(v) permits a multi-site chain and is never an infeasibility declaration. Choose the next vertex by `(has no introduced neighbor, |D(v)|, −introduced degree, −source degree, source rank)`, with the domain-size field set to zero when there is no introduced neighbor. Recompute after each private or public placement.

For a proposed state S, with pending set P, use this lexicographic score:

```text
Z = number of pending vertices with empty singleton domains
score(S) = (Q + |P| + Z, Z,
            −fsum(log1p(|D(w)|) for w in pending source-rank order),
            sum of occupied sites' distance to the Zephyr center,
            chains listed by source rank, with sites listed by target rank)
```

The first term is a **conditional lower bound when all currently placed chains are frozen**: each pending vertex needs at least one new site, and an empty singleton domain requires at least two. Retraction invalidates that bound. Here it is a comparative heuristic, never a global admissibility or optimality certificate. Z and logarithmic domain sizes break ties without an adjustable domain-loss coefficient. The geometric tie uses `(x,y)=(w,2z+j)` for Zephyr orientation 0 and `(2z+j,w)` for orientation 1, with distance `|x−m|+|y−m|`. Reuse audited coordinate parsing/checks; coordinates prioritize, while supplied edges alone certify couplers.

`PLACE(v,S)` considers every singleton in D(v) when D(v) is nonempty. Otherwise find the free target components touching all required neighbor chains. No such component means no extension for this v with the other chains fixed. Pick the required neighbor with the smallest free boundary, breaking ties by source rank; roots are all its free boundary sites in those qualifying components. With no required neighbors, roots are all free sites. For each root, build one shared tree: multi-source BFS from the current tree through free sites to the nearest uncovered neighbor contact; tie by neighbor rank, terminal target rank, then target-rank BFS traversal. Each extension immediately covers all incidental original contacts. Repeatedly remove the first target-ranked construction-tree leaf whose removal preserves a nonempty tree and every required contact; the birth root receives no protection. Score the resulting state and retain the smallest score. This enumerates roots and one greedy tree per root, not combinations of complete embeddings. Evaluate singleton roots by target rank and branch roots by decreasing direct contacts, center distance, then target rank. All scans are charged.

## One coordinated transaction

```text
v := next pending vertex; ordinary := PLACE(v, current state)
If ordinary exists and destroys no previously nonempty pending domain:
    publish ordinary.
Otherwise:
    If ordinary exists, let w be its newly empty-domain vertex with
        smallest old domain, then source rank.
        K := introduced neighbors of v or w, plus old owners occupying E(w)
             in the ordinary proposed state.
    If ordinary does not exist:
        K := introduced neighbors of v, plus old owners occupying E(v).

    Privately retract all K from the ORIGINAL entry state.
    Place v first, then reintroduce K using the same dynamic order and PLACE.
    Do not invoke nested retraction during this rebuild.
    If the full rebuild succeeds, compare it with ordinary at the identical
        introduced set I ∪ {v}; publish its smaller score (ordinary on a tie).
        If ordinary is absent, publish the rebuild.
    If the rebuild fails at x, find an occupancy-relaxed contact tree for x
        through free sites and outside owners I\K; current rebuilt owners
        and v remain blocked. Add every outside owner used by that tree to K
        and retry from the ORIGINAL entry state.
    If no such tree exists or no outside owner can be added:
        discard the rebuild; publish ordinary if available, otherwise fail.
```

The occupancy-relaxed guide uses the same singleton/root/greedy-tree construction on its expanded passable set. Replace BFS by Dijkstra with lexicographic path cost `(new outside-owned sites, new sites)`; already accumulated tree sites cost zero. Select the generated guide tree by `(outside-owned sites, total sites, center distance, ranked sites)`. A guide may overlap outside chains and is **never a candidate embedding**. Its only output to construction is the set of outside owners to retract. They may be closed owners. A zero-owner guide following an exhaustive ordinary-placement failure is an accounting inconsistency to report as ERROR, not an instruction to loop. The guide is a greedy obstruction explanation, not a minimum conflict-set proof.

Rebuilding privately preserves all outside chains exactly and re-establishes every original contact at each successful addition. Publication requires the complete rebuilt induced source, disjoint connectivity and consistent contact counts. Partial rebuilds, prefixes and guide trees never publish. K grows strictly after each retry, so at most |I| outside owners can be added; a successful publication introduces exactly one new vertex. These are finite set/progress properties, **not tunable repair limits**. A feasible rebuild that loses the score comparison ends this transaction; larger groups are sought only to resolve failed construction. Retaining ordinary after a failed or inferior transaction is selection between operators on one state, not a portfolio of complete algorithms.

## Deadline, observations and decision

Use the common absolute deadline `D=min(call_start+timeout, supplied_deadline)` and the existing finalization reserve `min(.5 s, timeout/10)`. Initialization, domains, sorting, all roots, copying, failed rebuilds, guides and certification consume that budget. Check before and after bulk operations and inside graph loops. No work, root, group-size, local-time or retry denial counter is active. On interruption discard the unfinished transaction and preserve the published state. A fully certified complete private proposal already obtained before the search cutoff may go directly to the existing final original-edge gate even if its root scan was censored; label that scan partial and make no best-root claim. Late output and exceptions receive no embedding credit. A partial source receives FAILURE, never a finite ACL.

Record initial/final maps; publication Q; domain counts and newly lost/recovered domains; generated/completed/censored roots; ordinary versus rebuild scores and choice; K membership and reason for every expansion; guide occupancy; private failure location; stage wall/CPU and all unsuccessful work. New owner choices or rerouting may change a conditional bound, so compare final proposal scores at the same introduced set. Published-set size rules out repeated complete construction states; repeated private geometry can still waste work while K expands and should be counted, not suppressed by an unexplained patience cap.

**Self-critique.** Domains describe singleton opportunities, not simultaneous feasibility, and can poorly predict good branched embeddings. Singleton-first generation excludes proactive larger trees while a singleton remains available. Broad contact dependencies can force a large rebuild; rebuilding greedily can recreate the same obstruction even after moving roots. All-root scoring and guide Dijkstra may dominate time. The coupled redesign deliberately changes representation, placement and coordinated movement together; novelty and benefit remain unproved. It must earn further work through complete constructors.

Focused checks cover only new risks: bitset domains versus direct adjacency, including an empty domain with a feasible multi-site extension; root/leaf/contact correctness; score and domain-loss reconciliation; retraction of a closed owner and strict outside-owner expansion; private failure/interruption rollback and fatal/late noncredit. Reuse the original-edge oracle. One hand control is target path 0–1–2–3 with an introduced isolated owner at 1 and introduced b at 3, pending edges b–v–w: ordinary v at 2 destroys w's domain, and a joint move of the closed isolate permits Q4. Keep supplied-state checks separate from complete-constructor evidence.

After those checks pass, move directly to root's frozen small complete screen: fresh local, community and hub sources at two sizes, plus hidden singleton controls; paired same-host A061/MM, all failures/times retained. Freeze exact input IDs and allowance before any call; candidates never receive witnesses. The cheap continuation requirement is **lower complete Q than A061 on two fresh inputs from different families, at least one also no worse than timely MM, and no lost A061 control success**. Failure rejects this fixed policy; improved domains or successful private retractions alone cannot pass. Completed extensions outside former strips would support the representation change; recovery requiring K expansion supports coordinated movement. Useful generated rebuilds losing the score comparison implicate acceptance; domain/guide cost censoring otherwise useful construction implicates computation. These observations guide bounded follow-up rather than proving isolated causality. Any regression blocks promotion; the unchanged class-level objective and untouched confirmation remain required.

## Root review clarification before code

Root authorized isolated implementation and the focused checks on 2026-09-09. Newly lost pending domains exclude the just-placed vertex. Final chain/site comparison keys contain seeded rank integers, never raw source or target labels. A previously certified full-source private proposal may pass the existing final original-edge gate after search interruption, with its incomplete root scan explicit; unfinished proposals and late results receive no credit. The zero-owner-guide ERROR requires a completed exhaustive PLACE failure, never a censored scan.

The actual proposed Transfer002 screen has **nine keys**: g0001, g0005, g0008, g0004, g0012, g0017, g0013, g0101, g0102. These are reused ER80, SBM80, BA160, WS80, planar160, singleton-control80 and grid128, plus newly generated ER100 and BA100. This binding supersedes the broad size description above: it is not two sizes of every family. The continuation criterion can count independently generated Transfer001 development structures as well as the two new structures, with exposure reported separately. The new isolated API is `zephyr_contact_domain.contact_domain_embed`, proposed descriptor `contact-domain`, config `{}`. No shared harness change, panel call or remote call is authorized before root's implementation/check review.
