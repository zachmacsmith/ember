# Independent review of the full-pipeline matching-star comparison

2026-09-08. The fixed star treatment has a marginal cumulative gain on this
development screen: six inputs improve, four regress, and 24 tie. Across the
34 source structures, Q decreases from 15,059 to 15,052 and the mean of the
34 observed ACL values decreases from 3.335135306 to 3.333413590, about 0.052%.
All 68 calls are timely valid successes. These results do not establish an
across-family improvement over MM or justify promotion from the star operator's
individual reductions alone.

The 25 committed star moves save 38 qubits inside the treatment, but its
ordinary moves save 31 fewer qubits than the control's ordinary moves. The
net improvement is seven qubits. That distinction is central to this result.

## Frozen experiment and completion

This is the prespecified [037 experiment](037_induced_star_pipeline.md), with
the completed [independent preflight](037_preflight_review.md). Each of the
34 distinct 017 development sources receives the fixed spectral-contact control
and that same configuration plus `polish_star_policy='matching'`, at seed 0
and 60 seconds. The 68 calls run sequentially on hyde03 with adjacent source
pairs and frozen arm order. No saved embedding, MM output, family label, or
competitor score enters either call. Direct singleton relocation stays off.

| Identity | Value |
| --- | --- |
| Commit | `13876c22b0576c3d41d54bffe5ec429e37f5d08c` |
| Source snapshot, 47 files | `5dfc63cfb5bb2a674cb3e556e13d2b4d18a1857c7a8f296ba27cc2dd5075abc9` |
| Transport, 153 inputs | `55064e25db44189b2ddd0f77d0285f17ae4de3292656b7b55e624ceffd24e2e9` |
| Ideal Z12 target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Retrieved archive, 432 files | `84aac4c4a530e3c07f78366eb35407e139d5f85fde5bcdf6b697f26d94379a25` |

Controller 134553 started at 04:45:37.938521 UTC and completed at
05:00:08.650611 UTC. Fresh connection checks followed that exact supervisor,
without restarting it. The terminal check found 68 finalized successes, a free
controller lock, stopped tmux, and supervisor exit 0. Retrieval began only after
that check and independently verified every archive-file hash. All 68 worker
records and claims are present; every process exits 0, and no result is marked
interrupted or recovered. Recorded worker intervals do not overlap; the smallest
gap is approximately 0.002308 seconds and the worker span is 870.696250 seconds.

The 34 structures represent 35 family memberships. King graph 32616 and
frustrated-square graph 32816 share the same normalized topology and one solver
input, recorded as 32616 in the table. That input counts once in totals and
means. Original Sudoku remains absent because its original instances do not
pass the necessary Z12 size bounds. The separate corrected Sudoku supplement
is not silently included in this experiment. All inputs remain development
data. Distinct node/edge counts and sorted degree sequences certify that these
34 structures are pairwise nonisomorphic; this does not imply statistical
independence or representative family sampling.

## Independent validation and scoring

The ordinary analyzer and independent standard-library auditor both pass.
The independent auditor imports no candidate or graph-library implementation.
It recomputes archive, transport, source, target, selection, graph, task, and
historical-result identities. It checks final/worker agreement, complete task
coverage, interpreter and implementation paths, import guards, deadlines, and
process sequencing. All 68 candidate workers use the prepared native Python
3.10.12 environment, with MM absent, no forbidden import attempts or loaded
embedding library, and implementation paths inside the frozen source.

For every final embedding, the auditor checks exact source-key coverage,
nonempty chains, target membership, duplicate qubits within and between chains,
chain connectivity, and every original source edge against exact original
target couplers. It independently recomputes Q, ACL, maximum chain length,
within-embedding chain-length variance, and logical-edge contact redundancy R.
Here Q counts occupied target vertices, ACL is Q divided by the source vertex
count, and R sums the number of interchain target couplers minus one over each
required source edge.
All recorded quality metrics agree with those calculations. There are no
failures, invalid results, timeouts, late valid embeddings, or missing timing
records in this run. Thus the paired quality denominator is all 34 inputs.

