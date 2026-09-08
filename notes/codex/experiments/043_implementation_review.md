# Independent 043 worker, controller and input review

2026-09-08. **The local integration gate passes.** The fixed proposal diagnostic
implements two separate observations on one unchanged entry, with one common
deadline per arm. This review neither authorizes a corpus launch nor provides
evidence of a quality or runtime advantage. No corpus proposal, constructor,
remote action or production edit was performed by this reviewer.

## Evidence and scope

The portable [checker](../../../results/codex/043-independent-review/checks.py)
was frozen before execution in `prepared/freeze001.json`. Its SHA256 is
`7ba5ce7e79fa34b204ef16af7048ca44390741d44ff4d8ab8be62d7131a71543`.
The [local result](../../../results/codex/043-independent-review/attempt001/summary.json)
passes all **18 checks**, with zero failures/errors and no prohibited imports.
It binds every exercised source file before and after execution. Four actual
proposal calls use only the two previously frozen tiny cycle and negative-label
fixtures. All other method and controller execution is synthetic or mocked;
the mock controller retains 68 observations without spawning a subprocess.

The complete child-generation/certificate, group-generator and ordinary-adapter
reviews belong to their separate accepted reviews. They were not repeated here.
The unchanged supervision and fatal-watchdog modules are exact reviewed 040
copies. Their changed caller contracts were inspected; historical supervision
tests were not rerun.

| Reviewed file in the bundle | SHA256 |
|---|---|
| `diagnostic/worker.py` | `7b93c55a3e48019164db3f72dbe80cea8fa81f1a9daee1429e7692721bbe104a` |
| `diagnostic/controller.py` | `88b2e3197d9ca6af399ca2b2d8dc188409c524b0eb59933d052f3b5b1ea10c6d` |
| `diagnostic/ordinary_proposal_diagnostic.py` | `7a6b2abaa886bcd5002eced4dde17b277b5d206164fb1ebadfc0e2de0e5cfc30` |
| `diagnostic/ownership_diagnostic_groups.py` | `838ffb1df7389e13fe110a318818c81eb16b7db7932ab03b3af54c8dd938daf6` |
| `source/ownership_exchange.py` | `015781019833ee5a3f49dcec5a189161104003224b1327b44cedda6e084532bb` |
| `source/contact_repair.py` | `c6f9a5555b010d5e877b568c1ee760e72d170f1f7e0c186179de16b53630da85` |

The summary also binds both reused lifecycle helpers. Local execution used
isolated Python 3.10.19 and NetworkX 3.4.2. This is a correctness check, not a
timing calibration.

## Input and scheduling identity

The independent stdlib [input check](../../../results/codex/043-independent-review/input_check_002.json)
verifies all 108 prepared file hashes, the accepted 042 retrieval digest, all
34 treatment identities, all 35 family memberships, and exactly 15,016 entry
qubits. It compares every explicitly ordered entry pair/list to its copied raw
042 record. It independently rederives both graph and arm order from the
unchanged 042 ledger and the prescribed random seeds, obtaining the exact 68
task vector. No family field enters the worker's structural graph objects.

All 105 original-label evaluator files are still present with their accepted
hashes. The portable 043 bundle copies the evaluator manifest; its original
graphs and label maps remain an explicit external 042 dependency. Subsequent
auditing must retain access to that bundle. This check reuses the accepted 042
validity and deletion-closure audit; it does not claim a new physical proof.

Input manifest SHA256:
`32093b458d922b21b5842be4dd14058270c2ca412f77f6ca1e14bcfcf0fc88b2`.
The first input-check attempt wrongly equated the target file's byte hash with
its canonical JSON record digest. The corrected checker validates both against
their proper accepted references. That reviewer-only failure is recorded in
`prepared/freeze001.json`; input preparation and benchmark bytes were unchanged.

## Verified integration boundaries

Both tiny arms independently generate the same complete ordered group vector
and hash. Real outputs are checked against original edges by a separate set/BFS
oracle. Every credited output is a private, valid strict contraction; the input
mapping and list order remain unchanged. Exactly one common gate is invoked
when a proposal exists: inside the ordinary adapter, outside exchange. The
ordinary gate is already included in its method wall and is not charged again.

Fake-clock checks preserve the same absolute deadline through generation,
method and gate; no method allowance is renewed. They reject a late common gate
and a candidate becoming late only after the query returns. The latter retains
its raw and gated evidence while removing credit. Phase wall sums reconcile
exactly to observed common wall. Interrupted work lacking a normal phase-end
assignment remains visible in `administration_and_unclassified_error_work`.
Input, adjacency, graph and group mutations reject otherwise valid proposals.
Generation interruption publishes no partial groups and invokes neither method.

The controller status matrix covers 38 success/failure cases, including fatal
SIGALRM, failure after publication, surviving descendants, missing output,
wrong identity, malformed JSON values/nested fields, nonfinite or huge
timestamps, and contradictory credit. A pre-test static finding was fixed by
root: valid JSON lists/scalars formerly caused `raw.get` to abort the ledger.
The corrected controller preserves them as invalid worker observations and
continues. The mock 68-task run also preserves invalid JSON and refuses restart
without overwriting the completed record.

## Remaining launch and interpretation requirements

Root must bind the final execution manifest, transport inventory, reviewed
protocol and launch helper; the current draft manifest deliberately refuses a
corpus launch. Repeat this portable checker once on the pinned hyde03
interpreter before the single launch. The launch helper's source map must
compare the eight imported files separately from `runner_sha256`, since adding
`diagnostic/checks.py` makes nine manifest files. Root applied this reported
caller correction before final staging; no passed checker or candidate changed.

The inspected outer launch design uses 2,000 seconds plus five-second kill
grace, while each worker has independent 20-second supervision/fatal alarm.
It records a launch attempt before starting tmux, refuses retry and requires
process, lock and supervisor quiescence before inventory. These are static
caller checks, not fresh remote lifecycle evidence from this reviewer.

The final saved-data auditor must enforce exact complete paired group equality,
full final validity and exchange-trace obligations. The controller does not
independently compare two completed group vectors. It preserves separate
observations so generation failures cannot become searched negatives.
Ordinary `expansions` is only a known returned-record prefix when
`routing_accounting_complete` is false; retain null `expansions_exact` and the
unaccounted indices. Do not call that prefix a complete cost.

Five seconds, unequal work-counter definitions, different move domains and the
34 repeatedly exposed entries limit inference. First returned contraction is
not earliest internal discovery. Noncooperative graph copying/sorting can
overrun before final rejection; the process watchdog is a backstop, not free
method time. Neither a successful tiny check nor an exchange-only observation
establishes neighborhood containment, cumulative embedding improvement or
novelty. No unresolved local worker/controller correctness blocker remains at
the reviewed hashes.

Rerun only to a new directory:

```sh
.venv/codex-native/bin/python -I -B results/codex/043-independent-review/checks.py --run results/codex/043-ownership-exchange-reach --out results/codex/043-independent-review/attempt002
```
