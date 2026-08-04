"""
docs/paper2/data/fullember2.py — the second full-Ember sweep (s3.67).
Consolidated algorithm (41ca50ed: one accounting, vcycle stride-gated,
outcome-first doctrine) vs stock minorminer, paired seed, BOTH fabrics.
Analysis: analyze_fullember.py on the batch dir. Sentinel: done-probe.

Run:  nohup .venv/bin/python docs/paper2/data/fullember2.py \
        > /data/max/fullember2.log 2>&1 &
"""
import os
os.chdir("/data/max/ember")
from ember_qc.benchmark import EmbeddingBenchmark

for topo in ("pegasus_16", "zephyr_12"):
    bench = EmbeddingBenchmark(target_graph=None)
    d = bench.run_full_benchmark(
        graph_selection="*",
        topologies=[topo],
        methods=["attraction", "minorminer"],
        n_trials=1,
        timeout=60,
        batch_note=f"s3.67 full-Ember sweep 2: consolidated attraction "
                   f"vs stock mm, {topo}, paired seed",
    )
    print(f"batch done ({topo}):", d, flush=True)
print("done-probe", flush=True)
