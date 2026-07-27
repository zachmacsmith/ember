# The racing portfolio (`p3-race8`), explained

Ground truth for this document is the code:
`packages/ember-qc/src/ember_qc/algorithms/paper3/race.py` (851 lines: `race()`,
`race_baseline_bestofk()`, the registered arm `p3-race8`). Spec/as-built record:
`docs/paper3/proposals/portfolio.md`. Evidence: `docs/paper3/notes.md` §4.2 (gate),
§4.6 (M3 result), §4.7 (the budget-on-the-table finding), §4.10 (M4 Table 4).
Where code and prose disagree, the code wins; divergences are flagged in section 5.

Terms, once. An *embedding* maps each source-graph variable to a connected set of
hardware qubits (its *chain*); *ACL* = average chain length = total qubits / number
of variables (lower is better). *minorminer* (MM) is D-Wave's stochastic embedding
search; *legalization* = getting a first valid embedding; *polish* = continuing MM's
chain-shortening on an existing embedding via warm restart (`initial_chains` +
`skip_initialization=True`). The *template* is P1's deterministic busclique
construction (`p3-template`): carve a K_n clique template out of the target, assign
variables to slots, prune to the source's edges, shorten. An *arm* is one strategy
in the race; a *quantum* is one polish time slice (default `total_budget/16`).

## 1. ELI5

**Idea (a) — a heterogeneous portfolio.**
No single starting strategy wins everywhere. Stock MM with different random seeds
lands in different basins of different quality; a Cuthill–McKee-ordered MM
(`mmfork-cuthill`, the C++ fork with a caller-supplied vertex order) wins on other
instances; template-seeded MM (`p3-clmm`, `p3-clmm-core`: busclique clique chains fed
to MM as seeds) wins on dense/mid ones; and on dense graphs the pure template beats
every search outright. So run all of them: the K=8 roster is one template slot, four
differently-seeded stock-MM slots, one cuthill slot, one clmm and one clmm-core slot.

**Idea (b) — successive-halving RACE.**
Eight full-budget runs cost 8x the budget. Instead, share ONE wall-clock budget:
legalize every arm cheaply (first valid embedding, no grinding), then give each
survivor a short polish quantum, rank arms by the best ACL they have reached so far,
drop the worse half, and repeat. The last survivor gets all remaining time. Budget
concentrates on the best-looking basin instead of being split evenly across eight.

This is only legitimate because of a measured fact — the §4.2 gate: after one-to-four
quanta of polish, an arm's current ACL predicts its final ACL (per-instance Spearman
rho(ACL@quantum4, ACL@quantum8): median **+0.885**, 9/9 instances >= 0.5, pooled
+0.876, p ~ 1e-46; even quantum 1 pools at +0.72). Had that correlation not held,
halving would be eliminating future winners on noise: all the scheduling overhead,
ending up grinding an arbitrary arm — strictly worse than plain best-of-8, which at
least gives every start its full share. That failure mode is real: ranking arms at
the *legalization* stage is exactly that dead (§3.16, r ~ -0.01), which is why
selection uses early-POLISH ACL only and why the gate ran before any racer code was
written (rho < 0.5 -> no racer, pre-declared).

**The fairness frame.**
The racer is a multi-run method, so comparing it to a single MM run would be cheating
(any best-of-N beats one run). Its pre-registered baseline (protocol rule 2) is
**best-of-8 stock minorminer given the SAME wall-clock and the same cores**:
`race_baseline_bestofk` runs K=8 full-default MM runs of `budget/8` each,
sequentially, and takes the lowest ACL. The parallel racer (`n_workers=8`) is
compared only against 8 parallel stock-MM runs each at the full budget. The claim is
always the *residual* over MM-given-the-same-privilege, never "beats single MM".

**The honest mechanism of the win.**
On sparse graphs stock MM's own stopping rule (chain-shortening patience) expires
long before the budget: in §4.6 the parallel best-of-8 controls finished in
**7.0–8.7 s median of their 60 s**, and §4.7 measured stock walls of 40.8 s at both
60 s AND 180 s budgets on (140,0.2) — "MM leaves budget on the table". The racer wins
by *converting that leftover wall-clock into quality*: warm-restart polish quanta
(large patience, `timeout=quantum`) keep grinding the best basins after stock MM
would have stopped. Sequentially it additionally beats uniform `budget/8` slicing by
adaptive allocation (the build smoke showed uniform 7.5 s slices are WORSE than one
60 s run on 3/4 pairs — even splitting hurts where the grind is long). A systems win
with an honest name: better budget allocation around unchanged MM dynamics.

