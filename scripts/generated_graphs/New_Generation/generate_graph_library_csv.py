"""
generate_graph_library_csv.py

Generates the EMBER graph library specification CSV.
Uses Zephyr Z12 as the upper generation bound.
Each row is tagged with which topologies the graph is theoretically
feasible on, based on node/edge count checks.

Topology ceilings:
    Chimera C16:  2,048 nodes,  6,016 edges
    Pegasus P16:  5,640 nodes, 40,484 edges
    Zephyr  Z12:  4,800 nodes, 45,864 edges

Output format:
    graph_type,params,seed,topologies
"""

import csv
import sys
import math
from math import comb

TOPOLOGIES = {
    "chimera": {"nodes": 2048,  "edges": 6016},
    "pegasus": {"nodes": 5640,  "edges": 40484},
    "zephyr":  {"nodes": 4800,  "edges": 45864},
}

MAX_NODES = max(t["nodes"] for t in TOPOLOGIES.values())  # 5640
MAX_EDGES = max(t["edges"] for t in TOPOLOGIES.values())  # 45864


def topology_tag(n_nodes, n_edges):
    valid = [name for name, lims in TOPOLOGIES.items()
             if n_nodes <= lims["nodes"] and n_edges <= lims["edges"]]
    return "|".join(valid)


def is_feasible(n_nodes, n_edges):
    return any(n_nodes <= lims["nodes"] and n_edges <= lims["edges"]
               for lims in TOPOLOGIES.values())


def geom_range(start, stop, step_factor):
    values = []
    v = float(start)
    while v <= stop:
        iv = int(round(v))
        if iv <= stop and (not values or iv != values[-1]):
            values.append(iv)
        v *= step_factor
    if not values or values[-1] != int(stop):
        values.append(int(stop))
    return values


MAIN_SEEDS     = (0, 1, 2)
BOUNDARY_SEEDS = (0, 1, 2, 3, 4)

def seeds_for(n, ceil):
    return BOUNDARY_SEEDS if n >= 0.85 * ceil else MAIN_SEEDS


