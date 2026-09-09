# A064 broader development result

2026-09-09. **The frozen transfer criterion passes; the MM objective does not.**
A064 and retained A061 each succeed on all22 inputs; MM succeeds on21 and times
out on K100. A064 reduces Q on21 inputs relative to A061 and ties on K100, with
no lost success or Q regression. The20 primary structures contain19 improvements
and one tie; the two relabelings each improve separately. The unchanged policy
therefore merits replicated breadth evaluation. It is not promoted: A061 remains
the single retained policy with the existing full-class record.

These are all exposed Transfer001 development inputs, seed0, ideal Z12,
60-second solver allocations, fresh paired A064/A061/MM calls on hyde06.
Seven inputs overlap the smaller A064 screen. The separate ER100/BA100 cohort is
not pooled here. The two relabelings are nested observations, not new structures.

| Generated family | Mean ACL A064 / A061 / MM | A064 vs MM wins / losses |
|---|---:|---:|
| random_er | 5.5719 / 5.6594 / 6.8125 | 1 / 1 |
| barabasi_albert | 3.2563 / 3.3281 / 3.4719 | 1 / 1 |
| regular | 4.3844 / 4.5656 / 4.9250 | 2 / 0 |
| watts_strogatz | 2.4406 / 2.5063 / 2.0000 | 0 / 2 |
| sbm | 3.6531 / 3.7500 / 3.4219 | 0 / 2 |
| random_planar | 1.6687 / 1.6812 / 1.6000 | 0 / 2 |

Each row contains two independent structures, sizes80/160, with all three
methods successful. These descriptive means do not estimate family populations.
ER80 and BA160 still lose despite favorable family means. Across the20 primary
structures, A064 wins4 and loses15 on19 common successes; the nested relabelings
add one win and one loss. The K100 timeout supplies no finite MM ACL comparison.
Grid Q162 versus MM133, honeycomb215/202 and wheel152/144 remain losses. All four
hidden-witness controls remain worse than MM, including the singleton80 control
at Q199 against MM181 and its hidden optimum80. No witness entered the candidate.

The [complete per-input table](../../../results/codex/a064-broader-transfer/report001/tables.md)
preserves every Q, ACL, within-chain variance, solver wall and process wall,
including failures and nested relabelings. Across-seed ACL variance remains
unmeasured. Within-chain variance increases are reported separately and are not
automatic vetoes. The existing [retained-policy class table](../mm_gap_retained_a061.md)
continues to expose all prior deficits, earlier failures and unmeasured Sudoku;
this development panel does not replace it.

The mechanism transfers beyond the small cohort: every one of the12 generated
inputs improves over A061, covering all six families. The20 primary structures
save227 sites; counting the nested observations separately adds11. There are170
strict commits across22 calls. All22 stages reach their deadline with no current
epoch fully closed;17 visit every source owner. The added stage consumes1074.385s,
of which875.655s (81.50%) is root ranking and180.153s reconstruction. This supports
computational cost as a concrete obstacle, without proving that more identical
search will close the remaining quality gaps. Sparse planar80/grid/relabel-grid
also spend substantial time reconstructing unsuccessful trees; ranking is not
the sole bottleneck on every input.

Total solver wall/CPU/process wall are1298.513/1298.323/1342.991s for A064,
207.322/207.254/247.717s for A061 and155.329/155.301/167.241s for MM. All66 calls
have known time fields. A064/MM solver ratios on common successes range2.03–156.02;
no roughly-MM-order runtime claim follows from the aggregate ratio. Historical
worker ru_maxrss remains raw evidence with the documented inherited-peak scope
problem, not an algorithm-specific memory comparison.

The run completed under detached supervision,66/66 terminal, supervisor0,
quiescent before retrieval. Fetch verified470 files, archive digest
`c9d3a672023954d24da85820f686390e61f64a8b61082a156758a75bdcefd384`.
The unchanged original-minor audit with its reviewed input-directory adapter
passed first execution (1.530s process), followed by the reused passive receipt
reader (0.243s). Root verified all33 receipt-reader bindings and reviewed the
per-input outcomes. Archive, exact sources, hashes and output bindings are under
`results/codex/a064-broader-transfer`; no constructor replay or MM-map input was
needed for analysis.

**Decision.** Preserve A064 as a promising general mechanism, keep A061 retained,
and test whether exact acceleration of its dominant root-distance calculation
makes the existing useful neighborhood computationally accessible. The next
experiment must charge cold compilation and conversion, preserve root ordering,
and reach a small complete-constructor screen promptly if its query test passes.
That is a distinct cost hypothesis, not permission for indefinite local repairs.
Replicated breadth, fresh structures and untouched confirmation remain required.