**How it relates to its neighbors.**
- **vs MM**: the racer *contains* MM — four arms ARE stock MM (its real dynamics,
  different seeds), and every polish quantum is a stock MM call. It changes when MM
  runs and which run gets more time, not what MM does.
- **vs busclique**: the template is one arm, run first, kept as a *floor* — never
  halved, never polished by the racer (only its own internal shorten). It costs
  ~nothing (~ms below K_max), guarantees success where search struggles, and wins
  dense instances outright. It is insurance, not a contestant.
- **vs ATE** (`p3-ate`): ATE is 2 arms, both evaluated to completion inside one
  budget (template AND stock MM; return the lower ACL). The racer is 8 arms with
  *staged elimination* — 8 full evaluations are unaffordable, so it buys ranking
  information with quanta instead. On dense cells its winner is the template
  ~always (ATE-with-overhead); its own value shows only where the template loses
  (sparse) — exactly how the claims are split (section 5).

## 2. Complete pseudocode

```
CONSTANTS  DEFAULT_QUANTUM_FRAC = 1/16   POLISH_PATIENCE = 2000 (trips only on true convergence)
           LEGALIZE_PATIENCE = 0         _MIN_SLICE_S = 0.05      _CONVERGED_FRAC = 0.5
           _TINY_TIMEOUT_S = 2.0         _SEED_MOD = 2^31 - 1     _EPS = 1e-9
  RACE8_SPEC = [(template,{}), (mm,{}) x4, (cuthill,{}), (clmm,{}), (clmm-core,{})]   # indices 0..7

SEEDS  arm_seed(seed, i)      = (seed*1000 + i) mod _SEED_MOD     # roster index order
       quantum_seed(aseed, q) = (aseed + 7919*q) mod _SEED_MOD    # q = arm's polish-quantum counter

race(source, target, total_budget_s, seed, arms_spec, n_workers=1, quantum_frac=1/16,
     polish_patience=2000, validate=True):
  deadline = now + total_budget_s;  quantum = max(0.05, total_budget_s * quantum_frac)
  publish (source, target, target-edge-list) to module global _SHARED   # workers read from it
  arms  = [Arm(i, kind, params, arm_seed(seed, i)) for i,(kind,params) in enumerate(arms_spec)]
  best  = (emb=None, acl=+inf)      # global best-EVER; adopt only on acl < best - 1e-9
                                    # (strict < => exact ties keep the EARLIEST achiever,
                                    #  and the template runs first)
  consider(emb, arm, stage): if emb nonempty and (not validate or is_valid_embedding(emb)):
      acl = sum(len(chain))/n_vars; maybe adopt as best; return acl   else return None

  # -- phase 0: template floor (never raced) ------------------------------------
  for each arm with kind == "template":
      if remaining < 0.05: status = "skipped:no-budget"; continue
      slice = min(remaining, max(2.0, quantum))   # bounded: above K_max the template's
      r = _run_template(...)                      # core+periphery mode contains an MM stage
      # = get_target_state(target); ate._template_arm(source, target, state, now+slice, arm.seed)
      #   -> direct busclique template (n <= K_max) or core+periphery (peel a degeneracy
      #      core, template it, stock MM with the core chains as initial_chains)
      consider(...); status = "floor" if valid else "template-failed"; keep meta as template_view

  racing = arms with kind != "template"
  # cuthill preflight: if the fork .so is absent (minorminer_forked._find_so() is None)
  # or ORDERINGS["cuthill"](source) fails -> cuthill arms status="skipped:fork-unavailable",
  # zero budget spent. Otherwise compute cuthill_order ONCE in the parent.
  live = racing arms not skipped
  if n_workers > 1 and live: pool = ProcessPoolExecutor(n_workers, mp_context="fork")
      # created AFTER phase 0 so fork children inherit _SHARED + warm busclique caches

  # -- phase 1: legalize every racing arm once ----------------------------------
  per arm (sequential: slice = min(quantum, remaining), skip if remaining < 0.05;
           parallel:  ONE common slice = min(quantum, remaining), all arms concurrently):
    kind mm        -> minorminer.find_embedding(source, target_edges, random_seed=arm.seed,
                        timeout=slice, chainlength_patience=0)      # first valid emb, no grind
    kind cuthill   -> forked_find_embedding(source, target, order=cuthill_order,
                        seed=arm.seed, timeout=slice, tries=params.get("tries",10),
                        fallback=False)                             # fork's own default patience
    kind clmm      -> clmm._clmm_embed(source, target, timeout=slice, seed=arm.seed,
                        core_seeding=False)                         # template seeds + 1-shot MM
    kind clmm-core -> same with core_seeding=True
    valid  -> arm.chains = result; status "racing";  invalid/empty -> status "legalize-failed"
  survivors = racing arms with status "racing", sorted by (best-so-far ACL, index)

  # -- phase 2: successive-halving polish rounds --------------------------------
  while len(survivors) > 1 and remaining >= 0.05:
      round += 1
      for arm in survivors if not arm.converged:          # best-first order; sequential mode
          if remaining < 0.05: break out of this round    # sizes each slice, parallel mode
          POLISH_QUANTUM(arm, slice=min(quantum, remaining))   # gives all one common slice
      sort survivors by (acl_best, index)                 # acl_best = best-so-far, monotone
      keep = len - len//2                                 # 7->4->2->1 (8-roster: 7 race)
      dropped tail -> status "dropped:r<round>"; record round info
      if all survivors converged: break

  POLISH_QUANTUM(arm, slice):                             # the §4.2-verified plumbing
      arm.n_quanta += 1
      emb = minorminer.find_embedding(source, target_edges,
              initial_chains=arm.chains, skip_initialization=True,
              timeout=slice, random_seed=quantum_seed(arm.seed, arm.n_quanta),
              chainlength_patience=polish_patience)       # 2000
      if emb nonempty: consider(emb); arm.chains = emb    # chain-forward the RAW result even
                                                          # if worse (raw ACL is non-monotone;
                                                          # best-ever is tracked separately)
      if elapsed_call < 0.5 * slice: arm.converged = True # ended on patience => CONVERGED:
                                                          # never polished again, still ranked

  # -- phase 3: last survivor gets the remainder --------------------------------
  winner_arm = survivors sorted by (acl_best, index), first; status "final"
  (other survivors keep status "survivor")
  while not winner_arm.converged and winner_arm.chains and remaining >= 0.05:
      POLISH_QUANTUM(winner_arm, min(quantum, remaining))  # stage "final1", "final2", ... —
      # quantum-sized chunks, NOT one big slice, so best-ever tracking survives MM's wander

  return {embedding/acl = global best-ever (may be a DROPPED arm or the template),
          winner = {index, kind, stage} of the best-ever, final_survivor = winner_arm.index,
          arms = per-arm views (status, acl_best, converged, full trajectory),
          rounds, template = template_view, budget = {total_s, elapsed_s, template_s,
          legalize_s, rounds_s, final_s}, quantum_s, n_workers}

race_baseline_bestofk(source, target, total_budget_s, seed, K):   # THE rule-2 control
  per = total_budget_s / K
  for i in 0..K-1:
      if remaining < 0.05: record "skipped:no-budget"; continue
      emb = minorminer.find_embedding(source, target_edges,
              timeout=min(per, remaining), random_seed=arm_seed(seed, i))   # FULL DEFAULTS
      validate; keep lowest ACL (strict <, earliest run wins ties)
  return {embedding, acl, best_run, runs[], K, budget{total_s, elapsed_s, per_run_s}}
  # same seed derivation as race -> paired on the master seed; deliberately NOT registered

p3-race8.embed(source, target, timeout=60, seed=42):     # registered arm; never raises
  if timeout <= 2.0:  # tiny degradation
      template with slice min(deadline, t0 + max(0.5*timeout, 0.25)), seed arm_seed(seed,0);
      then ONE stock full-default MM shot on the remainder, seed arm_seed(seed,1);
      lower ACL wins, template on exact ties; metadata mode="tiny"
  else:
      r = race(source, target, timeout, seed, RACE8_SPEC, n_workers=1, quantum_frac=1/16)
      metadata = {mode:"race", winner, final_survivor, acl, quantum_s, budget, rounds,
                  template, arms (condensed), trajectories keyed by arm index}
  no success -> status "TIMEOUT" if elapsed >= timeout-0.05 else "FAILURE"
```

