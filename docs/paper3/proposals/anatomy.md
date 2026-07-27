# P6 — Fork anatomy: paper-vs-program micro-science

No leaderboard wins expected; buys the "anatomy of the incumbent" section that derisks
reviewer trust in every other claim. Every embedding paper since 2014 cites the CMR
sketch as if it were the shipped program; `docs/paper2/mm-internals.md` §7 documents the
deltas — these switches measure their consequences. Owner: shared with P4 (same fork
files). Status: **built** (2026-07-26, commit `c0ca9e00`; spec below, as-built after it).

## Switches (parity-guarded, off by default; one probe each, 1–2 h, ER ladder + 2 dense
cells, 5 dev seeds, paired, predict-and-register before each run)

1. **`tree=union`** — revive the dead `construct_chain` (union-of-independent-paths,
   `embedding.hpp:180`, exactly what the 2014 paper describes); third arm `tree=sph-pure`
   (drop the `refcount>1` attach filter → textbook Takahashi–Matsuyama). Question: what
   does MM's Steiner attach actually buy? Prediction: a few % over union.
2. **`root=boltzmann`** — temperature-weighted root choice among candidates (proposed in
   CMR 2014 "to avoid local optima", never shipped) vs uniform-among-exact-minima.
   Prediction: null.
3. **`max_beta` finite** — the paper's D^occ exchange-rate pricing vs shipped
   effectively-infinite lexicographic overlap pricing. Prediction: finite β worse on
   feasibility. (Also completes the §3.13 open residual: separates "history useless in
   MM's dynamics" from "history useless at infinite β".)

## As-built (2026-07-26)

C++ in `scripts/mm_fork.patch` (byte-identical to stock at defaults; parity enforced by
the `build_mm_fork.sh` self-test + `tests/algorithms/test_p3_fork.py`):

- **`chain_tree`** (int, default 0) — a constructor dispatch at BOTH call sites
  (`find_chain`'s legalization construct and every audition construct inside
  `find_short_chain`, including the P4 deferred-audition path):
  0 = stock `construct_chain_steiner`; 1 = the revived `construct_chain`
  (union-of-independent-paths — it needed zero changes, only a caller); 2 = new
  `construct_chain_steiner_pure` in `embedding.hpp` (verbatim Steiner build minus the
  `refcount(p) > 1` attach filter → attach at ANY current chain node, textbook
  Takahashi–Matsuyama). No constructor consumes rng, so the dispatch itself cannot
  perturb the stream.
- **`root_boltzmann`** (double, default 0.0) — in the legalization-phase
  `find_chain(emb, u, target_chainsize)` only (the shortener has no argmin-root step to
  replace; its root rule IS the audition). At 0.0 the stock two lines
  (`collectMinima` + `randint`) run verbatim. When T > 0 the root is drawn among ALL
  finite-cost qubits with P(q) ∝ exp(−(total_distance[q] − min)/T). **Scale:** T is in
  units of the zero-occupancy qubit price (`weight_table[0] == 1`), i.e. "one extra
  free-qubit hop"; occupancy levels cost exponentially more (base ≈ 2^((63−log2 margin)/
  maxfill)), so any small T explores within an occupancy class and essentially never
  crosses one — the natural reading of the 2014 proposal under shipped pricing. Draw =
  one `ep.randint` at 2^30 resolution against the cumulative weight array (exp underflow
  guarded at x ≥ 745); T ≤ 0 (other than exactly 0) clamps to 1e-12 ≈ argmin-uniform.
  T → 0+ recovers the stock distribution in the limit, not the stock rng stream (spec'd
  so; the exact stock code path runs only at 0.0).
- **`max_beta`** — required NO C++: it is a stock 0.2.22 parameter already parsed by the
  pyx (`util.hpp` default `numeric_limits<double>::max()`; `populate_weight_table` uses
  `base = min(exp2(log2base), min(max_beta, round_beta))`, so finite max_beta < the
  auto base gives the paper's β^occ exchange-rate regime). Surfaced through
  `forked_find_embedding(max_beta=)`; verified live (embeddings diverge from stock at
  max_beta=2 on P8/P16 probes).
- Registered arm (fallback OFF per protocol): `p3-mm-union` (chain_tree=1).
  `chain_tree=2`, `root_boltzmann`, `max_beta` stay kwargs-only via
  `forked_find_embedding` — probes are script-route anyway.

**Deviations from spec:** none. One reading made explicit: `root_boltzmann` candidates =
all finite-cost qubits (spec: "ALL finite-cost candidates"), not just `collectMinima`'s
tie set; and it hooks only the legalization/pushdown root selection because that is the
only argmin-root site in the program (mm-internals §5).

## Probes (drafted pre-registration blocks — copy into notes.md §4.x AT LAUNCH, one per
probe, predictions committed BEFORE results; hyde06 via QUEUE.md)

