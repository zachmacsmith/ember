from qebench import EmbeddingBenchmark
from qeanalysis import BenchmarkAnalysis



bench = EmbeddingBenchmark(target_graph=None)
direc = bench.run_full_benchmark(
    graph_selection='100-130',
    topologies=['chimera_4x4x4'],
    methods=['minorminer','clique','atom','oct-triad','oct-triad-reduce','oct-fast-oct','oct-fast-oct-reduce'],
    n_trials=5,
    warmup_trials=1,
    timeout=60,
    batch_note='Random graphs 100-199 on chimera_4x4x4',
)

an = BenchmarkAnalysis(direc)
an.generate_report()
