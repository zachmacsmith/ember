# Anatomy of the attraction embedder

The current algorithm, one piece at a time: what each part does and why it
exists. Since the 2026-07-29 consolidation there is exactly **one pipeline**
— the superseded variants (point state, cross state, span field dynamics,
Poisson repulsion, and their knobs) live in git history (archive commit
`612ced3e`) and in `attraction.md`'s ledger, which also records every
verdict that justified deletion. `notes.md` is the chronological lab record;
`mm-internals.md` is what shipped minorminer actually does.

Code map:

| file | contents |
|---|---|
| `placement.py` | the driver: init, round loop, budget, fallback, polish dispatch (`attract_embed`, `AttractConfig`) |
| `field.py` | the coarse layer: `TileGrid`, stair readout, alternating arrangement, insertion order-search, wire-seed derivation |
| `loop.py` + `costs.py` + `trees.py` | the standalone `factored` router (the paper's minorminer-analysis family; not part of the attraction pipeline) |
| `polish.py` | `spur_prune` (used per round) and the native shorten (used only by `factored`) |

## 0. The one-paragraph version

A **multilevel embedder**: a coarse placement over the hardware's tile grid
decides *where* each variable lives — the global, joint decision that
one-chain-at-a-time local search cannot revise; discrete projection steps
enforce what gradients structurally cannot (integer capacity, row/column
ownership, variable order); the placement is transmitted to minorminer as
wire-coherent seed chains; minorminer legalizes cheaply per round, realized
geometry feeds back, and the last legal round is polished by minorminer's
full grind, **unconstrained**. Division of labour: geometry senses what
minorminer cannot; minorminer does what it is unbeatable at (fine
legalization, free local descent). The placement earns its keep only by
improving the endpoint of an unconstrained polish (free-polish doctrine,
notes §3.22).

The design target (Max, 2026-07-29): replace minorminer as the default
fallback that does everything well when nothing better is known — near
busclique's constructive optimum on cliques, with the flexibility to beat
both busclique and minorminer on dense problems that *aren't* exact
cliques (first confirmations: spin_glass_n163 and turán, §3.34–3.36). Easy
instances must stay cheap: the arm-length criterion (§4) makes the dense
machinery structurally inert wherever chains are sub-tile, so the expensive
part simply never engages where it has no business running.

## 1. The state: positions only

One continuous (x, y) per variable, in tile space. Everything extended
about a variable is a deterministic **readout** of positions (the s3.31
simplification: "extents were never legitimate state" — any embedding of v
must reach its neighbours, so v owes arms spanning its neighbours'
coordinates; that is a function of positions, not a quantity to evolve).

Under the **diagonal rule** (`_stair_contacts`, s3.34 — busclique's
staircase generalized): edge (u, v) is covered at u's h-arm × v's v-arm iff
(y_u, u) < (y_v, v). The y-lower variable reaches across columns, the
y-upper reaches up rows — one designated crossing per edge, so every edge
is paid for exactly once (the cross readout's 2× overpay was measured and
killed, s3.34). `derive_bars_stair` turns positions into arms; the
contact-capacity floor (`span_floor`, `kappa=13`) clamps total arm length
to ≥ deg/κ − 1 (a chain of L qubits hosts ≲ κL contacts — Pegasus degree
counting, §3.26).

**Invariants (correctness, not tuning):** bars are never recentered (the
contact-at-(x_u, y_v) guarantee, wire seeding's `line = round(y_v)`, and
the energy identity all assume each arm sits on its owner's row/column);
the rule is keyed on y-*order*, so every packing must be order-preserving.

## 2. The energy and its descent

`stair_energy` = total arm length = the single-coverage chain length of the
implied embedding — VLSI HPWL with two directional nets per variable.
Chain length **is** the objective, not a proxy. `stair_step` is one
subgradient step: per net, per axis, unit forces pull the two extreme
members inward; interior members feel nothing; trust-region clipped at one
tile. This is the "attraction": continuous gradient descent on continuous
coordinates. Its solo fixed point would be collapse (§3.18, measured) —
which is why it never acts alone: the arrangement's exact per-line capacity
is what makes the composed dynamics' minimizers genuinely spread (the
superposition is simply outside the feasible set being descended on).

## 3. The tile grid (`TileGrid`)

The hardware's canonical coarsening: per-tile **typed** wire pools, `cap`
shape (H, W, 2) — pool 0 vertical, pool 1 horizontal — counted from working
qubits (dead qubits reduce the right pool by construction). Typing matters
because untyped capacity can read 50% free while the h-pool is saturated
(§3.25); this is exactly VLSI's gcells with per-direction track capacities.
Also owns `wire_map` ((orientation, line, sub) → {tile: qubit}) — the
lookup all seed derivation runs on — and the affine drawing↔tile map.
Unrecognized targets (including Zephyr, until its adapter lands) fall back
to untyped drawing-space bins with the pool halved across both slots.
`cap_derate` (< 1) scales capacities during rounds: packing at exactly
100% starves routing slack (measured twice, s3.29/s3.31).

## 4. The arrangement (`alternate_arrange`) — where capacity is enforced

The fabric viewed as two coupled 1-D wire layers (rows of h-wires, columns
of v-wires, glued by tile-local coupling). Coordinate descent on the stair
energy: alternately pack rows (columns frozen — each participant's
h-interval is then a fixed 1-D interval, and rows are an exact
interval-packing problem) and columns (rows frozen). Capacity per line =
interval overlap **depth** (`line_depth`, the interval graph's clique
number) — no wire coloring inside the optimizer, only the depth test.
Iteration 0 is an unconditional feasibility projection (spreading from a
compact init must raise E); every later half-step is E-gated, so the
alternation is monotone on the feasible set. Converges in ~2 iterations.

**Who gets pushed out:** nobody by identity. The packing sorts participants
by current coordinate and, in that order, each tries lines outward from its
own position, taking the first with depth room — it preserves attraction's
rank order and meters out one line per capacity-quantum (order-preserving =
minimal-total-displacement 1-D transport). Attraction decides *order and
adjacency*; packing decides *spacing*.

**Participation is by arm length, per axis** (2026-07-29 refinement): a
variable enters row-packing iff its floored h-interval spans ≥ 1 tile — it
owes a wire run — and column-packing symmetrically. "A chain has an extent"
is detected by the chain *having an extent* (a readout combining the κ
floor with actual geometric spread), not by degree. A compact K15 never
engages (sub-tile floor — minorminer's territory, per the s3.39
crossover); a low-degree variable with one long edge packs on that axis
only; sparse sources with sub-tile edges are structurally untouched. κ
survives only inside the floor.

Sub-moves, in order per iteration:

- **`edge_monotonize`** (s3.40; replaced the global `_align_diagonal`):
  per-edge x-value transpositions where the x-order disagrees with the
  y-order, accepted on strict stair-E decrease, swept to fixpoint. Leverage
  scales with |Δx| — geometric edges self-neutralize, dense-structure edges
  do real reordering — so the sparse/dense interpolation is a property of
  the move, with no gate and no cluster awareness. Patches diagonalize in
  place (no cross-patch pressure; side-by-side tilings reachable). Measured
  insight: the diagonal is *sufficient, not necessary* — E requires
  contiguous suffix value-sets, and the E-equivalent mixed ("tent")
  couplings this move finds route as well or better (K100 13.14 vs the
  staircase era's 13.41).
- **`insertion_sweeps`** (s3.36/s3.40, on by default: `insert_sweeps=8`):
  best-insertion order search over the long-arm variables' y-queue,
  **priced at the y-values the permutation will assign** (rank space treats
  all gaps as one slot — a lie on clustered layouts) plus a lexicographic
  ε-rank tie-break (post-packing values quantize onto lines; a pure value
  landscape has flat plateaus that strict-improvement search cannot
  descend — the s3.40 bisection finding). Non-member neighbours fold in as
  fixed anchors, so edges into the sparse world guide relocations instead
  of only vetoing at the gate. Composite gating unchanged: propose in rank
  space, re-monotonize + repack, dispose by true stair energy with full
  revert (revert count surfaced in `diag`). Open miss on record: from a
  *random* init on multipartite, local transpositions + insertion stall
  ~1.5 ACL short of what the old global permutation reached (9.93 vs 8.24,
  s3.40) — spectral init covers it in practice; candidate fixes on the
  ledger.

## 5. Seed derivation — bars to real qubit chains

- **`wire_seeds_iv`** (default): interval-graph coloring per line, solved
  exactly by the greedy left-endpoint sweep (`_color_claim_bars`); each arm
  claims the **contiguous run** of its colored wire's qubits, so seeds are
  real coupled paths, not stitched nearest qubits (which inflated routed
  ACL ~30%, s3.30). Oversubscribed bars are left point-seeded;
  `_ensure_seeds` guarantees everyone ≥ 1 qubit. **Always best-effort — no
  discrete stage has an error path.** On Pegasus, ~56% in-tile coupler
  density means blindly-colored designated crossings are sometimes not real
  couplers; the router's cheap short-range repair carries legality (the
  accepted cost of single coverage, s3.34).
- **`wire_seeds_matched`** (`wire_exact=True`, off by default): per-line
  max-weight matching of tracks (the coloring's color classes; #tracks =
  depth, so feasibility can't break) to physical subs, alternating
  columns↔rows — coordinate ascent on couplable designated crossings, with
  self-junctions weighted (`junction_w=2`: a variable's own h×v corner is
  its chain's connectivity; omitting it traded corners for contacts, K100
  conn 100→44, s3.37). Holds the K140/spin_glass/turán records; trails
  blind greedy on K100 — the co-design frontier (see §8).
- **`bar_domains`** (parked): shape as a *constraint region* for
  minorminer's `restrict_chains` — MM keeps every sub-tile identity choice.
  The exact-handoff interface for the strip-minorminer-down agenda; blocked
  on the upstream restrict_chains hang/segfault (repro:
  `data/restrict_bug_repro.py`); unblock = fork-level patch when needed.

**Zephyr has two wire representations** (`courses` knob, notes §3.49/§3.50;
fabrics §4). Folded (default): sub = k, both j-courses on one run, a
claimed interval is the odd-coupler zigzag (~8 fresh contacts/bar).
Course-resolved (`courses=True`): sub = 2k+j, runs are same-course stride-2
external-coupler lanes — the representation busclique's templates are built
from (16 fresh contacts/bar, 8 claimable sub-lanes per line, 2-per-track
nesting expressible). Everything downstream (κ derivation, `_couples`,
arrange line capacity, claim loops) picks the mode up from `grid.stride`;
the flag is a structural no-op on Pegasus/Chimera/untyped targets.

## 6. The driver loop (`placement.py::attract_embed`)

- **Init**: spectral layout of the source scaled into the target's drawing
  box; circle fallback for degenerate spectra. A warm-start heuristic, not
  load-bearing (s3.36 init-independence).
- **The round** (`max_rounds=1` by default — the 1-shot protocol; capped at
  `round_frac=0.5` of timeout so the polish — where minorminer earns ~35%
  ACL, mm-internals §6 — cannot be starved): `geo_iters=1` ×
  (stair_step + arrange) — or, when `shake_cycles>0`, the §3.52
  settle-and-reshake shell in its place (contract-then-pack cycle 0,
  decaying-amplitude reshakes, keep-best (E, unplaced), deadline-guarded
  against eating the routing budget) — derive bars, derive seeds, stock-MM seeded
  legalization (`chainlength_patience=0`), `spur_prune`. *Why 1-shot*: the
  consolidation probe's pre-registered protocol rule — 1-shot beat the
  rounds protocol on all four dense cells (turán 8.40 vs 12.73 the smoking
  gun): feedback re-derives geometry from realized centroids and the next
  arrange cannot recover insertion-found order within budget. With
  `max_rounds>1` the feedback loop (realized chain centroids re-enter the
  geometry) is still available, and it measured *better* on sparse ws_n486
  (3.41 vs 3.76 — seeded re-rolls); a participant-gated adaptive-rounds
  rule is on record in `attraction.md` as an undesigned candidate.
- **RNG discipline** (`vary_rng`): fresh router stream per round by
  default; `False` freezes it so only geometry varies between rounds (the
  attribution arm; failed rounds still re-roll).
- **Selection**: the trajectory endpoint (last legal round) — legal-stage
  ACL carries no information about polished ACL (§3.16); `round_acls` and
  `round_E` are returned as free diagnostics.
- **Feasibility fallback**: if no round legalized, one *uncapped*
  `snap`-seeded attempt (nearest distinct qubits, high degree first) with
  all remaining time — degradation mode is "spectral-seeded stock MM", the
  net feasibility winner of §3.23.
- **Finish**: stock MM full grind warm-started from the selected round
  (`skip_initialization`), unconstrained, followed by a validity guard (a
  broken finishing pass can never corrupt a legal result).

## 7. Knobs (the complete list)

`max_rounds=1`, `round_frac=0.5`, `geo_iters=1`, `eta=0.5`,
`vary_rng=True`, `arrange_iters=8`, `insert_sweeps=8`, `kappa=None`
(derived from the target: degree-based on stride-1 fabrics, fresh
contacts per tile on course-resolved Zephyr), `span_floor=True`,
`cap_derate=1.0`, `wire_exact=False`, `courses=False` (Zephyr
course-resolved wires, notes §3.49/§3.50 — sub-lane = 2k+j, stride-2
same-course runs; no-op on Pegasus/Chimera), `shake_cycles=0` /
`shake_steps=16` (settle-and-reshake geometry cycles, §3.52: cycle 0
contracts `shake_steps` before the first pack — the frozen-fixed-point
remedy of §3.51 — later cycles inflate about the centroid by decaying
amplitude 2.0/1.0/0.5… and re-settle, keeping the best (E, unplaced);
0 = stock single-step geometry), `masked_pool=False` (line capacity
from masked-nonzero cap mean, §3.51 item 4; own switch, stride>1 only),
`order_shake=0` (coarse-to-fine discrete order shake, §3.53: segment
reversals + block relocations at decaying scale, chained before insertion
in the same true-E-gated composite), `shake_invert=False` (reshake cycles
use radial rank reversal instead of dilation, §3.53 — the core must earn
its place), `exact_seeds=False` (exactness completion, §3.54: corner +
edge + bridge passes drive the coverage deficit to zero by interval
arithmetic; on junction-complete fabrics validity is constructed and MM
legalization is skipped; includes boundary-line avoidance on stride-2
grids), `cover_select=False` (shake-shell keep-best keys on the
post-claim coupler deficit before E, §3.54 — de-exploits the E-proxy),
`snap_claims=False` (claim-time crossing alignment, §3.56: each arm's
claim is aimed at its contacts' lines parity-exactly at color time —
aim, don't repair; extensions drop to ~0 and completion becomes a
verifier; stride-2 grids only), `overload_lam=0.0` (feasibility priced
into the gate energy, §3.57: every E-gate and cycle selection scores
stair-E + λ·hinge² of claim-layer line-capacity violations; evaluation
only; λ trades, never ranks; round_E stays raw stair-E), `bins=None`
(untyped-fallback resolution). Unknown kwargs — including
every pre-consolidation knob — are silently ignored.

## 8. Open problems (the reasons remaining complexity exists)

- **Geometry/wire co-design** — the K100 gap to busclique's template
  (~12.5 vs 9.78): a coupler-perfect wire assignment may not exist for a
  coupler-blind layout on Pegasus (the matched-seeds 62–67% plateau,
  s3.37). Zephyr's junctions are complete — the pathology is absent by
  hardware design; the TileGrid Zephyr adapter is the cheapest path.
- **Strip minorminer down** (Max, 2026-07-29): MM still does exhaustive
  searching that our guidance should render unnecessary; the path runs
  through `bar_domains` (exact handoff) plus fork-level surgery.
- **Corridor / routing-capacity reservation** — arrange does not price
  non-participant traversal (suspected weak_strong_cluster loss mode);
  naive reservation sabotages cliques; needs its own design round.
- **Exact-clique containment** — the §3.26 template-arm decision (run the
  busclique-derived prior as a rival to the geometric rounds, keep the
  better) fits the one-algorithm goal and is unbuilt; in practice known
  embeddings are checked upstream anyway.
- **Hard-frontier eval** — success rate / time-to-first-legal / max
  embeddable n near capacity, the claim that matters for the
  minorminer-replacement thesis (§3.23's strategic emphasis); still owed
  for the consolidated pipeline.
