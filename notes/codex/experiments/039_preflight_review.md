# Independent 039 preflight

2026-09-08. **The recorded local and remote prelaunch gates pass.** Root alone
launches the predeclared comparison. This review made no candidate import,
constructor, refinement, prefix, benchmark or remote-launch call. Root executed
the reviewed remote probe through a fresh SSH connection and returned its raw
output and zero exit status.

The combined record is
[`preflight_final.json`](../../../results/codex/039-independent-review/preflight_final.json).
Its local input is `local_preflight_002.json` (SHA256
`5987773fa04fca646f4509fcbfde16f78f8d7744ae99f928aa778bacc576c220`);
its remote input is `039-launch/remote-preflight.json` (SHA256
`afd0db9a1ff3e8c71b806d96d18a0185b4f5f37c75db6ede67245765ca911342`).

## Frozen identities and checked scope

| Item | Verified identity/count |
| --- | --- |
| Integrated commit | `c61c474ca7bdd2f6e455cfa67f34af72b8d537cf` |
| Source snapshot, 48 files | `63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473` |
| Pilot manifest | `84197f8e3c2e4543ba5786eb51e31b1a57e1ade4de32c7ed51cb55d5d6a25bc3` |
| Transport map, 154 files | `5fa828ca4db741120dcc2998f5bdb4d2f30563ae6c9b314709190262b85dce39` |
| Target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Root freeze record | `fa0eb0a3c0b79a1592b9e694356e3ed5e22de1b8c061a2236c3192b2c84fce44` |
| Evaluator manifest, 103 files | `dc7632dd7d50cb72e81360f495d5b1a98c3a2ce68121c0ba4191dbfe9fa6c145` |

Every source file matches its committed Git bytes. The six reviewed production/
test hashes match the frozen source where applicable and both the root's
36-test record and author's 160-test record: successful exit, unchanged source
hashes and no prohibited imports/loaded modules. This checks their execution
records; it does not claim another test execution. All eight protocol/review
copies match their recorded hashes, working files and committed bytes. Relative
to 037, only contact/native/pilot change and the reviewed connected core is added.

All 103 evaluator files are byte-identical to the corresponding audited 038
originals, label maps, normalized graphs and target. Independent integer-label
and edge checks reconstruct every normalized graph exactly from its original
and inverse map, preserving isolates and all edges. The actual ideal Z12 record
has 4,800 nodes, 45,864 edges and maximum degree 20. All 34 distinct solver inputs
and 35 memberships remain; the king/frustrated-square structure has one aggregate
weight and original Sudoku remains absent. Evaluator-only originals are not
worker inputs.

Each of 68 task identities is recomputed. Control and treatment use seed zero,
60 seconds and identical configurations except
`polish_star_policy='connected'`. The explicit 34-input shuffle and per-input
arm shuffle reproduce exactly; every pair is adjacent. Parsed function defaults
confirm four configured passes, 512 groups, 500,000 refinement units, 50,000 per
visit and the retained reconstruction settings. The connected auxiliary share
is 25,000, including selection/setup/query/refresh, without another 2,048 cap.
No family policy, supplemental source or best-of output selection appears.

## Remote state and limits

The successful remote observation at Unix time `1788847769.8447886` confirms
all 154 staged file hashes, all 48 source files, 68 tasks, empty results/worker
results/claims/logs/JIT-cache directories, no prior attempt and a free run lock.
The current run and seven earlier project runs have no matching live worker or
supervisor. This describes the prelaunch observation, not subsequent execution.

Both interpreter paths remain under
`/home/dabh/ember-codex/envs/4e1fb892db12754e/`, preserving their venv paths.
Python 3.10.12 and every installed distribution agree with the prepared records;
NetworkX 3.4.2, NumPy 2.2.6, SciPy 1.15.3, Numba 0.65.1 and dwave-networkx 0.8.19
match the fixed pins. Native MM/busclique modules and distributions are absent;
the separately checked MM environment retains 0.2.22 but supplies no 039 task.
The probe uses stdlib metadata and module-presence inspection, so dependency
importability was not re-exercised and no candidate module was imported.

`Linger=no`, available tmux/timeout and `KillUserProcesses=false` establish the
existing disconnect-resistant route. The 60-second solver budget is distinct
from the 90-second worker watchdog and 6,420-second outer supervisor. Empty
per-task JIT caches and one-thread settings do not imply cold OS caches or
reserved CPUs. Report same-run timing descriptively under observed load.

## Reproduction and retained diagnostic failure

The local stdlib checker is `results/codex/039-independent-review/preflight.py`,
SHA256 `4405c7048f59d2a12ba6228f9903ff9d2f2668cd19fa60c4acfd754d8a401e32`.
The remote helper is `remote_preflight.py`, SHA256
`cf4e1c65ff22a60d2fba3c256edfc986da482ecb4fbec9a7c6c010c0f1ecf4ff`.
Local reproduction before any attempt, using a new output file:

```bash
.venv/bin/python results/codex/039-independent-review/preflight.py \
  --run results/codex/039-connected-star-pipeline \
  --revision c61c474ca7bdd2f6e455cfa67f34af72b8d537cf \
  --reviewed-hashes results/codex/039-protocol/reviewed_integration_hashes.json \
  --output results/codex/039-independent-review/local_preflight_003.json
```

Twenty tiny corruption/path checks pass, including wrong label inverses,
duplicate/foreign edges, missing isolates and solver-visible metadata. The
first negative fixture merely swapped symmetric path endpoints, which preserves
the normalized graph; its rejection expectation was wrong. That failure and
its reason are preserved in `synthetic_v1_symmetric_map_expectation.json`.
The corrected negative case swaps a center and endpoint; verifier logic did
not change to reject a valid graph equivalence. The passing report is
`records-xa1p17hb/report.json`.

No preflight gate remains unresolved for the fixed single start. Complete
original-graph output validation, diagnostic work reconciliation and quiescent
hash-verified retrieval remain post-run obligations. One development seed,
unsaved intermediate chains and the absence of an MM or singleton-center arm
retain the inference limits recorded in the protocol review.
