#!/usr/bin/env python3
"""Verification suite for ember-qc benchmark graphs.

Usage:
    python verify_graphs.py                    # verify all
    python verify_graphs.py --type grid        # verify only grid graphs
    python verify_graphs.py --id 500 501 502   # verify specific IDs
    python verify_graphs.py --summary          # print pass/fail counts only
    python verify_graphs.py --fail-only        # print only failures
"""

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx

GRAPH_DIR = Path("/Users/zachmacaskill-smith/Dropbox/Zach_Dropbox/Code/Research/ember/scripts/generated_graphs/New_Generation/libary/library2")

# =============================================================================
# Result tracking
# =============================================================================

class VerificationResult:
    def __init__(self, graph_id: int, name: str, graph_type: str):
        self.graph_id = graph_id
        self.name = name
        self.graph_type = graph_type
        self.checks: list[tuple[str, bool, str]] = []

    def check(self, name: str, condition: bool, detail: str = ""):
        self.checks.append((name, condition, detail))
        return condition

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    @property
    def failures(self) -> list[tuple[str, str]]:
        return [(n, d) for n, ok, d in self.checks if not ok]

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        n_pass = sum(1 for _, ok, _ in self.checks if ok)
        n_total = len(self.checks)
        msg = f"[{status}] ID {self.graph_id} ({self.name}): {n_pass}/{n_total} checks"
        for fname, detail in self.failures:
            msg += f"\n    FAIL: {fname} — {detail}"
        return msg


# =============================================================================
# Universal checks
# =============================================================================

def check_universal(G: nx.Graph, meta: dict, result: VerificationResult):
    result.check("has_nodes", G.number_of_nodes() > 0,
                 f"nodes={G.number_of_nodes()}")
    result.check("no_selfloops", nx.number_of_selfloops(G) == 0,
                 f"selfloops={nx.number_of_selfloops(G)}")
    result.check("simple_graph",
                 isinstance(G, nx.Graph) and not isinstance(G, nx.MultiGraph),
                 f"type={type(G).__name__}")
    result.check("int_labels",
                 all(isinstance(n, int) for n in G.nodes()),
                 f"types={set(type(n).__name__ for n in list(G.nodes())[:10])}")


# =============================================================================
# Type-specific checkers
# Keys match the `category` field in saved JSON (= registry type name).
# =============================================================================

