"""Frozen, isolated refinement ablation on saved native-search incumbents.

The legacy replay must match saved Joint1 embeddings before revised arms run.
No MM result embedding is loaded, and no arm's output seeds another arm.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUTS = ROOT / "results/codex/retrieved/hyde03/011-search-contact-ablation"
ARMS = {
    "legacy": {"boundary_sites": 0, "group_policy": "legacy"},
    "sites16": {"boundary_sites": 16, "group_policy": "legacy"},
    "groupsround_robin": {"boundary_sites": 0, "group_policy": "round_robin"},
    "both": {"boundary_sites": 16, "group_policy": "round_robin"},
}
EXPERIMENTS = {
    'sites-groups': ARMS,
    'contact-redundancy': {
        'legacy': ARMS['legacy'],
        'both': ARMS['both'],
        'both_redundancy': {**ARMS['both'], 'objective': 'qubits_contacts'},
    },
    'contact-trees': {
        'legacy': ARMS['legacy'],
        'both': ARMS['both'],
        'both_distance': {**ARMS['both'], 'tree_policy': 'distance'},
    },
}
COMMON = {
    "timeout": 60.0, "max_passes": 4, "max_groups": 512,
    "group_sizes": [1, 2, 3, 4], "beam_width": 1, "alternatives": 3,
    "halo": 2, "max_region": 512, "max_expansions": 500000,
    "group_expansions": 50000, "max_orders": 2,
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def canonical_embedding(embedding):
    return {str(v): sorted(chain) for v, chain in embedding.items()}


def graph_from_record(record):
    import networkx as nx
    graph = nx.Graph()
    graph.add_nodes_from(record["nodes"])
    graph.add_edges_from(record["edges"])
    for node, attributes in record["node_attributes"]:
        graph.nodes[node].update(attributes)
    for a, b, attributes in record["edge_attributes"]:
        graph.edges[a, b].update(attributes)
    graph.graph.update(record["metadata"])
    return graph


def contact_redundancy(embedding, source, target):
    """Independent whole-target enumeration, outside measured refinement."""
    owner = {q: v for v, chain in embedding.items() for q in chain}
    contacts = sum(q in owner and r in owner and source.has_edge(owner[q], owner[r])
                   for q, r in target.edges())
    return contacts - source.number_of_edges()


def verify(embedding, source, target):
    if not isinstance(embedding, dict) or set(embedding) != set(source):
        raise ValueError("Embedding has incorrect source coverage")
    owner = {}
    for vertex, chain in embedding.items():
        chain_set = set(chain)
        if not chain_set or len(chain_set) != len(chain):
            raise ValueError("Empty chain or duplicate physical vertex")
        if any(q not in target or q in owner for q in chain):
            raise ValueError("Foreign or overlapping physical vertex")
        owner.update({q: vertex for q in chain})
        reached, queue = {chain[0]}, [chain[0]]
        for q in queue:
            fresh = (set(target[q]) & chain_set) - reached
            reached.update(fresh)
            queue.extend(fresh)
        if reached != chain_set:
            raise ValueError("Disconnected chain")
    if any(not any(owner.get(q) == b for p in embedding[a] for q in target[p])
           for a, b in source.edges()):
        raise ValueError("Missing source-edge contact")
    lengths = [len(chain) for chain in embedding.values()]
    mean = sum(lengths) / len(lengths)
    return {"qubits": sum(lengths), "acl": mean, "max_chain": max(lengths),
            "within_chain_variance": sum((n - mean) ** 2 for n in lengths) / len(lengths)}


class EmbedderBlocker(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0].lower()
        if "minorminer" in root or root == "busclique":
            self.attempts.append(fullname)
            raise ImportError("Prohibited embedding dependency: " + fullname)


def check_snapshot(run, manifest):
    if digest(manifest["source_files"]) != manifest["source_snapshot"]:
        raise RuntimeError("Source snapshot digest mismatch")
    for relative, expected in manifest["source_files"].items():
        if file_digest(run / "source" / relative) != expected:
            raise RuntimeError("Frozen source changed: " + relative)
    for relative, expected in manifest["input_files"].items():
        if file_digest(run / relative) != expected:
            raise RuntimeError("Frozen input changed: " + relative)


def worker(run, task_id):
    manifest = json.loads((run / "manifest.json").read_text())
    task = manifest["tasks"][task_id]
    output = {"task_id": task_id, **task, "calls": 1,
              "source_snapshot": manifest["source_snapshot"],
              "host": platform.node(), "machine": platform.uname()._asdict(),
              "python": sys.version, "python_executable": sys.executable,
              "python_prefix": sys.prefix, "load_start": os.getloadavg()}
    blocker = EmbedderBlocker()
    try:
        check_snapshot(run, manifest)
        if digest(task)[:24] != task_id:
            raise RuntimeError("Task digest mismatch")
        if any(importlib.util.find_spec(name) is not None for name in
               ("minorminer", "_minorminer", "busclique")):
            raise RuntimeError("Candidate environment contains prohibited package")
        sys.meta_path.insert(0, blocker)
        sys.path.insert(0, str(run / "source/packages/ember-qc/src"))
        from ember_qc.algorithms.factored import contact_repair
        implementation = Path(contact_repair.__file__).resolve()
        if not implementation.is_relative_to(run / "source"):
            raise RuntimeError("Candidate imported outside frozen source")
        output["implementation_path"] = str(implementation)
        output["versions"] = {}
        for package in ("networkx", "numpy", "numba", "dwave-networkx", "minorminer", "scipy"):
            try:
                output["versions"][package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                output["versions"][package] = None
        case = manifest["cases"][task["case_id"]]
        source_data = json.loads((run / "graphs" / (case["graph"] + ".json")).read_text())
        target_data = json.loads((run / "target.json").read_text())
        if digest(source_data) != case["source_hash"] or digest(target_data) != case["target_hash"]:
            raise RuntimeError("Input graph identity mismatch")
        source, target = graph_from_record(source_data), graph_from_record(target_data)
        incumbent_record = json.loads((run / "incumbents" / (task["case_id"] + ".json")).read_text())
        expected_record = json.loads((run / "expected" / (task["case_id"] + ".json")).read_text())
        for record, expected_method in ((incumbent_record, "native-search"),
                                        (expected_record, "native-search-joint1")):
            if record["method"] != expected_method or record["status"] != "SUCCESS":
                raise RuntimeError("Ineligible saved input/reference method or status")
            if (record["source_hash"] != case["source_hash"] or
                    record["target_hash"] != case["target_hash"] or record["seed"] != case["seed"]):
                raise RuntimeError("Saved embedding identity mismatch")
            if record["forbidden_import_attempts"] or record["loaded_embedding_libraries"]:
                raise RuntimeError("Saved candidate has prohibited dependency evidence")
        incumbent = {int(v): list(chain) for v, chain in incumbent_record["embedding"].items()}
        expected = {int(v): list(chain) for v, chain in expected_record["embedding"].items()}
        initial_quality = verify(incumbent, source, target)
        expected_quality = verify(expected, source, target)
        for record, quality in ((incumbent_record, initial_quality), (expected_record, expected_quality)):
            if any(record[k] != quality[k] for k in ("qubits", "acl", "max_chain")):
                raise RuntimeError("Saved embedding metrics mismatch")
        if (digest(canonical_embedding(incumbent)) != case["incumbent_hash"] or
                digest(canonical_embedding(expected)) != case["expected_hash"]):
            raise RuntimeError("Saved embedding hash mismatch")
        working = {v: list(chain) for v, chain in incumbent.items()}
        solver_source, solver_target = source.copy(), target.copy()
        started, cpu = time.perf_counter(), time.process_time()
        embedding, info = contact_repair.contact_polish(
            working, solver_source, solver_target, **task["configuration"])
        output["refinement_wall"] = time.perf_counter() - started
        output["refinement_cpu"] = time.process_time() - cpu
        output["diag"] = info
        output["initial_quality"] = initial_quality
        validation_started = time.perf_counter()
        output.update(verify(embedding, source, target))
        output['initial_contact_redundancy'] = contact_redundancy(incumbent, source, target)
        output['final_contact_redundancy'] = contact_redundancy(embedding, source, target)
        if task['configuration'].get('objective') == 'qubits_contacts':
            actual_gain = output['final_contact_redundancy'] - output['initial_contact_redundancy']
            if actual_gain != info['contact_redundancy_gain']:
                raise RuntimeError('Contact redundancy delta mismatch')
        output["validation_wall"] = time.perf_counter() - validation_started
        output["embedding"] = {str(v): list(chain) for v, chain in embedding.items()}
        output["embedding_hash"] = digest(canonical_embedding(embedding))
        output["embedding_valid"] = True
        output["saved_reference_embedding_match"] = output["embedding_hash"] == case["expected_hash"]
        output["saved_reference_exact_list_match"] = output["embedding"] == expected_record["embedding"]
        output["saved_reference_quality_match"] = all(output[k] == expected_quality[k]
                                                       for k in ("qubits", "acl", "max_chain"))
        output["qubits_saved"] = initial_quality["qubits"] - output["qubits"]
        output["status"] = "SUCCESS" if output["refinement_wall"] <= task["configuration"]["timeout"] else "TIMEOUT"
        if task["arm"] == "legacy" and not (output["saved_reference_embedding_match"]
                                              and output["saved_reference_quality_match"]):
            output["status"] = "REFERENCE_MISMATCH"
    except Exception:
        output["status"] = "ERROR"
        output["traceback"] = traceback.format_exc()
    output["forbidden_import_attempts"] = blocker.attempts
    output["loaded_embedding_libraries"] = [name for name in sys.modules
        if "minorminer" in name.split(".")[0].lower() or name.split(".")[0].lower() == "busclique"]
    if output["forbidden_import_attempts"] or output["loaded_embedding_libraries"]:
        output["status"] = "DEPENDENCY_VIOLATION"
    output["load_end"] = os.getloadavg()
    write_json(run / "results" / (task_id + ".json"), output)


def prepare(run, inputs, python, experiment='sites-groups'):
    arms = EXPERIMENTS[experiment]
    run.mkdir(parents=True, exist_ok=False)
    for directory in ("source", "graphs", "incumbents", "expected", "results", "logs", "jit_cache"):
        (run / directory).mkdir()
    source_files = {}
    package = ROOT / "packages/ember-qc/src/ember_qc"
    for source in list(package.rglob("*.py")) + [Path(__file__), package / "graphs/manifest.json",
                                                package / "graphs/presets.csv"]:
        relative = source.relative_to(ROOT)
        dest = run / "source" / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        source_files[str(relative)] = file_digest(dest)
    previous = json.loads((inputs / "manifest.json").read_text())
    eligible = {}
    for task_id in previous["tasks"]:
        task = json.loads((inputs / "tasks" / (task_id + ".json")).read_text())
        if task["method"] not in ("native-search", "native-search-joint1"):
            continue  # In particular, never load MM result files.
        record = json.loads((inputs / "results" / (task_id + ".json")).read_text())
        if any(record[k] != value for k, value in task.items()):
            raise RuntimeError("Saved result/task mismatch")
        if record["status"] != "SUCCESS" or record["source_snapshot"] != previous["source_snapshot"]:
            raise RuntimeError("Ineligible saved candidate")
        eligible[task["graph"], task["seed"], task["method"]] = (task_id, record)
    expected_keys = {(g, s, m) for g, s, m in eligible if m == "native-search"
                     for m in ("native-search", "native-search-joint1")}
    if set(eligible) != expected_keys or len(eligible) != 36:
        raise RuntimeError("Expected exactly 18 Search/Joint1 candidate pairs")
    shutil.copyfile(inputs / "target.json", run / "target.json")
    cases, tasks = {}, {}
    for graph, seed, method in sorted(eligible):
        if method != "native-search":
            continue
        incumbent_id, incumbent = eligible[graph, seed, method]
        expected_id, expected = eligible[graph, seed, "native-search-joint1"]
        case = {"graph": graph, "seed": seed, "source_hash": incumbent["source_hash"],
                "target_hash": incumbent["target_hash"], "incumbent_task_id": incumbent_id,
                "expected_task_id": expected_id,
                "incumbent_hash": digest(canonical_embedding(incumbent["embedding"])),
                "expected_hash": digest(canonical_embedding(expected["embedding"]))}
        case_id = digest(case)[:24]
        cases[case_id] = case
        shutil.copyfile(inputs / "graphs" / (graph + ".json"), run / "graphs" / (graph + ".json"))
        shutil.copyfile(inputs / "results" / (incumbent_id + ".json"), run / "incumbents" / (case_id + ".json"))
        shutil.copyfile(inputs / "results" / (expected_id + ".json"), run / "expected" / (case_id + ".json"))
        for arm, options in arms.items():
            task = {"case_id": case_id, "graph": graph, "seed": seed, "arm": arm,
                    "configuration": {**COMMON, **options}}
            tasks[digest(task)[:24]] = task
    order = {}
    rng = random.Random(16001)
    for phase in ("reference", "revisions"):
        ids = [key for key, task in tasks.items() if (task["arm"] == "legacy") == (phase == "reference")]
        rng.shuffle(ids)
        order[phase] = ids
    input_paths = [run / "target.json"] + [f for d in ("graphs", "incumbents", "expected")
                                           for f in (run / d).glob("*.json")]
    manifest = {"purpose": "refinement-only fixed-policy ablation; no MM embedding input",
                'experiment': experiment,
                "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "python": os.path.abspath(python), "inputs": str(inputs),
                "input_source_snapshot": previous["source_snapshot"],
                "input_manifest_sha256": file_digest(inputs / "manifest.json"),
                "source_files": source_files, "source_snapshot": digest(source_files),
                "input_files": {str(f.relative_to(run)): file_digest(f) for f in input_paths},
                "cases": cases, "tasks": tasks, "order": order, "threads": 1,
                "timing": "contact_polish call only; copies/imports/independent validation excluded",
                "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    write_json(run / "manifest.json", manifest)
    print("Frozen", len(cases), "incumbents,", len(tasks), "tasks; snapshot", manifest["source_snapshot"], flush=True)


def run_jobs(run):
    manifest = json.loads((run / "manifest.json").read_text())
    check_snapshot(run, manifest)
    env = os.environ.copy()
    env.update({key: "1" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS")})
    env.update(PYTHONHASHSEED="0", PYTHONNOUSERSITE="1")
    for phase in ("reference", "revisions"):
        for task_id in manifest["order"][phase]:
            output = run / "results" / (task_id + ".json")
            if output.exists():
                continue
            cache = run / "jit_cache" / task_id
            cache.mkdir(exist_ok=False)
            env["NUMBA_CACHE_DIR"] = str(cache)
            command = [manifest["python"], "-I", str(run / "source/scripts/codex/refinement_ablation.py"),
                       "worker", str(run), task_id]
            start = time.perf_counter()
            with (run / "logs" / (task_id + ".log")).open("w") as log:
                try:
                    result = subprocess.run(command, env=env, cwd=run, stdout=log, stderr=log,
                                            timeout=90, check=False)
                    code = result.returncode
                except subprocess.TimeoutExpired:
                    code = None
            record = json.loads(output.read_text()) if output.exists() else {
                "task_id": task_id, **manifest["tasks"][task_id], "status": "NO_RESULT"}
            record.update(process_wall=time.perf_counter() - start, returncode=code)
            write_json(output, record)
            print(phase, record["graph"], record["seed"], record["arm"], record["status"],
                  "qubits", record.get("qubits"), "wall", round(record.get("refinement_wall", 0), 3), flush=True)
        if phase == "reference":
            records = [json.loads((run / "results" / (t + ".json")).read_text()) for t in manifest["order"][phase]]
            passed = all(r["status"] == "SUCCESS" and r.get("returncode") == 0
                         and r.get("saved_reference_embedding_match")
                         and r.get("saved_reference_quality_match") for r in records)
            write_json(run / "reference_gate.json", {"passed": passed, "cases": len(records),
                       "source_snapshot": manifest["source_snapshot"],
                       "result_hashes": {r["task_id"]: file_digest(run / "results" / (r["task_id"] + ".json")) for r in records}})
            if not passed:
                raise RuntimeError("Legacy replay gate failed; revised arms were not launched")
            print("All 18 legacy embeddings and quality match; launching fixed revisions", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("run", type=Path)
    prep.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    prep.add_argument("--python", default=str(ROOT / ".venv/codex-native/bin/python"))
    prep.add_argument('--experiment', choices=EXPERIMENTS, default='sites-groups')
    execute = sub.add_parser("run")
    execute.add_argument("run", type=Path)
    child = sub.add_parser("worker")
    child.add_argument("run", type=Path)
    child.add_argument("task_id")
    args = parser.parse_args()
    run = args.run.absolute()
    if args.action == "prepare":
        prepare(run, args.inputs.absolute(), args.python, args.experiment)
    elif args.action == "run":
        run_jobs(run)
    else:
        worker(run, args.task_id)


if __name__ == "__main__":
    main()
