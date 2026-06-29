"""
Training-data generation: randomized problem graphs labelled with PathFinder-
optimized embeddings (the "embeddings cache" of the patent). Each record is a
(graph, target, embedding, metrics) tuple; the supervised target for a vertex is
the centroid (in hardware coordinates) of its PF chain — derived at load time.

Splits are INSTANCE-DISJOINT (different seed ranges per split) so train/val/test
never share a graph. Reuses ember_qc's registry (pathfinder-thorough labeller)
and a ProcessPoolExecutor, mirroring docs/paper/data/run_sweep_opt.py.

CLI:
  python -m ember_qc_learn.datagen --out data/learn --scale small
  python -m ember_qc_learn.datagen --out data/learn --scale cluster --workers 120
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Optional, Tuple

import networkx as nx


# --------------------------------------------------------------------- config

@dataclasses.dataclass
class GenConfig:
    families: Tuple[str, ...] = ("ER", "REG", "BA", "GEO")
    sizes: Tuple[int, ...] = (12, 18, 24, 32, 40)
    er_densities: Tuple[float, ...] = (0.2, 0.35, 0.5, 0.7)
    reg_degrees: Tuple[int, ...] = (3, 4, 6)
    ba_m: Tuple[int, ...] = (2, 3, 5)
    geo_radius: Tuple[float, ...] = (0.30, 0.40, 0.55)
    targets: Tuple[str, ...] = ("pegasus_6", "zephyr_4")
    labeller: str = "pathfinder-thorough"
    label_seed: int = 0
    timeout: float = 20.0
    # instances per (family, size, param) cell, per split
    n_train: int = 12
    n_val: int = 3
    n_test: int = 3


SCALES = {
    "smoke": GenConfig(families=("ER", "BA"), sizes=(12, 20), er_densities=(0.3, 0.5),
                       ba_m=(2, 3), reg_degrees=(3,), geo_radius=(0.4,),
                       targets=("pegasus_6",), n_train=2, n_val=1, n_test=1, timeout=12.0),
    "small": GenConfig(n_train=6, n_val=2, n_test=2),
    "cluster": GenConfig(sizes=(10, 16, 22, 30, 40, 50), n_train=20, n_val=4, n_test=4,
                         timeout=25.0),
}


# --------------------------------------------------------------------- graph gen

def gen_graph(family: str, n: int, param, seed: int) -> Optional[nx.Graph]:
    """Deterministic random graph, integer-labelled 0..n-1. None if params invalid."""
    try:
        if family == "ER":
            g = nx.gnp_random_graph(n, float(param), seed=seed)
        elif family == "REG":
            d = int(param)
            if d >= n or (n * d) % 2 != 0:
                return None
            g = nx.random_regular_graph(d, n, seed=seed)
        elif family == "BA":
            m = int(param)
            if m >= n:
                return None
            g = nx.barabasi_albert_graph(n, m, seed=seed)
        elif family == "GEO":
            g = nx.random_geometric_graph(n, float(param), seed=seed)
        else:
            return None
    except Exception:
        return None
    g = nx.convert_node_labels_to_integers(g)
    if g.number_of_edges() == 0:
        return None
    return g


def _cells(cfg: GenConfig):
    """Yield (family, n, param) cells."""
    for n in cfg.sizes:
        for fam in cfg.families:
            params = {"ER": cfg.er_densities, "REG": cfg.reg_degrees,
                      "BA": cfg.ba_m, "GEO": cfg.geo_radius}[fam]
            for p in params:
                yield fam, n, p


def _split_seed(split: str, fam: str, n: int, p, i: int) -> int:
    """Disjoint per-split seed (instance i of a cell)."""
    base = {"train": 1_000, "val": 5_000_000, "test": 9_000_000}[split]
    h = abs(hash((fam, n, round(float(p), 4)))) % 100_000
    return base + h * 100 + i


def make_instances(cfg: GenConfig, split: str) -> List[Dict]:
    """All problem-graph instances for a split (instance-disjoint across splits)."""
    n_inst = {"train": cfg.n_train, "val": cfg.n_val, "test": cfg.n_test}[split]
    out = []
    for fam, n, p in _cells(cfg):
        for i in range(n_inst):
            s = _split_seed(split, fam, n, p, i)
            g = gen_graph(fam, n, p, s)
            if g is None:
                continue
            gid = f"{split}-{fam}-n{n}-p{p}-i{i}"
            out.append({"id": gid, "family": fam, "n": n, "param": float(p),
                        "seed": s, "edges": [[int(u), int(v)] for u, v in g.edges()]})
    return out


# --------------------------------------------------------------------- labelling

_TARGETS: Dict = {}
_CFG: Optional[GenConfig] = None


def _init(cfg_json: str) -> None:
    global _TARGETS, _CFG
    import warnings; warnings.filterwarnings("ignore")
    import ember_qc  # noqa: F401  (populate registry)
    import dwave_networkx as dnx
    _CFG = GenConfig(**json.loads(cfg_json))
    builders = {"pegasus_6": lambda: dnx.pegasus_graph(6),
                "zephyr_4": lambda: dnx.zephyr_graph(4)}
    _TARGETS = {t: builders[t]() for t in _CFG.targets}


def _label_one(rec: Dict) -> Dict:
    """Label one instance against all targets with the configured labeller."""
    from ember_qc.registry import ALGORITHM_REGISTRY
    from ember_qc.embedding_backend import is_valid_embedding
    g = nx.Graph(); g.add_nodes_from(range(rec["n"]))
    g.add_edges_from((u, v) for u, v in rec["edges"])
    algo = ALGORITHM_REGISTRY[_CFG.labeller]
    labels = {}
    for tname, tgt in _TARGETS.items():
        try:
            res = algo.embed(g, tgt, timeout=_CFG.timeout, seed=_CFG.label_seed) or {}
            emb = res.get("embedding") or {}
            if emb and is_valid_embedding({int(k): list(v) for k, v in emb.items()}, g, tgt):
                chains = {int(k): [int(q) for q in v] for k, v in emb.items()}
                acl = sum(len(c) for c in chains.values()) / max(len(chains), 1)
                labels[tname] = {"embedding": {str(k): v for k, v in chains.items()},
                                 "acl": acl,
                                 "qubits": sum(len(c) for c in chains.values()),
                                 "maxchain": max((len(c) for c in chains.values()), default=0)}
        except Exception as e:
            labels[tname] = {"error": str(e)[:200]}
    return {**rec, "labels": labels}


def generate(out_dir: str, cfg: GenConfig, workers: int) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "config.json"), "w") as f:
        json.dump(dataclasses.asdict(cfg), f, indent=2)
    cfg_json = json.dumps(dataclasses.asdict(cfg))
    summary = {}
    for split in ("train", "val", "test"):
        insts = make_instances(cfg, split)
        print(f"[{split}] {len(insts)} instances × {len(cfg.targets)} targets "
              f"({cfg.labeller}, timeout {cfg.timeout}s, workers {workers})", flush=True)
        t0 = time.perf_counter()
        rows, done = [], 0
        with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                                 initargs=(cfg_json,)) as ex:
            for r in ex.map(_label_one, insts, chunksize=1):
                rows.append(r); done += 1
                if done % 50 == 0:
                    print(f"  {done}/{len(insts)} ({time.perf_counter()-t0:.0f}s)", flush=True)
        path = os.path.join(out_dir, f"{split}.jsonl")
        n_valid = 0
        with open(path, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
                n_valid += sum(1 for t in r["labels"].values() if "embedding" in t)
        summary[split] = {"instances": len(rows), "valid_labels": n_valid}
        print(f"[{split}] wrote {path}: {len(rows)} instances, {n_valid} valid labels "
              f"({time.perf_counter()-t0:.0f}s)", flush=True)
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump({"config": dataclasses.asdict(cfg), "summary": summary}, f, indent=2)
    print("manifest:", summary, flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/learn")
    ap.add_argument("--scale", default="small", choices=list(SCALES))
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()
    generate(args.out, SCALES[args.scale], args.workers)


if __name__ == "__main__":
    main()
