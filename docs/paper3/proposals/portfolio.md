# P3 — Portfolio/racer under the strict fairness frame (`p3-race-*`)

GATE PASSED 2026-07-26 (notes §4.2: median per-instance ρ@q4 = +0.885, 9/9 ≥ 0.5,
pooled +0.876) — the racer build is unlocked; the strict fairness frame below is
unchanged and binding. Framing fixed by the user 2026-07-26: **"same wall-clock
budget, same cores, two strategies race."** The baseline for ANY multi-run scheme is
best-of-K-parallel stock MM — MM given the identical multi-run privilege — never
single-shot MM. If the residual over that baseline is ~0, that is reported and P3 ships
as a systems observation, not an algorithm claim. Owner: (built late in M2, only if the
gate passes). Status: **BUILT 2026-07-27** (`ember_qc/algorithms/paper3/race.py`;
as-built record at the bottom of this file). M3 measurement pending.

## Gate first (run before any build; shares data with P4)

Rank-stability probe: 3 dev instances × 16 seeds, polish in 8 warm-restart quanta
(`initial_chains` + `skip_initialization` + bounded `chainlength_patience`), record ACL
trajectories. Compute Spearman(ACL@quantum q, final ACL) per q. **ρ < 0.5 at the halfway
quantum → no racer** (selection is impossible; the DEAD legal-stage result §3.16 extends
into the polish). The same trajectories give P4 its patience/diminishing-returns curve.

## Mechanism (if gate passes)

Arms: {stock MM × seeds} ∪ {mmfork-cuthill × seeds} ∪ {p3-clmm variants} ∪
{p3-template — one deterministic slot, never halved early (costs ~nothing, wins dense)}.
K = 8 default; legalize all (legalization is 5–15% of a run); rounds of fixed polish
quanta (1/16 of total each); halve the field by current ACL; survivor gets the
remainder; return best-ever. Selection on early-POLISH ACL only (legal-stage selection
is DEAD, r ≈ −0.01).

## Registered claims (in order of confidence)

1. Variance: expected 30–60% reduction vs single-run MM — but reported against
   best-of-K-parallel MM, which also has min-of-K variance; the honest claim is the
   *residual* difference from arm heterogeneity.
2. Anytime curves and success-union (heterogeneous arms fail on different instances;
   the template slot floors success at 100% for n ≤ K_max).
3. ACL: only the residual over best-of-K-parallel MM at equal wall-clock on equal cores.

## Kill conditions

Gate ρ < 0.5 → build nothing beyond plain heterogeneous-best-of-K measurement. Racer
built but residual over parallel-MM ≈ 0 on all dev cells → report as observation, no
algorithm claim.

## Cost & reuse

300–500 LOC harness-level python (`docs/paper3/data/` runner logic + thin
`algorithms/paper3/race.py` if a registered arm is warranted). Reuses warm-restart
plumbing verified in `docs/paper2/data/basin_persistence.py`.

---

## As built (2026-07-27)

