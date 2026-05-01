"""
tests/test_charme_utils.py
===========================
Tests for ember_qc.algorithms.charme.utils — tensor/graph helpers used by
CHARME inference.  Requires torch and numpy (always available in dev env).

These tests are deliberately independent of torch_geometric or any binary.
"""
import pytest
import networkx as nx

torch = pytest.importorskip("torch", reason="torch required for CHARME utils tests")
import numpy as np

from ember_qc.algorithms.charme.utils import (
    generate_Chimera,
    get_hw_edge_index,
    get_hw_attr_synthetic,
    analysing_logical,
    convert_embedding_to_tensor,
    update_hw_attr_synthetic,
    update_embedding_matrix,
)


# ===========================================================================
# generate_Chimera
# ===========================================================================

class TestGenerateChimera:
    def test_node_count_default(self):
        # Chimera(16,16,4): 2 * 16 * 16 * 4 = 2048 nodes
        G = generate_Chimera(16, 16, 4)
        assert G.number_of_nodes() == 2 * 16 * 16 * 4

    def test_node_count_small(self):
        # Chimera(2,2,2): 2 * 2 * 2 * 2 = 16 nodes
        G = generate_Chimera(2, 2, 2)
        assert G.number_of_nodes() == 16

    def test_nodes_are_tuples(self):
        G = generate_Chimera(2, 2, 2)
        for node in G.nodes():
            assert isinstance(node, tuple)
            assert len(node) == 3  # (x, y, k)

    def test_intra_cell_edges_exist(self):
        # In Chimera each cell (i,j) has bipart_cell*bipart_cell intra-cell couplers.
        G = generate_Chimera(2, 2, 2)
        # Check cell (0,0): k in [0,1] connects to k in [2,3]
        assert G.has_edge((0, 0, 0), (0, 0, 2)) or G.has_edge((0, 0, 2), (0, 0, 0))
        assert G.has_edge((0, 0, 1), (0, 0, 3)) or G.has_edge((0, 0, 3), (0, 0, 1))

    def test_inter_cell_horizontal_edges(self):
        # k >= bipart_cell spans horizontally (same row, adjacent columns)
        G = generate_Chimera(2, 2, 2)
        # (0,0,2) -- (0,1,2): same row, k=2 (>= bipart_cell=2), adjacent columns
        assert G.has_edge((0, 0, 2), (0, 1, 2)) or G.has_edge((0, 1, 2), (0, 0, 2))

    def test_inter_cell_vertical_edges(self):
        # k < bipart_cell spans vertically (adjacent rows, same column)
        G = generate_Chimera(2, 2, 2)
        # (0,0,0) -- (1,0,0): k=0 (< bipart_cell=2), adjacent rows, same column
        assert G.has_edge((0, 0, 0), (1, 0, 0)) or G.has_edge((1, 0, 0), (0, 0, 0))

    def test_single_cell_chimera(self):
        # Chimera(1,1,2): one cell with 4 nodes, bipartite edges only
        G = generate_Chimera(1, 1, 2)
        assert G.number_of_nodes() == 4
        # No inter-cell edges since only one cell
        for u, v in G.edges():
            ux, uy, _ = u
            vx, vy, _ = v
            assert ux == vx == 0
            assert uy == vy == 0

    def test_chimera_is_networkx_graph(self):
        G = generate_Chimera(4, 4, 4)
        assert isinstance(G, nx.Graph)


# ===========================================================================
# get_hw_edge_index
# ===========================================================================

class TestGetHwEdgeIndex:
    def _chimera_with_mapping(self, rows=2, cols=2, t=2):
        G = generate_Chimera(rows, cols, t)
        for i, node in enumerate(G.nodes()):
            G.nodes[node]['mapping'] = i
            G.nodes[node]['embedding'] = -1
        return G

    def test_shape(self):
        G = self._chimera_with_mapping()
        ei = get_hw_edge_index(G)
        assert ei.shape[0] == 2
        # Each undirected edge → 2 directed edges
        assert ei.shape[1] == 2 * G.number_of_edges()

    def test_is_torch_tensor(self):
        G = self._chimera_with_mapping()
        ei = get_hw_edge_index(G)
        assert isinstance(ei, torch.Tensor)

    def test_values_in_range(self):
        G = self._chimera_with_mapping()
        ei = get_hw_edge_index(G)
        n = G.number_of_nodes()
        assert int(ei.min().item()) >= 0
        assert int(ei.max().item()) < n

    def test_bidirectional(self):
        # Both (u→v) and (v→u) must appear.
        G = self._chimera_with_mapping(1, 1, 2)
        ei = get_hw_edge_index(G)
        edges_set = set(zip(ei[0].tolist(), ei[1].tolist()))
        for u, v in edges_set:
            assert (v, u) in edges_set


# ===========================================================================
# get_hw_attr_synthetic
# ===========================================================================

class TestGetHwAttrSynthetic:
    def test_all_minus_one_initially(self):
        G = generate_Chimera(2, 2, 2)
        for node in G.nodes():
            G.nodes[node]['embedding'] = -1
        attr = get_hw_attr_synthetic(G)
        assert attr.shape == (G.number_of_nodes(), 1)
        assert (attr == -1).all()

    def test_shape(self):
        G = generate_Chimera(2, 2, 2)
        for node in G.nodes():
            G.nodes[node]['embedding'] = -1
        attr = get_hw_attr_synthetic(G)
        assert isinstance(attr, torch.Tensor)
        assert attr.shape[1] == 1

    def test_reflects_embedding_values(self):
        G = generate_Chimera(1, 1, 2)  # 4 nodes
        nodes = list(G.nodes())
        for node in nodes:
            G.nodes[node]['embedding'] = -1
        # Embed logical node 5 onto the first qubit
        G.nodes[nodes[0]]['embedding'] = 5
        attr = get_hw_attr_synthetic(G)
        assert float(attr[0].item()) == 5.0


