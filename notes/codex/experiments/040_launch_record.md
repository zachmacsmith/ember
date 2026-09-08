# 040 physical-line locality diagnostic: launch record

2026-09-08. Root launched the frozen diagnostic once on hyde03. Controller
143531 started at **07:37:00.001 UTC**. A new SSH observation at 07:37:20.614
found it running, first geometry worker 143539 active, the inherited lock busy,
and its detached tmux session present. There were no completed input records
at that observation. This records a launch, not a locality, timing or ACL result.

The run is `/home/dabh/ember-codex/runs/040-physical-locality`. Local preparation
is `results/codex/040-physical-locality`; root lifecycle evidence is under
`results/codex/040-launch`. Never repeat its start after a lost connection,
observer failure, partial output, timeout or adverse result. Reconnect to observe
the existing run. Retrieve only after controller/worker process, inherited-lock,
tmux and supervisor-exit evidence establishes quiescence; retain failed runs.

## Identity and scope

| Frozen item | SHA256 |
| --- | --- |
| Execution manifest | `3f6155277ba866f376427b105371bb7b8a8abc70cefe961542f5a139534e096d` |
| Diagnostic map, 10 files | `0c68ab814eb76aea5876ec79386d1cbabd59f8a37197c688e1d12d447c412733` |
| Transport map, 165 files | `9dfba5ece5e210c9ca932c5b4fa277e807ceafb3b67d083239c61590fdbe8865` |
| Prepared map, 153 files | `a5ddbd44613f37ebfa63c2e4232920573775fd3727e647dedce0b968b945bdcf` |
| Frozen production map, 48 files | `63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473` |
| Exact target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Remote focused-check summary | `18f703ee6e9c58e0dc4a228b785352ca2e682a7c60724065e4bbd6cb381c6c6b` |

The production revision is `c61c474ca7bdd2f6e455cfa67f34af72b8d537cf`;
accepted diagnostic notes are committed in `42b941b3`. The source is unchanged.
All 34 original development structures and 35 memberships are retained, with
the shared king/frustrated-square structure counted once in aggregates and the
original Sudoku absence explicit. Input order is the copied solver-input ledger
order. Each worker reads the canonical normalized graph. Hardware is ideal Z12,
with 4,800 physical vertices and 45,864 physical edges.

Each fresh geometry worker performs reference then capture with spectral seed
zero, scheduler seed zero, `snap=True`, and 1,000 asks. Both invocations use the
same 60-second common allowance. Capture copies the initial state and first 32
adopted fully repacked states, then the original search continues to its stop.
No conversion, seeding, completion, pruning or contact refinement is called in
that geometry phase. A separate offline process compares the unchanged raw-wire
conversion prefix with an exact cache update on every saved state. It never
calls seeding, completion, pruning or refinement. Raw physical validity is
reported independently; raw counts are not final ACL.

Geometry has one absolute 150-second process allowance, offline its own absolute
60-second allowance, and each has five-second process-group cleanup grace. The
detached outer supervisor has 7,780 seconds plus five-second hard-kill grace.
Workers are serial and use fixed single-thread settings; each input has a fresh
JIT directory. The shared host is not an exclusively reserved CPU. No timing
comparison to a different host or past MM run is planned.

Complete matching nonbinding geometry and clean timely phase completion are
required for full timing conclusions. Every partial, missing, invalid-raw,
interrupted or mismatched observation remains visible. The fixed falsifiers
reject cache speed benefit when aggregate update cost is at least full raw
conversion cost, and defer per-proposal use when added update cost exceeds 10%
of corresponding adopted-transition work. Zero denominators are undefined.
Missing coverage prevents an all-input cheapness conclusion. A successful
diagnostic would still require a separate search-policy design and full-pipeline
experiment; it would not establish a better embedding algorithm.

## Accepted prelaunch evidence

Root read and accepted the independent geometry/lifecycle and offline reviews,
verified 1,085 retained review artifact hashes and all diagnostic identities,
and passed the local final preparation check. Remote readiness confirmed the
native environment, absent prohibited packages, absent intended run path,
tmux/timeout and `KillUserProcesses=false`.

Staging verified all 165 transported files. Remote preflight matched the exact
manifest, code, target/input copies, ledger order and pinned environment, and
found no prior controller, worker, lock or session. The full final **23-check**
suite then passed in the actual hyde03 native interpreter with zero failures,
errors or prohibited imports, matching diagnostic and environment records.
Its tiny/synthetic inputs and JIT directory are separate from corpus outputs.
The remote start operation independently requires that saved pass before launch.

Root saved `root-prelaunch-acceptance.json`, invoked start once, observed exit
zero, and verified the live controller through a new SSH connection. No outcome
has been selected and no competitor embedding enters this diagnostic.

## Completion and retrieval

The original controller finished at 2026-09-08 07:57:57.603 UTC
(`1788854277.6030006`), with all 34 inputs and 68 phases recorded, zero exits
and no phase overruns. Fresh status and terminal-inventory observations verified
no matching processes, a free lock, stopped tmux and supervisor exit zero.
The terminal inventory contains 2,654 files, artifact-map digest
`13d0e1782fa2679efe4943d7d8b846816b5a7694a5e868c83041eec4b21ac3e1`.

Root retrieved only this inventory into
`results/codex/retrieved/hyde03/040-physical-locality` and verified the complete
local file map before writing `retrieval.json` at Unix time
`1788854592.912711`. Transfer exited zero and preserved the original controller
record. The inventory-file SHA256 is
`6c79615a3a8ac90b757ec41f23f87127e47a5c6b55b03aaf692562c08e16ecb1`.
No experiment restart occurred. These lifecycle and transfer facts do not by
themselves establish physical correctness or a speed benefit; those require
the saved-data results audit.
