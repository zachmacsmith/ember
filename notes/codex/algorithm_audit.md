# Audit of the existing embedding algorithms

Date: 2026-09-07. Branch: `codex`. Audited base commit:
`810745629ee5f711ee8b2d8157c648cf6b7ef548`.

Scope: source inspection of the current `factored` implementation, its immediate
dependencies, current handoff and paper-2 notes, selected tests, and other active
algorithm wrappers. This is a bounded audit, not a proof of the implementation
or a fresh benchmark. Historical performance numbers below remain unverified
measurements until rerun with the revised protocol. No embedding implementation
was changed. The small dynamic checks replaced MM routing with a logging stub;
they did not invoke MM.

The current algorithm worth preserving is the **two-order geometric embedder**
registered as `attraction`, implemented in
`packages/ember-qc/src/ember_qc/algorithms/factored/`. Its dense-graph results make
it a useful starting point. The shipped pipeline violates the user's MM-free
requirement, including in some runs with `tail="none"`. Its sparse-graph
performance and mathematical description both need substantial work.

## What actually executes

Paths below are relative to the repository root. Let `F` denote
`packages/ember-qc/src/ember_qc/algorithms/factored/`.

```text
registry: attraction
  F/__init__.py:26–42  Attraction.embed
    F/placement.py:111  attract_embed (tail defaults to "mm")
      target_layout -> TileGrid(courses=True)
      F/plane.py:299  arrange
        seeded permutations and mutable positions
        readout -> pack_axis -> F/field.py pack_lines
        units: order intervals at several scales + source neighborhoods
        align_reinsert: exact interleaving for fixed coordinate slots
        two alternating readouts, evaluate, adopt; retain best evaluated state
      F/field.py:786  wire_seeds_exact on stride-2 targets
        _convert_line per orientation and line; nearest-free singleton completion
      F/field.py:943  complete_seeds
        extend straight runs, then one-/two-qubit bridges
      if completion + structural validation succeeds: use resulting embedding
      otherwise: _mm_route(initial_chains=seed_chains)
      if empty: _mm_route(nearest-qubit singletons)
      F/polish.py:43  spur_prune
      if tail == "mm": _mm_route(warm=embedding), then ball_polish
      return result and diagnostics
```

The plane, line converter, completion, spur pruning, and ball/Steiner routines
contain no direct MM/busclique calls in the inspected source. Their existence
does not establish novelty: the geometric family explicitly generalizes a
known staircase construction, and the Steiner primitives closely follow known
minor-embedding construction methods.

## Findings requiring action before new benchmark claims

### 1. `tail="none"` is not an MM prohibition

`F/placement.py:90–108` imports `minorminer` inside `_mm_route` and calls
`minorminer.find_embedding`. The following call sites are independent of
`tail`:

- Lines 196–202: MM legalization when the native completion/validation gate
  does not pass.
- Lines 203–212: MM fallback from nearest unused qubits when no embedding was
  obtained.

Lines 119 and 222–237 make the MM warm-start and ball pass the default tail.
`F/__init__.py:12` calling MM an "optional polisher" is therefore incomplete.

**Reproduced:** K30 on Zephyr Z2 with `tail="none", max_asks=5, timeout=5`
attempts both MM fallbacks. Path8 on Chimera C3 does the same. K8 on Z3 with
`tail="none"` succeeds without either call. Thus some native runs are already
independent; the API is not fail-closed.

Required change: a genuinely separate MM-free entrypoint with no reachable MM
or busclique routing path. Unsupported targets or failed construction must
produce explicit failure or invoke only the new algorithm's own repair. Tests
should block MM, `_minorminer`, busclique, fork loading, and external embedding
binaries in the candidate process. Baseline MM runs must be separate processes.

### 2. Current diagnostics cannot certify MM independence

`mm_skipped` is assigned only for successful native legalization
(`F/placement.py:187–195`), before the MM tail. It stays true after a warm MM
call at line 226. `certified` at lines 265–274 checks converter/completion
counters, not whether MM executed and not the final returned embedding's
validation result.

**Reproduced:** K8 on Z3, `tail="mm"`, calls the warm MM stub while reporting
both `mm_skipped=True` and `certified=True`.

`legal_acl` is also not intrinsically an MM-free ACL: lines 215–217 compute it
after possible MM legalization and spur pruning. Give each result explicit
constructor identity, complete stage history, and independent final validation.
Prefer `mm_calls=0` from enforced isolation over inference from legacy flags.

### 3. The public structural validator has unstated preconditions

