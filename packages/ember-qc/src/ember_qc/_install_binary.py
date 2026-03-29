"""
ember_qc/_install_binary.py
============================
Download and install pre-built C++ binaries (ATOM, OCT) from GitHub releases.

Binary assets are published to GitHub releases by the `publish-ember-qc.yml`
workflow under tags matching ``ember-qc-v*``.  Asset names follow the pattern::

    {binary}-{platform}        e.g.  atom-darwin-arm64

Install layout under ``get_user_binary_dir()``:

    binaries/
      atom/
        main              ← ATOM executable
        main.version      ← plain-text version string, e.g. "0.5.0"
      oct_based/
        embedding/
          driver          ← OCT executable
          driver.version  ← plain-text version string
"""

from __future__ import annotations

import json as _json
import os
import platform
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# GitHub repo that hosts release assets.
# Override with EMBER_GITHUB_REPO if you fork or mirror.
_GITHUB_REPO: str = os.environ.get(
    "EMBER_GITHUB_REPO", "zachmacsmith/ember"
)

# Maps (sys.platform, normalised machine) → asset suffix used in binary names.
_PLATFORM_MAP: dict[tuple[str, str], str] = {
    ("linux",  "x86_64"): "linux-x86_64",
    ("darwin", "arm64"):  "darwin-arm64",
    ("darwin", "x86_64"): "darwin-x86_64",
}

# Known installable binaries: name → path relative to get_user_binary_dir().
_BINARY_REL_PATHS: dict[str, Path] = {
    "atom": Path("atom") / "main",
    "oct":  Path("oct_based") / "embedding" / "driver",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalise_machine(raw: str) -> str:
    """Normalise platform.machine() output to the keys used in _PLATFORM_MAP."""
    m = raw.lower()
    if m in ("arm64", "aarch64"):
        return "arm64"
    return m


def _version_sidecar(binary_path: Path) -> Path:
    """Return the path of the .version file stored alongside a binary."""
    return binary_path.parent / (binary_path.name + ".version")


def _read_installed_version(binary_path: Path) -> Optional[str]:
    sidecar = _version_sidecar(binary_path)
    if sidecar.exists():
        return sidecar.read_text().strip() or None
    return None


def _write_installed_version(binary_path: Path, version: str) -> None:
    _version_sidecar(binary_path).write_text(version + "\n")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_platform() -> Tuple[Optional[str], str]:
    """Return ``(platform_suffix, description)``.

    ``platform_suffix`` is ``None`` when the platform is not supported.
    """
    machine = _normalise_machine(platform.machine())
    sys_name = sys.platform  # e.g. 'linux', 'darwin', 'win32'
    suffix = _PLATFORM_MAP.get((sys_name, machine))
    desc = f"{sys_name}/{machine}"
    return suffix, desc


def resolve_version(version: Optional[str] = None) -> str:
    """Return version string (e.g. ``'0.5.0'``).

    If *version* is given it is returned as-is.  Otherwise the latest
    ``ember-qc-v*`` release tag is fetched from the GitHub API and the
    ``ember-qc-v`` prefix is stripped.

    Raises ``RuntimeError`` on network failure or API rate-limit.
    """
    if version:
        return version

    url = f"https://api.github.com/repos/{_GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "GitHub API rate limit reached.\n"
                "Specify a version explicitly:  ember install-binary --version X.Y.Z"
            ) from exc
        raise RuntimeError(
            f"GitHub API error ({exc.code}) fetching latest release.\n"
            f"URL: {url}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Network error fetching latest release from GitHub:\n  {exc}\n"
            f"URL: {url}\n"
            "Specify a version explicitly:  ember install-binary --version X.Y.Z"
        ) from exc

    tag: str = data.get("tag_name", "")
    prefix = "ember-qc-v"
    if tag.startswith(prefix):
        return tag[len(prefix):]
    # Unexpected tag format — return as-is and let download fail with a clear URL.
    return tag


def build_asset_url(binary: str, platform_suffix: str, version: str) -> str:
    """Construct the GitHub release asset download URL."""
    tag = f"ember-qc-v{version}"
    asset = f"{binary}-{platform_suffix}"
    return f"https://github.com/{_GITHUB_REPO}/releases/download/{tag}/{asset}"


