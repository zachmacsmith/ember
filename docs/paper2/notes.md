# Paper 2 — working notes

## 1. What this is

Design notes toward a second paper. Not a paper yet — a running record of the decisions
we make, why we make them, and the sources behind them, so the rationale survives between
working sessions. Terminology is defined here from scratch; we deliberately do **not**
reuse the vocabulary of the first paper ("Reweave", "cold start", "improver", "LNS"),
which was organized around wrapping `minorminer` rather than changing it.

Conventions: `H` is the source (problem) graph, `G` the target (hardware) graph,
`occ(q)` the number of chains currently claiming qubit `q`, `D` the diameter of `G`.
"MM" is `minorminer` (Cai–Macready–Roy [1]).

## 2. Premise

We change **minorminer's algorithm itself** and measure each change. MM's search makes
three separable choices, and we factor the implementation so each is independently
swappable:

| axis | minorminer's choice | our candidate replacement |
|---|---|---|
| qubit cost | `D^occ(q)`, recomputed each pass, no memory | same exponential backbone plus a history term with principled decay (§3) |
| chain construction | union of independent shortest paths to each placed neighbour — **the 2014 paper's description; shipped MM actually builds nearest-attach Steiner trees, see §3.14** | shortest-path-heuristic (SPH) Steiner tree: attach each neighbour to the nearest node of the growing tree [10, 11] |
| vertex order | fixed random order per restart | bandwidth-reducing order (Cuthill–McKee [12]) |

Minorminer is then *one corner of the family* (exponential cost with zero history,
union-of-paths trees, random order), and every claim in the paper reduces to flipping
one switch at a time against that corner. The external baseline is stock `minorminer`;
the internal sanity check is our own implementation at the MM corner.

*Relationship to paper 1.* The first paper (Reweave, `docs/paper/` on the
`new-algorithm` branch; not carried onto this one) built an improvement
pass that runs after minorminer and a vertex-order patch that runs inside it. Its own
ablation found the two imported routing ideas "individually redundant" — because it
tested them warm-started from a valid MM embedding, a regime where there is no congestion
to negotiate (its history term provably never activates there). The from-scratch regime
those ideas were designed for was tried once, in a configuration missing the order lever
and with the cost defects catalogued in §3.7, and abandoned. Paper 2 is the from-scratch
algorithm, done deliberately.

## 3. The cost of a qubit

The routing inner loop prices each qubit and builds chains cheapest-first, so the cost
function *is* the algorithm's theory of congestion. This section records what MM's cost
gets right, what negotiated congestion (PathFinder [2]) actually contributes, why neither
transfers unmodified, and the cost we chose.

### 3.1 What minorminer's `D^occ` gets right

MM prices qubit `q` at `w(q) = D^{occ(q)}` (with `D = diam(G)`), recomputed from current
occupancy each pass [1]. This has a property worth keeping, easiest seen by comparison:

- A free qubit costs `1`; a path of `L` free qubits costs `L`.
- A path containing even one singly-occupied qubit costs at least `D`. So the search
  prefers **any free detour up to ~`D` hops** over touching an occupied qubit.
- One level up: a path of `L` singly-occupied qubits (`L·D`) beats a path containing one
  doubly-occupied qubit (`≥ D²`) for all `L ≲ D`.

Occupancy *depth* is lexicographically dominant over path *length*, with a sane exchange
rate: one occupancy level ≈ `D` hops of detour. Overlap is spread thin rather than piled
deep — and shallow overlap is what rip-up repair can actually fix (evicting one chain per
contested qubit rather than several).

This is not an ad-hoc trick. Exponential-in-load resource pricing is the classic,
*provably good* congestion-control potential: Raghavan–Thompson rounding [4],
Awerbuch–Azar–Plotkin's O(log n)-competitive online routing [3], and Räcke's congestion
minimization [5] all hinge on exponential congestion costs. `D^occ` is the theoretically
respectable part of minorminer.

What it lacks is **memory**. The price depends only on the current snapshot, so two
chains contesting a qubit face symmetric prices forever; MM resolves the deadlock by
randomized order and patience — which is exactly its documented run-to-run variance.

### 3.2 What PathFinder actually contributes

PathFinder [2] (the negotiated-congestion router that FPGA CAD standardized on, via VPR
[6, 7]) prices a routing resource as

    cost(n) = (b_n + h_n) · p_n

with `b_n` a base cost, `p_n` a *present*-congestion multiplier that rises within a pass
as nets pile on (VPR: `p_n = 1 + pres_fac · overuse(n)`, with `pres_fac` growing
geometrically across passes), and `h_n` a *history* term that accumulates on every pass
in which `n` is over-subscribed.

Three observations from reading the sources rather than the folklore:

1. **The algebra is loose.** McMurchie–Ebeling use `(b+h)·p`; VPR's documentation and
   releases have used variants and expose every coefficient as a tunable
   (`initial_pres_fac`, `pres_fac_mult`, `acc_fac`, `max_pres_fac`) [6]. Nobody defends a
   formula; what is defended is the *invariants*: (i) a congestion-oblivious first pass
   discovers each net's ideal route; (ii) a monotone enforcement schedule forces
   feasibility eventually; (iii) cross-pass memory differentiates otherwise-identical
   free resources by their past.
2. **The genuine contribution is the memory.** History answers "who yields?": a
   chronically contested resource becomes expensive *even when momentarily free*, so the
   net that has an alternative discovers it, and the net that has none keeps the
   resource. That is precisely the mechanism MM's snapshot cost cannot express.
3. **There is no convergence theorem.** PathFinder can oscillate; termination is
   engineered (iteration caps, restarts). The rigorous versions of the idea are the
   Lagrangian-relaxation routers [8, 9]: relax the capacity constraints, and the
   multipliers — updated by (primal-dual) subgradient steps — play exactly the role of
   history. That reading matters below.

### 3.3 Why VPR's linear present term is wrong for minor embedding

The linear present cost inverts the property of §3.1. Under `cost(q) = 1 + p·occ(q)`,
compare a path of `L` singly-claimed qubits with a path that routes through one
doubly-claimed qubit (rest free, same length):

    L singles:   L·(1 + p)   =  L + L·p
    one double:  (L−1) + (1 + 2p)  =  L + 2p

For any `L > 2` the doubly-claimed path is **cheaper**, at every value of `p`. The
linear form prices total overlap *mass* and is indifferent-to-favourable toward overlap
*depth* — it will happily deepen an existing pile-up, producing exactly the
hard-to-repair contention that MM's exponential avoids.

FPGAs tolerate this because overuse there is shallow transient scaffolding that the
`pres_fac` ramp eventually crushes, and because the quality objective (delay) lives in a
separate term of the cost. In minor embedding, dense instances produce genuinely deep
contention, and chain length — the thing detours spend — *is* the quality objective.
So we keep the exponential present term.

### 3.4 Why add-only history is FPGA-specific

PathFinder's history never decreases. Four properties of the FPGA setting make that
harmless there — and all four fail here:

| FPGA routing | minor embedding |
|---|---|
| Router **stops at first legality**; scars are never taxed afterwards | We keep optimizing (chain length) after and during legalization; scars directly inflate ACL |
| Net terminals (pins) are **fixed**; the conflict structure is stationary, so old history stays relevant | A chain's "terminals" are its neighbours' current chains, which **move every pass**; old history can describe conflicts that no longer exist |
| The fabric is homogeneous and redundant; a scar diverts to an equivalent wire ~free | Pegasus/Zephyr — especially with dead qubits — are heterogeneous with thin redundancy; detours cost real qubits |
| Quality (delay) is a separate cost term | Quality is the same currency the congestion detours spend |

The original project notes (`docs/paper2/mm-observations.pdf`) flagged the failure mode from first
principles: resolving one conflict against already-inflated prices requires inflating
further, ratcheting without bound; "some sort of decay should probably happen once a
qubit is decongested."

But **blanket decay is also wrong.** A practitioner implementation of PathFinder
(OrthoRoute, a GPU PCB autorouter [13]) documents the failure: uniform `h ← 0.995·h`
every iteration made the router *forget the problem* and oscillate (improve for a dozen
iterations, then spike); their fix was accumulation without blanket decay plus a **cap on
`pres_fac`** so the present term never drowns the history signal. Decay must not erase
memory that is still doing work.

The resolution comes from the Lagrangian reading (§3.2, [8, 9]): history is a Lagrange
multiplier on the capacity constraint `occ(q) ≤ 1`, and the subgradient update for that
multiplier is

    h_q ← max(0, h_q + α·(occ_q − 1))

which **rises in proportion to overuse while contested (`occ ≥ 2`), holds at exactly-full
(`occ = 1`), decays while slack (`occ = 0`), and floors at 0**. It is state-dependent —
scars fade only where the congestion actually cleared — with bounded steps, not a
forgetting factor. Constant-step subgradient ascent converges to a neighbourhood of the
dual optimum; that is as close to "provably fine" as this family gets, and it is strictly
more defensible than both MM (no memory) and PathFinder (no down-step).

### 3.5 The chosen cost

    price(q) = (1 + h_q) · β^{occ(q)}          β = D̂ (estimated diameter of G) by default
    h_q     ← max(0, h_q + α·(occ_q − 1))      once per pass, every qubit

Why this shape:

- **`α = 0` recovers minorminer's cost exactly** (`h ≡ 0` ⇒ `price = D^occ`). MM is the
  memoryless corner of the family, which is the paper's plot in one line: we add one
  principled term and measure it.
- **The exponential backbone does all the enforcement.** History is never asked to grow
  large to force legality — that is `β^occ`'s job. Multiplicatively, `(1+h)` shifts a
  qubit's price by fractions of an occupancy level (`h = β−1` promotes a free qubit to
  the price of an occupied one); its only job is breaking who-yields symmetries among
  free qubits. This directly answers the ratchet worry in the project notes: there is no
  BIG-number escalation because feasibility pressure never routes through `h`.
- In log-space the cost is `log(1+h_q) + occ(q)·log β` — history is an additive "virtual
  occupancy" bias, and `log β` is the exchange rate between occupancy depth and path
  length (§3.1). Choosing `β = D` keeps MM's exchange rate; `β` is a knob, not a law.
- No `pres_fac` machinery. The geometric present-ramp exists in PathFinder to let early
  passes share freely and later passes enforce; MM demonstrates the exponential cost
  legalizes without a ramp (sharing still happens — the price is finite). If we ever want
  McMurchie–Ebeling's congestion-oblivious first pass, the clean way is to ramp **β**
  from 1 to `D̂` — one knob — recorded below as an ablation, default off.

**Open knobs** :

- `β`: fixed `D̂` (default) vs smaller bases vs ramped `1 → D̂`.
- `α` (history step size): default `1.0`; asymmetric up/down steps if oscillation or
  scar-persistence shows up in traces.
- Reroute **all** vertices per pass (MM-style, default) vs reroute only chains touching
  contested qubits (modern router practice).
- Where history lives once an improvement pass exists (paper 1 dropped it there
  entirely; that choice was never measured).

### 3.6 First empirical observation: history is the feasibility mechanism

Single-instance probe (2026-07-10; ER n=30 d=0.5 seed 12345 into clean Pegasus-6,
3 algorithm seeds — a probe, **not** a benchmark):

