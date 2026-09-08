# Induced-star integration: bounded design review

2026-09-08. Design only: no source edits or new solver experiments. The
[mathematical review](induced_star_relocation_review.md) supplies the certificate,
prior-art attribution, and fixed witness. This note proposes one concrete
integration for an initial ablation; its numerical work allowance is a
prespecified engineering choice, not a tuned or proven optimum.

**Recommendation:** attach one star proposal to a failed ordinary group visit,
after ordinary reconstruction has used its original allowance. Share the
remaining visit and global budgets, add no group visit, and leave direct
singleton relocation disabled. Use a small, lazy owner-only cache and discard
all block-domain state after each proposal. Include stars with two or more
leaves and allow more than four selected vertices.

## Current API and scheduler constraints

The inspected source hashes are:

| Module | SHA-256 |
| --- | --- |
| `contact_repair.py` | `804edfaaf9cdefe33249ffea9db1d752cd79c0e0b8a2a0d2bcd9478e0c483c57` |
| `contact_groups.py` | `43574f6f13eb33d790de535e4e614533d0f1df7f50d129932301b7832e1301bd` |
| `singleton_relocation.py` | `bd3b6f7b32490c00a3843dd400c4998a96dd0f4fef5a02cebe06d8a94f90b424` |

`contact_polish` generates an ordinary list once per pass. Both group generators
exclude blocks with no positive excess over individual degree bounds at that
time; an earlier accepted move can change their current excess. The round-robin
generator emits enabled singletons first, followed by groups from contiguous
windows of ranked logical neighbors and physical blockers. Lists are not rebuilt
after every accepted move.

`_repair` creates its own `_Budget`, returns aggregate work, and preserves the
incumbent when no proposal is accepted. Its region starts with the selected old
qubits, adds a free two-hop halo, and optionally adds boundary sites. The default
region cap is 512. Its returned diagnostics do not expose a reusable ownership
map. `repair_group` and `group_sizes` are restricted to one through four vertices;
the new operation should have a separate internal entry point, not relax those
contracts or send larger groups into generic reconstruction.

The current fixed candidate uses 512 total groups, 500,000 counted expansions,
50,000 expansions per group, four passes, beam width one, three alternatives,
two orders, 16 boundary sites, greedy trees, and `qubits_contacts`. The existing
direct-singleton path has a five-percent auxiliary allowance, cache maintenance,
and inserted visits. Those inserted visits and equal-size trajectories matter
to the failed 033 result; do not enable that path as a prerequisite for stars.

## Scheduling without added group visits

Use a separately named optional star policy; the off path must preserve current
execution and diagnostics. For the first comparison, reject its combination
with `singleton_policy='direct'` rather than silently selecting precedence.
When the star policy is enabled, enforce the simple, undirected, loopless source
and target precondition explicitly at entry; the present guard only runs for
the direct-singleton policy. Reuse the existing validated incumbent and fixed
adjacency context without weakening the original structural validator.

For every ordinary group, in the existing order:

1. Give `_repair` its unchanged `min(group_expansions, global_remaining)` limit.
2. Count this ordinary group exactly once. If it accepts a move, retain that
   result and refresh an already-built star owner cache using remaining work in
   this same visit. Do not also try a star.
3. If it accepts nothing, consider its first vertex as the star center, at most
   once per center per pass. Selection uses the current incumbent, not the
   pass-start chain lengths. Do not introduce a center queue or another sweep.
4. If selection produces an eligible positive-excess star, attempt its matching
   replacement within the remaining active visit, global, and auxiliary limits.
5. On a fully certified strict reduction, commit that single replacement and
   refresh the cache. Otherwise leave the incumbent unchanged and continue with
   the next ordinary group.

A star acceptance sets the existing pass `changed` flag and contributes once to
total accepted moves, qubits saved, and the trajectory. Add its work to the active
visit exactly once; do not count it again when aggregating the star-specific
diagnostics. The visit's complete work, including any refresh after an ordinary
acceptance, must stay within the limit originally supplied for that visit.

Record a center as considered before the bounded selection scan, so repeated
groups cannot repeatedly pay for the same unsuccessful selection in that pass.
This deliberately skips reconsidering a center whose neighbors change later in
the same pass. A later pass may reconsider it.

An accepted equal-Q redundancy move from ordinary reconstruction counts as
acceptance and suppresses the attached star attempt. Changing that rule would
change the experiment: a star search after every accepted move would be a
different scheduling hypothesis.

There are no added zero-excess visits and no increment to `groups_tried` for the
attached operation. This preserves the ordinary sequence until state changes,
but **does not guarantee unchanged ordinary coverage**: extra work can reach
the global limit earlier, and accepted star moves can change future pass lists.
Report those effects rather than describing the attachment as free work.

## Fixed structural block rule

Let `Delta` be the actual maximum target degree. Use the already stable logical
order in `ctx.nodes` solely to break structural ties.

- Reject a center whose logical degree is below two or above `Delta`.
- List its logical neighbors whose own logical degree is at most `Delta`.
  Rank them by decreasing `len(chain)-1`, then increasing logical degree, then
  stable logical rank. This prioritizes qubits that could be removed and uses
  lower degree as a cheap proxy for fewer external obligations.
