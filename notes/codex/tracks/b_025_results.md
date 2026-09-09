# B025: rejecting uphill selected moves reduced construction success

Retire the fixed nonincreasing-contact policy. The once-only saved-data audit passed all 27 records with no audit errors: B025 produced **2/9 valid embeddings**, the unchanged B023 control **6/9**, and stock MM **8/9**, with one MM timeout. B025 lost the regular, Watts–Strogatz, grid and honeycomb successes; both common successful embeddings used more qubits. Its historical gate (at least seven successes and three common-MM Q wins/ties) failed, but the direct regressions justify retirement independently of that screen threshold. No universal runtime multiplier is being applied.

Entries show validated Q / solver seconds; F means FAILURE and T means TIMEOUT. Failed private states receive no Q credit.

| Input | B025 | B023 | Stock MM |
|---|---:|---:|---:|
| Complete 40 | 197 / 5.40 | 183 / 3.79 | 194 / 8.88 |
| Complete 100 | F / 19.06 | F / 19.12 | T / 21.47 |
| Bipartite 30×30 | 236 / 14.08 | 195 / 6.30 | 180 / 14.75 |
| ER 80, degree 8 | F / 19.09 | F / 19.11 | 211 / 15.27 |
| Regular 80, degree 3 | F / 19.06 | 277 / 7.65 | 90 / 0.83 |
| Watts–Strogatz 80 | F / 19.06 | 306 / 8.94 | 94 / 0.98 |
| Grid 8×8 | F / 19.03 | 195 / 4.17 | 70 / 0.57 |
| Honeycomb 5×5 | F / 19.02 | 145 / 5.65 | 71 / 0.52 |
| King 8×8 | F / 19.07 | F / 7.55 | 90 / 2.09 |

All nine initial states and completed non-time action prefixes matched through the first acceptance rejection. Thereafter the trajectories diverged. B025 rejected **2,312 complete selected winners**: 1,815 erasures and 497 routes. It accepted 1,902 of 4,214 complete actions, with six interrupted actions. No selected zero-defect proposal was rejected, and no other scored zero-defect proposal was discarded. Contact loss/restoration still occurred (2,181 losses, 1,538 later restorations of previously lost edges); the two valid outputs underwent 47 cleanup deletions. Thus the representation can still reach feasibility, but this acceptance restriction makes the fixed search substantially less effective.

Every B025 failure reached the search deadline, below the work cap; individual work was 2.36–10.85 million units. Final missing-edge counts for K100/ER/regular/WS/grid/honey/king were 762/136/44/48/11/4/68; only K100 retained overlap (147). These are incomplete constructions, not competitive low-Q outputs. The added gate itself consumed only 78,049 units and 0.258 seconds; routing consumed 118.798 seconds, versus 57.283 for B023. Rejected moves retain old geometry and obligations, so the result combines acceptance effects with the resulting repeated routing and deadline exposure. It does not prove uphill acceptance universally necessary or the shared neighborhood sufficient.

All-attempt solver / CPU / process totals were **152.863 / 152.835 / 170.872 s** for B025, **82.278 / 82.086 / 96.033 s** for B023, and **65.369 / 65.311 / 79.755 s** for MM. These are contemporaneous hyde02 observations, including every failure; start load was 33.19–34.37 on 32 available CPUs. No historical timing is pooled. Stop numerical refinement and carry the acceptance/neighborhood distinction into the strategic review.

Full [CSV](/Users/dabh/ember/results/codex/track-b025-analysis/analysis001/table.csv), [audit summary](/Users/dabh/ember/results/codex/track-b025-analysis/analysis001/summary.json), [mechanism receipts](/Users/dabh/ember/results/codex/track-b025-analysis/mechanism001/summary.json), and [single invocation](/Users/dabh/ember/results/codex/track-b025-analysis/analysis001-invocation.json) retain exact values, failures and provenance. Original-graph validation and current-price selected-score checks were reused; no intermediate-chain replay or constructor rerun was performed.
