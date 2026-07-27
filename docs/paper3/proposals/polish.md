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
