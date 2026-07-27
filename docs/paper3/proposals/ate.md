# P1 — ATE: Adaptive Template Embedder (`p3-template`, `p3-ate`)

The headline dense arm. Owner: (M2 agent). Status: **built** (2026-07-26; see
"As built" below). Spec sections unchanged below the mechanism block.

## Mechanism

```
ATE(G, T, budget):
  cache = busgraph_cache(T)                      # warmed per machine
  if n <= K_max(T):
      tmpl  = cache.find_clique_embedding(n)     # right-sized (never subset a max clique)
      POS   = crossing_position_matrix(tmpl, T)  # POS[i][j] = index in chain i of the
                                                 # contact with chain j; O(n^2), cached per (T, n)
      pi    = assign(G, POS)                     # vertex -> template chain
      emb_T = spur_prune(relabel(tmpl, pi), G)   # factored/polish.py, exact trim
      emb_T = shorten_chains(emb_T, deadline~50ms)
  else:
      emb_T = core_periphery(G, T, cache)        # degeneracy-peel core -> template;
                                                 # MM routes periphery via initial_chains
                                                 # (source passed as GRAPH OBJECT)
  emb_M = search_arm(G, T, remaining_budget)     # stock MM (later: p3-clmm)
  return argmin_ACL(emb_T, emb_M)                # both reported in metadata
```