`packages/ember-qc/src/ember_qc/embedding_backend.py:505–532` verifies source
coverage, uniqueness of qubits, connectivity, and source-edge coverage. It does
not verify that every qubit belongs to the target or that the embedding has
exactly the source's keys. Singleton connectivity accepts an unknown qubit.

**Reproduced:** with source `nx.empty_graph(1)` and target `nx.path_graph(3)`,
both `{0: [999]}` and `{0: [0], 7: [2]}` return `True`.

This needs nuance: `validation.py:90–94` explicitly says that layer 1 requires
layer 2 to validate membership and types first. The bug is using the direct
backend helper as a complete public predicate without those checks, not proof
that the normal production runner accepts all such outputs. The handoff board
does not use either validation layer: `docs/paper2/data/rewrite_board.py:89–100`
accepts any nonempty mapping and divides by its number of keys.

Fix the direct predicate or its documented contract; always validate the exact
final mapping independently before calculating ACL over `|V(source)|`. No
evidence in this audit shows that the retained baseline embeddings actually
contained foreign qubits or extra keys; the hole makes that question harder to
answer because the board does not save embeddings.

### 4. The stated objective is not exact physical qubit count

`F/field.py:370–392` computes the sum of horizontal/vertical coordinate spans
plus `stride` for each arm having at least one assigned contact. The hardware
converter chooses parity and physical wires afterwards. Completion can add
qubits, and spur pruning can remove qubits. The packer books every point arm
(`F/plane.py:81–95`, `F/field.py:863–880`) while the objective does not charge an
inactive arm. An isolated source vertex has zero objective contribution but
must use at least one qubit.

**Reproduced:** K8 on Z3 has `stair=28`, `stride=2`, and 12 final qubits
(ACL 1.5). Even interpreting the span objective in qubit units as `28/2=14`
does not give the final physical count. Calling this objective "the total
derived chain length" (`F/plane.py:116–119`) or "chain length itself, not a
simulated proxy" (`F/field.py:14–17`) is too strong.

The useful exactness claim is narrower: interleaving and monotone line
assignment solve specified surrogate subproblems exactly under their stated
constraints. They do not globally minimize ACL or even exactly evaluate the
hardware ACL of every proposed order. Quantify surrogate error by graph family
and stage before choosing which objective to improve.

### 5. The search is not guaranteed monotone in its reported objective

`align_reinsert` sees fixed coordinate slots and a fixed other-axis picture
(`F/field.py:1515–1575`). After receiving an order, the caller reassigns both
axes (`F/plane.py:392–398`). It then explicitly accepts an evaluated worse
state and increments `adopt_worse` (`409–417`). Best-state retention avoids
returning a later inferior evaluated state, but does not make the search
trajectory monotone or supply a general convergence theorem.

Some comments still say only one axis is repacked (`F/plane.py:13–14`,
`305–308`). Actual positions also remain mutable state consumed by future
readouts and proposals. A pure mapping from two orders to a unique placement
would require a canonical readout or proof that the carried positions do not
matter; neither is established by these comments.

A zero-change pass is a stopping criterion relative to the scheduled move
family and current fixed-coordinate subproblem. It is not a certificate of
local optimality over arbitrary minor embeddings, nor of global independence
from initialization. Finite work budgets provide practical termination; the
unbudgeted accept-worse trajectory needs a separate cycle/termination analysis.

### 6. "Exact conversion" and "certificate" need restricted assumptions

The `_convert_line` DP assigns parity classes, then greedily assigns actual
lanes (`F/field.py:689–783`). Dead-qubit availability is checked during greedy
seating, after the class DP, and is not represented in the class-DP state.
Thus the method is not a joint exact parity-and-lane optimization on arbitrary
defective targets. `_lane_ok` checks present positions and gaps, but does not
require the first and last present positions to equal the requested endpoints
(`730–740`); a required hull can be shortened at a missing endpoint without
incrementing a converter miss at that point.

Completion uses coordinate arithmetic to extend crossings
(`F/field.py:1019–1030`) and may leave deficits. The `stride>1` gate
(`F/placement.py:154–159`) identifies course-resolved Zephyr geometry; it does
not verify that all expected physical couplers actually remain present.
Aggregate line capacity is not a proof of physical routability with damaged
wires or missing couplers. The full graph predicate must remain authoritative.

These are static limitations/risk points, not a demonstrated invalid pristine
Zephyr output. Existing `TestCertificate.test_certificate_sound`
(`tests/algorithms/test_field.py:1214–1230`) checks only three graphs on an
ideal Z3 target and validates the final pipeline output. Since the pipeline
can legalize with MM, that test does not establish converter soundness or
MM independence on its own.

