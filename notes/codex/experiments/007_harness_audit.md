# Experiment 007: independent audit of the pilot harness

Date: 2026-09-07, America/Chicago. Scope: read-only review of `scripts/codex/pilot.py` and the preserved `results/codex/005-harness-smoke` artifacts. The root agent owns harness edits. This audit did not run an embedding solver, modify the harness/results, or commit changes.

The audited harness version is preserved in the smoke run at `source/scripts/codex/pilot.py`, SHA-256 `6e8ae8a578cf0c63d3e0f15c47a7957f1519ba700f4a637e239e300adbc2029f`. Its aggregate source snapshot is `9d4ab4bea5c55a630e307220321c9af7aa2813ce8b38677e5a0b3bb4f280ddcb`. All 42 files listed in that manifest still matched their recorded SHA-256 values when read. Line references below refer to this preserved version, so later root-owned fixes do not invalidate the evidence locations.

## What the smoke run establishes

The run contains two tasks for K40, seed 0, 20-second solver budget, ideal Z12 with 4,800 qubits and 45,864 couplers. Both use the same recorded source and target hashes and ran on `dabhmbp`.

| Arm | Recorded result | Solver wall | Whole child-process wall |
|---|---|---:|---:|
| MM | SUCCESS, ACL 4.2, 168 qubits, max chain 6 | 2.7122 s | 3.0293 s |
| native-packed | ERROR: `KeyError: 'zephyr_index'` | 0.0704 s | 1.5131 s |

The candidate error is a harness serialization defect, **not evidence that this algorithm fails to embed K40**. `graph_record()` saved node IDs, edge endpoints and graph-level metadata, but omitted node attributes (`:46`). The frozen target claimed `data=True`, yet the reconstructed target lacked the `zephyr_index` attributes expected by the existing Zephyr-layout code (`:115`). Input hashes matched because they faithfully described the already incomplete serialization. The root agent independently identified this defect and is preserving node/edge attributes with a graph round-trip regression. The original failed run should remain an infrastructure-failure record.

The candidate row reports no loaded prohibited embedding module or attempted prohibited import, and its recorded installed minorminer version is null. MM records minorminer 0.2.22. Both rows report Python 3.10.19 and the same recorded versions of NetworkX, NumPy, Numba, SciPy and dwave-networkx. These observations support the intended environment separation for this smoke run; they do not prove comprehensive independence of every possible execution path.

The root reports that an earlier run, 003, incorrectly resolved a virtual-environment Python symlink to its base interpreter. The audited version already preserves the venv invocation path with `.absolute()` instead of `.resolve()` (`:264`). This audit did not independently inspect run 003.

## Material findings and minimum fixes

### 1. Graph round-trip correctness is a prerequisite to algorithm scoring

Preserve the node/edge attributes consumed by the algorithm, or reconstruct and verify an explicitly declared coordinate representation. Both methods must receive equivalent original target structure. Hash the full serialized input actually supplied, and distinguish this content hash from any topology-only identity used for duplicate detection. A matching hash is not a test that serialization preserves the required semantics.

**Minimum check:** round-trip an ideal Z12 and assert node IDs, edge endpoints, relevant node/edge attributes, and graph metadata are equivalent; invoke the coordinate/layout access used by the candidate on the reconstructed target. This catches the observed defect without running a research benchmark. Root is implementing this check.

### 2. A controller restart can duplicate a surviving worker

The controller holds `controller.lock`, launches a child with default descriptor inheritance, and writes `active.json` afterward (`:276`, `:304`). The lock is released if the controller dies, while the worker may continue. A replacement controller never reconciles `active.json`; it starts any task lacking a result file (`:294`). Both old and new workers can then replace the same output path (`:180`, `:321`), with the final writer determining which result survives. Logs are also opened with mode `w`, so a second attempt overwrites the first attempt's log.

This is a concrete process-lifetime race, even though the current controller runs only one worker at a time. Wi-Fi switching is harmless only when the remote controller is actually detached from the SSH session; the script itself does not detach it.

**Minimum fix:** keep the run lock alive in the child using `pass_fds=(lockfile.fileno(),)`, and write a unique attempt record before `Popen`. The latter covers a controller death after launch but before the active-PID record is written, followed by child failure without a result. A resume must not silently turn that ambiguous attempt into a fresh independent trial. Store separate logs and records by attempt ID. Root proposed the inherited-lock approach during this audit; it is a reasonable minimal duplicate-suppression mechanism.

**Remaining limitation:** the parent's watchdog disappears when the controller dies. A hung surviving worker can keep the inherited lock indefinitely. Remote robustness therefore also needs an external lifetime supervisor, or a documented orphan-reconciliation procedure that identifies and terminates the exact old worker before any replacement attempt. PID reuse must be distinguished using host/process-start identity, not PID alone. A detached normal completion and a controller-death recovery are separate acceptance cases.

### 3. Worker output and finalized task results are conflated

The worker writes directly into `results/` before exiting (`:180`). The controller subsequently reads that file, adds process duration and return code, and replaces it (`:315`). A controller dying between these actions leaves a file that the next controller accepts solely because it exists (`:296`), even though finalization never occurred. Conversely, if a worker writes output and then hangs or exits abnormally, the controller retains its status without explicitly resolving whether it is an accepted solver result or an incomplete process execution.

**Minimum fix:** separate worker-output files from controller-finalized result files and validate both schemas. With an acquired run lock, a complete worker output from an interrupted controller can be finalized without rerunning the solver. Mark `controller_interrupted=True`; use null for unobserved `process_wall` and `returncode`, not invented zeroes. An attempted task with no complete output needs an explicit interrupted-attempt outcome. If result validity is retained despite a later teardown error, state that policy and retain the process anomaly separately. Root proposed this separation and interrupted-finalization policy during the audit; it addresses the observed protocol gap.

