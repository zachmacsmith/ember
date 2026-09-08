# Experiment 009: first corrected independent development screen

Date: 2026-09-07. Branch: codex. Parent revision: 580d2044; exact uncommitted
Python source is frozen and hashed by the run manifest. Raw artifacts:
`results/codex/009-first-development-screen`.

This is development evidence on nine small generated graphs, not confirmation
across Ember's 36 families. It compares separate algorithm configurations, never
selects their best output for a candidate result, and gives candidates no MM
embedding input. All nine inputs remain development data forever.

## Question and prediction recorded before launch

Does the explicit native construction succeed across varied structures without
its inherited MM legalization, and does bounded coupled reconstruction improve
the resulting valid embeddings at a plausible runtime cost?

Prediction: packed construction will be fast and competitive on dense graphs,
but its ordering and native conversion will leave missing contacts or long
chains on some sparse inputs. Contact refinement can improve valid results but
cannot fix construction failure in its current API. A wider beam may improve
some assignments beyond width one, at additional cost; no improvement is also
a useful negative result. Search construction may exhaust its budget before
conversion. These are hypotheses, not assumed observations.

## Fixed experiment

- Ideal Z12 (4800 physical vertices), exact target including coordinate attributes
  in `target.json`. Source/target hashes are included in every immutable task.
- Graphs: K40, K100, complete bipartite 30+30, ER80 expected degree8,
  3-regular80, Watts–Strogatz80, grid8x8, honeycomb5x5, king8x8. Random graph
  seeds are fixed in the snapshotted generator. One solver seed (0) per input;
  this cannot estimate between-run ACL variance.
- Separate rows for MM, native search (1000 asks), native packed, packed with
  width-one refinement, and packed with width-four refinement. All refinement
  configurations use the same two passes and 48-group bound. Packed order is
  random globally; no graph-family dispatch. No winner-selection wrapper.
- Thirty-second solver deadline for each configuration, with kernel and parent
  process watchdogs allowing 30 additional seconds for imports/cleanup. Late
  valid solutions are TIMEOUT with only diagnostic quality, never credited wins.
- Sequential randomized method order on the same local host, one thread in the
  four configured numerical runtimes. Full process and solver wall times, solver
  CPU, peak RSS, versions, interpreter paths and host load are recorded.
- Fresh worker processes and empty per-task Numba caches. Compilation is charged
  inside solver time. This is a cold-call screen; it does not estimate steady-state
  service performance. The initial 008 smoke had an unspecified cache state and
  is kept separate.
- Candidate environment physically lacks MM/busclique, rejects attempted imports,
  and verifies the candidate module resides in frozen source. Original source and
  target graphs are retained for independent validation after the call.

## Harness verification and earlier failures

003 used a resolved virtual-environment symlink and accidentally launched the
base Python, which lacked NetworkX. 005 preserved the interpreter but omitted
Zephyr node attributes when serializing. Both are harness failures, preserved
without treating them as embedding-performance evidence.

008 round-tripped target attributes and produced valid embeddings of K40 on Z12:
native packed ACL3.9, MM ACL4.2 (one seed). This smoke demonstrates executable
comparison, not general superiority. Version2 runs additionally preserve worker
output separately from controller-finalized records. An inherited advisory lock
prevents a surviving worker from being duplicated after controller death. A
pre-spawn claim records uncertain launch attempts, and a kernel SIGALRM bounds
worker lifetime independently of its controller. Interrupted trials are retained,
not silently retried. Recovered process timing is unknown, not zero.

Four harness regressions pass, including deliberate controller termination while
a child lives, rejection of a second controller, subsequent recovery without a
duplicate start, graph/coordinate round-trip, and task-identity tampering.

## Outcome and decision

Pending at launch. Report every status before comparing quality. Summarize only
timely independently valid successes, retain missing/failed comparisons explicitly,
and do not infer a class-wide win from these individual development instances.
