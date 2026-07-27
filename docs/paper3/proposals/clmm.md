# P2 — CLMM++: template-seeded search (`p3-clmm`, `p3-clmm-core`, ...)

Mid-band contender, feasibility-frontier arm, and mandatory literature control.
Owner: (M2 agent). Status: **built** (see "As built" below); kill-gate not yet run.

## Mechanism

1. **`p3-clmm` — faithful Zbinden reproduction (the control):** busclique
   `find_clique_embedding(k)` chains passed as `initial_chains` to stock
   `minorminer.find_embedding` (source as GRAPH OBJECT — edge-list drops isolated
   vertices, §3.23 bug-1); k = min(n, K_max); when k < n, chains assigned to k
   lowest-degree vertices (sparse) or k random vertices (dense) per their rule;
   `skip_initialization=False` (MM legalizes around seeds). Single-shot — CLMM is not a
   restart scheme.
2. **Variants:** `p3-clmm-core` — seed the degeneracy k-core (the hard sub-structure)
   instead of degree/random selection, periphery left to MM's search (where MM excels);
   seed-form sweep (raw clique chains vs spur-pruned chains vs prune-to-core-subgraph)
   — which wins is p-dependent, measured not assumed; seed-size ladder k ∈ {n/4, n/2,
   3n/4, K_max} (all ~free from the same cache) — script-route kwargs, registered names
   only for survivors.
3. Output feeds `p3-ate` as its search arm once both exist.

## Novelty

Zbinden measured success counts only, Chimera/Pegasus, no Zephyr, no trimming,
degree/random selection. New: ACL-, variance-, and density-resolved evaluation under
honest controls; degeneracy-core seeding; pruned seeds; size ladder; Z12; head-to-head
vs the raw template (never run in the literature).

## Predictions

Mid-band p ∈ [0.08, p*], n ∈ [100, 300]: success-rate wins (their result, retested on
MM 0.2.22) and modest conditional ACL wins (0–8%) where MM's polish cannot fully wash
out the seed. Frontier: max-embeddable-n extension on P16/Z12 (K182+, ER n=300 p ≥ 0.3),
plus K140-class cells where unseeded arms fail.

## Viability

Seeds pre-solve the hardest sub-structure; MM legalizes the periphery — the demonstrated
K185+ mechanism. Frontier success results cannot "fail" as science: either outcome is
reportable.

## Kill gate (pre-registered)

6 mid-band cells (p ∈ {0.1, 0.2, 0.3} × n ∈ {150, 220}) + 2 frontier cells (K182, ER
n=300 p=0.5), 5 dev seeds, 60 s: `p3-clmm` + one variant vs stock MM. Kill the ACL claim
if no cell shows a paired win; kill ++ if it never beats the reproduction. Success/
frontier story survives regardless.

## Cost & reuse

200–400 LOC, `algorithms/paper3/clmm.py`. Reuses stock minorminer `initial_chains`
path, busclique cache, `degeneracy` order in `search_orders.py`, P1's prune utilities
(import from `ate` module or shared `_template_core.py`).

## Fairness

Must beat: stock MM (paired, same seed); the faithful reproduction (to claim ++); raw
template+prune on any n ≤ K_max cell it claims. No restarts. Success and ACL reported
separately.

## As built (M2, 2026-07-26)

Files: `packages/ember-qc/src/ember_qc/algorithms/paper3/clmm.py` (arms `p3-clmm`,
`p3-clmm-core`), `tests/algorithms/test_p3_clmm.py` (23 tests). Contract suite green
for both arms.

**`p3-clmm`** mirrors the script-local `clmm` arm of `docs/paper3/data/e0_crossover.py`
line for line where it can: k = min(n, busclique max clique);
`busgraph_cache(target).find_clique_embedding(k)` chains index-assigned to the sorted
chosen vertices; selection when k < n is Zbinden's rule (density ≥ 0.3 → sorted
`random.Random(seed).sample(sorted_nodes, k)`; else k lowest-degree, ties by node id);
single-shot `minorminer.find_embedding(source_GRAPH_OBJECT, list(target.edges()),
initial_chains=..., timeout=remaining, random_seed=seed)` with
`remaining = max(1.0, deadline − now)` (the e0 MM floor); `skip_initialization` left at
its default (False — MM legalizes around the seeds).

**`p3-clmm-core`** replaces the selection: peel by degeneracy order
(`search_orders.degeneracy_order`, reverse-elimination placement order) until ≤ k
vertices remain — i.e. the k highest-coreness vertices — and spur-prune each seeded
chain (`factored.polish.spur_prune`, run in index space so arbitrary labels never hit
its int casts) against the source edges *among seeded vertices only* before the MM
stage. Prune deadline = 0.5 × timeout so a slow prune can never starve MM (truncated
pruning is safe — validity-preserving move by move). Periphery entirely unseeded.

Both arms memoize busclique state in a module dict keyed by
`busgraph_cache(g).topology_identifier()` (ctor ~70 ms warm; entry holds the cache
object, max-clique size, lazily built frozen target adjacency, and each per-k chain
template — repeat calls are dict hits). `find_clique_embedding(k)` returns `{}` when
k exceeds the max clique — guarded, returns a failure dict rather than seeding nothing.
Success returns carry `metadata` = {template_k, n_seeded, selection
(all|random|lowdeg|core), seed_qubits_pre_prune, seed_qubits, maxclique}.

