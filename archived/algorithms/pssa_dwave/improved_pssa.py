"""
pssa_dwave/improved_pssa.py
============================
Improved PSSA for D-Wave hardware — public API.

Two ways to use this:

1. Standalone (any networkx graph):
       from pssa_dwave import embed, ImprovedPSSA
       success, phi = embed(I, topology="chimera", size=4)

2. QEBench plugin (drop into Quantum_Embedding_benchmark):
       The bottom of this file registers PSSA variants with
       @register_algorithm if qebench is importable.
       Just import this module and all variants appear in the registry.
"""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import networkx as nx

from pssa_dwave.core import (
    DWaveSchedule, Phi, NodeH, NodeI,
    build_hardware_graph, build_guiding_pattern,
    eemb, invert, pssa,
)
from pssa_dwave.terminal_search import terminal_search


# ===========================================================================
# Result container
# ===========================================================================

@dataclass
class EmbeddingResult:
    success:    bool
    phi:        Phi
    eemb:       int
    m_I:        int
    wall_time:  float
    topology:   str
    size:       int
    n_hw:       int

    @property
    def coverage(self) -> float:
        return self.eemb / self.m_I if self.m_I > 0 else 1.0

    def __str__(self):
        return (
            f"EmbeddingResult({self.topology}({self.size}), "
            f"{'✓' if self.success else '✗'} "
            f"{self.eemb}/{self.m_I} edges, "
            f"{self.wall_time:.2f}s)"
        )


# ===========================================================================
# Validity check
# ===========================================================================

def is_valid_embedding(phi: Phi, I: nx.Graph, H: nx.Graph) -> bool:
    """Verify M1 (connected), M2 (disjoint), M3 (edge coverage)."""
    inv = invert(phi)

    for i, sv in phi.items():
        if not sv:
            return False
        if len(sv) > 1 and not nx.is_connected(H.subgraph(sv)):
            return False

    all_hw = [u for sv in phi.values() for u in sv]
    if len(all_hw) != len(set(all_hw)):
        return False

    for i, j in I.edges():
        if not any(H.has_edge(u, v) for u in phi[i] for v in phi[j]):
            return False

    return True


# ===========================================================================
# Improved PSSA — main class
# ===========================================================================

class ImprovedPSSA:
    """
    Improved PSSA for D-Wave hardware (Chimera / Pegasus / Zephyr).

    Algorithm 1 (PSSA) + Algorithm 2 (terminal search) + D-Wave tuned schedule.

    Parameters
    ----------
    topology    : "chimera" | "pegasus" | "zephyr"
    size        : topology size parameter (m for chimera/pegasus, m for zephyr)
    tmax        : annealing steps. None = auto-scale to hardware size
    weighted    : degree-weighted shift proposals (best for cubic/regular graphs)
    T0          : phase 1 initial temperature. None = topology default
    Thalf       : phase 2 initial temperature. None = topology default
    beta        : exponential cooling factor. None = topology default
    cool_every  : steps between temperature updates (default 1000)
    pa_end      : final any-direction shift probability. None = topology default
    seed        : random seed
    verbose     : print annealing progress
    hardware_graph : supply your own nx.Graph instead of building from topology/size
                     useful for broken-qubit / subset hardware
    """

    def __init__(
        self,
        topology:        str  = "chimera",
        size:            int  = 4,
        tmax:            Optional[int]   = None,
        weighted:        bool = False,
        T0:              Optional[float] = None,
        Thalf:           Optional[float] = None,
        beta:            Optional[float] = None,
        cool_every:      int  = 1000,
        pa_end:          Optional[float] = None,
        seed:            Optional[int]   = None,
        verbose:         bool = False,
        hardware_graph:  Optional[nx.Graph] = None,
    ):
        self.topology  = topology
        self.size      = size
        self.weighted  = weighted
        self.seed      = seed
        self.verbose   = verbose

        # Build or accept hardware graph
        if hardware_graph is not None:
            self.H = hardware_graph
        else:
            self.H = build_hardware_graph(topology, size)

        n_hw = self.H.number_of_nodes()

        # Build schedule
        _tmax = tmax if tmax is not None else max(200_000, int(7e7 * n_hw / 102_400))
        self.schedule = DWaveSchedule(
            tmax       = _tmax,
            topology   = topology,
            T0         = T0,
            Thalf      = Thalf,
            beta       = beta,
            cool_every = cool_every,
            pa_end     = pa_end,
        )

        # Build guiding pattern
        self.gp = build_guiding_pattern(self.H, topology, size)

        if verbose:
            print(f"Hardware: {topology}({size}), {n_hw} nodes, "
                  f"{self.H.number_of_edges()} edges")
            print(f"Guiding pattern: {len(self.gp)} super vertices")
            print(self.schedule.summary())

    def run(self, I: nx.Graph) -> EmbeddingResult:
        """Embed input graph I into the hardware graph."""
        t0  = time.time()
        m_I = I.number_of_edges()

        phi_pssa, e_pssa = pssa(
            I, self.H, self.gp, self.schedule,
            weighted=self.weighted,
            seed=self.seed,
            verbose=self.verbose,
        )

        phi_final = terminal_search(phi_pssa, I, self.H)
        inv_final = invert(phi_final)
        e_final   = eemb(phi_final, I, self.H, inv_final)

        success = (e_final == m_I) and is_valid_embedding(phi_final, I, self.H)
        elapsed = time.time() - t0

        return EmbeddingResult(
            success   = success,
            phi       = phi_final,
            eemb      = e_final,
            m_I       = m_I,
            wall_time = elapsed,
            topology  = self.topology,
            size      = self.size,
            n_hw      = self.H.number_of_nodes(),
        )


