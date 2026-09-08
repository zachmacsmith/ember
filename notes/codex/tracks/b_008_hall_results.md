# B008 Hall diagnostic results

Hidden competition for singleton sites is present, well before some promotion cascades. All six bounded B006/B007 replays reach 40 committed placements with exactly the saved construction order, updates and promotion prefix. The read-only hook leaves the frozen source AST unchanged when removed, and all deadlines remain nonbinding. Every observed partial minor validates independently.

| Prefix | Completed domain states | Hall deficits | First deficit after commits | Matched / variables | Witness sites / variables |
|---|---:|---:|---:|---:|---:|
| B006 ER | 42 | 20 | 2 | 51 / 78 | 46 / 73 |
| B007 ER | 48 | 35 | 2 | 51 / 78 | 46 / 73 |
| B006 Watts–Strogatz | 43 | 3 | 21 | 58 / 59 | 1 / 2 |
| B007 Watts–Strogatz | 43 | 9 | 9 | 70 / 71 | 1 / 2 |
| B006 king | 42 | 17 | 2 | 60 / 62 | 8 / 10 |
| B007 king | 44 | 22 | 2 | 60 / 62 | 8 / 10 |

ER's second accepted singleton leaves 78 nonempty domains, but 73 variables collectively have only 46 eligible sites. Thus at least 27 of those singleton assumptions must change unless an earlier placement changes. King similarly has ten variables competing for eight sites after its second placement. Both witnesses precede any promotion. Watts–Strogatz's first recorded collisions involve two variables sharing one site; these occur after earlier promotions. State counts include successive promotions on an unchanged physical incumbent and are not independent instances.

All 262 matching checks finish; 106 have certified deficits and none hit the five-million-scan or five-second limits. Matching uses 380,422 scans and 0.206 seconds total, with a maximum individual call of 0.0133 seconds. These are local offline diagnostic costs, not an integrated constructor timing estimate. Prefix calls consume 10.04 seconds total, including approximately 0.020 seconds of capture; validation, matching and serialization run afterward. Raw observations retain each cost separately.

The matching implementation passes four tiny exhaustive-assignment fixtures and two interruption checks. A second agent independently verified ER's actual saved witness: its domain union has exactly 46 sites, the matching contains 51 eligible distinct assignments, and the 27-site deficiency proves no matching larger than 51 exists. No constructor was invoked for that independent check.

This supports a bounded injectivity check before accepting a singleton proposal, rather than assuming nonempty propagated domains establish feasible capacity. It does **not** show that rejecting such a proposal finds a better alternative or reduces final ACL. Promoting chains can relax the singleton model, and a covering matching still ignores simultaneous logical-edge realizability. The next cheap question is whether the unchanged small proposal set contains a covering alternative at these early failures. No candidate change or additional screen is implemented here; increasing existing caps is unsupported.

Details: [pre-code hypothesis and limits](b_hall_diagnostic.md), [all prefix summaries and identities](../../../results/codex/track-b008-hall/attempt001/summary.json), [costs and first witnesses](../../../results/codex/track-b008-hall/attempt001/cost_summary.json). Compressed per-prefix files alongside the summaries contain every domain bitset, physical-site map, partial embedding and certificate. Reproduce with `.venv/codex-native/bin/python -B results/codex/track-b008-hall/diagnostic.py run NEW_DIRECTORY`; this executes only the six predeclared prefixes, never MM.