| config | legal | ACL | passes |
|---|---|---|---|
| default (Cuthill–McKee + SPH + history, α=1) | 3/3 | 5.73, identical every seed | 26 |
| same, α=0 (minorminer's memoryless cost) | 0/3 | — | 64 (cap) |
| MM corner (random order + union trees, α=0) | 0/3 | — | 64 (cap) |
| MM corner + history (α=1) | 1/3 | 8.33 | 64/64/4 |
| stock minorminer, tries=1, chainlength_patience=0 | 3/3 | 4.39 | — |
| stock minorminer, defaults (10 tries + shortening) | 3/3 | 3.46 | — |

Two things worth keeping:

1. **In a deterministic fixed-order loop, α=0 deadlocks.** Snapshot prices cycle
   forever (the fallback legalizer cannot rescue), while α=1 converges in 26
   passes, identically across seeds. Real minorminer escapes the same
   price-deadlocks with *randomness* — a reshuffled order every pass and ten
   restarts. History is a deterministic replacement for that stochastic escape
   hatch: not a quality tweak but the **feasibility mechanism**, turning
   determinism from a variance liability into a feature. Corollary: "our loop at
   the MM corner" reproduces minorminer's *choices* but not its *randomness*,
   which this probe shows was itself load-bearing.
2. **Gap decomposition vs stock MM (5.73 vs 3.46 ACL).** ≈1.0 qubit/chain is
   minorminer's post-legality chain-shortening phase (`chainlength_patience`),
   machinery v1 deliberately omits. (Correction of an earlier reading: MM's
   `tries` are *feasibility* restarts that stop at the first success — paper 1's
   fork probe found `tries` ∈ 1..10 give identical ACL *and* wall-clock — so
   restarts contribute nothing here; the ≈1.0 is the shortening phase alone.)
   The remaining ≈1.3 is the to-first-legality gap: construction-detail
   differences plus the fact that we return chains *as negotiated* — still
   carrying the detours congestion pricing forced on them mid-fight, never
   straightened. Both point at the same v2 priority: a finishing/shortening
   pass.

### 3.7 Audit of the prior implementation (why the rewrite)

For the record, the defects in paper 1's implementation of these ideas
(`packages/ember-qc/src/ember_qc/algorithms/reweave.py`, which lives only on the
`new-algorithm` branch; none of this code is imported by the new implementation):

| defect | where | consequence |
|---|---|---|
| Linear present term `(1+h)(1 + pres·occ)` | `_negotiated_cost`, line 257 | depth-inversion of §3.3 — prefers deepening pile-ups on paths longer than 2 |
| Add-only, flat history (`h += 0.5` if contested; no down-step, no proportionality) | `_cold_start`, line 344 | permanent scars (§3.4); overuse depth invisible to the update |
| Cost cache not refreshed on release | `_cold_start`, lines 329–336 (updates on claim only) | a chain sees its *own just-released qubits* as still occupied — systematic self-avoidance, destabilizing exactly the routes negotiation is trying to stabilize |
| History unused outside the from-scratch path; improvement phase prices at `1 + 6·occ` | `_try_shorten`, line 393 | the headline algorithm's "negotiated congestion" never negotiates (h ≡ 0 from any valid warm start) |
| First pass already congestion-averse (`pres₀ = 0.5`) | `_cold_start`, line 324 | no congestion-oblivious discovery pass (ME invariant (i), §3.2) — minor |

The new implementation makes the staleness class of bug impossible by construction: the
cost object owns occupancy and prices, and `claim`/`release` are the only mutators.

### 3.8 Verified facts on minorminer's randomization (for the next design discussion)

Recorded 2026-07-10 so the basin/randomization discussion starts from sources,
not memory:

- The CMR paper's root selection is `g* := argmin_g Σ_j c(g,j)` by default, but it
  explicitly proposes the variant *"we may choose g* randomly, with the probability of
  choosing g proportional to e^−cost(g)"* to *"avoid getting stuck in local optima"*
  (arXiv:1406.2741). A temperature-controlled Boltzmann root is therefore
  CMR-sanctioned but **unshipped**.
- Shipped minorminer implements only the weak form: uniform random choice among the
  *exact-minimum* root candidates (`pathfinder.hpp`: `collectMinima(total_distance,
  min_list)` then `min_list[ep.randint(...)]`).
- Verified from `embedding_problem.hpp` (2026-07-10): the variable order is
  **re-shuffled on every call to `var_order()`, i.e. every pass** (the 2014 paper
  randomizes once per restart), with five order strategies (SHUFFLE, DFS, BFS, PFS,
  RPFS); **neighbour-visit order inside the searches is also randomized**
  (`shuffle_first` / `rndswap_first`) — randomized tie-breaking at the path level; and
  the weight function is not literally `diam^k` but a precomputed exponential table
  with configurable base, exponent capped at 63, and an `exponent_margin`
  overflow-scaling mechanism. None of this appears in the 2014 paper; all of it is
  public source (Apache-2.0). The shipped algorithm's diversity machinery is therefore:
  per-pass order shuffle + per-search neighbour shuffle + uniform-among-minima roots +
  feasibility restarts.
- **The shipped overlap penalty is not `diam^k`.** `find_embedding`'s `max_beta`
  parameter documents the weight as `beta^n` with the default "effectively
  infinite" (realized via the capped exponent table). So production minorminer
  prices overlap *lexicographically-hard* — any overlap level dominates any path
  length — rather than at the paper's `diam`-per-level exchange rate. Another
  load-bearing not-in-the-paper fact.

### 3.9 Second probe: matched cleanup, and a robustness discovery (2026-07-10)

Setup: polish pass added (`factored/polish.py` — spur-prune + free-space
rip-up-shorten to a fixpoint, the same move class as minorminer's
`chainlength_patience` phase; `RouterConfig.polish`, default off). 9-cell ER grid
(n ∈ {20,30,40} × d ∈ {0.3,0.5,0.7}, instance seed 12345) into clean Pegasus-6;
ours deterministic ×1, minorminer ×3 seeds; 120 s budget.

| cell | ours raw | ours+polish α=0.5 / 1 / 2 | mm raw | mm stock |
|---|---|---|---|---|
| n20 d0.3 | fail | fail / fail / fail | 2.30 | 1.72 |
| n20 d0.5 | fail | fail / fail / fail | 3.33 | 2.28 |
| n20 d0.7 | 5.20 | 3.80 / 3.45 / 3.00 | 3.33 | 2.63 |
| n30 d0.3 | fail | fail / fail / fail | 3.67 | 2.72 |
| n30 d0.5 | 5.73 | fail / 4.73 / 4.87 | 4.39 | 3.46 |
| n30 d0.7 | fail | fail / fail / fail | 4.91 | 3.86 |
| n40 d0.3 | fail | fail / fail / fail | 4.85 | 3.75 |
| n40 d0.5 | 11.97 | 7.95 / 6.72 / 6.90 | 5.53 | 4.52 |
| n40 d0.7 | fail | fail / fail / fail | 6.04 | 5.37 |

Three findings, in decreasing order of importance:

1. **The dominant problem is feasibility, not chain length: 6/9 cells never
   legalize.** Diagnosis (instrumented traces, n20 d0.3): a rolling limit cycle —
   exactly one contested qubit per pass, migrating along consecutive qubits of
   Pegasus wires ("walls" formed by long chains), the same vertex pairs
   re-colliding periodically. **Not history's fault and not a budget issue:
   α=0 fails identically, 256 passes = 64 passes, and with α up to 4 the wall
   prices ratchet to h ≈ 108 with nobody yielding** — i.e. the trapped chains
   have *no single-chain alternative at any price*. The deterministic
   construction crams chains into walled pockets, and one-chain-at-a-time
   best-response cannot execute the joint move (shift the wall) that escapes.
   This is the indivisible-bundle coordination failure of §"duality gap," now
   observed in the wild. minorminer escapes the same geometry by randomized
   root tie-breaking and randomized orders (§3.8) — diversity is doing
   *feasibility* work there, not just quality work.
2. **Matched cleanup does not close the quality gap (the bet's core claim:
   confirmed).** On every converged cell, ours+polish remains well above stock
   minorminer: 3.45 vs 2.63, 4.73 vs 3.46, 6.72 vs 4.52 (α=1). Polish is worth
   a lot (n40 d0.5: 11.97 → 6.72) but the *allocation* it inherits is worse
   than minorminer's — cleanup cannot fix where the chains ended up.
3. **The attributed mechanism is refuted: history helps, it doesn't hurt.**
   The α dose-response runs the wrong way for the stale-scar theory —
   polished ACL *falls* as α rises (means over converged cells: 5.88 / 5.09 /
   4.95 for α = 0.5 / 1 / 2; n20 d0.7: 3.80 / 3.45 / 3.00) and weaker history
   also converges less often (n30 d0.5 fails at α=0.5, succeeds at α=1,2).
   More memory ⇒ better allocations *and* better convergence. Fossil scars may
   still exist as a second-order effect, but they are not what separates us
   from minorminer.

Extended dose-response (same three converged cells, α up to 16, polished):
n20 d0.7: 3.00 / **2.90** / 3.35 / 3.15 for α = 2/4/8/16 (mm-stock 2.63);
n30 d0.5: 4.87 / **4.43** / 4.50 / 4.70 (mm 3.46);
n40 d0.5: 6.90 / 7.12 / 6.42 / **6.25** (mm 4.52). No U-turn indicting history:
a noisy plateau from α ≈ 1–4 on, best-over-α reaching +10% / +28% / +38% vs
stock MM. The residual gap is **α-independent** — whatever separates us from
minorminer, the history dose doesn't move it. The α-to-α scatter (~0.3–0.9
qubits/chain between deterministic trajectories) is basin-to-basin variation:
more evidence that basin selection, not scar magnitude, is the live variable.

Net reading: the missing ingredient is a mechanism for **joint reallocation /
symmetry breaking** — the "bounce between basins" discussion — and it is needed
for feasibility before it is needed for quality. Prices + polish are doing their
jobs; the deterministic single-agent dynamics is what deadlocks. Note the clean
cross-over with §3.8: minorminer with *no cross-pass memory* legalizes 9/9 via
randomness alone; we with *no randomness* legalize 3/9 via memory alone. For
feasibility the two mechanisms are substitutes; the paper-2 question is whether
memory + randomness beats randomness alone on quality — and adding randomization
is also what finally makes the α=0 control runnable (the honest history on/off
ablation this probe could not perform).

### 3.10 Drop-in experiment: status — blocked on replica fidelity (2026-07-10)

Goal (Max): make the history cost a drop-in replacement into minorminer's own
dynamics and see what happens. Vehicle: MM-faithful Python replica (fork patch
deferred). Built, as `RouterConfig` knobs (flags-off remains the deterministic
router; unit-tested): `order_per_pass` (re-shuffle vertex order every pass) and
`random_ties` (uniform root choice among the exact tie set — MM's rule — plus
uniform random seed qubits).

Found and fixed along the way: the seeding rule inherited from paper 1 placed a
no-placed-neighbour vertex at the qubit *farthest from everything occupied*.
Under randomized orders several pass-0 vertices seed this way, scattering
anchors to mutually opposite corners whose connecting chains become
cross-fabric walls — an anti-placement rule. (Deterministic Cuthill–McKee never
triggered it: only the first vertex ever seeds.)

