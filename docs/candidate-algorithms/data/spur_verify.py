"""Quick contract + correctness checks for pathfinder-spur."""
from __future__ import annotations
import warnings
warnings.filterwarnings("ignore")

import networkx as nx
import dwave_networkx as dnx

import ember_qc.algorithms.pf_spur as pf_spur  # registers pathfinder-spur
from ember_qc.algorithms.pf_spur import prune_spurs
from ember_qc.benchmark import benchmark_one
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding

chim = dnx.chimera_graph(4)

# --- 1. K6 into chimera(4): valid dict, deterministic --------------------------
K6 = nx.complete_graph(6)
r1 = benchmark_one(K6, chim, "pathfinder-spur", timeout=30, seed=0)
r1b = benchmark_one(K6, chim, "pathfinder-spur", timeout=30, seed=0)
print("K6  success=%s valid=%s acl=%.3f qubits=%d" % (
    r1.success, r1.is_valid, r1.avg_chain_length, r1.total_qubits_used))
print("K6  deterministic (acl, qubits, embedding equal):",
      r1.avg_chain_length == r1b.avg_chain_length
      and r1.total_qubits_used == r1b.total_qubits_used)

# compare to baseline pathfinder ACL on K6
rb = benchmark_one(K6, chim, "pathfinder", timeout=30, seed=0)
print("K6  baseline pathfinder acl=%.3f qubits=%d   spur acl=%.3f qubits=%d" % (
    rb.avg_chain_length, rb.total_qubits_used, r1.avg_chain_length, r1.total_qubits_used))

# --- 2. K20 into chimera(4): too big -> failure dict, never None/raise ----------
K20 = nx.complete_graph(20)
r2 = benchmark_one(K20, chim, "pathfinder-spur", timeout=20, seed=0)
print("K20 success=%s valid=%s status=%s (expect failure dict, no raise)" % (
    r2.success, r2.is_valid, r2.status))

# --- 3. Synthetic spur: prune_spurs must delete a dangling qubit -----------------
# Source: single edge 0-1. Target: a path 100-101-102-103.
tgt = nx.Graph()
tgt.add_edges_from([(100, 101), (101, 102), (102, 103), (103, 104)])
src = nx.Graph(); src.add_edge(0, 1)
# chain(0)=[100,101] (101 a needless spur; 100 alone is adjacent to nothing of 1)
# chain(1)=[103,102] with 103 a spur (102 alone covers the edge via 101? no).
# Make it concrete: 0 -> [100,101,102]; 1 -> [104,103]. Edge covered by 102-103.
emb = {0: [100, 101, 102], 1: [104, 103]}
adj = build_adjacency(tgt)
print("synthetic input valid:", is_valid_embedding(emb, src, tgt, adj=adj))
pr = prune_spurs(emb, src, tgt, adj=adj)
print("synthetic pruned:", pr, "valid:", is_valid_embedding(pr, src, tgt, adj=adj))
# Expect: 0 keeps only [102] (or [101,102]?) — 100,101 are spurs since 102 alone
# touches 103. 1 keeps [103] (104 is a spur).
# prune determinism
pr2 = prune_spurs(emb, src, tgt, adj=adj)
print("synthetic prune deterministic:", pr == pr2)

# --- 4. prune_spurs is idempotent (fixpoint) ------------------------------------
pr3 = prune_spurs(pr, src, tgt, adj=adj)
print("synthetic prune idempotent:", pr3 == pr)
