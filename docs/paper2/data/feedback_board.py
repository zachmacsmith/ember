"""Sequential, resumable benchmarks for the borrowed-strand feedback experiment.

The six native configurations are strict (the frozen pre-change source),
neutral (own strands, no full-set unit), macro (borrowing only for full-set
units), frozen (initial contact order fixed), oneway (spatial orders borrow;
contact order uses its own strands), and feedback (all three orders borrow).
The separate mm arm makes one stock call with the same requested wall limit.

Examples, from the repository root:
  .venv/bin/python docs/paper2/data/feedback_board.py --policy all
  .venv/bin/python docs/paper2/data/feedback_board.py --policy feedback --suite fingerprint
  .venv/bin/python docs/paper2/data/feedback_board.py --policy strict,feedback --suite sensitivity
  .venv/bin/python docs/paper2/data/feedback_board.py --policy feedback --cells K100 --seeds 0 --cold-cache

One process benchmarks one policy, one case at a time. A policy list launches
separate processes sequentially, never overlapping their timed work. Board and
sensitivity runs use a common 10-second cap with no ask cap. Fingerprints use
the original CELLS work budgets and safety timeouts. Imports/compilation/warmup,
graph loading, and independent validation are recorded outside case timings.

Results are saved atomically after every case. Reusing an output resumes it
only when engine, harness, loader, validation and dependency provenance match;
existing case inputs and budgets are checked before skipping. Different source
versions require different output files. Full diagnostics retain the distinction
between returned bookmarks and current states. No acceptance targets are set.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import fcntl
from functools import partial
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from plane_fingerprint import CELLS, _load as load_fingerprint
from rewrite_board import BOARD, _load as load_board

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
POLICIES = ("strict", "neutral", "macro", "frozen", "oneway", "feedback", "mm")
BASELINE_RECORD = HERE / "feedback_baseline.json"
DEFAULT_BASELINE = "/tmp/ember-feedback-baseline-f7a48a65c7d4/src"
SCHEMA = 1


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def hash_files(paths, *, root=None):
    digest = hashlib.sha256()
    for path in sorted(Path(p) for p in paths):
        digest.update(str(path.relative_to(root) if root else path.name).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def package_hash(folder):
    # Deliberately matches the convention in feedback_baseline.json.
    return hash_files(Path(folder).glob("*.py"))


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    if hasattr(value, "tolist"):
        return jsonable(value.tolist())
    return value


def save(output, artifact):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=output.parent,
                                     prefix=output.name + ".", suffix=".tmp",
                                     delete=False) as stream:
        json.dump(jsonable(artifact), stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    os.replace(temporary, output)


def csv_ints(value):
    try:
        result = tuple(dict.fromkeys(int(v) for v in value.split(",")))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not result or any(v < 0 for v in result):
        raise argparse.ArgumentTypeError("seeds must be nonnegative integers")
    return result


def jobs_for(args):
    selected = set(args.cells.split(",")) if args.cells else None
    available = {cell[0] for cell in (CELLS if args.suite == "fingerprint" else BOARD)}
    if selected and selected - available:
        raise ValueError("unknown cells: " + ", ".join(sorted(selected - available)))
    jobs = []
    if args.suite == "fingerprint":
        cells = [(name, fabric, spec, args.seeds if args.seeds is not None else seeds,
                  asks, timeout) for name, fabric, spec, seeds, asks, timeout in CELLS]
    else:
        seeds = args.seeds if args.seeds is not None else (
            (0,) if args.suite == "sensitivity" else (0, 1, 2))
        cells = [(name, fabric, spec, seeds, None, args.wall)
                 for name, fabric, spec in BOARD]
    for name, fabric, spec, seeds, asks, timeout in cells:
        if selected is not None and name not in selected:
            continue
        for seed in seeds:
            schedules = args.sched_seeds if args.sched_seeds is not None else (
                (1, 2) if args.suite == "sensitivity" else (seed,))
            for sched_seed in schedules:
                jobs.append(dict(cell=name, suite=args.suite, source_spec=spec,
                                 target_m=int(fabric[1:]), target_tile=4,
                                 seed=seed, sched_seed=sched_seed,
                                 max_asks=asks, timeout_seconds=timeout))
    return jobs


def job_key(job):
    return (job["suite"], job["cell"], job["seed"], job["sched_seed"])


def graph_hash(graph):
    # The shared loaders provide integer labels, including isolates.
    payload = dict(nodes=sorted(int(v) for v in graph),
                   edges=sorted((min(int(u), int(v)), max(int(u), int(v)))
                                for u, v in graph.edges()))
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def initialize(args):
    policy = args.policy
    if policy == "strict":
        sys.path.insert(0, str(Path(args.baseline_src).resolve()))
    else:
        sys.path.insert(0, str(ROOT / "packages" / "ember-qc" / "src"))
    cache = None
    if args.cold_cache:
        cache = tempfile.mkdtemp(prefix="ember-feedback-cache-")
        os.environ["NUMBA_CACHE_DIR"] = cache
    started = time.perf_counter()
    import minorminer
    from ember_qc import embedding_backend

    stats = dict(calls=0, wall=0.0)
    original_mm = minorminer.find_embedding

    def counted_mm(*call_args, **kwargs):
        stats["calls"] += 1
        if policy != "mm":
            raise AssertionError("native feedback benchmark invoked MinorMiner")
        t0 = time.perf_counter()
        try:
            return original_mm(*call_args, **kwargs)
        finally:
            stats["wall"] += time.perf_counter() - t0

    minorminer.find_embedding = counted_mm
    state = dict(policy=policy, stats=stats, capture={}, compile_event=None,
                 validator=embedding_backend.is_valid_embedding)
    mm_root = Path(minorminer.__file__).resolve().parent
    mm_hash = hash_files((p for p in mm_root.rglob("*")
                          if p.suffix in (".py", ".so", ".pyd")), root=mm_root)
    if policy != "mm":
        from numba.core import event
        from ember_qc.algorithms.factored import plane, placement
        state["compile_event"] = event
        source = Path(placement.__file__).resolve().parent
        if policy == "strict":
            if not source.is_relative_to(Path(args.baseline_src).resolve()):
                raise RuntimeError("strict arm imported outside its frozen source tree")
            record = json.loads(BASELINE_RECORD.read_text())
            if package_hash(source) != record["source_sha256"]:
                raise RuntimeError("strict source does not match feedback_baseline.json")
        elif "_policy" not in inspect.signature(plane.arrange).parameters:
            raise RuntimeError("current plane.arrange lacks the benchmark _policy hook")
        original_arrange, original_decode = plane.arrange, plane.decode

        def captured_decode(*call_args, **kwargs):
            layout = original_decode(*call_args, **kwargs)
            state["capture"]["current"] = layout
            return layout

        def captured_arrange(*call_args, **kwargs):
            state["capture"]["source"] = call_args[0]
            answer = original_arrange(*call_args, **kwargs)
            state["capture"]["bookmark"] = answer[0]
            return answer

        plane.decode = captured_decode
        plane.arrange = (captured_arrange if policy == "strict" else
                         partial(captured_arrange, _policy=policy))
        state.update(embed=placement.attract_embed, placement=placement,
                     source=source, code_hash=package_hash(source))
    else:
        state.update(source=mm_root, code_hash=mm_hash)
    provenance = dict(
        policy=policy, code_hash=state["code_hash"], source=str(state["source"]),
        harness_sha256=hash_files([Path(__file__)]),
        loaders_sha256=hash_files([HERE / "plane_fingerprint.py", HERE / "rewrite_board.py"]),
        validator_sha256=hash_files([Path(embedding_backend.__file__)]),
        minorminer_sha256=mm_hash, python=platform.python_version(),
        dependencies={name: importlib.metadata.version(name) for name in
                      ("numpy", "networkx", "numba", "dwave-networkx", "minorminer")})
    if policy == "strict":
        provenance["baseline"] = json.loads(BASELINE_RECORD.read_text())
    state["provenance"] = provenance
    state["startup"] = dict(started_at=utc_now(), cold_cache=args.cold_cache,
                            cache_directory=cache, import_seconds=time.perf_counter() - started)
    return state


def measure_call(state, callback):
    event = state["compile_event"]
    timer = event.TimingListener() if event else None
    listener = event.install_listener("numba:compile", timer) if event else nullcontext()
    with listener:
        started = time.perf_counter()
        result = callback()
        elapsed = time.perf_counter() - started
    return result, elapsed, timer.duration if timer is not None and timer.done else 0.0


def warmup(state):
    import networkx as nx
    import dwave_networkx as dnx
    import minorminer
    source, target = nx.path_graph(8), dnx.zephyr_graph(3, 4)
    records = []
    for stage in ("first", "warm"):
        state["stats"].update(calls=0, wall=0.0)
        if state["policy"] == "mm":
            callback = lambda: dict(embedding=minorminer.find_embedding(
                source, list(target.edges()), random_seed=123, timeout=1))
        else:
            callback = lambda: state["embed"](source, target, timeout=0,
                max_asks=200, seed=123, sched_seed=321, tail="none")
        result, elapsed, compilation = measure_call(state, callback)
        valid = bool(result.get("embedding")) and state["validator"](
            result["embedding"], source, target)
        if not valid or (state["policy"] != "mm" and state["stats"]["calls"]):
            raise RuntimeError("benchmark warmup failed: " + str(result.get("error")))
        records.append(dict(stage=stage, elapsed_seconds=elapsed,
                            compilation_seconds=compilation, valid=valid,
                            mm_calls=state["stats"]["calls"]))
    state["startup"]["warmup"] = records
    state["startup"]["total_seconds"] = (state["startup"]["import_seconds"] +
                                          sum(r["elapsed_seconds"] for r in records))
    state["capture"].clear()


def describe_layout(layout, state, target, input_graph):
    if layout is None:
        return None
    source = state["capture"]["source"]
    report = dict(outside_reserved_qubits=int(layout.book.outside),
                  reserved_qubits=int(layout.book.reserved) + len(source.isolates),
                  decoder_complete=bool(layout.complete), physical_qubits=None,
                  max_chain=None, valid=False)
    if (layout.book.outside == 0 and report["reserved_qubits"] <= len(target)):
        try:
            fabric = state["placement"].ZephyrFabric.from_graph(target)
            embedding = state["placement"].materialize(layout, source, fabric)
            report["valid"] = state["validator"](embedding, input_graph, target)
            if report["valid"]:
                report.update(physical_qubits=sum(map(len, embedding.values())),
                              max_chain=max(map(len, embedding.values())))
        except Exception as exc:
            report["validation_error"] = repr(exc)
    return report


def check_source(state):
    if state["policy"] != "mm" and package_hash(state["source"]) != state["code_hash"]:
        raise RuntimeError("engine source changed during the run; refusing mixed-source results")


def prepare_job(job):
    import dwave_networkx as dnx
    started = time.perf_counter()
    source = (load_fingerprint(job["source_spec"]) if job["suite"] == "fingerprint"
              else load_board(job["cell"], job["source_spec"]))
    target = dnx.zephyr_graph(job["target_m"], job["target_tile"])
    metadata = dict(input_sha256=graph_hash(source), target_sha256=graph_hash(target),
                    n=len(source), edges=source.number_of_edges())
    metadata["input_loading_seconds"] = time.perf_counter() - started
    return source, target, metadata


def run_job(job, state, source, target, metadata):
    import minorminer
    check_source(state)
    state["stats"].update(calls=0, wall=0.0)
    state["capture"].clear()
    load_before = os.getloadavg()
    if state["policy"] == "mm":
        callback = lambda: dict(embedding=minorminer.find_embedding(
            source, list(target.edges()), random_seed=job["seed"],
            timeout=job["timeout_seconds"]) or {})
    else:
        callback = lambda: state["embed"](source, target, timeout=job["timeout_seconds"],
            max_asks=job["max_asks"], seed=job["seed"], sched_seed=job["sched_seed"], tail="none")
    result, elapsed, compilation = measure_call(state, callback)
    check_source(state)
    validation_start = time.perf_counter()
    embedding = result.get("embedding") or {}
    valid = bool(embedding) and state["validator"](embedding, source, target)
    lengths = [len(chain) for chain in embedding.values()]
    diag = result.get("diag", {})
    row = dict(**job, **metadata, policy=state["policy"], success=valid,
               physical_qubits=sum(lengths) if valid else None,
               acl=sum(lengths) / len(source) if valid else None,
               max_chain=max(lengths) if valid else None,
               elapsed_seconds=elapsed, compilation_seconds=compilation,
               warm_timing_clean=compilation == 0.0, diag=jsonable(diag),
               error=result.get("error"), mm_calls=state["stats"]["calls"],
               mm_seconds=state["stats"]["wall"], load_at_start=load_before,
               load_at_end=os.getloadavg(), completed_at=utc_now(),
               code_hash=state["code_hash"])
    for key in ("asks", "passes", "accepts", "decode_calls", "dp_solves", "dp_cells",
                "direct_scores", "preparation_wall", "transition_wall", "dp_wall",
                "direct_wall", "interleave_wall", "packing_wall", "decode_wall",
                "bookmark_asks", "bookmark_wall", "stopped_by", "reserved_qubits",
                "outside_reserved_qubits", "adopt_worse", "interrupted_asks",
                "strict_accepts", "neutral_accepts", "borrowed_accepts", "whole_order_accepts"):
        row[key] = diag.get(key)
    if state["policy"] != "mm":
        row["current"] = describe_layout(state["capture"].get("current"), state, target, source)
        row["bookmark"] = describe_layout(state["capture"].get("bookmark"), state, target, source)
    row["external_validation_seconds"] = time.perf_counter() - validation_start
    if embedding and not valid:
        row["validation_error"] = "engine returned an invalid embedding"
    return row


def output_path(args, policy):
    if args.output:
        return Path(args.output)
    return HERE / ("feedback_%s_%s.json" % (args.suite, policy))


def run_policy(args):
    jobs = jobs_for(args)
    output = output_path(args, args.policy)
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_id = hashlib.sha256(str(output.resolve()).encode()).hexdigest()[:24]
    lock_path = Path(tempfile.gettempdir()) / ("ember-feedback-" + lock_id + ".lock")
    with open(lock_path, "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another process is writing " + str(output)) from exc
        state = initialize(args)
        if output.exists():
            artifact = json.loads(output.read_text())
            if artifact.get("schema") != SCHEMA or artifact.get("provenance") != state["provenance"]:
                raise RuntimeError("resume provenance mismatch; use a new output file")
        else:
            artifact = dict(schema=SCHEMA, provenance=state["provenance"],
                            created_at=utc_now(), cpu_count=os.cpu_count(),
                            platform=platform.platform(), sessions=[], rows=[])
        keys = [job_key(row) for row in artifact["rows"]]
        if len(keys) != len(set(keys)):
            raise RuntimeError("duplicate case keys in resume artifact")
        existing = dict(zip(keys, artifact["rows"]))
        warmup(state)
        session = dict(arguments=vars(args), startup=state["startup"],
                       worker=os.getpid(), load_at_start=os.getloadavg(),
                       requested_cases=len(jobs), resumed_cases=0, completed_cases=0)
        artifact["sessions"].append(session)
        artifact.pop("load_at_end", None)
        artifact["complete"] = False
        save(output, artifact)
        for job in jobs:
            source, target, metadata = prepare_job(job)
            old = existing.get(job_key(job))
            if old is not None:
                expected = jsonable(dict(**job, **metadata))
                comparison = [*job, "input_sha256", "target_sha256", "n", "edges"]
                if any(old.get(k) != expected[k] for k in comparison):
                    raise RuntimeError("resume input or budget mismatch for " + str(job_key(job)))
                session["resumed_cases"] += 1
                continue
            row = run_job(job, state, source, target, metadata)
            artifact["rows"].append(row)
            session["completed_cases"] += 1
            save(output, artifact)
            print("{policy} {cell} init={seed} sched={sched_seed}: valid={success} "
                  "Q={physical_qubits} max={max_chain} seconds={elapsed_seconds:.3f} "
                  "asks={asks} dp={dp_solves} MM={mm_calls} error={error}".format(**row), flush=True)
            if (row.get("validation_error") or
                    (args.policy != "mm" and row["mm_calls"])):
                raise RuntimeError("native/validity contract violation retained in " + str(output))
        artifact["rows"].sort(key=job_key)
        artifact["complete"] = True
        artifact["load_at_end"] = os.getloadavg()
        session["finished_at"] = utc_now()
        save(output, artifact)
        print("done-feedback", output, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--policy", default="feedback", help=", ".join(POLICIES) + "; comma-list or all")
    parser.add_argument("--suite", choices=("board", "fingerprint", "sensitivity"), default="board")
    parser.add_argument("--seeds", type=csv_ints, help="defaults: board 0,1,2; sensitivity 0; fingerprint CELLS")
    parser.add_argument("--sched-seeds", type=csv_ints, help="defaults: sensitivity 1,2; otherwise the init seed")
    parser.add_argument("--cells", default="", help="comma-separated cells from the selected suite")
    parser.add_argument("--wall", type=float, default=10.0, help="board/sensitivity timeout; fingerprints use CELLS")
    parser.add_argument("--output", help="artifact path; with multiple policies append _<policy> to its stem")
    parser.add_argument("--baseline-src", default=DEFAULT_BASELINE)
    parser.add_argument("--cold-cache", action="store_true")
    args = parser.parse_args(argv)
    policies = POLICIES if args.policy == "all" else tuple(dict.fromkeys(args.policy.split(",")))
    if not policies or any(p not in POLICIES for p in policies):
        parser.error("unknown policy; choose " + ", ".join(POLICIES))
    if args.wall <= 0:
        parser.error("--wall must be positive")
    if args.suite == "fingerprint" and "mm" in policies:
        parser.error("fingerprints measure native work budgets; select native policies")
    try:
        jobs_for(args)
    except ValueError as exc:
        parser.error(str(exc))
    if len(policies) == 1:
        args.policy = policies[0]
        run_policy(args)
        return
    for policy in policies:
        command = [sys.executable, str(Path(__file__).resolve()), "--policy", policy,
                   "--suite", args.suite, "--wall", str(args.wall),
                   "--baseline-src", args.baseline_src]
        for flag, value in (("--cells", args.cells), ("--seeds", args.seeds),
                            ("--sched-seeds", args.sched_seeds)):
            if value:
                command.extend([flag, ",".join(map(str, value)) if isinstance(value, tuple) else value])
        if args.cold_cache:
            command.append("--cold-cache")
        if args.output:
            output = Path(args.output)
            command.extend(["--output", str(output.with_name(output.stem + "_" + policy + output.suffix))])
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
