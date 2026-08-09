# Anatomy of the attraction embedder

The current algorithm, one piece at a time: what each part does and why it
exists. Since the 2026-08-03 **consolidation 2** there is exactly **one code
path** — the switch stack and its losing arms live in git history (archive
commit `9d99ebdd`; the older point/cross/span variants at `612ced3e`) and in
`attraction.md`'s ledger, which records every verdict that justified
deletion. `notes.md` is the chronological lab record; `mm-internals.md` is
what shipped minorminer actually does; `fabrics.md` is the measured target
anatomy.

Code map:

| file | contents |
|---|---|
| `placement.py` | the driver: init, contract, arrange, seeds, gate/route, fallback, polish (`attract_embed`, `AttractConfig`, `CONTRACT_STEPS`) |
| `field.py` | the coarse layer: `TileGrid`, stair readout, alternating arrangement + insertion, claim/snap/completion machinery, `claim_overload`; parked: `bar_domains` |
| `loop.py` + `costs.py` + `trees.py` | the standalone `factored` router (the paper's minorminer-analysis family; not part of the attraction pipeline) |
| `polish.py` | `spur_prune` (used by the pipeline); `shorten_chains`/`polish` (router-only) |

## 0. The one-paragraph version

A **placement-first constructor with a router fallback**: a coarse placement
over the hardware's tile grid decides *where* each variable lives — the
global, joint decision that one-chain-at-a-time local search cannot revise;
discrete projection steps enforce what gradients structurally cannot
(integer capacity, row/column ownership, variable order, claim-layer
feasibility); claims are aimed parity-exactly at their crossings and
completed to a **valid embedding by construction** on junction-complete
fabrics — minorminer legalization is *skipped* when the gate fires — and the
result is polished by minorminer's full grind, **unconstrained** (free-polish
doctrine, notes §3.22). On stride-1 fabrics (Pegasus/Chimera) the exactness
machinery is inert by the stride gate and minorminer legalizes the seeded
placement as before. Division of labour: geometry senses what minorminer
cannot; minorminer does what it is unbeatable at (fine legalization where
still needed, free local descent).

The design target (Max, 2026-07-29): replace minorminer as the default
fallback that does everything well when nothing better is known — near
busclique's constructive optimum on cliques (standing gaps 1.04–1.20×),
with the flexibility to beat both busclique and minorminer on dense problems
that *aren't* exact cliques, at parity-or-better off-template (s3.55). Easy
instances stay cheap: participation is by arm length (§4), so the dense
machinery is structurally inert wherever chains are sub-tile.

## 0.5 The five hardware facts (all the "annoyance items" in one place)

Everything fabric-specific in this codebase reduces to five measured facts
(details + verification: fabrics.md). If you understand these, every
parity/boundary/census mechanism below is just bookkeeping for one of them:

1. **A qubit is a bar, not a node** — a horizontal or vertical segment on a
   grid; the hardware graph is the intersection graph of bars. Anything that
   abstracts qubits to points has silently chosen a projection (the j-fold
   incident, fabrics §0).
2. **Lines carry a fixed number of parallel lanes** (8 on course-resolved
   Zephyr = 4 tracks x 2 courses). More overlapping arms than lanes on one
   line = someone gets no wire. This is `line_pools`, the packer's hard
   capacity, and `claim_overload`'s census — one book (s3.59/s3.61).
3. **Bars have parity** (Zephyr courses): a course-j bar sits only at even
   or only at odd positions. Interior crossings can be covered by either
   parity (the two candidate positions carry one each); parity FORCES only
   at claim endpoints and at the fabric boundary. This is `snap_claims`'
   p* arithmetic and the parity-preferring lane choice.
4. **Junctions are complete on Zephyr, ~56% on Pegasus** — on Zephyr,
   claim-coverage arithmetic IS validity (the mm-skip gate); on Pegasus it
   is not, which is why the exactness machinery is stride-gated off there.
