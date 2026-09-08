# Experiment 029: Sudoku supplement comparison protocol

Design recorded before runner edits, 2026-09-08 UTC. This task adds input support
and integrity tests only. It does not initialize a real run, transfer inputs,
launch embeddings, or change the algorithms.

The future comparison contains exactly the two frozen development records from
[027](027_sudoku_development_supplement.md): ID 1000002 (box order 2, 16 vertices)
and ID 1000003 (box order 3, 81 vertices). They remain separate from the inherited
017 selection and from original oversized Sudoku IDs 37900/37901. Orders 4 and
5 stay reserved and ungenerated. Necessary count bounds do not prove embeddability.

## Predeclared future comparison

Use ideal Zephyr Z12, seed 0, and a 60-second solver deadline for every call.
Both inputs receive all three fixed methods, for **six trials**:

1. `mm`, the isolated comparator.
2. `native-search-joint1-contacts`, the fixed random-initialized search with
   contact-redundancy refinement.
3. `native-search-joint1-contacts-spectral`, the same fixed method with the
   source-only spectral initializer.

Candidate settings are the existing named configurations: construction `search`,
1000 asks, four refinement passes, beam width one, 512 groups, group sizes
1/2/3/4, 16 boundary sites, round-robin group order, and objective
`qubits_contacts`. The spectral arm adds only `initialization="spectral"`;
all other algorithm defaults must be frozen and recorded with the eventual
source snapshot. MM receives no candidate embedding and candidates receive no MM
embedding. Each result remains a separate observation; no method is selected per
source, no policy changes by graph family, and both source outcomes are retained.

Report source-specific success/failure, validated ACL, solver time, and process
wall time. A single seed gives no across-run sample ACL variance. Two fixed
Sudoku graphs provide development evidence, not a stochastic puzzle population
or a family-wide superiority result. All initialization and repair time belongs
to the candidate's original deadline. Late/invalid results receive no successful
quality credit. Do not drop either input because of its outcome.

## Integration design and self-critique

Add `--input-supplement DIRECTORY` to pilot initialization, mutually exclusive
with `--corpus-selection`. The existing built-in graph and corpus-selection
paths retain their behavior. Supplement runs must keep every declared source;
`--graphs` cannot select only one Sudoku order.

Load the supplement using its reviewed loader; only its sanitized `record`
objects become solver graphs. Copy all eight original bundle files byte-for-byte
under the run's `input_supplement/`, and freeze the loader with runner source.
The run manifest binds the supplement identity, every bundle file, graph IDs and
source hashes, and the complete source/method/seed matrix. Tasks bind the same
supplement identity without adding source-family parameters to solver config.

The controller and analyzer must revalidate the frozen copy without consulting
the mutable original directory. Cluster transport includes every bundle file,
so existing transport and retrieval hashes also protect sidecars. Analysis must
retain validated provenance alongside its outcome summary.

Pre-implementation critique:

1. Copying only graph JSON would lose the correction's scientific identity.
   Tests must prove that the complete bundle and generator/protocol snapshots
   survive transport, and that missing sidecars fail before worker launch.
2. A manifest's surviving task list could conceal missing planned trials.
   Bind and verify the entire graph-by-method-by-seed matrix, including duplicate
   task rejection and both Sudoku sources, independently of available results.
3. The loader is executable source. Freeze and verify its bytes before using it
   for transferred-run validation; never import it from a mutable external
   supplement path during controller or analyzer execution.
4. Provenance must stay outside solver data. Test that graph roundtrips have
   empty graph/node/edge attributes and that configurations contain only the
   declared algorithm settings.
5. Existing 017 and built-in callers may lack the new argument. Use an optional
   path with no change to old behavior and run their existing focused regressions.

## Implemented path and verification

The new path is implemented in
[pilot.py](../../../scripts/codex/pilot.py),
[cluster.py](../../../scripts/codex/cluster.py), and
[analyze_pilot.py](../../../scripts/codex/analyze_pilot.py).
Existing built-in and corpus inputs do not import or freeze the optional
supplement loader. The new argument is optional for old programmatic callers,
and CLI/parser checks reject simultaneous corpus and supplement inputs.

