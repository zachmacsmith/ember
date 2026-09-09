# Retain side branches during joint path reassignment — design only

2026-09-08. The fixed pure-path operator remains unpromoted: it reaches the
cycle's Q126 optimum but ties on cubic, kagome, grid, planted and Petersen.
No further numerical analysis or candidate call follows that gate. This is one
new representation hypothesis, requiring root review before implementation.

**Diagnosis and hypothesis.** All25 unshortened non-cycle witnesses failed the
fixed-route allocator. The corrected monotonicity proof makes that allocator
complete for its positive contact constraints; changing segment-boundary search
cannot fix those questions. The current representation discards every selected
chain's off-route sites, including side-contact branches. Retaining those
branches while jointly moving the owners of the central route may permit
useful contractions across several of these recurring deficits. This targets
representation within the move, not neutral acceptance, reduction eligibility
or an increased search allowance. It does not prove that a smaller minor exists
inside the expanded representation.

Use the same one A053 construction and the same bounded post-lift path policy.
Keep its eight seeds, induced-path order, one canonical BFS witness,512 route
sites,32 route attempts,1M work and common stage/deadline rules. There is one
change: **retain every off-route component at its existing logical owner**.
Do not add free sites, release another owner, try another route, prune branches,
alter acceptance or choose between completed constructors.

For a selected logical path P and its current physical route L, define
`B_v = C_v minus sites(L)` for each selected owner. Compute the connected
components of B_v in the target. These components remain fixed for this path
query, including after a successful shortcut. Every proposed nonempty segment
for v must touch each retained component, making their union connected. It must
also supply every outside logical contact not already supplied by B_v. Outside
chains stay entirely fixed. These are positive contact requirements on route
sites; extending a segment cannot destroy one. Thus the same earliest-end
allocator has the same fixed-route feasibility argument, without adding an
exact solver. Extra physical contacts are harmless.

```text
after one complete original-valid A053 lift:
    generate the unchanged bounded induced-path sequence
    for each path, extract its one current physical witness L
    freeze outside chains and each selected owner's components off L
    build per-owner requirements:
        touch every retained component
        touch each outside logical neighbor not already reached by that owner's residue
    try the unshortened witness and the unchanged bounded forward chords
    greedily assign nonempty route segments satisfying these requirements
    candidate chain = retained residue union assigned segment
    independently certify the whole original minor; admit only timely strict-Q gains
```

At query entry, the original owner segments are a feasible partition of the
unshortened witness under this representation. Each off-route component must
touch that owner's route subset because its original whole chain is connected.
Every original outside contact is either supplied by its residue or by its
route subset. Therefore an unshortened-witness allocation failure would be a
correctness defect, not negative mechanism evidence. This property establishes
feasibility only; it does not promise a strict-Q shortcut. Component extraction,
contact-set construction, failed candidates and certificates all consume the
same existing work/time allowance. Component/site counts and their costs must
be reported separately, without reusing stale requirements after a different
path changes ownership.

**Hand-checkable changed reach.** Source edges are `a-b, b-c, b-x, c-y`.
Target edges are `0-1,1-2,2-3,0-2,1-4,2-4,4-5,3-6`. Start with
`a:{0}, b:{1,4}, c:{2,3}, x:{5}, y:{6}` and path `a-b-c`, whose witness is
`[0,1,2,3]`. A pure segment cannot touch x at5, so the earlier representation
rejects. Retain b's component `{4}` and shortcut to `[0,2,3]`: the candidate
`a:{0}, b:{2,4}, c:{3}` preserves frozen x/y and reduces Q7→6. Neither old
site of b or c is individually deletable while retaining all its contacts.
Removing target edge `2-4` must reject this particular shortcut because b's
retained branch would disconnect; its contact to x alone is insufficient.
These are step witnesses, not claims about the full path selector or novelty.

**Cheap prospective complete-constructor falsifier.** If root approves this
policy, require only the changed-reach/disconnected-residue tiny fixtures,
unshortened-witness feasibility and budget/deadline rollback checks. Then go
directly to18 fresh same-host complete calls: fixed A053, this one stage after
one A053 call, and isolated fresh MM; seed0/60s, on the same cycle1829,
cubic33219, kagome32122, grid1584, planted34404 and Petersen4083 bytes. The MM
comparator has its own process/environment and is never called by either
candidate. No additional saved-final search, exact solver, local tuning or
alternate complete output is proposed. Freeze graph order and within-input arm
order before calls, using the existing fresh-process harness. Preserve all
failures, Q/ACL, maximum chain, within-chain variance and same-host times;
report every candidate/MM result without pooling historical MM observations.
This is one seed on six exposed structures, not an across-seed variance or
held-out generalization estimate.

To support broader follow-up, require cycle benefit to remain, improvement on
at least one of the other five versus fresh A053, no loss of timely valid
coverage, no aggregate-Q regression and no >10× runtime regression versus
fresh A053. Each regression stays visible even if these aggregate conditions
pass. A favorable gate does not establish MM superiority: the fresh-MM table
separately determines which quality/runtime gaps remain. Cycle-only benefit or
no non-cycle improvements rejects this fixed broader-use hypothesis.
An allowance stop with a timely valid retained output is a measured finite
outcome; unvisited alternatives remain unknown.

**Self-critique.** Keeping branches repairs a representational exclusion but
may immobilize owner boundaries: a retained component can have only one route
attachment, so most shortcuts still fail. It also preserves costly redundant
material and pays for additional component/contact bookkeeping. The occupied
footprint, source order, frozen endpoints and one-route restrictions remain;
free-site rerouting or broader ownership relocation may be necessary instead.
A strict-Q local improvement is not a complete-constructor quality guarantee,
as B004 already showed. The two A057 failures still cannot enter this stage.
No coverage, MM, across-class or novelty claim follows, and the failed pure-path
gate is not retrospectively promoted.

Before wrapper code or outcomes, root approved this return convention: preserve
the local-stage stop/overrun verbatim and retain only a candidate whose full
certificate and admission finished before that local deadline, or the unchanged
certified A053 entry. A later local stop does not erase the earlier minor if
the wrapper's final original-graph validation and actual return finish before
the original absolute deadline. Final wrapper validation/bookkeeping costs are
recorded separately within that original deadline; no stage search/work is
renewed. An interrupted or late proposal certificate never publishes that
proposal. Approved proposal bytes and the timestamped clarification are saved
under `results/codex/branched-path/precode`.