- Traverse this list once. Keep a neighbor exactly when it has no source edge
  to any already retained leaf. Do not enumerate independent sets or alternate
  subsets. Keep every compatible candidate; there are at most `Delta` leaves.
- Require at least two retained leaves and positive current
  `sum(len(chain)-1)` over the center and leaves. Explicitly verify the induced
  star condition before constructing a physical proposal.

This permits 3 through `Delta+1` selected vertices, including blocks larger than
four. On ideal Z12, `Delta=20`, so the largest permitted block has 21 vertices.
Singleton centers or leaves are allowed if another selected chain contributes
a strict reduction. Rejecting all singleton centers would miss legitimate
coupling opportunities; accepting an all-singleton block would recreate a
zero-excess search that this design deliberately avoids.

The greedy subset is not optimal or complete. One early leaf can exclude several
others, and adding a leaf can destroy a feasible smaller placement. No result
from this one subset certifies failure of other stars around the center. The
initial recommendation to require four leaves was too restrictive: the fixed
three-vertex witness already exposes a bounded generic-search miss, and sparse
degree-two/three centers remain relevant. Report block-size strata instead of
excluding them or changing the policy by graph family.

## Domain evaluation and safe root generation

For the fixed selected set, precompute each member's frozen logical neighbor
set `F[v]`. Define a physical site as available exactly when the owner cache
maps it to no source vertex or to a selected vertex. A site is eligible for `v`
when it is available, has sufficient physical degree, and its adjacent owners
include every member of `F[v]`. Selected old owners must not count as frozen
contacts.

Compute adjacent frozen owners lazily per physical site and cache them only
inside this immutable block query. From that set, cache a bit mask of eligible
selected vertices. This avoids building full boundary intersections for every
selected member or repeating the same physical adjacency scan for many roots.
The mask has at most 21 bits on Z12. Construct a root's leaf domains by walking
its actual target neighbors and reading these eligibility masks.

Use a complete, deterministic root superset with the following single rule:

1. For each frozen neighbor chain of the center, its open target neighborhood is
   a necessary root superset. Assign it estimated enumeration cost
   `Delta * chain_length`.
2. For each frozen neighbor chain of a retained leaf, its two-hop neighborhood
   is a necessary root superset. Assign it cost `Delta**2 * chain_length`.
3. Choose the minimum estimate, breaking ties by hop count, selected-vertex
   rank, and frozen-neighbor rank. Enumerate that chain in target-rank order,
   then use the existing target-rank adjacency order. Deduplicate roots on first
   discovery. For two-hop enumeration, safely discard intermediate sites that
   fail that particular leaf's complete eligibility test.
4. If the entire block has no frozen neighbor, enumerate `ctx.rank` order over
   the target. Never interpret missing frozen obligations as an empty domain.

The cost estimate bounds walk enumeration before deduplication; it does not
predict exact work or feasibility. The root superset may omit the old region
because the proposed search is not confined to generic reconstruction's halo.
Filter every emitted root against the center's complete domain before matching.
This rule needs neither coordinates, a distance BFS, source family metadata,
nor outcome-dependent root selection. Its rank tie breaks can still bias early
truncated search and should not be called isomorphism invariant.

For each root, reject an empty leaf domain or a union smaller than the leaf
count. Then find one covering matching by ordinary augmenting paths. Process
leaves by increasing current domain size, tie by logical rank, and candidate
physical sites by target rank. Do not optimize redundancy or enumerate multiple
matchings: every complete selected placement uses the same number of qubits.
Stop on the first fully certified strict reduction. This is the conventional
LAD-style reduction discussed in the prior-art review, with frozen-chain domains.

## Owner cache: reuse the discipline, not unused singleton state

Prefer a dedicated small cache containing only `owner`, the exact incumbent
object, and a validity flag. Reuse or factor the auxiliary-budget adapter's
semantics if convenient, but do not invoke `SingletonSearch` or disguise empty
queue/volume fields as a valid `SingletonCache`.

`SingletonSearch` bundles singleton scan policy, an extra-visit queue, chain
volumes, ordered chains, setup flags, and singleton-specific diagnostics. The
new block query needs none of its queue or volume state, and its per-block
eligibility changes when the selected set changes. Reusing the whole object
would add construction and maintenance work and make invariants harder to
state. A shared neutral owner-cache utility could be reasonable later; it is
not required to validate this isolated hypothesis.

Build ownership lazily only after a block passes structural and excess checks.
The owner cache is reusable only when its incumbent identity matches the current
mapping and that mapping and its chain lists have remained immutable. Current
`_repair` creates a new mapping and new selected chain lists on acceptance;
that supports this contract, but must remain an explicit internal invariant.

Refresh after **every** accepted ordinary or star move, not merely after star
moves. Mark the cache invalid first, remove every old selected owner, then add
all new selected owners, and publish the new incumbent identity only after the
update completes. This order handles ownership transfer between selected chains.
Any insufficient work, deadline, or unexpected stale identity discards the cache
and disables star search for the remainder of this polish call. Keep an already
accepted valid embedding. Do not retry rebuilding repeatedly under a dwindling
budget. Query-local eligibility masks never survive a committed move.

