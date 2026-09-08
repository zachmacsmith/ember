# Connected-policy integration

2026-09-08. Stable for root's independent review and source freeze. Implementation
follows the previously critiqued [integration plan](connected_star_integration_plan.md)
and draft [039 protocol](experiments/039_connected_star_pipeline.md). No corpus
run, protocol amendment, commit or default-policy promotion occurred here.
The frozen connected core, shared dependency, author tests and 038 artifacts
were not edited.

The new experimental native option is `polish_star_policy='connected'`; contact
refinement receives `star_policy='connected'`. Both boundaries reject unsupported
graphs and the direct-singleton combination before disabled-polishing returns.
The pilot method `native-search-joint1-contacts-spectral-connected-star` differs
from the existing spectral control by exactly that policy option.

The existing failed-ordinary-visit loop constructs one `ConnectedStarSearch`
instead of `StarSearch` in connected mode. It adds no visits or groups, considers
each center at most once per pass, and suppresses the auxiliary query after any
ordinary acceptance, including an equal-Q redundancy improvement. Every query
and cache refresh uses the same remaining live visit and global allowance.
Auxiliary work remains `max_expansions // 20`; the connected core has no separate
2,048-unit cap. Returned work describes already charged operations and is not
charged again.

Connected diagnostics use `connected_star_search` with `policy='connected'`,
and connected commits/maintenance use operator `connected_star`. The returned
certificate's signed redundancy change and actual member-growth count enter
move/search aggregates and the trajectory only after the final commit deadline
check. A connected block may contain 23 source vertices even when ordinary
group sizes are limited to 1–4. Certified proposals, complete assignments and
actual commits remain separate counters. Cache refresh occurs after publication
of the valid incumbent; a failed refresh disables further auxiliary work and
retains that embedding.

The off/default path keeps its original loop and diagnostic keys. The historical
matching path also keeps its original keys, operator and member-growth behavior.
No connected diagnostic is added to either historical policy.

## Checks and evidence

`tests/algorithms/test_connected_star_integration.py` adds 36 focused tests.
The first guarded run passed all 36 in 2.82 seconds. A broader guarded run passed
160 tests in 5.44 seconds: new integration, historical matching integration,
connected core, native, generality, spectral integration, contact repair and
direct-singleton integration. These are test-suite durations, not solver
performance comparisons. Both runs used the project Python 3.10.19 test
interpreter, with single-thread numerical settings and the MM/busclique import
blocker installed before implementation imports. No prohibited import was
attempted or loaded. Exact versions and commands are saved in each invocation
record. There were no failed attempts in these two runs; the dependency emitted
its existing `dwave-networkx` deprecation warning.

The new tests cover:

- A real connected commit with center growth 1→2 and total Q falling by one;
  independent full original-edge validation and exact Q/R/growth accounting.
- A strict-Q commit with redundancy change −2, and a late certified growth
  proposal whose commit counters and trajectory remain unchanged.
- Once-per-center scheduling, no extra singleton sweep, equal-Q ordinary
  suppression, real ordinary-move cache refresh, and refresh interruption at
  the exact remaining visit limit.
- Shared global/visit/auxiliary accounting and a charged synthetic prefix over
  2,048 units demonstrating that the connected interface has no singleton-query
  cap. This injected-work check is not an efficiency measurement.
- The independently constructed ideal-Z12 degree-22 source star: one failed
  ordinary visit commits a 23-member selected block, center 3→2, total Q 25→24,
  with signed redundancy change −1. This is a local mechanism witness only.
- One fixed actual native spectral/Z12 smoke call: 18 seeded source vertices
  plus an explicit isolate, 20 layout asks, one contact pass, eight group visits
  at most, and no quality comparison. Original graphs remain unchanged and the
  final embedding is independently valid.
- Eight exact off/matching replays against immutable git commit
  `6044e200ff36c8585938e8113189d9c3200c8a4b`, across both group policies and
  successful/adversarial fixtures. Outputs and all non-time diagnostics agree.
  The four matching cases exercise two queries each and 2/1/2/1 actual matching
  commits; this is active-path coverage, not only no-op replay.

Raw invocation, stdout/stderr and hash records are under
`results/codex/connected-star-integration-checks/`. `focused001/summary.json`
has SHA-256 `6323ffc85b4f63a2fa7fd9cc1d33b2e4dd630c431615f2c126e3460df45d4ae7`;
`regression001/summary.json` has
`6b8ded53a50e5c4d2b99d7b9e5c03dbd66ffb4fc752412b3b990b8723d74d4a3`.
The active historical matching coverage record is
`historical_matching_coverage.json`, SHA-256
`b0ea68064ad3971c27cef5d2700388191d62b03008864afc34daf110f4c2bedd`.
`git diff --check` passes.

## Stable source identities and additive reproduction

| File | SHA-256 |
|---|---|
| `factored/contact_repair.py` | `0ce3c2e7f7287a173294190e476a47901d606043970eb46d6ff3f48ba9ec5f97` |
| `factored/native.py` | `1455154dcc31718b669c8deb75a68656dde5ef695b31bec00df7517adc4f1971` |
| `scripts/codex/pilot.py` | `10f74368859fc4e14f16bc921d1a0c4295b6df754cea153b4d67ec3a8c70f8ad` |
| New integration test | `d99f27a46fe4cb95a8fcfe235b90c6b239c93f04ee46679f682044bbbedb8216` |
| Unchanged connected core | `d58b16bdee4024e5f40d066165c17fec1e7a5193c97d31a63fa871d0b80d9473` |
| Unchanged shared dependency | `785a1ab9f88d8ec6454029fe648b5d62213063f17d4933bdadbef336602c965a` |

From the repository root, choose fresh output directories:

```sh
.venv/bin/python results/codex/connected-star-integration-checks/run_checks.py results/codex/connected-star-integration-checks/root_focused
.venv/bin/python results/codex/connected-star-integration-checks/run_checks.py results/codex/connected-star-integration-checks/root_regression --regression
```

The runner refuses existing output directories, records its arguments/environment
and source hashes, and verifies those hashes after testing. The historical replay
requires the named local git object. `pytest` is provided by the project test
environment; the separate native-only environment remains the intended solver
environment for the later frozen experiment.

The integration still inherits the core's incomplete single-root search and the
risk that auxiliary work displaces more productive ordinary moves. Passing
these checks establishes neither lower final ACL nor roughly-MM-scale runtime.
Root's independent integration review and the separately frozen 039 all-input
comparison remain necessary before any promotion decision.
