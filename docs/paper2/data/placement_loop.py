"""
docs/paper2/data/placement_loop.py
==================================
Prototype of the iterated placement loop (notes §3.18): keep one centroid per
problem variable in Pegasus drawing coordinates; each round, relax the
centroids toward their problem-graph neighbours (macroscopic move, O(n*k)
arithmetic), snap them to distinct qubits, let STOCK minorminer legalize from
those seeds (chainlength_patience=0 — the cheap ~1s phase, §3.15), spur-prune,
and read the realized chains' centroids back (congestion feedback). Keep the
best round; warm-polish it once at the end (§3.16-validated pipeline).

All heavy steps are unmodified C++ minorminer via its public API; the Python
steering layer is microseconds — the script reports the time split to prove it.

Arms: mm-full (stock baseline), loop (R rounds + polish), restart-control
(R unguided legalizations, keep best, polish — same cost shape, no geometry).

Run:   .venv/bin/python docs/paper2/data/placement_loop.py [--smoke]
"""

import csv
import os
import sys
import time

import networkx as nx
import numpy as np
import dwave_networkx as dnx
import minorminer
from scipy.spatial import cKDTree

from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
from ember_qc.algorithms.factored.polish import spur_prune

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "placement_loop.csv")

INSTANCE_SEED = 12345
SEEDS = range(5)
NS = (100, 140, 180)
ROUNDS = 10
ETA = 0.5

acl = lambda e: sum(len(c) for c in e.values()) / len(e)


class MMClock:
    """Wall-clock spent inside minorminer calls (the shared C++ machinery)."""
    def __init__(self):
        self.t = 0.0

    def find(self, *a, **kw):
        t0 = time.perf_counter()
        r = minorminer.find_embedding(*a, **kw)
        self.t += time.perf_counter() - t0
        return r


def centroids_of(chains, pos):
    return {v: np.mean([pos[q] for q in c], axis=0) for v, c in chains.items()}


def relax(cent, src_adj, eta=ETA):
    new = {}
    for v, p in cent.items():
        nbr = src_adj[v]
        if nbr:
            target = np.mean([cent[u] for u in nbr], axis=0)
            new[v] = p + eta * (target - p)
        else:
            new[v] = p
    return new


class DensityField:
    """v1 (notes §3.18): binned hardware capacity, measured from the layout —
    capacity[b] = number of working qubits whose drawing position falls in bin
    b (broken qubits simply don't count). Demand per centroid = lambda (current
    mean chain length). Centroids in overfull bins are pushed up to one bin
    toward the least-pressured neighbouring bin, scaled by the overflow."""

    def __init__(self, coords, B=16):
        self.B = B
        self.mins = coords.min(axis=0)
        span = coords.max(axis=0) - self.mins
        self.width = span / B
        self.cap = np.zeros((B, B))
        for xy in coords:
            i, j = self._bin(xy)
            self.cap[i, j] += 1

    def _bin(self, p):
        ij = np.clip(((p - self.mins) / self.width).astype(int), 0, self.B - 1)
        return int(ij[0]), int(ij[1])

    def _center(self, i, j):
        return self.mins + (np.array([i, j]) + 0.5) * self.width

    def push(self, cent, lam):
        count = np.zeros_like(self.cap)
        where = {}
        for v, p in cent.items():
            ij = self._bin(p)
            where[v] = ij
            count[ij] += 1
        with np.errstate(divide="ignore"):
            pressure = np.where(self.cap > 0, lam * count / np.maximum(self.cap, 1),
                                np.inf)
        new = {}
        for v, p in cent.items():
            i, j = where[v]
            pr = pressure[i, j]
            if pr <= 1.0:
                new[v] = p
                continue
            best, best_pr = (i, j), pr
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    a, b = i + di, j + dj
                    if 0 <= a < self.B and 0 <= b < self.B and pressure[a, b] < best_pr:
                        best, best_pr = (a, b), pressure[a, b]
            if best == (i, j):
                new[v] = p
            else:
                step = min(1.0, pr - 1.0)
                new[v] = p + step * (self._center(*best) - self._center(i, j))
        return new


