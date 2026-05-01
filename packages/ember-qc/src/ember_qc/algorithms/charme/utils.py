"""Graph/tensor helpers needed by CHARME inference.

Subset of archived/algorithms/charme/charme/utils.py — keeps only the
functions the inference-time env + model actually call. Dropped:
  - analysing_hw           (replaced by get_hw_edge_index + get_hw_attr_synthetic)
  - convert_graph_to_latent_embedding / DeepWalk (training only)
  - convert_graph_to_embeddingMinorminer (training only — builds targets)
  - init_logical_graph / init_logical_graph_erdos (training only)
  - normalize_state / convert_minorminer_to_tensor / is_subset etc. (unused)
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import torch


def generate_Chimera(topo_row: int = 16, topo_column: int = 16, bipart_cell: int = 4) -> nx.Graph:
    """Build a Chimera(topo_row, topo_column, bipart_cell) graph with (x,y,k) node labels.

    This is the labelling CHARME was trained against — each cell has two
    partitions of `bipart_cell` nodes (k ∈ [0,bipart_cell) and [bipart_cell,2*bipart_cell)),
    with horizontal/vertical inter-cell couplers.
    """
    edge_list = []
    for i in range(topo_row):
        for j in range(topo_column):
            for k1 in range(bipart_cell):
                for k2 in range(bipart_cell, 2 * bipart_cell):
                    edge_list.append(((i, j, k1), (i, j, k2)))
                    edge_list.append(((i, j, k2), (i, j, k1)))
            for k in range(bipart_cell, 2 * bipart_cell):
                if j != topo_column - 1:
                    edge_list.append(((i, j, k), (i, j + 1, k)))
                if j != 0:
                    edge_list.append(((i, j, k), (i, j - 1, k)))
            for k in range(bipart_cell):
                if i != topo_row - 1:
                    edge_list.append(((i, j, k), (i + 1, j, k)))
                if i != 0:
                    edge_list.append(((i, j, k), (i - 1, j, k)))
    return nx.from_edgelist(edge_list)


def get_hw_edge_index(hw_graph: nx.Graph) -> torch.Tensor:
    hw_edge_index = []
    for ed in hw_graph.edges:
        a = hw_graph.nodes[ed[0]]['mapping']
        b = hw_graph.nodes[ed[1]]['mapping']
        hw_edge_index.append([a, b])
        hw_edge_index.append([b, a])
    return torch.tensor(np.array(hw_edge_index).T)


def get_hw_attr_synthetic(hw_graph: nx.Graph) -> torch.Tensor:
    hw_attr = torch.zeros([len(hw_graph.nodes), 1])
    for idx, node in enumerate(hw_graph.nodes):
        hw_attr[idx][0] = hw_graph.nodes[node]['embedding']
    return hw_attr


def update_hw_attr_synthetic(hw_attr: torch.Tensor, hw_graph: nx.Graph,
                             curr_emb, new_emb) -> torch.Tensor:
    mapping_indices = [hw_graph.nodes[(e[0], e[1], e[2])]['mapping'] for e in curr_emb]
    hw_attr[mapping_indices] = torch.tensor([-1]).float()
    node_indices = [[e[3]] for e in new_emb]
    mapping_indices = [hw_graph.nodes[(e[0], e[1], e[2])]['mapping'] for e in new_emb]
    hw_attr[mapping_indices] = torch.tensor(node_indices).float()
    return hw_attr


def analysing_logical(logical_graph: nx.Graph):
    """Return (logical_edge_index [2,2E], logical_attr [N,1]).

    Assumes the graph is relabelled to 0..N-1 and has at least one edge.
    """
    X = np.array(logical_graph.edges)
    Y = X.copy()
    tmp = Y[:, 0].copy()
    Y[:, 0] = Y[:, 1].copy()
    Y[:, 1] = tmp
    Z = np.concatenate((X.T, Y.T), axis=1)
    logical_edge_index = torch.tensor(Z)
    logical_attr = torch.tensor(np.array([[1]] * len(logical_graph.nodes)), dtype=torch.float)
    return logical_edge_index, logical_attr


def convert_embedding_to_tensor(embedding, hw_graph: nx.Graph, logical_graph: nx.Graph) -> torch.Tensor:
    emb_matrix = torch.zeros([len(logical_graph.nodes), len(hw_graph.nodes)])
    for e in embedding:
        emb_matrix[e[3]][hw_graph.nodes[(e[0], e[1], e[2])]['mapping']] = 1
    return emb_matrix


def update_embedding_matrix(emb_matrix: torch.Tensor, hw_graph: nx.Graph,
                            curr_emb, new_emb) -> torch.Tensor:
    emb_matrix = emb_matrix.to_dense()
    node_indices = [e[3] for e in curr_emb]
    mapping_indices = [hw_graph.nodes[(e[0], e[1], e[2])]['mapping'] for e in curr_emb]
    emb_matrix[node_indices, mapping_indices] = 0
    node_indices = [e[3] for e in new_emb]
    mapping_indices = [hw_graph.nodes[(e[0], e[1], e[2])]['mapping'] for e in new_emb]
    emb_matrix[node_indices, mapping_indices] = 1
    return emb_matrix.to_sparse()
