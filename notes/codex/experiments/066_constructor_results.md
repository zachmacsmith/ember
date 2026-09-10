# A066: coordinated shortening passes the small constructor screen

2026-09-10. **Continue the mechanism: A066 improves four encodings representing
three structures, with no success or Q loss against pruning-only or A065.** All
five arms succeed on all nine inputs. A066 still loses to MM on every input;
this is bounded development evidence, not promotion or an all-class result.

The [frozen screen](066_constructor_screen.md) ran 45 separate cold calls on
hyde06: A066, its constant pruning-only ablation, A065, retained A061 and pinned
MM. Each used ideal Z12, seed 0 and 60 seconds. Candidates construct afresh with
one A061 entry and evolve one state; no MM/busclique calls, saved-map initialization
or output combination. The original common audit and corrected passive mechanism
reader each passed their first full execution; root verified 234 and 56 bindings,
respectively. There are no failures, late calls or unknown call-time fields.

Q is total qubits; ACL is Q/source vertices. Pruning-only and A065 have identical
final Q on every row, so their column is shared.

| Development input | A066 Q (ACL) | Pruning / A065 Q | A061 Q | MM Q (ACL) | Pair admissions |
|---|---:|---:|---:|---:|---:|
| ER80 | 252 (3.1500) | 252 | 261 | 248 (3.1000) | 0 |
| Planar80 | 126 (1.5750) | 126 | 127 | 118 (1.4750) | 0 |
| Grid128 | 159 (1.2422) | 162 | 168 | 133 (1.0391) | 4 |
| Singleton control80 | 199 (2.4875) | 199 | 201 | 181 (2.2625) | 0 |
| Fresh WS100 | 243 (2.4300) | 244 | 248 | 223 (2.2300) | 1 |
| Fresh SBM100 | 251 (2.5100) | 251 | 261 | 241 (2.4100) | 0 |
| Grid128 relabel | 157 (1.2266) | 158 | 163 | 133 (1.0391) | 1 |
| BA100 | 235 (2.3500) | 235 | 282 | 199 (1.9900) | 0 |
| Fresh planar100 | 169 (1.6900) | 170 | 174 | 155 (1.5500) | 1 |

The frozen criterion passes: no paired success loss or Q regression against
either control, and improvements over pruning on grid, WS and planar structures.
The relabeled grid is additional encoding evidence, not a fourth independent
structure. Planar100 supplies an improvement beyond the six fixed diagnostic
inputs; it and BA100 were new to this inherited refinement sequence but previously
exposed by other tracks. Planar80 remains negative. There is no untouched
confirmation or across-seed variability estimate.

Within-chain variance increases on WS100, from 1.2464 to 1.2651, and planar100,
from 1.0100 to 1.0139. It decreases on grid and its relabel and is unchanged on the
other five inputs. These increases are preserved, not hidden by the mean ACL gains.
Within-chain variance is not the requested across-run ACL variance.

The mechanism made seven atomic pair admissions, all during the first owner
round. Five selected assignments have the recorded neutral-first contact
condition; two selected grid assignments lack it. This does not prove every
possible assignment for either pair requires joint release. All seven receipts
reconcile exact Q−1, source adjacency, actual hardware couplers and global query
invalidation. Full intermediate embeddings were not independently replayed; the
original oracle independently validates the final returned maps.

**Local savings do not add directly to end-to-end gains.** Grid has four pair
admissions but saves only three qubits against pruning: its ordinary reconstruction
saves five qubits, compared with six in the ablation. Across the nine calls,
seven pair qubits and one fewer ordinary qubit yield six net additional qubits
saved. This preserves the measured interaction between complementary operators.
The four original negative diagnostic structures—ER80, planar80, control80 and
SBM100—remain unchanged, as does newly screened BA100. The mechanism does not
explain or resolve those remaining gaps.

All 895 pair attempts completed: 888 exhausted and seven found. A066 recorded 604
empty direct domains and five nonempty ones; the ablation recorded 615 and five.
These are queries across evolving states, not independent source vertices. Empty
domains close a proved futile query until the next state change. Pruning-only
performs zero pair attempts and shows no final Q improvement over A065 here.
Scalar base Q agrees across these arms; exact base-map/trajectory equality was
not established by this analysis.

All-call time totals, including imports/output in process wall:

| Arm | Solver wall (s) | Solver CPU (s) | Process wall (s) |
|---|---:|---:|---:|
| A066 | 531.110 | 530.909 | 550.571 |
| Pruning-only | 531.108 | 531.037 | 549.713 |
| A065 | 531.154 | 530.913 | 550.327 |
| A061 | 91.493 | 91.215 | 112.095 |
| MM | 18.777 | 18.762 | 24.716 |

All 27 added-stage searches reach their deadlines and remain cost-censored even
though their full calls succeed. No finite search exhaustion or speed improvement
is claimed. A066/MM paired solver-wall ratios range from 7.720× to 122.774×; the
roughly-MM-order runtime objective remains unmet on most inputs.

A066's nested obstruction/pair/admission intervals total 0.276191 seconds, versus
0.031587 seconds for the pruning-only intervals. The former is 0.0615% of its
449.048143-second added-stage total; these intervals already belong to the
headline call time. Non-improving ordinary reconstruction consumes 420.978716
seconds, 93.75% of that stage. Pruning lowers aggregate root-search time from
A065's 23.528569 seconds to 17.604950 seconds, but whole-call time and final Q do
not improve. Eliminating provably futile queries and adding the observed pair
moves have not removed the dominant cost or broader contact-placement deficits.

The complete-constructor ablation supports the coordinated operator's value at
small measured cost across three structures. It does not support repeated local
repairs as the main research direction, broad class claims, or a performance
claim against MM. Root owns the next broader screen decision; no refinement or
additional constructor/validator call was performed for this report.

Evidence in `results/codex/a066-constructor/`:
- Frozen screen SHA256 `3eb535ae9ba17a1d87d9fd03d5bd4f0de8000e59986776d27adb7e97130005e9`;
  manifest `af2013dbca4f6ba858c856224f19b76418b9a834352044f47ef44ac706af9eee`;
  source snapshot `5fca57bae67709454f2140f85c7a60106d6c60b372485a522fb6c91c71838dbe`.
  The frozen screen retains the contract, implementation, peer review, source and
  independent-oracle references.
- Original audit summary `audit001/output/summary.json`, SHA256
  `a802959473a95c1e2e93afd734207ef036cf0cf52fa8241fb7166dfa2bdafb6b`.
- Mechanism summary `mechanism001/output/summary.json`, SHA256
  `c7ef658e0b80a5ac7938dc89a57edc2effbf7bdacf6afbd16d6c8c9117ef8a38`.
  Complete all-call rows and six comparisons per input remain beside it.
- Passive scalar report `report001/summary.json`, SHA256
  `7baf1b1263d8aceef538ca7f5af5d0a71a32c3bbd938d5d6daa4a23aade6e78c`;
  binds seven authoritative input files. A preliminary message mis-summed the
  pair attempts as 995; the saved scalar projection establishes 895, used here.