### 7. The current comparison is neither across Ember nor time matched

The frozen board uses ten named instances, one target Z12, and only 3 or 10
random seeds (`docs/paper2/data/rewrite_board.py:34–49`). The `new` arm gets
up to 1800 seconds plus a per-instance evaluation budget (lines 82–84); MM
gets 60 seconds (75–78). The frozen README reports high server load. This may
support an explicitly quality-first comparison at reported effort, but not a
speed claim or equal-budget superiority.

Reported engine-only mean ACL versus MM from
`docs/handoff/baseline/RESULTS.md:44–64`:

| Instance | Existing native arm | MM | Interpretation before replication |
|---|---:|---:|---|
| K100 | 7.26 | 10.47 | Promising dense result |
| K140 | 9.77 | 20.29 | MM only 2/3 successful; compare success as well |
| Spin glass n163 | 10.85 | 20.56 | Promising dense result |
| Turan n162 | 6.00 | 11.30 | Promising biclique result |
| ER100 degree 10 | 4.60 | 4.82 | Small promising difference |
| Regular n316 | 4.75 | 3.59 | Clear loss |
| Small-world n486 | 4.40 | 3.14 | Clear loss |
| Grid n200 | 1.59 | 1.08 | Clear loss |
| Honeycomb n200 | 1.89 | 1.16 | Clear loss |
| King n196 | 2.56 | 1.76 | Clear loss |

The handoff's sparse "tie" language compares the rewrite against the older
polished algorithm, not generally against MM. The variance table reports
ranges over five draws, not variance estimates or uncertainty intervals.
Tolerances such as `max(0.3, 5%)` are engineering acceptance thresholds, not
evidence of statistical equality.

The summary silently pools every matching historical CSV
(`rewrite_board.py:108–140`); duplicates and mismatched revisions need explicit
run identifiers. Conditional mean ACL excludes failed runs. A publication
must separately report success, conditional quality, and a joint outcome
measure or prespecified treatment of failures.

## Other algorithms and dependency boundaries

| Component | Audit result | Evidence |
|---|---|---|
| `minorminer_forked` / `mmfork-*` | Modified MM, not an eligible candidate; can also retry stock-equivalent behavior | `algorithms/minorminer_forked.py:65–87, 125–145` |
| PSSA wrapper | Calls busclique to generate its guiding pattern; prohibited as a candidate in this project | `algorithms/pssa.py:90–105` |
| Current CHARME registry entry | Calls inference driver/ATOM binary; narrow checkpoint constraints (Chimera C16, 120 source vertices); not the current Zephyr candidate | `algorithms/charme/__init__.py:22–24, 81–120`; `env_infer.py:290–294` |
| CHARME reference implementation | Contains MM fallbacks; distinguish this file from the registered implementation | `algorithms/charme/_reference_charme_embed.py:237–243, 338–339` |
| CHARME training code | Uses MM-generated examples/results; must disclose training provenance for any learned method | `archived/algorithms/charme/charme/utils.py:3, 198`; `algorithms/charme_training/scripts/01_generate_training_data.py` |
| ATOM and OCT wrappers | External subprocess algorithms; no MM call found in inspected Python entrypoints; their binary implementation/provenance needs separate review before reuse | `algorithms/atom.py:63–69`; `algorithms/oct.py:113–116, 324–326` |
| `factored/trees.py` | Independent Python routing code, but root selection and shortest-path assembly are explicitly close to known CMR/MM constructions | `F/trees.py:85–137, 146–150` |

Here `algorithms/` in the last table means
`packages/ember-qc/src/ember_qc/algorithms/`, except explicitly archived paths.

The current `field.py:220–227` explicitly credits busclique's staircase for its
geometric construction. Reimplementing a known template independently satisfies
the no-call restriction but is not by itself a novel publication contribution.
Likewise, standard shortest-path/Steiner subroutines are reasonable components
if the new contribution is genuinely in the integrated algorithm, the analysis,
or the move family and is distinguished from previous work.

## Recommended next direction: one integrated branch-set search

Preserve the useful Zephyr geometry and exact interleaving/line-packing
subroutines, but treat them as construction and proposal components of one
algorithm whose authoritative state is an actual partial or valid assignment
of target qubits to source vertices. Use an explicit objective based on
feasibility and physical qubit count. This is consistent with the user's
quality-first, strict single-algorithm preference; it is not a selector among
independently implemented embedders.

