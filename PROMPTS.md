# Session Prompts

A verbatim, chronological log of the user prompts issued to Claude Code in the
session that produced the **Reweave** algorithm (originally named *PathFinder*,
renamed in Prompt 18 to avoid collision with the cited FPGA router of the same
name) and its ACM TQC write-up.
Prompts are recorded exactly as issued (including typos). **This file must be
updated with every new prompt** (see the project memory note). The prompts below
retain the original "PathFinder"/"PF" wording as typed; the method is now Reweave.

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

### Prompt 12

```
Consider the patent application in ~/Downloads/quantum_patent.pdf. This patent imagines training a neural network of some sort (perhaps a graph attention network, but perhaps some other time of machine learning model) to predict embeddings. For instance, one could build up a cache (training data) of randomized input problem graphs and their optimized via embeddings (e.g., found via PathFinder optimized), and then training a model to predict those embeddings directly. Rather than predicting embeddings directly, one might just predict initial chains, e.g. as a seed for MM. This could again be done by generating a bunch of training data with PF/MM, finding out some optimal architecture, and training it. The goal would be to have this neural model generate embeddings that are at least as good (in terms of ACL and variance in ACL) in quality as those produced by PF/MM heuristics. Create a plan that uses a dynamic workflow with multiple subagents to explore different AI/learning strategies that may apply to this problem, build a training and validation/test eval framework/pipeline, generate training/validation/test data, and run training and evaluation (using this repository’s evaluation/benchmarking framework) to ultimately see whether learning-based methods can help.
```

> _Outcome: built `packages/ember-qc-learn` (a "learned layout" → decode pipeline reusing
> the repair backend + `benchmark_one`). A dynamic Workflow implemented 4 families:
> gnn-seed (supervised), graph-VAE (generative K=8), objective-GNN (label-free),
> retrieval-cache (non-neural). Generated 1560/312/312 instance-disjoint PF-thorough-labeled
> graphs into P6+Z4; trained all families on a 4-GPU cluster (hyde01/02/03). Held-out test
> bake-off verdict: **learning helps** — `learned-vae` beats PathFinder-thorough on both mean
> ACL and run-to-run variance on P6 and Z4, and beats minorminer/-layout on every family;
> `learned-obj` beats minorminer everywhere at MM speed. Full writeup + figures in
> docs/candidate-algorithms/learning/._

### Prompt 13

```
What is left to run at this point?  What is running and where?
```

### Prompt 14

```
Can you add a new section to the paper called "Learning-Based Approach" that details the learned-vae method?  Include architecture diagrams, citations to (Graph?) VAEs, and any other background or helpful expositional content.  Then show (in the same section / as a subsection) the tables comparing learned-vae results on the various architectures (as you just showed above), emphasizing which methods are best for different tasks/scenarios.  But also, add a table comparing timing/performance.  Ensure in the prose you mention training time, and include a plot of training/validation loss per epoch so we can get a visual sense of whether we're overfitting or not.  Be sure to include a subsection as well that describes the dataset generation process as reviewers will certainly pay close attention to that.  Be sure to mention somewhere in the section the success rate of learned-vae, whether it's a 100%-success-type method or whether it has failure modes.  Upon completing all this, commit and push
```

> _Outcome: added §7 "A Learning-Based Approach" to docs/paper/pathfinder.tex — VAE/graph-VAE
> background + citations (refs.bib: kingma2014vae, kipf2016vgae, simonovsky2018graphvae,
> hamilton2017graphsage, velickovic2018gat, kingma2015adam); a TikZ architecture diagram; a
> dataset-generation subsection; a training subsection with training time (195s/80 epochs/A4000)
> and a real train/val loss-per-epoch plot (no overfitting); quality/per-family/timing tables; a
> "which method wins and when" guide; and an explicit 100%-success / failure-mode paragraph._

### Prompt 15

```
Yes, make those little changes in abstract/contributions/conclusion too, and commit and push (and make sure PROMPTS.md is up to date)
```

### Prompt 16

```
Why is the learning loss basically flat?  That seems suspicious.  Usually it means the learning model underfit.  Or maybe learning just converged in the first epoch, but why?  Not enough training data?  The network is relatively small (dimension like 160) so that makes me wonder.  Do some investigation and let me know what you think.
```

