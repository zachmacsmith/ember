# Current research checkpoint

Updated 2026-09-08 22:11 UTC. Branch `codex`. Goal active and unmet: one
general non-portfolio algorithm, no MM/busclique, ideal Z12, competitive mean
ACL and roughly MM-scale runtime. No new final-test inputs have been exposed.

- **A / literature / hyde03 available:** Retain A053 within the reduced-core
  line. Its broad comparison against A050 has 10 wins, two losses and 22 ties;
  [results](experiments/053_results_screen.md). A054 restricts elimination to
  degree two, making every reduction a minor operation. Its source-only gate,
  focused checks and eight reach calls pass. The subsequent preselected screen
  covers 13 structurally changed inputs and three unchanged controls: all 32
  paired outputs validate, but Q rises 5093→5123, with six wins, seven losses
  and three exact ties. Solver totals 79.164→80.565 seconds. The mathematical
  reduction property did not establish better heuristic quality. Do not adopt
  A054 over A053. Eighteen omitted inputs receive no new quality inference.
  [Protocol](experiments/054_degree_two_focused_screen.md). The next design
  review considers a general local criterion for degree-three elimination,
  with no new implementation or calls yet.
- **B / algorithm_audit / hyde02 available:** B018's movable-contact primitive
  passes its bounded gate, including Q5→3 on a path and rejection of an
  overlapping triangle-on-path state. This is not constructor evidence.
  [Results](tracks/b_018_results.md). Root read and approved the exact
  [B019 constructor policy](tracks/b_019_constructor_policy.md): one BFS
  initialization, changing coupler witnesses and connected owner trees,
  temporary overlap with explicit prices, and one evolving incumbent.
  Prepared state amortizes setup without excluding it from the work budget.
  Implementation, focused checks and four fixed five-second full-constructor
  falsifiers are authorized. No panel or registry edit yet.
- **C / benchmark_audit / hyde04 available:** Reject the access-preserving
  shortest-path/cut policy: zero of eight supplied starts completes, six
  exhaust their pass and two time out. Missing-contact counts are worse on
  every input than the previous unrestricted diagnostic, with different
  censoring retained. All 446 commits preserve unused connectivity and
  required free ports, so the invariant is verified but insufficient.
  [Results](tracks/c_preserved_access_routing_results.md). Stop routing-only
  adjustments. A bounded constructor review now considers variable occupied
  size and ownership changes before feasibility, distinct from both other
  tracks. No new code or calls yet.

054 is terminal and retrieved: 32 SUCCESS, controller 200969 finished,
free lock, absent tmux and supervisor exit 0; 266 archive files verified.
Its prepared saved-result screen passes once; all original-label embeddings
validate and no control replay discrepancies occur. Root read the checker
changes before execution. C's final routing report/source and all 71 bound
artifacts/references are checked without rerunning. Every cluster run is
quiescent. Observe existing handles after network loss; never restart because
SSH disconnected. Candidate outputs are never pooled.

The [workflow amendment](tracks/workflow.md) requires pre-code hypotheses,
pseudocode, self-critique and cheap falsifiers. Exploration retains isolated
libraries, targeted checks, independent original-edge validation and every
failure/time. Extensive publication audits remain deferred. All findings here
are exploratory. The latest fresh-MM baseline screen has 11 wins, 19 losses
and two ties on 32 common timely inputs; its lower macro ACL does not establish
all-class superiority, and the median solver ratio is 10.33. Novelty, seed
variance and fresh-instance superiority remain unresolved.
