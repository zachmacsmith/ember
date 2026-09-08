# Independent preflight of the full-pipeline star comparison

2026-09-08. This review checks the frozen experiment described in
[the 037 protocol](037_induced_star_pipeline.md). It does not run a constructor,
refiner, or benchmark. Root owns launch after the preflight is complete.

The combined local and remote preflight passes. The remote check at
2026-09-08T04:44:12.339305+00:00 verified the staged source, prepared environment,
and absence of any prior attempt. Root was sent clearance to start the exact
frozen run. This report records preflight, not a launch or result claim.

## Frozen identity and the staging correction

| Identity | Value |
| --- | --- |
| Committed source | `13876c22b0576c3d41d54bffe5ec429e37f5d08c` |
| Source snapshot | `5dfc63cfb5bb2a674cb3e556e13d2b4d18a1857c7a8f296ba27cc2dd5075abc9` |
| Corrected transport | `55064e25db44189b2ddd0f77d0285f17ae4de3292656b7b55e624ceffd24e2e9` |
| Target | `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938` |
| Corrected manifest bytes | `4adea4d37bbb419bc82c1d86505ca4bca7b38668dec87600fc57c2efd8c1001e` |

The first manifest incorrectly contained local macOS interpreter paths.
Independent preflight identified them before launch; cluster staging rejected
them before publishing the remote run. That failure is preserved. Comparison
of the original manifest with the corrected one confirms that only
`candidate_python` and `mm_python` changed. The original manifest SHA256 is
`fcfc453835ae0e5289d569416f22ef2d6438b92157bd0463c1c0afac04ff8b43`.
No source, target, graph, task identity, configuration, or attempt changed.

The corrected interpreters are respectively
`/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python` and
`/home/dabh/ember-codex/envs/4e1fb892db12754e/mm/bin/python`.
Although this manifest records both environments, all 68 scheduled tasks use
the native environment; there is no MM arm in this experiment.

## Source, input, and task checks

The independent local script recomputes all 153 transport-file hashes. Every
one of the 47 source files equals both its committed Git blob and the current
reviewed source bytes. Relative to frozen 036, only `contact_repair.py`,
`native.py`, and `scripts/codex/pilot.py` change; the sole added file is
`induced_star_relocation.py`. There are no removals. The corrected `field.py`
remains SHA256 `a055553988ba3db17ef3588986c1719070c3fcfae4bbfcce7a7084ffe45c7690`.
The complete old/new hash pairs are in the machine-readable preflight result.

The final recorded 110-test run includes actual source and test hashes.
Those hashes equal the committed files and the corresponding frozen candidate
files, including the final integration test
`5e335be88ebb48e828e4d049f3521964a340bb1182b3762f4c2b1c8cbe6f37d4`.
Its recorded exit is zero and its import blocker records no forbidden attempts.
This review checks the execution record and identities; it does not claim to
have independently rerun those tests. The log SHA256 is
`2be4362365cb7a7be5fb5e4f3553947a4a1d04837d45b3e460a9f19822089ca9`.

All 34 source records, both corpus sidecars, and the target are byte-identical
to 036 and retrieved 032. The exact target has 4,800 vertices and 45,864 edges.
Selection identities, original-source hashes, and normalized topology hashes
are recomputed, and candidate source records contain no family metadata.
The 34 solver inputs represent 35 family memberships; the shared king/
frustrated-square source appears only once. Original Sudoku remains absent.
The corrected Sudoku supplement is not part of this run. Count bounds are
necessary conditions, not a feasibility certificate for any unevaluated input.

Every task ID is recomputed from its complete task record. There is exactly one
task for each input and arm, all at solver seed 0 and 60 seconds. The two tasks
for each source are adjacent in the frozen order; each pair contains each arm
once. The treatment configuration is exactly the spectral contact control
plus `polish_star_policy='matching'`. No direct singleton relocation is enabled.
All 34 control task records otherwise reproduce 036 after excluding the new
source snapshot and corresponding task ID. Configuration fields and parsed
function defaults retain the protocol's shared work and visit limits.

The planned supervisor lifetime is 6,420 seconds: 300 plus the sum of the
68 per-task 60-second allowances and 30-second worker grace periods. Quality
is credited only for externally timed successful calls within 60 seconds;
the grace period is not extra successful solver budget. Complete process time
includes the separately recorded startup/import and validation overhead.

