# A057: two saved A053 failure stages

2026-09-08. Read-only diagnosis of exactly the two failed candidate records in
the accepted057 screen. No constructor/solver rerun, parameter change, new
partial-embedding audit or inspection of other outcomes.

| Input, seed | Last completed stage | Actual stopping point | Solver wall |
|---|---|---|---:|
| Hypercube `ember_4756`, 1 | Reduction: unchanged 256-vertex/1,024-edge core | Native conversion/completion fails its validity gate | 9.440s |
| Wheel `ember_2430`, 1 | One-site edgeless core; 109 lifting updates committed | Insertion of vertex66 blocks; its local repair allowance is exhausted | 4.256s |

**Hypercube.** No vertex was eliminated and no fill was created. The sole native
core call completes all1,000 geometric asks (`stopped_by='asks'`), with714
adoptions including319 worse adoptions. The returned layout records penalty5061;
conversion records32 misses. Completion makes12 extensions/22 bridges and
reports `deficit_edges=39`, with zero corner deficits. This is its saved repair
counter, not a new independent recount of the final missing-edge set. Native rejects
the constructed mapping as `CONSTRUCTION_FAILED`, before initial pruning,
contact refinement, final deletion or vacancy refinement. A053 reports
`core_failed`; it adopts no core mapping and attempts no lifting.

The nested failed-core evidence retains256 chain entries/Q1880, but this is an
uncredited failed construction, not a valid completed minor. The stopping fact
is geometry-to-physical conversion/completion reach on the chosen layout. It
is not a source-reduction failure, final cleanup failure or evidence that the
target lacks capacity. The fixed1,000-ask search limit is reached; the60-second
deadline is not. The outer187,552 setup/reduction scans exclude native's inner
search, so they must not be presented as its total work. The saved data do not
show whether another layout, completion neighborhood or additional asks would
succeed.

**Wheel.** Reduction leaves one edgeless core vertex and141 journal rows; native
is never called. At failed reverse index109, vertex66 requires placed owners
0,65,67 after privately releasing current fill edge65–67. The retained prefix
contains110/142 vertices/Q168. The transfer query checks all15 eligible donor
sites, rejects all15 for `new_contacts`, and uses5,011 scans; its64-site/50k
limits do not truncate this query. Ordinary insertion then returns no proposal.

The final blocked-repair record has pool `[25,71,67,65,0]` and identifies25/71
as sole-port competitors. Its first block, releasing25, is
`reconstruction_blocked` after798,089 scans. Its second, releasing71, stops
after201,765; selection used146. These total exactly the1M **per-query** cap.
No later blocks are inspected. Including an earlier successful repair, repair
work is1,047,911/5M; whole-wrapper work is6,299,945/20M. Neither global work nor
the60-second deadline binds. The wrapper calls this `insertion_blocked`, but
the more specific fact is **blocked ordinary/transfer reach followed by locally
work-censored repair**, not exhaustive neighborhood failure or infeasibility.
Required owner65 has one distinct free site in the saved failed-step demand
record; this and the competitor records suggest frontier contention, without
identifying every rejected ordinary branch's cause. The failed row's fill
release is not committed: the wrapper restores the prior requirement state.
Its `valid=False` is not an independent verdict on the retained partial minor.

**Implication for the proposed path stage.** It cannot act on either failure.
The proposal requires a complete original-valid A053 result and no pending
requirements. Hypercube never supplies one; wheel still has32 unplaced vertices
and active fill/pending guards. Applying the operator to either diagnostic map
would require a different feasibility/lifting mechanism and new certificates.
The current proposal is a quality hypothesis for successful outputs, not a
coverage remedy for these two failures.

Both raw result hashes match their accepted `analysis001/rows.json` entries:
hypercube task `9e185ca4af040f649cf8cff9`, SHA
`49b43e36b42bf3438a3400891f3e4f329d4ae17d47227813c9fc1d441bcd39fa`;
wheel task `29a0352e35b4cabf6fd8531e`, SHA
`1bbbaa8c7dc4bba0c29d64e14bc67b16ecc692d1667e22bd7708b285582c2851`.
Status/counter semantics were checked in the archived native, field-completion
and A053 wrapper source. Unsaved intermediate routes were not reconstructed.
