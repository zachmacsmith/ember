# P5 — Symmetric polish infrastructure + move-set completeness probe

Owner: (M2 agent). Status: spec.

## P5a — uniform cheap polish (MANDATORY infrastructure, ~50 LOC, land first)

A single helper used by every script-route runner: `terminal_polish(emb, G, T,
deadline)` = `spur_prune` + deadline-bounded `shorten_chains` (~2–20 ms), applied
identically to EVERY arm's output including minorminer's. Runners log both `acl` and
`acl_spur` (protocol rule 3). This is the autopsy's "MM+spur = −1.8% for 2 ms" rule made
structural — no arm ever again banks a polish the baseline didn't get.

## P5b — move-set completeness probe (science, gated)

Question: which move class, if any, improves embeddings that chain-local moves cannot?
§3.26 measured that MM's full grind cannot improve the template (joint-move blindness);
use the template as a test instrument.

Operators, run as symmetric anytime polish at matched time on (a) MM-converged
embeddings (mid-band dev cells), (b) the template on dense cells:
- `spur_prune`, `shorten_chains` (baselines);
- 1-vertex exact repair — minimum connected subgraph of a bounded region touching every
  pinned neighbor chain (port from `new-algorithm:.../lns_cpsat.py`; the operator that
  carried ALL of lns-cpsat's genuine −1.6%; cluster moves measured null there — skip);
- **2-vertex JOINT exact repair (new)** — rip a source-adjacent pair whose chains touch,
  re-embed both optimally within a bounded region (radius 2), boundary pinned,
  longest-pair-first, dirty-set scheduling.

## Kill gates (pre-registered)

- P5b-dense: exhaustive joint-pair repair on the K60 template (small enough for exact).
  No improving pair-move exists → drop the dense side; that negative is itself paper
  material (move-set completeness evidence for the regime thesis).
- P5b-midband: a 2-cell probe must beat spur-prune-only at matched extra time, AND beat
  "MM given the same extra time" (post-patience MM improves ~0 by construction — say so
  explicitly in the write-up).

## Cost & reuse

P5a ~50 LOC in `docs/paper3/data/_runner_common.py` (shared runner module). P5b ~300
LOC (`algorithms/paper3/joint_repair.py` + probe script); CP-SAT via ortools only if
the exact subproblem needs it (try plain BFS-enumeration DP first at radius 2). Reuses
bounded-region + dirty-set specs from `new-algorithm:docs/candidate-algorithms/`.

---

## PRE-REGISTRATION — P5b-dense, the K60 pair-move probe (2026-07-26)

PRE-REGISTERED 2026-07-26 (transcribe into notes.md as the next §4.x at merge; kept
here to avoid parallel-worktree edits to notes.md).

Question: does ANY exact bounded-region move — single-vertex (x1) or the NEW joint
source-adjacent-pair move (x2) — improve the K60 clique-template embedding on P16 that
§3.26 showed MM's full grind cannot improve (≤0.04 ACL in 3–42 s)?

Script: docs/paper3/data/p5_k60_pairmoves.py @ 2e06a7f6. Deterministic, seedless,
local (mac; no hyde06 queue slot needed — no wall-clock claims). Object under test:
the §3.26 template-arm output = busclique K60 chains, identity assignment, spur-pruned
against the complete source. Premise check recorded first: whether that spur-prune is
a no-op at K60/P16 (calibration on undersized cliques — C4/K12: 2 qubits removed,
P4/K20: 6 removed — shows the proposal's "no-op on K_n" assumption is false in
general; §3.26's numbers already included the prune, so its anchors are unaffected).

Cells / moves / budget: x1 on all 60 vertices; x2 on source-adjacent pairs ordered by
(-combined chain length, u, v) — all 1770, truncated to the first 400 in that order iff
the runtime projection (measured after 50 pairs) exceeds 28 min (the pre-registered
subsample rule). Per-move solver deadline 5 s, radius 2, node caps 150k/400k
(x1/x2); moves hitting a cap are recorded `proven=0` and counted separately.

Bars / decision tree:
- Zero improving x2 moves (all proven) → the pre-registered NEGATIVE: the 2-vertex
  joint move class cannot improve the template either → move-set completeness
  evidence for the regime thesis; drop the dense-side polish arm.
- Any improving move → headline-relevant: report counts, qubits saved per move, and
  `x2 beyond x1` (pairs improving where neither endpoint improves alone — the pure
  joint-move signal). x1-improving > 0 alone already revises §3.26's "template is
  polish-stable" from "MM's moves" to "MM's moves but not exact repairs".
- Unproven moves > 10% of the sweep → exactness caveat mandatory in any write-up;
  probe conclusions restricted to the proven subset.

--- results appended below; nothing above this line is edited after launch ---

## RESULTS — P5b-dense K60 probe (2026-07-27, run @ 4e748890)

CSV: `data/p5_k60_pairmoves.csv` (460 move rows; smoke calibration in
`p5_k60_pairmoves_smoke.csv`). Wall 27.6 min, local mac, deterministic/seedless.

**Verdict: the pre-registered negative is FALSIFIED. Improving pair moves exist on the
K60 template — including 58 pairs where neither endpoint is single-move improvable.**

- Template object: raw busclique K60 on P16 = 408 qubits; spur-prune removed **4**
  (premise "no-op on K_n" is false at K60/P16 too, as the calibration predicted) →
  404 qubits, ACL 6.7333 — matches the §3.26 anchor (6.73), so the instrument is the
  same object §3.26 measured.
- **x1** (exact single-vertex, radius 2): **2/60** vertices improvable (v=8, v=9,
  each 7→6), all 60 searches proven, ~1 s total.
- **x2** (joint pair, radius 2): projection 103 min > 28 min budget → truncated to the
  first **400/1770** pairs by (-combined length, u, v) (the pre-registered rule).
  **103/400 improving** (each certificate-valid: strict qubit decrease +
  `is_valid_embedding`; 71 of them proven pair-region-optimal), **80 certified
  no-improvement**, 249 unproven negatives (5 s/pair cap; mean 4.13 s/pair).
  Saved per move: 1 qubit x94, 2 qubits x9. **0** improvements are subsets of the old
  chains — every one relocates qubits.
- **x2 beyond x1: 58 pairs (54 proven)** — improving pairs whose BOTH endpoints are
  single-move stuck. Inspection of (2,16), (2,17), (2,32): both chains reshape — the
  partner relocates laterally at unchanged length to free the qubit vertex 2 needs;
  vertex 2 alone is **proven** stuck at radius 2, 3 AND 4 (region up to 350 qubits), so
  this is genuine joint-move blindness, not a region-size artifact.
- 34 distinct vertices participate in improving pairs; the counts are all measured
  from the SAME base embedding and are NOT additive (most pairs compete for the same
  slack). Sequential achievable gain ≥ 2 qubits (the x1 fixpoint); the sequential
  `anytime_polish` fixpoint on the template is the first M3 measurement (below) — not
  run here (probe consumed the compute budget).

**Decision-tree outcome (headline-relevant branch):** the §3.26 instrument — the
template MM's full grind cannot improve — is NOT locally optimal under exact bounded
moves. Two-sided reading: (a) the constructive ceiling is not tight; an exact-repair
polish stage stacked on the template lowers the ceiling further (strengthens P1 ATE:
template + polish, still deterministic-ish and cheap); (b) none of this rescues MM —
its own move set still cannot find these moves (§3.26), which is precisely the
move-set-completeness evidence P5b sought, in positive rather than negative form: the
missing move class is now exhibited, not just inferred.

**Mandatory exactness caveat (pre-registered bar: unproven 62% > 10%):** unproven
entries affect only NEGATIVE conclusions (a "no improvement found" under cap is not
"none exists"); every reported improvement carries its own certificate. Claims of
local optimality are restricted to the 80 certified pairs and the full x1 sweep.
The 1370 unswept pairs (truncation) can only ADD improving moves; 103/400 is a lower
bound on the swept prefix.

Premise corrections recorded for the file: (1) spur-prune is NOT a no-op on complete
sources — busclique leaves coverage-redundant end qubits on undersized cliques
(C4/K12: 2, P4/K20: 6, P16/K60: 4); §3.26's anchors already included the prune and are
unaffected. (2) polish.md's "up to 1770; subsample to ≤400" projection was right: full
exact x2 at K60 costs ~103 min at 5 s/pair caps.

## As built (P5, 2026-07-27)

Files:
- `packages/ember-qc/src/ember_qc/algorithms/paper3/joint_repair.py` (758 LOC) —
  `exact_repair_1`, `joint_repair_2`, `anytime_polish`, arm `p3-mmpolish`.
- `tests/algorithms/test_p3_polish.py` (276 LOC) — 19 tests: constructed detour case;
  the swap gadget (singles PROVEN stuck, pair move halves the total — the joint-move
  scenario in miniature); engine-vs-brute-force cross-check (incl. multiplicity-2
  requirements); anytime monotonicity/determinism/deadline; arm sanity. Contract
  suite: 15/15 for `p3-mmpolish`.
- `docs/paper3/data/p5_k60_pairmoves.py` (218 LOC) — this probe.
- P5a (`terminal_polish` in `data/_runner_common.py`) predates this work (landed with
  the M0/E0 scaffold @ caf62119) and is unchanged; every runner logs `acl`+`acl_spur`.

Design (deviations from the spec are flagged):
- **No ortools.** The lns-cpsat CP-SAT model is replaced by a plain branch-and-bound:
  duplicate-free connected-subgraph enumeration (ESU-style min-index rooting with
  include/exclude semantics) over the region, with admissible bounds
  (max-over-groups BFS-distance-plus-deficit, and a disjoint-witness deficit sum),
  incumbent-seeded so only strict improvements are ever found. Same optimum as the IP
  on the same region; deterministic; deadline-safe per 256 nodes.
- **Region** = ripped chains' qubits (always, so the incumbent stays feasible and no
  move can worsen) + free qubits within a radius-2 BFS ball. Deviation from
  lns-cpsat's region: the ball is taken over the FULL target adjacency then
  intersected with free fabric (free pockets behind pinned chains are reachable by
  adjacency, cf. rw_bounded's ball); halo appended in (depth, id) order, cap 350.
- **Pair mode** enumerates candidate unions under merged contact requirements (a
  contact mask needed by both sides must receive 2 distinct qubits — a necessary
  relaxation used only for pruning), then applies the exact side condition per
  candidate: split into two disjoint connected halves covering each side's contacts;
  the cross-edge (the ripped source edge's coupler) exists automatically.
- **Exact vs bounded, precisely:** optimality is always *within the region* (radius/
  cap are the outer bound; `shorten_chains` in the polish loop complements with
  whole-fabric free-space rebuilds). Within the region, `proven=True` iff the search
  completed under the node cap (150k x1 / 400k x2) and the move deadline; otherwise
  best-found is used and the outcome is labelled unproven. No greedy fallback was
  needed anywhere — every move either proves or reports unproven honestly.
- **anytime_polish** schedule = dirtyset.md's worklist (longest first, key
  `(len, -id)`; re-dirty the closed source-neighbourhood of changed chains; pair
  worklist keyed by combined length). One deliberate deviation: an x1-repaired vertex
  is not self-re-dirtied (it just re-proved region-minimum); it re-enters via
  neighbour changes. Monotone + valid by construction with a final input-fallback
  guard.
- **p3-mmpolish** = stock MM (graph-object source, seeded, 70 % of budget) +
  `anytime_polish` (rest). No counters reported (deadline-dependent counters would
  violate the seed-stability contract).

## M3 pre-registration DRAFT — P5b-midband arm (NOT yet launched)

To be transcribed into notes.md §4.x (with a fresh sha) when M3 opens and the E0 dev
suite is frozen; numbers below are placeholders only where marked.

Question: at matched wall-clock, does exact-repair polish beat (a) spur-prune-only
polish and (b) minorminer given the same extra time, on MM-converged embeddings in the
mid-band? (Post-patience MM improves ~0 by construction — mm-internals: the shortening
phase has converged; this is stated, and arm (b) exists to measure it anyway.)

Script: new `docs/paper3/data/p5_midband.py` (to be committed; script route,
`benchmark_one`-seeded, paired by literal (instance, seed)). Arms, all at 60 s total:
  1. `minorminer` @ 60 s (control).
  2. `p3-mmpolish` @ 60 s (MM 42 s + anytime_polish(spur,shorten,x1,x2) 18 s).
  3. mm+spur: MM 42 s + spur-prune only (isolates x1/x2's contribution over P5a).
All rows log `acl` and `acl_spur`; the table column is `acl_spur` (rule 3). Cells: the
two dev-suite cells straddling p* on the n≈100 ladder plus the near-cliff p=0.2 cell
(from the E0 FIXED rule; exact cells filled in at transcription). Seeds: instance
101–105 × algo 0–4; K60-template cell added as a dense control with
template+anytime_polish as arm 4 (the ceiling-shift measurement, incl. the sequential
fixpoint the probe did not run).
Bars: arm 2 beats arm 3 AND arm 1 on median paired ΔACL_spur < 0 with ≥60 % win rate
on both-succeed pairs in ≥2 of 3 mid-band cells. Decision: met → P5 arm enters the M4
freeze list; not met → P5 demoted to infrastructure (P5a + the K60 finding stand);
either way the ceiling-shift number feeds P1 ATE.