`packages/ember-qc/src/ember_qc/algorithms/paper3/race.py` (851 lines incl. docs);
tests `tests/algorithms/test_p3_race.py` (9 tests) + the general contract suite
(15 param'd tests for the arm). Three entry points:

- **`race(source, target, total_budget_s, seed, arms_spec, n_workers=1,
  quantum_frac=1/16, *, polish_patience=2000, validate=True, on_event=None)`** —
  the library the M3 scripts call. Arm kinds: `template` (P1 `_template_arm`,
  runs first, kept as a floor, never halved/polished), `mm` (stock MM; legalize
  `chainlength_patience=0`), `cuthill` (`forked_find_embedding` `fallback=False`,
  silently skipped when the fork .so is absent), `clmm`/`clmm-core`
  (P2 `_clmm_embed`). Phase 1 legalizes each racing arm once (one quantum slice);
  phase 2 runs halving rounds — every surviving arm polishes one quantum via the
  §4.2-verified warm-restart pattern (`initial_chains` + `skip_initialization` +
  `timeout=quantum`), the worst half by best-so-far ACL drops each round
  (keep = k − k//2, ties by arm index); the last survivor polishes on the
  remaining budget in quantum-sized chunks (so best-ever tracking survives MM's
  non-monotone raw returns). Best-ever VALID embedding wins; ties go to the
  earliest achiever (template first). Per-arm seeds `seed*1000+arm_index`
  (mod 2^31−1); per-quantum polish seeds derived from those. Metadata: full
  per-arm trajectories, survivor sets per round, winner/final-survivor, per-phase
  budget accounting.
- **`race_baseline_bestofk(source, target, total_budget_s, seed, K)`** — THE
  rule-2 control, in the same module so it cannot drift from the racer's
  accounting: K sequential full-default stock-MM runs of `budget/K` each
  (deadline-clamped), lowest raw ACL among valid results; per-run seeds
  `seed*1000+i`. Deliberately NOT registered as an arm.
- **`p3-race8`** (registered) — sequential race, K=8 roster
  (template + mm×4 + cuthill + clmm + clmm-core), quantum = `timeout/16`;
  `timeout ≤ 2 s` degrades to template + one stock-MM shot. Contract-clean
  (529-test algorithms suite green incl. the 15 p3-race8 contract params).

### Deviations from the spec (and from the §4.2 probe plumbing)

1. **`polish_patience=2000`, not the probe's 10^6.** Behaviorally identical at
   experiment scale — a no-improvement shortening sweep at n≥100/P16 costs
   ≥ tens of ms, so 2000 of them never fit inside any quantum ≤ ~60 s and quanta
   still end on timeout — but on toy instances patience trips in <0.5 s
   (measured K6/C4 ≈ 0.30 s), which makes the registered arm deterministic and
   fast under the contract suite (same-seed bit-identical results verified).
2. **Convergence early-exit** (not in the spec): a polish call returning in
   < half its slice ended on patience ⇒ the arm is marked converged and never
   polished again (it still competes on its best-so-far ACL); all-converged ends
   the race early. At experiment scale this fires only when a quantum truly
   converges; it is what makes contract-scale calls finish in ~2 s instead of
   burning the full timeout.
3. **Cuthill polish uses stock-MM warm restart** — the fork contributes the
   construction order only (`forked_find_embedding` exposes no
   `initial_chains`); polish machinery is shared across all arms.
4. **Cuthill legalize is the fork's full search at its default patience**, not
   patience=0 (the wrapper does not expose patience); that brief internal grind
   is the arm's construction identity. mm arms legalize at patience=0 per spec.
5. **Template slice is bounded** to max(2 s, one quantum): above K_max the
   template's core+periphery mode contains an MM stage that would otherwise eat
   the budget.
6. **Wall-clock overshoot**: every slice is clamped to the live deadline, so
   overshoot cannot accumulate, but MM's cooperative timeout can overrun the
   final call by ~one shortening sweep. Observed worst in the build smoke:
   65.4 s on a 60 s budget (ER(140,0.2)); typically ≤ +1.5 s.
7. `n_workers>1` (ProcessPoolExecutor, fork context) exists for the M3
   many-core scripts; its wall-clock claim is **per core count** and it must be
   baselined against best-of-K-parallel MM at the same core count (the
   sequential `race_baseline_bestofk` is the one-core control only).

### Build smoke (2026-07-27, NOT pre-registered, dev instances, local mac)

ER(n,p,i101) on P16, algo seeds {0,1}, 60 s budget, sequential; acl_spur column
(rule-3 terminal polish on every arm):

| cell        | seed | p3-race8 | bestof8-mm | mm-single 60s | Δ(race−bestof8) |
|-------------|------|----------|------------|---------------|-----------------|
| ER(100,0.5) | 0    | **9.63** | 12.17      | 11.75         | −2.54           |
| ER(100,0.5) | 1    | **9.63** | 12.25      | 12.30         | −2.62           |
| ER(140,0.2) | 0    | **11.89**| 16.21      | 14.50         | −4.32           |
| ER(140,0.2) | 1    | **11.89**| 15.49      | 15.01         | −3.61           |

Wall: race 60.1–65.4 s, bestof8 60.1–60.5 s, mm-single 25–37 s (stock patience
expires early — MM leaves budget unused at 60 s).

Honest read (rule 2): the race beats best-of-K on all four pairs, but the entire
margin is the **template floor** (winner=template on 4/4; both cells sit above
the density crossover). These two cells therefore demonstrate "portfolio =
template + insurance", not selection value: p3-ate would have delivered the same
headline here. The racer's residual — selection among polished mm-family arms —
must be established on sparse cells (e.g. (100,0.1)) and against p3-ate, which
is exactly what the M3 pre-registration below isolates. Also observed: best-of-8
at 7.5 s slices is WORSE than a single 60 s MM run on 3/4 pairs (uniform budget
splitting hurts where the grind is long) — the racer's adaptive allocation is
the fix, and e0_ceiling's best-of-K freebie does not transfer to short slices.

### M3 pre-registration block (DRAFT — copy into notes.md §4.x, fill in
sha/date, commit BEFORE launch; nothing below is a result)

```
### 4.x M3 — racer vs the rule-2 baseline (<date>)
PRE-REGISTERED <date>
Question: does p3-race8 beat best-of-K-parallel stock MM at equal wall-clock on
equal cores, and how much of the residual survives beyond the template floor?
Script/YAML: docs/paper3/data/<m3_runner>.py @ <sha> (imports race and
race_baseline_bestofk from ember_qc.algorithms.paper3.race; script route,
benchmark_one-style same-seed pairing).
Cells / arms / seeds / budget:
  ER (100,0.1), (140,0.2), (100,0.5) [sparse cell mandatory] x inst seeds
  101-105 x algo seeds 0-4, 60.0 s per attempt.
  Arms: p3-race8 (sequential, n_workers=1);
        CONTROL: race_baseline_bestofk K=8 at the same total budget and master
        seed (protocol rule 2 — THE baseline; race vs single MM is never the
        claim);
        p3-ate (context: isolates the template-floor share of any win);
        stock minorminer 60 s (context only).
  Both acl and acl_spur logged for every arm; headline tables use acl_spur.
  Timing-bearing cells re-measured --workers 1 on an idle machine (rule 5).
Bars:
  (a) racer claim: race8 <= bestof8 on >=70% of both-succeed pairs AND median
      per-pair dACL_spur <= -2%.
  (b) selection-beyond-the-floor claim: on at least one cell where the template
      does NOT win inside the race, median dACL_spur(race8 - p3-ate) <= -1%.
Decision tree:
  (a)&(b) met -> racer enters the M4 freeze as an algorithm claim.
  (a) only   -> report as "portfolio = template + insurance" (systems
                observation per the kill conditions; no selection claim).
  neither    -> demote to plain heterogeneous best-of-K measurement; racer is
                reported as a negative result.
Parallel variant (optional, separate table, never pooled): race(n_workers=8) vs
K=8 stock-MM runs each at the FULL budget on 8 cores — the per-core-count rule-2
baseline for the many-core frame.
```
