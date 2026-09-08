# Independent review of the one-prefix diagnostic

2026-09-08. **PASS: root may launch this exact frozen diagnostic once.**
Root retains launch ownership. No original-corpus prefix, placement search,
contact refinement, or comparison was executed during this review. The final
independent recheck found all corpus output directories empty and no attempt
record. This is diagnostic preflight clearance, not a positive research result.

The reviewed protocol is [038](038_initial_prefix_certificates.md), with the
[single-prefix instrumentation specification](../initial_prefix_instrumentation_spec.md).
Its purpose is to determine whether the actual initial placement can supply a
timely original-graph embedding attaining the exact integer qubit lower bound.
This is a mechanism screen, not an embedding method, a best-of selection policy,
an estimate of saved search time, or a comparison with MM. A negative screen
rejects this checkpoint position; it does not justify searching the recorded
data for a different checkpoint.

## Source and input audit already passed

The independent, standard-library-only script
`results/codex/038-independent-review/preflight.py` reads the frozen files and
compares every source file with both the audited 037 snapshot and its actual git
object. Its `--inputs-only` execution called no solver and imported no algorithm.
All 47 source files are byte-identical to commit
`13876c22b0576c3d41d54bffe5ec429e37f5d08c`, snapshot
`5dfc63cfb5bb2a674cb3e556e13d2b4d18a1857c7a8f296ba27cc2dd5075abc9`.
The target is the exact previously audited ideal Z12 record, hash
`38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`:
4,800 vertices, 45,864 undirected edges, maximum degree 20.

All 34 normalized graphs, original JSON graphs, and integer-to-original label
maps agree edge-for-edge and include every vertex. The graph-key execution order
is fixed and sorted. The preserved 017/012 selection sidecars retain all 35
family memberships, including the linked king/frustrated-square structure, and
the absence of original Sudoku. No supplemental Sudoku is silently substituted.
All these sources are development data. The independently checked input list is
the same 34 structures used by 037; it is not selected from 037 outcomes.

The preserved initial audit is
`results/codex/038-independent-review/inputs-preflight.json`, SHA-256
`be77a63a9467eead796914d830fe3c6dae7dea123942b80d722559fc6ac17bc8`.
At that check, all five corpus output directories were empty and no controller
attempt record existed. This is an observation about the inspected instant,
not authority to reuse or erase outputs after an attempt.

## Static execution review

The transform inserts exactly one top-level expression after the original
initial `best` assignment in `plane.arrange` (frozen lines 371–372). Removing it
must recover the original function AST without any other changes. The hook's
`PrefixCaptured(BaseException)` bypasses native's ordinary `except Exception`
and terminates the stack before the search loop. Separate sentinels guard the
proposal iterator, reinsertion, and contact refinement. The capture checks zero
asks, accepts, and passes and exactly three initial readouts on axes `(1,0,1)`.
The existing initial loop is not given new cancellation points between its
readouts; a late capture therefore remains a possible, retained outcome.

After capture the native stack is not resumed. Zero overload is only a cost
throttle. Eligible observations run at most one conversion, completion,
constructed validation, pruning, and final validation, retaining actual chain
maps. The original-label mapping is independently invertible. The physical
validator must check the original source and exact frozen target; a low count
or geometric proxy alone cannot establish a certificate. A valid, timely
embedding with `Q=L` establishes optimal Q on that particular input. It does not
establish a strict quality win over another optimum or family generalization.

Static inspection of frozen `field.py:801` (`wire_seeds_exact` and its helpers),
`field.py:960` (`complete_seeds`), and `polish.py:43` (`spur_prune`) found local
allocation/copying of the mutable physical chain state. Their grid/source/target
accesses are reads. The prefix itself can populate the grid's line-pool cache;
therefore any runtime immutability comparison must start at capture and include
those caches. A geometry/RNG hash alone does not verify grid or graph identity.

The measured interval is reset after AST preparation and begins before degree
checks and input copies. Native receives only its remaining allowance, and the
spectral/layout wrappers clamp to the same absolute common deadline. The
geometry copies, diagnostic progress publications, provenance checks and final
hashing performed during the invocation consume that allowance. They must not
be subtracted when classifying timeliness. Stage intervals begin after their
progress publications, so their sum is not the whole solver wall; wrapper and
serialization residuals require explicit accounting. Output publication after
the terminal observation belongs to process wall. CPU time and cold/second
invocation measurements are separate; the second invocation is not necessarily
fully warm if the first skipped work or failed.

The controller uses an exclusive, nonblocking flock, refuses existing attempt
records/results, creates fresh per-input cache directories, runs input workers
sequentially, and passes the lock descriptor to the child. Atomic no-clobber
observation publication and exclusive raw logs preserve completed evidence.
The supervisor waits/reaps its child and terminates its process group after the
150-second watchdog with at most five seconds of grace. Closing a parent lock
descriptor does not explicitly unlock the inherited worker descriptor. An
observer disconnect is not permission to relaunch. The launch command must use
the **frozen** controller and helpers, not mutable working copies of diagnostic
scripts.

## Issues raised and resolved before diagnostic freeze

