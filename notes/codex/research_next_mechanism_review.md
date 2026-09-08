# One next neighborhood hypothesis: contraction by ownership exchanges

2026-09-08. Design only. I read source and already-audited development reports;
I did not inspect new corpus outputs, execute a constructor or solver, or change
production code. I retain **one** proposal. It changes the physical assignments
the local search explores, rather than adding another secondary quality score.
It is not yet authorized for implementation or established as novel.

## What the evidence establishes

[032](experiments/032_results_review.md) has 122 jointly timely candidate/MM
trials: the candidate wins 38, loses 76, and has eight optimal ties. Across the
28 inputs with four successes from both methods, mean ACL is 2.26129 versus
2.22256. On two tree inputs MM attains ACL 1 on all four seeds, while the
candidate averages 1.08071 and 1.10331. The grid and honeycomb means are
1.36914/1.08203 and 1.44211/1.04737, respectively. These labels describe the
evaluation inputs; they must not select an algorithm. The paired median solver
time ratio is 7.9259, and 50 of 122 ratios exceed ten. These are historical
results preceding the converter correction, not current comparative timings.

The source exposes a concrete restriction, independently of those averages.
[`_alternatives`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L226)
releases selected chains and rebuilds them sequentially. Its generated roots
are truncated, a pending chain supplies only an old-location preference, and
the fixed leading configuration retains one prefix.
[`round_robin_groups`](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_groups.py#L9)
chooses windows of neighbors rather than discovering the chain dependencies of
a particular attempted shortening. Ordinary groups contain at most four chains.
The implementation can change ownership and grow a member already; those are
not missing capabilities to claim anew. What it lacks is a proposal that starts
with a particular deletion and repairs its consequences while retaining nearly
all the existing physical assignment.

The gap motivates that hypothesis but does **not** establish that this restriction
caused the measured ACL losses. Saved final embeddings do not reveal every
discarded reconstruction prefix or prove a useful exchange exists.

Prior failures constrain the design:

* [023](experiments/023_contact_tree_ablation.md): the stronger distance-guided
  tree policy loses six cases, ties twelve and wins none; it adds 24 qubits and
  substantially more work. Generating a better isolated tree is insufficient.
* [033](experiments/033_results_review.md): direct singleton relocation saves
  143 qubits inside its own trajectory, yet finishes one qubit worse overall.
  More equal-Q redundancy moves do not establish better final ACL.
* [037](experiments/037_results_review.md): singleton-star matching saves 38
  locally but only seven comparatively, with four regressing inputs. This was a
  small positive aggregate, not a clean failure or an across-class success.
* [039](experiments/039_results_review.md): connected-star search accepts two
  moves, finishes four qubits worse, and spends 98.42% of auxiliary work in
  uncertified considerations. Its independent-singleton-leaf restriction and
  one-root growth are real, but removing a restriction alone did not pay.
* [040](experiments/040_results_review.md): exact cached raw conversion costs
  2.304 times the recorded geometric transitions over the observed prefixes;
  63.49% of old/new line incidences change. Avoid repacking or reconverting a
  layout in each proposed physical exchange. These measurements concern the
  first 32 adoptions on all 34 inputs, not late-stage costs or final ACL.

## Proposed move and its certificate

Start with one independently valid embedding `C`, current ownership, and actual
target adjacency. Select a non-singleton chain from an ordinary scheduled group
and a site `q` whose deletion leaves its chain connected but loses at least one
logical contact. An already legal deletion belongs to the separately reviewed
deletion closure and is not this mechanism's claimed improvement.

In a private proposal, remove `q` permanently. Retain every other occupied site
in a small patch and vary its owner through transfers or swaps. Selected chains
remain nonempty and connected after each exploratory move; logical contacts may
be temporarily missing. Outside chains remain fixed. A swap is simultaneous:
two singleton owners can exchange their sites without either becoming empty.
Frozen-neighbor obligations and edges between selected chains are both checked.

Let `S` be the selected source vertices, `P` the union of their incumbent
chains, and `M` the exact set of missing logical edges incident to `S`.
Every trial partitions `P \ {q}` into connected nonempty chains for `S`.
Consequently it has exactly one fewer occupied site than the incumbent. A trial
with `M` empty is a strict-Q proposal regardless of its raw redundancy or
endpoint-support histogram. Full original-graph validation and the final shared
deadline check precede publication. Any failure leaves the incumbent unchanged.

This is a **fixed-occupied-footprint constraint search**. It neither grows a
center tree nor assigns singleton leaves to a center boundary. It permits an
arbitrary induced logical subgraph and multi-qubit members. It does not route
through a free-space halo, run another constructor, or choose among independent
embedding algorithms. The eventual experiment would compare two fixed revisions
of the one pipeline, not combine their final outputs.

## Bounded procedure

The following limits are a proposed diagnostic contract, not tuned values or a
performance claim: at most eight selected chains, 64 incumbent patch sites,
eight exchanges per branch, four ranked successors at a node and 256 visited
assignments per seed. Existing per-group/global work and common deadline remain
additional stopping conditions. A stricter implementation specification would
freeze these limits and the primitive work definition before any experiment.

```text
for an already scheduled group, under its existing work allowance:
    inspect connected, contact-essential deletion seeds in canonical order
    privately delete one seed q; leave every other chain at its incumbent sites
    form the initial patch from the scheduled group, subject to both size caps
    while the bounded depth-first search has unexplored successors:
        if no contact is missing:
            fully validate; check deadline; commit the one-qubit saving; return
        choose an unmet logical edge deterministically
        enumerate owned sites that can restore an actual contact for that edge
        propose transferring a site, or swapping it with a receiving-chain site
        admit a blocking owner only if its entire incumbent chain fits the caps
        require both changed chains to remain connected and nonempty
        recompute every affected logical contact, including contacts just lost
        rank successors by missing-edge count, changed-site count, canonical IDs
        explore the first four with undo records; allow deficit-increasing steps
        stop at depth, visited-state, work or deadline limits
    discard the private proposal and try the next seed only if budget remains
```

An admitted chain joins the same proposal with its incumbent assignment; its
qubits are added to `P`, preserving the global `Q−1` identity. Admission is
driven by an actual candidate site's owner, not by a source-family label. Patch
admission, missing-contact enumeration and the number of inspected candidates
must themselves be bounded and charged. `M` is a feasibility-search ordering,
not a replacement metric for valid returned embeddings. Depth-first backtracking
retains one evolving private assignment with an undo stack; it is not an
unbounded beam or a sequence of published equal-Q moves.

Build ownership/contact information once for the pass and refresh it after every
accepted ordinary or new move; a failed refresh must disable the cache without
discarding an accepted valid incumbent. This preparation costs up to
`O(Q Δ + n + m)` and is included in measured time/work. With at most `p` patch
sites, rechecking two changed chains and all affected contacts by direct scans
costs `O(p Δ)` per complete successor in the worst case. Generation can inspect
many frozen-neighbor sites; those scans are charged too. Total charged scans
stop at the actual group/global cap. Space is bounded by the original embedding,
ownership/contact data, bounded patch state, undo stack and visited signatures.
The cap bounds work; it does not show that a useful proposal fits within it.

The first full-pipeline comparison should replace the ordinary proposal policy
for every input, under the same visit/work limits, rather than append another
auxiliary stage. This makes loss of ordinary reconstruction power explicit.
Scans, copying, hashing and validation are timed and reported separately from
legacy BFS expansions: equal expansion limits do not imply equal total work.
Given 032's existing runtime gap, even unchanged total wall time is insufficient
to claim the desired MM-scale runtime. No speedup is asserted here.

## Hand-checkable mechanism and counterexample

A small reasoning witness has source path `F–E–A–B–C–D` and physical edges
`f–e–a0–a1–b–c–d`, plus `a0–c` and `b–d`. The incumbent is
`F:{f}, E:{e}, A:{a0,a1}, B:{b}, C:{c}, D:{d}`. Neither site of `A` is
individually deletable: deleting `a0` loses `E–A`, and deleting `a1` loses `A–B`.
Remove `a1` privately and swap the owners of `b,c`. The resulting path uses
six sites, with `A:{a0}, B:{c}, C:{b}`, and preserves all six chains and five
source edges. The frozen endpoints do not move. This explains why optimal-size
neighbors may need a simultaneous exchange without any equal-Q score increase.

This is a hand-derived arbitrary-target example, not an executed test, Zephyr
benchmark or claimed output of the current proposer. The existing three-chain
whole-reconstruction neighborhood could also recover it. It demonstrates the
specified exchange and deletion barrier, not superiority over that refiner.

Conversely, suppose fixed neighboring chains occupy endpoints `x,y` of physical
path `x–a–b–c–y`; the middle logical chain occupies `{a,b,c}`. A free site `z`
adjacent to both `x,y` permits replacement by `{z}`. Every connected chain in
the occupied interior that still touches both fixed endpoints needs all three
sites. The proposed occupied-only search cannot improve this instance; existing
free-space reconstruction can. This limitation survives unlimited exchange work
inside that particular patch.

## Self-critique and decisive next evidence

Transfer and swap search with temporarily unfulfilled contacts is established
prior art, including Bian et al. and PSSA; CMR also reassigns neighboring path
portions. The repository's [prior-art audit](contact_prior_art.md) documents these
mechanisms. The possible contribution is the deletion-conditioned, fixed-Q,
connected ownership search with conflict-driven patch admission and low measured
cost, not the words “swap,” “joint,” or “missing contact.” Novelty is unproved.

The most serious scientific risk is that the current ordinary refiner already
finds most useful small exchanges, while the remaining improvements require new
physical sites, disconnected intermediate chains, or larger patches. The degree
bound's unused slack does not prove any contraction exists. Canonical top-four
successor truncation can lose the needed cycle, even when a contraction fits the
patch; eight moves cannot cover arbitrarily long dependency chains. More states
could repeat 023/039's coverage losses. A strict local saving can also worsen
later cumulative quality, as 033/037/039 already demonstrate. No ordinary-path
replay guarantee survives commits or a binding common deadline.

Before implementation, root should approve a precise certificate/cache/budget
specification and independent tiny full-validity oracles. The next *authorized*
diagnostic could then use one fixed, own-algorithm incumbent per each of the 34
existing structures, comparing the proposed and ordinary neighborhoods with the
same declared work and wall allowances. It must report all misses, interrupted
queries and scans, independently validate proposals, and identify actual gains
not reached by the fixed ordinary control. If it produces only the hand fixture,
duplicates ordinary gains, or costs substantially more per useful contraction,
reject it without increasing limits to rescue particular inputs. Only a surviving
mechanism would justify a full, globally fixed all-34 pipeline ablation and later
repeated-seed/held-out evaluation. No such run is performed or authorized here.

I do not retain a second proposal merely to fill a list. Independent per-edge
orientation flips would relax `_stair_contacts`' global y-rank assignment, but
the old [handoff history](../../docs/handoff/HISTORY.md#36-orientation-flips-alignment-reinsertion-the-truth-round-s399s3101)
already reports that experiment and dense regressions. Those historical claims
are unverified here. A physical-capacity-aware variant remains speculative, and
040 argues against casually pricing it through repeated global conversion.

Inspected source identities: `field.py` SHA256 `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690`;
`plane.py` `5459df9e949df9b0b2e855f100361770b054523542a67c06ece50cbfa1b9b1e8`;
`contact_repair.py` `c6f9a5555b010d5e877b568c1ee760e72d170f1f7e0c186179de16b53630da85`;
`contact_groups.py` `43574f6f13eb33d790de535e4e614533d0f1df7f50d129932301b7832e1301bd`.
