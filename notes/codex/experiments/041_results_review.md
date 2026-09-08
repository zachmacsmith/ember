The endpoint-support policy produced a small mean-ACL improvement in experiment 041, with six regressions and a measured runtime increase. All 68 calls returned timely valid embeddings. Across the fixed 34-input development set, endpoint support lowered ACL on nine inputs, raised it on six, and tied on nineteen. Total Q changed from 15,059 to 15,050; arithmetic mean per-input ACL changed from 3.3351353061 to 3.3328938601 (−0.0022414460, approximately −0.0672%). This is limited evidence for further investigation, not a broad improvement or completion of the project objective.

The independent saved-data audit passed without errors or corrections. It did not call an embedding algorithm, converter, MM or busclique. The frozen executable and full tables are in `results/codex/041-results-review/analysis001/`; `summary.json` records the result, `pairs.json`/`.csv` retain all 34 comparisons, and `memberships.json`/`.csv` retain all 35 evaluation memberships. `details.json` preserves every raw diagnostic and independent physical check. The shared King's/frustrated-square topology contributes once to totals. Original Sudoku remains explicitly absent in `missing_original_families.json`; no supplemental graph replaces it. These inherited inputs are development data, with one instance per represented membership and one solver seed. Their arithmetic mean is not a family population mean; one seed cannot estimate across-seed ACL variance.

The two arms were `native-search-joint1-contacts-spectral` (control) and `native-search-joint1-endpoint-support-spectral` (endpoint). Both used ideal Z12, spectral construction, 1,000 layout asks, existing pre-refinement pruning, beam width 1, greedy trees, four refinement passes, 512 groups, group sizes 1–4, round-robin visits, 16 boundary sites and 500,000 routing expansions. The only configured change was `polish_objective='qubits_contacts'` to `'qubits_endpoint_support'`. There was no final deletion pass, star relocation, direct singleton policy, restart or selection among independent methods. An unused deletion-closure module was present in the snapshot but unreferenced by both arms. Lazy scoring and deadline checks make this a complete scoring-policy comparison; equal routing allowances do not make total work identical.

Each call ran serially on hyde03 in a fresh native Python process with a private initially empty JIT cache, fixed single-thread settings, a common 60-second solver deadline and 90-second process watchdog. The candidate environment lacked MM; saved package, interpreter, module-absence, source and task guards all passed. The native interpreter was `/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python` (Python 3.10.12; NetworkX 3.4.2, NumPy 2.2.6, SciPy 1.15.3, Numba 0.65.1, dwave-networkx 0.8.19). This screen has no MM arm.

The run was launched once under controller 150200 at 2026-09-08 09:07:16.175 UTC and finished at 09:15:23.430 UTC. Root's subsequent terminal observation found the controller and last worker absent, no matching run process, a free inherited lock, stopped tmux and supervisor exit 0. All 68 worker and controller-finalized records exist. No timeout, invalid output, process error, partial final record or unmatched outcome was omitted; the common timely-valid population is the entire planned set. The observed worker span was 487.2508 seconds with a minimum interworker gap of 0.00239 seconds.

Before reading outcomes, the auditor verified the exact 435-file retrieved inventory, digest `0216429b5820b8ea81f161f8e769180fdf10d99d561e4e0ac127f42e511f38a5`. It then checked all 156 transported inputs, 50 source files, manifest and task identities, all 105 evaluator/ledger files, original label maps, input order, frozen options and terminal evidence. Frozen source revision was `9d262fd4efa891308c5049d9e9375b28aa3385f8`, snapshot `ecd67cbed55a96a616d1aca018eb132d39c58e828394a2b2e5caad83859ed893`; runtime manifest was `0e8bdff10210f119599973f26e04da3554debdec5a09cba47538467939630805`, transport digest `b600e025b3d89d7696e17a11144695bc13c95c50b24e9b78208d91b3c1d45bf7`. Target digest was `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`.

Physical validity was independently checked against both each normalized source and its remapped original labels, preserving isolates and exact source keys. Every chain was nonempty, target-contained, disjoint and connected; every source edge had an actual original-target coupler. Whole-target-edge recounts independently recovered Q, ACL, maximum chain length, within-chain length dispersion, raw coupler redundancy R and the directed endpoint-support histogram H. Within-chain dispersion is not across-run ACL variance. The target independently had 4,800 vertices, 45,864 edges and maximum degree 20. Each chain also satisfied its degree-capacity lower bound and outgoing-coupler constraint. The path and cycle outputs attained Q=n and therefore certify two optimal ties; the other seventeen ties remain unresolved. Optimal ties are reported separately, without assuming that they satisfy a requirement for strict superiority.

