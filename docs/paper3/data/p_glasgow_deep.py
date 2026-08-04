"""§4.17 PROBE P: can a longer Glasgow budget hit the big-honeycomb
near-subgraphs?

The seven §4.16 honeycomb flip graphs (n=1870-2318; MM embeds them at ACL
1.2-1.6 in 15-56 s) x find_subgraph solver timeouts {5, 10, 20} s (stock pip
minorminer, parallel=False, seed 0), each hit validated as an embedding with
all chains length 1. Pre-registered decision tree (notes §4.17): T* = the
smallest timeout with >= 5/7 validated hits -> build p3-ember2's deep tier
with that T*; no timeout reaches 5/7 -> p3-ember2 is not built.

Run: .venv/bin/python docs/paper3/data/p_glasgow_deep.py
(sequential by design — walls are the measurement; ~<= 9 min worst case)
"""
from __future__ import annotations

import time

GIDS = (32426, 32432, 32442, 32447, 32472, 32475, 32502)
TIMEOUTS = (5, 10, 20)


def main() -> None:
    import dwave_networkx as dnx
    from minorminer.subgraph import find_subgraph
    from ember_qc.load_graphs import load_graph
    from ember_qc.embedding_backend import is_valid_embedding

    tgt = dnx.zephyr_graph(12)
    srcs = {gid: load_graph(gid) for gid in GIDS}
    hits = {t: 0 for t in TIMEOUTS}
    for t in TIMEOUTS:
        for gid in GIDS:
            src = srcs[gid]
            t0 = time.perf_counter()
            raw = find_subgraph(src, tgt, timeout=t, parallel=False, seed=0)
            wall = time.perf_counter() - t0
            ok = False
            if raw:
                emb = {v: [int(q)] for v, q in raw.items()}
                ok = (is_valid_embedding(emb, src, tgt)
                      and all(len(c) == 1 for c in emb.values()))
            hits[t] += ok
            print(f"t={t:2d}s gid={gid} n={src.number_of_nodes():4d} "
                  f"wall={wall:6.2f}s hit={ok}", flush=True)
        print(f"-- timeout {t}s: {hits[t]}/{len(GIDS)} validated hits",
              flush=True)
    tstar = next((t for t in TIMEOUTS if hits[t] >= 5), None)
    print(f"\nPROBE VERDICT: T* = {tstar} "
          f"({'BUILD p3-ember2' if tstar else 'DO NOT BUILD p3-ember2'})")
    print("P_GLASGOW_DEEP_DONE")


if __name__ == "__main__":
    main()