Parallel mode (`n_workers>1`): phase-1 and each round's polish batch run concurrently
on a fork-context `ProcessPoolExecutor`; every task in a batch gets the same slice; a
dead worker folds into a failed stage. Not reentrant (module-level `_SHARED` feeds
the fork snapshot). Wall-clock semantics in section 5.

## 3. Diagrams

Idealized full-length sequential race, K=8 roster (T = budget, q = T/16; widths are
budget; seven arms race, the template is the floor). `#` = polish quantum,
`L` = legalize, `x` = dropped, `c` = kept as floor.

```
arm 0 template  [Tmpl<=max(2s,q)]c  ....(never raced, never polished; floor)....
                       |  R1 (7 arms)   R2 (4)    R3 (2)    final (1 arm)
arm 1 mm(s*1000+1)  [L][####]        [####]    [####]    [####][####][####]...
arm 2 mm            [L][####]        [####]    [####]  x
arm 3 mm            [L][####]        [####]  x
arm 4 mm            [L][####]        [####]  x
arm 5 cuthill       [L][####]      x
arm 6 clmm          [L][####]      x
arm 7 clmm-core     [L][####]      x
time ->  |-tmpl-|-legalize-|--- 7q ---|-- 4q --|-- 2q --|--- remainder in q-chunks ---|
         drop worst half by best-so-far ACL after each round (keep k - k//2: 7->4->2->1);
         converged arms skip their quantum but stay ranked; all-converged ends early.
```