The exact target has maximum degree 20. A connected k-qubit chain has at most
18k+2 outgoing couplers, so a source vertex of degree d needs at least
`max(1, ceil((d-2)/18))` qubits. The auditor checks this bound and each chain's
actual outgoing-coupler count. Summed bounds are necessary conditions; a valid
embedding attaining the sum certifies optimal Q. The cycle and path pairs
attain ACL 1 and are certified optimal ties. The other 22 Q ties have no
optimality certificate here. This classification does not assume the user has
accepted ties as satisfying the project's goal.

One seed supplies no across-seed ACL variance estimate. The variance recorded
for each embedding describes its distribution of chain lengths, a different
quantity. Full physical metrics for all 68 embeddings are saved in
`final/details.json`; no within-chain variance is mislabeled as solver variance.

## Complete fixed-arm comparison

Negative ΔQ favors the star treatment. The last column is the sum of reductions
made by committed star moves *inside* that treatment; it is not the difference
from the control. Every source and every regression is retained below; ACL is
displayed to six decimal places while Q is exact.

| Family membership | ID | n | m | Control Q | Star Q | ΔQ | Control ACL | Star ACL | Star commits | Q saved by star moves |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| weak_strong_cluster | 33587 | 128 | 1988 | 427 | 427 | 0 | 3.335938 | 3.335938 | 0 | 0 |
| complete | 1041 | 127 | 8001 | 1180 | 1180 | 0 | 9.291339 | 9.291339 | 0 | 0 |
| honeycomb | 32367 | 190 | 264 | 273 | 272 | -1 | 1.436842 | 1.431579 | 2 | 5 |
| grid | 1584 | 128 | 232 | 173 | 171 | -2 | 1.351562 | 1.335938 | 3 | 4 |
| triangular_lattice | 31879 | 128 | 384 | 287 | 287 | 0 | 2.242188 | 2.242188 | 0 | 0 |
| hardware_native | 37603 | 128 | 352 | 250 | 250 | 0 | 1.953125 | 1.953125 | 0 | 0 |
| spin_glass | 37302 | 160 | 12720 | 1835 | 1835 | 0 | 11.468750 | 11.468750 | 0 | 0 |
| cycle | 1829 | 126 | 126 | 126 | 126 | 0 | 1.000000 | 1.000000 | 0 | 0 |
| cubic_lattice | 33219 | 125 | 300 | 224 | 224 | 0 | 1.792000 | 1.792000 | 0 | 0 |
| bipartite | 1363 | 126 | 3969 | 566 | 566 | 0 | 4.492063 | 4.492063 | 0 | 0 |
| path | 2030 | 141 | 140 | 141 | 141 | 0 | 1.000000 | 1.000000 | 0 | 0 |
| star | 2229 | 127 | 126 | 137 | 137 | 0 | 1.078740 | 1.078740 | 0 | 0 |
| circulant | 3499 | 134 | 402 | 198 | 198 | 0 | 1.477612 | 1.477612 | 0 | 0 |
| kneser | 5411 | 126 | 315 | 420 | 424 | +4 | 3.333333 | 3.365079 | 0 | 0 |
| barabasi_albert | 10662 | 122 | 472 | 444 | 444 | 0 | 3.639344 | 3.639344 | 0 | 0 |
| lfr_benchmark | 31357 | 100 | 204 | 189 | 189 | 0 | 1.890000 | 1.890000 | 0 | 0 |
| bcc_lattice | 33402 | 91 | 216 | 152 | 154 | +2 | 1.670330 | 1.692308 | 1 | 4 |
| regular | 14334 | 140 | 2800 | 1304 | 1304 | 0 | 9.314286 | 9.314286 | 0 | 0 |
| sbm | 30736 | 120 | 625 | 616 | 616 | 0 | 5.133333 | 5.133333 | 0 | 0 |
| generalized_petersen | 4083 | 126 | 189 | 212 | 212 | 0 | 1.682540 | 1.682540 | 0 | 0 |
| random_er | 6450 | 133 | 870 | 892 | 892 | 0 | 6.706767 | 6.706767 | 0 | 0 |
| frustrated_square / king_graph | 32616 | 121 | 420 | 243 | 243 | 0 | 2.008264 | 2.008264 | 1 | 2 |
| tree | 5058 | 121 | 120 | 134 | 133 | -1 | 1.107438 | 1.099174 | 1 | 1 |
| kagome | 32122 | 131 | 236 | 166 | 159 | -7 | 1.267176 | 1.213740 | 4 | 5 |
| turan | 3060 | 90 | 2700 | 460 | 460 | 0 | 5.111111 | 5.111111 | 0 | 0 |
| named_special | 37761 | 46 | 69 | 50 | 49 | -1 | 1.086957 | 1.065217 | 7 | 8 |
| binary_tree | 4905 | 127 | 126 | 138 | 139 | +1 | 1.086614 | 1.094488 | 2 | 2 |
| wheel | 2429 | 127 | 252 | 200 | 197 | -3 | 1.574803 | 1.551181 | 1 | 3 |
| shastry_sutherland | 33018 | 121 | 270 | 162 | 162 | 0 | 1.338843 | 1.338843 | 1 | 1 |
| watts_strogatz | 22972 | 174 | 1740 | 1712 | 1712 | 0 | 9.839080 | 9.839080 | 0 | 0 |
| johnson | 5242 | 120 | 1680 | 846 | 846 | 0 | 7.050000 | 7.050000 | 0 | 0 |
| random_planar | 31536 | 152 | 450 | 300 | 300 | 0 | 1.973684 | 1.973684 | 0 | 0 |
| planted_solution | 34404 | 133 | 175 | 145 | 145 | 0 | 1.090226 | 1.090226 | 2 | 3 |
| hypercube | 4755 | 128 | 448 | 457 | 458 | +1 | 3.570312 | 3.578125 | 0 | 0 |

