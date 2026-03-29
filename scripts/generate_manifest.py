"""
scripts/generate_manifest.py
=============================
Regenerate the graph library manifest.json from the bundled graph files.

Run this once after adding, removing, or modifying graphs in
  packages/ember-qc/src/ember_qc/graphs/library/
then commit the updated manifest.json.

Usage:
    python scripts/generate_manifest.py
    python scripts/generate_manifest.py --dry-run
"""

import argparse
import hashlib
import json
from pathlib import Path

_REPO_ROOT    = Path(__file__).resolve().parents[1]
_GRAPHS_DIR   = _REPO_ROOT / "packages" / "ember-qc" / "src" / "ember_qc" / "graphs"
LIBRARY_DIR   = _GRAPHS_DIR / "library"
MANIFEST_PATH = _GRAPHS_DIR / "manifest.json"


def _read_version() -> str:
    pyproject = _REPO_ROOT / "packages" / "ember-qc" / "pyproject.toml"
    try:
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("version") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return "dev"


def generate_manifest(
    library_dir: Path = LIBRARY_DIR,
    manifest_path: Path = MANIFEST_PATH,
    dry_run: bool = False,
) -> Path:
    """Regenerate manifest.json from the graph library directory.

    Args:
        library_dir:   Directory containing graph JSON files.
        manifest_path: Output path for manifest.json.
        dry_run:       Print what would be written without writing.

    Returns:
        Path to the manifest file (written or would-be written).
    """
    if not library_dir.exists():
        raise FileNotFoundError(f"Library directory not found: {library_dir}")

    version = _read_version()
    entries = []

    for json_file in sorted(library_dir.rglob("*.json")):
        prefix = json_file.stem.split("_", 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            continue

        raw  = json_file.read_bytes()
        data = json.loads(raw)
        meta = data.get("metadata", {})

        entries.append({
            "id":         gid,
            "type":       meta.get("type", data.get("category", "unknown")),
            "parameters": {k: v for k, v in meta.items() if k != "type"},
            "nodes":      data.get("num_nodes", 0),
            "edges":      data.get("num_edges", 0),
            "difficulty": None,
            "hash":       hashlib.sha256(raw).hexdigest(),
            "url":        None,
            "size_bytes": len(raw),
        })

    entries.sort(key=lambda e: e["id"])
    manifest = {"version": version, "graphs": entries}
    content  = json.dumps(manifest, indent=2) + "\n"

    if dry_run:
        print(f"[dry-run] Would write {len(entries)} entries to {manifest_path}")
        print(f"[dry-run] version: {version}")
    else:
        manifest_path.write_text(content, encoding="utf-8")
        print(f"Written {len(entries)} entries → {manifest_path}")
        print(f"version: {version}")

    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regenerate ember-qc graph manifest.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing")
    parser.add_argument("--library-dir", type=Path, default=LIBRARY_DIR,
                        help=f"Path to graph library directory (default: {LIBRARY_DIR})")
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH,
                        help=f"Output manifest path (default: {MANIFEST_PATH})")
    args = parser.parse_args()

    generate_manifest(
        library_dir=args.library_dir,
        manifest_path=args.manifest_path,
        dry_run=args.dry_run,
    )
