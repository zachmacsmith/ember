"""
docs/paper2/data/contract_probe.py
===================================
Stage-1 probe of the contraction design round (bars PRE-REGISTERED in the
plan file; notes s3.41 will carry the verdict). Two phases:

Phase A (router-free screen, in-process, both targets Z12 + P16): arms
{spectral-spread, random-uniform} x {deg_weight on/off} x {cycles 1, 4};
control E = the current pipeline's round_E handoff. SCREEN gate: some arm
reaches final E <= 1.1x control on >= 3/4 dense cells with zero entry
violations; CYCLES bar: cycles=4 must beat cycles=1 wherever cycles=1
jammed. wsc c3 structural check: patch column bands disjoint.

Phase B (routed, only if the screen passes — run separately after reading
Phase A): handled by contract_probe_routed.py written post-screen.

Run:  nohup .venv/bin/python docs/paper2/data/contract_probe.py \
        > docs/paper2/data/contract_probe.log 2>&1 &
"""

import time

import numpy as np
import networkx as nx
import dwave_networkx as dnx

from ember_qc.load_graphs import load_graph
from ember_qc.algorithms.factored import attract_embed
from ember_qc.algorithms.factored.field import (
    TileGrid, contract_layout, stair_energy)
from ember_qc.algorithms.factored.placement import (
    source_positions, target_layout)

CELLS = {
    "K100": None, "K140": None, "ER100_d10": None,
    "turan_n162": 2647, "spin_glass_n163": 37309,
    "wsc_c3_sz32_n96": 33571, "wsc_c3_sz64_n192": 33574,
    "regular_n316": 13096, "ws_n486": 17188,
}
DENSE = ("K100", "K140", "turan_n162", "spin_glass_n163")
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


def spread_init(kind, src, grid, seed=1234):
    nodes = sorted(src.nodes())
    if kind == "random":
        rng = np.random.default_rng(seed)
        return {v: np.array([0.5 + (grid.W - 2.0) * rng.random(),
                             0.5 + (grid.H - 2.0) * rng.random()])
                for v in nodes}
    # spectral scaled to the FULL fabric (not the middle 80%)
    cent = source_positions(src, np.zeros(2), np.ones(2))
    lo = np.array([0.5, 0.5])
    hi = np.array([grid.W - 1.5, grid.H - 1.5])
    out = {}
    for v in nodes:
        p = np.asarray(cent[v])  # in [0.1, 0.9]^2 box coords
        out[v] = lo + (p - 0.1) / 0.8 * (hi - lo)
    return out


def patch_band_overlap(pos, src):
    """wsc structural check: max pairwise column-band overlap fraction
    between the connected components (patches) of the source."""
    comps = [sorted(c) for c in nx.connected_components(src)]
    bands = [(min(float(pos[v][0]) for v in c),
              max(float(pos[v][0]) for v in c)) for c in comps]
    worst = 0.0
    for i in range(len(bands)):
        for j in range(i + 1, len(bands)):
            a, b = bands[i], bands[j]
            ov = min(a[1], b[1]) - max(a[0], b[0])
            w = min(a[1] - a[0], b[1] - b[0])
            if w > 1e-9:
                worst = max(worst, ov / w)
    return round(worst, 2)


def main():
    for tname, tfn in TARGETS.items():
        target = tfn()
        grid = TileGrid(target, target_layout(target))
        print(f"\n===== {tname} (grid {grid.W}x{grid.H}, typed={grid.typed})",
              flush=True)
        for cell, gid in CELLS.items():
            src = _load(cell, gid)
            if src.number_of_nodes() > grid.graph.number_of_nodes():
                continue
            src_adj = {v: sorted(src.neighbors(v)) for v in sorted(src)}
            # control: current pipeline's handoff E
            t0 = time.perf_counter()
            r = attract_embed(src, target, timeout=30, seed=0)
            ctrl_E = (r.get("round_E") or [float("nan")])[-1]
            print(f"[{tname}] {cell}: pipeline handoff E={ctrl_E} "
                  f"({round(time.perf_counter()-t0,1)}s, "
                  f"legal={r.get('legal_acl')})", flush=True)
            for init in ("spectral", "random"):
                for dw in (True, False):
                    for cyc in (1, 4):
                        pos = spread_init(init, src, grid)
                        e0 = stair_energy(pos, src_adj)
                        new, info = contract_layout(
                            pos, src_adj, grid, steps=300,
                            deg_weight=dw, cycles=cyc)
                        extra = ""
                        if cell.startswith("wsc_c3") and init == "spectral" \
                                and dw and cyc == 1:
                            extra = (" band_overlap="
                                     f"{patch_band_overlap(new, src)}")
                        print(f"  {init[:4]}/dw={int(dw)}/c{cyc}: "
                              f"E {round(e0)} -> {info['final_E']} "
                              f"(ctrl {ctrl_E}) blocked={info['blocked']} "
                              f"grow={info['growth_overfill']} "
                              f"t={info['time']}s "
                              f"cycles={info['cycle_E']}{extra}",
                              flush=True)
    print("done-contract-A", flush=True)


if __name__ == "__main__":
    main()
