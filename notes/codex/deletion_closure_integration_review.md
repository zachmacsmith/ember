# Independent review of final deletion integration

2026-09-08. No implementation blocker found. The independent integration suite
passes **12 unittest groups**, including 16 exact legacy/default/off replays.
All 20 files in the author's final manifest match their declared SHA-256 values
before and after execution. No production file was changed during this review.
No corpus output, 041 outcome, constructor, remote machine or embedding search
was used. The separately accepted exhaustive closure-core audit was not repeated.

## Source and contract review

I read the full [integration specification](deletion_closure_integration_spec.md),
[author implementation note](deletion_closure_integration_implementation.md),
native source, pilot delta and focused author tests. The inspected bytes are:

| File | SHA-256 |
| --- | --- |
| `native.py` | `49a2175874b4b0c65f2ddccde519e8905ae7fc3836e15e2a7c478b37f91e5c57` |
| `pilot.py` | `fedbdf4dc60c78bb357c93c465eda50e5eb403c888dc4e70f6255bf90666f5b9` |
| Frozen closure core | `66a2bc21af6c035ca0b03f9065e2ce780ca0503b9be1af95487eb19e6be67d8b` |
| Author artifact manifest | `ed1594e147221363cd9e15be3fa64da638690be683d3872680b26d0f86dafc20` |

The off path adds only policy control flow; it does not import the closure,
scan cleanup state or emit cleanup diagnostic keys. The supported enabled
combination is checked before construction, including disabled refinement and
empty-source requests. Actual graph types, loops and ordinary integer target
labels are checked; source labels retain native's existing canonical adapter.
`build_adjacency` copies the supplied target's full neighbor lists. The preceding
validity predicate reads the original target directly, not this routing cache.

The enabled wrapper preserves the initial prune and the single contact call.
It independently validates the contact return, invokes the closure at most once
with the same absolute deadline, retains the actual core flags/trace, and then
restores original labels before native's final original-graph check. Zero contact
savings and a contact group/work stop do not suppress cleanup. Time is not renewed,
and contact expansion accounting is not reused to describe cleanup scans.

The accepted core contract is important: an interruption before copying can
return the unchanged input alias with `input_validated=False`. The wrapper's
separate successful entry check establishes that input's validity without
rewriting the core's local flags. Later interruptions return the complete private
prefix, preserving already committed deletions. A completed closure can still
lead to native `TIMEOUT` or a final validation failure; the wrapper keeps those
statuses distinct. Known nested costs remain visible on caught exceptions.

The pilot adds one fixed arm, equal to the spectral-contact control plus
`final_cleanup='deletion'`. Every preexisting configuration is unchanged,
including omission of an explicit off option from the control. No algorithm
selection, second initialization, saved embedding input or external embedding
call is introduced.

## Independent executed evidence

The [portable verifier](../../results/codex/deletion-closure-integration-independent-review/verify.py)
uses standard-library `unittest` and the pinned candidate dependencies, without
pytest. Its SHA-256 is
`e3e6e1d80b051ee427b05d736fa2a8b91316bdd62271393c82edaae48615ef36`.
The successful run is `attempt003`, with summary SHA-256
`2b17c6e8c82f60bb0753e8fa6a058c06d1fab00c09e5d3c5eea42239c6b51e74`.

The primary fixture is different from the author's: a logical path of three
vertices plus an isolate, with tuple/string/integer source labels and a small
physical graph. Inert conversion/pruning/contact adapters expose actual native
wiring; the real closure executes. This arbitrary target is marked as Zephyr
only to pass the native entry boundary while geometry is mocked. It is not a
physical-Zephyr construction test. The saved fixture, test code and source hashes
make that distinction explicit.

