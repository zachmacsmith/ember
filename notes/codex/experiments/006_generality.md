# Experiment 006: generality controls and construction gaps

Date: 2026-09-07. Scope: small source-transformation controls and mechanism
diagnostics for `native.py` and `contact_repair.py`. No algorithm was changed.
This is not a Z12 benchmark or an MM comparison. The Z2/Z3 targets are tiny
correctness/representation probes; the research evaluation remains focused on
ideal Z12.

Audited working-file SHA-256 values:

```text
native.py          e852cc3af151182492c445b9c743b2c544b950fd0c4aace5243027d3c01e8599
contact_repair.py  b8a73f42e401e4db37b31b521d110cd91270ae63fa5c5839b01f581bc6fffd93
```

Both files are under
`packages/ember-qc/src/ember_qc/algorithms/factored/`. The executable controls
are in `tests/algorithms/test_native_generality.py`.

## Findings

1. On the tested sources, relabeling source vertices while preserving their
   insertion order leaves the normalized algorithm path unchanged. Source
   family/name/graph-ID metadata, an irrelevant metadata embedding, and edge
   insertion order are also inert. These checks pass for both native
   construction configurations, with contact refinement enabled.
2. Reordering source **nodes** changes finite-budget quality, even with the
   same graph adjacency and seed. This is explained by the current mapping
   from node insertion order to internal indices. It does not establish
   family dispatch or overfitting, but it is a reproducibility and robustness
   dimension that must be controlled in experiments.
3. The native packed constructor can fail on sources with independently
   verified ACL-1 embeddings. The current contact routine cannot repair these
   failures because it accepts only valid full incumbents. Construction
   completion, rather than polishing alone, is a necessary research step.
4. Warm runtimes for these tiny cases are tens of milliseconds, while first
   JIT use costs substantially more. These measurements do not predict Z12
   scaling or establish runtime within any factor of MM.

## Source transformations and test result

Command, deliberately preserving the isolated interpreter's symlink path:

```sh
PYTHONPATH=packages/ember-qc/src .venv/codex-native/bin/python \
    tests/algorithms/test_native_generality.py
```

The executable test file needs no pytest installation and can also be
collected normally by pytest. Result: **six checks passed**, taking 1.054 s
in the isolated process, including initial JIT/cache loading in that process.
Additional diagnostic rows are emitted afterwards as JSON.

Environment:

- Python executable: `/Users/dabh/ember/.venv/codex-native/bin/python`.
- Python prefix: `/Users/dabh/ember/.venv/codex-native`.
- Python 3.10.19, NetworkX 3.4.2, dwave-networkx 0.8.19.
- `importlib.util.find_spec("minorminer")` returned `None`.
- No external `minorminer`, `_minorminer`, or `busclique` module was loaded.
  Package discovery does import Ember's **Python comparator wrappers**
  `ember_qc.algorithms.minorminer` and `minorminer_forked`; wrapper registration
  is distinct from invoking an external embedding library. These wrappers
  were not called. The test's JSON distinguishes the two categories.

The transformation source is a 12-cycle with chords `(0,6)`, `(1,5)`, `(3,9)`
and an isolated vertex 20. Target: Z3. Configuration: seed 4, 20 asks for the
search configuration, two packing passes for the packed configuration, one
contact pass capped at three groups, beam width four, 10 s safety timeout.

The checks cover:

- Mixed tuple/string/integer source renaming, restoring original keys before
  comparing exact returned embeddings.
- Reversed source-edge insertion and endpoint orientation with a fixed source
  node list.
- Contradictory source metadata such as `family="complete"`,
  `graph_type="king_graph"`, `name="K100"`, arbitrary graph IDs, and a bogus
  `embedding` metadata field. Source adjacency is unchanged, and the metadata
  is verified unmodified after execution.
- Source node/edge insertion and metadata changes for direct `contact_polish`
  on an independently constructed path embedding.
- Validity of three node-insertion variants on four additional small sources.
- Honest incomplete-construction reporting on independently feasible paths,
  without making today's failure a required future behavior.

Every successful result is checked by a separate straightforward NetworkX
oracle: exact source keys, target membership, unique qubits, connected chains,
disjointness, and all source-edge contacts.

These are finite controls, not a proof that every possible attribute or
renaming is inert. Source inspection provides complementary evidence:
`native.py:29–54` selects an explicitly configured ordering using adjacency,
degrees and random priorities; it does not inspect source family metadata.
`native.py:131–134` relabels source vertices through `list(source_graph)`.
`contact_repair.py:26–39` uses deterministic label ordering, and its group
selection uses chain lengths, source neighbors and occupied physical neighbors.
The direct contact API is consequently not claimed to be invariant under
every arbitrary source renaming; the native adapter normalizes labels first.

## Node insertion order and observed runtime

For these rows the constructor is always packed/random, seed 4, two packing
passes, one contact pass with at most three groups. No algorithm or
configuration was chosen separately for a graph family. The three variants
are the original node order, its reversal, and a shuffle from `Random(811)`.
Edges are otherwise identical. Source names below label the **diagnostic
report**, not metadata consumed by the algorithm.

| Source | Qubits: base / reverse / shuffle | Warm total ms: base / reverse / shuffle | Contact BFS expansions: base / reverse / shuffle |
|---|---|---|---|
| Cycle24 plus three chords | 28 / 27 / 32 | 17.0 / 18.6 / 22.6 | 1175 / 2030 / 3215 |
| Random regular32, degree3, generator seed7 | 60 / 61 / 62 | 21.8 / 25.8 / 21.8 | 1253 / 4144 / 1006 |
| ER30, p=0.16, generator seed9 | 74 / 71 / 75 | 24.3 / 23.8 / 22.4 | 1346 / 1387 / 1469 |
| Star40 | 43 / 43 / 42 | 23.1 / 23.2 / 19.0 | 699 / 770 / 0 |