**Fidelity gap (open):** even after the fix, with matched randomization and
even at `beta=1e8` (MM's effectively-infinite base), the replica under random
orders rarely legalizes instances stock MM solves in milliseconds on a *single
try* (`tries=1` legalized 9/9 in §3.9):

| config (ER n=14 d=0.45 → Chimera 4,4,4; 3 seeds) | legal |
|---|---|
| cuthill, deterministic (regression) | 3/3 |
| cuthill + random ties | 2/3 |
| random order, fixed | 0/3 |
| random order per pass + ties | 1/3 |
| replica-MM corner (union, α=0, randomized) | 0/3 |
| replica + history (α=1, randomized) | 1/3 |
| stock minorminer, tries=1 | 3/3, milliseconds |

So randomization channels + cost base do **not** reproduce minorminer's
convergence: some structural piece of its rebuild/pass dynamics (chain
accounting during tear-out, termination-into-chain semantics, pass/phase
structure, …) is still unidentified — plausibly the most load-bearing
undocumented part of the program. The history 2×2 is **deliberately not run**:
against an unfaithful replica it would attribute the replica's own pathology to
the cost. Next step: extract the exact rebuild semantics from
`find_embedding`'s C++ (`pathfinder.hpp` `find_chain` / improvement loop,
`embedding.hpp` chain accounting) and close the gap, then run the 2×2.

### 3.11 The 2×2: does history hurt ACL? — No. (2026-07-13)

Ran at Max's request despite the §3.10 fidelity caveat ("any partial answer beats
none"). 8 arms × 9 cells × 5 seeds, all polished, 45 s budget: random-order
MM-style dynamics (`order_per_pass` + `random_ties`) with sph and union trees at
β=D̂, sph at β=10⁸ (MM's effectively-infinite base), and a cuthill+ties hedge
pair; each at α ∈ {0, 1}. (P6 turned out far friendlier to the randomized
replica than the Chimera fidelity check — α=0 legalizes often enough to pair.)

**Paired (cell, seed) comparisons — both α arms legal, identical dynamics:**

| family | pairs | mean ΔACL (α1 − α0) | shorter / longer / tie |
|---|---|---|---|
| random + sph, β=D̂ | 12 | +0.05 | 2 / 3 / 7 |
| random + union, β=D̂ | 15 | −0.12 | 4 / 3 / 8 |
| cuthill + ties, sph | 22 | −0.18 | 7 / 4 / 11 |
| random + sph, β=10⁸ | 16 | −0.27 | 6 / 3 / 7 |
| **pooled** | **65** | **≈ −0.15** | 19 / 13 / 33 |

**Feasibility, same experiment:** history roughly doubles legalization under
every randomized dynamics — 14→29, 15→32, 17→29 of 45 (cuthill hedge 24→32).

Two readings and a caution:

1. **History does not lengthen chains.** The paired effect is ≈ −0.15
   qubits/chain in history's favour, worst family +0.05 (noise), and it is
   largest at the MM-faithful β=10⁸. Combined with the α dose-response (§3.9)
   this closes the question that motivated the whole week: the stale-history
   theory of our quality gap is dead. History pays for itself twice —
   slightly shorter chains and ~2× the legalization rate.
2. **Beware the unpaired table.** Raw per-config means show α=1 *worse*
   (e.g. 4.83 vs 4.18): pure survivor bias — α=0 legalizes only the easy
   (cell, seed) draws, whose chains are naturally short. Pairing flips the
   sign. Any published comparison must be paired or success-rate-matched.
3. The gap to stock MM stands apart from all of this: mm-stock legalizes 27/27
   at ACL 3.37 vs our best arm 32/45 at ≈4.6–4.9. That residual is a
   *dynamics/fidelity* problem (§3.10), demonstrably not a history problem.

### 3.12 The drop-in experiment, unblocked: history inside stock minorminer (2026-07-13)

The §3.10 blocker is resolved from the other direction: instead of making the
replica faithful to minorminer, the history cost is now a switch inside
minorminer itself. The C++ fork (`scripts/mm_fork.patch`, previously only the
`var_order` lever) gains a `history_alpha` parameter implementing §3.5 verbatim
in MM's own dynamics:

- **Price.** minorminer computes every qubit's routing price in exactly one
  place (`pathfinder.hpp`, `compute_qubit_weights`); with `history_alpha > 0`
  that price becomes `(1 + h_q) · weight_table[occ(q)]`.
- **Update.** `h_q ← max(0, h_q + α·(occ_q − 1))` once at the end of each of
  MM's four pass types (initialization, improve-overfill, pushdown-overfill,
  improve-chainlength), where occupancy is globally consistent. During the
  post-legality chainlength phase `occ ≤ 1` everywhere, so h only decays —
  §3.4's "decay while slack" falls out for free.
- **Persistence.** h lives on the pathfinder object: it persists across passes
  *and* across `tries` restarts within one `find_embedding` call (congestion
  geometry is instance-level knowledge; the down-step fades stale scars), and
  is reset per call.
- **Overflow.** Scaled prices saturate at `max_distance / exponent_margin` —
  the same bound MM's weight table already respects — so path-sum arithmetic
  keeps stock's no-overflow guarantee. `h` is a double; prices stay int64.
- **Parity.** Both the multiply and the update are guarded by `α ≠ 0`, and the
  price path consumes no randomness, so `α = 0` (or the parameter absent) is
  **byte-identical to stock** — same embeddings, same RNG stream. Enforced by
  the build self-test and `tests/algorithms/test_mmfork_history.py` (identical
  embeddings vs the installed stock package across seeds).

One semantic caveat: shipped MM's table base is adaptive (effectively-infinite
`max_beta`, §3.8), so occupancy remains lexicographically dominant and `(1+h)`
acts as *sub-level* bias — history breaks who-yields symmetries among
equal-occupancy qubits, which per §3.5 is its only job here.

First activation probe (n∈{30,35,40}, d∈{0.4,0.5} into clean Pegasus-4, 4 seeds
each, `tries=10`; a probe, **not** a benchmark): easy instances legalize before
any pass ends contested, so h stays 0 and `α=1` reproduces stock exactly; on
the congested cells 6/12 runs diverged from stock, and every divergent run had
ACL ≤ stock (e.g. 3.23 vs 3.63, 4.18 vs 4.50). The honest history 2×2 —
`{α=0, α=1} × {stock order, fixed order}`, paired by (instance, seed) with
`fallback=False` — is now runnable against a control that *is* stock minorminer.

### 3.13 The 2×2 inside real minorminer: history is a wash (2026-07-13)

Ran via `docs/paper2/data/history_2x2.py` (raw rows in `history_2x2.csv`).
Arms: {α=0, α=1} × {stock order, Cuthill–McKee}, all pure (`fallback=False`,
stock `tries=10`); α=0/stock-order is byte-identical stock minorminer 0.2.22
(§3.12). Grid A: ER n∈{20,30,40} × d∈{0.3,0.5,0.7} into clean Pegasus-6;
Grid B (congested): n∈{30,35,40,45} × d∈{0.4,0.5} into clean Pegasus-4.
One instance per cell (seed 12345), algorithm seeds 0–9. Paired per
(cell, seed), both arms legal:

| family | grid | pairs | mean ΔACL (α1−α0) | shorter/longer/tie | diverged |
|---|---|---|---|---|---|
| stock | A/P6 | 90 | +0.012 | 1/5/84 | 6/90 |
| stock | B/P4 | 60 | −0.045 | 18/13/29 | 32/60 |
| cuthill | A/P6 | 90 | −0.010 | 4/1/85 | 5/90 |
| cuthill | B/P4 | 60 | +0.003 | 13/15/32 | 30/60 |
| **pooled** | | **300** | **−0.008** | 36/34/230 | |

Success rates are **identical arm-for-arm** (90/90 on every grid-A arm; 60/80
on every grid-B arm — the same hard (cell, seed) draws fail in all four arms).
Dose response (stock order, 4 congested cells, paired): −0.081 / −0.105 /
−0.016 for α = 0.25 / 1 / 4 — small, non-monotone, consistent with noise
around zero. Wall-clock overhead ≈3–6%.

Reading, in order of confidence:

1. **Inside real minorminer, the history term is inert-to-negligible.** On
   easy cells it literally never engages (84–85/90 exact ties — the designed
   negative control); on congested cells it engages in half the pairs
   (~30/60 divergent) and still moves nothing: ΔACL ≈ 0, shorter/longer
   balanced, feasibility unchanged in every arm. The §3.12 first probe
   (6/6 divergent runs improved) does not replicate at sample size —
   it was luck.
2. **This closes the loop on §3.9's substitutes hypothesis.** The replica
   needed history because it was deterministic — history was its only escape
   from price deadlocks (§3.6), and there it also shortened chains (§3.11,
   −0.15 pooled). Real MM already carries per-pass order shuffles, randomized
   tie-breaking, and feasibility restarts (§3.8); given that machinery,
   memory has nothing left to add. Randomness and memory are substitutes,
   and MM already has one.
3. **A mechanistic suspect for the null, untested:** shipped MM prices
   overlap lexicographically hard (β effectively infinite, §3.8), so
   `(1+h)` can only reorder qubits *within* an occupancy class, never
   across classes. The replica ran β = D̂, where history has real exchange
   rate against path length. A `max_beta`-lowered arm (stock exposes the
   parameter) would separate "history is useless in MM's dynamics" from
   "history is useless at infinite β". Also untested: h reset per try
   (ours persists), asymmetric up/down steps.

Consequence for the paper-2 thesis: the cost axis, at least in this form, is
not where minorminer loses. The order axis (§3.11 fork results: ~1–2% ACL,
halved variance) remains the only lever with a measured effect inside real MM.

### 3.14 Verified: shipped minorminer's inner step is already a Steiner heuristic (2026-07-13)

Read while scoping the tree switch for the fork; checked directly against the
0.2.22 source (clone in `external/minorminer-fork`). The headline fact:

- **`construct_chain_steiner` is the only chain constructor ever called**
  (`pathfinder.hpp:377` in `find_chain`; `:422` in `find_short_chain` — every
  pass type funnels through these two sites). It is a nearest-attach Steiner
  build: the first neighbour's path grows from the root; each subsequent
  neighbour attaches at the nearest node of the *current* chain — with attach
  candidates restricted to root/branch nodes (`refcount > 1`), a mild variant
  of pure Takahashi–Matsuyama SPH [10], which would allow any tree node.
- **The union-of-paths constructor (`construct_chain`, `embedding.hpp:180`) is
  dead code** — defined, documented, never invoked. Its own successor's doc
  comment says the Steiner build "has an opportunity to make shorter chains
  than `construct_chain`".
- The group-Steiner→Steiner contraction (touch a *connected chain*, not a
  vertex) is implemented as the seeding rule: each neighbour's Dijkstra seeds
  every qubit of that chain at distance 0 with `parent = -1`
  (`pathfinder.hpp:458-493`), and `link_path` (`chain.hpp:333`) walks parents
  until it lands in the neighbour's chain, making the landing qubit the
  neighbour's side of the link — condition (3) bookkeeping falls out exactly.

The 2014 CMR paper describes the union of independent shortest paths; the
shipped program outgrew its paper. Consequences:

1. **Paper 1's "replace union-of-paths with a real SPH Steiner tree" replaced
   something shipped minorminer does not do.** Its ablation's verdict that the
   SPH ingredient was "individually redundant" is retroactively unsurprising:
   both arms of that ablation were Steiner builders.
2. **The replica's `tree="union"` corner is mislabeled as "the MM corner"**
   (§2 table, §3.9–§3.11 arms). Shipped MM sits nearer our `sph` arm — though
   not identical: the `refcount>1` attach restriction, the per-neighbour full
   distance fields, and the root argmin differ from the replica's `_assemble`.
   A concrete, newly identified contributor to the §3.10 fidelity gap.
