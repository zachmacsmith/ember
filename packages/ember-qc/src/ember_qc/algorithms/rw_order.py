"""
ember_qc/algorithms/rw_order.py
===============================
Reweave **construction-order** variants — the vertex-ordering search lever (#1).

Reweave's negotiated cold start places vertices in a fixed order
(:meth:`ReweaveRouter._bfs_order`, BFS from the highest-degree vertex). The order
determines how compact the chains come out: a vertex placed after its neighbours
can anchor to them, one placed early floats. This module injects each ordering in
``search_orders.ORDERINGS`` into that slot, so we can benchmark them head-to-head.

Each variant is the **optimized** Reweave router (bounded routing + dirty-set LNS
+ spur) in **cold mode** (``base_method=None``) with ``_bfs_order`` overridden to
return the chosen order — exactly the one-method-override / ``router_cls=``
injection pattern from ``reweave_opt.py``. Cold mode is used because the warm
(MM-seeded) headline path skips the cold start entirely, so the order only bites
when Reweave builds from scratch. The *same* orderings are also fed to the
forked ``minorminer`` (``var_order=``) and to ATOM, so a winning order can be
compared across all three vehicles.

Registered: ``reweave-cold-<order>`` for every non-trivial order
(``degeneracy``, ``minfill``, ``mcs``, ``cuthill``, ``spectral``, ``community``).
``reweave-cold`` itself is the ``bfs`` baseline (in ``reweave_opt.py``).
"""
from __future__ import annotations

from ember_qc.registry import register_algorithm
from ember_qc.algorithms.reweave import _ReweaveBase
from ember_qc.algorithms.reweave_opt import _OptimizedRouter
from ember_qc.algorithms.search_orders import ORDERINGS


def _ordered_router(order_name: str) -> type:
    """An optimized Reweave router whose cold-start order is ``order_name``."""
    order_fn = ORDERINGS[order_name]

    class _OrderedColdRouter(_OptimizedRouter):
        def _bfs_order(self):
            order = order_fn(self.source)
            # guard: must be a permutation of the source vertices
            if len(order) != len(self.src_nodes) or set(order) != set(self.src_nodes):
                return super()._bfs_order()
            return order

    _OrderedColdRouter.__name__ = f"OrderedColdRouter_{order_name}"
    _OrderedColdRouter.__qualname__ = _OrderedColdRouter.__name__
    return _OrderedColdRouter


def _make_variant(order_name: str) -> type:
    cls = type(
        f"ReweaveCold_{order_name}",
        (_ReweaveBase,),
        {
            "_params": {"router_cls": _ordered_router(order_name), "base_method": None},
            "__doc__": (
                f"Reweave cold start (optimized) with the '{order_name}' construction "
                f"order — vertex-ordering search lever."
            ),
        },
    )
    return register_algorithm(f"reweave-cold-{order_name}")(cls)


# Register one variant per ordering (skip 'bfs' — that is plain reweave-cold).
_VARIANTS = {}
for _name in ORDERINGS:
    if _name == "bfs":
        continue
    _VARIANTS[_name] = _make_variant(_name)
