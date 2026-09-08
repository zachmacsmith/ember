# 049: reduce a source core, then expand one embedding

Specified before implementation, 2026-09-08. Root reviewed the design and
approved a bounded prototype and the targeted falsifiers below. No corpus
experiment is frozen or launched by this note.

**Hypothesis.** Eliminating vertices of current degree at most three may remove much of the geometric construction cost on sparse sources. One embedding of the surviving filled core can then be expanded by connected-chain insertion. This could address 047's sparse quality/runtime deficits more substantially than another refinement-budget change. It is a heuristic construction order, not a guaranteed minor-lifting theorem or a novelty claim.

## One coherent graph state

Keep the original source immutable. Seed-shuffle its sorted canonical integer IDs once to obtain a fixed tie rank. In each connected component retain the vertex of greatest **original** degree, resolving ties by that rank. Never eliminate this anchor. Repeatedly eliminate an eligible non-anchor in increasing `(current_degree, tie_rank)` order. Record `(v, S, F)`: its at-most-three surviving neighbors, and **only the previously absent neighbor pairs actually added** as clique fill. Existing edges never enter `F`.

After reduction, construct requirement adjacency `R` from the remaining core edges and the union of all journal edges `(v,s)` for `s in S`. Keep all original vertices in `R`, including those not yet placed. For current placed vertices `P`, `R[P]` is the exact required graph at that expansion stage. Unplaced neighbors in `R` are pending demands; they can include synthetic edges that must exist at an intermediate stage, not merely original edges.

Before reverse-inserting `(v,S,F)`, make a private trial requirement state by deleting exactly `F`. Insert `v` against that state. Commit the edge deletions and chain changes together only after validation and a final deadline check. Then the placed-induced graph is exactly the graph just before `v` was eliminated. On failure retain the preceding partial state and journal position. At completion, `R` must equal the original adjacency exactly; no synthetic requirement remains. This avoids a second independent pending-demand model and fits the existing builder's `future()` and partial-contact checks.

For degree `d≤3`, at most `d(d−1)/2≤d` edges are added while `d` are removed. Working edge count never increases; the journal contains at most three neighbor entries and three new-fill entries per eliminated vertex. A lazy degree heap with stale-entry checks gives a straightforward `O((n+m) log n)` reduction bound and `O(n+m)` storage. This does not bound the subsequent physical search.

## Smallest useful prototype

```text
start one absolute deadline D; normalize original graphs once
compute anchors, elimination journal, filled core, and R
if the residual core has an edge:
    call the current independent native constructor once on that core
else:
    place residual anchors directly on distinct available target sites
    (original isolated vertices need no contact/frontier reservation)
for (v,S,F) in reversed journal:
    remove F privately from R
    grow urgent existing neighbors, then insert a connected chain for v
    allow connector paths to be split between v and those neighbor chains
    prune only while preserving trial R contacts and pending extension ports
    validate the partial minor; commit it and the trial R before D
validate full original graph, exact R equality, and timeliness
return one complete embedding, or explicit failure with partial diagnostics
```

There is **at most one** native core call. The edgeless structural base case is accepted by root and avoids invoking the geometric/JIT pipeline for fully collapsed components. Anchors use descending original degree and the same fixed source tie rank; target choices use distinct available sites ranked by available degree and a seed-shuffled target tie rank. Preserve a free extension port for anchors with pending demands. The exact small base-case implementation needs a bounded scan, including disconnected and isolated components; it must not hide quadratic rescanning behind a “constant-time” claim.

Reuse the stable B003 `_Builder` insertion primitives from `frontier_bounded_construction.py`: `prepare()` grows an old neighbor with one remaining distinct free port; `path()` routes through free sites; `cut()` can give connector sites to either the new chain or the old neighbor; `prune()` preserves current contacts and a future extension port. Use the trial `R` as its required adjacency, not static original adjacency. The reverse order replaces its vertex-selection loop. Retain its 64 screened roots, four local insertion branches, bounded price `1+p/(1+p)`, and one 20-million adjacency-scan allowance for the whole expansion. These are initial inherited choices, not tuned from A049 outcomes. All setup, copying, sorting, failed branches, validation and publication count in elapsed time; scan units are not comparable to native routing pops.

