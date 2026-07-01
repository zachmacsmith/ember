#!/usr/bin/env bash
#
# docs/paper/reproduce.sh — reproduce the Reweave paper.
#
# Run from anywhere; it cd's to the repo root. LOCAL steps (a few minutes to
# ~1 h total on a multi-core workstation) regenerate every locally-computed
# result; the two CLUSTER-SCALE sweeps are documented at the end and their
# committed CSVs are analyzed locally, so every table and figure is covered
# either way.
#
#   1. environment (.venv) + optional minorminer fork (needed for mmfork-*)
#   2. preliminary sweep      -> raw_results.csv          (Sec. 5, App. A/B)
#   3. optimized sweep        -> raw_results_opt.csv      (Sec. 6)
#   4. ablation probe         -> ablation_probe.csv       (Sec. 6, 2x2 ablation)
#   5. solution quality       -> raw_solution_quality*.csv(Sec. 10)
#   6. analyses + LaTeX rows  (incl. K=15 instance stats on committed CSVs)
#   7. figures + PDF build
#
# Note: re-running a sweep OVERWRITES its committed CSV. Embedding-quality
# numbers are deterministic per seed and match the paper; wall-clock is
# machine-dependent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
DATA=docs/paper/data

echo "==> [1/7] environment (.venv)"
if [ ! -x .venv/bin/python ]; then
    "$PY" -m venv .venv
fi
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -e "packages/ember-qc[dev]" scipy matplotlib pandas \
    dwave-system dwave-samplers
if [ -x scripts/build_mm_fork.sh ] && [ ! -d external/minorminer-fork ]; then
    echo "    building the minorminer fork (required for mmfork-* algorithms)"
    bash scripts/build_mm_fork.sh || echo "    fork build failed — mmfork-* steps will fail"
fi

echo "==> [2/7] preliminary sweep (Sec. 5; Appendices A-B)"
.venv/bin/python "$DATA/run_sweep.py"
.venv/bin/python "$DATA/coldstart_probe.py" || true

echo "==> [3/7] optimized sweep (Sec. 6)"
.venv/bin/python "$DATA/run_sweep_opt.py"

echo "==> [4/7] 2x2 ablation probe (Sec. 6: Steiner vs congestion)"
.venv/bin/python "$DATA/ablation_probe.py"

echo "==> [5/7] solution quality on a simulator (Sec. 10; ~10 min)"
.venv/bin/python "$DATA/solution_quality.py"
.venv/bin/python "$DATA/solution_quality_large.py"

echo "==> [6/7] analyses + LaTeX table rows"
.venv/bin/python "$DATA/analyze.py" --latex
.venv/bin/python "$DATA/analyze_quality.py"      # fixed-effects + large arm + tab_solquality
.venv/bin/python "$DATA/analyze_instances.py"    # K=15 CIs/Wilcoxon on committed CSV + tab_instances
.venv/bin/python "$DATA/scaling_coords.py"       # scaling-figure coordinates from committed CSV

echo "==> [7/7] figures + PDF"
.venv/bin/python "$DATA/make_figures.py"
if command -v latexmk >/dev/null 2>&1; then
    ( cd docs/paper && latexmk -pdf -interaction=nonstopmode reweave.tex >/dev/null )
    echo "Done: docs/paper/reweave.pdf"
else
    echo "latexmk not found — skipping PDF build (install TeX Live with acmart/tikz/pgfplots)."
fi

cat <<'EOS'

CLUSTER-SCALE sweeps (hours on a many-core host; their committed CSVs are
analyzed above, so re-running is optional):
  K=15 multi-instance grid (Sec. 11):
      python docs/paper/data/run_sweep_instances.py <workers> 30 15 3
  Hardware-scale scaling, P16/Z15, K=8 (Sec. 9):
      python docs/paper/data/run_sweep_scaling.py <workers> 180 8
Search-guidance study (Sec. 8 tables): scripts and per-run CSVs under
  docs/candidate-algorithms/ (see search-guidance/README.md).
EOS
