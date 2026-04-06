#!/usr/bin/env python3
"""Fix JSON name fields that don't match their filename.

After renaming files to replace '.' with '-' in the beta value
(e.g. ws_n10_k4_b0.30_s0.json -> ws_n10_k4_b0-30_s0.json), the
`name` field inside the JSON still has the old value. This script
syncs name to match the filename stem.

Usage:
    python fix_graph_names.py                         # dry run
    python fix_graph_names.py --apply                 # write changes
    python fix_graph_names.py --type watts_strogatz   # one type only
"""

import argparse
import json
from pathlib import Path

GRAPH_DIR = Path("/Users/zachmacaskill-smith/Dropbox/Zach_Dropbox/Code/Research/ember/scripts/generated_graphs/New_Generation/libary/library2")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Write changes (default is dry run)")
    parser.add_argument("--type", metavar="TYPE",
                        help="Only process this graph type subdirectory")
    args = parser.parse_args()

    subdirs = ([GRAPH_DIR / args.type] if args.type
               else [d for d in sorted(GRAPH_DIR.iterdir()) if d.is_dir()])

    fixed = 0
    checked = 0

    for subdir in subdirs:
        for filepath in sorted(subdir.glob("*.json")):
            checked += 1
            # Filename format is "{id}_{name}.json" — strip the leading ID
            expected_name = "_".join(filepath.stem.split("_")[1:])

            with open(filepath) as f:
                data = json.load(f)

            current_name = data.get("name", "")

            if current_name == expected_name:
                continue

            print(f"  {'FIX' if args.apply else 'DRY'} {filepath.name}")
            print(f"       name: {current_name!r}")
            print(f"         -> {expected_name!r}")

            if args.apply:
                data["name"] = expected_name
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2)

            fixed += 1

    print(f"\nChecked {checked} files, {'fixed' if args.apply else 'would fix'} {fixed}.")
    if not args.apply and fixed > 0:
        print("Run with --apply to write changes.")


if __name__ == "__main__":
    main()