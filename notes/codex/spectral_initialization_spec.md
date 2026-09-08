# Bounded source-Laplacian initialization

Status: design and self-critique saved before implementation, 2026-09-07. This is a
source-only initialization experiment, not an embedding result. It does not change
the constructor, contact repair, or the currently selected algorithm.

## Motivation and scope

`plane.arrange` currently assigns two independent random ranks to source vertices.
The independent scheduler generator is then reset. The proposed change replaces
only those initial ranks with two orders from one low-energy source-Laplacian
plane. There is one solver and one resulting initialization, with no comparison
against other initializations. The subsequent constructor and repair are unchanged.

For an undirected simple source graph, the combinatorial Laplacian obeys
`x.T L x = sum_{uv in E} (x_u - x_v)^2`. Two low nonconstant modes minimize this
quadratic source-edge length subject to centering and orthogonality. This is a
conventional spectral layout relaxation, not a novel embedding algorithm or a
relaxation of the exact hardware chain objective. Sorting its coordinates may
reduce initial source-edge spans, but neither shorter physical chains nor a
better final local optimum follows from the relaxation.

Use `L / maximum_degree` on each nontrivial connected component. Scaling preserves
the eigenvectors, bounds the spectrum by two, and gives the fixed residual
tolerance a comparable scale. Use three nonconstant Ritz vectors: two for the
layout and one to expose a possibly unresolved eigenspace boundary. The third
vector is a numerical diagnostic, not a third embedding candidate.

## Precise proposed procedure

```text
spectral_orders(source_adjacency, seed=0, max_iterations=64,
                tolerance=1e-5, max_work=50_000_000, deadline=None):
    validate undirected, loop-free adjacency; canonicalize integer vertex IDs
    create ONE seeded random generator independent of the search scheduler
    find components; order by decreasing size, then least canonical vertex
    start empty output orders X and Y
    for each component C:
        check the shared deadline and work cap
        if C is an isolate: append its vertex to both orders; continue
        build sparse scaled L from source edges only
        draw seeded centered reference vectors and deterministic tie priorities
        if |C| <= 16:
            use bounded dense symmetric diagonalization of the same L
            discard the constant mode; retain at most three modes
            charge |C|^3 work units before the solve
        otherwise:
            center and orthonormalize three seeded starting vectors
            LOBPCG, smallest modes, constant-vector constraint,
            diagonal preconditioner, at most max_iterations iterations
            every L multiplication first charges nnz(L) * vector_columns
            every operator/preconditioner call checks the common deadline
        explicitly recompute and report returned Ritz residuals
        no retry with another solver, factorization, seed, or initialization
        on finite output above tolerance: report approximate, retain it
        on budget/deadline/numerical failure: return no orders and diagnosis
        orient the first two modes toward the seeded centered references
            by a two-dimensional orthogonal Procrustes rotation
        if only one nonconstant mode exists: use it on both axes
        sort each coordinate using fixed numerical tie bins, then seeded priority
        append each local order to X and Y in the common component-block order
    verify X and Y each contain every source vertex exactly once
    return (X, Y), diagnostics
```

The tiny dense base case avoids SciPy's implicit small-problem fallback when the
number of vectors is large relative to the matrix size; it is the same eigenproblem
and has a fixed maximum dimension, not source-family dispatch. Components larger
than that threshold always use the same block method and parameters. Isolates
and two-vertex components require no invented nonconstant modes.

The diagonal preconditioner is the inverse positive diagonal of scaled L. It is
an inexpensive numerical operation, not a linear system solve or an IP subroutine.
Matrix storage and construction after canonicalization require `O(n+m)` work.
Canonicalizing IDs, components and adjacency also incurs sorting costs. With a
constant block size, each sparse operator application costs `O(n+m)`; orthogonal
operations cost `O(n)`, and the internal dense eigenproblems have bounded dimension.
All components share the work cap. The work count is a numerical-operation proxy;
it excludes Python validation, allocation, sorting, preconditioning, and BLAS
overhead. The deadline is cooperative, checked around operations, not a hard
preemptive wall-time guarantee. A final overrun must be reported honestly.

## Reproducibility and numerical limitations

Canonical input order and sorted adjacency remove dictionary/edge insertion-order
effects. Seeded starting vectors, reference orientation, and tie priorities make
the policy deterministic within a fixed numerical stack. This is not a claim of
isomorphism-invariant output, bitwise cross-platform determinism, or independence
from vertex relabeling: symmetric graphs admit many equally valid orders.

Procrustes orientation removes arbitrary sign and basis rotation of a fixed
two-dimensional returned subspace, provided the reference projection has full
rank. It may mix two distinct eigenvectors; the result spans the same low-mode
plane and preserves the sum of their quadratic energies. Report Ritz residuals
before that rotation. Flag a deficient reference projection and near ties between
the second and third Ritz values; report every residual. The `residual_tolerance`
status refers to the first two layout vectors. The third residual contributes to
the cutoff-uncertainty diagnosis, and that status does not assert its convergence.
A low residual
does not certify that the solver found the globally lowest eigenvalues. A
degeneracy extending past the selected subspace can change that subspace; the
orientation rule does not cure it. No full large eigenspace is computed to conceal
this ambiguity.

