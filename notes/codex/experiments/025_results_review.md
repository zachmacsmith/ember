# Experiment 025: contact redundancy on the Ember readiness inputs

Both fixed candidate arms returned timely valid embeddings on all 34 selected
structures. The contact-redundancy objective improves 17 inputs, worsens 10,
and ties on 7 relative to strict qubit reduction. It saves 65 total qubits and
reduces the equally weighted input mean ACL by approximately 0.400%, from
3.493185 to 3.479215. This is a modest development improvement, with material
individual regressions. It does not close the broad gap to MM.

Against the historical MM019 outcomes on the identical inputs, each fixed arm
still has 8 lower-ACL and 23 higher-ACL results among the 31 common timely
successes. Both succeed on the three inputs where MM019 exceeded its deadline.
There are no optimal ties with MM: the five selected inputs where MM019 reaches
ACL 1 remain above 1 for both candidates. One solver seed and one selected
source per represented family cannot establish family means, across-seed
variance, or generalization. No best-of outputs or cross-run timings are pooled.

## Completion, identity, and independent checks

Controller PID 120218 on hyde03 finished at
`2026-09-08T02:51:07.705308Z`. Fresh SSH status confirmed 68/68 finalized
SUCCESS records, controller status complete, lock free, tmux stopped, and
supervisor exit 0. Only then was the full run retrieved to
`results/codex/retrieved/hyde03/025-corpus-contact-rearrangement/`.
The 429-file retrieval inventory passed its hash checks. No run was restarted.

| Identity | SHA-256 / commit |
| --- | --- |
| Frozen commit | `a33a44848d877baf085fb503a98bfdf8b0bcd0e5` |
| Source snapshot | `c4df2294edf74b55f767ee443e30f88d4a068cbed8a21e9b45cf33df420ffb8d` |
| Transport inputs | `dd31a6a2c94f15da08e6549eb8eada585a1e24fbeb9f493b05bad2e8509b5827` |
| Retrieved inventory | `6d4d1d4c8c87d6c2519be9ac982ea4f0fce763448b133aa44b5615e016de523c` |
| Ideal Z12 target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Readiness selection | `06c02356f8df5503b57f280ba4939c298cc05834c563a3da8a71f96fe245db98` |

The ordinary analyzer passed all 68 observations. A separate standard-library
verifier rechecked both transport/retrieval inventories, all 44 frozen source
files, all 68 task digests and result identities, all worker/final result pairs,
and all claims. Every worker field is preserved in its finalized result.
All 68 workers returned exit code 0 without interruption. The recorded worker
span is 833.596294 seconds; consecutive worker intervals do not overlap
(minimum gap 0.002709 seconds).

The independent embedding oracle imports neither the candidate nor the
runner's validator. It verifies exact source-key coverage, nonempty integer
chains, original-target membership, disjointness, connectivity, and every
logical contact using the frozen target's actual edges. It recomputes all
credited ACL, qubit-count, maximum-chain, and within-embedding chain-variance
values. All 68 embeddings pass and all solver wall measurements are at most
60 seconds. There are no late outputs, timeout records, invalid outputs,
initialization/construction failures, or missing results in 025.

The original and readiness sidecar bytes, target bytes, and all 34 source graph
record bytes are identical to those in retrieved 019. Canonical selection
digests, selection IDs, source hashes, normalized topology hashes, node/edge
counts, and source-attribute stripping also pass. The verifier additionally
rechecks the complete historical 019 retrieval inventory before using its MM
quality records and revalidates those MM witnesses against the same graphs.

All 68 candidates report the frozen run's native entry point and
`/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python`.
Every worker passed the package-absence guards, recorded no prohibited import
attempt or loaded embedding library, and reported minorminer absent. Python
and common dependency versions match 019. No MM embedding or competing solver
output is supplied to either candidate.

The retrieved run's `analysis/` contains `independent_review.py`,
`ember_embedding_oracle.py`, `independent_review.json`, `family_report.py`,
`family_results.csv`, and `family_table.md`, alongside the ordinary analyzer's
files. These added analysis files are not part of the original archive inventory.
All frozen source, input, task, witness, log, and sidecar files remain intact.