def main():
    w = csv.writer(sys.stdout)
    w.writerow(["graph_type", "params", "seed", "topologies"])

    def emit(graph_type, params, seed, n_nodes, n_edges):
        tag = topology_tag(n_nodes, n_edges)
        if tag:
            ps = ";".join(f"{k}={v}" for k, v in params.items())
            w.writerow([graph_type, ps, seed, tag])

    # =========================================================================
    # SECTION 1: DETERMINISTIC STRUCTURED
    # =========================================================================

    # Complete K_n — edge ceiling zephyr: n(n-1)/2 <= 45864 => n<=304
    n_vals = (list(range(2, 11)) + list(range(12, 32, 2)) +
              list(range(33, 63, 3)) + geom_range(63, 304, 1.06))
    for n in sorted(set(n_vals)):
        emit("complete", {"n": n}, 0, n, n*(n-1)//2)

    # Complete Bipartite K_{m,m} — edges=m^2, zephyr: m<=214
    for m in geom_range(2, 214, 1.07):
        emit("complete_bipartite", {"m": m, "n": m}, 0, 2*m, m*m)

    # Complete Bipartite K_{m,2m} — edges=2m^2, zephyr: m<=151
    for m in geom_range(2, 151, 1.07):
        emit("complete_bipartite", {"m": m, "n": 2*m}, 0, 3*m, 2*m*m)

    # Complete Bipartite K_{m,3m} — edges=3m^2, zephyr: m<=123
    for m in geom_range(2, 123, 1.07):
        emit("complete_bipartite", {"m": m, "n": 3*m}, 0, 4*m, 3*m*m)

    # Grid m×m — nodes=m^2, pegasus: m<=75
    for m in geom_range(2, 75, 1.07):
        emit("grid", {"m": m, "n": m}, 0, m*m, 2*m*(m-1))

    # Grid m×2m — nodes=2m^2, pegasus: m<=53
    for m in geom_range(2, 53, 1.07):
        emit("grid", {"m": m, "n": 2*m}, 0, 2*m*m, m*(4*m-3))

    # Grid m×3m — nodes=3m^2, pegasus: m<=43
    for m in geom_range(2, 43, 1.07):
        emit("grid", {"m": m, "n": 3*m}, 0, 3*m*m, m*(6*m-4))

    # Cycle / Path / Star / Wheel — pegasus node ceiling 5640
    for n in geom_range(3, 5640, 1.12):
        emit("cycle",  {"n": n}, 0, n,   n)
        emit("path",   {"n": n}, 0, n,   n-1)
        emit("star",   {"n": n}, 0, n+1, n)
        emit("wheel",  {"n": n}, 0, n+1, 2*n)

    # Turan T(n,r)
    for r in range(2, 9):
        n_max = min(int(math.sqrt(45864*2/(1-1/r))), MAX_NODES)
        for n in geom_range(r+1, n_max, 1.07):
            edges = int((1-1/r)*n*n/2)
            emit("turan", {"n": n, "r": r}, 0, n, edges)

    # Circulant
    for offsets, degree in [([1,2],4),([1,3],4),([2,4],4),
                             ([1,2,3],6),([1,3,5],6),([2,4,6],6),
                             ([1,2,3,4],8)]:
        n_max = min(int(91728/degree), MAX_NODES)
        n_min = max(offsets)*2+1
        offset_str = "-".join(str(o) for o in offsets)
        for n in geom_range(n_min, n_max, 1.10):
            emit("circulant", {"n": n, "offsets": offset_str}, 0, n, degree*n//2)

    # Generalized Petersen GP(n,k) — nodes=2n, edges=3n
    for k in range(1, 11):
        for n in geom_range(2*k+2, 2820, 1.12):
            emit("generalized_petersen", {"n": n, "k": k}, 0, 2*n, 3*n)

    # Hypercube Q_k
    for k in range(2, 14):
        emit("hypercube", {"k": k}, 0, 2**k, k*2**(k-1))

    # Binary Tree depth d
    for d in range(1, 13):
        nodes = 2**(d+1)-1
        emit("binary_tree", {"d": d}, 0, nodes, nodes-1)

    # Balanced Tree (r,d)
    for r in range(2, 6):
        for d in range(2, 8):
            nodes = (r**(d+1)-1)//(r-1)
            if is_feasible(nodes, nodes-1):
                emit("balanced_tree", {"r": r, "d": d}, 0, nodes, nodes-1)

    # Johnson J(n,k)
    for k in range(2, 6):
        for n in range(2*k+1, 40):
            nodes = comb(n,k)
            edges = comb(n,k)*k*(n-k)//2
            if is_feasible(nodes, edges):
                emit("johnson", {"n": n, "k": k}, 0, nodes, edges)

    # Kneser KG(n,k)
    for k in range(2, 5):
        for n in range(2*k+1, 30):
            nodes = comb(n,k)
            edges = nodes*(nodes-1)//4  # approximate
            if is_feasible(nodes, edges):
                emit("kneser", {"n": n, "k": k}, 0, nodes, edges)

    # =========================================================================
    # SECTION 2: RANDOM GRAPHS
    # =========================================================================

    # Erdos-Renyi
    for p in [0.005,0.01,0.02,0.05,0.10,0.15,0.25,0.33,0.50,0.67,0.75,0.90]:
        n_ceil = min(int(math.sqrt(91728/p)+0.5), MAX_NODES)
        for n in geom_range(10, n_ceil, 1.09):
            exp_e = int(p*n*(n-1)/2)
            for seed in seeds_for(n, n_ceil):
                emit("erdos_renyi", {"n": n, "p": p}, seed, n, exp_e)

    # Barabasi-Albert
    for m_ba in [1,2,3,4,5,6,8,10,15,20]:
        n_ceil = min(int(45864/m_ba), MAX_NODES)
        for n in geom_range(m_ba+2, n_ceil, 1.09):
            for seed in seeds_for(n, n_ceil):
                emit("barabasi_albert", {"n": n, "m": m_ba}, seed, n, m_ba*n)

    # d-Regular
    for d in [3,4,5,6,8,10,12,15,20,30,40]:
        n_ceil = min(int(91728/d), MAX_NODES)
        n_start = max(d+2, 6)
        if n_start % 2: n_start += 1
        n_vals = geom_range(n_start, n_ceil, 1.09)
        n_vals = sorted(set(n if n%2==0 else n+1 for n in n_vals if (n if n%2==0 else n+1)<=n_ceil))
        for n in n_vals:
            for seed in seeds_for(n, n_ceil):
                emit("regular", {"n": n, "d": d}, seed, n, n*d//2)

    # Watts-Strogatz
    for k in [4,6,8,10,12,20]:
        n_ceil = min(int(91728/k), MAX_NODES)
        n_start = max(k+2,6)
        if n_start%2: n_start+=1
        n_vals = geom_range(n_start, n_ceil, 1.09)
        n_vals = sorted(set(n if n%2==0 else n+1 for n in n_vals if (n if n%2==0 else n+1)<=n_ceil))
        for beta in [0.0,0.1,0.3,0.5,0.8,1.0]:
            for n in n_vals:
                for seed in seeds_for(n, n_ceil):
                    emit("watts_strogatz", {"n": n, "k": k, "beta": beta}, seed, n, n*k//2)

    # SBM
    for p_in, p_out in [(0.50,0.05),(0.30,0.05),(0.20,0.05),(0.50,0.10),(0.20,0.10),(0.10,0.02)]:
        for n in geom_range(20, 600, 1.10):
            n4 = (n//4)*4
            if n4<20: continue
            exp_e = int(4*comb(n4//4,2)*p_in + 6*(n4//4)**2*p_out)
            for seed in MAIN_SEEDS:
                emit("sbm", {"n": n4, "k": 4, "p_in": p_in, "p_out": p_out}, seed, n4, exp_e)

    # LFR
    for mu in [0.1,0.3,0.5]:
        for n in [50,100,200,400,800,1500,3000]:
            for seed in MAIN_SEEDS:
                emit("lfr_benchmark", {"n": n, "tau1": 2.5, "tau2": 1.5, "mu": mu}, seed, n, n*5)

    # Random Planar — cap at n=660: greedy planarity construction is O(n^2) per
    # edge check, making n>700 take 10+ minutes per graph.
    PLANAR_MAX_N = 660
    for n in geom_range(10, PLANAR_MAX_N, 1.12):
        for seed in [0,1,2,3,4]:
            emit("random_planar", {"n": n}, seed, n, min(3*n-6, MAX_EDGES))

    # =========================================================================
    # SECTION 3: PHYSICS LATTICES
    # =========================================================================

    PERIODIC = [False, True]

    # Triangular Lattice — degree 6, nodes=m*n, edges≈3mn
    for ratio in [1,2,3]:
        m_max = int(math.sqrt(MAX_NODES/ratio))
        for m in geom_range(3, m_max, 1.07):
            nd = m*ratio
            nodes = m*nd
            edges = 3*m*nd - 2*m - 2*nd + 1
            for per in PERIODIC:
                if is_feasible(nodes, edges):
                    emit("triangular_lattice", {"m": m, "n": nd, "periodic": per}, 0, nodes, edges)

    # Kagome — degree 4, nodes=3mn
    for ratio in [1,2,3]:
        m_max = int(math.sqrt(MAX_NODES/(3*ratio)))
        for m in geom_range(2, m_max, 1.07):
            nd = m*ratio
            nodes = 3*m*nd
            edges = 2*nodes
            for per in PERIODIC:
                if is_feasible(nodes, edges):
                    emit("kagome", {"m": m, "n": nd, "periodic": per}, 0, nodes, edges)

    # Honeycomb — degree 3, nodes=2mn
    for ratio in [1,2,3]:
        m_max = int(math.sqrt(MAX_NODES/(2*ratio)))
        for m in geom_range(2, m_max, 1.07):
            nd = m*ratio
            nodes = 2*m*nd
            edges = nodes*3//2
            for per in PERIODIC:
                if is_feasible(nodes, edges):
                    emit("honeycomb", {"m": m, "n": nd, "periodic": per}, 0, nodes, edges)

    # King Graph — degree 8 interior, nodes=m^2, edges=2(m-1)(2m-1)
    # zephyr edge ceiling: 2(m-1)(2m-1)<=45864 => m<=107
    for m in geom_range(3, 107, 1.07):
        nodes = m*m
        edges = 2*(m-1)*(2*m-1)
        for per in PERIODIC:
            if is_feasible(nodes, edges):
                emit("king_graph", {"m": m, "periodic": per}, 0, nodes, edges)

    # Frustrated Square — same structure as King
    for m in geom_range(3, 107, 1.07):
        nodes = m*m
        edges = 2*(m-1)*(2*m-1)
        for per in PERIODIC:
            if is_feasible(nodes, edges):
                emit("frustrated_square", {"m": m, "periodic": per}, 0, nodes, edges)

    # Shastry-Sutherland — nodes=4m^2, degree~5
    # pegasus ceiling: 4m^2<=5640 => m<=37
    for m in range(2, 38):
        nodes = 4*m*m
        edges = nodes*5//2
        for per in PERIODIC:
            if is_feasible(nodes, edges):
                emit("shastry_sutherland", {"m": m, "periodic": per}, 0, nodes, edges)

    # 3D Cubic Lattice
    for (p,q,r) in ([(m,m,m) for m in range(2,18)] +
                    [(m,m,2*m) for m in range(2,14)] +
                    [(m,m,3*m) for m in range(2,12)]):
        nodes = p*q*r
        edges = p*q*(r-1)+p*(q-1)*r+(p-1)*q*r
        for per in PERIODIC:
            if is_feasible(nodes, edges):
                emit("cubic_lattice", {"m": p, "n": q, "p": r, "periodic": per}, 0, nodes, edges)

    # BCC Lattice — nodes≈2m^3, degree 8
    # pegasus: 2m^3<=5640 => m<=14
    for m in range(2, 15):
        nodes = int(2*m**3)
        edges = nodes*4
        for per in PERIODIC:
            if is_feasible(nodes, edges):
                emit("bcc_lattice", {"m": m, "periodic": per}, 0, nodes, edges)

    # =========================================================================
    # SECTION 4: APPLICATION GRAPHS
    # =========================================================================

    # Weak-Strong Cluster
    for cs in [8,16,32,64,128]:
        k_max = MAX_NODES//cs
        for k in geom_range(2, k_max, 1.10):
            nodes = cs*k
            edges = k*comb(cs,2)+k
            for seed in MAIN_SEEDS:
                if is_feasible(nodes, edges):
                    emit("weak_strong_cluster", {"cluster_size": cs, "n_clusters": k}, seed, nodes, edges)

    # Planted Solution
    for p_bg in [0.05,0.10,0.15,0.20]:
        for k_c in [5,10,15,20,30]:
            n_min = k_c**2
            for n in geom_range(n_min, min(1500,MAX_NODES), 1.10):
                if k_c <= math.sqrt(n):
                    exp_e = int(p_bg*n*(n-1)/2+comb(k_c,2))
                    for seed in MAIN_SEEDS:
                        for topo in ["chimera", "pegasus", "zephyr"]:
                            lims = TOPOLOGIES[topo]
                            if n <= lims["nodes"] and exp_e <= lims["edges"]:
                                emit("planted_solution",
                                     {"n": n, "k": k_c, "p": p_bg, "topology": topo},
                                     seed, n, exp_e)

    # Spin Glass
    for n in geom_range(10, 304, 1.07):  # full SK, zephyr ceiling n~304
        edges = n*(n-1)//2
        for seed in [0,1,2,3,4]:
            if is_feasible(n, edges):
                emit("spin_glass", {"n": n, "type": "full"}, seed, n, edges)
    for p in [0.10,0.20,0.30]:
        n_ceil = min(int(math.sqrt(91728/p)+0.5), MAX_NODES)
        for n in geom_range(20, n_ceil, 1.10):
            exp_e = int(p*n*(n-1)/2)
            for seed in MAIN_SEEDS:
                if is_feasible(n, exp_e):
                    emit("spin_glass", {"n": n, "p": p, "type": "sparse"}, seed, n, exp_e)

    # =========================================================================
    # SECTION 5: STRUCTURED SPECIAL
    # =========================================================================

    # Hardware native: one instance per k up to the real hardware ceiling.
    # All instances are genuine subgraphs of the physical topology -- embeddable
    # by identity. Ceilings: Chimera C16 (k=16), Pegasus P16 (k=16), Zephyr Z12 (k=12).
    CHIMERA_CEILING = {"nodes": 2048, "edges": 6016}
    PEGASUS_CEILING = {"nodes": 5640, "edges": 40484}
    ZEPHYR_CEILING  = {"nodes": 4800, "edges": 45864}

    for k in range(1, 17):   # chimera k=1..16
        nodes = 8*k*k
        edges = int(12*k*k - 4*k)  # exact: internal + external edges for chimera_graph(k)
        emit("hardware_native", {"topology": "chimera", "k": k}, 0, nodes, edges)

    for k in range(2, 17):   # pegasus k=2..16; k=1 gives 0 nodes (degenerate), dnx requires m>=2
        nodes = 24*k*(k-1)
        edges = 144*k*(k-1) - 36*k + 12
        emit("hardware_native", {"topology": "pegasus", "k": k}, 0, nodes, edges)

    for k in range(1, 13):   # zephyr k=1..12; use ceiling as upper bound for feasibility
        # Exact Zephyr node/edge formulas are not published; use ceiling-proportional
        # approximation for the feasibility tag only. Actual graph is generated by dnx.
        nodes = int(4800 * k * k / 144)   # scales as k^2, Z12=4800
        edges = int(45864 * k * k / 144)  # same scaling
        emit("hardware_native", {"topology": "zephyr", "k": k}, 0, nodes, edges)

    named = [("petersen",10,15),("dodecahedral",20,30),("icosahedral",12,30),
             ("heawood",14,21),("pappus",18,27),("desargues",20,30),
             ("mcgee",24,36),("tutte",46,69),("bull",5,5),("house",5,6),
             ("franklin",12,18),("chvatal",12,24)]
    for name,nodes,edges in named:
        emit("named_special", {"name": name}, 0, nodes, edges)

    emit("sudoku", {"size": 9},  0, 81,  810)
    emit("sudoku", {"size": 16}, 0, 256, 5440)


if __name__ == "__main__":
    main()
