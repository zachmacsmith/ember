#!/usr/bin/env bash
# Build the Ember search-guidance fork of minorminer: stock 0.2.22 + a var_order=
# parameter that injects a custom vertex order into the FULL find_embedding search.
#
# Idempotent: clones the pinned tag if absent, applies scripts/mm_fork.patch (the
# ~90-line C++/Cython diff) if not already applied, then builds ONLY the
# _minorminer extension in place. Produces
#   external/minorminer-fork/minorminer/_minorminer*.so
# which ember_qc/algorithms/minorminer_forked.py loads standalone (it coexists in
# the same process with the stock pip-installed minorminer).
#
# Requires: git, a C++17 compiler, and a Python with Cython>=3.0.6 + setuptools.
# Usage:  bash scripts/build_mm_fork.sh  [PYTHON]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORK="$REPO/external/minorminer-fork"
PY="${1:-$REPO/.venv/bin/python}"
TAG="0.2.22"

echo ">> ember repo:   $REPO"
echo ">> fork dir:     $FORK"
echo ">> python:       $PY"

if [ ! -d "$FORK" ]; then
  echo ">> cloning minorminer $TAG ..."
  git clone --depth 1 --branch "$TAG" https://github.com/dwavesystems/minorminer.git "$FORK"
fi

cd "$FORK"

# Apply the patch if the working tree doesn't already contain it.
if git apply --check --reverse "$REPO/scripts/mm_fork.patch" 2>/dev/null; then
  echo ">> patch already applied"
else
  echo ">> applying scripts/mm_fork.patch ..."
  git apply "$REPO/scripts/mm_fork.patch"
fi

cp "$REPO/scripts/setup_mmfork.py" "$FORK/setup_mmfork.py"

# Ensure the build tool is present.
"$PY" -c "import Cython" 2>/dev/null || "$PY" -m pip install "Cython>=3.0.6"

echo ">> building _minorminer (forced re-cythonize) ..."
rm -f minorminer/_minorminer.cpp minorminer/_minorminer*.so
rm -rf build
"$PY" setup_mmfork.py

SO=$(ls minorminer/_minorminer*.so 2>/dev/null | head -1 || true)
if [ -z "$SO" ]; then
  echo "!! build failed: no _minorminer*.so produced" >&2
  exit 1
fi
echo ">> built: $SO"
echo ">> parity + var_order self-test ..."
"$PY" - "$FORK/minorminer" <<'PYEOF'
import sys, networkx as nx, dwave_networkx as dnx
sys.path.insert(0, sys.argv[1])
import _minorminer as f
import minorminer as s
p6 = dnx.pegasus_graph(6); T = list(p6.edges())
src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(30, 0.6, seed=7)); S = list(src.edges())
DEF = dict(max_no_improvement=10, timeout=1000, tries=10, chainlength_patience=10)
acl = lambda e: sum(len(c) for c in e.values())/len(e)
a = [acl(s.find_embedding(S, T, random_seed=k)) for k in range(8)]
b = [acl(f.find_embedding(S, T, random_seed=k, **DEF)) for k in range(8)]
assert a == b, f"PARITY FAILED: {a} != {b}"
c = [acl(f.find_embedding(S, T, random_seed=k, history_alpha=0.0, **DEF)) for k in range(8)]
assert a == c, f"PARITY FAILED at history_alpha=0: {a} != {c}"
order = sorted(src.nodes(), key=lambda v: -src.degree(v))
e = f.find_embedding(S, T, random_seed=0, var_order=order, **DEF)
assert len(e) == src.number_of_nodes(), "var_order run did not embed all nodes"
e = f.find_embedding(S, T, random_seed=0, history_alpha=1.0, **DEF)
assert len(e) == src.number_of_nodes(), "history_alpha run did not embed all nodes"
print("   parity OK (fork==stock with var_order unset AND with history_alpha=0);")
print("   var_order and history_alpha accepted and valid")
PYEOF
echo ">> done."
