# Independent critique of the ownership-exchange specification

2026-09-08. This reviews the implementation specification, not an implementation.
No candidate module, constructor, native pipeline, corpus or remote machine was
used. The only executed work is a small standard-library mathematical oracle.

The original reviewed spec has SHA-256
`246744d80dffcd2906d21557b4b080775ef49a84d53df10b343fe97e8f9e318e`.
Its state, admission, certificate and depth-dominance rules have no identified
soundness defect under the stated valid-incumbent/authoritative-adjacency
preconditions. The revised specification, SHA-256
`8d870c3a2e16615574ad018eec266258200bd7740b7cbd2450d47a47d299f82f`,
resolves the avoidable per-group setup repetition. I have independently read its
full diff against the preserved original and accept the revised API as a basis
for a bounded isolated prototype, subject to root's implementation authorization.

## Concrete setup issue and narrow remedy

The original one-group-per-call API repeats `O(Q Δ + n + m)` setup even for a
group with only a few patch sites. This is an avoidable algorithmic cost, not
just a Python optimization opportunity. The audited [039 control](experiments/039_results_review.md)
visits 14,528 groups across 34 calls. Its complete-127 input has 8,001 source
edges. Rechecking every source edge at least once in each of 512 hypothetical
calls costs at least **4,096,512 charged edge visits**, before ownership copying,
connectivity or any proposal search. A 500,000-unit allowance would finish at
most 62 such setups even if every other operation were free. This is an
analytic lower bound for that use pattern, not a measured prototype cost or a
claim that every input reaches 512 groups.

The clean remedy is one call over a bounded deterministic group sequence for a
single immutable incumbent: perform original-graph validation and ownership
setup once, search the supplied groups in order, return at most one fully
certified candidate. This requires no cross-call cache or accepted-move refresh.
A later call may be defined on a newly accepted incumbent; its setup must be
charged again. It is not valid to reuse failed-group results on that new state.

The batch contract must retain these details:

* Preserve the supplied group order, normalizing source labels only within each
  group. Charge bounded input traversal, ordering and any duplicate processing.
  A malformed group differs from a geometrically ineligible group; the API must
  define rejection versus per-group skipping explicitly.
* Use one live global allowance and the earlier absolute deadline. Setup,
  normalization, all unsuccessful groups, final copying and certification count.
  Reset DFS/visited state per **(group, deleted site)**; the same site with a
  different initial selected set is a different query. Do not renew work per
  seed/group or cache failure by deleted-site ID alone.
* Return on the first certified candidate. No input group sees another group's
  failed private assignment or a tentatively accepted incumbent. The owner map
  and entry certificate remain immutable.
* Keep any future per-visit allowance separate from this shared setup accounting.
  Assigning setup once to a batch changes work distribution; it is not exact
  replay of the original per-group policy. A scheduler comparison remains future
  work, and no frozen 039 or later experiment changes here.

The final revision meets these conditions. Its finite outer list/tuple supplies
an explicit bound `G = len(seed_groups)`; it adds no numerical group cap.
Every reached group access is charged, so no more than `min(G, B)` accesses can
occur with B units initially available. Groups are normalized lazily, with
uninspected suffixes disclosed. Malformed reached groups stop; fully checked
geometric/size ineligibility skips to the next group. Repeated occurrences remain
ordered and charged. Empty sequences explicitly return `no_groups` without
claiming entry validity. Fresh `(group_index, q)` DFS tables prevent failed
attempts in one patch from suppressing another. These rules share the immutable
entry certificate; they do not share mutable search state or compose outputs.

An oversized list-valued group must not be described as well formed unless its
required label/duplicate checks complete. If that traversal exhausts the work
allowance, the specified interrupted result takes precedence. This is an
implementation test obligation, not an additional requested API change.

Even batched setup can dominate a small allowance. An implementation must obtain
its advertised linear scan bound by accumulating represented logical contacts
from occupied target edges and ownership, rather than repeatedly scanning an
entire chain for each logical neighbor. Metered sorting, materialization and
hash/signature equality remain additional costs. No runtime claim follows from
the asymptotic improvement alone.

## State, undo and certificate conclusions

The invariant is sufficient: the deleted site is permanently absent; current
selected chains partition the surviving original patch; all chains remain
nonempty, connected and disjoint; outside owners retain their entry chains.
An admitted outside owner contributes its whole unchanged entry chain. Admission
and transfer/swap are one private child operation. Therefore admission preserves
global `Q_entry−1` and cannot silently allocate a free site or lose a source
vertex. An actual swap must test both final chains, permitting singleton swaps.

The missing-edge set must include all source edges incident to the enlarged
selected set, including the donor's newly affected frozen-neighbor contacts.
Requiring the particular chosen edge to become represented does not preserve
other contacts; those must be recomputed. A whole-original-graph certificate,
outside equality and the partition/Q checks before return correctly protect
against an erroneous incremental missing set. A mismatch is an internal error,
not an ordinary unsuccessful proposal.

Immutable parent handles with independently copied bounded child views give
straightforward rollback: interrupted admission, copying, generation, sorting or
validation discards the unfinished private state. Previously admitted chains
must retain their current assignments, not be reset to entry locations.
The frozen owner map is an entry map, so lookups for selected owners require the
current overlay. Treating it as a live ownership map would be an implementation
bug; the specification's distinction is sound.

The work/deadline contract is also coherent. Every traversal is charged and
global exhaustion ends the search. A fully prepared candidate may consume the
last available publication unit and return if its final clock check is timely;
calling a work-availability predicate afterward and demanding a spare unit
would incorrectly reject that boundary case. A valid-looking child found during
an incomplete generation step is deliberately not publishable. Test that
interruption explicitly. Python container/deallocation costs remain cooperative
and measured; this is not a hard real-time guarantee.

