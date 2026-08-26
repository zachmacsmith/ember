# Ember — `factored` branch

This branch changes **minorminer's algorithm itself** and measures each change. It contains,
on top of `main`'s benchmarking framework, exactly two things:

1. **`ember_qc/algorithms/factored/`** — minorminer's search with its three separable
   choices factored into independently swappable axes: qubit **cost** (history term; `alpha=0`
   recovers MM's `diam^occ`), chain **tree** (SPH Steiner vs. MM's union-of-paths), vertex
   **order** (Cuthill–McKee vs. random). Minorminer is one corner of the family; every claim
   is one switch flipped against that corner.
2. **The minorminer C++ fork** (`scripts/mm_fork.patch` + `build_mm_fork.sh`) — stock
   minorminer 0.2.22 plus two switches, byte-identical to stock when both are unset:
   `var_order=` (caller-supplied vertex order) and `history_alpha=` (the §3.5 history
   cost inside MM's real dynamics; see notes.md §3.12). Registered as `mmfork` /
   `mmfork-<order>` / `mmfork-history`. This is the gold standard for comparability:
   the control arm is literally stock minorminer.

**Ground rules.** Every change to minorminer must be a toggleable switch, defaulted to stock
behavior, measured one flip at a time against the stock corner — paired by (instance, seed),
never unpaired (survivor bias). Verify any claim about minorminer against its source, never
its paper — the shipped program has repeatedly outgrown the 2014 description.

**Read `docs/paper2/ideas.md` FIRST.** One page: the algorithm, the
constraints any redesign must respect, and the open fronts — the notes
were condensed 2026-08-06 (and ideas.md re-condensed 2026-08-26) because
accumulated micro-verdicts and Claude-invented doctrine were poisoning
later sessions. The only rule is to
find the correct algorithm from the principles of what makes it good.
Supporting references: `docs/paper2/attraction.md` (condensed verdict ledger —
check before proposing; prevents re-derivation), `docs/paper2/anatomy.md`
(the pipeline as-built), `docs/paper2/fabrics.md` (measured fabric anatomy),
`docs/paper2/mm-internals.md` (what shipped minorminer actually does),
`docs/paper2/notes.md` (condensed chronicle). `docs/paper2/archive/` holds
the full uncondensed records — history, not instruction: do not resurrect
its doctrine vocabulary or treat its micro-observations as binding.

The abandoned prior work (Reweave wrapper, speculative embedders, learning line) lives only
on the `new-algorithm` branch. Do not reintroduce it.
