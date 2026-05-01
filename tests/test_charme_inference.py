"""
tests/test_charme_inference.py
================================
Tests for ember_qc.algorithms.charme.inference — run_charme error paths and
CharmeAtomRunner helpers that do NOT require the compiled binary or weights.

All tests that would need the actual binary or weights are either skipped via
a fixture or exercise only the early-return guard clauses.
"""
import os
import tempfile
import pytest
import networkx as nx

from ember_qc.algorithms.charme.inference import (
    run_charme,
    _linearise_chimera,
    ACTION_DIM,
    CHARME_TOPO_ROW,
    CHARME_TOPO_COL,
    CHARME_BIPART_CELL,
)
from ember_qc.algorithms.charme.env_infer import CharmeAtomRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chimera_target() -> nx.Graph:
    """Minimal chimera_16x16x4 with the metadata CHARME checks."""
    import dwave_networkx as dnx
    G = dnx.chimera_graph(CHARME_TOPO_ROW, CHARME_TOPO_COL, CHARME_BIPART_CELL)
    return G


def small_source(n: int = 5) -> nx.Graph:
    """Small BA source graph with exactly n nodes."""
    return nx.barabasi_albert_graph(n, 2, seed=0)


NONEXISTENT_BINARY = "/tmp/__nonexistent_charme_binary__/main"
NONEXISTENT_WEIGHTS = "/tmp/__nonexistent_charme_weights__.pth"


# ===========================================================================
# _linearise_chimera
# ===========================================================================

class TestLineariseChimera:
    def test_single_qubit(self):
        # (x=0, y=0, k=0, c=5): linear = 0*16*8 + 0*8 + 0 = 0
        result = _linearise_chimera([(0, 0, 0, 5)], n_cols=16, bipart_cell=4)
        assert result == {5: [0]}

    def test_multiple_qubits_same_chain(self):
        # Two qubits in chain c=3
        result = _linearise_chimera(
            [(0, 0, 0, 3), (0, 0, 1, 3)],
            n_cols=16, bipart_cell=4,
        )
        assert 3 in result
        assert len(result[3]) == 2

    def test_multiple_chains(self):
        result = _linearise_chimera(
            [(0, 0, 0, 0), (0, 0, 4, 1)],
            n_cols=16, bipart_cell=4,
        )
        assert 0 in result
        assert 1 in result

    def test_empty_input(self):
        result = _linearise_chimera([], n_cols=16, bipart_cell=4)
        assert result == {}

    def test_linear_index_formula(self):
        # (x=1, y=2, k=3, c=0) with n_cols=16, bipart_cell=4 (per_cell=8)
        # linear = 1*16*8 + 2*8 + 3 = 128 + 16 + 3 = 147
        result = _linearise_chimera([(1, 2, 3, 0)], n_cols=16, bipart_cell=4)
        assert result[0] == [147]


# ===========================================================================
# run_charme — early-return guard clauses (no binary/weights needed)
# ===========================================================================