def install_binary(
    name: str,
    version: Optional[str] = None,
    force: bool = False,
) -> None:
    """Download and install *name* (``'atom'`` or ``'oct'``).

    Raises ``SystemExit`` on unrecoverable error so callers don't need to
    catch anything — the error message is already printed.
    """
    from ember_qc._paths import get_user_binary_dir

    if name not in _BINARY_REL_PATHS:
        known = ", ".join(sorted(_BINARY_REL_PATHS))
        print(f"Unknown binary '{name}'. Known binaries: {known}")
        sys.exit(1)

    dest: Path = get_user_binary_dir() / _BINARY_REL_PATHS[name]

    # ---- already installed? ------------------------------------------------
    if dest.exists() and not force:
        installed_ver = _read_installed_version(dest) or "unknown"
        print(f"{name} is already installed.")
        print(f"  Version : {installed_ver}")
        print(f"  Path    : {dest}")
        print(f"To reinstall:  ember install-binary {name} --force")
        return

    # ---- platform detection ------------------------------------------------
    platform_suffix, platform_desc = detect_platform()
    if platform_suffix is None:
        print(f"Unsupported platform: {platform_desc}")
        print(f"Pre-built binaries are available for: linux/x86_64, darwin/x86_64, darwin/arm64")
        print(f"To build from source, see:  external/{name}/BUILD.md")
        sys.exit(1)

    # ---- version resolution ------------------------------------------------
    try:
        ver = resolve_version(version)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    url = build_asset_url(name, platform_suffix, ver)
    print(f"Downloading {name} v{ver} for {platform_suffix} ...")
    print(f"  {url}")

    # ---- download to temp file, then move ----------------------------------
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Optional[Path] = None
    try:
        # Create temp file in the same directory as the destination so that
        # shutil.move is an atomic rename on the same filesystem.
        fd, tmp_str = tempfile.mkstemp(dir=dest.parent, prefix=f".{name}-download-")
        os.close(fd)
        tmp_path = Path(tmp_str)

        try:
            urllib.request.urlretrieve(url, tmp_path)
        except urllib.error.URLError as exc:
            print(f"Network error downloading {name}:")
            print(f"  {exc}")
            print(f"  URL: {url}")
            sys.exit(1)
        except Exception as exc:  # noqa: BLE001
            print(f"Unexpected error while downloading {name}: {exc}")
            print(f"  URL: {url}")
            sys.exit(1)

        shutil.move(str(tmp_path), dest)
        tmp_path = None  # ownership transferred

    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()

    # ---- set executable permissions ----------------------------------------
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # ---- write version sidecar ---------------------------------------------
    _write_installed_version(dest, ver)

    # ---- verify ------------------------------------------------------------
    # Neither ATOM nor OCT expose a --version flag; verification is a
    # simple existence + executable-bit check.
    if not dest.exists():
        print(f"Error: binary not found at expected path after install: {dest}")
        sys.exit(1)
    if not os.access(dest, os.X_OK):
        print(f"Error: binary at {dest} is not executable after install")
        sys.exit(1)

    print(f"Installed and verified: {name} → {dest}")


def list_binaries() -> None:
    """Print a formatted table of all known binaries and their install status."""
    from ember_qc._paths import get_user_binary_dir

    binary_dir = get_user_binary_dir()

    col_name    = 8
    col_status  = 15
    col_version = 9
    ruler = "─" * 72

    print(f"{'Binary':<{col_name}}  {'Status':<{col_status}}  {'Version':<{col_version}}  Path")
    print(ruler)

    for name, rel_path in _BINARY_REL_PATHS.items():
        path = binary_dir / rel_path
        if path.exists() and os.access(path, os.X_OK):
            ver = _read_installed_version(path) or "unknown"
            status = "✓ installed"
            display = str(path)
        elif path.exists():
            ver = _read_installed_version(path) or "unknown"
            status = "! not executable"
            display = str(path)
        else:
            ver = ""
            status = "✗ not installed"
            display = f"run: ember install-binary {name}"
        print(f"{name:<{col_name}}  {status:<{col_status}}  {ver:<{col_version}}  {display}")
