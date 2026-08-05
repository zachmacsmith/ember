"""
docs/paper2/data/fullember3.py — the third full-Ember sweep (s3.67).

One batch per invocation (a single phase x topology cell) so the external
supervisor (fullember3_supervisor.py) can kill/resume/relaunch cleanly.
Consolidated attraction vs stock minorminer vs the busclique template arm
(`clique`), paired seed. Runs on the patched JSONL-progress runner (the
result-queue feeder-starvation hang is gone; diagnosis:
/data/max/fullember3/diagnosis.log).

Usage:
  fullember3.py phaseA|phaseB|smoke <topology> [--workers N]
                [--resume BATCH_ID]

Exit codes: 0 = phase complete (batch compiled + promoted to results/);
            3 = incomplete but checkpointed (relaunch with --resume);
            1 = error.
"""
import argparse
import json
import os
import random
import sys
from pathlib import Path

os.chdir("/data/max/ember")

from ember_qc.benchmark import EmbeddingBenchmark, load_benchmark

ALGOS = ["attraction", "minorminer", "clique"]
SEED = 42
TIMEOUT = 60
STAGING = "/data/max/ember-qc-data/ember-qc/runs_unfinished"
RESULTS = "/data/max/ember/results"
PHASE_RESULTS = Path("/data/max/fullember3/phase_results.jsonl")

SMOKE_SIZE_PER_CAT = 10
SMOKE_FORCED = [37900, 37901]  # sudoku_n9 (6561), sudoku_n16 (65536: skipped by compat)


def smoke_selection() -> str:
    """Deterministic stratified sample: ~10 graphs per category spread across
    each category's size range, plus forced historical hangers (sudoku) and
    extra star/wheel/large representation. Returns a selection spec string."""
    from ember_qc.load_graphs import _manifest_by_id, _graph_dedup_info
    man = _manifest_by_id()
    skip, _ = _graph_dedup_info()
    by_cat = {}
    for gid, e in sorted(man.items()):
        if gid in skip:
            continue
        by_cat.setdefault(e.get("category", "?"), []).append((e.get("nodes", 0), gid))
    rng = random.Random(SEED)
    ids = set(SMOKE_FORCED)
    for cat, entries in by_cat.items():
        entries.sort()
        k = min(SMOKE_SIZE_PER_CAT, len(entries))
        # evenly spaced across the size-sorted list = spread across sizes
        step = max(1, len(entries) // k)
        picks = entries[::step][:k]
        ids.update(gid for _, gid in picks)
        # extra tail representation: the largest member of every category
        ids.add(entries[-1][1])
    # extra stars and wheels (historical spur_prune hangers), mid+large sizes
    for cat in ("star", "wheel"):
        entries = sorted(by_cat.get(cat, []))
        ids.update(gid for _, gid in entries[-6:])
    # ~30 additional n>1000 graphs across categories
    big = sorted((n, gid) for cat, es in by_cat.items() for n, gid in es
                 if n > 1000)
    ids.update(gid for _, gid in rng.sample(big, min(30, len(big))))
    return ",".join(str(g) for g in sorted(ids))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["phaseA", "phaseB", "smoke"])
    ap.add_argument("topology")
    ap.add_argument("--workers", type=int, default=100)
    ap.add_argument("--resume", default=None, metavar="BATCH_ID")
    args = ap.parse_args()

    if args.resume:
        final = load_benchmark(
            batch_id=args.resume, unfinished_dir=STAGING, output_dir=RESULTS,
            n_workers=args.workers, verbose=False, confirm=False,
        )
    else:
        if args.phase == "phaseA":
            node_args = {"max_nodes": 1000}
            selection = "*"
        elif args.phase == "phaseB":
            node_args = {"min_nodes": 1001}
            selection = "*"
        else:
            node_args = {}
            selection = smoke_selection()
        bench = EmbeddingBenchmark(target_graph=None, results_dir=RESULTS,
                                   unfinished_dir=STAGING)
        final = bench.run_full_benchmark(
            graph_selection=selection,
            topologies=[args.topology],
            methods=ALGOS,
            n_trials=1,
            timeout=TIMEOUT,
            seed=SEED,
            n_workers=args.workers,
            verbose=False,
            **node_args,
            batch_note=(f"s3.67 full-Ember sweep 3 [{args.phase}/{args.topology}]: "
                        f"attraction vs minorminer vs clique, paired seed"),
        )

    if final is None:
        print("PHASE_CHECKPOINTED", flush=True)
        return 3
    final = Path(final)
    if str(final).startswith(STAGING):
        # load_benchmark returns the staging dir when the session ended
        # cancelled/incomplete — still resumable.
        print(f"PHASE_CHECKPOINTED {final.name}", flush=True)
        return 3

    with open(PHASE_RESULTS, "a") as f:
        f.write(json.dumps({"phase": args.phase, "topology": args.topology,
                            "final_dir": str(final.resolve())}) + "\n")
    print(f"PHASE_DONE {final.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
