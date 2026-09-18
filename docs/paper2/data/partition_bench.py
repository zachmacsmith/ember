"""Sequential baseline/new audits for shared partition nominations.

Run the requested complete audit from the repository root:
  .venv/bin/python docs/paper2/data/partition_bench.py --suite all --policy all --cold-cache

Individual suites are board (ten cases, three seeds, ten warm seconds),
fingerprint (the existing CELLS work budgets), and micro (fixed baseline-decoded
snapshots, all destinations, seven set sizes, twenty repetitions). `snapshots`
creates the immutable common microbenchmark inputs using the frozen baseline.
All multi-arm invocations launch subprocesses sequentially. Native calls forbid
MinorMiner. The retained feedback harness supplies loading, timing, validation,
atomic resumable artifacts, and source-freeze checks; none of its old artifacts
are modified. Preparation timers include transition construction as before.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import feedback_board as common

HERE, ROOT = common.HERE, common.ROOT
RECORD = HERE / "partition_baseline.json"
BASELINE = "/tmp/ember-partition-baseline-7a4214bc4440/src"
SNAPSHOTS = HERE / "partition_snapshots.json"
MICRO_CELLS = ("K100", "ER100_d10", "grid_200")
SCHEMA = 1
_initialize_feedback = common.initialize


def initialize(args):
    # The old harness selects source imports and capture wrappers correctly;
    # its strict label means frozen source, not a change to baseline acceptance.
    translated = argparse.Namespace(**vars(args))
    translated.policy = "strict" if args.policy == "baseline" else "feedback"
    common.BASELINE_RECORD = RECORD
    state = _initialize_feedback(translated)
    state["policy"] = args.policy
    state["provenance"].update(
        policy=args.policy,
        harness_sha256=common.hash_files([Path(__file__), Path(common.__file__)]),
        experiment="shared-partition-nominations",
    )
    return state


def output_path(args, policy):
    return Path(args.output) if args.output else HERE / f"partition_{args.suite}_{policy}.json"


def content_hash(value):
    return hashlib.sha256(json.dumps(common.jsonable(value), sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def load_snapshots(path):
    artifact = json.loads(path.read_text())
    record = json.loads(RECORD.read_text())
    if (artifact.get("schema") != SCHEMA or not artifact.get("complete")
            or artifact.get("baseline_source_sha256") != record["source_sha256"]
            or artifact.get("loader_sha256") != common.hash_files(
                [HERE / "rewrite_board.py"])):
        raise RuntimeError("microbenchmark snapshot provenance mismatch")
    if artifact.get("content_sha256") != content_hash(artifact["snapshots"]):
        raise RuntimeError("microbenchmark snapshot content was modified")
    if [s["cell"] for s in artifact["snapshots"]] != list(MICRO_CELLS):
        raise RuntimeError("unexpected microbenchmark snapshot cells")
    return artifact


def make_snapshots(args):
    if args.policy != "baseline":
        raise ValueError("snapshots must be created by the baseline")
    output = Path(args.snapshots)
    if output.exists():
        load_snapshots(output)
        print("reused-partition-snapshots", output, flush=True)
        return
    state = initialize(args)
    common.warmup(state)
    import numpy as np
    from ember_qc.algorithms.factored.native_model import Source, complete_coordinates
    from ember_qc.algorithms.factored.plane import decode

    snapshots = []
    board = {name: (fabric, spec) for name, fabric, spec in common.BOARD}
    for cell in MICRO_CELLS:
        common.check_source(state)
        fabric, spec = board[cell]
        graph = common.load_board(cell, spec)
        source = Source.from_graph(graph)
        rng = np.random.default_rng(0)
        orders = np.asarray([rng.permutation(len(source.labels)) for _ in range(3)],
                            dtype=np.int64)
        metrics = {}
        layout, elapsed, compilation = common.measure_call(state, lambda: decode(
            orders, source, int(fabric[1:]), 4, seed=0, info=metrics))
        coords = complete_coordinates(orders, layout.coords, layout.book.active, 8)
        snapshots.append(common.jsonable(dict(
            cell=cell, n=len(source.labels), edges=graph.number_of_edges(),
            input_sha256=common.graph_hash(graph), chip_m=int(fabric[1:]), tile=4,
            seed=0, orders=orders, coords=coords, indptr=source.indptr,
            indices=source.indices, decoded_score=layout.book.score,
            decoder_complete=layout.complete, decode_seconds=elapsed,
            compilation_seconds=compilation, decoder_metrics=metrics)))
        common.check_source(state)
    if state["stats"]["calls"]:
        raise AssertionError("snapshot creation invoked MinorMiner")
    artifact = dict(schema=SCHEMA, complete=True, created_at=common.utc_now(),
                    baseline_source_sha256=state["code_hash"],
                    loader_sha256=common.hash_files([HERE / "rewrite_board.py"]),
                    provenance=state["provenance"], startup=state["startup"],
                    snapshot_definition="seed-0 independent orders, baseline total decode, dormant completion",
                    snapshots=snapshots, content_sha256=content_hash(snapshots), mm_calls=0)
    common.save(output, artifact)
    print("done-partition-snapshots", output, flush=True)


def array_hash(arrays):
    digest = hashlib.sha256()
    for array in arrays:
        digest.update(str(array.shape).encode())
        digest.update(str(array.dtype).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def micro_key(row):
    return row["cell"], row["axis"], row["size"]


def run_micro(args):
    import numpy as np

    snapshot_artifact = load_snapshots(Path(args.snapshots))
    state = initialize(args)
    from ember_qc.algorithms.factored.order_dp import _check_inputs, interleave

    state["provenance"]["snapshots_sha256"] = snapshot_artifact["content_sha256"]
    state["provenance"]["micro_definition"] = dict(
        repeats=args.repeats, checked=False, set_selection="destination-prefix",
        initialization_seed=0, candidate_deadline=None)
    output = output_path(args, args.policy)
    # The parent process already enforces one worker. Reuse the artifact lock
    # protocol as a further guard against accidental duplicate invocations.
    import fcntl
    import tempfile
    lock_id = hashlib.sha256(str(output.resolve()).encode()).hexdigest()[:24]
    with open(Path(tempfile.gettempdir()) / f"ember-partition-{lock_id}.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if output.exists():
            artifact = json.loads(output.read_text())
            if (artifact.get("schema") != SCHEMA
                    or artifact.get("provenance") != state["provenance"]):
                raise RuntimeError("microbenchmark resume provenance mismatch")
        else:
            artifact = dict(schema=SCHEMA, provenance=state["provenance"],
                            created_at=common.utc_now(), platform=platform.platform(),
                            cpu_count=os.cpu_count(), sessions=[], rows=[])
        keys = [micro_key(r) for r in artifact["rows"]]
        if len(keys) != len(set(keys)):
            raise RuntimeError("duplicate microbenchmark resume cases")
        done = set(keys)
        common.warmup(state)
        session = dict(arguments=vars(args), startup=state["startup"], worker=os.getpid(),
                       completed_queries=0, resumed_queries=0)
        artifact["sessions"].append(session)
        artifact["complete"] = False
        common.save(output, artifact)
        selected = set(args.cells.split(",")) if args.cells else set(MICRO_CELLS)
        for snapshot in snapshot_artifact["snapshots"]:
            if snapshot["cell"] not in selected:
                continue
            arrays = tuple(np.asarray(snapshot[k], dtype=np.int64) for k in
                           ("orders", "coords", "indptr", "indices"))
            orders, coords, indptr, indices = arrays
            frozen_hash = array_hash(arrays)
            n, chip_m = snapshot["n"], snapshot["chip_m"]
            sizes = tuple(dict.fromkeys((1, 2, n // 4, n // 2, n - 2, n - 1, n)))
            for axis in range(3):
                _check_inputs(*arrays, chip_m, axis)
                for size in sizes:
                    key = (snapshot["cell"], axis, size)
                    if key in done:
                        session["resumed_queries"] += 1
                        continue
                    common.check_source(state)
                    unit = tuple(map(int, orders[axis, :size]))
                    rows = []
                    state["stats"].update(calls=0, wall=0.0)
                    for repetition in range(args.repeats):
                        metrics = {}
                        answer, elapsed, compilation = common.measure_call(state,
                            lambda: interleave(*arrays, axis, unit, chip_m,
                                               info=metrics, checked=False))
                        result, flipped = answer
                        rows.append(dict(repetition=repetition,
                                         elapsed_seconds=elapsed,
                                         compilation_seconds=compilation,
                                         changed=result is not None, flipped=flipped,
                                         result_sha256=None if result is None else array_hash((result,)),
                                         metrics=common.jsonable(metrics)))
                    common.check_source(state)
                    if array_hash(arrays) != frozen_hash:
                        raise AssertionError("query mutated common snapshot inputs")
                    if state["stats"]["calls"]:
                        raise AssertionError("microbenchmark invoked MinorMiner")
                    signatures = {(r["changed"], r["flipped"], r["result_sha256"],
                                   tuple(r["metrics"]["score"])) for r in rows}
                    if len(signatures) != 1:
                        raise AssertionError("identical completed queries were nondeterministic")
                    row = dict(cell=snapshot["cell"], axis=axis, size=size,
                               policy=args.policy, n=n, edges=snapshot["edges"],
                               input_sha256=snapshot["input_sha256"],
                               arrays_sha256=frozen_hash, unit=unit,
                               code_hash=state["code_hash"], repetitions=rows,
                               elapsed_seconds=sum(r["elapsed_seconds"] for r in rows),
                               compilation_seconds=sum(r["compilation_seconds"] for r in rows),
                               mm_calls=state["stats"]["calls"], completed_at=common.utc_now())
                    artifact["rows"].append(row)
                    session["completed_queries"] += 1
                    common.save(output, artifact)
                    print(f"micro {args.policy} {key}: {row['elapsed_seconds']:.4f}s / "
                          f"{args.repeats} reps", flush=True)
        artifact["rows"].sort(key=micro_key)
        artifact["complete"] = True
        session["finished_at"] = common.utc_now()
        common.save(output, artifact)
        print("done-partition-micro", output, flush=True)


def child(args, suite, policy):
    command = [sys.executable, str(Path(__file__).resolve()), "--suite", suite,
               "--policy", policy, "--baseline-src", args.baseline_src,
               "--snapshots", args.snapshots, "--wall", str(args.wall),
               "--repeats", str(args.repeats)]
    if args.cold_cache:
        command.append("--cold-cache")
    if args.cells:
        command.extend(["--cells", args.cells])
    if args.seeds is not None:
        command.extend(["--seeds", ",".join(map(str, args.seeds))])
    if args.output and suite != "snapshots":
        path = Path(args.output)
        command.extend(["--output", str(path.with_name(
            f"{path.stem}_{suite}_{policy}{path.suffix}"))])
    subprocess.run(command, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=("all", "board", "fingerprint", "micro", "snapshots"),
                        default="board")
    parser.add_argument("--policy", default="all", help="baseline, new, comma-list, or all")
    parser.add_argument("--baseline-src", default=BASELINE)
    parser.add_argument("--snapshots", default=str(SNAPSHOTS))
    parser.add_argument("--cold-cache", action="store_true")
    parser.add_argument("--wall", type=float, default=10.0)
    parser.add_argument("--seeds", type=common.csv_ints)
    parser.add_argument("--cells", default="")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    args.sched_seeds = None
    policies = ("baseline", "new") if args.policy == "all" else tuple(
        dict.fromkeys(args.policy.split(",")))
    if not policies or any(p not in ("baseline", "new") for p in policies):
        parser.error("--policy must name baseline and/or new")
    if args.wall <= 0 or args.repeats <= 0:
        parser.error("wall and repetitions must be positive")
    if args.suite == "all":
        if args.cells or args.seeds is not None:
            parser.error("use individual suites to filter cells or seeds")
        child(args, "snapshots", "baseline")
        for suite in ("micro", "board"):
            for policy in policies:
                child(args, suite, policy)
        if "new" in policies:
            child(args, "fingerprint", "new")
        return
    if args.suite in ("micro", "snapshots"):
        if args.cells and set(args.cells.split(",")) - set(MICRO_CELLS):
            parser.error("micro cells are K100, ER100_d10, and grid_200")
        if args.suite == "snapshots":
            args.policy = "baseline"
            make_snapshots(args)
            return
        if not Path(args.snapshots).exists():
            child(args, "snapshots", "baseline")
    else:
        try:
            common.jobs_for(args)
        except ValueError as exc:
            parser.error(str(exc))
    if len(policies) > 1:
        for policy in policies:
            child(args, args.suite, policy)
        return
    args.policy = policies[0]
    if args.suite == "micro":
        run_micro(args)
    else:
        common.initialize = initialize
        common.output_path = output_path
        common.run_policy(args)


if __name__ == "__main__":
    main()