All input outcomes follow. Every entry in this table is SUCCESS and valid on the original source; Q is exact and ACL is displayed to four decimal places. Exact ACL fractions, source edge counts, both statuses and actual solver/process seconds are retained in the primary machine-readable pair table. The ratio is endpoint/control solver wall; values above one are slower. † marks a proven optimal tie.

| Input | Family membership | n | Q control → endpoint | ACL control → endpoint | Max chain control → endpoint | ΔQ | Solver ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| ember_32122 | kagome | 131 | 166 → 162 | 1.2672 → 1.2366 | 3 → 2 | -4 | 1.0375 |
| ember_1363 | bipartite | 126 | 566 → 566 | 4.4921 → 4.4921 | 5 → 5 | +0 | 1.0458 |
| ember_37603 | hardware\_native | 128 | 250 → 250 | 1.9531 → 1.9531 | 5 → 5 | +0 | 1.0551 |
| ember_31357 | lfr\_benchmark | 100 | 189 → 188 | 1.8900 → 1.8800 | 6 → 6 | -1 | 0.9707 |
| ember_4755 | hypercube | 128 | 457 → 456 | 3.5703 → 3.5625 | 7 → 6 | -1 | 1.0089 |
| ember_32367 | honeycomb | 190 | 273 → 273 | 1.4368 → 1.4368 | 4 → 4 | +0 | 1.0276 |
| ember_2429 | wheel | 127 | 200 → 200 | 1.5748 → 1.5748 | 11 → 11 | +0 | 1.0498 |
| ember_4905 | binary\_tree | 127 | 138 → 138 | 1.0866 → 1.0866 | 3 → 3 | +0 | 0.9938 |
| ember_37302 | spin\_glass | 160 | 1835 → 1835 | 11.4688 → 11.4688 | 12 → 12 | +0 | 1.0565 |
| ember_5058 | tree | 121 | 134 → 134 | 1.1074 → 1.1074 | 5 → 5 | +0 | 0.9810 |
| ember_33018 | shastry\_sutherland | 121 | 162 → 160 | 1.3388 → 1.3223 | 3 → 2 | -2 | 1.0332 |
| ember_37761 | named\_special | 46 | 50 → 50 | 1.0870 → 1.0870 | 2 → 2 | +0 | 1.0203 |
| ember_33587 | weak\_strong\_cluster | 128 | 427 → 426 | 3.3359 → 3.3281 | 7 → 7 | -1 | 1.0260 |
| ember_5411 | kneser | 126 | 420 → 420 | 3.3333 → 3.3333 | 7 → 7 | +0 | 1.0189 |
| ember_2030 | path † | 141 | 141 → 141 | 1.0000 → 1.0000 | 1 → 1 | +0 | 1.0180 |
| ember_31536 | random\_planar | 152 | 300 → 301 | 1.9737 → 1.9803 | 6 → 6 | +1 | 0.9922 |
| ember_32616 | frustrated\_square,king\_graph | 121 | 243 → 244 | 2.0083 → 2.0165 | 4 → 5 | +1 | 1.0666 |
| ember_4083 | generalized\_petersen | 126 | 212 → 212 | 1.6825 → 1.6825 | 5 → 5 | +0 | 1.0395 |
| ember_22972 | watts\_strogatz | 174 | 1712 → 1713 | 9.8391 → 9.8448 | 14 → 14 | +1 | 1.0125 |
| ember_5242 | johnson | 120 | 846 → 847 | 7.0500 → 7.0583 | 12 → 12 | +1 | 1.0143 |
| ember_33219 | cubic\_lattice | 125 | 224 → 223 | 1.7920 → 1.7840 | 5 → 5 | -1 | 0.9115 |
| ember_34404 | planted\_solution | 133 | 145 → 145 | 1.0902 → 1.0902 | 3 → 3 | +0 | 0.9963 |
| ember_33402 | bcc\_lattice | 91 | 152 → 152 | 1.6703 → 1.6703 | 6 → 6 | +0 | 1.0289 |
| ember_14334 | regular | 140 | 1304 → 1304 | 9.3143 → 9.3143 | 11 → 11 | +0 | 1.0236 |
| ember_2229 | star | 127 | 137 → 137 | 1.0787 → 1.0787 | 11 → 11 | +0 | 1.0605 |
| ember_3499 | circulant | 134 | 198 → 199 | 1.4776 → 1.4851 | 2 → 2 | +1 | 0.9907 |
| ember_30736 | sbm | 120 | 616 → 614 | 5.1333 → 5.1167 | 8 → 8 | -2 | 1.0310 |
| ember_1829 | cycle † | 126 | 126 → 126 | 1.0000 → 1.0000 | 1 → 1 | +0 | 1.0152 |
| ember_3060 | turan | 90 | 460 → 460 | 5.1111 → 5.1111 | 7 → 7 | +0 | 1.0511 |
| ember_6450 | random\_er | 133 | 892 → 892 | 6.7068 → 6.7068 | 11 → 11 | +0 | 0.9896 |
| ember_1041 | complete | 127 | 1180 → 1180 | 9.2913 → 9.2913 | 10 → 10 | +0 | 1.0252 |
| ember_10662 | barabasi\_albert | 122 | 444 → 445 | 3.6393 → 3.6475 | 10 → 10 | +1 | 1.0293 |
| ember_31879 | triangular\_lattice | 128 | 287 → 285 | 2.2422 → 2.2266 | 4 → 4 | -2 | 1.0162 |
| ember_1584 | grid | 128 | 173 → 172 | 1.3516 → 1.3438 | 3 → 3 | -1 | 1.0267 |

