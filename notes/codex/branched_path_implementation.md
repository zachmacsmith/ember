# Retained-branch path implementation

The isolated `branched_path_reconstruction.py` differs from frozen pure-path
source only in branch requirements, their allocation, and identity/diagnostics.
It keeps every selected owner's off-route component and requires the new route
segment to touch each component and every outside neighbor not already reached
by that residue. Components and domains stay fixed for one path and are rebuilt
for the next. The unshortened witness must remain feasible; failure raises a
correctness error. A complete original-graph certificate still precedes every
strict-Q admission. The eight seeds, 128-owner, 512-site, 32-attempt and 1M-work
bounds, source order, BFS witness, chord ranking and strict acceptance remain.

New component visits, domain scans, owner-map setup, copied sites, and
requirement tests use the same meter and absolute stage deadline. The
`branch_requirements` phase separates this extra work. Failed questions and
certificates remain counted. Counters describe declared reads/operations, not
all Python instructions; sorting, diagnostics and interpreter overhead remain
in measured wall time. The retained branches can forbid all useful shortcuts
and can preserve unnecessary qubits; no local or global optimum is claimed.

`branched_path_construction.py:branched_path_embed(source,target,*,seed=0,
timeout=60.,deadline=None)` calls fixed A053 exactly once. Failed/late A053
outputs cannot enter the stage. Complete output enters a single path stage
with `min(original_D, stage_start + min(1s, .2 * elapsed_before_stage))`.
A later local stop preserves only the already certified entry or earlier
admitted map. The wrapper preserves that local stop verbatim and performs one
final original-graph validation under the original deadline. Its validation
reads/wall and final bookkeeping are separate from the local work cap; there
is no renewed path search. A final late return is uncredited. Operator errors
surface as pipeline failures, preserving diagnostic/partial evidence.

Imports are eager before the pilot solver clock; cold imports and JIT remain
in whole-process time. The candidate imports A053 and the unchanged validator,
never MM or a second constructor. The two A057 failed constructions remain
outside this complete-output stage's reach. Root owns the descriptor-only
`native-branched-path` registry entry with `{}` configuration and transport.

Eight focused checks cover Q7→6 branch transfer, detached-residue rejection,
multiple components/unshortened feasibility, no-residue equivalence to the
frozen pure path, branch-setup work rollback, interrupted/late certificate
rollback, one-base/one-stage wrapper behavior, retained earlier gain after a
local stop, failed/late base preservation, final-deadline rejection and actual
import isolation. Attempt001 passed seven checks; its import-only check errored
because the test wrongly banned `dwave_networkx`, used by ordinary Ember
package initialization. Candidate source did not change. The preserved test
revision now extracts the audited pilot `NoExternalEmbedder`, checks native
environment absence of `minorminer`, `_minorminer` and `busclique`, and permits
the existing graph dependency. Only that affected check was repeated in
attempt002: PASS, no prohibited attempts. Both runs and the exact test-only
diff are retained. No saved-final, corpus, MM or constructor calls occurred.

The next evidence is the predeclared six-input complete-constructor comparison;
these targeted certificates do not promote the method or the failed pure-path
operator. Source/check identities and all attempted checks are bound in
`results/codex/branched-path/manifest.json`.
