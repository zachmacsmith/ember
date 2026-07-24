"""
docs/paper2/data/crossbar_testbed.py
=====================================
Router-free testbed for the cross-state coarse dynamics (notes s3.30): evolve
K_n crosses on the P16 tile grid under phase SCHEDULES and measure whether a
low-violation, spread, crossbar-like configuration emerges — without paying
for router calls or polish. Motivated by the 2026-07-19 findings:

  - contact capacity (extent floor = deg/kappa) makes collapse infeasible
    (the missing physics), BUT
  - from a compact start, spread-and-grow is a chicken-and-egg valley, and
  - tip-retraction chokes reach-growth during the over-capacity transient.

Forces are individually correct; their ORDER through the transient is the
open problem => schedules (the ePlace ramp lesson).

Run:  .venv/bin/python docs/paper2/data/crossbar_testbed.py [n]
"""

import sys
import time

import numpy as np
import networkx as nx
import dwave_networkx as dnx

from ember_qc.algorithms.factored.field import (
    PoissonField, TileGrid, bar_force, contact_step, deposit_cross)
from ember_qc.algorithms.factored.placement import (
    source_positions, target_layout)

KAPPA = 13.0


def simulate(n, schedule, init="compact", init_ext=0.0, log_every=0):
    target = dnx.pegasus_graph(16)
    grid = TileGrid(target, target_layout(target))
    pf = PoissonField(grid, hinge_w=1.0, mu_alpha=0.0)
    src_adj = {v: [u for u in range(n) if u != v] for v in range(n)}
    floor_ext = max(0.0, (n - 1) / KAPPA - 1.0)
    cent = source_positions(nx.complete_graph(n), np.zeros(2), np.ones(2))
    if init == "compact":
        tp = {v: np.array([7.5, 7.5])
              + (grid.to_tile(cent[v]) - grid.to_tile(np.array([0.5, 0.5]))) * 0.3
              for v in cent}
    else:  # spread
        tp = {v: np.array([1.5 + 12.0 * cent[v][0], 1.5 + 12.0 * cent[v][1]])
              for v in cent}
    ext = {v: np.array([init_ext / 2.0, init_ext / 2.0]) for v in cent}

    demand = None
    for phase in schedule:
        for step in range(phase["steps"]):
            tp, ext = contact_step(
                tp, ext, src_adj, eta=phase.get("eta", 0.3),
                extent_eta=phase.get("extent_eta", 0.3),
                extent_cost=phase.get("extent_cost", 0.05))
            if phase.get("floor", True):
                for v in ext:
                    s = ext[v].sum()
                    if s < floor_ext:
                        ext[v] = ext[v] + (floor_ext - s) / 2.0
            demand = deposit_cross(grid, tp, ext)
            fs = phase.get("field_step", 0.5)
            ew = phase.get("ext_w", 0.5)
            if fs > 0 or ew > 0:
                psi = pf.potential(demand)
                dp, de = bar_force(grid, psi, tp, ext, scale=fs, ext_w=ew)
                tp = {v: tp[v] + dp[v] for v in tp}
                ext = {v: np.maximum(0.0, ext[v] + de[v]) for v in ext}

    viol = np.maximum(0.0, demand - grid.cap)
    rows = [float(tp[v][1]) for v in tp]
    cols = [float(tp[v][0]) for v in tp]
    return dict(
        total_viol=round(float(viol.sum()), 1),
        max_viol=round(float(viol.max()), 1),
        extent_mean=round(float(np.mean([ext[v].sum() for v in ext])), 1),
        rows=len(set(int(round(r)) for r in rows)),
        cols=len(set(int(round(c)) for c in cols)),
        row_spread=round(max(rows) - min(rows), 1),
    )


