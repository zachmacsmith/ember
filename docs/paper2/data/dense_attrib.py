"""
docs/paper2/data/dense_attrib.py
=================================
Dense-regime attribution probe (notes §3.26 when analyzed): WHY does attraction
trail stock minorminer on dense-but-comfortable instances (§3.25: K100 14.50 vs
13.44)? Pre-registered decision tree:

  arm 'budget'   = attraction with max_rounds=1, round_frac=0.1 — one cheap
                   seeded legalization, ~90% of the budget to the polish.
                   If budget ≈ mm-full: the deficit was our rounds/polish
                   budget split, not geometry. If budget >> mm-full: our seeds
                   actively hurt dense dynamics (§3.10 anti-placement).
  arm 'template' = busclique K_n chains restricted to the source's edges
                   (spur-pruned), raw and then warm-polished by stock MM.
                   If template+polish << mm-full: ALL search methods (stock
                   included) sit far above the constructive optimum on dense
                   sources — the dense fix is a template prior in the
                   placement layer, and "beating mm on dense" is very much on
                   the table. If template+polish ≈ mm-full: search is already
                   near the ceiling and the residual is real representation
                   loss.

Cells: K60/K100/K140 (clique ladder toward the cliff) + bipartite_K48_96
(dense non-clique loss case from §3.23). 3 seeds, P16, 60 s.

Run:  .venv/bin/python docs/paper2/data/dense_attrib.py
"""

import csv
import os
import time

import networkx as nx
import dwave_networkx as dnx
import minorminer
from minorminer import busclique

from ember_qc.load_graphs import load_graph
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
from ember_qc.algorithms.factored import attract_embed
from ember_qc.algorithms.factored.polish import spur_prune

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "dense_attrib.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60

acl = lambda e: sum(len(c) for c in e.values()) / len(e)


def cells():
    yield "K60", nx.complete_graph(60)
    yield "K100", nx.complete_graph(100)
    yield "K140", nx.complete_graph(140)
    yield "biK48_96", nx.convert_node_labels_to_integers(load_graph(1350))


def template_embedding(src, target, adj):
    """busclique K_n chains restricted to src's edges, spur-pruned."""
    n = src.number_of_nodes()
    raw = busclique.find_clique_embedding(n, target)
    emb = {int(v): list(map(int, raw[v])) for v in range(n)}
    src_adj = {v: sorted(src.neighbors(v)) for v in src.nodes()}
    return spur_prune(emb, src_adj, adj)


def main():
    target = dnx.pegasus_graph(16)
    T_edges = list(target.edges())
    adj = build_adjacency(target)
    rows = []
    for name, src in cells():
        # template: deterministic construction, then per-seed warm polish
        tmpl = template_embedding(src, target, adj)
        assert is_valid_embedding(tmpl, src, target), f"template invalid: {name}"
        rows.append(dict(cell=name, arm="template-raw", seed=-1,
                         final_acl=round(acl(tmpl), 3), time=0.0))
        for s in SEEDS:
            t0 = time.perf_counter()
            pol = minorminer.find_embedding(
                src, T_edges, initial_chains=tmpl, skip_initialization=True,
                random_seed=s, timeout=TIMEOUT)
            rows.append(dict(cell=name, arm="template-polish", seed=s,
                             final_acl=round(acl(pol), 3) if pol else None,
                             time=round(time.perf_counter() - t0, 1)))

            t0 = time.perf_counter()
            r = attract_embed(src, target, timeout=TIMEOUT, seed=s)
            rows.append(dict(cell=name, arm="poisson", seed=s,
                             final_acl=round(acl(r["embedding"]), 3)
                             if r["embedding"] else None,
                             time=round(time.perf_counter() - t0, 1)))

            t0 = time.perf_counter()
            r = attract_embed(src, target, timeout=TIMEOUT, seed=s,
                              max_rounds=1, round_frac=0.1)
            rows.append(dict(cell=name, arm="budget", seed=s,
                             final_acl=round(acl(r["embedding"]), 3)
                             if r["embedding"] else None,
                             time=round(time.perf_counter() - t0, 1)))

            t0 = time.perf_counter()
            emb = minorminer.find_embedding(src, T_edges, random_seed=s,
                                            timeout=TIMEOUT)
            rows.append(dict(cell=name, arm="mm-full", seed=s,
                             final_acl=round(acl(emb), 3) if emb else None,
                             time=round(time.perf_counter() - t0, 1)))
            print(f"{name} seed {s} done", flush=True)

    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}")

    for name, _ in cells():
        parts = [f"{name:9s}"]
        for arm in ("template-raw", "template-polish", "poisson", "budget",
                    "mm-full"):
            ok = [r["final_acl"] for r in rows
                  if r["cell"] == name and r["arm"] == arm and r["final_acl"]]
            parts.append(f"{arm}={sum(ok)/len(ok):.2f}" if ok else f"{arm}=fail")
        print("  ".join(parts))


if __name__ == "__main__":
    main()
