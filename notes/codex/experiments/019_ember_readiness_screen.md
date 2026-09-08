# First end-to-end screen on the selected Ember corpus

Protocol fixed before any outcomes from this run. Use all 34 distinct solver
inputs from readiness selection 017, representing 35 family labels with one
exact duplicate shared across two labels. Preserve the missing Sudoku family
and original input-error ledger. All these inherited inputs are development
data. One input per family and one solver seed cannot establish family means,
ACL variance, or generalization.

Run exactly three independent arms on every input, at seed 0 and with a 60-second
solver allowance: stock MM, the fixed width-one joint reference, and the same
constructor/refinement with both revision-016 changes. This is 102 trials.
Candidate arms receive no MM embeddings. Method order is deterministically
shuffled per input; candidate and comparator run sequentially on the same host.
No result is selected between arms to form an algorithm output.

The revision is selected globally from the completed 016 ablation: its fixed
mean ACL was lowest among the four tested policies, with 21 fewer total qubits
than the reference across the 18 saved incumbents. This is modest evidence;
one case regressed, and the incremental boundary-site gain appeared in only
one case. Broad input coverage is the next test, not a claim of success.

Both native arms use geometric search with 1000 proposal evaluations, four
refinement passes, width one, 512 total group attempts, group sizes 1–4, and
500000 charged work units. The revision uses 16 additional boundary-contact
sites and round-robin neighboring-group coverage. All settings are fixed across
inputs. Initial search, conversion, pruning and refinement are one algorithmic
pipeline; there is no family dispatcher or runtime competition among solvers.

Use hyde03 with the existing separate native and MM environments under
`/home/dabh/ember-codex/envs/4e1fb892db12754e/`. Every worker is a fresh process,
uses one numerical-library thread, and has an empty per-task JIT cache. Solver
wall includes compilation and source/target copies; process wall is separate.
The detached tmux controller and inherited run lock preserve execution through
SSH disconnection. Kernel and controller watchdogs bound stuck workers; late
valid embeddings retain diagnostic quality but are excluded from timely means.

The manifest will freeze exact source, graph/target records, configurations,
task identities, original/readiness selection sidecars, and interpreter paths
before transfer. Transport must include both selection sidecars and verify them.
Retrieve only after quiescence and revalidate all embeddings and provenance.
Report each fixed arm separately, failures and missingness explicitly, and
timings only within this host/run. The existing local path smoke is separate
and is not pooled into this screen.

Expected outcomes are uncertain. The small development gains may disappear on
these new structures or fail because construction itself cannot produce a valid
embedding. Both are useful failure evidence. Retain all inputs and use observed
failure mechanisms to guide general revisions, rather than graph-specific rules.

## Launch record

The run was frozen at commit `d270f2bb1fe6a6808bc18a89a9a3ff4af36a9dac`.
Source snapshot: `466bf012bb71aeb6ca9981fbef1935a00e6e27580328481741fc0e2f7fa00024`.
Target hash: `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`.
Verified transport digest: `e94992ad66322fee4db82d02191468305345ffde37b782513811bfe21fe07b9d`.
The local frozen input is `results/codex/019-ember-readiness-screen`; the remote
run is `/home/dabh/ember-codex/runs/019-ember-readiness-screen` on hyde03.

The detached supervisor started successfully under tmux session
`ember-codex-04b4bb38085f50045e5a` in the isolated `ember-codex` tmux server.
Maximum supervisor lifetime is 9480 seconds, derived from all 102 trial
allowances and watchdog overhead. This is an upper bound, not an expected runtime.

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 status 019-ember-readiness-screen
.venv/bin/python scripts/codex/cluster.py --host hyde03 fetch 019-ember-readiness-screen results/codex/retrieved/hyde03/019-ember-readiness-screen
.venv/bin/python scripts/codex/analyze_pilot.py results/codex/retrieved/hyde03/019-ember-readiness-screen
```

Fetch and analysis must wait for verified quiescence. Do not relaunch a live
controller or treat a transient observation failure as process death.

A subsequent fresh SSH status check confirmed the live tmux session, occupied
worker lock, controller PID 115997, worker PID 116011, and one finalized SUCCESS
out of 102. The old systemd service fields are inactive because this run uses
tmux supervision; they are not a failure of the active controller.