SCHEDULES = {
    # everything on at once (the failing status quo)
    "S1-allon": [dict(steps=400)],
    # grow first (no field), then everything
    "S2-growfirst": [dict(steps=150, field_step=0.0, ext_w=0.0),
                     dict(steps=250)],
    # grow -> spread with extents frozen -> joint polish
    "S3-phases": [dict(steps=150, field_step=0.0, ext_w=0.0),
                  dict(steps=150, extent_eta=0.0, extent_cost=0.0, ext_w=0.0,
                       field_step=0.8),
                  dict(steps=100)],
    # linear ramp of field strength (ePlace style), approximated in 4 stages
    "S4-ramp": [dict(steps=100, field_step=0.1, ext_w=0.0),
                dict(steps=100, field_step=0.25, ext_w=0.1),
                dict(steps=100, field_step=0.5, ext_w=0.25),
                dict(steps=100, field_step=0.8, ext_w=0.5)],
    # no tip-retract at all (does growth alone + position field suffice?)
    "S5-noretract": [dict(steps=400, ext_w=0.0)],
    # strong field, weak retract
    "S6-strongfield": [dict(steps=400, field_step=1.0, ext_w=0.1)],
}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    print(f"K{n} router-free schedule sweep (floor={max(0.0,(n-1)/KAPPA-1.0):.1f})")
    for init, init_ext in (("compact", 0.0), ("spread", 12.0)):
        for name, sched in SCHEDULES.items():
            t0 = time.time()
            m = simulate(n, sched, init=init, init_ext=init_ext)
            print(f"{init:8s} {name:15s} viol={m['total_viol']:7.1f} "
                  f"max={m['max_viol']:5.1f} ext={m['extent_mean']:5.1f} "
                  f"rows={m['rows']:3d} cols={m['cols']:3d} "
                  f"spread={m['row_spread']:5.1f} ({time.time()-t0:.0f}s)",
                  flush=True)
    print("done")


if __name__ == "__main__" and "s7" not in sys.argv and "span" not in sys.argv:
    main()


