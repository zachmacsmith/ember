# Joint path operator: isolated implementation and fixed gate

The accepted proposal and root's budget-stop clarification were saved before
source or outcomes. Original proposal bytes remain in
`results/codex/joint-path-gate/precode`. No registry, A053/native source or
constructor invocation changes are included.

`factored/joint_path_reconstruction.py` implements the prescribed eight seeds,
128-owner induced paths, one BFS witness, 512-site route bound, forward chords
and at most32 greedy route attempts per path. It uses only the standard library.
There is no exact optimizer, free-site search, alternate route search, or
partial-minor feasibility mode. Every committed proposal has strictly fewer
qubits, connected disjoint nonempty segments, unchanged outside chains, and all
original contacts checked by the existing authoritative structural function.

The structural function is supplied explicitly. The checks/gate compile the
unchanged `_is_valid_embedding` AST from `embedding_backend.py`; only postponed
annotations are enabled. No backend/constructor imports or validation logic
changes occur. Read-only mapping/sequence views meter its source edges, chain
sites, target edges and lookups. Input/setup, target normalization, copies,
path/chord generation, greedy assignment and certificates share one1M work
counter and absolute deadline. Sorting and Python administration are charged to
wall time, not represented as extra adjacency visits. The counts are specific
to this operator and are not compared to A053 routing scans.

Pre-copy interruption can return the untouched valid caller entry by alias,
with `input_validated=False` and unknown Q delta. Later stops retain the complete
private entry or last admitted improvement. Work, route and attempt bounds are
normal finite outcomes with explicit unvisited alternatives. Interrupted
certificates and actual late returns remain distinct. A final observed late
return is `late_output` even if the retained mapping is valid. Certified and
committed counts remain separate; no spare work unit is required after a
completed certificate, but timeliness is checked immediately before admission.

Eight tiny checks passed on their first execution in0.057s: side-contact owner
shift, unique-side-contact rejection, actual cycle contraction, omitted branch
rejection, zero/small-budget alias rollback, certificate interruption, retaining
an earlier gain at a later exact work stop, and normal route-limit output. A
ninth focused check passed separately in0.016s: completion of the certificate
followed by deadline crossing before publication does not admit the candidate.
Core source did not change between these checks. The independent saved-record
oracle verifies the supplied and returned tiny graphs; no prohibited embedding
library was loaded. All commands, identities and logs are retained under
`results/codex/joint-path-gate/checks`.

The sole six-call gate is frozen by `plan.json` and `execution_manifest.json`.
It uses the exact saved A053 finals for cycle1829, cubic33219, kagome32122,
grid1584, planted34404 and Petersen4083, in that order. Each gets one fresh
isolated process, one operator call, the predeclared
`min(1s,0.2*saved_A053_solver_wall)` allowance, 1M work, and a five-second process
watchdog. The unchanged040 supervision helper supplies TERM/KILL/reaping with
one-second grace. Cold process/input/code setup, immutable-entry comparison,
independent final validation, encoding and atomic result publication are
included in observed elapsed time. A separate receipt timestamps publication.
This conservative saved-data diagnostic includes file/codec work that an
in-memory integration would not repeat; its exact cost scope remains visible.

Every saved final is checked with the unchanged042 record oracle against the
exact original-normalized source/target bytes already bound to the audited053
original-label provenance. Baseline and returned Q, valid/timely status, setup,
operator, final-oracle, process and all-work costs are preserved. No dataset
constructor, MM call, evolving native snapshot or physical-route optimality
claim is involved. Advance requires all six timely valid outputs with complete
accounting, a cycle improvement and at least one other improvement. Normal
budget stops do not invalidate a timely valid output. Missing/late/error output
does. No automatic repeat or allowance change follows any result.

The two A057 failures remain outside the API's reach: one lacks a valid native
core output, and the wheel has an incomplete lift with pending requirements.
Passing a quality-only saved-final gate would not address either failure.