An iteration-limited finite result is an **approximate spectral initialization**.
It remains a well-defined pair of orders and is always used under the same policy;
it is not called a converged low-mode solution. Numerical, deadline, and work
failures return no orders. The API never substitutes random orders or a second
solver. If integrated, the caller must report failure explicitly rather than
silently switching to another constructor.

SciPy is present in the isolated development environment (1.15.3), but is not a
direct dependency of `ember-qc`. The optional module should import it lazily and
report unavailability; deployment needs an explicit dependency decision. The
[SciPy 1.15.3 LOBPCG documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.sparse.linalg.lobpcg.html)
documents block starts, orthogonality constraints, preconditioning, iteration
limits, and approximate returned eigenpairs. It also warns that convergence
depends on spectral separation and conditioning. The numerical method is from
[Knyazev, 2001](https://doi.org/10.1137/S1064827500366124).

## Self-critique before implementation

1. **The relaxation can be wrong for the hardware objective.** Sorting loses
   distances, the two orders are correlated, and near-neighbor source placement
   can concentrate lane demand. A lower source quadratic energy is diagnostic
   only. The falsifier is no cumulative ACL improvement, validity loss, or a
   runtime tradeoff beyond the agreed regime at fixed global budgets.
2. **Bounded iterations may not find global structure.** Long low-gap components
   can converge slowly even with diagonal preconditioning. Returning an honestly
   labeled approximation avoids an unbounded solve, but its useful content may
   amount to local smoothing. Record residuals, actual operation counts, and
   timings at 80, 480, and about 4,800 vertices before any embedding trial.
3. **Component blocks are a heuristic.** Contiguous blocks avoid interleaving
   unrelated components on both axes, but could waste available fabric capacity.
   This is one fixed rule with no per-family exceptions; it must face disconnected
   inputs in the same evaluation, and failures count.
4. **Seed anchoring is not canonicalization.** Near degeneracies and numerical
   ties can change permutations. Tests should demand exact repeatability on the
   installed stack and invariance to insertion order/metadata, and separately
   expose degenerate boundary diagnostics rather than assert impossible symmetry
   breaking guarantees.
5. **Additional work can erase local benefits.** Experiment 023 found zero wins,
   12 ties, and six losses for the stronger distance-tree proposal in cumulative
   search: 24 more qubits, 7.68M versus 4.14M expansions, and 13 versus two work-cap
   stops, despite useful isolated moves. That policy is not promoted. The spectral
   initializer must charge its time to the same end-to-end deadline and preserve
   the scheduler sequence. Report both equal-ask controls and equal-total-time
   cumulative outcomes; an improved first layout alone is insufficient evidence.

## Bounded tests and later integration contract

First test permutation coverage, component/isolate handling, exact repeated and
insertion-reordered inputs, metadata independence at the adjacency boundary,
residuals on small analytically checkable graphs, degenerate-space warnings,
iteration-limited reporting, and atomic absence of output under budget/deadline
failure. Then measure source-only preprocessing/solver time and residuals on
several sparse and dense structures at fixed parameters. No embedding runs are
authorized in this subtask.

Suggested API: `spectral_orders(src_adj, *, seed=0, max_iterations=64,
tolerance=1e-5, max_work=50_000_000, deadline=None) -> (orders_or_none, diagnostics)`.
`orders_or_none` is `(x_order, y_order)`, not arrays of per-vertex ranks.
`plane.arrange` must invert each order to ranks before building its positions.
The scheduler RNG is already reset independently; integration must preserve that
sequence, `max_asks`, and the single original absolute deadline. Tests of source
structure only support feasibility of this initialization, not embedding quality,
novelty, or superiority to MinorMiner.

## Implemented source-only feasibility check

Implementation is now present in
[`spectral_order.py`](../../packages/ember-qc/src/ember_qc/algorithms/factored/spectral_order.py).
The public API matches the contract above. Finite unconverged output returns
`status="approximate"`; `status="residual_tolerance"` means the first two returned
Ritz residuals meet the tolerance, not that the lowest modes are certified. The
third residual and cutoff uncertainty remain separately visible. Numerical rank
errors and non-finite output return `numerical_failure`, with no retry. Deadline
and work stops discard the entire pair of orders, including any completed
component prefix. Empty and isolate-only inputs need no SciPy import or solver.

`tests/algorithms/test_spectral_order.py` has **19 passing tests** (0.67 seconds
reported by pytest). They cover analytic path eigenvalues, component blocks,
isolates and two-vertex sources, insertion order and metadata controls, repeat
reproducibility, fixed-subspace orientation, unresolved degeneracy, approximate
iteration-limited output, shared work caps, truthful late deadlines, malformed
inputs, and numerical failure without retry. These are initializer tests, not
embedding tests.

The following single source-only run used Python 3.10.19, NumPy 2.2.6, SciPy 1.15.3,
NetworkX 3.4.2 on macOS 26.6.2 arm64. All rows use the same seed and solver limits.
Graph construction and conversion to the input adjacency mapping occur outside
the timed function. Source validation, component discovery, sparse construction,
the solver, and final sorting occur inside. The first row includes cold SciPy
import; all later rows have the module cached. Timings are single local
observations, not performance estimates across machines or repeated runs.

| Source structure | Vertices | Edges | Wall (s) | Charged work | Largest of first two residuals | Status |
|---|---:|---:|---:|---:|---:|---|
| path | 80 | 79 | 0.20776 | 42,602 | 9.62e-6 | tolerance |
| regular degree 3 | 80 | 120 | 0.00596 | 34,560 | 7.63e-6 | tolerance |
| regular degree 8 | 80 | 320 | 0.01005 | 84,240 | 6.60e-6 | tolerance |
| rectangular grid | 80 | 142 | 0.00540 | 32,396 | 5.67e-6 | tolerance |
| complete | 80 | 3,160 | 0.00239 | 57,600 | 6.24e-16 | tolerance |
| path | 480 | 479 | 0.01768 | 293,352 | 1.71e-3 | approximate |
| regular degree 3 | 480 | 720 | 0.01714 | 378,240 | 1.33e-5 | approximate |
| regular degree 8 | 480 | 1,920 | 0.01816 | 790,560 | 1.55e-5 | approximate |
| rectangular grid | 480 | 916 | 0.01701 | 455,464 | 1.71e-5 | approximate |
| complete | 480 | 114,960 | 0.06347 | 2,073,600 | 1.14e-15 | tolerance |
| path | 4,800 | 4,799 | 0.07246 | 2,937,192 | 2.04e-3 | approximate |
| regular degree 3 | 4,800 | 7,200 | 0.07375 | 3,916,800 | 2.24e-3 | approximate |
| regular degree 8 | 4,800 | 19,200 | 0.09040 | 8,812,800 | 1.24e-3 | approximate |
| rectangular grid | 4,800 | 9,460 | 0.10426 | 4,838,880 | 3.95e-3 | approximate |

All 14 returned orders contain every source vertex exactly once. All four largest
cases use 204 operator columns and report an uncertain selected-subspace boundary.
Complete sources expose a tied boundary even when residuals are tiny, as they
should: their nonconstant eigenvalues are degenerate. The 4,800-vertex path's
smallest returned Ritz value is `2.03825e-4`, whereas its true smallest nonconstant
scaled eigenvalue is `1 - cos(pi/4800)`, about `2.142e-7`. The bounded solve does
**not** recover that global mode. Small cost and valid permutations support trying
the heuristic; they do not show that it captures the structure needed to close
the ACL gap. No source structure triggers a different code path except component
size for the fixed tiny numerical base case.

No embeddings were computed in this subtask. The next decisive experiment is one
globally fixed initialization inside the same constructor with unchanged
scheduler, search policy, and total deadline. Measure actual final validity and
ACL on the cumulative development panel, including the dense cases and every
regression. A first-layout or source-energy improvement is not a substitute.

Reproduce tests:

```sh
PYTHONPATH=packages/ember-qc/src .venv/bin/python -m pytest -q tests/algorithms/test_spectral_order.py
```

Reproduce the source-only diagnostic; output includes all returned eigenvalues,
residuals, exact work, version, and coverage checks. The symlink path preserves the
isolated environment, where MM is unavailable.

```sh
PYTHONPATH=packages/ember-qc/src .venv/codex-native/bin/python - <<'PY'
import json
import networkx as nx
from ember_qc.algorithms.factored.spectral_order import spectral_orders
for n in (80, 480, 4800):
    a, b = {80:(8,10),480:(20,24),4800:(60,80)}[n]
    cases = [('path', nx.path_graph(n)),
             ('regular3', nx.random_regular_graph(3,n,seed=41)),
             ('regular8', nx.random_regular_graph(8,n,seed=41)),
             ('grid', nx.convert_node_labels_to_integers(nx.grid_2d_graph(a,b)))]
    if n <= 480:
        cases.append(('complete',nx.complete_graph(n)))
    for name, graph in cases:
        orders, info = spectral_orders({v:list(graph[v]) for v in graph},seed=0)
        c = info['components'][0]
        print(json.dumps(dict(shape=name,n=n,edges=graph.number_of_edges(),
            status=info['status'],wall=info['wall'],work=info['work'],
            columns=info['operator_columns'],residuals=c.get('residuals'),
            values=c.get('eigenvalues'),cutoff_uncertain=c.get('cutoff_uncertain'),
            coverage=orders is not None and all(len(o)==n and set(o)==set(graph)
                                              for o in orders),
            scipy=info['scipy_version'])), flush=True)
PY
```

Module SHA256 at handoff:
`02dd5ad22567f3b0e0d1b5836e1f55b975377de3f275a28823a3e518e5425b56`.
Test SHA256:
`23333a86bc186a91fcc27a9ed2e63dbbebd5ce8761c4cb827ba94f7753c419e3`.
The final two small changes after the timing run only skip imports on isolate-only
inputs and convert a solver-raised rank/constraint error into explicit failure;
neither changes the successful connected-source computations in the table.