def s7_sweep(n=100):
    """Floor + periodic assignment + parameter grid over the transient forces.
    Finalists (true_viol < 100) get a real quality check: bar seeds -> one MM
    route (patience=0) -> warm polish -> ACL vs template 9.78 / mm 13.6."""
    import itertools
    import minorminer as mm
    from ember_qc.algorithms.factored.field import assign_rows_cols, bar_seeds
    from ember_qc.algorithms.factored.polish import spur_prune
    from ember_qc.embedding_backend import build_adjacency

    target = dnx.pegasus_graph(16)
    grid = TileGrid(target, target_layout(target))
    adj = build_adjacency(target)
    T_edges = list(target.edges())
    src = nx.complete_graph(n)
    src_adj = {v: [u for u in range(n) if u != v] for v in range(n)}
    floor_ext = (n - 1) / KAPPA - 1.0
    cent0 = source_positions(src, np.zeros(2), np.ones(2))
    saved_cap = grid.cap.copy()

    combos = list(itertools.product(
        (1, 5, 25),          # assign every k steps (after 50-step warmup)
        (0.4, 0.8),          # extent_eta
        (0.0, 0.03),         # extent_cost
        (0.0, 0.2),          # ext_w (tip retract)
    ))
    print(f"S7 sweep: {len(combos)} combos, K{n}, floor={floor_ext:.1f}")
    best = []
    for (ak, ee, ec, ew) in combos:
        pf = PoissonField(grid, hinge_w=1.0, mu_alpha=0.0)
        grid.cap = saved_cap * 0.65
        tp = {v: np.array([7.5, 7.5]) +
              (grid.to_tile(cent0[v]) - grid.to_tile(np.array([0.5, 0.5]))) * 0.3
              for v in cent0}
        ext = {v: np.zeros(2) for v in cent0}
        for step in range(300):
            tp, ext = contact_step(tp, ext, src_adj, eta=0.3,
                                   extent_eta=ee, extent_cost=ec)
            for v in ext:
                s = ext[v].sum()
                if s < floor_ext:
                    ext[v] = ext[v] + (floor_ext - s) / 2.0
            if step >= 50 and (step - 50) % ak == 0:
                tp, _ = assign_rows_cols(tp, ext, grid, threshold=2.0)
            demand = deposit_cross(grid, tp, ext)
            psi = pf.potential(demand)
            dp, de = bar_force(grid, psi, tp, ext, scale=0.5, ext_w=ew)
            tp = {v: tp[v] + dp[v] for v in tp}
            ext = {v: np.maximum(0.0, ext[v] + de[v]) for v in ext}
        grid.cap = saved_cap
        demand_t = deposit_cross(grid, tp, ext)
        viol = float(np.maximum(0.0, demand_t - grid.cap).sum())
        rows = [float(tp[v][1]) for v in tp]
        em = float(np.mean([ext[v].sum() for v in ext]))
        nr = len(set(int(round(r)) for r in rows))
        print(f"ak={ak:2d} ee={ee} ec={ec} ew={ew}: viol={viol:6.0f} "
              f"ext={em:5.1f} rows={nr:3d} spread={max(rows)-min(rows):5.1f}",
              flush=True)
        best.append((viol, (ak, ee, ec, ew), dict(tp=dict(tp), ext=dict(ext))))

    best.sort(key=lambda t: t[0])
    print("\nfinalist route checks (top 3 by violation):")
    for viol, params, state in best[:3]:
        seeds = bar_seeds(grid, state["tp"], state["ext"])
        emb = mm.find_embedding(src, T_edges, initial_chains=seeds,
                                chainlength_patience=0, random_seed=0,
                                timeout=60)
        if not emb:
            print(f"  {params}: viol={viol:.0f} -> route FAILED", flush=True)
            continue
        emb = spur_prune(emb, {v: sorted(src.neighbors(v)) for v in src}, adj)
        pol = mm.find_embedding(src, T_edges, initial_chains=emb,
                                skip_initialization=True, random_seed=0,
                                timeout=60)
        acl = (sum(len(c) for c in pol.values()) / len(pol)) if pol else None
        print(f"  {params}: viol={viol:.0f} -> legal, polished ACL={acl:.2f} "
              f"(template 9.78, mm ~13.6)", flush=True)
    print("done-s7")


