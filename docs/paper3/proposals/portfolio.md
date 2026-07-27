# P3 — Portfolio/racer under the strict fairness frame (`p3-race-*`)

DEMOTED pending its gate. Framing fixed by the user 2026-07-26: **"same wall-clock
budget, same cores, two strategies race."** The baseline for ANY multi-run scheme is
best-of-K-parallel stock MM — MM given the identical multi-run privilege — never
single-shot MM. If the residual over that baseline is ~0, that is reported and P3 ships
as a systems observation, not an algorithm claim. Owner: (built late in M2, only if the
gate passes). Status: spec, gated.

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
