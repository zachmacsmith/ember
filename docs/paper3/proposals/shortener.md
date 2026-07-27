# P4 — Shortener economics: fork switches for the 85–95% slice

Speed axis. MM spends 85–95% of wall-clock in the shortening phase
(`improve_chainlength_pass` → `find_short_chain`, §3.15/§3.17); its cost is the
exhaustive audition (construct the full Steiner chain at EVERY meeting point, measure,
tear out unless strictly better). Owner: shared with P6 (same fork files, one agent).
Status: **built** (2026-07-26, commit `c0ca9e00`; spec below, as-built after it).

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

## As-built (2026-07-26)

C++ in `scripts/mm_fork.patch` (fork of stock 0.2.22; every switch byte-identical to
stock at its default — enforced by the `build_mm_fork.sh` self-test and
`tests/algorithms/test_p3_fork.py` parity on 4 (graph, seed) cases):

- **`short_audit`** (int, default 0) — in `find_short_chain` the lockstep sweep is kept
  verbatim; when the switch is on, the per-meeting-point construct/tear block only
  RECORDS the candidate root and its estimate `est(q) = Σ_v distances[v][q]`
  (well-defined at discovery: `counts[q] == degree` fires at the last ball's pop, after
  every `distances[v][q]` is final). Audition is deferred to after the sweep:
  - mode 1 (estimate-only): one construction, at the min-est candidate (ties →
    discovery order = stock's lockstep-radius order); kept iff `cs < stopcheck`
    (`stopcheck = max(last_size, target_chainsize)` — the identical strict-improvement
    test stock uses for its early exit), else thaw the original.
  - mode 2 (budgeted): candidates in `stable_sort` by (est, discovery order); stock's
    keep-the-best acceptance verbatim (first construction always freezes, i.e. mode 2
    keeps stock's sideways/rebalance moves), early exit on `cs < stopcheck`, stop after
    `audit_budget` constructions; final `thaw_back` restores best-so-far.
- **`audit_budget`** (int, default 3; clamped to ≥1; read only when `short_audit == 2`).
- **`dirty_skip`** (int, default 0) — in `improve_chainlength_pass`: skip variable u iff
  `dirty_fail_at[u] != 0` and no w ∈ N[u] ∪ {u} has `dirty_epoch_of[w] > dirty_fail_at[u]`.
  After processing u, u and all its neighbors are re-fingerprinted; the audit counts as
  FAILED (marker set) only when *every* fingerprint in the closed neighborhood is
  unchanged — i.e. the steal_all → audit → thaw/flip round-trip provably returned the
  exact prior state. Fingerprints are order-independent 64-bit sums of splitmix64 over
  (qubit, parent(qubit)) pairs plus all link endpoints, so parent-tree and linkage
  changes are caught, not just qubit-set changes (a 2^-64 collision wrongly skips one
  re-audit — a missed exploration, never an invalid embedding). Wholesale invalidation
  (`dirty_valid = false`) at every point that can mutate chains unobserved:
  `heuristicEmbedding` entry, initialization / improve_overfill / pushdown_overfill
  passes, `quickPass`, and the chainlength-loop rollback; the next chainlength pass
  re-baselines. Conservative by construction: any doubt → no skip.
- Registered arms (in `ember_qc/algorithms/paper3/p3_mm_fork.py`, fallback OFF per
  protocol): `p3-mm-audit` (short_audit=2, audit_budget=3), `p3-mm-dirty` (dirty_skip=1).
  `short_audit=1` and combinations stay kwargs-only via `forked_find_embedding`.

**Deviations from spec:** none in semantics. Two design choices worth flagging:
(i) mode 2 retains stock's sideways acceptance (the switch changes only the audition
*economics*, not the acceptance rule); mode 1 is stricter per the spec ("accept if
strictly better"). (ii) in audit modes the sweep always runs to its stock radius bound
(no mid-sweep early exit) — the sweep is the cheap part (§3.17); the constructions it
skips are the expensive part. Items 3 (patience economics) and 4 (BFS fast path in
`factored/polish.py`) are NOT built — they are harness/Python work outside the fork,
still open.

**Micro-timing sanity (2026-07-26, mac, workers=1, one process, serial — NOT a
claim):** ER(140, 0.3, nx seed 101) on P16 (2,891 edges → 5,640 qubits), algo seeds
{0,1}, 30 s, `fallback=False`. Every run is timeout-bound (the grind uses the whole
budget), so the read is ACL at fixed 30 s:

| arm | seed 0 wall | seed 0 ACL | seed 1 wall | seed 1 ACL |
|---|---|---|---|---|
| stock (mmfork) | 30.12 s | 20.000 | 30.66 s | 19.779 |
| short_audit=1 | 30.59 s | 21.529 | 30.22 s | 21.436 |
| short_audit=2 (j=3) | 30.29 s | 20.250 | 31.41 s | 20.379 |
| dirty_skip=1 | 30.86 s | 20.000 | 30.98 s | 19.336 |

Directional read only: estimate-only gives back ~8% ACL at this budget on this cell
(the audit really is the polish's accuracy mechanism, §3.17); budgeted j=3 sits ~1–3%
off stock; dirty_skip is parity-or-better (identical at seed 0 — no skips fired
mid-grind — and −2.2% at seed 1). On smaller instances that reach the failing tail
inside the budget, dirty_skip shows the intended wall-clock effect (e.g. ER(60, 0.25)
P8: 6.8 s → 5.5 s, stream divergence proving skips fired). The kill gate's budget
sweep {5, 15, 60, 180 s} is where the fixed-wall-clock bet actually gets tested.

## Kill gate (pre-registered, ~2 h after build)

Time-matched Pareto, ER n=180 P16, 5 dev seeds, {stock, A, B(j=3), dirty} × budgets
{5, 15, 60, 180 s}. Any switch not on the Pareto frontier anywhere dies. Stock dominates
everywhere → proposal dies (patience-curve measurement still ships as paper anatomy).

### Drafted pre-registration block (copy into notes.md §4.x AT LAUNCH; hyde06 via QUEUE.md)

```
### 4.x P4 kill gate — shortener-economics Pareto (<date>)
PRE-REGISTERED <date>
Question: at FIXED wall-clock, do cheaper auditions (short_audit=1/2) or skipped
  re-audits (dirty_skip=1) put any point on the time-quality Pareto frontier that
  stock MM does not dominate, on dense-regime ER at P16 scale?
Script/YAML: docs/paper3/data/p4_pareto.py @ <git sha>   [script route, paired]
Cells / arms / seeds / budget: ER(180, p∈{0.1, 0.3}) on pegasus_graph(16),
  instance seeds 101–105; arms {mmfork, short_audit=1, short_audit=2 (budget 3),
  dirty_skip=1} via forked_find_embedding(fallback=False), algo seeds 0–4,
  budgets {5, 15, 60, 180 s} (explicit time sweep per protocol rule 5); both
  acl and acl_spur logged for every arm; ≤48 workers, arms interleaved.
Bars: a switch SURVIVES iff at ≥1 budget it wins the paired median ΔACL_spur
  (same instance seed, same algo seed) vs stock with ≥60% both-succeed win rate,
  or matches ACL_spur (|Δ| ≤ 1%) at ≤0.5× stock wall-clock (wall-clock compared
  within-batch only; headline numbers re-measured at workers=1 idle).
Decision tree: any survivor → keep its registered arm, fold into P2/P3
  multiplier experiments (seeded runs polish more; bigger K per budget).
  Stock dominates everywhere → P4 dies; ship the patience-curve measurement as
  paper anatomy; registered arms stay for the anatomy section only.
--- results appended below; nothing above this line is edited after launch ---
```

## Wins if

2–5× wall-clock at equal ACL on ER n ∈ [100, 220], or better ACL at fixed budget.
Multiplies P2 (seeded runs polish more) and P3 (bigger K per budget). Speed is a
first-class paper metric; headline speed numbers re-measured at workers=1 idle.

## Cost & reuse

100–200 LOC C++ + pyx bindings (actual: mm_fork.patch grew 214 → 673 lines total for
P4+P6 combined); extends `scripts/mm_fork.patch`; parity self-test in
`scripts/build_mm_fork.sh` must stay green (stock == switches-off, byte-identical) —
extended to cover all seven switches; tests follow
`tests/algorithms/test_mmfork_history.py` pattern (`tests/algorithms/test_p3_fork.py`).
