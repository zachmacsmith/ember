"""
docs/paper2/data/ballbar_probe.py
=================================
Ball v2 (2026-08-10): bar-based rebuild vs the router, three arms on
identical stock-mm inputs. bars = the pipeline's constructor family
(straight arms colored against the frozen world with require_free,
stride-gated completion via only=S); router = the original sph_tree
Steiner build; bars+fallback = bars first, router on reject. Sanity
(n=1, 20 s): bars propose ~30x faster but with weaker candidates on
Z12; bars-only rejects everything on stride-1 (no completion; corner
connectivity is a ~56% junction coin on Pegasus) — this probe decides
the default arm with real budgets.

Run:  nohup .venv/bin/python docs/paper2/data/ballbar_probe.py \
        > docs/paper2/data/ballbar_probe.log 2>&1 &
Smoke: add `smoke` argv. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ballbar_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
POLISH = 30
ARMS = ("router", "bars", "bars+fallback")

BOARD = [
    ("turan_n162", "Z12", 2647), ("K140", "Z12", None),
    ("spin_glass_n163", "Z12", 37309),
    ("honeycomb_200", "Z12", 32393), ("king_graph_196", "Z12", 32622),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
]


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _run(job):
    cell, fabric, gid, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    import minorminer
    from ember_qc.algorithms.factored import ball_polish
    from ember_qc.embedding_backend import build_adjacency, is_valid_embedding
    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    t0 = time.perf_counter()
    emb = minorminer.find_embedding(src, list(target.edges()),
                                    random_seed=seed, timeout=TIMEOUT) or {}
    emb = {int(v): sorted(int(q) for q in c) for v, c in emb.items()}
    adj = build_adjacency(target)
    row = dict(cell=cell, fabric=fabric, gid=gid, seed=seed,
               input_acl=None)
    if not emb or not is_valid_embedding(emb, src, target, adj=adj):
        row["wall"] = round(time.perf_counter() - t0, 1)
        return row
    row["input_acl"] = round(sum(len(c) for c in emb.values()) / len(emb), 3)
    for arm in ARMS:
        b0 = time.perf_counter()
        out, info = ball_polish(emb, src, target, deadline=b0 + POLISH,
                                adj=adj, rebuild=arm)
        key = arm.replace("+", "_")
        row[f"{key}_acl"] = round(sum(len(c) for c in out.values())
                                  / len(out), 3)
        row[f"{key}_acc"] = info["accepted"]
        row[f"{key}_tried"] = info["tried"]
        row[f"{key}_wall"] = round(info["wall"], 1)
    row["wall"] = round(time.perf_counter() - t0, 1)
    return row


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD)
    if smoke:
        cells = [c for c in cells if c[0] == "turan_n162" and c[1] == "Z12"]
    seeds = SEEDS[:1] if smoke else SEEDS
    jobs = [(c, f, g, s) for c, f, g in cells for s in seeds]
    print(f"{len(cells)} cells x {len(seeds)} seeds (3 arms in-job); "
          f"load {os.getloadavg()}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} seed {row['seed']}: "
                  f"in={row.get('input_acl')} "
                  f"r={row.get('router_acl')}({row.get('router_acc')}) "
                  f"b={row.get('bars_acl')}({row.get('bars_acc')}/"
                  f"{row.get('bars_tried')}) "
                  f"bf={row.get('bars_fallback_acl')}"
                  f"({row.get('bars_fallback_acc')})", flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    print("\nsummary (mean ACL by arm; lower wins):")
    for cell, fabric, _ in cells:
        sel = [r for r in rows if r["cell"] == cell and r["fabric"] == fabric
               and r.get("input_acl") is not None]
        if not sel:
            continue
        parts = [f"{fabric} {cell:<18} in={mean([r['input_acl'] for r in sel])}"]
        for arm in ARMS:
            key = arm.replace("+", "_")
            parts.append(f"{arm}={mean([r.get(f'{key}_acl') for r in sel])}"
                         f"(acc {mean([r.get(f'{key}_acc') for r in sel])})")
        print("  ".join(parts))
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
