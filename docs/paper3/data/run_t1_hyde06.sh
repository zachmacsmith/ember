#!/bin/bash
# paper3 v1.2 §4.15 T1 chain — hyde06, one QUEUE batch (QUEUE.md row 11).
# T1a dev gates -> T1b native CLI -> T1c beta (switches + arms) -> T1d racer.
# Launch (detached, from /data/dabh/ember):
#   nohup bash docs/paper3/data/run_t1_hyde06.sh > run_t1.log 2>&1 < /dev/null &
set -e
cd /data/dabh/ember && . ./env.sh
echo "=== launch context ==="
uptime
# rsync deploy — no .git on the run host; the deployed sha is stamped in
# QUEUE.md row 11 and printed by the sync step on the coordinator side.
git rev-parse --short HEAD 2>/dev/null || echo "(rsync deploy; sha in QUEUE.md row 11)"
date
# Fork rebuild per machine — the parity self-test must pass (set -e aborts
# the chain otherwise; §4.15 T1c/T1d and p3-mm-beta[-fb] need the .so).
bash scripts/build_mm_fork.sh 2>&1 | tail -4
echo "=== FORK_OK ==="

# T1a — fresh WITHIN-BATCH dev-suite run (bar iii compares walls in-batch):
# archive the tracked M3 CSV so all five arms re-run cleanly.
if [ -f docs/paper3/data/dev_suite.csv ]; then
  mv docs/paper3/data/dev_suite.csv docs/paper3/data/dev_suite_m3_archive.csv
fi
nice -n 5 .venv/bin/python -u docs/paper3/data/dev_suite.py --topo Z12 \
  --arms minorminer,p3-template,p3-ate,p3-mmpolish,p3-ember --workers 48
echo "=== T1A_DONE ==="

nice -n 5 .venv/bin/ember run docs/paper3/experiments/t1b_native.yaml
echo "=== T1B_DONE ==="

nice -n 5 .venv/bin/python -u docs/paper3/data/p6_probes.py --topo Z12 \
  --confirm-beta --workers 48
echo "=== T1C_SWITCHES_DONE ==="

nice -n 5 .venv/bin/python -u docs/paper3/data/t1c_arms.py --workers 30
echo "=== T1C_ARMS_DONE_MARKER ==="

nice -n 5 .venv/bin/python -u docs/paper3/data/t1d_race9.py --outer-workers 5
echo "=== T1D_DONE ==="
echo "=== T1_ALL_DONE ==="
