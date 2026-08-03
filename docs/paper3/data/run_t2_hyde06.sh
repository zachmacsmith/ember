#!/bin/bash
# paper3 v1.2 §4.16 T2 — Z12 library re-verify (QUEUE row 12).
# Arms {p3-ember, p3-mm-beta-fb}, 30,221-graph set, master seed 4242, 60W.
# Launch (detached): nohup bash docs/paper3/data/run_t2_hyde06.sh > run_t2.log 2>&1 < /dev/null &
set -eo pipefail
cd /data/dabh/ember && . ./env.sh
echo "=== T2 launch context ==="
uptime
date
# p3-mm-beta-fb needs the fork .so — assert it is live (max_beta probe).
.venv/bin/python - <<'PY'
import networkx as nx
import dwave_networkx as dnx
from ember_qc.algorithms.minorminer_forked import forked_find_embedding
r = forked_find_embedding(nx.path_graph(6), dnx.zephyr_graph(2),
                          max_beta=3.0, seed=0, timeout=5.0, fallback=False)
assert r.get("embedding"), "fork probe FAILED — .so not live"
print("fork probe OK")
PY
echo "=== T2_FORK_OK ==="
nice -n 5 .venv/bin/ember run docs/paper3/experiments/t2_z12.yaml
echo "=== T2_DONE ==="