## Fixed configuration and quality comparison

“Strict” is `native-search-joint1-sites-groups` and “contacts” is
`native-search-joint1-contacts`. Both use the same native constructor, seed 0,
1000 placement evaluations, width one, four refinement passes, 512 group
attempts, sizes 1–4, 500000 refinement work units, 512-qubit region cap,
16 additional boundary sites, round-robin group order, greedy contact trees,
and 60-second solver allowance. Only contacts adds the explicit configuration
`polish_objective='qubits_contacts'`. Each arm uses one fixed configuration on
every source structure.

The strict control reproduces all 34 strict019 final embeddings exactly when
each chain is treated as a set, not merely their ACL values. Construction and
pruned qubit counts also match on every input. This is useful evidence that
the code changes preserved the tested strict behavior at this seed. It is not
a proof for other inputs, seeds, or platforms.

| Fixed arm | Success / attempted | Total qubits, 34 inputs | Mean ACL, same 34 inputs | Mean ACL on the 31 inputs with timely MM019 output |
| --- | ---: | ---: | ---: | ---: |
| Strict025 | 34 / 34 | 15771 | 3.493185 | 2.859913 |
| Contacts025 | 34 / 34 | 15706 | 3.479215 | 2.844822 |
| Historical MM019 | 31 / 34 | undefined on all 34 | undefined on all 34 | 2.961536 |

MM019's three deadline failures remain explicit: complete 1041 and regular
14334 returned valid embeddings late, and spin_glass 37302 did not return a
valid embedding. Their late outputs are diagnostic only and do not enter the
31 common-success ACL comparisons. See `019_results_review.md` for their
full records and interpretation. The common-success subset is selected by
MM's outcome; its mean is not an unconditional all-input quality estimator.

Contacts' largest individual savings over strict are Barabási–Albert (-21
qubits), Kneser (-15), honeycomb (-11), triangular lattice (-7), and grid and
Watts–Strogatz (-6 each). It regresses on SBM (+10), Johnson (+4), wheel (+3),
binary tree (+2), and six structures by one qubit each: hardware-native,
circulant, LFR, the shared frustrated-square/king input, Shastry–Sutherland,
and planted solution. These losses are retained; no input-specific objective
selection is applied.

The contact objective's acceptance of some equal-size rearrangements does not
guarantee a better final qubit count than strict reduction under finite search.
Both arms have the same per-input recorded layout orders, layout ranks,
constructed qubit counts, and pruned counts. Across the 34 inputs, construction
uses 19255 qubits and pruning reduces this to 16370. Refinement saves 599
qubits for strict and 664 for contacts. Both report 22 work-limit stops,
11 group-limit stops, and one no-improvement stop. The observed gain therefore
comes from different refinement trajectories at fixed limits, rather than a
changed constructor or longer deadline.

## Within-run runtime observations

Every trial ran in a fresh process on hyde03 with a separate initially empty
JIT cache and one numerical-library thread. Solver wall includes copies,
construction, pruning/refinement, and first-call compilation; process wall also
includes loading/import/startup and post-call validation. The one-minute system
load at worker start ranged from 11.47 to 16.95. These are shared-host, one-seed
observations, so small speed differences are not established effects.

| Arm | Median solver / process seconds | Mean solver / process seconds |
| --- | ---: | ---: |
| Strict025 | 8.394 / 11.146 | 9.461 / 12.098 |
| Contacts025 | 8.282 / 10.997 | 9.640 / 12.411 |

| Contacts/strict ratio across 34 paired inputs | Mean | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: |
| Solver wall | 1.017609 | 1.004776 | 0.732413 | 1.800416 |
| Process wall | 1.026319 | 1.010977 | 0.752328 | 1.669864 |