3. **The tree experiment inverts.** The arm worth building in the fork is the
   *dumber* union constructor (revive the dead code behind a switch) — the
   question becomes "what does MM's Steiner trick buy?", not "does adding
   Steiner help?" — plus pure-SPH (drop the `refcount>1` filter) as the
   third point. All three share every other line of the program.
4. Another entry for the §3.8 list of load-bearing not-in-the-paper facts
   (with the per-pass reshuffle, the capped-exponent weight table, and the
   effectively-infinite β). The paper is a sketch of this program, not a
   specification of it; claims must be verified against source.

### 3.15 Where stock minorminer spends its time (2026-07-13)

Probe (`data/mm_time_budget.py`, raw in `mm_time_budget.csv`): stock MM on
Pegasus-16 (5640 qubits), ER at average degree 10, n ∈ {60,100,140,180,220},
2 seeds, decomposed with MM's own knobs — `chainlength_patience=0` isolates
legalization from the shortening phase; `threads ∈ {4,16}` parallelizes the
per-neighbour root-distance Dijkstras.

| n | full run | legalize-only | legalization share | ACL legal-only → polished |
|---|---|---|---|---|
| 60 | 1.2 s | 0.16–0.29 s | ~13–22% | 6.4 → 4.0 |
| 100 | 4.6–5.6 s | 0.44 s | ~8% | 9.1 → 5.7 |
| 140 | 10–12 s | 0.5–0.7 s | ~5% | 13.2–14.2 → 7.9–8.2 |
| 180 | 7.5–17 s | 0.8 s | ~5–10% | 15.0–15.7 → 9.9–10.4 |
| 220 | 8.4–9.0 s | 1.4 s | ~15% | 17.5–18.0 → 12.5–12.9 |

Findings:

1. **85–95% of wall-clock is the post-legality shortening phase**
   (`improve_chainlength_pass` / `find_short_chain`), and it earns its keep:
   a consistent ~30–38% ACL reduction over the legal-only result. Legalization
   is cheap and scales mildly. MM's economy is "legalize fast and dumb, then
   spend 10× that budget polishing" — the opposite of where §"root selection
   waste" reasoning pointed. Any speed project aimed at the legalization
   search (early-exit root argmin, flood construction *as a speed play*)
   attacks ≤15% of the bill; Amdahl closes that avenue.
2. **`threads` is a no-op at these scales**: 4 and 16 threads give wall-clock
   and ACL identical to 1 thread at every size. The parallel pathfinder covers
   only the legalization-phase root-distance computation. Another shipped-vs-
   assumed surprise for the §3.8/§3.14 list.

What this motivates instead, in order:

- **Best-of-N legalizations → shorten the winner once.** Legalization ≈5–15%
  of a run, so N-way basin diversity costs ≈ one polish. Stock parameters
  suffice end-to-end (`chainlength_patience=0` for the cheap runs;
  `initial_chains` + `skip_initialization` to warm-start the polish).
  Gating question first: does legal-only ACL predict polished ACL on the
  same instance (if the grind washes out the starting basin, N-way selection
  buys nothing)? A small paired probe answers it.
- **The shortening phase's diminishing-returns curve** (`chainlength_patience`
  sweep): if most of the polish arrives early, cheap runs get much cheaper
  and the N in best-of-N grows at fixed budget.

### 3.16 The basin does not survive the polish (2026-07-13)

Gate experiment for the best-of-N idea (`data/basin_persistence.py`, raw in
`basin_persistence.csv`). Pegasus-16, ER avg degree 10, n ∈ {100,140,180}
(instance seed 12345), 16 seeds each. Per seed: legal-only run
(`chainlength_patience=0`), then a warm-started polish of exactly that
embedding (`initial_chains` + `skip_initialization`, stock patience).
Fidelity confirmed: the two-stage pipeline's polished ACLs match plain
full-run ACLs on the same instance.

| cell | pairs | Pearson(legal, polished) | Spearman | mean legal → polished |
|---|---|---|---|---|
| n=100 | 16 | −0.28 (p=.29) | −0.07 | 9.40 → 5.95 |
| n=140 | 16 | +0.05 (p=.84) | −0.16 | 13.55 → 8.36 |
| n=180 | 16 | −0.01 (p=.97) | +0.02 | 15.92 → 9.92 |
| pooled (centered) | 48 | **−0.01 (p=.93)** | −0.04 | |

Bootstrapped best-of-N preview (select by legal ACL, report polished ACL):
flat at every N — 5.96/5.97/5.96/5.94 (n=100), 8.38/8.34/8.27/8.25 (n=140),
9.91/9.92/9.94/10.00 (n=180) for N = 1/2/4/8.

Reading:

1. **Legal-only ACL carries no information about polished ACL.** The
   shortening grind (which cuts ~35–40% of ACL, §3.15) is chaotic enough to
   wash out the starting embedding's apparent quality. Best-of-N cheap
   legalizations *selected by legal ACL* is dead — killed for the price of
   one probe, before any code was built on it.
2. What is *not* dead: polished outcomes do spread (~±5% ACL run-to-run,
   the full-run columns), so there is variance worth selecting over — it just
   can't be seen from the legal stage. The standard fallback is racing /
   successive halving: give all N candidates a *small* polish budget, keep
   the best half, iterate. Whether early-polish ACL predicts full-polish ACL
   is exactly the `chainlength_patience` curve question (§3.15) — the two
   experiments merged into one: trace ACL vs polish budget per seed and
   compute rank stability over the trajectory.
3. Untested alternative predictors from the legal stage (max chain length,
   qubit dispersion, congestion structure) — noted, not pursued.

Consequence: the shortener itself is the target. Making the polish cheaper
(§3.15 shortener menu: dirty-set + fat-first scheduling, spur-pruning,
endpoint moves, early-exit inner searches) pays on every run
unconditionally; basin selection paid only if this probe had gone the
other way.

### 3.17 Verified: the shortening rebuild is already lockstep meeting-point search; the cost is its exhaustive audition (2026-07-14)

Read `find_short_chain` (`pathfinder.hpp:388-450`), the rebuild used by
`improve_chainlength_pass` — i.e. the inner step of the phase where 85–95% of
wall-clock goes (§3.15):

- Tears out `u`, then expands k Dijkstras (one per neighbour chain) **in
  lockstep by distance**, through free qubits only — synchronized ball growth;
  `counts[q]` tracks how many balls have reached `q`.
- Every free qubit reached by all k balls is a candidate root — the meeting
  points, visited in increasing lockstep radius.
- At **every** candidate it constructs the full Steiner chain
  (`construct_chain_steiner`), measures the *actual* length, and tears it out
  unless it improves; it exits early only on strict improvement over the
  current size, and abandons at radius > current chain length.

Consequences:

1. **The expense is the audition, not the search structure.** Construct-and-
   tear at every meeting point, most expensive exactly when no improvement
   exists (the audit exhausts the ball and fails) — i.e. in the
   diminishing-returns tail of the grind, ~10 failing full sweeps before
   patience expires. The audit exists because the legalization-phase estimate
   (sum of root distances) is loose for Steiner trees (trunk-sharing), so
   estimate-ranking misranks candidates; the code's own comment: this variant
   "takes quite a long time" vs the others that "simply pick a random root
   candidate with minimum estimated chainlength".
2. **Candidate switch for the fork** (the first speed lever aimed at the 90%
   slice): `short_audit` mode — (A) estimate-only: one construction per
   rebuild using the legalization-style estimated root; (B) budgeted: audit
   candidates in estimated order, stop at first improvement or j
   constructions. Not a free win per-rebuild (the audit is the polish's
   accuracy mechanism); the bet is at *fixed wall-clock* — cheaper rebuilds
   buy more sweeps/retries than the per-rebuild loss costs. Experiment must
   be time-matched Pareto (stock vs A vs B), P16 scale.
3. Third entry in the shipped-vs-paper list (§3.8 randomization, §3.14
   Steiner construction, now the shortening rebuild): design discussion here
   independently reinvented both the meeting-point root search and the
   Steiner attach — the shipped program keeps arriving first. The remaining
   headroom is in its *economics* (audit cost, scheduling, patience), not its
   search primitives.

### 3.18 Placement-loop prototype v0: attraction-only orbits, as predicted (2026-07-14)

Prototype of the iterated placement loop (`data/placement_loop.py`, raw in
`placement_loop.csv`): one centroid per variable in `pegasus_layout`
coordinates; per round, one Laplacian-smoothing step (η=0.5, attraction only)
→ snap to distinct qubits (KD-tree, degree-first) → **stock minorminer**
legalization from those seeds (`initial_chains`, `chainlength_patience=0`) →
spur-prune → read centroids back from realized chains. Best round warm-polished
(§3.16 pipeline). Repulsion deliberately left implicit (snap distinctness +
router exclusion). Arms: mm-full, loop (R=10), restart-control (same router
budget, no steering). P16, ER avg degree 10, n ∈ {100,140,180}, 5 seeds.

Max's pre-registered prediction (made mid-run, from the 3-body analogy):
attraction-only dynamics has collapse as its fixed point; the round dynamics
(contract → fabric re-inflates → read back) should therefore orbit, not
descend. **Confirmed:**

- Mean legal-ACL trajectories are flat oscillations around round 0:
  8.52 → (8.7–9.1) at n=100; 12.54 → (12.3–12.9) at n=140;
  14.65 → (14.4–15.7) at n=180. No descent anywhere.
- Final ACLs: loop ≈ control ≈ mm-full (e.g. n=180: 9.95 / 10.28 / 10.10)
  at ~2× mm-full's wall-clock — no win, exactly what flat geometry + §3.16's
  worthless selection predicts. Controls behaved (control ≈ mm-full).
- Wall-clock fairness held: steering glue is 0.3–1.9 s vs 8.7–20.5 s inside
  stock minorminer (≤8%).

Verdict: **the v0 force law is refuted, not the family** — the pre-registered
distinction. The trajectory diagnostic did its job: geometry fails to improve
its own legal ACL under pure attraction. v1 force law (Max): keep attraction,
add **density-overflow repulsion** — bin the layout, capacity = measured
working qubits per bin (broken qubits handled by construction), demand =
centroids × current mean chain length λ (read from last round — capacity
tightens/loosens as chains lengthen/shorten), push centroids in overfull bins
down the pressure gradient. Rationale: for dense sources, collapse-to-capacity
is *correct* (the clique-embedding shape), so rest-length springs are the
wrong fix; density-limited attraction handles both regimes. This is also
VLSI's actual choice (ePlace density fields, not pairwise repulsion).

### 3.19 Placement-loop v1: density-limited attraction descends (2026-07-14)

Same harness, same instances/seeds as §3.18; only the force law changed
(`placement_loop.py --v1`, raw in `placement_loop_v1.csv`): attraction as
before + binned density-overflow repulsion (16×16 bins, capacity = measured
qubits per bin, demand = λ per centroid with λ read back from the previous
round's realized chains, overfull bins push centroids toward the
least-pressured neighbour bin).

**Legal-ACL trajectories now descend** where v0 orbited:

- n=100: 8.52 → 8.07 best (round 7), settling ~8.2–8.6 (v0: never below 8.52)
- n=140: 12.54 → 11.80–11.86 by rounds 8–10, near-monotone (v0: orbit 12.3–12.9)
- n=180: 14.65 → wobble 14.4–14.9, min 14.39 (weak descent; largest size least moved)

**Final polished ACL, paired per (cell, seed), 15 pairs:**

| v1 vs | mean ΔACL | v1 wins |
|---|---|---|
| mm-full (½ the budget) | −0.31 | 11/15 |
| v0 loop (same budget) | −0.23 | 11/15 |
| restart-control (same budget, no steering) | **−0.34** | 10/15 |

