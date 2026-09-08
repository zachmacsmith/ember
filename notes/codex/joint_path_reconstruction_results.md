# Joint path saved-final gate: cycle gain, advancement fails

The one authorized six-call gate returns six independently valid, timely maps
with complete accounting. **Do not advance or register the fixed operator:**
the cycle improves, but none of the other five inputs does. The declared
cycle-plus-another condition fails. There were no errors, lost outputs,
deadline/work stops, watchdog events or retries. Every process was reaped.

| Saved A053 input | Q before → after | Paths / route attempts | Work | Operator wall | Cold observed wall |
|---|---:|---:|---:|---:|---:|
| Cycle1829 |148 → **126**|1 /2|139,061|0.094s|0.203s|
| Cubic33219 |258 →258|4 /128|255,263|0.169s|0.271s|
| Kagome32122 |173 →173|6 /119|194,143|0.129s|0.235s|
| Grid1584 |167 →167|3 /84|170,298|0.117s|0.222s|
| Planted34404 |158 →158|6 /34|121,384|0.083s|0.192s|
| Petersen4083 |174 →174|6 /192|255,017|0.171s|0.273s|

Cycle's selected path contains125 owners and initially147 route sites. Greedy
joint reassignment on the unshortened witness releases its unused suffix,
reducing full Q148→128. One chord shortcut then gives Q128→126. Both proposals
are certified and committed; Q126 equals the number of source vertices and is
therefore optimal for this particular supplied graph. This is positive evidence
that simultaneous owner-boundary changes can remove overhead inaccessible to
the prior one-site lifting trajectory. It is not a uniqueness result against
all ordinary or vacancy moves, a new cycle constructor, or an across-input gain.

All557 non-cycle route attempts return `insufficient_suffix`. Fourteen of26
paths reach the normal32-attempt bound; their unvisited alternatives remain
unknown. No output is missing because of these finite limits. No complete
constructor was rerun, and the two A057 construction failures cannot enter
this successful-output-only stage.

Total operator work is1,135,166 across six separate budgets: setup584,300;
path selection46,257; witness extraction52,080; chord generation29,615;
allocation364,750; certification57,912; publication252. Operator wall/CPU are
0.763/0.764s. Cold worker/input/code setup adds0.589s; independent final checks
add0.027s. Observed time through encoded atomic publication totals1.396s;
process times, including supervisor observation, total1.603s. Setup inside the
operator accounts for0.396s of its0.763s. These are local saved-data costs, not
a fresh same-host full-constructor speed comparison. The largest observed
per-input time is0.273s, within its predeclared allowance.

## Additive correction: allocation is complete within a fixed route

The proposal's claim that greedy could consume a uniquely needed later site
was **incorrect for these constraints**. No source or numerical result is
changed by this correction, and no exact solver or further execution is added.

Fix the ordered physical route and logical owner order. Each owner needs a
nonempty contiguous segment containing a contact to every fixed outside
neighbor; additional sites/contacts do not invalidate it. Suppose a feasible
partition has endpoints `b1,...,bk`. Greedy's first endpoint `g1≤b1`, because it
takes the earliest prefix meeting owner1's contacts. Inductively, if
`g(i−1)≤b(i−1)`, greedy owner i starts no later than that feasible segment.
Extending to `bi` contains the entire feasible segment, hence covers its
contacts; its earliest feasible end satisfies `gi≤bi`. A feasible partition
always leaves at least one site per remaining owner, so the code's suffix
reservation cannot reject it. This proves completeness of the implemented
feasibility test, and minimizes the final used endpoint for this fixed first
site/order. A later starting point cannot rescue feasibility: append its
omitted prefix to owner1. It can affect minimum occupied Q when prefix release
is allowed; this prototype fixes the first site.

Consequently, each completed allocation rejection excludes the nonempty
contiguous-segment representation on **that candidate route/order**, not merely
one unsearched cut. This remains far from global or path-neighborhood
optimality: other physical routes, source orders, off-route branches, free
sites and the unvisited chords are outside the conclusion. All25 non-cycle
unshortened witnesses also reject. Since their original minors are valid and
their selected chains supply ordered connected route subsets, these witnesses
lose required side-contact support supplied by omitted chain material; simply
searching more segment boundaries on the same witness cannot fix that loss.

The scoped decision remains unchanged: preserve the optimal cycle witness and
the five ties, retain A053, and make no complete-constructor/promotion claim.
Raw commands, receipts, outputs, process records, all route attempts and
accounting are in `results/codex/joint-path-gate/attempt001`; `derived.json`
contains only arithmetic over those saved records. Frozen core SHA
`c07cac2ef6605ee6b653ad7c3056a1c12b2f5e7a33aeb57bfce1d126841d0f1f`;
pre-execution manifest SHA
`c8db357d4107afd4614480509af94b49d1e860a9a549e1825eeefa22befffdcf`.
