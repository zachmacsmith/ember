# Independent review of the 039 draft protocol

2026-09-08. Read-only review; no solver, benchmark, prefix call, remote action,
or production edit. The intended comparison is coherent, but this is **not
launch clearance**. It compares adding connected-center refinement against
the same pipeline with star refinement off, not against the singleton-center
treatment or MM.

Initial reviewed draft SHA256:
`1377f5487571d4dfaa52e9a56222b2ac2cad593842be185d780957d5414e764a`.
Root resolved the ordering, first-zero, output-uniqueness and original-file
provenance wording during this review. Final reviewed draft SHA256:
`3ea4c6b2a71e3d66d5b140c56f2b811f17b88eaf845ddecb9735b358c731b69c`.
Integration-plan SHA256:
`00cc9c7eadb708a8e92e900b0456291df9c58b7b7dd3490a4482f8039b39eb51`.
Read source identities: pilot `0d472453daa309e11630519f4813bc592c41ddbfc93725beaf5312417d118b4b`,
native `4fd880391e9c5bf2f3ed4e6f238ce987070108a7fc5eb36cac6aa95d69b7cbc9`,
contact `a79c78909a979726c7af93ca8a0a12a6c1228c795562be3d3cb029084797269e`,
cluster `f7f6f5f7a1e33d0ad58eb6abcf1e16e13101ed52327c82e8cbb6b1dae623f1ac`.
These identities describe the reviewed pre-integration state, not a future freeze.

## Configuration and accounting

The existing control configuration resolves to search construction, spectral
initialization, 1,000 placement evaluations, four refinement passes, beam 1,
512 total ordinary groups of sizes 1–4, 16 boundary sites, round-robin scheduling,
and `qubits_contacts`. Native defaults supply 500,000 refinement work units,
greedy trees, legacy singleton policy and star policy off. Contact defaults
supply 50,000 work units per visit, three alternatives, halo 2, region cap 512
and two reconstruction orders. The treatment should differ in its resolved
configuration only by `polish_star_policy='connected'`, under the predeclared
method `native-search-joint1-contacts-spectral-connected-star`.

At review time neither native nor contact accepts `connected`, and pilot has
no corresponding method. This is an acknowledged integration requirement, not
an executable comparison yet. The revised draft correctly says **at most four**
successors: the first complete zero-deficit successor proceeds immediately to
certification.

The 500,000 units bound refinement, not construction or all pipeline overhead.
Each ordinary visit receives `min(50,000, remaining global work)`. Connected
selection, lazy setup, queries and maintenance use that visit's live remainder
and collectively at most 25,000 units across the entire refinement call. There
is no extra query ceiling and no extra visit. A query can consume the remaining
auxiliary allowance. Five percent of operation units is not five percent of
wall time or equal coverage relative to the earlier singleton-center policy.

Integration must add actual `member_growth` and signed R only on scheduler
commit, including the negative R gain demonstrated by the fixed Z12 witness.
The certified-proposal counters may include a proposal rejected by the final
deadline; committed totals must exclude it. Construct exactly one selected
search class, require legacy singleton policy, and suppress attempts after any
ordinary acceptance, including equal-Q contact improvement. Mark the first
vertex considered once per pass before selection. A selected block can exceed
four vertices while consuming one ordinary visit.

Advance the live visit once by ordinary reconstruction's returned work.
Proposal and refresh already charge it; do not add their returned counts again.
Add the completed visit once to the global total. Refresh after publication
must retain the valid committed map if maintenance disables the cache. Preserve
the off path and historical matching diagnostics unless explicitly versioned;
label the new policy/operator. The frozen 037 audit's singleton-degree and
2,048-unit assumptions must not be applied to connected traces.

## Ordering, isolation and provenance

