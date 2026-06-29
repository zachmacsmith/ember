#!/usr/bin/env bash
# scripts/cluster_bootstrap.sh — provision a hyde GPU node for ember-qc-learn.
#
# Installs uv (if missing), creates a Python 3.11 venv at ~/emberlearn with a
# CUDA-12.1 PyTorch + torch_geometric + the embedding deps. Idempotent: re-running
# reuses the venv. Repo sync + `uv pip install -e` of the ember packages happens
# separately (sync_repo()), after the code exists.
#
# Usage (remote):  bash cluster_bootstrap.sh
# Drivers: hyde01 = 550 (A6000), hyde02/03 = 535 (A4000); cu121 works with both.
set -euo pipefail

VENV="$HOME/emberlearn"
export PATH="$HOME/.local/bin:$PATH"

echo "==> uv"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version

echo "==> venv (Python 3.11, seeded with pip)"
[ -x "$VENV/bin/python" ] || uv venv --seed --python 3.11 "$VENV"

echo "==> torch (cu121) — large download, please wait"
uv pip install --python "$VENV/bin/python" torch --index-url https://download.pytorch.org/whl/cu121

echo "==> torch_geometric + embedding deps (PyPI)"
uv pip install --python "$VENV/bin/python" \
    torch_geometric numpy networkx scipy "dwave-networkx" minorminer pandas scikit-learn

echo "==> verify"
"$VENV/bin/python" - <<'PY'
import torch, torch_geometric as g
print(f"torch {torch.__version__} | cuda {torch.cuda.is_available()} "
      f"| ndev {torch.cuda.device_count()} | pyg {g.__version__}")
for i in range(torch.cuda.device_count()):
    print("  gpu", i, torch.cuda.get_device_name(i))
PY
echo "BOOTSTRAP_OK"