Same budget, two allocations:

```
best-of-8 (rule-2 baseline)               race (staged elimination)
run0 [==T/8==]  \                         8 starts, cheap legalize, then quanta
run1 [==T/8==]   8 independent            only for current leaders:
...              full-default MM runs;    [LLLLLLL][7q][4q][2q][remainder -> 1]
run7 [==T/8==]  /  take min ACL           budget flows to the best basin (floor =
      every start gets 1/8, winners       template, kept aside); losers cost ~1-2
      and losers alike                    quanta, the winner gets ~everything else
```

## 4. Walkthroughs with real numbers

Both runs executed against this tree (sequential, `RACE8_SPEC`, `race()` called
directly — the registered arm wraps exactly this); real numbers, mac, 2026-07-27.

### 4a. K6 on `chimera_graph(4)` — dense: template wins instantly

`race(nx.complete_graph(6), dnx.chimera_graph(4), total_budget_s=10.0, seed=42)`
(quantum = 0.625 s):

```
template: acl=2.333 (0.02s)                      <- floor set in 20 ms
legalized: [(5,2.333),(6,2.333),(7,2.333),(3,2.667),(1,2.833),(2,2.833),(4,2.833)]
round 1: keep [1,2,3,4] drop [5,6,7]  (2.2s)     all seven at acl_best=2.3333
round 2: keep [1,2]     drop [3,4]    (2.6s)
race done: acl=2.3333 winner={'index':0,'kind':'template','stage':'template'} (2.6s of 10s)
budget: {template_s:0.02, legalize_s:0.013, rounds_s:2.528, final_s:0.0}  elapsed 2.562
template view: {k_max:16, template_mode:'direct', assign_order:'identity', acl:2.3333}
```

Narration. The template (arm 0, seed 42000) produces ACL 2.3333 (14 qubits / 6
variables) in 0.02 s; `consider()` adopts it, `status="floor"`. Legalization gives
cuthill/clmm/clmm-core 2.3333 immediately (ordered or template-seeded construction)
and the patience-0 mm arms 2.6667–2.8333. Round 1: every arm's q1 reaches 2.3333 —
a 7-way tie — so the sort key `(acl_best, index)` decides by INDEX and drops arms
5,6,7 (cuthill, clmm, clmm-core) despite their earlier arrival. Most q1 calls
returned in <0.31 s (< half the 0.625 s slice) => `converged=True`; in round 2 only
non-converged arm 4 polishes (`q2` at t=2.562). The two survivors [1,2] are then
both converged, so the loop breaks EARLY; phase 3 names arm 1 `final_survivor`
(`status="final"`) but never polishes it (`final_s=0.0`), and the race returns at
2.56 s of its 10 s budget. `winner` is the best-EVER: the template — strict-`<`
adoption keeps the earliest achiever of 2.3333, so `winner != final_survivor` (both
reported). This is "portfolio = template + insurance" on dense: the racer adds
nothing over the template (p3-ate would deliver the same headline); the seven search
arms are insurance costing a couple of quanta, not even the whole budget.