def span_sweep(n=100):
    """Span-state sweep (notes s3.31): position-only state, derived bars,
    one closed-form energy. The point of the sweep is the ABSENCE of knobs:
    no extent_eta/extent_cost/ext_w axes exist any more -- only projection
    cadence, step size, participation threshold, and a capacity derate. If
    parity needs s7-scale tuning, the simplification failed (ledger verdict).
    Finalists: wire_seeds_iv -> one MM route (patience=0) -> warm polish ->
    ACL vs cross-emergent 13.46 / mm ~13.6 / template 9.78."""
    import itertools
    import minorminer as mm
    from ember_qc.algorithms.factored.field import (
        assign_rows_cols, bar_force_iv, bar_widths, deposit_bars,
        derive_bars, span_energy, span_step, wire_seeds_iv)
    from ember_qc.algorithms.factored.polish import spur_prune
    from ember_qc.embedding_backend import build_adjacency

    target = dnx.pegasus_graph(16)
    grid = TileGrid(target, target_layout(target))
    adj = build_adjacency(target)
    T_edges = list(target.edges())
    src = nx.complete_graph(n)
    src_adj = {v: [u for u in range(n) if u != v] for v in range(n)}
    cent0 = source_positions(src, np.zeros(2), np.ones(2))
    saved_cap = grid.cap.copy()
    bounds = (grid.W, grid.H)

    combos = list(itertools.product(
        (1, 5, 25),      # assign every k steps (after 50-step warmup)
        (0.3, 0.6),      # eta: span-subgradient step size
        (2.0, 4.0),      # assign_threshold on derived w+h
        (1.0, 0.65),     # cap derate during dynamics (1.0 = stock; 0.65 was
                         # s7's cross-tuned trick, swept independently here)
    ))
    print(f"SPAN sweep: {len(combos)} combos, K{n}, 300 steps, compact init")
    results = []
    for (ak, eta, thr, derate) in combos:
        pf = PoissonField(grid, hinge_w=1.0, mu_alpha=0.0)
        grid.cap = saved_cap * derate
        tp = {v: np.array([7.5, 7.5]) +
              (grid.to_tile(cent0[v]) - grid.to_tile(np.array([0.5, 0.5]))) * 0.3
              for v in cent0}
        e_pre = e_post = None
        for step in range(300):
            tp = span_step(tp, src_adj, eta=eta)
            if step >= 50 and (step - 50) % ak == 0:
                e_pre = span_energy(tp, src_adj)
                bars = derive_bars(tp, src_adj, bounds=bounds)
                tp, _ = assign_rows_cols(tp, bar_widths(bars), grid,
                                         threshold=thr)
                e_post = span_energy(tp, src_adj)
            bars = derive_bars(tp, src_adj, bounds=bounds)
            demand = deposit_bars(grid, tp, bars)
            psi = pf.potential(demand)
            dp = bar_force_iv(grid, psi, tp, bars, scale=0.5)
            tp = {v: tp[v] + dp[v] for v in tp}
        grid.cap = saved_cap
        bars = derive_bars(tp, src_adj, bounds=bounds)
        demand_t = deposit_bars(grid, tp, bars)
        viol = float(np.maximum(0.0, demand_t - grid.cap).sum())
        rows = [float(tp[v][1]) for v in tp]
        widths = bar_widths(bars)
        em = float(np.mean([widths[v].sum() for v in widths]))
        nr = len(set(int(round(r)) for r in rows))
        E = span_energy(tp, src_adj)
        proj = (f" E_assign={e_pre:.0f}->{e_post:.0f}"
                if e_pre is not None else "")
        print(f"ak={ak:2d} eta={eta} thr={thr} derate={derate}: "
              f"E={E:7.0f} viol={viol:6.0f} ext={em:5.1f} rows={nr:3d} "
              f"spread={max(rows)-min(rows):5.1f}{proj}", flush=True)
        results.append((viol, (ak, eta, thr, derate), dict(tp)))

    results.sort(key=lambda t: t[0])
    print("\nfinalist route checks (top 3 by violation):")
    for viol, params, tp in results[:3]:
        bars = derive_bars(tp, src_adj, bounds=bounds)
        seeds = wire_seeds_iv(grid, tp, bars)
        widths = bar_widths(bars)
        unseeded = sum(1 for v in tp
                       if max(widths[v]) >= 1.0 and len(seeds.get(v, [])) <= 1)
        emb = mm.find_embedding(src, T_edges, initial_chains=seeds,
                                chainlength_patience=0, random_seed=0,
                                timeout=60)
        if not emb:
            print(f"  {params}: viol={viol:.0f} unseeded={unseeded} "
                  f"-> route FAILED", flush=True)
            continue
        emb = spur_prune(emb, {v: sorted(src.neighbors(v)) for v in src}, adj)
        pol = mm.find_embedding(src, T_edges, initial_chains=emb,
                                skip_initialization=True, random_seed=0,
                                timeout=60)
        acl = (sum(len(c) for c in pol.values()) / len(pol)) if pol else None
        print(f"  {params}: viol={viol:.0f} unseeded={unseeded} -> legal, "
              f"polished ACL={acl:.2f} (cross-emergent 13.46, mm ~13.6, "
              f"template 9.78)", flush=True)
    print("done-span")


if __name__ == "__main__" and "s7" in sys.argv:
    s7_sweep(int(sys.argv[2]) if len(sys.argv) > 2 else 100)

if __name__ == "__main__" and "span" in sys.argv:
    span_sweep(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
