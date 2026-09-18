"""Resumable single-worker audit of live nominations and streamed merge costs.

After tests, freeze exactly the verified production source:
  .venv/bin/python docs/paper2/data/live_bench.py --freeze --expected-source HASH
Then run (from a detached supervisor, never overlapping workers):
  .venv/bin/python docs/paper2/data/live_bench.py --suite all --policy all --cold-cache

The four board arms are baseline, loop (new loop with frozen dense kernels),
full, and stock mm. Microqueries reuse the immutable partition snapshots.
Equivalence compares exact fixed-work layouts and non-timing diagnostics of loop
and full; kernel work counters intentionally differ. Improving usable layouts
are retained during calls and converted independently after case timing ends.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

import feedback_board as common
import partition_bench as micro

HERE, ROOT = common.HERE, common.ROOT
RECORD = HERE / "live_baseline.json"
FREEZE = HERE / "live_freeze.json"
POLICIES = ("baseline", "loop", "full", "mm")
EARLY_SECONDS = (0.01, 0.1, 1.0, 10.0)
_original_run_job = common.run_job


def content_hash(value):
    return hashlib.sha256(json.dumps(common.jsonable(value), sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def freeze(args):
    if not args.expected_source:
        raise ValueError("--freeze requires --expected-source from the completed validation")
    production = ROOT / "packages" / "ember-qc" / "src"
    package = production / "ember_qc" / "algorithms" / "factored"
    current = common.package_hash(package)
    if current != args.expected_source:
        raise RuntimeError("production source differs from the validated expected hash")
    baseline_record = json.loads(RECORD.read_text())
    baseline = Path(baseline_record["snapshot_src"])
    if common.package_hash(baseline / "ember_qc/algorithms/factored") != baseline_record["source_sha256"]:
        raise RuntimeError("baseline source mismatch")
    if FREEZE.exists():
        old = load_freeze()
        if old["production_source_sha256"] != current:
            raise RuntimeError("existing freeze differs; preserve it before starting another experiment")
        print("reused-live-freeze", old["source_hashes"], flush=True)
        return
    sources = {"baseline": str(baseline)}
    hashes = {"baseline": baseline_record["source_sha256"]}
    archives = {}
    for policy in ("full", "loop"):
        source = Path(f"/tmp/ember-live-{policy}-{current[:12]}") / "src"
        if source.exists():
            shutil.rmtree(source)
        shutil.copytree(production, source, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if policy == "loop":
            shutil.copyfile(baseline / "ember_qc/algorithms/factored/order_dp.py",
                            source / "ember_qc/algorithms/factored/order_dp.py")
        sources[policy] = str(source)
        hashes[policy] = common.package_hash(source / "ember_qc/algorithms/factored")
        archive = HERE / f"live_{policy}_source.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            stream.add(source, arcname="src")
        archives[policy] = dict(path=archive.name,
                               sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    if common.package_hash(package) != current:
        raise RuntimeError("production changed while freezing")
    record = dict(schema=1, created_at=common.utc_now(), production_source_sha256=current,
                  baseline_record_sha256=hashlib.sha256(RECORD.read_bytes()).hexdigest(),
                  sources=sources, source_hashes=hashes, archives=archives,
                  loop_definition="full source with only order_dp.py replaced by exact baseline bytes")
    common.save(FREEZE, record)
    print("frozen-live-sources", hashes, flush=True)


def load_freeze():
    record = json.loads(FREEZE.read_text())
    if record["baseline_record_sha256"] != hashlib.sha256(RECORD.read_bytes()).hexdigest():
        raise RuntimeError("baseline provenance changed after source freeze")
    for policy in ("baseline", "loop", "full"):
        source = Path(record["sources"][policy])
        if common.package_hash(source / "ember_qc/algorithms/factored") != record["source_hashes"][policy]:
            raise RuntimeError(f"frozen {policy} source was modified or is missing")
    return record


def initialize(args):
    frozen = load_freeze()
    policy = args.policy
    source_tree = Path(frozen["sources"]["full" if policy == "mm" else policy])
    sys.path.insert(0, str(source_tree))
    cache = None
    if args.cold_cache:
        cache = tempfile.mkdtemp(prefix=f"ember-live-{policy}-cache-")
        os.environ["NUMBA_CACHE_DIR"] = cache
    started = time.perf_counter()
    import minorminer
    from ember_qc import embedding_backend
    stats = dict(calls=0, wall=0.0)
    original_mm = minorminer.find_embedding

    def counted_mm(*call_args, **kwargs):
        stats["calls"] += 1
        if policy != "mm":
            raise AssertionError("native live benchmark invoked MinorMiner")
        before = time.perf_counter()
        try:
            return original_mm(*call_args, **kwargs)
        finally:
            stats["wall"] += time.perf_counter() - before

    minorminer.find_embedding = counted_mm
    state = dict(policy=policy, stats=stats, capture={}, compile_event=None,
                 validator=embedding_backend.is_valid_embedding, capture_started=None)
    mm_root = Path(minorminer.__file__).resolve().parent
    mm_hash = common.hash_files((p for p in mm_root.rglob("*")
                                if p.suffix in (".py", ".so", ".pyd")), root=mm_root)
    if policy != "mm":
        from numba.core import event
        from ember_qc.algorithms.factored import plane, placement
        state["compile_event"] = event
        source = Path(placement.__file__).resolve().parent
        if not source.is_relative_to(source_tree):
            raise RuntimeError("native engine imported outside selected frozen source")
        original_arrange, original_decode = plane.arrange, plane.decode

        def captured_decode(*call_args, **kwargs):
            layout = original_decode(*call_args, **kwargs)
            capture = state["capture"]
            capture["current"] = layout
            if state["capture_started"] is None:
                return layout
            problem = capture["source"]
            usable = (layout.book.outside == 0 and
                      layout.book.reserved + len(problem.isolates) <= capture["target_qubits"])
            if usable and (capture.get("best_reserved") is None or
                           layout.book.reserved < capture["best_reserved"]):
                capture["best_reserved"] = int(layout.book.reserved)
                info = kwargs.get("info", {})
                # Aggregate relation counters identify the current query without
                # forcing detailed production tracing or retaining every layout.
                relation_counts = {name: int(values.get("asks", 0)) for name, values
                                   in info.get("relation_work", {}).items()}
                previous = capture.get("relation_counts", {})
                changed = [name for name, count in relation_counts.items()
                           if count != previous.get(name, 0)]
                capture.setdefault("improvements", []).append(dict(
                    elapsed_seconds=time.perf_counter() - state["capture_started"],
                    ask=int(info.get("asks", 0)), layout=layout,
                    reference_round=int(info.get("passes", 0)),
                    nomination_relation=((info.get("last_query") or {}).get("relation") or
                                         (changed[0] if len(changed) == 1 else None))))
            capture["relation_counts"] = {name: int(values.get("asks", 0)) for name, values
                                          in kwargs.get("info", {}).get("relation_work", {}).items()}
            return layout

        def captured_arrange(*call_args, **kwargs):
            capture = state["capture"]
            capture["source"] = call_args[0]
            capture["target_qubits"] = kwargs.get("target_qubits") or (
                4 * call_args[2] * call_args[1] * (2 * call_args[1] + 1))
            answer = original_arrange(*call_args, **kwargs)
            capture["bookmark"] = answer[0]
            return answer

        def timed_embed(*call_args, **kwargs):
            state["capture_started"] = time.perf_counter()
            try:
                return placement.attract_embed(*call_args, **kwargs)
            finally:
                state["capture_started"] = None

        plane.decode, plane.arrange = captured_decode, captured_arrange
        state.update(embed=timed_embed, placement=placement, plane=plane,
                     source=source, code_hash=common.package_hash(source))
    else:
        state.update(source=mm_root, code_hash=mm_hash)
    state["provenance"] = dict(
        policy=policy, code_hash=state["code_hash"], source=str(state["source"]),
        experiment="live-reference-streamed-costs",
        freeze_sha256=hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
        harness_sha256=common.hash_files([Path(__file__), Path(common.__file__), Path(micro.__file__)]),
        loaders_sha256=common.hash_files([HERE / "plane_fingerprint.py", HERE / "rewrite_board.py"]),
        validator_sha256=common.hash_files([Path(embedding_backend.__file__)]),
        minorminer_sha256=mm_hash, python=platform.python_version(),
        dependencies={name: importlib.metadata.version(name) for name in
                      ("numpy", "networkx", "numba", "dwave-networkx", "minorminer")},
        early_seconds=list(EARLY_SECONDS),
        early_quality_definition="strictly improving usable reservation bookmarks, converted after timing")
    state["startup"] = dict(started_at=common.utc_now(), cold_cache=args.cold_cache,
                            cache_directory=cache, import_seconds=time.perf_counter() - started)
    return state


def output_path(args, policy):
    return Path(args.output) if args.output else HERE / f"live_{args.suite}_{policy}.json"


def run_job(job, state, source, target, metadata):
    row = _original_run_job(job, state, source, target, metadata)
    if state["policy"] == "mm":
        row["early_quality"] = None  # Stock API does not expose improving incumbents.
        return row
    before = time.perf_counter()
    improvements = []
    for record in state["capture"].get("improvements", []):
        report = common.describe_layout(record["layout"], state, target, source)
        if not report["valid"]:
            raise AssertionError("captured usable bookmark failed independent conversion/validation")
        report.update(acl=report["physical_qubits"] / len(source))
        improvements.append({**{key: value for key, value in record.items() if key != "layout"},
                             **report})
    row["improving_bookmarks"] = improvements
    row["early_quality"] = {str(limit): next((entry for entry in reversed(improvements)
                                               if entry["elapsed_seconds"] <= limit), None)
                            for limit in EARLY_SECONDS}
    row["bookmark_validation_seconds"] = time.perf_counter() - before
    row["event_metrics_available"] = state["policy"] == "full"
    for key in ("event_states", "event_updates", "strand_preparations", "traceback_checks", "tracebacks"):
        row[key] = row["diag"].get(key) if row["event_metrics_available"] else None
    for key in ("completed_rounds", "reference_visits", "nomination_counts", "relation_work"):
        row[key] = row["diag"].get(key)
    if row["success"] and (not improvements or
                            improvements[-1]["physical_qubits"] != row["physical_qubits"]):
        raise AssertionError("captured bookmark does not match returned native embedding")
    return row


def equivalence_payload(result, state):
    """Only algorithm state/work shared by both kernel representations."""
    ignored = {"event_states", "event_updates", "strand_preparations", "traceback_checks",
               "tracebacks", "preparation_wall", "transition_wall", "dp_wall", "direct_wall",
               "interleave_wall", "packing_wall", "decode_wall", "nomination_wall",
               "bookmark_wall", "elapsed", "elapsed_seconds", "wall"}

    def strip(value):
        if isinstance(value, dict):
            return {key: strip(item) for key, item in value.items()
                    if key not in ignored and not key.endswith("_wall") and not key.endswith("_seconds")}
        if isinstance(value, (list, tuple)):
            return [strip(item) for item in value]
        return common.jsonable(value)

    bookmark, info = result
    current = state["capture"]["current"]
    def layout_data(layout):
        return None if layout is None else dict(orders=layout.orders, coords=layout.coords,
                                                score=layout.book.score, complete=layout.complete)
    return strip(dict(current=layout_data(current), bookmark=layout_data(bookmark), diag=info))


def run_equivalence(args):
    import networkx as nx
    state = initialize(args)
    if args.policy not in ("loop", "full"):
        raise ValueError("equivalence requires loop or full")
    from ember_qc.algorithms.factored.native_model import Source
    common.warmup(state)
    output = output_path(args, args.policy)
    if output.exists():
        artifact = json.loads(output.read_text())
        if artifact.get("provenance") != state["provenance"]:
            raise RuntimeError("equivalence resume provenance mismatch")
    else:
        artifact = dict(schema=1, complete=False, provenance=state["provenance"],
                        sessions=[], rows=[])
    artifact["sessions"].append(state["startup"])
    artifact["complete"] = False
    done = {(row["cell"], row["seed"], row["max_asks"]) for row in artifact["rows"]}
    if len(done) != len(artifact["rows"]):
        raise RuntimeError("duplicate equivalence cases")
    cases = {"clique": nx.complete_graph(9), "path": nx.path_graph(9),
             "bipartite": nx.complete_bipartite_graph(4, 5),
             "er": nx.gnp_random_graph(11, .3, seed=17),
             "disconnected": nx.disjoint_union(nx.cycle_graph(7), nx.path_graph(4))}
    for name, graph in cases.items():
        problem = Source.from_graph(graph)
        for seed in (0, 1, 2):
            for asks in (0, 1, 4, 17, 70):
                if (name, seed, asks) in done:
                    continue
                state["capture"].clear()
                state["stats"].update(calls=0, wall=0.0)
                common.check_source(state)
                result, elapsed, compilation = common.measure_call(state, lambda: state["plane"].arrange(
                    problem, 3, 4, seed=seed, sched_seed=(seed + 1) % 3,
                    max_asks=asks, deadline=None, trace=True))
                common.check_source(state)
                payload = equivalence_payload(result, state)
                artifact["rows"].append(dict(cell=name, seed=seed, max_asks=asks,
                                             input_sha256=common.graph_hash(graph),
                                             elapsed_seconds=elapsed, compilation_seconds=compilation,
                                             payload=payload, payload_sha256=content_hash(payload),
                                             mm_calls=state["stats"]["calls"]))
                if state["stats"]["calls"]:
                    raise AssertionError("equivalence invoked MinorMiner")
        common.save(output, artifact)
        print("equivalence", args.policy, name, flush=True)
    artifact["rows"].sort(key=lambda row: (row["cell"], row["seed"], row["max_asks"]))
    artifact["complete"] = True
    common.save(output, artifact)
    print("done-live-equivalence", output, flush=True)


def compare_equivalence():
    artifacts = [json.loads((HERE / f"live_equivalence_{policy}.json").read_text())
                 for policy in ("loop", "full")]
    if not all(artifact["complete"] for artifact in artifacts):
        raise RuntimeError("incomplete equivalence artifacts")
    rows = [artifact["rows"] for artifact in artifacts]
    if len(rows[0]) != 75 or len(rows[1]) != 75:
        raise RuntimeError("expected 75 fixed-work cases per kernel representation")
    for old, new in zip(*rows):
        for key in ("cell", "seed", "max_asks", "input_sha256", "payload_sha256"):
            if old[key] != new[key]:
                raise AssertionError(f"kernel trajectory mismatch: {old['cell']}, seed={old['seed']}, "
                                     f"asks={old['max_asks']}, field={key}")
    common.save(HERE / "live_equivalence.json", dict(
        complete=True, cases=len(rows[0]), exact_matching_cases=len(rows[0]),
        sources={policy: artifact["provenance"]["code_hash"]
                 for policy, artifact in zip(("loop", "full"), artifacts)},
        artifacts_sha256=common.hash_files([HERE / f"live_equivalence_{policy}.json"
                                          for policy in ("loop", "full")]),
        compared="current and bookmark coordinates/orders/scores plus all non-timing shared diagnostics"))
    print("fixed-work-equivalence: 75/75 exact", flush=True)


def child(args, suite, policy):
    command = [sys.executable, str(Path(__file__).resolve()), "--suite", suite,
               "--policy", policy, "--wall", str(args.wall), "--repeats", str(args.repeats),
               "--snapshots", args.snapshots]
    if args.cold_cache:
        command.append("--cold-cache")
    if args.cells:
        command.extend(["--cells", args.cells])
    if args.seeds is not None:
        command.extend(["--seeds", ",".join(map(str, args.seeds))])
    if args.output:
        path = Path(args.output)
        command.extend(["--output", str(path.with_name(f"{path.stem}_{suite}_{policy}{path.suffix}"))])
    subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=("all", "board", "fingerprint", "micro", "equivalence"), default="board")
    parser.add_argument("--policy", default="all", help="baseline, loop, full, mm, comma-list, or all")
    parser.add_argument("--wall", type=float, default=10.0)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--snapshots", default=str(HERE / "partition_snapshots.json"))
    parser.add_argument("--seeds", type=common.csv_ints)
    parser.add_argument("--cells", default="")
    parser.add_argument("--output")
    parser.add_argument("--cold-cache", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--expected-source")
    args = parser.parse_args(argv)
    args.sched_seeds = None
    if args.freeze:
        freeze(args)
        return
    load_freeze()
    if args.wall <= 0 or args.repeats <= 0:
        parser.error("wall and repetitions must be positive")
    policies = POLICIES if args.policy == "all" else tuple(dict.fromkeys(args.policy.split(",")))
    if not policies or any(policy not in POLICIES for policy in policies):
        parser.error("unknown policy")
    if args.suite == "all":
        if args.cells or args.seeds is not None or args.output:
            parser.error("all suites use complete standard cases and standard artifact paths")
        for policy in ("loop", "full"):
            child(args, "equivalence", policy)
        compare_equivalence()
        for policy in ("baseline", "full"):
            child(args, "micro", policy)
        for policy in policies:
            child(args, "board", policy)
        if "full" in policies:
            child(args, "fingerprint", "full")
        return
    allowed = {"board": POLICIES, "fingerprint": ("full",),
               "micro": ("baseline", "full"), "equivalence": ("loop", "full")}[args.suite]
    if args.policy == "all":
        policies = allowed
    if any(policy not in allowed for policy in policies):
        parser.error(f"{args.suite} supports only {allowed}")
    if len(policies) > 1:
        for policy in policies:
            child(args, args.suite, policy)
        if args.suite == "equivalence" and not args.output:
            compare_equivalence()
        return
    args.policy = policies[0]
    common.initialize, common.output_path, common.run_job = initialize, output_path, run_job
    if args.suite == "micro":
        if args.cells and set(args.cells.split(",")) - set(micro.MICRO_CELLS):
            parser.error("micro cells are K100, ER100_d10, and grid_200")
        micro.initialize, micro.output_path = initialize, output_path
        micro.run_micro(args)
    elif args.suite == "equivalence":
        run_equivalence(args)
    else:
        common.jobs_for(args)
        common.run_policy(args)


if __name__ == "__main__":
    main()
