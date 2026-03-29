"""
ember_qc/algorithms/pssa.py
============================
PSSA — Path Super-Vertex Simulated Annealing for D-Wave hardware.

Adapted from Sugie et al. (2020) for Chimera / Pegasus / Zephyr topologies:
  - Replaces King's graph with D-Wave hardware graphs
  - Replaces Okuyama diagonal-stripe guiding pattern with busclique clique embedding
  - Double-exponential annealing schedule with topology-specific parameters
  - Algorithm 2 (terminal search) post-processing

Usage (standalone):
    from ember_qc.algorithms.pssa import embed, ImprovedPSSA
    success, phi = embed(I, topology="chimera", size=4, seed=42)

Usage (ember-qc registry):
    Registered automatically on import via _register_pssa_algorithms().
    Algorithms: "pssa", "pssa-weighted", "pssa-fast", "pssa-thorough"
"""

import logging
import math
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
NodeI  = int
NodeH  = int
Phi    = Dict[NodeI, List[NodeH]]
InvPhi = Dict[NodeH, NodeI]


# ===========================================================================
# Hardware graph builders
# ===========================================================================

def build_hardware_graph(topology: str, size: int) -> nx.Graph:
    """
    Build a D-Wave hardware graph.

    Parameters
    ----------
    topology : "chimera" | "pegasus" | "zephyr"
    size     : the m parameter
    """
    try:
        import dwave_networkx as dnx
        if topology == "chimera":
            G = dnx.chimera_graph(size)
        elif topology == "pegasus":
            G = dnx.pegasus_graph(size)
        elif topology == "zephyr":
            G = dnx.zephyr_graph(size)
        else:
            raise ValueError(f"Unknown topology '{topology}'. Use: chimera, pegasus, zephyr")
        return nx.convert_node_labels_to_integers(G)
    except ImportError:
        raise ImportError("dwave-networkx is required: pip install dwave-networkx")


# ===========================================================================
# Guiding pattern — busclique clique embedding
# ===========================================================================

def build_guiding_pattern(H: nx.Graph, topology: str, size: int) -> Dict[int, List[NodeH]]:
    """
    Build the guiding pattern using busclique (falls back to path partition).

    Returns {sv_index: [hw_node, ...]} — one entry per guiding super vertex.
    """
    try:
        from minorminer.busclique import find_clique_embedding
        import dwave_networkx as dnx

        try:
            if topology == "chimera":
                topo_graph = dnx.chimera_graph(size)
            elif topology == "pegasus":
                topo_graph = dnx.pegasus_graph(size)
            elif topology == "zephyr":
                topo_graph = dnx.zephyr_graph(size)
            else:
                topo_graph = H

            n_nodes = H.number_of_nodes()
            lo, hi = 2, min(n_nodes, 300)
            best_emb: Dict = {}
            while lo <= hi:
                mid = (lo + hi) // 2
                emb = find_clique_embedding(mid, topo_graph)
                if emb:
                    best_emb = emb
                    lo = mid + 1
                else:
                    hi = mid - 1

            if best_emb:
                node_map = {v: i for i, v in enumerate(H.nodes())}
                gp: Dict[int, List[NodeH]] = {}
                for sv_idx, chain in best_emb.items():
                    try:
                        int_chain = [int(u) for u in chain]
                    except (TypeError, ValueError):
                        int_chain = [node_map.get(u, u) for u in chain]
                    gp[sv_idx] = int_chain
                return gp
        except Exception:
            pass

        # Fallback: busclique on the already-relabelled H
        n_nodes = H.number_of_nodes()
        lo, hi = 2, min(n_nodes, 200)
        best_emb = {}
        while lo <= hi:
            mid = (lo + hi) // 2
            emb = find_clique_embedding(mid, H)
            if emb:
                best_emb = emb
                lo = mid + 1
            else:
                hi = mid - 1
        if best_emb:
            return {k: list(v) for k, v in best_emb.items()}

    except ImportError:
        pass

    return _path_partition_guiding(H)