**Assignment.** After pruning, a path-shaped template chain for v costs ≈ the span of
the crossing coordinates of v's neighbors → objective `min_pi Σ_v span_{u∈N(v)}
POS[pi(v)][pi(u)]` (minimum-linear-arrangement flavor over crossbar slots). Pipeline:
(a) seed orders {identity, cuthill, spectral} from `search_orders.py`; (b) score each
exactly by prune-simulation on POS (no target-graph work); (c) 2-swap local search on
the span objective, deterministic RNG, 100 ms cap; (d) final spur_prune. Zero cross-seed
variance by construction.

## Registered variants

`p3-template` (template arm alone, deterministic; fails for n>K_max unless
core-periphery kicks in), `p3-ate` (auto-select template vs stock-MM search arm at equal
total budget; the never-worse product arm). Assignment ablations via kwargs in the
script route only.

## Novelty vs prior art

CLMM seeds *search* (success-metric only, no trim/assignment, no ACL); DWaveCliqueSampler
practice = untrimmed clique template, no assignment, no adaptive fallback; 2504.21112 =
bipartite sources only. New: density-resolved crossover map; trimmability-aware
assignment; never-worse selector with a deterministic 100%-success arm below K_max;
"search cannot improve the construction" as a regime demonstration (§3.26: ≤0.04).

## Predictions (pre-registered intuitions, not bars)

K-ladder P16 replicates §3.26 (16/39/57% at K60/K100/K140); ER crossover p*(n) ∈
[0.25, 0.6], decreasing in n; margin 10–30% at p ∈ [0.7, 0.9]; trimmed-template ACL
model ≈ (n/12 + 1.5)·(1 − 2/(pn+1)) on P16. Z12 analog expected (busclique native).

## Viability

n ≤ K_max: legal by construction (K_n embeds every subgraph) — success 100%,
deterministic, where factored search arms failed K140 0/3. n > K_max: core+periphery
inherits CLMM's demonstrated frontier extension (K185+ on P16). `p3-ate` success =
union of both arms.

## Kill gates (pre-registered)

- **KG1** = E0 crossover map itself: kill if template+prune (identity assignment) never
  beats MM below p=0.9 at any n.
- **KG2** assignment honesty gate: on win/near-tie cells, 32 random assignments + prune
  → oracle spread; kill the 2-swap optimizer if best-of-32 gain < 2%; keep seeds-only if
  seeds capture the spread. (Internal best-of-N is protocol-legal here: whole arm ≪ one
  MM run.)
- **KG3** escape probe (informational): pssa-fast initialized AT the pruned template on
  K100 + one dense-ER cell. Predicted: cannot improve (§3.26 joint-move blindness).

## Cost & reuse

400–700 LOC python, `algorithms/paper3/ate.py` (+`_template_core.py` helpers). Reuses
`minorminer.busclique.busgraph_cache`, `factored/polish.py` (spur_prune,
shorten_chains), `embedding_backend.py` (validity, growth), `search_orders.py`, the
template-restriction recipe in `docs/paper2/data/dense_attrib.py`.

## Fairness

Must beat, paired at equal budget: stock MM; MM+spur (same polish column); `p3-clmm`
(P2); on any n ≤ K_max cell also raw busclique+prune (to show assignment/trim add
value). Cold-cache wall-clock disclosed once per target; warm cache is the default.
Assignment tuned on dev seeds only.

## As built (2026-07-26)

Files: `ember_qc/algorithms/paper3/_template_core.py` (526 LOC, shared — P2+ import
from here), `ember_qc/algorithms/paper3/ate.py` (296 LOC, registers `p3-template` /
`p3-ate`), `tests/algorithms/test_p3_ate.py` (269 LOC, 30 tests). All 30 contract
tests pass for both arms.

**Actual defaults.**

- busgraph_cache singleton keyed by busclique's own `topology_identifier()` (sha256
  of the busgraph; verified stable across instances/processes and distinct per
  broken-qubit variant). TargetState holds the frozen adjacency, K_max, and the
  per-`n` (ordered chains, POS) cache. Construction ~14 ms on P16 warm.
- Chain ordering: endpoint-first greedy walk of the induced subgraph (min induced
  degree, then smallest label; corridor-first tie-break). On C4/P4/P16 every clique
  chain induces an exact path (verified in tests: consecutive-adjacent).
- POS: first contact, per spec. `ordered_template` returns None (arm fails cleanly)
  if any pair lacks a contact — never observed for right-sized busclique templates.
- Assignment: seed orders {identity, cuthill, spectral} (tie-break in that order)
  scored by the exact span simulator; 2-swap local search from the best seed.
  `ASSIGN_WALL_CAP_S = 0.100`, `SHORTEN_CAP_S = 0.050`; assignment cap is also
  clamped to 50% of the remaining budget (25% in the core+periphery path).
  Fixed RNG seed `0xA7E` — the run seed never reaches the template path.
- Complete-source fast path: for K_n the span objective is assignment-invariant
  (chains interchangeable under the simulator), so seeds + refinement are skipped —
  exact, not an approximation.
- Local-search stops: floor (objective = n), convergence (max(200, 4n) consecutive
  rejects), deterministic op-budget (2e6-op cost model ≈ the wall cap), wall-clock
  backstop (checked every 32 proposals).
- `n > K_max`: core = last-K_max suffix of the min-(degree, label) degeneracy peel;
  core assigned/restricted/pruned against core-internal edges; then stock
  `minorminer.find_embedding(source_GRAPH_OBJECT, edges, initial_chains=core,
  timeout=remaining, random_seed=seed)`. No `skip_initialization` (periphery has no
  chains yet). MM's raw output is returned (no template-side shorten).
- `p3-ate` budget split: below K_max the template stage gets the full deadline —
  its internal caps bound it; measured cost ~1.3–1.7 s at n=100 on P16 (the exact
  spur_prune dominates, not the spec's "~ms"; the assignment/shorten caps hold).
  Above K_max it gets timeout/2 and stock MM the rest. MM stage skipped below 0.05 s remaining. Selection: lower raw ACL of the
  valid embeddings, tie → template. Winner + both ACLs + template metadata recorded
  in `metadata`. Seed default 42 (mirrors the stock `minorminer` arm).
- Statuses: only FAILURE/TIMEOUT (contract); E0's script-side INFEASIBLE is not
  used by registered arms.

**Prune-simulator validation (first-contact span vs real `spur_prune`),**
assignment = the shipped pipeline, 7 probe cells:

| cell | sim total | real total | gap | per-vertex exact | max abs diff |
|---|---|---|---|---|---|
| ER(14,.5)@C4 | 57 | 56 | +1.8% | 13/14 | 1 |
| ER(16,.8)@C4 | 72 | 74 | −2.7% | 12/16 | 1 |
| K16@C4 | 76 | 78 | −2.6% | 12/16 | 1 |
| ER(30,.5)@P4 | 101 | 102 | −1.0% | 29/30 | 1 |
| ER(36,.8)@P4 | 158 | 161 | −1.9% | 31/36 | 2 |
| K36@P4 | 162 | 164 | −1.2% | 32/36 | 2 |
| ER(30,.2)@P4 | 70 | 70 | 0.0% | 28/30 | 1 |

Mismatch mechanisms, both anticipated: simulator *over*-estimates when a pair has
multiple contacts (real prune keeps a better one than the first); *under*-estimates
via neighbour-chain coupling (a neighbour prunes the qubit our first contact
touched, forcing a longer interval). Unit test asserts the measured envelope with
margin (total gap ≤ 10%, per-vertex |diff| ≤ 3, ≥60% exact).

**Deviations from the spec (with why).**

1. The 100 ms assignment cap is implemented as a deterministic proposal-count
   budget sized to ≈100 ms by an op-cost model, with the wall clock as a backstop
   only — a bare wall-clock cap would make same-input reruns diverge whenever the
   cap binds (contract: same seed → identical output). Reruns are identical unless
   the host is far slower than the model.
2. Mechanism block says prune → shorten; no second spur_prune after shorten (the
   spec's literal pipeline; `polish()`'s trailing prune is left to the harness's
   uniform `acl_spur` column so the arm matches its spec exactly).
3. Inside `p3-ate` the comparison is template (pruned+shortened) ACL vs MM raw
   ACL — the deliverable's "return the lower-ACL valid embedding", with no
   MM-side polish inside the arm. Experiment tables still use one polish column
   for all arms (protocol rule 3); the internal selector could in principle
   mis-pick near ties across columns — accepted, disclosed here.
4. Added stops (floor / convergence) to the 2-swap so converged searches return
   early instead of burning the cap.

## M3 pre-registration (DRAFT — copy into notes.md §4.x and stamp shas at launch)

```
### 4.x P1/ATE dev-suite evaluation (M3) (<date>)
PRE-REGISTERED <date>
Question: does p3-ate beat stock minorminer 0.2.22 on the dense side of the E0
  crossover map without regressing anywhere, and does the assignment stage earn
  its complexity (KG2)?