The Kneser, BCC-lattice, binary-tree, and hypercube inputs regress. Kneser and
hypercube have no committed star move, illustrating that unsuccessful auxiliary
search can still alter the available ordinary-search work. The BCC-lattice
star move saves four qubits locally but the complete treatment uses two more
than the control. Conversely, Kagome saves five qubits through star moves and
seven in the cumulative comparison. Local operator gains do not determine
the complete result. Kagome's seven-qubit decrease equals the net total;
the other 33 inputs' Q changes cancel. This is descriptive concentration,
not a reason to restrict deployment or scoring by family.

## Search accounting and deadlines

All 68 contact traces pass the independent accounting helper. Within every
pair, the recorded initialization, layout, constructed Q, and pruned Q agree.
Both arms construct 18,490 qubits in total and prune to 15,676 before refinement.
Inferred starting R also agrees in all 34 pairs. These are consistency checks:
the full intermediate embeddings and placement states were not saved.

| Recorded refinement quantity | Control | Star treatment |
| --- | ---: | ---: |
| Ordinary group visits | 14,528 | 14,475 |
| Completed/started passes recorded | 38 | 38 |
| Total shared work | 10,585,018 | 11,018,751 |
| Work charged to ordinary repair | 10,585,018 | 10,418,270 |
| Work charged to star search and maintenance | 0 | 600,481 |
| All committed improvements | 1,163 | 1,142 |
| Equal-Q improvements | 588 | 570 |
| Q saved by ordinary moves | 617 | 586 |
| Q saved by star moves | 0 | 38 |
| Total Q saved after pruning | 617 | 624 |
| R change after pruning | +654 | +646 |
| Independently measured final R | 7,628 | 7,620 |

The treatment uses 53 fewer ordinary visits and 166,748 fewer ordinary work
units while total work rises by 433,733. Its ordinary savings decrease by 31.
This reflects the combined effect of changed incumbents, later opportunities,
and work allocation; it does not isolate a causal cost for one of those factors.
Matching's 38-qubit reductions must not be reported as a 38-qubit comparative gain.

Every call stays within 512 ordinary visits, four passes, 500,000 shared work
units, 50,000 per visit, a 25,000-unit auxiliary share, and 2,048 query units.
The maximum recorded star-path visit uses 20,697 units. All proposal, setup,
and refresh work is charged to its existing visit and global budget, with
no added visits or independent reconstruction branch. The helper verifies
first-failed-visit attachment, once-per-center/pass consideration, suppression
after ordinary acceptance including equal-Q acceptance, selected induced-star
structure, and original-source labels.

