"""One bounded approximate Laplacian initialization from source adjacency only.

This conventional spectral layout is an optional initializer, not an embedder.
Finite iteration-limited Ritz vectors are used and explicitly labeled approximate.
Work/deadline/numerical failures return no orders; there is no alternate initializer.
"""
from __future__ import annotations

from numbers import Integral
import time
import warnings

import numpy as np


class _Stopped(Exception):
    pass


class _Work:
    def __init__(self, limit, deadline):
        self.limit = limit
        self.deadline = deadline
        self.used = 0
        self.columns = 0
        self.dense = 0

    def check(self):
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise _Stopped('deadline')

    def charge(self, cost, *, columns=0, dense=False):
        self.check()
        if self.used + cost > self.limit:
            raise _Stopped('work_limit')
        self.used += cost
        self.columns += columns
        if dense:
            self.dense += cost


def _components(src_adj, work):
    """Validate a simple undirected integer adjacency and canonicalize it."""
    ids = list(src_adj)
    if any(not isinstance(v, Integral) or isinstance(v, bool) for v in ids):
        raise ValueError('Source vertices must be integer IDs')
    ids.sort()
    known = set(ids)
    adj = {}
    for v in ids:
        work.check()
        neighbors = set(src_adj[v])
        if v in neighbors or not neighbors <= known:
            raise ValueError('Source adjacency must be loop-free with known vertices')
        adj[v] = neighbors
    for v in ids:
        work.check()
        if any(v not in adj[u] for u in adj[v]):
            raise ValueError('Source adjacency must be undirected')
    remaining = set(ids)
    components = []
    for start in ids:
        if start not in remaining:
            continue
        remaining.remove(start)
        pending = [start]
        component = []
        while pending:
            work.check()
            v = pending.pop()
            component.append(v)
            for u in adj[v]:
                if u in remaining:
                    remaining.remove(u)
                    pending.append(u)
        components.append(sorted(component))
    components.sort(key=lambda component: (-len(component), component[0]))
    return ids, adj, components


def _orient(vectors, references):
    """Anchor a fixed returned subspace; cannot resolve a larger cutoff tie."""
    selected = vectors[:, :min(2, vectors.shape[1])]
    if selected.shape[1] == 1:
        dot = float(selected[:, 0] @ references[:, 0])
        direction = selected[:, 0] * (-1.0 if dot < 0 else 1.0)
        return np.column_stack((direction, direction)), abs(dot) <= 1e-12
    left, singular, right = np.linalg.svd(selected.T @ references[:, :2])
    oriented = selected @ (left @ right)
    deficient = bool(singular[-1] <= 1e-12 * max(1.0, singular[0]))
    return oriented, deficient


def _axis_order(component, coordinates, priorities):
    scale = float(np.max(np.abs(coordinates)))
    bins = (np.rint(coordinates / (scale * 1e-10)).astype(np.int64)
            if scale > 0 else np.zeros(len(component), dtype=np.int64))
    return [component[i] for i in sorted(range(len(component)),
            key=lambda i: (int(bins[i]), int(priorities[i]), component[i]))]


