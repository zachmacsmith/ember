# Independent review of source-Laplacian initialization

Reviewed 2026-09-08 UTC, before end-to-end integration. Scope: the
[specification](spectral_initialization_spec.md),
[initializer](../../packages/ember-qc/src/ember_qc/algorithms/factored/spectral_order.py),
its tests, and the current `plane.arrange`/`native_embed` interfaces. The reviewed
initializer SHA-256 is
`02dd5ad22567f3b0e0d1b5836e1f55b975377de3f275a28823a3e518e5425b56`.
No implementation was edited and no embedding was run for this review.

**Recommendation: proceed with one fixed spectral initialization as a controlled
end-to-end experiment, after the integration conditions below are checked.**
I found no mathematical or independence defect in the reviewed module that
requires abandoning it. This recommendation permits evaluation; it does not
promote the initializer or predict a physical-chain improvement. The existing
broad quality and runtime gaps remain unresolved.

## Source dependence and conventional attribution

The public input consists of integer source adjacency, a seed, numerical limits,
and a deadline. There is no target graph, target coordinate, graph-family label,
saved embedding, training record, or benchmark result in this interface. Inspection
finds no MM/busclique import or call. The only imported numerical capabilities are
NumPy and lazily loaded SciPy. Input connectivity determines component processing;
component size determines a fixed, dimension-at-most-16 dense base case. Neither
is a family-specific constructor choice.

Each component produces one coordinate plane. The third vector is used to assess
the boundary of the selected subspace, not as another embedding result. The code
does not try several layouts and select an output. LOBPCG's internal Ritz updates
are ordinary iterations of the same numerical procedure; they do not constitute
independent embedding algorithms. Components share a work limit and their orders
are concatenated by one declared rule.

