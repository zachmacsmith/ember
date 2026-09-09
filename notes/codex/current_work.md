# Current research checkpoint

Updated 2026-09-09 02:15 UTC. Branch `codex`; goal active and unmet.
Single general heuristic, no MM/busclique, no portfolio, ideal Z12. Success,
mean ACL, variability and roughly MM-scale runtime remain separate requirements;
optimal ACL-one ties are acceptable.

The [latest mechanism milestone](mechanism_cycle_061_b023_c009.md) covers 136
complete-constructor calls, all terminal, retrieved once and independently
analyzed once. Root reviewed the candidate sources and specific new-risk checks
before freezing the runs. Shared worker/import/validator logic is unchanged;
only constructor descriptors were added. All jobs from that milestone and
earlier screens are terminal. The next three independent screens are now live.

- **A: retain unchanged branch reconstruction within measured scope.** The
  [060 replication](experiments/060_branched_path_results.md) and full 34-input
  [061 breadth screen](experiments/061_branched_path_breadth_screen.md) pass their
  frozen gates. In 061, A053/new both succeed 34/34; the new stage improves six
  and ties 28, with no per-input Q regression. New breadth gains are named-special
  and honeycomb. All 40 saved Q comes from the stage, whose base Q always matches
  fresh A053. Against MM: eight wins, 17 losses, four optimal ties and five MM
  timeouts. Twelve common solver ratios exceed 10x. Prior planted/wheel/hypercube
  seed failures remain unresolved. No stage-cap tuning; next proposal targets
  construction and must distinguish neighborhood, acceptance and cost.
- **B: retire B023's fixed policy.** [Results](tracks/b_023_results.md): 6/9 valid
  versus MM 8/9, only one common Q win. Every successful trajectory loses and
  restores contacts, but four sparse successes use 2.04–3.26x MM's Q after cleanup.
  Only one of 2,868 actions is interrupted. Poor placement, restricted relocation
  and forced acceptance remain confounded. Prepare one distinct construction
  hypothesis; no pass/price/cleanup rescue from partial metrics.
- **C: retire C009's fixed policy.** [Results](tracks/c_009_results.md): 0/8 valid
  versus MM 6/8. All hit search work before the wall limit; generation costs
  74.7% of solver time. Five inputs never publish a replacement library. The
  other three remain invalid; pairwise support does not prove global consistency.
  Prepare one substantially different general construction hypothesis; no larger
  domain or cap justified by partial coordination scores.

The [gap analysis](mm_gap_current_replications.md) and
[72 class/size rows](mm_gap_current_tables.md) retain all 36 baseline classes:
056 original four-seed A053 134/136 versus MM 120/136; 057 additional two-seed
68/70 versus 64/70; 058 two Sudoku sizes 4/4 each. Eighteen class memberships
repeat positive mean ACL gaps. These versions and cohorts are never merged into
061 means. One-seed 061 cannot estimate across-seed ACL variance; within-chain
variance is a different quantity. All observations are exposed development data.

The [workflow](tracks/workflow.md) requires a representation/neighborhood/
acceptance/cost diagnosis, distinguishing observation, hypothesis, pseudocode,
self-critique and cheap complete-constructor falsifier before new code. Three
independent next-track memos have been reviewed. Isolated implementations are
authorized after their exact pre-code policies: A changes only dependency-ready
lifting order, B changes only the initial bijection on the same physical sites,
and C grows an auxiliary clone graph with bounded greedy placement revision.
The reviewed implementations are frozen and launched: [A062, 36 calls on 06](experiments/062_launch_record.md),
[B024, 27 calls on 02](tracks/b_024_launch_record.md), and
[C010, 16 calls on 03](tracks/c_010_launch_record.md). Each has fresh same-host
MM comparisons; A/B also have their unchanged control. Six, four and three
targeted risk groups passed respectively; C repeated only its affected final
error-credit safeguard after a proactive correction. Root verified all frozen
source/input bindings and task vectors. Their small screens decide continuation
from complete success, quality and time. No implementation is approved merely
because a partial score improves. Exact neighborhood solves
remain optional local diagnostics, never global constructors.

Transport identities: [061](experiments/061_launch_record.md),
[B023](tracks/b_023_launch_record.md), [C009](tracks/c_009_launch_record.md).
Observation failure never authorizes replacement launches. Same-host paired
comparisons only; 06 has a distinct Python environment and high observed load.
Protected `.verified.json` and `.claude/` remain untouched. No held-out evidence,
nonideal hardware, alternate architecture or publication/novelty claim exists.
