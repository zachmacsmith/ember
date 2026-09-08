# B009 development results

B009's stronger feasibility check is cheap on this panel, but its fixed construction policy is not a general improvement. Six of nine candidate calls complete, versus seven for the explicit B007 ancestor. ER regresses from a valid 310-qubit embedding to a blocked partial minor. Watts–Strogatz improves by 60 qubits, regular worsens by ten, and king worsens by sixteen; the other completed inputs tie. Fresh MM comparisons retain only the two optimal grid/honeycomb wins and four losses.

| Input | Q, B007 → B009 | Fresh MM Q | Matching units | B009 seconds | B009/MM time |
|---|---:|---:|---:|---:|---:|
| complete 40 | failed → failed | 194 | 0 | 21.19 | — |
| complete 100 | failed → failed | late | 0 | 32.03 | — |
| bipartite 30+30 | 330 → 330 | 180 | 0 | 23.41 | 6.42× |
| ER 80 | 310 → failed | 211 | 99,944 | 12.03 | — |
| regular 80 | 100 → 110 | 90 | 23,945 | 7.39 | 13.36× |
| Watts–Strogatz 80 | 193 → 133 | 94 | 50,907 | 13.50 | 18.76× |
| grid 64 | 64 → 64 | 70 | 10,360 | 4.95 | 7.16× |
| honeycomb 70 | 70 → 70 | 71 | 13,597 | 6.40 | 6.11× |
| king 64 | 112 → 128 | 90 | 52,501 | 13.28 | 5.76× |

All complete outputs and retained partial minors validate on original graphs. The detached run finished all 18 calls before retrieval; all 175 archived file hashes pass. The late MM K100 result is valid at 1,121 qubits but takes 63.34 seconds and receives no timely credit. K40 still blocks after 32 placements, and K100 reaches its 20-million-unit limit after 35. ER blocks after 63 placements at 6.55 million units, well below the global limit.

All 846 matching queries complete, consuming 251,254 units and 0.795 seconds combined. No query, total matching, growth or propagation limit causes an unknown result. Matching, growth and propagation accounting reconcile with their overlapping global counts. Thus the negative outcomes cannot be rescued by increasing matching allowances. Regular and Watts–Strogatz also retain substantial runtime gaps against their contemporary MM calls. Load remains approximately 33–34 on 32 logical CPUs; timing comparisons are exploratory observations, not portable speed claims.

The early ER collision is actually avoided: its second-placement lookahead rejects two 78-variable matchings covering only 51 variables, then finds a covering 78/78 alternative. Nevertheless, the later construction blocks. King sees four consecutive 62-variable/60-covered lookahead failures before promoting the vertex. Matching detects genuine capacity conflicts and sometimes finds a locally better alternative, but does not ensure a good continuation. Ordinary promoted-chain insertion can still proceed when optional single-chain growth cannot restore all future singleton assumptions.

Do not promote B009. Preserve matching as an inexpensive, necessary feasibility signal and preserve the failed policy response as a lesson. The next substantive issue is how to revise already committed placement when a conflict cannot be resolved by this one-chain neighborhood; this screen does not authorize another larger-cap run. B007 was itself rejected, so its Watts–Strogatz regression being partly reversed is insufficient evidence for adoption.

Details: [pre-code policy and critique](b_matching_feasibility.md), [all pairs](../../../results/codex/track-b009-analysis/analysis001/pairs.csv), [raw records](../../../results/codex/track-b009-analysis/analysis001/rows.json), [per-input matching/growth accounting](../../../results/codex/track-b009-analysis/analysis001/matching_summary.json), [freeze](../../../results/codex/track-b009-checks/freeze.json). Reproduction uses `track-b009-analysis/analyze.py ARCHIVE NEW_DIRECTORY`, then `summarize_matching.py NEW_DIRECTORY`; neither calls a solver.
