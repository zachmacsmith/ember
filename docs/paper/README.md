# PathFinder ACM TQC article

Self-contained ACM TQC (`acmart`) write-up of the PathFinder minor-embedding
algorithm and its Ember evaluation.

## Build

```bash
cd docs/paper
latexmk -pdf pathfinder.tex      # -> pathfinder.pdf
# or: pdflatex pathfinder && bibtex pathfinder && pdflatex pathfinder && pdflatex pathfinder
```

Requires a TeX distribution with `acmart.cls`, `tikz`, `pgfplots`, `algorithmicx`
(TeX Live 2022+ has all of these).

## Provenance

Every number in the Results section comes from `data/summary.csv`, produced by:

```bash
.venv/bin/python data/run_sweep.py        # writes data/raw_results.csv + data/summary.csv
```

The sweep drives Ember's `benchmark_one` harness over an Erdős–Rényi (and
d-regular / Barabási–Albert) source grid into clean Pegasus P6, broken Pegasus P6
(5% faulty qubits), and Zephyr Z4, with five seeds per cell. Figures are inline
TikZ/pgfplots; there are no external image dependencies.
