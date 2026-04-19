#!/usr/bin/env python3
"""
upload_hypercube.py — Overwrite ONLY the hypercube/ subfolder on HuggingFace.

Use this after regenerating the local hypercube JSONs (e.g. to fix the
tuple-vs-int node-label bug). Other categories on HF are left untouched.

Usage:
    python upload_hypercube.py
    python upload_hypercube.py --token hf_xxx
    python upload_hypercube.py --source /path/to/local/hypercube/dir
    python upload_hypercube.py --dry-run

The local source directory must contain the regenerated files directly,
e.g. <source>/4750_hypercube_Q2.json, ..., 4760_hypercube_Q12.json.
By default the script targets the in-repo regeneration location:
    scripts/generated_graphs/New_Generation/libary/library2/hypercube/
"""

import argparse
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID    = "zachmacsmith/ember-graphs"
REPO_TYPE  = "dataset"
PATH_IN_REPO = "hypercube"   # subfolder on HF to overwrite

DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "scripts" / "generated_graphs" / "New_Generation"
    / "libary" / "library2" / "hypercube"
)


def main():
    parser = argparse.ArgumentParser(
        description="Upload only the hypercube/ folder, overwriting on HuggingFace.",
    )
    parser.add_argument(
        "--source", type=Path, default=DEFAULT_SOURCE,
        help=f"Local hypercube directory to upload (default: {DEFAULT_SOURCE}).",
    )
    parser.add_argument(
        "--token", type=str, default=None,
        help="HuggingFace write token. Omit if logged in via `huggingface-cli login`.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List files that would be uploaded without uploading.",
    )
    args = parser.parse_args()

    if not args.source.exists() or not args.source.is_dir():
        print(f"Error: source directory not found or not a directory: {args.source}")
        sys.exit(1)

    files = sorted(args.source.glob("*.json"))
    if not files:
        print(f"Error: no .json files in {args.source}")
        sys.exit(1)

    print(f"Source:       {args.source}")
    print(f"Repo:         {REPO_ID} ({REPO_TYPE})")
    print(f"Path in repo: {PATH_IN_REPO}/")
    print(f"Files ({len(files)}):")
    for f in files:
        print(f"  {f.name}  ({f.stat().st_size:,} B)")

    if args.dry_run:
        print("\nDry run — nothing uploaded.")
        return

    api = HfApi(token=args.token)
    api.create_repo(repo_id=REPO_ID, repo_type=REPO_TYPE, exist_ok=True)

    print(f"\nUploading {len(files)} files to {REPO_ID}:{PATH_IN_REPO}/ ...")
    # upload_folder upserts: existing files at the same repo path are
    # overwritten; files outside the listed allow_patterns / folder are
    # left untouched.
    api.upload_folder(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        folder_path=str(args.source),
        path_in_repo=PATH_IN_REPO,
        allow_patterns=["*.json"],
        commit_message="Fix hypercube graphs: relabel tuple nodes to integers",
    )
    print(f"\nDone: https://huggingface.co/datasets/{REPO_ID}/tree/main/{PATH_IN_REPO}")


if __name__ == "__main__":
    main()