The spectral placement objective is conventional. Hall's 1970 paper formulates
quadratic placement through eigenvectors of a graph-derived matrix; this is the
appropriate attribution for the layout relaxation, in addition to the numerical
solver citation. [Hall, *An r-Dimensional Quadratic Placement Algorithm*](https://pubsonline.informs.org/doi/10.1287/mnsc.17.3.219).

LOBPCG should be attributed to Knyazev, with the actual SciPy version recorded.
The constraint, block-start, preconditioner, and smallest-eigenpair API usage match
the official documentation. [Knyazev, 2001](https://doi.org/10.1137/S1064827500366124),
[SciPy 1.15.3 LOBPCG documentation](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.sparse.linalg.lobpcg.html).

The SVD orientation is an orthogonal Procrustes operation, also conventional.
Schönemann's original paper treats this constrained least-squares transformation.
[Schönemann, 1966](https://doi.org/10.1007/BF02289451).
These ingredients do not support a novelty claim on their own. Any eventual
contribution must be evaluated in the complete physical embedding algorithm and
positioned against the existing minor-embedding literature separately.

## Mathematical and numerical checks

For each nontrivial connected component, degrees are positive and
`L = (D - A) / maximum_degree` is symmetric positive semidefinite. Its constant
null vector is unique on that component. Scalar scaling preserves its
eigenvectors; the quadratic form is the source-edge squared-distance objective
divided by maximum degree. The constant-vector constraint therefore removes the
correct null direction without introducing hardware information.

The small dense path removes the first constant eigenvector. The sparse path uses
three centered, QR-orthonormalized starting vectors, an explicit constant-vector
constraint, and a positive diagonal preconditioner. Returned vectors are checked
for finite values, centering, orthonormality, and explicit original-operator Ritz
residuals. Solver rank failures and linear-algebra failures produce no orders;
there is no retry with another initializer.

I checked the installed SciPy 1.15.3 source: its small-problem condition is
`n - sizeY < 5 * sizeX`. Here `sizeY=1` and `sizeX=3` on the sparse path, so the
first sparse size, 17, avoids that fallback. The local implementation resides in
`.venv/codex-native/lib/python3.10/site-packages/scipy/sparse/linalg/_eigen/lobpcg/lobpcg.py`.
The [official SciPy source](https://github.com/scipy/scipy/blob/v1.15.3/scipy/sparse/linalg/_eigen/lobpcg/lobpcg.py)
is the corresponding versioned reference.

A separate source-only boundary check on the 17-vertex path, seed zero, used
`lobpcg`, returned two valid permutations without mutating adjacency, and reported
residuals `1.0281e-6`, `3.6355e-6`, and `7.2011e-6`, with 2450 charged work units
and no warning. This is an API boundary check, not a timing or quality sample.
The implementation author separately reported 19 passing focused tests; those
tests were inspected, not independently rerun here.

For a fixed returned two-dimensional subspace and full-rank reference projection,
the Procrustes factor absorbs sign flips and rotations of the supplied basis.
Multiplying the two vectors by a two-dimensional orthogonal matrix preserves
their total quadratic energy. It does not preserve each eigenvector separately
when their eigenvalues differ; recording residuals before rotation is correct.
An eigenspace that extends beyond the retained plane remains ambiguous. The code
reports that risk through the second/third Ritz gap and reference-rank flag.

Two reporting details deserve precision:

- `residual_tolerance` currently means that the first two vectors meet the
  tolerance. The third residual is recorded and contributes to
  `cutoff_uncertain`, but does not independently change the overall status to
  `approximate`. The specification's implementation addendum now states this
  explicitly. A result summary must not call all three returned modes converged
  from that status alone.
- Canonicalization is not entirely linear time: sorting vertex IDs, components,
  and adjacency contributes sorting cost. Sparse products and storage have the
  stated `O(n+m)` scaling for a fixed block width; the whole preprocessing stage
  should not be described as exclusively linear work.

Neither detail changes the produced orders. Neither is a reason to invent a
fallback or a source-family exception.

## Failure modes that the experiment must expose

**Low-energy coordinates need not mean low ACL.** Sorting discards distances;
rotation changes both orders; coordinate locality can still concentrate physical
wire demand. Packing, conversion, and contact repair optimize different
constraints. Improvement in the initial quadratic objective, source-edge span,
or first packed layout alone is insufficient.

**An accurate residual is not a certificate of the lowest modes.** Spectral
separation, starting vectors, and preconditioning affect LOBPCG convergence, as
the official documentation explains. The fixed iteration limit must remain a
limit. On a regular connected graph the diagonal preconditioner is only a scalar
multiple of the identity, so it does not provide a structural conditioning
improvement. On a long path or weakly connected component, the returned plane
may reflect local smoothing without recovering its long-range structure. These
are risks to test, not grounds to assume that a particular source fails.

The author's saved source-only feasibility table supplies one concrete warning:
all four 4800-vertex examples are labeled approximate, and the path's smallest
returned Ritz value, `2.03825e-4`, is about 952 times its analytic lowest
nonconstant scaled eigenvalue, `1 - cos(pi/4800)`. That table and its reproduction
command are in the specification's implementation addendum. I inspected this
reported evidence without repeating its timing runs. It directly limits a
claim that the bounded policy always recovers global modes; it does not show
that the resulting embedding is good or bad.

**Symmetry does not define a preferred two-dimensional layout.** Many different
planes can be equally optimal for a highly degenerate spectrum. Seed anchoring
cannot resolve a subspace that the eigensolver did not return, and tie bins can
still change when numerical errors cross bin boundaries. Repeatability on the
same numerical stack is weaker than bitwise cross-platform reproducibility or
invariance to vertex relabeling.

**Component blocks may use the fabric poorly.** Keeping disconnected components
contiguous on both axes removes irrelevant interleaving but restricts placement.
Only the cumulative embedding result can show whether the rule is useful. Its
policy must stay fixed across the evaluation.

**The operation limit is not an overall resource limit.** Matrix assembly,
Python sets/lists, QR/SVD, preconditioning, sorting, imports, and allocations are
not charged as sparse products. Deadline checks are cooperative and can observe
an overrun after an operation. The standalone API may allocate a large adjacency
before its first charged multiply; the native adapter's existing source-capacity
check should precede initialization. An end-to-end watchdog remains necessary
for truthful wall-time accounting.

## Integration conditions

The reviewed standalone module is ready for integration work. The following are
concrete conditions on that work, not unresolved mathematical defects:

1. **Respect the order/rank distinction.** The returned lists name vertices in
   coordinate order. Invert each list into a vertex-to-rank map before assigning
   `plane.arrange` positions. Treating a permutation as an array of ranks can
   silently initialize a different layout while preserving superficial coverage.
2. **Preserve one trajectory and one original deadline.** Use one pair of orders,
   keep the scheduler generator's independent reset, and charge spectral time to
   the same absolute deadline as construction and repair. Do not compare its
   output with a random initialization inside the solver. Equal-ask experiments
   and equal-total-time experiments answer different questions; record both
   honestly when evaluating the complete method.
3. **Keep failures explicit.** Missing SciPy, numerical failure, work exhaustion,
   or an expired deadline must not silently substitute random ranks. The package
   does not yet declare SciPy directly, so deployment must decide and record the
   dependency before using this policy. Preserve the standalone diagnosis in the
   end-to-end result and continue to validate every final embedding normally.
4. **State the actual reproducibility boundary.** `native_embed` currently maps
   source vertices to integers using source insertion order. Thus the module's
   insertion-order invariance on a fixed integer adjacency does not establish
   insertion-order invariance of the entire native adapter. The adapter is still
   source-only, but any stronger invariance claim requires an adapter-level test
   and a declared labeling rule. No metadata-based identity should enter the
   initializer to conceal this difference.

No hidden dependency on MM, target-specific input to this initializer, or
portfolio selection was found. The appropriate next evidence is a prespecified
comparison of complete valid embeddings, including failures and all initialization
time, against the same fixed baseline. The spectral relaxation itself supplies
neither an ACL bound nor evidence of an across-class win.
