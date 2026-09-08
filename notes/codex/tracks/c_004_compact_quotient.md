# C004: one compact target allocation before quotient reconfiguration

This policy is specified before implementation or its eight-input screen. C003 found four minors, but its full-target allocation left Q=927/598/1411/1633 after deletion, versus fresh MM's 141/121/134/281. The failed searches spent about 14.2 seconds and recorded 80–89 million BFS adjacency visits. The next test changes the initial physical allocation, while retaining C003's single evolving movable-region search.

**Hypothesis.** An initially bounded physical domain prevents early logical contacts from becoming spread across all 4,800 sites. It can shorten both eventual chains and distance-guidance work while allowing region exchanges and safe site transfers within that domain. Let L be the sum of the necessary per-source-vertex chain bounds derived from the exact target maximum degree Δ: `max(1,ceil((degree(u)-2)/(Δ-2)))` when Δ>2, and 1 otherwise. Select exactly `B=min(|largest target component|,4L)` target sites. The fixed factor four supplies experimental headroom over a necessary bound; it is not a proof that the domain can embed the source.

```text
read exact source and full target structure under the same deadline D
find the largest connected target component
approximate its center by the midpoint of a two-sweep BFS path
take one seeded BFS prefix of B sites from that center
form the exact induced target subgraph on those sites, retaining original IDs
coarsen that one subgraph to n connected regions and assign source labels
run unchanged C003 label-exchange / safe site-transfer search on this quotient
if first complete minor exists, run unchanged deletion cleanup
map chains back to the original full target; independently validate under D
otherwise retain explicit partial state, missing edges and all time/work
```

There is one domain size and one evolving state per call. No larger-domain retry, independent constructor, cached embedding, clique construction, MM/busclique call, family dispatch or independent best-of choice is permitted. Both diameter sweeps, subset construction, induced adjacency, coarsening, assignment, search, trimming, output mapping and the original-target validation share the solver deadline. Imports retain the audited pilot timing convention. C003's eight swap candidates, sixteen safe transfer scores, temperature 0.5, alternating move types and final-validation reserve are unchanged. Only frozen utility functions are reused; its constructor is never called.

**Self-critique and prior art.** Movable-region annealing is established PSSA/Bian prior art, and induced-subgraph restriction is a general search heuristic. This is an experimental allocation policy, not an established novel algorithm. The two-sweep midpoint need not be a graph center. A BFS prefix can lose useful long-range couplers and impose a small separator, even when global n/m/degree bounds hold. The initial factor four can be too small for dense sources or too large for paths. Furthermore, a region assignment can fail its individual degree bound even when total B is sufficient. Exchanges/transfers cannot escape the outer subset boundary, so this revisits an explicit capacity risk at the whole-domain level, rather than making C002's separate parent cuts irrevocable. Failures must not be described as source infeasibility on full Z12. No subset-size tuning follows automatically from a failed screen.

**Cheap falsifier.** First use tiny supplied graphs to check exact connected subset size, induced original-edge preservation, lower-bound allocation, final original-ID validity, late success rejection and partial target-ID mapping. Then freeze the unchanged C001–C003 eight-input panel, ideal Z12, seed 0, 15 seconds, fresh paired stock MM on prepared hyde04. The allocation hypothesis is rejected if C004 loses any of the four C003 successful inputs or fails to reduce Q on at least three of those four. Dense failures and all eight statuses remain explicit regardless of that sparse diagnostic. MM superiority still requires timely valid paired outputs; improving on C003 alone is not the project objective. No new held-out inputs are generated or inspected.
