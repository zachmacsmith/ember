"""Graph generation registry.

Each graph type has a registered generator function.  Call ``generate_graphs()``
with a type name and per-parameter value lists; every combination is generated
and saved to ``generated_graphs/<type>/``.

Graph IDs are integers derived from a SHA-256 hash of the graph type,
parameters, and UTC generation timestamp — practically collision-free
across separate runs.

Generated JSON matches the format used by ``test_graphs/``:
    id, name, category, generated_at, num_nodes, num_edges, density,
    metadata, graph (node-link format)

Notes
-----
- ``random_planar``: greedy planarity-preserving construction — correct but
  not a uniform distribution over planar graphs.
- ``butterfly`` / ``wagner``: no NetworkX built-in; manually constructed.
- ``circulant`` offsets parameter: each value in the sweep list must be a
  tuple of integers, e.g. ``offsets=[(1, 2), (1, 3)]`` generates two graphs.
- ``hardware_native``: requires dwave-networkx; generates the full hardware
  topology graph at scale k (chimera_graph(k), pegasus_graph(k)).
- ``np_problem``: ER random graph tagged with an NP-hard problem label in
  metadata. The graph structure is the problem instance graph.
- ``named_special``: dispatches to a specific named-graph generator by the
  ``name`` parameter (petersen, tutte, house, etc.).

Usage
-----
    from generate_graphs import generate_graphs, generate_from_csv

    generate_graphs("complete", n=[4, 5, 6, 8, 10, 12, 15])
    generate_graphs("random_er", n=[10, 20, 50], p=[0.2, 0.5, 0.8], seed=[0, 1, 2])
    generate_graphs("circulant", n=[10, 12], offsets=[(1,), (1, 2), (1, 4)])
    generate_graphs("petersen")   # no parameters

    generate_from_csv("graph_library.csv")

CLI
---
    python generate_graphs.py complete --n 4 5 6 8 10
    python generate_graphs.py random_er --n 10 20 --p 0.2 0.5 --seed 0 1 2
    python generate_graphs.py circulant --n 10 12 --offsets 1 2   # one offset-set per call
    python generate_graphs.py --csv graph_library.csv
    python generate_graphs.py --list
"""

import argparse
import csv as _csv_module
import json
import random as _random
from datetime import datetime, timezone
from itertools import combinations, product
from pathlib import Path
from typing import Any

import networkx as nx

GENERATED_DIR = Path(__file__).parent / "library"


# =============================================================================
# ID ranges
# Starting ID for each graph type. IDs count up sequentially from these values.
# Ranges are sized with ~20% headroom above current instance counts.
# Reserved: 0–999 (future QUBO), 27100–29999 (future expansion).
# =============================================================================

ID_RANGES: dict[str, int] = {
    # Deterministic structured (1000–3849)
    "complete":              1000,
    "bipartite":             1100,
    "grid":                  1300,
    "cycle":                 1450,
    "path":                  1550,
    "star":                  1650,
    "wheel":                 1750,
    "turan":                 1850,
    "circulant":             2350,
    "generalized_petersen":  2950,
    "hypercube":             3550,
    "binary_tree":           3600,
    "tree":                  3650,
    "johnson":               3700,
    "kneser":                3800,
    # Random (3850–22449)
    "random_er":             3850,
    "barabasi_albert":       6250,
    "regular":               9000,
    "watts_strogatz":        11750,
    "sbm":                   21200,
    "lfr_benchmark":         22000,
    "random_planar":         22100,
    # Physics lattices (22450–23599)
    "triangular_lattice":    22450,
    "kagome":                22700,
    "honeycomb":             22900,
    "king_graph":            23150,
    "frustrated_square":     23250,
    "shastry_sutherland":    23350,
    "cubic_lattice":         23450,
    "bcc_lattice":           23550,
    # Application (23600–26149)
    "weak_strong_cluster":   23600,
    "planted_solution":      24150,
    "spin_glass":            26150,
    # Structured special (26900–27099)
    "hardware_native":       26900,
    "named_special":         27000,
    "sudoku":                27050,
    # NP problems — reserved, not yet implemented (27100+)
    "np_problem":            27100,
}