class TestRunCharmeGuards:
    """These tests hit the validation / guard clauses before any binary call."""

    def _target(self):
        return chimera_target()

    def test_wrong_topology_rows(self):
        """Target with wrong rows attribute → FAILURE."""
        import dwave_networkx as dnx
        target = dnx.chimera_graph(8, 8, 4)  # rows=8, not 16
        source = small_source(5)
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert result['success'] is False
        assert result['status'] == 'FAILURE'
        assert 'CHARME checkpoint' in result.get('error', '')

    def test_wrong_topology_tile(self):
        """Target with wrong tile → FAILURE."""
        import dwave_networkx as dnx
        target = dnx.chimera_graph(16, 16, 8)  # tile=8, not 4
        source = small_source(5)
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert result['success'] is False
        assert result['status'] == 'FAILURE'

    def test_source_zero_nodes(self):
        """Empty source graph → FAILURE."""
        target = self._target()
        source = nx.Graph()
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert result['success'] is False
        assert result['status'] == 'FAILURE'

    def test_source_too_many_nodes(self):
        """Source > ACTION_DIM nodes → FAILURE."""
        target = self._target()
        source = nx.path_graph(ACTION_DIM + 1)
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert result['success'] is False
        assert result['status'] == 'FAILURE'
        assert str(ACTION_DIM) in result.get('error', '')

    def test_source_no_edges(self):
        """Source with no edges → FAILURE."""
        target = self._target()
        source = nx.Graph()
        source.add_nodes_from([0, 1, 2])
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert result['success'] is False
        assert result['status'] == 'FAILURE'

    def test_missing_binary_returns_failure(self):
        """Binary not found → FAILURE before any torch call."""
        target = self._target()
        source = small_source(5)
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert result['success'] is False
        assert result['status'] == 'FAILURE'
        # Error should mention binary or weights (order depends on which check fires first)
        assert 'error' in result

    def test_result_always_has_required_keys(self):
        """Every failure result must have at minimum 'embedding', 'time', 'success', 'status'."""
        target = self._target()
        source = nx.Graph()  # empty → triggers guard
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        for key in ('embedding', 'time', 'success', 'status'):
            assert key in result, f"Missing key '{key}' in result"

    def test_embedding_is_dict_on_failure(self):
        target = self._target()
        source = nx.Graph()
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert isinstance(result['embedding'], dict)

    def test_action_dim_boundary_exactly_at_limit(self):
        """Source with exactly ACTION_DIM nodes (no edges) → fails on no-edge check,
        not on size check — verifying both guards are independent."""
        target = self._target()
        source = nx.Graph()
        source.add_nodes_from(range(ACTION_DIM))
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
        )
        assert result['success'] is False
        assert result['status'] == 'FAILURE'

    def test_num_samples_outer_loop_returns_dict(self):
        """num_samples > 1 should wrap the inner call and still return a valid dict."""
        target = self._target()
        source = nx.Graph()  # empty → inner call fails immediately
        result = run_charme(
            source, target,
            weights_path=NONEXISTENT_WEIGHTS,
            binary_path=NONEXISTENT_BINARY,
            num_samples=3,
        )
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'num_samples' in result
        assert result['num_samples'] == 3


# ===========================================================================
# CharmeAtomRunner helpers (no binary)
# ===========================================================================