### 4b. Sparse: `gnp_random_graph(60, 0.06, seed=3)` on `pegasus_graph(6)` — real selection

Source: 102 edges, disconnected (1 isolated vertex — handled fine).
`race(src, dnx.pegasus_graph(6), total_budget_s=24.0, seed=7)` (quantum = 1.5 s):

```
template: acl=2.55 (0.27s)   {k_max:60, mode:'direct', assign_order:'spectral'}
legalized: [(5,1.40),(7,1.40),(6,1.50),(1,1.667),(3,1.683),(2,1.75),(4,1.90)]
round 1: keep [7,3,2,4] drop [5,1,6] (10.7s)  acl_best {7:1.15, 3:1.1667, 2:1.1833, 4:1.20}
round 2: keep [7,3]     drop [2,4]   (16.2s)  acl_best {7:1.15, 3:1.1667}
round 3: keep [7]       drop [3]     (18.8s)
final: arm 7 polishes final1..final5 (quantum chunks), stays 1.15
race done: acl=1.15 winner={'index':7,'kind':'clmm-core','stage':'q1'} (24.0s of 24s)
budget: {template_s:0.271, legalize_s:0.143, rounds_s:18.387, final_s:5.199}  elapsed 24.002
```

The template legalizes validly at ACL 2.55 but LOSES — it stays a floor and is never
ranked into the halving. After q1 the field has already spread: clmm-core (arm 7)
found 1.15 at t=3.36 s and every later quantum — its own q2/q3, five `final` chunks —
confirms rather than improves it (the §4.2 story: early-polish rank is the final
rank). Round 1 shows a live tie-break: cuthill (arm 5) and mm (arm 4) both sit at
1.20; index keeps 4 and drops 5. The mm arms trail (best 1.1667); an mm-FAMILY arm
(clmm-core = template-seeded MM) wins the race. Deadline honesty: elapsed 24.002 s on
a 24 s budget (+2 ms overshoot).

The paired rule-2 control, `race_baseline_bestofk(src, tgt, 24.0, seed=7, K=8)`
(same master seed => run i's seed 7000+i matches arm i's):

```
runs 0..7 acl: 1.3667 1.2833 1.3167 1.2667 1.3333 1.3667 1.3000 1.3667
best_run=3  acl=1.2667  per_run_s=3.0  elapsed=0.304s (!) of 24s
```

Race 1.15 vs best-of-8 1.2667: **-0.1167 ACL (-9.2%)** on the same seed — and the
mechanism made visible: every full-default MM run hit its patience in 0.02-0.06 s,
so the baseline used 0.3 s of its 24 s budget. Extreme at toy scale, but the same
§4.6/§4.7 phenomenon (stock MM stops at ~7-9 s median on the eval sparse cells,
leaving most of a 60 s budget unused); the racer's warm-restart quanta are what
convert that leftover into the 1.4 -> 1.15 drop.

## 5. Other details

**Determinism.** The whole schedule is a pure function of `(seed, arms_spec)`:
per-arm seeds `seed*1000+index`, per-quantum seeds `arm_seed + 7919*q` (both mod
2^31-1). Stage results are bit-deterministic whenever every MM call ends on its own
stopping rule (patience) rather than the clock — always true at contract scale
(K6/C4 patience trips in ~0.3 s). At experiment scale the wall clock truncates
quanta, and — exactly as for stock MM with a binding `timeout` — results are
deterministic only up to CPU-speed jitter in where the clock falls.

