#!/bin/bash
# §4.15 results-side remedies (2026-08-03), one chain, launch AFTER T1D_DONE
# (one batch at a time; QUEUE row 13):
#   R1 — T1a re-run: the original T1a raw CSV was clobbered on the host by a
#        mid-experiment deploy of the tracked M3 record (sync rule now
#        excludes result records). Identical registry, fresh within-batch
#        walls; the first run's summary (preserved in notes) doubles as a
#        replication check.
#   R2 — T1c ramp re-run: the 450 ramp rows were instrumentation failures
#        (stale fork .so without beta_ramp; masked build error — both fixed).
#        Drop the invalid rows, resume p6 over exactly those keys.
# Launch (detached): nohup bash docs/paper3/data/run_t1_remedies.sh > run_t1_remedies.log 2>&1 < /dev/null &
set -eo pipefail
cd /data/dabh/ember && . ./env.sh
echo "=== remedies context ==="
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

# R1 — T1a re-run. The live dev_suite.csv on this host is the deploy-restored
# M3 record (duplicate of dev_suite_m3_archive.csv and of git); remove it so
# the batch is fresh.
rm -f docs/paper3/data/dev_suite.csv
nice -n 5 .venv/bin/python -u docs/paper3/data/dev_suite.py --topo Z12 \
  --arms minorminer,p3-template,p3-ate,p3-mmpolish,p3-ember --workers 48
echo "=== T1A_RERUN_DONE ==="

# R2 — ramp re-run: drop invalid rows, resume exactly those 450 keys.
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
echo "=== T1_REMEDIES_ALL_DONE ==="
