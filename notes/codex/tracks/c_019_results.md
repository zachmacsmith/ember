# C019 complete exploratory results

2026-09-10. **Reject fixed C019 and its cardinality ablation.** The weighted constructor has 3/12 timely valid embeddings and nine TIMEOUTs; cardinality has 0/12, all TIMEOUTs. A061 and MM each have 12/12. No class-level promotion or confirmation claim follows. See [mechanism decision](c_019_decision.md).

## Every outcome

Q is total occupied qubits; ACL=Q/source nodes. TO entries show independently checked terminal missing contacts M, followed by diagnostic Q; those partial maps receive no embedding credit. W/C are weighted/cardinality. Times are complete solver wall seconds for W/C/A061/MM; all failed-attempt time is included.

| Input | Seed | W: credited Q or TO(M,Q) | C: TO(M,Q) | A061 Q | MM Q | W−A061 / W−MM | Wall W / C / A061 / MM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| g0013 grid128 | 0 | 164 | TO(17,190) | 168 | 133 | -4 / +31 | 15.676 / 59.502 / 4.682 / 0.261 |
| g0013 grid128 | 1 | 165 | TO(21,171) | 161 | 133 | +4 / +32 | 14.065 / 59.501 / 5.090 / 0.249 |
| g0302 BA96 | 0 | TO(13,310) | TO(189,145) | 290 | 318 | — | 59.500 / 59.500 / 5.438 / 1.421 |
| g0302 BA96 | 1 | TO(9,284) | TO(172,171) | 287 | 271 | — | 59.500 / 59.501 / 5.474 / 5.271 |
| g0304 WS96 | 0 | TO(2,199) | TO(56,168) | 224 | 192 | — | 59.500 / 59.500 / 5.107 / 0.532 |
| g0304 WS96 | 1 | TO(9,224) | TO(46,185) | 227 | 190 | — | 59.500 / 59.501 / 5.248 / 0.589 |
| g0305 SBM96 | 0 | 233 | TO(102,162) | 224 | 225 | +9 / +8 | 51.482 / 59.500 / 5.503 / 1.038 |
| g0305 SBM96 | 1 | TO(15,265) | TO(90,160) | 238 | 217 | — | 59.500 / 59.501 / 5.561 / 0.712 |
| g0307 singleton control96 | 0 | TO(78,262) | TO(282,147) | 266 | 189 | — | 59.501 / 59.500 / 5.770 / 1.474 |
| g0307 singleton control96 | 1 | TO(61,270) | TO(250,150) | 236 | 176 | — | 59.500 / 59.501 / 5.402 / 1.139 |
| g0309 BA96 relabel | 0 | TO(12,301) | TO(160,157) | 267 | 274 | — | 59.500 / 59.500 / 5.664 / 2.833 |
| g0309 BA96 relabel | 1 | TO(2,303) | TO(181,156) | 293 | 287 | — | 59.500 / 59.500 / 5.436 / 3.064 |

The complete gain is grid seed 0: Q164 versus A061 Q168, closing 4/35=11.4% of that A061–MM gap. Preserve it, together with the grid seed 1 +4Q and SBM seed 0 +9Q regressions. All three complete C019 maps are worse than MM. Grid mean ACL exactly ties A061 because the two opposite Q changes cancel; this does not satisfy the row-wise no-regression criterion. No qualifying structure gains in both seeds. BA and its relabel both fail in both seeds, so relabeling supplies no completion rescue and is not an independent topology.

## ACL and variation, with support

Cells give mean ACL / sample variance across credited seeds. A061/MM each have support 2 in every row. C019 support is 2 for grid, 1 for SBM and 0 elsewhere; an unavailable variance is not zero. Cardinality has support 0 throughout. These are exploratory two-seed descriptions, not population estimates.

