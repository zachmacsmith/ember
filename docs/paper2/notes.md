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
