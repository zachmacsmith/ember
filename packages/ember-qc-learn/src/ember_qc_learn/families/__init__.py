"""
Bake-off model families. Each module is self-contained — it defines its model
and/or training loss and registers a ``learned-<family>`` algorithm into ember_qc's
registry on import. Imported (best-effort) by ember_qc_learn.algorithms.
"""