# ===========================================================================
# Convenience function
# ===========================================================================

def embed(
    I:          nx.Graph,
    topology:   str  = "chimera",
    size:       int  = 4,
    tmax:       Optional[int]   = None,
    weighted:   bool = False,
    seed:       Optional[int]   = None,
    verbose:    bool = False,
    hardware_graph: Optional[nx.Graph] = None,
) -> Tuple[bool, Phi]:
    """
    One-line embed interface.

    Example
    -------
        import networkx as nx
        from pssa_dwave import embed

        I = nx.random_regular_graph(3, 20, seed=0)
        success, phi = embed(I, topology="chimera", size=4, seed=42)
    """
    algo   = ImprovedPSSA(topology=topology, size=size, tmax=tmax,
                          weighted=weighted, seed=seed, verbose=verbose,
                          hardware_graph=hardware_graph)
    result = algo.run(I)
    return result.success, result.phi


# ===========================================================================
# QEBench plugin registration
# Automatically registers PSSA variants if qebench is installed.
# To use: import pssa_dwave.improved_pssa  (anywhere before running bench)
# ===========================================================================

def _register_qebench_algorithms():
    """Register PSSA variants into QEBench's algorithm registry."""
    try:
        from qebench.registry import register_algorithm, EmbeddingAlgorithm
    except ImportError:
        return   # qebench not installed — standalone mode only

    import time as _time

    class _PSSABase(EmbeddingAlgorithm):
        """Base for PSSA QEBench wrappers."""
        _topology = "chimera"
        _weighted = False
        _tmax_override = None

        def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
            try:
                t0 = _time.time()

                # Detect topology from graph metadata if available
                topology = self._detect_topology(target_graph)
                size     = self._detect_size(target_graph, topology)

                algo = ImprovedPSSA(
                    topology       = topology,
                    size           = size,
                    tmax           = self._tmax_override,
                    weighted       = self._weighted,
                    hardware_graph = target_graph,   # use the graph as-is
                    verbose        = False,
                )
                result = algo.run(source_graph)

                elapsed = _time.time() - t0
                if not result.success and result.eemb == 0:
                    return None

                return {
                    'embedding': result.phi,
                    'time':      elapsed,
                    'coverage':  result.coverage,
                    'eemb':      result.eemb,
                    'm_I':       result.m_I,
                }
            except Exception as e:
                print(f"PSSA error: {e}")
                return None

        def _detect_topology(self, H: nx.Graph) -> str:
            """Guess D-Wave topology from graph metadata."""
            data = H.graph
            if 'family' in data:
                fam = str(data['family']).lower()
                if 'chimera' in fam:
                    return 'chimera'
                if 'pegasus' in fam:
                    return 'pegasus'
                if 'zephyr' in fam:
                    return 'zephyr'
            # Heuristic by average degree
            avg_deg = sum(d for _, d in H.degree()) / max(H.number_of_nodes(), 1)
            if avg_deg < 8:
                return 'chimera'
            elif avg_deg < 18:
                return 'pegasus'
            else:
                return 'zephyr'

        def _detect_size(self, H: nx.Graph, topology: str) -> int:
            """Guess topology size parameter from node count."""
            n = H.number_of_nodes()
            if topology == 'chimera':
                # n = 2*m*m*t, t=4 → m = sqrt(n/8)
                import math
                return max(1, round(math.sqrt(n / 8)))
            elif topology == 'pegasus':
                # n ≈ 24*(m-1)^2 → m ≈ sqrt(n/24) + 1
                import math
                return max(2, round(math.sqrt(n / 24) + 1))
            elif topology == 'zephyr':
                # n = 4*m*(2m+1) → solve quadratic
                import math
                m = (-1 + math.sqrt(1 + 2 * n)) / 4
                return max(1, round(m))
            return 4

    @register_algorithm("pssa")
    class PSSADefault(_PSSABase):
        """PSSA — path-annealing minor embedding, auto topology detection."""
        pass

    @register_algorithm("pssa-weighted")
    class PSSAWeighted(_PSSABase):
        """PSSA with degree-weighted shifts — best for regular/cubic graphs."""
        _weighted = True

    @register_algorithm("pssa-fast")
    class PSSAFast(_PSSABase):
        """PSSA with reduced tmax — faster, lower quality. tmax = 50,000."""
        _tmax_override = 50_000

    @register_algorithm("pssa-thorough")
    class PSSAThorough(_PSSABase):
        """PSSA with extended tmax — slower, higher quality. tmax = 2,000,000."""
        _tmax_override = 2_000_000


# Run registration on import
_register_qebench_algorithms()
