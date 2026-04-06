#!/usr/bin/env python3
"""
deploy_to_hf.py — Flatten and upload the EMBER graph library to HuggingFace.

Usage:
    python deploy_to_hf.py <source_dir>
    python deploy_to_hf.py <source_dir> --token hf_xxx
    python deploy_to_hf.py <source_dir> --skip-flatten   # reuse existing staging
    python deploy_to_hf.py <source_dir> --dry-run        # flatten only, no upload
"""

import argparse
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID    = "zachmacsmith/ember-graphs"
REPO_TYPE  = "dataset"
SKIP_FILES = {"id_ranges.json"}   # housekeeping files, not graph instances


# =============================================================================
# Phase 1: Flatten
# =============================================================================

# Graph types that must be split into subdirectories to stay under HF's
# 10,000 files-per-directory limit. Maps category name -> (filename_pattern, subdir_fn)
# subdir_fn takes a filename and returns the subdirectory suffix to append.

import re as _re

def _ws_subdir(filename: str) -> str:
    """Extract k value from a watts_strogatz filename and return subdir name."""
    m = _re.search(r'_k(\d+)_', filename)
    return f"watts_strogatz_k{m.group(1)}" if m else "watts_strogatz_other"

SPLIT_RULES: dict[str, callable] = {
    "watts_strogatz": _ws_subdir,
}


def count_library(source_dir: Path) -> tuple[int, dict[str, Path]]:
    """Count graph JSON files and build a mapping of file -> upload destination.

    For categories in SPLIT_RULES, files are remapped to a subdirectory
    (e.g. watts_strogatz/file.json -> watts_strogatz_k4/file.json) so that
    no single HuggingFace directory exceeds 10,000 files.

    Returns:
        (count, file_map) where file_map maps source Path -> repo-relative path str
    """
    file_map: dict[Path, str] = {}
    for json_file in sorted(source_dir.rglob("*.json")):
        if json_file.name in SKIP_FILES:
            continue
        # Determine the category from the parent directory name
        category = json_file.parent.name
        if category in SPLIT_RULES:
            subdir = SPLIT_RULES[category](json_file.name)
        else:
            subdir = category
        file_map[json_file] = f"{subdir}/{json_file.name}"

    # Sanity check: warn if any target directory still exceeds 10k
    dest_counts: dict[str, int] = {}
    for dest in file_map.values():
        d = dest.split("/")[0]
        dest_counts[d] = dest_counts.get(d, 0) + 1
    for d, n in sorted(dest_counts.items()):
        if n > 10000:
            print(f"WARNING: {d}/ has {n} files — still exceeds HF 10k limit.")
        else:
            print(f"  {d}/: {n} files")

    return len(file_map), file_map


# =============================================================================
# Phase 2: Upload
# =============================================================================

def _build_staging(source_dir: Path, file_map: dict, staging_dir: Path) -> None:
    """Copy files into a staging directory with the split structure applied."""
    import shutil as _shutil
    if staging_dir.exists():
        _shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)
    for src, dest_rel in file_map.items():
        dest = staging_dir / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        _shutil.copy2(src, dest)


def upload(source_dir: Path, repo_id: str, token: str | None,
           count: int, file_map: dict, dry_run: bool):
    """Stage split directories and upload to HuggingFace.

    Categories in SPLIT_RULES are reorganised into subdirectories
    (e.g. watts_strogatz_k4/) so no HF directory exceeds 10,000 files.
    A temporary staging directory is built, uploaded, then removed.
    """
    staging_dir = source_dir.parent / ".hf_staging"

    if dry_run:
        print(f"Dry run — would upload {count:,} graphs to {repo_id}")
        return

    print(f"\nBuilding staging directory...")
    _build_staging(source_dir, file_map, staging_dir)
    print(f"Staging ready: {staging_dir}")

    print(f"\nUploading {count:,} graphs to {repo_id}...")
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type=REPO_TYPE, exist_ok=True)

    try:
        api.upload_large_folder(
            repo_id=repo_id,
            folder_path=staging_dir,
            repo_type=REPO_TYPE,
            ignore_patterns=["*.cache", "*.tmp", ".huggingface"],
            print_report=True,
            print_report_every=30,
        )
    finally:
        import shutil as _shutil
        _shutil.rmtree(staging_dir, ignore_errors=True)

    print(f"\nDone: https://huggingface.co/datasets/{repo_id}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Deploy the EMBER graph library to HuggingFace.",
        epilog=(
            "The nested {category}/{id}_{name}.json structure is uploaded directly.\n"
            "Each category subdirectory stays under HuggingFace's 10k file limit.\n"
            "If interrupted, rerun the same command — upload_large_folder resumes automatically."
        ),
    )
    parser.add_argument(
        "source", type=Path,
        help="Local library directory (contains category subdirectories).",
    )
    parser.add_argument(
        "--token", type=str, default=None,
        help="HuggingFace write token. Omit if logged in via `huggingface-cli login`.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Count files and validate structure without uploading.",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Error: source directory does not exist: {args.source}")
        sys.exit(1)

    count, file_map = count_library(args.source)
    print(f"\nFound {count:,} graphs in {args.source}")

    upload(args.source, REPO_ID, args.token, count, file_map, args.dry_run)


if __name__ == "__main__":
    main()