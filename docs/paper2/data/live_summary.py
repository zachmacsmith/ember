"""Validate and summarize the completed live-reference/streamed-cost audit."""
from __future__ import annotations
import json
import statistics
from pathlib import Path
import feedback_board as common
from live_bench import POLICIES

HERE = Path(__file__).resolve().parent


def load(suite, policy, count):
    path = HERE / f"live_{suite}_{policy}.json"
    result = json.loads(path.read_text())
    if not result.get("complete") or len(result["rows"]) != count:
        raise AssertionError(f"incomplete {path.name}: {len(result['rows'])}/{count}")
    return result


def native_rows(rows):
    for row in rows:
        if row.get("validation_error") or row.get("mm_calls", 0):
            raise AssertionError("native validity/MM violation")
        if row.get("compilation_seconds", 0):
            raise AssertionError("cold compilation contaminated warm measurement")


def aggregate(rows):
    valid = [row for row in rows if row["success"]]
    result = dict(cases=len(rows), successes=len(valid),
                  elapsed_seconds=sum(row["elapsed_seconds"] for row in rows),
                  physical_qubits=sum(row["physical_qubits"] for row in valid),
                  mean_acl=statistics.mean(row["acl"] for row in valid) if valid else None,
                  mean_max_chain=statistics.mean(row["max_chain"] for row in valid) if valid else None,
                  mm_calls=sum(row["mm_calls"] for row in rows))
    for name in ("asks", "passes", "decode_calls", "dp_solves", "dp_cells", "preparation_wall",
                 "transition_wall", "dp_wall", "packing_wall", "decode_wall", "interleave_wall",
                 "completed_rounds", "reference_visits", "event_states", "event_updates",
                 "strand_preparations", "traceback_checks", "tracebacks"):
        values = [row[name] for row in rows if row.get(name) is not None]
        result[name] = sum(values) if values else None
    result["early_quality"] = {}
    for limit in ("0.01", "0.1", "1.0", "10.0"):
        values = [row["early_quality"][limit] for row in rows if row.get("early_quality")]
        available = [value for value in values if value]
        result["early_quality"][limit] = dict(successes=len(available),
            physical_qubits=sum(value["physical_qubits"] for value in available)) if values else None
    relation_work = {}
    for row in rows:
        for relation, metrics in (row.get("relation_work") or {}).items():
            total = relation_work.setdefault(relation, {})
            for name, value in metrics.items():
                if isinstance(value, (int, float)):
                    total[name] = total.get(name, 0) + value
    # Loop-only kernels do not expose streamed event counters. Explicitly mark
    # these unavailable instead of interpreting the new loop's default zeros.
    if rows and not rows[0].get("event_metrics_available"):
        for total in relation_work.values():
            for name in ("event_states", "event_updates", "strand_preparations", "traceback_checks", "tracebacks"):
                total[name] = None
    result["relation_work"] = relation_work
    return result


def paired(left, right):
    a = {common.job_key(row): row for row in left}
    b = {common.job_key(row): row for row in right}
    keys = sorted(a.keys() & b.keys())
    for key in keys:
        if a[key]["input_sha256"] != b[key]["input_sha256"] or a[key]["target_sha256"] != b[key]["target_sha256"]:
            raise AssertionError("paired graph mismatch")
    keys = [key for key in keys if a[key]["success"] and b[key]["success"]]
    old = sum(a[key]["physical_qubits"] for key in keys)
    new = sum(b[key]["physical_qubits"] for key in keys)
    return dict(paired_successes=len(keys), before_physical_qubits=old, after_physical_qubits=new,
                qubit_ratio=new / old if old else None,
                wins=sum(b[key]["physical_qubits"] < a[key]["physical_qubits"] for key in keys),
                ties=sum(b[key]["physical_qubits"] == a[key]["physical_qubits"] for key in keys),
                losses=sum(b[key]["physical_qubits"] > a[key]["physical_qubits"] for key in keys))


def main():
    board = {policy: load("board", policy, 30) for policy in POLICIES}
    fingerprint = load("fingerprint", "full", 15)
    micro = {policy: load("micro", policy, 63) for policy in ("baseline", "full")}
    for policy, artifact in board.items():
        if policy != "mm":
            native_rows(artifact["rows"])
    native_rows(fingerprint["rows"])
    signature_keys = ("score", "baseline_score", "donor", "donor_mask", "borrow_side", "borrow_size", "borrowed", "strict")
    micro_rows = {policy: {(row["cell"], row["axis"], row["size"]): row for row in artifact["rows"]}
                  for policy, artifact in micro.items()}
    query_summary = []
    for key, old in micro_rows["baseline"].items():
        new = micro_rows["full"][key]
        if old["arrays_sha256"] != new["arrays_sha256"] or old["unit"] != new["unit"]:
            raise AssertionError("micro input mismatch")
        for row in (old, new):
            if len(row["repetitions"]) != 20:
                raise AssertionError("micro requires twenty repetitions per query")
            native_rows(row["repetitions"])
        for a, b in zip(old["repetitions"], new["repetitions"]):
            for name in ("changed", "flipped", "result_sha256"):
                if a[name] != b[name]:
                    raise AssertionError(f"micro exact result mismatch {key}: {name}")
            for name in signature_keys:
                if a["metrics"].get(name) != b["metrics"].get(name):
                    raise AssertionError(f"micro exact provenance mismatch {key}: {name}")
        before = statistics.median(row["elapsed_seconds"] for row in old["repetitions"])
        after = statistics.median(row["elapsed_seconds"] for row in new["repetitions"])
        query_summary.append(dict(cell=key[0], axis=key[1], size=key[2],
            baseline_median_seconds=before, full_median_seconds=after,
            speedup=before / after,
            baseline_metrics=old["repetitions"][0]["metrics"], full_metrics=new["repetitions"][0]["metrics"]))
    artifacts = [*board.values(), fingerprint, *micro.values()]
    result = dict(complete=True, board={policy: aggregate(artifact["rows"]) for policy, artifact in board.items()},
                  pairs={f"{a}_to_{b}": paired(board[a]["rows"], board[b]["rows"])
                         for a, b in (("baseline", "loop"), ("baseline", "full"), ("loop", "full"), ("mm", "full"))},
                  fingerprints=aggregate(fingerprint["rows"]),
                  micro=dict(queries=63, repetitions_per_query=20, exact_matches=63,
                             total_baseline_seconds=sum(row["elapsed_seconds"] for row in micro["baseline"]["rows"]),
                             total_full_seconds=sum(row["elapsed_seconds"] for row in micro["full"]["rows"]),
                             median_query_speedup=statistics.median(row["speedup"] for row in query_summary),
                             queries_detail=query_summary),
                  compile_sessions=[dict(policy=artifact["provenance"]["policy"], sessions=artifact["sessions"])
                                    for artifact in artifacts],
                  equivalence=json.loads((HERE / "live_equivalence.json").read_text()))
    common.save(HERE / "live_summary.json", result)
    print(json.dumps({key: value for key, value in result.items() if key not in ("micro", "compile_sessions")}, indent=2))
    print("micro seconds baseline/full:", result["micro"]["total_baseline_seconds"], result["micro"]["total_full_seconds"])
    print("median micro speedup:", result["micro"]["median_query_speedup"])


if __name__ == "__main__":
    main()
