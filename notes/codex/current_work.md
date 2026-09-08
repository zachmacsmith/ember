# Current research checkpoint

Updated 2026-09-08 17:00 UTC. Branch `codex`. Goal active and unmet: one
principled general embedding heuristic, no MM/busclique or portfolio, ideal
Z12 first, competitive mean ACL and roughly MM-scale runtime.

The user changed the workflow to prioritize informative experiments. See
[the plan amendment](tracks/workflow.md). Three independent tracks now run
concurrently; hypotheses, pseudocode and self-critiques precede implementation.
Exploratory screens use isolated dependencies, targeted checks, independent
embedding validation and complete failure/time accounting. Exhaustive replay
is deferred until a candidate is promising or shared correctness code changes.

- **A, root, hyde03:** 043 completed: ordinary17 contractions, exchange3 (all shared),
  zero exchange-only. All20 outputs independently valid;29 exchange work limits.
  044 tests only a larger exchange work cap with the same five-second deadline. It compares first
  contractions against ordinary reconstruction on all 34 accepted 042 entries,
  five seconds each. It is not a full-pipeline or MM comparison.
  [Protocol](experiments/043_ownership_exchange_reach_protocol.md).
- **B, algorithm_audit, hyde02:** new demand-aware connected-tree constructor;
  nine fixed development inputs with fresh same-host MM pairs.
  [Hypothesis](tracks/b_construction.md).
- **C, benchmark_audit, hyde05:** new multilevel contact-preserving region
  splitting constructor; eight fixed development inputs with fresh same-host
  MM pairs. [Hypothesis](tracks/c_multilevel.md).

043 controller170963 is terminal and its496file archive is retrieved.
See [screen results](experiments/043_results_screen.md) and
[044 hypothesis](experiments/044_ownership_work_allowance.md).

The shared pilot has two explicit standalone entrypoints. Eight targeted and
36 existing checks passed; historical method configurations are unchanged.
Each track owns a distinct module and host. Literature owns shared pilot edits
and the minimal independent saved-result screen for 043.

Latest completed full comparison: **042**, 68/68 timely valid, all 34 structures.
Final safe deletion gave 13 ACL improvements, 21 ties, no regressions: total
Q 15059 to 15016, macro ACL 3.3351353061 to 3.3259371863, solver time +2.3%.
All final entries are single-deletion-minimal, not globally minimum. This is a
small development improvement, with no MM superiority claim.
[Accepted results](experiments/042_root_results_acceptance.md).

043 immutable transport digest:
`4a02011ce100353b1196fdea96772713e4c103a4003e83bc4878f36828c91f70`;
execution manifest:
`d9964b0deee8ce679781257ee451b3589ed01546718d35258ace4af516b1e572`.
Local lifecycle evidence: `results/codex/043-launch`; remote:
`/home/dabh/ember-codex/runs/043-ownership-exchange-reach`.
All older controllers are terminal. Observe an existing run after connection
loss; never restart because SSH disconnected. Fresh tracks manage their own
isolated runs. Detailed older evidence remains in experiment notes/session log.

All existing development results remain exploratory. No fresh final-test
instances have been exposed, no broad across-class win established, and no
publication-ready novelty claim made. The old optional optimal-ACL-1 tie
question remains unanswered; this does not block experiments.
