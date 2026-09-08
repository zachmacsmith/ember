# Joint path reconstruction after lifting — proposal only

2026-09-08. Retain fixed A053. The packed-orientation gate is incomplete:
packing choices differed, but it produced no physical-Q comparison and cubic
setup exhausted its allowance. Its failed publication attempt and amended
repeat remain preserved; no further gate repeat, allowance change or geometry
candidate is proposed here.

**Hypothesis.** Some remaining short-chain overhead is trapped in the ownership
boundaries of an already usable physical route. Reassigning several consecutive
logical vertices together, while shortening that route through existing target
edges, may remove this overhead. Test one bounded constructive path operator
after A053 has completed its original-valid lift. This changes neither reduction
eligibility nor the native core, and cannot rescue an incomplete construction.
No implementation or new candidate call has occurred.

## What the existing evidence distinguishes

* **Representation capacity:** the exposed cycle has a saved original-valid
  Q126 embedding. A053 returns Q148, so the target and minor representation can
  achieve the lower value. This does not put that embedding inside the current
  occupied sites, the proposed route, or any fixed local neighborhood. The
  retained-core/lifting excess table is a decomposition, not causal evidence.
* **Placement and neighborhood:** literal A051 discarded synthetic physical
  requirements. Its cycle made 41 insertion attempts with no placed original
  neighbor, then stopped at 20M scans with 119 vertices/Q266 partial. That is
  consistent with losing spatial guidance, but unsaved intermediate positions
  prevent a route-level causal claim. Fixed A053 instead retains fill, and its
  ordinary B003/B004 primitive selects four roots from a 64-root shortlist,
  one weighted shortest connector at a time, and one connected ownership cut
  for that connector. It does not jointly revise a long sequence of prior
  owner boundaries.
* **Acceptance:** the saved A053 cycle has 125 transfer queries: 18 certified
  transfers, all committed at raw ΔQ0; the other 107 report no eligible donor.
  Its 107 ordinary insertions add 147 sites to the one-site core. Their saved
  ΔQ histogram is 81×1, 20×2, 5×4 and 1×6. Final chain sizes are
  115×1, 6×2, 1×3, 3×4 and 1×6. Thus refusal of neutral transfers does not
  explain this example. A053's transfer needs one site of a required chain of
  size at least two; it cannot relocate several singleton owners together.
  Blocked repair runs zero times because an ordinary proposal remains feasible.
* **Cost:** this cycle consumes 3,008,706/20M scans, including 116,876 transfer
  scans, and completes in 1.946s in the saved053 call. Its global allowance did
  not bind. A051's work exhaustion is different evidence and is not remedied
  merely by noting A053's spare allowance.

Simply invoking old reinsertion on expensive feasible steps is not the selected
proposal. B004 already tried that schedule: 116 queries, 100 complete proposals,
20 commits, six inputs exhausting the 5M repair allowance, and three final-Q
regressions despite a large bipartite gain. This is negative evidence against
using immediate insertion cost as a sufficient scheduling/acceptance signal.
The proposed operation instead changes many owner boundaries simultaneously on
one route, after all original obligations are present. It uses no neutral or
invalid intermediate *commits*.

## Fixed constructive policy proposed for review

Run fixed A053 once under the original deadline. Only a complete original-valid
result enters the new stage. Keep a private working minor; unchanged A053 is the
control, not an alternative output selected by an input-specific rule. The
original source adjacency is the only physical requirement at this stage.
All fill has already been removed and there are no pending vertices.

Use source/target input-order ranks for every tie, without a new RNG. At stage
entry take the first eight nonsingleton source owners ranked by decreasing
chain length then source rank. From each seed grow one induced logical path at
either end. An extension must be adjacent to that end and to no other vertex
already in the path. Prefer decreasing stage-entry chain length, then source
rank, then end index. Stop at 128 owners or no extension; keep paths of at least
two owners and deduplicate reversal-equivalent paths. Do not refill the eight
seed slots after skips. This selects the same structural motif in any graph;
there is no cycle, lattice or family dispatch. In a chordless cycle this rule
can select all but one owner, with the excluded owner supplying both boundary
contacts. On graphs with chords it often produces much shorter paths.