def save_id_ranges(path: Path | None = None) -> Path:
    """Write ID_RANGES to a JSON file for external reference.

    Defaults to ``generated_graphs/id_ranges.json``.
    """
    out = path or (GENERATED_DIR / "id_ranges.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(ID_RANGES, f, indent=2)
    return out


# =============================================================================
# Structured generators
# =============================================================================

def gen_complete(n: int):
    return nx.complete_graph(n), f"K{n}", {"type": "complete", "n": n}


def gen_bipartite(m: int, n: int):
    G = nx.complete_bipartite_graph(m, n)
    return G, f"bipartite_K{m}_{n}", {"type": "complete_bipartite", "m": m, "n": n}


def gen_grid(m: int, n: int, periodic: bool = False):
    G = nx.convert_node_labels_to_integers(nx.grid_2d_graph(m, n, periodic=periodic))
    suffix = "_periodic" if periodic else ""
    return G, f"grid_{m}x{n}{suffix}", {"type": "grid", "m": m, "n": n, "periodic": periodic}


def gen_cycle(n: int):
    return nx.cycle_graph(n), f"cycle_{n}", {"type": "cycle", "n": n}


def gen_path(n: int):
    return nx.path_graph(n), f"path_{n}", {"type": "path", "n": n}


def gen_star(n: int):
    """Star graph S_n: n leaves + 1 hub = n+1 total vertices."""
    return nx.star_graph(n), f"star_{n}", {"type": "star", "n": n}


def gen_wheel(n: int):
    """Wheel graph W_n: n rim vertices + 1 hub = n+1 total vertices."""
    G = nx.wheel_graph(n + 1)
    return G, f"wheel_{n}", {"type": "wheel", "n": n}


def gen_binary_tree(depth: int):
    """Balanced binary tree: branching factor 2, given depth."""
    G = nx.balanced_tree(2, depth)
    return G, f"binary_tree_d{depth}", {"type": "binary_tree", "depth": depth}


def gen_tree(r: int, h: int):
    """General balanced tree: branching factor r, depth h."""
    G = nx.balanced_tree(r, h)
    return G, f"tree_r{r}_d{h}", {"type": "balanced_tree", "branching": r, "depth": h}


def gen_hypercube(k: int):
    """Hypercube Q_k: 2^k nodes, each with degree k."""
    return nx.hypercube_graph(k), f"hypercube_Q{k}", {"type": "hypercube", "k": k}


def gen_turan(n: int, r: int):
    """Turan graph T(n,r): max edges on n vertices without K_{r+1}."""
    G = nx.turan_graph(n, r)
    return G, f"turan_n{n}_r{r}", {"type": "turan", "n": n, "r": r}


def gen_circulant(n: int, offsets: tuple):
    """Circulant graph C_n(S): node i connects to i+-s mod n for each s in offsets."""
    G = nx.circulant_graph(n, list(offsets))
    offsets_str = "-".join(str(s) for s in offsets)
    return G, f"circulant_n{n}_S{offsets_str}", {
        "type": "circulant", "n": n, "offsets": list(offsets),
    }


def gen_johnson(n: int, k: int):
    """Johnson graph J(n,k): vertices = k-subsets of {0..n-1}, edges = subsets sharing k-1 elements."""
    try:
        G = nx.convert_node_labels_to_integers(nx.johnson_graph(n, k))
    except AttributeError:
        subsets = list(combinations(range(n), k))
        G = nx.Graph()
        G.add_nodes_from(range(len(subsets)))
        for i, s in enumerate(subsets):
            s_set = set(s)
            for j in range(i + 1, len(subsets)):
                if len(s_set & set(subsets[j])) == k - 1:
                    G.add_edge(i, j)
    return G, f"johnson_n{n}_k{k}", {"type": "johnson", "n": n, "k": k}


def gen_kneser(n: int, k: int):
    """Kneser graph KG(n,k): vertices = k-subsets of {0..n-1}, edges = disjoint subsets."""
    try:
        G = nx.convert_node_labels_to_integers(nx.kneser_graph(n, k))
    except AttributeError:
        subsets = list(combinations(range(n), k))
        G = nx.Graph()
        G.add_nodes_from(range(len(subsets)))
        for i, s in enumerate(subsets):
            s_set = set(s)
            for j in range(i + 1, len(subsets)):
                if not (s_set & set(subsets[j])):
                    G.add_edge(i, j)
    return G, f"kneser_n{n}_k{k}", {"type": "kneser", "n": n, "k": k}


def gen_generalized_petersen(n: int, k: int):
    """Generalized Petersen graph GP(n,k): outer n-cycle + inner star polygon with step k.
    2n nodes: outer ring 0..n-1, inner ring n..2n-1."""
    G = nx.Graph()
    G.add_nodes_from(range(2 * n))
    for i in range(n):
        G.add_edge(i, (i + 1) % n)          # outer cycle
        G.add_edge(i, i + n)                 # spoke
        G.add_edge(i + n, (i + k) % n + n)  # inner star
    return G, f"gen_petersen_n{n}_k{k}", {"type": "generalized_petersen", "n": n, "k": k}


def gen_sudoku(n: int):
    """Sudoku graph of order n: nodes = cells of n^2 x n^2 grid, edges = cells sharing row/col/box.
    Standard Sudoku is n=3 (81 nodes, 9x9 grid)."""
    G = nx.sudoku_graph(n)
    return G, f"sudoku_n{n}", {"type": "sudoku", "n": n}


# =============================================================================
# Named generators (fixed structure, no parameters)
# =============================================================================

def gen_petersen():
    return nx.petersen_graph(), "petersen", {"type": "petersen"}


def gen_dodecahedral():
    return nx.dodecahedral_graph(), "dodecahedral", {"type": "dodecahedral"}


def gen_icosahedral():
    return nx.icosahedral_graph(), "icosahedral", {"type": "icosahedral"}


def gen_moebius_kantor():
    return nx.moebius_kantor_graph(), "moebius_kantor", {"type": "moebius_kantor"}


def gen_heawood():
    return nx.heawood_graph(), "heawood", {"type": "heawood"}


def gen_pappus():
    return nx.pappus_graph(), "pappus", {"type": "pappus"}


def gen_desargues():
    return nx.desargues_graph(), "desargues", {"type": "desargues"}


def gen_bull():
    return nx.bull_graph(), "bull", {"type": "bull"}


def gen_butterfly():
    """Butterfly graph: two triangles sharing a single vertex.
    5 nodes, 6 edges. No NetworkX built-in -- constructed manually."""
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2), (2, 0), (0, 3), (3, 4), (4, 0)])
    return G, "butterfly", {"type": "butterfly"}


def gen_wagner():
    """Wagner graph (W_8 / M_8): 8-cycle plus 4 long diagonals.
    8 nodes, 12 edges, 3-regular. No NetworkX built-in -- constructed manually."""
    G = nx.cycle_graph(8)
    G.add_edges_from([(0, 4), (1, 5), (2, 6), (3, 7)])
    return G, "wagner", {"type": "wagner"}


def gen_tutte():
    """Tutte graph: 46 nodes, 69 edges, 3-regular, smallest 3-connected
    non-Hamiltonian cubic graph."""
    return nx.tutte_graph(), "tutte", {"type": "tutte"}


def gen_house():
    """House graph: 5 nodes, 6 edges. Square with a triangle roof."""
    return nx.house_graph(), "house", {"type": "house"}


def gen_chvatal():
    """Chvatal graph: 12 nodes, 24 edges, 4-regular, smallest triangle-free
    4-chromatic graph."""
    return nx.chvatal_graph(), "chvatal", {"type": "chvatal"}


def gen_mcgee():
    """McGee graph: 24 nodes, 36 edges, 3-regular, girth 7.
    Constructed via LCF notation [12, 7, -7]^8."""
    G = nx.LCF_graph(24, [12, 7, -7], 8)
    return G, "mcgee", {"type": "mcgee"}


def gen_franklin():
    """Franklin graph: 12 nodes, 18 edges, 3-regular, bipartite, girth 4.
    Constructed via LCF notation [5, -5]^6."""
    G = nx.LCF_graph(12, [5, -5], 6)
    return G, "franklin", {"type": "franklin"}


# Dispatch table for named_special -- maps name string to zero-arg generator
_NAMED_SPECIAL_DISPATCH = {
    "petersen":       gen_petersen,
    "dodecahedral":   gen_dodecahedral,
    "icosahedral":    gen_icosahedral,
    "moebius_kantor": gen_moebius_kantor,
    "heawood":        gen_heawood,
    "pappus":         gen_pappus,
    "desargues":      gen_desargues,
    "bull":           gen_bull,
    "butterfly":      gen_butterfly,
    "wagner":         gen_wagner,
    "tutte":          gen_tutte,
    "house":          gen_house,
    "chvatal":        gen_chvatal,
    "mcgee":          gen_mcgee,
    "franklin":       gen_franklin,
}


def gen_named_special(name: str):
    """Dispatch to a zero-parameter named-graph generator by name string."""
    if name not in _NAMED_SPECIAL_DISPATCH:
        raise ValueError(
            f"Unknown named_special '{name}'. "
            f"Available: {sorted(_NAMED_SPECIAL_DISPATCH)}"
        )
    return _NAMED_SPECIAL_DISPATCH[name]()


# =============================================================================
# Random generators
# =============================================================================

def gen_random_er(n: int, p: float, seed: int = 0):
    """Erdos-Renyi G(n, p)."""
    G = nx.gnp_random_graph(n, p, seed=seed)
    return G, f"er_n{n}_p{p:.2f}_s{seed}", {
        "type": "erdos_renyi", "n": n, "p": p, "seed": seed,
    }


def gen_barabasi_albert(n: int, m: int, seed: int = 0):
    """Barabasi-Albert preferential attachment graph."""
    G = nx.barabasi_albert_graph(n, m, seed=seed)
    return G, f"ba_n{n}_m{m}_s{seed}", {
        "type": "barabasi_albert", "n": n, "m": m, "seed": seed,
    }


def gen_regular(n: int, d: int, seed: int = 0):
    """d-regular random graph. Requires n*d even and n > d."""
    if (n * d) % 2 != 0:
        raise ValueError(f"n*d must be even for a d-regular graph (got n={n}, d={d})")
    G = nx.random_regular_graph(d, n, seed=seed)
    return G, f"regular_n{n}_d{d}_s{seed}", {
        "type": "regular", "n": n, "d": d, "seed": seed,
    }


