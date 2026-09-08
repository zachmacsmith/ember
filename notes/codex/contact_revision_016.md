# Contact reconstruction revision 016: sites and group coverage

Design and self-critique recorded before implementation. The current fixed
reference is geometric search followed by width-one joint reconstruction, chosen
globally from experiment 011. It remains worse than MM on six sparse development
inputs. A width-four beam used more work and was slightly worse overall; merely
widening it is not the next intervention.

## Candidate change A: include complete boundary-contact sites

For a selected logical vertex, intersect the physical neighbor sets of its frozen
logical neighbors' chains, then remove qubits occupied by frozen chains. Every
remaining site satisfies all those external contacts with a singleton chain.
Internal contacts to other selected vertices still need reconstruction and full
validation. Include a bounded number of these sites in the selected physical
region, in addition to the existing free-space halo and all released old qubits.

Keep the original region intact. Add sites only while room remains under the same
region cap, round-robin across selected vertices. Prioritize contact with old
selected-neighbor chains, then available physical degree, then deterministic
target rank. No source-family labels or stored answers enter the algorithm.
An isolated selected vertex with no frozen contacts does not nominate the entire
target. Budget checks cover the boundary scans and deadline; all work is recorded.

Evidence: experiment 013 found two ER chains with validated singleton alternatives
outside their default regions. All three sites are at free-space distance three;
they do not demonstrate disconnected relocation. The two logical vertices are
adjacent, so their independent gains cannot be summed without joint revalidation.

Self-critique: boundary intersections are standard contact-set operations, not a
novelty claim. They may be empty for longer required chains and may add nothing
when the old region fills its cap. A larger region can worsen bounded search by
changing root ordering. Finite site selection has no completeness guarantee.
The specific ER opportunity is a mechanism test, not justification for ER-only
behavior. Falsifier: no reproducible benefit beyond ordinary halo enlargement at
matched limits, or overhead exceeds saved routing work on broader development data.

## Candidate change B: expose alternative neighboring groups

The existing selector uses only the first highest-cost neighbor of each center
for its pair proposal. Even without a group cap, this leaves many logical or
physical adjacent pairs unexamined. Generate candidate groups in rounds instead:
start with singleton groups, then expose each center's first neighboring window,
then its next window, retaining strict deduplication and the existing total group
and routing-work limits. The proposal list remains deterministic and uses only
current chain cost, source adjacency, and physical occupancy. Within a round,
visit every eligible center before returning to a previous center's next size.

Evidence: fixed-incumbent diagnostics found omitted bipartite and Watts–Strogatz
pairs with real coordinated reductions beyond their declared singleton controls.
These independent gains also must not be summed as if they form one embedding.

Self-critique: broader coverage is not automatically better prioritization. It may
spend budget on weak pairs or delay useful larger groups. The chosen group window
does not enumerate every subset of neighbors. A pass still sees a snapshot of
group proposals, though every move uses current chains and is atomically validated.
This is a scheduling change within one search, not a new constructor or a portfolio.
Falsifier: gains disappear under equal routing-work limits or fail to generalize
to unseen development structures and sizes.

## Controlled experiment

First replay width-one contact reconstruction on all 18 saved, valid native-search
incumbents from experiment 011 and check it reproduces the corresponding fixed
joint-one outputs. No MM embedding is an input. Then compare four fixed policies:
reference, sites only, group coverage only, both. Every policy has identical group,
region and routing-work caps. Record all accepted moves, validity, actual work and
repair wall time. Do not claim end-to-end speed from this refinement-only diagnostic.

If a globally fixed revision is promising, run it end-to-end with MM on a balanced
readiness subset of the actual Ember corpus. Keep all failures and ties, and do
not select a policy separately for each graph. Neither this development ablation
nor the existing nine-input screen establishes all-family superiority or novelty.
