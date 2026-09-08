# Frozen corpus adapter smoke

The pilot now accepts the predetermined 017 readiness selection. It verifies
selection identity, original ledger identity, normalized graph hashes and counts,
family membership consistency, and exact-content deduplication before freezing
tasks. Only integer vertices, unweighted edges and empty source attributes reach
the solver. Complete selection and missing-input provenance remain in sidecars;
execution and analysis verify those sidecars against the frozen manifest.

Before running the broader comparison, exercise the adapter end to end on one
selected path input (Ember ID 2030, 141 vertices), one seed, and two fixed methods:
stock MM and the unchanged width-one joint reference. This is a harness smoke,
not a new candidate selection or family-level comparison. A trivial sparse input
keeps this verification inexpensive. Preserve any algorithm failure faithfully.
Both methods receive 60 seconds, fresh processes, one numerical thread, and the
candidate uses the MM-free local environment. The frozen run is
`results/codex/018-corpus-adapter-smoke`; its manifest binds exact source, target,
input, configurations and selection sidecars.

Focused harness/corpus validation: 39 tests pass, including changes to source
records, leaked attributes, membership mismatch, duplicated structures, selection
hashes, shipped tasks and original missing-input sidecars. The full 34-input
selection also loads and verifies successfully. These checks establish data
handling only; they do not establish embedding quality.

Run command:

```sh
.venv/bin/python scripts/codex/pilot.py run results/codex/018-corpus-adapter-smoke
```

Both calls completed and passed the independent result/provenance analyzer.
MM returned ACL 1.0 in 0.1657 solver seconds; the fixed native reference returned
ACL 1.24113 in 6.5013 solver seconds. These are one local trial on one input,
including cold JIT cost, not timing distributions. The candidate's quality gap
and substantial overhead on this easy path remain failures to address, not
reasons to remove the input or introduce a path-specific dispatch.

Source snapshot: `a7c20a80d698305fe46bcf6be0e549c83f7ef1c7c95d76d1ef986aadb259ee70`.
Readiness identity: `06c02356f8df5503b57f280ba4939c298cc05834c563a3da8a71f96fe245db98`.
Full embeddings, wall/process measurements and validated tables are preserved
under the run directory. No candidate was selected from this smoke result.
