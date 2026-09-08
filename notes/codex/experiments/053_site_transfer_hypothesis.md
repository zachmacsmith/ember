# A053: one-site transfer during filled-core expansion

Design only, before implementation or candidate calls. Fixed ancestor: A050
`reduced_reinsertion_construction.py`, SHA256
`ef27c7483be80b4e168d4bf2a201afdffd9ff3baaac0df291d938c5f4334c112`.
A052 is rejected; neither its original-only requirements nor guidance/cache
policy enters this prototype.

**Hypothesis.** A physical chain already realizing an elimination fill contact
may contain a site that can represent the reinserted source vertex. Moving
ownership of that site can add a logical vertex at constant occupied Q, while
retaining the spatial structure provided by filled-core construction. This
could avoid paying for a new route and then pruning the old one. It is a
conventional local ownership transfer, with no novelty or general lifting
guarantee. The question is its measured usefulness before A050's ordinary
insertion and blocked repair, within one evolving construction.

## Exact proposed policy

Keep A050's anchors, elimination order, filled core, one native core call,
reverse journal, original deadline, 20M global scan allowance, ordinary
insertion and blocked repair unchanged. At each reverse row for unplaced `v`,
privately remove **only that row's `created_fill` edges** from requirement graph
`R`, producing `R'`. Let `S=R'[v]∩placed`; the journal guarantees `|S|≤3`.
Try one transfer query before ordinary insertion. This also permits rows with
empty `created_fill`: every surviving original or synthetic requirement must
still hold. If no required chain has at least two sites, skip the query.

The candidate pool comprises `(a,q)` for `a∈S`, `|C_a|≥2`, `q∈C_a`. Complete
pool construction and ordering before inspection; order by
`(|C_a|, source_rank(a), target_rank(q))` using the inherited fixed ranks.
Inspect the first **64** pairs, stopping at the first fully certified proposal.
Small donors precede large ones to limit connectivity-check cost; this is not
a claim that they give better later placements. Interrupted pool construction
does not expose a differently ordered prefix.

The only raw change is `C'_a=C_a−{q}`, `C'_v={q}`; every other chain stays
exactly equal. No site becomes free or newly occupied. No chain growth, second
transfer, swap, path search or additional release belongs to this query.
Reject unless the donor is nonempty and connected, `q` touches every chain in
`S` (including the remaining donor), all surviving donor contacts in `R'` hold,
and all placed-chain future-port guards hold after inserting `v`. Future
demands use the **whole current `R'`**, including pending synthetic journal
edges, not just the original source or this row's neighbor list.

For a cheap local check, build the current owner map/free set once per query.
Count pending demands after adding `v`. Since occupancy is unchanged, all
unchanged chains retain their free boundaries; only donor and new-vertex
boundaries need recomputation. An old chain with no free port and a remaining
pending demand already rules out this transfer-only query: shrinking a donor
cannot create a free boundary. Do not assume entry frontier guards passed;
the native core admission establishes a minor, and can lack future ports.
Inspect donor connectivity and remaining contact owners in one traversal of
its induced target subgraph, scanning original target adjacency. The first
locally admissible trial receives the existing `engine.valid(complete=False)`
gate against `R'`, exact key/ownership/Q checks, and the full future-port gate.
A disagreement is an internal error, not a reason to silently try another
route. No replacement validator framework is proposed.

```text
for row in reversed(journal):
    R' = private removal of exactly row.created_fill from R
    trial = first certified one-site transfer(v, entry, R')
    if transfer exhausted its local allowance or returned no proposal:
        trial = unchanged A050 ordinary insertion(v, entry, R')
        if ordinary returned None: use unchanged A050 blocked repair
    if no trial, or global work/deadline interrupts: retain entry and R
    if transfer/ordinary succeeded:
        apply inherited cleanup only to endpoints of row.created_fill
    if repair succeeded: retain its existing frozen-owner cleanup rule
    check original deadline; atomically adopt trial and R'
validate the completed embedding against the original source and target
```

The transfer query gets at most **50,000 scans per row** and **1,000,000 scans
over the constructor**, both consumed inside the live 20M allowance. A local
limit disables the remainder of that query, with ordinary A050 work still
allowed if global work/time remains. Cumulative exhaustion skips later transfer
queries. Global exhaustion or the absolute deadline ends construction without
renewal; no ordinary retry follows either event. Existing 1M/query and 5M total
repair allowances stay separate overlapping subtotals of the same global work.