| Input | C019 support; mean / variance | A061 mean / variance | MM mean / variance |
| --- | ---: | ---: | ---: |
| grid128 | 2; 1.285156 / 0.00003052 | 1.285156 / 0.00149536 | 1.039062 / 0.00000000 |
| BA 96 | 0; — | 3.005208 / 0.00048828 | 3.067708 / 0.11984592 |
| WS 96 | 0; — | 2.348958 / 0.00048828 | 1.989583 / 0.00021701 |
| SBM 96 | 1; 2.427083 / — | 2.406250 / 0.01063368 | 2.302083 / 0.00347222 |
| singleton control 96 | 0; — | 2.614583 / 0.04882812 | 1.901042 / 0.00916884 |
| BA 96 relabel | 0; — | 2.916667 / 0.03667535 | 2.921875 / 0.00916884 |

Within-embedding chain-length variance is a separate measure: C019 grid seeds 0/1 are 0.311523/0.330505; SBM seed 0 is 2.328016. Every per-seed reference and candidate within-chain variance is retained in `mechanism001/output/encoding_statistics.json`, along with support and status. No failed partial-map ACL is averaged.

## Complete cost and validity trajectories

| Method | Valid / attempts | Solver wall sum | Solver CPU sum | Process wall sum |
| --- | ---: | ---: | ---: | ---: |
| joint-star-construction | 3/12 | 616.727 | 616.698 | 627.057 |
| cardinality-star-construction | 0/12 | 714.008 | 713.971 | 724.739 |
| native-branched-path | 12/12 | 64.374 | 64.364 | 72.802 |
| mm | 12/12 | 18.584 | 18.584 | 21.471 |

All 48 attempts have known wall/CPU/process times and no audit errors. Weighted total solver wall is 33.2× MM and 9.58× A061 on the paired host, while losing nine successes. These measured comparisons reject the present cost/quality result; they are not an invented universal runtime gate.

- Grid seed 0 first validates at 14.259s/Q166, then Q165 at 14.581s and Q164 at 14.707s; stops at 15.676s after a completed unchanged quality sweep. It first meets A061 final Q at first validity. One additional equal-Q/R admission is retained between strict-Q events.
- Grid seed 1 first validates at 13.356s/Q165 and stops at 14.065s with no strict-Q improvement; it never reaches A061 Q161.
- SBM seed 0 first validates at 50.988s/Q233 and stops at 51.482s with no strict-Q improvement; it never reaches A061 Q224.
- Every other weighted call and every cardinality call has no first-valid event and stops at the 59.5 s search deadline. These are construction failures, not late valid outputs or failed final validation. The partial terminal states remain connected/disjoint but miss the contacts shown above. All three successful stops are deterministic `valid_policy_exhausted`, not proofs of neighborhood optimality.

## Evidence bindings

Root retrieved the terminal 387-file archive once (25.137s), digest `b6e98fe0dcf009f4d514c63eb893400e7d575ce2e6a1aa9e1ccab7cbd48d2720`; terminal status005 has 48/48 finalized, supervisor 0, controller complete, tmux absent and lock free. Original multi-seed audit first PASS: 4.098 s process, 247 bindings verified by root; summary `120a67d00329d6ef8a28c20345c473b1b253b84abb6a1d1e43f62908bd0c3067`.

Approved passive reader `9cbb23d3e0784bf7b81cae6d5b9ad2f7865b6370889e4537c120d14dc3328205` ran once through unchanged `local_action.py`, first PASS, 15.107 s process/14.967 s analysis, 254 bindings, 0 constructor calls; summary `39fad9c46062ab241a1f78e4800e45c83c4afc4dd71b11da383e1c6994a5ff90`. Original oracle and audit own embedding credit. No new solver, projection, refinement, test or constructor was run after the screen. Interactive inspection only read these already-generated receipts; one display command used a nonexistent summary key and raised KeyError, without changing any evidence or rerunning the reader.

Frozen source snapshot `0a9101a38e6c7ab914c62cd58e1f208d5e9651fcdc8e69ba3368795c3d329dc1`; manifest `b0070af3e2c70fc828b56823f1ecaf4ea759869349665e051226a99ba0125141`; screen `10c1fa683a0ad8d81b5d9fde892038e0702f8a392a168e13e7136b281d0eb96c`. Prepared/check/source artifacts remain unchanged. `results/codex/c019-joint-star/mechanism_completion001.json` binds execution and these outcome notes.
