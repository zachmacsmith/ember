# C003 results: movable connected target regions

C003 produced four timely valid embeddings out of eight inputs. Every one used substantially more qubits than stock MM. The other four candidate calls exhausted the construction allowance with original source edges still missing. This policy reaches the predeclared minimum of four successes, but does not support a quality claim or promotion as a competitive general constructor.

The fixed eight-input development panel, ideal Z12, seed 0 and 15-second per-method allowance are unchanged from C001/C002. Each candidate call was paired with a fresh stock MM process on the same lightly loaded hyde04 host and pinned, separate interpreters. No timing population is pooled across screens. Candidate imports load the new constructor and exact hash-bound V1 structural utilities, with no call to either earlier constructor. MM/busclique are absent from the candidate interpreter and both import-guard lists were empty.

| Family / graph | n | Candidate status | Candidate Q / ACL | MM status | MM Q / ACL | Solver seconds C / MM | Process seconds C / MM |
|---|---:|---|---:|---|---:|---:|---:|
| path / ember_2030 | 141 | SUCCESS | 927 / 6.574 | SUCCESS | 141 / 1.000 | 1.098 / 0.148 | 1.420 / 0.466 |
| tree / ember_5058 | 121 | SUCCESS | 598 / 4.942 | SUCCESS | 121 / 1.000 | 0.843 / 0.120 | 1.117 / 0.365 |
| grid / ember_1584 | 128 | SUCCESS | 1411 / 11.023 | SUCCESS | 134 / 1.047 | 1.775 / 0.340 | 2.019 / 0.616 |
| random_planar / ember_31536 | 152 | SUCCESS | 1633 / 10.743 | SUCCESS | 281 / 1.849 | 5.024 / 0.563 | 5.278 / 0.816 |
| random_er / ember_6450 | 133 | TIMEOUT | — | SUCCESS | 1044 / 7.850 | 14.503 / 8.259 | 14.751 / 8.529 |
| regular / ember_14334 | 140 | TIMEOUT | — | TIMEOUT | 2481 / 17.721 (late diagnostic) | 14.503 / 15.328 | 14.751 / 15.603 |
| complete / ember_1041 | 127 | TIMEOUT | — | TIMEOUT | 2170 / 17.087 (late diagnostic) | 14.503 / 17.268 | 14.752 / 17.609 |
| sbm / ember_30736 | 120 | TIMEOUT | — | SUCCESS | 638 / 5.317 | 14.502 / 4.066 | 14.753 / 4.325 |

The four timely pairs have candidate/MM solver ratios 7.44, 6.99, 5.22 and 8.93, respectively; process ratios are 3.05, 3.06, 3.28 and 6.46. These single observations are descriptive. The path and tree MM outputs attain the absolute ACL=1 lower bound; C003 does not tie it. MM regular and complete outputs are structurally valid but returned after the external 15-second limit, so their Q/ACL values are diagnostic only. The candidate reserves 0.5 seconds for final validation: unsuccessful construction stops at about 14.503 seconds, with no valid complete output or credited quality. This is recorded as TIMEOUT, without asserting a 15-second external overrun.

**What changed and what failed.** The candidate repeatedly contracts adjacent target regions of similar size, preferring smaller connecting cuts among equally sized partners, and greedily assigns source labels to the resulting quotient. It then alternates missing-edge-guided whole-region label exchanges and connectivity-preserving boundary-site transfers in one evolving state. These moves cross every earlier coarsening boundary. All four successful entries initially occupied all 4,800 target sites. Completed deletion passes removed 3,873 / 4,202 / 3,389 / 3,167 sites, leaving Q=927 / 598 / 1,411 / 1,633. The large reduction does not make those final chain lengths competitive. No continuation beyond the first complete minor was attempted.

| Family | Missing edges: initial → best → final | Completed search visits | Committed swaps / transfers | Search seconds | BFS adjacency entries |
|---|---:|---:|---:|---:|---:|
| path | 6 → 0 → 0 | 59 | 16 / 29 | 0.296 | 2,036,042 |
| tree | 1 → 0 → 0 | 4 | 0 / 2 | 0.032 | 378,672 |
| grid | 25 → 0 → 0 | 201 | 49 / 100 | 1.029 | 6,815,472 |
| random_planar | 68 → 0 → 0 | 940 | 91 / 470 | 4.355 | 27,733,675 |
| random_er | 306 → 119 → 119 | 2849 | 88 / 1424 | 14.189 | 87,817,744 |
| regular | 1559 → 1056 → 1056 | 2845 | 47 / 1422 | 14.176 | 87,011,904 |
| complete | 5349 → 3716 → 3716 | 2201 | 1101 / 1100 | 14.153 | 80,174,368 |
| sbm | 187 → 37 → 37 | 2985 | 105 / 1492 | 14.200 | 89,198,272 |