The same-run timing totals were:

| Measurement | Control seconds | Endpoint seconds |
|---|---:|---:|
| Solver wall, sum | 207.2310 | 211.8009 |
| Solver wall, mean | 6.0950 | 6.2294 |
| Solver CPU, sum | 207.2192 | 211.7897 |
| Whole process wall, sum | 241.4290 | 245.5737 |
| Whole process wall, mean | 7.1009 | 7.2228 |
| Contact-refinement wall, sum | 31.4297 | 36.2998 |

Endpoint solver wall increased 2.2052% in total. The median paired solver ratio was 1.0244, ranging from 0.9115 to 1.0666; the corresponding process ratio was 1.0198, ranging from 0.8607 to 1.1144. Maximum solver time was 16.8106 seconds for control and 17.7604 for endpoint, both below the common allowance. This is one contemporaneous observation per pair on a shared machine, not a repeated runtime distribution or a controlled causal estimate of one scoring operation. CPU affinity allowed cores 0–31; load observations are retained with their actual 1-, 5- and 15-minute windows. No historical timings are pooled.

Within all 34 pairs, stored non-time layout, initialization, conversion, completion, constructed Q and pruned Q matched exactly, with no missing comparison fields. Both arms had 32 spectral `residual_tolerance` and two `approximate` initialization statuses. The legacy control also reproduced all 34 archived 039 control embeddings exactly, including serialized chain order, physical chain sets, Q and all non-time diagnostics. That is historical consistency evidence only. It adds no concurrent MM comparison or cross-run speed claim.

The refinement accounting reconciled exactly:

| Saved quantity | Control | Endpoint |
|---|---:|---:|
| Constructed Q | 18,490 | 18,490 |
| Pre-refinement pruned Q | 15,676 | 15,676 |
| Refinement qubits saved | 617 | 626 |
| Final Q | 15,059 | 15,050 |
| Committed groups | 1,163 | 1,219 |
| Equal-Q committed groups | 588 | 635 |
| Shortening committed groups | 575 | 584 |
| Groups tried | 14,528 | 14,557 |
| Routing expansions | 10,585,018 | 10,521,985 |

Thus endpoint scoring saved nine additional qubits overall, but changed subsequent visits and reconstructions. Both arms stopped on 19 inputs at the group limit, on 13 at the work limit and on two after no improvement; none stopped at a deadline. The 663 recorded endpoint `best_equal_updates` are within-group incumbent updates, distinct from 635 final equal-Q commits. Likewise 589 `best_qubit_updates` are distinct from 584 finally shortening groups. Neither internal update count is a count of independent final solutions.

All 34 endpoint diagnostic records retained signed and nullable values correctly. The 584 shortening group commits had unmeasured entry-to-returned R/H deltas, as allowed by strict-Q acceptance without scoring. Consequently 32 inputs have null net R/H; only the star (`ember_2229`) and complete graph (`ember_1041`) have complete aggregate deltas. The 635 measured equal-Q contributions comprise 566 positive, 51 zero and 18 negative R changes. Negative R is legitimate: the new objective prefers an endpoint-support histogram and does not require raw coupler redundancy to increase. Their known R contributions sum to +990, which is a partial sum, not the total endpoint-run R change and not a directly comparable improvement over the control's fully measured +654. Null never means zero. Final R/H are independently recountable from final chains, while subtraction-based pre-refinement values, when available, remain inferred rather than independent witnesses.

