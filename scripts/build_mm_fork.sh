#!/usr/bin/env bash
# Build the Ember fork of minorminer: stock 0.2.22 + parity-guarded switches
# (var_order=, history_alpha=, the paper3 P4/P6 set: short_audit=,
# audit_budget=, dirty_skip=, chain_tree=, root_boltzmann=, and the paper3 W2
# beta-ramp pair: beta_ramp=, beta_ramp_hold=), each byte-identical to stock
# at its default.
#
# Idempotent: clones the pinned tag if absent, applies scripts/mm_fork.patch
# (the C++/Cython diff) if not already applied, then builds ONLY the
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

# Always patch from the PRISTINE tag. A leftover tree with an OLDER patch
# applied makes `git apply` fail ("patch does not apply") — that is exactly
# how the 2026-08-03 T1c ramp rows died on hyde06 (stale .so without the
# beta_ramp switch; §4.15 amendment 5). reset --hard restores the tag
# checkout; clean -fdx drops build artifacts and the old .so.
git reset --hard --quiet
git clean -fdxq
echo ">> applying scripts/mm_fork.patch (pristine $TAG tree) ..."
git apply "$REPO/scripts/mm_fork.patch"

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
echo ">> parity + switch self-test ..."
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
# every fork switch, explicitly at its default, must stay byte-inert
OFF = dict(history_alpha=0.0, short_audit=0, audit_budget=3, dirty_skip=0,
           chain_tree=0, root_boltzmann=0.0, beta_ramp=0.0, beta_ramp_hold=0)
c = [acl(f.find_embedding(S, T, random_seed=k, **OFF, **DEF)) for k in range(8)]
assert a == c, f"PARITY FAILED with all switches at defaults: {a} != {c}"
order = sorted(src.nodes(), key=lambda v: -src.degree(v))
ON = [dict(var_order=order), dict(history_alpha=1.0), dict(short_audit=1),
      dict(short_audit=2, audit_budget=3), dict(dirty_skip=1),
      dict(chain_tree=1), dict(chain_tree=2), dict(root_boltzmann=2.0),
      dict(max_beta=8.0, beta_ramp=2.0),
      dict(max_beta=8.0, beta_ramp=2.0, beta_ramp_hold=1)]
for kw in ON:
    e = f.find_embedding(S, T, random_seed=0, **kw, **DEF)
    assert len(e) == src.number_of_nodes(), f"engaged run {kw} did not embed all nodes"
print("   parity OK (fork==stock with every switch unset AND at explicit defaults);")
print("   var_order/history_alpha/short_audit/audit_budget/dirty_skip/chain_tree/")
print("   root_boltzmann/beta_ramp/beta_ramp_hold accepted and valid when engaged")
PYEOF
echo ">> done."