The four failed states retain valid nonempty, disjoint, connected ownership regions covering all 4,800 target sites. Independent original-edge recounts find exactly 119/870 missing edges for random_er, 1,056/2,800 for regular, 3,716/8,001 for complete and 37/625 for sbm, agreeing with saved final diagnostics. They are not minor embeddings of the original graphs. Their initial/best counts and work histories are algorithm diagnostics; earlier complete ownership states were not saved and cannot be independently replayed from those counters.

Target coarsening took 0.170–0.228 seconds and assignment 0.053–0.100 seconds. All eight completed both. On failed inputs the search consumed about 14.2 seconds, and the recorded BFS work alone reached 80–89 million adjacency entries. BFS counts include initialization/validation where used; this is not a measured attribution of every CPU second to BFS. Safe transfer eligibility and articulation checks also contribute. Every failed final visit retains its attempted/scored prefix in the counters; completed visit counts exclude a deadline-interrupted visit. No accounting makes rejected work free.

**Decision and next hypothesis.** Retain the finding that removing irreversible physical partitions can recover sparse construction. Reject full-target occupancy followed only by deletion as the current route to low ACL. A subsequent candidate should introduce compactness before it fixes logical contacts and should avoid repeatedly traversing the whole physical target to guide one site. More time or seeds alone would not address the observed four-way quality loss. Any such revision needs its own pre-code hypothesis and fixed-policy falsifier; no C004 policy or new run is implied by this report.

The movable-region/annealing framework is established prior art. PSSA already uses whole-region swaps and adjacent site shifts scored by represented input edges; see [Sugie et al., Section 3](https://arxiv.org/html/2004.03819). C003 tests its light-edge target coarsening and particular allocation/search policy, without a supplied clique embedding. Novelty remains unresolved. The evidence covers eight repeatedly used development instances and one algorithm seed: it establishes neither family means nor variance across solver seeds, clean generalization, or a publication result.

**Checks and provenance.** Six targeted synthetic test groups passed in 0.067 seconds: complete tiny-source coverage, independent coupler/missing-edge recounts for every region swap and 80 safe transfers, distance/articulation cache checks, target contraction invariants and deadline handling. The one affected standalone pilot adapter check also passed. The saved-data auditor was frozen before result records were read and ran once after quiescent retrieval; it passed all 158 archived hashes, all 16 original-label embedding validations/status/quality checks, and every saved failed ownership/missing-edge check. It imports only the existing independently reviewed embedding oracle, never the constructor or MM. The known dwave-networkx deprecation warning occurred during initialization; it was not a trial failure. A prestart observer attempted to store an absent session ID after a successful zero-attempt observation; this was recorded, caused no start, and did not alter the run.

Controller 161288 started at Unix 1788890077.0762842 and completed at 1788890194.304034. Fresh terminal status showed complete, 16 finalized trials, free inherited lock, stopped tmux and supervisor exit 0 before retrieval. The retained last-worker active record is historical, not a live worker claim. The host was reused from earlier quiescent C runs, without modifying shared services or environments.

- Runtime source snapshot: `3d74829a60b4896c6b6e27cdb366468e5bab9114f854abf1ddc279a02a1602fb` (59 files).
- Main candidate SHA256: `4fc12515fb088be951e8270dad0bc06d64b49a1b9db86037d4592776c507fec1`.
- Frozen pilot SHA256: `1b281a9a500ac6f25ca442200ea3179c7a12cb0f79a3ed7fdba2b05e92145d83`.
- Transport digest: `b030eca28b5d8783f5440ce16c4b38af25962476af9214226df0b081f70557af`.
- Retrieved archive digest: `f93773d6a223abeba9f17eb1a5020e742e12044358affe8886f2cd420fce245b`.
- Full results: `results/codex/track-c-003/review/results.json`.
- Exact audit: `.venv/codex-native/bin/python -B results/codex/track-c-003/review/analyze.py <fresh-output.json>`.

The snapshot records repository revision `823849a0b6e8f0b15e506b9728fc7cbdde61fa82`; new C003 bytes were not yet committed at initialization and are bound by the source-file map instead. The target bytes are identical to C001/C002; its canonical content digest is `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`. The separately recorded raw target-file SHA256 is `c683ae784e2ee9a1d14f0760368deaa5cfeee2c47a6c2eade683e5412e61177c`; these are different encodings of the same frozen record, not different targets.
