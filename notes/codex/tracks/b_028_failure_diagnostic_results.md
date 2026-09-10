# B028 fixed-state diagnostic: decision

The distance-sum root score fails to rank the actual constructed chain cost on
all four saved failure states. Useful proposals already exist with the same
neighbor chains and captured routes. This supports investigating construction
that accounts for shared sites when selecting a root and attaching paths.
It does not establish a successful constructor: every diagnostic was censored,
no proposal removed all overlap, and fixed B028 remains rejected.

## Evidence and limits

One immutable four-case run on `hyde02`, launched 2026-09-09 at 23:20:27 UTC.
All 11 lifecycle actions returned 0 without observation timeouts. The four worker
exits and supervisor exit were 1 from the declared 60 s diagnostic deadlines;
there were no outer watchdog kills, missing terminal records or restarts.
The archive was fetched once and all 51 files matched the terminal inventory:
`8af2ba2ed3f3a731dbf9abd1b40ba88461f52c32a33722b1f7a8ccebd45251aa`.
Evidence lives under `results/codex/b028-failure-diagnostic/`.

The passive reader reused the frozen structural checker and original oracle.
It checked all 4,322 completed saved proposals from their recorded chain/witness
deltas against the original graphs, including independent Q/O/Phi recounts.
There are zero valid minors. Four interrupted reconstruction rows receive no
credit, including one whose candidate construction finished before its
independent check was interrupted. Original-root chain/witness deltas and full
state hashes equal the baseline; full cached-tree equality and entry immutability
also passed inside each worker. No prohibited imports, arithmetic fallbacks or
candidate calls occurred in passive analysis. Representative cached trees do not
recreate the original constructor trajectory.

`Q` counts physical memberships, `O = sum(max(k-1,0))` counts overlap, and
`Phi = Q + sum(p*k*(k-1)/2)` uses frozen prices. Each table cell is **Q / O / Phi**.
The singleton control is a source with a hidden single-site embedding, not an
edgeless graph. All alternatives below remain private, overlapping proposals.

| State | Entry | Selected root | First lower Phi | Lowest observed Phi | Lowest observed O |
|---|---|---|---|---|---|
| ER80, g0001 | 249 / 42 / 354 | 250 / 43 / 361 | 248 / 40 / 350 | 246 / 41 / 349 | 259 / 38 / 357 |
| Singleton control80, g0017 | 189 / 77 / 425 | 187 / 75 / 418 | 186 / 74 / 415 | 186 / 74 / 415 | 193 / 73 / 421 |
| Fresh ER100, g0101 | 334 / 60 / 527 | 336 / 56 / 520 | 332 / 61 / 519 | 335 / 59 / 519 | 333 / 56 / 526 |
| Fresh BA100, g0102 | 248 / 19 / 288 | 241 / 18 / 280 | 242 / 16 / 279 | 237 / 17 / 275 | 240 / 15 / 276 |

For every completed current-interface proposal, all other owners' chains are
identical. Independently checking the saved costs gives exactly
`Phi(candidate) = Phi(fixed residual) + sum(cost[q] for q in new owner chain)`.
For ER80, the selected root has J=18 and unique-site cost 22; the first better
root has J=20 and unique-site cost 11. Other selected/first-better pairs are
J 25/33 with cost 12/9, J 24/37 with cost 18/17, and J 22/27 with cost 15/14.
Thus the inversion concerns actual constructed site unions, not changing prices
or accepting different neighbor embeddings. Attachment and subsequent trimming
affect those unions; this experiment does not isolate path sharing as the sole
cause, nor justify treating J as an upper bound on final cost.

The first better proposals appear early, but their costs are observations, not
new iteration caps. Rank counts original-root reconstruction as rank 1.
Delta triples below are **delta Q / delta O / delta Phi**.

| State | First better rank | Cumulative reconstruction seconds | Worker elapsed at receipt | Delta from selected | Delta from entry |
|---|---:|---:|---:|---|---|
| g0001 | 3 | 0.064 | 9.952 | -2 / -3 / -11 | -1 / -2 / -4 |
| g0017 | 23 | 0.577 | 11.824 | -1 / -1 / -3 | -3 / -3 / -10 |
| g0101 | 22 | 1.068 | 20.351 | -4 / +5 / -1 | -2 / +1 / -8 |
| g0102 | 4 | 0.159 | 23.282 | +1 / -2 / -1 | -6 / -3 / -9 |

The reconstruction column includes proposal construction and independent checks;
it excludes genuine routing, route-map serialization and JSONL emission. The
worker column includes cold setup/JIT and preceding diagnostic work. No cold
cost is excluded from the full process accounting below.

## What was and was not resolved

