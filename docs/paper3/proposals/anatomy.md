# P6 — Fork anatomy: paper-vs-program micro-science

No leaderboard wins expected; buys the "anatomy of the incumbent" section that derisks
reviewer trust in every other claim. Every embedding paper since 2014 cites the CMR
sketch as if it were the shipped program; `docs/paper2/mm-internals.md` §7 documents the
deltas — these switches measure their consequences. Owner: shared with P4 (same fork
files). Status: spec.

## Switches (parity-guarded, off by default; one probe each, 1–2 h, ER ladder + 2 dense
cells, 5 dev seeds, paired, predict-and-register before each run)

1. **`tree=union`** — revive the dead `construct_chain` (union-of-independent-paths,
   `embedding.hpp:180`, exactly what the 2014 paper describes); third arm `tree=sph-pure`
   (drop the `refcount>1` attach filter → textbook Takahashi–Matsuyama). Question: what
   does MM's Steiner attach actually buy? Prediction: a few % over union.
2. **`root=boltzmann`** — temperature-weighted root choice among candidates (proposed in
   CMR 2014 "to avoid local optima", never shipped) vs uniform-among-exact-minima.
   Prediction: null.
3. **`max_beta` finite** — the paper's D^occ exchange-rate pricing vs shipped
   effectively-infinite lexicographic overlap pricing. Prediction: finite β worse on
   feasibility. (Also completes the §3.13 open residual: separates "history useless in
   MM's dynamics" from "history useless at infinite β".)

## Cost

~150 LOC C++ total on the existing patch infrastructure; parity self-test green before
every probe; no build proceeds past its probe.
