"""Validate and summarize the completed shared-partition audit, without imports
from the implementation or benchmark harness. Run only after all five artifacts
are complete: python docs/paper2/data/partition_summary.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics as stats
import struct


HERE = Path(__file__).resolve().parent
BOARD = ("K100", "K140", "ER100_d10", "turan_n162", "spin_glass_n163",
         "regular_n316", "ws_n486", "grid_200", "honeycomb_200", "king_graph_196")
MICRO = {"K100": 100, "ER100_d10": 100, "grid_200": 200}
NO_FIT = "no native embedding fitting the chip was found within the budget"
WORK = ("asks", "passes", "accepts", "strict_accepts", "neutral_accepts",
        "borrowed_accepts", "whole_order_accepts", "dp_solves", "dp_cells",
        "direct_scores", "candidate_pairs", "candidate_duplicates",
        "unique_partitions", "nomination_duplicates", "nomination_wall",
        "preparation_wall", "transition_wall", "dp_wall", "direct_wall",
        "interleave_wall", "packing_wall", "decode_wall", "decode_calls",
        "adopt_worse", "repeated_sweep_states")
MICRO_METRICS = ("preparation_wall", "transition_wall", "dp_wall", "direct_wall",
                 "strand_solves", "dp_cells", "direct_scores", "candidate_pairs",
                 "candidate_duplicates", "borrow_side", "borrow_size")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def arrays_hash(snapshot):
    """Match the saved NumPy int64 array hash using only standard-library bytes."""
    digest = hashlib.sha256()
    for name in ("orders", "coords", "indptr", "indices"):
        values = snapshot[name]
        matrix = bool(values) and isinstance(values[0], list)
        shape = (len(values), len(values[0])) if matrix else (len(values),)
        flat = [v for row in values for v in row] if matrix else values
        digest.update(str(shape).encode())
        digest.update(b"int64")
        digest.update(struct.pack(f"={len(flat)}q", *flat))
    return digest.hexdigest()


def indexed(rows, key, expected, label):
    result = {key(row): row for row in rows}
    require(len(result) == len(rows) and set(result) == expected,
            f"{label}: missing, extra, or duplicate cases")
    return result


def median(values):
    values = [v for v in values if v is not None]
    return stats.median(values) if values else None


def distribution(values):
    values = list(values)
    return dict(total=sum(values), median=median(values), maximum=max(values, default=None))


def work(row):
    return {name: row.get(name, row.get("diag", {}).get(name)) for name in WORK}


def total_work(rows):
    values = [work(row) for row in rows]
    return {name: sum(v[name] for v in values) if all(v[name] is not None for v in values)
            else None for name in WORK}


def startup(artifact):
    return [session["startup"] for session in artifact["sessions"]]


def completed_states(row):
    sweeps = [s for s in row["diag"]["sweep_traj"]
              if s["pass_index"] > 0 and s["complete"] and s["decode_complete"]]
    comparable = [s for s in sweeps if s["bookmark_score"] is not None]
    gaps = [s["current_score"][1] - s["bookmark_score"][1] for s in comparable
            if s["current_score"][0] == s["bookmark_score"][0] == 0]
    return dict(completed_sweeps=len(sweeps), comparable_sweeps=len(comparable),
                above_bookmark=sum(tuple(s["current_score"]) > tuple(s["bookmark_score"])
                                   for s in comparable),
                max_in_chip_reserved_gap=max(gaps, default=None),
                last_completed=sweeps[-1] if sweeps else None)


def board_summary(rows):
    valid = [r for r in rows if r["success"]]
    return dict(runs=len(rows), successes=len(valid),
                physical_qubits={"median": median(r["physical_qubits"] for r in valid),
                                  "mean": stats.mean(r["physical_qubits"] for r in valid)
                                  if valid else None},
                average_chain_median=median(r["acl"] for r in valid),
                maximum_chain_median=median(r["max_chain"] for r in valid),
                elapsed_seconds=distribution(r["elapsed_seconds"] for r in rows),
                work=total_work(rows),
                stopped_by={reason: sum(r["stopped_by"] == reason for r in rows)
                            for reason in sorted({r["stopped_by"] for r in rows})})


def paired_quality(baseline, new):
    common = [key for key in baseline if baseline[key]["success"] and new[key]["success"]]
    ratios = [new[key]["physical_qubits"] / baseline[key]["physical_qubits"] for key in common]
    return dict(common_successes=len(common), wins=sum(r < 1 for r in ratios),
                ties=sum(r == 1 for r in ratios), losses=sum(r > 1 for r in ratios),
                geometric_mean_qubit_ratio=math.exp(stats.mean(map(math.log, ratios)))
                if ratios else None,
                new_only_successes=sum(new[k]["success"] and not baseline[k]["success"]
                                       for k in baseline),
                baseline_only_successes=sum(baseline[k]["success"] and not new[k]["success"]
                                            for k in baseline))


def row_summary(row):
    return dict(cell=row["cell"], seed=row["seed"], success=row["success"],
                error=row["error"],
                physical_qubits=row["physical_qubits"], average_chain=row["acl"],
                max_chain=row["max_chain"], elapsed_seconds=row["elapsed_seconds"],
                work=work(row), current=row["current"], bookmark=row["bookmark"],
                failure=None if row["success"] else dict(
                    reason=row["error"], stopped_by=row["stopped_by"],
                    outside_reserved_qubits=row["outside_reserved_qubits"],
                    reserved_qubits=row["reserved_qubits"],
                    best_expanded_score=row["diag"].get("best_expanded_score")),
                completed_states=completed_states(row))


def micro_group(queries):
    # Equal weight per fixed query: each contributes its own 20-repeat median.
    result = dict(queries=len(queries),
                  median_paired_elapsed_ratio=median(q["elapsed_median_ratio"] for q in queries))
    for policy in ("baseline", "new"):
        result[policy] = dict(elapsed_median=median(q[policy]["elapsed_median"] for q in queries),
            metrics={name: median(q[policy]["metrics"][name] for q in queries) for name in MICRO_METRICS})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=HERE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths, artifacts = {}, {}
    for name in ("baseline", "validation", "snapshots", "board_baseline", "board_new",
                 "micro_baseline", "micro_new", "fingerprint_new"):
        paths[name] = args.directory / f"partition_{name}.json"
        artifacts[name] = json.loads(paths[name].read_text())
    hashes = {"baseline": artifacts["baseline"]["source_sha256"],
              "new": artifacts["validation"]["source_sha256"]}
    snapshots = artifacts["snapshots"]
    require(snapshots["complete"] and snapshots["baseline_source_sha256"] == hashes["baseline"],
            "snapshot baseline/complete mismatch")
    require(content_hash(snapshots["snapshots"]) == snapshots["content_sha256"],
            "snapshot contents do not match hash")
    snap = indexed(snapshots["snapshots"], lambda r: r["cell"], set(MICRO), "snapshots")
    require(snapshots["mm_calls"] == 0, "snapshot MinorMiner calls")
    boards, micros, fingerprints = {}, {}, None
    provenance = []
    for name in ("board_baseline", "board_new", "micro_baseline", "micro_new", "fingerprint_new"):
        artifact = artifacts[name]
        policy = name.rsplit("_", 1)[1]
        require(artifact["complete"], f"{name}: audit not complete")
        require(artifact["provenance"]["policy"] == policy and
                artifact["provenance"]["code_hash"] == hashes[policy], f"{name}: source mismatch")
        provenance.append(artifact["provenance"])
        for row in artifact["rows"]:
            require(row["code_hash"] == hashes[policy] and row["policy"] == policy,
                    f"{name}: row source/policy mismatch")
            require(row["mm_calls"] == row["compilation_seconds"] == 0,
                    f"{name}: timed compilation or MinorMiner calls")
        if name.startswith("board"):
            boards[policy] = indexed(artifact["rows"], lambda r: (r["cell"], r["seed"]),
                                      {(cell, seed) for cell in BOARD for seed in range(3)}, name)
        elif name.startswith("micro"):
            expected = {(cell, axis, size) for cell, n in MICRO.items() for axis in range(3)
                        for size in (1, 2, n // 4, n // 2, n - 2, n - 1, n)}
            micros[policy] = indexed(artifact["rows"], lambda r: (r["cell"], r["axis"], r["size"]),
                                      expected, name)
            require(artifact["provenance"]["snapshots_sha256"] == snapshots["content_sha256"],
                    f"{name}: mismatched snapshot source")
        else:
            expected = {(cell, 0) for cell in ("K8", "K10", "K100", "path60", "grid_200")}
            expected.update(("turan_n162", seed) for seed in range(10))
            fingerprints = indexed(artifact["rows"], lambda r: (r["cell"], r["seed"]), expected, name)
    for field in ("harness_sha256", "loaders_sha256", "validator_sha256",
                  "minorminer_sha256", "python", "dependencies"):
        require(all(p[field] == provenance[0][field] for p in provenance), f"mismatched {field}")
    for key, old in boards["baseline"].items():
        new = boards["new"][key]
        for field in ("input_sha256", "target_sha256", "n", "edges", "target_m", "target_tile"):
            require(old[field] == new[field], f"{key}: paired {field} mismatch")
        for row in (old, new):
            require(row["timeout_seconds"] == 10 and row["max_asks"] is None and
                    row["sched_seed"] == row["seed"] and row["warm_timing_clean"],
                    f"{key}: board timing/schedule mismatch")
    for row in [r for values in boards.values() for r in values.values()] + list(fingerprints.values()):
        require(row["diag"].get("mm_calls", 0) == 0,
                f"{row['cell']}: internal MinorMiner")
        require(not any(report.get("validation_error") for report in
                        (row, row.get("current") or {}, row.get("bookmark") or {})),
                f"{row['cell']}: physical validation error")
        if row["success"]:
            require(row["error"] is None and row["bookmark"] is not None and row["bookmark"]["valid"] and
                    row["bookmark"]["physical_qubits"] == row["physical_qubits"],
                    f"{row['cell']}: returned bookmark is not independently valid")
        else:
            require(row["error"] == NO_FIT and row["bookmark"] is None and
                    row["physical_qubits"] is None,
                    f"{row['cell']}: unexpected failure or invalid returned embedding")
    fingerprint_limits = {"K8": (2000, 120), "K10": (2000, 120), "K100": (10000, 900),
                          "path60": (3000, 300), "grid_200": (8000, 900), "turan_n162": (15000, 900)}
    for (cell, seed), row in fingerprints.items():
        require((row["max_asks"], row["timeout_seconds"]) == fingerprint_limits[cell] and
                row["sched_seed"] == seed and row["warm_timing_clean"], "fingerprint limits mismatch")
        if cell in BOARD:
            board = boards["new"][(cell, 0)]
            require(row["input_sha256"] == board["input_sha256"] and
                    row["target_sha256"] == board["target_sha256"], "fingerprint graph mismatch")
    query_rows, score_changes = [], [0, 0]
    for key, old in sorted(micros["baseline"].items()):
        new = micros["new"][key]
        cell, axis, size = key
        snapshot = snap[cell]
        for field in ("input_sha256", "arrays_sha256", "unit", "n", "edges"):
            require(old[field] == new[field], f"{key}: query {field} mismatch")
        require(old["input_sha256"] == snapshot["input_sha256"] == boards["baseline"][(cell, 0)]["input_sha256"]
                and old["arrays_sha256"] == arrays_hash(snapshot)
                and old["unit"] == snapshot["orders"][axis][:size], f"{key}: query snapshot mismatch")
        sizes = (1, 2, old["n"] // 4, old["n"] // 2, old["n"] - 2, old["n"] - 1, old["n"])
        size_label = ("1", "2", "n/4", "n/2", "n-2", "n-1", "n")[sizes.index(size)]
        result = dict(cell=cell, axis=axis, size=size, size_label=size_label, n=old["n"])
        for policy, row in (("baseline", old), ("new", new)):
            reps = row["repetitions"]
            require(len(reps) == 20 and {r["repetition"] for r in reps} == set(range(20)),
                    f"{key}: incomplete repetitions")
            signatures = set()
            for rep in reps:
                m = rep["metrics"]
                require(rep["compilation_seconds"] == 0 and m["complete"], f"{key}: incomplete/cold query")
                require(tuple(m["score"]) <= tuple(m["baseline_score"]), f"{key}: query worsened incumbent")
                signatures.add((rep["changed"], rep["flipped"], rep["result_sha256"], tuple(m["score"])))
            require(len(signatures) == 1, f"{key}: repeated query nondeterministic")
            result[policy] = dict(score=reps[0]["metrics"]["score"],
                                  elapsed_median=median(r["elapsed_seconds"] for r in reps),
                                  elapsed_total=sum(r["elapsed_seconds"] for r in reps),
                                  metrics={m: median(r["metrics"].get(m) for r in reps) for m in MICRO_METRICS})
        require(old["repetitions"][0]["metrics"]["baseline_score"] ==
                new["repetitions"][0]["metrics"]["baseline_score"], f"{key}: differing baseline scores")
        a, b = tuple(result["baseline"]["score"]), tuple(result["new"]["score"])
        require(b <= a, f"{key}: enlarged family returned worse optimum")
        score_changes[int(b == a)] += 1
        result["elapsed_median_ratio"] = result["new"]["elapsed_median"] / result["baseline"]["elapsed_median"]
        query_rows.append(result)
    summary = dict(schema=1, source_hashes=hashes,
                   artifact_sha256={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()},
                   validation=dict(board_runs=60, fingerprint_runs=15, micro_queries_per_arm=63,
                                   repetitions_per_query=20, timed_micro_calls=2520,
                                   paired_inputs_match=True, timed_compilation_seconds=0, mm_calls=0,
                                   micro_strict_improvements=score_changes[0], micro_ties=score_changes[1]),
                   notes=["Preparation time includes transition construction; do not add both.",
                          "Missing baseline counters remain null, not zero.",
                          "Completed-sweep gaps exclude partial sweeps and incomplete decodes.",
                          "Micro groups summarize per-query 20-repeat medians; ratios are paired before aggregation.",
                          "Quality aggregates include successful runs only; paired ratios use joint successes."],
                   board={}, paired=paired_quality(boards["baseline"], boards["new"]),
                   micro=dict(queries=query_rows), fingerprint=dict(
                       total=board_summary(list(fingerprints.values())),
                       rows=[row_summary(r) for r in fingerprints.values()],
                       startup=startup(artifacts["fingerprint_new"])))
    for policy, rows_by_key in boards.items():
        rows = list(rows_by_key.values())
        summary["board"][policy] = dict(total=board_summary(rows),
            by_case={cell: board_summary([r for r in rows if r["cell"] == cell]) for cell in BOARD},
            rows=[row_summary(r) for r in rows],
            startup=startup(artifacts[f"board_{policy}"]))
        states = [completed_states(r) for r in rows]
        last = [s["last_completed"] for s in states
                if s["last_completed"] is not None and s["last_completed"]["bookmark_score"] is not None]
        summary["board"][policy]["completed_states"] = dict(
            completed_sweeps=sum(s["completed_sweeps"] for s in states),
            comparable_sweeps=sum(s["comparable_sweeps"] for s in states),
            above_bookmark=sum(s["above_bookmark"] for s in states),
            last_comparable_runs=len(last),
            last_at_bookmark=sum(s["current_score"] == s["bookmark_score"] for s in last),
            last_above_bookmark=sum(tuple(s["current_score"]) > tuple(s["bookmark_score"]) for s in last),
            max_in_chip_reserved_gap=max((s["max_in_chip_reserved_gap"] for s in states
                                           if s["max_in_chip_reserved_gap"] is not None), default=None))
    for policy in ("baseline", "new"):
        summary["micro"][policy] = dict(startup=startup(artifacts[f"micro_{policy}"]),
            actual_elapsed_seconds=sum(q[policy]["elapsed_total"] for q in query_rows))
    summary["micro"]["by_size"] = {label: micro_group([q for q in query_rows if q["size_label"] == label])
                                       for label in ("1", "2", "n/4", "n/2", "n-2", "n-1", "n")}
    summary["micro"]["by_cell"] = {cell: micro_group([q for q in query_rows if q["cell"] == cell])
                                       for cell in MICRO}
    summary["micro"]["by_axis"] = {str(axis): micro_group([q for q in query_rows if q["axis"] == axis])
                                       for axis in range(3)}
    output = args.output or args.directory / "partition_summary.json"
    output.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(f"Validated 60 board runs, 15 fingerprints, and 2520 micro calls; wrote {output}")


if __name__ == "__main__":
    main()
