import argparse
import hashlib
import json
import sys
from pathlib import Path

# Anchors
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LIBRARY_DIR = Path("/Users/zachmacaskill-smith/Dropbox/Zach_Dropbox/Code/Research/ember/scripts/generated_graphs/New_Generation/libary/library2")
DEFAULT_MANIFEST_PATH = SCRIPT_DIR / "manifest2.json"

def generate_manifest(
    library_dir: Path,
    manifest_path: Path,
    version: str = "1.0.0",
    dry_run: bool = False,
):
    if not library_dir.exists():
        print(f"Error: Directory not found: {library_dir}", file=sys.stderr)
        sys.exit(1)

    entries = []
    
    # Use rglob to find all JSONs recursively
    json_files = sorted(library_dir.rglob("*.json"))
    total_files = len(json_files)
    
    print(f"Processing {total_files} files...")

    for i, json_file in enumerate(json_files):
        # Prevent self-inclusion
        if json_file.resolve() == manifest_path.resolve():
            continue

        try:
            raw = json_file.read_bytes()
            data = json.loads(raw)
            meta = data.get("metadata", {})

            # 1. Extraction with fallbacks
            gid   = data.get("id")
            gname = data.get("name")
            
            # If JSON is missing ID/Name, attempt to parse from filename: "ID_NAME.json"
            if gid is None or gname is None:
                parts = json_file.stem.split("_", 1)
                try:
                    gid = gid if gid is not None else int(parts[0])
                    gname = gname if gname is not None else (parts[1] if len(parts) > 1 else json_file.stem)
                except (ValueError, IndexError):
                    continue

            # 2. Build lean entry (Short keys to save manifest KB)
            # We exclude the URL because it is predictable: base_url/{id}_{name}.json
            entry = {
                "id":   gid,
                "name": gname,
                "type": data.get("category", meta.get("type", "unknown")),
                "n":    data.get("num_nodes", 0),
                "e":    data.get("num_edges", 0),
                "d":    round(data.get("density", 0), 4),
                "h":    hashlib.sha256(raw).hexdigest()[:16], # Truncated hash for size or full? Full is safer.
                "sz":   len(raw)
            }
            
            # Optional: Include specific generation params if they exist
            # This keeps the manifest searchable by logic like "n=3, m=1"
            params = {k: v for k, v in meta.items() if k not in ["type", "topologies"]}
            if params:
                entry["p"] = params
            
            # Promote topologies to a list if present
            if "topologies" in meta:
                entry["topo"] = meta["topologies"]

            entries.append(entry)

            if i % 1000 == 0 and i > 0:
                print(f"  Progress: {i}/{total_files}...")

        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Skipping {json_file.name} due to error: {e}")

    # Sort by ID for consistent diffs in git
    entries.sort(key=lambda x: x["id"])

    manifest_data = {
        "version": version,
        "count": len(entries),
        "graphs": entries
    }

    if dry_run:
        print(f"\n[Dry-run] Would write {len(entries)} entries to {manifest_path}")
    else:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, separators=(',', ':')) # Compact encoding
        print(f"\nSuccess: Manifest written to {manifest_path}")
        print(f"Final size: {manifest_path.stat().st_size / 1024:.2f} KB")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--library-dir", type=Path, default=DEFAULT_LIBRARY_DIR)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--version", type=str, default="1.0.0")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    generate_manifest(args.library_dir, args.manifest_path, args.version, args.dry_run)