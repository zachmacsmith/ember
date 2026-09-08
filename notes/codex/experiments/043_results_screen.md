# 043 exploratory first-contraction screen

2026-09-08. **The current ownership-exchange allocation shows no additional first-contraction reach over ordinary reconstruction on these entries.** Ordinary returned 17 credited contractions; exchange returned three, all on inputs where ordinary also returned one. This is a development diagnostic, not a full embedding comparison or a novelty result.

The minimal screen passes: all 68 task rows are retained, all 20 credited outputs are valid against the original source labels and original target, and every one of the 34 completed paired group vectors and hashes agrees. The screen reused the accepted 042 original-label decoder and minor validator. No trace replay, constructor, MM call or additional solver run occurred.

| Paired credited outcome | Inputs |
|---|---:|
| Both | 3 |
| Ownership only | 0 |
| Ordinary only | 14 |
| Neither | 17 |

| Arm | Contractions | No contraction | No groups | Work limit | Common wall, total | Process wall, total | Groups inspected |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ordinary | 17 | 12 | 2 | 3 | 24.774 s | 31.704 s | 8,715 |
| Ownership | 3 | 0 | 2 | 29 | 20.760 s | 28.402 s | 119 |

Both arms had zero deadline, invalid-output or process failures. All work totals are known: ordinary used 4,093,011 routing expansions; exchange used 37,085,183 elementary units. These are different counters and must not be compared as equal operations. Worker phase costs reconcile to common wall; nested method/gate costs are not added again.

Exchange hit 1,250,000 units on 29 of 32 nonempty-group inputs. Its maximum common wall was only 0.900 s of the allowed five seconds (median 0.654 s); ordinary maximum was 3.118 s (median 0.488 s). The exchange cap sharply limits coverage: it inspected 119 groups in total, at most 36 on any input, versus ordinary’s 8,715. This supports reconsidering the allocation or implementation cost; it does not show that an enlarged search would help. The 12 ordinary no-contraction rows finished the supplied sequence, but individual routing calls remained capped. Neither arm’s negative result proves neighborhood infeasibility.

Ordinary’s returned proposals reduce Q by one on 16 inputs and by two on one; each exchange proposal reduces Q by one. These independent first-return reductions are not a realized cumulative embedding gain. The timing totals compare the fixed observations on hyde03, with unequal search coverage; they do not establish a faster useful algorithm.

All 34 input rows follow the frozen order below. `C1`/`C2` mean a credited reduction by one/two qubits; `N` means no contraction returned after the supplied group sequence; `W` means global work cap; `G` means no eligible groups. Seconds are complete common wall. The shared king/frustrated-square structure has two memberships and one aggregate input. Original Sudoku absence is unchanged.

| Input | Membership(s) | Entry Q | Ordinary | O seconds | Ownership | X seconds |
|---|---|---:|---|---:|---|---:|
| ember_6450 | random_er | 887 | C1 | 0.484 | W | 0.728 |
| ember_31536 | random_planar | 300 | C1 | 0.251 | C1 | 0.183 |
| ember_32367 | honeycomb | 273 | C1 | 0.304 | W | 0.669 |
| ember_3499 | circulant | 198 | C1 | 0.479 | W | 0.682 |
| ember_32122 | kagome | 166 | C1 | 0.233 | W | 0.683 |
| ember_1041 | complete | 1180 | N | 3.102 | W | 0.792 |
| ember_4083 | generalized_petersen | 210 | C1 | 0.281 | C1 | 0.452 |
| ember_14334 | regular | 1303 | W | 1.629 | W | 0.817 |
| ember_37603 | hardware_native | 250 | C1 | 0.322 | W | 0.636 |
| ember_2030 | path | 141 | G | 0.052 | G | 0.052 |
| ember_37302 | spin_glass | 1835 | W | 3.118 | W | 0.900 |
| ember_1363 | bipartite | 566 | N | 1.228 | W | 0.694 |
| ember_10662 | barabasi_albert | 443 | C1 | 0.329 | W | 0.623 |
| ember_37761 | named_special | 50 | N | 0.289 | W | 0.670 |
| ember_30736 | sbm | 613 | N | 1.059 | W | 0.706 |
| ember_1829 | cycle | 126 | G | 0.054 | G | 0.054 |
| ember_2229 | star | 137 | W | 1.364 | W | 0.638 |
| ember_5058 | tree | 134 | N | 0.498 | W | 0.642 |
| ember_33402 | bcc_lattice | 152 | C1 | 0.307 | W | 0.644 |
| ember_31879 | triangular_lattice | 286 | N | 0.554 | W | 0.647 |
| ember_5242 | johnson | 842 | C1 | 1.413 | W | 0.701 |
| ember_32616 | frustrated_square/king_graph | 242 | C1 | 0.527 | C1 | 0.162 |
| ember_3060 | turan | 460 | N | 1.233 | W | 0.661 |
| ember_4905 | binary_tree | 138 | N | 0.466 | W | 0.646 |
| ember_33018 | shastry_sutherland | 162 | N | 0.529 | W | 0.694 |
| ember_1584 | grid | 173 | N | 0.563 | W | 0.669 |
| ember_22972 | watts_strogatz | 1699 | C2 | 0.935 | W | 0.860 |
| ember_4755 | hypercube | 453 | C1 | 0.408 | W | 0.633 |
| ember_33587 | weak_strong_cluster | 427 | N | 0.877 | W | 0.666 |
| ember_5411 | kneser | 415 | C1 | 0.492 | W | 0.623 |
| ember_34404 | planted_solution | 145 | C1 | 0.318 | W | 0.694 |
| ember_33219 | cubic_lattice | 222 | N | 0.551 | W | 0.624 |
| ember_2429 | wheel | 199 | C1 | 0.247 | W | 0.593 |
| ember_31357 | lfr_benchmark | 189 | C1 | 0.278 | W | 0.621 |

Artifacts: [summary](../../../results/codex/043-results-review/screen001/summary.json), [all 68 rows](../../../results/codex/043-results-review/screen001/rows.json), [paired rows](../../../results/codex/043-results-review/screen001/pairs.json), and [standalone screen](../../../results/codex/043-results-review/screen.py).

Archive: `cd76579c1c02a97c6ec2cad033c9a5ada176ca10a342eca3690a9f3684a31358` (496 files). Execution manifest: `d9964b0deee8ce679781257ee451b3589ed01546718d35258ace4af516b1e572`. Screen source: `72cd3c38ab7b18fb0a8a57730952fb81143c05d48ccf4220a651e049bcd1245b`, frozen before reading these outcomes. Original-label evaluator manifest: `55de041ac01eca4763d5e9d9c0ed8d24ea01bb983ad39d18c0fe3d1bb7a2072a`. Root supplied the quiescent archive; the screen checked its inventory and reused the original-label files.

Trace/admission/ranked-child replay is explicitly deferred under the revised experimental workflow. Valid final output proves the returned minor and Q, not every saved intermediate search assertion. No claim about new instances, all graph families, final ACL, or advantage over MM follows from this screen.

```sh
.venv/codex-native/bin/python -I -B results/codex/043-results-review/screen.py --archive results/codex/retrieved/hyde03/043-ownership-exchange-reach --archive-digest cd76579c1c02a97c6ec2cad033c9a5ada176ca10a342eca3690a9f3684a31358 --out results/codex/043-results-review/screen002
```