def check_complete(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    expected_edges = n * (n - 1) // 2
    result.check("edge_count", G.number_of_edges() == expected_edges,
                 f"expected={expected_edges}, got={G.number_of_edges()}")
    result.check("is_regular", nx.is_regular(G))


def check_bipartite(G, meta, result):
    # registry type: "bipartite" (CSV type was "complete_bipartite")
    m, n = meta["m"], meta["n"]
    result.check("node_count", G.number_of_nodes() == m + n,
                 f"expected={m+n}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == m * n,
                 f"expected={m*n}, got={G.number_of_edges()}")
    result.check("is_bipartite", nx.is_bipartite(G))


def check_grid(G, meta, result):
    m, n = meta["m"], meta["n"]
    periodic = meta.get("periodic", False)
    result.check("node_count", G.number_of_nodes() == m * n,
                 f"expected={m*n}, got={G.number_of_nodes()}")
    if not periodic:
        expected_edges = m * (n - 1) + n * (m - 1)
        result.check("edge_count", G.number_of_edges() == expected_edges,
                     f"expected={expected_edges}, got={G.number_of_edges()}")
    result.check("is_bipartite", nx.is_bipartite(G))
    result.check("is_connected", nx.is_connected(G))
    result.check("is_planar", nx.is_planar(G))
    degs = set(dict(G.degree()).values())
    result.check("max_degree_le_4", max(degs) <= 4, f"max_degree={max(degs)}")
    if periodic:
        result.check("is_regular_periodic", nx.is_regular(G), f"degrees={degs}")


def check_cycle(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == n,
                 f"expected={n}, got={G.number_of_edges()}")
    result.check("all_degree_2", set(dict(G.degree()).values()) == {2})
    result.check("is_connected", nx.is_connected(G))


def check_path(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == n - 1,
                 f"expected={n-1}, got={G.number_of_edges()}")
    result.check("is_connected", nx.is_connected(G))
    degs = sorted(dict(G.degree()).values())
    result.check("endpoints_degree_1", degs[0] == 1 and degs[1] == 1)


def check_star(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n + 1,
                 f"expected={n+1}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == n,
                 f"expected={n}, got={G.number_of_edges()}")
    result.check("is_connected", nx.is_connected(G))
    result.check("hub_degree", max(dict(G.degree()).values()) == n,
                 f"max_degree={max(dict(G.degree()).values())}, expected={n}")


def check_wheel(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n + 1,
                 f"expected={n+1}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == 2 * n,
                 f"expected={2*n}, got={G.number_of_edges()}")
    result.check("is_connected", nx.is_connected(G))


def check_turan(G, meta, result):
    n, r = meta["n"], meta["r"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    q, s = divmod(n, r)
    expected_edges = (n * n - s * (q + 1) ** 2 - (r - s) * q ** 2) // 2
    result.check("edge_count", G.number_of_edges() == expected_edges,
                 f"expected={expected_edges}, got={G.number_of_edges()}")
    result.check("is_connected", nx.is_connected(G))


def check_circulant(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("is_regular", nx.is_regular(G))
    result.check("is_connected", nx.is_connected(G))


def check_generalized_petersen(G, meta, result):
    n, k = meta["n"], meta["k"]
    result.check("node_count", G.number_of_nodes() == 2 * n,
                 f"expected={2*n}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == 3 * n,
                 f"expected={3*n}, got={G.number_of_edges()}")
    result.check("is_3_regular", set(dict(G.degree()).values()) == {3})
    result.check("is_connected", nx.is_connected(G))
    if n == 5 and k == 2:
        result.check("petersen_isomorphic",
                     nx.is_isomorphic(G, nx.petersen_graph()))


def check_hypercube(G, meta, result):
    k = meta["k"]
    result.check("node_count", G.number_of_nodes() == 2 ** k,
                 f"expected={2**k}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == k * 2 ** (k - 1),
                 f"expected={k * 2**(k-1)}, got={G.number_of_edges()}")
    result.check("is_bipartite", nx.is_bipartite(G))
    result.check("is_connected", nx.is_connected(G))
    result.check("is_regular", nx.is_regular(G))


def check_binary_tree(G, meta, result):
    depth = meta["depth"]
    expected_nodes = 2 ** (depth + 1) - 1
    result.check("node_count", G.number_of_nodes() == expected_nodes,
                 f"expected={expected_nodes}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == expected_nodes - 1,
                 f"expected={expected_nodes-1}, got={G.number_of_edges()}")
    result.check("is_tree", nx.is_tree(G))


def check_tree(G, meta, result):
    # registry type "tree" (balanced_tree); metadata keys: branching, depth
    r = meta.get("branching", meta.get("r"))
    h = meta.get("depth", meta.get("h"))
    expected_nodes = (r ** (h + 1) - 1) // (r - 1)
    result.check("node_count", G.number_of_nodes() == expected_nodes,
                 f"expected={expected_nodes}, got={G.number_of_nodes()}")
    result.check("is_tree", nx.is_tree(G))


def check_johnson(G, meta, result):
    from math import comb
    n, k = meta["n"], meta["k"]
    expected_nodes = comb(n, k)
    result.check("node_count", G.number_of_nodes() == expected_nodes,
                 f"expected={expected_nodes}, got={G.number_of_nodes()}")
    result.check("is_regular", nx.is_regular(G))
    result.check("is_connected", nx.is_connected(G))


def check_kneser(G, meta, result):
    from math import comb
    n, k = meta["n"], meta["k"]
    expected_nodes = comb(n, k)
    result.check("node_count", G.number_of_nodes() == expected_nodes,
                 f"expected={expected_nodes}, got={G.number_of_nodes()}")
    result.check("is_regular", nx.is_regular(G))


def check_sudoku(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n ** 4,
                 f"expected={n**4}, got={G.number_of_nodes()}")
    result.check("is_regular", nx.is_regular(G))
    result.check("is_connected", nx.is_connected(G))


def check_random_er(G, meta, result):
    # registry type "random_er" (CSV type was "erdos_renyi")
    n, p = meta["n"], meta["p"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    expected = n * (n - 1) / 2 * p
    sigma = math.sqrt(n * (n - 1) / 2 * p * (1 - p))
    actual = G.number_of_edges()
    result.check("edge_count_statistical",
                 abs(actual - expected) <= 4 * max(sigma, 1),
                 f"expected~{expected:.0f}±{4*sigma:.0f}, got={actual}")
    density = nx.density(G)
    result.check("density_close_to_p",
                 abs(density - p) < max(0.15, 3 / math.sqrt(n)),
                 f"density={density:.4f}, p={p}")


def check_barabasi_albert(G, meta, result):
    n, m = meta["n"], meta["m"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    expected_edges = m * (n - m)
    result.check("edge_count", G.number_of_edges() == expected_edges,
                 f"expected={expected_edges}, got={G.number_of_edges()}")
    # Note: BA seed nodes (first m nodes) legitimately have degree < m.
    # Checking min_degree >= m is incorrect — check mean degree instead.
    mean_deg = 2 * G.number_of_edges() / G.number_of_nodes()
    result.check("mean_degree_reasonable", mean_deg >= m * 0.9,
                 f"mean_degree={mean_deg:.2f}, expected>={m*0.9:.1f}")
    result.check("is_connected", nx.is_connected(G))


def check_regular(G, meta, result):
    n, d = meta["n"], meta["d"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == n * d // 2,
                 f"expected={n*d//2}, got={G.number_of_edges()}")
    result.check("is_regular", nx.is_regular(G))
    result.check("all_degree_d", set(dict(G.degree()).values()) == {d},
                 f"expected={{{d}}}, got={set(dict(G.degree()).values())}")


def check_watts_strogatz(G, meta, result):
    n, k = meta["n"], meta["k"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == n * k // 2,
                 f"expected={n*k//2}, got={G.number_of_edges()}")
    if meta.get("beta", None) == 0:
        result.check("regular_at_beta0", nx.is_regular(G))
    result.check("is_connected", nx.is_connected(G))


def check_sbm(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("is_connected_or_documented",
                 nx.is_connected(G) or meta.get("p_out", 0) < 0.01,
                 f"connected={nx.is_connected(G)}, p_out={meta.get('p_out')}")


def check_lfr_benchmark(G, meta, result):
    result.check("node_count", G.number_of_nodes() == meta["n"],
                 f"expected={meta['n']}, got={G.number_of_nodes()}")
    result.check("is_connected", nx.is_connected(G))


def check_random_planar(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("is_planar", nx.is_planar(G))
    result.check("edge_bound", G.number_of_edges() <= 3 * n - 6,
                 f"edges={G.number_of_edges()}, max={3*n-6}")


def check_random_tree(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("edge_count", G.number_of_edges() == n - 1,
                 f"expected={n-1}, got={G.number_of_edges()}")
    result.check("is_tree", nx.is_tree(G))


def check_triangular_lattice(G, meta, result):
    result.check("is_connected", nx.is_connected(G))
    if not meta.get("periodic", False):
        result.check("is_planar", nx.is_planar(G))
    result.check("not_bipartite", not nx.is_bipartite(G))
    result.check("max_degree_6", max(dict(G.degree()).values()) == 6)
    if meta.get("periodic", False):
        result.check("is_regular_periodic", nx.is_regular(G))


def check_kagome(G, meta, result):
    result.check("is_connected", nx.is_connected(G))
    result.check("not_bipartite", not nx.is_bipartite(G))
    if not meta.get("periodic", False):
        result.check("is_planar", nx.is_planar(G))
    degs = set(dict(G.degree()).values())
    if meta.get("periodic", False):
        result.check("all_degree_4", degs == {4}, f"degrees={degs}")
    else:
        result.check("max_degree_4", max(degs) == 4, f"degrees={degs}")


def check_honeycomb(G, meta, result):
    result.check("is_connected", nx.is_connected(G))
    result.check("is_bipartite", nx.is_bipartite(G))
    if not meta.get("periodic", False):
        result.check("is_planar", nx.is_planar(G))
    result.check("no_triangles", sum(nx.triangles(G).values()) == 0)
    if meta.get("periodic", False):
        result.check("all_degree_3_periodic",
                     set(dict(G.degree()).values()) == {3})


def check_king_graph(G, meta, result):
    m, n = meta["m"], meta["n"]
    result.check("node_count", G.number_of_nodes() == m * n,
                 f"expected={m*n}, got={G.number_of_nodes()}")
    result.check("not_bipartite", not nx.is_bipartite(G))
    result.check("is_connected", nx.is_connected(G))
    degs = dict(G.degree())
    result.check("max_degree_8", max(degs.values()) == 8)
    if meta.get("periodic", False):
        result.check("all_degree_8_periodic", set(degs.values()) == {8})
    elif m >= 3 and n >= 3:
        result.check("corner_degree_3", min(degs.values()) == 3)


def check_frustrated_square(G, meta, result):
    check_king_graph(G, meta, result)


def check_shastry_sutherland(G, meta, result):
    m, n = meta["m"], meta["n"]
    result.check("node_count", G.number_of_nodes() == m * n,
                 f"expected={m*n}, got={G.number_of_nodes()}")
    result.check("is_connected", nx.is_connected(G))
    result.check("not_bipartite", not nx.is_bipartite(G))


def check_cubic_lattice(G, meta, result):
    x, y, z = meta["x"], meta["y"], meta["z"]
    result.check("node_count", G.number_of_nodes() == x * y * z,
                 f"expected={x*y*z}, got={G.number_of_nodes()}")
    result.check("is_bipartite", nx.is_bipartite(G))
    result.check("is_connected", nx.is_connected(G))
    degs = dict(G.degree())
    if meta.get("periodic", False):
        result.check("is_regular_periodic", set(degs.values()) == {6})
    else:
        result.check("max_degree_6", max(degs.values()) == 6)
        if x >= 3 and y >= 3 and z >= 3:
            result.check("min_degree_3", min(degs.values()) == 3)


def check_bcc_lattice(G, meta, result):
    m = meta["m"]
    expected_nodes = (m + 1) ** 3 + m ** 3
    result.check("node_count", G.number_of_nodes() == expected_nodes,
                 f"expected={expected_nodes}, got={G.number_of_nodes()}")
    result.check("is_bipartite", nx.is_bipartite(G))
    result.check("is_connected", nx.is_connected(G))


def check_weak_strong_cluster(G, meta, result):
    nc = meta["n_clusters"]
    cs = meta["cluster_size"]
    ie = meta["inter_edges_per_cluster"]
    result.check("node_count", G.number_of_nodes() == nc * cs,
                 f"expected={nc*cs}, got={G.number_of_nodes()}")
    intra_edges = 0
    for c in range(nc):
        sub = G.subgraph(range(c * cs, (c + 1) * cs))
        intra_edges += sub.number_of_edges()
        if c == 0:
            expected_clique = cs * (cs - 1) // 2
            result.check("cluster_0_is_clique",
                         sub.number_of_edges() == expected_clique,
                         f"expected={expected_clique}, got={sub.number_of_edges()}")
    result.check("inter_edge_count",
                 G.number_of_edges() - intra_edges == nc * ie,
                 f"expected={nc*ie}, got={G.number_of_edges()-intra_edges}")
    result.check("is_connected", nx.is_connected(G))


def check_planted_solution(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("has_edges", G.number_of_edges() > 0)
    # Hardware subgraphs may be sparse; at least n//2 edges is a reasonable minimum
    result.check("reasonable_density", G.number_of_edges() >= n // 2,
                 f"edges={G.number_of_edges()}, expected>={n//2}")


def check_spin_glass(G, meta, result):
    n = meta["n"]
    result.check("node_count", G.number_of_nodes() == n,
                 f"expected={n}, got={G.number_of_nodes()}")
    result.check("all_edges_weighted",
                 all("weight" in d for _, _, d in G.edges(data=True)))
    if meta.get("edge_density", 1.0) >= 1.0:
        expected = n * (n - 1) // 2
        result.check("complete_edge_count", G.number_of_edges() == expected,
                     f"expected={expected}, got={G.number_of_edges()}")
    if meta.get("weight_distribution") == "bimodal":
        weights = {d["weight"] for _, _, d in G.edges(data=True)}
        result.check("bimodal_weights", weights == {-1.0, 1.0},
                     f"weight_values={weights}")


def check_hardware_native(G, meta, result):
    result.check("has_nodes", G.number_of_nodes() > 0)
    result.check("has_edges", G.number_of_edges() > 0)
    result.check("is_connected", nx.is_connected(G))
    result.check("is_regular", nx.is_regular(G),
                 f"degrees={set(dict(G.degree()).values())}")


def check_named_special(G, meta, result):
    result.check("has_nodes", G.number_of_nodes() > 0)
    result.check("has_edges", G.number_of_edges() > 0)
    result.check("is_connected", nx.is_connected(G))
    name = meta.get("name", meta.get("type", ""))
    KNOWN = {
        "petersen": (10, 15), "dodecahedral": (20, 30), "icosahedral": (12, 30),
        "heawood": (14, 21), "pappus": (18, 27), "desargues": (20, 30),
        "mcgee": (24, 36), "tutte": (46, 69), "bull": (5, 5),
        "house": (5, 6), "franklin": (12, 18), "chvatal": (12, 24),
    }
    if name in KNOWN:
        en, ee = KNOWN[name]
        result.check("known_node_count", G.number_of_nodes() == en,
                     f"expected={en}, got={G.number_of_nodes()}")
        result.check("known_edge_count", G.number_of_edges() == ee,
                     f"expected={ee}, got={G.number_of_edges()}")


# =============================================================================
# Dispatch — keys must match the `category` field in saved JSON files
# =============================================================================

TYPE_CHECKERS = {
    # Structured
    "complete":             check_complete,
    "bipartite":            check_bipartite,          # registry name (CSV: complete_bipartite)
    "grid":                 check_grid,
    "cycle":                check_cycle,
    "path":                 check_path,
    "star":                 check_star,
    "wheel":                check_wheel,
    "turan":                check_turan,
    "circulant":            check_circulant,
    "generalized_petersen": check_generalized_petersen,
    "hypercube":            check_hypercube,
    "binary_tree":          check_binary_tree,
    "tree":                 check_tree,               # registry name (CSV: balanced_tree)
    "johnson":              check_johnson,
    "kneser":               check_kneser,
    "sudoku":               check_sudoku,
    # Random
    "random_er":            check_random_er,          # registry name (CSV: erdos_renyi)
    "barabasi_albert":      check_barabasi_albert,
    "regular":              check_regular,
    "watts_strogatz":       check_watts_strogatz,
    "sbm":                  check_sbm,
    "lfr_benchmark":        check_lfr_benchmark,
    "random_planar":        check_random_planar,
    "random_tree":          check_random_tree,
    # Physics lattices
    "triangular_lattice":   check_triangular_lattice,
    "kagome":               check_kagome,
    "honeycomb":            check_honeycomb,
    "king_graph":           check_king_graph,
    "frustrated_square":    check_frustrated_square,
    "shastry_sutherland":   check_shastry_sutherland,
    "cubic_lattice":        check_cubic_lattice,
    "bcc_lattice":          check_bcc_lattice,
    # Application
    "weak_strong_cluster":  check_weak_strong_cluster,
    "planted_solution":     check_planted_solution,
    "spin_glass":           check_spin_glass,
    # Special
    "hardware_native":      check_hardware_native,
    "named_special":        check_named_special,
}


# =============================================================================
# Load
# =============================================================================

def load_graph(filepath: Path) -> tuple[nx.Graph, dict, int, str]:
    """Load a graph JSON. Handles both 'edges' (NX 3.x) and 'links' (NX 2.x) key."""
    with open(filepath) as f:
        data = json.load(f)

    graph_data = data["graph"]

    # Files generated before the edges="edges" fix use "links" key.
    # Normalise to "edges" so node_link_graph always works.
    if "links" in graph_data and "edges" not in graph_data:
        graph_data = {**graph_data, "edges": graph_data["links"]}
        del graph_data["links"]  # avoid ambiguity

    G = nx.node_link_graph(graph_data, edges="edges")

    if not all(isinstance(n, int) for n in G.nodes()):
        G = nx.convert_node_labels_to_integers(G)

    return G, data.get("metadata", {}), data["id"], data.get("category", "unknown")


# =============================================================================
# Verify and collect
# =============================================================================

def verify_one(filepath: Path) -> VerificationResult:
    G, meta, gid, category = load_graph(filepath)
    result = VerificationResult(gid, filepath.stem, category)
    check_universal(G, meta, result)
    checker = TYPE_CHECKERS.get(category)
    if checker:
        try:
            checker(G, meta, result)
        except Exception as e:
            result.check("type_check_error", False, f"Exception: {e}")
    else:
        result.check("has_type_checker", False,
                     f"No checker for category '{category}'")
    return result


def collect_files(graph_type: str = None, ids: list[int] = None) -> list[Path]:
    files = []
    if ids:
        id_set = set(ids)
        for subdir in GRAPH_DIR.iterdir():
            if not subdir.is_dir():
                continue
            for f in subdir.glob("*.json"):
                try:
                    if int(f.name.split("_")[0]) in id_set:
                        files.append(f)
                except ValueError:
                    pass
    elif graph_type:
        type_dir = GRAPH_DIR / graph_type
        if type_dir.is_dir():
            files = sorted(type_dir.glob("*.json"))
        else:
            print(f"No directory found for type '{graph_type}'")
    else:
        for subdir in sorted(GRAPH_DIR.iterdir()):
            if subdir.is_dir() and subdir.name != "__pycache__":
                files.extend(sorted(subdir.glob("*.json")))
    return files


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Verify ember-qc benchmark graphs")
    parser.add_argument("--type", help="Verify only this graph type")
    parser.add_argument("--id", nargs="+", type=int, help="Verify specific graph IDs")
    parser.add_argument("--summary", action="store_true", help="Print only summary")
    parser.add_argument("--fail-only", action="store_true", help="Print only failures")
    parser.add_argument("--limit", type=int, default=0, help="Limit files (0=all)")
    args = parser.parse_args()

    files = collect_files(graph_type=args.type, ids=args.id)
    if args.limit > 0:
        files = files[:args.limit]
    if not files:
        print("No graph files found.")
        sys.exit(1)

    print(f"Verifying {len(files)} graph files...\n")

    results = []
    type_stats: dict = defaultdict(lambda: {"pass": 0, "fail": 0, "errors": []})

    for f in files:
        try:
            r = verify_one(f)
            results.append(r)
            s = type_stats[r.graph_type]
            if r.passed:
                s["pass"] += 1
            else:
                s["fail"] += 1
                s["errors"].extend(r.failures)
            if not args.summary and (not args.fail_only or not r.passed):
                print(r.summary())
        except Exception as e:
            print(f"ERROR loading {f.name}: {e}")
            type_stats["_load_error"]["fail"] += 1

    total_pass = sum(1 for r in results if r.passed)
    total_fail = sum(1 for r in results if not r.passed)

    print(f"\n{'='*60}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total: {len(results)} graphs verified")
    print(f"  PASS: {total_pass}")
    print(f"  FAIL: {total_fail}")
    print()
    print(f"{'Type':<25} {'Pass':>6} {'Fail':>6} {'Total':>6}")
    print(f"{'-'*25} {'-'*6} {'-'*6} {'-'*6}")
    for gtype in sorted(type_stats):
        s = type_stats[gtype]
        total = s["pass"] + s["fail"]
        flag = "  " if s["fail"] == 0 else "!!"
        print(f"{flag} {gtype:<23} {s['pass']:>6} {s['fail']:>6} {total:>6}")

    if total_fail > 0:
        print(f"\n{total_fail} graphs FAILED verification.")
        all_failures = [check for r in results if not r.passed
                        for check, _ in r.failures]
        print("\nTop failure reasons:")
        for reason, count in Counter(all_failures).most_common(10):
            print(f"  {reason}: {count}")

    sys.exit(1 if total_fail > 0 else 0)


if __name__ == "__main__":
    main()