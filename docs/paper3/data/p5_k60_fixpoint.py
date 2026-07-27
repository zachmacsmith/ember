"""§4.4: sequential exact-move fixpoint on the K60/P16 template.

Run: .venv/bin/python docs/paper3/data/p5_k60_fixpoint.py
Deterministic, seedless, ~<=30 min. Output: p5_k60_fixpoint.txt (+ stdout).
"""
from __future__ import annotations

import time

import dwave_networkx as dnx
import networkx as nx
from minorminer import busclique

from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.algorithms.paper3.joint_repair import anytime_polish
from ember_qc.embedding_backend import is_valid_embedding

DEADLINE_S = 30 * 60
N = 60

def main() -> None:
    t0 = time.perf_counter()
    target = dnx.pegasus_graph(16)
    source = nx.complete_graph(N)
    raw = busclique.busgraph_cache(target).find_clique_embedding(N)
    emb = {i: list(raw[k]) for i, k in enumerate(sorted(raw))}
    emb = spur_prune(emb, source, target)
    q0 = sum(len(c) for c in emb.values())
    acl0 = q0 / N
    print(f"start: qubits={q0} ACL={acl0:.4f} (expect 404 / 6.7333)", flush=True)

    polished = anytime_polish(emb, source, target, deadline=DEADLINE_S)
    q1 = sum(len(c) for c in polished.values())
    acl1 = q1 / N
    ok = is_valid_embedding(polished, source, target)
    dt = time.perf_counter() - t0
    lines = [
        f"K60/P16 exact-move fixpoint ({time.strftime('%Y-%m-%d')})",
        f"start:  qubits={q0}  ACL={acl0:.4f}",
        f"end:    qubits={q1}  ACL={acl1:.4f}  valid={ok}",
        f"gain:   {q0 - q1} qubits  dACL={acl0 - acl1:.4f}",
        f"wall:   {dt:.1f}s (deadline {DEADLINE_S}s)",
    ]
    out = "\n".join(lines)
    print(out, flush=True)
    with open(__file__.replace(".py", ".txt"), "w") as fh:
        fh.write(out + "\n")

if __name__ == "__main__":
    main()