**Routing preference:** lower actual Phi exists within the already captured
neighborhood on all four states. New movable interfaces are unnecessary for
these particular improvements. This is an existential result, not an optimum.

**Acceptance/objective:** lower Phi can worsen O. Fresh ER100's first better-Phi
proposal raises O from the selected root's 56 to 61, even above entry O=60;
the best observed Phi still has O=59. BA100's first better Phi raises Q by one
relative to the selected root. The lowest-O ER80 proposal raises Q by ten
relative to entry. All completed-root regressions remain in the archive and
machine-readable summary, with counts relative to both baseline and entry.
Pinned B028 `visit` accepts every completed feasibility proposal, including
increases; this diagnostic neither exercises nor proves a better acceptance rule.

**Terminal computation:** the four pending-owner proposals completed. Their
Q/O/Phi outcomes are respectively 249/42/354, 189/77/425, 336/61/529 and
248/18/287. Relative to entry these are two score ties, one regression and one
one-unit overlap improvement. Finishing the censored route is therefore useful
in one state, and does not explain all four constructor failures.

**Movable interfaces:** unresolved. All four current-root enumerations exhausted
the wall allowance before retarget selection began. No retarget candidate was
attempted. This scheduling failure must not be reported as evidence against
interface movement.

| State | Completed / attempted / captured roots | Pending proposal s | Current baseline s | Whole process s | User / system CPU s |
|---|---|---:|---:|---:|---|
| g0001 | 1634 / 1635 / 4691 | 7.578 | 0.817 | 60.56 | 59.94 / 0.54 |
| g0017 | 1277 / 1278 / 4800 | 8.548 | 0.576 | 62.19 | 61.12 / 0.95 |
| g0101 | 630 / 631 / 4799 | 14.463 | 1.461 | 62.85 | 62.01 / 0.79 |
| g0102 | 773 / 774 / 4800 | 18.964 | 1.223 | 62.41 | 61.43 / 0.95 |

All eight genuine routes completed. Captured roots cover all 4,800 target sites
only for g0017/g0102; none of the four captured pools was exhaustively evaluated.
Complete root reconstructions consume 171.171 s, **71.3%** of the 240.114 s of
recorded worker time. Independent checks consume 49.981 s (20.8%), candidate
certificate work 53.718 s (22.4%), and captured-route output 4.478 s (1.9%).
The last three are exclusive stage categories; the first two validation costs
are largely included in reconstruction time and must not be added to it.
Per-proposal output is not isolated as a separate stage. Mean complete-root
proposal costs are 0.030, 0.037, 0.063 and 0.046 s. Full process totals are
**248.01 s wall, 244.50 s user CPU, 3.23 s system CPU**. Cold compilation-dispatch
receipts total 34.263 s and overlap routing execution. Worker overruns are
0.006–0.045 s; process startup/teardown and terminal output remain charged.
Raw RSS is preserved without algorithm-specific memory inference. Host load was
approximately 34; there was no paired MM timing comparison in this diagnostic.

## Next decision

Continue a bounded design investigation of incremental cost of actual shared
chain sites during root selection and attachment. The same mechanism addresses
the observed preference inversion on ER80, the control and both fresh inputs.
First derive a cheaper evaluation that retains connected chains and witnesses;
full reconstruction of thousands of roots is unsuitable as a constructor operator.
Any constructor screen must measure feasibility and Q alongside Phi, especially
the fresh ER100 regression. Do not infer a useful root cap from the four ranks.

Stop exhaustive current-root enumeration as the default diagnostic allocation.
If interfaces remain a priority, a separately frozen follow-up must give its
retarget query time before bulk root enumeration, since this run never tested it.
No refinement, next diagnostic or complete-constructor run is authorized by this
note. The retained algorithm's class-level results are unchanged; four exposed
development states, including two fresh source realizations, establish a local
mechanism failure but no class-level generalization or improvement.

## Result records

- `retrieval_review001/verification.json`: PASS, all 51 hashes and lifecycle actions.
- `saved_analysis001/summary.json`: PASS, 4,322 independent checks; SHA
  `3f3e653640b5fc83f674a66c7039e108f415befad08733b75da93f9b88898cbd`.
  The reader ran once, 3.793 s wall / 3.601 s CPU, no candidate imports or calls.
- `saved_analysis001/union_cost_receipt.json` preserves a passive reporting error:
  example labels keyed only by state hash were overwritten when different roots
  produced identical states. Its residual-state/Phi checks remain valid, but use
  `union_cost_receipt_corrected.json` for example roots/J; it matches kind, root
  and state hash. No worker data, proposal or main-reader result was changed.
- Every raw proposal, incomplete row, process time and stream remains in
  `retrieved001/arms/<case>/`. No failure was retried or excluded.