## The two-swap witness is reachable as specified

The independent oracle uses source labels `L,A,B,C,D,R = 0,1,2,3,4,5`, physical
labels `q,a,l,b,c,d,r = 10,11,12,13,14,15,16`, and initial group `{A,B}`. Thus
`q` is A's first sorted site. Both possible individual deletions from A lose a
logical edge. After deleting q, only A–B is missing.

Full direct enumeration gives **four** complete first-state swap children. The
intended B/D swap ranks first. It changes the missing edge to D–R, leaving the
deficit count at one, and admits D. The D/C swap ranks first at the next state,
admits C and restores every contact. All chains are nonempty singletons after
the initial deletion; transfers therefore fail the donor nonempty requirement.
The desired route has depth two and does not depend on a fifth-ranked child.

Exhaustively checking all **720** singleton assignments over the six surviving
sites finds four valid full minors; exactly one preserves the frozen L/R sites,
the stated final assignment. Q falls from seven to six. These are arbitrary-target
toy facts, not native-Zephyr measurements, ordinary-refiner misses or a novelty
claim. Strict deficit descent or a visited key consisting only of deficit count
removes this particular route; the test does not assert that every such altered
search fails to find every other possible solution.

## Depth dominance and deliberate reach exclusions

For a fixed incumbent and deleted site, exact selected set plus exact ownership
partition determines the patch, all deficits, changed-site count, admissible
donors and ordered successors. No history-based taboo is present. Reaching this
same state at depth d permits every continuation that remains available at a
greater depth d′, since it has at least as many remaining operations. Retaining
minimum entered depth is therefore a sound structural dominance rule.

The independent abstract example reaches X first at depth three and later at
depth two. X requires six further edges to a goal. With limit eight, a
seen-once table fails, whereas minimum-depth revisits reach the goal at depth
eight. This is an abstract fixed-successor graph, not a claimed physical
realization. Global work/state caps still constrain the actual prefix explored;
dominance does not establish completeness or identical runtime under those caps.
Dominated encounters and admitted DFS entries should have distinct counters.

Connected-original-patch admission excludes a useful move even with unlimited
work. A second independently validated fixture uses target cycle
`a–q–b1–b2–b3–x–c3–c2–c1–a`, and source edges A–B, A–C, C–D. Entry chains are
`A:{a,q}, B:{b1,b2,b3}, C:{c1,c2,c3}, D:{x}`. Delete q and swap A's a with D's x:
all contacts return with one fewer occupied site. For initial group `{A}`, the
required original patch `{a,q,x}` is disconnected, so admission rejects it.
Including B in the initial group connects that same donor's original patch.
This demonstrates why group identity and admitted-set identity matter. It is
an explicit neighborhood exclusion, not a certificate error or evidence that
all allowed groups miss the move.

The other stated exclusions are also real: no free-site escape, no preparatory
move failing to restore the chosen edge, no temporarily disconnected chain, and
fixed patch/depth/top-four/state limits. Complete-generation ranking may consume
the allowance after discovering a potentially successful child. Increasing
limits after seeing a favorable instance would not establish the original
hypothesis and could repeat the cost/coverage failures in 023 and 039.

## Evidence and decision

The standard-library script is
[`check_toys.py`](../../results/codex/ownership-exchange-spec-review/check_toys.py).
`attempt001` passes; `attempt002` repeats the same three checks after adding
explicit spec-byte verification and a saved copy of the original spec. Their
three deterministic result JSON files are byte-identical. No failed toy assertion
or candidate execution occurred. The frozen attempt002 verifier SHA-256 is
`cafb8f5d34b3b72b97d017311937421a9a878a5023c9ce60fb85c6d180c688bc`, and its
summary SHA-256 is `c77985d5d29b8cbf2b54f1c9222f7e9b803385f17e9674ed57630f81ea7ca2fe`.

A bounded isolated prototype is scientifically justified on the reviewed batched
revision, to test whether this neighborhood exposes useful moves at acceptable
cost. It is not justified as a default algorithm or an across-class
improvement. Elementary swaps/transfers, temporary contact deficits and minimum
depth search are established techniques. The prototype needs independent
full-validity, exact-neighborhood and budget-prefix tests, followed only by a
separately authorized mechanism comparison. Stronger toy reach does not refute
the observed displacement and runtime risks from prior full-pipeline experiments.

Self-critique: I proposed the original hypothesis, which can bias this review
toward its intended witness. The explicit remote-swap exclusion, setup lower
bound and independent whole-assignment enumeration help expose limits, but these
tiny cases cannot estimate opportunity frequency or generation cost on the
development graphs. Those remain empirical questions; the original ACL gap does
not identify this mechanism as its cause.

The executed toy evidence remains bound to the **original** specification's
unchanged mathematical search rules. The revised batch API received static and
invariant reasoning review, not an implementation test. The three toys were not
rerun merely to attach a different spec hash, and no batch implementation exists
in this review's artifacts. A later implementation must test once-only setup,
ordered/duplicate groups, malformed/ineligible distinction, unvisited suffixes,
fresh per-occurrence tables and exact live-work accounting directly.

Safe repeat of the original-bound toy oracle in a fresh directory:

```sh
.venv/codex-native/bin/python -I -B \
  results/codex/ownership-exchange-spec-review/check_toys.py \
  results/codex/ownership-exchange-spec-review/root_repeat \
  --spec results/codex/ownership-exchange-spec-review/attempt002/reviewed_spec.md
```