The most justified experimental hypothesis is **joint neighborhood replacement
with geometric guidance and unrestricted local branch sets**:

1. Build a candidate assignment using the plane mechanism with all MM paths
   removed. Retain its qubit assignment and unsatisfied obligations, if any.
2. Select a small connected group of source vertices using actual conflicting
   qubits, long-chain boundaries, and unsatisfied source edges. Expand the
   target region only when the local subproblem is infeasible.
3. Jointly solve for connected disjoint branch sets inside the region with
   fixed external obligations. Allow Zephyr external and odd couplers, straight
   runs, bends, and small branching structures. This permits sparse chains that
   the one-horizontal-plus-one-vertical representation cannot express cheaply.
4. Accept valid count-improving replacements or use a prespecified controlled
   escape mechanism while retaining the best independently valid embedding.
   Use the same state, obligations, and physical objective during construction,
   repair, and improvement.

The existing ball pass is an experimental starting point, not evidence that
this hypothesis succeeds. It already selects groups but rebuilds primarily via
bar constructions and a sequential Steiner heuristic
(`F/ball.py:709–730`), so **joint** optimization against real physical
constraints is a substantive difference to test. A small exact region solver
can also serve as an oracle for move quality even if too slow for production.

**One self-critique before implementation:** local exact minor embedding is
combinatorially difficult; sparse small-world shortcuts may require changes
spanning much of the chip, so a bounded region may be systematically too small.
Allowing larger regions may be prohibitively slow and geometric initialization
may still determine the basin. Joint replacement and large-neighborhood search
are established general ideas, so the mere combination is not yet a novelty
claim. The first experiment should compare the present independent ball
rebuild against joint physical repair on identical saved MM-free inputs,
reporting feasibility, actual qubit reductions, region size, runtime, and
whether the known dense quality survives. If joint repair cannot improve
these same sparse inputs at generous budgets, that is evidence against this
specific neighborhood/region choice, not a universal refutation of joint
search. Do not broaden an adverse result into a ban on all penalties,
initializations, or graph-structural moves.

## Reproduction of the bounded checks

Observed local versions: Python 3.10.19, NetworkX 3.4.2,
dwave-networkx 0.8.19, minorminer 0.2.22. The environment version is reported
for reproducibility; minorminer was not used to generate any candidate output
in these checks. A first JIT compilation took about two seconds and was inside
the five-second budget; the demonstrations establish call reachability, not
performance.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import warnings
warnings.filterwarnings('ignore')
import networkx as nx, dwave_networkx as dnx
import ember_qc.algorithms.factored.placement as p
from ember_qc.embedding_backend import is_valid_embedding

s = nx.empty_graph(1)
t = nx.path_graph(3)
for e in ({0: [999]}, {0: [0], 7: [2]}):
    print('validator', repr(e), is_valid_embedding(e, s, t))

calls = []
def forbid(*args, **kwargs):
    calls.append({'seed': kwargs.get('seed'),
                  'warm': kwargs.get('warm') is not None})
    return {}
p._mm_route = forbid

cases = [
    ('zephyr_certified', nx.complete_graph(8), dnx.zephyr_graph(3), 'none'),
    ('chimera_none', nx.path_graph(8), dnx.chimera_graph(3), 'none'),
    ('zephyr_mm_tail', nx.complete_graph(8), dnx.zephyr_graph(3), 'mm'),
    ('zephyr_lowbudget', nx.complete_graph(30), dnx.zephyr_graph(2), 'none'),
]
for name, s, t, tail in cases:
    calls.clear()
    r = p.attract_embed(s, t, seed=0, tail=tail, max_asks=5, timeout=5)
    print(name, calls.copy(), len(r.get('embedding', {})), r.get('diag'))
PY
```

Observed routing calls:

```text
validator {0: [999]} True
validator {0: [0], 7: [2]} True
zephyr_certified: [] ; 8 chains ; legal_acl=1.5 ; stair=28 ; stride=2
chimera_none:     [{seed:0,warm:False}, {seed:99,warm:False}] ; 0 chains
zephyr_mm_tail:   [{seed:0,warm:True}] ; 8 chains ; certified=True ; mm_skipped=True
zephyr_lowbudget: [{seed:0,warm:False}, {seed:99,warm:False}] ; 0 chains
```

The exact returned diagnostics and static call graph support the findings
above. This audit did not re-run the ten-cell board, conduct a complete
literature novelty review, or verify every historical experiment.