Reading, carefully:

1. **The force law was the missing piece, as §3.18 predicted**: adding Max's
   density term turns orbits into descent at two of three sizes and flips the
   loop from indistinguishable-from-re-rolling to beating the same-budget
   unguided control by −0.34 ACL (10/15). Geometry is now doing real work —
   the first mechanism this whole investigation has added to the MM ecosystem
   with a measured positive effect.
2. Honest caveats: 5 seeds per cell; the mm-full comparison is at ~2× its
   wall-clock (the clean same-budget claim is vs control); the n=180
   trajectory barely descends (possible λ/bin-resolution effects at scale);
   descent is ~5–6% of legal ACL, and much of the final gain may flow through
   "better basin → same polish" — which §3.16 said doesn't work from *random*
   basins, so steered basins behaving differently is itself notable and
   should be re-checked (does v1's legal ACL now correlate with polished
   ACL?).
3. Next levers, in order: more seeds + a size sweep for significance; the
   n=180 weakness (bin size vs chain extent; λ per-variable instead of
   global); round schedule (descend further before polishing); and only then
   thinking about speed (the loop still pays ~11 legalizations).

### 3.20 Placement-loop v2: per-variable charge helps the geometry, not the endpoint (2026-07-14)

Charge-model iteration on §3.19, same harness/instances/seeds
(`placement_loop.py --v2`, raw in `placement_loop_v2.csv`).

Design note first: the originally proposed "measured footprint" charge (deposit
last round's realized chain qubits into bins) is **logically inert** for a
threshold-1 push — realized chains occupy distinct qubits, so realized density
can never exceed capacity. Only *proposal* demand can signal crowding. v2
therefore keeps demand on proposals but replaces the global scalar λ with each
variable's own realized chain length from the previous round (per-variable,
measured; still isotropic — the H/V wire-orientation refinement stays parked,
along with interval/crossbar coordinates, per Max: chains also turn corners,
so H/V is itself a cartoon; finer modelling judged not worth its cost yet).

Results (5 seeds × 3 cells, paired):

