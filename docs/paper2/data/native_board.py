"""Reproducible native/reference/MM comparisons, with real timings and MM calls.

Examples:
  .venv/bin/python docs/paper2/data/native_board.py --suite fingerprint --engine native
  .venv/bin/python docs/paper2/data/native_board.py --engine native --seeds 0,1,2
  .venv/bin/python docs/paper2/data/native_board.py --engine mm --seeds 0,1,2
  .venv/bin/python docs/paper2/data/native_board.py --engine baseline --baseline-src /tmp/ember-three-order-baseline-8107456/packages/ember-qc/src

Baseline and native run in separate invocations so imported code cannot mix.
A worker warms the selected engine before timing cases; --cold-cache measures
this startup with a fresh Numba cache, recorded separately from case time.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from plane_fingerprint import CELLS, _load as load_fingerprint
from rewrite_board import BOARD, BUDGET, _load as load_board

_STATE = {}


def initialize(engine, baseline_src, cold_cache):
    if baseline_src and engine == "baseline":
        sys.path.insert(0, baseline_src)
    if cold_cache:
        os.environ["NUMBA_CACHE_DIR"] = tempfile.mkdtemp(prefix="ember-native-bench-cache-")
    started = time.perf_counter()
    import networkx as nx
    import dwave_networkx as dnx
    import minorminer
    original = minorminer.find_embedding
    stats = {"calls": 0, "wall": 0.0}
    def counted(*args, **kwargs):
        stats["calls"] += 1
        if engine == "native":
            raise AssertionError("native benchmark invoked MinorMiner")
        t0 = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            stats["wall"] += time.perf_counter() - t0
    minorminer.find_embedding = counted
    if engine != "mm":
        from ember_qc.algorithms.factored import attract_embed
        import ember_qc.algorithms.factored.placement as module
        warm = attract_embed(nx.path_graph(8), dnx.zephyr_graph(3, 4),
                             timeout=0, max_asks=200, seed=123, tail="none")
        if not warm.get("embedding"):
            raise RuntimeError("benchmark warmup failed: %r" % warm)
        source = Path(module.__file__).parent
        digest = hashlib.sha256()
        for file in sorted(source.glob("*.py")):
            digest.update(file.name.encode())
            digest.update(file.read_bytes())
        code_hash = digest.hexdigest()
    else:
        source = Path(minorminer.__file__)
        code_hash = getattr(minorminer, "__version__", "unknown")
    _STATE.update(engine=engine, stats=stats, warmup=time.perf_counter() - started,
                  source=str(source), code_hash=code_hash)


def run(job):
    name, source_spec, chip_m, seed, asks, timeout, suite = job
    import dwave_networkx as dnx
    import minorminer
    from ember_qc.embedding_backend import is_valid_embedding
    source = (load_fingerprint(source_spec) if suite == "fingerprint"
              else load_board(name, source_spec))
    target = dnx.zephyr_graph(chip_m, 4)
    stats = _STATE["stats"]
    stats.update(calls=0, wall=0.0)
    start = time.perf_counter()
    result = {}
    if _STATE["engine"] == "mm":
        embedding = minorminer.find_embedding(source, list(target.edges()),
                                             random_seed=seed, timeout=timeout) or {}
    else:
        from ember_qc.algorithms.factored import attract_embed
        result = attract_embed(source, target, timeout=timeout, max_asks=asks,
                               seed=seed, tail="none")
        embedding = result.get("embedding") or {}
    elapsed = time.perf_counter() - start
    valid = bool(embedding) and is_valid_embedding(embedding, source, target)
    diag = result.get("diag", {})
    lengths = [len(c) for c in embedding.values()]
    return dict(cell=name, seed=seed, engine=_STATE["engine"], n=len(source),
                edges=source.number_of_edges(), success=valid,
                physical_qubits=sum(lengths) if valid else None,
                acl=sum(lengths)/len(source) if valid else None,
                max_chain=max(lengths) if valid else None,
                elapsed_seconds=elapsed, timeout_seconds=timeout,
                max_asks=asks, asks=diag.get("asks"), passes=diag.get("passes"),
                accepts=diag.get("accepts"), decode_calls=diag.get("decode_calls"),
                packing_seconds=diag.get("packing_wall"),
                interleave_seconds=diag.get("interleave_wall"),
                reserved_qubits=diag.get("reserved_qubits"),
                outside_reserved_qubits=diag.get("outside_reserved_qubits", diag.get("pen")),
                active_horizontal=diag.get("active_horizontal"),
                active_vertical=diag.get("active_vertical"),
                certified=diag.get("certified"), stopped_by=diag.get("stopped_by"),
                mm_calls=stats["calls"], mm_seconds=stats["wall"],
                error=result.get("error"), worker=os.getpid(),
                worker_warmup_seconds=_STATE["warmup"],
                source=_STATE["source"], code_hash=_STATE["code_hash"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("native", "baseline", "mm"), default="native")
    parser.add_argument("--suite", choices=("board", "fingerprint"), default="board")
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--cells", default="")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--wall", type=float, default=60)
    parser.add_argument("--wall-only", action="store_true",
                        help="use the common wall cap without the inherited per-cell ask budget")
    parser.add_argument("--baseline-src")
    parser.add_argument("--cold-cache", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.engine == "baseline" and not args.baseline_src:
        parser.error("baseline requires --baseline-src")
    selected = set(args.cells.split(",")) if args.cells else None
    jobs = []
    if args.suite == "fingerprint":
        for name, fabric, spec, seeds, asks, timeout in CELLS:
            if selected is None or name in selected:
                jobs.extend((name, spec, int(fabric[1:]), seed, asks, timeout, args.suite)
                            for seed in seeds)
    else:
        for name, fabric, gid in BOARD:
            if selected is None or name in selected:
                jobs.extend((name, gid, int(fabric[1:]), int(seed),
                             None if args.wall_only else BUDGET[name], args.wall, args.suite)
                            for seed in args.seeds.split(","))
    output = Path(args.output) if args.output else Path(__file__).with_name(
        "three_order_%s_%s.json" % (args.suite, args.engine))
    artifact = dict(protocol=vars(args), load_at_start=os.getloadavg(),
                    cpu_count=os.cpu_count(), rows=[])
    def save():
        output.write_text(json.dumps(artifact, indent=2) + "\n")
    save()
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize,
                             initargs=(args.engine, args.baseline_src, args.cold_cache)) as pool:
        for future in as_completed([pool.submit(run, job) for job in jobs]):
            row = future.result()
            artifact["rows"].append(row)
            save()
            print("{cell} seed={seed} {engine}: valid={success} Q={physical_qubits} "
                  "ACL={acl} seconds={elapsed_seconds:.3f} asks={asks} "
                  "MM={mm_calls} error={error}".format(**row), flush=True)
    artifact["rows"].sort(key=lambda r: (r["cell"], r["seed"]))
    artifact["load_at_end"] = os.getloadavg()
    save()
    print("wrote", output, flush=True)


if __name__ == "__main__":
    main()
