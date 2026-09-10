# A next decision: contact coverage during reconstruction

2026-09-10, version 2 after completed A066 transfer. **Design for review, with
no implementation or calls.** Keep A
incremental and test one broader change to its dominant reconstruction operation:
choose a path by distinct missing contacts reached per added site, instead of
stopping at the nearest missing contact. Go from a tiny distinguishing fixture
to a complete-constructor screen; do not begin another saved-map exact campaign.
The broader A066 fixed policy fails its frozen criterion: all 17 successes
survive, seven inputs improve over A065, but ER160, SBM160 and wheel each
regress by one qubit. A061 remains retained. Preserve the
[initial-evidence design](a_067_contact_coverage_decision_v1_initial_evidence.md);
the proposed change below is a new bounded hypothesis, not reinstatement of A066.
The [complete transfer result](../experiments/066_remaining_transfer_results.md)
and [combined class gaps](../a066_combined_class_gaps.md) preserve the rejected
policy and retained A061 reference.

The [initial results](../experiments/066_constructor_results.md) preserve nine MM
Q losses, including BA100 235 versus 199, grid128 159 versus 133, WS100 243 versus
223 and SBM100 251 versus 241. The pair mechanism adds six net qubits of savings
across nine encodings. Non-improving ordinary reconstruction consumes 93.75% of
the added stage; [95.43% of that stage](../experiments/066_initial_trajectories.md)
occurs after eventual final Q. These are two overlapping retrospective measures,
not additive costs or proof of a safe stopping time. The opportunity is to make
reconstruction generate better trees across chain lengths and source structures,
not merely execute more of the existing rejected trees. No substantial gain is
established yet. The completed broader receipts sharpen the decision. ER160
has no pair or exact-obstruction observations; SBM160 has ten pair attempts and
no pair admission. Each loses one ordinary admission. Wheel instead saves ten
pair qubits but eleven fewer ordinary qubits, for a net one-qubit regression.
Their base scalar Q agrees between A066 and A065; this is not map equality.
Thus one universal explanation of all three regressions would be unsupported.

Late useful computation is now directly observed: A065 admits ER160's final
qubit at 58.212 seconds from wrapper entry and SBM160's at 55.160 seconds.
A066's initial 95% retrospective figure cannot justify a universal cutoff.
The next test must preserve complete incumbent trajectories and compare against
A065 as well as A066; a benefit relative only to a regressed policy is insufficient.
Broader non-improving reconstruction remains 77.80% of A066 stage time, but
larger ER/regular/SBM also spend substantial time ranking roots. The attachment
change targets quality and the former cost regime; it does not claim to resolve
every measured runtime deficit. A066 still loses every displayed WS, SBM, planar
and control instance; grid and BA100 retain Q excesses of 26 and 36. These are
the substantive deficits the new mechanism must help, beyond another pair count.

The [prior source review](a065_remaining_mechanisms.md) identified MM's ability
to revise whole chains and contacts without requiring every working-state change
to reduce total Q. A066's global state can already represent arbitrary connected
chains, but each query freezes most surrounding geometry and selects one greedy
tree per root. This proposal addresses the latter restriction only. It neither
reproduces MM's contact mobility nor establishes which capability caused a saved
MM win.

| Explanation of persistent gaps | Observation that would distinguish it |
|---|---|
| Restricted contact domain | No shorter connected tree can meet the fixed outside contacts. Changing attachment scores cannot help; a separately demonstrated empty domain is local infeasibility evidence, not global embedding infeasibility. C017's BA result illustrates this distinction on its own different state. |
| Generated move neighborhood | Under identical prepared donors and root, the new path sequence yields a strictly smaller independently valid final tree than nearest-first. That establishes an omitted move on that query, not a complete quality gain. |
| Acceptance | Both versions retain strict total-Q admission. A valid strictly smaller proposal passes that rule; any gain here needs no neutral acceptance. Lack of such proposals leaves neutral/uphill barriers unresolved. |
| Computation and allocation | New reconstruction can cost more per root. Whole-call trajectories must show whether useful admissions arrive sooner or lower final Q compensates for less root coverage. More contacts per extension, more visits, or a better local ratio alone are insufficient. |

**Hypothesis.** Nearest-first attachment sometimes commits a branch to one contact
when a slightly longer path reaches several missing neighbor groups together.
That commitment can force a larger final tree. A general coverage-per-cost rule
can reduce this source of excess across local, community and hub inputs. The
current implementation already grows shared branches from the entire tree and
counts incidental contacts; the proposed distinction is looking beyond the first
contact layer, not introducing branch sharing for the first time.

```text
use A066's same constructor, prepared donors, roots, scheduler and valid state
for each ordinary focus reconstruction:
    T = {root}; M = neighbor groups not contacted by T
    while M is nonempty:
        multi-source BFS from every site of T through the same free graph
        for each canonical shortest-path predecessor, propagate the union of
            missing groups actually contacted along that path
        choose an extension P minimizing new_sites(P) / new_groups(P)
            compare integer cross products; then fewer new sites, seeded order
        finish tied BFS layers; stop deeper exploration only when its depth L
            satisfies L * best_gain > best_length * |M|
        attach that actual path to T; update missing groups
    use the unchanged witness selection and final tree trimming
    certify the composed map; publish only a strict total-Q improvement
```

