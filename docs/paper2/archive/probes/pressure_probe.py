"""
docs/paper2/data/pressure_probe.py
===================================
Phase A of the pressure round (bars pre-registered in the plan; s3.42(b)
carries the verdict). Router-free, both targets. Arms per cell:
contract-v2 (pressure, cycles=4) vs contract-v1 (the leaky wall) vs the
pipeline handoff (round_E). Reports E_wire, residual overload (v2) /
growth overfill (v1), the BLOB-AREA LAW check (occupied area vs predicted
bar-mass / (cap density * derate)), and implied-bar shape stats on the
liquid cells (Max's shape question).

Run:  nohup .venv/bin/python docs/paper2/data/pressure_probe.py \
        > docs/paper2/data/pressure_probe.log 2>&1 &
"""

import time

import numpy as np
import networkx as nx
import dwave_networkx as dnx

from ember_qc.load_graphs import load_graph
from ember_qc.algorithms.factored import attract_embed
from ember_qc.algorithms.factored.field import (
    TileGrid, _target_kappa, contract_layout, derive_bars_stair,
    stair_energy)
from ember_qc.algorithms.factored.placement import (
    source_positions, target_layout)

CELLS = {
    "K100": None, "K140": None, "ER100_d10": None,
    "turan_n162": 2647, "spin_glass_n163": 37309,
    "wsc_c3_sz32_n96": 33571, "wsc_c3_sz64_n192": 33574,
    "regular_n316": 13096, "ws_n486": 17188,
}
LIQUID = ("ER100_d10", "spin_glass_n163")
TARGETS = {"Z12": lambda: dnx.zephyr_graph(12, 4),
           "P16": lambda: dnx.pegasus_graph(16)}


def _load(name, gid):
    if name == "K100":
        return nx.complete_graph(100)
    if name == "K140":
        return nx.complete_graph(140)
    if name == "ER100_d10":
        return nx.convert_node_labels_to_integers(
            nx.gnp_random_graph(100, 10.0 / 99.0, seed=12345))
    return nx.convert_node_labels_to_integers(load_graph(gid))


def spread_init(src, grid):
    cent = source_positions(src, np.zeros(2), np.ones(2))
    lo = np.array([0.5, 0.5])
    hi = np.array([grid.W - 1.5, grid.H - 1.5])
    return {v: lo + (np.asarray(cent[v]) - 0.1) / 0.8 * (hi - lo)
            for v in sorted(src.nodes())}


def blob_stats(pos, src_adj, grid, kappa):
    """(occupied_area, predicted_area, mean_bar_len, max_bar_len)."""
    bars = derive_bars_stair(pos, src_adj, kappa=kappa,
                             bounds=(grid.W, grid.H))
    mass = sum(float(h[1] - h[0]) + float(v[1] - v[0]) + 1.0
               for (h, v) in bars.values())
    dens = float(grid.cap.sum()) / (grid.W * grid.H)  # wires per tile
    predicted = mass / dens
    occ = set()
    for v, (h_iv, v_iv) in bars.items():
        r = int(round(float(pos[v][1])))
        c = int(round(float(pos[v][0])))
        for t in range(int(np.floor(h_iv[0])), int(np.ceil(h_iv[1])) + 1):
            occ.add((r, t))
        for t in range(int(np.floor(v_iv[0])), int(np.ceil(v_iv[1])) + 1):
            occ.add((t, c))
    lens = [float(h[1] - h[0]) + float(v[1] - v[0])
            for (h, v) in bars.values()]
    return len(occ), round(predicted, 1), round(float(np.mean(lens)), 2), \
        round(float(np.max(lens)), 2)


def main():
    for tname, tfn in TARGETS.items():
        target = tfn()
        grid = TileGrid(target, target_layout(target))
        kappa = _target_kappa(grid)
        print(f"\n===== {tname} (kappa {kappa:.1f})", flush=True)
        for cell, gid in CELLS.items():
            src = _load(cell, gid)
            src_adj = {v: sorted(src.neighbors(v)) for v in sorted(src)}
            t0 = time.perf_counter()
            r = attract_embed(src, target, timeout=30, seed=0)
            ctrl_E = (r.get("round_E") or [float("nan")])[-1]
            print(f"[{tname}] {cell}: pipeline handoff E={ctrl_E} "
                  f"({round(time.perf_counter()-t0,1)}s)", flush=True)
            for arm, kw in (("v2", dict(pressure=True)),
                            ("v1", dict(pressure=False))):
                pos = spread_init(src, grid)
                new, info = contract_layout(pos, src_adj, grid, steps=300,
                                            cycles=4, **kw)
                ew = stair_energy(new, src_adj)
                feas = (f"resid={info['residual_overload']}" if kw["pressure"]
                        else f"grow={info['growth_overfill']}")
                extra = ""
                if kw["pressure"]:
                    occ, pred, mlen, xlen = blob_stats(new, src_adj, grid,
                                                      kappa)
                    extra = (f" area={occ}/pred={pred}"
                             f" barlen(mean/max)={mlen}/{xlen}")
                print(f"  {arm}: E_wire={round(ew,1)} (ctrl {ctrl_E}) "
                      f"{feas} best_cyc={info.get('best_cycle')} "
                      f"t={info['time']}s{extra}", flush=True)
    print("done-pressure-A", flush=True)


if __name__ == "__main__":
    main()
