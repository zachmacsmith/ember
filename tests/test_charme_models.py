"""
tests/test_charme_models.py
============================
Tests for ember_qc.algorithms.charme.models — ActorCritic and sub-modules.

These tests skip gracefully when torch_geometric is not installed.
"""
import pytest

torch = pytest.importorskip("torch", reason="torch required")
torch_geometric = pytest.importorskip("torch_geometric", reason="torch_geometric required")

from ember_qc.algorithms.charme.models import ActorCritic, Actor, Critic


# ===========================================================================
# Module-level import guard
# ===========================================================================

class TestRequireGCN:
    def test_gcnconv_imported(self):
        from ember_qc.algorithms.charme.models import GCNConv
        assert GCNConv is not None


# ===========================================================================
# ActorCritic instantiation
# ===========================================================================

class TestActorCriticInit:
    def setup_method(self):
        self.dev = torch.device("cpu")

    def test_instantiates_without_error(self):
        model = ActorCritic(device=self.dev, logical_size=120)
        assert model is not None

    def test_has_actor_and_critic(self):
        model = ActorCritic(device=self.dev, logical_size=120)
        assert isinstance(model.actor, Actor)
        assert isinstance(model.critic, Critic)

    def test_custom_logical_size(self):
        # Should accept any logical_size
        model = ActorCritic(device=self.dev, logical_size=60)
        assert model is not None

    def test_default_channels(self):
        model = ActorCritic(device=self.dev)
        assert model is not None


# ===========================================================================
# act() method — mask mechanics
# ===========================================================================

class TestActorCriticAct:
    def setup_method(self):
        from ember_qc.algorithms.charme.utils import (
            generate_Chimera, get_hw_edge_index, get_hw_attr_synthetic,
            analysing_logical, convert_embedding_to_tensor,
        )
        import networkx as nx

        dev = torch.device("cpu")
        self.model = ActorCritic(device=dev, logical_size=10)
        self.model.eval()

        # Build a minimal state for a 5-node source on a tiny Chimera(2,2,4)
        source = nx.path_graph(5)
        hw = generate_Chimera(2, 2, 4)
        for i, node in enumerate(hw.nodes()):
            hw.nodes[node]['mapping'] = i
            hw.nodes[node]['embedding'] = -1

        logical_ei, logical_attr = analysing_logical(source)
        # Pad to logical_size=10
        pad = torch.zeros(5, 1)
        logical_attr = torch.cat([logical_attr, pad], dim=0)

        hw_ei = get_hw_edge_index(hw)
        hw_attr = get_hw_attr_synthetic(hw)
        emb = convert_embedding_to_tensor([], hw, source)
        pad2 = torch.zeros(5, emb.shape[1])
        emb = torch.cat([emb, pad2], dim=0).to_sparse()

        self.state = {
            'logical_attr': logical_attr,
            'logical_edge_index': logical_ei,
            'hw_attr': hw_attr,
            'hw_edge_index': hw_ei,
            'emb_matrix': emb,
        }

    def test_act_returns_int(self):
        mask = [False] * 10
        mask_connected = [True] * 10
        # Make at least one node available
        mask_connected[0] = False
        result = self.model.act(self.state, mask, mask_connected, greedy=True)
        assert isinstance(result, int)

    def test_act_greedy_in_range(self):
        mask = [False] * 10
        mask_connected = [True] * 10
        mask_connected[2] = False
        result = self.model.act(self.state, mask, mask_connected, greedy=True)
        assert 0 <= result < 10

    def test_act_sampled_in_range(self):
        mask = [False] * 10
        mask_connected = [True] * 10
        mask_connected[1] = False
        result = self.model.act(self.state, mask, mask_connected, greedy=False)
        assert 0 <= result < 10

    def test_act_does_not_choose_masked_node(self):
        mask = [True] * 10
        mask_connected = [True] * 10
        # Only node 3 available
        mask[3] = False
        mask_connected[3] = False
        result = self.model.act(self.state, mask, mask_connected, greedy=True)
        # argmax of masked distribution should pick 3
        assert result == 3

    def test_act_greedy_deterministic(self):
        mask = [False] * 10
        mask_connected = [False] * 10
        r1 = self.model.act(self.state, mask, mask_connected, greedy=True)
        r2 = self.model.act(self.state, mask, mask_connected, greedy=True)
        assert r1 == r2
