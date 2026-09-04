"""brick_gate.py — the s3.107 falsification gate (Phase A; verdict: s3.108).

Claim under test (notes s3.107): the stalled turán seat state's
infeasibility (73 deficits) is INVISIBLE to the plane at junction
resolution and must become VISIBLE as cover overload at BRICK
resolution (1 brick = grid.stride = 2 junctions = one qubit-length),
while the orders crystal (0 deficits) stays clean.

Measured verdict (2026-08-24): the PREMISE is refuted. Two censuses:

1. raw `_arms` census (what seat_energy's cover uses): at brick
   resolution BOTH states show cover-16 bricks (crystal hinge2 514,
   stalled 521 — no separation). Breakdown traced every cover-16 cell
   to PHANTOM POINT ARMS: `_arms` seeds each side's interval with the
   variable's own coordinate, so a variable with no contacts on that
   side still deposits cover 1. Stacks of 8 co-located variables put
   8 phantom points per junction; at brick resolution two adjacent
   stacks merge to 16. Under the stair rule an edge consumes u's
   h-arm and v's v-arm only — an empty side demands no bar.

2. demand-honest census (empty sides excluded): the crystal is
   completely clean at BOTH resolutions (junction 0, brick 0); the
   stalled state is visibly overloaded at BOTH (junction hinge2 11,
   brick 6 — v-line 2 at depth 9 > pool 8 along its whole length).
   The doom is visible at junction resolution already; the brick
   ruler adds nothing for this failure mode.

Decomposition (as-shipped seat_energy, lam=1): crystal stair 1766 /
pen 0; stalled stair 1693 / pen 11. The shipped objective already
SEES the stalled state's infeasibility — it is outvoted: Delta-stair
73 vs Delta-pen 11, endpoint ordering flips at lam > 73/11 ~ 6.6.

States: the exact s3.106 autopsy specimens (deterministic, no RNG).

Run:  cd /data/max/ember && .venv/bin/python docs/paper2/data/brick_gate.py
Sentinel: done-gate.
"""

import numpy as np
import networkx as nx
import dwave_networkx as dnx

from ember_qc.load_graphs import load_graph
from ember_qc.algorithms.factored.field import (
    TileGrid, alternate_arrange, _target_kappa, _stair_contacts,
    stair_energy, line_pools)
from ember_qc.algorithms.factored.placement import target_layout
from ember_qc.algorithms.factored import seat as S
from ember_qc.algorithms.factored.coarsen import coarsen


def build_states():
    z = dnx.zephyr_graph(12, 4)
    grid = TileGrid(z, target_layout(z), courses=True)
    kappa = _target_kappa(grid)
    src = nx.convert_node_labels_to_integers(load_graph(2647))
    adj = {v: sorted(src.neighbors(v)) for v in src}
    levels = coarsen(adj, units=True)
    groups = []
    mem = {v: [v] for v in levels[0].adj}
    for li in range(1, len(levels)):
        up = {}
        for c, ms in mem.items():
            up.setdefault(levels[li].parent_of[c], []).extend(ms)
        mem = up
        g = [sorted(ms) for ms in up.values() if len(ms) > 1]
        if g:
            groups.append(g)
    unit_lists = []
    for level in reversed(groups):
        for cl in sorted(level, key=lambda g: (-len(g), g)):
            if len(cl) >= 2:
                unit_lists.append(sorted(cl))
    p0 = {v: np.array([float(i), float(i)])
          for i, v in enumerate(sorted(src))}

    stalled, _ = alternate_arrange(
        {v: p.copy() for v, p in p0.items()}, adj, grid,
        iters=1, kappa=kappa, snap=True, overload_lam=1.0)
    e_cur = S.seat_energy(stalled, adj, grid, lam=1.0)
    info = {"gather_accepts": 0}
    for _ in range(3):
        acc = 0
        for cl in unit_lists:
            r = S.best_gather(cl, stalled, adj, grid, lam=1.0,
                              e_cur=e_cur, info=info)
            if r is not None:
                stalled, e_cur = r
                acc += 1
        if acc == 0:
            break

    crystal, _ = alternate_arrange(
        {v: p.copy() for v, p in p0.items()}, adj, grid,
        iters=8, kappa=kappa, snap=True, overload_lam=1.0,
        cluster_groups=groups)
    return grid, adj, crystal, stalled


