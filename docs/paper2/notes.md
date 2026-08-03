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

### 3.32 Product mode: alternation replaces the field; first ACL win over MM, at the cliff (2026-07-27)

Built per the three discussion outcomes (Max: "let's build some of this"):
**(1) alternating 1-D arrangement** — the product-topology framing made
operational. `alternate_arrange` (field.py): capacity-forced variables are
packed into integer rows (columns frozen; every h-interval is then a fixed
1-D interval and rows are exact interval packing, capacity = overlap DEPTH
per line — the wire *coloring* disappears from the algorithm, only the
clique-number test remains) alternating with columns; iteration 0 is the
unconditional feasibility projection, later half-steps accept only if span
energy does not increase (monotone coordinate descent on the s3.31 E).
Pipeline knob `span_dynamics="arrange"`: span_step + alternation, NO field
calls. **(2) domains handoff** — `bar_domains` builds per-variable
cross-region domains for minorminer's `restrict_chains` (shape as a
constraint, MM keeps all sub-tile identity choices). **(3) swap
contingency** — Metropolis swaps along permutation directions only,
default OFF. +4 tests (502 pass).

**Upstream bug found (report to dwavesystems):** stock minorminer 0.2.22
with `restrict_chains` + `initial_chains` on the same variable HANGS
indefinitely, ignoring its own timeout (repro: K20 -> P6, margin-1 domains,
90+ s against timeout=5; restrict alone returns in 0.0 s; disjoint
initial/restrict variable sets are safe). Parallel testing also hit
segfaults with non-trivial domains in other configurations. The domains
handoff is therefore PARKED behind a hard error (`seed_mode="domains"`
raises), `bar_domains` tested and ready, pending a fork-level fix.

**Router-free testbed (arrange_sweep_k100.log):** the alternation is a
dramatically better OPTIMIZER — converges in 2 iterations / ~0 s to the
states the field dynamics needs 300 steps / ~20 s to find, with exact
feasibility (viol=0 at derate 1.0 AND 0.85; the field never got below ~2 at
stock) and zero schedule knobs. But its routed finalists all miss the
field's mark: best 14.22 (derate 0.65) vs field-span 13.15 — the
pre-registered testbed keep-alive (<= 13.46) FAILED. Third independent
measurement of the E-vs-routability wedge: minimum implied qubit mass at a
given derate is NOT the router's preferred operating point; slack beats
tightness (10 rows E=1800 -> 15.08; 12 rows E=2200 -> 18.14(!); 16 rows
E=2900 -> 14.22). Swap sweeps: E-neutral on K_n exactly as the symmetry
argument predicted (2200 -> 2200); contingency stays off.

**Pipeline mini-probe (arrange_probe.csv; K100/K140/ws_n486, 3 seeds, 60 s;
baselines from span_probe.csv, same seeds):**

| cell | point | span-tb | mm-full | arrange | arrange-1shot |
|---|---|---|---|---|---|
| K100 | 14.30 | 15.11 | 13.44 | 14.60 | 15.86 |
| K140 | fail | 21.84 (3/3) | 20.70 | **20.45 (3/3)** | **19.69 (3/3)** |
| ws_n486 | 3.26 | 3.12 | 3.89 | 3.41 | 3.88 |

(arrange = span + arrange dynamics + wire seeds, rounds as usual;
arrange-1shot = same, max_rounds=1, round_frac=0.5.)

Findings:

1. **K140: first ACL win over stock minorminer on a dense cell, ever, in
   this program — arrange-1shot 19.69 (seeds 19.88/19.31/19.88) and
   arrange 20.45, both under mm's 20.70, both 3/3 legal** (point and cross
   still fail 0/3). The cliff — the regime the strategic emphasis declared
   decisive — is now held by the product-mode configuration: alternation
   places, wire seeds transmit, MM legalizes and polishes. The s3.31
   feasibility parity (span-tb 21.84) is upgraded to an outright win.
2. **K100 stays unbeaten** (arrange 14.60: better than span-tb 15.11 and
   cross 14.80, behind point 14.30, mm 13.44, and the field one-shot
   13.96). The 13.46 bar remains standing against every pipeline
   configuration. Comfortable-dense and at-the-cliff keep preferring
   opposite protocols, and the preference INVERTED between dynamics
   (field: 1shot better at K100, rounds better at K140; arrange: the
   reverse) — n=3, recorded as an open pattern, not a theory.
3. **Guard: ws_n486 arrange 3.41** ~ the s3.31 span-default 3.37 (the
   alternation is inert on sparse by capacity gating, as designed; the
   +0.15 vs point is the standing span-arm offset, not an arrange
   regression). arrange-1shot 3.88 is expected-bad on sparse (rounds do
   the work there) and is not a default-candidate arm.
4. **Wall-clock:** arrange rounds cost ~0 s of geometry; K140 runs finish
   in 29-61 s vs span-tb's routinely exhausted budget — the win at the
   cliff comes with budget to spare (1shot used ~30 s of 60).

Verdict vs pre-registration: K140 gate PASSED and exceeded (ACL win, not
just 3/3); K100 <= 15.11 PASSED (14.60), stretch bars not met; testbed
keep-alive FAILED (14.22 > 13.46); guard within the known span offset.

*Addendum (same day, bug scope):* the "restrict alone is safe / the hang
needs initial_chains on the same variable" characterization above is too
narrow — on P16 with K100 margin-1 domains, `restrict_chains` WITHOUT any
`initial_chains` (chainlength_patience=0, timeout=20) hangs past a 60 s
wall kill, 3/3 trials (`data/restrict_bug_repro.py`). The P6 0.0 s return
was small-instance luck, not a safety condition. Any upstream report
should state: non-trivial domains at scale hang regardless of seeding;
default-patience configurations additionally segfault. Paired-by-seed
check of the K140 headline (repo rule): arrange-1shot wins all three
seeds vs mm-full (19.87/20.24, 19.88/21.26, 19.31/20.58; mean -1.01) —
the win is not a mean artifact.
Defaults unchanged (`state="point"`, `span_dynamics="field"`) — the flip
candidate that emerges is REGIME-SPECIFIC: product mode + wire seeds as
the cliff/hard-frontier configuration, not a global default.

Next options recorded: (a) hard-frontier eval (s3.23 neither-bucket) with
arrange-1shot — the K140 result says this is now the strongest card;
(b) irregular-dense cells (spin_glass/turan) — the switch-point argument;
(c) fork-level restrict_chains fix to unlock the domains handoff;
(d) the K100 residual (13.46 bar) stays open — the E-vs-routability wedge
needs a slack-aware objective (pack to ~85%? optimize E + congestion
margin?) before any dynamics can close it.

### 3.33 Coupler-aware coloring + handoff slack: mechanism real, gate failed; the field's true residual advantage is heterogeneity (2026-07-27)

Built (all default-off; 508 tests): `wire_couple` — t-coordinated coloring
(rows greedy as always; columns pick the FREE sub maximizing actual
couplers to contact partners' assigned row wires at the crossing tiles;
coloring stays exact, the score only breaks the freedom), `slack_steps`
(slack_relax: span_step refinement clamped to +-0.49 of each assigned line
— round() invariant), `seed_stride` (claim every stride-th qubit).
Premise measured first: Pegasus tiles couple only ~56% of h/v wire pairs
(80/144 at a P4 tile; Chimera 16/16, mechanism no-ops there).

**Testbed (couple_sweep_k100.log; fixed arrange states, handoff arms only,
x3 routing seeds):**

| arm (derate 1.0) | ACL mean | (derate 0.65) | ACL mean |
|---|---|---|---|
| base | 15.09 | | 14.43 |
| +couple | **14.51** | | 14.68 |
| +slack | 15.09 (=base) | | 14.43 (=base) |
| +stride2 | 14.66 (var, best 13.84) | | 14.41 |
| +couple+slack | 14.51 | | 15.27 |

Findings, in order:

1. **The coupler mechanism is real where packing is tight**: derate 1.0,
   15.09 -> 14.51, better on all three routing seeds individually (-0.6
   ACL). At loose packing (0.65) it is a small negative — when rows have
   slack the router finds couplers itself, and the score's reshuffling of
   wire choices only perturbs.
2. **Slack as built is exactly inert** — identical seeds to base: for K_n
   full-width bars the sub-0.5-tile endpoint shifts are swallowed by
   floor/ceil in the claim loop. Hypothesis unexercised, not refuted.
3. **The mechanism metric saturated**: couplable-contact fraction = 1.000
   even for blind seeds — 20-30-qubit crosses always have SOME coupler
   pair. It measures existence, not the coupler budget at designated
   crossings; needs a per-crossing definition before it can gate anything.
4. **Gate FAILED at every operating point**: best arrange-family K100 =
   14.51 vs 13.46 (proceed), 13.15 (field), 13.44 (mm). Pipeline probe not
   run, defaults unchanged, per pre-registration.
5. **The derate fill-in (couple_fill.log) closes the row-count confound
   with a sharper finding**: uniform exact packing QUANTIZES — rows jump
   10, 11, 12, 13, 16 as derate sweeps 1.0 -> 0.65; the field's 14-row
   operating point (its 13.15 state) is UNREACHABLE by any uniform derate.
   And the 13-row states route terribly (base 18.95; +couple 16.4). Routed
   ACL vs rows for arrange states is non-monotone garbage (10: 15.1,
   12: ~18 bimodal, 13: 19.0, 16: 14.4) while the field's 14-row
   heterogeneous state sits at 13.15 below all of them.

