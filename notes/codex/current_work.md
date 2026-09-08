# Current research checkpoint

Updated 2026-09-08 17:50 UTC. Branch `codex`. Goal active and unmet: one
general embedding heuristic, no MM/busclique or portfolio, ideal Z12 first,
competitive mean ACL and roughly MM-scale runtime.

The [workflow amendment](tracks/workflow.md) prioritizes informative experiments
across three independent tracks. Hypotheses, pseudocode, self-critiques and
cheap falsifiers precede implementation. Screens retain dependency isolation,
targeted checks, independent validity checks and complete failure/time records.

- **A, root, hyde03:** 045 vacancy repair finds 25 first contractions versus
  ordinary reconstruction's 17, including eight additional inputs. All 42
  credited outputs are original-valid; root independently replayed the eight
  additional traces. [Results](experiments/045_results_screen.md). The bounded
  cumulative pipeline stage passed 20 focused checks. 046 is staged and its
  detached start is requested: 34 unchanged readiness inputs, seed zero, fresh
  control/treatment pairs, 60 seconds, one stage allowance of min(1 second,
  20% of preceding pipeline time), 50,000 proposals, at most 20 contractions.
  [Hypothesis](experiments/046_vacancy_pipeline_hypothesis.md).
- **B, algorithm_audit, hyde02:** B003 completes 7/9, but loses ACL to MM on all
  seven timely pairs. B002/B003's six common outputs have unchanged summed Q.
  Bounded costs improve construction progress but leave committed placements
  difficult to repair. B004 will test bounded release and reinsertion of a small
  connected block within one evolving partial embedding.
  [Results](tracks/b_bounded_cost.md).
- **C, benchmark_audit, hyde04:** C001 and C002 both fail on all eight inputs.
  Six C002 partial allocations have too few target couplers between fixed
  regions to represent their source-edge requirements. Fixed-parent splitting
  is rejected. C003 investigates target coarsening followed by connected-region
  and label reconfiguration with movable boundaries.
  [Results](tracks/c_002_results.md).

Latest accepted full pipeline comparison is 042: 68/68 timely valid outputs,
13 ACL improvements and 21 ties after safe deletion; Q 15059 to 15016, macro
ACL 3.3351353061 to 3.3259371863, solver time +2.3%. These development gains
do not establish superiority to MM. No new final-test instances are exposed.

046 frozen snapshot:
`5dadefe9e1c9099282701cc45c060a810e355a92d4128dc537c443f7e50b9dd7`;
manifest:
`79bc699bd2da6de320d9b2499bd733420199585086c19afa7afb0ba8ea9e5936`.
Transport: `ec5c8b3826598391c3439274999b1b40a1b7018af00c53f9b7837d59a3b1c6b5`.
Lifecycle evidence is in `results/codex/046-launch`; frozen inputs in
`results/codex/046-vacancy-pipeline`. All prior A controllers are terminal.
Observe an existing run after connection loss; never restart because SSH
disconnected. Each fresh construction track manages its own host and immutable
run. Literature owns new pilot registrations and the minimal 046 result screen.