For each selected path, freeze every outside chain and extract **one** simple
physical witness in logical-path order. Choose the first ranked actual coupler
between each consecutive pair of chains. Inside each chain use deterministic
BFS to join its incoming and outgoing endpoints. For the first/last chain,
use a first ranked site touching its first ranked outside neighbor as the outer
endpoint, or its first ranked site when there is no outside neighbor. Disjoint
entry chains make the concatenated route simple. Abort this path if its route
exceeds 512 sites. Branch sites omitted from this witness are not silently
retained: every selected owner must ultimately meet its outside obligations
using its proposed route segment, or the proposal fails.

The route positions retain their physical order. A forward target edge between
nonconsecutive positions is a chord shortcut: removing the strictly intervening
positions preserves a simple physical route. Enumerate the complete current
chord list, rank by most removed positions then endpoint indices, and inspect a
bounded prefix. Skip a shortcut leaving fewer sites than selected owners.
Include the unshortened witness as the first candidate, to expose any removable
off-route material. Across this path, inspect at most 32 candidate routes,
including rejected candidates and that first witness. A successful shortcut
does not renew the limit; rebuild its chord list on the shortened route.

For each candidate route, assign owners in logical order to consecutive,
nonempty segments. Greedily end the current segment at the first position whose
sites touch **every distinct outside logical neighbor** of that owner, while
leaving at least one route site per remaining owner. The last segment may end
once its obligations are met; unused suffix sites are released. Failure to
finish all owners rejects this route. No alternate cut search, mask-state
optimizer or shortest-path optimality claim is part of this heuristic.

```text
E = the one successful fixed-A053 output
freeze seed/path ordering from E
for each bounded induced source path:
    extract one current physical witness; freeze all outside chains
    try its witness and bounded forward-chord shortcuts
    greedily partition each proposed route among the path's owners
    check every original contact, coverage, connectivity and disjointness
    if timely and strict total Q decreases:
        privately adopt the complete replacement and continue on this route
return the last complete certified minor through the original final/time gate
```

At most eight paths, 128 owners/path, 512 route sites and 32 route attempts/path
are fixed first-prototype bounds, not evidence-based tuning. Propose a stage
deadline `min(original_D, stage_start + min(1s, 0.2 * elapsed_A053))` and one
shared 1M site/edge-visit allowance for its setup, extraction, generation,
copies, assignment and certificates. These new work units are not equated to
B003 routing scans; fixed A053's 20M limit remains unchanged. Wall time charges
all administration, sorting and failed work. No renewal per path or commit.
Interrupted list generation/assignment publishes no partial proposal. A stage
stop retains the last fully certified mapping; an actual return past the
original deadline remains late and receives no timely credit. Reuse the
existing original-graph validator, not a new validation framework. Record
setup, routing, assignment and validation costs separately, including failures.

Exact side-contact checking is a soundness condition, not neighborhood
optimization. A nonempty contiguous segment is connected; route positions are
unique and drawn only from released selected chains, so ownership is disjoint
from the frozen outside. Consecutive segments realize logical-path edges.
Induced-path selection rules out missing internal chords, and the side-contact
check covers every remaining incident source edge in both directions. Outside
edges remain unchanged. The independent whole-minor gate checks these facts
again before admission. Merely finding a physical path is insufficient.

## Hand checks and one cheap discriminator, if authorized

A contact-essential toy makes the distinction concrete. Let source path
`a-b-c` also require `b-x` and `c-y`. The target has path `0-1-2-3`, plus edges
`0-2`, `1-4`, `2-4`, `3-5`. Start with `a:{0}, b:{1}, c:{2,3}, x:{4}, y:{5}`.
Neither site of `c` is individually deletable: each supplies a different
required contact. The shortcut route `[0,2,3]` jointly yields
`a:{0}, b:{2}, c:{3}` with frozen x/y and Q6→5. Removing target edge `2-4`
makes this particular shortcut inadmissible; b's side contact cannot be waived.
A cycle with one two-site chain and a chord bypassing another singleton owner
is a second hand-checkable owner-shift witness. Neither toy establishes extra
reach versus all existing ordinary/group or vacancy moves.