### 4. Task and terminal-result identity are not checked on resume

Initialization hashes each task (`:254`), but `execute()` trusts task contents and any existing result without recomputing or comparing their identity (`:294`). The worker checks source/target content hashes (`:124`) but not the task digest or its relationship to the run manifest. Therefore editing a task's timeout/configuration while leaving its ID unchanged, or accidentally placing another run's result at its filename, can silently mislabel or skip work. The controller's source-file verification (`:284`) is useful, but does not cover these task/result mismatches.

**Minimum fix:** recompute each task ID from its canonical fields excluding `task_id`; require filename, manifest membership, source snapshot and target identity to agree. Recompute the aggregate source snapshot from the file-hash manifest. Validate result task/attempt IDs, graph hashes, method, configuration, seed, timeout and source snapshot before skipping or promoting a record. Reject duplicate task IDs in the manifest. Validate required terminal fields rather than equating file existence with completion. Root is adding these identity checks.

### 5. Late-result quality is mixed into ordinary quality fields

The worker correctly detects `solver_wall > timeout` and sets `TIMEOUT` (`:156`), but it still writes ordinary `acl`, `qubits` and `max_chain` for any structurally valid embedding (`:163`). An aggregation that selects rows merely because ACL exists will credit late answers. The generous outer watchdog (`timeout + 30`, `:308`) is an operational limit; it must not become extra credited optimization time.

**Minimum fix:** only timely successful outputs get scored quality fields. Put any valid late answer's metrics under clearly named `diagnostic_quality`, alongside its mathematical-validity flag and preserved witness. The root proposed this change during the audit. Require screening summaries to validate status and the declared score-eligibility flag, not just metric presence.

The timed lambda includes source/target `.copy()` for both methods (`:138`, `:143`); this is symmetric runner preparation within the reported solver interval. Imports, materialization and verification are outside that interval. `process_wall` includes child startup, imports, input loading, solving, verification, serialization and controller wait/teardown; **startup is not separately measured**, despite the manifest wording (`:268`). Label it whole-process elapsed time, or add actual phase timestamps. Do not call `process_wall - solver_wall` pure startup time.

### 6. Fresh processes do not imply a fixed JIT-cache state

The source snapshot is shared among worker processes, and `factored/field.py` has Numba `cache=True` kernels. A successful first run can generate caches reused by subsequent tasks. The comment claiming cache mode is recorded per task (`:133`) is not implemented in the task schema. Method ordering can therefore determine which arm pays compilation cost, and a resumed run can have a different cache state. No `.nbc` cache files existed in the inspected smoke snapshot, consistent with its early native failure; that does not test the successful-run policy.

**Minimum fix:** declare either cold per-task cache directories, or an explicitly prewarmed environment with initialization costs recorded separately. Record the actual policy and relevant cache/compiler/CPU information. Cold/warm choices are experimental conditions, not implementation optimizations to change after looking at results. This matters for budgeted ACL as well as timing: compilation consumes time that would otherwise be available for search.

### 7. Environment and error provenance need a small amount of additional evidence

The correctly preserved venv path and snapshot `sys.path` insertion are useful (`:98`, `:266`). However, the manifest records absolute paths rather than interpreter identity, and inherited Python environment variables or installed import hooks are not ruled out. Report `sys.executable`, `sys.prefix`, `sys.base_prefix`, the environment lock/hash and the resolved `__file__` paths of imported candidate modules. Assert that project modules used by the candidate come from the frozen snapshot. Starting the child with Python isolated mode is compatible with the worker's explicit snapshot-path insertion and reduces dependence on inherited Python configuration.

The import blocker plus absent MM installation is a helpful dependency check, not a proof against all arbitrary aliased/native/subprocess code. Retain the source/call-path audit and environment inventory. An environment containing a prohibited package currently raises before the blocker exists, so it is labeled generic `ERROR` rather than a dependency/preflight failure (`:108`). A malformed response or a validator exception also becomes generic `ERROR` (`:170`).

**Minimum fix:** record an execution phase such as environment preflight, input materialization, algorithm import, algorithm call, validation, or serialization, and preserve an infrastructure-vs-algorithm failure category. Do not infer an embedding-method failure from a harness exception. The K40 smoke error is an example of why that distinction is necessary. Full nested dependency isolation remains a separate eligibility audit, not a claim established by this smoke run.

## Suggested completion sequence

For the next local screen: repair and verify graph round trips; validate task/result identities; separate terminal finalization; move late quality to diagnostics; record environment identity and a fixed cache policy. Re-run a small source/target transport and worker-lifecycle check before drawing algorithmic lessons. Preserve the failed 005 artifacts and use a new immutable run directory for corrected harness/source inputs.

Before remote unattended execution: verify real detachment from SSH, inherited-lock behavior across controller death, explicit interrupted-attempt reconciliation, and a bound on orphaned worker lifetime. Preserve attempt records and append/reconnect progress without overwriting old results. Atomic `os.replace` avoids readers seeing a partially written JSON file; it is not a full power-loss durability guarantee without file/directory synchronization. Power-loss durability is broader than the requested Wi-Fi-switching requirement and should not be implied unless tested.

All these changes are general experiment-protocol fixes. They do not choose graph-specific algorithm behavior, repair a weak family by special-casing its identifier, or convert development screens into confirmatory evidence.