1. The initial worker checked only captured geometry and scheduler RNG for
   mutation. Root and this reviewer requested captured grid state (including
   caches), captured source/target adjacency, and source/target graph identity
   checks before/after physical work. The final worker now checks all five
   categories. Serialization preserves graph/node/neighbor iteration order,
   tuple/dictionary structure, and ndarray dtype, shape, strides and exact bits.
   Their cost stays in the common interval. A focused physical-grid mutation
   test preserves an otherwise valid witness but rejects its certificate.
2. The controller's external watchdog disappears if the controller is killed.
   An inherited flock prevents a competing restart but does not stop an orphaned
   nonpreemptible physical call. A worker kernel alarm and explicit death-path
   handling were requested before launch. The final worker arms a default-fatal
   kernel SIGALRM before heavy imports, using the unused portion of the absolute
   150-second launch allowance supplied by its controller. It is not reset for
   the second invocation. The original external 150-second timeout and five-
   second cleanup grace remain. Controller and observations retain alarm
   metadata; an alarm exit cannot manufacture a completed second observation.
   Direct alarm, already-expired deadline, and orphaned-child checks passed.
3. Preserve both the scalar remaining native timeout and its received internal
   deadline before clamping, as the instrumentation specification requires.
   These fields are now recorded and audited against the common deadline.
4. A capture check can increment its counter and then fail before full payload
   fields exist. The analyzer must retain and identify such failed/partial
   records rather than index missing geometry/layout keys and lose its summary.
   Dependency/instrumentation errors, missing second observations, and watchdog
   records must remain explicit. The final analyzer retains such rows with an
   audit error and suppresses their certificate/replay claims. Cold/second
   comparisons include the full structural state hashes. Separate synthetic
   partial-capture and structural-replay-mismatch cases passed. No replacement
   invocation is authorized.

## Final freeze and verification

The completed freeze contains 170 manifest-listed files, including all 47
unchanged production source files; the manifest itself is the 171st file.
Independent inspection after the focused checks found no additional frozen
files or cache directories. The single native invocation's fixed keyword
configuration matches every 037 spectral-control task, with seed and scheduler
seed zero. The only new instrumentation inside the copied `arrange` function is
the reviewed capture expression; independently deleting it recovers the exact
original AST. The native-only interpreter and dependency versions match the
manifest, and all prohibited package availability checks are false.

| Artifact | SHA-256 |
|---|---|
| Frozen manifest | `09bd7718cec3456ef5861c79f86065a582694902692c068b47240a7996f3aa3c` |
| Diagnostic file-map snapshot | `ec34d4e18e0fb72870e473b92669959f968288cec95bf62e2deb28bce85e9d78` |
| Initial final-freeze preflight | `5bef4bc0907566fefbf835b31779ac15f7e154a86d8960042b65b24feec3c7bb` |
| Independent recheck after focused tests | `fef4c2e4079ff650cbcc0e3a291fb8d849b71efea651d4d3034a334a4086c6ab` |
| Repeated analyzer-check summary | `99c6d65c94ba00ef286e6d8728ceada62c5ec92404e63c76d985b0a1a0a4052f` |
| Root repeated watchdog summary | `04030480c7363914348b14b3c5173ee7cc708b2d6cee4618e18f0fcd9f600f62` |

Independent repeats passed seven instrumentation tests and two analyzer groups.
The instrumentation cases use only a six-vertex path plus an isolate on Z2;
their fault injections and timings are not corpus performance evidence. They
check initial-state/chain replay, isolate coverage, original-graph validity,
zero proposals, stage quotas, mutation rejection, an already-expired common
deadline, and a valid Q=L witness whose final validation crosses the deadline.
The late witness remains valid diagnostic evidence, with TIMEOUT, timely=false,
and certificate=false.

The independent supervision and watchdog repeats encountered a sandbox
`PermissionError` when starting `ps`; their stdout/stderr and partial test
artifacts are preserved. These were observer restrictions in synthetic tests,
not candidate or corpus failures. Root then ran the same manifest-bound bytes
successfully: eight supervision groups in
`038-independent-review/supervision-root-repeat/check-one50ume`, and three
watchdog groups in `038-initial-prefix-certificates/checks/watchdog/check-yi_bl_u3`.
Both root stderr files are empty. Root's separate read-only check of PID 59347,
the orphan from the blocked observer probe, returned no process. Its prior
partial evidence remains in `checks/watchdog/check-9hsu7cik`; nothing was erased
or relabeled as a passing probe. Root also independently read the final frozen
implementation and ran its ordinary preflight successfully.

The independent source/input/environment/AST check can be repeated **before
launch** with a fresh output path:

```sh
.venv/codex-native/bin/python results/codex/038-independent-review/preflight.py results/codex/038-independent-review/root-final-recheck.json
```

The strict unstarted-output check will intentionally fail after an actual
attempt. The full record of source, input, environment and diagnostic hashes is
in `final-preflight.json` and `prelaunch-recheck.json` under that review directory.
Root must launch the frozen controller once and retain all outcomes; a positive
initial-prefix certificate still requires a separately frozen full-pipeline
paired ablation before any claim of net runtime benefit or production change.
