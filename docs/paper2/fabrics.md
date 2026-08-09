# Fabrics — the target-graph bestiary

## 0. What this is

Measured facts about the target topologies (Chimera, Pegasus, Zephyr), collected as
they are encountered, so that hardware-to-graph translation mistakes die here instead
of recurring. Same doctrine as `mm-internals.md`: **every claim verified against the
actual graph object** (`dwave_networkx` constructions, coupler censuses, direct
adjacency checks), never against a paper figure or folklore. Dates mark when a fact
was measured; scripts are one-liners against `dnx.*_graph` unless noted.

**The founding lesson (2026-08-01, the Zephyr j-fold incident, notes §3.49):** a
qubit is not a node. In every D-Wave fabric the qubit is a **bar** — a horizontal or
vertical segment laid on a grid — and the hardware graph is the *intersection graph*
of those bars (couplers where bars cross or abut). Any model that abstracts qubits to
points has already chosen a projection, and the projection can silently erase the
structure the optimal constructions are written in. When adapting a new fabric:
translate the **bar picture**, then verify the translation by census, before building
anything on it. The checklist is §5.

## 1. The three coupler species (all families)

| species | geometry | role |
|---|---|---|
| **internal** | an h-bar crosses a v-bar | the workhorse: realizes source edges between perpendicular chains; junction structure determines packing constants |
| **external** | two collinear bars abut end-to-end (same wire, z ↔ z+1) | extends straight lanes; what constructive templates are made of |
| **odd** | two *parallel* bars in the same neighborhood (paired k, or paired j-course) | flexibility reserve: course-switching, chain doubling, router escape routes. Measured: busclique-style constructions use **zero** of them (§4) |

Degree decomposes accordingly (interior qubits): Chimera 6 = 4+2+0, Pegasus 15 =
12+2+1, Zephyr 20 = 16+2+2.

## 2. Chimera (C_m, t = 4) — the ancestor, for calibration

Measured on C16 (2026-08-01): 2048 qubits, 6016 couplers (4096 internal + 1920
external), mean degree 5.88.

- Bar picture: qubit spans **1 cell**; each cell is a complete K_{4,4} junction
  (verified 16/16 on an interior cell). 4 wires per line, no courses, no odd
  couplers.
- Per bar: 4 internal couplers → 4 distinct perpendicular wires (1 coupler each).
  Fresh-contact rate: 4 per bar. κ (contact capacity) ≈ 4 — matches
  `_target_kappa`'s 2E/n − 2.
- The lane arithmetic is the textbook case: biclique K_{4m,4n} by full h-lines ×
  full v-lines, every crossing complete. This is the picture everyone carries in
  their head; the later fabrics deform it, which is what this file is for.

## 3. Pegasus (P_m, t = 4) — the broken-junction fabric

Measured on P16 (2026-08-01): 5640 qubits, 40484 couplers (32400 internal + 5264
external + 2820 odd), mean degree 14.36.

- Bar picture: qubit spans **3 cells**. Coordinates (u, w, k, z): orientation u,
  line w, track k ∈ 0..11 (12 wires per line), position z.
- Per bar: 12 internal couplers → **12 distinct perpendicular wires, one coupler
  each** (verified mid-fabric). But a length-3 bar geometrically *crosses* more
  wires than it couples: **junction coverage ≈ 0.56** (notes §3.41) — the shifts
  determine which crossings get couplers. THE Pegasus trap: geometric adjacency in
  a drawing does not imply a coupler. Any wire-level matching or crossing count
  must consult the coupler list, never the geometry (this throttled the §3.37
  wire matching at ~62%, correctly diagnosed there as an existence problem).
- κ ≈ 13.3 (2E/n − 2). Odd couplers pair adjacent tracks (k, k±1) at the same
  position; external couplers extend the wire (12 × (m−1) per line family).

## 4. Zephyr (Z_m, t = 4) — the brick-wall fabric

