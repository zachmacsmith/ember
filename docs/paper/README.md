# Reweave ACM TQC article

Self-contained ACM TQC (`acmart`) write-up of the Reweave minor-embedding
algorithm and its Ember evaluation, plus everything needed to reproduce it.

## Files

| Path | What |
|------|------|
| `reweave.tex` / `reweave.pdf` | the article (source + compiled) |
| `refs.bib` | bibliography |
| `reproduce.sh` | one-shot end-to-end reproduction (env → sweep → analysis → PDF) |
| `data/run_sweep.py` | the **preliminary** benchmark sweep; writes `data/raw_results.csv` + `data/summary.csv` (§Preliminary Results) |
| `data/run_sweep_opt.py` | the **optimized** sweep (same grid; adds `reweave-base`/`-stacked`); writes `data/raw_results_opt.csv` + `data/summary_opt.csv` (§Optimizations) |
| `data/analyze.py` | regenerates **every** preliminary statistic and the LaTeX table rows from `summary.csv` |
| `data/coldstart_probe.py` | backs the §"Preliminary Algorithm" cold-start contrast |
| `data/make_figures.py` | renders the **supplementary result figures** from `summary_opt.csv` → `figures/` (matplotlib) |
| `figures/*.{png,pdf}` | rendered result figures (see below) — supplementary to the paper's in-text TikZ/pgfplots |
| `data/summary.csv`, `data/summary_opt.csv` (+ raw) | the committed sweep results — the single source of truth for every number in the paper |

### Supplementary figures (`figures/`)

`data/make_figures.py` renders four matplotlib views of the **optimized** sweep
(`summary_opt.csv`) — handy for slides and a quick visual read; they plot the same
numbers the paper's tables report (the paper's own in-text figures are vector
TikZ/pgfplots, so these are **not** embedded in `reweave.tex`):

| Figure | Shows |
|--------|-------|
| `acl_vs_density` | ACL mean ± std vs density (ER → clean $P_6$), panels per $n$ — the quality + density trend |
| `acl_std_vs_density` | ACL std vs density — Reweave's run-to-run variance advantage |
| `time_vs_mm` | wall-clock relative to compiled `minorminer` (=1.0) — Reweave ~1.3×, thorough 3–6× |
| `topology_robustness` | mean ACL per algorithm across clean $P_6$ / broken $P_6$ / Zephyr $Z_4$ |

Regenerate with `.venv/bin/python docs/paper/data/make_figures.py` (needs
`matplotlib` + `pandas`, both pulled in by `ember-qc-analysis`). Deterministic: a
pure function of the committed CSV.

## Reproduce everything

```bash
bash docs/paper/reproduce.sh          # from anywhere in the repo
```

This (1) creates `.venv` and installs `ember-qc` (+ matplotlib/pandas), (2) runs
the sweep, (3) prints every reported statistic and the LaTeX rows, (4) runs the
cold-start probe, (5) renders the supplementary figures, and (6) builds
`reweave.pdf`. Or run the steps individually:

```bash
python3 -m venv .venv && .venv/bin/pip install -e "packages/ember-qc[dev]" scipy matplotlib pandas
.venv/bin/python docs/paper/data/run_sweep.py        # -> data/{raw_results,summary}.csv
.venv/bin/python docs/paper/data/analyze.py --latex  # verify numbers + emit table rows
.venv/bin/python docs/paper/data/coldstart_probe.py  # §3.4 cold-start contrast
.venv/bin/python docs/paper/data/make_figures.py     # -> figures/*.{png,pdf}
cd docs/paper && latexmk -pdf reweave.tex         # -> reweave.pdf
```

`analyze.py` (no flag) prints each statistic annotated with the paper claim it
backs, so you can diff its output against the text.

## Notes

- **Determinism.** Embedding-quality numbers (ACL, std, max chain, qubits,
  success) are deterministic per seed and will exactly match the committed CSVs
  and the paper. **Wall-clock times (Table 2) are machine-dependent.**
- Re-running `run_sweep.py` **overwrites** the committed CSVs.
- The PDF build needs a TeX distribution with `acmart`, `tikz`, `pgfplots`,
  `algorithmicx` (TeX Live 2022+). Figures are inline TikZ/pgfplots — no external
  image dependencies.
- The sweep takes a few minutes with parallel workers
  (`run_sweep.py [n_workers] [timeout]`).
