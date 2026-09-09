# Focused construction literature check

2026-09-09. Design support only; no code reuse or performance inference.
Root searched minor embedding with vertex splitting, subgraph placement and
Gromov–Wasserstein matching while the completed screens were analyzed.
The narrow searches found no directly useful vertex-splitting or transport
constructor. Absence from these results is not evidence of novelty.

King et al.'s February 2025 manuscript explicitly reports using Glasgow Subgraph
Solver for the subgraph mapping in supplementary section I.D. This is relevant
prior art for constraint-based placement, not a general minimal-minor constructor
or evidence for performance on Ember. Any adaptive-splitting proposal would need
to explain its separate chain-growth mechanism and bounded heuristic search;
calling a global exact subgraph solver is not our intended approach.
[Primary manuscript, PDF page 19](https://www.dwavequantum.com/media/bljnr3zz/beyond-classical-computation-in-quantum-simulation.pdf).

Sugie et al. report improved PSSA scaling on random cubic and Barabási–Albert
inputs up to 102,400 hardware nodes, while their constant-density random graphs
do not exceed the stated deterministic complete-embedding threshold. This is
another reason to keep graph-class outcomes separate. That abstract does not
establish mean-ACL superiority on Z12 or validate our proposed mechanisms.
[Primary manuscript abstract](https://arxiv.org/abs/2004.03819).

An OSTI manuscript fetch failed; no inference relies on its unexamined contents.
No external algorithm or solver is imported into a candidate by this check.