Measured on Z12 (2026-08-01, this file's occasion): 4800 qubits, 45864 couplers
(36864 internal + 4600 odd + 4400 external), mean degree 19.11.

### 4.1 The brick wall

Coordinates (u, w, k, j, z): orientation u, line w ∈ 0..2m (2m+1 lines per
orientation), track k ∈ 0..3, **course j ∈ {0,1}**, position z ∈ 0..m−1. Position
along the line: p = 2z + j.

- Each line crosses the perpendicular lines at **2m+1 junction sites**.
- Each qubit is a bar spanning **exactly 2 adjacent junctions** (verified: an
  h-bar couples verticals in exactly 2 columns, {p, p+1}).
- Along one track, the j=0 bars tile the line end-to-end (external couplers at
  the shared junction boundaries), and the j=1 bars do the same **offset by one
  junction** — a running-bond brick wall, two courses per track. A line therefore
  carries **8 straight sub-lanes** (4 tracks × 2 courses), NOT 4 wires.

### 4.2 Junctions are complete

Every junction is a complete bipartite **K_{8,8}**: 8 h-bars (2 per track, one
from each course) × 8 v-bars, all 64 couplers present (verified 64/64 at an
interior junction). The Pegasus 56% pathology is absent by design. Consequence:
16 internal couplers per bar = 2 junctions × 8 opposite bars, and each of the 16
is a **distinct** perpendicular sub-lane — one coupler per opposite lane, zero
waste.

### 4.3 Coupler species

- **External** (same course, z ↔ z+1): bars abut end-to-end sharing no junction
  columns; these build straight lanes. 4400 on Z12.
- **Odd** (same track, j0 ↔ j1, positions p ↔ p+1): tie the two courses of one
  track; the bars overlap in one junction. 4600 on Z12. **Constructions use zero
  of them**: K184's chains = external links + exactly 1 corner crossing each
  (0/184 chains contain an odd coupler); the turán-6 template is pure external.
  They are flexibility reserve (course pairing, router negotiation).

### 4.3b Boundary lines have HALF crossing capacity (2026-08-02, s3.54)

A bar at position p covers junction lines {p, p+1} with p ∈ 0..2m−1, so
**line 0 is reachable only by even-course (j=0) bars and line 2m only by
odd-course** — the boundary lines see 4 crossing sub-lanes per side, not
8. Parity-blind packing onto line 0 creates structurally uncoverable
crossings (the "7 turán runs → 245 infeasible designated crossings"
figure is archive-recorded with no retained artifact —
`archive/notes_v3.69_full.md`, s3.74; the mechanism itself is verified
by the parity arithmetic above). Any exactness-seeking layout should treat lines 0 and 2m as
half-capacity or avoid them outright.

### 4.4 Packing constants (the lane arithmetic)

A straight same-course lane of L bars covers 2L junctions and meets **16L distinct
opposite sub-lanes** (8 per junction, no overlap between consecutive bars). Hence:

- **Biclique**: K_{a,b} lanes need L = ⌈max(a,b)/16⌉. Turán n162 ≈ K_{81,81}:
  **⌈81/16⌉ = 6** — and it is sharp to one variable (16·5 = 80). Measured
  (`data/template_quotes_z12.py`, s3.74 re-derivation): busclique's biclique
  constructor gives K_{80,80} ACL 5.50, but at K_{81,81} it jumps to **11.00**,
  NOT the 6.0 this file previously reported as measured — the 6.00 quote is
  real but comes from the K162 clique template *restricted* to the turán edges
  and spur-pruned (`data/zephyr_triad.log`: "K162-restriction template ACL =
  6.00"). So ⌈81/16⌉ = 6 is achievable by construction while busclique's own
  biclique call overshoots it ~2×. Verified construction: every chain a
  straight 6-bar run on one sub-lane, block A all-vertical, block B
  all-horizontal, adjacency 100% internal couplers, wires nested 2 chains each
  (the two courses, interleaved).
- **Clique = biclique + one arm**: the clique chain is an L (one lane per block
  direction + 1 corner). K162 template ACL 12.00 = exactly 2 × turán's 6.00;
  K184 (= K_max on Z12) ACL 13.00 (both re-derived s3.74:
  `data/template_quotes_z12.log`). The §3.35 "diagonal contains the biclique"
  insight holds quantitatively: bipartiteness just deletes the own-block arm.
- General rule: constants scale with the junction — 4t opposite lanes per bar.
  Fatter junctions or more tracks divide chain length directly.

### 4.5 The j-fold trap (why our numbers were 2× template)

The TileGrid Zephyr adapter (`field.py` §"typed Zephyr adapter") models each
**track** (u, w, k) as one wire and folds j into the along-position — chosen
deliberately so claimed runs are contiguous. But a contiguous run in folded
coordinates is the **odd-coupler zigzag** alternating courses: 1 junction of
advance per bar, ~8 fresh contacts per bar instead of 16, and the 2-per-track
course nesting is unclaimable. Floor for the folded representation on turán:
~10–11; unnested ~20; pipeline measured 14.03 vs template 6.00 (notes §3.48).
The Laws were fine; the alphabet was missing the course letter. Fix direction:
sub-lane = (k, j), position = z; same-course runs are contiguous via external
couplers, so the fold's motivation is satisfied by the unfold as well.

Related standing bug: `_couples` indexes Zephyr runs by perpendicular *line*
index where Zephyr keys by *position* (two coordinate spaces that coincide on
Chimera/Pegasus and diverge on Zephyr) — all wire-exact metrics on Zephyr were
garbage until this is fixed (notes §3.48 Part 1).

**Status (2026-08-01, notes §3.50): fixed, behind the `courses` switch**
(default off; `AttractConfig.courses`). Under the flag: sub-lane = 2k+j
(position stays p, geometry untouched), κ = fresh contacts per tile
(cross-orientation degree / stride ≈ 7.7), `_couples` gets the parity
lookup (bar crossing line c sits at p = c or c−1 by course parity;
verified 64/64 — correct in course mode only, the folded arm keeps the
§3.48 ticket), arrange line pool × stride. Measured on Z12
(`course_probe`, pre-registered): turán 13.30 → 10.02 (9.72 with wire
matching; mm 12.01), spin_glass 17.14 (2/3) → 14.01 (3/3), K140
**0/3 → 14.04 (3/3)** vs mm 18.27 (2/3), K100 11.92 → 10.57 — landing
near the folded-floor ~10–11 arithmetic above; template gaps now
1.2–1.6×. Cost on record: ER 4.81 → 5.09 (suspected κ-floor activation
on sparse sources — deg/κ−1 turns positive at κ ≈ 7.7; unattributed).

## 5. Translation checklist for the next fabric

1. **Draw the bars, not the nodes.** Get orientation, span (junctions covered),
   lines, tracks, courses from coordinates; verify each with an adjacency probe.
2. **Census the couplers** into internal / external / odd by coordinate rule and
   check the totals against `G.number_of_edges()`.
3. **Dissect one interior junction**: who passes through, how many couplers of
   the possible ones exist (Chimera 16/16, Zephyr 64/64, Pegasus *incomplete* —
   never assume completeness).
4. **Measure the fresh-contact rate** of the natural straight lane (distinct
   opposite lanes per added bar). This — not raw degree — is what κ must equal;
   `2E/n − 2` happens to match only when the claimable run is the efficient one.
5. **Identify the claimable object** in the model (what a contiguous interval in
   adapter coordinates physically is) and check it coincides with the lane the
   constructions use. If it doesn't, the representation has a ceiling; measure it
   before blaming the search.
6. **Check what the constructions ignore** (odd couplers, so far always) — that
   is the router's slack, not the template's currency.
