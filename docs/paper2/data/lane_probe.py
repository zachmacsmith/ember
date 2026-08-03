"""
docs/paper2/data/lane_probe.py
===============================
Max's simplification probe (2026-08-01, after the s3.50 fragmentation
dissection): "see what happens if we ignore all this silly coloring
stuff — the coloring is polish on a layout that should already be
working; mostly an artifact of Pegasus; Zephyr should let us have a
simpler algorithm so we can know the main components are working."

Arms, sharing IDENTICAL geometry (course grid, stair_step + arrange +
derived bars — the pipeline's own stages; only the CLAIM layer differs):

- iv    : wire_seeds_iv (interval coloring), the registered claim layer.
- lane  : whole-lane seeder — per axis, per line, count to the line's
          lane capacity (8 on Zephyr course grids), spill to the nearest
          line with a free lane, claim the arm's full interval on a lane
          the variable owns outright. No interval graph, no coloring,
          no sharing. ~25 lines.

Routed protocol: patience-0 seeded legalization (25 s) + spur_prune +
warm polish (rest of 60 s), 3 routing seeds; geometry is deterministic.
Diagnostics per run: wires/chain (fragmentation) and per-orientation
line-bundle width of the final embedding.

Expectation on record (from the s3.50 dissection): if fragmentation and
the bundle bloat are the claim layer's fault, lane pulls turan toward
the ~6+overhead arithmetic and kills the wires/chain ~1.8 tail; if the
numbers do not move, the defect is upstream in arrange's line
assignment, not in claiming.

Run:  nohup .venv/bin/python docs/paper2/data/lane_probe.py \
        > docs/paper2/data/lane_probe.log 2>&1 &
"""
import math
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

SEEDS = (0, 1, 2)
TIMEOUT = 60
CELLS = {"K100": None, "K140": None,
         "turan_n162": 2647, "spin_glass_n163": 37309}


def _load(name, gid):
    import networkx as nx
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(gid))


def lane_seeds(grid, pos, bars):
    """Whole-lane claims: one variable, one wire, count-to-capacity,
    spill to the nearest line. Zephyr-course simple case of seeding."""
    from ember_qc.algorithms.factored.field import _ensure_seeds
    claimed, chains = set(), {v: [] for v in pos}
    for o in (1, 0):
        tuples = []
        for v in sorted(pos):
            h_iv, v_iv = bars[v]
            iv = h_iv if o == 1 else v_iv
            if float(iv[1] - iv[0]) < 1.0:
                continue
            line = int(round(float(pos[v][1] if o == 1 else pos[v][0])))
            tuples.append((line, float(iv[0]), float(iv[1]), v))
        subs_by_line = defaultdict(list)
        for (u, ln, s) in grid.wire_map:
            if u == o:
                subs_by_line[ln].append(s)
        for ln in subs_by_line:
            subs_by_line[ln].sort()
        used = {ln: 0 for ln in subs_by_line}
        for line, a, b, v in sorted(tuples):
            home = None
            for ln in sorted(subs_by_line,
                             key=lambda l: (abs(l - line), l)):
                if used[ln] < len(subs_by_line[ln]):
                    home = ln
                    break
            if home is None:
                continue  # fabric full; point-seeded by _ensure_seeds
            sub = subs_by_line[home][used[home]]
            used[home] += 1
            run = grid.wire_map.get((o, home, sub), {})
            for t in range(int(math.floor(a)), int(math.ceil(b)) + 1):
                q = run.get(t)
                if q is not None and q not in claimed:
                    claimed.add(q)
                    chains[v].append(q)
    _ensure_seeds(grid, claimed, chains, pos)
    return {v: c for v, c in chains.items() if c}


