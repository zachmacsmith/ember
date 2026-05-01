"""PPO actor-critic network for CHARME (inference only).

Trimmed from archived/algorithms/charme/charme/models.py:
  - removed `evaluate()` (PPO-update-only, not used at inference)
  - `act()` gets a `greedy` flag so callers can choose argmax vs sampled
  - kept `critic` intact because the trained state_dict contains its weights
    and we load the whole checkpoint

The architecture is dimension-flexible in `num_nodes` and hardware size —
the `state_dict` does *not* hard-code logical size (the final `lin` is
128→1), so a single checkpoint can in principle run on differently-sized
hardware. Trained distribution is Chimera 16×16×4 with 120-node BA sources;
the wrapper enforces that.
"""
from __future__ import annotations

import torch
import torch.nn as nn
from torch.distributions import Categorical

try:
    from torch_geometric.nn import GCNConv
except ImportError:  # pragma: no cover
    GCNConv = None


def _require_gcn():
    if GCNConv is None:
        raise ImportError(
            "torch_geometric is required for CHARME inference (GCNConv).\n"
            "Install: pip install torch_geometric"
        )


class Critic(nn.Module):
    def __init__(self, in_logical_channels, hidden_logical_channels,
                 in_hardware_channels, hidden_hardware_channels,
                 logical_size, device):
        super().__init__()
        _require_gcn()
        self.conv_logical_1 = GCNConv(in_logical_channels, hidden_logical_channels)
        self.conv_logical_2 = GCNConv(hidden_logical_channels, hidden_logical_channels)
        self.conv_logical_3 = GCNConv(hidden_logical_channels, hidden_logical_channels)

        self.conv_hardware_1 = GCNConv(in_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_2 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_3 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)

        self.lin = nn.Linear(128, 1)
        self.lin2 = nn.Linear(logical_size, 1)
        self.device = device

    def forward(self, state):
        x_logical = state['logical_attr']
        logical_edge_index = state['logical_edge_index']
        x_hardware = state['hw_attr']
        hardware_edge_index = state['hw_edge_index']
        emb_matrix = state['emb_matrix']

        if x_logical.dim() == 2:
            x_logical = x_logical.unsqueeze(0)
        if logical_edge_index.dim() == 2:
            logical_edge_index = logical_edge_index.unsqueeze(0)
        if x_hardware.dim() == 2:
            x_hardware = x_hardware.unsqueeze(0)
        if hardware_edge_index.dim() == 2:
            hardware_edge_index = hardware_edge_index.unsqueeze(0)
        if emb_matrix.dim() == 2:
            emb_matrix = emb_matrix.unsqueeze(0)

        B = x_logical.shape[0]
        x_log = torch.cat([
            self.conv_logical_3(
                self.conv_logical_2(
                    self.conv_logical_1(x_logical[i], logical_edge_index[i]).to(self.device),
                    logical_edge_index[i]).to(self.device),
                logical_edge_index[i]).to(self.device).unsqueeze(0)
            for i in range(B)
        ], dim=0)
        x_hw = torch.cat([
            self.conv_hardware_3(
                self.conv_hardware_2(
                    self.conv_hardware_1(x_hardware[i], hardware_edge_index[i]).to(self.device),
                    hardware_edge_index[i]).to(self.device),
                hardware_edge_index[i]).to(self.device).unsqueeze(0)
            for i in range(B)
        ], dim=0)
        x_emb = torch.stack([torch.sparse.mm(emb_matrix[i], x_hw[i]) for i in range(B)])
        x_final = torch.cat((x_log, x_emb), dim=-1)
        y = self.lin(x_final)
        y = self.lin2(y.transpose(1, 2))
        return y


