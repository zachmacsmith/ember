# P4 — Shortener economics: fork switches for the 85–95% slice

Speed axis. MM spends 85–95% of wall-clock in the shortening phase
(`improve_chainlength_pass` → `find_short_chain`, §3.15/§3.17); its cost is the
exhaustive audition (construct the full Steiner chain at EVERY meeting point, measure,
tear out unless strictly better). Owner: shared with P6 (same fork files, one agent).
Status: spec.

## Switches (all parity-guarded in `scripts/mm_fork.patch` style, off by default)

1. **`short_audit`** (§3.17, designed there): in `find_short_chain`,
   (A) estimate-only — one construction at the best estimated root;
   (B) budgeted — audit candidates in estimated order, stop at first improvement or j
   constructions (default j=3).
   The bet is at FIXED WALL-CLOCK: cheaper rebuilds buy more sweeps than per-rebuild
   accuracy loss costs. (The audit exists because sum-of-root-distances misranks Steiner
   trees via trunk sharing — expect some ACL give-back per rebuild.)
2. **`dirty_skip`**: negative cache — skip the rebuild for v if no chain in N[v] changed
   since v's last FAILED audit. Attacks the measured worst case: ~10 failing full sweeps
   before patience expires. (Distinct from the DEAD rip-up *selection* policies, which
   chose what to rebuild for quality; this skips provably-unchanged work for speed.)
3. Harness-level patience economics from the P3-gate trajectory data (no C++).
4. Python-side bonus: BFS fast path in `factored/polish.py::shorten_chains` when prices
   are uniform (they are by default).

## Kill gate (pre-registered, ~2 h after build)

Time-matched Pareto, ER n=180 P16, 5 dev seeds, {stock, A, B(j=3), dirty} × budgets
{5, 15, 60, 180 s}. Any switch not on the Pareto frontier anywhere dies. Stock dominates
everywhere → proposal dies (patience-curve measurement still ships as paper anatomy).

## Wins if

2–5× wall-clock at equal ACL on ER n ∈ [100, 220], or better ACL at fixed budget.
Multiplies P2 (seeded runs polish more) and P3 (bigger K per budget). Speed is a
first-class paper metric; headline speed numbers re-measured at workers=1 idle.

## Cost & reuse

100–200 LOC C++ + pyx bindings; extends `scripts/mm_fork.patch`; parity self-test in
`scripts/build_mm_fork.sh` must stay green (stock == switches-off, byte-identical);
follow `tests/algorithms/test_mmfork_history.py` pattern for tests.