For a nontrivial core, use the current fixed cyclic native configuration once.
**Root's pre-code implementation decision:** keep the native implementation
unchanged for this exploratory prototype. The wrapper owns the original
absolute deadline and supplies only its remaining relative allowance to the
core call. Native's internal relative clock starts slightly later because of
call setup; this is cooperative cancellation, not an exact shared inner
deadline. The wrapper must immediately reject a core return after its original
deadline, even if native labels it SUCCESS, and must retain that full elapsed
cost. Expansion and final adoption use the original absolute deadline directly.
A fake-clock late-core test is required. This avoids changing shared correctness
infrastructure before the construction hypothesis has evidence. No free-space
reconstruction fallback, second full constructor, or choice between complete
outputs is proposed. Failed lifting remains evidence. Existing `repair_group`
is a strict-Q improver of a valid complete minor and cannot directly insert a
previously absent vertex. Geometric `field.complete_seeds` is likewise not a
generic reverse-insertion interface.

## High-degree growth and counterexamples

For a connected chain of `k` sites in a target of maximum degree `Δ`, at most `(Δ−2)k+2` couplers leave it: at least `k−1` internal edges each consume two degree incidences. A logical degree-127 hub on ideal Zephyr with `Δ=20` therefore needs **at least seven sites**. A fixed singleton anchor cannot work. Count the **distinct free neighboring sites** of each chain, not outgoing couplers; several couplers may lead to the same future leaf site.

The first prototype uses B003's incremental rule: before inserting a neighbor, if further pending demand remains, grow a chain having only one free port until it exposes at least two, or fail. Later pruning retains a port while demand remains. This permits eventual hub growth without reserving 127 sites at once. It is insufficient as a general capacity guarantee: a sole port may enter a dead end; multiple neighbors compete for the same sites; wheel rim contacts need joint routing even when the hub has ample ports. Record pending demand, chain size, distinct boundary size and staged growth at failures.

A hand-checkable missing-detour example is target path `q0–q1–q2–q3`, with the filled core edge embedded as `a={q1}, b={q2}`. Replacing its synthetic edge by source path `a–v–b` has no free connected route touching both fixed endpoint chains. Yet `a={q0}, v={q1}, b={q2}` is valid. B003 can split **new free connector paths** but does not relocate these already occupied singleton endpoints, so this core choice can fail. Clique contacts after degree-three fill likewise do not supply a free branch set touching all three neighbors. These are incompleteness examples, not reasons to add an unplanned alternate constructor.

## Self-critique and cheap falsifier

Elimination may leave a large minimum-degree-four core, create inconvenient fill contacts, or discard placement information needed for expansion. A good core ACL need not lift well. Port protection can lengthen chains or still trap later insertions. A fixed anchor and reverse order can be poor. Nested synthetic requirements increase pending degrees and may make the inherited lookahead conservative. Full repeated validation or anchor scans could erase the speed benefit. None of elimination, connected routing, port protection, or their combination has established novelty here.

Before implementation freeze, use a few fixed checks: nested fill with shared existing edges and exact final adjacency recovery; components/isolates; deadline rollback; the missing-detour failure above; degree-two subdivisions; and an independently generated degree-127 star and wheel on ideal Z12. Require valid output or truthful failed insertion, never presumed embeddability. The star test must demonstrate a multi-site hub if it succeeds. These are correctness/failure witnesses, not new held-out performance inputs.

**Pre-screen reach gate:** the star, wheel and degree-two subdivision cases
must actually complete under the fixed bounded policy before launching the
34-input screen. Failure on these basic lift cases is informative evidence
against this first construction policy, even when correctly reported. Save it
and reconsider the mechanism instead of automatically increasing its limits.
The deliberately blocked P4 core remains an expected truthful failure.

Only after those checks, propose a cheap fresh paired screen on the same 34 development structures, seed zero, ideal Z12, common 60 seconds: current cyclic pipeline versus this single reduced-core algorithm. Preserve every failure, reduction/core size, fill count, core time, expansion work/time, growth Q, failed insertion, final original-valid Q/ACL and total process time. No experiment is frozen or launched by this design. If lifting failures or expansion cost overwhelm the sparse gains, reject or revise the mechanism explicitly; do not select a per-family winner. One seed cannot establish ACL variance or an all-class advantage.

Source inspected: B003 `frontier_bounded_construction.py` (`prepare`, `path`, `cut`, `prune`, `insert`), current `native.py`, `contact_repair.py::_grow/repair_group`, and `field.py::complete_seeds`. The proposed algorithm uses one evolving partial embedding; local insertion branches are internal proposals, not a portfolio of complete embedders.
