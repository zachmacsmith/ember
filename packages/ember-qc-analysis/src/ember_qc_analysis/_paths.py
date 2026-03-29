"""
ember_qc_analysis/_paths.py
============================
User data directory resolution for ember-qc-analysis.

Platform-appropriate directories:
  Linux:   ~/.local/share/ember-qc-analysis/
  macOS:   ~/Library/Application Support/ember-qc-analysis/
  Windows: C:\\Users\\name\\AppData\\Local\\ember-qc-analysis\\ember-qc-analysis\\
"""

import logging
from pathlib import Path

from platformdirs import user_data_dir

logger = logging.getLogger(__name__)

_APP_NAME   = "ember-qc-analysis"
_APP_AUTHOR = "ember-qc-analysis"


def get_user_dir() -> Path:
    """Return the platform-appropriate user data directory, creating it if needed."""
    path = Path(user_data_dir(_APP_NAME, _APP_AUTHOR))
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning(
            "ember-qc-analysis: could not create user data directory %s: %s. "
            "Configuration will not persist.",
            path, exc,
        )
    return path


def get_user_config_path() -> Path:
    """Return the path to config.json (may not exist yet)."""
    return get_user_dir() / "config.json"