# ===========================================================================
# analysing_logical
# ===========================================================================

class TestAnalysingLogical:
    def test_k3_shapes(self):
        # K3: 3 nodes, 3 edges → 6 directed edges
        G = nx.relabel_nodes(nx.complete_graph(3), {0: 0, 1: 1, 2: 2})
        ei, attr = analysing_logical(G)
        assert ei.shape == (2, 6)
        assert attr.shape == (3, 1)

    def test_attr_all_ones(self):
        G = nx.path_graph(4)
        _, attr = analysing_logical(G)
        assert (attr == 1.0).all()

    def test_edge_index_bidirectional(self):
        G = nx.path_graph(3)   # edges: 0-1, 1-2
        ei, _ = analysing_logical(G)
        edges_set = set(zip(ei[0].tolist(), ei[1].tolist()))
        assert (0, 1) in edges_set
        assert (1, 0) in edges_set
        assert (1, 2) in edges_set
        assert (2, 1) in edges_set

    def test_returns_torch_tensors(self):
        G = nx.path_graph(3)
        ei, attr = analysing_logical(G)
        assert isinstance(ei, torch.Tensor)
        assert isinstance(attr, torch.Tensor)

    def test_single_edge_graph(self):
        G = nx.Graph()
        G.add_nodes_from([0, 1])
        G.add_edge(0, 1)
        ei, attr = analysing_logical(G)
        assert ei.shape == (2, 2)  # one edge, bidirectional
        assert attr.shape == (2, 1)


# ===========================================================================
# convert_embedding_to_tensor
# ===========================================================================

class TestConvertEmbeddingToTensor:
    def _hw_with_mapping(self):
        G = generate_Chimera(2, 2, 2)
        for i, node in enumerate(G.nodes()):
            G.nodes[node]['mapping'] = i
        return G

    def test_empty_embedding_all_zeros(self):
        hw = self._hw_with_mapping()
        logical = nx.complete_graph(4)
        t = convert_embedding_to_tensor([], hw, logical)
        assert t.shape == (4, hw.number_of_nodes())
        assert (t == 0.0).all()

    def test_shape(self):
        hw = self._hw_with_mapping()
        logical = nx.path_graph(3)
        t = convert_embedding_to_tensor([], hw, logical)
        assert t.shape == (3, hw.number_of_nodes())

    def test_is_torch_tensor(self):
        hw = self._hw_with_mapping()
        logical = nx.path_graph(2)
        t = convert_embedding_to_tensor([], hw, logical)
        assert isinstance(t, torch.Tensor)

    def test_nonempty_embedding_sets_ones(self):
        hw = self._hw_with_mapping()
        logical = nx.path_graph(2)
        # Embed logical node 0 on the first HW qubit
        first_hw_node = list(hw.nodes())[0]
        mapping_idx = hw.nodes[first_hw_node]['mapping']  # == 0
        x, y, k = first_hw_node
        emb = [(x, y, k, 0)]  # logical 0 → qubit (x,y,k)
        t = convert_embedding_to_tensor(emb, hw, logical)
        assert float(t[0][mapping_idx].item()) == 1.0


# ===========================================================================
# update_hw_attr_synthetic
# ===========================================================================

class TestUpdateHwAttrSynthetic:
    def test_updates_correctly(self):
        G = generate_Chimera(1, 1, 2)
        for node in G.nodes():
            G.nodes[node]['embedding'] = -1
        nodes = list(G.nodes())
        G.nodes[nodes[0]]['mapping'] = 0
        hw_attr = torch.tensor([[-1.0], [-1.0], [-1.0], [-1.0]])
        x, y, k = nodes[0]
        old_emb = [(x, y, k, 5)]
        x2, y2, k2 = nodes[1]
        G.nodes[nodes[1]]['mapping'] = 1
        new_emb = [(x2, y2, k2, 7)]
        out = update_hw_attr_synthetic(hw_attr.clone(), G, old_emb, new_emb)
        # Old qubit should now be -1 (reset), new qubit should be 7
        assert float(out[0].item()) == -1.0
        assert float(out[1].item()) == 7.0


# ===========================================================================
# update_embedding_matrix
# ===========================================================================

class TestUpdateEmbeddingMatrix:
    def test_no_change_on_empty_updates(self):
        hw = generate_Chimera(1, 1, 2)
        for i, node in enumerate(hw.nodes()):
            hw.nodes[node]['mapping'] = i
        logical = nx.path_graph(2)
        t = convert_embedding_to_tensor([], hw, logical).to_sparse()
        out = update_embedding_matrix(t, hw, [], [])
        # Should remain all-zero
        dense = out.to_dense()
        assert (dense == 0).all()

    def test_updates_values(self):
        hw = generate_Chimera(1, 1, 2)
        nodes = list(hw.nodes())
        for i, node in enumerate(nodes):
            hw.nodes[node]['mapping'] = i
        logical = nx.path_graph(2)
        x, y, k = nodes[0]
        new_emb = [(x, y, k, 0)]
        t = convert_embedding_to_tensor([], hw, logical).to_sparse()
        out = update_embedding_matrix(t, hw, [], new_emb)
        dense = out.to_dense()
        assert float(dense[0][0].item()) == 1.0