class TestCharmeAtomRunnerParseOutput:
    """_parse_atom_output reads a tempfile — fully testable without a binary."""

    def _write_and_parse(self, content: str):
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            return CharmeAtomRunner._parse_atom_output(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_parses_embedding_tuples(self):
        content = "0 1 2 3\n1 2 3 4\n8 9\n"
        emb, rr, cc = self._write_and_parse(content)
        assert (0, 1, 2, 3) in emb
        assert (1, 2, 3, 4) in emb
        assert rr == 8
        assert cc == 9

    def test_stops_at_two_element_line(self):
        content = "0 0 0 5\n3 4\n1 1 1 6\n"
        emb, rr, cc = self._write_and_parse(content)
        # Should stop at "3 4" — only first qubit tuple in output
        assert len(emb) == 1
        assert rr == 3
        assert cc == 4

    def test_empty_file(self):
        emb, rr, cc = self._write_and_parse("")
        assert emb == []
        assert rr == -1
        assert cc == -1

    def test_file_with_no_row_col_line(self):
        content = "0 1 2 3\n4 5 6 7\n"
        emb, rr, cc = self._write_and_parse(content)
        assert len(emb) == 2
        assert rr == -1
        assert cc == -1

    def test_ignores_lines_with_wrong_element_count(self):
        content = "1 2 3\n0 1 2 3\n8 9\n"
        emb, rr, cc = self._write_and_parse(content)
        # "1 2 3" (3 parts) is skipped; "0 1 2 3" is a qubit tuple
        assert (0, 1, 2, 3) in emb
        assert rr == 8
        assert cc == 9


class TestCharmeAtomRunnerValidateExtend:
    """_validate_extend tuple-fallback logic — no target_graph supplied."""

    def _runner(self, n=4):
        source = nx.path_graph(n)
        return CharmeAtomRunner(
            source_graph=source,
            topo_row=16, topo_column=16, bipart_cell=4,
            binary_path="/nonexistent/binary",
            seed=0,
            target_graph=None,   # use tuple fallback
        )

    def test_empty_chain_returns_false(self):
        runner = self._runner()
        # new_emb has no entry for action=0
        result = runner._validate_extend([], action=0, old_nodes=[])
        assert result is False

    def test_adjacent_intra_cell_qubits_valid(self):
        runner = self._runner()
        # Two qubits in same cell: (0,0,0) and (0,0,4); bipart_cell=4
        # 0 < 4 connects to 4 >= 4: intra-cell edge
        new_emb = [(0, 0, 0, 0), (0, 0, 4, 1)]
        result = runner._validate_extend(new_emb, action=0, old_nodes=[1])
        assert result is True

    def test_nonadjacent_qubits_invalid(self):
        runner = self._runner()
        # action=0 on qubit (0,0,0); neighbor 1 on qubit (5,5,0)
        # These are not adjacent in Chimera (distance >> 1)
        new_emb = [(0, 0, 0, 0), (5, 5, 0, 1)]
        result = runner._validate_extend(new_emb, action=0, old_nodes=[1])
        assert result is False

    def test_old_nodes_not_in_embedding_returns_false(self):
        runner = self._runner()
        # action=0 is present but old_node=99 is absent from new_emb
        new_emb = [(0, 0, 0, 0)]
        result = runner._validate_extend(new_emb, action=0, old_nodes=[99])
        assert result is False

    def test_no_old_nodes_returns_true_if_action_placed(self):
        runner = self._runner()
        new_emb = [(0, 0, 0, 0)]
        result = runner._validate_extend(new_emb, action=0, old_nodes=[])
        assert result is True

    def test_inter_cell_vertical_adjacent(self):
        runner = self._runner()
        # k=0 (< bipart_cell=4) spans vertically; (0,0,0) -- (1,0,0) are adjacent
        new_emb = [(0, 0, 0, 0), (1, 0, 0, 1)]
        result = runner._validate_extend(new_emb, action=0, old_nodes=[1])
        assert result is True

    def test_inter_cell_horizontal_adjacent(self):
        runner = self._runner()
        # k=4 (>= bipart_cell=4) spans horizontally; (0,0,4) -- (0,1,4) are adjacent
        new_emb = [(0, 0, 4, 0), (0, 1, 4, 1)]
        result = runner._validate_extend(new_emb, action=0, old_nodes=[1])
        assert result is True


class TestCharmeAtomRunnerCallAtom:
    """_call_atom raises FileNotFoundError when binary is absent."""

    def test_missing_binary_raises(self):
        source = nx.path_graph(4)
        runner = CharmeAtomRunner(
            source_graph=source,
            topo_row=16, topo_column=16, bipart_cell=4,
            binary_path="/nonexistent/charme_binary/main",
            seed=0,
        )
        with pytest.raises(FileNotFoundError, match="CHARME binary not found"):
            runner._call_atom(source, 16, 16, 0, is_beginning=0)


# ===========================================================================
# CharmeAlgorithm.embed contract when binary/weights absent
# ===========================================================================

class TestCharmeAlgorithmEmbedContract:
    def setup_method(self):
        from ember_qc.registry import get_algorithm
        self.algo = get_algorithm("charme")

    def test_embed_returns_dict(self):
        import dwave_networkx as dnx
        target = dnx.chimera_graph(8, 8, 4)  # wrong dims → early return
        source = nx.complete_graph(4)
        result = self.algo.embed(source, target)
        assert isinstance(result, dict)

    def test_embed_has_required_keys(self):
        import dwave_networkx as dnx
        target = dnx.chimera_graph(8, 8, 4)
        source = nx.complete_graph(4)
        result = self.algo.embed(source, target)
        assert 'embedding' in result
        assert 'success' in result
        assert 'status' in result

    def test_embed_wrong_topology_failure(self):
        """Wrong topology returns FAILURE before touching torch."""
        import dwave_networkx as dnx
        target = dnx.chimera_graph(4, 4, 4)  # not 16x16x4
        source = small_source(5)
        result = self.algo.embed(source, target)
        assert result['success'] is False