## Observer failures and preserved evidence

A fresh status query succeeded before the remote import probe: 68 planned,
zero finalized, no controller, active record, or supervision record, free lock,
stopped tmux, and inactive service. Its displayed result is preserved as an
explicitly labeled transcription. A second status query, intended to capture
raw output, failed to resolve the jump host from the reviewer's sandbox.
This is an observer connection failure, not a controller or solver failure.
Root executed the independent probe through its working SSH context.

The first remote probe stopped because its audit code indexed distribution
metadata by the display name `dwave-networkx`; installed metadata uses a
different normalized spelling. The raw script, empty stdout, stderr, and hashes
are preserved. This was an audit-script error, not evidence of a package
version mismatch. The corrected probe uses `importlib.metadata.version(name)`.
It changes neither environment nor frozen input and runs no solver.

The probe records source directories before and after its isolated `-B` imports.
Numba may create empty `__pycache__` directories at import despite Python's
bytecode setting. Empty directories are recorded rather than removed; every
frozen source byte must still match, no extra source files or compiled caches
are permitted, and the per-task result, claim, log, and JIT-cache directories
must remain empty. Such an empty directory does not constitute compiled-code
warmup. Preexisting directories cannot be attributed more precisely than the
earlier import-only probe without a saved earlier directory inventory.

## Review artifacts and limits

Artifacts are under `results/codex/037-independent-review/`. The local final
result is `preflight-final.json`; `preflight.py` accepts an exclusive-create
output path so a repeat can preserve the original result:

```sh
.venv/bin/python results/codex/037-independent-review/preflight.py results/codex/037-independent-review/preflight-repeat.json
```

The independent remote script is `remote_preflight.py`, with its successful raw
stdout and stderr in `remote-preflight.json` and `remote-preflight.stderr`.
No remote start command belongs to this review.

The remote probe checked all 153 transport files and 47 source files before
and after importing the frozen native, contact-repair, and star modules.
Python 3.10.12 resolves all three implementations inside the frozen run. Native
module searches find no MM, `_minorminer`, `minorminer_fork`, or busclique;
the raw distribution inventory contains no corresponding installed package.
There are no forbidden import attempts or loaded forbidden modules. Package
versions match the prepared pins: NumPy 2.2.6, SciPy 1.15.3, NetworkX 3.4.2,
Numba 0.65.1, and dwave-networkx 0.8.19. The separate unused MM environment
contains MM 0.2.22 as expected.

All five output/cache directories remain empty, no controller or supervision
exists, and the lock and tmux checks show no active run. The prior 032 controller
is complete with its lock free and tmux stopped. One empty
`algorithms/factored/__pycache__` directory was already present before the
successful probe; the successful rerun created no additional directories.
No additional source files or compiled caches were present. Remote stderr is
empty. Host load averages were approximately 15.74, 15.11, and 14.95 on the
32-CPU shared host; this is not a claim of exclusive or idle-host timing.

`combined-clearance.json` binds the successful local and remote identities.
Its artifact-map digest is
`4d90198e793d3ae8bb728391bd7f618f622512e534608c9a517c841ed29c1859`.
The local auditor SHA256 is
`5d8e26d0ccf0b6f9c8019f7b9bfad3cf167daaff4113e9a15c14db51fc3c6a20`;
its final result is
`6f598803e804dea1797c0452dff77cf48b4d06ccf8e4d000b3ff05ea743c9f9c`.
The revised remote auditor is
`5cd3b14e6436bc455f9647cf29674d2cae90a5955bda681c597ddbdabe79bcb0`;
its successful result is
`abb44ad857532465568fdee6db066dddedc6418873d3be6244fbda6dd8b7d436`.

Passing preflight establishes the declared experiment's identity and readiness,
not an embedding-quality result. One seed on inherited sources cannot establish
across-seed variance, family population means, or unseen-instance generalization.
The 036 replay is cross-platform quality/provenance evidence only; within-037
times must remain separate. Any historical 032 MM quality comparison must retain
the original successes and timeouts and cannot supply a contemporaneous MM
timing comparison. No arm selection by source or family is authorized.
