#!/bin/bash
# §4.15 results-side remedy (2026-08-03): re-run the 450 T1c ramp rows.
# The original rows are instrumentation failures — the run host's fork .so
# was stale (old patch; no beta_ramp switch) because build_mm_fork.sh could
# not patch a tree carrying the previous patch AND the chain's `| tail`
# masked the failure. Both fixed (build script resets to pristine tag;
# chain scripts use pipefail). This script asserts the switch is live
# BEFORE burning rows, drops the invalid ramp rows, and resumes p6.
# Launch detached AFTER T1D_DONE (one batch at a time, QUEUE row 13):
#   nohup bash docs/paper3/data/run_t1c_ramp_rerun.sh > run_t1c_rerun.log 2>&1 < /dev/null &
set -eo pipefail
cd /data/dabh/ember && . ./env.sh
echo "=== ramp rerun context ==="
uptime
date
bash scripts/build_mm_fork.sh 2>&1 | tail -4
.venv/bin/python - <<'PY'
import networkx as nx
import dwave_networkx as dnx
from ember_qc.algorithms.minorminer_forked import forked_find_embedding
r = forked_find_embedding(nx.path_graph(6), dnx.zephyr_graph(2),
                          max_beta=3.0, beta_ramp=2.0, seed=0, timeout=5.0,
                          fallback=False)
assert r.get("embedding"), "beta_ramp probe FAILED — fork switch not live"
print("beta_ramp probe OK")
PY
echo "=== FORK_RAMP_OK ==="
.venv/bin/python - <<'PY'
import csv
p = "docs/paper3/data/p6_probes_confirm_beta_z12.csv"
rows = list(csv.DictReader(open(p)))
keep = [r for r in rows if r["arm"] not in ("ramp2", "ramp2h")]
fields = list(rows[0].keys())
with open(p, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    w.writerows(keep)
print(f"dropped {len(rows) - len(keep)} invalid ramp rows; kept {len(keep)}")
PY
nice -n 5 .venv/bin/python -u docs/paper3/data/p6_probes.py --topo Z12 \
  --confirm-beta --resume --workers 48
echo "=== T1C_RAMP_RERUN_DONE ==="
