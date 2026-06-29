"""
ember_qc/algorithms/diffembed.py
================================
Differentiable embedding by annealed soft-assignment (approach 3.2).

Minor embedding, viewed continuously: represent the assignment of the ``m``
hardware qubits to the ``n`` logical vertices as a **soft matrix**
``S ∈ R^{m×(n+1)}`` that is *row-stochastic* — every qubit row is a probability
distribution over the ``n`` chains **plus one "unassigned" column**, so a qubit
belongs to at most one chain while a chain may own many qubits (many-to-one, the
opposite of a permutation).  ``S = softmax(Z / τ)`` for free logits ``Z`` and a
temperature ``τ`` that is annealed from ~1 toward ~0 (the Gumbel–Sinkhorn
sharpening idea of Mena et al. 2018, here run deterministically without the
Gumbel perturbation).  The whole objective is smooth and is minimised by Adam:

    L(S) = − w_edge · edge_satisfaction(S)      (reward adjacent vertices on adjacent qubits)
           + w_cont  · contiguity(S)            (Dirichlet energy  trace(Sᵀ L_G S))
           + w_load  · load(S)                  (a qubit split across >1 chain)
           + w_spread· spread(S)                (total assigned mass — keeps chains short)

* **Edge satisfaction** rewards, for every source edge ``(u,v)``, soft adjacency
  ``Σ_{(q,r)∈E(G)} S[q,u]S[r,v] + S[q,v]S[r,u] = Σ S_uᵀ A_G S_v`` — maximised when
  the two logical vertices sit on *adjacent* qubits.
* **Contiguity** is the graph-Laplacian Dirichlet energy ``trace(Sᵀ L_G S) =
  Σ_{(q,r)∈E(G)} ‖S[q]−S[r]‖²``: a smoothness prior that makes each chain's
  membership vary slowly across the fabric → compact, near-connected supports.
* **Load** penalises a qubit shared by two chains, ``Σ_q (a_q² − Σ_v S[q,v]²)``
  with ``a_q`` the qubit's total assigned mass — zero iff each row is one-hot.
* **Spread** penalises total assigned mass so the "unassigned" escape column is
  used and chains stay short.

Contiguity is *soft* — it encourages but does not guarantee connected chains — so
the relaxation only does **placement**; the shared round→repair backend
(:mod:`ember_qc.embedding_backend`) turns the annealed ``S`` into a *valid*
embedding: ``round_assignment_matrix`` (argmax per qubit, the unassigned column
acting as a learned threshold) → ``grow_to_connected`` → ``resolve_overlaps``.
Because non-convex descent is init-sensitive, ``S`` is warm-started from one
cheap ``minorminer`` pass (relaxed to logits); a random / spectral start is
available for ablation.  The best *valid* embedding seen across the τ schedule is
returned, so the method is never worse than its minorminer seed.

Registered:  ``diff-softassign``.

Pure ``torch`` (CPU); no GPU or optional deps beyond ``torch`` / ``numpy``.
"""

from __future__ import annotations

