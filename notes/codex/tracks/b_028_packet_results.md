# B028 paired query packet: proceed to the small constructor test

Both fixed cold packets completed all six queries on hyde02, with worker/outer/supervisor exit 0. Exact roots, ordered settled-distance/predecessor maps, route statistics and resulting attachments agree on **all six** inputs. No constructor ran. This establishes local-query equivalence on these states and supports testing whether the saved computation improves complete embeddings; it establishes no new success rate, ACL or generalization result.

The [saved-only analysis](../../../results/codex/track-b028-routing/analysis001/output/summary.json) passed on its first execution (0.656 s analysis; 0.857 s observed outer execution is not used as a candidate metric). It verified all 31 files against the quiescent remote inventory; archive digest `6847b7f50aa3033718098e7c4c61aef19b3054e46c7733bf40166827d9d53b85`. Full terminal records and GNU time output are in [retrieved001](../../../results/codex/track-b028-routing/retrieved001). Every remote action succeeded once; there were no observation timeouts, restarts, unattempted queries, late packets or prohibited imports. Prior preparation/compiler failures remain preserved as documented in the [implementation note](b_028_implementation.md).

| Measured cost | B027 | B028 |
|---|---:|---:|
| Cold packet wall, including import/JIT/adaptation | 15.777 s | 14.887 s |
| Cold packet CPU | 15.761 s | 14.820 s |
| Full process wall | 19.31 s | 18.56 s |
| Full process user + system CPU | 19.27 s | 18.48 s |
| Maximum process RSS | 80,920 KiB | 251,856 KiB |
| Routing plus adaptation on five queries after first compilation | 9.374 s | 2.454 s |

The full cold improvement is only **1.060 times** for packet wall, or **1.040 times** for complete process wall. The five later queries give a **3.819 times** reduction in routing plus adaptation. That secondary measurement excludes the entire first query rather than subtracting an estimated compiler cost from the headline. A descriptive check excluding the dense complete-100 query still gives **2.099 times**, from 2.423670 to 1.154461 s; the individual grid and honeycomb regressions remain below. All target/query packing, checked allocation, seeding, heap work and dictionary conversion remain included in each reported routing time.

| Saved-state query | Neighbors | B027 routing + adaptation | B028 routing + adaptation | Observation |
|---|---:|---:|---:|---|
| g0001 ER 80 | 15 | 1.32794 s | 7.95837 s | Cold startup regression |
| g0005 SBM 80 | 9 | 0.32512 s | 0.28345 s | Modest reduction |
| g0013 grid 128 | 4 | 0.00441 s | 0.21625 s | Regression |
| g0014 honeycomb 190 | 3 | 0.02630 s | 0.21725 s | Regression |
| g0016 partial complete 100 | 36 | 6.95015 s | 1.29991 s | Largest absolute reduction |
| g0019 branch control 80 | 18 | 2.06784 s | 0.43751 s | Reduction |

B028's first two compiling dispatches cost 5.867 s, including their kernel work. First typed allocation costs another 1.068 s and lazy import 0.633 s; all are charged. No new signatures compile on the other five queries. The largest measured noncompiling dispatch is 0.002962 s, within the retained 1 s constructor finalization reserve; this observation does not prove a universal wall-time bound. No arithmetic fallback occurs.

The packet creates a separate engine for each source, so each pays 0.186–0.224 s to pack Z12. A complete constructor packs its target once; this explains much of the grid/honeycomb query regressions but does **not** erase them. Per-query cost packing still costs about 0.011–0.013 s, which exceeds the original grid query's entire routing time. Conversion costs 0.528 s on the dense query, comparable to its 0.510 s compiled kernel cost. The observed acceleration therefore varies with query structure. Dense-query savings cannot establish an all-class improvement, and the forthcoming grid/control rows must expose any end-to-end regression.

Proceed to the separately frozen six-input screen in [the constructor protocol](b_028_constructor_screen.md). This is the direct test of the computational-starvation explanation: additional complete sweeps and price updates must lead to independently valid, competitive embeddings. More labels or faster local queries alone cannot justify another refinement. B027 remains rejected, A061 remains the retained algorithm, and all-class confirmation remains outstanding.