After tiny tests for these witnesses, side-contact rejection, skipped branching
contacts, entry immutability and interrupted publication, propose one saved-final
gate on the same six fixed A053 inputs: cycle1829, cubic33219, kagome32122,
grid1584, planted34404 and Petersen4083. Use their already saved valid finals;
no new snapshots or native reruns. Each has one fresh bounded stage, with its
allowance computed from that record's saved A053 solver wall and the rule above,
plus a five-second process watchdog. Freeze exact records and runner first.
Retain all six outcomes and distinguish route-extraction/side-contact failure,
greedy-allocation failure, no strict-Q shortcut, work/deadline stop and success.
Setup is included; no warm retry or enlarged allowance follows a cost stop.

Advance only if the fixed gate completes on all six and improves the cycle plus
at least one of the other five, with independently valid timely outputs. Zero
complete gains rejects this fixed heuristic; interrupted coverage is cost/unknown
and does not pass. Gains on a route show constructive reach, not minimum Q.
An optional tiny exact route/partition oracle could distinguish greedy failure
from no feasible assignment *inside that route*, but is not required for the
candidate or an automatic next diagnostic. No exact global/subproblem solver
belongs in production.

A passing gate should lead directly, after root review, to twelve fresh paired
complete A053/A053-plus-path calls on those six source inputs at the existing
60-second deadline. Preserve all failures, regressions, Q/ACL and same-host
times; a saved-entry gain does not guarantee a better fresh full construction.
No improvement in complete output rejects integration even if local shortcuts
exist. A >10× time regression rejects cheapness and requires an accounting
explanation, not more allowance. Neither this comparison nor the toy would
establish superiority to a newly scheduled ordinary post-lift repair stage.

## Self-critique and limit of the claim

The strongest restriction is representational: this prototype uses only one
ordered route through currently occupied sites. It cannot discover the known
Q126 cycle embedding if reaching it needs free sites, a different route order,
or different frozen endpoints. Side contacts may require a branched chain that
cannot fit a segment of the chosen route. Even when a feasible segmentation
exists, the greedy earliest cut can consume a site uniquely needed by a later
owner. Forward shortcuts, long-path selection and immediate strict-Q adoption
can miss a better subsequent route. The proposal claims none of these searches
are complete. A zero result does not prove compact embeddings unavailable or
neutral-intermediate acceptance necessary.

This is a conventional rerouting/ownership-reassignment idea, not a novelty
claim. Its unproved contribution boundary is useful, inexpensive *joint*
owner reassignment beyond A053's one-site lifting transition on some current
short-chain deficits. B004's negative schedule remains a warning that a useful
local witness and lower immediate Q need not improve a full constructor. No
reduction revision, MM/busclique call, cache, portfolio, source edit, registry
entry or new run is authorized by this note.

Evidence inspected: A051 implementation note SHA `5b18e77d…`; B004 design/results
`d08aebf1…`; A053 wrapper `801432d5…`, transfer `c61b2479…`, blocked helper
`ff0edb1e…`, pinned path primitive `f29cdef9…`; saved053 cycle result
`704dad35ee06509f76ca4079.json`, SHA
`1fd2d4891f039f27931afb3946caae9d7e89c270759e04a5695e809d6abe5077`.
The prior-art overlap is documented in `ownership_exchange_prior_art.md`.

## Authorized gate clarification, before implementation and outcomes

Root approved the bounded operator, its specified tiny checks and one fixed
six-saved-final gate. The original proposal bytes are preserved under
`results/codex/joint-path-gate/precode/original_proposal.md`. This paragraph
supersedes the gate's earlier treatment of every interrupted search as missing
evidence: **a declared work/route-budget stop is a measured finite-heuristic
outcome when the last fully certified mapping returns valid and timely.**
Unvisited routes remain unknown. Discard the incomplete proposal; do not discard
earlier certified output or describe ordinary budget exhaustion as a lost result.
Lost output, late return and an interrupted certificate are separately reported.
Advancement requires timely independently valid returned maps on all six,
cycle plus one other improvement, and complete work accounting. No extra
allowance, retry, registry entry or complete-constructor screen is authorized.

The isolated API accepts the unchanged authoritative structural-validator
function as an explicit dependency. Metered read-only graph/chain views charge
its visited sites/edges without replacing its validation logic. Entry is a
supplied valid complete minor; a pre-copy/pre-validation stop may return the
untouched entry by alias with `input_validated=False`, never a partial copy.
After copying, only whole certified private maps can replace it. The gate also
uses the separate saved-record original-graph oracle on every returned map.
