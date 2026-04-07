"""
ember_qc/config.py
==================
User-level persistent configuration for ember-qc.

User data directory (OS-conventional, survives pip upgrades):
  Linux:   ~/.local/share/ember-qc/
  macOS:   ~/Library/Application Support/ember-qc/
  Windows: C:\\Users\\<user>\\AppData\\Local\\ember-qc\\ember-qc\\

Subdirectory layout:
  config.json       — persistent user config (written only when a key is set)
  algorithms/       — TODO: custom user algorithm files (not yet loaded)
  binaries/         — compiled C++ binaries installed via `ember install-binary`

Priority order (highest to lowest):
  1. Explicit argument passed at call time
  2. Environment variable  (EMBER_OUTPUT_DIR, EMBER_WORKERS, etc.)
  3. Stored config         (config.json)
  4. Package default

Public API:
  ensure_user_dirs()            -> None   (called automatically on import)
  get(key, explicit=None)       -> resolved value
  set_value(key, value)         -> None   (writes to config.json)
  reset()                       -> None   (deletes config.json)
  show()                        -> dict   ({key: {value, source}})
  resolve_output_dir(explicit)  -> Path | None

Path helpers are in ember_qc._paths:
  get_user_dir(), get_user_algo_dir(), get_user_binary_dir(), get_user_config_path()
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ember_qc._paths import get_user_dir, get_user_config_path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema: defaults and environment variable names
# ---------------------------------------------------------------------------

CONFIG_SCHEMA: Dict[str, Dict[str, Any]] = {
    "output_dir": {
        "default":  None,
        "env_var":  "EMBER_OUTPUT_DIR",
        "type":     (str, type(None)),
        "description": "Directory where benchmark results are written. "
                       "Null means ./results/ in the current working directory.",
    },
    "unfinished_dir": {
        "default":  "default",
        "env_var":  "EMBER_UNFINISHED_DIR",
        "type":     (str, type(None)),
        "description": (
            "Where in-progress and paused benchmark runs are staged. "
            "\"default\" — platform user data dir (~/.local/share/ember-qc/runs_unfinished/ on Linux). "
            "\"child\" — .runs_unfinished/ folder next to the output_dir, guaranteed same filesystem. "
            "Any other value is treated as an explicit directory path."
        ),
    },
    "default_workers": {
        "default":  1,
        "env_var":  "EMBER_WORKERS",
        "type":     int,
        "description": "Number of parallel workers for benchmark runs.",
    },
    "default_timeout": {
        "default":  60.0,
        "env_var":  "EMBER_TIMEOUT",
        "type":     float,
        "description": "Per-trial timeout in seconds.",
    },
    "default_topology": {
        "default":  None,
        "env_var":  "EMBER_TOPOLOGY",
        "type":     (str, type(None)),
        "description": "Target topology to run against. Null means all topologies.",
    },
    "default_graphs": {
        "default":  None,
        "env_var":  "EMBER_GRAPHS",
        "type":     (str, type(None)),
        "description": "Default graph selection string or preset name. "
                       "Null means all graphs (\"*\").",
    },
    "default_n_trials": {
        "default":  1,
        "env_var":  "EMBER_N_TRIALS",
        "type":     int,
        "description": "Number of measured trials per (problem, algorithm, topology) combination.",
    },
    "default_warmup_trials": {
        "default":  0,
        "env_var":  "EMBER_WARMUP_TRIALS",
        "type":     int,
        "description": "Number of warmup trials to discard before measuring.",
    },
    "default_seed": {
        "default":  42,
        "env_var":  "EMBER_SEED",
        "type":     int,
        "description": "Master random seed for reproducible runs.",
    },
    "default_fault_rate": {
        "default":  0.0,
        "env_var":  "EMBER_FAULT_RATE",
        "type":     float,
        "description": "Fraction of topology qubits to remove randomly. 0.0 means no faults.",
    },
    "log_level": {
        "default":  "WARNING",
        "env_var":  "EMBER_LOG_LEVEL",
        "type":     str,
        "description": "Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    },
    "default_verbose": {
        "default":  None,
        "env_var":  "EMBER_VERBOSE",
        "type":     (bool, type(None)),
        "description": "Print per-trial output. True = verbose, False = progress bar, "
                       "null = auto (verbose when n_workers == 1).",
    },
}

_SENTINEL = object()  # used to distinguish "not passed" from None


# ---------------------------------------------------------------------------
# User data directory
# ---------------------------------------------------------------------------

# Re-export the most commonly needed path helper so callers can do:
#   from ember_qc.config import get_user_data_dir
get_user_data_dir = get_user_dir
get_config_path   = get_user_config_path


def ensure_user_dirs() -> None:
    """
    Create the user data directory and required subdirectories.

    Safe to call multiple times — a no-op if directories already exist.
    Degrades gracefully if the directory cannot be created (logs a warning,
    does not raise).
    """
    from ember_qc._paths import (
        get_user_dir, get_user_algo_dir, get_user_binary_dir,
        get_user_unfinished_dir, get_user_graphs_dir,
    )
    try:
        get_user_dir().mkdir(parents=True, exist_ok=True)
        get_user_binary_dir().mkdir(exist_ok=True)
        get_user_unfinished_dir().mkdir(exist_ok=True)

        # algorithms/ exists for future custom algorithm registration.
        # TODO: load .py files from this directory at init time so user-defined
        #       algorithms are automatically available in the registry.
        #       See TODO_userConfig.md §3 (Custom Algorithm Registration).
        get_user_algo_dir().mkdir(exist_ok=True)

        # graphs/ caches graph files fetched from remote (Phase 2).
        # During Phase 1 all graphs are bundled; this directory is always empty.
        graphs_dir = get_user_graphs_dir()
        graphs_dir.mkdir(exist_ok=True)
        local_index = graphs_dir / "local_index.json"
        if not local_index.exists():
            local_index.write_text("{}\n", encoding="utf-8")

    except OSError as exc:
        logger.warning(
            "ember-qc: could not create user data directory %s: %s. "
            "Built-in algorithms and package defaults will still work.",
            get_user_dir(), exc,
        )


# ---------------------------------------------------------------------------
# Config file I/O
# ---------------------------------------------------------------------------

def _load_stored() -> Dict[str, Any]:
    """Read config.json; return {} if it does not exist or cannot be parsed."""
    path = get_user_config_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("ember-qc: config.json is not a JSON object — ignoring.")
            return {}
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("ember-qc: could not read config.json (%s) — using defaults.", exc)
        return {}


def _write_stored(data: Dict[str, Any]) -> None:
    """Write config.json, creating the user data directory first."""
    ensure_user_dirs()
    path = get_user_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _coerce(key: str, raw: str) -> Any:
    """
    Coerce a string value (from an environment variable) to the expected type.
    Raises ValueError with a helpful message on failure.
    """
    expected = CONFIG_SCHEMA[key]["type"]
    # Handle nullable types
    if isinstance(expected, tuple) and type(None) in expected:
        if raw.lower() in ("null", "none", ""):
            return None
        # Strip None from the tuple and coerce to the remaining type
        non_none = [t for t in expected if t is not type(None)]
        expected = non_none[0] if non_none else str

    if expected is bool:
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"Expected boolean for '{key}', got: {raw!r}")

    try:
        return expected(raw)
    except (ValueError, TypeError):
        raise ValueError(
            f"Config key '{key}' expects type {expected.__name__}, "
            f"could not coerce: {raw!r}"
        )


def _validate(key: str, value: Any) -> None:
    """Raise ValueError if value is not a valid type for key."""
    if key not in CONFIG_SCHEMA:
        valid = ", ".join(sorted(CONFIG_SCHEMA))
        raise ValueError(f"Unknown config key: {key!r}. Valid keys: {valid}")

    expected = CONFIG_SCHEMA[key]["type"]
    if not isinstance(value, expected):
        if isinstance(expected, tuple):
            type_names = " | ".join(t.__name__ for t in expected)
        else:
            type_names = expected.__name__
        raise ValueError(
            f"Config key '{key}' expects {type_names}, got {type(value).__name__}: {value!r}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get(key: str, explicit: Any = _SENTINEL) -> Any:
    """
    Resolve a config value using the priority chain:
      explicit arg > environment variable > stored config > package default

    Parameters
    ----------
    key      : config key name (see CONFIG_SCHEMA)
    explicit : value passed at call time; if provided (including None), it
               wins over all other sources

    Returns
    -------
    The resolved value, already coerced to the correct type.
    """
    if key not in CONFIG_SCHEMA:
        valid = ", ".join(sorted(CONFIG_SCHEMA))
        raise ValueError(f"Unknown config key: {key!r}. Valid keys: {valid}")

    schema = CONFIG_SCHEMA[key]

    # 1. Explicit argument
    if explicit is not _SENTINEL:
        return explicit

    # 2. Environment variable
    env_raw = os.environ.get(schema["env_var"])
    if env_raw is not None:
        return _coerce(key, env_raw)

    # 3. Stored config
    stored = _load_stored()
    if key in stored:
        value = stored[key]
        # Silently ignore keys with wrong types (backwards compatibility)
        try:
            _validate(key, value)
            return value
        except ValueError:
            logger.warning(
                "ember-qc: stored config key '%s' has unexpected type — using default.", key
            )

    # 4. Package default
    return schema["default"]


def set_value(key: str, value: Any) -> None:
    """
    Write a config value to config.json.

    Validates the key and type before writing. Raises ValueError on failure.
    """
    _validate(key, value)
    stored = _load_stored()
    stored[key] = value
    _write_stored(stored)


def reset() -> None:
    """Delete config.json, reverting all keys to package defaults."""
    path = get_user_config_path()
    if path.exists():
        path.unlink()


def show() -> Dict[str, Dict[str, Any]]:
    """
    Return a dict describing the current resolved state of all config keys.

    Each entry has the form:
      {
        "value":   <resolved value>,
        "source":  "explicit" | "env" | "stored" | "default",
        "env_var": "EMBER_...",
      }

    "explicit" is never returned here (no call-time arg is known at this level).
    """
    stored = _load_stored()
    result = {}
    for key, schema in CONFIG_SCHEMA.items():
        env_raw = os.environ.get(schema["env_var"])
        if env_raw is not None:
            try:
                value = _coerce(key, env_raw)
                source = "env"
            except ValueError:
                value = schema["default"]
                source = "default"
        elif key in stored:
            try:
                _validate(key, stored[key])
                value = stored[key]
                source = "stored"
            except ValueError:
                value = schema["default"]
                source = "default"
        else:
            value = schema["default"]
            source = "default"

        result[key] = {
            "value":   value,
            "source":  source,
            "env_var": schema["env_var"],
            "description": schema["description"],
        }
    return result


def resolve_unfinished_dir(setting: Optional[str], output_dir: Optional[str] = None) -> Path:
    """Resolve the staging directory for in-progress runs.

    Parameters
    ----------
    setting : value of the ``unfinished_dir`` config key, or None.
        ``None`` / ``"default"`` — platform user data dir.
        ``"child"``              — ``.runs_unfinished/`` next to *output_dir*,
                                   guaranteeing same-filesystem atomic moves.
        Anything else            — treated as an explicit directory path.
    output_dir : resolved output directory (needed for ``"child"`` mode).
    """
    if not setting or setting == "default":
        from ember_qc._paths import get_user_unfinished_dir
        return get_user_unfinished_dir()
    if setting == "child":
        if output_dir:
            return Path(output_dir) / ".runs_unfinished"
        # output_dir unknown — fall back to user data dir with a warning
        logger.warning(
            "ember-qc: unfinished_dir=\"child\" requires output_dir to be set; "
            "falling back to platform user data dir."
        )
        from ember_qc._paths import get_user_unfinished_dir
        return get_user_unfinished_dir()
    # Explicit path
    return Path(setting)


def resolve_output_dir(explicit: Optional[str] = None) -> Optional[Path]:
    """
    Single shared function for resolving the benchmark output directory.

    Priority: explicit arg > EMBER_OUTPUT_DIR env var > stored config > None
    Returns None when no output dir is configured (caller uses CWD / default).
    """
    raw = get("output_dir", explicit=explicit if explicit is not None else _SENTINEL)
    return Path(raw).expanduser() if raw is not None else None


# ---------------------------------------------------------------------------
# Initialise user dirs on import
# ---------------------------------------------------------------------------
ensure_user_dirs()
