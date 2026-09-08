# A054 implementation and bounded gate

The authorized source-only comparison, six focused checks and eight fresh
reach calls all passed. **The evidence supports a structural change and a
one-qubit wheel gain, with higher measured runtime; it does not establish a
general improvement.** No registry entry, full candidate panel, cap change,
alternate output selection or additional reach call was made.

`factored/degree_two_construction.py:reduced_core_embed(source,target,*,seed=0,
timeout=60.,deadline=None)` is an isolated copy of fixed A053. Its exact diff
changes only the two eligibility comparisons from ≤3 to ≤2, the module/
algorithm identity, version and `elimination_degree_limit=2`. A focused
literal-source assertion checks that boundary. Anchors, ranks, native core
configuration, transfer/repair modules, budgets, original deadline, fill
provenance, pruning and final validation are unchanged. Final source SHA256:
`404e1e76bd7c199b93e3c60291c1a0304089b90f4c2c0e0a8c48ccc658cc65ee`.

Before implementation, `source-comparison001` processed all 34 frozen 053
source records under a shared five-second/two-million-operation allowance
per input for both reductions and certificate checking. All threshold3
journals matched saved 053; all threshold2 source-minor witnesses passed
independent branch-set connectivity, disjointness and original-edge checks.
No target graph or solver was used. There were no unknown/interrupted/error
outcomes: maximum work was 244,400 operations and maximum elapsed 0.0832 s.
All 34 rows, 35 evaluator memberships, hashes and witnesses remain saved.

Thirteen cores/journals change. Retained core nodes increase 3,073→3,498,
core edges 42,027→42,552, while synthetic core edges fall 620→99. Eliminations
fall 1,244→819 and total created fill 989→257. Fewer artificial contacts do
not mean fewer total core edges. Petersen's core changes from 77 nodes/189
edges to 126/189, with 147 synthetic edges removed; cubic changes 117/300→125/300,
removing 24 synthetic edges. The source-minor certificate bounds the optimum
core cost, not the heuristic output or its ability to lift cheaply.

The six first-attempt checks passed in 0.031 s: direct contractions on cycle/
triangle, older shared-fill provenance, components/isolates/anchors/K4,
deadline interruption without input mutation, exact implementation scope,
and nonbinding small-constructor equivalence. The supplied local transfer
witnesses from A053 were not repeated. No prohibited imports occurred.

| Fixed input | n / m / maximum degree | Q053 / Q054 | Solver s053 / s054 | Engine scans053 / scans054 | Native core calls053 / calls054 |
|---|---|---:|---:|---:|---:|
| Star | 128 / 127 / 127 | 138 / 138 | 1.883 / 1.781 | 1,911,393 / 1,911,393 | 0 / 0 |
| Wheel | 128 / 254 / 127 | 191 / 190 | 6.000 / 8.045 | 5,964,868 / 199,536 | 0 / 1 |
| Subdivided K5 | 15 / 20 / 4 | 17 / 17 | 1.742 / 1.731 | 237,379 / 237,379 | 1 / 1 |
| Exposed cycle | 126 / 126 / 2 | 148 / 148 | 3.093 / 2.914 | 3,008,706 / 3,008,706 | 0 / 0 |

All eight fresh-process outputs are independently original-valid SUCCESS;
there are no deadline, process, work-limit or internal failures. Every fresh
A053 embedding and compared non-time journal/update/work record matches its
saved A053 counterpart. The three unchanged-reduction A054 cases also match
their fresh A053 pairs exactly. Wheel retains its whole original source core
under threshold2, so it performs no reverse insertions or transfers. The other
A054 cases retain 0/1/18 transfers for star/subdivision/cycle, respectively.

The eight calls used the four exact predeclared inputs, A053 then A054 per
input, seed0, separate processes and 20-second constructor allowances. Total
Q is 494→493, solver wall 12.719→14.472 s (CPU12.208→13.828), and process
wall 16.136→18.215 s. **Engine scans exclude native core internal work.**
Wheel's large scan-count drop reflects moving work into the native core;
its measured wall time increases. These few local timings do not establish
a stable runtime ratio. Cycle's existing Q148 deficit is unchanged by this
policy, as predicted from its identical reduction.

The original policy is preserved before the authorized diagnostic-limit
amendment. All plans precede measurement. Code, input and artifact hashes,
all 34 source rows, all eight outputs/process records and the exact source
diff are bound in `results/codex/a054-degree-two/manifest.json`. The completed
commands were:

```sh
.venv/codex-native/bin/python -I -B results/codex/a054-degree-two/compare_reductions.py results/codex/a054-degree-two/source-comparison001
.venv/codex-native/bin/python -I -B results/codex/a054-degree-two/run_checks.py results/codex/a054-degree-two/attempt001
```

These immutable output directories record the completed work, not permission
to rerun it. No further implementation or candidate experiment precedes parent
review of the quality/runtime tradeoff.
