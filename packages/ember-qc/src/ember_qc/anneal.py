"""
ember_qc/anneal.py
==================
Helpers for the solution-quality validation: a random Ising generator and a
**spin-vector Monte Carlo (SVMC)** sampler — a semiclassical proxy for quantum
annealing (Shin, Smith, Smolin & Vazirani 2014) used as a cross-check on the
classical simulated-annealing results.

Embedding, unembedding, and classical simulated annealing themselves use the
D-Wave reference implementations (``dwave.embedding``, ``dwave.samplers``); only
SVMC is hand-rolled here. In SVMC each qubit is a classical O(2) rotor with angle
``theta in [0, pi]`` (``sigma^z -> cos theta``, ``sigma^x -> sin theta``); the
system is annealed under

    H(s) = -A(s) * sum_i sin theta_i
           + B(s) * ( sum_i h_i cos theta_i + sum_{i<j} J_ij cos theta_i cos theta_j )

with a transverse field ``A(s)=1-s`` turning off and the problem ``B(s)=s`` turning
on as ``s`` runs 0 -> 1, by Metropolis updates at inverse temperature ``beta``. The
readout is ``spin_i = sign(cos theta_i)``. The vectorization is over the reads.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import networkx as nx


def random_ising(G: nx.Graph, seed: int = 0, kind: str = "pm1") -> Tuple[dict, dict]:
    """A random Ising (h, J) on the vertices/edges of ``G``.

    ``kind='pm1'`` draws h, J uniformly from {-1, +1}; ``'gauss'`` from N(0, 1)."""
    rng = np.random.default_rng(seed)
    if kind == "gauss":
        h = {v: float(rng.normal()) for v in G.nodes()}
        J = {(u, v): float(rng.normal()) for u, v in G.edges()}
    else:
        h = {v: float(rng.choice([-1.0, 1.0])) for v in G.nodes()}
        J = {(u, v): float(rng.choice([-1.0, 1.0])) for u, v in G.edges()}
    return h, J


def ising_energy(h: dict, J: dict, sample: dict) -> float:
    e = sum(h[v] * sample[v] for v in h)
    e += sum(w * sample[u] * sample[v] for (u, v), w in J.items())
    return float(e)


def svmc_sample(h: dict, J: dict, num_reads: int = 64, num_sweeps: int = 1000,
                beta: float = 5.0, seed: int = 0) -> List[Dict[int, int]]:
    """Spin-vector Monte Carlo. Returns ``num_reads`` samples (qubit -> +/-1).

    Vectorized over reads; suitable for the embedded problems in the
    solution-quality cross-check (tens-to-low-hundreds of qubits)."""
    qubits = sorted(set(h) | {q for e in J for q in e})
    idx = {q: i for i, q in enumerate(qubits)}
    Q = len(qubits)
    hv = np.array([h.get(q, 0.0) for q in qubits], dtype=float)
    nbr: List[list] = [[] for _ in range(Q)]
    jw: List[list] = [[] for _ in range(Q)]
    for (u, v), w in J.items():
        i, j = idx[u], idx[v]
        nbr[i].append(j); jw[i].append(w)
        nbr[j].append(i); jw[j].append(w)
    nbr = [np.array(x, dtype=int) for x in nbr]
    jw = [np.array(x, dtype=float) for x in jw]

    rng = np.random.default_rng(seed)
    theta = rng.uniform(0.0, np.pi, size=(num_reads, Q))
    denom = max(1, num_sweeps - 1)
    for step in range(num_sweeps):
        s = step / denom
        A, B = 1.0 - s, s
        for i in range(Q):
            if nbr[i].size:
                nf = (np.cos(theta[:, nbr[i]]) * jw[i]).sum(axis=1)
            else:
                nf = np.zeros(num_reads)
            th_old = theta[:, i]
            th_new = rng.uniform(0.0, np.pi, size=num_reads)
            dcos = np.cos(th_new) - np.cos(th_old)
            dsin = np.sin(th_new) - np.sin(th_old)
            dE = -A * dsin + B * (hv[i] * dcos + dcos * nf)
            accept = (dE <= 0) | (rng.random(num_reads) < np.exp(-beta * np.minimum(dE, 30.0)))
            theta[accept, i] = th_new[accept]

    spins = np.where(np.cos(theta) >= 0.0, 1, -1)
    return [{qubits[j]: int(spins[r, j]) for j in range(Q)} for r in range(num_reads)]
