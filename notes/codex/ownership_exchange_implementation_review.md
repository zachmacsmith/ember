# Independent ownership-exchange implementation review

2026-09-08. **The bounded correctness gate passes.** No unresolved source defect
was found in the isolated proposer. This approves the reviewed implementation
against its restricted contract; it does not establish novelty, benchmark ACL
gains, usable amortization, or permission to integrate or run a corpus experiment.
No constructor, native pipeline, corpus input, competitor, scientific package
or remote operation was used here.

The accepted [specification](ownership_exchange_implementation_spec.md) has
SHA-256 `8d870c3a2e16615574ad018eec266258200bd7740b7cbd2450d47a47d299f82f`.
The reviewed
[module](../../packages/ember-qc/src/ember_qc/algorithms/factored/ownership_exchange.py)
has SHA-256 `015781019833ee5a3f49dcec5a189161104003224b1327b44cedda6e084532bb`.
Author tests are independently identified by
`6654d95dd6cf6ef561c5d901b6088f41a3072b5553700e77814ada1c17516b03`.
The author's 38 passing tests are author evidence, distinct from this review's
ten test groups. All 28 author-manifest files and 39 retained independent-attempt
file records pass a separate hash readback (67 checks).

## Source reasoning

Entry setup copies and validates a single immutable incumbent once for the
nonempty supplied group sequence. Groups are accessed lazily in caller order;
each group/deletion seed receives fresh state and visited records. Whole-donor
admission retains every site from that donor's entry chain. The permanent
deletion, original-patch connectivity, eight-owner and 64-original-site bounds
are preserved by child copies; no child mutates its parent or shared entry.

Complete successor generation enumerates the declared occupied boundary,
simultaneous transfers/swaps and both eligible orientations before returning
the ranked top four. Intermediate physical chains remain nonempty, connected
and disjoint. The chosen missing logical edge must be restored, while other
missing contacts may change. Exact signatures include the selected owner set
and complete surviving ownership partition. The deleted site and immutable
entry are fixed within each seed. Minimum-depth dominance therefore permits
shallower revisits without admitting a history-dependent shortcut. Hash buckets
perform token equality checks after collisions.

The final certificate reconstructs ownership and source contacts independently
of incremental deficits. It checks original-patch membership and connectivity,
the complete surviving partition, unchanged outside chain lists, and exactly
one fewer occupied site. Only complete materialization, validation, publication
reservation and a final timely check can return a candidate. A fully certified
but late proposal remains distinguishable from a returned candidate.

The simple undirected target contract remains a caller precondition. Setup checks
occupied target rows and source symmetry; it does not certify all unused target
adjacency or arbitrary mutable/custom iterables. Integer labels, stable mappings
and ordinary chain/group containers are part of the declared interface.

## Independent execution

The final portable, stdlib-only run is
`results/codex/ownership-exchange-independent-review/attempt003`. Its summary
SHA-256 is `27dd692c9d45988abdedbd5eee1bc5d397aea1bd406f686553799b36f5d9b034`.
The import guard rejects Ember, D-Wave, MM, busclique, NumPy and SciPy imports;
none were loaded. The suite took 4.47 seconds locally, an audit duration only.

| Check | Result and scope |
|---|---|
| Exhaustive tiny domain | All 64 simple four-site targets, eight three-vertex logical graphs including isolates, and 60 ownership/free-site assignments: 30,720 combinations, 10,476 independently valid minors. |
| Exact public result | All 10,476 match the independent restricted-search oracle: 1,368 candidates and 9,108 non-proposals; all positive traces here have depth one. Full lists, deleted site, selected owners and trace descriptors agree. |
| Complete child enumeration | 5,424 generated states in that domain contain 8,304 valid children. An oracle over all elementary ownership changes agrees with every child rank and retained result. It does not reuse the production boundary walker or contact cache. |
| More than four children | A separate nine-site fixture has six transfers and six swaps. Complete generation retains the four globally preferred transfers and discards eight children, displacing worse swaps encountered earlier. Reversing input/adjacency/list order preserves the selected move and preserves outside lists in their supplied order. |
| Larger structural witnesses | Nine fixed cases cover a genuine transfer, the two-swap three-owner cycle, frozen long chains, negative labels, whole-donor admission at 64 versus 65 sites and eight versus nine owners, and changed eligibility under successive supplied groups. Thirteen more generated states match all 14 complete children. |
| Work prefixes | Every allowance 0–617 for the five-site transfer: only exactly 617 units returns the candidate. All 618 outcomes have exact live-budget deltas, stay within the cap and preserve input values. In 160 interrupted prefixes a valid-looking child existed but incomplete generation correctly prevented certification/publication. |
| Clock prefixes | All 630 observed fake-clock cut positions reject late output; earlier explicit/inherited deadline wins. The final post-finalization crossing reports wall 2, deadline 1 and overrun 1, retaining certificate evidence while returning no candidate. |
| Private rollback | All 250 allowances through one complete 249-unit generation preserve the parent, immutable entry and ownership map, including interrupted admission. |
| Batch and state semantics | Setup runs once; repeated groups repeat their search; a later enlarged group reconsiders the same deleted site. Ineligible groups skip, malformed groups stop, success leaves a malformed suffix uninspected, and an empty sequence performs no entry setup. Shallower revisits and distinct signatures with colliding integer hashes remain eligible. |
| Independent certificate | Deliberately corrupting a valid-looking terminal state is rejected by the full original-graph certificate, with no output or completed-certificate claim. Each returned trace is also independently replayed and every intermediate physical partition checked. |