def spectral_orders(src_adj, *, seed=0, max_iterations=64, tolerance=1e-5,
                    max_work=50_000_000, deadline=None):
    """Return ``((x_order, y_order), diagnostics)`` or ``(None, diagnostics)``.

    The input is simple undirected adjacency with integer vertex IDs, matching
    the geometric constructor's internal source representation. Graph metadata
    and target hardware are absent from this interface. Approximate output is
    accepted under one fixed rule; a small residual is not a lowest-mode proof.

    Work is charged before sparse operator products as nonzeros times columns,
    and before the dense base case as dimension cubed. Preprocessing, sorting,
    orthogonalization, and preconditioning are additional uncounted work.
    ``deadline`` uses ``time.perf_counter`` and is checked cooperatively.
    """
    if (not isinstance(max_iterations, Integral) or isinstance(max_iterations, bool)
            or max_iterations < 0):
        raise ValueError('max_iterations must be a nonnegative integer')
    if (not isinstance(max_work, Integral) or isinstance(max_work, bool)
            or max_work < 0):
        raise ValueError('max_work must be a nonnegative integer')
    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('tolerance must be positive and finite')
    if deadline is not None and not np.isfinite(deadline):
        raise ValueError('deadline must be finite or None')
    started = time.perf_counter()
    work = _Work(int(max_work), deadline)
    info = {'policy': 'component_scaled_laplacian_lobpcg', 'seed': int(seed),
            'max_iterations': int(max_iterations), 'tolerance': float(tolerance),
            'max_work': int(max_work), 'numpy_version': np.__version__,
            'scipy_version': None, 'components': [], 'warnings': []}

    def finish(orders, status):
        ended = time.perf_counter()
        overrun = max(0.0, ended - deadline) if deadline is not None else 0.0
        if deadline is not None and ended >= deadline:
            status, orders = 'deadline', None
        info.update(status=status, wall=ended - started, deadline_overrun=overrun,
                    work=work.used, operator_columns=work.columns,
                    dense_work=work.dense)
        return orders, info

    try:
        work.check()
        ids, adj, components = _components(src_adj, work)
        info.update(vertices=len(ids), edges=sum(map(len, adj.values())) // 2,
                    component_count=len(components))
        # Lazy optional dependency: isolates do not require an eigensolver.
        # There is no alternate solver on import failure.
        if any(len(component) > 1 for component in components):
            try:
                import scipy
                from scipy import sparse
                from scipy.sparse.linalg import lobpcg
            except ImportError as exc:
                info['error'] = str(exc)
                return finish(None, 'dependency_unavailable')
            info['scipy_version'] = scipy.__version__
        rng = np.random.default_rng(seed)
        orders = ([], [])
        approximate = False
        for component in components:
            work.check()
            n = len(component)
            entry = {'first_vertex': int(component[0]), 'vertices': n,
                     'edges': sum(len(adj[v]) for v in component) // 2}
            info['components'].append(entry)
            component_started = time.perf_counter()
            before_work = work.used
            if n == 1:
                orders[0].extend(component)
                orders[1].extend(component)
                entry.update(solver='isolate', status='trivial', work=0, wall=0.0,
                             eigenvalues=[], residuals=[], cutoff_uncertain=False,
                             reference_rank_deficient=False)
                continue
            ranks = {v: i for i, v in enumerate(component)}
            degrees = np.array([len(adj[v]) for v in component], dtype=float)
            maximum_degree = float(np.max(degrees))
            rows, columns = [], []
            for v in component:
                work.check()
                neighbors = sorted(adj[v])
                rows.extend([ranks[v]] * len(neighbors))
                columns.extend(ranks[u] for u in neighbors)
            adjacency = sparse.csr_matrix((np.ones(len(rows)), (rows, columns)),
                                          shape=(n, n))
            laplacian = (sparse.diags(degrees) - adjacency).tocsr()
            laplacian /= maximum_degree
            entry['operator_nonzeros'] = int(laplacian.nnz)

            def multiply(block):
                width = 1 if block.ndim == 1 else block.shape[1]
                work.charge(int(laplacian.nnz) * width, columns=width)
                result = laplacian @ block
                work.check()
                return result

            def precondition(block):
                work.check()
                inverse = maximum_degree / degrees
                result = inverse * block if block.ndim == 1 else inverse[:, None] * block
                work.check()
                return result

            references = rng.standard_normal((n, 3))
            references -= references.mean(axis=0)
            priorities = rng.permutation(n)
            block_size = min(3, n - 1)
            if n <= 16:
                entry['solver'] = 'dense_base_case'
                work.charge(n ** 3, dense=True)
                values, vectors = np.linalg.eigh(laplacian.toarray())
                work.check()
                values, vectors = values[1:1 + block_size], vectors[:, 1:1 + block_size]
            else:
                entry['solver'] = 'lobpcg'
                initial, _ = np.linalg.qr(references)
                constant = np.full((n, 1), 1.0 / np.sqrt(n))
                with warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter('always', UserWarning)
                    try:
                        values, vectors = lobpcg(
                            multiply, initial[:, :block_size], Y=constant,
                            M=precondition, largest=False, tol=float(tolerance),
                            maxiter=int(max_iterations))
                    except ValueError as exc:
                        # Solver constraints/rank failures are numerical failures;
                        # malformed source adjacency has already raised explicitly.
                        raise FloatingPointError(str(exc)) from exc
                info['warnings'].extend(str(item.message)[:1000]
                                        for item in captured[:10])
                info['warnings'] = info['warnings'][:20]
                order = np.argsort(values)
                values, vectors = values[order], vectors[:, order]
            if not np.isfinite(values).all() or not np.isfinite(vectors).all():
                raise FloatingPointError('Non-finite spectral output')
            residuals = np.linalg.norm(multiply(vectors) - vectors * values, axis=0)
            centered_error = float(np.max(np.abs(vectors.sum(axis=0))) / np.sqrt(n))
            orthogonal_error = float(np.linalg.norm(vectors.T @ vectors - np.eye(block_size)))
            if (not np.isfinite(residuals).all() or centered_error > 1e-7
                    or orthogonal_error > 1e-7):
                raise FloatingPointError('Returned vectors are not a finite centered orthonormal block')
            residual_converged = bool(np.max(residuals[:2]) <= tolerance)
            approximate |= not residual_converged
            gap = float(values[2] - values[1]) if len(values) > 2 else None
            uncertain = bool(gap is not None and gap <= max(
                10 * tolerance, 4 * float(residuals[1] + residuals[2])))
            coordinates, deficient = _orient(vectors, references)
            for axis in (0, 1):
                orders[axis].extend(_axis_order(component, coordinates[:, axis], priorities))
            entry.update(status='residual_tolerance' if residual_converged else 'approximate',
                         eigenvalues=values.tolist(), residuals=residuals.tolist(),
                         cutoff_gap=gap, cutoff_uncertain=uncertain,
                         reference_rank_deficient=deficient,
                         centered_error=centered_error, orthogonal_error=orthogonal_error,
                         work=work.used - before_work,
                         wall=time.perf_counter() - component_started)
        work.check()
        if any(len(order) != len(ids) or set(order) != set(ids) for order in orders):
            raise FloatingPointError('Output does not preserve source coverage')
        return finish(orders, 'approximate' if approximate else 'residual_tolerance')
    except _Stopped as exc:
        return finish(None, str(exc))
    except (FloatingPointError, np.linalg.LinAlgError) as exc:
        info['error'] = str(exc)
        return finish(None, 'numerical_failure')
