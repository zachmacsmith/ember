# Stop when a validated embedding attains a qubit lower bound

Design and self-critique only. This is a future hypothesis, separate from the
frozen 037 experiment. No algorithm source was changed and no constructor or
embedding experiment was called for this note.

The stopping certificate is exact, but its practical availability is unknown.
A check after an existing physical conversion is inexpensive and cannot save
the preceding layout search. Saving layout time requires an earlier physical
witness. Existing geometric scores do not certify that witness. The recommended
next investigation is at most **one additional, prespecified physical check**
per run, after cheaper source/target capacity tests. Repeated conversion is not
recommended.

## Evidence motivating the question

The independent [032 review](experiments/032_results_review.md#optimality-certificates)
finds optimal ACL-one candidate witnesses on path and cycle in every recorded
seed, yet layout uses all 1000 evaluations in 132 of 136 candidate calls.
The maximum paired solver ratio, 28.412993 on cycle seed 2, occurs at an optimal
ACL tie. These are historical observations motivating a general stopping rule;
neither source names nor MM measurements enter the proposed algorithm. The
saved final witnesses do not establish when their optimality became available.

Experiment [030](physical_checkpoint_spec.md#cost-and-negative-findings) evaluated
29, 64 and 57 physical checkpoints on three fixed random-initialization inputs.
Its callback overhead was respectively 81.2%, 76.3% and 55.9% of remaining warm
placement time. The only strict physical improvement was seven *unrefined*
qubits on complete-40; the two sparse inputs had no gain. These are measured
costs of that diagnostic, not estimates of this proposal or a cold/warm speed
comparison. A certificate rule must not quietly revive that 64-evaluation
selection policy.

## Exact certificate and its scope

Let the simple, undirected, loopless source be G=(V,E), with n vertices,
m edges and degrees d_v. Let the actual available target be H=(W,F), with
N vertices and maximum degree Delta. Use actual target adjacency, including
missing qubits and couplers; an architecture label is not a degree certificate.

For any nonempty connected chain C of t qubits, the number of target couplers
leaving C satisfies

```text
boundary_edges(C) = sum(deg_H(q) for q in C) - 2*internal_edges(C)
                  <= Delta*t - 2*(t-1) = (Delta-2)*t + 2.
```

Connectivity supplies at least t-1 internal couplers. A source vertex v must
contact d_v distinct other chains and thus needs at least d_v boundary couplers.
For Delta > 2 define

```text
b = Delta - 2
ell[v] = max(1, (d[v] - 2 + b - 1) // b)   # exact integer ceiling
L = sum(ell.values())
```

For Delta <= 2, use the universally valid but weaker ell[v]=1; division by
Delta-2 is not defined or useful there. Separate low-degree infeasibility
arguments are not required for this stopping certificate. For an empty source,
L=0 and the empty valid embedding is optimal; do not divide by n to report ACL.

Every valid minor embedding has Q >= L. Therefore an independently validated
embedding with **Q=L** is globally optimal in Q, and in mean chain length Q/n
when n>0. There is no need to solve an optimization problem to verify it.

Equality also forces every chain to have length ell[v]: no other chain can
compensate for one exceeding its own lower bound. If all runs on the same input
attain this certificate, their ACL variance is zero. A certificate in one run
does not establish that other seeds attain it. For a single certified embedding
the whole vector of chain lengths is fixed by the bound; geometric location and
contact redundancy remain unconstrained.

This proves optimal **Q**, not optimal secondary contact redundancy. Stopping
can omit equal-Q moves that improve redundancy. Once Q=L, those moves cannot
enable any lower-Q valid output on this target. If redundancy itself becomes a
requested output objective, ending its optimization needs a separate decision.
An optimal ACL-one result can tie another optimal result; it cannot strictly
beat ACL one. The stopping theorem does not settle the project's convention for
counting such ties.

The proof requires exact source coverage, nonempty connected chains, disjoint
physical ownership, and every source edge represented by an actual target
coupler. A partial chain map with a small count is not a certificate. Count
integer qubits from actual chains and validate against the same graphs. In
particular, do not certify from a floating geometric score or solely from a
logged qubit total. A future implementation must check the simple, undirected,
loopless graph contract before enabling this certificate; metadata alone is
insufficient. The current contact context uses a floating division in
its lower-bound calculation
([contact_repair.py:68](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L68));
the future certificate should use the integer formula above even though current
Z12 inputs are far below floating-point precision limits.

## Cheap necessary prechecks that can eliminate extra conversions

There is a source/target-only relaxation of attaining L. It does **not** inspect
or predict the current placement. Sort actual target degrees in nonincreasing
order D_1,...,D_N and let P(k)=sum(D_i for i<=k), with P(0)=0.

At Q=L, chain v has exactly ell[v] qubits. Applying the boundary identity before
replacing each target degree by Delta gives three necessary conditions:

1. **Individual degree capacity:** for every v,
   `P(ell[v]) >= d_v + 2*(ell[v]-1)`.
   The sum of degrees of any ell[v] distinct physical vertices is at most
   P(ell[v]), irrespective of whether they can form a connected chain.
2. **Total degree capacity:**
   `P(L) >= 2*m + 2*(L-n)`.
   Sum the individual requirements over disjoint chains; their union has
   exactly L qubits. Multiple physical couplers representing one logical edge
   only increase the required degree sum and cannot invalidate this necessary
   inequality.
3. **Distinct singleton sites:** for every integer threshold r,
   `count(v: ell[v]==1 and d_v>=r) <= count(q: deg_H(q)>=r)`.
   All vertices whose minimum chain length is one need distinct physical sites
   of sufficiently large degree. Degree eligibility sets are nested, so suffix
   counts test exactly this *degree-only assignment relaxation*. They do not
   test adjacency between the assigned sites. Ignoring occupancy needed by
   longer chains makes the relaxation weaker, not unsafe.

Also require L<=N before querying P(L). A violation of L<=N proves that no valid
embedding exists at all under the lower bound; the other failures only prove
that Q=L is impossible. These latter failures must not be reported as embedding
infeasibility. They can disable all **extra** conversions whose only purpose is
to discover a witness attaining this particular bound. The ordinary embedding
pipeline still runs. This design does not silently replace L by another bound.

A hand example shows why this can be useful without graph-family dispatch.
Take a source with two adjacent degree-four vertices, each also adjacent to
three distinct leaves. Replace one degree-four vertex in the target by two
adjacent degree-three vertices, distributing its four external edges two to
each. The target has nine qubits, maximum degree four, and only one degree-four
qubit. The source has eight vertices and L=8. The singleton suffix test fails
at r=4, although contracting the two replacement vertices gives a valid
nine-qubit minor embedding. Thus rejecting the certificate is distinct from
rejecting the embedding problem. This is a proof example, not an experiment.

All tests can pass while L is unattainable. A triangle source and a four-cycle
target pass with L=3, but three singleton sites in the target cannot form a
triangle; a two-qubit chain supplies a four-qubit minor witness instead. The
weak Delta<=2 bound remains valid in this example. Adding a pendant target
vertex raises Delta to three without removing the counterexample or changing
its passing degree tests. Connectivity and required adjacency remain missing
from the relaxation.

With degree histograms and an integer prefix table, these tests require
O(n+N+Delta) additional arithmetic and O(N+Delta) storage once degrees are
available. Building or checking adjacency costs O(n+m+N+|F|) if it is not
already available. The prefix table can instead be evaluated at only the
needed sizes, but that optimization needs no new search method. Charge this
setup to the ordinary solver deadline, once per call; never rebuild it at each
placement proposal. A low target degree makes the histograms small. These
conditions may reject nothing on intact Z12 when high-degree qubits are
abundant relative to the source; no useful rejection rate is assumed.

Independent mathematical review by `/root/literature` agrees with all three
conditions under these contracts, including the need to check L<=N before
querying a degree prefix. Since all ell[v] are positive, this also bounds every
individual ell[v] by N. This is a proof review, not a numerical experiment.

## What cannot currently gate conversion safely

The [physical-cost audit](physical_cost_model.md#why-completion-and-pruning-break-a-cheap-exact-final-cost-claim)
separates geometric score, emitted wires, seeded chains, completed chains and
post-pruning qubits. Completion changes shared occupancy, while pruning uses
actual live contacts and can remove a whole redundant arm. The constructor
initially emits both arm orientations even when a surviving singleton uses
only one. Consequently, a raw two-arm cost can exceed L while its pruned
embedding attains L. An exact raw count alone is not a lower bound on pruned Q.

Do **not** use any of these as an impossibility test for certification:

* geometric score greater than a rescaled L;
* raw or completed Q greater than L;
* active arm count, hull spans or a preferred contact orientation;
* zero misses as sufficient physical validity, or positive overload as proof
  that a copied and projected state cannot yield a valid optimum.

The ranking reversals in 030 refute equality and order preservation between
these costs. They do not prove that no stronger placement-dependent bound can
ever be derived. A safe future rejection bound would have to hold after all
allowed completion and pruning operations. No such cheap, informative bound
has been established from the current summaries. Restricting possible singleton
sites to current geometric arms is also unjustified when completion can add
qubits outside those arms. Exact subgraph feasibility at L=n would solve a
much harder problem than the proposed histogram relaxation.

There is one trivial state-dependent precheck once physical chains already
exist: if their exact Q is not L, skip a **certificate-only validation**. This
does not eliminate conversion and must not skip any validity check required by
the ordinary pipeline. If Q=L, run the full validator before declaring success.

## Two distinct possible placements of the stopping check

### Check at existing physical boundaries

Native currently converts and completes only after layout, validates, prunes,
then calls contact refinement once before final validation
([native.py:204](../../packages/ember-qc/src/ember_qc/algorithms/factored/native.py#L204)).
At these existing stages, Q=L can end the remaining optimization with the normal
final validator and the original deadline. This adds no physical checkpoint.
Inside refinement, update an integer global Q by each accepted group's exact
old/new count; test equality after atomic accepted moves, not from beam prefixes.

The benefit is limited. Current group generators omit groups with no positive
excess over individual chain lower bounds
([contact_groups.py:31](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_groups.py#L31),
[contact_repair.py:478](../../packages/ember-qc/src/ember_qc/algorithms/factored/contact_repair.py#L478)).
At Q=L every individual excess is zero, so a fresh group-generation pass already
has no useful groups. An explicit certificate could avoid context setup or
remaining stale groups after the last reduction, and make optimality visible,
but it cannot recover time already spent on 1000 layout evaluations. Do not
present this inexpensive addition as a solution to 032's runtime gap.

### Future single early-check hypothesis

To test actual layout savings without repeated checkpoint selection, use one
globally fixed opportunity: immediately after the existing initial three
packing readouts and initial proxy record, before the first search proposal
([plane.py:363](../../packages/ember-qc/src/ember_qc/algorithms/factored/plane.py#L363)).
Only nontrivial calls with remaining placement work have this opportunity.

The source/target degree tests above must pass. For the first bounded diagnostic,
also require that this initial state already has zero geometric overload. That
last restriction is a **cost throttle, not a mathematical rejection bound**:
overloaded states can become optimal after projection, and this rule deliberately
misses those stopping opportunities. There is no later retry when overload falls,
no checkpoint-index tuning, and no attempt at each strict proxy improvement.

```text
compute integer ell, L and degree-capacity conditions once
run the existing initialization and initial packing unchanged
if there is remaining search, necessary conditions pass, and initial overload==0:
    consume the only optional early-check slot
    copy the current geometry and books
    use the existing conversion, completion and isolate rules on the copy
    if still timely and full physical validation succeeds:
        use the existing deadline-limited pruning rule
        if exact Q==L and a final full validation succeeds while timely:
            return this embedding with an optimal-Q certificate
    discard the temporary physical candidate, regardless of its other merits
continue the unchanged placement trajectory and its original final conversion
at ordinary validated physical boundaries, return when exact Q==L
```

There is one evolving placement state, one initialization, no restart and no
comparison between alternative solver outputs. An uncertified early candidate
does not seed refinement or compete with the final retained geometric state.
Contact repair is not run at the early check: either an optimal-Q witness ends
the call, or the ordinary pipeline can later make its one existing repair call.

Copies must preserve the current layout, best proxy record, proposal history and
scheduler RNG. At equal non-time work and without deadline binding, an
uncertified probe must leave the subsequent search trajectory identical to the
control. Wall time is not preserved: probe cost consumes the same absolute
deadline and can reduce later work or turn a formerly timely call into a timeout.

**One call is not a hard work bound.** Current conversion and completion have
no internal cancellation points, and pruning does not check every innermost
operation. A before/after deadline check cannot interrupt a large conversion.
An implementation must retain truthful timeout reporting and the outer worker
watchdog; it cannot advertise a strict per-probe wall cap. If a hard auxiliary
work limit is required before deployment, cancellable primitive operations are
a prerequisite and a separate implementation task. Do not grant extra wall time
or retry after an interrupted probe. An optimal but late witness may be recorded
as a certificate in diagnostics, but must not count as timely success.

## Self-critique before implementation

1. **The bound is often unattainable or reached late.** Degree capacity ignores
   topology. The promising 032 final witnesses do not imply their initial
   geometric state prunes to the bound. A single early check may miss every
   optimum and only add overhead. That outcome would reject this placement
   of the check, without falsifying the theorem.
2. **The truly safe prechecks may be almost vacuous on Z12.** Most small sources
   have ample eligible target sites. Stronger site matching or topology tests
   could consume the time this rule seeks to save. Do not expand them into
   another embedding solver or tune thresholds from named inputs.
3. **Construction and pruning costs are real.** Reducing 64 opportunities to one
   bounds repetition, not worst-case latency. Completion/global occupancy and
   converter state growth remain. Cold imports/JIT and initial packing also
   remain even after an immediate certificate; no MM-scale speed guarantee
   follows.
4. **Quality is protected only when the stop is certified and timely.** Then Q
   cannot be worse than any valid continuation. Failed probes still consume the
   common deadline and can worsen output quality or success on other calls.
   Preserve those regressions. Returning a smaller but uncertified probe would
   introduce the physical-output selection policy deliberately excluded here.
5. **Validation and diagnostics can invalidate the apparent savings.** Full
   validation is mandatory at the return boundary and costs work. Use integer
   counts and original graph labels, report certificate time separately from
   completion time, and do not call the rule novel merely because its proof is
   exact. It is a conventional lower-bound stopping criterion inside the same
   embedding algorithm.

## Falsifiable next diagnostic, only after separate authorization

First, inspect the saved source/target degrees and final validated outputs for
all 34 current inputs. Compute L, each necessary-condition outcome, and final
certificate status. This needs no construction and would quantify whether the
degree prechecks reject anything; it cannot estimate early savings. Recompute
degrees from graph edges, not saved family labels or an advertised Delta.

If the question remains useful, freeze the current globally fixed pipeline and
take **exactly its initial prefix** on all 34 inputs, seed zero: source-only
spectral initialization, the same three packing readouts, and at most the one
eligible physical check above. Freeze input, target, source and environment
hashes beforehand. No later placement, alternate initialization, contact repair
or MM call is needed for this mechanism screen. Independently validate every
returned chain map; retain all failed, skipped, late and nonattaining cases.
Record graph sizes/degrees, L and gate reasons, initial proxy/overload, actual
constructed/pruned Q, chain hashes, initialization/packing/check/prune/validation
wall, and total deadline status. Measure empty-cache and warm costs separately;
neither is a proxy for the other.

If zero eligible initial prefixes attain L, stop this hypothesis rather than
searching for favorable checkpoint indices. A source/target capacity gate that
rejects no input should be reported as ineffective in this screen, even though
mathematically correct. If any timely certificate exists, a separately
prespecified full-pipeline paired ablation must compare the one-check rule with
the unchanged control on **all** 34 inputs under the same deadline. Preserve
nonattaining overhead, binding-deadline failures, all Q differences and full
non-time replay checks; do not run it only on the certified subset. Historical
032 times cannot establish a speed improvement for a later implementation.

Status: stable design only. No proposed check changes 037, and no performance
gain, early certificate, or source/target gate rejection has been measured for
this proposal.
