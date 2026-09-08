# Independent review of matching-star integration

2026-09-08. No blocker found in the scheduler, native adapter, or fixed pilot
configuration. This follows the completed
[independent core review](induced_star_core_review.md); the connected-center
extension remains unimplemented. The reviewer made no source or test edits and
ran no new constructor or full-pipeline experiment during this integration review.

## Reviewed identity

| File | SHA256 |
| --- | --- |
| `contact_repair.py` | `a79c78909a979726c7af93ca8a0a12a6c1228c795562be3d3cb029084797269e` |
| `native.py` | `4fd880391e9c5bf2f3ed4e6f238ce987070108a7fc5eb36cac6aa95d69b7cbc9` |
| `scripts/codex/pilot.py` | `0d472453daa309e11630519f4813bc592c41ddbfc93725beaf5312417d118b4b` |
| `test_induced_star_integration.py` | `5e335be88ebb48e828e4d049f3521964a340bb1182b3762f4c2b1c8cbe6f37d4` |

The core remains the reviewed `785a1ab9…` snapshot. These are precommit source
identities; later edits require their own review rather than inheritance of
this conclusion.

## Accounting and scheduling

At the beginning of an ordinary group visit, the scheduler creates a budget
whose limit is the smaller of the original group ceiling and remaining global
work. Ordinary `_repair` receives that limit; its reported work is then placed
in the same visit budget. An attached star query and any maintenance consume
only what remains. The complete visit total is added to global `expansions`
once. Star work is also charged to the core's fixed whole-call 5% auxiliary
share, without creating additional global work. Its returned work counter is
descriptive and is not charged a second time.

The original group generators and remaining group count are retained. Every
ordinary visit increments `groups_tried` once whether or not a star query is
attached. No added group, zero-excess sweep, or separate center queue appears.
Only a failed ordinary visit can trigger an attempt, and its first vertex is
the center. The center is marked considered before structural selection;
failure, ineligibility, or budget exhaustion does not permit another attempt
for that center during the pass. The set resets at the next pass. Any ordinary
acceptance, including equal-Q redundancy improvement, suppresses the attached
attempt as required by the saved policy.

This preserves the scheduling rule, not an unchanged future trajectory: star
work consumes allowance, accepted replacements change the evolving embedding,
and subsequent ordinary proposals can differ. The experiment must measure that
cumulative effect and retain displaced-work costs.

## Validity, deadlines, and ownership

The public contact boundary rejects unsupported graph kinds for matching mode
and validates the original incumbent before dispatch. The native adapter
rejects invalid policies and direct-singleton/matching combinations before
construction; its existing source-kind checks remain. It forwards one policy
option into the same single contact-refinement call with the same deadline.
Its final original-graph validator remains in place.

The scheduler forms a candidate map from the immutable incumbent and the
core's selected-only certified replacement, then checks the shared deadline
before committing. If time expires after certification, it retains the old
embedding and records a rejected commit. A completed committed move is published
before ownership maintenance: an interrupted refresh disables future auxiliary
search and does not undo a valid accepted embedding. Every accepted ordinary
or star move invokes refresh using the same active visit; a cache that has not
been constructed requires no maintenance.

The cache removes all old selected ownership before adding new ownership, so
selected qubits can change owners without transient collision. Neither query
eligibility masks nor a partially refreshed owner map cross a commit. The
incumbent identity contract inspected in the core review is preserved: `_repair`
and the star scheduler produce new mappings and do not mutate old chain lists.

The final contact return measures elapsed time and reports a crossed deadline.
As before, these are cooperative deadline checks with a later native/pilot
validity and timing decision; no hard real-time guarantee is inferred.

## Proposal counts and actual commits

The integration keeps the three relevant stages separate:

- `complete_proposals` includes matching-complete attempts before certification,
  including attempts whose certificate is later interrupted.
- Core `certified_proposals` and an attempt's proposal `accepted` flag describe
  a completely certified returned replacement.
- `star_search.accepted`, `attempt.committed`, and the accepted trajectory
  describe actual scheduler commits after its deadline check.

The attempt also records `commit_rejection`, and visit records separate ordinary,
proposal, and maintenance work. Aggregate accepted Q/R changes and trajectory
entries use committed changes. A larger provisional-proposal count must not be
reported as a larger quality improvement. Generic region-size diagnostics still
describe ordinary reconstruction; matching root search is not confined to that
region and has its own work counters.

## Off-path replay and test scope

The source diff leaves the original off-policy loop intact. The native adapter
omits the new keyword and diagnostic key when the policy is off. The new pilot
configuration is exactly the current spectral configuration plus
`polish_star_policy='matching'`, with singleton policy remaining legacy. There
is no graph-family dispatch or per-input output selector.

The integration test comparing new default behavior with new explicit off
behavior alone would not prove preservation of the previous source. Root
provided an additional comparison to frozen pre-integration source, which this
review inspected:

* `results/codex/induced-star-root-review/contact_before.py` is byte-identical
  to 036's frozen `contact_repair.py`, SHA256
  `804edfaaf9cdefe33249ffea9db1d752cd79c0e0b8a2a0d2bcd9478e0c483c57`.
* `check_off_replay.py` compares exact final mappings and all non-time diagnostic
  fields on six valid tiny quotient minors under each of the two group policies.
  Its outputs contain 12 exact replays; both policies perform meaningful
  reductions and nonzero search work.
* The recorded `off_replay.json` hash is
  `e284eb2a0a9dfce3cc6464c980d008da3e756e39b72441bf70a236888c351259`.

These existing checks were inspected, not repeated unnecessarily. They are
small contact-path regression checks, not full native trajectory or performance
measurements. The additional independent 96-case core oracle is preserved
separately with its safe additive rerun command.

The final test-only revision was reviewed separately after the original
`54035fcf…` test snapshot. It strengthens visit/auxiliary accounting assertions,
checks rejected commits explicitly, verifies that a selected star can exceed
the ordinary four-chain group size, and adds native off-policy argument and
target-loop boundary checks. All reviewed implementation hashes remain unchanged.

The new integration tests cover attached attempts without extra groups,
once-per-center/pass behavior, ordinary/equal-Q suppression, shared global and
per-visit caps, deadline expiry after certification, incomplete maintenance,
mixed labels and isolates, original-graph rejection, native forwarding/final
validation, and the fixed actual-Z12 mathematical witness. Ordinary proposal
outcomes are stubbed in scheduling fixtures to isolate those transitions; this
does not establish performance relative to the real ordinary proposer.

One explicitly named, prespecified real native smoke is also present in the
final test file: a fixed 24-vertex random source with mixed labels and an added
isolate, Z3 target, spectral initialization, 40 placement evaluations, and one
bounded refinement pass. It checks original-graph validity and preservation,
source coverage, the isolate, shared work accounting, and policy forwarding.
It asserts no Q advantage or speed comparison. The revised module docstring
correctly distinguishes this call from the stubbed adapter tests. This reviewer
inspected the final test code without rerunning the regression already in
progress under root; no new smoke outcome is claimed here.

Root owns required test execution, commit, and the next experiment freeze.
This review clears the inspected implementation logic; cumulative quality and
time remain unmeasured for the integrated policy. Retain the off policy unless
the separately frozen comparison supports a global change.

Status: independent scheduler/API review complete with no requested source change.
