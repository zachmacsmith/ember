"""
Reference family: a GNN that predicts a per-vertex hardware coordinate (a learned
layout), trained by MSE to the Reweave chain centroids. Decoded primarily via
seed->MM (the patent's predict-then-refine). The proven-out family that anchors
the shared train/decode interface before the workflow adds the others.
"""
from __future__ import annotations

import torch.nn as nn

from ember_qc_learn.models.base import CoordModel, GNNBackbone, register_model


@register_model("gnn-seed")
class GNNSeed(CoordModel):
    def __init__(self, in_dim: int, hidden: int = 128, layers: int = 4,
                 conv: str = "sage", dropout: float = 0.1):
        super().__init__()
        self.cfg = dict(in_dim=in_dim, hidden=hidden, layers=layers,
                        conv=conv, dropout=dropout)
        self.backbone = GNNBackbone(in_dim, hidden, layers, conv, dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2), nn.Sigmoid(),   # -> [0,1]^2
        )

    def forward(self, data):
        h = self.backbone(data.x, data.edge_index)
        return self.head(h)
