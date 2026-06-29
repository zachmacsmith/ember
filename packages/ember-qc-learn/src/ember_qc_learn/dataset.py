"""
Torch dataset for the learned-embedding bake-off.

Each example is a problem graph H with:
  x          [n, F]   source structural features (features.source_features)
  edge_index [2, 2E]  bidirectional source edges
  y          [n, 2]   SUPERVISED LABEL: the centroid (in the target's normalized
                      hardware coordinates) of each vertex's PathFinder chain
  meta                id / edges / embedding / n  (kept off the tensor path, for decode+eval)

A model maps (x, edge_index) -> predicted [n, 2] coords in the same normalized
frame; decode.py snaps coords to qubits. One dataset per (split, target) so the
hardware geometry is fixed. Records lacking a valid label for the target are skipped.
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

import networkx as nx
import numpy as np
import torch
from torch_geometric.data import Data

from ember_qc_learn.features import source_features, target_geometry


def record_to_graph(rec: Dict) -> nx.Graph:
    H = nx.Graph()
    H.add_nodes_from(range(rec["n"]))
    H.add_edges_from((int(u), int(v)) for u, v in rec["edges"])
    return H


def chain_centroids(embedding: Dict[int, List[int]], geo: Dict,
                    source_nodes: List[int]) -> np.ndarray:
    """[n, 2] centroid of each vertex's chain in normalized hardware coords."""
    coords, qidx = geo["coords"], geo["node_to_idx"]
    out = np.zeros((len(source_nodes), 2), dtype=np.float32)
    for i, v in enumerate(source_nodes):
        chain = embedding.get(v, [])
        rows = [qidx[q] for q in chain if q in qidx]
        out[i] = coords[rows].mean(0) if rows else coords.mean(0)
    return out


def build_examples(jsonl_path: str, target_name: str, geo: Dict):
    """(Data list, meta list) for one (split, target). Metadata is kept OUT of the
    Data objects so torch_geometric can batch them (it would try to collate dicts).
    Skips records without a valid label."""
    examples: List[Data] = []
    metas: List[Dict] = []
    with open(jsonl_path) as f:
        for line in f:
            rec = json.loads(line)
            lab = rec.get("labels", {}).get(target_name)
            if not lab or "embedding" not in lab:
                continue
            emb = {int(k): [int(q) for q in v] for k, v in lab["embedding"].items()}
            H = record_to_graph(rec)
            sf = source_features(H)
            y = chain_centroids(emb, geo, sf["nodes"])
            d = Data(
                x=torch.from_numpy(sf["x"]),
                edge_index=torch.from_numpy(sf["edge_index"]),
                y=torch.from_numpy(y),
                num_nodes=sf["n"],
            )
            examples.append(d)
            metas.append({"id": rec["id"], "n": rec["n"], "edges": rec["edges"],
                          "embedding": emb, "acl": lab["acl"], "family": rec["family"],
                          "target": target_name})
    return examples, metas


class EmbedDataset:
    """Lightweight holder: PyG Data list + the shared target geometry."""

    def __init__(self, jsonl_path: str, target_name: str,
                 geo: Optional[Dict] = None, target_graph=None):
        if geo is None:
            import dwave_networkx as dnx
            builders = {"pegasus_6": lambda: dnx.pegasus_graph(6),
                        "zephyr_4": lambda: dnx.zephyr_graph(4)}
            target_graph = builders[target_name]()
            geo = target_geometry(target_graph, target_name)
        self.geo = geo
        self.target_name = target_name
        self.examples, self.meta = build_examples(jsonl_path, target_name, geo)

    def __len__(self):
        return len(self.examples)

    def loader(self, batch_size: int = 16, shuffle: bool = False):
        from torch_geometric.loader import DataLoader
        return DataLoader(self.examples, batch_size=batch_size, shuffle=shuffle)