The current pilot retains `names` order and shuffles each input/seed's method
list with `random.Random(f'{name}:{seed}').shuffle(order)`. Pairs stay adjacent.
The revised draft supplies the input shuffle externally: shuffle the sorted
34 graph keys with seed `ember-codex-039-input-order`, then pass that exact list
through `--graphs`. I independently reproduced the saved order and verified
the exact 037 input set, solver seed zero and both declared method identifiers.
The order artifact SHA256 is
`8be5feff3102f38801ab32abf4efc17c9967aa22cc11b63e3969b955d01151fc`.
Its referenced manifest SHA256 `09bd7718cec3456ef5861c79f86065a582694902692c068b47240a7996f3aa3c`
matches `038-initial-prefix-certificates/frozen/manifest.json`. Verify both
ordering levels against the eventual 68 task identities before any call.
Graph identity used for evaluator ordering is not runtime family dispatch.

Fresh processes, fresh per-task Numba cache directories, and explicit one-thread
OpenMP/OpenBLAS/MKL/Numba settings are present. `PYTHONHASHSEED=0` is set. Solver
time excludes imports but includes first-call JIT compilation; process wall
includes startup, imports and final validation. These are not claims of cold
OS caches or exclusive physical CPU access. The solver deadline is 60 seconds;
the current worker alarm and controller wait are 90 seconds. The additional
30 seconds does not qualify late embeddings as timely success. The detached
outer supervisor allowance is 6,420 seconds for 68 calls.

Inherited advisory locks, durable claims and finalized-result skipping prevent
normal controller retries. `write_json` itself uses `os.replace`, so “write-once”
is a controller execution policy, not a non-overwriting filesystem primitive.
Require a fresh run, no prior claims/results, and preserve every observed
interruption. The revised draft now describes that mechanism accurately.

The saved 037 selection confirms 34 unique inputs, 35 family memberships, one
linked duplicate structure and absent original Sudoku. Its target digest is
`38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`.
The loader verifies sanitized normalized records and keeps family metadata out
of solver graphs. It copies those records and both selection ledgers, but not
the original raw graph or label-map files themselves. The revised draft now
requires a separate evaluator-only freeze of the audited 038 original records
and label maps, matched exactly to the eventual 039 task records. This required
archive and its equivalence checks remain part of preflight, not something the
unchanged pilot automatically supplies. Preserve every selected membership and exact normalized edge set;
no supplement, eligibility filter, per-family policy, or best-of output enters
this comparison.

## Remaining launch gates and inference limits

1. Root must accept the independent frozen-core review and complete scheduler,
   native and pilot integration checks on the final bytes. Independent core
   review has now reported passing matching/original-graph/prefix checks; that
   does not replace the integration gate. Include actual member growth, negative
   R, final-deadline rejection, cache-refresh failure, factory exclusivity,
   shared accounting, unchanged off behavior and the small native correctness
   smoke required by the integration plan.
2. Verify the now-resolved ordering and evaluator-only provenance requirements;
   freeze the exact method,
   effective defaults, protocol, integrated Git/source identities, all inputs,
   task order and environment records. Independent preflight must verify paired
   configuration equality except the one policy, all 34 input hashes and
   memberships, original target identity, dependency exclusion, hyde03 paths,
   fresh task caches, no existing attempts and an available persistent supervisor.
3. Root alone launches the frozen run. Retrieve only after quiescence and verify
   all transfer/result hashes and process statuses. Preserve partial/late output
   diagnostically, never as primary successful ACL observations.

Report all inputs and common-success denominators explicitly. Arithmetic mean
per-input ACL weights structures equally; pooled total Q weights larger sources
more and can rank changes differently. Report both without duplicating the
linked structure. Only a valid embedding attaining a proved Q lower bound is
an optimum certificate; passing degree/capacity conditions alone is insufficient.

Scalar Q/R trajectories permit arithmetic reconciliation, not independent
validation of unsaved intermediate chains. Final R can be recounted from actual
couplers; an initial R inferred from final R minus logged gains is not an
independent intermediate measurement. One seed provides no across-seed ACL
variance. This development-only off-versus-connected comparison cannot establish
superiority over MM, superiority over the singleton-center mode, the isolated
benefit of compression, or unseen-family generalization. No portfolio selection
is present in the prescribed algorithm or reporting plan.
