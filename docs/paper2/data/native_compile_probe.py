"""Measure cold Numba compilation separately from native embedding work.

Run in a fresh process: .venv/bin/python docs/paper2/data/native_compile_probe.py
The event timer excludes nested double-counting. This is a small warmup probe,
not a claim that every possible future dtype/signature has been compiled.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


def main():
    os.environ["NUMBA_CACHE_DIR"] = tempfile.mkdtemp(prefix="ember-native-compile-")
    start = time.perf_counter()
    import networkx as nx
    import dwave_networkx as dnx
    import numba
    from numba.core import event
    from ember_qc.algorithms.factored import attract_embed
    from ember_qc.algorithms.factored import placement
    import_seconds = time.perf_counter() - start
    source, target = nx.path_graph(8), dnx.zephyr_graph(3, 4)
    rows = []
    for label in ("cold", "warm"):
        timer = event.TimingListener()
        start = time.perf_counter()
        with event.install_listener("numba:compile", timer):
            result = attract_embed(source, target, timeout=0, max_asks=200,
                                   seed=123, tail="none")
        elapsed = time.perf_counter() - start
        assert result["success"] and result["diag"]["mm_calls"] == 0
        rows.append(dict(run=label, elapsed_seconds=elapsed,
                         compilation_seconds=timer.duration if timer.done else 0.0,
                         asks=result["diag"]["asks"],
                         physical_qubits=result["diag"]["physical_qubits"]))
    digest = hashlib.sha256()
    for file in sorted(Path(placement.__file__).parent.glob("*.py")):
        digest.update(file.name.encode())
        digest.update(file.read_bytes())
    report = dict(import_seconds=import_seconds, numba=numba.__version__,
                  code_hash=digest.hexdigest(), load_average=os.getloadavg(),
                  scope="Path8/Z3 warmup, fresh Numba cache, one process", rows=rows)
    output = Path(__file__).with_name("three_order_compilation.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
