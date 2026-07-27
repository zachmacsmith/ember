#!/usr/bin/env bash
# Deploy the paper3 working tree's TRACKED files to hyde06:/data/dabh/ember.
# Tracked-only is deliberate: experiments must run from committed state
# (docs/paper3/protocol.md rule 6 — script@sha pre-registration).
# Usage: bash scripts/hyde06_sync.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if ! git diff-index --quiet HEAD -- docs/paper3/data/ 2>/dev/null; then
  echo "WARNING: uncommitted changes under docs/paper3/data/ will NOT deploy." >&2
fi
git ls-files | rsync -az --files-from=- ./ hyde06.dabh.io:/data/dabh/ember/
echo "synced $(git rev-parse --short HEAD) -> hyde06:/data/dabh/ember"
echo "remote runs: ssh hyde06.dabh.io 'cd /data/dabh/ember && . ./env.sh && ...'"
