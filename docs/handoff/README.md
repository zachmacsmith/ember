# Historical handoff: the two-order attraction embedder

**This folder documents the earlier two-order engine, not the current native
core.** Begin current work with the [three-order design contract](../paper2/three-orders.md)
and the [results report](../paper2/three-orders-results.md) with retained
evidence. The first three-order build is implemented; universal quality or
speed superiority over MinorMiner has not been established.

The current design uses three random orders, contact-derived active bars, a
conservative guard that accounts for three junction rows, and exact conditional
minimum-cut packing. Strict fixed-objective interleaver winners are accepted;
the accumulated proposal is decoded once per sweep and adopted even if its
decoded score worsens. A finite native bookmark preserves the best usable
answer. Native output is the default (`tail="none"`); explicit MinorMiner
polishing starts only from an already valid native embedding. This build
supports intact Zephyr, with abutment deferred and no graph-specific patches.

## How to use this archive

The documents below explain the s3.127 rewrite and its experiments in early
September 2026. Their two-order stair rule, mandatory crosses, packing DP,
converter/completion pipeline, default-tail descriptions, and fingerprint
targets are historical. They must not override the current contract or code.
Their performance tables apply only to the recorded revisions, budgets, and
solver configurations.

- [ALGORITHM.md](ALGORITHM.md): the earlier algorithm and its diagrams.
- [CODE_MAP.md](CODE_MAP.md): the earlier package structure and call graph.
- [EXPERIMENTS.md](EXPERIMENTS.md): historical experiment setup and harnesses;
  check current interfaces before reusing commands.
- [HISTORY.md](HISTORY.md): earlier proposals, tests, and refutations.
- [OPEN_FRONTS.md](OPEN_FRONTS.md): questions open at that snapshot.
- [AI_HANDOFF.md](AI_HANDOFF.md): historical working conventions and pitfalls;
  current owner instructions and the three-order contract take precedence.
- [baseline/RESULTS.md](baseline/RESULTS.md): frozen baseline evidence.
  `compare_baseline.py` compares against that historical engine.

The predecessor before s3.127 is at commit `ea5d1cf2`; its records and probes
are in `docs/paper2/archive/`. The continuing chronicle is
[notes.md](../paper2/notes.md). For physical facts and the external solver,
[fabrics.md](../paper2/fabrics.md) and
[mm-internals.md](../paper2/mm-internals.md) remain useful references. Use
[ideas.md](../paper2/ideas.md) for the concise current algorithm summary.
