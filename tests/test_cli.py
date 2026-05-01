"""
tests/test_cli.py
==================
Tests for ember_qc.cli — verifying argument-parser changes introduced in v1.4.0
(charme added to install-binary choices) and other CLI surface.
"""
import pytest
from ember_qc.cli import build_parser


# ===========================================================================
# install-binary parser
# ===========================================================================

class TestInstallBinaryParser:
    def setup_method(self):
        self.parser = build_parser()

    def _parse(self, args):
        return self.parser.parse_args(args)

    def test_charme_is_valid_choice(self):
        ns = self._parse(["install-binary", "charme"])
        assert ns.name == "charme"

    def test_atom_still_valid(self):
        ns = self._parse(["install-binary", "atom"])
        assert ns.name == "atom"

    def test_oct_still_valid(self):
        ns = self._parse(["install-binary", "oct"])
        assert ns.name == "oct"

    def test_unknown_binary_rejected(self):
        with pytest.raises(SystemExit):
            self._parse(["install-binary", "unknown_binary_xyz"])

    def test_list_flag_accepted(self):
        ns = self._parse(["install-binary", "--list"])
        assert ns.list_binaries is True

    def test_force_flag_accepted(self):
        ns = self._parse(["install-binary", "charme", "--force"])
        assert ns.force is True

    def test_version_flag_accepted(self):
        ns = self._parse(["install-binary", "charme", "--version", "1.2.3"])
        assert ns.binary_version == "1.2.3"

    def test_name_optional_with_list(self):
        # --list without a name is valid (prints the list)
        ns = self._parse(["install-binary", "--list"])
        assert ns.name is None


# ===========================================================================
# Top-level subcommands presence
# ===========================================================================

class TestTopLevelSubcommands:
    """Verify expected subcommands are registered in the parser."""

    def _subcommand_names(self):
        parser = build_parser()
        subparsers_actions = [
            a for a in parser._subparsers._actions
            if hasattr(a, '_name_parser_map')
        ]
        assert len(subparsers_actions) > 0
        return list(subparsers_actions[0]._name_parser_map.keys())

    def test_install_binary_subcommand_exists(self):
        assert "install-binary" in self._subcommand_names()

    def test_run_subcommand_exists(self):
        assert "run" in self._subcommand_names()

    def test_results_subcommand_exists(self):
        assert "results" in self._subcommand_names()


# ===========================================================================
# Parser produces correct defaults
# ===========================================================================

class TestInstallBinaryDefaults:
    def test_force_defaults_false(self):
        parser = build_parser()
        ns = parser.parse_args(["install-binary", "charme"])
        assert ns.force is False

    def test_version_defaults_none(self):
        parser = build_parser()
        ns = parser.parse_args(["install-binary", "charme"])
        assert ns.binary_version is None

    def test_list_defaults_false(self):
        parser = build_parser()
        ns = parser.parse_args(["install-binary", "charme"])
        assert ns.list_binaries is False
