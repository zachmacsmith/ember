# Induced-star core implementation

2026-09-08. The isolated core implements the previously frozen
[specification](induced_star_implementation_spec.md). It does not change contact,
native, or pilot scheduling. The implementation is a bounded local operation
using ordinary augmenting paths, with no external embedder or optimization
solver dependency. Matching/domain prior art and the limitations of the witness
remain as documented in the [independent review](induced_star_relocation_review.md).

## Frozen files and checks

| File | SHA-256 |
| --- | --- |
| `packages/ember-qc/src/ember_qc/algorithms/factored/induced_star_relocation.py` | `785a1ab9f88d8ec6454029fe648b5d62213063f17d4933bdadbef336602c965a` |
| `tests/algorithms/test_induced_star_relocation.py` | `ca23428c08bcebb77040c097ef73756f5f3cd5ded00b9392d7a63c72912fd0ba` |

The final run passes **139 tests**, comprising 85 new core tests and the existing
contact/singleton tests. It includes 48 independently generated tiny instances
whose restricted feasibility is compared with direct injective assignment,
every query stage interrupted by work and simulated deadline limits, every work
prefix of a complete small query, Hall-subset failure, augmenting paths,
heterogeneous labels, leaf conflicts, a block larger than four, owner transfers,
ordinary-move cache refresh, and incomplete maintenance. Original-graph checks
independently verify returned chains and exact Q/R deltas.

The exact guarded test command was:

```sh
.venv/bin/python - <<'PY'
import importlib.abc, sys
class NoMM(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'minorminer', 'busclique'}:
   raise ImportError('MM/busclique prohibited in induced-star tests')
sys.meta_path.insert(0, NoMM())
import pytest
raise SystemExit(pytest.main([
 'tests/algorithms/test_induced_star_relocation.py',
 'tests/algorithms/test_contact_repair.py',
 'tests/algorithms/test_singleton_relocation.py', '-q']))
PY
```

The dedicated native environment has no pytest installation, so tests used the
existing `.venv` interpreter under that import guard. Both environments use
Python 3.10.19, NetworkX 3.4.2 and dwave-networkx 0.8.19 for these checks. No
packages were installed. A separate guarded native smoke imports the checkout
explicitly through `packages/ember-qc/src`; the isolated environment does not
implicitly put this checkout on its import path.

## API and accounting contract for integration

`StarSearch(ctx, auxiliary_limit)` is constant work: it stores the existing
context and initializes counters, without scanning the source or creating a
source-rank map. Pass `max_expansions // 20` as the auxiliary limit.

`propose(embedding, center, visit_budget)` returns either a selected-only mapping
of singleton chains or `None`, together with move metadata. The core first runs
bounded structural selection. Only an eligible positive-excess block triggers
lazy ownership construction. Selection and physical query share the fixed
2,048-unit query ceiling. Setup is outside that ceiling but remains inside the
same active visit and auxiliary allowances.

Every budget charge advances the supplied active visit directly. Consequently,
the caller must not charge `move['expansions']` to that visit again. This returned
quantity is the new work performed by the call, excluding any preceding ordinary
work. It equals `query_work + setup_work`. Query `stage_work` sums exactly to
`query_work`. Per-call `query_wall + setup_wall` equals `wall`; setup time is also
available cumulatively. These are elapsed diagnostics, not benchmark estimates.

`refresh(old_embedding, accepted_embedding, changed_group, visit_budget)` returns
a boolean and is a no-op before a cache exists. For an existing cache it charges
all removal/insertion work to this same visit and auxiliary allowance. The
per-call fields `last_refresh_work`, `last_refresh_wall`, and
`last_refresh_reason` distinguish success, failure, and no-op; cumulative
`refresh_work` and `refresh_wall` include failed maintenance. Removing all old
owners before adding new ones permits ownership transfers within the group.
Incomplete or stale maintenance disables the cache for the rest of the polish
call, while preserving the already accepted embedding.

Aggregate `search.info['work']` equals `setup_work + query_work + refresh_work`.
`proposal_wall` includes setup and queries; `setup_wall` is its setup subset,
and `refresh_wall` is separate. Do not add the setup subset again when computing
total elapsed diagnostics.

The aggregate proposal fields deliberately use `certified_proposals`,
`proposed_qubits_saved`, and `proposed_contact_redundancy_gain`. They count
certified results returned to the scheduler, not actual commits. The caller
owns the final deadline check, mapping publication, actual accepted-move
counters, pass-change flag, and trajectory. Move metadata includes `accepted`
for a certified proposal, exact Q/R deltas, selected group, zero member growth,
zero equal-size moves, root/domain/matching counts, and completion reason.

The lower-level functions `select_star`, `query_star`, `build_owner_cache`, and
`refresh_owner_cache` accept context/budget objects for independent testing.
A budget implements `pop`, `check`, and `stopped_by`; optional `charge(stage)`
provides stage accounting. The core expects an already validated embedding of
simple, undirected, loopless graphs using fixed original adjacency. The enabled
scheduler must enforce those graph preconditions. Original mappings and chain
lists remain immutable for the lifetime of an owner cache.

## Completion and interruption

The first complete covering matching undergoes a fresh certificate and exact
old/new incident-coupler scoring before a replacement is returned. An interrupted
matching, scoring pass, or certificate returns no proposal. Query-local masks
are discarded after the query and cannot become stale across accepted moves.

Finalization permits a computation that used exactly its last allowed work
unit: completed setup, refresh, or certification is not partial merely because
no units remain. An expired deadline still prevents publication. Tests cover
this boundary explicitly. After a genuine interrupted operation, no completed
status is inferred from a partially populated dictionary.

## Physical witness and limits

On the previously fixed ideal Z12 witness, the core returns **8→5 qubits** within
the fixed policy: 692 query units and 13 setup units, totaling 705 visit units.
The first proposal uses a two-hop seed from frozen chain `x`, generates 16 root
walk occurrences (two duplicates), considers 13 eligible roots, and obtains one
covering matching. Old and new incident redundancy are both zero. Refreshing
the three changed chains costs 15 more units, for 720 total auxiliary/visit
units. These counters are diagnostics on one mathematical fixture.

The saved generic result remains independently valid at seven qubits. The
test validates that saved result without rerunning generic reconstruction or
selecting another witness. All 14,400 unilateral singleton substitutions on
the old Zephyr embedding still fail in the independent original-graph check.

The new core is not evidence of cumulative improvement or novelty. Larger
blocks, multi-qubit frozen boundaries, and scheduling effects deserve independent
review before integration; additional oracles are being prepared by the other
reviewer. The fixed query ceiling can truncate promising searches, and cache
work can reduce ordinary coverage. No full pipeline or benchmark run was
performed for this core implementation.