The maximum ratio occurs on Kagome, where contacts saves two qubits but costs
1.80× solver and 1.67× process time in this observation. Median overhead is
small, but this should not be described as a guaranteed near-zero cost. No
025/MM timing ratio is reported: MM was not rerun in 025, and changes in host
load and source code separate these experiments. Exact control embeddings
across runs establish quality reproducibility here, not stable timing.

## Family-mapped ledger

Each row is one graph observation at seed 0. `MM019 ACL` is explicitly
historical quality. The time ratios compare only contacts025 with strict025.
Rows marked `*` share the exact input `ember_32616` and the same two candidate
trials; aggregates count this structure once. Its normalized topology hash is
`ad061ab01ea949cfe9e993013fde26052d059f31be29c63a2ef3a93d3a06c1c4`.
Distinct normalized hashes do not establish pairwise non-isomorphism.

The 35 observed family memberships correspond to 34 structures. Sudoku remains
missing because neither inherited manifest entry passes the fixed necessary
Z12 count bounds. No substitute was generated for this run and no Sudoku
solver failure is inferred. The complete original selection/error ledger is
preserved in the sidecar. CSV consumers must aggregate by `graph_key` before
calculating input-level counts or means.

| Family | Selected ID → input ID | n / m | MM019 ACL | Strict025 ACL | Contacts025 ACL | Contacts − strict qubits | Contacts/strict solver / process time |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| barabasi_albert | 10662 | 122 / 472 | 3.3607 | 3.6721 | 3.5000 | -21 | 1.03 / 1.10 |
| bcc_lattice | 33402 | 91 / 216 | 1.2637 | 1.7143 | 1.6703 | -4 | 1.00 / 1.00 |
| binary_tree | 4905 | 127 / 126 | 1.0000 | 1.1654 | 1.1811 | +2 | 0.83 / 0.86 |
| bipartite | 1363 | 126 / 3969 | 6.1587 | 4.4921 | 4.4921 | +0 | 1.04 / 1.06 |
| circulant | 3499 | 134 / 402 | 1.4627 | 1.8433 | 1.8507 | +1 | 0.97 / 0.97 |
| complete | 1041 | 127 / 8001 | TIMEOUT | 9.2913 | 9.2913 | +0 | 0.96 / 0.97 |
| cubic_lattice | 33219 | 125 / 300 | 1.4960 | 1.9600 | 1.9200 | -5 | 1.00 / 1.01 |
| cycle | 1829 | 126 / 126 | 1.0000 | 1.1587 | 1.1508 | -1 | 1.02 / 1.01 |
| frustrated_square * | 32816 → 32616 | 121 / 420 | 1.4132 | 2.3306 | 2.3388 | +1 | 1.02 / 1.03 |
| generalized_petersen | 4083 | 126 / 189 | 1.3095 | 1.8333 | 1.8175 | -2 | 0.98 / 0.98 |
| grid | 1584 | 128 / 232 | 1.0469 | 1.6953 | 1.6484 | -6 | 1.01 / 1.01 |
| hardware_native | 37603 | 128 / 352 | 1.4609 | 2.1875 | 2.1953 | +1 | 0.98 / 0.93 |
| honeycomb | 32367 | 190 / 264 | 1.0316 | 1.7053 | 1.6474 | -11 | 1.03 / 1.02 |
| hypercube | 4755 | 128 / 448 | 3.2969 | 3.5547 | 3.5469 | -1 | 1.17 / 1.18 |
| johnson | 5242 | 120 / 1680 | 9.8750 | 7.3833 | 7.4167 | +4 | 1.00 / 1.02 |
| kagome | 32122 | 131 / 236 | 1.2214 | 1.8244 | 1.8092 | -2 | 1.80 / 1.67 |
| king_graph * | 32616 | 121 / 420 | 1.4132 | 2.3306 | 2.3388 | +1 | 1.02 / 1.03 |
| kneser | 5411 | 126 / 315 | 2.8968 | 3.4048 | 3.2857 | -15 | 1.00 / 1.00 |
| lfr_benchmark | 31357 | 100 / 204 | 1.6000 | 1.9700 | 1.9800 | +1 | 1.02 / 0.98 |
| named_special | 37761 | 46 / 69 | 1.0000 | 1.1522 | 1.1522 | +0 | 0.99 / 1.09 |
| path | 2030 | 141 / 140 | 1.0000 | 1.2482 | 1.2340 | -2 | 1.04 / 1.02 |
| planted_solution | 34404 | 133 / 175 | 1.0226 | 1.3684 | 1.3759 | +1 | 0.84 / 0.98 |
| random_er | 6450 | 133 / 870 | 7.8496 | 6.5564 | 6.5414 | -2 | 1.05 / 1.04 |
| random_planar | 31536 | 152 / 450 | 1.8487 | 2.3421 | 2.3224 | -3 | 1.03 / 1.02 |
| regular | 14334 | 140 / 2800 | TIMEOUT | 9.3571 | 9.3500 | -1 | 0.96 / 1.00 |
| sbm | 30736 | 120 / 625 | 5.3167 | 5.0083 | 5.0917 | +10 | 0.99 / 0.99 |
| shastry_sutherland | 33018 | 121 / 270 | 1.2149 | 1.6694 | 1.6777 | +1 | 1.10 / 1.11 |
| spin_glass | 37302 | 160 / 12720 | TIMEOUT | 11.4625 | 11.4625 | +0 | 1.20 / 1.19 |
| star | 2229 | 127 / 126 | 1.1339 | 1.0709 | 1.0709 | +0 | 1.04 / 1.04 |
| sudoku | no eligible READY input | — | not attempted | not attempted | not attempted | — | — |
| tree | 5058 | 121 / 120 | 1.0000 | 1.1983 | 1.1901 | -1 | 0.81 / 0.84 |
| triangular_lattice | 31879 | 128 / 384 | 2.0859 | 2.7031 | 2.6484 | -7 | 0.73 / 0.75 |
| turan | 3060 | 90 / 2700 | 8.8111 | 5.0778 | 5.0778 | +0 | 0.97 / 0.97 |
| watts_strogatz | 22972 | 174 / 1740 | 13.7931 | 10.0000 | 9.9655 | -6 | 1.03 / 1.03 |
| weak_strong_cluster | 33587 | 128 / 1988 | 3.6797 | 3.3828 | 3.3828 | +0 | 1.07 / 1.14 |
| wheel | 2429 | 127 / 252 | 1.1575 | 1.9843 | 2.0079 | +3 | 0.90 / 0.90 |