def gen_watts_strogatz(n: int, k: int, beta: float, seed: int = 0):
    """Watts-Strogatz small-world graph."""
    G = nx.watts_strogatz_graph(n, k, beta, seed=seed)
    return G, f"ws_n{n}_k{k}_b{beta:.2f}_s{seed}", {
        "type": "watts_strogatz", "n": n, "k": k, "beta": beta, "seed": seed,
    }


def gen_sbm(n: int, n_communities: int, p_in: float, p_out: float, seed: int = 0):
    """Stochastic block model. Divides n vertices into n_communities equal-ish blocks."""
    block_size, remainder = divmod(n, n_communities)
    sizes = [block_size + (1 if i < remainder else 0) for i in range(n_communities)]
    p = [[p_in if i == j else p_out for j in range(n_communities)]
         for i in range(n_communities)]
    G = nx.stochastic_block_model(sizes, p, seed=seed)
    G = nx.convert_node_labels_to_integers(G)
    # Strip 'block' node attrs and 'partition' graph attr (contain sets)
    for _, data in G.nodes(data=True):
        data.clear()
    G.graph.clear()
    return G, f"sbm_n{n}_c{n_communities}_pi{p_in:.2f}_po{p_out:.2f}_s{seed}", {
        "type": "sbm", "n": n, "n_communities": n_communities,
        "p_in": p_in, "p_out": p_out, "seed": seed,
    }


def gen_random_planar(n: int, seed: int = 0):
    """Random planar graph.

    Greedy construction: add edges in random order, rejecting any that break
    planarity.  The result is a valid planar graph but not drawn from a
    uniform distribution over planar graphs.
    """
    rng = _random.Random(seed)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng.shuffle(edges)
    for u, v in edges:
        G.add_edge(u, v)
        if not nx.check_planarity(G)[0]:
            G.remove_edge(u, v)
    return G, f"planar_n{n}_s{seed}", {
        "type": "random_planar", "n": n, "seed": seed,
    }


def gen_random_tree(n: int, seed: int = 0):
    """Uniformly random labeled tree on n nodes (Prufer sequence)."""
    G = nx.random_tree(n, seed=seed)
    return G, f"random_tree_n{n}_s{seed}", {
        "type": "random_tree", "n": n, "seed": seed,
    }


# =============================================================================
# Physics lattice generators
# =============================================================================

def _clean_lattice(G):
    """Convert to integer-labelled graph and strip all non-serializable attributes."""
    H = nx.convert_node_labels_to_integers(G)
    for _, data in H.nodes(data=True):
        data.clear()
    for _, _, data in H.edges(data=True):
        data.clear()
    H.graph.clear()
    return H


def gen_triangular_lattice(m: int, n: int, periodic: bool = False):
    """Triangular lattice: each interior node has degree 6.
    Requires m>=3, n>=5 when periodic=True."""
    G = _clean_lattice(nx.triangular_lattice_graph(m, n, periodic=periodic))
    suffix = "_periodic" if periodic else ""
    return G, f"triangular_{m}x{n}{suffix}", {
        "type": "triangular_lattice", "m": m, "n": n, "periodic": periodic,
    }


def gen_honeycomb(m: int, n: int, periodic: bool = False):
    """Honeycomb (hexagonal) lattice: each node has degree 3, bipartite structure.
    Periodic requires even n > 1 and m > 1."""
    G = _clean_lattice(nx.hexagonal_lattice_graph(m, n, periodic=periodic))
    suffix = "_periodic" if periodic else ""
    return G, f"honeycomb_{m}x{n}{suffix}", {
        "type": "honeycomb", "m": m, "n": n, "periodic": periodic,
    }


def gen_cubic_lattice(x: int, y: int, z: int, periodic: bool = False):
    """3D cubic lattice: interior nodes have degree 6.
    Used in D-Wave 3D spin glass simulations (King et al. 2023 Nature)."""
    G = nx.convert_node_labels_to_integers(
        nx.grid_graph(dim=[x, y, z], periodic=periodic)
    )
    suffix = "_periodic" if periodic else ""
    return G, f"cubic_{x}x{y}x{z}{suffix}", {
        "type": "cubic_lattice", "x": x, "y": y, "z": z, "periodic": periodic,
    }


def gen_king_graph(m: int, n: int, periodic: bool = False):
    """King graph: square grid plus all diagonal edges (degree 8 interior nodes).
    Equivalent to J1-J2 square lattice with both nearest and next-nearest neighbours."""
    base = nx.grid_2d_graph(m, n, periodic=periodic)
    for i in range(m):
        for j in range(n):
            for di, dj in [(1, 1), (1, -1)]:
                ni, nj = i + di, j + dj
                if periodic:
                    ni, nj = ni % m, nj % n
                if 0 <= ni < m and 0 <= nj < n:
                    base.add_edge((i, j), (ni, nj))
    G = nx.convert_node_labels_to_integers(base)
    suffix = "_periodic" if periodic else ""
    return G, f"king_{m}x{n}{suffix}", {
        "type": "king_graph", "m": m, "n": n, "periodic": periodic,
    }


def gen_frustrated_square(m: int, n: int, periodic: bool = False):
    """Frustrated square lattice (J1-J2 model): square grid plus next-nearest-neighbour diagonals.
    Structurally identical to king_graph; registered separately for physics labelling."""
    G, _, meta = gen_king_graph(m, n, periodic=periodic)
    suffix = "_periodic" if periodic else ""
    return G, f"frustrated_sq_{m}x{n}{suffix}", {
        "type": "frustrated_square", "m": m, "n": n, "periodic": periodic,
    }


def gen_kagome(m: int, n: int, periodic: bool = False):
    """Kagome lattice: line graph of the hexagonal (honeycomb) lattice.
    Corner-sharing triangles with coordination number 4.
    m, n are the honeycomb lattice dimensions (kagome nodes approx 3*m*n)."""
    hex_graph = nx.hexagonal_lattice_graph(m, n, periodic=periodic)
    G = _clean_lattice(nx.line_graph(hex_graph))
    suffix = "_periodic" if periodic else ""
    return G, f"kagome_{m}x{n}{suffix}", {
        "type": "kagome", "m": m, "n": n, "periodic": periodic,
    }


def gen_shastry_sutherland(m: int, n: int, periodic: bool = False):
    """Shastry-Sutherland lattice: square lattice with orthogonal dimer bonds.
    Each 2x2 plaquette has one diagonal, alternating orientation in a
    checkerboard pattern. m x n is the grid of unit cells."""
    G = nx.Graph()
    for i in range(m):
        for j in range(n):
            node = i * n + j
            # Right neighbour
            if j + 1 < n:
                G.add_edge(node, node + 1)
            elif periodic and n > 1:
                G.add_edge(node, i * n)
            # Down neighbour
            if i + 1 < m:
                G.add_edge(node, node + n)
            elif periodic and m > 1:
                G.add_edge(node, j)
            # Diagonal dimer: NE diagonal on even plaquettes, NW on odd
            if (i + j) % 2 == 0:
                ni, nj = i - 1, j + 1
                if periodic:
                    ni, nj = ni % m, nj % n
                if 0 <= ni < m and 0 <= nj < n:
                    G.add_edge(node, ni * n + nj)
    G = nx.convert_node_labels_to_integers(G)
    suffix = "_periodic" if periodic else ""
    return G, f"shastry_sutherland_{m}x{n}{suffix}", {
        "type": "shastry_sutherland", "m": m, "n": n, "periodic": periodic,
    }