The endpoint scorer recorded 34,560 attempts, all complete, with zero invalid scores, interrupted scores or interrupted comparisons; every last-interrupted-stage value was null. Its accounting included 8,132 cache hits, 13,214 ownership setups, 4,879,187 owner entries, 489,134 source-adjacency entries and 479,290 distinct incident source edges. Selected-chain and ownership-overlay counts both totaled 275,364 sites. It examined 5,463,156 target-adjacency entries, inserted 2,626,187 directed endpoint-set elements and 2,444,194 histogram entries, and made 21,346 comparisons examining 42,122 bins. Source adjacency entries count repeated examinations; distinct incident edges do not count selected-selected edges twice. Endpoint multiplicity counts distinct qubits, not the number of couplers to them.

Measured ownership-setup, score, comparison and proposal-validation wall totals were respectively 1.6143225, 3.8382193, 0.0453181 and 1.9899967 seconds (7.4878566 combined). These fields remain inside the full refinement/solver wall and outside routing-expansion counts. The control lacks a matching operation-level partition, and the new trajectory differs, so these 7.4879 seconds cannot be called an independently measured incremental overhead or subtracted to claim a faster solver. Initial validation and remaining Python overhead are also included in total wall. Attempt counts and rejected/noncommitting work were retained; no interrupted scoring happened in this particular screen.

The diagnostic audit verifies saved arithmetic, bounds, counter partitions and acceptance ordering, including integer histogram bins and signed deltas. It cannot independently reconstruct unsaved intermediate embeddings, ownership overlays or per-proposal score scans. Its complete final physical checks do not turn scalar trajectory summaries into intermediate certificates. Endpoint cardinality remains a proxy for later shortening; the independently reviewed Z12 counterexample already shows that a preferred histogram can have less deletion flexibility. This screen neither removes that counterexample nor establishes novelty.

The result auditor and endpoint helper were frozen before the first outcome read. At that point root had disclosed only terminal completion and 68 SUCCESS statuses. Fixed comparison expectations had already been frozen before launch. Nine stdlib synthetic check groups passed, including corruption rejection, signed-R loss, strict-Q unscored commits, mixed known/unknown deltas, interrupted setup preservation, late-valid diagnostic-only output and source-isolate checks. All 34 saved historical controls passed the common accounting helper before the 041 saved-data audit. Actual audit execution `analysis001` passed once, with empty stderr and no source corrections or solver calls. Root separately verified all 435 archive hashes and independently recounted canonical-source validity and Q on all 68 outputs; its `041-root-results-review/structural_*` tables agree. This is a distinct structural cross-check; no complete root auditor repeat is asserted here.

The frozen main auditor SHA256 is `161a6128a422437d22007215b21a73651cb7a614cff626922566a58a153ae8c0`; endpoint helper is `125a84ed9addedcd2de264a60dd2fb26119c8ea6b6b109e359cfda1d01c58173`. `results/codex/041-results-review/review_manifest.json` binds the report, executable copies, checks, tables and external evidence. A reviewer can independently repeat the saved-data analysis into a fresh exclusive output directory with:

```sh
.venv/codex-native/bin/python -B results/codex/041-results-review/analysis001/analyze.py \
  results/codex/retrieved/hyde03/041-endpoint-support-pipeline \
  results/codex/retrieved/hyde03/039-connected-star-pipeline \
  --output results/codex/041-root-results-review/independent-repeat001 \
  --archive-digest 0216429b5820b8ea81f161f8e769180fdf10d99d561e4e0ac127f42e511f38a5 \
  --terminal-observation results/codex/041-launch/observation002/summary.json \
  --terminal-sha256 5ba5f8b02aadb71e74cef221ec09080b43637c35da8b4794be852b5a274f5677
```

The six quality regressions, eighteen equal-Q commits with reduced R, null net diagnostics and runtime cost remain part of the evidence. A tiny development-set mean gain warrants at most further fixed-policy replication and investigation. It does not justify per-input dispatch, broad promotion, a generalization claim or a claim that MM has been defeated.
