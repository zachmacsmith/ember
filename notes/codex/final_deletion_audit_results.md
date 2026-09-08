# Individual deletion opportunities in frozen 039 controls

All 34 final control embeddings passed independent validation against their
original source graphs and target. Of their 15,059 occupied sites, **43 are
individually safely removable**, spread across 43 chains on 13 inputs. The
other **21 inputs have no individually safe deletion**. This establishes an
observable cleanup opportunity after the historical refinement path; it does
not establish a deployable speed benefit, composed 43-qubit reduction or a
better embedding algorithm.

The [design and critique](final_deletion_audit_design.md) were saved before
deletion outcomes. The diagnostic uses only the standard library, never calls
a solver, converter or production pruning function, and leaves every original
mapping and chain list unchanged. Family names below are evaluator labels;
the same test was applied to every site on every input.

| Frozen input | Evaluator membership | Original control Q | Individually removable sites / affected chains |
| --- | --- | ---: | ---: |
| ember_14334 | regular | 1304 | 1 / 1 |
| ember_4905 | binary_tree | 138 | 0 / 0 |
| ember_31879 | triangular_lattice | 287 | 1 / 1 |
| ember_1363 | bipartite | 566 | 0 / 0 |
| ember_3499 | circulant | 198 | 0 / 0 |
| ember_1041 | complete | 1180 | 0 / 0 |
| ember_2030 | path | 141 | 0 / 0 |
| ember_5411 | kneser | 420 | 5 / 5 |
| ember_6450 | random_er | 892 | 5 / 5 |
| ember_37603 | hardware_native | 250 | 0 / 0 |
| ember_37302 | spin_glass | 1835 | 0 / 0 |
| ember_3060 | turan | 460 | 0 / 0 |
| ember_32367 | honeycomb | 273 | 0 / 0 |
| ember_34404 | planted_solution | 145 | 0 / 0 |
| ember_33219 | cubic_lattice | 224 | 2 / 2 |
| ember_31357 | lfr_benchmark | 189 | 0 / 0 |
| ember_32616 | frustrated_square; king_graph | 243 | 1 / 1 |
| ember_2429 | wheel | 200 | 1 / 1 |
| ember_1584 | grid | 173 | 0 / 0 |
| ember_22972 | watts_strogatz | 1712 | 13 / 13 |
| ember_32122 | kagome | 166 | 0 / 0 |
| ember_33587 | weak_strong_cluster | 427 | 0 / 0 |
| ember_1829 | cycle | 126 | 0 / 0 |
| ember_30736 | sbm | 616 | 3 / 3 |
| ember_4083 | generalized_petersen | 212 | 2 / 2 |
| ember_5242 | johnson | 846 | 4 / 4 |
| ember_31536 | random_planar | 300 | 0 / 0 |
| ember_4755 | hypercube | 457 | 4 / 4 |
| ember_5058 | tree | 134 | 0 / 0 |
| ember_33402 | bcc_lattice | 152 | 0 / 0 |
| ember_2229 | star | 137 | 0 / 0 |
| ember_33018 | shastry_sutherland | 162 | 0 / 0 |
| ember_37761 | named_special | 50 | 0 / 0 |
| ember_10662 | barabasi_albert | 444 | 1 / 1 |

There are 34 distinct inputs and 35 memberships; the shared
frustrated-square/King's-graph input is counted once in totals. Every site has
a saved individual record identifying its original logical vertex, physical
qubit, chain size, nonemptiness/connectivity result and any sole-contact
neighbors. All 43 positive certificates were cross-checked with a separate
complete original-graph validator omitting only that one site. Their original
chain sizes range from 2 to 12.

Original validity checks cover exact source keys, nonempty connected chains,
target membership, duplicate/disjoint ownership and every original edge.
The main test obtains both endpoint-support sets through a complete scan of
the original target edges, then traverses each nonempty shortened chain and
checks every incident logical contact. Reported work includes 1,559,376 target
edges scanned, 675,665 incident-support tests, 52,417 chain traversal vertices
and 1,037,909 adjacency entries in those traversals, plus 43 complete deletion
validations. Counters do not include every Python/container operation or the
internal work of those complete validations.

The saved enumeration phase, including per-input identity reads and record
writing, took 1.136 seconds locally, below its prespecified 180-second cap.
Initial archive/evaluator hashing and synthetic checks precede that timer.
This was a shared, unreserved host, not a native deadline measurement or an
integrated cleanup benchmark. No timing from this diagnostic is pooled with
039's remote solver timings.

Provenance binds all 433 retrieved files, 103 evaluator files, 48 source files,
34 exact control task/result records and their worker records. The source
snapshot is `63a0aed1a880cbf008aa68ae7201aed7a4da635dea9362e5d296b1d13a91a473`;
retrieval digest is
`9ad6f638f60242f51f79eb4002696c7222032bb76f8ff9406198a5ec40de4ed6`.
Inverse label maps reproduce each original source topology, including inputs
whose original node iteration differs from canonical order. Each raw result's
file and serialized embedding hashes match the accepted 039 independent audit.
The selected method is always `native-search-joint1-contacts-spectral`, seed 0,
with the original 60-second allowance and fixed configuration.

The first launch stopped before enumeration because the prior audit hash map
contains an additional `retrieval.json` entry. All 433 shared entries matched;
the revised check additionally binds that entry to the actual retrieval file.
The failed preflight and successful synthetic checks are retained in
`attempt001`. The completed enumeration is in
[`attempt002`](../../results/codex/final-deletion-audit/attempt002/summary.json),
with [all-input CSV](../../results/codex/final-deletion-audit/attempt002/per_input.csv),
per-input certificates and a detailed provenance record. No failed solver run
or unfavorable graph was dropped.

Independent review of the [conditional closure design](deletion_closure_design.md):
the monotonicity argument is sound for fixed graphs and deletion-only updates.
For unchanged C_u, nonemptiness/connectivity of C_u minus q cannot change;
shrinking another chain only removes its possible contacts. Hence an unsafe
deletion cannot become safe solely through deletions elsewhere. Closing chains
one at a time therefore needs no later revisits to closed chains, but may
choose a different surviving embedding than globally interleaved sweeps.

Keeping the legacy sorted chain/site order while skipping chains unchanged
since their own last completed sweep preserves the accepted deletion sequence
under nonbinding deadlines: every skipped attempt was unsafe at that earlier
sweep and remains unsafe. Induction over retained attempts gives the same
current embedding at each possible acceptance. A chain changed by its own
deletion must remain eligible for another sweep, since an earlier articulation
can become removable. Every candidate still needs current contact validation:
an external deletion can make a formerly safe site unsafe. Binding deadlines
can change which valid prefix is reached. This is a mathematical assessment;
it is not a replay test of an optimized implementation.

Distinct affected chains do not make the 43 deletions composable: two physical
couplers witnessing the same logical edge may each rely on the other chain's
prospectively deleted site. No deletion sequence or closure was executed here.
The 21 zero cases are already minimal under individual deletion of these saved
chains; relocation or reconstruction may still improve them. These findings
justify considering a separately specified cleanup option and controlled
deadline-aware experiment. They do not authorize integration into native or
the endpoint-support arm, establish novelty, or predict other seeds/inputs.

Exact rerun, choosing a fresh output directory:

```sh
python3 -B results/codex/final-deletion-audit/audit.py results/codex/final-deletion-audit/repeat001
```

The script refuses existing output paths, verifies the frozen identities before
enumeration, and imports no embedding package. The surrounding artifact manifest
binds this script, both review notes and all retained diagnostic records.