Charge each source-neighbor/target-neighbor examination, copied or enumerated
chain site, pool key/comparison, owner-map entry and certificate traversal to
the transfer allowance and global counter. Check time during setup, candidate
inspection, copying, full certification and immediately before publication.
All sorting/allocation wall is included. For pool size `P≤sum_{a∈S}|C_a|`,
setup is `O(QΔ + |R| + P log P)` and each donor check is `O(|C_a|Δ+|R'[a]|)`;
at most one completed full gate adds `O(QΔ+|R|)`. Actual scans, not these bounds,
determine truncation. Large Python allocations/sorts remain cooperatively
timed, not preemptible; preserve the existing outer return-time gate.

No entry set is mutated. Completed raw transfer has ΔQ=0; inherited subsequent
fill-endpoint cleanup can lower Q and change those endpoints, so save its
separate pruning count and final committed ΔQ. That cleanup retains its A050
global/deadline accounting, outside the transfer subtotal. If it interrupts,
do not adopt either transfer or `R'`. Save row/seed identities, full pool size,
inspected prefix, rejection counts, query/global limits, work/wall, donor/site,
raw certificate, actual commit, and before/raw/after Q. Failed attempts and
certified-but-uncommitted proposals remain visible. With no accepted transfer
and nonbinding limits, ordinary/repair choices must reproduce A050 exactly;
the added work/time still can change binding outcomes.

## Fixed correctness witnesses and cheap reach experiment

Use ordinary integer labels, explicit original edges, and independently
validate the entry against the preceding filled requirements and the result
against `R'`. Every positive must have unchanged occupied sites and ΔQ=0.

1. **Subdivided edge:** target path `0–1–2`, entry `a:{0,1}, b:{2}`.
   Original edges are `a–v, v–b`; this row created `a–b`. Transferring site1
   gives `a:{0}, v:{1}, b:{2}`. There are no remaining pending demands.
2. **Degree-three center:** entry `a:{0,1}, b:{2}, c:{3}`; target edges
   `0–1, 1–2, 1–3, 2–3`. Original edges are `v–a, v–b, v–c`; the row created
   the triangle on `a,b,c`. Transferring1 realizes the original star at Q4.
   The extra physical edge2–3 is harmless. A literal target claw cannot
   realize the preceding filled triangle and is not a valid entry witness.
3. **Required-contact rejection:** add original `a–b` to witness1; its fill
   list is empty. Site1 cannot move because it supplies the sole retained
   `a–b` contact. Also test an older synthetic `a–b` created while eliminating
   an earlier vertex `z` from original edges `z–a,z–b,v–a,v–b`: reversing `v`
   does not release it. Add free leaves as needed to satisfy pending guards.
4. **Articulation rejection:** donor `{0,1,2}`, other chain `{3}`, target edges
   `0–1,1–2,1–3`. Only site1 can touch the other chain, but removing it splits
   the donor. No transfer is admissible.
5. **Frontier rejection:** with witness1's entry, add free site3 adjacent only
   to1 and an unplaced requirement `a–z`. Moving1 strands the donor despite
   valid current contacts. Separately, use target `0–1–2` plus free leaves
   `0–3,2–4`, and pending `v–z`: moving1 strands the new vertex. A current minor
   alone never overrides either guard.

Add one bounded interruption/rollback case, one prefix-cap case, and one
no-transfer A050-equivalence fixture. Do not expand into a general enumeration.
If these pass, the proposed reach diagnostic is exactly the four already
frozen small inputs: star128, wheel128, subdivided K5 and cycle126. Run fixed
A050 then A053 once per input, fresh isolated processes, seed0 and a common
20-second allowance, unchanged 20M work. This is eight calls, with independent
original-graph final/prefix checks and all outcomes retained; no MM calls.
Record final Q, transfer attempts/commits, all work/time, repair reach and costs.
Any invalid output or basic reach failure stops this prototype before 34
inputs. If none of the three non-star cases improves final Q, defer a broad
screen; any regression requires explicit parent review. No cap/order changes
or substituted witnesses after outcomes. These calls require root approval;
this note implements and runs nothing.

**Self-critique.** A chain contact witness need not contain a transferable site.
One site may not touch all required neighbors, can be an articulation, or can
carry an original/older synthetic obligation that must remain. A constant-Q
step can still leave a worse future placement. Future-port preservation is
necessary but far from sufficient for later routing. Testing only 64 sites
and reserving 5% of global work for this query can miss useful transfers or
reduce ordinary reach. Repeated full setup/gates can consume more than the
saved routing work. Filled-core excess outside transferable neighborhoods
remains. The fixed diagnostic can reject this narrow mechanism; it cannot
establish superiority across graph classes, novelty, or a general lifting
theorem.

**Parent review requested before code:** the 64-site order, 50k/1M allowances,
full-guard admission and inherited post-transfer cleanup, plus the fixed
eight-call reach comparison. Integration is a separate isolated constructor
copied from A050; no current native, pilot, or frozen source changes.