import logging
import random as _random
import time
from typing import Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import (
    Adjacency,
    Embedding,
    build_adjacency,
    grow_to_connected,
    is_valid_embedding,
    reconstruct_path,
    resolve_overlaps,
    round_assignment_matrix,
    weighted_multisource_dijkstra,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Soft-assignment optimiser
# ==============================================================================

class DiffSoftAssign:
    """One annealed soft-assignment run over a fixed (source, target) pair.

    Owns the torch state (logits ``Z``, the fixed graph operators) and exposes
    :meth:`run`, which anneals τ, rounds+repairs at every temperature level, and
    returns the best valid embedding together with a per-level ACL trace (the
    τ-annealing diagnostic).
    """

    def __init__(
        self,
        source: nx.Graph,
        target: nx.Graph,
        *,
        seed: int = 0,
        init: str = "mm",
        # objective weights (on count-normalised terms, so all are O(1)).
        # Defaults are tuned so a minorminer warm start stays inside the valid
        # basin under annealing (load dominates to keep rows one-hot; edge+
        # contiguity nudge placement; spread is gentle) — see the candidate doc.
        w_edge: float = 1.0,
        w_cont: float = 0.05,
        w_load: float = 2.0,
        w_spread: float = 0.02,
        # temperature homotopy
        tau_start: float = 1.0,
        tau_end: float = 0.08,
        n_levels: int = 7,
        inner_steps: int = 25,
        lr: float = 0.03,
        init_logit: float = 4.0,
        init_noise: float = 0.30,
        repair_passes: int = 20,
    ):
        import torch  # local import: torch is heavy and only needed here

        self.torch = torch
        self.source = source
        self.target = target
        self.seed = int(seed)
        self.init = init

        self.w_edge = w_edge
        self.w_cont = w_cont
        self.w_load = w_load
        self.w_spread = w_spread
        self.tau_start = tau_start
        self.tau_end = tau_end
        self.n_levels = max(1, n_levels)
        self.inner_steps = max(1, inner_steps)
        self.lr = lr
        self.init_logit = init_logit
        self.init_noise = init_noise
        self.repair_passes = repair_passes

        # Determinism: seed every RNG torch/numpy/python might touch, pin threads
        # (single-thread CPU reductions are order-stable ⇒ seed-stable output).
        torch.manual_seed(self.seed)
        np.random.seed(self.seed % (2**32))
        _random.seed(self.seed)
        try:
            torch.set_num_threads(1)
        except Exception:
            pass

        # ---- frozen graph operators ------------------------------------------
        self.adj: Adjacency = build_adjacency(target)
        self.qubit_nodes: List[int] = [int(q) for q in self.adj.keys()]
        self.m = len(self.qubit_nodes)
        self.q_index: Dict[int, int] = {q: i for i, q in enumerate(self.qubit_nodes)}

        self.src_nodes: List[int] = [int(v) for v in source.nodes()]
        self.n = len(self.src_nodes)
        self.s_index: Dict[int, int] = {v: j for j, v in enumerate(self.src_nodes)}

        # Target edge index (one direction) as qubit positions, for Dirichlet
        # energy and a symmetric sparse adjacency for the edge-satisfaction term.
        e_src, e_dst = [], []
        for u, nbrs in self.adj.items():
            iu = self.q_index[int(u)]
            for w in nbrs:
                iw = self.q_index[int(w)]
                if iu < iw:  # undirected, once
                    e_src.append(iu)
                    e_dst.append(iw)
        self.edge_src = torch.tensor(e_src, dtype=torch.long)
        self.edge_dst = torch.tensor(e_dst, dtype=torch.long)
        self.n_tedges = len(e_src)

        # Source adjacency A_H as a dense {0,1} (n×n) — n is tens of vertices.
        self.A_H = torch.zeros((self.n, self.n), dtype=torch.float32)
        for u, v in source.edges():
            iu, iv = self.s_index[int(u)], self.s_index[int(v)]
            self.A_H[iu, iv] = 1.0
            self.A_H[iv, iu] = 1.0
        self.n_sedges = int(source.number_of_edges())

        # The logits.  Column n is the "unassigned" escape column.
        self.Z = None  # set by _init_logits

    # -------------------------------------------------------------- init -------

    def _mm_embedding(self, timeout: float) -> Optional[Embedding]:
        """One quick minorminer pass to warm-start placement (None on failure)."""
        try:
            import minorminer
            raw = minorminer.find_embedding(
                self.source, list(self.target.edges()),
                random_seed=self.seed, timeout=max(0.5, timeout), verbose=0,
            )
        except Exception as exc:
            logger.debug("diffembed mm seed failed: %s", exc)
            return None
        if not raw:
            return None
        qset = set(self.qubit_nodes)
        emb: Embedding = {}
        for v in self.src_nodes:
            chain = raw.get(v)
            if not chain or any(int(q) not in qset for q in chain):
                return None
            emb[v] = [int(q) for q in chain]
        return emb

    def _init_logits(self, mm_emb: Optional[Embedding]) -> None:
        """Build the (m, n+1) logit matrix according to ``self.init``."""
        torch = self.torch
        Z = torch.zeros((self.m, self.n + 1), dtype=torch.float32)

        if self.init == "spectral":
            self._spectral_logits(Z)
        elif self.init == "mm" and mm_emb is not None:
            # One-hot the minorminer chains; everything else points "unassigned".
            Z[:, self.n] = self.init_logit  # default: unassigned
            for v, chain in mm_emb.items():
                col = self.s_index[int(v)]
                for q in chain:
                    i = self.q_index[int(q)]
                    Z[i, self.n] = 0.0
                    Z[i, col] = self.init_logit
        # 'random' (or mm-fallback / spectral) keeps the small-noise base below.

        # Reproducible symmetry-breaking noise (torch RNG already seeded).
        Z = Z + self.init_noise * torch.randn(self.m, self.n + 1)
        self.Z = Z.clone().detach().requires_grad_(True)

    def _spectral_logits(self, Z) -> None:
        """Init logits from low Laplacian eigenvectors (placement by geometry).

        Embeds qubits and source vertices into the same low-dimensional Laplacian
        eigenspace and seeds each qubit's logits by proximity to source vertices.
        A cheap, MM-free geometric warm start used only for ablation.
        """
        torch = self.torch
        try:
            import scipy.sparse as sp
            import scipy.sparse.linalg as spla
        except Exception:
            return  # leave logits at zero → effectively random init

        k = min(8, max(2, self.m - 2))

        def coords(g: nx.Graph, nodes: List[int], idx: Dict[int, int]):
            n = len(nodes)
            rows, cols = [], []
            for a, b in g.edges():
                ia, ib = idx[int(a)], idx[int(b)]
                rows += [ia, ib]
                cols += [ib, ia]
            A = sp.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
            deg = np.asarray(A.sum(1)).ravel()
            L = sp.diags(deg) - A
            kk = min(k + 1, n - 1)
            if kk < 2:
                return np.zeros((n, k))
            try:
                vals, vecs = spla.eigsh(L.astype(float), k=kk, which="SM")
            except Exception:
                return np.zeros((n, k))
            order = np.argsort(vals)
            vecs = vecs[:, order][:, 1:]  # drop the constant eigenvector
            out = np.zeros((n, k))
            out[:, : vecs.shape[1]] = vecs
            return out

        qc = coords(self.target, self.qubit_nodes, self.q_index)
        sc = coords(self.source, self.src_nodes, self.s_index)
        if qc.shape[1] == 0 or sc.shape[1] == 0:
            return
        # standardise each axis so the two spectra share a scale
        for M in (qc, sc):
            std = M.std(0)
            std[std == 0] = 1.0
            M -= M.mean(0)
            M /= std
        d2 = ((qc[:, None, :] - sc[None, :, :]) ** 2).sum(-1)  # (m, n)
        Z[:, : self.n] = torch.tensor(-d2, dtype=torch.float32)
        Z[:, : self.n] *= (self.init_logit / max(1.0, float(np.abs(d2).max())))

    # ----------------------------------------------------------- objective -----

    def _soft(self, tau: float):
        """Row-softmax of the logits at temperature ``tau`` → (m, n+1) matrix."""
        return self.torch.softmax(self.Z / max(tau, 1e-6), dim=1)

    def _adj_matmul(self, X):
        """Sparse product ``A_G · X`` via edge-list scatter (differentiable, CPU-stable).

        ``(A_G X)[q] = Σ_{r ~ q} X[r]``; accumulated over the undirected edge list
        in both directions.  Avoids a ``torch.sparse`` tensor (and its invariant
        warning) while staying O(|E_G|·n).
        """
        torch = self.torch
        out = torch.zeros((self.m, X.shape[1]), dtype=X.dtype)
        if self.n_tedges:
            out = out.index_add(0, self.edge_src, X.index_select(0, self.edge_dst))
            out = out.index_add(0, self.edge_dst, X.index_select(0, self.edge_src))
        return out

    def _loss(self, S, tau: float):
        """Scalar loss at the current logits and temperature ``tau``."""
        torch = self.torch
        S_real = S[:, : self.n]                     # drop the unassigned column

        # Edge satisfaction:  Σ_{(u,v)∈E_H} (S_uᵀ A_G S_v) / (c_u c_v), where
        # c_v = Σ_q S[q,v] is column mass.  Column-normalising is essential: the
        # raw bilinear form Σ S_uᵀ A_G S_v grows quadratically with claimed mass,
        # so its unconstrained optimum piles every chain onto the same dense
        # region (huge reward, ungrowable rounding).  Dividing by c_u c_v removes
        # any benefit from spreading/overlap, so the reward (≤ ~1 per edge) is
        # maximised only by concentrating adjacent vertices on *adjacent* qubits.
        AS = self._adj_matmul(S_real)               # (m, n) = A_G · S_real
        M = S_real.t().mm(AS)                        # (n, n) = S_realᵀ A_G S_real
        c = S_real.sum(0)                            # (n,) column mass
        cc = c.unsqueeze(1) * c.unsqueeze(0) + 1e-3  # outer product (+ guard)
        edge_sat = (self.A_H * (M / cc)).sum() / max(1, self.n_sedges)

        # Contiguity (Dirichlet energy):  Σ_{(q,r)∈E_G} ‖S_real[q]−S_real[r]‖²
        if self.n_tedges:
            diff = S_real.index_select(0, self.edge_src) - S_real.index_select(0, self.edge_dst)
            contig = (diff * diff).sum() / self.n_tedges
        else:
            contig = torch.zeros((), dtype=S.dtype)

        # Load:  a qubit split across >1 chain.  Σ_q (a_q² − Σ_v S[q,v]²) ≥ 0.
        a = S_real.sum(1)                            # (m,) assigned mass per qubit
        load = (a * a - (S_real * S_real).sum(1)).sum() / self.m

        # Spread: total assigned mass (push surplus qubits to "unassigned").
        spread = a.sum() / self.m

        return (-self.w_edge * edge_sat
                + self.w_cont * contig
                + self.w_load * load
                + self.w_spread * spread)

    # ------------------------------------------------------------- rounding ----

    def _round_repair(self, S_np: np.ndarray, repair_seed: int) -> Optional[Embedding]:
        """Round a soft matrix and repair it into a valid embedding (or None).

        ``S_np`` is the full (m, n+1) softmax.  A qubit is assigned to its argmax
        *real* column only when that beats the unassigned column; otherwise it is
        left free.  Source vertices that win no qubit are seeded with their most
        probable free qubit so coverage holds, then the shared backend grows and
        legalises the chains.
        """
        S_real = S_np[:, : self.n]
        unassigned = S_np[:, self.n]
        real_max = S_real.max(axis=1)
        keep = real_max > unassigned          # real column beats "unassigned"

        masked = np.where(keep[:, None], S_real, 0.0)
        chains = round_assignment_matrix(
            masked, self.qubit_nodes, self.src_nodes, threshold=0.0
        )

        # Coverage: give every empty chain a seed qubit (prefer a free one).
        assigned = {q for ch in chains.values() for q in ch}
        for v in self.src_nodes:
            if chains.get(v):
                continue
            col = self.s_index[v]
            # qubits by descending membership in this column, id as tiebreak
            order = sorted(range(self.m), key=lambda i: (-S_real[i, col], self.qubit_nodes[i]))
            pick = None
            for i in order:
                q = self.qubit_nodes[i]
                if q not in assigned:
                    pick = q
                    break
            if pick is None:
                pick = self.qubit_nodes[order[0]]  # all taken → overlap; repair fixes
            else:
                assigned.add(pick)
            chains[v] = [pick]

        grown = grow_to_connected(chains, self.target, adj=self.adj)
        emb = resolve_overlaps(
            grown, self.source, self.target,
            max_passes=self.repair_passes, seed=repair_seed, adj=self.adj,
        )
        if emb is not None:
            return emb
        # resolve_overlaps makes chains connected & disjoint but never moves two
        # chains together, so it fails (returns None) when the soft placement
        # left adjacent vertices apart — an *edge-coverage* miss.  Stitch those
        # edges with shortest-path connectors (backend Dijkstra) and retry.
        stitched = self._stitch_edges(grown)
        return resolve_overlaps(
            stitched, self.source, self.target,
            max_passes=self.repair_passes, seed=repair_seed, adj=self.adj,
        )

    def _stitch_edges(self, chains: Embedding, rounds: int = 4) -> Embedding:
        """Extend chains so every source edge is covered (best-effort, bounded).

        For each uncovered source edge the *shorter* chain is grown toward the
        other along a node-weighted shortest path — free / own qubits cost 1,
        qubits owned by a third chain cost a detour penalty (borrowed only when
        unavoidable, then cleaned up by a subsequent ``resolve_overlaps``).  This
        is exactly the routing the relaxation's soft contiguity term cannot
        guarantee; it reuses the backend's Dijkstra primitives so the behaviour
        matches the rest of ember-qc.  Deterministic; at most ``rounds`` sweeps.
        """
        adj = self.adj
        DETOUR = 50.0
        work: Embedding = {int(v): [int(q) for q in c] for v, c in chains.items()}
        for _ in range(rounds):
            owner: Dict[int, set] = {}
            for v, c in work.items():
                for q in c:
                    owner.setdefault(q, set()).add(v)
            uncovered: List[Tuple[int, int]] = []
            for u, v in self.source.edges():
                cv = set(work[v])
                if not any(w in cv for q in work[u] for w in adj.get(q, ())):
                    uncovered.append((int(u), int(v)))
            if not uncovered:
                break
            for u, v in uncovered:
                a, b = (u, v) if len(work[u]) <= len(work[v]) else (v, u)
                ca, cb = set(work[a]), set(work[b])
                if any(w in cb for q in ca for w in adj.get(q, ())):
                    continue  # already fixed by an earlier stitch this sweep
                targets = {w for q in cb for w in adj.get(q, ()) if w not in cb}
                if not targets:
                    continue
                cost = {q: (1.0 if (q not in owner or owner[q] <= {a}) else DETOUR)
                        for q in adj}
                dist, pred = weighted_multisource_dijkstra(
                    adj, ca, cost, targets=set(targets)
                )
                reach = [(dist[t], t) for t in targets if t in dist]
                if not reach:
                    continue
                _, nearest = min(reach, key=lambda t: (t[0], t[1]))
                path = reconstruct_path(pred, nearest)
                if not path:
                    continue
                merged = sorted(set(work[a]) | set(path))
                work[a] = merged
                for q in path:
                    owner.setdefault(q, set()).add(a)
        return work

    # -------------------------------------------------------------- driver -----

    @staticmethod
    def _acl(emb: Embedding) -> float:
        return sum(len(c) for c in emb.values()) / max(1, len(emb))

    def _better(self, cand: Embedding, best: Optional[Embedding]) -> bool:
        """Prefer fewer total qubits, then lower max chain (deterministic)."""
        if best is None:
            return True
        ct, bt = sum(len(c) for c in cand.values()), sum(len(c) for c in best.values())
        if ct != bt:
            return ct < bt
        return max(map(len, cand.values())) < max(map(len, best.values()))

    def run(self, deadline: Optional[float], mm_timeout: float
            ) -> Tuple[Optional[Embedding], List[dict]]:
        """Anneal τ, round+repair at each level, return (best valid emb, trace)."""
        torch = self.torch
        mm_emb = self._mm_embedding(mm_timeout) if self.init == "mm" else None
        self._init_logits(mm_emb)

        best: Optional[Embedding] = None
        trace: List[dict] = []

        # Seed "best" with the warm start itself so we never regress below MM.
        if mm_emb is not None and is_valid_embedding(mm_emb, self.source, self.target, adj=self.adj):
            best = {int(v): [int(q) for q in c] for v, c in mm_emb.items()}

        opt = torch.optim.Adam([self.Z], lr=self.lr)
        # geometric temperature ladder τ_start → τ_end
        if self.n_levels == 1:
            taus = [self.tau_end]
        else:
            ratio = (self.tau_end / self.tau_start) ** (1.0 / (self.n_levels - 1))
            taus = [self.tau_start * ratio**i for i in range(self.n_levels)]

        for level, tau in enumerate(taus):
            for _ in range(self.inner_steps):
                opt.zero_grad()
                S = self._soft(tau)
                loss = self._loss(S, tau)
                loss.backward()
                opt.step()
            if deadline is not None and time.perf_counter() > deadline:
                # Safety only: a well-budgeted run never trips this, so normal
                # operation stays fully deterministic.
                break

            with torch.no_grad():
                S_np = self._soft(tau).detach().cpu().numpy().astype(np.float64)
                cur_loss = float(self._loss(self._soft(tau), tau))
            emb = self._round_repair(S_np, repair_seed=self.seed + level)
            rec = {"level": level, "tau": round(float(tau), 4),
                   "loss": round(cur_loss, 4),
                   "valid": bool(emb is not None),
                   "acl": round(self._acl(emb), 3) if emb else None}
            trace.append(rec)
            if emb is not None and self._better(emb, best):
                best = emb

            if deadline is not None and time.perf_counter() > deadline:
                break

        return best, trace


# ==============================================================================
# Functional entry point + registration
# ==============================================================================

def embed_diff_softassign(
    source_graph: nx.Graph,
    target_graph: nx.Graph,
    *,
    timeout: float = 60.0,
    seed: int = 0,
    return_trace: bool = False,
    mm_fraction: float = 0.5,
    **params,
) -> dict:
    """Run annealed soft-assignment and return an ember-qc result dict.

    Always returns a dict (never ``None``, never raises): on success
    ``{"embedding": {v:[q,...]}, "time": t}`` with plain-int chains; on failure
    ``{"embedding": {}, "time": t, "success": False, "status": "FAILURE"}``.
    """
    start = time.perf_counter()
    deadline = start + timeout if timeout and timeout > 0 else None
    mm_timeout = max(0.5, timeout * mm_fraction) if timeout and timeout > 0 else 30.0
    try:
        solver = DiffSoftAssign(source_graph, target_graph, seed=int(seed), **params)
        best, trace = solver.run(deadline, mm_timeout)
        elapsed = max(time.perf_counter() - start, 1e-6)
        if not best:
            out = {"embedding": {}, "time": elapsed,
                   "success": False, "status": "FAILURE"}
        else:
            emb = {int(v): [int(q) for q in c] for v, c in best.items()}
            out = {"embedding": emb, "time": elapsed}
        if return_trace:
            out["trace"] = trace
        return out
    except Exception as exc:  # contract: never raise
        logger.error("diffembed error: %s", exc)
        return {"embedding": {}, "time": max(time.perf_counter() - start, 1e-6),
                "success": False, "status": "FAILURE", "error": str(exc)}


@register_algorithm("diff-softassign")
class DiffSoftAssignAlgorithm(EmbeddingAlgorithm):
    """Differentiable annealed soft-assignment — global continuous placement,
    minorminer-seeded, rounded and repaired by the shared backend (approach 3.2)."""

    @property
    def version(self) -> str:
        return "1.0.0"

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs) -> dict:
        seed = kwargs.get("seed", 0)
        if seed is None:
            seed = 0
        return embed_diff_softassign(
            source_graph, target_graph, timeout=timeout, seed=int(seed),
        )
