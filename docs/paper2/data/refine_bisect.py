"""
docs/paper2/data/refine_bisect.py
==================================
Bisection of the refine_probe turan failure (16.48 in-pipeline / 11.50
random-init vs the 8.4 bar): which refinement broke multipartite block
discovery? Arms via monkeypatch on the CURRENT code, E-first (routing only
after attribution):

  new        as-built (value-priced insertion + edge monotonization)
  rank       insertion forced back to rank pricing (values/anchors dropped)
  nomono     edge_monotonize disabled (identity)
  rank+nomono  both — approximates the pre-refinement machinery minus the
               global alignment (which is deleted; its numbers are on
               record: s3.36 routed 8.24-8.47, consolidation probe 8.40)

Run:  .venv/bin/python docs/paper2/data/refine_bisect.py
"""
import numpy as np
import networkx as nx
import dwave_networkx as dnx

from ember_qc.load_graphs import load_graph
from ember_qc.algorithms.factored import field
from ember_qc.algorithms.factored.placement import target_layout

src = nx.convert_node_labels_to_integers(load_graph(2647))
nodes = sorted(src.nodes())
src_adj = {v: sorted(src.neighbors(v)) for v in nodes}
target = dnx.pegasus_graph(16)
grid = field.TileGrid(target, target_layout(target))

_real_insert = field.insertion_sweeps
_real_mono = field.edge_monotonize


def rank_insert(order, adj, *, max_sweeps=8, values=None, anchors=None):
    return _real_insert(order, adj, max_sweeps=max_sweeps)


def no_mono(pos, adj, *, max_sweeps=16):
    return ({v: np.asarray(p, dtype=float).copy() for v, p in pos.items()},
            {"sweeps": 0, "swaps": 0, "time": 0.0})


def run(name, insert_fn, mono_fn):
    field.insertion_sweeps = insert_fn
    field.edge_monotonize = mono_fn
    try:
        rng = np.random.default_rng(1234)
        tp = {v: np.array([1.5 + 13.0 * rng.random(),
                           1.5 + 13.0 * rng.random()]) for v in nodes}
        tp = field.stair_step(tp, src_adj, eta=0.3)
        tp, info = field.alternate_arrange(tp, src_adj, grid, iters=8,
                                           insert_sweeps=8)
        print(f"{name:12s} E={info['E'][-1]:8.0f} "
              f"traj={[round(e) for e in info['E'][:3]]}..."
              f"{round(info['E'][-1])} reverts={info['insert_reverts']} "
              f"mono_swaps={info['mono_swaps']}", flush=True)
        return tp
    finally:
        field.insertion_sweeps = _real_insert
        field.edge_monotonize = _real_mono


run("new", _real_insert, _real_mono)
run("rank", rank_insert, _real_mono)
run("nomono", _real_insert, no_mono)
run("rank+nomono", rank_insert, no_mono)
print("done-bisect", flush=True)