### Deviations from the spec / from the e0 script arm

1. **Density source.** The e0 arm branches on the *generator parameter* p; a
   registered arm cannot see it, so `p3-clmm` branches on realized
   `nx.density(source)`. Instances whose realized density straddles 0.3 can take the
   other branch than the e0 script arm. (Only matters when k < n.)
2. **Status refinement.** Empty MM returns are classified TIMEOUT when the deadline
   has passed, else FAILURE (e0 records FAILURE always; the contract prefers the
   distinction).
3. **No in-arm validation.** The e0 arm self-validates; registered arms rely on the
   runner's Layer-1 validation (matches the stock `minorminer` wrapper).
4. **No `_template_core.py`.** The spec's shared-prune-utilities module is owned by
   P1's agent; busclique/prune helpers here are module-private per the parallel-work
   rule (consolidation at merge).
5. **Non-busclique targets fail cleanly** (`clmm: busclique unavailable`) — no silent
   fallback to unseeded stock MM (protocol: fallback variants are explicit `-fb`).
6. **Not yet built:** the seed-form sweep and the k-ladder (spec §Mechanism-2) are
   script-route kwargs by design — registered names only for survivors after the kill
   gate.

### M2 smoke (dev evidence, local mac, 30 s, paired (instance, seed) via
`benchmark_one`; not a pre-registered result)

Cells {ER(150,0.2,101), ER(100,0.5,101), K182} × P16 × algo seeds {0,1} ×
{minorminer, p3-clmm, p3-clmm-core}, raw `acl` column (no terminal polish in this
smoke), one sequential local batch:

| cell        | seed | minorminer      | p3-clmm         | p3-clmm-core    |
|-------------|------|-----------------|-----------------|-----------------|
| ER(150,0.2) | 0    | 17.51 / 30.6 s  | 12.91 / 30.0 s  | 12.89 / 30.9 s  |
| ER(150,0.2) | 1    | 18.44 / 30.2 s  | 12.95 / 30.4 s  | 13.30 / 14.4 s  |
| ER(100,0.5) | 0    | 12.54 / 29.7 s  |  9.80 / 12.1 s  |  9.69 / 12.4 s  |
| ER(100,0.5) | 1    | 12.31 / 31.2 s  |  9.78 / 15.3 s  |  9.71 / 13.2 s  |
| K182        | 0    | FAIL / 39.1 s   | FAIL / 52.2 s   | FAIL / 44.6 s   |
| K182        | 1    | FAIL / 56.7 s   | FAIL / 54.5 s   | FAIL / 59.0 s   |

Read: mid-band, both seeded arms win every paired cell by −21% to −30% ACL, at ½–1×
MM's wall time; core ≈ faithful (splits 3–1 by hundredths, one −0.35 regression).
K182 at 30 s: **all three arms fail** — Zbinden's frontier result did NOT replicate
at this budget/machine (their setting was not 30 s single-shot; the 60 s hyde06
kill-gate is the real test). Also observed: on K182 MM's cooperative timeout is
coarse — every arm (stock included) overshot 30 s by 9–29 s; fits the script-route
watchdog's +30 s grace, but pad budgets accordingly. Local smoke ≠ batch claim
(protocol rule 5); a foreground re-run reproduced the seeded-arm ACLs to the
hundredth and the K182 all-fail pattern.

### Drafted M3 pre-registration block (copy into notes.md §4.x, fill sha + date,
BEFORE launch — protocol rule 6)

```
### 4.x P2 kill-gate: template-seeded MM (CLMM / CLMM++) vs stock MM (<date>)
PRE-REGISTERED <date>
Question: Does faithful CLMM seeding beat single-shot stock MM on success rate and
  paired conditional ACL in the mid-band, and does degeneracy-core seeding
  (p3-clmm-core) beat the faithful reproduction anywhere?
Script/YAML: docs/paper3/data/p2_killgate.py @ <sha> (script route: benchmark_one,
  same algo seed per arm, arms interleaved in one batch; MM-family + p3-clmm* all
  cooperative, no watchdog needed; every arm logs acl AND acl_spur — rule 3)
Cells / arms / seeds / budget: mid-band p ∈ {0.1, 0.2, 0.3} × n ∈ {150, 220} (6
  cells, instance seeds 101–105) + frontier K182 (1 instance) and ER(300, 0.5)
  (seeds 101–105), all on P16; arms {minorminer, p3-clmm, p3-clmm-core}; algo seeds
  0–4; 60.0 s per attempt; hyde06 ≤ 48 workers, loadavg logged.
Bars: (B1, ACL claim) ≥ 1 mid-band cell where p3-clmm vs minorminer paired
  ΔACL_spur < 0 on both-succeed pairs, Wilcoxon p < 0.05. (B2, ++ claim)
  p3-clmm-core beats p3-clmm in ≥ 1 cell on paired ACL_spur (same test) or on
  success count. (B3, frontier) success rates reported separately/unpaired —
  no bar, either outcome reportable.
Decision tree: B1 met → keep the P2 ACL claim; launch the seed-form/k-ladder sweep
  (script-route kwargs) on the winning cells. B1 not met → kill the ACL claim; P2
  survives as success/frontier story only. B2 not met → kill p3-clmm-core (name
  retired at M4); keep p3-clmm as the literature control either way. B3: report
  observed frontier n regardless of direction.
--- results appended below; nothing above this line is edited after launch ---
```
