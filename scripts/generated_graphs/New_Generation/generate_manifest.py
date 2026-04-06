import argparse
import hashlib
import json
import sys
from pathlib import Path

# Anchors everything to the directory where the script is located
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
DEFAULT_LIBRARY_DIR = SCRIPT_DIR / "library"

def generate_manifest(
    library_dir: Path,
    manifest_path: Path,
    version: str = "1.0.0",
    dry_run: bool = False,
) -> Path:
    """
    Scans library_dir for JSON graphs and writes a manifest to manifest_path.
    """
    if not library_dir.exists():
        print(f"Error: Library directory not found: {library_dir}", file=sys.stderr)
        sys.exit(1)

    entries = []

    # Recursively find all .json files
    for json_file in sorted(library_dir.rglob("*.json")):
        # Skip the manifest itself if it happens to be in the search path
        if json_file.resolve() == manifest_path.resolve():
            continue

        # Extract ID from filename prefix (e.g., "001_graph.json" -> 1)
        prefix = json_file.stem.split("_", 1)[0]
        try:
            gid = int(prefix)
        except ValueError:
            # Skip files that don't start with an integer ID
            continue

        try:
            raw = json_file.read_bytes()
            data = json.loads(raw)
            meta = data.get("metadata", {})

            entries.append({
                "id":         gid,
                "type":       meta.get("type", data.get("category", "unknown")),
                "parameters": {k: v for k, v in meta.items() if k != "type"},
                "nodes":      data.get("num_nodes", 0),
                "edges":      data.get("num_edges", 0),
                "difficulty": meta.get("difficulty"), 
                "hash":       hashlib.sha256(raw).hexdigest(),
                "url":        None,
                "size_bytes": len(raw),
            })
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not process {json_file.name}: {e}")
            continue

    entries.sort(key=lambda e: e["id"])
    manifest = {"version": version, "graphs": entries}
    content = json.dumps(manifest, indent=2) + "\n"

    if dry_run:
        print(f"[dry-run] Would write {len(entries)} entries to {manifest_path}")
    else:
        manifest_path.write_text(content, encoding="utf-8")
        print(f"Success: Written {len(entries)} entries to {manifest_path}")

    return manifest_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Graph Manifest Generator")
    parser.add_argument("--library-dir", type=Path, default=DEFAULT_LIBRARY_DIR,
                        help=f"Source of JSON graphs (default: {DEFAULT_LIBRARY_DIR})")
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH,
                        help=f"Output file (default: {DEFAULT_MANIFEST_PATH})")
    parser.add_argument("--version", type=str, default="1.0.0",
                        help="Manual version string for the manifest")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    
    args = parser.parse_args()

    generate_manifest(
        library_dir=args.library_dir,
        manifest_path=args.manifest_path,
        version=args.version,
        dry_run=args.dry_run,
    )