def _path_partition_guiding(H: nx.Graph) -> Dict[int, List[NodeH]]:
    """Fallback: greedily grow connected paths covering all H nodes."""
    visited: Set[NodeH] = set()
    paths: List[List[NodeH]] = []
    for start in sorted(H.nodes()):
        if start in visited:
            continue
        path = [start]
        visited.add(start)
        frontier = start
        while True:
            nbrs = [v for v in H.neighbors(frontier) if v not in visited]
            if not nbrs:
                break
            nxt = nbrs[0]
            path.append(nxt)
            visited.add(nxt)
            frontier = nxt
        paths.append(path)
    return {i: path for i, path in enumerate(paths)}


# ===========================================================================
# Initial placement
# ===========================================================================

def initial_placement(I: nx.Graph, gp: Dict[int, List[NodeH]], H: nx.Graph) -> Phi:
    """Split guiding pattern into |V(I)| path super vertices."""
    nodes_I = sorted(I.nodes())
    n = len(nodes_I)

    all_hw: List[NodeH] = []
    for gk in sorted(gp.keys()):
        all_hw.extend(gp[gk])

    seen: Set[NodeH] = set()
    unique_hw: List[NodeH] = []
    for u in all_hw:
        if u not in seen:
            unique_hw.append(u)
            seen.add(u)
    for u in sorted(H.nodes()):
        if u not in seen:
            unique_hw.append(u)
            seen.add(u)

    total = len(unique_hw)
    block = total // n
    remainder = total % n

    phi: Phi = {}
    idx = 0
    for ni, v in enumerate(nodes_I):
        size = block + (1 if ni < remainder else 0)
        phi[v] = unique_hw[idx: idx + size]
        idx += size
    return phi


# ===========================================================================
# Utilities
# ===========================================================================

def invert(phi: Phi) -> InvPhi:
    inv: InvPhi = {}
    for i, path in phi.items():
        for u in path:
            inv[u] = i
    return inv


def eemb(phi: Phi, I: nx.Graph, H: nx.Graph, inv: InvPhi) -> int:
    """Count embedded edges Eemb(φ)."""
    covered: Set[Tuple[NodeI, NodeI]] = set()
    for u, v in H.edges():
        i = inv.get(u)
        j = inv.get(v)
        if i is None or j is None or i == j:
            continue
        edge = (min(i, j), max(i, j))
        if edge not in covered and I.has_edge(i, j):
            covered.add(edge)
    return len(covered)


def _leaves(path: List[NodeH]) -> List[NodeH]:
    if len(path) == 1:
        return [path[0]]
    return [path[0], path[-1]]


def _remove_leaf(path: List[NodeH], u: NodeH) -> List[NodeH]:
    if path[0] == u:
        return path[1:]
    return path[:-1]


def _attach_leaf(path: List[NodeH], u: NodeH, v: NodeH) -> List[NodeH]:
    if path[0] == v:
        return [u] + path
    return path + [u]


# ===========================================================================
# Annealing schedule
# ===========================================================================