The star treatment records 4,042 considerations and 1,034 actual root queries.
There are 25 matching-complete and certified proposals, all 25 committed after
the scheduler's deadline check, on 11 inputs. No certification is rejected at
commit time in this run. The complete counters still distinguish those events
so a late certified proposal cannot be mistaken for an accepted improvement.

| Consideration outcome | Count |
| --- | ---: |
| Accepted and committed | 25 |
| Exhaustive no match for the selected fixed block | 930 |
| Query limit | 56 |
| Auxiliary limit | 44 |
| Cache/search already disabled | 1,713 |
| Center degree outside singleton capacity | 1,100 |
| No qubit excess for the selected block | 155 |
| Too few eligible independent leaves | 19 |

The 1,813 incomplete considerations are the query-limit, auxiliary-limit,
and already-disabled outcomes. Of the 44 auxiliary-limit outcomes, 23 occur
inside actual root queries and 21 before another query starts. An exhaustive
no-match result concerns the chosen block and fixed outside embedding; it is
not a proof of global embedding optimality. Structural rejection and an
interrupted query are not interchangeable evidence.

| Selected block size | Root queries | Accepted commits | Exhaustive no match | Query limit | Auxiliary limit inside query |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3–4 | 591 | 23 | 528 | 26 | 14 |
| 5–8 | 360 | 1 | 326 | 26 | 7 |
| 9–21 | 83 | 1 | 76 | 4 | 2 |

Actual committed sizes are eight blocks of size 3, fifteen of size 4, one of
size 5, and one of size 9. Size bins are descriptive and never select a method
for a graph. The size-9 BCC-lattice move does not prevent that input's regression.

Auxiliary work splits into 11,632 setup, 584,792 query, and 4,057 refresh units.
The query-stage sums are 34,430 selection, 45,466 obligations, 301,294 eligibility,
74,490 root generation, 127,393 domains, 483 matching, 844 scoring, and 392
certificate units. There are 33,979 generated roots including 6,216 duplicates,
5,510 eligible roots, 25 matched roots, and 168 inspected matching edges.
The matching-edge counter is distinct from all 483 matching-stage work units.

The lazy owner cache is built in 24 calls and fully refreshed 415 times.
Twenty-three calls consume the complete auxiliary share: 21 end disabled by
`auxiliary_limit` and two by `refresh_auxiliary_limit`. A failed refresh disables
later auxiliary work while retaining the already valid committed embedding.
No stale-cache inconsistency is recorded. The audit checks exact completed
cache-build work, exact star-refresh work, ordinary-refresh parity and lower
bounds, and the saved cache-state event sequence. It cannot reconstruct the
unsaved intermediate owner map.

Both arms stop 19 calls at the group limit, 13 at the work limit, and two for
no improvement. No native or contact deadline is crossed. Each arm's spectral
initializer records 32 residual-tolerance results and two approximate results
(cycle and path), with no initialization failure, work-limit stop, or deadline
stop. Each arm uses 3,691,205 initialization work units in total and at most
642,880 in a call. There are eight warning-bearing calls and 16 warning messages
across both arms. These saved residual/work checks do not independently recover
the unsaved eigenvectors or certify an exact lowest eigenspace.

## Complete timing and historical replay

All timing below comes from the same 037 run on hyde03. Both arms use the same
prepared native environment, per-task empty JIT caches, and one configured
computational thread. First-call JIT work is charged to solver time. Imports,
startup, and validation outside the solver interval remain in process time.
All records have affinity 0–31 on the shared 32-CPU host; observed one-minute
load ranges from about 10.96 to 17.05. There is no exclusive-host timing claim.

| Time measure | Control mean (s) | Star mean (s) | Control total (s) | Star total (s) |
| --- | ---: | ---: | ---: | ---: |
| Full solver wall | 9.652705 | 9.830773 | 328.191959 | 334.246267 |
| Full solver CPU | 9.651969 | 9.829840 | 328.166945 | 334.214568 |
| Full process wall | 12.746861 | 12.835355 | 433.393276 | 436.402066 |
| Contact phase wall | 1.194784 | 1.230310 | 40.622650 | 41.830531 |

