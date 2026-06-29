"""Sanity checks for the multilevel embedder (scratch, not a pytest module)."""
import io
import sys
import warnings
import hashlib
warnings.filterwarnings("ignore")

import networkx as nx
import dwave_networkx as dnx

import ember_qc.algorithms.multilevel  # noqa: F401 -> registers "multilevel"
from ember_qc.registry import ALGORITHM_REGISTRY
from ember_qc.benchmark import benchmark_one

algo = ALGORITHM_REGISTRY["multilevel"]
print("registered:", "multilevel" in ALGORITHM_REGISTRY, "| version:", algo.version)


def ghash(g):
    h = hashlib.sha256()
    h.update(str(sorted(g.nodes())).encode())
    h.update(str(sorted(g.edges())).encode())
    return h.hexdigest()


# 1. K6 -> chimera(4) must be VALID (via benchmark_one harness).
C4 = dnx.chimera_graph(4)
r = benchmark_one(nx.complete_graph(6), C4, "multilevel", timeout=30.0, seed=0)
print("\n[K6 -> C4] success=%s valid=%s status=%s acl=%.2f qubits=%d levels=%s prov=%s" % (
    r.success, r.is_valid, r.status, r.avg_chain_length, r.total_qubits_used,
    (r.metadata or {}).get("levels"), (r.metadata or {}).get("provenance")))
assert r.success and r.is_valid, "K6->C4 must be valid"

# 2. Determinism: same seed -> identical embedding.
e1 = algo.embed(nx.complete_graph(6), C4, timeout=30.0, seed=3)["embedding"]
e2 = algo.embed(nx.complete_graph(6), C4, timeout=30.0, seed=3)["embedding"]
print("[determinism K6] identical:", e1 == e2)
assert e1 == e2

# bigger ER determinism
src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(30, 0.5, seed=12345))
P6 = dnx.pegasus_graph(6)
d1 = algo.embed(src, P6, timeout=20.0, seed=1)
d2 = algo.embed(src, P6, timeout=20.0, seed=1)
print("[determinism ER30 P6] identical:", d1["embedding"] == d2["embedding"],
      "| valid:", bool(d1["embedding"]) and __import__("ember_qc.embedding_backend", fromlist=["is_valid_embedding"]).is_valid_embedding(d1["embedding"], src, P6),
      "| prov:", (d1.get("metadata") or {}).get("provenance"),
      "| levels:", (d1.get("metadata") or {}).get("levels"))
assert d1["embedding"] == d2["embedding"]

# 3. Graceful failure: K20 -> path_graph(2).
fr = algo.embed(nx.complete_graph(20), nx.path_graph(2), timeout=1.0, seed=0)
print("[K20 -> P2] embedding:", fr["embedding"], "| success flag:", fr.get("success"))
assert fr["embedding"] == {}
assert fr.get("success") is False

# 4. No stdout / no input mutation / returns dict.
src2 = nx.complete_graph(6); tgt2 = C4.copy()
hs, ht = ghash(src2), ghash(tgt2)
buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
try:
    res = algo.embed(src2, tgt2, timeout=10.0, seed=0)
finally:
    sys.stdout = old
print("[stdout empty]:", buf.getvalue() == "", "| inputs unchanged:",
      ghash(src2) == hs and ghash(tgt2) == ht, "| is dict:", isinstance(res, dict))
assert buf.getvalue() == ""
assert ghash(src2) == hs and ghash(tgt2) == ht

# 5. Timeout respected (K15 -> chimera, 0.5s budget, must finish well under 5s).
import time
t0 = time.perf_counter()
rt = algo.embed(nx.complete_graph(15), C4, timeout=0.5, seed=0)
el = time.perf_counter() - t0
print("[timeout 0.5s] elapsed=%.2fs (<5s required) returned_dict=%s" % (el, isinstance(rt, dict)))
assert el < 5.0

# 6. Counters present, non-neg ints, seed-stable.
ra = algo.embed(nx.complete_graph(6), C4, timeout=10.0, seed=7)
rb = algo.embed(nx.complete_graph(6), C4, timeout=10.0, seed=7)
for k in ["target_node_visits", "cost_function_evaluations",
          "embedding_state_mutations", "overlap_qubit_iterations"]:
    assert isinstance(ra[k], int) and not isinstance(ra[k], bool) and ra[k] >= 0, (k, ra[k])
    assert ra[k] == rb[k], (k, ra[k], rb[k])
print("[counters] ok:", {k: ra[k] for k in ["target_node_visits", "cost_function_evaluations", "embedding_state_mutations", "overlap_qubit_iterations"]})

print("\nALL SANITY CHECKS PASSED")
