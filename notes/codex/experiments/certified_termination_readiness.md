# Degree gates do not exclude any of the 34 current inputs

This is the authorized **read-only** first diagnostic from
[the certified-termination design](../certified_termination_design.md).
All 34 saved 036 final embeddings validate against their original Ember graphs.
Two attain the exact connected-chain degree lower bound. All three proposed
degree-capacity gates pass on every input, so they would prevent **zero** extra
certification conversions in this corpus.

No constructor, initialization, prefix search, conversion, pruning, refinement
or MM call was made. No production source changed. These results do not authorize
or measure an early checkpoint, and do not change experiment 037.

## Recomputed target and why all gates pass

The target has 4800 vertices, 45864 undirected couplers and maximum degree 20.
Its degree histogram, computed from physical edges, is:

| Degree | Physical vertices |
|---:|---:|
| 10 | 32 |
| 11 | 32 |
| 12 | 320 |
| 18 | 368 |
| 19 | 368 |
| 20 | 3680 |

For each original source vertex, the verifier computes
`ell_v = max(1, (d_v - 2 + 17) // 18)` with integer arithmetic and sums L.
The 34 values of L range from 46 to 1440; 13 inputs have L greater than their
source vertex count. No input fails the size condition L<=4800, individual
degree-sum capacity, total degree-sum capacity, or distinct singleton degree
eligibility. Full vertex requirements, available capacities, slacks and every
singleton threshold are retained in
[bounds.json](../../../results/codex/certified-termination-readiness/final/bounds.json).

The non-rejection is explained by the relaxation itself, rather than merely by
the observed final embeddings. There are 3680 maximum-degree sites, more than
every L. Consequently, the sum of the largest k target degrees is exactly 20k
for every queried k<=L. The definition of ell_v already ensures
`d_v + 2*(ell_v-1) <= 20*ell_v`, so individual capacity and its summed inequality
pass automatically. Every ell_v=1 vertex has d_v<=20, and their total number is
at most n<=L; distinct maximum-degree sites therefore also satisfy the singleton
degree-only assignment relaxation. Physical adjacency between those sites is
not tested. This argument is general to a target with at least L sites of its
maximum degree; it uses no source-family condition.

An independent mathematical check by `/root/literature` agrees with this
automatic-passage argument. It is separate from the physical-witness validation.

Thus these degree gates provide no discrimination on the present intact Z12
inputs. Their soundness does not imply a useful reduction in checkpoint cost.

## Existing final certificates

A valid embedding with Q=L has globally minimum qubit count. The independent
validator checks original source coverage including isolates, nonempty integer
chains, target membership, unique ownership, connectivity and every original
logical edge. It recomputes Q and also checks each actual chain's internal and
boundary edge counts against the degree argument. Recorded Q, ACL, maximum chain
length and within-embedding variance agree with the recomputation.

| Saved run | Candidate calls validated / timely | Q=L certificates | Certified inputs |
|---|---:|---:|---|
| 036, seed 0 | 34 / 34 | 2 | cycle `ember_1829`: Q=L=126; path `ember_2030`: Q=L=141 |
| 032, seeds 0–3, separate historical replication | 136 / 136 | 8 | The same two inputs, every seed |

All ten historical certified calls used 1000 layout evaluations. These final
witnesses do not reveal whether their initial or any earlier layout could
already have produced an optimum. The other 32 outputs in 036 exceed L by
4–1463 qubits; the other 128 outputs in 032 exceed it by 3–1463. A positive gap
does not prove that a better embedding exists or that the bound is attainable.
The two runs use different frozen source revisions and are not pooled into an
estimate of runtime or seed variability.

Every per-input bound and observed result is retained in
[results.csv](../../../results/codex/certified-termination-readiness/final/results.csv).
The full independent chain checks are in
[observations.json](../../../results/codex/certified-termination-readiness/final/observations.json).
Family names in this report identify observations only; the gate and validation
code reads graph adjacency and does not dispatch by name or metadata.

## Provenance and safe reproduction

The artifact directory is
`results/codex/certified-termination-readiness/`.
Its 450 copied input files total 15,885,330 bytes: original Ember records and
label maps for all 34 inputs, normalized graph records, the target, corpus
sidecars, the frozen design, both run manifests/controllers, and 170 candidate
task/result pairs. No MM result was read or copied. The freeze step also
rehashed the 46 source files in 036 and 45 in 032 against their saved manifests;
it never imported them.

Original raw graph hashes match the original corpus selection. Reconstructing
original adjacency through the saved label maps gives exactly each normalized
solver input, including isolates. Target and normalized source bytes are
identical between the two runs. Saved task/source/target identities, seed coverage
and configuration identities are checked. The source snapshots remain separate:

* 036: `56338bafc7038d75001fe9fd36b067f246dc13ab796a2fdd29ded59b3226f243`.
* 032: `89a3e77bf1df22a7eea436e42f0bc04c81055e098d7baf78c632a76224046994`.

The original-source freeze script is
[freeze_inputs.py](../../../results/codex/certified-termination-readiness/freeze_inputs.py).
It is write-once and intentionally refuses to replace the existing input
directory. Use the standalone
[verify.py](../../../results/codex/certified-termination-readiness/verify.py)
for an additive rerun against the frozen inputs:

```sh
.venv/codex-native/bin/python results/codex/certified-termination-readiness/verify.py results/codex/certified-termination-readiness/root_repeat
```

Choose another fresh output directory if `root_repeat` already exists. The
verifier uses only the Python standard library and blocks imports of the
candidate package, MM/busclique and scientific graph/numerical packages. The
audit ran under the isolated native Python 3.10.19 environment. Its own runtime
is not an embedding performance measurement. All input bytes are rehashed on
each verification; the original final outputs and previous analyses stay intact.

The [input index](../../../results/codex/certified-termination-readiness/inputs/index.json)
has SHA-256
`4a87d29677484f2fabf9d942defb766803fd09873e0c4462ab7546ab2f4556fd`.
The digest of its file-hash mapping is
`1461aef88fbfb52e52b1e01b1a74824cbaecc3b8e5a0dcf733c040dd21c36739`.
Verifier SHA-256 is
`2d10c498c391b42ab41387ecc524960f948835e094ca9828b0b9222ae3cd023a`.
The [summary](../../../results/codex/certified-termination-readiness/final/summary.json)
contains the complete audit outcome, with output hashes in
[artifact_hashes.json](../../../results/codex/certified-termination-readiness/final/artifact_hashes.json).

The negative gate result limits the proposed precheck's usefulness on this
corpus. It neither falsifies the optimality certificate nor supplies evidence
for spending time on an early physical check. That remains an unmeasured,
separately reviewed hypothesis.
