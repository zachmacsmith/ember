# After B030: bounded ATOM/CHARME mechanism review

2026-09-10. **No B031 constructor is selected from these leads.** The review
resolves an unexamined operation, but does not establish a credible route to
compact fixed-Z12 embeddings. Exactly two external primary sources were read,
the papers below. No author code, checkpoint, binary, new input, saved embedding,
candidate dependency, implementation or experiment was used.

Starting points were the existing [literature review](../literature_review.md),
[contact review](../contact_prior_art.md) and
[ownership review](../ownership_exchange_prior_art.md). The question was which
construction operation differs materially from our completed work, not whether
the papers' aggregate comparison claims transfer to Ember.

**ATOM's concrete operations.** Algorithm 2 selects a free root by summed clean
shortest-path lengths to embedded neighbors, then divides unshared path portions
between the new owner and old owners using logical degree. Algorithm 3 maps an
old Chimera cell coordinate `(x,y,z)` to `(2x,2y,z)` and gives every occupied
site an additional orientation-specific bridging site. Thus it moves the whole
contact structure coherently rather than rerouting each owner independently.
The stated expansion assumes sufficient hardware and doubles the active grid
dimensions. [ATOM, §III-B/C, Algorithms 2–3](https://arxiv.org/html/2307.01843).

Two deductions matter. With fixed selected paths and complete disjoint assignment
of their free union, changing the ownership split cannot reduce the current
total added Q; its possible benefit is future contact placement. The displayed
expansion allocates two distinct sites per previous occupied site, hence doubles
Q for that operation. It supplies space and preserves contact relationships,
not immediate compaction. Neither fact establishes its final quality on Z12.

**What CHARME adds.** Its learned action chooses the next source vertex; the
state transition calls ATOM's insertion and expansion routines. Its order
refinement searches prefixes, evaluating candidate next insertions and pruning
with an estimated completion cost. The proof describes minimizing a union of
clean shortest paths, whereas ATOM's displayed root rule minimizes their summed
lengths. Those objectives need not agree. Moreover, future neighbor-chain growth
changes path endpoint sets; shrinking the free set alone does not establish the
cost monotonicity needed for a bound. These are reasons not to import the bound
without a separate proof, not a claim of a tested implementation bug. The paper
itself distinguishes its non-expansion condition from empirical behavior on
general prefixes. [CHARME v2, §3.3–3.4, Theorem 1 and Algorithm 3](https://arxiv.org/html/2406.07124v2).

| Lead | Existing work and decision |
|---|---|
| Degree-based division of insertion paths | Early B constructors already grew old neighbors while inserting a new tree; B018–B029 also changed contact/chain allocation. Redistribution alone supplies no new immediate-Q operation. Do not relabel it as B031. |
| Learning or searching insertion order | A's separate initial-layout review owns this question. It does not introduce a distinct chain-construction mechanism, and cannot repair an inadequate deterministic transition by assumption. No learned model or MM-derived training is proposed. |
| Coherent contact-preserving hardware deformation | Materially different from B030: its patches could fragment owners or lose contacts, while the ATOM expansion retains the existing contact network through bridges. Also different from C018's whole-owner regrowth and C019's joint star assignment. This is an untested operation here, but expansion itself increases Q and is finite on Z12. Not selected for code. |

The geometric lead is not eliminated as a mathematical idea. Its missing
ingredient is an **actual Q-reducing or Q-controlled transformation on fixed
Zephyr**, preserving many mutually dependent contact positions while creating
useful insertion space. An inverse expansion merely undoes an earlier imposed
expansion; it does not establish a useful compaction of arbitrary candidate
states. A proposed local strip insertion/deletion would need an exact Zephyr
map, collision/contact conditions and a reason to expect low final Q before
becoming a constructor proposal. Calling such a map “topology adaptation” is
not that design. No coordinate transformation or hidden hardware-size increase
is authorized by this review.

This caution follows measured failures, not a demand for guaranteed success.
B030 made 31,037 slots and 613 accepted merges without any recorded M=0 state;
the merges added 1,747 sites. Adding another access-restoring growth operation
without a compactness mechanism repeats that unresolved tradeoff. B023 restored
contacts but left sparse Q far above MM; B029's lower overlap accompanied larger
initial Q and two regressed old successes. C018 already demonstrates completion
through nonlocal owner rebuilding, with poor first-valid and final quality.
C001/C002 show why preserving coarse boolean contacts alone cannot justify
later subdivision. All of these rejections remain intact.

**Decision.** Close CHARME as a lead for a distinct B chain constructor, and
record ATOM's coherent deformation as an unimplemented but currently incomplete
lead. Do not launch an ATOM translation, order-search sweep, dilation-only
constructor or saved-state campaign from this review. No before-code candidate
is presented because its central low-Q operation is still missing. A future
proposal must make that operation concrete, identify whether geometry, joint
contact feasibility or cost is the target, and proceed to a small complete
screen with first-valid/ACL trajectories rather than promote successful
expansion or a lower distance proxy. Component novelty is not claimed.