Diagnosis: couplers explain ~0.6 of the arrange-vs-field routing gap and
are now fixable machinery (kept, default-off). The remaining advantage of
the field states is their INHOMOGENEITY: uneven row loads, varied interval
endpoints, fractional positions — a diversity of local configurations that
gives the router options. Exact uniform packing is the router's worst
customer at fixed coarse quality: maximal confidence, zero variety, and a
quantized row count that skips the sweet spot. (s3.29 measured "100% packed
starves the router"; this round adds "uniformly packed at ANY derate
starves it too".)

Options recorded for Max: (a) heterogeneous packing — per-row load targets
drawn unevenly (or per-row derate jitter) so the packer can express
14-row-like states; cheap testbed experiment; (b) declare the per-regime
split and move on: field dynamics owns comfortable-dense (13.15-class
states), arrange owns the cliff (s3.32's 19.69 K140 paired win) — the
best-of-both selection is already house style (template-arm precedent),
and the hard-frontier eval (the strategic goal) is ready to run with the
per-regime winners; (c) redesign the couplable metric (per-designated-
crossing) before any further coupler work.

### 3.34 Staircase readout: K100 gate failed, K140 record, first irregular-dense win (2026-07-29)

Built behind `readout="stair"` (default "cross"; 515 tests): the diagonal
rule — edge (u,v) covered at u's h-arm x v's v-arm iff (y_u,u) < (y_v,v);
arms span assigned contacts only; `derive_bars_stair` / `stair_energy` /
`stair_step`; alternation packs staircase intervals (the orientation
assignment is keyed on y-ORDER, hence invariant under the order-preserving
pack — the sort is now load-bearing for correctness, tested).

**Testbed (stair_sweep_k100.log; routing x3 seeds):**

| cell/arm | E | seedACL | conn | cov | routed mean |
|---|---|---|---|---|---|
| K100 d1.0 base | 1211 | 14.0 | 83/100 | 95.5% | **14.21** |
| K100 d1.0 +couple | 1211 | 14.0 | 75/100 | 95.8% | 14.69 |
| K100 d0.85 base | 1506 | 17.0 | 88/100 | 97.2% | 15.40 |
| K100 d0.85 +couple | 1506 | 17.0 | 91/100 | 96.8% | 14.95 |
| K140 d1.0 base | 2458 | 19.5 | 111/140 | 98.9% | **19.51 (3/3)** |

Findings:

1. **The halving is real**: seeds 20.0 -> 14.0 (cross -> stair), legality
   forfeited exactly as pre-registered (17 disconnected chains, 4.5%
   uncovered edges) and the router repairs it for ~+0.2 ACL. Routed 14.21
   beats every cross-arrange arm ever measured (14.51+). **Gate FAILED
   anyway** (14.21 > 13.15); stretch 11.2 untouched; pipeline stair probe
   not run, defaults unchanged.
2. **K140 program record: 19.51 mean {19.41, 19.62, 19.49}, 3/3, beats
   stock mm on every paired seed** (20.24/21.26/20.58; mean -1.19), from
   the single-shot testbed protocol with spread 0.21 — the most consistent
   dense result the program has produced.
3. **Polish collapse**: seed ~= routed at both cells (14.0->14.21,
   19.5->19.51). As seeds approach constructive quality the router's
   contribution — and its vacancy appetite (s3.33) — fades toward
   busclique's no-router limit. The triangular occupancy also frees ~45%
   of in-block qubits as a by-product (1311 used vs ~2100 cross), so the
   workspace question resolves itself from both ends.
4. **Coupled scoring: 0-for-4 across s3.33-s3.34 arms** (noisy-negative
   every time redundancy or repair suffices). Retired as a default
   candidate; the coupler problem returns only if exact per-line matching
   is ever built.
5. **K100 residual localized**: E=1211 vs template ~878 (+38%) — a packing
   NESTING gap: busclique puts one arm per wire with complementary lengths
   sharing rows end-to-end; our order-preserving sort stacks similar
   lengths, so same-length arms can never share a wire. The gap is now a
   1-D packing problem, not a search or router problem.

**Irregular-dense (deferred s3.23-loss cells, first measurement ever;
arrange_probe.csv, 3 seeds, 60 s):**

| cell | mm-full | stair | stair-1shot | arrange | arrange-1shot |
|---|---|---|---|---|---|
| spin_glass_n163 d0.30 | 25.37 (2/3) | 20.87 (3/3) | **20.53 (3/3)** | 21.44 | 22.31 |
| turan_n162 (~K81,81) | **8.26 (3/3)** | 11.28 | 11.11 | 10.97 | 16.15 |

6. **First irregular-dense WIN, and it is large: spin_glass_n163 —
   stair-1shot 20.53 vs mm 25.37, paired 20.98/23.29 and 20.33/27.44 plus
   a feasibility win on the seed mm fails outright (2/3).** -19% ACL and
   better feasibility on exactly the cell class the strategic emphasis
   predicted (degree variance makes template restriction overpay; mm
   struggles at 60 s). The home-turf thesis finally has its first direct
   confirmation in the dense regime.
7. **Turan loss names the next gap**: turan_n162 is ~complete bipartite,
   and the diagonal rule is clique-shaped — bipartite sources have a
   native two-block construction (one side lives on rows, the other on
   columns; busclique's biclique) that the staircase cannot express; mm
   finds it implicitly (8.26 vs our 10.97). Candidate mechanism: a
   block-aware orientation rule (2-color the source, e.g. by spectral
   sign, and assign orientation by block instead of by y-order).

Options recorded for Max: (a) nesting-aware packing (finding 5 — the
remaining K100 headroom, a pure 1-D problem); (b) the bipartite/block
orientation rule (finding 7); (c) pipeline confirmation probe for stair at
the cliff + spin_glass (testbed numbers 19.51/20.53 need the
rounds-vs-1shot pipeline treatment before any default flips); (d) the
hard-frontier eval with stair-1shot as the flagship arm.

### 3.35 Diagonal alignment: three records and a first; adjacent swaps measured inert (2026-07-30)

The s3.34 K100 residual was mis-attributed to within-row nesting; the true
cause was UNCORRELATED axis orders (rows sorted by y-noise, columns by
x-noise), which makes h-arms reach backward. Busclique's diagonal =
x-rank == y-rank; aligned, E = n*side (K4 arithmetic: aligned E 12 vs
misaligned 14, growing with n). Built: `_align_diagonal` in
alternate_arrange (stair readout) — a pure PERMUTATION of the
participants' existing x-values (x-rank := y-rank), E-gated like every
projection, acting only in attraction's null directions. Max's calls:
committed diagonal bias (no dual proposals; the standing E-gate is the
only safety), row-first kept (row/col order is mirror-symmetric up to one
transient iteration). Also realized, killing the per-edge orientation
variable AND the proposed bipartite rule: **the diagonal rule already
contains the biclique** — a y-order separating bipartite blocks makes one
side pure h-lines and the other pure v-lines; turan's failure was an
ORDER problem (interleaved blocks from the circle init).

**Emergence check (one configuration, no topology detection;
emergence_check.py / .log; routing x3):**

| cell | E | seedACL | conn | cov | routed | prev best | mm |
|---|---|---|---|---|---|---|---|
| K100 | 900 | 10.9 | 100/100 | 95.7% | **12.51** | 14.21 | 13.44 |
| K140 | 1729 | 14.2 | 63/140 | 98.4% | **17.64** | 19.51 | 20.70 |
| turan swaps=0 | 2276 | 15.5 | 159/162 | 98.1% | 14.20 | 10.97* | **8.26** |
| turan swaps=30 | 2219 | 15.6 | 115/162 | 97.5% | 13.92 | | |
| spin_glass swaps=0 | 2283 | 14.9 | 107/163 | 91.7% | **18.05** | 20.53 | 25.37 (2/3) |
| spin_glass swaps=30 | 2277 | 14.9 | 106/163 | 92.1% | 18.55 | | |

(*pipeline rounds protocol; testbed single-shot not directly comparable.)

1. **K100: first search win over stock minorminer in program history**
   (12.51 vs 13.44), E=900 vs the ~880 arithmetic — the alignment claim
   held almost exactly. The old 13.15 gate falls; the 11.2 primary bar
   stands (template gap now 2.7; residual = coupler repair + ordering).
2. **K140 record 17.64** (3/3; -3.1 vs mm) despite conn dropping to
   63/140 — tighter packing worsens corner coupling, repair stays cheap.
3. **Alignment is general, not a clique trick**: spin_glass (irregular)
   improved 20.53 -> 18.05; the E-gate admitted the permutation where it
   paid on a graph with no clique structure.
4. **Pre-registered prediction CONFIRMED: adjacent swaps are
   plateau-bound.** Turan E moved 2276 -> 2219 in 30 sweeps against an
   optimal ~1094 (= 2ab/k; mm's 8.26 is near-OPTIMAL there — losing that
   cell to mm means losing to the true construction). Arm spans are
   maxes, so single adjacent swaps have dE ~= 0 from interleaved orders;
   the Metropolis contingency in its current form has no teeth anywhere
   (spin_glass likewise inert). Blocks did not emerge.
5. Diagnosis + the general fix (recorded, unbuilt): **rank RELOCATION
   (insertion) moves** — move one variable's position in the order to
   anywhere; this flips ALL its edge orientations at once, giving
   first-order energy signal exactly where adjacent swaps see flatness.
   Insertion is the canonical 1-D arrangement neighborhood: block
   separation (bipartite), community contiguity, and degree ordering are
   all consequences of one topology-blind move class.
6. **Init-independence standard (Max)**: the scaffolding + order moves
   must take RANDOM initializations to the same solutions; spectral
   layout is demoted to a warm-start heuristic, never load-bearing. The
   random-init arm is the pre-registered emergence test for the
   relocation build: turan bar = E approaching ~1100 and routed closing
   toward mm's 8.26 BY EMERGENCE; K100/K140/spin_glass as no-regression
   guards, from both spectral and random inits.

### 3.36 Insertion order search: blocks emerge from random init; turan falls; the dense board is swept vs minorminer (2026-07-30)

Built: `insertion_sweeps` (field.py) — best-insertion on the participants'
queue with EXACT integer-slot semantics (a fractional-rank shortcut was
tried and collapsed by rank-stacking — s3.30's pathology reborn in the
proxy, caught by the clique no-op test); candidates adjacent to
neighbours' slots; monotone, deterministic; numpy O(n^2) per candidate
(participants fabric-bounded). Wired into alternate_arrange
(`insert_sweeps`, default 0) as propose-in-rank-space /
dispose-by-true-E with full composite revert; pipeline knob
`AttractConfig.insert_sweeps` (default 0). 521 tests.

**Emergence check (16 arms: 4 cells x insert {0,8} x init
{spectral, random}; emergence_insert.log; routing x3):**

| cell | arm | E | seedACL | routed | blocksep | t_ins |
|---|---|---|---|---|---|---|
| turan_n162 | spectral, ins=0 | 2276 | 15.5 | 14.12 | 0.9/81 | — |
| turan_n162 | spectral, ins=8 | 1811 | 11.7 | **8.47** | **81/81** | 1.7s |
| turan_n162 | random, ins=8 | 1782 | 11.5 | **8.24** | **81/81** | 2.0s |
| K100 | spectral, ins=8 | 900 | 10.9 | 12.51 | — | 0.24s |
| K140 | spectral, ins=8 | 1729 | 14.2 | 17.39 | — | 0.67s |
| spin_glass | random, ins=8 | 2267 | 15.1 | 17.59 | — | 4.6s |

Scorecard vs the pre-registered bars:

1. **PRIMARY BAR: PASSED COMPLETELY. Block separation emerged perfectly
   (blocksep 81.0/81, bar was >72.9) on turan from BOTH inits**, with all
   162 chains connected (pure lines), and routed **8.47 (spectral) /
   8.24 (random)** vs the 10.97 bar and the 9.5 stretch. The random-init
   arm **beats stock minorminer (8.26)** on the one cell where mm is
   near-optimal (2ab/k bound ~7.7+1). The biclique construction was
   DISCOVERED, not programmed: one topology-blind move set, from random
   positions.
2. **Guards: PASSED** (K100 12.51 =, K140 17.39 — slightly better than
   s3.35's 17.64, spin_glass 18.05 =, all 3/3). K_n insertion no-ops in
   one sweep as the symmetry argument requires.
3. **Init-independence: 3/4.** turan (8.24 vs 8.47 — random BETTER),
   spin_glass (17.59 vs 18.05 — random better), K140 (+3.9%, inside the
   5% band). **K100 FAILS (14.95 vs 12.51)** — and instructively:
   insertion is provably inert on K_n (all orders equivalent), so the
   deficit is in the CONTINUOUS geometry (the harness ran ONE stair_step
   before packing; a random cloud hasn't contracted in one step). The
   failure localizes attraction's true role: warm-start contraction,
   which spectral was silently providing. Cheap follow-up: ~20
   stair_steps for random inits, remeasure.
4. **Wall-time bar: FAILED as written, satisfied in intent.** t_ins is
   20x t_arr (the alternation is 0.03-0.09 s — 2x of almost-zero was a
   miscalibrated bar), but absolute cost is 0.2-5 s ~ 3-8% of one 60 s
   routing call. The "cheap global optimization" claim stands on
   absolute terms; the bar's letter does not. Recorded as
   miscalibration, not waved through.

Standing after this round, dense cells vs stock minorminer: K100 12.51
vs 13.44; K140 17.39 vs 20.70; spin_glass 17.59 vs 25.37 (2/3); turan
8.24 vs 8.26. **Every measured dense cell class now at parity or won**
— the last loss cell fell to emergence. Remaining gaps: template on pure
K_n (9.78 vs 12.51; nesting/coupler-exactness territory), the K100
random-init contraction fix, pipeline confirmation of testbed numbers,
and the OPEN corridor-reservation design question (arrange mode still
does not price non-participant traversal; Max: naive reservation would
sabotage cliques — needs its own design round before mixed/clustered
graphs are attempted).

### 3.37 Wire matching: turan and K140 records, K100/spin_glass regress; the 99% bar refuted and the reason found (2026-07-31)

Built: `_line_tracks` + `wire_seeds_matched` (field.py; scipy
linear_sum_assignment per line, columns<->rows coordinate ascent on
satisfied designated crossings; ALWAYS best-effort — leftovers to the
router; `wire_exact` pipeline knob, default off; 525 tests). The honest
per-designated-crossing metric replaces the saturating any-pair one.

**Results (exact_check.log; stair+insert seeds, spectral, routing x3):**

| cell | designated greedy | designated matched | routed greedy | routed matched |
|---|---|---|---|---|
| K100 | 2752/4895 (56%) | 3110 (64%) | 12.51 | 13.25 (conn 100->44!) |
| K140 | 59% | 63% | 17.79 | **17.17** |
| turan_n162 | 57% | 62% | 8.47 | **8.04** |
| spin_glass | 54% | 67% | 18.05 | 18.69 |

1. **The blind coloring satisfies designated crossings at exactly the
   background coupler density (~56%)** — chance level, as geometry
   predicts. The saturating any-pair metric had hidden this completely.
2. **Mechanism bar (>=99%) FAILED — the matching plateaus at ~62-67%.**
   Two named causes: (a) **the objective omits SELF-JUNCTIONS** — a
   variable's own h-arm x v-arm corner (chain connectivity!) is not in
   the crossings list, so the matching happily sacrifices corners for
   contacts: K100 connectivity collapsed 100/100 -> 44/100 and routed
   REGRESSED 12.51 -> 13.25 (spin_glass likewise 18.05 -> 18.69). Greedy
   was accidentally kinder to corners. (b) **the busclique existence
   proof does NOT transfer**: it guarantees a perfect wire assignment for
   busclique's OWN co-designed geometry; our packer fixes rows/columns
   coupler-blind first, and for that layout a perfect assignment may not
   exist at all. 100% likely requires geometry<->wire CO-DESIGN, not
   wire assignment after the fact.
3. **Where corners don't bind, the matching already pays**: turan 8.04
   (3/3; new record; mm 8.26 now beaten clearly, 2ab/k bound ~7.7 in
   sight) and K140 17.17 (new record; mm 20.70; template 13.17) — both
   cells where chains are single lines (turan) or corner-poor. Matching
   cost is trivial (t_match 0.12-0.34 s).
4. Per the pre-registered tier discipline: STOPPED here — no objective
   patching or solver escalation without discussion. Agenda for the
   design round: (i) add self-junctions to the matching objective
   (weighted — connectivity is worth more than one contact; likely
   reverses both regressions; arguably a bug-fix to the crossing list,
   but it changes the objective, so it waits); (ii) the deeper
   co-design question: rows/columns are currently assigned coupler-blind
   and wire assignment inherits an impossible layout — options range
   from t-aware packing tie-breaks to joint geometry/wire passes;
   (iii) the corridor-reservation question remains open alongside.

Defaults unchanged everywhere (`wire_exact=False`). Standing dense board
(best arms): K100 12.51, K140 17.17, spin_glass 18.05, turan 8.04 — vs mm
13.44 / 20.70 / 25.37 / 8.26; template K100 9.78, K140 13.17.

*Addendum (junction fix, same day; Max: "the self-coupler thing definitely
should be fixed"; junction_check.log):* self-junctions added to the
matching objective at weight 2.0 (contacts metric definitionally
unchanged). Rerun, matched arms: **K100 conn 100/100 restored** (from 44;
mini-bar passed) but routed 13.13 — still behind blind-greedy's 12.51
(mini-bar failed; the regression shrank from 13.25 but persists — K100's
dense all-pairs crossing structure appears to route better off greedy's
uniform chance-pattern than off the matcher's concentrated one; open,
belongs to the co-design discussion). **K140 17.04 (new record; conn
74->125)**, **spin_glass 17.50 (new record; conn 111->150; mini-bar
passed)**, turan 8.04 held (pure lines, junctions vacuous). Standing board
after the junction fix: K100 12.51 (greedy seeds), K140 17.04, spin_glass
17.50, turan 8.04 — three of four cells now carried by matched wires; vs
mm 13.44 / 20.70 / 25.37 / 8.26. Co-design stakes now localized to K100's
last 2.7 vs template.

### 3.38 The consolidation: one algorithm, defaults flipped, spin_glass record; rounds measured harmful on dense (2026-07-29)

Max's directive: one algorithm he can follow; code is regenerable, ideas
are not — `attraction.md` keeps the fossil record, `anatomy.md` is now the
clean as-built spec of only the current pipeline. Decisions taken in
discussion: wire_exact stays an off-default switch; the native purity arm
deleted from attraction (`factored` stays registered); bar_domains KEPT
parked as the exact-handoff interface for the strip-minorminer-down agenda
(fork-level patch of the restrict_chains bug when needed; no upstream
report). Archive commit `612ced3e` holds everything deleted; the full
deletion list with per-item verdicts is in attraction.md's consolidation
ledger entry.

Build: `field.py` 1602->~1000 lines (TileGrid + stair readout + arrange +
insertion + wire seeds + matched seeds + parked bar_domains only),
`placement.py` 769->~400 (single pipeline; 12 knobs), tests 780->745 pass
(35 deleted-machinery tests removed; ported: kappa-floor and wire-run
properties onto the stair/interval functions). Pre-existing failures
unchanged (4F + 80E, identical on the archive commit).

**Probe** (`data/consolidation_probe.py`; bars pre-registered in the plan
file before any run; 3 seeds x 60 s, P16). Run 1 (24 workers) DISCARDED:
machine load ~70 made wall-clock timeouts starve the rounds budget —
spin_glass 0/3 for every arm including mm 1/3, while a direct sequential
run legalized in 2 rounds (legal 17.7); contention lesson recorded. Scoring
run (8 workers), means over legal seeds:

| cell | 1shot (NEW DEFAULT) | rounds | mm |
|---|---|---|---|
| K100 | **13.41** | 13.49 | 13.77 |
| K140 | **18.55** (3/3) | 20.20 | 21.91 |
| turan_n162 | 8.40 | 12.73 | **8.26** |
| spin_glass_n163 | **17.22** (3/3, record; was 17.50) | 18.04 | 24.53 (2/3) |
| regular_n316 | 3.56 | 3.56 | 4.02 |
| ws_n486 | 3.76 | **3.41** | 3.89 |
| ER100_d10 | 5.88 | 5.94 | 5.67 |

1. **Protocol rule fired: 1shot beat rounds on 4/4 dense cells** ->
   default = `max_rounds=1, round_frac=0.5`. The mechanism reads clean:
   feedback re-derives geometry from realized centroids and the next
   arrange cannot recover insertion-found order within budget (turan 12.73
   vs 8.40 is the smoking gun — the s3.31 "transfer economics" cost,
   now measured as the dominant term). Rounds still help SPARSE quality
   (ws 3.41 vs 3.76: seeded re-rolls, the s3.23 mechanism) — a
   participant-gated adaptive-rounds rule is the obvious unbuilt
   candidate, parked for a design decision.
2. **Minimum bars: met except turan by 0.14** (parity; mm near-optimal
   there per the 2ab/k bound). spin_glass is the headline: irregular-dense,
   mm fails 1/3 and averages 24.5; we legalize 3/3 at 17.22 — the
   home-turf thesis carrying the consolidation.
3. **Target bars (harness records in-pipeline): spin_glass + turan met;
   K100 13.41 vs 12.51, K140 18.55 vs 17.04 NOT met.** Suspect (1)
   compact init probed under a pre-registered acceptance rule and
   REVERTED: K100/K140 -0.15 but turan +2.0 / spin_glass +0.5 — compact
   init interleaves blocks harder than insertion recovers (the s3.35
   circle-init lesson re-measured). Drafting lesson on record: the
   acceptance rule listed only K100 + guards, so its letter passed while
   the trade was plainly bad; overridden by the consolidation's own
   minimum bars. Suspect (2) insertion plumbing: confirmed working
   (turan 8.40 ~ harness 8.24/8.47). Suspect (3) eta and the residual
   harness-protocol deltas (one arrangement x3 routing seeds vs per-seed
   re-derivation) left open — cross-run absolutes swing with machine load
   (mm 13.72-14.33 between runs), so settle it on a quiet box.

Standing dense board after consolidation (paired, this probe): 13.41 /
18.55 / 17.22 / 8.40 vs mm 13.77 / 21.91 / 24.53 / 8.26. Records carried
from the pre-consolidation harness (12.51 K100 greedy, 17.04 K140 matched,
8.04 turan matched) remain the reproduction targets; wire_exact holds
three of them behind its switch.

### 3.39 Multi-dense-patch probe (weak_strong_cluster): patch-size crossover found; rounds beat 1shot off the single-block regime (2026-07-29)

Max's question after the consolidation Q&A ("how do cliques end up
together / who pushes sparse away / what does the permuter know"): probe
the several-dense-patches family. Cells: c disjoint K32/K64 cliques, ONE
inter-edge per cluster pair (ids 33571/33601/33640/33574) — every member a
participant, inter-edges participant-participant (visible to the insertion
proxy; the sparse-fringe blind spot does NOT apply here). 3 arms x 3 seeds
x 60 s, P16, 8 niced workers (machine carried a 60-core batch; ~68 free).
`data/wsc_probe.py` / `.log` / `.csv`.

| cell | 1shot (default) | rounds | mm |
|---|---|---|---|
| 3xK32 (n96) | 6.14 | 5.18 | **4.68** |
| 5xK32 (n160) | 5.68 | 5.47 | **4.99** |
| 8xK32 (n256) | 5.34 | 5.34 | **5.15** |
| 3xK64 (n192) | 9.79 | 9.67 | 9.89 (**we win, both arms**) |

1. **Patch-size crossover, cleanly measured.** K32 patches sit below the
   size where the staircase construction pays: mm's irregular local
   negotiation is near-optimal there and our block discipline is pure
   overhead (-1.46 at c3). The gap shrinks monotonically as the fabric
   fills (c8: -0.19), and at K64 patches both our arms beat mm — on a
   graph busclique cannot address at all. Same shape as the s3.26
   template-vs-search finding: constructive structure wins only above a
   patch-size threshold, here bracketed between K32 and K64.
2. **Rounds beat 1shot decisively off the single-block regime** (c3xK32:
   5.18 vs 6.14; ws_n486 previously 3.41 vs 3.76). Reading: feedback
   rounds re-place PATCHES relative to each other from realized centroids
   — the inter-block geometry is exactly what one shot cannot revise. With
   s3.38's opposite result on single-block dense (rounds destroy
   insertion-found order), the adaptive-rounds design question now has a
   clean shape: single dense component -> 1shot; multiple
   patches/sparse-coupled -> rounds. Candidate gate: component count of
   the participant subgraph (computable from the existing capacity gate,
   no topology detection). UNDESIGNED — needs its own decision round
   (default remains 1shot).
3. Agenda implications: (a) the K32-patch loss is the below-cliff overhead
   question, not the corridor question (inter-edges here are
   participant-participant); the corridor/sparse-traversal suspect remains
   unmeasured — a wsc variant with sparse bridges or low-degree fringe
   would isolate it; (b) K64-patch win is the first direct evidence for
   the beats-busclique-off-clique thesis on multi-patch terrain.

### 3.40 Local interpolation refinements: the diagonal demoted to a theorem, degree demoted to a readout; the tie-plateau found and fixed; two honest misses (2026-07-29)

Design round from Max's "it feels bad to be aware of any particular
cluster... a simple rule that interpolates between perfect clique embedding
and the right layout for geometric graphs" — after the mixed-size-placement
discussion identified the global x-rank:=y-rank alignment as the un-real
part (one 1D order for the whole graph; side-by-side patch tilings
unreachable; deg>κ a binary cliff conscripting non-clique hubs). Built, all
three approved refinements ("implement all 3 and see how it goes"):

1. **`edge_monotonize`** replaces `_align_diagonal`: per-edge x-value
   transpositions, strict stair-E gate, sorted-edge sweeps to fixpoint.
   Leverage ∝ |Δx|: geometric edges self-neutralize, clique edges do real
   reordering — the sparse/dense interpolation is a property of the move.
   Patches diagonalize in place; no cross-patch pressure exists.
2. **Arm-length participation** replaces the degree gate: a variable enters
   row/column packing per-axis iff its floored stair interval ≥ 1 tile (it
   owes a wire run). κ survives only in the floor. The K14/K15 cliff and
   degree conscription are gone; a compact K15 is MM's business, a
   low-degree variable with one long edge packs on that axis only.
3. **Value-priced insertion + fixed anchors**: the proxy prices slots at
   the y-values the permutation will assign (rank space lies on clustered
   layouts); non-member neighbours fold in as constant bounds (they guide,
   not just veto). Composite revert counter surfaced in diag.

**Found along the way (unit test, K16): the diagonal was sufficient, never
necessary.** Stair E requires contiguous SUFFIX VALUE-SETS; per-edge descent
finds E-equivalent mixed couplings — part diagonal, part mirrored, "tents"
(build the y-suffix downward, extend the contiguous x-block left OR right
each step; every L/R sequence is optimal; busclique is the all-right
corner). ρ(x-rank, y-rank) ≈ 0.17 at E 242 vs ideal 240. K100 then ROUTED
BETTER than the pure staircase era (13.09/13.14 vs 13.41) — the router does
not care which member of the optimal family it gets.

**Probe** (`refine_probe.py`; bars pre-registered in the plan; +mm2
passthrough null — measured null widths: turán 0.66, spin_glass 3+ ACL
between mm seeds). First run FAILED turán catastrophically (16.48 vs 8.26;
random-init 11.50 vs the ≤8.5 bar). **Bisection** (`refine_bisect.py`,
monkeypatch arms): monotonization innocent (E 3335 vs 3308 without);
**value pricing guilty** (rank restores 2098 in both combos). Mechanism:
insertion runs after packing QUANTIZES y onto integer lines → the value
multiset is full of ties → the value-priced landscape is flat plateaus and
strict-improvement search cannot descend. **Rank pricing was never
"correct" — it was an accidental plateau-smoothing tie-break.** Fix:
lexicographic pricing, value + 1e-4·slot (max ~0.05 tiles, far under the
1-tile line quantum) — restores E 2098 exactly; one line.

**Post-fix board (default arm; mm/mm2 from the same probe):** K100
**13.14** (mm 13.86/14.12; and 13.09 pre-fix — best pipeline numbers ever),
K140 19.34 (mm 21.91/21.75, 3/3), spin_glass 18.45 (mm 24.05 2-of-3 /
20.90, 3/3), turán 8.93 (mm 8.26, mm2 8.92 — parity at the null edge),
regular 3.44, ws 3.79, ER 6.12 (mm 5.67/5.87). wsc ladder: c3×K32 gap
−1.16 (from −1.46), c5 −0.26, **c8 4.98 vs 5.15 WIN**, **c3×K64 9.22 vs
9.89 WIN**. Verdicts:

- The c3×K32 gap did NOT close → the global diagonal was not the cause of
  the small-patch loss; **patches-too-small confirmed** as the dominant
  story (the below-crossover overhead of s3.39).
- **EMERGENCE bar MISSED**: random-init turán 9.93 (E 2098; spectral 8.93;
  the old global-alignment machinery got 8.24 from random init, s3.36).
  The global permutation could jump between distant orderings in one move;
  per-edge transpositions + insertion descend the same landscape locally
  and stall ~1.5 ACL short from bad inits. The known fight, now measured.
  Candidate next moves (NOT built): an E-tie-biased monotone preference;
  block-insertion (relocate runs, not singles); or accepting spectral
  dependence on multipartite (spectral is cheap and always available).
- ER slipped ~+0.25 beyond the null — small, real, unattributed.
- Wall-time fine (mono 0.24 s at n=162, under the insertion phase).

Kept as default: the board improves or holds everywhere except the two
recorded misses, and the design is the one Max asked for — no rule mentions
a cluster, a diagonal, or a degree threshold; κ is physics only. Both
misses stay open on the ledger.

### 3.41 Contraction Stage 1: the wall leaks through arm growth; cycles vindicated, magnets-rate refuted; routed bars failed except the multi-patch payoff; Zephyr adapter + derived κ shipped (2026-07-29)

Design round from Max's capacity insight ("an energy-lowering swap should
never be vetoed by capacity — a veto means the layout was wrong") plus two
amendments (repetition/cycles; switch the frontier to Zephyr). Built
(`contract_layout`, `_target_kappa`, typed Zephyr TileGrid adapter; 511
tests): spread-start contraction, capacity as excluded volume approached
from below (sequential entry gating = invariant-by-entrants, no forced
projection), optional unnormalized degree-weighted steps (magnets-rate),
interleaved edge_monotonize, settle-and-reshake cycles with decaying
amplitude returning the best settlement. Probe: `contract_probe.py`
(Phase A screen, Z12 + P16) and `contract_probe_routed.py` (Phase B).
Bars pre-registered in the plan.

**Phase A:** screen gate passed on the letter — E far below the pipeline
handoff on every dense cell, zero entry violations — but the
growth-overfill diagnostic (deliberately measured-not-blocked) exposed
the load-bearing finding: **the wall leaks through arm growth.** Entry
gating stops bodies; residents' arms lengthen in place as neighbours
converge, and dense settlements sit 60–140 deep past line capacity — the
spectacular E (K140 61, turán 33, spin_glass 32) is partly fictional.
Clean cells (grow ≈ 0): sparse guards E 26–43 vs pipeline handoffs
1600–2900; wsc patches band_overlap 0.0 (coalesce in place). **CYCLES bar
passed emphatically** (reshake rescues jams 10–100×: 3005→26, 4316→43,
1573→8.8 — Max's repetition amendment is the strongest mechanism in the
data). **Magnets-rate refuted**: dw=1 loses to normalized steps nearly
everywhere once cycles exist (hubs overshoot; 10–30× blocked). Wall-time
bar missed on the heaviest cells (up to ~15 s at c4).

**Phase B (routed; finalist spec/dw=0/c4):** the routed bars FAILED
broadly, exactly along the leak line. Z12 (fresh mm/mm2 baselines, first
ever): contract loses on K100 (11.54 vs 10.28), K140 (21.43 at 1/3 vs mm
18.27 — feasibility deficit ✗), turán (13.66 vs 12.01), spin_glass
(0/3 ✗✗ vs mm 3/3), wsc cells; small wins ER (4.74 vs 4.97) and parity
ws. P16 continuity: worse than the pipeline on K100/K140/spin_glass/
regular/ws — the sparse-guard E gains did NOT translate to routing
(regular E 26 → routed 4.30 vs pipeline 3.44: low model-E under a leaky
wall, and over-deep bars that the coloring cannot seed, buy nothing).
**Salvages:** (1) **P16 wsc c3×K32 PAYOFF BAR MET** — 5.32 vs pipeline
5.84, gap to mm 0.64 ≤ the 0.7 target; the clean-contraction multi-patch
case delivered exactly where grow ≈ 0. (2) Z12 ER win. (3) Permanent
infrastructure: the typed Zephyr adapter (junctions measured
near-complete vs Pegasus 0.56) and derived κ (mean target degree − 2;
kappa=None default) are in the default pipeline. (4) First Z12 per-cell
baselines: mm is markedly stronger on Zephyr (K100 10.28; spin_glass
17.87 3/3 vs P16's 24 with failures) — paper3's "Zephyr legalizes
easily" confirmed at cell level; margins there will be thinner
everywhere.

**Verdict:** Stage 1 as built is not a pipeline candidate; the
pre-registered jamming rule fires in a sharper form — it is not that the
projection earns its keep (the screen passed), but that **E under a leaky
wall is not the objective**. Stage 2, if pursued, has one mandatory
change (growth-tight wall: arms may not lengthen into full lines — the
excluded volume must bind bars, not just bodies) and one proven component
to keep (cycles). The wsc payoff and ER results say the thesis lives
where the wall holds. No default changes; contract_layout stays a
probe-callable mechanism. Discussion with Max next.

### 3.42 The pressure round (2026-07-30)

#### (a) Derivation — written before any code, per the round's discipline

**State.** Positions (x_v, y_v). Within a step, stair contacts are frozen
(computed from the y-order at step start, standard subgradient semantics),
and so is each variable's floor pad c_v (see below). M_v = {v} ∪
h-contacts(v); M'_v = {v} ∪ v-contacts(v).

**Bars.** v's h-bar: x-interval [a'_v, b'_v] with a_v = min_{u∈M_v} x_u,
b_v = max, widened by the frozen pad c_v = max(0, need_v − (w_v+h_v))/4
per side (need_v = deg_v/κ − 1; matching derive_bars_stair). Row
membership is BILINEAR: weight ω_v(r) = 1 − f on r = ⌊y_v⌋ and f on r+1,
f = y_v − ⌊y_v⌋ — this is what makes cross-line motion differentiable.
v-bars symmetric (y-interval over M'_v, column membership from x_v).

**Load and pressure.** Cell coverage χ_v(t) = |[a'_v, b'_v] ∩ [t, t+1)|
∈ [0,1] (piecewise linear in the ends). Row load L(r,t) = Σ_v ω_v(r)
χ_v(t). Overload o(r,t) = relu(L(r,t) − cap_r·derate), cap_r = the row's
mean h-pool. P = Σ_{r,t} o(r,t)² + (column term). E_total = E_wire +
λ_P·P; λ_P ramps with the cycle index.

**Gradients (the load-bearing part).**

1. *Axial, through the ends.* ∂χ_v(t)/∂a'_v = −1 exactly in the cell
   t_a = ⌊a'_v⌋ (extending left adds coverage there), 0 elsewhere;
   symmetric +1 at t_b = ⌊b'_v⌋ for b'_v. Hence
   ∂P/∂a'_v = −Σ_r ω_v(r)·2o(r, t_a),  ∂P/∂b'_v = +Σ_r ω_v(r)·2o(r, t_b).
   Chain to positions through the min/max: a_v = x_{u_min} where u_min is
   the (x, id)-tie-broken argmin over M_v, so
   **∂P/∂x_u = Σ_{v : u = u_min(M_v)} ∂P/∂a'_v + Σ_{v : u = u_max(M_v)}
   ∂P/∂b'_v** (+ the analogous v-bar terms landing on y_u). This is the
   third-party push: u is billed for every neighbour's bar whose end u
   defines. A non-extreme member of M_v gets nothing from v's bar — the
   test suite asserts both directions.
2. *Perpendicular, through the membership.* ∂ω_v(⌊y_v⌋)/∂y_v = −1,
   ∂ω_v(⌊y_v⌋+1)/∂y_v = +1, so
   **∂P/∂y_v (row term) = Σ_t χ_v(t)·2[o(r+1, t) − o(r, t)]** — the bar
   slides toward the less-overloaded row. Symmetric column term lands on
   x_v.
3. Forces = −λ_P·∇P added to the attraction subgradient; trust-region
   clip at 1 tile unchanged. Kinks (cell boundaries, argmin ties,
   L = cap) are measure-zero; the finite-difference test samples away
   from them.

Frozen-within-step quantities (contacts, pads, and the argmin/argmax
attribution) are refreshed every step; the FD test freezes identically so
it checks the implemented function, not the refresh policy.

#### (b) Build + Phase A verdict (2026-07-30)

Built exactly per (a): `PressureState` / `pressure_energy` /
`pressure_forces` / `contract_layout` v2 (v1 leaky wall kept as the
control arm). **The finite-difference gradient test passed on the first
run of the real implementation** — the physics is as derived (plus
sign-specific third-party billing, perpendicular slide, gas inertness;
516 tests). Smoke: residual overload 0.0 on P4/Z4 K20, deterministic.

**Phase A (`pressure_probe.py`): the LEAK-CLOSED bar FAILED at probe
scale.** Residual overloads at settlement on dense cells: 24–160 (bar:
≤ ~1). The diagnosis is clean and is NOT the physics: at deep overload
(o ~ 50–150), the pressure force λ·2·o·η exceeds the 1-tile trust clip by
orders of magnitude → every step is a full-tile bang-bang in the sign
direction, no equilibrium, settlement (Σ|Δ| < 1e-3) never fires, the
step cap ends mid-thrash. Symptom fingerprint in the data: best_cycle=0
(the SOFT-λ settlement wins the final-λ scoring — the hard cycles thrash
to worse states than the soft ones), and wall-time 10–22 s (bar ~12 s).
**A stiff barrier defeats fixed-step subgradient descent — the integrator
is the failure, the FD-verified forces are not.** Where the barrier is
NOT stiff, everything works: P16 regular resid 0.1, wsc c3 0.22, ws 3.2.

First blob-area-law data (liquid/sparse cells, P16): occupied ~1.5–2× the
predicted mass/density area (regular 90 vs 54, ws 202 vs 110) — right
order, outside the 25% band; not scoreable until settlements are real.
First shape data recorded (bar lengths mean 2.6–12.7 by cell). Phase B
skipped (routing leaky layouts was already measured in s3.41).

Named integrator candidates for the next decision (NOT built): (i)
per-step E_total acceptance with deterministic step-halving (Armijo-style
— guarantees descent, kills bang-bang); (ii) per-variable force
normalization (direction-only steps with a decaying schedule); (iii)
within-cycle λ continuation instead of per-cycle jumps. All three are
integrator-only; the derivation and tests stand as-is.

### 3.43 The Armijo integrator: numerics fixed, and the pre-registered plateau confirmed as the real obstruction (2026-07-30)

Built per plan: contract v2.1 — descent direction = the true −∇ of the
frozen-within-step model (wire nets + PressureState fixed at step start),
α0 from the 1-tile trust region, deterministic backtracking (7 halvings),
acceptance only on frozen-E decrease, settlement by relative-E tolerance,
plus a **hardening tail** (penalty continuation: double λ and re-settle
until the residual clears or a fixed cap fires). New tests: monotone
trajectory contract, stiff-barrier settlement, sign conventions; 518 pass.

**The integrator works**: bang-bang is dead (stalled steps 11–20 out of
134–388; every accepted step descends by construction; wall time 3.5–10 s
on the s3.42 failing cells vs 10–22 before). **And that is precisely what
exposed the real obstruction**: with λ hardened to 16384, residual
overload sits pinned at 27 (P16 spin_glass) / 56 (Z12 turán). Not
thrash — the s3.42 pre-registered PLATEAU rule, firing exactly as
written: local pressure can only shrink bars axially and slide them
toward *less-loaded adjacent* lines; inside a uniformly overloaded blob
the differential is zero, so only the rim peels (~one line per
settlement) and the interior is gradient-blind despite arbitrarily large
λ. Gauss's-law problem, third appearance in the program (s3.19's one-bin
push; s3.42's naming of the risk; now measured under a provably-monotone
integrator, which removes every alternative explanation). Small-scale
synthetics show the same floor in miniature (residual ~1.5–1.8; unit
bars annotated accordingly).

Probe phases NOT launched (the leak bar already fails at smoke; routing
plateau layouts was measured in s3.41). **Decision point per the
pre-registered rule**: the recorded fallback is the Poisson-solved
pressure source — replace the pointwise hinge with the electrostatic
energy of the overload source (interior variables then feel the total
enclosed excess; the s3.19-era machinery exists in git history), with
its own mini-derivation + FD tests under the s3.42 discipline. This is a
physics change and awaits Max. Everything else stands: derivation, FD
tests, the integrator, the cycles mechanism, and the phase-picture frame
whose liquid corner is exactly what's blocked on this one term.

### 3.44 The Poisson round (2026-07-30)

#### (a) Derivation — committed before code, per the standing discipline

Replaces s3.42(a)'s pointwise hinge² with the electrostatic energy of the
overload source; everything else in that derivation (bar readout, bilinear
membership, axial/perpendicular chain rule, frozen-within-step semantics)
carries over verbatim.

Per axis grid (rows H×W; columns W×H):

- **Source**: s(cell) = relu(L(cell) − cap_line·derate) / cap_scale,
  cap_scale = mean line cap. One-sided: slack fabric is silent.
- **Potential**: ψ = G·(s − mean s), G = pseudoinverse of the grid
  Laplacian (Neumann; the pre-consolidation PoissonField construction,
  archive 612ced3e), computed once per grid shape and cached.
- **Energy**: P = ½ Σ_cells s·ψ per axis, summed over axes. Since G is
  symmetric and the mean-subtraction is idempotent against G's kernel,
  ∂P/∂s = ψ, hence **∂P/∂L(cell) = ψ(cell)·1[L(cell) > cap]/cap_scale.**

Consequently the position-gradient is s3.42(a) with the substitution
2·o(cell) → ψ(cell)·1[over(cell)]/cap_scale everywhere:

1. Axial: ∂P/∂a'_v = −Σ_r ω_v(r)·ψ(r, t_a)·1[over]/cap_scale (and the
   +ψ analogue at b'_v), billed to the (value, id)-tie-broken span
   extremes — third-party billing unchanged in structure.
2. Perpendicular: ∂P/∂y_v = Σ_t χ_v(t)·[ψ(r1,t)·1[over] −
   ψ(r0,t)·1[over]]/cap_scale.

Why this breaks the plateau: inside a uniformly overloaded blob,
1[over] ≡ 1 and ψ is the solved potential of the whole excess
distribution — its interior gradient is proportional to enclosed excess
(Gauss), nonzero everywhere except the exact center. The rim-only
blindness of the local form is gone by construction, while slack end
cells still contribute nothing (one-sidedness preserved). Kinks: at
capacity crossings 1[over] jumps (P is C⁰ there) — measure-zero, same FD
sampling discipline; ψ itself is smooth in s.

**Amendment (same day, pre-probe, from the first build measurement):**
the pure electrostatic form has a flaw the derivation should have caught:
G annihilates constants, so **P_pois measures overload CONTRAST, not
overload** — a uniformly-overloaded configuration has ψ = 0 and P = 0,
and descent drives excess toward uniformity rather than zero (measured:
the small synthetic settled at residual 3.16, WORSE than the local form's
1.46). Fix: the standard two-term composition — **P = P_hinge + P_pois**
(the local hinge², whose zero is exactly feasibility, plus the Poisson
term, which supplies the interior gradient the hinge lacks). Both terms
share the identical chain-rule structure, so the cell weight is simply
the sum: dP/dL = 2·o + ψ·1[over]/cap_scale. The FD gate tests the sum.
(Two-term present+long-range compositions are the classical resolution —
same family as hinge²+μ in s3.25 and McMurchie–Ebeling.)

#### (b) Build + go/no-go verdict (2026-07-30)

Built per (a)+amendment: `_lpinv` cache (the 612ced3e PoissonField
construction), `_psi_weights` two-term composition, FD gradient gate
green on the summed weights, plateau unit tests pass, 518 total.

**Go/no-go smoke FAILED**: the pinned cells are unmoved — P16 spin_glass
28.9 (was 27.4), Z12 turán 57.7 (was 56.1), λ hardened to 16384, stalls
low, descent monotone. The Poisson interior gradient exists (unit tests
prove it) and does not move the real cells: **the plateau was true but
not binding there.** A back-of-envelope feasibility check says spread
configurations exist (total floored mass ≪ total capacity on both
cells), so the obstruction is in the descent's ability to find them, not
in existence. Candidate diagnoses, recorded for the next decision:

1. **Early-settle semantics**: relative-tolerance settlement (1e-4) on
   E_total at large λ·P can fire while absolute progress is still
   meaningful — the trajectory may simply be cut off (check: is P still
   falling when settle fires?).
2. **Hot-spot step throttling**: α is set by the max per-variable force;
   a few extreme-overload cells dominate it, so interior variables move
   microscopically per step — classic ill-conditioning wanting a
   diagonal preconditioner (per-variable step scales or coordinate-wise
   backtracking).
3. **Something structural in the readout** still unaccounted — the
   possibility Max's "is it scary that a group property can be
   implemented directly in the energy" question was pointing at; if (1)
   and (2) are exonerated by a trajectory diagnosis, this rises.

Probe phases not launched. Verdict: two consecutive from-the-record
fixes (Armijo, Poisson) have each been individually validated and
neither moves the pinned cells — the honest read is that the failure is
not yet diagnosed, and the next step should be a DIAGNOSIS probe
(trajectory of P, per-variable step sizes, and a hand-constructed
feasible layout's E_total vs the settled one — is the feasible state
even downhill-reachable?) before any further mechanism is built.

**Step-0 diagnosis addendum (2026-07-30, `data/diag_feasible.py`, Z12
turán): OPTIMIZER-STUCK, decisively.** A hand-built √n×√n spread layout
scores E_total 191,614 vs the settled state's 401,166 (less than half)
at overload 9.2 vs 57.7 — a dramatically better state is downhill of the
descent and unreached (suspect #2, hot-spot α throttling / basin
transport, convicted; suspect #1's tolerance semantics at most
secondary). Second finding: even the hand-spread layout retains overload
9.2 — under the stair readout, turán's PINNED contacts concentrate load
that no node positioning fully relieves, feeding suspect #3 and the
contact round (s3.45) directly.

### 3.45 The contact round: place the edges (Option B unshelved) (2026-07-30)

#### (a) The model — committed before any code, per the standing discipline

Max's reframing ("is minor embedding actually a problem about edges
rather than nodes?") = the 2026-07-19 ledger's Option B, held in reserve.
Qubits host wires; **couplers host edges** — so place the edges.

- **State**: one contact point c_e per source edge, in tile space
  (|E| × 2 reals). Nothing else is state: variables are NETS — v's chain
  is whatever routes through v's contact set, so chain cost is a
  net-wirelength readout, and the current stair model is exactly this
  model with contacts FROZEN at (x_u, y_v).
- **Energy**: E = Σ_v hpwl(C_v) + λ·P(density), C_v = {c_e : v ∈ e}.
  hpwl = x-span + y-span of C_v (bbox proxy for the net's Steiner
  routing; undercounts high-degree nets by a bounded routing factor —
  accepted for Stage 1, recorded). Subgradient: per net, per axis, unit
  pulls on the extreme CONTACTS ((value, edge-id) tie-break); each
  contact sums pulls from its two nets.
- **Density**: per-tile JUNCTION load — bilinear splat of contacts onto
  tiles vs the tile's junction capacity J(tile) = count of physical
  h↔v couplers there (computed once from wire_map + graph edges).
  P = the s3.44 two-term form (hinge² + ½sψ Poisson) applied to this
  point load. **No chain rule through any readout: the placed object is
  the capacity-consuming object.** ∂P/∂c_e flows through the bilinear
  splat weights only (the classical ePlace gradient).
- **Dynamics**: spread init (contacts at endpoint midpoints of a spread
  node layout), the s3.43 Armijo integrator verbatim (frozen-model
  descent: nets' extreme-attribution and the splat's cell assignment
  frozen within a step), cycles with decaying reshake, hardening tail.
  Deterministic throughout.
- **The bridge, restated as bookkeeping**: every edge needs a seat;
  blob area = |E| / junction-density; K_n = the densest seating (the
  triangle/staircase emerges as minimal net-bboxes over all-pairs
  seats); ER at density p interpolates linearly. κ dissolves into local
  junction geometry.
- **Null directions, recorded for later rounds**: within-net contact
  permutations; seat swaps between edges sharing an endpoint. The
  insertion lessons will reincarnate here; out of Stage-1 scope.
- **Readout (Stage 1, deliberately crude, best-effort doctrine)**: snap
  contacts to nearest free physical couplers (greedy, sorted edge id,
  seat-exclusive); the h-side qubit goes to the endpoint whose contact
  set is horizontally wider (tie: lower id); seeds = per-variable unions
  of their contact-side qubits (possibly disconnected — MM legalizes;
  s3.28 measured disconnected seeds repairable). Routing protocol
  unchanged (patience-0 legalize + spur_prune + warm polish).

#### (b) Build + probe verdict (2026-07-30)

Built per (a): `contact.py` (junction_caps, ContactState, energy/forces,
contact_place = the Armijo+cycles+hardening shell, contact_seeds with
qubit-level seat exclusivity). **FD gradient gate passed on the first run
of the real implementation — third consecutive round**; K6 triangle
miniature feasible; 525 tests.

**Probe (Z12, 4 cells, 3 routing seeds vs recorded mm/mm2):**

| cell | contact | mm / mm2 | placement resid | verdict |
|---|---|---|---|---|
| ER100_d10 | **4.65 (3/3)** | 4.97 / 4.86 | 0.0 | **WIN — best ever on the cell; signal-of-life bar MET** |
| spin_glass_n163 | 0/3 routed | 17.87 / 18.36 | **0.26** | placement SOLVED (node model: pinned at 57); readout fails |
| K100 | 17.24 (3/3) | 10.28 / 11.33 | 0.1 | feasible placement; crude readout costs ~7 ACL |
| turan_n162 | 0/3 | 12.01 / 10.99 | **965** | placement itself failed — see below |

Readings, in order of importance:

1. **The edge-placement thesis scored its first real win on its home
   cell**: ER100 4.65 beats both mm arms with EXACT seating feasibility —
   every edge got a coupler, first probe, crude readout. "Each edge needs
   a seat" is now a measured mechanism, not a metaphor.
2. **The pinned-density problem is solved in contact variables**:
   spin_glass settles at residual 0.26 where the node model was pinned at
   57 through three rounds of fixes. The failure MOVED — from placement
   (fundamental) to readout (engineering): Stage-1's disconnected
   contact-union seeds are unroutable at n≈163 within budget. Named next
   step: Stage-2 readout — connect each net's seats (SPH tree over its
   contact qubits; trees.py machinery exists).
3. **K100 same shape**: feasible triangle-ish placement (hpwl 1095,
   resid 0.1), big routed gap from seed disconnection. Crystal-corner
   competitiveness awaits the same Stage-2 readout.
4. **turán reproduced the s3.44 conditioning diagnosis, undiluted**:
   all cross-block contacts init into one central pile (~8.7k contacts
   between three blocks), and global-α Armijo cannot spread a
   1000-deep pile (dmax throttling: interior motion ~1/dmax per step) —
   suspect #2 from the s3.44 list, now isolated in a clean setting.
   Named next step: per-contact (diagonal) preconditioning, doubly
   motivated by step-0's optimizer-stuck conviction.
5. Wall-time 7–23 s at |E| up to 8.7k — inside the bar, unoptimized.

**Verdict: the round Max asked for — promising, with the next two moves
named by the data**: (i) Stage-2 readout (net routing over seats),
(ii) diagonal preconditioning for pile spreading. No default changes;
the contact model is the first line in this program to beat minorminer
on a liquid-family cell.

### 3.46 Contact Stage 2: connected readout + preconditioning — one bar of four; the gridlock and the stubborn pile (2026-07-30)

Built per plan: (A) connected readout — seats joined per variable by
early-exit BFS through free fabric, connectors claimed, unreachable
seats dropped AND released; (B) per-contact force clipping replacing the
global 1/max|f| step scale, both loops. 526 tests (readout contract:
connected/disjoint/deterministic/edge-covering; K6,6 pile miniature
settles ≤0.5 — honesty note: added post-patch, red-first check skipped).

**Probe (same protocol/baselines as s3.45):**

| cell | Stage 2 | Stage 1 | mm/mm2 | bar | verdict |
|---|---|---|---|---|---|
| ER100_d10 | 4.72 (3/3) | 4.65 | 4.97/4.86 | ≤4.9 | **✓ win holds** |
| K100 | 15.50 (3/3) | 17.24 | 10.28/11.33 | ≤13 | ✗ (improved 1.7) |
| turan | 15.53 (2/3!) | 0/3 | 12.01/10.99 | resid ≤1 | ✗ resid 928 — but ROUTES now |
| spin_glass | 0/3, resid 4.63 | 0/3, resid 0.26 | 17.87 | 3/3 | ✗✗ placement DEGRADED |

Two sharp findings:

1. **Readout gridlock**: the exclusive connector claiming starves later
   variables — dropped seats: K100 2410/4950 (49%), spin_glass
   2823/~3900 (72%), ER 466/505 (92%!). ER still wins because near-
   singleton seeds + MM ≈ Stage 1 there, but on dense cells the
   sequential greedy readout destroys the seating it was built to
   transmit. Named fix candidate (NOT built): **connect without
   claiming** — connectors overlap freely and MM's overlap pricing
   resolves them (overlap is priced, not forbidden — minorminer's own
   design premise; our exclusive claiming was more rigid than the
   router we hand off to). Note the irony: a negotiated readout is
   minorminer's legalization re-invented — the right division may be
   connected-overlapping seeds (cheap) + MM negotiation (theirs).
2. **The turán pile survives the preconditioner** (resid 965 → 928; the
   K6,6 miniature passed, the K81,81 original didn't) — so the pile is
   NOT merely step-size throttling at scale. Standing hypothesis: an
   attraction-dominated equilibrium (all 162 nets pull their ~81
   contacts toward the shared midline; the net pulls are the pile's
   glue, and hardening λ fights n·deg worth of them). Needs a genuine
   diagnosis round (per-term force decomposition at the pinned state),
   not another integrator patch — two integrator patches have now
   under-delivered on this cell.
   Meanwhile the connected readout salvages turán to 15.5 (2/3) from a
   TERRIBLE placement — evidence the readout direction is right even
   where the placement is wrong.

Score: 1 of 4 bars. Per the failure protocol: report + discuss.
Positive core intact: ER win reproduced twice (4.65/4.72 vs mm
4.97/mm2 4.86); the model's home cell is stable. No default changes.

### 3.47 The reunification experiment: the L-model matches or beats the contact model everywhere; corners-only state confirmed (2026-07-30)

The measurement the contact rounds never made (`pipeline_z12_probe.py`):
the registered attraction default (corners + derived arms + arrange +
wire seeds, Zephyr adapter, derived κ ≈ 17) under the full routed
protocol on the four Z12 cells. Decision framing pre-registered in the
script header.

| cell | pipeline | contact (s3.46) | mm | mm2 |
|---|---|---|---|---|
| K100 | **12.21 (3/3)** | 15.50 | 10.28 | 11.33 |
| ER100_d10 | **4.81 (3/3)** | 4.72 | 4.97 | 4.86 |
| turan | **14.03 (3/3)** | 15.53 (2/3) | 12.01 | 10.99 |
| spin_glass | **19.85 (2/3)** | 0/3 | 17.87 (3/3) | 18.36 |

**Verdict: reunification CONFIRMED.** The pipeline dominates the contact
model on three cells and ties it within the mm null on the fourth (ER
gap 0.09 vs null 0.11) — per-edge freedom buys nothing measurable even
on the contact model's home cell, at 60× the state and none of the
structure. The corners-only state (arms, orientations, seats all
derived) is the right representation; the contact detour's enduring
value is the UNDERSTANDING it forced: seats are the real constraint,
Zephyr's junction-completeness makes them a theorem given distinct
wires, gauge freedom is the optimizer's enemy, and mm's overlap pricing
is lexicographic (Max's correction, from mm-internals — the
"overlap-is-chill" fiction traced to the paper-vs-program table).

Z12 standings after the first-ever untuned pipeline run there: WE hold
ER (4.81 and 4.72 both beat mm 4.97 — two independent models, twice
each); mm holds K100 (10.28), turan (12.01), spin_glass (17.87 3/3 vs
our 2/3). Zephyr is mm-friendly terrain (paper3's finding, now at cell
level for our own line). The obvious next opportunity, recorded: the
crystal-cell gap on Z12 is exactly where s3.37's wire-exact matching was
throttled by Pegasus's 56% junctions — on Zephyr the matching's
existence assumptions hold; `wire_exact=True` on Z12 is unmeasured.

Contact model disposition: retires to probe-callable status with the
ledger carrying its lessons; `contact.py` stays (tested, FD-gated) as
the measurement instrument it proved to be. No default changes.

### 3.48 The Zephyr triad: the terrain belongs to templates, not minorminer; the matching has a Zephyr coordinate bug; shapes converge post-polish (2026-07-30)

`zephyr_triad.py`, three parts, readings pre-registered in the plan.

**Part 2 — template truth (the commanding result).** Z12 K_max = 184 —
so EVERY cell we contest (n ≤ 163) is inside clique-template coverage,
which was never true on P16 (K_max ~150). The truth table:

| cell | template(-restriction) | mm | our pipeline |
|---|---|---|---|
| K100 | 8.00 | 10.28 (1.29×) | 12.21 (1.53×) |
| K140 | 11.00 | ~18.6+ | 19.34 (P16) |
| turan_n162 | **6.00** | 12.01 (2.0×) | 14.03 (2.3×) |
| spin_glass_n163 | **11.64** | 17.87 (1.54×) | 19.85 (1.7×) |

**Minorminer did not conquer Zephyr — busclique did.** mm sits 1.3–2.0×
above template-restriction on every dense cell; the crude K_n-restriction
(relabel + spur_prune, 60 s of nothing) HALVES mm's turán. The "mm got
good on Zephyr" story from s3.47 was measured against the wrong
adversary: the real reigning algorithm on Z12 dense terrain is the
constructive template, and both search lines (mm and ours) are far from
it. The program's thesis (flexible near-busclique structure) now has a
measured mountain with a number on it: turán at 6.00.

**Part 3 — chain shapes (post-polish caveat: MM's grind reshapes, so
this measures the OPTIMUM's shape more than the seeds').** Segments per
chain, mm vs ours: ER 2.48/2.45 (agree), turán **1.39/1.85 median 1**
(both discover straight-wire chains — the biclique-optimal shape; the
L-model's shape is RIGHT here, its placement is 2.3× off), K100
2.93/3.91 (mm uses ~3 segments — even mm deviates from the pure L),
spin_glass **4.81/4.53 median 4** (chains are 4–5-segment paths; the
single-bend L is the wrong Zephyr shape for irregular-dense). Note ours
≈ mm on shape stats nearly everywhere — the differentiator is WHERE
chains sit, not their form; and single-seed noise even had ours beating
mm on spin_glass this run (16.96 vs 18.14).

**Part 1 — wire_exact on Z12: neutral, and the metric exposed a bug.**
Routed ≈ the s3.47 pipeline within noise on all four cells. Designated
satisfaction: K100 61.6% — the exact Pegasus plateau, on the fabric
whose junctions are complete; ER/turán/spin_glass 25–27%, BELOW Pegasus
levels. Per the pre-registered reading this is a Zephyr-specific bug,
and the suspect is identified: `_couples(grid, r, s_h, c, s_v)` indexes
an h-wire's run by the perpendicular LINE index (c ∈ 0..2m), but Zephyr
runs are keyed by position p = 2z+j (0..2m−1) — two different coordinate
spaces (they coincide on Pegasus/Chimera, diverge on Zephyr). The
matching optimized, and the metric counted, against garbage lookups.
Every wire_exact/coupler claim on Zephyr is unfounded until `_couples`
gets a per-family crossing-index map. Fix ticket on the ledger; the
greedy default path is unaffected (its runs are real coupled paths —
adapter-tested).

**Synthesis — the data picks the road.** Not packing tuning (shapes and
stats say our placements are mm-class already), not the multi-segment
representation first (a real question, but second-order next to a 2×
gap), and not the matching (bugged on this fabric). The road is
**template-gap closure on Z12**: the terrain's true champion embeds
turán at 6.00 with zero search, and neither search line is within 2× of
it. Options for the next decision, in tension with each other: (a)
contain — the §3.26 template-rival arm (run the restriction, keep the
better; brutal numbers, but it's busclique's win, not ours); (b) learn —
make the L-model FIND restriction-like structure (on turán it already
produces the right SHAPE at the wrong places; the delta is pure
organization, exactly the crystal machinery's jurisdiction, now with a
6.00 target instead of folklore); (c) both, with (a) as the floor while
(b) is the research line. Max's call.

### 3.49 The Zephyr anatomy session: template-6 explained, the j-fold convicted, the bestiary founded (2026-08-01)

Diagnosis round with Max on why template turán = 6.00 and what the 2.3×
pipeline gap actually is. All claims measured directly on Z12 (busclique +
adjacency probes); full anatomy now in **`fabrics.md`** (new organized
reference: the target-graph bestiary, one section per fabric, translation
checklist for the next one). Headlines:

1. **The 6 is lane arithmetic, sharp to one variable.** Zephyr junctions
   are complete K_{8,8} (verified 64/64); a bar spans 2 junctions and
   meets 16 distinct opposite sub-lanes (one coupler each, zero waste);
   a straight lane of L bars meets 16L. Turán: ⌈81/16⌉ = 6, and 16·5 =
   80 makes K_{81,81} exactly one variable over the L=5 line (measured:
   K_{80,80} restriction 5.5, K_{81,81} 6.0 uniform).
2. **Clique = biclique + one arm, quantitatively.** K162 template ACL
   12.00 = exactly 2 × turán's 6.00 (the L-chain's two arms serve the
   two blocks; bipartiteness deletes the own-block arm). §3.35's "the
   diagonal already contains the biclique" holds on Zephyr to the digit.
   The One Shape survives; "contain" is unnecessary if the representation
   can spell it.
3. **The pipeline's 14.03 is a representation ceiling, not a Laws
   failure.** The template's lanes are same-course (j-fixed) external-
   coupler runs, nested 2 per track (courses interleaved). The TileGrid
   Zephyr adapter folds j into the along-position ("what makes runs
   contiguous"), so the claimable object is the odd-coupler zigzag: ~8
   fresh contacts per bar instead of 16, nesting unclaimable — folded
   floor ~10–11, unnested ~20, observed 14.03; mm's 12.01 sits near the
   same ceiling (search doesn't find stride-2 either). Odd couplers are
   confirmed pure flexibility: 0/184 K184 chains use one; turán template
   is pure external. κ ≈ 17 (degree-derived) is accidentally calibrated
   to the *unfolded* rate — the floor under-provisions claimable arms
   ~2×.
4. **Fix direction (unbuilt, awaiting design round):** unfold the
   adapter (sub-lane = (k, j), position = z; same-course runs stay
   contiguous via external couplers, so the fold's motivation is met by
   the unfold), re-derive κ from measured fresh-contact rate of the
   claimable run, then the pre-registered bar writes itself: turán
   descending from 14 toward 6 + router overhead, clique cells pulled
   toward their halved arithmetic by the same change — one
   representation fix moving both regimes, per the interpolation thesis.
   The `_couples` line-vs-position bug (§3.48) remains a separate fix
   ticket.

### 3.50 The course round: Zephyr unfolded, the dense board swept, K140 rescued from 0/3 (2026-08-01)

Built per the s3.49 fix direction, as the `courses` switch (default off =
folded stock; house rules): Zephyr adapter emits sub = 2k+j under the
flag (position stays p = 2z+j, geometry/caps unchanged); `grid.stride`
(2 iff course-resolved Zephyr) is the single mode signal consumed
downstream — `_target_kappa` becomes fresh-contacts-per-tile
(cross-orientation degree / stride ≈ 7.7 on Z12, replacing the folded
18 that under-provisioned arms 2×), `_couples` gains the parity lookup
(bar crossing line c sits at p = c or c−1 by course parity; verified
64/64 at interior junctions — the first sound coupler predicate on
Zephyr, s3.48 bug fixed IN COURSE MODE ONLY), and arrange's line pool
scales by stride (8 interleaved course arms per line). Claim loops
needed zero changes (gap-tolerant `run.get`). Stride-1 fabrics are
structurally untouched (invariance tests). 535 tests green (9 new).

**Probe** (`data/course_probe.py` / `.csv`, bars pre-registered in the
docstring before any run; Z12, 5 cells × 3 arms × 3 seeds × 60 s,
6 niced workers, quiet box):

| cell | default | courses | courses+exact | mm / mm2 | template |
|---|---|---|---|---|---|
| K100 | 11.92 | 10.57 | 10.57 | 10.28 / 11.33 | 8.00 |
| K140 | **FAIL 0/3** | **14.04 (3/3)** | 14.23 | 18.27 (2/3) / 18.91 | 11.00 |
| ER100_d10 | 4.81 | 5.09 | 5.09 | 4.97 / 4.86 | — |
| turan_n162 | 13.30 | 10.02 | **9.72** | 12.01 / 10.99 | 6.00 |
| spin_glass_n163 | 17.14 (2/3) | **14.01 (3/3)** | 14.07 | 17.87 / 18.36 | 11.64 |

Scorecard vs the pre-registered bars:

1. **MINIMUM: passed on turán decisively** (10.02 / 9.72 vs the <12.01
   bar — beats mm AND mm2), spin_glass legality 3/3 (bar ≥2/3) — but the
   no-regression clause FAILS on the letter at ER: 4.81 → 5.09 (+0.28,
   beyond the ~0.11 mm null). Suspected mechanism, recorded not tested:
   κ 18 → 7.7 flips sparse floors from inactive (deg/κ−1 < 0) to active
   (~0.3 tiles) — a knob interaction, not lane physics; a
   floor-threshold or per-regime κ probe would isolate it.
2. **STRETCH: K100 ≤ 11 MET (10.57); turán ≤ 9 missed by 0.72** (best
   seed 9.03). Template gaps close from 1.53× / — / 2.34× / 1.70× to
   **1.32× / 1.28× / 1.62× / 1.20×** (K100/K140/turán/spin_glass).
3. **Unregistered headline: K140.** The folded pipeline FAILS 0/3 on
   Z12 K140; courses legalizes 3/3 at 14.04 — below mm's 18.27 (2/3)
   by −4.2 with a feasibility win on top. The representation was a
   feasibility ceiling too, not just a quality one.
4. **The dense Z12 board vs minorminer after one flip: 3 wins, 1 near-tie.**
   K140 −4.2, spin_glass −3.9 (with 3/3 vs mm's 3/3 at 17.87), turán
   −2.3; K100 10.57 vs 10.28 (mm holds by 0.29). mm holds ER (5.09 vs
   4.97). Course wall-clock is also ~2–3× faster to legality (turán
   ~20–30 s vs 60; the lanes route almost without negotiation).
5. **wire_exact in course mode** (first sound run on Zephyr): −0.30 on
   turán (9.72, the new cell record), neutral-to-noise elsewhere
   (K100/K140/ER byte-close to greedy). The co-design question now has
   a working instrument on the fabric it was built for.

Defaults unchanged (`courses=False`) per the no-flip decision rule; the
flip (and the ER floor interaction) are the next discussion. Docs:
`fabrics.md` §4.5 updated, `anatomy.md` knob roll-call + representation
note, `attraction.md` ledger entry.

### 3.51 The coloring acquitted; the compaction gap convicted (2026-08-01)

Two probes from the post-s3.50 diagnosis discussion (Max: tracks/courses
are coordinate illusion — Zephyr is "just big Chimera" with length-2
overlapping qubits, each line admitting two disjoint end-to-end tilings;
and "see what happens if we ignore all this silly coloring stuff").

1. **Terminology correction on the record**: the "nesting" claim of the
   s3.50 dissection was double-counting from the track vocabulary — in
   the wire frame the turán template gives each variable exactly ONE
   whole wire (162 chains, 162 sub-lanes). End-to-end wire sharing is
   structurally impossible inside a bipartite rectangle (every lane must
   span the opposite block); it is real only for clique staircases
   (complementary arm lengths — K100's residual) and sparse locals.
2. **The coloring is acquitted** (`data/lane_probe.py`): a ~25-line
   whole-lane seeder (count to capacity, spill to nearest line, no
   interval graph) produces BYTE-IDENTICAL routed results to
   wire_seeds_iv on K100/K140/turán (10.57/14.15/10.12; spin_glass
   within noise) on identical geometry — on Zephyr crystal terrain the
   interval coloring already degenerates to counting. Max's "coloring is
   polish, mostly a Pegasus artifact" — confirmed literally.
3. **The compaction gap is convicted** (stage trace, turán): init
   spreads B's centroids 19.8 tiles (minimal ~10); the pipeline's single
   stair_step leaves 19.3 (8 steps: 15.9 — attraction contracts but
   slowly, and geo_iters=1); arrange then packs arms to the NEAREST line
   with room — no compaction force exists — freezing THREE separated
   clumps ({2-7},{11-15},{19-23} at 7/line); every opposite arm must
   span the smear: v-intervals mean 16.8 vs the rectangle's 11. The
   final ~10 ACL vs template 6 is this smear, end to end. Same
   Gauss's-law shape as s3.19/s3.43: local placement rules cannot merge
   distant clumps.
4. Two mechanical notes: line capacity lands at 7/line not 8 (pool =
   grid-mean cap x stride is dragged down by the degenerate boundary
   line; per-line sub counts would give 8); and the fragmentation
   observed in s3.50 is the router extending under-spanned seeds across
   sibling wires, downstream of the same smear.

**Candidate fix (undesigned, awaiting discussion)**: compaction in the
packer's line-selection policy — fill lines contiguously from the bundle
median outward (E-gated as everything else; for complete-overlap arm
sets contiguous center-out fill IS the template layout), plus per-line
sub-count capacity. Predicted from the arithmetic: B on 11-12 contiguous
lines, intervals ~11-12, turán toward ~7.

### 3.52 The shake round: turan 7.70, minorminer beaten on every Z12 cell; cycle 0 is the mechanism; the E-proxy inverts on K140 (2026-08-01)

Built per plan from Max's magnet-ball design: the s3.41 settle-and-reshake
shell transplanted onto stair-E as `shake_cycles`/`shake_steps` (default
0 = stock, byte-identical), keep-best (E, unplaced), deadline-guarded;
`masked_pool` (7.68 -> 8 line capacity, s3.51 item 4) as its OWN
default-off switch after design-round pre-validation measured it moving
pack-level E the wrong way. 538 tests green. Design-round measurements
on record: stock geometry frozen at E 3088; shell cycle 0 alone 2674;
4-cycle shell 3.76 s.

**Probe** (`data/shake_probe.py` / `.csv`, bars pre-registered; Z12,
5 cells x 5 arms x 3 seeds x 60 s. Load caveat: an external batch
re-entered mid-run (load 60-115); scored anyway because the paired
control replicated s3.50's quiet-box values to the hundredth on 4/5
cells and legality is 3/3 everywhere -- no s3.38 starvation signature):

| cell | courses (ctl) | shake1 | shake | pool | shake_pool | tmpl |
|---|---|---|---|---|---|---|
| K100 | 10.57 | 10.02 | 10.02 | 10.37 | **9.67** | 8.00 |
| K140 | 13.92 | 14.17 | 14.79 | 13.62 | **12.16** | 11.00 |
| ER100_d10 | 5.09 | 4.70 | 4.81 | **4.66** | 4.81 | -- |
| turan_n162 | 10.02 | **7.70** | **7.70** | 9.19 | 9.45 | 6.00 |
| spin_glass | 14.01 | 14.21 | 14.21 | 14.47 | **13.93** | 11.64 |

Scorecard vs the pre-registered bars:

1. **MINIMUM: turan passed emphatically** (7.70 vs the <=9.0 bar and the
   10.02 paired control; mm 12.01), spin_glass 3/3 -- but the
   no-regression clause FAILS on K140 in the registered shake arm
   (13.92 -> 14.79, beyond noise). **STRETCH: K100 <= 10.28 MET**
   (10.02 -- the first K100 win over minorminer in program history);
   turan <= 7.5 missed by 0.20.
2. **Attribution is total: cycle 0 IS the mechanism.** shake1 = shake
   byte-identically on 4/5 cells (identical ACL and E) -- keep-best
   discarded every reshake everywhere except K140. "Contract before the
   first pack" was the entire remedy; the decaying-amplitude reshakes
   add nothing on this board (kept as cheap insurance; K140 says even
   that is not free).
3. **The E-proxy inverts on K140 and under pool.** K140: 4-cycle shake
   found LOWER E (2660 vs 2788) yet routed WORSE (14.79 vs 14.17);
   pool arms: pack-E worse (turan 3703 vs 3088) yet routed BETTER
   (9.19 vs 10.02). Stair-E is a good but imperfect proxy for routed
   ACL near the optimum -- selection on E alone has a measured failure
   mode (the s3.16 legal-vs-polished lesson, one level up).
4. **The report-only pool arms are the sleeper hit**: shake_pool takes
   K100 9.67, K140 12.16, spin_glass 13.93 -- all program records --
   and pool alone takes ER 4.66 (< mm 4.97). The pre-validation E
   warning was real but routing forgave it; the capacity fix helps
   cliques (arms genuinely need 8/line) while diluting turan's shake
   win (9.45 vs 7.70 -- interaction unexplained, on the ledger).
5. **Standing Z12 board, best measured arm per cell: minorminer is
   beaten on all five cells** -- 9.67 / 12.16 / 4.66 / 7.70 / 13.93 vs
   mm 10.28 / 18.27(2/3) / 4.97 / 12.01 / 17.87. Template gaps:
   1.21x / 1.11x / -- / 1.28x / 1.20x (from 1.53x / -- / -- / 2.34x /
   1.70x two days ago). The s3.50 ER regression is healed (shake/pool
   both fix it; geometry E 286 -> 41).

Defaults unchanged (all three switches off) per the no-flip rule. The
flip discussion now has a real menu: shake1 (cheap, huge on turan/K100,
mild K140/spin_glass cost), pool (cliques/ER), or per-regime. Open
items: the K140 E-inversion, the pool-x-shake interaction on turan, and
whether (E, unplaced) selection should consult capacity pressure.

### 3.53 The discrete-shake round: order moves at scale work (turan 7.19), inversion is null under the confound, and the E-proxy inversion becomes a pattern (2026-08-01)

Built per plan: `order_shake` (segment reversals + block relocations at
decaying scale L = n/2..2, sharing insertion's rank-space proxy via the
factored `_order_proxy`; chained before insertion inside the SAME
true-E-gated composite -- coarse moves raise raw E before fine repair, so
separate gates would reject them all) and `shake_invert` (reshake cycles
do radial RANK REVERSAL about the centroid instead of dilation -- the
s3.52 finding that dilation preserves radial order made the core
uncontestable). Design-validated numerically before build (reversal
involution proxy-exact; block-move masks generalize insertion's L=1
bit-exactly, destination clamp [0, n-L]; anchor arrays are order-aligned
and must be realigned per call -- a caught would-be bug). 544 tests green.

**Probe** (`data/dshake_probe.py` / `.csv`, reading pre-registered; Z12,
5 cells x 4 arms x 3 seeds x 60 s, 12 workers on a quiet box; base
replicated the s3.52 shake1 values -- scorable):

| cell | base | invert | dshake | both | tmpl |
|---|---|---|---|---|---|
| K100 | 10.02 E1383 | 10.02 | 10.02 | 10.02 | 8.00 |
| K140 | 14.25 E2788 | 14.86 E2755 | 14.17 | 14.86 E2755 | 11.00 |
| ER100_d10 | 4.70 E66 | 4.85 E51 | 4.70 | 4.85 E51 | -- |
| turan_n162 | 7.70 E2674 | 7.70 | **7.19** E2671 | 7.38 E2563 | 6.00 |
| spin_glass | 14.21 | 14.21 | 14.10 | 14.10 | 11.64 |

1. **order_shake: the mechanism is real.** turan 7.70 -> 7.19 paired
   (template gap 1.20x, best the program has seen), spin_glass -0.11
   (marginal), zero regressions anywhere, and K100's exact tie is the
   symmetry argument confirming correctness (order moves provably inert
   on K_n). The coarse-to-fine order anneal reaches states insertion
   alone could not -- Max's "discrete form of shaking" hypothesis
   confirmed on exactly the cell class (block-structured) it predicted.
2. **shake_invert: null-to-harmful, UNDER THE RECORDED CONFOUND.** It
   never improved a cell; keep-best discarded the inversion on 3/5
   (byte-identical to base) and kept it on K140/ER where it LOWERED E
   yet routed worse. The pre-registered escape clause applies: the
   post-inversion resettle had no order repair (order search gated to
   cycle 0). "Inversion without post-inversion order search is null";
   all-cycles order search is the next flip if inversion is pursued.
3. **The E-vs-routed inversion is now a PATTERN, not an incident**:
   K140 (s3.52 and again here), ER (E 66->51, ACL 4.70->4.85), and
   both-arm turan (E 2563 -- the round's lowest -- routing 7.38 > 7.19).
   Every mechanism that pushes geometric E below the base settlement
   routes slightly worse. Standing suspect: router slack (s3.52 item 3)
   -- tighter placements starve repair space. This is the round's real
   discovery: stair-E selection is systematically exploitable near the
   optimum, and a slack-aware selection term is the named next design
   question.
4. Unrun combination on the ledger: dshake x masked_pool (the s3.52
   clique records used pool; dshake's turan record didn't). The
   per-cell best board stands at K100 9.67 / K140 12.16 / ER 4.66 /
   turan **7.19** / spin_glass 13.93 -- every cell beats minorminer;
   template gaps 1.11-1.28x.

Defaults unchanged (five switches, all off) per protocol. Flip menu and
the slack-aware selection question go to discussion.

### 3.54 The exact-seeds round: K140 at 1.04x template with minorminer SKIPPED; the slack tax abolished where it was worst; turan trades against it (2026-08-02)

Built per plan: `complete_seeds` (corner + edge + bridge passes; parity
extension formula verified an exact iff over all 36,864 Z12
cross-orientation couplers), boundary-line avoidance (the NEW Zephyr
anatomy fact of the design round, fabrics s4.3b: lines 0/2m have HALF
crossing capacity -- parity-blind packing there created 245 structurally
uncoverable turan crossings), the mm-skip gate (valid seeds bypass
legalization entirely; minorminer verified from C++ source to
verify-and-return valid initial_chains), and `cover_select` (keep-best
on post-claim coupler deficit; the cheap interval estimate measured
VACUOUSLY ZERO -- intervals contain their crossings by construction).
550 tests green.

**Probe** (`data/exact_probe.py` / `.csv`, bars pre-registered; Z12,
5 cells x 6 arms x 3 seeds x 60 s, 12 workers, quiet box; s = mm_skips,
d = residual deficit):

| cell | base | dshake | exact | exact0 | exact4 | cover4 | tmpl |
|---|---|---|---|---|---|---|---|
| K100 | 10.02 | 10.02 | **8.73** s1 d0 | 10.19 s1 | 8.73 s1 | 8.73 s1 | 8.00 |
| K140 | 14.17 | 14.17 | **11.40** s1 d0 | 13.15 s1 | 11.40 s1 | 11.40 s1 | 11.00 |
| ER100 | 4.70 | 4.70 | 4.76 d363 | 5.00 d275 | 4.73 | 5.03 | -- |
| turan | 7.70 | **7.19** | 9.44 d729 | 9.00 s1 d0 | 9.44 | 8.43 s1 d0 | 6.00 |
| spin_glass | 14.21 | 14.10 | **12.51** d10 | 12.70 d21 | 12.51 | 15.84 s1 d0 | 11.64 |

Scorecard:

1. **MECHANISM BAR: passed emphatically.** The gate fires 3/3 on
   K100 and K140 in every exact arm (deficit 0, minorminer legalization
   SKIPPED), plus turan exact0/cover4 and spin_glass cover4. Validity by
   construction is real and routine on the crystal cells.
2. **Where the slack tax was worst, abolishing it pays exactly as
   predicted: K100 9.67 -> 8.73 (1.09x template), K140 12.16 -> 11.40
   (1.036x -- essentially template-level), spin_glass 13.93 -> 12.51
   (1.07x; residual d10 routed off a near-complete warm start).** These
   are the three cells of the s3.52/s3.53 E-inversion pattern; with
   repair abolished, tight geometry stopped being punished.
3. **MINIMUM BAR FAILED on turan -- the predicted hiccup, localized.**
   Exactness and turan's best geometry currently conflict: the
   dshake-tight packing is incompletable (d729; the s3.53 E-leak
   quantified: lower E -> 3x deficit), and boundary avoidance disturbs
   the near-perfect lane layout, so exact arms land 8.43-9.44 vs
   dshake's 7.19. The fix direction is co-design (completion-aware
   packing), not more completion.
4. **cover_select: mixed, stays off.** Helps turan (8.43 vs 9.44 --
   deficit-first selection picks completable geometry), identical on
   cliques, HARMFUL on spin_glass (15.84: forcing deficit-0 selects a
   bad-E settlement). Deficit and E must be traded, not ordered.
5. **ER: no benefit, no harm** (d275-363 -- liquid cells never gate;
   ACL within noise). Max's prediction that exactness helps liquid
   cells: not confirmed at this seed granularity.

**Standing best-arm board vs templates: 8.73/8.00, 11.40/11.00,
7.19/6.00, 12.51/11.64 -- gaps 1.09x / 1.04x / 1.20x / 1.07x** (from
1.53x/--/2.34x/1.70x five days ago). All cells beat minorminer by
1.2-1.6x. Open: the turan exactness-geometry conflict (co-design),
deficit-E tradeoff in selection, ER liquid regime untouched by
exactness. Defaults unchanged (seven switches, all off).

### 3.55 The identity audit: the off-template board swept, completion helps where no template exists (2026-08-02)

Max's challenge after s3.54 ("if we collapse into worse templates we are
nothing — make sure the policies help on graphs for which templates
don't exist or are not near-optimal"). Probe (`data/offtmpl_probe.py` /
`.csv`, bars pre-registered): five Z12 cells busclique cannot address —
liquid (ER100), sparse structured (regular_n316, ws_n486), multi-patch
(wsc c8xK32, c3xK64) — stock mm as fresh paired baseline vs the switch
stack in increments. Load caveat: external batch active (load 44-66);
scorable — ER base replicated its quiet-box 4.70 exactly.

| cell | mm | base | dshake | exact (stack) |
|---|---|---|---|---|
| ER100_d10 | 4.97 | **4.70** | 4.70 | 4.76 |
| regular_n316 | 3.36 | 2.76 | 2.75 | **2.75** |
| ws_n486 | 3.08 | 3.35 | 3.35 | **3.01** |
| wsc_c8xK32 | 3.78 | 3.78 | 3.75 | **3.74** |
| wsc_c3xK64 | 7.31 | 7.48 | 7.42 | **7.22** |

1. **IDENTITY BAR: PASSED 5/5** (bar was >=4/5): best-of-stack beats or
   ties mm on every off-template cell — regular_n316 by -18% (2.75 vs
   3.36), ER -0.27, ws -0.07, wsc_c3xK64 -0.09, wsc_c8 tie-win. The
   dense-round tuning did NOT overfit; the algorithm's home terrain is
   intact and improved.
2. **EXACTNESS OFF-TEMPLATE: PASSED, and better than the bar** — exact
   never regresses beyond noise vs dshake, and IMPROVES ws_n486
   (3.35 -> 3.01, flipping a cell mm was winning) and wsc_c3xK64
   (7.42 -> 7.22, likewise). Completion is measured to be what it
   claims: graph-agnostic finishing that reduces router churn — Max's
   "exactness helps liquid/sparse too" prediction lands on ws/wsc
   (not ER, where it is noise-neutral).
3. Notable: the two cells the stack was BEHIND mm on (ws, c3xK64) are
   exactly the ones exact_seeds rescued — off-template, the router-churn
   reduction is the differentiator, not the gate (mm_skips ~0 there).

Verdict: the worse-templates collapse is measured not to be happening —
the stack wins on terrain where no template exists, and the completion
mechanism is part of WHY it wins there. The program's thesis (one
general algorithm bridging busclique's crystal and minorminer's liquid)
now has supporting measurements on both ends of the bridge.

### 3.56 The snap round: aim-don't-repair confirmed (extensions -> 0), turan gates valid at 8.04, and the d729 re-attribution (2026-08-02)

HONESTY ITEM FIRST — s3.54's turan attribution is corrected: the d729
residual was NOT misalignment. Design-round simulation on the real
geometry found 4 columns packed to interval depth 9-12 against 8
sub-lanes: 9 arms never received a wire at all, and 9x81 = 729 (every
residual edge incident to exactly those 9 variables). Snap cannot color
the uncolorable; **oversubscription in the packer is the named remaining
turan blocker** (a future packing round). The simulation also exposed
that the s3.54 matrix never ran dshake+exact together — and predicted
that combination completes turan to d0.

Built: `snap_claims` (wire_seeds_iv takes src_adj; claims are aimed at
the stair-assigned contacts' lines parity-exactly at color time, hull of
the original interval and p* = c if c%2==s%2 else c-1; participation
gate stays on the original interval; parity-agnostic hull widening kept
as a zero-cost guard, measured inert). 553 tests green.

**Probe** (`data/snap_probe.py` / `.csv`, bars pre-registered; Z12,
5 cells x 3 arms x 3 seeds x 60 s, quiet box; all arms courses +
shake_cycles=1 + order_shake=1; s=mm_skips d=deficit e=extensions):

| cell | dshake | exact_ds | snap | tmpl |
|---|---|---|---|---|
| K100 | 10.02 | 8.73 s1 d0 e100 | 8.74 s1 d0 **e0** | 8.00 |
| K140 | 14.17 | 11.40 s1 d0 e123 | 11.41 s1 d0 **e0** | 11.00 |
| ER100_d10 | 4.70 | 4.76 d363 | 4.76 d367 | -- |
| turan_n162 | **7.19** | 8.04 s1 d0 e77 | 8.04 s1 d0 **e0** | 6.00 |
| spin_glass | 14.10 | 12.77 d4 e193 | **12.66** d4 e42 | 11.64 |

1. **MECHANISM: passed completely.** Snap zeroes the extension passes on
   every gating cell (e100/e123/e77 -> 0; spin_glass 193 -> 42, the
   residue from oversubscribed arms) at byte-equal ACLs — completion is
   now a verifier, exactly as designed. And the missing arm behaved as
   simulated: **turan completes to d0 and GATES VALID under
   dshake+exact** (s1 d0, all three seeds).
2. **MINIMUM: one clause failed, honestly.** turan exact arms land 8.04
   -- above the <=7.70 bar (though far below s3.54's 9.44/8.43: the
   exactness price on the cell collapses from +2.25 to +0.85). All
   other cells hold their s3.54 values (K100/K140 identical; spin_glass
   12.66 within the cell's noise of 12.51, and snap is its best exact
   number yet). STRETCH (<=7.19) not met.
3. **The turan ledger is now exact**: 7.19 (non-exact dshake, router
   negotiated) vs 8.04 (valid-by-construction, minorminer never
   legalizes). The +0.85 gap is the oversubscription defect plus
   boundary-avoidance's shaved lanes — both packing-side. When packing
   respects depth 8, the two numbers should meet; that is the next
   round's precise target.
4. snap is ACL-neutral by design and slightly positive on spin_glass;
   its enduring value is structural: cover_select now scores the exact
   claim layer, and every deficit that remains is a packing fact, not a
   claiming artifact.

Standing best-arm board: K100 8.73 / K140 11.40 / ER 4.66 / turan 7.19
/ spin_glass 12.66 — template gaps 1.09x / 1.04x / -- / 1.20x / 1.09x.
Eight switches, all default-off. Open: the oversubscription packing
round (turan's last conflict), the flip council.

### 3.57 The overload-gate round: feasibility priced into the energy — turan's exact arm 7.90, nothing else moved (2026-08-02)

Max's design, verbatim brief: "feasibility is part of the energy...
figure out the good way to put the penalty in the energy and see if
that fixes turan and nothing else breaks." Built as `overload_lam`:
every existing E-gate and cycle selection scores stair-E + lam *
hinge^2 of the CLAIM LAYER'S OWN line-capacity census (`claim_overload`
— audited to be the uncolorability count squared, not a proxy);
evaluation only, no descent; one lam everywhere; round_E stays raw
stair-E; lam=0 short-circuits byte-identically. 556 tests green.

Design-round dose-response (the step function, on record): lam=0 broken
(d729 at LOWER stair-E than the repaired state — E-blindness in one
number: 2802 vs 2808); lam=1-2 repaired (+6 tiles E = 0.2%; the
depth-repairing composite the raw gate REVERTED is accepted — the
revert counter flipped 1 -> 0); lam>=4 over-trades (+80 E, routed
8.28). lam=1 chosen.

**Probe** (`data/overload_probe.py` / `.csv`, bars pre-registered; Z12,
5 cells x 3 arms x 3 seeds x 60 s, quiet box):

| cell | control (os=1, lam0) | ovl (os=1, lam1) | ovl_nos (os=0, lam1) | tmpl |
|---|---|---|---|---|
| K100 | 8.74 s1 d0 | 8.74 | 8.74 | 8.00 |
| K140 | 11.41 s1 d0 | 11.41 | 11.41 | 11.00 |
| ER100_d10 | 4.76 d367 | 4.76 | 4.76 | -- |
| turan_n162 | 8.04 s1 d0 | 8.04 | **7.90** s1 d0 | 6.00 |
| spin_glass | 12.66 d4 | 12.66 | **12.47** d7 | 11.64 |

1. **MINIMUM: PASSED exactly as validated** — turan best ovl arm 7.90
   (bar <= 8.0; the design-round prediction to the hundredth), gates
   firing s1 d0; guards byte-identical (K100/K140/ER) — "nothing else
   breaks," delivered on the letter. STRETCH (<= 7.19) not met.
2. **The penalty is inert where feasible and decisive where not** —
   ovl == control on every already-feasible geometry (the designed
   guard), and on the os=0 geometry it unlocks d729 -> 0 valid at
   routed 7.90. With the penalty in place, the order_shake step is
   UNNECESSARY on turan (its role there was accidentally dodging the
   overload the gates could not see; the penalty sees it).
3. **Bonus: spin_glass 12.47 (best exact yet)** — the os=0+lam1
   geometry routes better despite d7 residue.
4. The turan account closes at: 7.19 negotiated (non-exact) vs 7.90
   constructed (minorminer never legalizes) — exactness price +0.71,
   down from +2.25 at s3.54. The remaining gap between the two numbers
   is boundary-avoidance's shaved lanes plus routing-vs-construction
   economics; the cell's true frontier remains template 6.00.

Standing best-arm board: K100 8.73 / K140 11.40 / ER 4.66 / turan 7.19
(7.90 constructed) / spin_glass 12.47 — template gaps 1.09x / 1.04x /
-- / 1.20x / 1.07x. Nine switches, all default-off. The flip council is
the outstanding decision; feasibility-in-the-energy is the round that
made the switch stack coherent enough to convene it.

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
