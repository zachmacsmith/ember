"""
docs/paper2/data/template_bounds_z12.py
========================================
Template-restriction bounds for the s3.58 full-Z12 sweep: for every
manifest graph with n <= 184 (Z12 K_max), the busclique K_n template
relabeled degree-descending and spur-pruned to the source's edges — the
zephyr_triad Part-2 protocol at dataset scale. Valid by construction
(every chain pair in a clique template is coupled; pruning preserves
coverage). Graphs with n > 184 have NO template — that column is the
algorithm's home turf, not a gap.

Output: template_bounds_z12.csv (gid, name, category, n, e, tmpl_acl,
prune_s). Constructive and wall-clock-insensitive: safe to run on a
loaded box at nice 10.

Run:  nohup .venv/bin/python docs/paper2/data/template_bounds_z12.py \
        > docs/paper2/data/template_bounds_z12.log 2>&1 &
"""
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "template_bounds_z12.csv")
KMAX = 184

_shared = {}


def _init():
    import dwave_networkx as dnx
    from minorminer import busclique
    Z = dnx.zephyr_graph(12, 4)
    _shared["adj"] = {q: set(Z[q]) for q in Z.nodes()}
    bc = busclique.busgraph_cache(Z)
    _shared["bc"] = bc


def _run(gid):
    import networkx as nx
    from ember_qc.load_graphs import load_graph
    from ember_qc.algorithms.factored.polish import spur_prune
    try:
        src = nx.convert_node_labels_to_integers(load_graph(gid))
        n = src.number_of_nodes()
        if n < 2 or n > KMAX:
            return None
        t0 = time.perf_counter()
        raw = _shared["bc"].find_clique_embedding(n)
        if not raw:
            return None
        order = sorted(src.nodes(), key=lambda v: (-src.degree(v), v))
        chains = {v: list(raw[i]) for i, v in enumerate(order)}
        src_adj = {v: sorted(src.neighbors(v)) for v in src.nodes()}
        pruned = spur_prune(chains, src_adj, _shared["adj"],
                            deadline=time.perf_counter() + 20)
        acl = sum(len(c) for c in pruned.values()) / len(pruned)
        return dict(gid=gid, n=n, e=src.number_of_edges(),
                    tmpl_acl=round(acl, 3),
                    prune_s=round(time.perf_counter() - t0, 2))
    except Exception as exc:
        return dict(gid=gid, n=-1, e=-1, tmpl_acl=None,
                    prune_s=None, err=str(exc)[:80])


def main():
    os.nice(10)
    from ember_qc.load_graphs import _manifest_by_id
    man = _manifest_by_id()
    todo = sorted(gid for gid, e in man.items()
                  if 2 <= int(e.get("n", e.get("nodes", 0))) <= KMAX)
    print(f"{len(todo)} graphs with n <= {KMAX}", flush=True)
    done = set()
    if os.path.exists(OUT):
        with open(OUT) as fh:
            done = {int(r["gid"]) for r in csv.DictReader(fh)}
        print(f"resuming: {len(done)} already done", flush=True)
    todo = [g for g in todo if g not in done]

    mode = "a" if done else "w"
    fields = ["gid", "n", "e", "tmpl_acl", "prune_s", "err"]
    with open(OUT, mode, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if not done:
            w.writeheader()
        count = 0
        with ProcessPoolExecutor(max_workers=10, initializer=_init) as ex:
            for row in ex.map(_run, todo, chunksize=8):
                if row is None:
                    continue
                w.writerow({k: row.get(k) for k in fields})
                count += 1
                if count % 500 == 0:
                    fh.flush()
                    print(f"{count}/{len(todo)}", flush=True)
    print("done-template-bounds", flush=True)


if __name__ == "__main__":
    main()