def _run(job):
    cell, gid, arm, seed = job
    os.nice(10)
    import dwave_networkx as dnx
    import numpy as np
    from ember_qc.algorithms.factored.field import (
        TileGrid, _target_kappa, alternate_arrange, derive_bars_stair,
        stair_step, wire_seeds_iv)
    from ember_qc.algorithms.factored.placement import (
        _mm_route, source_positions, target_layout)
    from ember_qc.algorithms.factored.polish import spur_prune
    from ember_qc.registry import validate_embedding

    src = _load(cell, gid)
    Z = dnx.zephyr_graph(12, 4)
    src_adj = {v: sorted(src.neighbors(v)) for v in src.nodes()}
    adj = {q: set(Z[q]) for q in Z.nodes()}
    pos_t = target_layout(Z)
    grid = TileGrid(Z, pos_t, courses=True)
    coords = np.array([pos_t[q] for q in sorted(pos_t)])
    lo, hi = coords.min(axis=0), coords.max(axis=0)
    kappa = _target_kappa(grid)

    t0 = time.perf_counter()
    cent = source_positions(src, lo, hi)
    tpts = {v: grid.to_tile(p) for v, p in cent.items()}
    tpts = stair_step(tpts, src_adj, eta=0.5)
    tpts, _ = alternate_arrange(tpts, src_adj, grid, iters=8, kappa=kappa,
                                insert_sweeps=8)
    bars = derive_bars_stair(tpts, src_adj, kappa=kappa,
                             bounds=(grid.W, grid.H))
    seeds = (lane_seeds(grid, tpts, bars) if arm == "lane"
             else wire_seeds_iv(grid, tpts, bars))

    legal = _mm_route(src, Z, chains=seeds, seed=seed, timeout=25)
    if not legal:
        return dict(cell=cell, arm=arm, seed=seed, final_acl=None,
                    frag=None, vlines=None,
                    time=round(time.perf_counter() - t0, 1))
    pruned = spur_prune(legal, src_adj, adj)
    rest = max(5.0, TIMEOUT - (time.perf_counter() - t0))
    polished = _mm_route(src, Z, warm=pruned, seed=seed, timeout=rest)
    final = polished if (polished and
                         validate_embedding(polished, src, Z)) else pruned
    acl = round(sum(len(c) for c in final.values()) / len(final), 3)

    conv = dnx.zephyr_coordinates(12, 4)
    C = {q: conv.linear_to_zephyr(q) for q in Z}
    wire = lambda q: (C[q][0], C[q][1], 2 * C[q][2] + C[q][3])
    frag = sum(len({wire(q) for q in c}) for c in final.values()) / len(final)
    vlines = len({C[q][1] for c in final.values()
                  for q in c if C[q][0] == 0})
    return dict(cell=cell, arm=arm, seed=seed, final_acl=acl,
                frag=round(frag, 2), vlines=vlines,
                time=round(time.perf_counter() - t0, 1))


def main():
    jobs = [(c, g, arm, s) for c, g in CELLS.items()
            for arm in ("iv", "lane") for s in SEEDS]
    rows = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']} {row['arm']} seed {row['seed']}: "
                  f"{row['final_acl']} frag={row['frag']} "
                  f"vlines={row['vlines']} ({row['time']}s)", flush=True)
            rows.append(row)

    print("\nsummary (ACL mean over legal seeds (n) | wires/chain | "
          "v-line bundle width):")
    for cell in CELLS:
        parts = [f"{cell:16s}"]
        for arm in ("iv", "lane"):
            sel = [r for r in rows if r["cell"] == cell and r["arm"] == arm
                   and r["final_acl"]]
            if sel:
                parts.append(
                    f"{arm}={sum(r['final_acl'] for r in sel)/len(sel):.2f}"
                    f"({len(sel)}) f{sum(r['frag'] for r in sel)/len(sel):.2f}"
                    f" v{sum(r['vlines'] for r in sel)/len(sel):.0f}")
            else:
                parts.append(f"{arm}=FAIL(0)")
        print("  ".join(parts))
    print("done-lane-probe", flush=True)


if __name__ == "__main__":
    main()
