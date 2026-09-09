# C012 implementation and tiny gate

The [before-code frontier policy](c_012_frontier_policy.md) is implemented unchanged in [zephyr_frontier.py](../../../packages/ember-qc/src/ember_qc/algorithms/zephyr_frontier.py). All five declared check groups passed on their first execution. No panel, comparator, registry or remote call was made. This is an exploration gate for root review, not evidence of broader quality or runtime performance.

The standalone API is `frontier_embed(source, target, *, seed=0, timeout=60.0, deadline=None)`, proposed descriptor `zephyr-frontier`, config `{}`. It imports only the standard library. Supplied Zephyr coordinates and every actual coupler are checked; missing sites/couplers remain missing. A single seeded sweep schedules source births, one proper-suffix transaction after ordinary birth failure, and atomic frontier carrying. Private copies, local contact deltas, actual connectivity, live ports and final original-edge validation are charged to the common absolute deadline. Integer work counters never deny work. Source/target node ranks identify diagnostic IDs; returned maps use the original labels.

[The focused tests](../../../tests/test_codex_zephyr_frontier.py) ran once under the pinned native Python, with prohibited-import guards. The five full tiny constructions used ideal Z2, seed 0, and five seconds each. An independently loaded original-edge oracle checked every returned map; these are actual complete constructor calls, unlike the separate supplied-state transaction fixtures.

| Tiny source | Q | ACL | Measured wall / CPU, ms |
|---|---:|---:|---:|
| Path, 8 vertices | 8 | 1.000 | 4.90 / 4.90 |
| Binary tree, 7 vertices | 7 | 1.000 | 5.14 / 5.12 |
| Star, 22 vertices | 24 | 1.091 | 9.10 / 9.10 |
| Grid, 3×3 | 11 | 1.222 | 5.72 / 5.70 |
| Path of 3 plus 2 isolates | 5 | 1.000 | 4.95 / 4.95 |

Every call returned timely `SUCCESS` with no error. The degree-21 star exceeds Z2's maximum degree 20 and exercised carrying that added two sites. The grid required a three-site birth. Only the ACL-1 outputs are certified optimal by the vertex-count bound; Q24 and Q11 are not claimed optimal.

The actual-coupler joint fixture releases two owners' proper suffixes and restores a complete original minor at unchanged Q where ordinary birth fails. Its old-contact negative rolls back. Separate checks cover protected roots/singletons, malformed construction trees, a live owner whose membership survives but last free port expires, and conflicting carries that discard a successful private prefix. Deadline injection preserves the published state. Fatal exceptions and a late valid final map retain diagnostic evidence but receive no embedding credit. No central primitive failed.

The suite reports 0.111 seconds; its subprocess took 0.684 seconds. The recorded parent CPU measures only the invocation wrapper. Per-call wall/CPU and unsuccessful transaction receipts are retained in [attempt001](../../../results/codex/track-c-012-checks/attempt001/records/full_tiny_summary.json). Stderr retains the known dwave-networkx deprecation warning and successful unittest log. Event costs enclose stage costs and must not be added to them. The [freeze manifest](../../../results/codex/track-c-012-checks/freeze.json) binds source, policy, tests and every saved outcome.

Fixed roots, closed-owner immobility, a three-strip birth window and one monotone sweep remain experimental exclusions. Tiny reach does not establish adequate live-frontier capacity, useful dense placement, or good carry Q. The next authorized decision belongs to root's fixed complete panel; no local policy refinement or extra test suite is implied.
