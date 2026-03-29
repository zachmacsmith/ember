"""
ember_qc_analysis/_config.py
=============================
Configuration system for ember-qc-analysis.

Priority order (highest to lowest):
  1. Explicit argument passed at call time
  2. Environment variable  (EMBER_ANALYSIS_INPUT_DIR, etc.)
  3. Stored config         (config.json)
  4. Package default

Config keys:
  input_dir    — directory where ember-qc results live
  output_dir   — directory where analysis outputs are written
  fig_format   — output figure format: png, pdf, svg
  active_batch — currently staged batch path (session state)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ember_qc_analysis._paths import get_user_config_path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

DEFAULTS: Dict[str, Any] = {
    "input_dir":    None,
    "output_dir":   None,
    "fig_format":   "png",
    "active_batch": None,
}

ENV_VARS: Dict[str, str] = {
    "input_dir":  "EMBER_ANALYSIS_INPUT_DIR",
    "output_dir": "EMBER_ANALYSIS_OUTPUT_DIR",
    "fig_format": "EMBER_ANALYSIS_FIG_FORMAT",
    # active_batch has no env var — it is session state
}

_VALID_FIG_FORMATS = {"png", "pdf", "svg"}

_TYPES: Dict[str, Any] = {
    "input_dir":    (str, type(None)),
    "output_dir":   (str, type(None)),
    "fig_format":   str,
    "active_batch": (str, type(None)),
}

_SENTINEL = object()


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def load_config() -> Dict[str, Any]:
    """Load stored config, merged over defaults. Unknown keys are ignored."""
    path = get_user_config_path()
    stored: Dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                stored = data
            else:
                logger.warning("ember-qc-analysis: config.json is not a JSON object — ignoring.")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("ember-qc-analysis: could not read config.json (%s) — using defaults.", exc)

    result = dict(DEFAULTS)
    for key in DEFAULTS:
        if key in stored:
            result[key] = stored[key]
    return result


def _write_config(data: Dict[str, Any]) -> None:
    path = get_user_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except OSError as exc:
        raise OSError(f"Could not write config: {exc}") from exc


def set_config(key: str, value: Any) -> None:
    """Validate key and type, then write to config.json."""
    if key not in DEFAULTS:
        valid = ", ".join(sorted(DEFAULTS))
        raise ValueError(f"Unknown config key '{key}'. Valid keys: {valid}")

    expected = _TYPES[key]
    if not isinstance(value, expected):
        if isinstance(expected, tuple):
            type_names = " | ".join(t.__name__ for t in expected)
        else:
            type_names = expected.__name__
        raise TypeError(f"'{key}' expects {type_names}, got {type(value).__name__}: {value!r}")

    if key == "fig_format" and value not in _VALID_FIG_FORMATS:
        raise ValueError(f"'fig_format' must be one of: {', '.join(sorted(_VALID_FIG_FORMATS))}")

    stored = load_config()
    stored[key] = value
    _write_config({k: v for k, v in stored.items() if k in DEFAULTS})


def get_config(key: str) -> Any:
    """Return the resolved value for key using the full priority chain."""
    return resolve(key)


def reset_config() -> None:
    """Delete config.json, reverting all keys to package defaults."""
    path = get_user_config_path()
    if path.exists():
        path.unlink()


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def resolve(key: str, explicit: Any = _SENTINEL) -> Any:
    """
    Resolve a config value using the full priority chain:
      explicit arg > environment variable > stored config > package default
    """
    if key not in DEFAULTS:
        valid = ", ".join(sorted(DEFAULTS))
        raise ValueError(f"Unknown config key '{key}'. Valid keys: {valid}")

    # 1. Explicit argument
    if explicit is not _SENTINEL:
        return explicit

    # 2. Environment variable (only for keys that have one)
    env_var = ENV_VARS.get(key)
    if env_var:
        raw = os.environ.get(env_var)
        if raw is not None:
            if raw.lower() in ("null", "none", ""):
                return None
            return raw

    # 3. Stored config
    stored = load_config()
    if stored.get(key) is not None:
        return stored[key]

    # 4. Default
    return DEFAULTS[key]


def get_output_dir(batch_dir: Path, explicit: Optional[str] = None) -> Path:
    """
    Resolve the output directory for analysis outputs.

    Priority:
      1. explicit arg (--output-dir flag)
      2. EMBER_ANALYSIS_OUTPUT_DIR env var
      3. Stored output_dir config
      4. Default: batch_dir/analysis/
    """
    resolved = resolve("output_dir", explicit=explicit if explicit is not None else _SENTINEL)
    if resolved:
        return Path(resolved)
    return batch_dir / "analysis"


# ---------------------------------------------------------------------------
# ember-qc output directory discovery
# ---------------------------------------------------------------------------

def _discover_emberqc_output_dir() -> Optional[Path]:
    """
    Opportunistically read ember-qc's configured output_dir.

    Attempts to import ember_qc._paths and read its config. Returns None
    silently on any failure — ember-qc may not be installed.
    """
    try:
        from ember_qc._paths import get_user_config_path as _qc_config_path
        qc_config = _qc_config_path()
        if not qc_config.exists():
            return None
        with open(qc_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("output_dir")
        if raw:
            return Path(raw)
    except Exception:
        pass
    return None


def _has_valid_batch(directory: Path) -> bool:
    """Return True if directory contains at least one valid ember-qc batch."""
    if not directory.exists():
        return False
    for child in directory.iterdir():
        if child.is_dir() and is_valid_batch(child):
            return True
    return False


# ---------------------------------------------------------------------------
# Batch validation
# ---------------------------------------------------------------------------

def is_valid_batch(path: Path) -> bool:
    """Return True if path is a valid ember-qc batch directory."""
    return path.is_dir() and (
        (path / "results.db").exists() or (path / "runs.csv").exists()
    )


def validate_batch(path: Path) -> None:
    """
    Raise ValueError with a clear message if path is not a valid batch.
    """
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    if not (path / "results.db").exists() and not (path / "runs.csv").exists():
        raise ValueError(
            f"Not a valid ember-qc batch directory: {path}\n"
            "Expected results.db (or runs.csv for older batches)."
        )


# ---------------------------------------------------------------------------
# Input directory resolution with ember-qc discovery
# ---------------------------------------------------------------------------

def resolve_input_dir(
    explicit: Optional[str] = None,
    prompt: bool = True,
) -> Optional[Path]:
    """
    Resolve the input directory, running ember-qc discovery if needed.

    Args:
        explicit: value from --input-dir flag
        prompt:   whether to show interactive prompts (False in non-interactive contexts)

    Returns:
        Resolved Path, or None if unresolved and prompt is False.

    Raises:
        SystemExit: if interactive resolution fails or is declined.
    """
    import sys

    # 1. Explicit arg
    if explicit is not None:
        return Path(explicit)

    # 2. Environment variable
    env_raw = os.environ.get("EMBER_ANALYSIS_INPUT_DIR")
    if env_raw:
        return Path(env_raw)

    # 3. Stored config
    stored = load_config()
    if stored.get("input_dir"):
        return Path(stored["input_dir"])

    if not prompt:
        return None

    # 4. ember-qc discovery
    discovered = _discover_emberqc_output_dir()
    if discovered and _has_valid_batch(discovered):
        print(f"\nNo input directory set. ember-qc output directory found:")
        print(f"  {discovered}")
        print()
        print("Use this as input directory?")
        print("  [1] Yes, for this session only")
        print("  [2] Yes, and save as default")
        print("  [3] No")
        try:
            choice = input("Choice [1/2/3]: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "3"

        if choice == "1":
            return discovered
        elif choice == "2":
            set_config("input_dir", str(discovered))
            print(f"Saved. To change later: ember-analysis config set input_dir <path>")
            return discovered
        # Fall through to error on "3" or anything else

    # 5. No input dir found
    print(
        "\nNo input directory set.\n"
        "Run: ember-analysis config set input_dir <path>\n"
        "  or: ember-analysis stage <batch_path>"
    )
    sys.exit(1)
