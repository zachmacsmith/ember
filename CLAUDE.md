# Ember — `paper3` branch

Mission: beat stock minorminer 0.2.22 on **dense random graphs** (primary; MM is the
structureless fallback in practice), without regressing on structured (secondary).
Thesis: embedding has two regimes split by a density crossover p*(n) — search below
(§3.21: sparse ER is bisection-limited, MM already optimal-scaling), construction above
(§3.26: every search method is 16–57% over the clique-template ceiling and MM's polish
cannot improve the template). Program plan, portfolio (P1 ATE … P6 anatomy), and
milestones: `docs/paper3/` — read `protocol.md` (measurement constitution, BINDING),
`notes.md` (§4.x lab record), `proposals/*.md`, `survey.md`, `QUEUE.md` (hyde06 lock).

**Ground rules (supersets of factored's; violations are protocol breaches):**
- Pair by (instance, seed) via the script route (`benchmark_one` with the same seed per
  arm); the CLI salts seeds with the algorithm name → CLI tables say "(instance, trial)".
- **No best-of-K arm is ever compared against single-shot MM.** Multi-run schemes race
  best-of-K-parallel stock MM at equal wall-clock on equal cores. Internal best-of-N is
  legal only when the whole arm fits inside one MM run's budget.
- Identical cheap polish on all arms: log `acl` AND `acl_spur`, tables use one column.
- Dev instance seeds 101–115 / eval 901–915 (frozen, disjoint; eval untouched until the
  M4 freeze). Success rates separate/unpaired; ΔACL on both-succeed pairs only.
- Pre-register every experiment (bar + decision tree) in notes.md §4.x before launch.
- Every minorminer change is a toggleable switch, default stock, one flip at a time,
  parity self-test green. Verify MM claims against source, never the 2014 paper
  (`docs/paper2/mm-internals.md` has the anatomy with file:line cites).
- hyde06 runs: repo at /data/dabh/ember (NEVER $HOME), ≤64 workers (64 physical cores /
  128 SMT), ≤48 for timing-bearing runs, one batch at a time via QUEUE.md.
- New arms register as `p3-*` by ADDING files under `ember_qc/algorithms/paper3/`
  (auto-imported) — never edit shared registration lines in parallel work.

Inherited from `factored` (all still present here): the factored router,
`ember_qc/algorithms/factored/`, the mm C++ fork toolchain (`scripts/mm_fork.patch`,
`build_mm_fork.sh`; rebuild per machine), `docs/paper2/` (notes §1–§3.31,
mm-internals.md, attraction.md — consult before re-deriving MM behavior or re-proposing
tried ideas; the DEAD-levers list in notes §3.13/§3.16/paper2 is binding). Salvaged from
`new-algorithm`: `ember_qc/anneal.py` + `docs/paper3/data/solution_quality/` (SVMC
solution-quality pipeline). Everything else on `new-algorithm` (Reweave, speculative
embedders, learning line) stays abandoned — do not reintroduce; its measurement sins are
catalogued in notes.md §4.0.2 and are what `protocol.md` exists to prevent.
