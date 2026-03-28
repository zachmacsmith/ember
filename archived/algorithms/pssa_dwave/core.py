"""
pssa_dwave/core.py
==================
Core PSSA algorithm rewritten for D-Wave hardware graphs.

Replaces King's graph with Chimera / Pegasus / Zephyr.
Replaces Okuyama guiding pattern with busclique clique embedding.

Algorithm is otherwise identical to Sugie et al. (2020):
  - Swap and shift moves on path super vertices
  - Double-exponential annealing schedule
  - Terminal search post-processing

Hardware graph differences vs King's graph:
  Chimera  — bipartite unit cells, degree 6, sparse
  Pegasus  — degree 15, denser, native Pegasus couplers
  Zephyr   — degree 20, densest D-Wave topology to date
"""

import math
import random
from collections import defaultdict
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
                 chimera(m)  → m×m Chimera,  2*m*m*t nodes  (t=4 default)
                 pegasus(m)  → Pegasus P(m),  24*(m-1)^2 + 3*(m-1) nodes
                 zephyr(m)   → Zephyr Z(m),   ~4*m*(2*m+1) nodes

    Returns
    -------
    nx.Graph — the hardware graph with node integer labels
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
        # Relabel to consecutive integers for uniform node handling
        return nx.convert_node_labels_to_integers(G)
    except ImportError:
        raise ImportError(
            "dwave-networkx is required. Install with: pip install dwave-networkx"
        )


def hardware_node_count(topology: str, size: int) -> int:
    """Return expected number of nodes for a given topology and size."""
    if topology == "chimera":
        return 2 * size * size * 4      # default t=4
    elif topology == "pegasus":
        return 24 * (size - 1) ** 2 + 3 * (size - 1)
    elif topology == "zephyr":
        return 4 * size * (2 * size + 1)
    return 0


# ===========================================================================
# Guiding pattern — busclique clique embedding
# ===========================================================================

def build_guiding_pattern(H: nx.Graph, topology: str, size: int) -> Dict[int, List[NodeH]]:
    """
    Build the guiding pattern for D-Wave hardware using busclique.

    For D-Wave topologies the natural guiding structure is the largest
    clique embedding, found by minorminer.busclique.  This replaces the
    Okuyama K_{L+1} diagonal-stripe construction used for King's graph.

    busclique finds the largest K_N embeddable in the hardware and returns
    N chains, each a list of hardware nodes.  These N chains become the
    guiding super vertices that PSSA splits into |V(I)| initial paths.

    Falls back to a path-partition of all hardware nodes if busclique
    is unavailable.

    Returns
    -------
    Dict[int, List[NodeH]]  — {sv_index: [hw_node, ...] as connected path}
    """
    try:
        from minorminer.busclique import find_clique_embedding, busgraph_cache
        # Use busgraph_cache for speed on standard topologies
        try:
            import dwave_networkx as dnx
            if topology == "chimera":
                topo_graph = dnx.chimera_graph(size)
            elif topology == "pegasus":
                topo_graph = dnx.pegasus_graph(size)
            elif topology == "zephyr":
                topo_graph = dnx.zephyr_graph(size)
            else:
                topo_graph = H

            # Find largest clique — busclique returns {logical: [physical,...]}
            # We want as many guiding SVs as possible to initialise well
            n_nodes = H.number_of_nodes()
            # Binary search for largest embeddable clique
            lo, hi = 2, min(n_nodes, 300)
            best_emb = {}
            while lo <= hi:
                mid = (lo + hi) // 2
                emb = find_clique_embedding(mid, topo_graph)
                if emb:
                    best_emb = emb
                    lo = mid + 1
                else:
                    hi = mid - 1

            if best_emb:
                # Convert to integer-labelled hardware nodes
                node_map = {v: i for i, v in enumerate(H.nodes())}
                # If H was already relabelled, topo_graph nodes may differ
                # Safe approach: use the relabelled H directly
                gp: Dict[int, List[NodeH]] = {}
                for sv_idx, chain in best_emb.items():
                    # chain entries may be tuples (Pegasus/Zephyr) — map to ints
                    try:
                        int_chain = [int(u) for u in chain]
                    except (TypeError, ValueError):
                        int_chain = [node_map.get(u, u) for u in chain]
                    gp[sv_idx] = int_chain
                return gp

        except Exception:
            pass

        # Fallback: find clique on the integer-relabelled H
        from minorminer.busclique import find_clique_embedding
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

    # Hard fallback: partition hardware nodes into connected paths
    # (less efficient but always works — no busclique dependency)
    return _path_partition_guiding(H)