def gen_bcc_lattice(m: int, periodic: bool = False):
    """3D Body-Centered Cubic (BCC) lattice: m x m x m unit cells.
    Bipartite graph: corner sublattice + body-centre sublattice.
    Only body-centre <-> corner edges (no intra-sublattice edges).
    Each body-centre connects to its 8 surrounding corners. Coordination number 8."""
    G = nx.Graph()
    def corner_id(i, j, k):
        return ("c", i % (m + 1), j % (m + 1), k % (m + 1))
    def center_id(i, j, k):
        return ("b", i % m, j % m, k % m)

    for i in range(m + 1):
        for j in range(m + 1):
            for k in range(m + 1):
                G.add_node(corner_id(i, j, k))
    for i in range(m):
        for j in range(m):
            for k in range(m):
                bc = center_id(i, j, k)
                G.add_node(bc)
                for di in (0, 1):
                    for dj in (0, 1):
                        for dk in (0, 1):
                            G.add_edge(bc, corner_id(i + di, j + dj, k + dk))
    G = nx.convert_node_labels_to_integers(G)
    suffix = "_periodic" if periodic else ""
    return G, f"bcc_{m}{suffix}", {
        "type": "bcc_lattice", "m": m, "periodic": periodic,
    }


# =============================================================================
# Network science generators
# =============================================================================

