"""
docs/paper2/data/diag_feasible.py
==================================
The s3.44(b) step-0 diagnosis: is a hand-built spread layout DOWNHILL of
the settled pinned state under the current (stair + two-term pressure)
model? Decides between {model-wrong: the feasible state is not lower
E_total} and {optimizer-stuck: lower but unreached}. Z12 turan (the worst
pinned cell).

Run:  .venv/bin/python docs/paper2/data/diag_feasible.py
"""
import numpy as np
import networkx as nx
import dwave_networkx as dnx

from ember_qc.load_graphs import load_graph
from ember_qc.algorithms.factored.field import (
    PressureState, TileGrid, contract_layout, pressure_energy,
    stair_energy)
from ember_qc.algorithms.factored.placement import (
    source_positions, target_layout)

target = dnx.zephyr_graph(12, 4)
grid = TileGrid(target, target_layout(target))
src = nx.convert_node_labels_to_integers(load_graph(2647))
nodes = sorted(src.nodes())
src_adj = {v: sorted(src.neighbors(v)) for v in nodes}
LAM = 16.0  # lambda_final of the standard 4-cycle ramp


def etotal(pos):
    x = np.array([float(pos[v][0]) for v in nodes])
    y = np.array([float(pos[v][1]) for v in nodes])
    st = PressureState(pos, src_adj, grid)
    p = pressure_energy(st, x, y)
    # residual overload for the report
    a_h = x[st.Hm].min(1) - st.pad
    b_h = x[st.Hm].max(1) + st.pad
    a_v = y[st.Vm].min(1) - st.pad
    b_v = y[st.Vm].max(1) + st.pad
    from ember_qc.algorithms.factored.field import _axis_loads
    Lr, _, _, _ = _axis_loads(a_h, b_h, y, st.row_cap, st.H, st.W)
    Lc, _, _, _ = _axis_loads(a_v, b_v, x, st.col_cap, st.W, st.H)
    over = max(float(np.maximum(0.0, Lr - st.row_cap[:, None]).max()),
               float(np.maximum(0.0, Lc - st.col_cap[:, None]).max()))
    return stair_energy(pos, src_adj), p, over


# settled pinned state (reproduce s3.44 smoke)
cent = source_positions(src, np.zeros(2), np.ones(2))
lo = np.array([0.5, 0.5])
hi = np.array([grid.W - 1.5, grid.H - 1.5])
pos0 = {v: lo + (np.asarray(cent[v]) - 0.1) / 0.8 * (hi - lo)
        for v in nodes}
settled, info = contract_layout(pos0, src_adj, grid, steps=300, cycles=4,
                                pressure=True)
ew_s, p_s, ov_s = etotal(settled)
print(f"settled:    E_wire={ew_s:.1f}  P={p_s:.1f}  "
      f"E_total={ew_s + LAM * p_s:.1f}  overload={ov_s:.1f}")

# hand-built spread layout: sqrt(n) x sqrt(n) lattice over the fabric,
# variables ordered by spectral rank (keeps some adjacency locality)
side = int(np.ceil(np.sqrt(len(nodes))))
order = sorted(nodes, key=lambda v: (float(pos0[v][1]), float(pos0[v][0])))
hand = {}
for i, v in enumerate(order):
    r, c = divmod(i, side)
    hand[v] = np.array([1.0 + c * (grid.W - 2.0) / side,
                        1.0 + r * (grid.H - 2.0) / side])
ew_h, p_h, ov_h = etotal(hand)
print(f"hand-spread: E_wire={ew_h:.1f}  P={p_h:.1f}  "
      f"E_total={ew_h + LAM * p_h:.1f}  overload={ov_h:.1f}")

if ew_h + LAM * p_h < ew_s + LAM * p_s:
    print("VERDICT: optimizer-stuck (feasible-ish state IS downhill, "
          "descent failed to reach it)")
else:
    print("VERDICT: model-wrong-or-hand-layout-bad (spread state is NOT "
          "downhill of the pinned state at this lambda)")
print("done-diag", flush=True)
