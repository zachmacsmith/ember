# Session Prompts

A verbatim, chronological log of the user prompts issued to Claude Code in the
session that produced the PathFinder algorithm and its ACM TQC write-up.
Prompts are recorded exactly as issued (including typos). **This file must be
updated with every new prompt** (see the project memory note).

Session start: 2026-06-28.

---

### Session configuration (slash commands, before any prose prompt)

```
/effort max
/model claude-opus-4-8[1m]
```

---

### Prompt 1

```
Our goal is to discover and validate a new algorithm for quantum embedding that beats the standard MinorMiner (MM) algorithm with p-norm layout, eihter by replacing/improving upon the core MM rip-and-replace iterative procedure for finding a valid embedding, and/or by coming up with a better algorithm for making a good initial guess/layout.  Read CLAUDE.md, which has some ideas already, then scaffold §2 (the embedder interface, shared round→repair backend, eval harness, and baseline wrappers), then implement 3.5 PathFinder.  This repository (Ember) already has benchmark infrastructure for assessing the performance of different embedding algorithms, including MM, so we have most of what we need to determine whether a new candidate algorithm is better than MM (with p-norm layout) or not.
```

### Prompt 2

```
Can you create a latex document that describes everything you've done so far, including (1) an introduction to the embedding problem (conceptual and mathematical, maybe with a diagram or two), (2) a literature review of existing embedding algorithms, (3) a presentation of the new algorithm you've invented (pathfinder and pathfinder-thorough) - or summary/description, if this algorithm is really just lifted from some other paper (it's fine for the novelty to just be the application if not the algorithm), (4) a quick (one paragraph) summary of Ember and how we evalute the new method against other methods, (5) a results section that shows the ACL performance metrics you just showed in the table above, and (6) in the same results section, a table showing performance (speed) metrics for each algorithm/variant.  Write this in the format of an ACM TQC (Transactions on Quantum Computing) article.  Perform at least one self critique loop.
```

> _During Prompt 2 (plan mode), Claude asked two clarifying questions. The user
> chose: **Results scope** → "Expand the sweep first"; **Authorship** →
> "Anonymized placeholder"._

### Prompt 3

```
Please commit everything and push.  Do not list Claude as a co-author of any commits.
```

### Prompt 4

```
Did you push all the scripts and commands necessary to reproduce all the results reported in this paper draft?  If not, can you go ahead and do do?  Also, please write and push a PROMPTS.md file that has all the prompts issued so far in this session of Claude (including this one).  Make a memory to always update PROMPTS.md every time there is a new prompt.
```

### Prompt 5

```
There were several other possible algorithms envisioned in CLAUDE.md.  PathFinder works well, but can we consider (fan out subagents, use a dynamic workflow) the other algorithms in parallel and evaluate each in the same way as we evaluated PathFinder?  Write up the results of each algorithm in a separate .md file; do NOT touch the PathFinder LaTeX paper for now.  Let's see how each algorithm performs first.  For any ideas you may have (e.g., one of the ideas is about sliced optimal transport or Gromov-Wasserstein stuff), be sure to go read some relevant background papers and get context before attempting any implementation.
```

### Prompt 6

```
Based on all the findings so far, do you have any other ideas for (1) promising embedding algorithms we should try, or (2) ways to increase the speed of PathFinder?
```

### Prompt 7

```
Algorithmically, let's try 1, 3, and 4.  For implementation, yes, let's try 1, 2, 3, 4, and 5.  Fan out subagents so we can measure the impact of each of these potential improvements on their own, and then, for any promising fixes/improvements, let's try combining them to see if performance (quality or speed) improves even further.  Eventually we can converge on one production version of PathFinder that has as many optimizations baked into it as we can find and verify.  Commit and push as a quick checkpoint before you start this pass.
```

### Prompt 8

```
Continue the background agents, I hit ctrl+c by mistake!
```

### Prompt 9

```
Go ahead and write a new section of the paper titled Optimizations and describe the optimizations we ended up baking in, in that section.  In that section, you can report new results of the optimized PathFinder algorithm versus MM and MM with p-norm layout.  I'd change the earlier section to be something like "Preliminary Algorithm" so that readers know that an optimized version and improved results are coming.  The abstract and intro and conclusion of the paper will also need to be updated to reflect the new optimizations and new numbers from the optimized algorithm.  Remember to do an update pass on PROMPTS.md, and then commit and push everything when done
```

### Prompt 10

```
If MM is written in C++, we should make sure we're making a fair comparison for performance (runtime).  It is totally fine to use numba and to implement any kernels in C++ rather than in Python, if that yields improved performance.  Consider the "optimized" version of Pathfinder and whether i can be sped up by using numba or by rewriting some or all of the algorithm in C++.
```

> _Outcome: investigated and **measured a negative result.** Profiling attributes
> 70–84% of optimized-`pathfinder` runtime to the compiled-C++ `minorminer` base
> call (PathFinder's wall-clock is ≥ minorminer's by construction — it runs
> minorminer then improves). A numba-compiled node-weighted Dijkstra
> (`pf_numba.py`, kept un-registered for reproducibility) gives **no net speedup**:
> restricted to the bounded region it is a wash with pure-Python `pathfinder`
> (n40 d0.7 P6: 1.74 s vs 1.74 s, identical ACL), and on the full graph it is ~24%
> slower — bounded routing already shrank each Dijkstra to a region where the
> compiled kernel's per-node win is cancelled by call overhead. So the ~1.3×
> overhead is the improvement pass, not interpreter overhead, and the comparison is
> fair; a C++ rewrite would hit the same ceiling. Paper §Optimizations and
> §Limitations updated to report this; production stays pure-Python._

### Prompt 11

```
Some of the earlier logs mentioned missing matplotlib and causing errros, as if it were trying to make some plots for the paper.  Please add and install matplotlib as a dependency and in our venv.  Create any plots you were thinking were necessary then commit and push.
```

> _Outcome: the matplotlib error was from `tests/test_ember_qc_analysis.py` (the
> `ember-qc-analysis` package's plotting suite), **not** the paper — whose figures
> are deliberately inline TikZ/pgfplots. matplotlib + seaborn were already declared
> deps of `ember-qc-analysis`, just not installed; installed the analysis package
> into `.venv` (matplotlib 3.10.9) and wired it into CI + `reproduce.sh`. Installing
> it un-masked pre-existing stale-fixture failures (the package renamed
> `problem_name`→`graph_name` and `significant`→`significant_005` after the test was
> last touched); fixed the test fixtures → full `test_ember_qc_analysis.py` now
> green (166 passed). Added `docs/paper/data/make_figures.py` → four supplementary
> result figures (`docs/paper/figures/`: ACL vs density, ACL-std vs density,
> wall-clock vs MM, topology robustness) rendered from the committed
> `summary_opt.csv`; not embedded in the .tex (kept the paper's vector figures)._