def gen_lfr_benchmark(n: int, tau1: float, tau2: float, mu: float,
                      average_degree: int, seed: int = 0):
    """LFR benchmark graph: scale-free degree distribution + community structure.
    tau1 > 1 (degree power law), tau2 > 1 (community size power law),
    0 < mu < 1 (fraction of inter-community edges)."""
    G = nx.LFR_benchmark_graph(
        n, tau1, tau2, mu,
        average_degree=average_degree,
        min_community=max(3, min(20, n // 10)),
        max_community=max(n // 3, 10),
        seed=seed,
    )
    G = nx.convert_node_labels_to_integers(G)
    G.remove_edges_from(nx.selfloop_edges(G))
    for _, data in G.nodes(data=True):
        data.clear()
    return G, f"lfr_n{n}_t1{tau1:.1f}_t2{tau2:.1f}_mu{mu:.2f}_k{average_degree}_s{seed}", {
        "type": "lfr_benchmark", "n": n, "tau1": tau1, "tau2": tau2,
        "mu": mu, "average_degree": average_degree, "seed": seed,
    }


def gen_random_geometric(n: int, radius: float, dim: int = 2, seed: int = 0):
    """Random geometric graph: nodes placed uniformly in [0,1]^dim,
    edges between nodes within Euclidean distance `radius`."""
    G = nx.random_geometric_graph(n, radius, dim=dim, seed=seed)
    G = nx.convert_node_labels_to_integers(G)
    return G, f"rgg_n{n}_r{radius:.2f}_d{dim}_s{seed}", {
        "type": "random_geometric", "n": n, "radius": radius, "dim": dim, "seed": seed,
    }


# =============================================================================
# Application / physics generators
# =============================================================================

def gen_spin_glass(n: int, edge_density: float, weight_distribution: str = "bimodal",
                   seed: int = 0):
    """Weighted random spin glass instance.
    edge_density=1.0 gives complete K_n; <1.0 gives ER sparse instance.
    weight_distribution: 'bimodal' (+-1), 'gaussian', or 'uniform' ([-1,1]).
    Weights stored as edge attribute 'weight'. Graph structure = QUBO interaction graph."""
    rng = _random.Random(seed)
    if edge_density >= 1.0:
        G = nx.complete_graph(n)
    else:
        G = nx.gnp_random_graph(n, edge_density, seed=seed)
    weight_fns = {
        "bimodal":  lambda: rng.choice([-1.0, 1.0]),
        "gaussian": lambda: rng.gauss(0.0, 1.0),
        "uniform":  lambda: rng.uniform(-1.0, 1.0),
    }
    if weight_distribution not in weight_fns:
        raise ValueError(f"weight_distribution must be one of {list(weight_fns)}")
    wfn = weight_fns[weight_distribution]
    for u, v in G.edges():
        G[u][v]["weight"] = wfn()
    return G, f"spin_glass_n{n}_d{edge_density:.2f}_{weight_distribution}_s{seed}", {
        "type": "spin_glass", "n": n, "edge_density": edge_density,
        "weight_distribution": weight_distribution, "seed": seed,
    }


def gen_weak_strong_cluster(n_clusters: int, cluster_size: int,
                             inter_edges_per_cluster: int, seed: int = 0):
    """Weak-strong cluster graph: dense intra-cluster + sparse inter-cluster edges.
    Each cluster is a complete subgraph; inter_edges_per_cluster random edges connect
    each cluster to other clusters (D-Wave benchmark from Denchev et al. 2016)."""
    rng = _random.Random(seed)
    G = nx.Graph()
    total = n_clusters * cluster_size
    G.add_nodes_from(range(total))
    for c in range(n_clusters):
        base = c * cluster_size
        for i in range(cluster_size):
            for j in range(i + 1, cluster_size):
                G.add_edge(base + i, base + j)
    for c in range(n_clusters):
        other_clusters = [o for o in range(n_clusters) if o != c]
        for _ in range(inter_edges_per_cluster):
            oc = rng.choice(other_clusters)
            u = c  * cluster_size + rng.randrange(cluster_size)
            v = oc * cluster_size + rng.randrange(cluster_size)
            G.add_edge(u, v)
    return G, f"wsc_c{n_clusters}_sz{cluster_size}_ie{inter_edges_per_cluster}_s{seed}", {
        "type": "weak_strong_cluster", "n_clusters": n_clusters,
        "cluster_size": cluster_size, "inter_edges_per_cluster": inter_edges_per_cluster,
        "seed": seed,
    }


def gen_power_grid(n_buses: int, topology_type: str = "radial", seed: int = 0):
    """Power grid / infrastructure graph.
    topology_type='radial': random spanning tree (no cycles, degree 2-3 most nodes).
    topology_type='meshed': spanning tree plus added edges creating short cycles."""
    rng = _random.Random(seed)
    G = nx.random_tree(n_buses, seed=seed)
    if topology_type == "meshed":
        nodes = list(G.nodes())
        n_extra = max(1, n_buses // 5)
        for _ in range(n_extra):
            u, v = rng.sample(nodes, 2)
            if not G.has_edge(u, v):
                G.add_edge(u, v)
    elif topology_type != "radial":
        raise ValueError("topology_type must be 'radial' or 'meshed'")
    return G, f"power_grid_n{n_buses}_{topology_type}_s{seed}", {
        "type": "power_grid", "n_buses": n_buses,
        "topology_type": topology_type, "seed": seed,
    }


def gen_planted_solution(n: int, topology: str = "chimera", seed: int = 0):
    """Planted solution graph: random n-node induced subgraph of a hardware topology.

    Selects n random nodes from the full hardware graph and returns the induced
    subgraph. By construction the result is always embeddable on that topology --
    the planted solution (known optimal embedding) is the identity map.

    topology: 'chimera' (D-Wave 2000Q), 'pegasus' (Advantage), 'zephyr' (Advantage2).
    Requires dwave-networkx.
    """
    import dwave_networkx as dnx

    rng = _random.Random(seed)
    if topology == "chimera":
        m = max(1, int((n / 8) ** 0.5) + 2)
        hw = dnx.chimera_graph(m)
    elif topology == "pegasus":
        m = max(2, int((n / 24) ** 0.5) + 2)
        hw = dnx.pegasus_graph(m)
    elif topology == "zephyr":
        m = max(2, int((n / 48) ** 0.5) + 2)
        hw = dnx.zephyr_graph(m)
    else:
        raise ValueError(f"topology must be 'chimera', 'pegasus', or 'zephyr', got '{topology}'")

    hw = nx.convert_node_labels_to_integers(hw)
    if hw.number_of_nodes() < n:
        raise ValueError(
            f"Hardware graph {topology} (m={m}) has {hw.number_of_nodes()} nodes, "
            f"need {n}. Increase topology size."
        )
    chosen = sorted(rng.sample(list(hw.nodes()), n))
    G = nx.convert_node_labels_to_integers(hw.subgraph(chosen).copy())
    return G, f"planted_{topology}_n{n}_s{seed}", {
        "type": "planted_solution", "n": n, "topology": topology, "seed": seed,
    }


def gen_hardware_native(topology: str, k: int):
    """Full hardware topology graph at scale k.

    Generates the complete hardware graph for the given topology and scale
    parameter k, as used by D-Wave quantum processors:
      - 'chimera': chimera_graph(k)  k=1..16 (C16 ceiling: 2,048 nodes, 6,016 edges)
      - 'pegasus': pegasus_graph(k)  k=1..16 (P16 ceiling: 5,640 nodes, 40,484 edges)
      - 'zephyr':  zephyr_graph(k)   k=1..12 (Z12 ceiling: 4,800 nodes, 45,864 edges)

    Only generate within the real hardware ceiling so every instance is a
    genuine subgraph of the corresponding physical topology — embeddable by
    the identity map.

    Requires dwave-networkx.
    """
    import dwave_networkx as dnx

    HARDWARE_CEILINGS = {
        "chimera": {"max_k": 16, "nodes": 2048,  "edges": 6016},
        "pegasus": {"max_k": 16, "min_k": 2, "nodes": 5640,  "edges": 40484},  # k=1 degenerate
        "zephyr":  {"max_k": 12, "nodes": 4800,  "edges": 45864},
    }
    if topology not in HARDWARE_CEILINGS:
        raise ValueError(
            f"topology must be one of {list(HARDWARE_CEILINGS)}, got '{topology}'"
        )
    max_k = HARDWARE_CEILINGS[topology]["max_k"]
    if k > max_k:
        raise ValueError(
            f"{topology} k={k} exceeds hardware ceiling k={max_k}"
        )

    if topology == "chimera":
        hw = dnx.chimera_graph(k)
    elif topology == "pegasus":
        hw = dnx.pegasus_graph(k)
    elif topology == "zephyr":
        hw = dnx.zephyr_graph(k)

    G = nx.convert_node_labels_to_integers(hw)
    for _, data in G.nodes(data=True):
        data.clear()
    for _, _, data in G.edges(data=True):
        data.clear()
    G.graph.clear()
    return G, f"hardware_{topology}_k{k}", {
        "type": "hardware_native", "topology": topology, "k": k,
    }


def gen_np_problem(problem: str, n: int, seed: int = 0):
    """Random ER graph instance for a given NP-hard combinatorial problem.

    The underlying graph is G(n, 0.5) -- a standard random instance for
    benchmarking. The ``problem`` label is stored in metadata only; no
    QUBO encoding is performed here.

    problem: one of 'max_cut', 'graph_coloring_k3', 'graph_coloring_k4',
             'max_clique', 'vertex_cover', 'mis'.
    """
    VALID = {"max_cut", "graph_coloring_k3", "graph_coloring_k4",
             "max_clique", "vertex_cover", "mis"}
    if problem not in VALID:
        raise ValueError(f"problem must be one of {sorted(VALID)}, got '{problem}'")
    G = nx.gnp_random_graph(n, 0.5, seed=seed)
    return G, f"np_{problem}_n{n}_s{seed}", {
        "type": "np_problem", "problem": problem, "n": n, "seed": seed,
    }


# =============================================================================
# QUBO interaction graph generators
# =============================================================================

def gen_mis_qubo(n: int, p: float, seed: int = 0):
    """MIS / Vertex Cover QUBO interaction graph.
    One variable per vertex; two variables coupled iff the corresponding vertices
    are adjacent (they cannot both be in an independent set).
    The QUBO interaction graph IS the underlying ER graph."""
    G = nx.gnp_random_graph(n, p, seed=seed)
    return G, f"mis_qubo_n{n}_p{p:.2f}_s{seed}", {
        "type": "mis_qubo", "n": n, "p": p, "seed": seed,
    }


def gen_matching_qubo(n: int, p: float, seed: int = 0):
    """Minimal Maximal Matching QUBO interaction graph.
    One variable per edge of the underlying ER graph; two variables are coupled
    iff their corresponding edges share a vertex (line graph construction)."""
    underlying = nx.gnp_random_graph(n, p, seed=seed)
    G = nx.convert_node_labels_to_integers(nx.line_graph(underlying))
    return G, f"matching_qubo_n{n}_p{p:.2f}_s{seed}", {
        "type": "matching_qubo", "n": n, "p": p, "seed": seed,
    }


def gen_portfolio_qubo(n_assets: int, covariance_structure: str = "random", seed: int = 0):
    """Portfolio optimisation QUBO interaction graph.
    One variable per asset; edges connect assets with non-zero covariance.
    covariance_structure:
      'random' -- dense near-complete graph (all assets correlated)
      'block'  -- block-diagonal (assets clustered into sqrt(n_assets) groups)
      'sparse' -- sparse ER-like graph (p approx 0.3)
    """
    rng = _random.Random(seed)
    G = nx.Graph()
    G.add_nodes_from(range(n_assets))
    if covariance_structure == "random":
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                G.add_edge(i, j)
    elif covariance_structure == "block":
        n_blocks = max(2, round(n_assets ** 0.5))
        block_size, remainder = divmod(n_assets, n_blocks)
        idx = 0
        for b in range(n_blocks):
            size = block_size + (1 if b < remainder else 0)
            block = list(range(idx, idx + size))
            for i in block:
                for j in block:
                    if i < j:
                        G.add_edge(i, j)
            idx += size
    elif covariance_structure == "sparse":
        p_sparse = 0.3
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                if rng.random() < p_sparse:
                    G.add_edge(i, j)
    else:
        raise ValueError("covariance_structure must be 'random', 'block', or 'sparse'")
    return G, f"portfolio_qubo_n{n_assets}_{covariance_structure}_s{seed}", {
        "type": "portfolio_qubo", "n_assets": n_assets,
        "covariance_structure": covariance_structure, "seed": seed,
    }


# =============================================================================
# Registry
# Maps type_name -> (generator_fn, [ordered_param_names])
# =============================================================================

REGISTRY: dict[str, tuple] = {
    # Structured
    "complete":            (gen_complete,            ["n"]),
    "bipartite":           (gen_bipartite,           ["m", "n"]),
    "grid":                (gen_grid,                ["m", "n", "periodic"]),
    "cycle":               (gen_cycle,               ["n"]),
    "path":                (gen_path,                ["n"]),
    "star":                (gen_star,                ["n"]),
    "wheel":               (gen_wheel,               ["n"]),
    "binary_tree":         (gen_binary_tree,         ["depth"]),
    "tree":                (gen_tree,                ["r", "h"]),
    "hypercube":           (gen_hypercube,           ["k"]),
    "turan":               (gen_turan,               ["n", "r"]),
    "circulant":           (gen_circulant,           ["n", "offsets"]),
    "johnson":             (gen_johnson,             ["n", "k"]),
    "kneser":              (gen_kneser,              ["n", "k"]),
    "generalized_petersen":(gen_generalized_petersen,["n", "k"]),
    "sudoku":              (gen_sudoku,              ["n"]),
    # Named (no parameters)
    "petersen":       (gen_petersen,       []),
    "dodecahedral":   (gen_dodecahedral,   []),
    "icosahedral":    (gen_icosahedral,    []),
    "moebius_kantor": (gen_moebius_kantor, []),
    "heawood":        (gen_heawood,        []),
    "pappus":         (gen_pappus,         []),
    "desargues":      (gen_desargues,      []),
    "bull":           (gen_bull,           []),
    "butterfly":      (gen_butterfly,      []),
    "wagner":         (gen_wagner,         []),
    "tutte":          (gen_tutte,          []),
    "house":          (gen_house,          []),
    "chvatal":        (gen_chvatal,        []),
    "mcgee":          (gen_mcgee,          []),
    "franklin":       (gen_franklin,       []),
    # Named dispatch (parameterised by name string)
    "named_special":  (gen_named_special,  ["name"]),
    # Random
    "random_er":       (gen_random_er,       ["n", "p", "seed"]),
    "barabasi_albert": (gen_barabasi_albert, ["n", "m", "seed"]),
    "regular":         (gen_regular,         ["n", "d", "seed"]),
    "watts_strogatz":  (gen_watts_strogatz,  ["n", "k", "beta", "seed"]),
    "sbm":             (gen_sbm,             ["n", "n_communities", "p_in", "p_out", "seed"]),
    "random_planar":   (gen_random_planar,   ["n", "seed"]),
    "random_tree":     (gen_random_tree,     ["n", "seed"]),
    # Physics lattice
    "triangular_lattice": (gen_triangular_lattice, ["m", "n", "periodic"]),
    "honeycomb":          (gen_honeycomb,          ["m", "n", "periodic"]),
    "cubic_lattice":      (gen_cubic_lattice,      ["x", "y", "z", "periodic"]),
    "king_graph":         (gen_king_graph,         ["m", "n", "periodic"]),
    "frustrated_square":  (gen_frustrated_square,  ["m", "n", "periodic"]),
    "kagome":             (gen_kagome,             ["m", "n", "periodic"]),
    "shastry_sutherland": (gen_shastry_sutherland, ["m", "n", "periodic"]),
    "bcc_lattice":        (gen_bcc_lattice,        ["m", "periodic"]),
    # Network science
    "lfr_benchmark":    (gen_lfr_benchmark,    ["n", "tau1", "tau2", "mu", "average_degree", "seed"]),
    "random_geometric": (gen_random_geometric, ["n", "radius", "dim", "seed"]),
    # Application
    "spin_glass":         (gen_spin_glass,         ["n", "edge_density", "weight_distribution", "seed"]),
    "weak_strong_cluster":(gen_weak_strong_cluster,["n_clusters", "cluster_size", "inter_edges_per_cluster", "seed"]),
    "power_grid":         (gen_power_grid,         ["n_buses", "topology_type", "seed"]),
    "planted_solution":   (gen_planted_solution,   ["n", "topology", "seed"]),
    # Hardware topology
    "hardware_native":    (gen_hardware_native,    ["topology", "k"]),
    # NP problem instances
    "np_problem":         (gen_np_problem,         ["problem", "n", "seed"]),
    # QUBO interaction graphs
    "mis_qubo":       (gen_mis_qubo,       ["n", "p", "seed"]),
    "matching_qubo":  (gen_matching_qubo,  ["n", "p", "seed"]),
    "portfolio_qubo": (gen_portfolio_qubo, ["n_assets", "covariance_structure", "seed"]),
}


# =============================================================================
# Save
# =============================================================================

def _save(G: nx.Graph, graph_id: int, name: str, graph_type: str,
          metadata: dict, generated_at: str) -> Path:
    out_dir = GENERATED_DIR / graph_type
    out_dir.mkdir(parents=True, exist_ok=True)

    n = G.number_of_nodes()
    data = {
        "id":           graph_id,
        "name":         name,
        "category":     graph_type,
        "generated_at": generated_at,
        "num_nodes":    n,
        "num_edges":    G.number_of_edges(),
        "density":      round(2 * G.number_of_edges() / (n * (n - 1)) if n > 1 else 0, 6),
        "metadata":     metadata,
        "graph":        nx.node_link_data(G),
    }

    filepath = out_dir / f"{graph_id}_{name}.json"
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


# =============================================================================
# Main generation call
# =============================================================================

def generate_graphs(graph_type: str, start_id: int | None = None,
                    **params: list[Any]) -> list[Path]:
    """Generate graphs for every combination of the supplied parameter values.

    IDs are assigned sequentially starting from ``start_id``.  If ``start_id``
    is omitted, the value from ``ID_RANGES`` is used.  IDs increment by 1 per
    generated graph in the order combinations are produced.

    Args:
        graph_type: Key from REGISTRY.
        start_id:   First ID to assign. Defaults to ``ID_RANGES[graph_type]``.
        **params:   Each keyword maps a parameter name to a list of values to
                    sweep.  The cartesian product of all lists is generated.
                    For fixed-signature types (e.g. ``petersen``) pass nothing.
                    For ``circulant``, each ``offsets`` value must be a tuple,
                    e.g. ``offsets=[(1, 2), (1, 3)]``.

    Returns:
        List of paths to saved JSON files.
    """
    if graph_type not in REGISTRY:
        raise ValueError(
            f"Unknown graph type '{graph_type}'. Available: {list(REGISTRY)}"
        )

    if start_id is None:
        if graph_type not in ID_RANGES:
            raise ValueError(
                f"No starting ID registered for '{graph_type}'. "
                f"Pass start_id=<int> explicitly or add an entry to ID_RANGES."
            )
        start_id = ID_RANGES[graph_type]

    gen_fn, param_names = REGISTRY[graph_type]

    for k in params:
        if k not in param_names:
            raise ValueError(
                f"Unknown parameter '{k}' for '{graph_type}'. Expected: {param_names}"
            )

    if not param_names:
        combinations_list = [{}]
    else:
        value_lists = [params.get(k, [None]) for k in param_names]
        combinations_list = [
            dict(zip(param_names, combo))
            for combo in product(*value_lists)
        ]

    current_id = start_id
    saved = []
    for combo in combinations_list:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        graph_id = current_id
        current_id += 1
        kwargs = {k: v for k, v in combo.items() if v is not None}
        G, name, metadata = gen_fn(**kwargs)
        path = _save(G, graph_id, name, graph_type, metadata, generated_at)
        saved.append(path)
        print(f"  [{graph_id}] {path.name}")

    return saved


# =============================================================================
# CSV ingestion
# =============================================================================

def _parse_params(raw: str) -> dict[str, str]:
    """Parse a semicolon-delimited ``key=value`` param string into a raw string dict.

    Example: ``"n=10;p=0.5;type=sparse"`` -> ``{"n": "10", "p": "0.5", "type": "sparse"}``
    Empty string returns ``{}``.
    """
    if not raw or not raw.strip():
        return {}
    result = {}
    for token in raw.split(";"):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"Malformed param token (no '='): '{token}'")
        k, _, v = token.partition("=")
        result[k.strip()] = v.strip()
    return result


def _coerce_value(v: str) -> Any:
    """Coerce a string value to int, float, bool, or leave as str."""
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def _translate_row(csv_type: str, raw_params: dict[str, str], seed: int
                   ) -> tuple[str, dict[str, Any]]:
    """Translate a CSV row into a (registry_type, kwargs) pair ready for a generator call.

    Handles all type renames and parameter renames/reshapes between the CSV
    spec produced by generate_graph_library_csv.py and the generator registry.

    Args:
        csv_type:   The ``graph_type`` field from the CSV row.
        raw_params: Key/value strings parsed from the CSV ``params`` field.
        seed:       The integer seed from the CSV ``seed`` field.

    Returns:
        (registry_type, kwargs) where kwargs values are fully coerced and renamed.

    Raises:
        ValueError: For unknown types or structurally invalid param combos.
    """
    p = {k: _coerce_value(v) for k, v in raw_params.items()}

    # ------------------------------------------------------------------
    # complete_bipartite -> bipartite
    # ------------------------------------------------------------------
    if csv_type == "complete_bipartite":
        return "bipartite", {"m": p["m"], "n": p["n"]}

    # ------------------------------------------------------------------
    # erdos_renyi -> random_er
    # ------------------------------------------------------------------
    if csv_type == "erdos_renyi":
        return "random_er", {"n": p["n"], "p": p["p"], "seed": seed}

    # ------------------------------------------------------------------
    # balanced_tree: param rename d -> h
    # ------------------------------------------------------------------
    if csv_type == "balanced_tree":
        return "tree", {"r": p["r"], "h": p["d"]}

    # ------------------------------------------------------------------
    # binary_tree: param rename d -> depth
    # ------------------------------------------------------------------
    if csv_type == "binary_tree":
        return "binary_tree", {"depth": p["d"]}

    # ------------------------------------------------------------------
    # sbm: param rename k -> n_communities; inject seed
    # ------------------------------------------------------------------
    if csv_type == "sbm":
        return "sbm", {
            "n": p["n"], "n_communities": p["k"],
            "p_in": p["p_in"], "p_out": p["p_out"], "seed": seed,
        }

    # ------------------------------------------------------------------
    # circulant: offsets stored as dash-separated string "1-2-3" -> tuple
    # ------------------------------------------------------------------
    if csv_type == "circulant":
        offsets = tuple(int(x) for x in str(p["offsets"]).split("-"))
        return "circulant", {"n": p["n"], "offsets": offsets}

    # ------------------------------------------------------------------
    # king_graph / frustrated_square: CSV has only m (square grid)
    # Registry expects m and n; set n=m.
    # ------------------------------------------------------------------
    if csv_type in ("king_graph", "frustrated_square"):
        kwargs: dict[str, Any] = {"m": p["m"], "n": p["m"]}
        if "periodic" in p:
            kwargs["periodic"] = p["periodic"]
        return csv_type, kwargs

    # ------------------------------------------------------------------
    # shastry_sutherland: CSV has only m (square unit-cell grid)
    # Registry expects m and n; set n=m.
    # ------------------------------------------------------------------
    if csv_type == "shastry_sutherland":
        kwargs = {"m": p["m"], "n": p["m"]}
        if "periodic" in p:
            kwargs["periodic"] = p["periodic"]
        return csv_type, kwargs

    # ------------------------------------------------------------------
    # cubic_lattice: CSV uses m/n/p -> registry uses x/y/z
    # ------------------------------------------------------------------
    if csv_type == "cubic_lattice":
        kwargs = {"x": p["m"], "y": p["n"], "z": p["p"]}
        if "periodic" in p:
            kwargs["periodic"] = p["periodic"]
        return "cubic_lattice", kwargs

    # ------------------------------------------------------------------
    # spin_glass: param renames p -> edge_density, type -> weight_distribution
    # "full" means edge_density=1.0 (complete SK model)
    # "sparse" uses the explicit p value
    # ------------------------------------------------------------------
    if csv_type == "spin_glass":
        sg_type = p.get("type", "bimodal")
        if sg_type == "full":
            edge_density = 1.0
            weight_dist = "bimodal"
        else:
            edge_density = float(p.get("p", 0.5))
            weight_dist = "bimodal"
        return "spin_glass", {
            "n": p["n"], "edge_density": edge_density,
            "weight_distribution": weight_dist, "seed": seed,
        }

    # ------------------------------------------------------------------
    # sudoku: param rename size -> n
    # ------------------------------------------------------------------
    if csv_type == "sudoku":
        return "sudoku", {"n": p["size"]}

    # ------------------------------------------------------------------
    # planted_solution: CSV now has topology in params (one row per topology).
    # k and p (planted clique size / background density) are problem metadata,
    # not graph-structure params -- forwarded via _extra_metadata so they land
    # in the saved JSON but are not passed to the generator.
    # ------------------------------------------------------------------
    if csv_type == "planted_solution":
        return "planted_solution", {
            "n": p["n"],
            "topology": p["topology"],
            "seed": seed,
            "_extra_metadata": {"k": p.get("k"), "p": p.get("p")},
        }

    # ------------------------------------------------------------------
    # named_special: single name param, dispatched via gen_named_special
    # ------------------------------------------------------------------
    if csv_type == "named_special":
        return "named_special", {"name": p["name"]}

    # ------------------------------------------------------------------
    # hardware_native: topology + k, no seed
    # ------------------------------------------------------------------
    if csv_type == "hardware_native":
        return "hardware_native", {"topology": p["topology"], "k": p["k"]}

    # ------------------------------------------------------------------
    # np_problems (CSV plural) -> np_problem (registry singular); inject seed
    # ------------------------------------------------------------------
    if csv_type == "np_problems":
        return "np_problem", {"problem": p["problem"], "n": p["n"], "seed": seed}

    # ------------------------------------------------------------------
    # lfr_benchmark: CSV omits average_degree; default to 5
    # ------------------------------------------------------------------
    if csv_type == "lfr_benchmark":
        return "lfr_benchmark", {
            "n": p["n"], "tau1": p["tau1"], "tau2": p["tau2"], "mu": p["mu"],
            "average_degree": p.get("average_degree", 5), "seed": seed,
        }

    # ------------------------------------------------------------------
    # Pass-through: type name matches registry directly.
    # Inject seed into kwargs if the generator accepts it.
    # ------------------------------------------------------------------
    if csv_type not in REGISTRY:
        raise ValueError(
            f"CSV type '{csv_type}' has no registry entry and no translation rule. "
            f"Add a translation in _translate_row() or register a generator."
        )

    _, param_names = REGISTRY[csv_type]
    kwargs = dict(p)
    if "seed" in param_names:
        kwargs["seed"] = seed
    return csv_type, kwargs


def generate_from_csv(
    csv_path: str | Path,
    *,
    skip_errors: bool = False,
    topologies_filter: list[str] | None = None,
) -> list[Path]:
    """Generate all graphs specified in a CSV library file.

    The CSV must have columns: ``graph_type``, ``params``, ``seed``, ``topologies``.
    The ``params`` field uses semicolon-delimited ``key=value`` pairs.
    The ``topologies`` field is stored in each graph's metadata but does not
    affect generation logic.

    Args:
        csv_path:          Path to the CSV file.
        skip_errors:       If True, log failures and continue; otherwise re-raise.
        topologies_filter: Optional list of topology names (e.g. ``["chimera"]``).
                           Only rows whose ``topologies`` field contains at least
                           one of the listed names will be generated.

    Returns:
        List of paths to all successfully saved JSON files.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    saved: list[Path] = []
    errors: list[tuple[int, str, Exception]] = []

    # Per-type sequential ID counters, seeded from ID_RANGES.
    # Each type counts up independently; counter state persists across the run
    # so that multiple CSV rows of the same type get consecutive IDs.
    id_counters: dict[str, int] = dict(ID_RANGES)

    with csv_path.open(newline="") as fh:
        reader = _csv_module.DictReader(fh)
        rows = list(reader)

    print(f"Generating {len(rows)} graphs from {csv_path.name}...\n")

    for line_num, row in enumerate(rows, start=2):  # start=2: row 1 is header
        csv_type   = row["graph_type"].strip()
        params_raw = row["params"].strip()
        seed_raw   = row["seed"].strip()
        topologies = row["topologies"].strip()

        # Optional topology filter
        if topologies_filter:
            row_tops = {t.strip() for t in topologies.split("|")}
            if not row_tops.intersection(topologies_filter):
                continue

        try:
            seed = int(seed_raw)
            raw_params = _parse_params(params_raw)
            registry_type, kwargs = _translate_row(csv_type, raw_params, seed)

            gen_fn, _ = REGISTRY[registry_type]
            generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            # Strip internal keys before passing to generator; keep for metadata
            extra_metadata = kwargs.pop("_extra_metadata", {})
            if registry_type not in id_counters:
                raise RuntimeError(
                    f"No ID range registered for '{registry_type}'. "
                    f"Add an entry to ID_RANGES."
                )
            graph_id = id_counters[registry_type]
            id_counters[registry_type] += 1
            G, name, metadata = gen_fn(**kwargs)
            if extra_metadata:
                metadata.update(extra_metadata)

            # Attach topology feasibility from the CSV into metadata
            metadata["topologies"] = topologies.split("|")

            path = _save(G, graph_id, name, registry_type, metadata, generated_at)
            saved.append(path)
            print(f"  [{graph_id}] {path.name}")

        except Exception as exc:
            msg = f"Line {line_num}: {csv_type} params={params_raw!r} -- {exc}"
            if skip_errors:
                print(f"  SKIP {msg}")
                errors.append((line_num, csv_type, exc))
            else:
                raise RuntimeError(msg) from exc

    # Write ID_RANGES and per-type next-available IDs to disk for reference.
    ranges_path = GENERATED_DIR / "id_ranges.json"
    ranges_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ranges_path, "w") as f:
        json.dump({
            "starting_ids": ID_RANGES,
            "next_available": {
                t: id_counters[t]
                for t in ID_RANGES
                if id_counters[t] != ID_RANGES[t]   # only types that were used
            },
        }, f, indent=2)
    print(f"  ID ranges written to {ranges_path}")

    print(f"\n{len(saved)} graph(s) saved to {GENERATED_DIR}/")
    if errors:
        print(f"{len(errors)} error(s) skipped.")
    return saved


# =============================================================================
# CLI
# =============================================================================

def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate test graphs and save to generated_graphs/<type>/."
    )
    parser.add_argument(
        "graph_type", nargs="?",
        help="Graph type to generate (see --list for options).",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all registered graph types and their parameters.",
    )
    parser.add_argument(
        "--csv", metavar="FILE",
        help="Generate all graphs specified in a CSV library file.",
    )
    parser.add_argument(
        "--skip-errors", action="store_true",
        help="When using --csv, log failures and continue rather than aborting.",
    )
    parser.add_argument(
        "--topologies", nargs="+", metavar="TOPOLOGY",
        help="When using --csv, only generate rows matching these topology names "
             "(e.g. --topologies chimera pegasus).",
    )

    # One flag per unique parameter name across all types.
    all_params = sorted({p for _, (_, ps) in REGISTRY.items() for p in ps})
    for p in all_params:
        if p == "offsets":
            parser.add_argument(
                "--offsets", nargs="+", metavar="INT",
                help="Offset integers for circulant graph (one set per CLI call).",
            )
        else:
            parser.add_argument(
                f"--{p}", nargs="+",
                help=f"Values for parameter '{p}' (space-separated).",
            )

    return parser


def _coerce(value: str) -> Any:
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


if __name__ == "__main__":
    parser = _build_cli()
    args = parser.parse_args()

    # --csv mode
    if args.csv:
        generate_from_csv(
            args.csv,
            skip_errors=args.skip_errors,
            topologies_filter=args.topologies or None,
        )
        raise SystemExit(0)

    if args.list or not args.graph_type:
        print("Registered graph types:\n")
        categories = [
            ("Structured",      ["complete", "bipartite", "grid", "cycle", "path", "star",
                                 "wheel", "binary_tree", "tree", "hypercube", "turan",
                                 "circulant", "johnson", "kneser",
                                 "generalized_petersen", "sudoku"]),
            ("Named",           ["petersen", "dodecahedral", "icosahedral", "moebius_kantor",
                                 "heawood", "pappus", "desargues", "bull", "butterfly", "wagner",
                                 "tutte", "house", "chvatal", "mcgee", "franklin",
                                 "named_special"]),
            ("Random",          ["random_er", "barabasi_albert", "regular", "watts_strogatz",
                                 "sbm", "random_planar", "random_tree"]),
            ("Physics lattice", ["triangular_lattice", "honeycomb", "cubic_lattice",
                                 "king_graph", "frustrated_square", "kagome",
                                 "shastry_sutherland", "bcc_lattice"]),
            ("Network science", ["lfr_benchmark", "random_geometric"]),
            ("Application",     ["spin_glass", "weak_strong_cluster", "power_grid",
                                 "planted_solution"]),
            ("Hardware",        ["hardware_native"]),
            ("NP problems",     ["np_problem"]),
            ("QUBO",            ["mis_qubo", "matching_qubo", "portfolio_qubo"]),
        ]
        for cat, names in categories:
            print(f"{cat}:")
            for name in names:
                _, pnames = REGISTRY[name]
                pstr = ", ".join(pnames) if pnames else "(no parameters)"
                print(f"  {name:<22}  {pstr}")
            print()
        print(f"Output directory: {GENERATED_DIR}")
        raise SystemExit(0)

    _, param_names = REGISTRY[args.graph_type]
    kwargs: dict[str, list] = {}
    for p in param_names:
        if p == "offsets":
            raw = getattr(args, "offsets", None)
            if raw:
                kwargs["offsets"] = [tuple(int(v) for v in raw)]
        else:
            raw = getattr(args, p, None)
            if raw:
                kwargs[p] = [_coerce(v) for v in raw]

    print(f"Generating '{args.graph_type}' graphs...")
    paths = generate_graphs(args.graph_type, **kwargs)
    print(f"\n{len(paths)} graph(s) saved to {GENERATED_DIR / args.graph_type}/")