# Frozen initial-prefix diagnostic

2026-09-08. Implementation is stable for independent preflight. No production
source changed and no corpus prefix invocation has run. Root owns launch after
the independent freeze review. The five runtime output directories are empty;
there is no `controller.json`. Synthetic checks live separately under `checks/`.

The [protocol](038_initial_prefix_certificates.md) and
[instrumentation specification](../initial_prefix_instrumentation_spec.md)
were written and critiqued before implementation. Pre-freeze review added the
approved full-state audit, failure-aware analyzer and orphan-worker alarm; their
policy disclosures are included in the frozen bytes.

## Identities and implementation

All paths below are relative to
`results/codex/038-initial-prefix-certificates/` unless stated otherwise.

| Artifact | SHA-256 |
|---|---|
| `frozen/manifest.json` | `09bd7718cec3456ef5861c79f86065a582694902692c068b47240a7996f3aa3c` |
| Diagnostic file-map digest | `ec34d4e18e0fb72870e473b92669959f968288cec95bf62e2deb28bce85e9d78` |
| 037 production source-map digest | `5dfc63cfb5bb2a674cb3e556e13d2b4d18a1857c7a8f296ba27cc2dd5075abc9` |
| Environment-record digest | `4c108364965f9a656f749a47bed4ed7a25a645319ce9beaf43ca4eea30d75eb7` |
| `preflight.json` | `4e085af1568a75dd8481523d5b7ffbda38d607b30c8128695d44f5b983bca9dd` |

The manifest binds 170 files: all 47 production files from commit
`13876c22b0576c3d41d54bffe5ec429e37f5d08c`, 34 original and normalized graph
records with label maps, the original selection sidecars, Z12 target, diagnostic
scripts, protocol/specification and AST artifacts. The local preflight verifies
every frozen byte, original-to-normalized adjacency mapping, exact matrix,
environment, AST restoration and absence of existing run outputs. MM, its fork,
the native MM module and busclique are unavailable in the pinned environment.

The sole AST addition follows the original first top-level `best` assignment at
`plane.py:372`; removing it restores the original AST exactly. Original/restored
AST digest is `a04f6068ae73464d4183008eb5934a73946509fef56fb311005782ac7c3fc200`;
transformed digest is `3b8b222f3db6c717eee3da63abfa70fa0824a3816ef9df42eeefdd9e6f5cc008`.
The worker invokes the actual native prefix and exits it through the dedicated
`BaseException` capture. Proposal and contact-refinement sentinels enforce zero
search. One eligible copied physical state follows the frozen conversion,
completion, isolate, validation and pruning sequence.

Before/after structural hashes include all grid data, graph attributes and
iteration order, source and target adjacency, and caller graphs. Geometry and
RNG have their own hashes. Hash/copy work remains in the 60-second common wall;
serialization after finalization remains in process wall. Both received native
deadlines and the scalar remaining timeout are retained. The post-analyzer
independently validates original-graph embeddings, stage counts/order, source
and worker provenance, deadlines and full-state replay. Partial schema/capture
failures are saved as audit errors and cannot establish replay or a certificate.

The controller holds an inherited advisory lock, publishes atomic records,
launches one sequential worker per input, and never restarts existing output.
External process-group supervision retains a 150-second timeout and five-second
termination grace. A once-armed default-fatal kernel alarm uses the remaining
absolute launch allowance; the second invocation cannot reset it. It survives
controller death and may leave missing observations, which remain missing.

## Focused evidence

| Check artifact | Outcome |
|---|---|
| `checks/instrumentation_005/summary.json` | 7 tests passed; AST identity, zero proposals, actual synthetic cold/second capture, original-graph validity, mutation rejection and late-final-validation rejection |
| `checks/analyzer/check-7nchrw41/summary.json` | 2 groups passed; incomplete capture remains a reported audit failure, and structural-state disagreement is detected despite equal geometry/RNG/chains |
| `checks/watchdog/check-ek45rpvy/summary.json` | 3 groups passed; direct fatal alarm, live orphan stops after parent exit, expired allowance grants no fresh time |
| `checks/supervision/check-4wzjgbci/checks.json` | 8 groups passed; immutable publication, inherited lock, partial failures, exception/interruption cleanup, timeout and remaining-descendant cleanup |

Instrumentation test duration was 2.086 seconds. This is a synthetic test-suite
duration, not a corpus solver result. The tiny path-plus-isolate witness establishes
the declared prefix/validation mechanism only. No quality or speed advantage is
inferred from it. Earlier check directories remain intact. In particular, the
first watchdog attempt `check-odpwynbe` encountered a sandbox-denied `ps` call;
the approved process-inspection reruns passed. Earlier supervision failures and
their macOS process-probe/reap correction are also preserved by that suite.

The orphan observer cannot reap another parent's exit status; the direct-child
test separately verifies `-SIGALRM`. Process-group cleanup cannot guarantee
reaping orphan zombies or killing descendants that deliberately escape their
group. The worker itself retains its kernel alarm independently. Nonpreemptible
numeric operations can exceed the common solver deadline; late records never
count as certificates, and the process alarm supplies the separate hard bound.
This diagnostic still cannot establish net complete-pipeline runtime savings.

## Safe reproductions

Run from the repository root, preserving the native interpreter symlink. Each
explicit output must be fresh. These commands use frozen diagnostic bytes and
do not launch a corpus worker:

```sh
.venv/codex-native/bin/python results/codex/038-initial-prefix-certificates/frozen/diagnostic/controller.py preflight results/codex/038-initial-prefix-certificates --output results/codex/038-initial-prefix-certificates/preflight_repeat.json
.venv/codex-native/bin/python results/codex/038-initial-prefix-certificates/frozen/diagnostic/checks.py results/codex/038-initial-prefix-certificates/checks/instrumentation_repeat
.venv/codex-native/bin/python results/codex/038-initial-prefix-certificates/frozen/diagnostic/analyzer_checks.py
.venv/codex-native/bin/python results/codex/038-initial-prefix-certificates/frozen/diagnostic/watchdog_checks.py
.venv/codex-native/bin/python results/codex/038-initial-prefix-certificates/frozen/diagnostic/supervision_checks.py --output-root results/codex/038-initial-prefix-certificates/checks/supervision_repeat
```

Watchdog/supervision checks need permitted local process inspection. Their
automatically named directories are additive. Do not run `prepare.py` again or
write check outputs inside `frozen/`. The complete-run analyzer is reserved for
verified controller completion and accepts a fresh additive output directory.