The depth condition follows because any extension can reach at most `|M|`
distinct missing groups. It bounds this specified score search over canonical
shortest paths only; it is not a final-Q lower bound or exhaustive path search.
Use the existing seeded traversal for predecessor ties and arbitrary-size group
masks, with no 64-neighbor cutoff. Every path, label union, reconstruction and
certification cost remains charged. There is no additional owner, root, distance
or operation-count limit and no production exact solver. Retain the existing
deadline and its failure/censoring accounting.

**Important pre-code correction:** do not cap the growing tree at its eventual
strict-Q size allowance. The existing final trim can remove the starting root
and obsolete branches, so intermediate size is not a sound bound on final size.
Likewise, union labels must count distinct original neighbors along one actual
path; independent distance sums are not shared-tree costs.

**One self-critique.** Coverage per site is still a local proxy. A path with many
nearby contacts may make a remaining distant contact expensive. A single canonical
shortest path can miss a better equal-length route; frozen donors and witness
selection remain restrictive. Exploring past the nearest layer can consume the
remaining wall allowance sooner, and a locally better admission can worsen later
complete trajectories. Familiar coverage heuristics provide no novelty claim.
These limitations justify a bounded test, not repeated weight/path-width repairs.

**Cheap falsifier and checks.** First use one tiny fixed-domain fixture, without
MM or a saved benchmark map: free edges `r-a, r-b, a-x, x-c, b-c`; required
contacts `D:{r}, A:{a,c}, B:{c}, C:{c}`. Start at r, with a preceding r in the
seeded BFS source order. Nearest-first attaches a, then reaches c through a-x;
the retained r-to-c tree has four sites. The proposed rule reaches A/B/C through
r-b-c at cost 2 for gain 3 and retains three sites. The unchanged oracle checks
the completed tiny maps after attaching fixed donor sites realizing those
contacts. Failure to realize this distinction rejects the implementation; this
fixture is not development or Zephyr-performance evidence. A second controlled
case must preserve the nearest choice when no alternative improves its ratio.

Check only the new risks: distinct labels and repeated contact deduplication,
more than 64 groups, sound tied-layer stopping, actual path connectivity,
final-trim removal of an initial root, and interruption without partial admission.
Reuse the existing dependency guard, certificate and independent validator.
The actual research falsifier is the immediately following complete screen,
not an exact neighborhood campaign. Exact solves remain optional future
diagnostic instruments only if a concrete unresolved observation warrants them.

**Revised proposed complete screen, to freeze after review.** Use Transfer004's
nine new encodings plus the three A066 regression anchors, ER160, SBM160 and
wheel: twelve encodings/eleven structures. This changes the unexecuted v1 panel
to retain every observed policy regression in the next comparison.
The six fresh random families, two hidden-witness controls and BA relabel give
fresh transfer and label sensitivity without source-family logic in the candidate.
Run the new single algorithm, unchanged A066, unchanged A065, retained A061 and pinned MM
separately on the same host, seed 0, with the existing 60-second call allowance:
60 calls. The A065 arm prevents inherited regressions from disappearing behind
an A066-only comparison; it is not an output selector. Record all
solver/CPU/process time, failures, within-chain variance,
reported base-validity bounds and complete incumbent-Q admission trajectories.
Never combine outputs. Hidden control witnesses remain evaluator-private.

Continue only with no success loss or Q regression against either A065 or A066 and complete
Q gains spanning at least three random-source families, including fresh inputs.
The three-family condition demands evidence commensurate with this mechanism's
class-spanning claim; grid and its relabel do not supply two structures. Report
each MM excess and its reduction separately. If gains remain a few isolated
qubits with effectively unchanged persistent gaps and deadline-dominated cost,
that is insufficient to extend another local refinement sequence. Root should
judge the measured quality/cost tradeoff, without an unexplained universal
runtime ratio. Any success/Q regression rejects this new fixed policy for retention
and stays visible even if other inputs improve. A local ratio or witness gain
without complete-output benefit retires the policy rather than prompting more
ratio tuning. One seed is an exploratory decision, not promotion, across-seed
variance evidence or confirmation of class-wide superiority.

This differs from [B029](b_029_causal_decision.md), which evaluated actual trimmed
unions but prioritized overlap in a local root move with fixed residual labels;
its lower overlap produced larger Q on both retained successful inputs, while
six constructions still failed. Here overlap is absent, strict-Q acceptance
remains, and contact attachment itself changes.
The [C017 negatives](c_017_decision.md) prevent interpreting a routing score as
a remedy for empty fixed-contact domains. Stop narrow pair-length extensions,
unmeasured cutoff claims and speed-only reconstruction work at this milestone.

Evidence binding: initial trajectory summary SHA256
`3067f7dcdca58d37766ed05b7cd2f62a7be6417cc0af02ca0643c58c3a3b308a`;
initial complete scalar report
`7baf1b1263d8aceef538ca7f5af5d0a71a32c3bbd938d5d6daa4a23aade6e78c`;
[Transfer004 preparation](../transfer_cycle_004_input_results.md) panel
`b54a8ed0af8e35b3901630fddd2892e3735338ad29104913d3332df49eed250d`.
Version 1 SHA256: `2cf4e47bc0d616567db7425fd0d39e34edc2ecba997ce2ecb8b4bc76e083f532`.
Version 2 incorporates only completed, root-audited broader receipts. No candidate
or validator ran while preparing either version. The proposed screen is not an
execution authorization, and further local follow-ups are not automatic.
Broader/combined scalar report SHA256:
`6fe49155a7451bf4790f229cb52674deb166778fa0d69e8ec89fcfaf65da095e`.