5. **Boundary junction lines have half the crossing reach** (one parity
   only), so boundary tile lines pack at half pool and their perpendicular
   partners must take the coupling parity (s3.61; formerly "avoid
   outright").

The engineering principle tying them together: **one accounting** — the
packer, the coloring, and the verifier must read the same books, or the
mismatch surfaces as a deficit on the tightest instance (turán, five rounds
running: representation → compaction → lane depth → gate blindness →
crossing coverage).

## 1. The state: positions only

One continuous (x, y) per variable, in tile space. Everything extended
about a variable is a deterministic **readout** of positions (s3.31:
"extents were never legitimate state").

Under the **diagonal rule** (`_stair_contacts`, s3.34 — busclique's
staircase generalized): edge (u, v) is covered at u's h-arm × v's v-arm iff
(y_u, u) < (y_v, v) — one designated crossing per edge, every edge paid for
exactly once. `derive_bars_stair` turns positions into arms; the
contact-capacity floor (`span_floor`, κ derived per fabric) clamps total arm
length to ≥ deg/κ − 1.

**Invariants (correctness, not tuning):** bars are never recentered; the
rule is keyed on y-*order*, so every packing must be order-preserving.

## 2. The energy and its descent

`stair_energy` = total arm length = the single-coverage chain length of the
implied embedding — VLSI HPWL with two directional nets per variable. Chain
length **is** the objective, not a proxy. `stair_step` is one subgradient
step: per net, per axis, unit forces pull the two extreme members inward;
trust-region clipped at one tile.

**Contraction** (`CONTRACT_STEPS = 16` in `placement.py`): the driver runs
16 stair steps before the first pack — the s3.52 cycle-0 mechanism. Stock
single-step geometry was a frozen fixed point (s3.51: one step on a 20-tile
cloud, then nearest-line packing snaps back all drift); contraction before
packing was the *entire* measured mechanism of the shake shell, whose
decaying reshakes never won keep-best and were deleted at consolidation 2.
Stride-gated like the rest of the flip (the s3.58 P16 guard measured it at
+2.0 ACL on Pegasus turán against a clean control): stride-1 fabrics keep
the pre-flip single step.

## 3. The tile grid (`TileGrid`)

The hardware's canonical coarsening: per-tile **typed** wire pools, `cap`
shape (H, W, 2) — pool 0 vertical, pool 1 horizontal — counted from working
qubits. Owns `wire_map` ((orientation, line, sub) → {position: qubit}) and
the affine drawing↔tile map. Unrecognized targets fall back to untyped bins.

**Zephyr is course-resolved by default** (`courses=True` since consolidation
2; s3.49–s3.50, fabrics §4.5): sub-lane = 2k+j, runs are same-course
stride-2 external-coupler lanes — the representation busclique's templates
are built from (16 fresh contacts/bar, 8 claimable sub-lanes per line).
`courses=False` is the folded control arm (the measured 2×-template ceiling,
s3.48). Structural no-op on Pegasus/Chimera/untyped targets. κ derivation,
claim loops, and arrange capacity all key off `grid.stride`.

**The stride gate** (`placement.py`, consolidation 2): `exact_seeds`,
`overload_lam`, and the 16-step contraction engage only when
`grid.stride > 1`. Zephyr's junctions are complete K₈,₈ (fabrics §4.2), so
claim-layer coverage arithmetic *is* validity; Pegasus's ~56% junctions
(fabrics §3) do not qualify — coverage ≠ validity there, and the machinery
is unmeasured on that fabric. On stride-1 targets the default is
byte-identical to the pre-flip pipeline (guarded by a test; confirmed by
the s3.58 P16 probe after the contraction gate landed).

## 4. The arrangement (`alternate_arrange`) — where capacity is enforced

The fabric viewed as two coupled 1-D wire layers. Coordinate descent on the
stair energy: alternately pack rows (columns frozen) and columns (rows
frozen). Each half-step is the **exact order-preserving DP** (`pack_lines`,
s3.59): contiguous runs of the (value, id)-sorted participants per line,
capacity = interval overlap depth vs. the line's integer sub-lane pool
(`line_pools` — the claim layer's own census, shared with
`claim_overload`; ONE accounting), cost = minimal total displacement,
skips only at structural infeasibility. Feasibility intervals are the
claim layer's (`derive_bars_stair`). Iteration 0 is an unconditional
feasibility projection; every later half-step is E-gated. Converges in
~2 iterations. Lane oversubscription (the d729 class) is impossible by
construction; the open turán residual is CROSSING-PARITY demand (s3.59
— depth-8-full lines leave snap no aiming slack; the parity-aware
packer is the named next refinement).

**Participation is by arm length, per axis**: a variable enters row-packing
iff its floored h-interval spans ≥ 1 tile. Sparse sources have no
participants and pass through untouched.

Sub-moves, in order per iteration:

- **`edge_monotonize`** (s3.40): per-edge x-transpositions where the x-order
  disagrees with the y-order, accepted on strict stair-E decrease. The
  sparse/dense interpolation is a property of the move — leverage scales
  with |Δx|.
- **`insertion_sweeps`** (s3.36, on by default; runs AFTER the iteration
  loop as up to two gated composites, not per-iteration): best-insertion
  order search over the long-arm members' y-queue, priced at the y-values
  the permutation will assign, non-member neighbours folded in as fixed
  anchors. Propose in rank space, re-monotonize + repack, dispose by the
  gate energy with full revert (plus the s3.61 hard no-new-overload veto
  on DP-policy fabrics).

**Feasibility is in the gate energy** (`overload_lam = 1.0`, s3.57): every
E-gate scores stair-E + λ·hinge² of `claim_overload` — the claim layer's
own uncolorability census (arms that would exceed a line's sub-lane count).
Evaluation only, never descended on; λ trades, never ranks. This is what
made the deleted `order_shake` unnecessary: its role was accidentally
dodging overload the gates couldn't see.

## 4.5 The V-cycle init (`coarsen.py`; default since s3.66)

Two-stage source coarsening: exact-twin groups collapse unconditionally
(whole blocks at once), then one greedy weighted closed-neighborhood-
Jaccard matching over distance-≤2 candidates at τ=0.34 (τ boxed by the
derivation's limit values; unit-tested insensitive across the window).
The coarse quotient is placed by spectral-of-the-COARSE-graph (circle
fallback), children spread in golden-angle discs at COARSE_SPAN scale;
single-supernode quotients use the V0 measured anchor geometry; graphs
that don't coarsen get the coarse layout directly. **Stride-gated like
the rest of the flip** (`eff_vcycle = cfg.vcycle and stride2`,
placement.py — the s3.66 guard probe measured the compact coarse init
regressing dense cells on the P16 legacy path): active on
course-resolved Zephyr, inert on Pegasus/Chimera. (This paragraph
previously claimed "fabric-agnostic — active on every target"; corrected
2026-08-06 after the s3.68 probe surfaced the drift — no coarsening
change can affect Pegasus until that gate is revisited.) Measured
(s3.62-64): five records, exactness gates firing on all dense cells;
losing arms (mass shares, tangent closure, segments) at the
consolidation-3 marker with their numbers. Since s3.70 the DEFAULTS
include `vcycle_agg=True` (leader-aggregation fixpoint in place of the
single matching round — parity twice-measured) and `cluster_moves=True`
(coarse moves: cluster gather/relocate as E-gated composites inside
arrange, on raw members, fabric-agnostic — turán 8.12→6.52 at 3 seeds
with the blow-up tail eliminated, `data/cmove_probe.csv`; corrected
s3.74, the earlier 10-seed figures had no artifact; expanders exactly
at stock).
`vcycle_transport` remains off (ungated init transport: wins lattices,
loses expanders; its gather lives on as the cluster move).

## 5. Seed derivation — bars to real qubit chains

`wire_seeds_iv`: interval-graph coloring per line, solved exactly by the
greedy left-endpoint sweep (`_color_claim_bars`); each arm claims the
contiguous run of its colored wire's qubits, so seeds are real coupled
paths. Always best-effort — no discrete stage has an error path.

**Snap-aimed claims** (`snap_claims=True`, s3.56 — "aim, don't repair"):
each arm's claim is aimed at its stair-assigned contacts' lines
parity-exactly at color time. Extensions drop to ~0 and completion becomes
a verifier. Stride-2 grids only.

**Exactness completion** (`exact_seeds=True`, s3.54): corner + edge +
bridge passes drive the coverage deficit to zero by interval arithmetic;
includes boundary-line avoidance (fabrics §4.3b: lines 0/2m have half
crossing capacity — their pools are zeroed). On junction-complete fabrics
deficit 0 = validity: **the mm-skip gate** hands the seeds through as the
legal embedding and minorminer legalization never runs. Residual deficits
route as before with a strictly better warm start.

**`bar_domains`** (parked): shape as a *constraint region* for minorminer's
`restrict_chains` — the exact-handoff interface for the strip-minorminer-
down agenda; blocked on the upstream restrict_chains hang/segfault (repro:
`data/restrict_bug_repro.py`); unblock = fork-level patch when needed.

## 6. The driver (`placement.py::attract_embed`) — one pass

1. **Init**: spectral layout of the source scaled into the target's drawing
   box; circle fallback for degenerate spectra. A warm-start heuristic, not
   load-bearing (s3.36 init-independence).
2. **Geometry**: `CONTRACT_STEPS` stair steps, then one `alternate_arrange`
   call (insertion + overload-priced gates included).
3. **Seeds**: snap-aimed coloring; on stride>1, completion; if deficit 0
   and the chains validate — mm-skip.
4. **Route** (gate not fired): stock MM seeded legalization
   (`chainlength_patience=0`), capped at `round_frac=0.5` of timeout so the
   polish — where minorminer earns ~35% ACL, mm-internals §6 — cannot be
   starved.
5. **Feasibility fallback**: if nothing legalized, one *uncapped*
   `snap`-seeded attempt (nearest distinct qubits, high degree first) with
   all remaining time — degradation mode is "spectral-seeded stock MM", the
   net feasibility winner of §3.23.
6. **Finish**: stock MM full grind warm-started (`skip_initialization`),
   unconstrained, followed by a validity guard (a broken finishing pass can
   never corrupt a legal result).

The rounds protocol (multi-round feedback, `vary_rng`, round selection) was
deleted at consolidation 2: 1-shot beat rounds on all dense cells at the
first consolidation, and the sparse cells that motivated rounds are now won
by the exact stack (ws_n486 3.01 vs rounds' 3.41, s3.55).

## 7. Knobs (the complete list — 11)

`round_frac=0.5`, `eta=0.5`, `arrange_iters=8`, `insert_sweeps=8`,
`kappa=None` (derived from the target: degree-based on stride-1 fabrics,
fresh contacts per tile on course-resolved Zephyr), `span_floor=True`,
`courses=True`, `exact_seeds=True`, `snap_claims=True`, `overload_lam=1.0`,
`vcycle=True` (the two-stage coarsening init; default since s3.66).
Unknown kwargs — including every deleted knob — are silently ignored.

## 8. Open problems (the reasons remaining complexity exists)

- **Pegasus co-design** — validity-by-construction needs coupler-aware
  claim aiming on incomplete junctions (the 56% fabric); until then the
  stride gate keeps Pegasus on the router path. The generalization test
  for the exactness principle.
- **Strip minorminer down** (Max, 2026-07-29): with mm-skip routine on
  crystal cells, MM's remaining surface is residual-deficit legalization
  and the polish. UNBLOCKED (s3.60): the restrict_chains bug is patched
  in the fork and the seeds+domains handoff embeds within domains (K100
  P16 11.81 single-seed diagnostic); the strip-down probe is its own
  future round.
- **Corridor / routing-capacity reservation** — arrange does not price
  non-participant traversal (suspected weak_strong_cluster loss mode);
  naive reservation sabotages cliques; needs its own design round.
- **Hard-frontier eval** — success rate / time-to-first-legal / max
  embeddable n near capacity, plus the full-Ember sweep rerun under the
  consolidated default: the claims that matter for the
  minorminer-replacement thesis (§3.23's strategic emphasis).