Expected exhaustive results were saved before candidate execution in `oracle001`
with SHA-256
`e21d7acdc02d2174cd200d302e907a4eba99bf71b14c483e675ddf0c6b0f6b97`.
Original physical edge sets drive validity and contacts. This domain contains
only a bounded fraction of possible graph/search states. It does not exhaustively
exercise eight-deep or 256-state physical searches. Exact depth-dominance checks
are data-structure checks, not a new physical reachability witness. Restricted
non-proposals are not certificates of contraction infeasibility. The previously
reviewed mathematical witnesses were not rerun merely to bind the revised
specification hash.

## Cost and accounting

`_Context.validate` at source line 287 rebuilds occupied ownership, checks each
chain's connectivity, accumulates contacting owner pairs in one occupied-target
adjacency pass, then checks the source edges. Its graph scans meet
`O(Q Δ+n+m)` rather than rescanning each chain for every logical neighbor.
Three supplied-minor checks record exactly 20/24/32 physical adjacency entries
and 2/6/14 logical adjacency entries for 1/3/7 logical edges; connectivity has its
own separate physical scan. Setup adds occupied-row and source-structure checks,
and charged label ordering adds sorting overhead.

No repeated-entry setup factor is hidden across groups in this API. The remote
two-group fixture copies its nine entry qubits once and returns in 2,014 units.
The two-swap fixture uses 1,527 units; the 64-site admission fixture uses 7,254.
These are declared elementary work counts on supplied toy inputs, not operation
counts comparable with MM or production timing estimates. Frozen-neighbor
boundary enumeration can scan a chain much larger than the 64-site patch;
complete generation, state copying and failed admission can still dominate.
Only the shared finite allowance bounds total query work. Nested group/seed/
generation work intervals must not be summed; disjoint work categories match
the live allowance delta, and exclusive stage times sum to query wall.

## Findings and retained attempts

Static review identified a diagnostic boundary before the declared source
freeze: a final deadline crossing after `finish()` could reject correctly while
retaining an earlier wall/overrun measurement. The author fixed this by retaining
the crossing timestamp; all executions here use that corrected source. No search
policy changed from this finding.

Independent `attempt001` had one reviewer-only assertion error: the expected
stop-reason spelling was `disconnected_patch`, while the implementation reports
`disconnected_original_patch`. All oracle comparisons passed. Its complete
bytes remain intact. `attempt002` corrects that assertion and strengthens the
linear-scan counter assertions; nine groups pass. `attempt003` adds the
twelve-child global-ranking fixture to close the identified coverage gap; ten
groups pass. No candidate source changed during these runs. The author's separate
failed test-count assertion and temporary oracle-domain expansion remain
preserved in the author manifest and are not counted as independent tests.

Self-critique: the independent oracle shares the accepted mathematical move
definition with the implementation, so exact agreement checks implementation
fidelity rather than proving the definition is effective. Original-edge validity,
enumerating all elementary ownership changes and independently replaying traces
reduce shared implementation errors. They cannot show that useful contractions
are common, that the occupied-only restriction is adequate, or that complete
generation is worth its cost. A separately authorized reach/cost diagnostic is
the next evidentiary step; this review does not select a scheduler or displace
the current pipeline.

## Reproduction and artifact scope

From the repository root, choose **new** output paths:

```text
.venv/codex-native/bin/python -I -B results/codex/ownership-exchange-independent-review/verify.py --repo /Users/dabh/ember --out results/codex/ownership-exchange-independent-review/root-repeat
.venv/codex-native/bin/python -I -B results/codex/ownership-exchange-independent-review/check_recorded_artifacts.py --repo /Users/dabh/ember --out results/codex/ownership-exchange-independent-review/recorded_artifacts_root.json
```

The verifier's SHA-256 is
`3bce62bfd33a4927914caf67c14368a7012e06355d98448e0ba5d08d8d9a4003`.
Both commands refuse existing output paths. Exact source/spec, scripts,
commands, Python identity, expected and actual records, failures, counters and
summary hashes are retained under the review directory. `review_manifest.json`
binds the frozen review files; later additive root repetitions are outside its
initial file set. No production, author-owned or frozen experiment file was
edited by this reviewer.