class DWaveSchedule:
    """
    Double-exponential annealing schedule tuned per D-Wave topology.

    Topology defaults (T0, Thalf, beta, pa_end):
      chimera  (degree ~6):  (70,  40,  0.9998,  0.40)  — most exploration
      pegasus  (degree ~15): (55,  28,  0.9999,  0.487) — paper defaults
      zephyr   (degree ~20): (45,  22,  0.99995, 0.55)  — least exploration
    """
    TOPOLOGY_DEFAULTS = {
        "chimera": (70.0,  40.0,  0.9998,  0.40),
        "pegasus": (55.0,  28.0,  0.9999,  0.487),
        "zephyr":  (45.0,  22.0,  0.99995, 0.55),
    }

    def __init__(
        self,
        tmax:        int,
        topology:    str            = "chimera",
        T0:          Optional[float] = None,
        Thalf:       Optional[float] = None,
        beta:        Optional[float] = None,
        cool_every:  int            = 1000,
        ps0:         float          = 1.0,
        ps_end:      float          = 0.0,
        pa0:         float          = 0.095,
        pa_end:      Optional[float] = None,
    ):
        defaults    = self.TOPOLOGY_DEFAULTS.get(topology, self.TOPOLOGY_DEFAULTS["chimera"])
        self.tmax   = tmax
        self.T0     = T0     if T0     is not None else defaults[0]
        self.Thalf  = Thalf  if Thalf  is not None else defaults[1]
        self.beta   = beta   if beta   is not None else defaults[2]
        self.pa_end = pa_end if pa_end is not None else defaults[3]
        self.cool_every = cool_every
        self.ps0    = ps0
        self.ps_end = ps_end
        self.pa0    = pa0
        self.topology = topology
        self._half  = tmax // 2

    def temperature(self, t: int) -> float:
        if t < self._half:
            return self.T0    * (self.beta ** (t // self.cool_every))
        return self.Thalf * (self.beta ** ((t - self._half) // self.cool_every))

    def ps(self, t: int) -> float:
        return self.ps0 + (self.ps_end - self.ps0) * t / self.tmax

    def pa(self, t: int) -> float:
        return self.pa0 + (self.pa_end - self.pa0) * t / self.tmax

    def summary(self) -> str:
        return (
            f"DWaveSchedule({self.topology}): "
            f"T0={self.T0}, Thalf={self.Thalf}, beta={self.beta}, "
            f"tmax={self.tmax:,}, pa_end={self.pa_end}"
        )


def _shift_direction_prob(i, j, phi, deg, weighted):
    if not weighted:
        return 0.5
    dri = len(phi[i]) / max(deg[i], 1)
    drj = len(phi[j]) / max(deg[j], 1)
    denom = dri + drj
    return 0.5 if denom == 0 else dri / denom


# ===========================================================================
# Algorithm 1: PSSA
# ===========================================================================

def pssa(
    I:        nx.Graph,
    H:        nx.Graph,
    gp:       Dict[int, List[NodeH]],
    schedule: DWaveSchedule,
    weighted: bool           = False,
    seed:     Optional[int]  = None,
    verbose:  bool           = False,
    deadline: Optional[float] = None,
) -> Tuple[Phi, int]:
    """PSSA Algorithm 1 (Sugie et al. 2020) for D-Wave hardware."""
    if seed is not None:
        random.seed(seed)

    nodes_I  = sorted(I.nodes())
    edges_I  = list(I.edges())
    m_I      = len(edges_I)
    deg      = dict(I.degree())
    H_adj: Dict[NodeH, Set[NodeH]] = {u: set(H.neighbors(u)) for u in H.nodes()}

    gp_lookup: Dict[NodeH, int] = {}
    for gk, path in gp.items():
        for hw in path:
            gp_lookup[hw] = gk

    phi     = initial_placement(I, gp, H)
    inv     = invert(phi)
    cur_e   = eemb(phi, I, H, inv)

    phi_best  = {i: list(p) for i, p in phi.items()}
    eemb_best = cur_e

    if eemb_best == m_I:
        return phi_best, eemb_best

    tmax = schedule.tmax
    log_every = max(1, tmax // 10)

    for t in range(tmax):
        if deadline is not None and t % 1000 == 0 and time.time() > deadline:
            break
        T  = schedule.temperature(t)
        ps = schedule.ps(t)
        pa = schedule.pa(t)

        if verbose and t % log_every == 0:
            print(f"  t={t:>9,} ({100*t//tmax:3d}%)  T={T:6.3f}  Eemb={cur_e}/{m_I}")

        if random.random() < ps:
            # ---- SHIFT ----
            candidates = [i for i in nodes_I if len(phi[i]) > 1]
            if not candidates:
                continue
            i = random.choice(candidates)
            leaves_i = _leaves(phi[i])
            u = random.choice(leaves_i)
            allow_any = random.random() < pa

            candidate_jv: List[Tuple[NodeI, NodeH]] = []
            for v in H_adj[u]:
                j = inv.get(v)
                if j is None or j == i:
                    continue
                if v not in _leaves(phi[j]):
                    continue
                if allow_any or gp_lookup.get(u) == gp_lookup.get(v):
                    candidate_jv.append((j, v))

            if not candidate_jv:
                continue

            j, v = random.choice(candidate_jv)
            p_ij = _shift_direction_prob(i, j, phi, deg, weighted)

            if random.random() < p_ij:
                new_phi_i = _remove_leaf(phi[i], u)
                new_phi_j = _attach_leaf(phi[j], u, v)
                hw_changed, new_owner = u, j
            else:
                if len(phi[j]) < 2:
                    continue
                new_phi_j = _remove_leaf(phi[j], v)
                new_phi_i = _attach_leaf(phi[i], v, u)
                hw_changed, new_owner = v, i

            phi_prop    = {k: phi[k] for k in phi}
            phi_prop[i] = new_phi_i
            phi_prop[j] = new_phi_j
            inv_prop    = dict(inv)
            inv_prop[hw_changed] = new_owner

        else:
            # ---- SWAP ----
            if not edges_I:
                continue
            ie, k = random.choice(edges_I)
            adjacent_j: Set[NodeI] = set()
            for hw_k in phi[k]:
                for hw_nbr in H_adj[hw_k]:
                    j_cand = inv.get(hw_nbr)
                    if j_cand is not None and j_cand != k and j_cand != ie:
                        adjacent_j.add(j_cand)
            if not adjacent_j:
                continue
            j = random.choice(list(adjacent_j))

            phi_prop     = {k2: phi[k2] for k2 in phi}
            phi_prop[ie] = list(phi[j])
            phi_prop[j]  = list(phi[ie])
            inv_prop     = dict(inv)
            for hw in phi[ie]:
                inv_prop[hw] = j
            for hw in phi[j]:
                inv_prop[hw] = ie

        # ---- Metropolis acceptance ----
        prop_e = eemb(phi_prop, I, H, inv_prop)
        delta  = prop_e - cur_e

        if T > 0:
            accept = math.exp(min(delta / T, 0)) > random.random() if delta < 0 else True
        else:
            accept = delta >= 0

        if accept:
            phi   = phi_prop
            inv   = inv_prop
            cur_e = prop_e
            if cur_e > eemb_best:
                phi_best  = {k: list(p) for k, p in phi.items()}
                eemb_best = cur_e
            if eemb_best == m_I:
                if verbose:
                    print(f"  Embedding found at t={t:,}")
                return phi_best, eemb_best

    return phi_best, eemb_best


# ===========================================================================
# Algorithm 2: Terminal search
# ===========================================================================

def _repr_counts(phi, I, H, inv):
    counts = defaultdict(int)
    for u, v in H.edges():
        i = inv.get(u)
        j = inv.get(v)
        if i is None or j is None or i == j:
            continue
        edge = (min(i, j), max(i, j))
        if I.has_edge(i, j):
            counts[edge] += 1
    return counts


def _is_deletable(u, i, phi, I, H, inv, repr_counts):
    sv = phi[i]
    if len(sv) <= 1:
        return False
    remaining = [w for w in sv if w != u]
    if not nx.is_connected(H.subgraph(remaining)):
        return False
    for v in H.neighbors(u):
        j = inv.get(v)
        if j is None or j == i or not I.has_edge(i, j):
            continue
        edge = (min(i, j), max(i, j))
        via_u = sum(1 for w in H.neighbors(u) if inv.get(w) == j)
        if repr_counts.get(edge, 0) - via_u <= 0:
            return False
    return True


def _bfs_path(i, j, phi, H, free):
    source = set(phi[i])
    target = set(phi[j])
    queue  = deque(source)
    parent: Dict[NodeH, Optional[NodeH]] = {u: None for u in source}
    visited = set(source)
    while queue:
        u = queue.popleft()
        for v in H.neighbors(u):
            if v in visited:
                continue
            if v not in free and v not in target:
                continue
            if v in target:
                path: List[NodeH] = []
                cur = u
                while cur not in source:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
            visited.add(v)
            parent[v] = u
            queue.append(v)
    return None


def terminal_search(phi: Phi, I: nx.Graph, H: nx.Graph) -> Phi:
    """Algorithm 2 — Terminal search. Works on any D-Wave topology."""
    phi = {i: list(p) for i, p in phi.items()}
    inv = invert(phi)
    rc  = _repr_counts(phi, I, H, inv)

    hw_nodes = list(H.nodes())
    n_hw     = len(hw_nodes)
    free: Set[NodeH] = set()
    no_del = 0
    idx    = 0

    # Phase 1: free wasted hardware nodes
    while no_del < n_hw:
        u = hw_nodes[idx % n_hw]
        idx += 1
        i = inv.get(u)
        if i is None or u in free:
            no_del += 1
            continue
        if _is_deletable(u, i, phi, I, H, inv, rc):
            phi[i] = [w for w in phi[i] if w != u]
            del inv[u]
            free.add(u)
            for v in H.neighbors(u):
                j = inv.get(v)
                if j is None or j == i or not I.has_edge(i, j):
                    continue
                edge = (min(i, j), max(i, j))
                via_u = sum(1 for w in H.neighbors(u) if inv.get(w) == j)
                rc[edge] = max(0, rc.get(edge, 0) - via_u)
            no_del = 0
        else:
            no_del += 1

    # Phase 2: BFS link remaining unconnected input edges
    for i in sorted(I.nodes()):
        for j in I.neighbors(i):
            if j <= i:
                continue
            linked = any(inv.get(v) == j for u in phi[i] for v in H.neighbors(u))
            if linked:
                continue
            path = _bfs_path(i, j, phi, H, free)
            if path is not None:
                for v in path:
                    phi[i].append(v)
                    inv[v] = i
                    free.discard(v)
                edge = (min(i, j), max(i, j))
                rc[edge] = rc.get(edge, 0) + 1

    return phi


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
# Result container
# ===========================================================================

@dataclass
class PSSAResult:
    success:   bool
    phi:       Phi
    eemb:      int
    m_I:       int
    wall_time: float
    topology:  str
    size:      int
    n_hw:      int

    @property
    def coverage(self) -> float:
        return self.eemb / self.m_I if self.m_I > 0 else 1.0

    def __str__(self):
        return (
            f"PSSAResult({self.topology}({self.size}), "
            f"{'ok' if self.success else 'fail'} "
            f"{self.eemb}/{self.m_I} edges, {self.wall_time:.2f}s)"
        )


# ===========================================================================
# ImprovedPSSA — main class
# ===========================================================================

class ImprovedPSSA:
    """
    PSSA + terminal search for D-Wave hardware.

    Parameters
    ----------
    topology       : "chimera" | "pegasus" | "zephyr"
    size           : topology m parameter
    tmax           : annealing steps (None = auto-scale to hardware size)
    weighted       : degree-weighted shift proposals
    hardware_graph : supply your own nx.Graph (for faulty-qubit hardware)
    seed           : random seed
    verbose        : print annealing progress
    """

    def __init__(
        self,
        topology:       str             = "chimera",
        size:           int             = 4,
        tmax:           Optional[int]   = None,
        weighted:       bool            = False,
        T0:             Optional[float] = None,
        Thalf:          Optional[float] = None,
        beta:           Optional[float] = None,
        cool_every:     int             = 1000,
        pa_end:         Optional[float] = None,
        seed:           Optional[int]   = None,
        verbose:        bool            = False,
        hardware_graph: Optional[nx.Graph] = None,
    ):
        self.topology = topology
        self.size     = size
        self.weighted = weighted
        self.seed     = seed
        self.verbose  = verbose

        self.H = hardware_graph if hardware_graph is not None else build_hardware_graph(topology, size)
        n_hw   = self.H.number_of_nodes()

        _tmax = tmax if tmax is not None else max(200_000, int(7e7 * n_hw / 102_400))
        self.schedule = DWaveSchedule(
            tmax=_tmax, topology=topology,
            T0=T0, Thalf=Thalf, beta=beta, cool_every=cool_every, pa_end=pa_end,
        )
        self.gp = build_guiding_pattern(self.H, topology, size)

        if verbose:
            print(f"Hardware: {topology}({size}), {n_hw} nodes, {self.H.number_of_edges()} edges")
            print(f"Guiding pattern: {len(self.gp)} super vertices")
            print(self.schedule.summary())

    def run(self, I: nx.Graph, deadline: Optional[float] = None) -> PSSAResult:
        t0  = time.perf_counter()
        m_I = I.number_of_edges()

        phi_pssa, _ = pssa(
            I, self.H, self.gp, self.schedule,
            weighted=self.weighted, seed=self.seed, verbose=self.verbose,
            deadline=deadline,
        )
        phi_final = terminal_search(phi_pssa, I, self.H)
        inv_final = invert(phi_final)
        e_final   = eemb(phi_final, I, self.H, inv_final)
        success   = (e_final == m_I) and is_valid_embedding(phi_final, I, self.H)

        return PSSAResult(
            success=success, phi=phi_final, eemb=e_final, m_I=m_I,
            wall_time=time.perf_counter() - t0, topology=self.topology,
            size=self.size, n_hw=self.H.number_of_nodes(),
        )


def embed(
    I:              nx.Graph,
    topology:       str             = "chimera",
    size:           int             = 4,
    tmax:           Optional[int]   = None,
    weighted:       bool            = False,
    seed:           Optional[int]   = None,
    verbose:        bool            = False,
    hardware_graph: Optional[nx.Graph] = None,
) -> Tuple[bool, Phi]:
    """One-line embed interface."""
    algo   = ImprovedPSSA(topology=topology, size=size, tmax=tmax,
                          weighted=weighted, seed=seed, verbose=verbose,
                          hardware_graph=hardware_graph)
    result = algo.run(I)
    return result.success, result.phi


# ===========================================================================
# QEBench registration
# ===========================================================================

_logger = logging.getLogger(__name__)


from ember_qc.registry import EmbeddingAlgorithm, register_algorithm


class _PSSABase(EmbeddingAlgorithm):
    _weighted      = False
    _tmax_override = None
    supported_counters: List[str] = []

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, **kwargs) -> dict:
        seed     = kwargs.get('seed', None)
        timeout  = kwargs.get('timeout', 60.0)
        topology = self._detect_topology(target_graph)
        size     = self._detect_size(target_graph, topology)
        start    = time.time()
        deadline = start + timeout if timeout is not None else None
        try:
            algo = ImprovedPSSA(
                topology=topology,
                size=size,
                tmax=self._tmax_override,
                weighted=self._weighted,
                hardware_graph=target_graph,
                seed=seed,
                verbose=False,
            )
            result = algo.run(source_graph, deadline=deadline)

            elapsed = time.time() - start
            if not result.success:
                return {'embedding': {}, 'time': elapsed, 'status': 'FAILURE'}

            # Cast to plain Python ints — no numpy types in embedding
            embedding = {int(k): [int(v) for v in chain] for k, chain in result.phi.items()}
            return {'embedding': embedding, 'time': elapsed}

        except Exception as e:
            _logger.error("pssa error: %s", e)
            return {'embedding': {}, 'time': time.time() - start, 'status': 'FAILURE', 'error': str(e)}

    def _detect_topology(self, H: nx.Graph) -> str:
        data = H.graph
        if 'family' in data:
            fam = str(data['family']).lower()
            for name in ('chimera', 'pegasus', 'zephyr'):
                if name in fam:
                    return name
        avg_deg = sum(d for _, d in H.degree()) / max(H.number_of_nodes(), 1)
        if avg_deg < 8:
            return 'chimera'
        elif avg_deg < 18:
            return 'pegasus'
        return 'zephyr'

    def _detect_size(self, H: nx.Graph, topology: str) -> int:
        n = H.number_of_nodes()
        if topology == 'chimera':
            return max(1, round(math.sqrt(n / 8)))
        elif topology == 'pegasus':
            return max(2, round(math.sqrt(n / 24) + 1))
        elif topology == 'zephyr':
            m = (-1 + math.sqrt(1 + 2 * n)) / 4
            return max(1, round(m))
        return 4


@register_algorithm("pssa")
class PSSADefault(_PSSABase):
    """PSSA — path-annealing minor embedding, auto topology detection."""


@register_algorithm("pssa-weighted")
class PSSAWeighted(_PSSABase):
    """PSSA with degree-weighted shifts — best for regular/cubic graphs."""
    _weighted = True


@register_algorithm("pssa-fast")
class PSSAFast(_PSSABase):
    """PSSA with reduced tmax — faster, lower quality (tmax=50,000)."""
    _tmax_override = 50_000


@register_algorithm("pssa-thorough")
class PSSAThorough(_PSSABase):
    """PSSA with extended tmax — slower, higher quality (tmax=2,000,000)."""
    _tmax_override = 2_000_000
