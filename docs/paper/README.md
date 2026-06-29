# PathFinder ACM TQC article

Self-contained ACM TQC (`acmart`) write-up of the PathFinder minor-embedding
algorithm and its Ember evaluation, plus everything needed to reproduce it.

## Files

| Path | What |
|------|------|
| `pathfinder.tex` / `pathfinder.pdf` | the article (source + compiled) |
| `refs.bib` | bibliography |
| `reproduce.sh` | one-shot end-to-end reproduction (env → sweep → analysis → PDF) |
| `data/run_sweep.py` | the **preliminary** benchmark sweep; writes `data/raw_results.csv` + `data/summary.csv` (§Preliminary Results) |
| `data/run_sweep_opt.py` | the **optimized** sweep (same grid; adds `pathfinder-base`/`-stacked`); writes `data/raw_results_opt.csv` + `data/summary_opt.csv` (§Optimizations) |
| `data/analyze.py` | regenerates **every** preliminary statistic and the LaTeX table rows from `summary.csv` |
| `data/coldstart_probe.py` | backs the §"Preliminary Algorithm" cold-start contrast |
| `data/summary.csv`, `data/summary_opt.csv` (+ raw) | the committed sweep results — the single source of truth for every number in the paper |

## Reproduce everything

```bash
bash docs/paper/reproduce.sh          # from anywhere in the repo
```

This (1) creates `.venv` and installs `ember-qc`, (2) runs the sweep, (3) prints
every reported statistic and the LaTeX rows, (4) runs the cold-start probe, and
(5) builds `pathfinder.pdf`. Or run the steps individually:

```bash
python3 -m venv .venv && .venv/bin/pip install -e "packages/ember-qc[dev]" scipy
.venv/bin/python docs/paper/data/run_sweep.py        # -> data/{raw_results,summary}.csv
.venv/bin/python docs/paper/data/analyze.py --latex  # verify numbers + emit table rows
.venv/bin/python docs/paper/data/coldstart_probe.py  # §3.4 cold-start contrast
cd docs/paper && latexmk -pdf pathfinder.tex         # -> pathfinder.pdf
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