The paired star/control solver ratio has median 1.000984, mean 1.031677, and
range 0.564246–1.698551. The paired process ratio has median 0.999846, mean
1.020152, and range 0.638288–1.535072. All 34 timing pairs are timely successes.
The star search records 1.146140 seconds inside proposals, including 0.017748
seconds of setup, plus 0.009857 seconds of refresh. Those intervals are included
in contact, solver, and process totals; they are not added again.

Whole-call timing differences also occur in the shared earlier stages despite
matching stage diagnostics. Mean layout wall time is 8.083466 versus 8.252081
seconds. The timing ratios are single-run observations, not an isolated
estimate of operator overhead or a statistically established speed change.
The 5% auxiliary allowance is a share of work units, not 5% of wall time.
There is no contemporaneous MM arm, so these ratios say nothing about a
candidate/MM speed threshold.

The historical 036 control ran on local macOS/Python 3.10.19. The audit rechecks
its source and original graphs, validates all final embeddings, and matches
all 102 task/worker/final hashes to the previous 036 review. The 037 control
has the same Q on 33 inputs and one fewer qubit on spin glass (1,836→1,835).
Twenty-eight serialized embeddings replay exactly. The other six are complete,
spin glass, bipartite, star, Turan, and Johnson. Recorded layout summaries agree
on 28 inputs, constructed Q on 30, and pruned Q on 31. Complete numerical
initialization summaries agree on none across platforms. Exact cross-platform
replay was not a prerequisite; no historical timing ratio is formed.

## Audit artifacts and limitations

Raw results are at `results/codex/retrieved/hyde03/037-induced-star-pipeline`.
Independent outputs are at `results/codex/037-independent-review/final`:
`summary.json`, `details.json`, `pairs.csv`, `initializations.json`, and
`historical_036_replay.json`, together with the exact auditor and helpers.
`diagnostic_summaries.json` and `all_input_table.md` are additive summaries.
Their standard-library reproducer is `results/codex/037-independent-review/summarize.py`;
a separate local repeat produced byte-identical summary and table files.
`review_manifest.json` binds this note and the additive summaries to their hashes.

The first full independent run stopped at an auditor path-normalization error
while looking up historical 036 hashes. It had not written a final result.
The failed auditor version and error record are preserved; correcting only
command-line path normalization produces the successful audit reported here.
No source, task, result, environment, or solver execution changed. Earlier
staging and observer/probe errors remain documented in the preflight report.

The independent star helper passed 19 synthetic accounting/corruption checks
without importing a solver. Before seeing 037 outcomes, it also passed all
34 saved 036 control traces against independently recomputed physical Q/R.
The complete 037 audit then checked all 68 actual records with no diagnostic
errors. These checks support recorded invariants and final validity; they do
not turn unsaved intermediate states into independently observed evidence.

Root independently repeated the complete standalone auditor into a separate
directory. The summary, pairs, details, initialization, and historical-036 JSON
outputs are byte-identical to this review's originals, including summary SHA256
`7199873aa92ae9c9057fa593c9e925fb586cf749d290222c8082dc68c36146df`.

Auditor SHA256:
`5dcf261a06d4f124d6deb6e58c43c91e88063b36a9416839eb165bba08fb314f`.
Star-helper SHA256:
`6e82c9cdd55630706fb69e07e6556eb011dba3779d88ab319f8e99169c67ff6d`.
Successful summary SHA256:
`7199873aa92ae9c9057fa593c9e925fb586cf749d290222c8082dc68c36146df`.
The primary artifact map is `audit_artifacts.json`, digest
`3a6c1291f7211a2c45e8b08fa8726363d0476981cf93e6b6336d62bc1eab7d16`.

Repeat into a fresh output directory, preserving the existing analysis:

```sh
.venv/bin/python results/codex/037-independent-review/analyze.py results/codex/retrieved/hyde03/037-induced-star-pipeline results/codex/036-converter-correction-pipeline --output results/codex/037-independent-review/root_repeat
```

The small net change, four regressions, single solver seed, and inherited
source selection leave the research objective unresolved. The evidence favors
studying why strict local reductions and unsuccessful searches displace useful
ordinary work, using a fixed general rule and fresh instances. It does not
support a family-specific selector, a best-of score, an across-family victory,
or a publication-level generalization claim.