def _pools(grid):
    s, W, H = grid.stride, grid.W, grid.H
    Wb = (W + s - 1) // s
    # true per-brick pools from wire_map (dead qubits and the phantom
    # over-allocated column self-absorb: no bars there -> 0)
    poolb_h = np.zeros((H, Wb))
    poolb_v = np.zeros((W, Wb))
    for (o, ln, sub), d in grid.wire_map.items():
        A = poolb_h if o == 1 else poolb_v
        for t in d:
            A[ln, t // s] += 1.0
    # as-priced per-line pools (seat_energy broadcasts these)
    lp = line_pools(grid)
    lp_h = np.zeros(H)
    lp_v = np.zeros(W)
    for (o, ln), p in lp.items():
        if o == 1 and 0 <= ln < H:
            lp_h[ln] = p
        elif o == 0 and 0 <= ln < W:
            lp_v[ln] = p
    return poolb_h, poolb_v, lp_h, lp_v


def _stats(C, pool):
    over = np.maximum(C - pool, 0.0)
    return int(C.max()), int((over > 0).sum()), float((over * over).sum())


def census(grid, adj, pos, tag, *, honest):
    """Cover census at junction and brick resolution.

    honest=False: raw `_arms` intervals (what seat_energy uses),
    including the phantom own-coordinate seed on contact-free sides.
    honest=True: only sides with contacts deposit cover (the stair
    rule's actual demand).
    """
    s, W, H = grid.stride, grid.W, grid.H
    Wb = (W + s - 1) // s
    poolb_h, poolb_v, lp_h, lp_v = _pools(grid)
    contacts = _stair_contacts(pos, adj)
    Cj_h = np.zeros((H, W))
    Cj_v = np.zeros((W, H))
    Cb_h = np.zeros((H, Wb))
    Cb_v = np.zeros((W, Wb))
    for v, (h_us, v_us) in contacts.items():
        x = int(round(float(pos[v][0])))
        y = int(round(float(pos[v][1])))
        if h_us or not honest:
            xs = [int(round(float(pos[u][0]))) for u in h_us] + [x]
            a, b = min(xs), max(xs)
            Cj_h[y, a:b + 1] += 1.0
            Cb_h[y, a // s:b // s + 1] += 1.0
        if v_us or not honest:
            ys = [int(round(float(pos[u][1]))) for u in v_us] + [y]
            a, b = min(ys), max(ys)
            Cj_v[x, a:b + 1] += 1.0
            Cb_v[x, a // s:b // s + 1] += 1.0
    j = [_stats(Cj_h, lp_h[:, None]), _stats(Cj_v, lp_v[:, None])]
    b = [_stats(Cb_h, poolb_h), _stats(Cb_v, poolb_v)]
    kind = "honest" if honest else "raw   "
    print(f"  [{kind}] junction: maxcov={max(j[0][0], j[1][0])} "
          f"cells={j[0][1] + j[1][1]} hinge2={j[0][2] + j[1][2]:.0f}"
          f" | brick: maxcov={max(b[0][0], b[1][0])} "
          f"cells={b[0][1] + b[1][1]} hinge2={b[0][2] + b[1][2]:.0f}")
    for name, C, P in (("h", Cb_h, poolb_h), ("v", Cb_v, poolb_v)):
        for i, jx in zip(*np.where(C - P > 0)):
            print(f"      {name} line={i:2d} brick={jx:2d} "
                  f"cover={int(C[i, jx]):2d} pool={int(P[i, jx])}")


def main():
    grid, adj, crystal, stalled = build_states()
    for tag, pos in (("crystal  (0 deficits)", crystal),
                     ("stalled (73 deficits)", stalled)):
        print(f"[{tag}]")
        census(grid, adj, pos, tag, honest=False)
        census(grid, adj, pos, tag, honest=True)
        contacts = _stair_contacts(pos, adj)
        e = stair_energy(pos, adj, contacts=contacts)
        E = S.seat_energy(pos, adj, grid, lam=1.0)
        print(f"  stair={e:.0f}  pen(as-shipped)={E - e:.0f}  "
              f"seat_E(lam=1)={E:.0f}")
    print("done-gate", flush=True)


if __name__ == "__main__":
    main()
