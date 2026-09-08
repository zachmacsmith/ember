# Shared pilot adapters for the two exploratory constructors

2026-09-08. Integration owner: literature agent. Demand construction and
multilevel region construction remain separate algorithms, each compared with
MM in its own track and on its assigned host. No constructor calls native,
another constructor, MM or busclique; no result is selected between algorithms.

Before implementation, the agreed APIs are:

| Pilot method | Standalone frozen module | Function |
|---|---|---|
| `demand-tree` | `algorithms/factored/demand_construction.py` | `demand_embed` |
| `multilevel-regions` | `algorithms/multilevel_regions.py` | `multilevel_embed` |

Both functions accept `(source, target, *, seed, timeout, deadline)` and return
the existing pilot response dictionary: `embedding`, `status`, `diag`, optional
`error` and `partial_embedding`. Failed output uses an empty embedding mapping.
Initial method configurations are empty. Both modules are independently written
standalone Python; they use the supplied graph interface and standard library.

The current pilot has no generic candidate entrypoint: every non-MM method
imports `native_embed`. Add one small explicit constructor registry and exact
byte-hash loader under the existing frozen source tree. The caller supplies the
absolute deadline `measured_start + timeout`; graph copies occur inside that
measured interval. Each implementation must respect the earlier of this deadline
and any internal timeout. Imports remain outside solver wall, while the existing
fresh-process measurement includes them. Original source and target objects
remain available to the unchanged independent validator after the call.

Keep existing native configurations and behavior intact. Constructor method
lookup returns its declared empty configuration without changing the historical
native `CONFIGS` dictionary. The existing snapshot includes both new modules;
no cluster transport, controller, result schema or analyzer rewrite is needed.
The worker's prohibited-import check remains active before constructor loading.
MM runs only through its existing comparator branch and separate environment.

Targeted checks will cover exact source loading, unknown entrypoints, corrupted
bytes, valid/invalid/late output, shared absolute deadline, original-input
validation after a deliberately mutating constructor, and preserved old method
configurations. Tiny synthetic adapter modules suffice to test the harness;
each track owner separately checks its algorithm and freezes it before launch.
The adapters do not authorize a run or specify new evaluation inputs.

Self-critique: direct loading verifies the requested file but is not a sandbox
for arbitrary imports; the standalone-module contract and existing import guard
remain necessary. A cooperative deadline cannot prevent every overrun; the
existing worker/controller backstop and final timeout classification remain.
The original validator's cost is outside solver wall for both candidates and
MM, while process wall includes it. These adapters improve experiment speed,
not statistical coverage: same-host paired timings and failure coverage must
remain visible, and a small development screen cannot establish broad quality.

## Implemented and checked

The shared pilot now has 51 added lines and three changed configuration lookups.
`CONSTRUCTORS` specifies exactly the two paths/functions above; `method_config`
retains each historical native/MM config and returns a fresh empty constructor
config. The worker loads hash-verified bytes directly, registers the standalone
module for dataclass support, and passes the existing timed graph copies with
the common absolute deadline. No cluster, analyzer, validator or algorithm
source was changed by this integration.

Eight targeted adapter checks pass. They include both constructor signatures,
source-hash rejection, original-edge validation after deliberately changing the
private graph copies, valid-but-late diagnostic quality, and a constructor that
catches a prohibited import attempt: the worker still records
`DEPENDENCY_VIOLATION`. The 36 existing supplement checks also pass; no historical
registry assertion needed weakening. `git diff --check` passes.

All attempts are preserved under
`results/codex/constructor-harness-checks`. Attempt001 stopped before collection
because the isolated candidate environment intentionally lacks pytest.
Attempt002 used the repository pytest environment to run seven adapter checks
and the 36 supplement checks, with each adapter worker still in isolated native
Python. Attempt003 added the explicit forbidden-import case and passed all
eight adapter checks. There were no algorithm or corpus calls in these tests.

The track owners can use the unchanged `pilot.py init` with `--methods
mm,demand-tree` or `--methods mm,multilevel-regions`, their predeclared graph list,
the existing readiness selection, and their own host's native/MM interpreter
paths. Snapshot initialization must wait for that track's constructor file to
be stable. Existing `cluster.py stage/start/status/retrieve` and
`analyze_pilot.py` remain method-neutral; each host runs its own comparator for
paired timing. No cross-host timing pooling is justified.

Focused rerun:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -I -B -m pytest -p pytest_timeout -q tests/test_codex_constructor_pilot.py
```

## Track B002 adapter

The agreed B002 variant adds `frontier-tree` →
`algorithms/factored/frontier_construction.py:frontier_embed`, with the same
`(source, target, *, seed, timeout, deadline)` API and an empty configuration.
This is a new explicit entrypoint within Track B; it does not call or select
between the previous constructor and the new one. Only two registry lines and
one additional parameterized worker case are needed. Existing run snapshots,
method configs, dispatch, validator and process handling remain unchanged.
All nine targeted adapter cases pass in `attempt004-frontier`; no actual B002
constructor or corpus call was needed to check this entrypoint wiring.

## Track C002 adapter

`multilevel-regions-v2` selects
`algorithms/multilevel_regions_v2.py:multilevel_embed`, with the same API and
empty configuration. The first V2 module used a package-relative helper import,
which was incompatible with the standalone pilot loader. The author corrected
it to load exact hash-checked sibling V1 bytes and use only structural utility
functions; the V1 constructor is never called. A separate isolated import-only
check confirms the real V2 loads through the pilot without `ember_qc` package
imports or prohibited dependency attempts. No candidate was invoked.

All ten targeted adapter tests pass in `attempt005-multilevel-v2`. The actual
import-only evidence is under `multilevel-v2-import`. This adds two registry
lines and one parameterized case; old methods and frozen screens are intact.

## Track B003 adapter

`frontier-tree-bounded` selects
`algorithms/factored/frontier_bounded_construction.py:frontier_embed` with the
unchanged deadline API and empty configuration. The dedicated fresh-worker
adapter case passes in `attempt006-frontier-bounded`. Only that newly added
case was run: it checks the two-line registry addition without repeating the
already passing shared harness checks or invoking the actual constructor.

## Track C003 and B004 adapters

After the immutable 046 freeze, `quotient-reconfiguration` adds the standalone
`algorithms/quotient_reconfiguration.py:quotient_embed` entrypoint. C003 froze
pilot `1b281a9a` before the next registration. `frontier-tree-reinsert` then adds
`algorithms/factored/frontier_reinsertion_construction.py:frontier_embed`; its
pilot hash is `375b686eab25298b8bfabbf41e44cc4c37d056541938c743c58023d1c6a4e6b3`.
Both retain the same absolute-deadline API and empty configuration. Each added
only two registry lines and one parameterized worker case; each affected case
passed independently in 0.30 seconds. Evidence is in
`constructor-harness-checks/quotient_manifest.json` and
`frontier_reinsert_manifest.json`. These were synthetic adapter checks, with
the existing isolated worker and validator; no real constructor or corpus was
called by this integration task. Existing 046 and C003 snapshots are unchanged.