An independent predicate scans the full original physical edge set to check exact
source coverage, nonempty connected chains, disjointness, membership and every
logical edge. A separate full-global-sweep reference recomputes that predicate
for each deletion. It agrees with the actual closure's final ordered lists and
complete `(round, source, qubit, old_size, new_size)` sequence. The measured test
arithmetic is construction 9, initial prune 8, contact return 7 and final 4 qubits;
the three cleanup deletions are separate from the one contact deletion. Reversing
the actual trace reconstructs the entry chain sets and validates every recovered
state. Every individual deletion from the final fixture is invalid.

The suite additionally covers:

* 16 exact result-envelope comparisons against preserved pre-integration native
  source: default and explicit off across eight normal, disabled, invalid-option,
  injected-error and controlled-deadline cases. Cleanup imports are rejected on
  these off calls. These are deterministic wiring replays, not real-time claims.
* All enabled deadline skip stages, disabled-refinement precedence, empty source,
  and zero contact savings. A separate `timeout=None` call passes `None` unchanged
  through every observed deadline-bearing stage.
* Eight independently malformed contact outputs: foreign site, disconnected
  chain, missing contact, empty chain, repeated site, overlap, missing source and
  extra source. None reaches the closure. The explicit invalid-input flag is
  tested separately from independent entry validation.
* Actual-core expiry during copying and just before each of three commits.
  The alias/private distinction, native entry certificate, saved earlier
  deletions, final validity and final timeout all agree.
* Original final validation rejection, a late but physically valid final result,
  and exceptions in contact, entry validation and the closure call. A deliberate
  corrupt-module-output check confirms that foreign sites or missing physical
  contacts are rejected by the original final validator.
* Early policy/graph/target-label guards, unknown fields on an unreached pipeline,
  full contact-diagnostic preservation, one fixed pilot delta, and graph/entry
  nonmutation throughout the fixtures.

The successful run used `.venv/codex-native/bin/python`, NetworkX 3.4.2, NumPy
2.2.6, Numba 0.65.1, SciPy 1.15.3 and dwave-networkx 0.8.19. MM distribution
metadata is absent. No external MM/busclique import was attempted or loaded.
The roughly 0.95-second audit wall is verification cost, not solver speed evidence.
The author's separately verified 34 focused/189 broader checks include its actual
tiny Z3 smoke; I did not repeat those counts or describe that smoke as independently
executed here.

## Preserved reviewer failures and scope limits

`attempt001` stopped before test execution because my initial import guard matched
the internal `ember_qc.algorithms.minorminer` registration wrapper. Its embedding
package imports are lazy. I restricted the guard to external package roots,
matching the isolated pilot rule; this does not permit an MM call. The original
verifier and an explicitly labeled record of the observed startup failure remain.

`attempt002` had one failed expectation: an injected extra canonical source key
causes the existing label-restoration comprehension to raise `IndexError`, yielding
native `ERROR` with an empty embedding before final validation. I had incorrectly
expected `INVALID_OUTPUT`. The final test requires the observed safe failure and
separately exercises original final validation for label-restorable corruption.
This deliberately invalid replacement is outside the frozen core's contract.
No production source changed to obtain the passing run.

The review establishes bounded wiring correctness, not minimum Q, a runtime gain
or population-level ACL improvement. Full validators/container operations remain
cooperative and can cross a deadline. Enabled prerequisites consume time before
construction; a binding clock can therefore change the pre-cleanup trajectory.
Fake-clock off replays do not establish production timing equality. Root's future
full-pipeline comparison must retain failures, late embeddings, stage differences
and closure costs rather than infer a benefit from fixture savings.

Safe repeat from the repository root, choosing a fresh output directory:

```sh
.venv/codex-native/bin/python -I -B \
  results/codex/deletion-closure-integration-independent-review/verify.py \
  results/codex/deletion-closure-integration-independent-review/root_repeat \
  --repo "$PWD" \
  --reference-dir "$PWD/results/codex/deletion-closure-integration-checks/reference"
```

The explicit repository/reference arguments make the harness portable; the
20-file author manifest and its referenced files must accompany a target-host
repeat. The harness refuses an existing attempt directory. Root retains source
freeze, target-host verification, launch and promotion authority.
