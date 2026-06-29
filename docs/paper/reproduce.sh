#!/usr/bin/env bash
#
# docs/paper/reproduce.sh — reproduce the PathFinder paper end-to-end.
#
# Run from anywhere; it cd's to the repo root. Steps:
#   1. create a virtualenv and install ember-qc (+ scipy)
#   2. run the benchmark sweep  -> docs/paper/data/{raw_results,summary}.csv
#   3. regenerate every reported statistic + LaTeX table rows
#   4. (optional) the §3.4 cold-start contrast
#   5. build the PDF (needs a TeX distribution with acmart, tikz, pgfplots)
#
# Note: re-running step 2 OVERWRITES the committed CSVs. The embedding-quality
# numbers (ACL, std, qubits, success) are deterministic per seed and will match
# the paper; wall-clock times are machine-dependent. The sweep takes a few
# minutes with parallel workers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"

echo "==> [1/5] environment (.venv)"
if [ ! -x .venv/bin/python ]; then
    "$PY" -m venv .venv
fi
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -e "packages/ember-qc[dev]" scipy

echo "==> [2/5] benchmark sweep (Ember benchmark_one over the source x target grid)"
.venv/bin/python docs/paper/data/run_sweep.py

echo "==> [3/5] regenerate reported statistics + LaTeX table rows"
.venv/bin/python docs/paper/data/analyze.py --latex

echo "==> [4/5] cold-start contrast (§3.4)"
.venv/bin/python docs/paper/data/coldstart_probe.py || true

echo "==> [5/5] build the article"
if command -v latexmk >/dev/null 2>&1; then
    ( cd docs/paper && latexmk -pdf -interaction=nonstopmode pathfinder.tex >/dev/null )
    echo "Done: docs/paper/pathfinder.pdf"
else
    echo "latexmk not found — skipping PDF build (install TeX Live with acmart/tikz/pgfplots)."
fi
