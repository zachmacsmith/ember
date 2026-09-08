# Connected-center core implementation record

2026-09-08. Work begins from the reviewed fixed implementation specification
`41e7b0bc31d7fa44a8c2f326d0a143315b6e5f178a5e7164cc530a32919f1e99`.
Only the new internal core, its focused tests and additive correctness artifacts
are in scope. Scheduler/native/pilot integration and corpus experiments are
excluded from this implementation step.

The core uses one fixed selected source block, one optimistic-score root,
demand-class assignment, at most four charged successor copies, and the specified
steering BFS. It reuses owner-cache and live shared-budget primitives from the
audited singleton module but calls no singleton proposal search. No extra
2,048-unit query limit is introduced. The final certificate must independently
recount actual qubits, member growth and incident-coupler redundancy.

Before code, the main risks remain invalid cached eligibility after interruption,
class-capacity paths that lose an occupied assignment, hidden large copies,
mistaking edge capacity for distinct sites, and returning a previously scored
state after a later work interruption. The implementation will keep speculative
states private, publish only completed static predicates, and preserve the known
seven-vertex root failure. Compact copies and direct fill make no runtime or
quality guarantee.

The core and tests are now frozen for independent review. The sole algebraic
simplification beyond the written pseudocode was agreed with root before freeze:
when every leaf demand is already assigned, new eligible-site counts cannot
change either leaf term in the prescribed successor ranking. The shortlist then
counts only newly covered frozen-center obligations. A focused check computes
the original numerical ranking and verifies equality while prohibiting those
unnecessary eligibility calls. This does not change the chosen policy.

## Interface and accounting

`ConnectedStarSearch(ctx, auxiliary_limit)` performs constant constructor work.
The caller supplies the original simple, undirected, loopless source and target
in the existing stable contact context, a validated immutable incumbent, and
`auxiliary_limit = global_work // 20`. This internal core relies on those graph
and incumbent preconditions; it does not duplicate the public final validator.

`propose(embedding, center, visit)` returns a selected-only replacement or `None`,
plus per-call diagnostics. `refresh(old, new, selected, visit)` is required after
each external commit once the lazy cache exists. It is a no-op before setup.
The exact incumbent object identity governs cache compatibility. Refresh removes
all old selected ownership before inserting new ownership; interruption discards
the cache and disables this search object, retaining the caller's accepted map.
No domain or speculative state persists across proposals.

The live supplied visit is charged immediately. Returned `expansions` must not
be added again. Aggregate `work` is exactly `setup_work + query_work + refresh_work`;
selection belongs to query work, and `query_stage_work` reconciles with it.
Per-call `setup_work`, `query_work`, `stage_work`, `wall`, `setup_wall`, and
`query_wall` are retained. Refresh exposes exact last-call work, wall, and reason,
as well as cumulative totals. No separate 2,048-unit ceiling applies.

`accepted` and aggregate `certified_proposals` count returned certificates, not
scheduler commits. `complete_proposals` counts zero-deficit states sent to full
certification; an interrupted certificate can increment it without returning a
proposal. `maximum_assignments` concerns individual fixed footprints, including
discarded trials; `covering_assignments` only counts full leaf demand, which can
still leave center obligations uncovered. `complete=True` with
`heuristic_no_proposal` means the fixed heuristic reached a specified stop, never
that the selected block is infeasible. `last_fixed_footprint` labels its operator
and can describe a discarded trial; `growth` contains only retained states.

Each copied footprint/boundary/coverage/assignment/class-count/scalar record is
charged. Diagnostics count actual copied records, completed copies and memo
entries; the memo can include discarded-trial or BFS sites. Eligibility entries
are published only after a complete static decision and a paid write. The
center may grow while selected Q falls; `member_growth` counts actual grown
logical chains. The independent incident-coupler recount permits negative R gain
only alongside strict Q reduction.

## Focused evidence and retained failures

The final guarded test run passed **43 tests**, including 1,536 small compressed
matching/deletion cases compared with exhaustive expanded-leaf assignments;
16 independently generated original-graph fixtures checked across their singleton
and two-site connected footprints; and exact final original-graph/Q/R checks.
The suite covers overlapping domains that require exchanging a filled class,
multiple demand, occupied-site deletion, Hall neighborhoods containing owned
sites, multi-qubit frozen chains, mixed labels, memo interruptions, charged copy
prefixes, every operation/deadline prefix of representative successful and
failed queries, augmentation-path prefixes, setup and refresh prefixes, final
deadline behavior, one-root failure, unfiltered site capacity, and positive
member growth. The separate steering fixture needs a non-improving intermediate
growth step. MM and busclique top-level imports were prohibited.

