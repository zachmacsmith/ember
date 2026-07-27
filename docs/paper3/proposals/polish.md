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