For a supplement run, the manifest's `input_supplement` block records the original
bundle identity, hashes of all eight shipped files, the two graph identities,
and a content hash of the complete comparison plan. Every task additionally
binds `input_supplement_id`, `input_supplement_plan_id`, and
`supplement_graph_id`; these are evaluator fields, outside candidate `config`
and graph data. Worker results preserve them so controller finalization and
analysis can verify the original identity.

`check_supplement_provenance(run, manifest)` verifies the copied bundle and its
loader source, recomputes input identities and Sudoku semantics, checks the plain
solver graph copies, and requires exactly one task for every declared
source/method/seed combination. It rejects a missing source, missing method trial,
duplicate task, altered configuration or timeout, or mismatched plan binding.
Even shrinking the declared method list and recomputing its plan hash invalidates
the unchanged task bindings. These checks supplement the existing source,
target, task, result, and transport identities; they do not replace them.

The loader executes from `run/source/scripts/codex/sudoku_supplement.py` after
its bytes are verified against the source snapshot. Its frozen bundle is
`run/input_supplement/`. Neither controller nor analyzer consults the original
027 directory. The loader is compiled directly without writing bytecode into
the immutable bundle. The entire bundle joins the cluster transport file map,
so the existing remote verifier and retrieval hashes cover it. No new remote
operation or deployment mechanism was added.

Analysis retains evaluator provenance in `analysis/input_provenance.json` and
under `input_supplement` in `analysis/summary.json`. The original raw graph,
sidecar, generator, and protocol bytes remain available in the retrieved run.
Missing terminal results still make `checked_run` fail as incomplete. Failed
observations remain failures, with no fabricated ACL or zero elapsed time.

[test_codex_pilot_supplement.py](../../../tests/test_codex_pilot_supplement.py)
adds **36 focused tests**. The combined suite passes **103 tests**:

```sh
.venv/bin/python -m pytest -q \
  tests/test_codex_pilot_supplement.py \
  tests/test_codex_sudoku_supplement.py \
  tests/test_codex_pilot_corpus.py \
  tests/test_codex_cluster.py \
  tests/test_codex_pilot_analysis.py
```

The final invocation reported 2.20 seconds and only the existing
`dwave-networkx` deprecation warning. Tests initialize temporary fixtures using
a tiny inert repository and a two-vertex dummy target; they do not load an
embedding implementation. Synthetic finalized failures exercise analysis and
provenance retention. One mocked dependency-guard failure checks worker identity
propagation before any solver import. Transfer tests call the local bundle
builder and only the remote helper's verifier definitions; they do not invoke
SSH, stage a real run, or launch a controller remotely.

Coverage includes byte-for-byte transfer of all bundle files, loading after the
original directory has been removed, immutable-loader hash checking before code
execution, corrupt/missing sidecars, solver metadata leakage, complete trial
matrix checks, missing terminal results, result provenance loss, old built-in
initialization without the new argument, and existing corpus/cluster/analyzer
regressions. `git diff --check` passes for the assigned files.

Review-time source hashes, before any later launch preparation:

| File | SHA-256 |
| --- | --- |
| `pilot.py` | `ca2ac1ed9f21113a7ff217a7a36490f1ba8403ff4bf50cc610894ff5aa1fc0fe` |
| `cluster.py` | `33278be2b4a41db2c277d92a9e8eedb55788dfdbfaef2a1b7a4573e5eb85e9e0` |
| `analyze_pilot.py` | `dfd503274a509eb04d59657b46435f91f8c7a4da66903b7c3f7a356e76bb76ad` |
| Supplement integration tests | `1f94abe02c214787b238910dadd8bcc454536bb4ebddd8ed2aeb8984d0cbc39b` |

A real run directory, algorithm source snapshot, cluster host, transfer identity,
and launch time are intentionally absent until the parent reviews this support
and performs the later initialization. No actual experiment 029 has been staged
or launched in this task. Algorithm modules and the original 017/027 records
were not edited.
