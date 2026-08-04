#!/bin/bash
# paper3 v1.3 §4.17 T4 — Z12 library re-verify of p3-mm-beta-mf (QUEUE row 17).
# Launch (detached): nohup bash docs/paper3/data/run_t4_hyde06.sh > run_t4.log 2>&1 < /dev/null &
set -eo pipefail
cd /data/dabh/ember && . ./env.sh
echo "=== T4 launch context ==="
uptime
date
# The arm needs the fork .so — assert live (max_beta probe).
.venv/bin/python - <<'PY'
import networkx as nx
import dwave_networkx as dnx
from ember_qc.algorithms.minorminer_forked import forked_find_embedding
r = forked_find_embedding(nx.path_graph(6), dnx.zephyr_graph(2),
                          max_beta=3.0, seed=0, timeout=5.0, fallback=False)
assert r.get("embedding"), "fork probe FAILED — .so not live"
print("fork probe OK")
PY
echo "=== T4_FORK_OK ==="
nice -n 5 .venv/bin/ember run docs/paper3/experiments/t4_z12.yaml
echo "=== T4_DONE ==="
