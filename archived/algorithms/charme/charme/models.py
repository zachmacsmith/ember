"""Neural network models for CHARME (extracted from CHARME_training.ipynb).

This module contains:
- actor: policy network
- critic: value network
- ActorCritic: wrapper used by PPO
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal
from torch.distributions import MultivariateNormal
from torch.distributions import Categorical

try:
    from torch_geometric.nn import GCNConv
except Exception as e:  # pragma: no cover
    GCNConv = None


class critic(nn.Module):
    def __init__(self, in_logical_channels, hidden_logical_channels,
                 in_hardware_channels, hidden_hardware_channels,
                 out_channels, logical_size, device):
        super().__init__()
        if GCNConv is None:
            raise ImportError("torch_geometric is required for critic (GCNConv not available).")

        self.conv_logical_1 = GCNConv(in_logical_channels, hidden_logical_channels)
        self.conv_logical_2 = GCNConv(hidden_logical_channels, hidden_logical_channels)
        self.conv_logical_3 = GCNConv(hidden_logical_channels, hidden_logical_channels)

        self.conv_hardware_1 = GCNConv(in_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_2 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_3 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)

        self.lin = nn.Linear(128, 1)
        self.lin2 = torch.nn.Linear(logical_size, 1)
        self.logical_size = logical_size

        self.device = device

    def forward(self, state):
        x_logical = state['logical_attr']
        logical_edge_index = state['logical_edge_index']
        x_hardware = state['hw_attr']
        hardware_edge_index = state['hw_edge_index']
        embedding_matrix = state['emb_matrix']
        #embedding_dict = state['emb_dict']
        
        if x_logical.dim() == 2:
            x_logical = x_logical.unsqueeze(dim=0)
        if logical_edge_index.dim() == 2:
            logical_edge_index = logical_edge_index.unsqueeze(dim=0)
        if x_hardware.dim() == 2:
            x_hardware = x_hardware.unsqueeze(dim=0)
        if hardware_edge_index.dim() == 2:
            hardware_edge_index = hardware_edge_index.unsqueeze(dim=0)
        if embedding_matrix.dim() == 2:
            embedding_matrix = embedding_matrix.unsqueeze(dim=0)
        #if type(embedding_dict) is dict:
        #    embedding_dict = [embedding_dict]
        
        minibatch_size = x_logical.shape[0]
        num_nodes = x_logical.shape[1]
        
        x_logical_next = [self.conv_logical_3(self.conv_logical_2(self.conv_logical_1(x_logical[i], logical_edge_index[i]).to(self.device), logical_edge_index[i]).to(self.device), logical_edge_index[i]).to(self.device).unsqueeze(dim=0)
                  for i in range(minibatch_size)]
        x_logical_next = torch.cat(x_logical_next, dim=0)
        
        x_hardware_next = [self.conv_hardware_3(self.conv_hardware_2(self.conv_hardware_1(x_hardware[i], hardware_edge_index[i]).to(self.device), hardware_edge_index[i]).to(self.device), hardware_edge_index[i]).to(self.device).unsqueeze(dim=0)
                   for i in range(minibatch_size)]
        x_hardware_next = torch.cat(x_hardware_next, dim=0)
        
        x_emb = torch.stack([torch.sparse.mm(embedding_matrix[i], x_hardware_next[i]) for i in range(minibatch_size)])
        
        x_final = torch.cat((x_logical_next, x_emb), dim=-1)
        y = self.lin(x_final)
        y = self.lin2(y.transpose(1,2))
        return y


class actor(nn.Module):
    def __init__(self, in_logical_channels, hidden_logical_channels,
                 in_hardware_channels, hidden_hardware_channels,
                 out_channels, logical_size, action_dim, device):
        super().__init__()
        if GCNConv is None:
            raise ImportError("torch_geometric is required for actor (GCNConv not available).")

        self.conv_logical_1 = GCNConv(in_logical_channels, hidden_logical_channels)
        self.conv_logical_2 = GCNConv(hidden_logical_channels, hidden_logical_channels)
        self.conv_logical_3 = GCNConv(hidden_logical_channels, hidden_logical_channels)

        self.conv_hardware_1 = GCNConv(in_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_2 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)
        self.conv_hardware_3 = GCNConv(hidden_hardware_channels, hidden_hardware_channels)

        self.lin = nn.Linear(128, 1)
        self.softmax = torch.nn.Softmax(dim=1)
        self.logical_size = logical_size
        self.action_dim = action_dim
        self.device = device

    def forward(self, state):
        #print("State: ", state)
        x_logical = state['logical_attr']
        logical_edge_index = state['logical_edge_index']
        x_hardware = state['hw_attr']
        hardware_edge_index = state['hw_edge_index']
        embedding_matrix = state['emb_matrix']
        #embedding_dict = state['emb_dict']
        
        if x_logical.dim() == 2:
            x_logical = x_logical.unsqueeze(dim=0)
        if logical_edge_index.dim() == 2:
            logical_edge_index = logical_edge_index.unsqueeze(dim=0)
        if x_hardware.dim() == 2:
            x_hardware = x_hardware.unsqueeze(dim=0)
        if hardware_edge_index.dim() == 2:
            hardware_edge_index = hardware_edge_index.unsqueeze(dim=0)
        if embedding_matrix.dim() == 2:
            embedding_matrix = embedding_matrix.unsqueeze(dim=0)
            
        minibatch_size = x_logical.shape[0]
        num_nodes = x_logical.shape[1]
        x_logical_next = [self.conv_logical_3(self.conv_logical_2(self.conv_logical_1(x_logical[i], logical_edge_index[i]).to(self.device), logical_edge_index[i]).to(self.device), logical_edge_index[i]).to(self.device).unsqueeze(dim=0)
                  for i in range(minibatch_size)]
        x_logical_next = torch.cat(x_logical_next, dim=0)
        x_hardware_next = [self.conv_hardware_3(self.conv_hardware_2(self.conv_hardware_1(x_hardware[i], hardware_edge_index[i]).to(self.device), hardware_edge_index[i]).to(self.device), hardware_edge_index[i]).to(self.device).unsqueeze(dim=0)
                   for i in range(minibatch_size)]
        x_hardware_next = torch.cat(x_hardware_next, dim=0)
        #x_hardware = self.conv_hardware(x_hardware, hardware_edge_index)
        x_emb = torch.stack([torch.sparse.mm(embedding_matrix[i], x_hardware_next[i]) for i in range(minibatch_size)])
        x_final = torch.cat((x_logical_next, x_emb), dim=-1)
        #print(self.lin(x_final).squeeze(dim=-1).shape)
        y = self.softmax(self.lin(x_final).squeeze(dim=-1))
        return y


class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim, has_continuous_action_space, action_std_init, device,
                 in_logical_channels=1, hidden_logical_channels=64,
                 in_hardware_channels=1, hidden_hardware_channels=64):
        super().__init__()

        self.has_continuous_action_space = has_continuous_action_space
        self.action_dim = action_dim
        self.device = device
        self.max_prob = torch.tensor(0).to(self.device)
        
        if has_continuous_action_space:
            self.action_var = torch.full((action_dim,), action_std_init * action_std_init).to(device)

        self.actor = actor(in_logical_channels, hidden_logical_channels,
                           in_hardware_channels, hidden_hardware_channels,
                           out_channels=hidden_logical_channels,
                           logical_size=action_dim, action_dim=action_dim, device = device).to(device)

        self.critic = critic(in_logical_channels, hidden_logical_channels,
                             in_hardware_channels, hidden_hardware_channels,
                             out_channels=hidden_logical_channels,
                             logical_size=action_dim, device = device).to(device)

    def set_action_std(self, new_action_std: float):
        if self.has_continuous_action_space:
            self.action_var = torch.full((self.action_dim,), new_action_std * new_action_std).to(self.device)

    def forward(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def act(self, state, mask, mask_connected):
        state_cuda = {}
        #print(state)
        for k in state.keys():
            if (k != 'emb_dict'):
                state_cuda[k] = state[k].to(self.device)
            else:
                state_cuda[k] = state[k]
        action_prob = self.actor(state_cuda).squeeze()
        #print(state_cuda)
        action_prob = torch.add(action_prob, 0.000000000001)
        #print(action_prob)
        final_mask = [a or b for a, b in zip(mask, mask_connected)]
        mask_tensor = torch.tensor(final_mask, device=self.device)
        action_prob = action_prob.masked_fill(mask_tensor==True,0)
        #print(action_prob)
        dist = Categorical(action_prob)

        #print(action_prob)
        #print(dist)
        pred_action = dist.sample()
        #print(pred_action)
        action_logprob = dist.log_prob(pred_action)
        state_val = self.critic(state_cuda).squeeze()
        action = pred_action
        return action.detach(), action_logprob.detach(), state_val.detach()

    def evaluate(self, hw_attr, logical_index, logical_edge_index, logical_attr, hw_edge_index, action):
        from torch.distributions import Categorical, MultivariateNormal

        action_logits = self.actor(hw_attr, logical_index, logical_edge_index, logical_attr, hw_edge_index)

        if self.has_continuous_action_space:
            action_var = self.action_var.expand_as(action_logits)
            cov_mat = torch.diag_embed(action_var).to(self.device)
            dist = MultivariateNormal(action_logits, cov_mat)
            action_logprobs = dist.log_prob(action)
            dist_entropy = dist.entropy()
        else:
            dist = Categorical(logits=action_logits)
            action_logprobs = dist.log_prob(action)
            dist_entropy = dist.entropy()

        state_values = self.critic(hw_attr, logical_index, logical_edge_index, logical_attr, hw_edge_index)
        return action_logprobs, state_values, dist_entropy
