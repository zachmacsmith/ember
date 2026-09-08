# 044: larger exchange allowance gives no additional reach

2026-09-08. **Reject increasing only the ownership work cap as the next improvement under this fixed policy.** The 10M-unit run returned exactly the same three exchange contractions as 043's 1.25M run; ordinary again returned 17. There were no ownership-only contractions. This meets the experiment's predeclared cheap falsifier.

| Paired credited outcome | 043 | 044 |
|---|---:|---:|
| Both | 3 | 3 |
| Ownership only | 0 | 0 |
| Ordinary only | 14 | 14 |
| Neither | 17 | 17 |

The minimal saved-result screen passes. All 68 rows remain present; all 20 credited outputs validate against the original source labels and original target; all 34 completed paired group vectors and hashes agree. The unchanged accepted validator was reused. No solver calls or trace replay were performed by the screen.

| Fresh 044 measurement | Ordinary | Ownership |
|---|---:|---:|
| Credited contractions | 17 | 3 |
| No contraction after group sequence | 12 | 0 |
| No groups | 2 | 2 |
| Work limit | 3 | 24 |
| Deadline | 0 | 5 |
| Common wall, total | 24.652 s | 136.012 s |
| Common wall, median | 0.479 s | 4.569 s |
| Process wall, total | 31.602 s | 149.222 s |
| Groups inspected | 8,715 | 560 |

Every recorded work total is known: ordinary used 4,093,011 routing expansions; ownership used 290,102,249 elementary units. These counters have different definitions. There were no invalid outputs or process failures. Common phase totals reconcile without adding nested method costs twice.

Compared descriptively with 043, exchange group inspections rose from 119 to 560, while credited input identities and reductions remained unchanged. The five new deadline rows were ember_3499, ember_32122, ember_37761, ember_33018, ember_34404. All other ownership nonempty negatives still reached the enlarged work cap. Ordinary's statuses, credited reductions and total routing work also match its previous observation. Timing comparison above uses only freshly paired 044 processes on hyde03; historical times are not pooled.

This is negative evidence for the simple allocation change, not a proof that the ownership neighborhood lacks useful moves. More work can stay concentrated in unproductive early groups, and the recorded limits still leave searches incomplete. Any further study requires a separately specified change to allocation or moves, rather than another cap increase under this identity. Independent proposals do not establish cumulative embedding gain, final ACL, novelty or an advantage over MM. Trace replay remains deferred because additional reach was absent.

[All 68 rows](../../../results/codex/044-results-review/screen001/rows.json), [paired records](../../../results/codex/044-results-review/screen001/pairs.json), [summary](../../../results/codex/044-results-review/screen001/summary.json), and [descriptive reach comparison](../../../results/codex/044-results-review/reach_comparison.json) preserve the details. All 34 inputs and 35 memberships remain included; no replacement or outcome-dependent selection occurred.

Archive SHA256 digest: `320a57ec8436433a8b685fba754967791bd73d757d1f58c8d0e730d08ae2536f` (496 files). Frozen screen: `c61c5eda45e64ad252fdfad721f8a8b8d33d49bb679c6ec57a1627e992559c2b`. Its exact changes from 043 were only the experiment heading, cap and manifest/transport bindings. One complete saved-result screen executed and passed.
