# Experiment 011: contact refinement after geometric order search

Date: 2026-09-07. Development data only. Source is frozen before launch in
`results/codex/011-search-contact-ablation`; its manifest records the exact
source revision, file hashes, input hashes, settings and seeds.

## Rationale and critique before running

Experiment009 found that the native search configuration substantially improves
on packed construction for sparse inputs. Packed construction is therefore not
the lead general configuration. Preserve its dense results and negative sparse
results; do not introduce family-based switching. Native search remains the one
constructor for every candidate in this ablation.

The implemented contact primitive is unchanged. Expose its existing group-size
and expansion bounds through the native entry point so single-chain and joint
moves can be compared. The five fixed configurations are MM, native search
without contact refinement, search plus singleton reconstruction, search plus
width-one joint reconstruction, and search plus width-four joint reconstruction.
They are independent experimental rows, with no per-instance best-result choice.

Self-critique of these configurations: singleton reconstruction may account for
most easy reductions; wider beams can spend budget on alternatives that never
complete. Group selection may revisit overlapping regions and fail to cover the
whole source. A fixed number of attempts is not equal work, so report actual BFS
expansions, accepted moves, CPU and wall time. A wider beam can produce a worse
final trajectory under fixed work bounds. Width-one already examines both pair
orders; a growing member is not evidence specific to width four. Strict qubit
descent can still stop above a useful local plateau. None of these mechanisms
alone establishes novelty (see `../contact_prior_art.md`).

Prediction: reconstruction will shorten some valid search embeddings, especially
where the geometric representation retains unnecessary chain segments. Dense
embeddings may have little room left. The immediate falsifier is no material
quality gain beyond singleton/width-one controls at a plausible runtime cost.
Do not fit graph-specific group counts or roots in response to individual rows.

## Frozen protocol

Reuse all nine development inputs from009, two solver seeds (0,1). Sixty-second
solver allowance for every method, correcting009's short K100 MM time allowance
without relabeling its recorded timeout as a success. Native search uses1000 asks.
Refinement uses four passes, a total512 group cap,500000 popped-vertex cap,
and the existing per-group/region/root bounds. Singleton groups are `[1]`;
both joint configurations allow `[1,2,3,4]`, with width1 or4 respectively.

The global limits are identical across input classes. All methods use sequential
randomized method order, fresh processes, empty per-task JIT caches and one thread.
Candidate environment contains no MM/busclique. Validation and deadline accounting
are identical to corrected experiment009. Timing is exploratory on the developer
machine; separate solver and whole-process values. Two seeds provide only a very
weak variance estimate, not a class-level precision claim or confirmation.

## Results

Pending at launch. Compare quality on paired timely valid trials and report
coverage/status separately. Preserve optimal ACL1 ties as ties. More scales,
seeds and actual Ember corpus coverage are required before deciding on a general
improvement, and fresh confirmation data are still untouched.