> _Outcome: the flat loss is **posterior collapse** from an **ill-posed target** — the
> VAE/gnn-seed regress an *absolute* hardware coordinate, but placement is arbitrary
> under the fabric's symmetries, so the loss-optimal prediction is the constant global
> mean (reached in 1 epoch). Verified: the model outputs one constant point for every
> vertex; MSE = the predict-the-mean null model. Not underfit/data/size. Also found the
> earlier "VAE beats PF-thorough" was an artifact: the collapsed VAE = best-of-8 MM
> (8 restarts vs PF-thorough's 4)._

### Prompt 17

```
Ok, so sounds like the VAE did not learn anything useful then.  Sounds lke we need some new objective and maybe different dataset and things like that.  Some model that predicts a constant for all inputs is not useful and not even worth analyzing.  Please explore the space of possible objectives and design choices for applying a VAE or even other network type to this problem, and see if there are some nontrivial things you can come up with.  Retrain and re-run experiments and regenerate new data sets as helpful.
```

> _Outcome: the fix is a **symmetry-invariant (Procrustes) objective** — align prediction
> to target up to rotation/reflection/scale/translation before MSE, so the loss sees only
> relative structure. This cures the collapse and yields a real layout (`learned-procrustes`)
> that beats minorminer by ~1% at equal budget (single-shot −0.8% p=0.047; best-of-8 −0.9%),
> statistically significant but small. A **decode-aware RL** (REINFORCE through the MM
> decoder) does not exceed it (unstable, drifts down) — the limit is the placement action
> space, not the objective. Paper §7 + abstract/contributions/conclusion rewritten to this
> honest story; the VAE "win" retracted; learning verdict doc + scripts updated._

### Prompt 18

```
In parallel, I think we need to change the name PathFinder.  It seems like PathFinder is the name of some existing method, like we cite some other existing method called PathFinder.  So can we go through the whole codebase and paper and name the method something else that's distinct (at least not the name of one of the methods we're already citing?)?
```

> _Outcome: renamed the method **PathFinder → Reweave** (the cited method was the FPGA
> router PathFinder, McMurchie–Ebeling 1995). Comprehensive rename across code (registry
> IDs reweave/-thorough/-base/-cold/-stacked/-numba, modules reweave.py/reweave_opt.py/
> rw_*.py, classes ReweaveRouter etc.), the paper (title + prose + tables + file
> reweave.tex/pdf), docs, ~1260 CSV algorithm-column rows + variant filenames, memory, and
> the PF→RW abbreviation. The FPGA "PathFinder" (line in §Background + the mcmurchie1995pathfinder
> bib key/title) is deliberately PRESERVED so the two are now clearly distinct. CLAUDE.md
> (research brief) and the verbatim prompts above keep "PathFinder" (FPGA reference / historical)._

### Prompt 19

```
You mentioned one untried lever — learning to guide minorminer's search (vertex ordering / a rip-up policy) rather than its initialization.  This is a separate, larger effort, but let's build a plan of how we might do such a thing - opening up MM's internals and inventing and benchmarking some new algorithms and heuristics.  Could be deterministic or learning-based approaches.  Do a literature search first to see what might be plausible, and then build a plan to ideate, implement, test, iterate, and rank/summarize.
```

> _Outcome: literature search done (CHARME GNN-RL order→ATOM, Nembrini PPO, Gasse
> learn-to-branch by imitation, FPGA RL-Ripper rip-and-reroute, degeneracy ordering /
> MM order-sensitivity); plan written + approved. Decisions (via clarifying questions):
> **all three vehicles** — Reweave (open Python MM-style engine), a **fork of real
> minorminer** (patch `var_order`/rip policy in the C++), and CHARME's **ATOM** constructive
> embedder; **deterministic and learned in parallel** (hyde GPU cluster for the learned side);
> deliverable = a **sprint + ranked leaderboard/verdict** (no paper/production changes yet).
> Focus levers = vertex order + rip-up selection. Plan: ceiling probes (honesty gate) →
> deterministic battery + learned policies → combine/ablate/cross-vehicle → rank/summarize._

### Prompt 20

```
Tables 7-9 show ACL metrics but do not show timing/performance.  We need to establish whether our new algorithms (stacked or unstacked) are faster or slower than MM, mm-layout, etc.  Can you run these experiments (if necessary), add to the paper, commit, and push?  (Be sure to update PROMPTS.md as usual)
```

> _Outcome: ran a back-to-back wall-clock experiment (`mmfork_timing.py`) over the standard
> grid for minorminer / minorminer-layout / mmfork / mmfork-cuthill / mmfork-portfolio /
> reweave / reweave+mmfork. Findings: single-order mmfork variants run at ${\sim}$MM speed
> (the order is computed once and is nearly free; mmfork ≡ MM); the portfolio is ${\sim}6\times$
> MM (it runs every order) and the stacked reweave+mmfork is portfolio-cost + Reweave's
> ${\sim}1.3\times$ improver. Added a wall-clock column to Table 7 (tab:mmfork) and a dedicated
> per-cell timing table + a "Timing" paragraph to the search-guidance section; rebuilt the PDF.
> Committed and pushed._

### Prompt 21

```
(1) Any idea on how to speed up any of our new algorithms?  (2) You keep mentioning cells.  Are you only testing on representative single cells from a given hardware architecture?  What about trying out problems using an actual hardware graph from a real D-Wave system (lots of copies of cells all connected to each other)?  Can we do a scaling study with a real hardware graph like that that shows how all the methods perform as you go from small to big problems?  Perhaps even if one of our methods is slower at small n, it scales better as n grows?  (3) It is weird that reweave is only 1.7x MM and mmfork is 1.0x MM but combining them gives 6.4x MM (way slower).  What's up with that?  And are we testing reweave+mmfork or reweave+mmfork-cuthill (which seems more promising?)?
```

> _Outcome: (3) the 6.4x is because `reweave+mmfork` seeds Reweave from `base_method="mmfork-portfolio"`
> (5.9x) — not reweave(1.7x)⊕mmfork(1.0x). Added `reweave-mmfork-cuthill` (Reweave seeded from the
> 1.0x single Cuthill order, ~1.7x) — the promising cheap stack. (1) speedups: `mmfork-cuthill-fast`
> (a good order needs few restarts → reduced `tries`, sub-1x MM) and a parallelized portfolio
> (run its ~6 orders concurrently). (2) scaling study on the REAL hardware topologies — Advantage
> `pegasus_graph(16)` (5640q) and Advantage2 `zephyr_graph(15)` (7440q) + faults — sweeping problem
> size small→large on the hyde cluster (128 cores), measuring ACL/variance/success/time vs n. Added a
> "Scaling Behavior" paper section + timing fixes. (Note: "cell" was my term for a (size,density,target)
> grid point — the target was already a full P6 hardware graph, but only 680q; this study uses the
> full-size 5640q/7440q graphs.)_