## Work bounds, deadlines, and incomplete results

Proposed initial limits: the existing per-group and global limits remain
unchanged; all star setup, scans, scoring, and maintenance share an auxiliary
cap `floor(max_expansions/20)`. Cap each attached query's selection/domain/root/
matching/certificate work at 2,048 new work units, in addition to the one-time
owner build and subsequent owner maintenance. Setup and maintenance still
consume this same visit's remaining work and the auxiliary cap. This separation
lets an owner build larger than 2,048 units complete without granting unbounded
query work. These fixed limits must be recorded before the ablation, not tuned
against its output.

One new unit covers one source/chain record, occupied physical vertex, physical
adjacency scan, selected-vertex eligibility check, or examined matching edge,
as applicable. Charge repeated matching-edge examinations, duplicate walk
processing, rejected roots, and all incomplete work. A physical adjacency scan
does at most `Delta` neighbor operations; an eligibility test checks at most
`Delta` required frozen neighbors. Sorting and allocation also have explicit
finite bounds and measured time: do not claim that a count of these units equals
machine instructions. Existing generic counters already omit work such as full
validity checks and some sorting, so end-to-end timing remains necessary.

With `N=|V_target|`, `Q` occupied qubits, `n=|V_source|`, `k` retained leaves,
and `s=k+1` selected vertices, the untruncated bounds are:

| Operation | Bound before the shared limits truncate it |
| --- | --- |
| Owner build | `n+Q` charged records; `O(Q)` owner entries; `Q<=N` |
| One cache refresh | old plus new selected qubits, with constant per-selected metadata; at most `2N+O(s)` |
| Leaf selection | at most `Delta` candidates, `O(Delta log Delta)` sorting and `O(Delta**3)` tuple-membership work; small local adjacency sets reduce this to `O(Delta**2)` after construction |
| Frozen obligations | at most `s*Delta` source-neighbor records |
| Root walk generation | at most `|seed_chain|*Delta**h`, `h` one or two, or `N` target sites without a seed; deduplication uses `O(N)` memory |
| Query-local eligibility | at most `N` site adjacency scans and `s*N` eligibility checks; `O(N*Delta*s)` elementary membership work |
| Matching at one root | at most `k*Delta` edges; simple augmenting paths inspect `O(k**2*Delta)` edges |
| All roots, absent truncation | at most `N` distinct roots; matching bound `O(N*k**2*Delta)` |

On Z12, `N=4,800`, `Delta=20`, and `k<=20`. The full-root bound is intentionally
too expensive to promise; the shared auxiliary and per-query limits make this
a bounded heuristic. Deduplication, eligibility-mask creation, and all loops
must check those limits before the corresponding work, rather than charging
after the fact. Deadline checks occur within root generation and augmenting
paths, not only between roots.

A failed or truncated root is not a proof that the block has no replacement.
Report `exhaustive_no_match` only after exhausting the complete generated root
superset and every necessary matching test without any cap. Otherwise return
`truncated` with its limiting counter and unchanged incumbent. A complete
matching is provisional until all membership, distinctness, frozen-contact,
and source-star certificate checks finish and the deadline permits commit.

Compute exact old/new logical-edge redundancy for the accepted group before
commit if the existing trajectory schema requires the delta. Use an ownership
overlay for new singleton sites and ignore released old owners. Charge that
work; if the required score/certificate cannot finish, do not publish a partially
scored move. After commit, incomplete cache maintenance disables further star
search but does not revoke the accepted embedding. This differs from rejecting
an incomplete proposal and must have separate diagnostics.

## Necessary diagnostics, tests, and remaining risks

Keep ordinary accepted-move diagnostics unchanged. Add star considerations,
selection rejections, query attempts, owner setup/refresh work, query work by
stage, roots generated/eligible/matched, matching edges inspected, truncation
reasons, accepted qubit reductions, redundancy deltas, and cache-disable reason.
Record actual selected vertices and block size in accepted trajectories. Report
size strata 3–4, 5–8, and 9–21 diagnostically, never as runtime policies.

The immediate acceptance invariant is strict total-Q decrease. Equal-size star
relocations are excluded even when ordinary `qubits_contacts` permits them.
Validate exhaustive tiny matching cases against direct injective assignments,
including leaf conflicts, frozen occupancy, empty obligations, and label-type
collisions. Test interruptions during setup, matching, scoring, and ownership
transfer, plus an accepted ordinary move followed by a star query. Require the
off policy to replay current results exactly. These are proposed tests, not tests
run for this design note.

The main remaining limitation is coverage: failed ordinary groups often consume
their whole allowance, leaving no star search; successful equal-Q moves suppress
it; the first group vertex need not be the most useful center; and one greedy
leaf subset may be too restrictive. Conversely, relaxing each restriction can
recreate the added-cost problem observed in 033. Start with this bounded,
auditable rule, compare cumulative results from the same saved incumbents, and
retain the old policy unless gains survive all setup and displaced-work costs.