def _path_partition_guiding(H: nx.Graph) -> Dict[int, List[NodeH]]:
    """
    Fallback guiding pattern: greedily grow connected paths covering all H nodes.
    Used when busclique is unavailable.
    """
    visited: Set[NodeH] = set()
    paths: List[List[NodeH]] = []

    # BFS-based path growing
    for start in sorted(H.nodes()):
        if start in visited:
            continue
        path = [start]
        visited.add(start)
        frontier = start
        while True:
            nbrs = [v for v in H.neighbors(frontier)
                    if v not in visited]
            if not nbrs:
                break
            nxt = nbrs[0]
            path.append(nxt)
            visited.add(nxt)
            frontier = nxt
        paths.append(path)

    return {i: path for i, path in enumerate(paths)}


# ===========================================================================
# Initial placement — split guiding pattern into |V(I)| super vertices
# ===========================================================================

def initial_placement(I: nx.Graph, gp: Dict[int, List[NodeH]],
                       H: nx.Graph) -> Phi:
    """
    Split guiding pattern into |V(I)| path super vertices.

    The guiding pattern has K super vertices (one per clique node).
    We concatenate all guiding paths into one ordered list of hardware
    nodes and then cut it into |V(I)| contiguous blocks — each block
    is a path in H (contiguous within a guiding chain = connected).

    This matches the paper Section 3 / Fig. 2a approach, adapted so
    that the guiding chains are busclique paths rather than diagonal
    stripes.
    """
    nodes_I = sorted(I.nodes())
    n = len(nodes_I)

    # Collect all HW nodes in guiding order
    all_hw: List[NodeH] = []
    for gk in sorted(gp.keys()):
        all_hw.extend(gp[gk])

    # Deduplicate while preserving order (busclique chains are disjoint
    # but guard against edge cases)
    seen: Set[NodeH] = set()
    unique_hw: List[NodeH] = []
    for u in all_hw:
        if u not in seen:
            unique_hw.append(u)
            seen.add(u)

    # Add any hardware nodes not covered by guiding pattern
    for u in sorted(H.nodes()):
        if u not in seen:
            unique_hw.append(u)
            seen.add(u)

    total   = len(unique_hw)
    block   = total // n
    remainder = total % n

    phi: Phi = {}
    idx = 0
    for ni, v in enumerate(nodes_I):
        size     = block + (1 if ni < remainder else 0)
        phi[v]   = unique_hw[idx: idx + size]
        idx     += size

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
# D-Wave tuned schedule
# ===========================================================================

class DWaveSchedule:
    """
    Double-exponential annealing schedule tuned for D-Wave hardware.

    WHY THESE DIFFER FROM THE PAPER (King's graph params):
    -------------------------------------------------------
    The paper used T0=60.315, Thalf=33.435, beta=0.9999 for King's graph
    which has fixed degree d=8 everywhere.  D-Wave topologies have:

      Chimera  — degree 6, bipartite structure, sparse
      Pegasus  — degree 15, much denser connectivity
      Zephyr   — degree 20, densest D-Wave topology

    Higher hardware degree means:
      - Each super vertex has more neighbours to connect to
      - The energy landscape is smoother (easier to find embeddings)
      - You need LESS exploration at high temperature
      - Cooling can be faster (higher beta)

    Lower hardware degree (Chimera) means:
      - Fewer options per move → need MORE exploration
      - Higher T0 to escape local traps
      - Slower cooling (lower beta)

    Parameters per topology
    -----------------------
    Chimera  (d≈6):  T0=70, Thalf=40, beta=0.9998  — most exploration needed
    Pegasus  (d≈15): T0=55, Thalf=28, beta=0.9999  — close to paper defaults
    Zephyr   (d≈20): T0=45, Thalf=22, beta=0.99995 — least exploration needed

    tmax tuning
    -----------
    Paper used 7×10^7 for 102,400-node King's graph.
    D-Wave hardware is much smaller:
      chimera(16) = 2048 nodes,  pegasus(16) = 5627,  zephyr(4) = 160
    Scale tmax roughly proportionally: tmax ≈ 7e7 * (n_hw / 102400)
    Minimum 200,000 to ensure meaningful annealing.

    Shift/swap schedule
    -------------------
    ps (shift probability): 1.0 → 0.0  — same as paper, topology-independent
    pa (any-direction shift): topology-dependent end value
      Chimera: 0.095 → 0.40  (less any-direction — sparse graph, stay local)
      Pegasus: 0.095 → 0.487 (paper defaults)
      Zephyr:  0.095 → 0.55  (more any-direction — dense, explore more)
    """

    # Per-topology defaults — (T0, Thalf, beta, pa_end)
    TOPOLOGY_DEFAULTS = {
        "chimera": (70.0,  40.0,  0.9998,  0.40),
        "pegasus": (55.0,  28.0,  0.9999,  0.487),
        "zephyr":  (45.0,  22.0,  0.99995, 0.55),
    }

    def __init__(
        self,
        tmax:        int,
        topology:    str   = "chimera",
        T0:          Optional[float] = None,
        Thalf:       Optional[float] = None,
        beta:        Optional[float] = None,
        cool_every:  int   = 1000,
        ps0:         float = 1.0,
        ps_end:      float = 0.0,
        pa0:         float = 0.095,
        pa_end:      Optional[float] = None,
    ):
        defaults = self.TOPOLOGY_DEFAULTS.get(topology, self.TOPOLOGY_DEFAULTS["chimera"])
        self.tmax       = tmax
        self.T0         = T0    if T0    is not None else defaults[0]
        self.Thalf      = Thalf if Thalf is not None else defaults[1]
        self.beta       = beta  if beta  is not None else defaults[2]
        self.pa_end     = pa_end if pa_end is not None else defaults[3]
        self.cool_every = cool_every
        self.ps0        = ps0
        self.ps_end     = ps_end
        self.pa0        = pa0
        self.topology   = topology
        self._half      = tmax // 2

    @classmethod
    def auto(cls, topology: str, n_hw: int, **overrides) -> "DWaveSchedule":
        """
        Build a schedule with tmax auto-scaled to hardware size.

        tmax = max(200_000, int(7e7 * n_hw / 102_400))

        For context:
          chimera(4)  →  128 nodes  → tmax ~  87,000  → clamped to 200,000
          chimera(16) → 2048 nodes  → tmax ~ 1,400,000
          pegasus(16) → 5627 nodes  → tmax ~ 3,850,000
          zephyr(4)   →  336 nodes  → tmax ~  230,000
        """
        tmax = max(200_000, int(7e7 * n_hw / 102_400))
        return cls(tmax=tmax, topology=topology, **overrides)

    def temperature(self, t: int) -> float:
        if t < self._half:
            steps = t // self.cool_every
            return self.T0 * (self.beta ** steps)
        else:
            steps = (t - self._half) // self.cool_every
            return self.Thalf * (self.beta ** steps)

    def ps(self, t: int) -> float:
        return self.ps0 + (self.ps_end - self.ps0) * t / self.tmax

    def pa(self, t: int) -> float:
        return self.pa0 + (self.pa_end - self.pa0) * t / self.tmax

    def summary(self) -> str:
        return (
            f"DWaveSchedule({self.topology}): "
            f"T0={self.T0}, Thalf={self.Thalf}, "
            f"beta={self.beta}, tmax={self.tmax:,}, "
            f"pa_end={self.pa_end}"
        )