**Wall-clock honesty.** Every slice is clamped to the live deadline
(`min(quantum, remaining)`; nothing starts with < 0.05 s left), so overshoot cannot
accumulate; only MM's cooperative timeout can overrun the final call. The module
docstring says ~1 s at benchmark scales; the build smoke recorded a worst case of
65.4 s on a 60 s budget (typically <= +1.5 s) — see divergence (1). Walkthrough 4b
overshot by 2 ms. Sequential polish is best-first, so if the deadline truncates a
round, the leaders got their quanta first.

**The template-floor exclusion (§4.6 pre-registration).** On mid/dense cells the
racer wins big (-1.9..-17.6% dev) but `winner=template` on 21-25/25 — that is the ATE
story wearing a racer hat, and the pre-registration EXCLUDES those rows from the
selection claim. The racer's own claim lives on template-free cells, where the
winner is an mm-family arm. This split was fixed before the data existed.

**Parallel mode.** `n_workers=8` runs each batch concurrently (fork pool created
after the template phase so children inherit `_SHARED` and warm busclique caches);
its budget is wall time ON 8 CORES, so per protocol rule 2 its baseline is 8
parallel stock-MM runs each at the FULL budget — per-core-count claims, never pooled
with sequential ones. Sequential `race_baseline_bestofk` is the one-core control only.

**Results (eval scale, §4.10 Table 4, K=15 fresh instances, acl_spur headline
column — every arm gets the same terminal spur-prune before comparison; the racer's
internal selection uses raw ACL).** The selection claim confirms on the
template-free sparse cells (160,0.05), all 75 pairs per cell: P16 -3.25% seq
(80% wins, p=1.8e-9) / -6.42% parallel (96%, p=7.9e-14); Z12 -4.27% seq (88%,
p=1.2e-11) / -7.87% parallel (97%, p=7.9e-14). Pooled over all six selection cells:
seq **-7.73%** (95% wins, p=1.5e-72, 450 pairs) — the pooled number includes the
mid cells, where winner=template 72-75/75 and only the excluded "template +
insurance" story applies. Dev-scale §4.6 saw the same shape (seq -2.31/-4.97%,
par -5.57/-7.53% on the template-free cells; race winners there: mm 20-25, cuthill
1-4, clmm-core 0-1 of 25); Z12 (100,0.2) parallel -1.86% at 76% missed the -2% bar
and is reported, not claimed.

**When the racer is NOT the right tool.** (i) Dense / above-crossover instances:
the template wins ~always — just use ATE, same embedding, no budget burned on seven
doomed arms. (ii) Anywhere time-to-result matters: the racer spends the FULL budget
by design on every call (excluded from the M5 library sweep for exactly this —
~1,500 core-h of by-design burn). (iii) Budgets <= 2 s: degrades to template + one
MM shot (`mode="tiny"`). (iv) Non-busclique targets: template and clmm arms fail
gracefully and the roster degrades to mm x4 + cuthill — no floor, no seeded arms.

**Divergences found (code vs docs).**
1. *Overshoot bound*: the module docstring claims ~1 s cooperative-timeout overshoot
   at benchmark scales; portfolio.md's own smoke recorded +5.4 s worst (65.4 s on a
   60 s budget). Docs-internal tension; the code clamps slice SIZES but cannot bound
   MM's overrun of the last call. Trust the recorded worst case.
2. *Roster vs spec*: the pre-gate spec said "{mmfork-cuthill x seeds}" (plural); as
   built there is exactly one cuthill arm (and one clmm, one clmm-core). The
   as-built section documents the real roster; the spec section was never updated.
3. *"Every surviving arm polishes one quantum per round" is idealized*: the code
   drops the worst half by BEST-SO-FAR ACL even when convergence (or the deadline,
   mid-round) meant some arms got no quantum that round — ranking is on standing,
   not on this round's work. Walkthrough 4a round 2 shows it (only arm 4 polished).
4. *Chain-forwarding does not re-check validity*: `_fold_polish` adopts any
   non-empty polish result as `arm.chains` even if `consider()` judged it invalid.
   Unreachable with MM's valid-or-empty return contract, and the global best is
   validation-protected regardless — a belt-and-braces note, not a bug.
5. The five deviations in portfolio.md's as-built section (patience 2000 vs the
   probe's 10^6; convergence early-exit; cuthill polished via stock-MM warm
   restart; cuthill legalized at the fork's default patience, not 0; template
   slice bounded to max(2 s, quantum)) all verify against the code exactly.