def snap(cent, tree, qubits, degree_order):
    """Each variable (high degree first) claims the nearest unclaimed qubit."""
    claimed = set()
    seeds = {}
    for v in degree_order:
        k = 16
        while True:
            dists, idxs = tree.query(cent[v], k=min(k, len(qubits)))
            for i in np.atleast_1d(idxs):
                q = qubits[int(i)]
                if q not in claimed:
                    claimed.add(q)
                    seeds[v] = q
                    break
            if v in seeds:
                break
            if k >= len(qubits):
                raise RuntimeError("snap exhausted qubits")
            k *= 4
    return seeds


def run_loop(S, T_edges, src_adj, pos, tree, qubits, degree_order, adj, seed, clock,
             field=None):
    """R rounds of relax->[density push]->snap->route->prune."""
    traj, fails = [], 0
    best_emb, best_acl = None, float("inf")
    # round 0: unguided legalization to obtain initial geometry
    emb = clock.find(S, T_edges, random_seed=seed, timeout=60, chainlength_patience=0)
    cent, lam = None, 3.0
    if emb:
        emb = spur_prune(emb, src_adj, adj)
        a = acl(emb)
        traj.append(a)
        best_emb, best_acl = emb, a
        cent = centroids_of(emb, pos)
        lam = a
    else:
        fails += 1
        traj.append(None)
        cent = {v: pos[qubits[len(qubits) // 2]] for v in src_adj}  # degenerate start
    for r in range(1, ROUNDS + 1):
        cent = relax(cent, src_adj)
        if field is not None:
            cent = field.push(cent, lam)
        seeds = snap(cent, tree, qubits, degree_order)
        emb = clock.find(S, T_edges, random_seed=seed * 100 + r, timeout=60,
                         chainlength_patience=0,
                         initial_chains={v: [q] for v, q in seeds.items()})
        if not emb:
            fails += 1
            traj.append(None)
            continue  # keep current geometry, try again with fresh router seed
        emb = spur_prune(emb, src_adj, adj)
        a = acl(emb)
        traj.append(a)
        if a < best_acl:
            best_emb, best_acl = emb, a
        cent = centroids_of(emb, pos)  # realized geometry, congestion-deformed
        lam = a
    return best_emb, traj, fails


def run_control(S, T_edges, src_adj, adj, seed, clock):
    """R+1 unguided legalizations, keep best (same router budget as the loop)."""
    best_emb, best_acl, fails = None, float("inf"), 0
    for r in range(ROUNDS + 1):
        emb = clock.find(S, T_edges, random_seed=seed * 100 + r, timeout=60,
                         chainlength_patience=0)
        if not emb:
            fails += 1
            continue
        emb = spur_prune(emb, src_adj, adj)
        a = acl(emb)
        if a < best_acl:
            best_emb, best_acl = emb, a
    return best_emb, fails


def polish(S, T_edges, emb, seed, clock):
    out = clock.find(S, T_edges, random_seed=seed, timeout=300,
                     initial_chains=emb, skip_initialization=True)
    return out or None


def make_cell(n, target):
    d = 10.0 / (n - 1)
    src = nx.convert_node_labels_to_integers(nx.gnp_random_graph(n, d, seed=INSTANCE_SEED))
    S = list(src.edges())
    src_adj = {v: sorted(src.neighbors(v)) for v in src.nodes()}
    degree_order = sorted(src.nodes(), key=lambda v: -src.degree(v))
    return src, S, src_adj, degree_order


def main(smoke=False, v1=False):
    target = dnx.pegasus_graph(4 if smoke else 16)
    T_edges = list(target.edges())
    adj = build_adjacency(target)
    pos = dnx.pegasus_layout(target)
    qubits = sorted(pos)
    coords = np.array([pos[q] for q in qubits])
    tree = cKDTree(coords)
    field = DensityField(coords, B=4 if smoke else 16) if v1 else None
    csv_path = CSV_PATH.replace(".csv", "_v1.csv") if v1 else CSV_PATH
    loop_arm = "loop-v1" if v1 else "loop"

    if smoke:
        src, S, src_adj, degree_order = make_cell(30, target)
        clock = MMClock()
        best, traj, fails = run_loop(S, T_edges, src_adj, pos, tree, qubits,
                                     degree_order, adj, 0, clock, field=field)
        assert best and is_valid_embedding(best, src, target), "loop output invalid"
        pol = polish(S, T_edges, best, 0, clock)
        assert pol and is_valid_embedding(pol, src, target), "polished output invalid"
        print(f"smoke OK ({loop_arm}): traj={['%.2f' % t if t else 'F' for t in traj]} "
              f"polished acl={acl(pol):.2f} fails={fails}")
        return

    rows = []
    t_start = time.time()
    for n in NS:
        src, S, src_adj, degree_order = make_cell(n, target)
        for seed in SEEDS:
            if not v1:
                # mm-full baseline (v1 reuses v0's, same instances/seeds)
                clock = MMClock(); t0 = time.perf_counter()
                emb = clock.find(S, T_edges, random_seed=seed, timeout=300)
                rows.append(dict(n=n, seed=seed, arm="mm-full",
                                 final_acl=round(acl(emb), 3) if emb else None,
                                 total_time=round(time.perf_counter() - t0, 2),
                                 mm_time=round(clock.t, 2), fails=0 if emb else 1,
                                 trajectory=""))
            # loop
            clock = MMClock(); t0 = time.perf_counter()
            best, traj, fails = run_loop(S, T_edges, src_adj, pos, tree, qubits,
                                         degree_order, adj, seed, clock, field=field)
            pol = polish(S, T_edges, best, seed, clock) if best else None
            rows.append(dict(n=n, seed=seed, arm=loop_arm,
                             final_acl=round(acl(pol), 3) if pol else None,
                             total_time=round(time.perf_counter() - t0, 2),
                             mm_time=round(clock.t, 2), fails=fails,
                             trajectory=";".join("%.3f" % t if t else "F" for t in traj)))
            if not v1:
                # restart-control
                clock = MMClock(); t0 = time.perf_counter()
                best, fails = run_control(S, T_edges, src_adj, adj, seed, clock)
                pol = polish(S, T_edges, best, seed, clock) if best else None
                rows.append(dict(n=n, seed=seed, arm="control",
                                 final_acl=round(acl(pol), 3) if pol else None,
                                 total_time=round(time.perf_counter() - t0, 2),
                                 mm_time=round(clock.t, 2), fails=fails,
                                 trajectory=""))
        print(f"[{time.time()-t_start:5.0f}s] n={n} done", flush=True)

    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {csv_path}\n")

    # ── summary ───────────────────────────────────────────────────────────────
    arms = (loop_arm,) if v1 else ("mm-full", "loop", "control")
    for n in NS:
        print(f"n={n}")
        for arm in arms:
            rs = [r for r in rows if r["n"] == n and r["arm"] == arm]
            ok = [r for r in rs if r["final_acl"]]
            if ok:
                m = sum(r["final_acl"] for r in ok) / len(ok)
                t = sum(r["total_time"] for r in ok) / len(ok)
                mt = sum(r["mm_time"] for r in ok) / len(ok)
                print(f"  {arm:8s}: ACL {m:6.3f}  time {t:6.1f}s "
                      f"(mm {mt:5.1f}s, glue {t-mt:4.1f}s)  ok {len(ok)}/{len(rs)}")
        # mean trajectory across seeds (loop arm)
        trajs = [[float(x) if x != "F" else None for x in r["trajectory"].split(";")]
                 for r in rows if r["n"] == n and r["arm"] == loop_arm and r["trajectory"]]
        if trajs:
            L = max(len(t) for t in trajs)
            means = []
            for i in range(L):
                vals = [t[i] for t in trajs if i < len(t) and t[i] is not None]
                means.append(sum(vals) / len(vals) if vals else float("nan"))
            print("  loop legal-ACL trajectory (mean per round): "
                  + " ".join("%.2f" % m for m in means))


if __name__ == "__main__":
    main(smoke="--smoke" in sys.argv, v1="--v1" in sys.argv)