# ===========================================================================
# Degree-weighted shift direction  (Section 4.2, Eq. 7-8)
# ===========================================================================

def _shift_direction_prob(i, j, phi, deg, weighted):
    if not weighted:
        return 0.5
    dri = len(phi[i]) / max(deg[i], 1)
    drj = len(phi[j]) / max(deg[j], 1)
    denom = dri + drj
    return 0.5 if denom == 0 else dri / denom


# ===========================================================================
# Algorithm 1: PSSA — D-Wave edition
# ===========================================================================

def pssa(
    I:            nx.Graph,
    H:            nx.Graph,
    gp:           Dict[int, List[NodeH]],
    schedule:     DWaveSchedule,
    weighted:     bool          = False,
    seed:         Optional[int] = None,
    verbose:      bool          = False,
) -> Tuple[Phi, int]:
    """
    PSSA Algorithm 1 (Sugie et al. 2020) for D-Wave hardware.

    Identical logic to the King's graph version — only the hardware graph
    and guiding pattern differ.
    """
    if seed is not None:
        random.seed(seed)

    nodes_I  = sorted(I.nodes())
    edges_I  = list(I.edges())
    m_I      = len(edges_I)
    deg      = dict(I.degree())

    H_adj: Dict[NodeH, Set[NodeH]] = {u: set(H.neighbors(u)) for u in H.nodes()}

    # Guiding pattern lookup
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
        T  = schedule.temperature(t)
        ps = schedule.ps(t)
        pa = schedule.pa(t)

        if verbose and t % log_every == 0:
            pct = 100 * t // tmax
            print(f"  t={t:>9,} ({pct:3d}%)  T={T:6.3f}  Eemb={cur_e}/{m_I}")

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
                if allow_any:
                    candidate_jv.append((j, v))
                else:
                    if gp_lookup.get(u) == gp_lookup.get(v):
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
            edge = random.choice(edges_I)
            ie, k = edge

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
            phi     = phi_prop
            inv     = inv_prop
            cur_e   = prop_e

            if cur_e > eemb_best:
                phi_best  = {k: list(p) for k, p in phi.items()}
                eemb_best = cur_e

            if eemb_best == m_I:
                if verbose:
                    print(f"  ✓ Embedding found at t={t:,}")
                return phi_best, eemb_best

    return phi_best, eemb_best
