# C019 focused packet: first execution PASS

2026-09-10 UTC. Root reviewed the fixed source and test packet before execution.
The unchanged recorded-action wrapper ran it **once**, in the existing isolated
native environment with `-I -B`. All four focused cases passed: zero test
failures/errors, zero forbidden import attempts, four tiny public calls and
zero development or remote calls. No source correction or rerun was needed.

The checks establish the specified local correctness boundaries:

- Weighted assignment agrees with tiny direct enumeration, including shared
  preferred sites, forbidden edges, partial deficiency and boundary-site deletion.
  Cardinality-only assignment preserves the matched count while deliberately
  ignoring cost; two fixtures have costs 8 versus 1 and 13 versus 0.
- A degree-six source center obtains a connected four-site branching center on
  a maximum-degree-three target, with six distinct singleton leaves and Q=10.
  Original internal gaps are included in the reconstructed energy change.
- A separate fixture keeps its long neighboring chain unchanged, publishes all
  selected ownership together and invalidates exactly the changed-owner fields.
  Actual source-edge competition is resolved in another complete Q=6 fixture.
- Interrupted assignment/growth/certification leaves prior state intact.
  A completed equal-Q/R-improving admission remains the latest certified Q=3,
  R=1 geometry after a post-publication interruption, without a new strict-Q
  event. Injected final-deadline and post-valid runtime-error public calls return
  TIMEOUT and ERROR respectively, with no embedding credit.

Both public entrypoints independently validate on the tiny branching fixture
at Q=10. Their reported call walls are 1.563925 and 1.714997 seconds. These calls
share a correctness-check process and are **not independent cold-process
performance comparisons**. The entire newly started packet process includes
support imports and JIT work: test wall 7.646335 s, CPU 6.888371 s; wrapper
elapsed 8.081614 s, exit zero. All injected-failure work is included in those
totals; its individual call times were not separately saved and are not zero.
No benchmark speed or generalization claim follows.

Records are in `results/codex/c019-joint-star/focused001/`: exact invocation,
stdout, stderr, terminal status and `output/summary.json`. The pre-execution
source freeze binds nine files; an execution binding adds the original wrapper,
environment configuration and inherited isolation flags. A post-execution
completion receipt verifies the source/check/helper/oracle bytes stayed fixed.
Versions are NumPy 2.2.6, Numba 0.65.1, llvmlite 0.47.0 and NetworkX 3.4.2.

Production SHA256: `7d4af935203634ae68610c5d299cbe5b798d3247cddac72c0da6c1b9d852dba3`.
Kernel SHA256: `d9c18fa0c90ac9846c0363dc77d62ede613f83cf09da6bd34ac44088087b9444`.
Test SHA256: `c254c452b03a7b202cdeaa0bb5eca3993b6cfc21c307c633a0ec8ed475ebd0ad`.
Existing algorithms, shared validators and the benchmark harness were not edited.
Root owns registration, screen freeze, remote execution and the original audit.