- **Legal-stage geometry improved**, most where it was weakest: n=180's
  trajectory now genuinely drifts down (second half 14.0–14.4 vs round-0
  14.65; min 14.03 vs v1's 14.39); best-legal-per-seed means: 11.09 vs 11.26
  (n=140), 13.72 vs 13.90 (n=180), ≈tie at n=100.
- **Final polished ACL did not improve**: v2 vs v1 +0.083, v2 wins 5/15 —
  noise-level, slightly the wrong way. The legal-stage gain is eaten by the
  polish (the §3.16 lesson again, now applying between two *steered* variants).
- The family's edge replicates a third time: v2 beats same-budget control
  −0.254 (9/15) and mm-full-at-half-budget −0.230 (10/15), consistent with
  v1's −0.34/−0.31.

Verdict: **v1 stays the default force law by parsimony** (simpler, same
endpoint). Max's pre-run prediction ("charge modelling won't be big enough to
fix 180, but I suspect it would be helpful") — confirmed on both halves.
The recurring structural lesson: improvements to the *legal-stage* geometry
keep failing to survive MM's polish. The next high-value question is therefore
not the force law but the *handoff*: either polish less destructively (local
polish only, preserving the placement's structure), or select/iterate at the
polished level rather than the legal level (e.g. polish the best 2–3 rounds
briefly, race them — merges with the §3.16(2) successive-halving idea).

### 3.21 Why nothing crushes minorminer on this suite: ER is bisection-limited (2026-07-14)

Two one-off measurements (inline, from existing CSVs + one busclique call),
prompted by Max's "something feels wrong — surely MM can't be optimal?"

1. **ACL is linear in n at fixed average degree.** Stock MM full runs, ER at
   avg degree 10 into P16: ACL/n = 0.068, 0.056, 0.057, 0.056, 0.058 for
   n = 60…220 (two independent datasets agree). Constant ACL/n is the
   signature of a *geometric* limit: fixed-degree ER is an expander —
   bisection width Θ(n) — while a quasi-2D fabric's cut capacity grows only
   with the perimeter of the occupied region, forcing total chain mass (and
   hence ACL at fixed n/qubit ratio... more precisely the occupied-region
   scale) to grow until the cut fits. Any embedder pays Θ(n) ACL on this
   class; MM sits on the right scaling law already. **On random ER the only
   available prizes are the constant, speed, variance, and parallelism.**
2. **The crossbar/clique construction is not descriptive of good sparse
   embeddings.** busclique K180 on P16: ACL 16.67. Reusing those exact chains
   for our ER(180, deg 10) instance and spur-pruning to its edges: ACL 13.87
   — far worse than MM's 10.1. The crossbar pays for all-to-all capacity the
   sparse instance doesn't need; its regularity buys everything at the
   density cliff and nothing out here. MM's sparse embeddings rightly look
   nothing like it.

Consequences for the placement family: ER at fixed degree is the *unique*
class with no latent geometry for centroids to discover (a random graph's
2D "positions" carry no information), so "not crushing MM on ER" is the
expected behaviour of a correct geometric method — the replicated −0.3 edge
(§3.19–3.20) is nibbling the constant, which is all that exists there. The
family's honest home-turf test is structured sources — geometric kNN, grids/
lattices, planted communities (real QUBOs are usually structured) — where
round-0 placement should already be strong and trajectories should descend
hard. If it cannot win *there*, the family is dead; if it wins big, the
result is "structure-aware embedding: matches MM on random, beats it on
structured" — a defensible paper thesis. (The SOTA eval's kNN/BA/d-regular
extensions point the same direction.)

### 3.22 The attraction embedder v3: pure arm refuted on ER, hybrid at parity (2026-07-17)

The placement loop became a registered algorithm (`attraction`;
`factored/placement.py`, tests in `test_attraction.py`). Changes vs the §3.19
prototype: **own initialization** (spectral layout of H scaled into the target
layout; circle fallback for degenerate spectra — no round-0 minorminer call,
no MM basin as anchor), seeded construction via `initial_chains` (now
supported by the factored router: seeds claimed before pass 0), and a
finishing pass. Probe script `data/placement_v3.py`.

**Pure arm** (no minorminer anywhere: native router + region-biased native
shorten, γ=1): ER n=100 → P16: legal 11.80, final 9.84, 403 s — vs stock MM
5.66 in 5.7 s. Two decomposed gaps: (a) construction — our seeded
legalization (11.8) is *worse* than MM's unguided one (~8.5); on an expander
the spectral seeds are noise (§3.21), and the §3.10 fidelity gap compounds;
(b) finishing — region-biased shorten cut 17% where MM's free grind cuts
~37%. **Region-biasing the polish is refuted** (Max's call, confirmed by the
numbers): biasing the *search* hides genuinely shorter rebuilds even though
acceptance was on true length. Principle adopted: *the placement earns its
keep by improving the endpoint of an unconstrained polish, or it wasn't
real.* γ now defaults to 0; the biased arm is kept only as an ablation.

**Hybrid** (per Max: combine the good attraction with the good polish):
geometry + snap as before, but per-round routing = stock MM seeded cheap
legalization (`initial_chains` + `chainlength_patience=0`) and finish =
stock MM warm-started full grind. Same cell: final 6.16 in 5.9 s vs mm-full
5.66 in 5.4 s — one seed, equal wall-clock, inside the ±5% seed band (v1's
paired −0.3 edge needs the 5-seed probe to re-confirm under spectral init).
This is now the registered default; `backend="native", polish="native"` is
the purity arm.

**Source-verified along the way** (the shipped-vs-assumed list grows):
`pathfinder.hpp`'s comment "Dijkstra … is responsible for 99% of our runtime"
describes the *legalization* phase and predates the §3.15 measurement
(legalization ≈ 10% of wall-clock); `find_short_chain` — where the time
actually goes — expands through free qubits at unit weight (`d += 1`), i.e.
lockstep BFS balls, not weighted Dijkstra. A native shortener should use BFS,
not a heap.

**Parked (Max, 2026-07-17):** the binned density field feels wrong —
centroids should perhaps be true real-valued points drifting under a
continuous density repulsion (the ePlace electrostatic direction, §3.18)
rather than receiving one-bin pushes on a 16×16 grid. Suspected relevant to
the n=180 bin-resolution weakness (§3.19). Revisit after the dataset run.

**Reference docs split out** (2026-07-17): organized state now lives in two
sibling files — `mm-internals.md` (source-verified account of shipped minorminer
0.2.22: phases, search primitives incl. the Dijkstra-vs-BFS resolution, cost
table, randomization channels, paper-vs-program deltas, fork hooks) and
`attraction.md` (the attraction embedder: multilevel framing, as-built v3 spec,
idea ledger with confirmed/refuted/parked status, and the pre-registered
predictions for the full-Ember sweep). These notes remain the chronological
record; update the ledger there when a section here settles a question.

**Dataset context, corrected mid-launch** (2026-07-17): the *local*
`test_graphs/` directory (101 graphs, median n ≈ 10, max 121) is only the
offline layer. The full Ember library is the HuggingFace dataset
(`zachmacsmith/ember-graphs`): **31,149 graphs, n from 2 to 65,536, median
192**, of which 24,061 fit Pegasus-16 — thousands of instances in and beyond
the n ≥ 100 regime where the v1 edge was measured, including fabric-filling
sizes. A naive full run (3 trials, 1 worker) is weeks of compute; the first
sweep is therefore `attraction` vs `minorminer`, all P16-eligible graphs,
1 trial (paired by shared seed), 60 s timeout, ~40 workers — expected
hours, not weeks. Note the CLI pre-loads graphs serially before running, so
the library was bulk-prefetched in parallel first.

### 3.23 First full-Ember sweep: structured wins, dense losses, two bugs (2026-07-18)

Completed: `attraction` (hybrid v3) vs stock `minorminer`, 23,642 P16-eligible
graphs paired by shared seed, 60 s, 1 trial, 40 workers
(`results/batch_2026-07-17_20-34-03`; analysis `data/analyze_fullember.py`).
Headline: successes 15,427 (mm) vs 13,986 (att); of paired graphs — both legal
13,590, only-mm 1,837, only-att 396, neither 7,819 (beyond either's reach at
60 s). Pooled paired ΔACL **+0.016** (≈zero), win/loss/tie
**6,481 / 5,995 / 1,114** — attraction wins *more* paired comparisons; the mean
is dragged positive by dense-instance blowouts.

**Two implementation bugs found by the sweep (both fixed and verified same day):**

1. **Isolated-vertex seeding — 1,546 failures, ~all of the success-rate gap.**
   `_mm_route` passed the source as an *edge list*; minorminer then rejects
   `initial_chains` entries for degree-0 vertices ("labels that weren't referred
   to by any edges"). Graph 5550 (n=10, 8 isolated): fail → 0.1 s success. Fix:
   pass the graph object (matching the `minorminer` wrapper, which comments on
   exactly this trap).
2. **Unbounded `spur_prune` on hub-and-spoke sources** — star/wheel hub chains
   (hundreds of qubits) made the quadratic prune blow the whole budget (star
   301-1000 median 838 s vs 60 s cap; wheel ~1,066 s). Fix: `deadline=` param,
   checked per chain (pruning is validity-preserving, early stop always safe).
   Star n=393: 838 → 221 s; residual is MM's own per-pass timeout granularity
   on huge hubs (stock shows the same, e.g. 337 s sudoku run).

**Scorecard vs the §3.22/attraction.md pre-registered predictions:**

1. *Small n ties* — *confirmed* (typical |ΔACL| ≤ 0.01, tie-heavy).
2. *Structured mid-size wins* — **confirmed, stronger and at larger sizes than
   predicted**: regular 301-1000 **−0.755** (82W/5L); planted_solution 301-1000
   **−0.497** (512/188) *plus net feasibility +154* (only-att 215 vs only-mm
   61); watts_strogatz 301-1000 −0.210 (434/258); lattices sweep it at scale —
   bcc −0.527 (6/0), cubic 301-1000 −0.398 (10/3), honeycomb n>1000 −0.432
   (11/0), shastry_sutherland n>1000 (9/0), hardware_native 101-300 −0.416.
3. *Mid ER parity-to-slight-loss* — worse than predicted at the congested band
   (101-300: **+1.24**); small ER parity. Consistent with the unvalidated v3
   regressions (§3.22) — the cadence/rounds ablation just got more urgent.
4. *Dense blunted to parity* — **too optimistic: clear losses.** complete
   101-300 **+8.2**, turán +4.1, dense bipartite +4.0, spin_glass +2.0, kneser
   +1.3, weak_strong_cluster +0.3–0.5 at every size. The density-field plateau
   problem is now the top *algorithmic* defect (roadmap items 5–6).
5. *Hard-tail success deficit* — confirmed in raw numbers but ~fully explained
   by bug 1; **and inverted at 301-1000**, where seeding delivers net
   feasibility wins (only-att 396, concentrated there — geometry is a
   feasibility mechanism at scale, echoing §3.9's diversity observation from
   the other side).

Net reading: placement helps exactly where the theory said it should (structured
sources, larger n — the first broad, external confirmation of the family
thesis), is neutral where nothing is winnable (small/random), and loses where
its known cartoons bind (dense = monopole + plateau; congested mid-ER = v3
regressions). Wall-clock ~2–4× stock typical (3 legalizations + polish).
Pending: re-sweep of the bug-affected subset; then roadmap order stands —
budget/selection/cadence fixes, then the field redesign.

### 3.24 v3.1 plumbing: trust-region cadence, budget reserve, selection, attribution (2026-07-18)

Design round following the §3.23 postmortem discussions with Max; changes only,
no measurement claims (the paired cadence ablation is still owed). All prior
behavior reachable via config for one-flip experiments.

- **Trust-region cadence**: `geo_iters` 10 → 1. The insight (from the "why does
  over-solving the coarse problem *hurt*?" discussion): the coarse model's
  calibration data (λ, realized centroids) comes from the fine level, so it is a
  *local* proxy valid near the last realized embedding — running it to its
  fixpoint both optimizes fictions (trust-region violation; over-optimizing a
  misaligned proxy harms, unlike exact-vs-SGD gradients on a shared objective)
  and erases the router's feedback (fixpoints forget initial conditions). v1's
  one-step cadence was unknowingly trust-region-correct.
- **Adaptive rounds under a budget**: fixed `outer_rounds=3` → `max_rounds=10`
  bounded by `round_frac=0.4` of the timeout; polish reserve falls out by
  construction; **uncapped feasibility fallback** when no round legalizes
  (degradation mode = spectral-seeded stock MM, the §3.23 net feasibility
  winner). Verified on a neither-bucket WS instance: 61.5 s vs 60 s budget.
- **Selection**: default best-legal-round → **last round** (trajectory
  endpoint); `best_legal` kept as ablation arm. Note §3.16's null was measured
  on unsteered i.i.d. ER basins; steered+structured is open. Every run now
  returns `round_acls` (per-round legal ACL) as a free rank-stability
  diagnostic.
- **Attribution switch**: `vary_rng=False` freezes the router RNG across rounds
  so only geometry varies — un-confounding steering from re-rolling (each round
  previously changed both seeds and geometry simultaneously; the §3.18 control
  handled this at experiment level only). Failed rounds still re-roll.

Directional single-seed check (not a claim): ER n=100 → P16 final ACL
6.16 (v3) → **5.96** (v3.1), v1 mean ≈ 5.95, stock mm 5.66; rounds 3 → 10 at
comparable wall-clock. 49 tests pass (5 new). Next: the VLSI round — tile-graph
coarse target, route-smeared charges, hinge²+μ Poisson field (attraction.md
roadmap 4–6, field design settled in the ledger).

### 3.25 The VLSI round: typed tiles + smeared demand + Poisson field — new default (2026-07-18)

Built per the settled design (attraction.md roadmap 4–6 with Max's corrections):
`factored/field.py` — **TileGrid** (per-family typed tile capacities from dnx
coordinates: chimera (i,j,u,k), pegasus nice (t,y,x,u,k) with t merged;
per-tile (vertical, horizontal) wire pools measured from working qubits; affine
drawing↔tile map; untyped drawing-bin fallback incl. zephyr), **segment-smeared
deposits** [`spindler2007rudy`] (each variable's λ along straight half-segments
toward neighbours, mass split h/v by direction — traversal charging, the fix
for the point-deposit field's blindness to §3.21's cut constraint), and
**PoissonField** [`lu2015eplace`] (one-sided source `hinge_w·relu(ρ−cap)² + μ`,
`μ ← max(0, μ + α_μ(ρ−cap))` once per router round; Neumann pseudo-inverse
solve; forces trust-region-clipped at 1 tile). λ updates damped
(`lam_tau=0.5`). All switchable; `field="push"` = v3.1 control arm.

**Field probe** (`data/field_probe.py` / `.csv`; 3 seeds, P16, 60 s; cells from
§3.23's verdict classes; pre-registered rule: poisson becomes default iff the
dense cell improves and the win cells don't regress):

| cell | push | poisson | mm-full |
|---|---|---|---|
| K100 (dense loss) | 15.83 | **14.50** | 13.44 |
| ER100 d10 (parity) | 5.89 | **5.70** | 5.67 |
| regular_n316 (win guard) | 3.54 | **3.50** | 4.02 |
| ws_n486 (win guard) | 3.45 | **3.11** | 3.89 |

Rule satisfied on all four → **poisson is the registered default**. Readings:
the dense gap to stock halves (2.4 → 1.1 ACL) but does not close — monopole
shape (anisotropy, multi-qubit seeds) and/or the coarse solver remain the
residual; the ws win *widens* (−0.34); ER reaches statistical parity with
stock (probe mean 5.70 vs 5.67; the standard n=100 cell now reads 5.57 vs
5.66 on seed 0). **First data on Max's stale-shadow-price prediction**: at run
end 32–60% of μ-mass sits on currently-slack tiles (`field_diag.mu_stale_frac`)
— staleness is real; whether it costs anything is unmeasured (hinge²-only
`mu_alpha=0` ablation owed, alongside the cadence ablation). 472 tests pass
(15 new for the field).

### 3.26 Dense attribution: every search method is 30-60% above the constructive ceiling (2026-07-19)

Probe `data/dense_attrib.py` (`.csv`), pre-registered decision tree; K60/K100/
K140 clique ladder + bipartite_K48_96, P16, 60 s, 3 seeds:

| cell | template-raw | template+polish | poisson | budget | mm-full |
|---|---|---|---|---|---|
| K60 | 6.73 | 6.70 | 8.76 | 8.27 | 7.83 |
| K100 | 9.78 | 9.78 | 14.55 | 13.76 | 13.62 |
| K140 | 13.17 | 13.17 | **fail 0/3** | 25.16 | 20.72 |
| biK48_96 | 6.21 | 6.17 | 8.39 | 8.36 | 6.68 |

(`template` = busclique K_n chains restricted to the source's edges +
spur-prune; `budget` = attraction `max_rounds=1, round_frac=0.1`, i.e. seeded
mm with a full-length polish.)

Findings, in order of importance:

1. **The constructive template dominates every search method, including stock
   minorminer, by 15-57%** (K100: mm 39% above it; K140: 57%). And MM's full
   grind **cannot improve the template at all** (dACL <= 0.04 in 3-42 s of
   polishing): the crossbar is a local optimum of the chain-local move set --
   the s3.9 joint-move blindness measured from the other side. Consequence:
   the dense game is not "close a 1.1 gap to mm"; mm itself is far from the
   ceiling, and whoever adopts a **template prior** wins dense outright. A
   template IS a placement -- this slots natively into the attraction layer
   (recognize density -> constructive prior -> restrict -> brief polish), and
   s3.21 already measured the sparse side of the crossover (template terrible
   at ER deg-10), so a best-of-both arm needs no density threshold: evaluate
   both, keep the better (template evaluation is ~free).
2. **The s3.25 K100 gap was mostly budget split**: `budget` 13.76 vs mm 13.62
   (residual 0.14 vs 1.1 for the default). At comfortable dense sizes the
   geometry wasn't the problem; the rounds' clock was.
3. **But near the cliff the seeds actively hurt**: K140 `budget` 25.16 vs mm
   20.72, and the default pipeline **fails outright** (rounds + fallback
   exhaust 60 s without legalizing an instance mm solves) -- the s3.10
   anti-placement effect is real for dense sources: disk seeding fights the
   extended-bar structure the router needs to build. biK48_96 confirms
   geometry (not budget) as the culprit there too (budget ~ poisson >> mm).
4. Together with s3.25: the field fixed what a field can fix (plateau); the
   remaining dense deficit is **representational** (point-state cannot express
   bars) -- and the template result shows the payoff for fixing it is much
   larger than parity: 30-60% over stock MM. Next build: the template arm.

### 3.27 The two ablations: mu inert, cadence a wash, steering suffices (2026-07-19)

`data/ablations_mu_cadence.py` (`.csv`): 7 arms x 4 cells x 5 seeds, P16, 60 s.
Mean final ACL:

| cell | default (hinge2+mu) | mu0 | hinge0 | geo10 | geo1_frozen | geo10_frozen | mm-full |
|---|---|---|---|---|---|---|---|
| K100 | 14.69 | 14.53 | 15.27 | 14.77 | 14.97 | 14.99 | 12.69 |
| ER100 | 5.76 | 5.72 | 5.84 | 5.82 | 5.70 | 5.78 | 5.74 |
| regular_n316 | 3.50 | 3.49 | 3.44 | 3.51 | 3.62 | 3.43 | 4.08 |
| ws_n486 | 3.13 | 3.26 | 3.33 | 3.15 | 3.38 | 3.06 | 3.87 |

1. **mu is inert.** hinge2-only (mu0) is within noise of hinge2+mu on every
   cell despite 30-60% stale mu-mass (s3.25) -- Max's staleness is real but
   harmless AND the memory earns nothing. The s3.13 pattern a second time: a
   memory mechanism is inert when another mechanism (here the hinge2 present
   term with per-round fresh calibration) already covers its job. Default
   flipped to `mu_alpha=0` by parsimony (the s3.20 precedent); mu stays as a
   knob. mu-only (hinge0) is mildly worse on 3/4 cells: the present term is
   the load-bearing one.
2. **Cadence is a wash under the poisson field** (geo10 vs default within
   noise everywhere). The v3 over-solving regression (s3.24's trust-region
   story) does NOT reproduce with the new field -- it was either specific to
   the discontinuous push field or partly noise in the original single-seed
   probe. The trust-region *theory* stands (and the field's 1-tile clip
   embodies it); the measured claim is hereby softened: with a smooth,
   one-sided, damped field, deeper coarse iteration neither helps nor hurts.
   `geo_iters=1` stays default (cheaper, no downside).
3. **Steering alone suffices** (the attribution arms): frozen-RNG
   trajectories -- rounds differing ONLY by geometry -- reach parity with
   vary-RNG (geo10_frozen is even the best arm on both win-guard cells:
   3.43 / 3.06). Trajectory gains are attributable to the geometry, not to
   re-rolling. The v1-era question "is the loop just fancy restarts?" is
   answered: no.
4. Caveat for all K100 comparisons: mm-full variance on K100 is large
   (12.69 five-seed mean here vs 13.44/13.62 on the 3-seed probes); dense
   conclusions should lean on s3.26's template result, which dwarfs this
   variance, not on ~1-ACL search-vs-search deltas.

### 3.28 Extent-state v1: bars emerge at the right scale; the assignment doesn't (2026-07-19)

Option A built (`field.py` CrossState: contact-deficit descent whose zero-extent
limit is exactly L1 point attraction; own-bar typed deposits; measured-extent
feedback; `seed_mode="bars"` multi-qubit seeds as the separate s3.10-risk
switch). 482 tests pass. Probe `data/extent_probe.py` (`.csv`), 3 seeds,
pre-registered bar: K100 <= ~11.2, no guard regression, no K140 failure.

| cell | point | cross | cross-bars | mm-full | (template s3.26) |
|---|---|---|---|---|---|
| K100 | 14.30 | 15.28 | 14.69 | 13.44 | 9.78 |
| K140 | fail | fail | **24.15 (2/3)** | 20.72 | 13.17 |
| ER100 | 5.65 | 6.23 | 5.65 | 5.67 | -- |
| regular_n316 | 3.54 | 3.45 | **3.42** | 4.02 | -- |
| ws_n486 | 3.26 | 3.23 | 3.31 | 3.89 | -- |

**Verdict: the pre-registered bar FAILED; default stays `state="point"`.**
What the diagnostics salvage from the failure -- three findings:

1. **The representation works: bars of crossbar scale genuinely emerge.**
   K100 extent_mean 11.7-12.7 tiles (template bars ~10-15). Contact demand +
   capacity pressure grow the right shapes, and the sparse limit is safe
   (guards fine; cross-bars == point on ER; cross slightly *best* on
   regular_n316).
2. **What fails is the ASSIGNMENT, not the shape**: max_violation 14-25 at
   equilibrium -- everyone's bars want the same central rows/columns and
   gradient flow settles into an oversubscribed smear instead of the
   1-bar-per-row lattice. The crossbar's remaining content is a
   *permutation* (which row/column each variable owns), and continuous
   dynamics cannot break that combinatorial symmetry -- the s3.9 deadlock
   phenomenon, now at the coarse level. Identified cheap candidate fix
   (v2, unbuilt): a discrete assignment step -- rank-order bars by current
   position and assign distinct rows/columns by argsort (or a small
   matching), then let the field/contact dynamics polish around the broken
   symmetry.
3. **Bar seeds carry real feasibility signal**: cross-bars is the ONLY arm
   that legalizes K140 at all (2/3, vs 0/3 for both point-seeded arms) --
   transmitting shape to the router does exactly what s3.26's anti-placement
   diagnosis predicted it would. The s3.10 caution (multi-qubit seeds hurt)
   is refuted in the dense regime, unproven elsewhere.

### 3.29 Extent-state v2: assignment and attraction fight; bar failed again, K140 regressed (2026-07-19)

v2 added the two s3.28-diagnosed fixes: tip-potential field-bar coupling
(translation = bar-averaged gradient; extent force = -psi at tips) and the
per-round rank-order assignment (distinct integer rows/columns,
capacity-many per line). 482 tests pass; K20 smoke max_violation 3.22 -> 0.16
(tip coupling works locally). Probe `data/extent_probe_v2.py` (`.csv`), same
pre-registered bar:

| cell | point | cross-v1 | cross2 | cross2-bars | mm-full |
|---|---|---|---|---|---|
| K100 | 14.30 | 15.23 | 14.94 | 15.98 | 13.44 |
| K140 | fail | fail | fail | **fail (v1 bars: 2/3)** | 20.72 |
| ER100 | 5.65 | 5.88 | 5.61 | 5.61 | 5.67 |
| regular_n316 | 3.54 | 3.46 | 3.72 | 3.40 | 4.02 |
| ws_n486 | 3.26 | 3.22 | 3.25 | 3.46 | 3.89 |

**Bar FAILED (0-for-2 for the emergence program); defaults unchanged; and the
bars arm REGRESSED on K140 feasibility (2/3 -> 0/3).** Guards unharmed (the
sparse regime remains untouched by all of this). Diagnosis from the
diagnostics (K100 cross2: assigned=100, yet max_violation 25, extent_mean
10.4):

1. **Assignment and attraction fight each round with no fixpoint.** The loop
   is contact-attract (re-stacks bars) -> deposit -> field -> assign
   (un-stacks) -> route; next round attraction undoes the assignment again.
   The crossbar is a fixed point of the assignment but NOT of the composed
   dynamics -- assigned coordinates would need to be *pinned* (attraction
   projected along-bar for assigned variables) for the lattice to persist.
   Also an ordering artifact: deposits (hence field + violation diagnostics)
   sample the pre-assignment stacked configuration.
2. **Row packing at 100% of pool capacity starves routing slack** (per_row =
   floor(mean h-pool) ~ 12 bars/row = exactly full): the K140 bar seeds land
   on wire-saturated rows and the router cannot legalize around them --
   explains the feasibility regression vs v1's unassigned (looser) bars.
3. ACL: every cross arm ~ point (14.3-16.0) vs bar 11.2. Two design
   iterations have not moved dense ACL at all; the binding constraint is
   evidently not what each iteration fixed.

Options recorded for Max (build stopped pending direction): (a) v3 = pin
assigned coordinates + pack rows at ~60% + post-assign re-deposit -- risks
the complexity spiral Max pre-warned about ("lost the plot irrecoverably");
(b) concede the dense regime to the template arm (parity with existing
D-Wave practice, the "ugly" option); (c) park dense and run the
hard-frontier eval (s"Strategic emphasis": success-vs-budget on the s3.23
neither-bucket) where the algorithm already holds its only unambiguous wins.

### 3.30 The missing physics: contact capacity (2026-07-19/20, in progress)

Max's directive after the v2 failure: dense and random graphs are the regime
that matters (structured wins are replaceable by specialized methods; we are
a heavy replacement for the heavy fallback); and his hypothesis: the crosses
cannot MOVE properly -- "we're evolving them sloppily."

Router-free diagnostic (evolving the coarse dynamics with no router, no
polish -- a testbed we should have built two iterations ago): the current
cross dynamics on K100 collapses to ONE row, ZERO extents, and near-zero
violation. **The coarse model's global minimum for a clique is total
collapse, and collapse is FEASIBLE in the model** -- 100 coincident
point-variables deposit 100 units into a fabric holding 5,640, all contact
deficits are zero at distance zero, and nothing objects. Root cause: the
model prices qubit occupancy and wire occupancy but **never prices contact
itself**. In reality a chain of L qubits hosts at most ~kappa*L
neighbour-contacts (kappa ~ 13 usable couplers/qubit on Pegasus -- the
degree-counting bound of s3.26, ACL >= (n-1)/kappa). v1/v2 bars only grew
for REACH; the actual reason crossbar bars are long is CONTACT HOSTING.
Two design iterations built spreading machinery on an energy landscape whose
minimum was collapse.

Fix: **extent floor** 1 + w + h >= deg(v)/kappa (contact capacity imported
as a constraint). Testbed-confirmed: collapse becomes infeasible (violation
jumps from ~0 to ~240 at the collapsed state; extents grow to the floor).
Two remaining TRANSIENT pathologies, both order-of-forces problems:
(a) chicken-and-egg valley -- spreading requires longer bars, bars only grow
under deficits that appear after spreading; from a compact start gradient
flow cannot find the coordinated valley; (b) **tip-retraction chokes
reach-growth**: during the over-capacity transient the whole region has high
psi, tips retract before bars can grow to reach distant partners, growth
pins at the floor, unresolved deficits re-collapse the spread (confirmed:
spread init re-collapses to row_spread 2.9). Forces individually correct;
their ORDER through the transient is the open problem -- the standard remedy
is an annealing schedule (ePlace's ramp exists for exactly this).

Testbed built (`data/crossbar_testbed.py`): router-free K_n schedule sweep
(all-on / grow-first / three-phase / ramped / no-retract / strong-field, x
compact/spread inits). Running; results decide the v3 schedule before
anything touches the pipeline. Methodology note: testing coarse dynamics
through the full pipeline+router+polish was an attribution disaster -- the
router-free testbed is how every future force-law change gets validated
first.

### 3.30 (concluded) Emergent crossbar reaches MM parity; the residual gap is constructive fine detail (2026-07-20)

Continuation of the s3.30 program, all in the router-free testbed
(`crossbar_testbed.py` + inline probes):

1. **Schedule sweep (12 variants)**: ALL converge to the same blob attractor
   (viol ~240, spread ~3) -- not an ordering problem. Derived cause: at that
   state every force is balanced (bar-averaged field force cancels BY
   SYMMETRY on blob-spanning bars; deficits vanish at floor-scale spread;
   rent pins extents at the floor). A genuine constrained local minimum.
2. **Floor + assignment are complementary**: assignment forces spread ->
   spread creates deficits -> deficits justify growth -> growth stabilizes
   the assignment. Jointly: viol 240 -> ~150, rows 2 -> 6; the S7 parameter
   sweep (24 combos; assignment cadence x growth x rent x retract) found
   genuine coarse crossbars (11 rows, extents ~11, spread ~10) at
   ak=5, ee=0.4, ec=0.03, ew=0.2 with 65%-derated capacity.
3. **The sub-tile last mile**: routed ACL from coarse-crossbar seeds was
   ~14.3 because bar_seeds picked nearest qubits per tile with NO WIRE
   CONTINUITY (adjacent tiles' seeds on uncoupled wires -> router stitching
   inflation). Fix: `wire_seeds` -- per (row, orientation) interval-graph
   coloring (greedy left-endpoint sweep, exact for intervals) assigns each
   bar ONE physical wire; seeds become contiguous coupled runs. TileGrid now
   carries sub-wire indices ((t,k) for pegasus nice) and a wire lookup.
4. **Result: K100 emergent-crossbar pipeline = 13.46 polished** (stock mm
   13.62, previous best arm 13.57, template 9.78). MM parity achieved by the
   emergent route for the first time; the template remains 3.7 ahead. Gap
   decomposition from seed stats (chains 9-18, mean 11.9): (a) region
   oversize -- the 65%-derated assignment spreads over ~13 rows vs
   busclique's tighter packing (bars ~12 vs ~10); (b) cross-orientation
   colors chosen independently -- h-run and v-run may land on different
   t-shifts whose wires are NOT intra-tile coupled at the crossing, costing
   bridge qubits; (c) MM's polish cannot compress crossbars (s3.26), so
   seed-level inflation is permanent.

Reading: the coarse-to-fine refinement of an emergent crossbar is
CONVERGING toward busclique's construction layer by layer -- expected: on
pure cliques busclique is near-optimal and emergence can at best tie it.
**The value regime for the emergent route is irregular dense** -- graphs
where per-variable degree varies (the floor is per-variable: deg_v/kappa!)
and K_n template restriction overpays (spin_glass 101-300, turan, dense
bipartite -- the s3.23 loss cells). Next: (i) t-coordinated coloring +
tighter packing (constructive detail); (ii) wire v3 (floor + assignment +
wire_seeds) into the pipeline behind switches; (iii) probe on the
IRREGULAR-dense cells where neither mm nor template is the right answer.
Methodology: the router-free testbed reduced iteration from ~40 min probes
to ~10 s simulations -- every force-law change validates there first.

### 3.31 Span state: extents demoted to a readout — bar failed at K100, the cliff opens (2026-07-23)

Design settled in discussion (Max: "is there a way to capture the properties
we want with minimal complexity?"): the s3.28-3.30 machinery evolved extents
under fictional forces, but **extents were never legitimate state** — any
embedding of v owes bars spanning its neighbours' coordinates, so extents
are a deterministic READOUT of positions. State = one (x, y) per variable;
h-bar = x-interval of N[v]+v at row y_v (contact for (u,v) at (x_u, y_v),
inside both bars by construction); energy `E = sum_v [xspan + yspan]` = the
implied embedding's total bar length — VLSI HPWL, one net per closed
neighbourhood. Chain length IS the objective, not a simulated quantity.
Dynamics keep the v2 shape (Max: no annealing): HPWL-subgradient attraction,
Poisson field on EXACT implied-bar deposits (RUDY smear obsolete in this
state), argsort assignment as projection of the same energy. Deleted:
extent ODEs, tip retraction, lambda/chain_len feedback (no measured-length
calibration exists — the charge-feedback instability channel is gone),
fit_extents. Collapse is infeasible in-model (stacked variables still
deposit 1+w+h; the pool overfills); the deg/kappa floor survives as a
readout clamp; assignment participation is capacity-gated (only
deg/kappa-1 > 0 variables enter the sort — sparse sources structurally
untouched). Built behind `state="span"` (default unchanged); `seed_mode=
"wire"` finally wires s3.30's interval coloring into the pipeline
(roadmap item (ii)); +10 tests incl. the previously-untested wire_seeds.

**Router-free testbed (24 combos, ZERO schedules; span_sweep_k100.log):**
dynamics insensitive to eta and threshold — identical outcomes across both
axes; only assignment cadence and capacity derate matter. The no-knob-zoo
property is real. Stock capacity converges to a 10-row crossbar (viol~2)
but routes at 15.16; the 0.65-derated 14-row config routes at **13.15**
(ak=5) — 100%-packed rows starve routing slack, s3.29's lesson re-measured
from the clean side. Gate (<= 13.46) PASSED, untuned.

**Pre-registered probe (span_probe.py / .csv; 3 seeds, 60 s; bar: K100 <=
13.46 near-default, biK48 beats point, guards hold, K140 feasibility >=
point):**

| cell | point | span | span-tb | cross | mm-full |
|---|---|---|---|---|---|
| K100 | 14.30 | 14.47 | 15.11 | 14.80 | 13.44 |
| K140 | fail | fail | **21.84 (3/3)** | fail | 20.70 |
| biK48_96 | 8.20 | 9.34 | **8.01** | 9.20 | 6.68 |
| ER100_d10 | 5.65 | 5.66 | 6.09 | 5.61 | 5.67 |
| regular_n316 | 3.54 | 3.66 | **3.44** | 3.72 | 4.02 |
| ws_n486 | 3.26 | 3.37 | **3.12** | 3.25 | 3.89 |

(span = state flip alone, defaults; span-tb = testbed-decided arm: wire
seeds + geo_iters=30 + cap_derate=0.65 + assign_every=5, recorded before
the run.)

**Verdict: the K100 bar FAILED (15.11 / one-shot 13.96 vs 13.46) — the
emergence program is 0-for-3 on dense ACL bars; defaults unchanged.**
Findings, in decreasing order of importance:

1. **The cliff opens: span-tb is the only search arm that legalizes K140 at
   all — 3/3** (mean 21.84, best seed 20.74 ~ mm 20.70), vs 0/3 for point,
   span-default, AND cross, all of which fail outright. The s3.26
   anti-placement failure (seeds actively hurting near the cliff) is fixed
   by derived bars + wire-coherent seeds. This is the hard-frontier regime
   the strategic emphasis declared the one that matters; the span arm is
   the first steered configuration that reaches the cliff without hurting
   feasibility.
2. **The coarse layer is exonerated; the residual dense gap is transfer
   economics.** In-pipeline the coarse state converges to testbed grade
   (max_violation ~2.4), yet routes at 15.11. Attribution (existing
   switches only, span_oneshot.log): converge-once-then-route-once
   (geo_iters=300, max_rounds=1) gives **13.96** — the interleaved round
   loop costs ~1.1 ACL on K100 (re-centroid feedback overwrites the coarse
   trajectory each round; budget splits). Residual ~0.8 vs the testbed's
   13.15 = init (spectral/circle vs compact) + polish-budget split.
   Notably K140 prefers the OPPOSITE protocol (one-shot 23.9 vs rounds
   21.8): comfortable-dense wants converge-then-route, at-the-cliff wants
   feedback rounds.
3. **Guards: span-tb sweeps both win-guard cells** (3.44 / 3.12 vs point's
   3.54 / 3.26) and takes biK48_96 (8.01 vs 8.20) — capacity-gated
   assignment leaves sparse dynamics untouched by construction (probe
   diag: assigned=0 on all guard cells). One regression: span-tb ER100
   +0.44 (derate + depth on the parity cell); span-defaults hold parity
   there (5.66 vs 5.65).
4. **Span dominates cross on every measured cell with strictly fewer
   knobs** (K100 14.47 vs 14.80; biK48 8.01 vs 9.20; K140 3/3 vs 0/3;
   guards <=). The cross arm is now a dominated configuration whose only
   remaining role is historical comparison — deletion is Max's call (the
   2026-07-23 protocol said "delete after span wins"; span beat cross
   everywhere but missed the dense bar).

Options recorded for Max: (a) keep dense-ACL status quo, adopt the span
pieces where they win (wire seeds, capacity gating, the K140 feasibility
result feeds the hard-frontier eval directly); (b) build the dense
one-shot path properly (converge-then-route as a first-class mode with
testbed-style budgeting — the 13.96->13.15 residual says ~0.8 more is
available, still shy of the bar); (c) concede dense ACL to the template
arm (9.78, untouched by every search method all program).

## 4. References

Numbered here; BibTeX in `refs.bib` (keys in brackets).

1. Cai, Macready, Roy (2014). *A Practical Heuristic for Finding Graph Minors.*
   arXiv:1406.2741. — minorminer; the `D^occ` cost and the open initial-placement
   problem. [`cai2014minorminer`]
2. McMurchie, Ebeling (1995). *PathFinder: A Negotiation-Based Performance-Driven Router
   for FPGAs.* FPGA '95. — negotiated congestion; `(b+h)·p`; no convergence claim.
   [`mcmurchie1995pathfinder`]
3. Awerbuch, Azar, Plotkin (1993). *Throughput-Competitive On-Line Routing.* FOCS '93. —
   exponential-in-load pricing, O(log n)-competitive congestion. [`awerbuch1993online`]
4. Raghavan, Thompson (1987). *Randomized Rounding.* Combinatorica 7(4). — exponential
   potential in provable congestion minimization. [`raghavan1987rounding`]
5. Räcke (2002). *Minimizing Congestion in General Networks.* FOCS '02. — exponential
   congestion potentials in general networks. [`racke2002congestion`]
6. Betz, Rose (1997). *VPR: A New Packing, Placement and Routing Tool for FPGA Research.*
   FPL '97; and the VTR documentation (`docs.verilogtorouting.org`) for the modern cost
   parameterization (`pres_fac`, `acc_fac`, `max_pres_fac`). [`betz1997vpr`, `vtrdocs`]
7. Murray et al. (2020). *VTR 8: High-Performance CAD and Customizable FPGA Architecture
   Modelling.* ACM TRETS. — current reference implementation of negotiated congestion.
   [`murray2020vtr8`]
8. Hoo, Kumar, Ha (2015). *ParaLaR: A Parallel FPGA Router Based on Lagrangian
   Relaxation.* FPL '15. — FPGA routing as LP with relaxed capacity constraints;
   multipliers ≈ history. [`hoo2015paralar`]
9. Agrawal, Ahuja, et al. (2019). *ParaLarPD: Parallel FPGA Router Using Primal-Dual
   Sub-Gradient Method.* Electronics 8(12):1439. — the subgradient multiplier update we
   adopt for history. [`paralarpd2019`]
10. Takahashi, Matsuyama (1980). *An Approximate Solution for the Steiner Problem in
    Graphs.* Math. Japonica 24. — the SPH tree-construction heuristic.
    [`takahashi1980sph`]
11. Mehlhorn (1988). *A Faster Approximation Algorithm for the Steiner Problem in
    Graphs.* IPL 27(3). — Steiner approximation context. [`mehlhorn1988steiner`]
12. Cuthill, McKee (1969). *Reducing the Bandwidth of Sparse Symmetric Matrices.* ACM '69.
    — the bandwidth-reducing vertex order. [`cuthill1969bandwidth`]
13. Benchoff. *OrthoRoute — GPU-accelerated PCB autorouting* (web,
    `bbenchoff.com/pages/OrthoRoute.html`, accessed 2026-07-10). — practitioner
    documentation of blanket-decay oscillation and pres_fac capping in a PathFinder
    implementation. [`benchoff2025orthoroute`]
14. Gómez-Tejedor, Osaba, Villar-Rodriguez (2025). *Addressing the Minor-Embedding
    Problem in Quantum Annealing and Evaluating State-of-the-Art Algorithm Performance.*
    arXiv:2504.13376. — evaluation protocol and MM failure modes. [`gomez2025eval`]
15. Spindler, Johannes (2007). *Fast and Accurate Routing Demand Estimation for
    Efficient Routability-driven Placement.* DATE '07. — RUDY: segment/rect-smeared
    routing demand; the deposit model of `field.py`. [`spindler2007rudy`]
16. Lu, Chen, Chang, Sha, Huang, Teng, Cheng (2015). *ePlace: Electrostatics-Based
    Placement Using FFT and Nesterov's Method.* ACM TODAES 20(2). — charges +
    Poisson-solved density potential; the field architecture attraction.md adapts
    (one-sided source is our departure). [`lu2015eplace`]
17. Cheng, Kahng, Kang, Wang (2019). *RePlAce.* IEEE TCAD 38(9). — ePlace line's
    current reference implementation. [`cheng2019replace`]
18. Eisenmann, Johannes (1998). *Generic Global Placement and Floorplanning.*
    DAC '98. — force-directed spreading precursor. [`eisenmann1998force`]
19. Karypis, Aggarwal, Kumar, Shekhar (1999). *Multilevel Hypergraph Partitioning:
    Applications in VLSI Domain.* IEEE TVLSI 7(1). — the multilevel
    coarsen-solve-refine paradigm behind the tile-grid framing. [`karypis1999hmetis`]
20. Garg, Könemann (1998). *Faster and Simpler Algorithms for Multicommodity Flow.*
    FOCS '98. — fractional MCF via multiplicative weights; the principled-solver
    option for the coarse routing subproblem. [`garg1998mcf`]
21. Müller, Radke, Vygen (2011). *Faster Min-Max Resource Sharing in Theory and
    Practice.* Math. Prog. Computation 3. — BonnRoute's shipped fractional-MCF
    global routing. [`mueller2011resource`]
22. Nocedal, Wright (2006). *Numerical Optimization*, 2nd ed. — trust-region
    methods; the cadence rationale of §3.24. [`nocedal2006numopt`]