class Actor(nn.Module):
    def __init__(self, in_logical_channels, hidden_logical_channels,
                 in_hardware_channels, hidden_hardware_channels,
                 device):
        super().__init__()
        _require_gcn()
        self.conv_logical_1 = GCNConv(in_logical_channels, hidden_logical_channels)
        self.conv_logical_2 = GCNConv(hidden_logical_channels, hidden_logical_channels)
        self.conv_logical_3 = GCNConv(hidden_logical_channels, hidden_logical_channels)

        self.conv_hardware_1 = GCNConv(in_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_2 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_3 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)

        self.lin = nn.Linear(128, 1)
        self.softmax = nn.Softmax(dim=1)
        self.device = device

    def forward(self, state):
        x_logical = state['logical_attr']
        logical_edge_index = state['logical_edge_index']
        x_hardware = state['hw_attr']
        hardware_edge_index = state['hw_edge_index']
        emb_matrix = state['emb_matrix']

        if x_logical.dim() == 2:
            x_logical = x_logical.unsqueeze(0)
        if logical_edge_index.dim() == 2:
            logical_edge_index = logical_edge_index.unsqueeze(0)
        if x_hardware.dim() == 2:
            x_hardware = x_hardware.unsqueeze(0)
        if hardware_edge_index.dim() == 2:
            hardware_edge_index = hardware_edge_index.unsqueeze(0)
        if emb_matrix.dim() == 2:
            emb_matrix = emb_matrix.unsqueeze(0)

        B = x_logical.shape[0]
        x_log = torch.cat([
            self.conv_logical_3(
                self.conv_logical_2(
                    self.conv_logical_1(x_logical[i], logical_edge_index[i]).to(self.device),
                    logical_edge_index[i]).to(self.device),
                logical_edge_index[i]).to(self.device).unsqueeze(0)
            for i in range(B)
        ], dim=0)
        x_hw = torch.cat([
            self.conv_hardware_3(
                self.conv_hardware_2(
                    self.conv_hardware_1(x_hardware[i], hardware_edge_index[i]).to(self.device),
                    hardware_edge_index[i]).to(self.device),
                hardware_edge_index[i]).to(self.device).unsqueeze(0)
            for i in range(B)
        ], dim=0)
        x_emb = torch.stack([torch.sparse.mm(emb_matrix[i], x_hw[i]) for i in range(B)])
        x_final = torch.cat((x_log, x_emb), dim=-1)
        return self.softmax(self.lin(x_final).squeeze(-1))


class ActorCritic(nn.Module):
    """Inference-only ActorCritic. The checkpoint's `actor.*` and `critic.*`
    keys load cleanly into this module."""

    def __init__(self, device,
                 in_logical_channels: int = 1, hidden_logical_channels: int = 64,
                 in_hardware_channels: int = 1, hidden_hardware_channels: int = 64,
                 logical_size: int = 120):
        super().__init__()
        self.device = device
        self.actor = Actor(in_logical_channels, hidden_logical_channels,
                           in_hardware_channels, hidden_hardware_channels,
                           device=device).to(device)
        self.critic = Critic(in_logical_channels, hidden_logical_channels,
                             in_hardware_channels, hidden_hardware_channels,
                             logical_size=logical_size, device=device).to(device)

    @torch.no_grad()
    def act(self, state, mask, mask_connected, *, greedy: bool = True) -> int:
        """Select one action.

        Args:
            mask:           nodes already embedded (cannot pick again).
            mask_connected: nodes with no embedded neighbour yet (cannot pick).
            greedy:         True → argmax of the masked distribution.
                            False → sample from Categorical (CHARME's training behaviour).
        """
        state_dev = {k: v.to(self.device) if hasattr(v, 'to') else v for k, v in state.items()}
        action_prob = self.actor(state_dev).squeeze()
        action_prob = action_prob + 1e-12
        final_mask = [a or b for a, b in zip(mask, mask_connected)]
        mask_tensor = torch.tensor(final_mask, device=self.device)
        action_prob = action_prob.masked_fill(mask_tensor, 0.0)
        if greedy:
            return int(action_prob.argmax().item())
        return int(Categorical(action_prob).sample().item())
