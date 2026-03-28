#!/usr/bin/env bash
# QEBench setup script
# Usage: bash setup.sh
# Installs Python dependencies and compiles the C++ algorithms (ATOM, OCT).

set -e  # exit on first error (overridden per-section below)

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS="✅"
FAIL="❌"
WARN="⚠️ "

echo ""
echo "========================================"
echo " QEBench Setup"
echo "========================================"
echo ""

# ── 1. Python dependencies ────────────────────────────────────────────────────
echo "[ 1/3 ] Installing Python dependencies..."

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "  $FAIL Python not found. Install Python 3.8+ and re-run."
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)

if "$PYTHON" -m pip install -r "$REPO_DIR/requirements.txt" -q; then
    echo "  $PASS Python dependencies installed"
else
    echo "  $FAIL pip install failed — check the error above"
    exit 1
fi

# ── 2. Compile ATOM ───────────────────────────────────────────────────────────
echo ""
echo "[ 2/3 ] Compiling ATOM..."

ATOM_DIR="$REPO_DIR/algorithms/atom"
ATOM_BIN="$ATOM_DIR/main"

if ! command -v g++ &>/dev/null; then
    echo "  $WARN g++ not found — skipping ATOM compilation"
    echo "        Install g++ (macOS: xcode-select --install  |  Linux: sudo apt install g++)"
    ATOM_OK=false
else
    ATOM_LOG=$(mktemp)
    if (cd "$ATOM_DIR" && make -s 2>&1 > "$ATOM_LOG"); then
        if [ -f "$ATOM_BIN" ]; then
            echo "  $PASS ATOM compiled  →  algorithms/atom/main"
            ATOM_OK=true
        else
            echo "  $FAIL make succeeded but binary not found at algorithms/atom/main"
            cat "$ATOM_LOG"
            ATOM_OK=false
        fi
    else
        echo "  $FAIL ATOM compilation failed:"
        cat "$ATOM_LOG"
        ATOM_OK=false
    fi
    rm -f "$ATOM_LOG"
fi

# ── 3. Compile OCT ────────────────────────────────────────────────────────────
echo ""
echo "[ 3/3 ] Compiling OCT-Based..."

OCT_DIR="$REPO_DIR/algorithms/oct_based"
OCT_BIN="$OCT_DIR/embedding/driver"

if ! command -v g++ &>/dev/null; then
    echo "  $WARN g++ not found — skipping OCT compilation"
    OCT_OK=false
else
    OCT_LOG=$(mktemp)
    if (cd "$OCT_DIR" && TERM=xterm make build -s 2>&1 | col -b > "$OCT_LOG"); then
        if [ -f "$OCT_BIN" ]; then
            echo "  $PASS OCT compiled  →  algorithms/oct_based/embedding/driver"
            OCT_OK=true
        else
            echo "  $FAIL make succeeded but binary not found at algorithms/oct_based/embedding/driver"
            cat "$OCT_LOG"
            OCT_OK=false
        fi
    else
        echo "  $FAIL OCT compilation failed:"
        cat "$OCT_LOG"
        OCT_OK=false
    fi
    rm -f "$OCT_LOG"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo " Algorithm Availability"
echo "========================================"
echo "  $PASS minorminer       (always available — Python only)"
echo "  $PASS clique           (always available — Python only)"
if [ "$ATOM_OK" = true ]; then
    echo "  $PASS atom             (compiled)"
else
    echo "  $WARN atom             (not compiled — run: cd algorithms/atom && make)"
fi
if [ "$OCT_OK" = true ]; then
    echo "  $PASS oct-triad        (compiled)"
    echo "  $PASS oct-fast-oct     (compiled)"
    echo "  $PASS oct-hybrid-oct   (compiled)"
else
    echo "  $WARN oct-*            (not compiled — run: cd algorithms/oct_based && make build)"
fi
echo "  $WARN charme           (Python integration pending)"
echo ""
echo "========================================"
echo " Quick start:"
echo "========================================"
echo ""
echo "  from qebench import benchmark_one, load_test_graphs"
echo "  import dwave_networkx as dnx"
echo ""
echo "  chimera = dnx.chimera_graph(4, 4, 4)"
echo "  result  = benchmark_one(chimera, chimera, 'minorminer',"
echo "                          topology_name='chimera_4x4x4')"
echo "  print(result.success, result.avg_chain_length)"
echo ""
echo "  See README.md for full usage."
echo ""