```
### 4.x P6a tree ablation — what does MM's Steiner attach buy? (<date>)
PRE-REGISTERED <date>
Question: paired ACL/success cost of the 2014 paper's union-of-paths build
  (chain_tree=1) and of textbook SPH (chain_tree=2) vs shipped nearest-attach
  Steiner (stock), at unchanged dynamics.
Prediction (committed): stock beats union by a few % ACL; sph-pure ≈ stock
  (the attach filter is a micro-optimization, not load-bearing).
Script/YAML: docs/paper3/data/p6_tree.py @ <git sha>   [script route, paired]
Cells / arms / seeds / budget: ER ladder n ∈ {60,100,140,180} at avg degree 10
  + dense cells ER(100, 0.3) and ER(140, 0.3), P16; instance seeds 101–105;
  arms {mmfork, chain_tree=1, chain_tree=2} (fallback=False); algo seeds 0–4;
  60 s; acl + acl_spur logged; ≤48 workers, interleaved.
Bars: report-only anatomy — no kill bar; the DELTA is the deliverable.
  Success rates reported separately/unpaired; ΔACL on both-succeed pairs.
Decision tree: any arm beating stock (median paired ΔACL_spur < −1%) is a
  surprise → escalate to a 15-seed confirm before any paper claim.
--- results appended below; nothing above this line is edited after launch ---
```

```
### 4.x P6b Boltzmann root — the paper's unshipped proposal (<date>)
PRE-REGISTERED <date>
Question: does temperature-weighted root choice (root_boltzmann ∈ {0.5, 2, 8})
  change ACL, variance, or success vs stock uniform-among-minima?
Prediction (committed): null on ACL and success at T ≤ 2 (within-occupancy-
  class exploration only); possible mild ACL degradation at T = 8.
Script/YAML: docs/paper3/data/p6_root.py @ <git sha>   [script route, paired]
Cells / arms / seeds / budget: same cells as P6a; arms {mmfork,
  root_boltzmann=0.5, 2.0, 8.0} (fallback=False); algo seeds 0–4; 60 s.
Bars: report-only anatomy. Variance claim requires ≥10 seeds → if the 5-seed
  spread looks interesting, rerun the ONE interesting cell at seeds 0–9 before
  writing anything about variance.
Decision tree: null (expected) → one paragraph + table in the anatomy section.
--- results appended below; nothing above this line is edited after launch ---
```

```
### 4.x P6c finite max_beta — D^occ pricing vs lexicographic overlap (<date>)
PRE-REGISTERED <date>
Question: does the 2014 paper's finite exchange-rate pricing (max_beta ∈
  {2, D̂ = graph-diameter estimate, 16}) hurt feasibility/ACL vs the shipped
  effectively-infinite beta? Completes the §3.13 residual (history at finite β).
Prediction (committed): finite β worse on success rate near the feasibility
  cliff (overlap no longer lexicographically dominates), ≈ null on ACL where
  both succeed.
Script/YAML: docs/paper3/data/p6_beta.py @ <git sha>   [script route, paired]
Cells / arms / seeds / budget: P6a cells PLUS one near-cliff cell from E0's
  feasibility table (largest n with MM 4/5 at p=0.2); arms {mmfork,
  max_beta=2, max_beta=D̂, max_beta=16} (fallback=False); algo seeds 0–4; 60 s.
Bars: report-only anatomy; success rates separate/unpaired per protocol.
Decision tree: feasibility drop confirmed → the "lexicographic overlap is
  load-bearing" claim ships with file:line cites; no drop → §3.13 residual
  reopens (history_alpha × finite-β 2×2 becomes a candidate follow-up probe).
--- results appended below; nothing above this line is edited after launch ---
```

## Cost

~150 LOC C++ total on the existing patch infrastructure (actual: shared with P4 in the
214 → 673 line `mm_fork.patch`); parity self-test green before every probe; no build
proceeds past its probe.
