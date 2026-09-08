# Reduced-core prototype implementation

The isolated `reduced_core_construction.py` module implements the accepted 049
journal/requirement graph and one expansion with pinned B003 primitives. Native
is imported eagerly, and is unchanged. An edgeless core avoids native invocation
and JIT work, not import cost. A nontrivial core receives one remaining relative
timeout; the wrapper rejects any return after its original absolute deadline.
The inherited 20M adjacency-scan limit is shared across setup, reduction,
expansion, and validation. Other operations remain charged to elapsed time.

Initial attempt001 completed nine targeted test groups with no prohibited
imports. Z12 reach falsifiers all succeeded: degree-127 star Q138, degree-127
wheel Q235, and once-subdivided K5 Q18. Their one-process diagnostic times were
1.06, 4.72 and 1.83 seconds respectively; these are not fresh-process benchmark
comparisons. The native core runs only for the subdivided K5. The deliberate
P4 fixed-core missing-detour case fails truthfully, while an independently
written alternative placement validates. Initial source/test bytes and all
observations are retained under `reduced-core-checks/attempt001`.

## Pre-change review clarification

Before changing the initial implementation, root identified two bounded issues.
First, a native failure's top-level `partial_embedding`, error and other fields
must survive alongside status and `diag`; the wrapper must retain that failed
response as diagnostic evidence without adopting it. Second, removing recorded
fill edges relaxes obligations of their endpoints even when insertion does not
change those chains. After the one selected B003 insertion, call its same safe
pruner on **only the endpoints of that step's removed fill edges**. If it changes
chains, validate the resulting partial minor against the same trial requirement
graph, within the original deadline, before the joint commit. Preserve pending
extension ports through the inherited pruning rule. This is cleanup of released
requirements, not a global postprocessor, alternate constructor, or new cap.
A tiny C4 target / three-source path fixture will check the previously untouched
endpoint becoming safely reducible; a failed core fixture will check evidence
retention. The initial attempt remains unchanged.

## Final bounded check result

Attempt002 passes all 11 focused groups in 7.232 seconds, with no prohibited
imports and unchanged source hashes. It includes the two review corrections,
original-edge validity, exact nested-fill recovery, input nonmutation,
components/isolates, fixed core configuration and one-call behavior, work stops,
late-core rejection, and interruption immediately before an insertion commit.
No shared native code changed, and no broad native regression was run.

| Fixed Z12 source | Vertices | Edges | Hub degree | Final Q | Hub chain | Core calls | Wrapper seconds | Scans |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Star with 127 leaves | 128 | 127 | 127 | 138 | 11 | 0 | 1.07791 | 1,559,996 |
| Wheel with 127 rim vertices | 128 | 254 | 127 | 189 | 15 | 0 | 4.47898 | 6,375,877 |
| Each K5 edge subdivided once | 15 | 20 | — | 17 | — | 1 | 1.62810 | 236,592 |

All three reach falsifiers complete and independently validate against their
original graphs. Both hubs exceed the necessary seven-site lower bound. The
wheel's endpoint cleanup saves 24 sites directly and changes later expansion;
the final 46-Q improvement from attempt001 is therefore not attributed solely
to those 24 deletions. The subdivision saves one site through that cleanup.
These are sequential local correctness diagnostics with a 20-second allowance,
not paired fresh-process timing measurements. Native's only real call is the
five-vertex residual K5; its measured core wall is 1.48203 seconds.

Validation is included in total work/time: 0.69185 seconds for the star,
1.06012 for the wheel and 0.01007 for the subdivision. It includes completed
private B003 alternatives as well as retained states; it is not a committed-only
cost. Likewise `staged_extension_sites` and `staged_pruned_sites` count private
proposal work and must not be interpreted as net final growth or savings.
`released_fill_qubits_pruned` in the committed update list is the exact local
extra-cleanup Q difference for that adopted insertion. Per-stage scans sum to
`scan_count`; phase wall partitions the main body, while `validation_wall` and
`core_wall` are overlapping diagnostic subtotals, never additive to phase wall.
Parameter/publication overhead remains in the full `wall` measurement.

The wrapper returns no complete credited embedding on failure or timeout.
Committed partial chains and their exact active requirement graph are retained;
late complete native output and top-level failure data remain explicitly
unadopted diagnostics. Final original-graph validation remains required by the
pilot. Core's relative inner clock can end later than the outer deadline; the
outer gate rejects that result, and no retry or alternate constructor follows.

Implementation SHA: `b0f3f6dd238cd7fbee625e5d2687a54bb058ad92a2116cfe96e227edd922db5c`.
Tests SHA: `1b3cc92d418b330d830e22e524993da130f149698c2e2173c733e1373a435c2c`.
Pinned B003 SHA: `b94ff1e9d9a2384cbdb2fcccd7250af770c3758e579849569861932a6483062c`.
Unchanged native SHA: `496b54221c2ea77710dc6979fc7f9a202af995c51d029134bdbe6b703764a225`.

Rerun only when warranted, into a new immutable attempt directory:

```sh
.venv/codex-native/bin/python -I -B results/codex/reduced-core-checks/run_checks.py results/codex/reduced-core-checks/attempt003
```

No MM/busclique, saved embedding, Ember corpus, remote call, or alternative
constructor is used in these checks. Fixed fixtures and target bytes were
written and hashed before each attempt; both attempts are retained.