All twelve outputs passed independent validation. The contact stage consumed
approximately 0.94–12.0 ms of the warm totals. In a separate first-call probe,
the initial packed invocation took 0.485 s, of which 0.472 s was reported in
layout; the following small search invocation took 0.023 s. JIT/cache setup
must be distinguished from warm steady-state work and still included when the
execution model pays it.

These are single observations on a developer machine with concurrent work,
not timing distributions under controlled load. No MM timing was measured.
The relatively large variation in BFS expansions also shows why a fixed
number of group attempts is not a fixed amount of computation. Conversely,
zero BFS expansions do not imply zero time: graph setup and group selection
still execute.

The node-order effect is expected from the present implementation: the same
numeric random seed assigns random priorities/permutations to different
vertices after reindexing. Reproducible experiments should preserve source
serialization, record its hash, and include independent relabel/node-order
draws in development robustness checks. Exact fixed-seed invariance is not
needed to invent a general heuristic; blindly sorting original labels would
not provide graph-isomorphism invariance either.

## Independently feasible construction failures

A deterministic DFS tree of each target contains a sufficiently long simple
physical path. Taking its first n vertices gives a directly verified
singleton-chain embedding of `nx.path_graph(n)`, so feasibility and ACL=1 do
not rely on MM or an unverified capacity estimate.

| Source / target | Verified witness ACL | Native packed result | Final layout misses | Converter misses | Missing source edges |
|---|---:|---|---:|---:|---:|
| Path40 / Z2 | 1 | `CONSTRUCTION_FAILED` | 16 | 32 | 7 |
| Path80 / Z3 | 1 | `CONSTRUCTION_FAILED` | 40 | 74 | 32 |

Configuration: shared random order, seed 4, two packing passes, no polishing,
10 s safety timeout. The failed attempts took approximately 0.045 and 0.029 s
in the recorded run, returning partial assignments of 92 and 188 qubits,
respectively. Earlier repetitions were faster; no timing conclusion follows.

For context, an additional diagnostic with edgeless sources of 40 on Z2 and
80/120/200 on Z3 succeeded despite many geometric packing/converter misses.
That observation does not prove the surrogate model is wrong in every case,
but it reinforces that its counters are not physical infeasibility proofs.

`native.py:167–170` returns immediately on incomplete native construction.
Contact search is called only after complete validity at lines 174–178.
`contact_repair.py` explicitly rejects invalid inputs. Thus increasing
`polish_passes` cannot address these particular construction failures.

The layout's reported `pen`/`stair` is calculated before its final bounded
projection (`native.py:70–81`), whereas `misses` is the final readout's count.
These diagnostics refer to different stages. They should not be treated as
a single synchronized physical state or an exact account of every dropped
claim.

## Prioritized general improvements, with critique before implementation

### 1. Extend the same joint operation to incomplete physical assignments

Introduce a precise partial-state normalization and validator. Keep only
connected disjoint realized chains, retain discarded/unplaced vertices as
pending obligations, and recompute all lost contacts. Let the existing bounded
group operation insert missing vertices and repair missing source edges using
one evolving state. Before full feasibility, rank by pending vertices/missing
contacts before physical qubit count; afterwards preserve the existing strict
valid qubit-reduction rule. Group selection should start from actual missing
contacts and blocking owners, never source-family names.

**Self-critique:** strict deficit descent can stall, and the available local
region may contain no completion. Controlled rollback or temporary deficit
increases require explicit bounds and a clearly separate fully valid
incumbent. Removing the valid-input precondition without a correct partial
invariant would silently create invalid embeddings. Beam/BFS completion is
also close to established routing heuristics; novelty remains unproved.

**Decisive test:** restore feasibility on independent deficit-bearing inputs
from multiple source structures, saving every changed contact and qubit.
Compare identical initial assignments and work limits. Success solely on
these two paths would be insufficient to promote the change.

### 2. Evaluate a fixed locality-aware ordering as a research revision

The cheap constructor's random shared order makes graph neighbors widely
separated before physical packing. The existing degree/BFS order options
provide inexpensive controls. Evaluate one fixed structural rule across the
same balanced development set and node-order draws, without choosing an
ordering per graph or selecting among completed embeddings at runtime.
Retain one constructor configuration for the chosen algorithm.

**Self-critique:** source locality alone can destroy favorable dense/bipartite
arrangements; the packed representation may remain too restricted even with
a good order. A change that fixes only the path examples could be precisely
the overfitting the user warned against. Promotion requires broad success
and quality evidence under the same globally fixed policy.

### 3. Make physical failure information drive bounded general updates

Record separate pre-/post-projection positions, packing misses, converter
misses, disconnected chains, absent vertices, and actual missing contacts.
Use that causal information to prioritize bounded order/contact updates in
the same construction state. Review whether inactive geometric arms consume
capacity unnecessarily, but derive any revised accounting against actual
chain connectivity/contact requirements before implementation.

**Self-critique:** improving a capacity surrogate can worsen physical
routability, and repeatedly invoking the full interleaving optimizer would
violate the intended runtime scale. The first implementation should be a
bounded, measurable update, with an independent physical validator and full
stage timing. These observations do not justify an ad hoc special path,
grid, clique, or family-specific constructor.

## Next decision

Use the broad Z12 development pilot to determine whether incomplete
construction or expensive valid-chain refinement is the dominant problem.
The small controls here justify a partial-state completion investigation and
clearer stage diagnostics. They do not establish a better default ordering,
an MM speed ratio, a publication result, or a reason to add family-specific
rules.
