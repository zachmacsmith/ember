"""
Graph-VAE family (patent FIG 7): a *generative* learned-layout model.

Encoder:  GNNBackbone(H) -> per-node features h; a graph-level summary via
          global mean+max pooling -> (mu, logvar) over a small latent z.
Decoder:  each node's backbone feature h_i concatenated with the (broadcast)
          sampled graph latent z -> per-vertex coords in [0,1]^2.

``forward(data)`` returns the *deterministic* layout (z = mu) so the model
satisfies the shared CoordModel interface and the train harness's val-ACL
selection. The generative payoff — sampling several z and keeping the best
decoded layout — lives in the inference adapter (families/vae.py), which calls
``encode`` once and ``decode_coords`` K times.

Trained with a custom VAE loss (``VAELoss`` below): reconstruction MSE of the
reparameterized decode against the Reweave chain-centroid labels + a small
KL term (beta, linear warmup). All torch-coupled code lives here so the family
file can stay import-safe (no torch at module top).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import global_max_pool, global_mean_pool

from ember_qc_learn.models.base import CoordModel, GNNBackbone, register_model


@register_model("graph-vae")
class GraphVAE(CoordModel):
    """Generative layout VAE. cfg keys mirror the train harness: in_dim, hidden,
    layers, conv, dropout, latent_dim."""

    def __init__(self, in_dim: int, hidden: int = 128, layers: int = 4,
                 conv: str = "sage", dropout: float = 0.1, latent_dim: int = 16):
        super().__init__()
        self.cfg = dict(in_dim=in_dim, hidden=hidden, layers=layers, conv=conv,
                        dropout=dropout, latent_dim=latent_dim)
        self.latent_dim = latent_dim
        self.backbone = GNNBackbone(in_dim, hidden, layers, conv, dropout)
        # graph-level latent from mean+max pooled node features
        self.enc_mu = nn.Linear(2 * hidden, latent_dim)
        self.enc_logvar = nn.Linear(2 * hidden, latent_dim)
        # decoder: [node feature ; broadcast latent] -> coords in [0,1]^2
        self.dec = nn.Sequential(
            nn.Linear(hidden + latent_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2), nn.Sigmoid(),
        )

    # -- helpers --------------------------------------------------------------
    @staticmethod
    def _batch_vec(data, h: torch.Tensor) -> torch.Tensor:
        b = getattr(data, "batch", None)
        if b is None:
            return torch.zeros(h.size(0), dtype=torch.long, device=h.device)
        return b

    def encode(self, data):
        """-> (h[N,hidden], batch[N], mu[B,latent], logvar[B,latent])."""
        h = self.backbone(data.x, data.edge_index)
        b = self._batch_vec(data, h)
        g = torch.cat([global_mean_pool(h, b), global_max_pool(h, b)], dim=-1)
        return h, b, self.enc_mu(g), self.enc_logvar(g)

    @staticmethod
    def reparameterize(mu: torch.Tensor, logvar: torch.Tensor,
                       generator: "torch.Generator | None" = None) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        if generator is None:
            eps = torch.randn_like(std)
        else:
            eps = torch.randn(std.shape, generator=generator,
                              dtype=std.dtype, device=std.device)
        return mu + std * eps

    def decode_coords(self, h: torch.Tensor, b: torch.Tensor,
                      z: torch.Tensor) -> torch.Tensor:
        """Broadcast graph-level z[B,latent] to nodes and decode -> coords[N,2]."""
        if z.dim() == 1:
            z = z.unsqueeze(0)
        z_node = z[b]
        return self.dec(torch.cat([h, z_node], dim=-1))

    # -- interface ------------------------------------------------------------
    def forward(self, data):
        """Deterministic layout (z = mu) for the CoordModel interface / eval."""
        h, b, mu, _logvar = self.encode(data)
        return self.decode_coords(h, b, mu)


class VAELoss:
    """Stateful loss_fn(model, batch, geo) -> scalar.

    reconstruction MSE(decoded coords from reparameterized z, batch.y centroids)
    + beta * KL(N(mu, sigma) || N(0, I)). beta linearly warms up over
    ``warmup_steps`` batches (call count). KL is summed over latent dims and
    averaged over graphs in the batch.
    """

    def __init__(self, beta: float = 0.01, warmup_steps: int = 200):
        self.beta = float(beta)
        self.warmup_steps = max(1, int(warmup_steps))
        self.step = 0

    def __call__(self, model, batch, geo) -> torch.Tensor:
        h, b, mu, logvar = model.encode(batch)
        z = model.reparameterize(mu, logvar)
        coords = model.decode_coords(h, b, z)
        recon = F.mse_loss(coords, batch.y)
        kl = (-0.5 * (1.0 + logvar - mu.pow(2) - logvar.exp())).sum(dim=-1).mean()
        beta_t = self.beta * min(1.0, self.step / self.warmup_steps)
        self.step += 1
        return recon + beta_t * kl