Logs remain under
[`results/codex/connected-star-core-checks`](../../results/codex/connected-star-core-checks/).
`focused-cr6qm_mv.log` preserves an initial overly broad import guard that also
blocked Ember's inert algorithm-registration module. The corrected guard blocks
the actual external packages. `focused-scdf1mm1.log` preserves three incorrect
test expectations: a purported success reused the known unrescuable root, and
an exhausted BFS was incorrectly expected to reconstruct a route. These were
test-fixture errors; no core policy changed to make them pass. The separately
constructed steering-success fixture exercises route reconstruction explicitly.
`focused-ysrm01j8.log` records 42 passing checks; final
`focused-aqbxg05u.log` records 43 passing checks in 1.10 seconds.

Four converter-free witness calls also passed in the isolated native environment
(Python 3.10.19, NetworkX 3.4.2, dwave-networkx 0.8.19, macOS arm64). Source,
target, incumbent, returned chains, exact quality, configuration, hashes, stage
work, and diagnostics are frozen separately for each case in
[`native-witness-001/report.json`](../../results/codex/connected-star-core-checks/native-witness-001/report.json).
The report verifies that source hashes stayed unchanged during execution.

| Fixed witness | Q before → after | Center size | Setup / query work | Copies / records | Memo entries | Outcome |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Ideal Z12, source K1,22 | 25 → 24 | 3 → 2 | 48 / 1,760 | 1 / 43 | 105 | Certified; R 2 → 1 |
| Center grows, leaves shorten | 7 → 6 | 1 → 2 | 12 / 196 | 1 / 8 | 6 | Certified; member growth 1 |
| Seven-vertex bad root | 7 → no proposal | — | 12 / 160 | 2 / 14 | 6 | Expected heuristic failure |
| Same root, larger strict allowance | 8 → 7 | 3 → 3 | 13 / 346 | 4 / 30 | 10 | One BFS steering step |

The actual ideal-Z12 witness is constructed directly: the first maximum-degree
physical root, first adjacent mate exposing at least 22 distinct sites, first
adjacent extra preserving that boundary capacity, then the first 22 boundary
sites. These three connected sites and singleton leaves form the incumbent.
The degree-22 source center exceeds target maximum degree 20; the returned
two-qubit center and 22 singleton leaves are independently valid. This is one
mechanism witness, not a search over competing embedding outputs. Its 1,808 work
units and roughly 0.004-second core diagnostic do not establish corpus coverage
or benchmark runtime. The bad-root case saves an explicit valid lower-Q embedding
at another root while the prescribed core returns no proposal.

## Frozen identities and reproduction

| Artifact | SHA256 |
| --- | --- |
| `connected_star_relocation.py` | `d58b16bdee4024e5f40d066165c17fec1e7a5193c97d31a63fa871d0b80d9473` |
| `test_connected_star_relocation.py` | `67763d5a9822c5f6d3bcd61cebae35a647602a7c0ae32bb2f65d42a5bb6f28a8` |
| `witness_check.py` | `0638586bc81b05210ba3c9ee31cfb6456dcc1ea6dcbc25247864f1c5b7194058` |
| `native-witness-001/report.json` | `31dbd8acf675b4caf1863008ffceed1addae7b6fa53f32e736db35ef3da317c5` |

Run the focused checks from the repository root:

```bash
.venv/bin/python - <<'PY'
import importlib.abc, sys, pytest
class NoMM(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'minorminer', '_minorminer', 'busclique'}:
            raise AssertionError('forbidden dependency: ' + fullname)
sys.meta_path.insert(0, NoMM())
raise SystemExit(pytest.main(['-q', 'tests/algorithms/test_connected_star_relocation.py']))
PY
```

Run the fixed witnesses with a **new** output path; existing paths and finalized
observations are refused:

```bash
.venv/codex-native/bin/python results/codex/connected-star-core-checks/witness_check.py \
  --output results/codex/connected-star-core-checks/native-witness-002
```

Independent code review and any later scheduler integration remain separate
gates. One root, one greedy leaf subset, four successors and one bounded BFS
remain heuristic restrictions. Class compression is conventional exact matching;
known-only memoization and compact copies do not prove speed. Sort/allocation
time is included in wall time and deadlines are cooperative. These checks make
no claim of novelty or superiority over MM, and no corpus benchmark or production
algorithm default changed in this core-only task.
