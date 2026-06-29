"""
Model interface for the bake-off. The unifying output is a per-vertex coordinate
in the target's normalized hardware frame [0,1]^2 (a *learned layout*). From coords
the decoder supports BOTH paths: seed->MM (snap to nearest free qubit) and
direct->repair (proximity soft-assignment). Families differ in architecture/loss,
not interface — so the workflow can add families consistently.
"""
from __future__ import annotations

from typing import Dict

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv, GCNConv, SAGEConv

MODEL_REGISTRY: Dict[str, type] = {}


def register_model(name: str):
    def deco(cls):
        cls.model_name = name
        MODEL_REGISTRY[name] = cls
        return cls
    return deco


def build_model(name: str, **kw) -> "CoordModel":
    return MODEL_REGISTRY[name](**kw)


_CONVS = {
    "sage": lambda i, o: SAGEConv(i, o),
    "gat": lambda i, o: GATv2Conv(i, o, heads=4, concat=False),
    "gcn": lambda i, o: GCNConv(i, o),
}


class GNNBackbone(nn.Module):
    """Residual message-passing stack with LayerNorm; conv in {sage,gat,gcn}."""

    def __init__(self, in_dim: int, hidden: int = 128, layers: int = 4,
                 conv: str = "sage", dropout: float = 0.1):
        super().__init__()
        Conv = _CONVS[conv]
        self.inp = nn.Linear(in_dim, hidden)
        self.convs = nn.ModuleList(Conv(hidden, hidden) for _ in range(layers))
        self.norms = nn.ModuleList(nn.LayerNorm(hidden) for _ in range(layers))
        self.dropout = dropout

    def forward(self, x, edge_index):
        h = F.relu(self.inp(x))
        for conv, norm in zip(self.convs, self.norms):
            h = norm(h + F.relu(conv(h, edge_index)))
            h = F.dropout(h, self.dropout, training=self.training)
        return h


class CoordModel(nn.Module):
    """Maps a PyG batch -> [N, 2] predicted coords in [0,1]^2 (one row per node)."""
    out_kind = "coords"

    def forward(self, data) -> torch.Tensor:  # pragma: no cover - interface
        raise NotImplementedError

    def predict_coords(self, data) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            return self.forward(data)
