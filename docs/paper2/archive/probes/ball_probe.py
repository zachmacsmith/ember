"""
docs/paper2/data/ball_probe.py
==============================
Stage-0 ball polish (2026-08-08 build round): does composite whole-chain
re-embedding beat minorminer's warm-started grind at equal seconds, on
the SAME finished embeddings?

Per (cell, fabric, input_arm, seed), ONE job: build a finished embedding
(input_arm "stock" = stock minorminer 60 s; "attract" = the shipped
attraction pipeline 60 s), then run BOTH polish arms on that identical
embedding in-process:
  - ball : ball_polish, 30 s deadline (deterministic, strict descent)
  - grind: warm-started stock mm (initial_chains + skip_initialization),
           30 s, validity-guarded fallback to the input
Note the grind arm on the attract input is a MARGINAL comparison by
design — attraction's finish stage already ground once at 60 s; the
question is what the next 30 s buys under each polish. The stock input
arm passes the source as a graph object (edge lists drop isolated
vertices; board cells are connected but the convention stands).

Interesting outcome (no bar liturgy): ball beats grind on the lattice
cells (grid/honeycomb/king) without losing elsewhere; any P16 movement
is the first from a mechanism that is fabric-agnostic by construction.
ball_wall is recorded separately — ball may reach its fixpoint before
30 s while the grind always burns the full budget.

Run:  nohup .venv/bin/python docs/paper2/data/ball_probe.py \
        > docs/paper2/data/ball_probe.log 2>&1 &
Smoke: add `smoke` argv. Sentinel: done-probe.
"""
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ball_probe.csv")
SEEDS = (0, 1, 2)
TIMEOUT = 60
POLISH = 30
INPUT_ARMS = ("stock", "attract")

BOARD = [
    ("K100", "Z12", None), ("K140", "Z12", None),
    ("ER100_d10", "Z12", None),
    ("turan_n162", "Z12", 2647), ("spin_glass_n163", "Z12", 37309),
    ("regular_n316", "Z12", 13096), ("ws_n486", "Z12", 17188),
    ("grid_200", "Z12", 1590), ("honeycomb_200", "Z12", 32393),
    ("king_graph_196", "Z12", 32622),
    ("K100", "P16", None), ("turan_n162", "P16", 2647),
    ("ws_n486", "P16", 17188),
]


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def _stats(emb):
    if not emb:
        return None, None
    acl = round(sum(len(c) for c in emb.values()) / len(emb), 3)
    return acl, max(len(c) for c in emb.values())


def _run(job):
    cell, fabric, gid, input_arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    import minorminer
    from ember_qc.algorithms.factored import attract_embed, ball_polish
    from ember_qc.embedding_backend import build_adjacency, is_valid_embedding

    src = _load(cell, gid)
    target = (dnx.zephyr_graph(12, 4) if fabric == "Z12"
              else dnx.pegasus_graph(16))
    t0 = time.perf_counter()

    if input_arm == "stock":
        emb = minorminer.find_embedding(
            src, list(target.edges()), random_seed=seed,
            timeout=TIMEOUT) or {}
    else:
        emb = attract_embed(src, target, timeout=TIMEOUT,
                            seed=seed).get("embedding") or {}
    emb = {int(v): sorted(int(q) for q in c) for v, c in emb.items()}
    adj = build_adjacency(target)
    if not emb or not is_valid_embedding(emb, src, target, adj=adj):
        return dict(cell=cell, fabric=fabric, gid=gid, input_arm=input_arm,
                    seed=seed, input_acl=None, input_max=None,
                    ball_acl=None, ball_max=None, ball_tried=None,
                    ball_accepted=None, ball_sweeps=None, ball_wall=None,
                    grind_acl=None, grind_max=None, grind_wall=None,
                    wall=round(time.perf_counter() - t0, 1))
    input_acl, input_max = _stats(emb)

    b0 = time.perf_counter()
    ball_emb, info = ball_polish(emb, src, target,
                                 deadline=b0 + POLISH, adj=adj)
    ball_acl, ball_max = _stats(ball_emb)

    g0 = time.perf_counter()
    grind = minorminer.find_embedding(
        src, list(target.edges()), random_seed=seed, timeout=POLISH,
        initial_chains=emb, skip_initialization=True) or emb
    if not is_valid_embedding(grind, src, target, adj=adj):
        grind = emb
    grind_wall = round(time.perf_counter() - g0, 1)
    grind_acl, grind_max = _stats(grind)

    return dict(cell=cell, fabric=fabric, gid=gid, input_arm=input_arm,
                seed=seed, input_acl=input_acl, input_max=input_max,
                ball_acl=ball_acl, ball_max=ball_max,
                ball_tried=info["tried"], ball_accepted=info["accepted"],
                ball_sweeps=info["sweeps"],
                ball_wall=round(info["wall"], 1),
                grind_acl=grind_acl, grind_max=grind_max,
                grind_wall=grind_wall,
                wall=round(time.perf_counter() - t0, 1))


def main():
    smoke = "smoke" in sys.argv
    cells = list(BOARD)
    if smoke:
        cells = [c for c in cells
                 if c[0] in ("honeycomb_200", "turan_n162") and c[1] == "Z12"]
    seeds = SEEDS[:1] if smoke else SEEDS
    print(f"{len(cells)} cells x {len(INPUT_ARMS)} inputs x {len(seeds)} "
          f"seeds; load {os.getloadavg()}", flush=True)
    jobs = [(c, f, g, ia, s) for c, f, g in cells
            for ia in INPUT_ARMS for s in seeds]
    rows = []
    with ProcessPoolExecutor(max_workers=24) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['fabric']} {row['cell']:<18} {row['input_arm']:<8} "
                  f"seed {row['seed']}: in={row['input_acl']} "
                  f"ball={row['ball_acl']} (acc {row['ball_accepted']}/"
                  f"{row['ball_tried']}, {row['ball_wall']}s) "
                  f"grind={row['grind_acl']} ({row['grind_wall']}s)",
                  flush=True)
            rows.append(row)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    print("\nsummary (mean ACL; d = ball - grind, negative = ball wins):")
    for cell, fabric, _ in cells:
        for ia in INPUT_ARMS:
            sel = [r for r in rows if r["cell"] == cell
                   and r["fabric"] == fabric and r["input_arm"] == ia
                   and r["input_acl"] is not None]
            if not sel:
                print(f"{fabric} {cell:<18} {ia:<8} no legal inputs")
                continue
            mi = mean([r["input_acl"] for r in sel])
            mb = mean([r["ball_acl"] for r in sel])
            mg = mean([r["grind_acl"] for r in sel])
            acc = mean([r["ball_accepted"] for r in sel])
            bw = mean([r["ball_wall"] for r in sel])
            d = round(mb - mg, 3) if (mb is not None and mg is not None) \
                else None
            print(f"{fabric} {cell:<18} {ia:<8} in={mi} ball={mb} "
                  f"grind={mg} d={d:+.3f} acc={acc} ball_wall={bw}s"
                  if d is not None else
                  f"{fabric} {cell:<18} {ia:<8} in={mi} ball={mb} "
                  f"grind={mg}")
    print("load at end:", os.getloadavg(), flush=True)
    print("done-probe", flush=True)


if __name__ == "__main__":
    main()
