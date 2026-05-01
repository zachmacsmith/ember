"""
tests/test_presets.py
======================
Tests for graph preset loading — verifies new 'charme' and 'charme_easy'
presets are present and parseable.

API notes:
  - load_presets() → dict[str, str]  (raw CSV value strings, not parsed)
  - parse_graph_selection(spec: str) → Set[int]  (parses a single spec string)
  - list_presets() → List[str]
"""
import pytest
from ember_qc.load_graphs import load_presets, list_presets, parse_graph_selection


class TestCharmePresets:
    def setup_method(self):
        self.presets = load_presets()

    def test_charme_preset_exists(self):
        assert "charme" in self.presets, (
            f"'charme' missing from presets. Available: {list(self.presets.keys())}"
        )

    def test_charme_easy_preset_exists(self):
        assert "charme_easy" in self.presets, (
            f"'charme_easy' missing from presets. Available: {list(self.presets.keys())}"
        )

    def test_charme_preset_nonempty_raw_string(self):
        raw = self.presets["charme"]
        assert isinstance(raw, str) and len(raw) > 0

    def test_charme_easy_preset_nonempty_raw_string(self):
        raw = self.presets["charme_easy"]
        assert isinstance(raw, str) and len(raw) > 0

    def test_charme_easy_ids_start_at_90000(self):
        ids = parse_graph_selection("charme_easy")
        assert all(gid >= 90000 for gid in ids), (
            f"Expected all charme_easy IDs >= 90000; got {sorted(ids)[:5]}"
        )

    def test_charme_preset_ids_are_integers(self):
        ids = parse_graph_selection("charme")
        assert all(isinstance(gid, int) for gid in ids)

    def test_charme_easy_preset_ids_are_integers(self):
        ids = parse_graph_selection("charme_easy")
        assert all(isinstance(gid, int) for gid in ids)


class TestExistingPresets:
    """Smoke-test that pre-existing presets are still intact."""

    def setup_method(self):
        self.presets = load_presets()

    def test_small_preset_exists(self):
        assert "small" in self.presets

    def test_sensitivity_preset_exists(self):
        assert "sensitivity" in self.presets

    def test_list_presets_includes_charme(self):
        names = list_presets()
        assert "charme" in names
        assert "charme_easy" in names


class TestParseGraphSelection:
    def test_charme_preset_parseable(self):
        ids = parse_graph_selection("charme")
        assert isinstance(ids, (set, list))
        assert len(ids) > 0
        assert all(isinstance(i, int) for i in ids)

    def test_charme_easy_preset_parseable(self):
        ids = parse_graph_selection("charme_easy")
        assert isinstance(ids, (set, list))
        assert len(ids) > 0

    def test_charme_easy_count(self):
        ids = parse_graph_selection("charme_easy")
        # charme_easy has 45 entries per presets.csv (90000–90044)
        assert len(ids) == 45

    def test_charme_preset_ids_unique(self):
        ids = list(parse_graph_selection("charme"))
        assert len(ids) == len(set(ids)), "Duplicate IDs in 'charme' preset"
