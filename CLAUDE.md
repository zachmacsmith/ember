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
never unpaired (survivor bias). Design rationale, source-verified minorminer facts, and the
open fidelity gap between the Python replica and stock MM: `docs/paper2/notes.md`.

The abandoned prior work (Reweave wrapper, speculative embedders, learning line) lives only
on the `new-algorithm` branch. Do not reintroduce it.