Script/YAML: docs/paper3/data/ate_dev.py @ <sha>   (script route: paired seeds)
Cells / arms / seeds / budget: the E0 standing dev suite (§4.1 output, ≤16 cells
  per topology, P16 + Z12) × {p3-template, p3-ate, minorminer, and p3-clmm if P2
  has landed} × dev instance seeds 101–105 (K_n cells: 1 instance) × algo seeds
  0–4 (deterministic template cells: once) × 60 s. Candidate arms subprocess-
  watchdogged per protocol; hyde06 ≤48 workers, BLAS/OMP=1.
Bars (acl_spur column, both-succeed pairs, per cell):
  B1 dense win: on every dev cell at p >= p*(n) and every K_n anchor with
     n <= K_max: p3-ate vs minorminer median paired dACL <= -5% AND win rate
     >= 70%.
  B2 no regression: on every remaining dev cell: p3-ate median paired dACL
     <= +1% AND p3-ate successes >= minorminer successes.
  B3 template value-add: on B1 cells with n <= K_max, p3-template beats raw
     busclique+prune (identity assignment, E0's `template` arm) median dACL < 0.
  KG2 assignment honesty (win/near-tie cells, n <= K_max, script kwargs):
     32 random assignments + prune per cell -> oracle spread; kill the 2-swap if
     best-of-32 gain over identity < 2%; keep seeds-only if the three seed
     orders capture >= 80% of that spread.
Decision tree: B1 & B2 met -> P1 is the M4 headline candidate (freeze config,
  then eval seeds 901-915 / algo 10-14). B1 not met -> KG1 fires: ER-dense claim
  dies; rescope P1 to K_n/structured-dense only. B2 not met -> selector bug or
  polish-column asymmetry: fix or demote p3-ate to dense-only registration.
  KG2 fires -> replace two_swap_refine with seeds-only (refine=False default),
  re-run the failing cells once.
--- results appended below; nothing above this line is edited after launch ---
```
