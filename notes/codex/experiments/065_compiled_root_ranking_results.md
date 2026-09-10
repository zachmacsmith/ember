# A065 paired root-ranking result

2026-09-09. **Exact fixed-query ordering passes; proceed promptly to the small
complete-constructor screen.** This resolves a computational-cost question and
establishes no new embedding success rate, ACL result or class-level win.

All six full ordered root lists match the pinned A064 method, as do complete
input-state fingerprints and BFS pop/arc/distance-initialization counts. The
lists contain 4545, 4186, 4678, 4637, 4082 and 4604 roots respectively. Both cold
packets, outer workers and detached supervisor exit0. All 12 queries complete;
there are no deadlines, invalid queries, prohibited imports or unattempted rows.

| Full measured cost | A064 | A065 |
|---|---:|---:|
| Cold packet wall | 8.513716s | 3.176140s |
| Cold packet CPU | 8.511228s | 2.911720s |
| Complete timed command wall | 8.615445s | 3.483262s |
| Complete command user + system CPU | 8.612070s | 3.214337s |

Cold packet speedup is 2.681 times; complete command speedup is 2.473 times.
The packet clock includes input verification, imports, queries and per-query
output. Terminal summary writing is retained in the complete command clock.
The small outer observer's own startup/output are excluded; no memory comparison
is inferred. Both arms run separately on hyde06 with the same pinned native
environment. This single pair does not estimate timing variability.

| Saved-state query | Neighbors | A064 ranking | A065 ranking | Outcome |
|---|---:|---:|---:|---|
| ER80 | 3 | 0.129473s | 1.170993s | Cold-start regression |
| BA160 | 37 | 1.419993s | 0.036674s | Lower cost |
| planar80 | 10 | 0.425830s | 0.021044s | Lower cost |
| grid128 | 3 | 0.130694s | 0.029197s | Lower cost |
| K100 | 99 | 3.829185s | 0.081845s | Lower cost |
| singleton control80 | 20 | 0.867381s | 0.032442s | Lower cost |

Every ranking time includes that context's target packing, query packing,
allocation, kernel, root conversion/sort and instrumentation. The packet creates
six contexts and charges six CSR packs (0.0119–0.0200s each); a complete constructor
packs its target once. Each private target CSR occupies 772232 array bytes;
query arrays occupy 197208–209752 bytes. These are array payloads, not process RSS.

The sole compiling dispatch costs 0.766747s, including its actual BFS work;
first lazy import costs another 0.373827s. Both remain charged. No other query
compiles another signature. The maximum measured noncompiling dispatch is
0.00014457s; this observation is not a universal interrupt-latency guarantee.
The five later rankings total 6.673083s for A064 and 0.201203s for A065 (33.166
 times); excluding K100 still gives 23.827 times. These secondary figures exclude
the entire first query, without subtracting estimated compilation from the cold
headline. Target/query conversion remains included, preserving the sparse cases.

The first-query ranking penalty is 1.041520s. At the separately observed adapted
savings, repayment would take approximately 1/3/11/1/2 queries of the respective
BA/planar/grid/K100/control type. The previous A064 run completed 126/69/101/12/92
rankings on those inputs. This supports feasibility of amortization, not a
prediction of later query costs: the packet samples one initial longest-chain
owner per graph and pays one compilation across six contexts. Every real cold
constructor must pay its own compilation. ER80 lacks a separate postcompile
query observation; its first-query regression remains explicit.

**Decision.** The measured bottleneck can be made substantially cheaper without
changing any root eligibility or ordering on these states. Test A065/A064/MM
complete constructors next on the six diagnostic structures, fresh WS100/SBM100
and nested grid relabeling, with root-owned frozen inputs and paired timing.
A064's fixed witnesses, greedy shared paths, strict-Q acceptance and sparse
reconstruction cost remain unresolved. If greatly increased search produces no
complete-output Q gain, stop acceleration-only refinements. A061 remains retained;
no confirmation input or paper claim is used here.

Saved-only analysis passed first execution (0.0143s analysis; 0.0436s recorded
outer execution). It verified all 48 files against the quiescent inventory,
archive digest `ecbe94094430a00f387029edd52b0a90fe0437fa7149be2b0f32437d696f96eb`.
The [full report](../../../results/codex/a065-root-ranking/analysis001/output/summary.json)
retains every raw status, time, root-order result and binding. The reader was
prepared before outcomes were read. Source/check/extraction and preflight failures
are documented in the [implementation note](065_compiled_root_ranking_implementation.md).