## Interpretation and next step

Contact redundancy transfers a small mean-ACL improvement from the earlier
incumbent experiments to these selected end-to-end development inputs, with
10 regressions. It leaves the MM win/loss partition unchanged. Sparse-input
ACL remains substantially worse than MM on many selected graphs, including
the five with demonstrated ACL-1 MM witnesses. The results justify studying
general construction and refinement limitations; they do not justify calling
the method an all-family winner or making family-specific exceptions.

The spectral-initialization protocol and its full input/configuration freeze
were completed before these outcomes were used. After 025 quiescence and
verified retrieval, that already authorized 026 run was started without waiting
for this narrative; its actual launch is recorded in
`026_spectral_initialization.md` and `026_launch_status.md`. It is a separate
fixed comparison with its own contemporaneous control. None of its outcomes
are included in this report.

Reproduction from the retrieved archives:

```sh
.venv/bin/python scripts/codex/analyze_pilot.py results/codex/retrieved/hyde03/025-corpus-contact-rearrangement
.venv/bin/python results/codex/retrieved/hyde03/025-corpus-contact-rearrangement/analysis/independent_review.py results/codex/retrieved/hyde03/025-corpus-contact-rearrangement results/codex/retrieved/hyde03/019-ember-readiness-screen
.venv/bin/python results/codex/retrieved/hyde03/025-corpus-contact-rearrangement/analysis/family_report.py results/codex/retrieved/hyde03/025-corpus-contact-rearrangement results/codex/retrieved/hyde03/019-ember-readiness-screen
```
